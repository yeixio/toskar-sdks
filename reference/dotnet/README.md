# .NET reference

*Generated from the SDK's XML doc comments by `dotnet/scripts/reference.py`.*

The official .NET SDK for Toskar: local AI across your own computers. It's in the `Toskar` namespace.

```csharp
using var toskar = new ToskarClient();
await foreach (var e in toskar.ChatStreamAsync(new ChatRequest { Message = "Plan a three-day trip to Juneau" }))
{
    if (e is ChatEvent.Token token) Console.Write(token.Text);
}
```

`toskar.Api` has [every route](api.md), generated from Toskar Core's API spec, and its models are in `Toskar.Models`. The routes themselves, with every field: [toskar.ai/developers/api](https://toskar.ai/developers/api).

## Contents

- **Connecting:** [ToskarClient](#toskarclient), [ToskarOptions](#toskaroptions), [ChatEvent](#chatevent), [ToskarApi](#toskarapi)
- **Errors:** [ToskarException](#toskarexception), [ErrorCodes](#errorcodes)
- **Pairing and reaching a computer from anywhere:** [ToskarClient.PairAsync](#toskarclientpairasyncaddress-code-devicename-confirm-cancellationtoken), [new ToskarClient](#new-toskarclientdevice-options), [ToskarClient.Path](#toskarclientpath), [ToskarClient.ReconnectAsync](#toskarclientreconnectasynccancellationtoken), [Device](#device), [Route](#route), [ConnectionPath](#connectionpath), [Records](#records), [AddressRecord](#addressrecord)
- **Finding computers on the network:** [ToskarClient.FindAsync](#toskarclientfindasynctimeout-cancellationtoken), [ToskarClient.ServiceType](#toskarclientservicetype), [DiscoveredComputer](#discoveredcomputer)
- **The contract:** [Contract](#contract)
- [Every route on `toskar.Api`](api.md)
- [Error codes](errors.md)

## Connecting

### ToskarClient

A connection to Toskar Core. Dispose it when you're done, to free its connections.

```csharp
sealed class ToskarClient : IDisposable
```

#### ToskarClient.DefaultUrl

This computer's Toskar Core, which needs no key.

```csharp
const string DefaultUrl = "http://127.0.0.1:7331"
```

#### new ToskarClient(options)

Connects to Toskar Core: this computer's, unless options or `TOSKAR_URL` say another.

```csharp
ToskarClient(ToskarOptions? options = null)
```

#### new ToskarClient(url, key)

Connects to the Toskar Core at url, with key for any address other than this computer's loopback.

```csharp
ToskarClient(string url, string? key = null)
```

#### ToskarClient.Url

Where Toskar Core answers.

```csharp
string Url { get; }
```

#### ToskarClient.Api

Every route, typed from Toskar Core's API spec.

```csharp
ToskarApi Api { get; }
```

#### ToskarClient.ChatAsync(request, cancellationToken)

Asks once and waits for the whole answer.

```csharp
Task<ChatAnswer> ChatAsync(ChatRequest request, CancellationToken cancellationToken = default)
```

#### ToskarClient.ChatStreamAsync(request, cancellationToken)

Asks and yields the answer as it's written: tokens, then done. A failure throws a `ToskarException` with its code, such as `ErrorCodes.NO_MODEL_INSTALLED`, and ends the stream.

```csharp
IAsyncEnumerable<ChatEvent> ChatStreamAsync(ChatRequest request, CancellationToken cancellationToken = default)
```

#### ToskarClient.EventsAsync(cancellationToken)

Yields what happens on Toskar as it happens, such as models loading and automations running, until you cancel.

```csharp
IAsyncEnumerable<Event> EventsAsync(CancellationToken cancellationToken = default)
```

#### ToskarClient.VersionAsync(cancellationToken)

Core's version and its client contract.

```csharp
Task<VersionResponse> VersionAsync(CancellationToken cancellationToken = default)
```

#### ToskarClient.Dispose()

Frees the connections, unless the HttpClient was given.

```csharp
void Dispose()
```

### ToskarOptions

How to connect: every setting has a default.

```csharp
sealed record ToskarOptions
```

#### ToskarOptions.Url

Where Toskar Core answers. Default: `TOSKAR_URL`, or `ToskarClient.DefaultUrl`, this computer.

```csharp
string? Url { get; init; }
```

#### ToskarOptions.Key

The API key for any address other than this computer's loopback. Default: `TOSKAR_API_KEY`.

```csharp
string? Key { get; init; }
```

#### ToskarOptions.Retries

How many times a safe request (GET, HEAD, OPTIONS) that fails to connect or answers 502, 503, or 504 is retried. A chat is never retried: it could answer twice.

```csharp
int Retries { get; init; }
```

#### ToskarOptions.Timeout

How long to wait for an answer to start. A streamed answer then runs for as long as it takes.

```csharp
TimeSpan Timeout { get; init; }
```

#### ToskarOptions.HttpClient

The HttpClient to send requests with, in place of one the client makes. The client doesn't dispose it.

```csharp
HttpClient? HttpClient { get; init; }
```

#### ToskarOptions.Headers

Headers to add to every request.

```csharp
IReadOnlyDictionary<string, string>? Headers { get; init; }
```

### ChatEvent

One event of a streamed chat: a `Token`, then `Done`.

```csharp
abstract record ChatEvent
```

#### ChatEvent.Token

The next piece of the answer.

```csharp
sealed record Token(string Text) : ChatEvent
```

#### ChatEvent.Done

The answer is finished and saved, with what the runtime measured when it reported it.

```csharp
sealed record Done(GenerationMetrics? Metrics) : ChatEvent
```

### ToskarApi

Every route of Toskar Core's API, typed: `toskar.Api.ListModelsAsync()` and so on. An error answer throws a `ToskarException`.

```csharp
sealed class ToskarApi
```

Its methods: [every route on `toskar.Api`](api.md).

## Errors

### ToskarException

An error from Toskar Core: `{"error": {"code", "message", "details"}}`. `Code` is stable, such as `ErrorCodes.NO_MODEL_INSTALLED`; `Exception.Message` is English text for logs; `Details` has the values the message needs.

The SDK's own codes, for what goes wrong before Toskar Core answers, are `CONNECTION_FAILED` (with the cause as the inner exception), `CONNECTION_LOST` (a stream cut off), `BAD_URL`, and `HTTP_<status>` for an answer that isn't Toskar's.

```csharp
sealed class ToskarException : Exception
```

#### new ToskarException(status, code, message, details, inner)

An error with its code.

```csharp
ToskarException(int status, string code, string message, JsonObject? details = null, Exception? inner = null)
```

#### ToskarException.Status

The HTTP status Toskar answered with, or 0 when it didn't answer.

```csharp
int Status { get; }
```

#### ToskarException.Code

The error's code, such as `NO_MODEL_INSTALLED`.

```csharp
string Code { get; }
```

#### ToskarException.Details

The values the message needs, when Toskar sent them.

```csharp
JsonObject? Details { get; }
```

#### ToskarException.ToString()

The message, status, and code, for logs, such as `toskar: No such model (404 MODEL_NOT_FOUND)`.

```csharp
override string ToString()
```

### ErrorCodes

The codes Toskar Core answers errors with, for `ToskarException.Code`. A newer Core may answer with one this list doesn't have yet.

```csharp
static class ErrorCodes
```

Every code, with its text: [the error codes](errors.md).

## Pairing and reaching a computer from anywhere

### ToskarClient.PairAsync(address, code, deviceName, confirm, cancellationToken)

Pairs with the computer at address (host:port, as found or typed) using the code Connect a device shows on it. The device must be on the computer's local network.

Parameters:

- `address`: The computer's host:port.
- `code`: The code Connect a device shows.
- `deviceName`: What the computer calls this device.
- `confirm`: Shows the person the short pin, such as 9B80-D9D9, and says whether the computer shows the same. Null skips the check, as a script with no one to ask does.
- `cancellationToken`: Cancels pairing.

```csharp
static Task<Device> PairAsync(string address, string code, string deviceName, Func<string, Task<bool>>? confirm = null, CancellationToken cancellationToken = default)
```

### ToskarClient.PairAsync(address, code, deviceName, confirm, cancellationToken)

Pairs with the computer at address (host:port, as found or typed) using the code Connect a device shows on it. The device must be on the computer's local network.

Parameters:

- `address`: The computer's host:port.
- `code`: The code Connect a device shows.
- `deviceName`: What the computer calls this device.
- `confirm`: Shows the person the short pin, such as 9B80-D9D9, and says whether the computer shows the same. Null skips the check, as a script with no one to ask does.
- `cancellationToken`: Cancels pairing.

```csharp
static Task<Device> PairAsync(string address, string code, string deviceName, Func<string, bool> confirm, CancellationToken cancellationToken = default)
```

### new ToskarClient(device, options)

Connects as a paired device: every connection pinned to its computer's certificate, at home when it answers, and otherwise directly or through its relay, from its address record. Of the options, the device's own address and key take the place of `ToskarOptions.Url`, `ToskarOptions.Key`, and `ToskarOptions.HttpClient`.

```csharp
ToskarClient(Device device, ToskarOptions? options = null)
```

### ToskarClient.Path

How the client reaches its paired computer now, or null before its first request, or for a client that isn't a paired device.

```csharp
ConnectionPath? Path { get; }
```

### ToskarClient.ReconnectAsync(cancellationToken)

Chooses the way in again, as after the network changed, and says which it found.

```csharp
Task<ConnectionPath?> ReconnectAsync(CancellationToken cancellationToken = default)
```

### Device

What a paired device keeps, to connect again. Save it as a password is saved: `ApiKey` and the route's secret and token are secrets. `JsonSerializer` reads and writes it as the other SDKs' JSON.

Parameters:

- `Address`: The computer's host:port at home.
- `ApiKey`: The device's own key.
- `Pin`: "sha256:<hex>" of the computer's certificate. It only ever comes from pairing.
- `Route`: How to find the computer away from home, when it has access from anywhere.

```csharp
sealed record Device(string Address, string ApiKey, string Pin, Route? Route = null)
```

### Route

How to find a computer away from home.

Parameters:

- `Secret`: The route secret, base64url without padding.
- `Id`: The route's ID.
- `Relay`: The relay the computer uses, such as relay.toskar.ai.
- `Token`: Lets the device look the computer up on Toskar's relay.

```csharp
sealed record Route(string Secret, string Id, string Relay, string? Token = null)
```

### ConnectionPath

How the client reaches its computer.

```csharp
enum ConnectionPath
```

#### ConnectionPath.Home

At its address at home.

```csharp
Home
```

#### ConnectionPath.Direct

Directly, at an address from its address record.

```csharp
Direct
```

#### ConnectionPath.Relay

Through its relay.

```csharp
Relay
```

### Records

Address records, and the route IDs and pins they're checked with.

```csharp
static class Records
```

#### Records.RouteId(secret)

The route ID a route secret names.

```csharp
static string RouteId(string secret)
```

#### Records.PinOf(der)

The pin of a certificate: "sha256:<hex>" of its DER.

```csharp
static string PinOf(byte[] der)
```

#### Records.ShortPin(pin)

How a pin is shown for the person to compare: its first 8 hex digits, as ABCD-1234.

```csharp
static string ShortPin(string pin)
```

#### Records.Open(blob, secret, pin, now, maxAge)

Opens an address record as docs/connecting.md says: sealed with the route secret, from the certificate with pin, for this route, and no older than maxAge (an hour by default). It throws a `ToskarException` with `RECORD_SEALED`, `RECORD_PIN`, or `RECORD_STALE` otherwise.

```csharp
static AddressRecord Open(byte[] blob, string secret, string pin, DateTimeOffset? now = null, TimeSpan? maxAge = null)
```

### AddressRecord

What an address record says: the computer's ways in, and when it wrote them.

```csharp
sealed record AddressRecord(IReadOnlyList<string> Addresses, DateTimeOffset At)
```

## Finding computers on the network

### ToskarClient.FindAsync(timeout, cancellationToken)

Asks the network for timeout (3 seconds by default) and answers the computers that answered, by name.

Parameters:

- `timeout`: How long to listen for answers.
- `cancellationToken`: Stops looking.

```csharp
static Task<IReadOnlyList<DiscoveredComputer>> FindAsync(TimeSpan? timeout = null, CancellationToken cancellationToken = default)
```

### ToskarClient.ServiceType

What Toskar Core advertises over mDNS.

```csharp
const string ServiceType = "_localai._tcp"
```

### DiscoveredComputer

A Toskar Core found on the network.

Parameters:

- `Name`: The computer's name.
- `NodeId`: The computer's node ID.
- `Version`: Toskar Core's version.
- `Address`: The API's host:port, to pair with: the first of `Addresses` that answers.
- `Addresses`: Every host:port found for the computer. A computer can have addresses this device can't reach, such as a container network's.
- `OnNetwork`: False when the API answers only on that computer: say to turn on Connect a device there, rather than that it's unreachable.

```csharp
sealed record DiscoveredComputer(string Name, string NodeId, string Version, string Address, IReadOnlyList<string> Addresses, bool OnNetwork)
```

## The contract

### Contract

The client contract this SDK was built for.

```csharp
static class Contract
```

#### Contract.Version

The contract version, such as 1.60.

```csharp
const string Version = "1.60"
```
