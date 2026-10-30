//! Connecting as a paired device, as the Toskar apps do (Toskar Core's
//! docs/connecting.md): pairing with the code Connect a device shows, the
//! computer's certificate pinned on every connection, and reaching it at
//! home or, with access from anywhere, directly or through its relay.

use std::sync::{Arc, Mutex};
use std::time::Duration;

use futures_util::StreamExt;
use futures_util::stream::FuturesUnordered;
use reqwest::Url;
use reqwest::header::AUTHORIZATION;
use rustls::client::danger::{HandshakeSignatureValid, ServerCertVerified, ServerCertVerifier};
use rustls::crypto::{CryptoProvider, WebPkiSupportedAlgorithms};
use rustls::pki_types::{CertificateDer, ServerName, UnixTime};
use rustls::{DigitallySignedStruct, SignatureScheme};
use serde::{Deserialize, Serialize};
use time::OffsetDateTime;

use crate::generated::codes::CONTRACT_VERSION;
use crate::models::PairedDevice;
use crate::records::{self, AddressRecord};
use crate::{Error, Result};

/// What a paired device keeps, to connect again. Save it as a password is
/// saved: `api_key` and the route's secret and token are secrets. It's
/// serde, in the same JSON as the other SDKs'.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Device {
    /// The computer's host:port at home.
    pub address: String,
    /// The device's own key.
    pub api_key: String,
    /// "sha256:<hex>" of the computer's certificate. It only ever comes from pairing.
    pub pin: String,
    /// How to find the computer away from home, when it has access from anywhere.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub route: Option<Route>,
}

/// How to find a computer away from home.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Route {
    /// The route secret, base64url without padding.
    pub secret: String,
    /// The route's ID.
    pub id: String,
    /// The relay the computer uses, such as relay.toskar.ai.
    pub relay: String,
    /// Lets the device look the computer up on Toskar's relay.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub token: Option<String>,
}

/// How the client reaches its computer.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum ConnectionPath {
    /// At its address at home.
    Home,
    /// Directly, at an address from its address record.
    Direct,
    /// Through its relay.
    Relay,
}

impl ConnectionPath {
    /// "home", "direct", or "relay", as the other SDKs say it.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Home => "home",
            Self::Direct => "direct",
            Self::Relay => "relay",
        }
    }
}

/// Pairs with the computer at address (host:port, as found or typed) using
/// the code Connect a device shows on it. The device must be on the
/// computer's local network.
///
/// `confirm` shows the person the short pin, such as 9B80-D9D9, and says
/// whether the computer shows the same. A script with no one to ask passes
/// `|_| true`.
pub async fn pair(address: &str, code: &str, device_name: &str, confirm: impl FnOnce(&str) -> bool) -> Result<Device> {
    let base = base_of(address)?;
    let timeout = Duration::from_secs(30);
    // The certificate the computer shows, for the person to check.
    let seeing = Arc::new(Pinning::new(None));
    let http = seeing.clone().client(timeout)?;
    let health = base.join("api/v1/health").expect("a path joins");
    match tokio::time::timeout(timeout, http.get(health).send()).await {
        Ok(Ok(_)) => {}
        Ok(Err(e)) => {
            return Err(Error::new(
                0,
                "CONNECTION_FAILED",
                format!("Couldn't reach the computer at {address}: {e}"),
            )
            .with_source(e));
        }
        Err(_) => {
            return Err(Error::new(
                0,
                "CONNECTION_FAILED",
                format!("Couldn't reach the computer at {address}: no answer within {timeout:?}"),
            ));
        }
    }
    let seen = seeing
        .seen()
        .ok_or_else(|| Error::new(0, "PIN_MISMATCH", "The computer showed no certificate"))?;
    if !confirm(&records::short_pin(&seen)) {
        return Err(Error::new(0, "NOT_CONFIRMED", "The short pin wasn't confirmed"));
    }

    // Then the code, to that certificate alone.
    let http = Arc::new(Pinning::new(Some(seen.clone()))).client(timeout)?;
    let body = serde_json::json!({ "code": code, "device_name": device_name });
    let sent = tokio::time::timeout(
        timeout,
        http.post(base.join("api/v1/devices/pair").expect("a path joins"))
            .header("toskar-client-contract", CONTRACT_VERSION)
            .json(&body)
            .send(),
    )
    .await
    .map_err(|_| {
        Error::new(
            0,
            "CONNECTION_FAILED",
            format!("Couldn't reach the computer at {address}"),
        )
    })?;
    let response = sent.map_err(|e| connection_error(e, address))?;
    let status = response.status().as_u16();
    let text = response
        .bytes()
        .await
        .map_err(|e| Error::new(200, "CONNECTION_LOST", "The answer stopped before it finished").with_source(e))?;
    if status >= 300 {
        return Err(Error::from_body(status, &text));
    }
    let paired: PairedDevice = serde_json::from_slice(&text)
        .map_err(|e| Error::new(200, "BAD_ANSWER", format!("Toskar's answer didn't decode: {e}")).with_source(e))?;
    if !paired.tls_fingerprint.eq_ignore_ascii_case(&seen) {
        return Err(pin_mismatch());
    }
    let route = paired.route_secret.filter(|s| !s.is_empty()).map(|secret| Route {
        secret,
        id: paired.route_id.unwrap_or_default(),
        relay: paired.relay.unwrap_or_default(),
        token: paired.token,
    });
    Ok(Device {
        address: address.into(),
        api_key: paired.api_key,
        pin: seen,
        route,
    })
}

/// Marks a refused certificate in the TLS error, so it can be told from a
/// computer that isn't there.
const PIN_REFUSED: &str = "toskar: the computer's certificate isn't the one paired with";

pub(crate) fn pin_mismatch() -> Error {
    Error::new(
        0,
        "PIN_MISMATCH",
        "The computer's certificate isn't the one paired with",
    )
}

/// Whether a request failed because the pinned certificate was refused.
pub(crate) fn is_pin_mismatch(e: &(dyn std::error::Error + 'static)) -> bool {
    let mut next = Some(e);
    while let Some(e) = next {
        if e.to_string().contains(PIN_REFUSED) {
            return true;
        }
        next = e.source();
    }
    false
}

/// A request's failure: `PIN_MISMATCH` for a refused certificate, `CONNECTION_FAILED` otherwise.
pub(crate) fn connection_error(e: reqwest::Error, at: &str) -> Error {
    if is_pin_mismatch(&e) {
        pin_mismatch().with_source(e)
    } else {
        Error::new(0, "CONNECTION_FAILED", format!("Couldn't reach Toskar at {at}: {e}")).with_source(e)
    }
}

/// Trusts exactly the certificate with pin, checked before any request is
/// sent; names, dates, and signers aren't checked. With no pin, it trusts
/// any certificate and keeps its pin, for pairing.
#[derive(Debug)]
pub(crate) struct Pinning {
    pin: Option<String>,
    seen: Mutex<Option<String>>,
    algorithms: WebPkiSupportedAlgorithms,
}

impl Pinning {
    pub(crate) fn new(pin: Option<String>) -> Self {
        Self {
            pin,
            seen: Mutex::new(None),
            algorithms: provider().signature_verification_algorithms,
        }
    }

    fn seen(&self) -> Option<String> {
        self.seen.lock().ok().and_then(|s| s.clone())
    }

    /// A client whose connections are pinned.
    pub(crate) fn client(self: Arc<Self>, timeout: Duration) -> Result<reqwest::Client> {
        let tls = rustls::ClientConfig::builder_with_provider(Arc::new(provider()))
            .with_safe_default_protocol_versions()
            .map_err(|e| Error::new(0, "CONNECTION_FAILED", "Couldn't set up TLS").with_source(e))?
            .dangerous()
            .with_custom_certificate_verifier(self)
            .with_no_client_auth();
        reqwest::Client::builder()
            .tls_backend_preconfigured(tls)
            .connect_timeout(timeout)
            // The way in changes, and a computer's restart drops its connections.
            .pool_idle_timeout(Duration::from_secs(60))
            .build()
            .map_err(|e| Error::new(0, "CONNECTION_FAILED", "Couldn't set up HTTP").with_source(e))
    }
}

fn provider() -> CryptoProvider {
    rustls::crypto::aws_lc_rs::default_provider()
}

impl ServerCertVerifier for Pinning {
    fn verify_server_cert(
        &self,
        end_entity: &CertificateDer<'_>,
        _intermediates: &[CertificateDer<'_>],
        _server_name: &ServerName<'_>,
        _ocsp_response: &[u8],
        _now: UnixTime,
    ) -> std::result::Result<ServerCertVerified, rustls::Error> {
        let got = records::pin_of(end_entity.as_ref());
        match &self.pin {
            None => {
                if let Ok(mut seen) = self.seen.lock() {
                    *seen = Some(got);
                }
                Ok(ServerCertVerified::assertion())
            }
            Some(pin) if pin.eq_ignore_ascii_case(&got) => Ok(ServerCertVerified::assertion()),
            Some(_) => Err(rustls::Error::General(PIN_REFUSED.into())),
        }
    }

    // The handshake still proves the computer has the certificate's key.

    fn verify_tls12_signature(
        &self,
        message: &[u8],
        cert: &CertificateDer<'_>,
        dss: &DigitallySignedStruct,
    ) -> std::result::Result<HandshakeSignatureValid, rustls::Error> {
        rustls::crypto::verify_tls12_signature(message, cert, dss, &self.algorithms)
    }

    fn verify_tls13_signature(
        &self,
        message: &[u8],
        cert: &CertificateDer<'_>,
        dss: &DigitallySignedStruct,
    ) -> std::result::Result<HandshakeSignatureValid, rustls::Error> {
        rustls::crypto::verify_tls13_signature(message, cert, dss, &self.algorithms)
    }

    fn supported_verify_schemes(&self) -> Vec<SignatureScheme> {
        self.algorithms.supported_schemes()
    }
}

const HOME_TIMEOUT: Duration = Duration::from_millis(2500);
const TRY_TIMEOUT: Duration = Duration::from_secs(6);
const RELAY_DELAY: Duration = Duration::from_secs(1);
const RECORD_MAX_AGE: Duration = Duration::from_secs(60 * 60);
const RECORD_LIMIT: usize = 1 << 20;

/// Toskar's own relay. It's asked only with a route token.
const TOSKAR_RELAY: &str = "relay.toskar.ai";

/// Chooses the way in, and again when it stops answering: home first, then
/// the address record's ways, the direct ones at once and the relay's a
/// second later.
#[derive(Debug)]
pub(crate) struct Router {
    device: Device,
    pinned: reqwest::Client,
    relay: reqwest::Client,
    way: Mutex<Option<(ConnectionPath, String)>>,
    choosing: tokio::sync::Mutex<()>,
}

impl Router {
    pub(crate) fn new(device: Device, pinned: reqwest::Client, relay: reqwest::Client) -> Self {
        Self {
            device,
            pinned,
            relay,
            way: Mutex::new(None),
            choosing: tokio::sync::Mutex::new(()),
        }
    }

    fn known(&self) -> Option<(ConnectionPath, String)> {
        self.way.lock().ok().and_then(|w| w.clone())
    }

    pub(crate) fn path(&self) -> Option<ConnectionPath> {
        self.known().map(|(path, _)| path)
    }

    pub(crate) fn forget(&self) {
        if let Ok(mut way) = self.way.lock() {
            *way = None;
        }
    }

    pub(crate) fn forget_way(&self, used: &str) {
        if let Ok(mut way) = self.way.lock() {
            if way.as_ref().is_some_and(|(_, w)| w == used) {
                *way = None;
            }
        }
    }

    /// The way in to use, host:port, choosing one when there's none.
    pub(crate) async fn current(&self) -> Result<String> {
        if let Some((_, way)) = self.known() {
            return Ok(way);
        }
        let _choosing = self.choosing.lock().await;
        if let Some((_, way)) = self.known() {
            return Ok(way);
        }
        let (path, way) = self.choose().await?;
        if let Ok(mut known) = self.way.lock() {
            *known = Some((path, way.clone()));
        }
        Ok(way)
    }

    /// Whether the computer answers health at address, pinned, within
    /// timeout. Another certificate is `PIN_MISMATCH`.
    async fn answers(&self, address: &str, timeout: Duration) -> Result<bool> {
        let Ok(url) = base_of(address).map(|b| b.join("api/v1/health").expect("a path joins")) else {
            return Ok(false);
        };
        // With the key: a computer that asks for one answers health only
        // with it. The connection is pinned before anything is sent.
        let request = self
            .pinned
            .get(url)
            .header(AUTHORIZATION, format!("Bearer {}", self.device.api_key));
        let response = match tokio::time::timeout(timeout, request.send()).await {
            Ok(Ok(response)) => response,
            Ok(Err(e)) if is_pin_mismatch(&e) => return Err(pin_mismatch().with_source(e)),
            _ => return Ok(false),
        };
        if response.status().as_u16() != 200 {
            return Ok(false);
        }
        #[derive(Deserialize)]
        struct Health {
            #[serde(default)]
            status: String,
        }
        let body = tokio::time::timeout(timeout, response.bytes()).await;
        Ok(matches!(body, Ok(Ok(b)) if serde_json::from_slice::<Health>(&b).is_ok_and(|h| h.status == "ok")))
    }

    async fn choose(&self) -> Result<(ConnectionPath, String)> {
        // Home answering with another certificate means the computer's
        // changed, or it isn't the computer: say so; pairing again is the
        // way on.
        if self.answers(&self.device.address, HOME_TIMEOUT).await? {
            return Ok((ConnectionPath::Home, self.device.address.clone()));
        }
        let route = self
            .device
            .route
            .as_ref()
            .filter(|r| !r.secret.is_empty())
            .ok_or_else(unreachable)?;
        let relay = host_only(&route.relay).to_lowercase();
        // Toskar's relay answers only for a subscription; without one, it
        // isn't asked, so nothing about this device reaches it.
        if relay == TOSKAR_RELAY && route.token.as_deref().unwrap_or("").is_empty() {
            return Err(unreachable());
        }
        let record = self.record(route).await?;
        let mut tries: FuturesUnordered<_> = record
            .addresses
            .iter()
            .map(|address| {
                let relay = relay.clone();
                async move {
                    let is_relay = host_only(address).to_lowercase().ends_with(&format!(".{relay}"));
                    if is_relay {
                        tokio::time::sleep(RELAY_DELAY).await;
                    }
                    // Another certificate at a way in is someone else's
                    // device there: that way just doesn't count.
                    let ok = self.answers(address, TRY_TIMEOUT).await.unwrap_or(false);
                    let path = if is_relay {
                        ConnectionPath::Relay
                    } else {
                        ConnectionPath::Direct
                    };
                    ok.then(|| (path, address.clone()))
                }
            })
            .collect();
        while let Some(tried) = tries.next().await {
            if let Some(found) = tried {
                return Ok(found);
            }
        }
        Err(unreachable())
    }

    async fn record(&self, route: &Route) -> Result<AddressRecord> {
        let url = base_of(&route.relay)
            .ok()
            .and_then(|b| b.join(&format!("v1/routes/{}/record", route.id)).ok())
            .ok_or_else(|| no_record(None))?;
        let mut request = self.relay.get(url);
        if let Some(token) = route.token.as_deref().filter(|t| !t.is_empty()) {
            request = request.header(AUTHORIZATION, format!("Bearer {token}"));
        }
        let fetch = async {
            let mut response = request.send().await.map_err(|e| no_record(Some(e)))?;
            if response.status().as_u16() != 200 || response.content_length().unwrap_or(0) > RECORD_LIMIT as u64 {
                return Err(no_record(None));
            }
            let mut data = Vec::new();
            while let Some(chunk) = response.chunk().await.map_err(|e| no_record(Some(e)))? {
                data.extend_from_slice(&chunk);
                if data.len() > RECORD_LIMIT {
                    return Err(no_record(None));
                }
            }
            Ok(data)
        };
        let data = tokio::time::timeout(TRY_TIMEOUT, fetch)
            .await
            .map_err(|_| no_record(None))??;
        records::open(
            &data,
            &route.secret,
            &self.device.pin,
            OffsetDateTime::now_utc(),
            RECORD_MAX_AGE,
        )
    }
}

fn unreachable() -> Error {
    Error::new(0, "UNREACHABLE", "The computer can't be reached")
}

/// The source, when there is one, says why the relay couldn't be asked, such as its certificate.
fn no_record(source: Option<reqwest::Error>) -> Error {
    let e = Error::new(
        0,
        "NO_RECORD",
        "No address record for the computer: it may be off or asleep, or have no access from anywhere",
    );
    match source {
        Some(source) => e.with_source(source),
        None => e,
    }
}

/// The way in's address, host:port, as a base URL.
pub(crate) fn base_of(way: &str) -> Result<Url> {
    Url::parse(&format!("https://{way}/"))
        .ok()
        .filter(|u| u.path() == "/" && u.query().is_none() && u.host().is_some())
        .ok_or_else(|| Error::new(0, "BAD_ADDRESS", format!("{way} isn't host:port")))
}

/// The host of host:port, [v6]:port, or a bare host or IPv6 address.
pub(crate) fn host_only(address: &str) -> &str {
    if let Some(rest) = address.strip_prefix('[') {
        if let Some(end) = rest.find(']') {
            return &rest[..end];
        }
    }
    if address.matches(':').count() == 1 {
        return &address[..address.rfind(':').unwrap_or(address.len())];
    }
    address
}
