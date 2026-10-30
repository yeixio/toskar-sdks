# Swift reference

*Generated from the SDK's doc comments by `swift/scripts/reference.py`.*

The official Swift SDK for Toskar: local AI across your own computers.

```swift
let toskar = try Toskar()
for try await event in toskar.chatStream(ChatRequest(message: "Plan a three-day trip to Juneau")) {
    if case .token(let text) = event { print(text, terminator: "") }
}
```

`toskar.api` has every route, generated from Toskar Core's API spec. The routes themselves, with every field: [toskar.ai/developers/api](https://toskar.ai/developers/api).

## Contents

- **Connecting:** [Toskar](#toskar), [ChatRequest](#chatrequest)
- **Errors:** [ToskarError](#toskarerror), [Error.toskar](#errortoskar)
- **Pairing and reaching a computer from anywhere:** [Toskar.pair](#toskarpairaddresscodedevicenameconfirm), [Toskar.init](#toskarinitdeviceretriestimeout), [Toskar.path](#toskarpath), [Toskar.reconnect](#toskarreconnect), [Device](#device), [Route](#route), [ConnectionPath](#connectionpath), [Toskar.toskarRelay](#toskartoskarrelay), [Toskar.pinOf](#toskarpinof_), [Toskar.shortPin](#toskarshortpin_), [Toskar.routeID](#toskarrouteid_), [Toskar.openRecord](#toskaropenrecord_secretpinnowmaxage), [AddressRecord](#addressrecord)
- **Finding computers on the network:** [Toskar.find](#toskarfindtimeout), [Toskar.serviceType](#toskarservicetype), [DiscoveredComputer](#discoveredcomputer)
- **The contract:** [contractVersion](#contractversion)
- [Error codes](errors.md)

## Connecting

### Toskar

A connection to Toskar Core.

```swift
final class Toskar
```

#### Toskar.init(url:key:retries:timeout:session:transport:headers:)

Connects to Toskar Core.

- Parameters:
  - url: Where Toskar Core answers. Default: `TOSKAR_URL`, or
    `Toskar.defaultURL`, this computer.
  - key: The API key for any address other than this computer's
    loopback. Default: `TOSKAR_API_KEY`.
  - retries: How many times a safe request (GET, HEAD, OPTIONS) that
    fails to connect or answers 502, 503, or 504 is retried. A chat
    is never retried: it could answer twice.
  - timeout: How long to wait for an answer to start. A streamed
    answer then runs for as long as it takes.
  - session: The URLSession to send requests with, in place of one
    made with `timeout`.
  - transport: What sends requests, in place of URLSession, such as
    AsyncHTTPClientTransport on Linux, where URLSession doesn't
    stream answers.
  - headers: Headers to add to every request.

```swift
convenience init(url: URL? = nil, key: String? = nil, retries: Int = 2, timeout: TimeInterval = 60, session: URLSession? = nil, transport: (any ClientTransport)? = nil, headers: [String : String] = [:]) throws
```

#### Toskar.ChatEvent

One event of a streamed chat.

```swift
enum ChatEvent
```

##### Toskar.ChatEvent.done(_:)

The answer is finished and saved, with what the runtime
measured when it reported it.

```swift
case done(Components.Schemas.GenerationMetrics?)
```

##### Toskar.ChatEvent.token(_:)

The next piece of the answer.

```swift
case token(String)
```

#### Toskar.api

Every route, typed from Toskar Core's API spec. An error answer
throws, and `error.toskar` is its `ToskarError`.

```swift
let api: Client
```

#### Toskar.chat(_:)

Asks once and waits for the whole answer.

```swift
func chat(_ request: ChatRequest) async throws -> Components.Schemas.ChatAnswer
```

#### Toskar.chatStream(_:)

Asks and yields the answer as it's written: tokens, then done. A
failure throws a `ToskarError` with its code, such as
`.noModelInstalled`, and ends the stream.

```swift
func chatStream(_ request: ChatRequest) -> AsyncThrowingStream<ChatEvent, Error>
```

#### Toskar.defaultURL

This computer's Toskar Core, which needs no key.

```swift
static let defaultURL: URL
```

#### Toskar.events()

Yields what happens on Toskar as it happens, such as models loading
and automations running, until you stop.

```swift
func events() -> AsyncThrowingStream<Components.Schemas.Event, Error>
```

#### Toskar.url

Where Toskar Core answers.

```swift
let url: URL
```

#### Toskar.version()

Core's version and its client contract.

```swift
func version() async throws -> Components.Schemas.VersionResponse
```

### ChatRequest

A chat message to send: what `chat` and `chatStream` take.

```swift
typealias ChatRequest = Operations.Chat.Input.Body.JsonPayload
```

## Errors

### ToskarError

An error from Toskar Core: `{"error": {"code", "message", "details"}}`.

`code` is stable, such as `.noModelInstalled`; `message` is English text
for logs; `details` has the values the message needs.

    do { … } catch let error where error.toskar?.code == .noModelInstalled { … }

```swift
struct ToskarError
```

#### ToskarError.init(status:code:message:details:)

```swift
init(status: Int, code: Code, message: String, details: OpenAPIObjectContainer? = nil)
```

#### ToskarError.Code

A code Toskar Core answers errors with. A newer Core may answer with
one the SDK doesn't name yet, so it's open.

```swift
struct Code
```

##### ToskarError.Code.init(_:)

```swift
init(_ rawValue: String)
```

#### ToskarError.code

```swift
let code: Code
```

#### ToskarError.details

```swift
let details: OpenAPIObjectContainer?
```

#### ToskarError.message

```swift
let message: String
```

#### ToskarError.status

The HTTP status Toskar answered with.

```swift
let status: Int
```

### Error.toskar

The `ToskarError` this is, or that a generated call wrapped, or nil.

```swift
var toskar: ToskarError? { get }
```

## Pairing and reaching a computer from anywhere

### Toskar.pair(address:code:deviceName:confirm:)

Pairs with the computer at address (host:port, as found or typed)
using the code Connect a device shows on it. The device must be on
the computer's local network.

- Parameter confirm: Shows the person the short pin, such as
  9B80-D9D9, and says whether the computer shows the same. Nil
  skips the check, as a script with no one to ask does.

```swift
static func pair(address: String, code: String, deviceName: String, confirm: (@Sendable (String) async -> Bool)? = nil) async throws -> Device
```

### Toskar.init(device:retries:timeout:)

Connects as a paired device: every connection pinned to its
computer's certificate, at home when it answers, and otherwise
directly or through its relay, from its address record.

```swift
convenience init(device: Device, retries: Int = 2, timeout: TimeInterval = 60) throws
```

### Toskar.path

How the client reaches its paired computer now, or nil before its
first request, or for a client that isn't a paired device.

```swift
var path: ConnectionPath? { get async }
```

### Toskar.reconnect()

Chooses the way in again, as after the network changed, and says
which it found.

```swift
@discardableResult func reconnect() async throws -> ConnectionPath?
```

### Device

What a paired device keeps, to connect again. Save it as a password
is saved, such as in the Keychain: `apiKey` and the route's secret
and token are secrets. It's Codable, as the other SDKs' JSON.

```swift
struct Device
```

#### Device.init(address:apiKey:pin:route:)

```swift
init(address: String, apiKey: String, pin: String, route: Route? = nil)
```

#### Device.address

The computer's host:port at home.

```swift
var address: String
```

#### Device.apiKey

```swift
var apiKey: String
```

#### Device.pin

"sha256:<hex>" of the computer's certificate. It only ever comes
from pairing.

```swift
var pin: String
```

#### Device.route

How to find the computer away from home, when it has access from
anywhere.

```swift
var route: Route?
```

### Route

How to find a computer away from home.

```swift
struct Route
```

#### Route.init(secret:id:relay:token:)

```swift
init(secret: String, id: String, relay: String, token: String? = nil)
```

#### Route.id

```swift
var id: String
```

#### Route.relay

The relay the computer uses, such as relay.toskar.ai.

```swift
var relay: String
```

#### Route.secret

The route secret, base64url without padding.

```swift
var secret: String
```

#### Route.token

Lets the device look the computer up on Toskar's relay.

```swift
var token: String?
```

### ConnectionPath

How the client reaches its computer.

```swift
enum ConnectionPath
```

#### ConnectionPath.direct

```swift
case direct
```

#### ConnectionPath.home

```swift
case home
```

#### ConnectionPath.relay

```swift
case relay
```

### Toskar.toskarRelay

Toskar's own relay. It's asked only with a route token.

```swift
static let toskarRelay: String
```

### Toskar.pinOf(_:)

The pin of a certificate: "sha256:<hex>" of its DER.

```swift
static func pinOf(_ der: Data) -> String
```

### Toskar.shortPin(_:)

How a pin is shown for the person to compare: its first 8 hex
digits, as ABCD-1234.

```swift
static func shortPin(_ pin: String) -> String
```

### Toskar.routeID(_:)

The route ID a route secret names.

```swift
static func routeID(_ secret: String) throws -> String
```

### Toskar.openRecord(_:secret:pin:now:maxAge:)

Opens an address record as docs/connecting.md says: sealed with
the route secret, from the certificate with pin, for this route,
and no older than maxAge. It throws `.recordSealed`,
`.recordPin`, or `.recordStale` otherwise.

```swift
static func openRecord(_ blob: Data, secret: String, pin: String, now: Date = Date(), maxAge: TimeInterval = 3600) throws -> AddressRecord
```

### AddressRecord

What an address record says: the computer's ways in, and when it
wrote them.

```swift
struct AddressRecord
```

#### AddressRecord.addresses

```swift
let addresses: [String]
```

#### AddressRecord.at

```swift
let at: Date
```

## Finding computers on the network

### Toskar.find(timeout:)

Browses for timeout seconds and returns the computers that
answered, by name.

```swift
static func find(timeout: TimeInterval = 3) async -> [DiscoveredComputer]
```

### Toskar.serviceType

What Toskar Core advertises.

```swift
static let serviceType: String
```

### DiscoveredComputer

A Toskar Core found on the network.

```swift
struct DiscoveredComputer
```

#### DiscoveredComputer.address

The API's host:port, to pair with: the first of `addresses` that
answers.

```swift
let address: String
```

#### DiscoveredComputer.addresses

Every host:port found for the computer. A computer can have
addresses this device can't reach, such as a container network's.

```swift
let addresses: [String]
```

#### DiscoveredComputer.name

```swift
let name: String
```

#### DiscoveredComputer.nodeID

```swift
let nodeID: String
```

#### DiscoveredComputer.onNetwork

False when the API answers only on that computer: say to turn on
Connect a device there, rather than that it's unreachable.

```swift
let onNetwork: Bool
```

#### DiscoveredComputer.version

Toskar Core's version.

```swift
let version: String
```

## The contract

### contractVersion

The client contract this SDK was built for, sent as Toskar-Client-Contract.

```swift
let contractVersion: String
```
