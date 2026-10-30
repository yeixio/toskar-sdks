# Kotlin and Java reference

*Generated from the SDK's KDoc by `kotlin/scripts/reference.py`.*

The official Kotlin and Java SDK for Toskar: local AI across your own computers.

```kotlin
val toskar = Toskar()
toskar.chatStream(ChatRequest(message = "Plan a three-day trip to Juneau")).use { events ->
    for (event in events) if (event is ChatEvent.Token) print(event.text)
}
```

`toskar.api` has [every route](api.md), generated from Toskar Core's API spec, and its models are in `ai.toskar.api`. The routes themselves, with every field: [toskar.ai/developers/api](https://toskar.ai/developers/api).

## Contents

- **Connecting:** [Toskar](#toskar), [ChatEvent](#chatevent), [EventStream](#eventstream)
- **Errors:** [ToskarException](#toskarexception), [ErrorCodes](#errorcodes)
- **Pairing and reaching a computer from anywhere:** [Toskar.pair](#toskarpairaddress-code-devicename-confirm), [Toskar.constructor](#toskarconstructordevice-retries-timeout), [Toskar.path](#toskarpath), [Toskar.reconnect](#toskarreconnect), [Device](#device), [Route](#route), [ConnectionPath](#connectionpath), [ShortPinCheck](#shortpincheck), [Records](#records), [AddressRecord](#addressrecord)
- **Finding computers on the network:** [Toskar.find](#toskarfindtimeout), [Toskar.SERVICE_TYPE](#toskarservice_type), [DiscoveredComputer](#discoveredcomputer)
- **The contract:** [CONTRACT_VERSION](#contract_version)
- [Every route on `toskar.api`](api.md)
- [Error codes](errors.md)

## Connecting

### Toskar

A connection to Toskar Core. Every call waits for its answer, so call it
off the main thread. Close it when you're done, to free its connections.

Parameters:

- `url`: Where Toskar Core answers. Default: `TOSKAR_URL`, or `DEFAULT_URL`, this computer.
- `key`: The API key for any address other than this computer's loopback. Default: `TOSKAR_API_KEY`.
- `retries`: How many times a safe request (GET, HEAD, OPTIONS) that fails to connect or answers 502, 503, or 504 is retried. A chat is never retried: it could answer twice.
- `timeout`: How long to wait for an answer to start. A streamed answer then runs for as long as it takes.
- `httpClient`: The OkHttpClient to send requests with, in place of one made with `timeout`. Toskar doesn't close it.
- `headers`: Headers to add to every request.

```kotlin
class Toskar : Closeable
```

#### Toskar.constructor(url, key, retries, timeout, httpClient, headers)

```kotlin
constructor(url: String? = null, key: String? = null, retries: Int = 2, timeout: Duration = Duration.ofSeconds(60), httpClient: OkHttpClient? = null, headers: Map<String, String> = emptyMap())
```

#### Toskar.url

Where Toskar Core answers.

```kotlin
val url: String
```

#### Toskar.api

Every route, typed from Toskar Core's API spec.

```kotlin
val api: Api
```

#### Toskar.chat(request)

Asks once and waits for the whole answer.

```kotlin
fun chat(request: ChatRequest): ChatAnswer
```

#### Toskar.chatStream(request)

Asks and yields the answer as it's written: tokens, then done. A
failure throws a `ToskarException` with its code, such as
`ErrorCodes.NO_MODEL_INSTALLED`, and ends the stream. Close it to stop
early.

```kotlin
fun chatStream(request: ChatRequest): EventStream<ChatEvent>
```

#### Toskar.events()

Yields what happens on Toskar as it happens, such as models loading
and automations running, until you close it.

```kotlin
fun events(): EventStream<Event>
```

#### Toskar.version()

Core's version and its client contract.

```kotlin
fun version(): VersionResponse
```

#### Toskar.close()

Frees the connections, unless the OkHttpClient was given.

```kotlin
override fun close()
```

#### Toskar.DEFAULT_URL

This computer's Toskar Core, which needs no key.

```kotlin
const val DEFAULT_URL: String
```

### ChatEvent

One event of a streamed chat.

```kotlin
sealed class ChatEvent
```

#### ChatEvent.Token

The next piece of the answer.

```kotlin
data class Token(val text: String) : ChatEvent()
```

#### ChatEvent.Done

The answer is finished and saved, with what the runtime measured when it reported it.

```kotlin
data class Done(val metrics: GenerationMetrics?) : ChatEvent()
```

### EventStream

A stream of events, read as you iterate. Close it to stop early; it
closes itself when it ends. From Java:

    try (EventStream<ChatEvent> events = toskar.chatStream(request)) {
        for (ChatEvent event : events) { … }
    }

```kotlin
class EventStream<T : Any> : Iterable<T>, Closeable
```

## Errors

### ToskarException

An error from Toskar Core: `{"error": {"code", "message", "details"}}`.

`code` is stable, such as `ErrorCodes.NO_MODEL_INSTALLED`; `message` is
English text for logs; `details` has the values the message needs.

    try { … } catch (e: ToskarException) { if (e.code == ErrorCodes.NO_MODEL_INSTALLED) … }

The SDK's own codes, for what goes wrong before Toskar Core answers, are
`CONNECTION_FAILED` (with the cause), `CONNECTION_LOST` (a stream cut off),
`BAD_URL`, and `HTTP_<status>` for an answer that isn't Toskar's.

```kotlin
class ToskarException(val status: Int, val code: String, message: String, val details: JsonObject? = null, cause: Throwable? = null) : RuntimeException(message, cause)
```

#### ToskarException.status

The HTTP status Toskar answered with, or 0 when it didn't answer.

```kotlin
val status: Int
```

#### ToskarException.code

```kotlin
val code: String
```

#### ToskarException.details

```kotlin
val details: JsonObject?
```

### ErrorCodes

The codes Toskar Core answers errors with, for `ToskarException.code`. A
newer Core may answer with one this list doesn't have yet.

```kotlin
object ErrorCodes
```

Every code, with its text: [the error codes](errors.md).

## Pairing and reaching a computer from anywhere

### Toskar.pair(address, code, deviceName, confirm)

Pairs with the computer at address (host:port, as found or typed)
using the code Connect a device shows on it. The device must be on
the computer's local network.

Parameters:

- `confirm`: Shows the person the short pin, such as 9B80-D9D9, and says whether the computer shows the same. Null skips the check, as a script with no one to ask does.

```kotlin
fun pair(address: String, code: String, deviceName: String, confirm: ShortPinCheck? = null): Device
```

### Toskar.constructor(device, retries, timeout)

Connects as a paired device: every connection pinned to its
computer's certificate, at home when it answers, and otherwise directly
or through its relay, from its address record.

```kotlin
constructor(device: Device, retries: Int = 2, timeout: Duration = Duration.ofSeconds(60))
```

### Toskar.path

How the client reaches its paired computer now, or null before its
first request, or for a client that isn't a paired device.

```kotlin
val path: ConnectionPath?
```

### Toskar.reconnect()

Chooses the way in again, as after the network changed, and says which it found.

```kotlin
fun reconnect(): ConnectionPath?
```

### Device

What a paired device keeps, to connect again. Save it as a password is
saved: `apiKey` and the route's secret and token are secrets. It's
`@Serializable`, as the other SDKs' JSON:
`Json.encodeToString(Device.serializer(), device)`.

```kotlin
data class Device(val address: String, val apiKey: String, val pin: String, val route: Route? = null)
```

#### Device.address

The computer's host:port at home.

```kotlin
val address: String
```

#### Device.apiKey

```kotlin
val apiKey: String
```

#### Device.pin

"sha256:<hex>" of the computer's certificate. It only ever comes from pairing.

```kotlin
val pin: String
```

#### Device.route

How to find the computer away from home, when it has access from anywhere.

```kotlin
val route: Route?
```

### Route

How to find a computer away from home.

```kotlin
data class Route(val secret: String, val id: String, val relay: String, val token: String? = null)
```

#### Route.secret

The route secret, base64url without padding.

```kotlin
val secret: String
```

#### Route.id

```kotlin
val id: String
```

#### Route.relay

The relay the computer uses, such as relay.toskar.ai.

```kotlin
val relay: String
```

#### Route.token

Lets the device look the computer up on Toskar's relay.

```kotlin
val token: String?
```

### ConnectionPath

How the client reaches its computer.

```kotlin
enum class ConnectionPath(val value: String)
```

#### ConnectionPath.HOME

```kotlin
HOME("home")
```

#### ConnectionPath.DIRECT

```kotlin
DIRECT("direct")
```

#### ConnectionPath.RELAY

```kotlin
RELAY("relay")
```

### ShortPinCheck

Shows the person the short pin, such as 9B80-D9D9, and says whether the computer shows the same.

```kotlin
fun interface ShortPinCheck
```

#### ShortPinCheck.confirm(shortPin)

```kotlin
fun confirm(shortPin: String): Boolean
```

### Records

Address records, and the route IDs and pins they're checked with.

```kotlin
object Records
```

#### Records.routeID(secret)

The route ID a route secret names.

```kotlin
fun routeID(secret: String): String
```

#### Records.pinOf(der)

The pin of a certificate: "sha256:<hex>" of its DER.

```kotlin
fun pinOf(der: ByteArray): String
```

#### Records.shortPin(pin)

How a pin is shown for the person to compare: its first 8 hex digits,
as ABCD-1234.

```kotlin
fun shortPin(pin: String): String
```

#### Records.open(blob, secret, pin, now, maxAge)

Opens an address record as docs/connecting.md says: sealed with the
route secret, from the certificate with pin, for this route, and no
older than maxAge. It throws a `ToskarException` with `RECORD_SEALED`,
`RECORD_PIN`, or `RECORD_STALE` otherwise.

```kotlin
fun open(blob: ByteArray, secret: String, pin: String, now: Instant = Instant.now(), maxAge: Duration = Duration.ofHours(1)): AddressRecord
```

### AddressRecord

What an address record says: the computer's ways in, and when it wrote them.

```kotlin
data class AddressRecord(val addresses: List<String>, val at: Instant)
```

## Finding computers on the network

### Toskar.find(timeout)

Asks the network for timeout and returns the computers that
answered, by name. On Android, hold a `WifiManager.MulticastLock`
while it looks.

```kotlin
fun find(timeout: Duration = Duration.ofSeconds(3)): List<DiscoveredComputer>
```

### Toskar.SERVICE_TYPE

What Toskar Core advertises over mDNS.

```kotlin
const val SERVICE_TYPE: String
```

### DiscoveredComputer

A Toskar Core found on the network.

```kotlin
data class DiscoveredComputer(val name: String, val nodeID: String, val version: String, val address: String, val addresses: List<String>, val onNetwork: Boolean)
```

#### DiscoveredComputer.name

```kotlin
val name: String
```

#### DiscoveredComputer.nodeID

```kotlin
val nodeID: String
```

#### DiscoveredComputer.version

Toskar Core's version.

```kotlin
val version: String
```

#### DiscoveredComputer.address

The API's host:port, to pair with: the first of `addresses` that answers.

```kotlin
val address: String
```

#### DiscoveredComputer.addresses

Every host:port found for the computer. A computer can have addresses
this device can't reach, such as a container network's.

```kotlin
val addresses: List<String>
```

#### DiscoveredComputer.onNetwork

False when the API answers only on that computer: say to turn on
Connect a device there, rather than that it's unreachable.

```kotlin
val onNetwork: Boolean
```

## The contract

### CONTRACT_VERSION

The client contract this SDK was built for.

```kotlin
const val CONTRACT_VERSION: String
```
