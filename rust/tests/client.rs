use std::time::Duration;

use futures_util::StreamExt;
use toskar::models::ChatRequest;
use toskar::{ChatEvent, Client, error_codes};
use wiremock::matchers::{header, method, path};
use wiremock::{Mock, MockServer, ResponseTemplate};

const VERSION: &str = r#"{"version":"1.12.0","contract":{"version":"1.60","major":1},"commit":"abc","build_date":"2026-10-29","license":"AGPL-3.0","product":"Toskar","source":"https://github.com/yeixio/toskar-core"}"#;
const SSE: &str = "text/event-stream";

fn json(body: &str) -> ResponseTemplate {
    ResponseTemplate::new(200).set_body_raw(body.as_bytes().to_vec(), "application/json")
}

fn sse(body: &str) -> ResponseTemplate {
    ResponseTemplate::new(200).set_body_raw(body.as_bytes().to_vec(), SSE)
}

fn toskar(core: &MockServer) -> Client {
    Client::builder()
        .url(core.uri())
        .retries(2)
        .timeout(Duration::from_secs(5))
        .build()
        .unwrap()
}

fn hi() -> ChatRequest {
    ChatRequest {
        message: "Hi".into(),
        ..Default::default()
    }
}

#[tokio::test]
async fn says_its_contract_and_sends_the_key() {
    let core = MockServer::start().await;
    Mock::given(method("GET"))
        .and(path("/api/v1/version"))
        .and(header("toskar-client-contract", toskar::CONTRACT_VERSION))
        .and(header("authorization", "Bearer secret"))
        .respond_with(json(VERSION))
        .expect(1)
        .mount(&core)
        .await;
    let toskar = Client::builder().url(core.uri()).key("secret").build().unwrap();
    assert_eq!(toskar.version().await.unwrap().version, "1.12.0");
}

#[tokio::test]
async fn chats_waiting_for_the_whole_answer() {
    let core = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/api/v1/chat"))
        .respond_with(json(r#"{"content":"Hello there","metrics":null}"#))
        .mount(&core)
        .await;
    let answer = toskar(&core).chat(&hi()).await.unwrap();
    assert_eq!(answer.content, "Hello there");
    let sent = &core.received_requests().await.unwrap()[0];
    assert_eq!(sent.headers.get("accept").unwrap(), "application/json");
    // Unset fields stay out of the request, and stream says how it's answered.
    assert_eq!(
        String::from_utf8_lossy(&sent.body),
        r#"{"message":"Hi","stream":false}"#
    );
}

#[tokio::test]
async fn streams_an_answer_as_it_is_written() {
    let core = MockServer::start().await;
    let body = ": ping\n\nevent: token\ndata: {\"content\":\"Hel\"}\n\nevent: token\ndata: {\"content\":\"lo\"}\n\nevent: done\ndata: {\"metrics\":{\"prompt_tokens\":3,\"completion_tokens\":2,\"total_tokens\":5,\"ttft_ms\":1,\"prompt_ms\":1,\"eval_ms\":1,\"total_ms\":2,\"prompt_tok_per_sec\":3,\"eval_tok_per_sec\":2}}\n\n";
    Mock::given(method("POST"))
        .and(path("/api/v1/chat"))
        .respond_with(sse(body))
        .mount(&core)
        .await;
    let mut events = toskar(&core).chat_stream(&hi()).await.unwrap();
    let mut text = String::new();
    let mut metrics = None;
    while let Some(event) = events.next().await {
        match event.unwrap() {
            ChatEvent::Token(t) => text += &t,
            ChatEvent::Done(m) => metrics = m,
        }
    }
    assert_eq!(text, "Hello");
    assert_eq!(metrics.unwrap().completion_tokens, 2);
    assert_eq!(
        core.received_requests().await.unwrap()[0]
            .headers
            .get("accept")
            .unwrap(),
        SSE
    );
}

#[tokio::test]
async fn a_streamed_failure_has_its_code() {
    let core = MockServer::start().await;
    let body = "event: error_code\ndata: {\"code\":\"NO_MODEL_INSTALLED\",\"message\":\"Install a model\"}\n\n";
    Mock::given(method("POST")).respond_with(sse(body)).mount(&core).await;
    let mut events = toskar(&core).chat_stream(&hi()).await.unwrap();
    let e = events.next().await.unwrap().unwrap_err();
    assert_eq!(e.code, error_codes::NO_MODEL_INSTALLED);
    assert_eq!(e.message, "Install a model");
    assert!(events.next().await.is_none());
}

#[tokio::test]
async fn a_cut_off_stream_says_so() {
    let core = MockServer::start().await;
    Mock::given(method("POST"))
        .respond_with(sse("event: token\ndata: {\"content\":\"Hel\"}\n\n"))
        .mount(&core)
        .await;
    let events: Vec<_> = toskar(&core).chat_stream(&hi()).await.unwrap().collect().await;
    assert_eq!(events.last().unwrap().as_ref().unwrap_err().code, "CONNECTION_LOST");
}

#[tokio::test]
async fn an_error_answer_is_an_error() {
    let core = MockServer::start().await;
    Mock::given(path("/api/v1/models"))
        .respond_with(ResponseTemplate::new(404).set_body_raw(
            r#"{"error":{"code":"MODEL_NOT_FOUND","message":"No such model","details":{"model_id":"x"}}}"#,
            "application/json",
        ))
        .mount(&core)
        .await;
    Mock::given(path("/api/v1/version"))
        .respond_with(ResponseTemplate::new(500).set_body_string("oops"))
        .mount(&core)
        .await;
    let toskar = Client::builder().url(core.uri()).retries(0).build().unwrap();
    let e = toskar.api().list_models().await.unwrap_err();
    assert_eq!(e.status, 404);
    assert_eq!(e.code, error_codes::MODEL_NOT_FOUND);
    assert_eq!(e.message, "No such model");
    assert_eq!(e.details.unwrap()["model_id"], "x");
    // A body that isn't Toskar's still says what happened.
    assert_eq!(toskar.version().await.unwrap_err().code, "HTTP_500");
}

#[tokio::test]
async fn retries_a_safe_request_but_never_a_chat() {
    let core = MockServer::start().await;
    Mock::given(path("/api/v1/version"))
        .respond_with(ResponseTemplate::new(503))
        .up_to_n_times(2)
        .mount(&core)
        .await;
    Mock::given(path("/api/v1/version"))
        .respond_with(json(VERSION))
        .mount(&core)
        .await;
    toskar(&core).version().await.unwrap();
    assert_eq!(core.received_requests().await.unwrap().len(), 3);

    let busy = MockServer::start().await;
    Mock::given(path("/api/v1/version"))
        .respond_with(ResponseTemplate::new(503))
        .mount(&busy)
        .await;
    assert_eq!(toskar(&busy).version().await.unwrap_err().status, 503);
    assert_eq!(busy.received_requests().await.unwrap().len(), 3);

    let chat = MockServer::start().await;
    Mock::given(path("/api/v1/chat"))
        .respond_with(ResponseTemplate::new(503))
        .mount(&chat)
        .await;
    assert_eq!(toskar(&chat).chat(&hi()).await.unwrap_err().status, 503);
    assert_eq!(chat.received_requests().await.unwrap().len(), 1);
}

#[tokio::test]
async fn a_computer_that_isnt_there_says_so() {
    // A port nothing listens on: wiremock keeps its servers for reuse.
    let gone = std::net::TcpListener::bind("127.0.0.1:0")
        .unwrap()
        .local_addr()
        .unwrap();
    let e = Client::builder()
        .url(format!("http://{gone}"))
        .retries(0)
        .build()
        .unwrap()
        .version()
        .await
        .unwrap_err();
    assert_eq!(e.code, "CONNECTION_FAILED");
    assert_eq!(e.status, 0);
    assert!(std::error::Error::source(&e).is_some());
}

#[tokio::test]
async fn reads_the_events_stream() {
    let core = MockServer::start().await;
    let body = "data: {\"id\":\"e1\",\"type\":\"model.loaded\",\"contract\":\"1.60\",\"timestamp\":\"2026-10-29T16:04:05.123456789Z\",\"payload\":{\"model_id\":\"m1\"}}\n\ndata: {\"id\":\"e2\",\"type\":\"model.unloaded\",\"contract\":\"1.60\",\"timestamp\":\"2026-10-29T16:04:06Z\",\"payload\":{}}\n\n";
    Mock::given(path("/api/v1/events"))
        .respond_with(sse(body))
        .mount(&core)
        .await;
    let seen: Vec<_> = toskar(&core)
        .events()
        .await
        .unwrap()
        .map(Result::unwrap)
        .collect()
        .await;
    assert_eq!(
        seen.iter().map(|e| e.r#type.as_str()).collect::<Vec<_>>(),
        ["model.loaded", "model.unloaded"]
    );
    assert_eq!(seen[0].timestamp.unix_timestamp_nanos(), 1_793_289_845_123_456_789);
}

#[tokio::test]
async fn puts_parameters_in_the_path_and_query() {
    let core = MockServer::start().await;
    Mock::given(method("DELETE"))
        .respond_with(json("{}"))
        .mount(&core)
        .await;
    Mock::given(method("GET")).respond_with(json("[]")).mount(&core).await;
    let toskar = toskar(&core);
    toskar.api().delete_memory("a/b c").await.unwrap();
    toskar.api().list_people(Some("admin"), None).await.unwrap();
    let sent = core.received_requests().await.unwrap();
    assert_eq!(sent[0].url.path(), "/api/v1/memory/a%2Fb%20c");
    assert_eq!(sent[1].url.query(), Some("role=admin"));
}

#[tokio::test]
async fn keeps_out_what_a_newer_core_adds() {
    let core = MockServer::start().await;
    Mock::given(method("POST"))
        .respond_with(json(r#"{"content":"Hi","metrics":null,"new_field":{"a":1}}"#))
        .mount(&core)
        .await;
    let a = toskar(&core).chat(&hi()).await.unwrap();
    assert_eq!(a.content, "Hi");
    assert!(a.metrics.is_none());
}

#[test]
fn reads_the_address_from_the_environment_or_this_computer() {
    assert_eq!(
        Client::builder().url("http://studio.test:7331/").build().unwrap().url(),
        "http://studio.test:7331"
    );
    assert_eq!(Client::builder().url("ftp://x").build().unwrap_err().code, "BAD_URL");
}
