# Toskar for Rust

The official Rust SDK for [Toskar](https://toskar.ai). It's async, on Tokio and reqwest, and needs Rust 1.85 or later.

<!-- snippet: skip -->
```toml
# Cargo.toml
[dependencies]
toskar = "0.3"
tokio = { version = "1", features = ["macros", "rt-multi-thread"] }
futures-util = "0.3"
```

Every item and route: [the reference](https://github.com/yeixio/toskar-sdks/blob/main/reference/rust/README.md).

It isn't on crates.io yet. Until it is, use it from this repository: `toskar = { git = "https://github.com/yeixio/toskar-sdks" }`.

## Quick start

<!-- snippet: run -->
```rust
use futures_util::StreamExt;
use toskar::{ChatEvent, Client, models::ChatRequest};

// This computer's Toskar Core, at http://127.0.0.1:7331, needs no key.
// Elsewhere: Client::builder().url("http://studio.local:7331").key("tk_…").build()?,
// or set TOSKAR_URL and TOSKAR_API_KEY.
let toskar = Client::new()?;

// Stream an answer as it's written.
let request = ChatRequest { message: "Plan a three-day trip to Juneau".into(), ..Default::default() };
let mut events = toskar.chat_stream(&request).await?;
while let Some(event) = events.next().await {
    if let ChatEvent::Token(text) = event? {
        print!("{text}");
    }
}

// Or wait for the whole answer.
let request = ChatRequest { message: "Summarize this in one line: …".into(), ..Default::default() };
println!("{}", toskar.chat(&request).await?.content);
```

## Every route, typed

`toskar.api()` is generated from Toskar Core's API spec, so every operation is an async method named after it, and every answer is a struct in `toskar::models`:

```rust
use toskar::models::CreateConversationRequest;

let models = toskar.api().list_models().await?; // Vec<Model>
let request = CreateConversationRequest { title: Some("Trip".into()), ..Default::default() };
let chat = toskar.api().create_conversation(Some(&request)).await?;
let messages = toskar.api().list_conversation_messages(&chat.id).await?;
```

A field Core may leave out is an `Option`, every struct is `Default`, and a newer Core's new fields and values are passed over, not failed on. Values that only a few are known for, such as `effort`, are strings, so a new one doesn't break your build. Optional query parameters are `Option` arguments: `list_people(Some("admin"), None)`.

## Errors

Toskar answers errors with a stable code. Any call that gets one answers a `toskar::Error`, with the code, a message for logs, and the details:

```rust
use toskar::error_codes;

let request = ChatRequest { message: "Hi".into(), ..Default::default() };
match toskar.chat(&request).await {
    Err(e) if e.code == error_codes::NO_MODEL_INSTALLED => {
        toskar.api().install_model("qwen2.5-7b-q4", None, None, None).await?;
    }
    other => println!("{}", other?.content),
}
```

A streamed answer that fails yields its error, with the code Toskar sent. One that stops before it finishes yields `CONNECTION_LOST`, and a computer that doesn't answer is `CONNECTION_FAILED`, with the network error as its `source()`.

## Events

```rust
let mut events = toskar.events().await?; // until you drop it
while let Some(event) = events.next().await {
    println!("{}", event?.r#type); // such as model.download.progress or automation.completed
}
```

## Retries and timeouts

Safe requests (GET, HEAD, OPTIONS) that fail to connect, or that Toskar answers with 502, 503, or 504, are retried twice with backoff. A chat is never retried, since it could answer twice. Each request waits 60 seconds for its answer to start, and a streamed answer then runs for as long as it takes. Change these on the builder, or bring your own `reqwest::Client`:

```rust
use std::time::Duration;

let patient = Client::builder().retries(5).timeout(Duration::from_secs(300)).build()?;
```

## Pairing, as the Toskar apps do

An app can pair as a device, with the code **Connect a device** shows on the computer, instead of using an API key. It then reaches its computer at home and, when the computer has access from anywhere, directly or through its relay, always pinned to the computer's own certificate ([how it works](https://github.com/yeixio/toskar-core/blob/main/docs/connecting.md)).

```rust
use toskar::Device;

// On the computer's network, with the code it shows:
let device = toskar::pair("192.168.1.20:7331", "123456", "Kitchen tablet", |short_pin| {
    // Show the short pin, such as 9B80-D9D9, and ask whether the computer shows the same.
    ask_the_person(short_pin)
})
.await?;
// Save device as a password is saved: its key and route are secrets. It's
// serde, in the same JSON as the other SDKs':
let saved = serde_json::to_string(&device)?;

let device: Device = serde_json::from_str(&saved)?;
let paired = Client::builder().device(device).build()?;
let models = paired.api().list_models().await?;
println!("{:?}", paired.path()); // Some(Home), Some(Direct), or Some(Relay)
```

Every connection checks the computer's certificate before anything is sent. A different certificate is `PIN_MISMATCH`, and is never accepted on its own: pair again to trust a new one. Away from home, the client opens the computer's sealed address record from its relay, tries its direct ways in at once and the relay a second later, and keeps the first that answers. `paired.reconnect().await?` chooses again, as after the network changes. A device key reaches the routes a device needs. Scripts and servers that need the rest use a key from API Access.

## Find computers on the network

Computers running Toskar announce themselves on the home network (mDNS, `_localai._tcp`). `toskar::find` lists them, so a person can pick one instead of typing an address:

```rust
for computer in toskar::find(std::time::Duration::from_secs(3)).await? {
    println!("{} {}", computer.name, computer.address);
}
```

Pair with `computer.address`. When `computer.on_network` is false, the computer answers only on itself: tell the person to turn on Connect a device there, rather than that it's unreachable. A computer can have addresses this device can't reach, such as a container network's. `address` is the first one that answers, and `addresses` has them all.
