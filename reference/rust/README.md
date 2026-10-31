# Rust reference

*Generated from the crate's doc comments by `rust/scripts/reference.py`.*

The official Rust SDK for Toskar: local AI across your own computers. Every item is at the crate's root, but for `records` and `models`.

```rust
let toskar = toskar::Client::new()?;
let request = ChatRequest { message: "Plan a three-day trip to Juneau".into(), ..Default::default() };
let mut events = toskar.chat_stream(&request).await?;
while let Some(event) = events.next().await {
    if let ChatEvent::Token(text) = event? {
        print!("{text}");
    }
}
```

`toskar.api()` has [every route](api.md), generated from Toskar Core's API spec, and its models are in `toskar::models`. The routes themselves, with every field: [toskar.ai/developers/api](https://toskar.ai/developers/api).

## Contents

- **Connecting:** [Client](#client), [Builder](#builder), [ChatEvent](#chatevent), [Api](#api), [DEFAULT_URL](#default_url)
- **Errors:** [Error](#error), [Result](#result), [error_codes](#error_codes)
- **Pairing and reaching a computer from anywhere:** [pair](#pairaddress-code-device_name-confirm), [Builder::device](#builderdevicedevice), [Client::path](#clientpath), [Client::reconnect](#clientreconnect), [Device](#device), [Route](#route), [ConnectionPath](#connectionpath), [records](#records), [records::AddressRecord](#recordsaddressrecord), [records::route_id](#recordsroute_idsecret), [records::pin_of](#recordspin_ofder), [records::short_pin](#recordsshort_pinpin), [records::open](#recordsopenblob-secret-pin-now-max_age)
- **Finding computers on the network:** [find](#findtimeout), [SERVICE_TYPE](#service_type), [DiscoveredComputer](#discoveredcomputer)
- **The contract:** [CONTRACT_VERSION](#contract_version)
- [Every route on `toskar.api()`](api.md)
- [Error codes](errors.md)

## Connecting

### Client

A connection to Toskar Core. It's cheap to clone: clones share their
connections.

```rust
#[derive(Clone, Debug)]
pub struct Client
```

#### Client::new()

Connects to Toskar Core: this computer's, unless `TOSKAR_URL` says another.

```rust
pub fn new() -> Result<Self>
```

#### Client::builder()

How to connect, with every setting's default.

```rust
pub fn builder() -> Builder
```

#### Client::url()

Where Toskar Core answers.

```rust
pub fn url(&self) -> &str
```

#### Client::api()

Every route, typed from Toskar Core's API spec.

```rust
pub fn api(&self) -> Api<'_>
```

#### Client::chat(request)

Asks once and waits for the whole answer.

```rust
pub async fn chat(&self, request: &ChatRequest) -> Result<ChatAnswer>
```

#### Client::chat_stream(request)

Asks and yields the answer as it's written: tokens, then done. A
failure is an `Error` with its code, such as
`error_codes::NO_MODEL_INSTALLED`, and ends the stream.

```rust
pub async fn chat_stream(&self, request: &ChatRequest) -> Result<BoxStream<'static, Result<ChatEvent>>>
```

#### Client::events()

Yields what happens on Toskar as it happens, such as models loading
and automations running, until you drop it.

```rust
pub async fn events(&self) -> Result<BoxStream<'static, Result<Event>>>
```

#### Client::version()

Core's version and its client contract.

```rust
pub async fn version(&self) -> Result<VersionResponse>
```

### Builder

How to connect: every setting has a default. Start with `Client::builder`.

```rust
#[derive(Clone, Debug, Default)]
pub struct Builder
```

#### Builder::url(url)

Where Toskar Core answers. Default: `TOSKAR_URL`, or `DEFAULT_URL`, this computer.

```rust
pub fn url(self, url: impl Into<String>) -> Self
```

#### Builder::key(key)

The API key for any address other than this computer's loopback. Default: `TOSKAR_API_KEY`.

```rust
pub fn key(self, key: impl Into<String>) -> Self
```

#### Builder::retries(retries)

How many times a safe request (GET, HEAD, OPTIONS) that fails to
connect or answers 502, 503, or 504 is retried. Default: 2. A chat is
never retried: it could answer twice.

```rust
pub fn retries(self, retries: u32) -> Self
```

#### Builder::timeout(timeout)

How long to wait for an answer to start. Default: 60 seconds. A
streamed answer then runs for as long as it takes.

```rust
pub fn timeout(self, timeout: Duration) -> Self
```

#### Builder::http_client(http)

The reqwest client to send requests with, in place of one the SDK makes.

```rust
pub fn http_client(self, http: reqwest::Client) -> Self
```

#### Builder::header(name, value)

A header to add to every request.

```rust
pub fn header(self, name: impl Into<String>, value: impl Into<String>) -> Self
```

#### Builder::build()

Connects.

```rust
pub fn build(self) -> Result<Client>
```

### ChatEvent

One event of a streamed chat.

```rust
#[derive(Clone, Debug, PartialEq)]
pub enum ChatEvent
```

#### ChatEvent::Token

The next piece of the answer.

```rust
Token(String)
```

#### ChatEvent::Done

The answer is finished and saved, with what the runtime measured when it reported it.

```rust
Done(Option<GenerationMetrics>)
```

### Api

Every route of Toskar Core's API, typed: `toskar.api().list_models()`
and so on, one async method for each operation, named after it. An
error answer is an `Error` with Toskar's code.

```rust
pub struct Api<'a>
```

Its methods: [every route on `toskar.api()`](api.md).

### DEFAULT_URL

This computer's Toskar Core, which needs no key.

```rust
pub const DEFAULT_URL: &str = "http://127.0.0.1:7331"
```

## Errors

### Error

An error from Toskar Core: `{"error": {"code", "message", "details"}}`.

`code` is stable, such as `error_codes::NO_MODEL_INSTALLED`;
`message` is English text for logs; `details` has the values the message
needs.

The SDK's own codes, for what goes wrong before Toskar Core answers, are
`CONNECTION_FAILED` (with the cause as its source), `CONNECTION_LOST` (a
stream cut off), `BAD_URL`, and `HTTP_<status>` for an answer that isn't
Toskar's.

```rust
#[derive(Debug)]
pub struct Error
```

#### Error::status

The HTTP status Toskar answered with, or 0 when it didn't answer.

```rust
pub status: u16
```

#### Error::code

The error's code, such as `NO_MODEL_INSTALLED`.

```rust
pub code: String
```

#### Error::message

English text for logs.

```rust
pub message: String
```

#### Error::details

The values the message needs, when Toskar sent them.

```rust
pub details: Option<Map<String, Value>>
```

#### Error::new(status, code, message)

An error with its code.

```rust
pub fn new(status: u16, code: impl Into<String>, message: impl Into<String>) -> Self
```

### Result

What the SDK's calls answer.

```rust
pub type Result<T, E = Error> = std::result::Result<T, E>
```

### error_codes

The codes Toskar Core answers errors with, for `Error::code`. A newer
Core may answer with one this list doesn't have yet.

```rust
pub mod error_codes
```

Every code, with its text: [the error codes](errors.md).

## Pairing and reaching a computer from anywhere

### pair(address, code, device_name, confirm)

Pairs with the computer at address (host:port, as found or typed) using
the code Connect a device shows on it. The device must be on the
computer's local network.

`confirm` shows the person the short pin, such as 9B80-D9D9, and says
whether the computer shows the same. A script with no one to ask passes
`|_| true`.

```rust
pub async fn pair(address: &str, code: &str, device_name: &str, confirm: impl FnOnce(&str) -> bool) -> Result<Device>
```

### Builder::device(device)

Connects as a paired device: every connection pinned to its
computer's certificate, at home when it answers, and otherwise
directly or through its relay, from its address record. The device's
own address and key take the place of `Builder::url`,
`Builder::key`, and `Builder::http_client`.

```rust
pub fn device(self, device: Device) -> Self
```

### Client::path()

How the client reaches its paired computer now: `None` before its
first request, or for a client that isn't a paired device.

```rust
pub fn path(&self) -> Option<ConnectionPath>
```

### Client::reconnect()

Chooses the way in again, as after the network changed, and says which it found.

```rust
pub async fn reconnect(&self) -> Result<Option<ConnectionPath>>
```

### Device

What a paired device keeps, to connect again. Save it as a password is
saved: `api_key` and the route's secret and token are secrets. It's
serde, in the same JSON as the other SDKs'.

```rust
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Device
```

#### Device::address

The computer's host:port at home.

```rust
pub address: String
```

#### Device::api_key

The device's own key.

```rust
pub api_key: String
```

#### Device::pin

"sha256:<hex>" of the computer's certificate. It only ever comes from pairing.

```rust
pub pin: String
```

#### Device::route

How to find the computer away from home, when it has access from anywhere.

```rust
pub route: Option<Route>
```

### Route

How to find a computer away from home.

```rust
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Route
```

#### Route::secret

The route secret, base64url without padding.

```rust
pub secret: String
```

#### Route::id

The route's ID.

```rust
pub id: String
```

#### Route::relay

The relay the computer uses, such as relay.toskar.ai.

```rust
pub relay: String
```

#### Route::token

Lets the device look the computer up on Toskar's relay.

```rust
pub token: Option<String>
```

### ConnectionPath

How the client reaches its computer.

```rust
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum ConnectionPath
```

#### ConnectionPath::Home

At its address at home.

```rust
Home
```

#### ConnectionPath::Direct

Directly, at an address from its address record.

```rust
Direct
```

#### ConnectionPath::Relay

Through its relay.

```rust
Relay
```

#### ConnectionPath::as_str()

"home", "direct", or "relay", as the other SDKs say it.

```rust
pub fn as_str(self) -> &'static str
```

### records

Address records: how a paired device finds its computer away from home
(Toskar Core's docs/connecting.md). A record is sealed with the route
secret only the computer and its paired devices have, and signed by the
computer's own certificate, so a relay that keeps it can neither read it
nor change it.

```rust
pub mod records
```

### records::AddressRecord

What an address record says: the computer's ways in, and when it wrote them.

```rust
#[derive(Clone, Debug, PartialEq)]
pub struct AddressRecord
```

#### records::AddressRecord::addresses

The ways in, host:port.

```rust
pub addresses: Vec<String>
```

#### records::AddressRecord::at

When the computer wrote the record.

```rust
pub at: OffsetDateTime
```

### records::route_id(secret)

The route ID a route secret names.

```rust
pub fn route_id(secret: &str) -> Result<String>
```

### records::pin_of(der)

The pin of a certificate: "sha256:<hex>" of its DER.

```rust
pub fn pin_of(der: &[u8]) -> String
```

### records::short_pin(pin)

How a pin is shown for the person to compare: its first 8 hex digits, as ABCD-1234.

```rust
pub fn short_pin(pin: &str) -> String
```

### records::open(blob, secret, pin, now, max_age)

Opens an address record as docs/connecting.md says: sealed with the
route secret, from the certificate with pin, for this route, written at
most max_age before now. It answers an `Error` with `RECORD_SEALED`,
`RECORD_PIN`, or `RECORD_STALE` otherwise.

```rust
pub fn open(blob: &[u8], secret: &str, pin: &str, now: OffsetDateTime, max_age: Duration) -> Result<AddressRecord>
```

## Finding computers on the network

### find(timeout)

Asks the network for timeout and answers the computers that answered, by name.

```rust
for computer in toskar::find(std::time::Duration::from_secs(3)).await? {
    println!("{} {}", computer.name, computer.address);
}
```

```rust
pub async fn find(timeout: Duration) -> Result<Vec<DiscoveredComputer>>
```

### SERVICE_TYPE

What Toskar Core advertises over mDNS.

```rust
pub const SERVICE_TYPE: &str = "_localai._tcp"
```

### DiscoveredComputer

A Toskar Core found on the network.

```rust
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct DiscoveredComputer
```

#### DiscoveredComputer::name

The computer's name.

```rust
pub name: String
```

#### DiscoveredComputer::node_id

The computer's node ID.

```rust
pub node_id: String
```

#### DiscoveredComputer::version

Toskar Core's version.

```rust
pub version: String
```

#### DiscoveredComputer::address

The API's host:port, to pair with: the first of `addresses` that answers.

```rust
pub address: String
```

#### DiscoveredComputer::addresses

Every host:port found for the computer. A computer can have addresses
this device can't reach, such as a container network's.

```rust
pub addresses: Vec<String>
```

#### DiscoveredComputer::on_network

False when the API answers only on that computer: say to turn on
Connect a device there, rather than that it's unreachable.

```rust
pub on_network: bool
```

## The contract

### CONTRACT_VERSION

The client contract this SDK was built for.

```rust
pub const CONTRACT_VERSION: &str = "1.60"
```
