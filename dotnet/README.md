# Toskar for .NET

The official .NET SDK for [Toskar](https://toskar.ai), for C# and any .NET language. It needs .NET 8 or later.

<!-- snippet: skip -->
```sh
dotnet add package Toskar
```

Every type, method, and route: [the reference](https://github.com/yeixio/toskar-sdks/blob/main/reference/dotnet/README.md).

## Quick start

<!-- snippet: run -->
```csharp
using Toskar;
using Toskar.Models;

// This computer's Toskar Core, at http://127.0.0.1:7331, needs no key.
// Elsewhere: new ToskarClient("http://studio.local:7331", "tk_…"),
// or set TOSKAR_URL and TOSKAR_API_KEY.
using var toskar = new ToskarClient();

// Stream an answer as it's written.
await foreach (var e in toskar.ChatStreamAsync(new ChatRequest { Message = "Plan a three-day trip to Juneau" }))
{
    if (e is ChatEvent.Token token)
    {
        Console.Write(token.Text);
    }
}

// Or wait for the whole answer.
var answer = await toskar.ChatAsync(new ChatRequest { Message = "Summarize this in one line: …" });
Console.WriteLine(answer.Content);
```

## Every route, typed

`toskar.Api` is generated from Toskar Core's API spec, so every operation is an async method named after it, and every answer is a record in `Toskar.Models`:

```csharp
var models = await toskar.Api.ListModelsAsync(); // List<Model>
var chat = await toskar.Api.CreateConversationAsync(new CreateConversationRequest { Title = "Trip" });
var messages = await toskar.Api.ListConversationMessagesAsync(chat.Id);
```

Properties are PascalCase (`ModelId` for `model_id`). One that Core may leave out is nullable, and a newer Core's new fields and values are passed over, not failed on. Values that only a few are known for, such as `Effort`, are strings, so a new one doesn't break your build. The schema `Task` is `ToskarTask`, so it never hides `System.Threading.Tasks.Task`.

## Errors

Toskar answers errors with a stable code. Any call that gets one throws a `ToskarException`, with the code, a message for logs, and the details:

```csharp
try
{
    await toskar.ChatAsync(new ChatRequest { Message = "Hi" });
}
catch (ToskarException e) when (e.Code == ErrorCodes.NO_MODEL_INSTALLED)
{
    await toskar.Api.InstallModelAsync("qwen2.5-7b-q4");
}
```

A streamed answer that fails throws its error, with the code Toskar sent. One that stops before it finishes throws `CONNECTION_LOST`, and a computer that doesn't answer throws `CONNECTION_FAILED`, with the network error as its inner exception.

## Events

```csharp
await foreach (var e in toskar.EventsAsync()) // until you cancel
{
    Console.WriteLine(e.Type); // such as model.download.progress or automation.completed
}
```

## Retries, timeouts, and cancelling

Safe requests (GET, HEAD, OPTIONS) that fail to connect, or that Toskar answers with 502, 503, or 504, are retried twice with backoff. A chat is never retried, since it could answer twice. Each request waits 60 seconds for its answer to start, and a streamed answer then runs for as long as it takes. Every method takes a `CancellationToken`, and the settings are in `ToskarOptions`:

```csharp
using var patient = new ToskarClient(new ToskarOptions { Retries = 5, Timeout = TimeSpan.FromMinutes(5) });
```

Bring your own `HttpClient` with `ToskarOptions.HttpClient`, such as one from `IHttpClientFactory`; the client then leaves disposing it to you.

## Pairing, as the Toskar apps do

An app can pair as a device, with the code **Connect a device** shows on the computer, instead of using an API key. It then reaches its computer at home and, when the computer has access from anywhere, directly or through its relay, always pinned to the computer's own certificate ([how it works](https://github.com/yeixio/toskar-core/blob/main/docs/connecting.md)).

```csharp
using System.Text.Json;

// On the computer's network, with the code it shows:
var device = await ToskarClient.PairAsync("192.168.1.20:7331", "123456", "Kitchen tablet",
    // Show the short pin, such as 9B80-D9D9, and ask whether the computer shows the same.
    shortPin => AskThePerson(shortPin));
// Save device as a password is saved: its key and route are secrets. It's
// in the same JSON as the other SDKs':
var saved = JsonSerializer.Serialize(device);

using var paired = new ToskarClient(JsonSerializer.Deserialize<Device>(saved)!);
var models = await paired.Api.ListModelsAsync();
Console.WriteLine(paired.Path); // Home, Direct, or Relay
```

`PairAsync` also takes a `Func<string, Task<bool>>`, to ask in a dialog. Every connection checks the computer's certificate before anything is sent. A different certificate throws `PIN_MISMATCH`, and is never accepted on its own: pair again to trust a new one. Away from home, the client opens the computer's sealed address record from its relay, tries its direct ways in at once and the relay a second later, and keeps the first that answers. `await paired.ReconnectAsync()` chooses again, as after the network changes. A device key reaches the routes a device needs. Scripts and servers that need the rest use a key from API Access.

## Find computers on the network

Computers running Toskar announce themselves on the home network (mDNS, `_localai._tcp`). `ToskarClient.FindAsync` lists them, so a person can pick one instead of typing an address. It needs no other library:

```csharp
foreach (var computer in await ToskarClient.FindAsync(TimeSpan.FromSeconds(3)))
{
    Console.WriteLine($"{computer.Name} {computer.Address}");
}
```

Pair with `computer.Address`. When `computer.OnNetwork` is false, the computer answers only on itself: tell the person to turn on Connect a device there, rather than that it's unreachable. A computer can have addresses this device can't reach, such as a container network's. `Address` is the first one that answers, and `Addresses` has them all.
