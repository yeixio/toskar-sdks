use std::collections::BTreeMap;
use std::sync::Arc;
use std::time::Duration;

use bytes::Bytes;
use futures_util::stream::BoxStream;
use futures_util::{StreamExt, stream};
use reqwest::header::{ACCEPT, AUTHORIZATION, CONTENT_TYPE, HeaderMap, HeaderName, HeaderValue};
use reqwest::{Method, Url};
use serde::de::DeserializeOwned;

use crate::connect::{self, ConnectionPath, Device, Pinning, Router};
use crate::generated::codes::{CONTRACT_VERSION, error_codes};
use crate::models::{ChatAnswer, ChatDone, ChatRequest, ChatToken, Event, GenerationMetrics, VersionResponse};
use crate::{Api, Error, Result, sse};

/// This computer's Toskar Core, which needs no key.
pub const DEFAULT_URL: &str = "http://127.0.0.1:7331";

/// The most of an error answer read; Core's are small.
const ERROR_LIMIT: usize = 1 << 20;

/// A connection to Toskar Core. It's cheap to clone: clones share their
/// connections.
#[derive(Clone, Debug)]
pub struct Client {
    url: Url,
    headers: HeaderMap,
    retries: u32,
    timeout: Duration,
    http: reqwest::Client,
    router: Option<Arc<Router>>,
}

/// One event of a streamed chat.
#[derive(Clone, Debug, PartialEq)]
pub enum ChatEvent {
    /// The next piece of the answer.
    Token(String),
    /// The answer is finished and saved, with what the runtime measured when it reported it.
    Done(Option<GenerationMetrics>),
}

/// How to connect: every setting has a default. Start with [`Client::builder`].
#[derive(Clone, Debug, Default)]
pub struct Builder {
    url: Option<String>,
    key: Option<String>,
    retries: Option<u32>,
    timeout: Option<Duration>,
    http: Option<reqwest::Client>,
    headers: BTreeMap<String, String>,
    device: Option<Device>,
    pub(crate) relay_http: Option<reqwest::Client>,
}

impl Builder {
    /// Where Toskar Core answers. Default: `TOSKAR_URL`, or [`DEFAULT_URL`], this computer.
    pub fn url(mut self, url: impl Into<String>) -> Self {
        self.url = Some(url.into());
        self
    }

    /// The API key for any address other than this computer's loopback. Default: `TOSKAR_API_KEY`.
    pub fn key(mut self, key: impl Into<String>) -> Self {
        self.key = Some(key.into());
        self
    }

    /// How many times a safe request (GET, HEAD, OPTIONS) that fails to
    /// connect or answers 502, 503, or 504 is retried. Default: 2. A chat is
    /// never retried: it could answer twice.
    pub fn retries(mut self, retries: u32) -> Self {
        self.retries = Some(retries);
        self
    }

    /// How long to wait for an answer to start. Default: 60 seconds. A
    /// streamed answer then runs for as long as it takes.
    pub fn timeout(mut self, timeout: Duration) -> Self {
        self.timeout = Some(timeout);
        self
    }

    /// The reqwest client to send requests with, in place of one the SDK makes.
    pub fn http_client(mut self, http: reqwest::Client) -> Self {
        self.http = Some(http);
        self
    }

    /// A header to add to every request.
    pub fn header(mut self, name: impl Into<String>, value: impl Into<String>) -> Self {
        self.headers.insert(name.into(), value.into());
        self
    }

    /// Connects as a paired device: every connection pinned to its
    /// computer's certificate, at home when it answers, and otherwise
    /// directly or through its relay, from its address record. The device's
    /// own address and key take the place of [`Builder::url`],
    /// [`Builder::key`], and [`Builder::http_client`].
    pub fn device(mut self, device: Device) -> Self {
        self.device = Some(device);
        self
    }

    /// Connects.
    pub fn build(self) -> Result<Client> {
        self.build_with(|name| std::env::var(name).ok())
    }

    pub(crate) fn build_with(mut self, env: impl Fn(&str) -> Option<String>) -> Result<Client> {
        let timeout = self.timeout.unwrap_or(Duration::from_secs(60));
        let mut router = None;
        if let Some(device) = self.device.take() {
            let pinned = Arc::new(Pinning::new(Some(device.pin.clone()))).client(timeout)?;
            self.url = Some(format!("https://{}", device.address));
            self.key = Some(device.api_key.clone());
            self.http = Some(pinned.clone());
            let relay = self.relay_http.take().unwrap_or_default();
            router = Some(Arc::new(Router::new(device, pinned, relay)));
        }
        let env = |name: &str| if router.is_some() { None } else { env(name) };
        let not_empty = |s: Option<String>| s.filter(|s| !s.is_empty());
        let raw = not_empty(self.url)
            .or_else(|| not_empty(env("TOSKAR_URL")))
            .unwrap_or_else(|| DEFAULT_URL.into());
        let raw = raw.trim_end_matches('/').to_string();
        let url = Url::parse(&format!("{raw}/"))
            .ok()
            .filter(|u| matches!(u.scheme(), "http" | "https"))
            .ok_or_else(|| Error::new(0, "BAD_URL", format!("{raw} isn't an http or https address")))?;
        let mut headers = HeaderMap::new();
        // Core answers 426 CONTRACT_MISMATCH to a client of another major version.
        headers.insert("toskar-client-contract", HeaderValue::from_static(CONTRACT_VERSION));
        if let Some(key) = not_empty(self.key).or_else(|| not_empty(env("TOSKAR_API_KEY"))) {
            let value = HeaderValue::from_str(&format!("Bearer {key}"))
                .map_err(|_| Error::new(0, "BAD_KEY", "The API key isn't a header value"))?;
            headers.insert(AUTHORIZATION, value);
        }
        for (name, value) in self.headers {
            let bad = || Error::new(0, "BAD_HEADER", format!("{name} isn't a header"));
            headers.insert(
                HeaderName::from_bytes(name.as_bytes()).map_err(|_| bad())?,
                HeaderValue::from_str(&value).map_err(|_| bad())?,
            );
        }
        let http = match self.http {
            Some(http) => http,
            None => reqwest::Client::builder()
                .connect_timeout(timeout)
                .build()
                .map_err(|e| Error::new(0, "CONNECTION_FAILED", "Couldn't set up HTTP").with_source(e))?,
        };
        Ok(Client {
            url,
            headers,
            retries: self.retries.unwrap_or(2),
            timeout,
            http,
            router,
        })
    }
}

impl Client {
    /// Connects to Toskar Core: this computer's, unless `TOSKAR_URL` says another.
    pub fn new() -> Result<Self> {
        Builder::default().build()
    }

    /// How to connect, with every setting's default.
    pub fn builder() -> Builder {
        Builder::default()
    }

    /// Where Toskar Core answers.
    pub fn url(&self) -> &str {
        self.url.as_str().trim_end_matches('/')
    }

    /// How the client reaches its paired computer now: `None` before its
    /// first request, or for a client that isn't a paired device.
    pub fn path(&self) -> Option<ConnectionPath> {
        self.router.as_ref().and_then(|r| r.path())
    }

    /// Chooses the way in again, as after the network changed, and says which it found.
    pub async fn reconnect(&self) -> Result<Option<ConnectionPath>> {
        let Some(router) = &self.router else {
            return Ok(None);
        };
        router.forget();
        router.current().await?;
        Ok(router.path())
    }

    /// Every route, typed from Toskar Core's API spec.
    pub fn api(&self) -> Api<'_> {
        Api { client: self }
    }

    /// Asks once and waits for the whole answer.
    pub async fn chat(&self, request: &ChatRequest) -> Result<ChatAnswer> {
        let request = ChatRequest {
            stream: Some(false),
            ..request.clone()
        };
        self.api().chat(&request).await
    }

    /// Asks and yields the answer as it's written: tokens, then done. A
    /// failure is an [`Error`] with its code, such as
    /// [`error_codes::NO_MODEL_INSTALLED`], and ends the stream.
    pub async fn chat_stream(&self, request: &ChatRequest) -> Result<BoxStream<'static, Result<ChatEvent>>> {
        let request = ChatRequest {
            stream: Some(true),
            ..request.clone()
        };
        let body = crate::api::json(&request)?;
        let response = self
            .send_raw(
                "POST",
                "/api/v1/chat",
                &[],
                &[],
                &[],
                Some(body),
                "text/event-stream",
                true,
            )
            .await?;
        let events = Box::pin(sse::events(response));
        let answer = stream::unfold((events, false), |(mut events, finished)| async move {
            if finished {
                return None;
            }
            loop {
                let Some(event) = events.next().await else {
                    // Every stream ends with done or an error, so one that just stops was cut off.
                    let lost = Error::new(200, "CONNECTION_LOST", "The answer stopped before it finished");
                    return Some((Err(lost), (events, true)));
                };
                let event = match event {
                    Ok(e) => e,
                    Err(e) => return Some((Err(e), (events, true))),
                };
                match event.name.as_str() {
                    "token" => {
                        return match serde_json::from_str::<ChatToken>(&event.data) {
                            Ok(t) => Some((Ok(ChatEvent::Token(t.content)), (events, false))),
                            Err(e) => Some((Err(bad_answer(e)), (events, true))),
                        };
                    }
                    "done" => {
                        let done = serde_json::from_str::<ChatDone>(&event.data).ok();
                        return Some((Ok(ChatEvent::Done(done.and_then(|d| d.metrics))), (events, true)));
                    }
                    "error_code" => return Some((Err(Error::from_body(200, event.data.as_bytes())), (events, true))),
                    "error" => {
                        let message = if event.data.is_empty() {
                            "The chat failed".into()
                        } else {
                            event.data
                        };
                        return Some((Err(Error::new(200, error_codes::CHAT_FAILED, message)), (events, true)));
                    }
                    _ => continue,
                }
            }
        });
        Ok(answer.boxed())
    }

    /// Yields what happens on Toskar as it happens, such as models loading
    /// and automations running, until you drop it.
    pub async fn events(&self) -> Result<BoxStream<'static, Result<Event>>> {
        let response = self
            .send_raw("GET", "/api/v1/events", &[], &[], &[], None, "text/event-stream", true)
            .await?;
        let events = sse::events(response).filter_map(|event| async move {
            match event {
                Ok(e) if e.data.is_empty() => None,
                Ok(e) => Some(serde_json::from_str::<Event>(&e.data).map_err(bad_answer)),
                Err(e) => Some(Err(e)),
            }
        });
        Ok(events.boxed())
    }

    /// Core's version and its client contract.
    pub async fn version(&self) -> Result<VersionResponse> {
        self.api().get_version().await
    }

    // The generated Api calls these.

    pub(crate) async fn call<T: DeserializeOwned>(
        &self,
        method: &str,
        path: &str,
        params: &[&str],
        query: &[(&str, Option<String>)],
        headers: &[(&str, Option<String>)],
        body: Option<(Bytes, &'static str)>,
    ) -> Result<T> {
        let bytes = self
            .bytes_with(method, path, params, query, headers, body, "application/json")
            .await?;
        serde_json::from_slice(&bytes).map_err(bad_answer)
    }

    pub(crate) async fn bytes(
        &self,
        method: &str,
        path: &str,
        params: &[&str],
        query: &[(&str, Option<String>)],
        headers: &[(&str, Option<String>)],
        body: Option<(Bytes, &'static str)>,
    ) -> Result<Vec<u8>> {
        self.bytes_with(method, path, params, query, headers, body, "*/*")
            .await
            .map(|b| b.to_vec())
    }

    pub(crate) async fn send(
        &self,
        method: &str,
        path: &str,
        params: &[&str],
        query: &[(&str, Option<String>)],
        headers: &[(&str, Option<String>)],
        body: Option<(Bytes, &'static str)>,
    ) -> Result<()> {
        self.bytes_with(method, path, params, query, headers, body, "*/*")
            .await
            .map(|_| ())
    }

    #[allow(clippy::too_many_arguments)]
    async fn bytes_with(
        &self,
        method: &str,
        path: &str,
        params: &[&str],
        query: &[(&str, Option<String>)],
        headers: &[(&str, Option<String>)],
        body: Option<(Bytes, &'static str)>,
        accept: &str,
    ) -> Result<Bytes> {
        let response = self
            .send_raw(method, path, params, query, headers, body, accept, false)
            .await?;
        match tokio::time::timeout(self.timeout, response.bytes()).await {
            Ok(Ok(bytes)) => Ok(bytes),
            Ok(Err(e)) => {
                Err(Error::new(200, "CONNECTION_LOST", "The answer stopped before it finished").with_source(e))
            }
            Err(_) => Err(Error::new(200, "CONNECTION_LOST", "The answer didn't finish in time")),
        }
    }

    /// Sends a request, retrying a safe one, and answers an [`Error`] for an
    /// error answer.
    #[allow(clippy::too_many_arguments)]
    pub(crate) async fn send_raw(
        &self,
        method: &str,
        path: &str,
        params: &[&str],
        query: &[(&str, Option<String>)],
        headers: &[(&str, Option<String>)],
        body: Option<(Bytes, &'static str)>,
        accept: &str,
        stream: bool,
    ) -> Result<reqwest::Response> {
        let method =
            Method::from_bytes(method.as_bytes()).map_err(|_| Error::new(0, "BAD_REQUEST", "Not an HTTP method"))?;
        let safe = matches!(method, Method::GET | Method::HEAD | Method::OPTIONS);
        let attempts = if safe { 1 + self.retries } else { 1 };
        let mut attempt = 1;
        loop {
            // A paired device's way in, chosen again after one stops answering.
            let way = match &self.router {
                Some(router) => Some(router.current().await?),
                None => None,
            };
            let base = match &way {
                Some(way) => connect::base_of(way)?,
                None => self.url.clone(),
            };
            let target = target(base, path, params, query)?;
            let mut request = self.http.request(method.clone(), target).headers(self.headers.clone());
            for (name, value) in headers {
                if let Some(value) = value {
                    request = request.header(*name, value);
                }
            }
            request = request.header(ACCEPT, accept);
            if let Some((bytes, media)) = &body {
                // Bytes clone cheaply, so a retry sends the same body.
                request = request.header(CONTENT_TYPE, *media).body(bytes.clone());
            } else if matches!(method, Method::POST | Method::PUT | Method::PATCH) {
                request = request.body(Bytes::new());
            }
            // Waiting for the answer to start has the timeout; a stream then runs on.
            let sent = tokio::time::timeout(self.timeout, request.send()).await;
            let failed = match sent {
                Ok(Ok(response)) => {
                    let status = response.status().as_u16();
                    if status < 300 {
                        let _ = stream;
                        return Ok(response);
                    }
                    if attempt >= attempts || !matches!(status, 502..=504) {
                        let text = read_limited(response).await;
                        return Err(Error::from_body(status, &text));
                    }
                    None
                }
                Ok(Err(e)) if connect::is_pin_mismatch(&e) => return Err(connect::pin_mismatch().with_source(e)),
                Ok(Err(e)) => {
                    if let (Some(router), Some(way)) = (&self.router, &way) {
                        router.forget_way(way);
                    }
                    Some(connect::connection_error(e, self.url()))
                }
                Err(_) => Some(Error::new(
                    0,
                    "CONNECTION_FAILED",
                    format!(
                        "Couldn't reach Toskar at {}: no answer within {:?}",
                        self.url(),
                        self.timeout
                    ),
                )),
            };
            if let Some(e) = failed {
                if attempt >= attempts {
                    return Err(e);
                }
            }
            tokio::time::sleep(backoff(attempt)).await;
            attempt += 1;
        }
    }
}

fn target(mut url: Url, path: &str, params: &[&str], query: &[(&str, Option<String>)]) -> Result<Url> {
    {
        let mut segments = url
            .path_segments_mut()
            .map_err(|_| Error::new(0, "BAD_URL", "The address can't have a path"))?;
        segments.pop_if_empty();
        let mut next = params.iter();
        for segment in path.split('/').filter(|s| !s.is_empty()) {
            if segment.starts_with('{') {
                segments.push(next.next().copied().unwrap_or_default());
            } else {
                segments.push(segment);
            }
        }
    }
    let pairs: Vec<_> = query
        .iter()
        .filter_map(|(k, v)| v.as_ref().map(|v| (*k, v.as_str())))
        .collect();
    if !pairs.is_empty() {
        url.query_pairs_mut().extend_pairs(pairs);
    }
    Ok(url)
}

fn bad_answer(e: serde_json::Error) -> Error {
    Error::new(200, "BAD_ANSWER", format!("Toskar's answer didn't decode: {e}")).with_source(e)
}

fn backoff(attempt: u32) -> Duration {
    let jitter = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.subsec_millis() % 100)
        .unwrap_or(0);
    Duration::from_millis((200u64 << (attempt - 1)) + u64::from(jitter))
}

async fn read_limited(response: reqwest::Response) -> Vec<u8> {
    let mut out = Vec::new();
    let mut body = response.bytes_stream();
    while let Some(Ok(chunk)) = body.next().await {
        out.extend_from_slice(&chunk);
        if out.len() >= ERROR_LIMIT {
            out.truncate(ERROR_LIMIT);
            break;
        }
    }
    out
}
