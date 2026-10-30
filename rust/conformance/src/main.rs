//! Runs the shared conformance cases (conformance/README.md) with the Rust
//! SDK. It prints one line of JSON and exits 0, or prints
//! {"error": {"code", "message"}} and exits 1.

use std::error::Error as _;
use std::time::Duration;

use base64::Engine;
use futures_util::StreamExt;
use serde_json::{Value, json};
use toskar::models::{ChatRequest, UploadArtifactRequest};
use toskar::{ChatEvent, Client, Device, Error, Result};

const USAGE: &str = "usage: toskar-conformance pair <address> <code> | call <device.json> | chat|stream <model> <message> | events <model> <message> <until> | upload <file> | download <id>";

fn ask(model: &str, message: &str) -> ChatRequest {
    ChatRequest {
        message: message.into(),
        model_id: Some(model.into()),
        ..Default::default()
    }
}

async fn run(args: &[String]) -> Result<Value> {
    let args: Vec<&str> = args.iter().map(String::as_str).collect();
    match args.as_slice() {
        ["pair", address, code] => {
            let mut shown = String::new();
            let device = toskar::pair(address, code, "Rust conformance", |s| {
                shown = s.into();
                true
            })
            .await?;
            return Ok(json!({ "device": device, "short_pin": shown }));
        }
        ["call", file] => {
            let text = std::fs::read_to_string(file).map_err(other)?;
            let device: Device = serde_json::from_str(&text).map_err(other)?;
            let toskar = Client::builder().device(device).retries(0).build()?;
            let settings = toskar.api().get_settings().await?;
            return Ok(json!({
                "path": toskar.path().map(|p| p.as_str()).unwrap_or(""),
                "node_name": settings.get("node_name").and_then(Value::as_str).unwrap_or(""),
            }));
        }
        _ => {}
    }
    // The rest connect as TOSKAR_URL and TOSKAR_API_KEY say.
    let toskar = Client::builder().retries(0).build()?;
    match args.as_slice() {
        ["chat", model, message] => Ok(json!({ "content": toskar.chat(&ask(model, message)).await?.content })),
        ["stream", model, message] => {
            let (mut content, mut tokens, mut done) = (String::new(), 0, false);
            let mut events = toskar.chat_stream(&ask(model, message)).await?;
            while let Some(event) = events.next().await {
                match event? {
                    ChatEvent::Token(text) => {
                        tokens += 1;
                        content += &text;
                    }
                    ChatEvent::Done(_) => done = true,
                }
            }
            Ok(json!({ "content": content, "tokens": tokens, "done": done }))
        }
        ["events", model, message, until] => {
            // Listens to the events stream, asks once, and lists the events' types until one of type until.
            let mut events = toskar.events().await?;
            let until = until.to_string();
            let listening = tokio::spawn(async move {
                let mut types = Vec::new();
                while let Some(event) = events.next().await {
                    let event = event?;
                    let last = event.r#type == until;
                    types.push(event.r#type);
                    if last {
                        break;
                    }
                }
                Ok::<_, Error>(types)
            });
            // Time to subscribe before asking.
            tokio::time::sleep(Duration::from_secs(1)).await;
            toskar.chat(&ask(model, message)).await?;
            let types = tokio::time::timeout(Duration::from_secs(30), listening)
                .await
                .map_err(|_| Error::new(0, "ERROR", "No event of that type within 30 s"))?
                .map_err(other)??;
            Ok(json!({ "types": types }))
        }
        ["upload", file] => {
            let data = std::fs::read(file).map_err(other)?;
            let name = std::path::Path::new(file)
                .file_name()
                .map(|n| n.to_string_lossy().into_owned())
                .unwrap_or_default();
            let request = UploadArtifactRequest {
                name,
                content_base64: Some(base64::engine::general_purpose::STANDARD.encode(&data)),
                ..Default::default()
            };
            let up = toskar.api().upload_artifact(&request).await?;
            Ok(json!({ "id": up.id, "name": up.name, "size_bytes": up.size_bytes }))
        }
        ["download", id] => {
            let data = toskar.api().get_artifact_content(id, None).await?;
            let hash = aws_lc_rs::digest::digest(&aws_lc_rs::digest::SHA256, &data);
            let hex: String = hash.as_ref().iter().map(|b| format!("{b:02x}")).collect();
            Ok(json!({ "sha256": hex, "size_bytes": data.len() }))
        }
        _ => Err(Error::new(0, "ERROR", USAGE)),
    }
}

fn other(e: impl std::fmt::Display) -> Error {
    Error::new(0, "ERROR", e.to_string())
}

#[tokio::main]
async fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match run(&args).await {
        Ok(out) => println!("{out}"),
        Err(e) => {
            // With the root cause, such as a certificate the relay showed: a test bed's log then says why.
            let mut message = e.message.clone();
            let mut cause = e.source();
            while let Some(c) = cause {
                if c.source().is_none() && !message.contains(&c.to_string()) {
                    message = format!("{message}: {c}");
                }
                cause = c.source();
            }
            println!("{}", json!({ "error": { "code": e.code, "message": message } }));
            std::process::exit(1);
        }
    }
}
