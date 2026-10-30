# Toskar for Swift

The official Swift SDK for [Toskar](https://toskar.ai). It needs Swift 5.9 or later, on macOS 13, iOS 16, tvOS 16, watchOS 9, visionOS 1, or later, or on Linux.

<!-- snippet: skip -->
```swift
// Package.swift
dependencies: [
    .package(url: "https://github.com/yeixio/toskar-sdks", from: "0.3.0"),
],
targets: [
    .target(name: "MyApp", dependencies: [.product(name: "Toskar", package: "toskar-sdks")]),
]
```

## Quick start

<!-- snippet: run -->
```swift
import Toskar

// This computer's Toskar Core, at http://127.0.0.1:7331, needs no key.
// Elsewhere: Toskar(url: URL(string: "http://studio.local:7331"), key: "tk_…"),
// or set TOSKAR_URL and TOSKAR_API_KEY.
let toskar = try Toskar()

// Stream an answer as it's written.
for try await event in toskar.chatStream(ChatRequest(message: "Plan a three-day trip to Juneau")) {
    if case .token(let text) = event {
        print(text, terminator: "")
    }
}

// Or wait for the whole answer.
let answer = try await toskar.chat(ChatRequest(message: "Summarize this in one line: …"))
print(answer.content)
```

## Every route, typed

`toskar.api` is generated from Toskar Core's API spec by [Swift OpenAPI Generator](https://github.com/apple/swift-openapi-generator), so every operation is a method, and each answer is an enum of what it can be:

```swift
let models = try await toskar.api.listModels().ok.body.json // [Components.Schemas.Model]
let chat = try await toskar.api.createConversation(body: .json(.init(title: "Trip"))).created.body.json
let messages = try await toskar.api.listConversationMessages(path: .init(id: chat.id)).ok.body.json
```

## Errors

Toskar answers errors with a stable code. Any call that gets one throws, and `error.toskar` is the `ToskarError`, with the code, a message for logs, and the details:

```swift
do {
    _ = try await toskar.chat(ChatRequest(message: "Hi"))
} catch let error where error.toskar?.code == .noModelInstalled {
    // Install one: try await toskar.api.installModel(path: .init(id: "qwen2.5-7b-q4"), body: .json(.init()))
}
```

A streamed answer that fails throws its error, with the code Toskar sent. One that stops before it finishes throws `CONNECTION_LOST`.

## Events

```swift
for try await event in toskar.events() { // until you stop
    print(event._type) // such as model.download.progress or automation.completed
}
```

## Retries and timeouts

Safe requests (GET, HEAD, OPTIONS) that fail to connect, or that Toskar answers with 502, 503, or 504, are retried twice with backoff. A chat is never retried, since it could answer twice. Each request waits 60 seconds for its answer to start, and a streamed answer then runs for as long as it takes. Change these with `retries:` and `timeout:`, or bring your own `session:`.

## Linux

On Linux, URLSession waits for a whole answer before handing it over, so `chatStream` gives the answer when it's finished and `events()` never yields. Send requests with [AsyncHTTPClient](https://github.com/swift-server/swift-openapi-async-http-client) instead, and both stream:

```swift
import OpenAPIAsyncHTTPClient

let toskar = try Toskar(transport: AsyncHTTPClientTransport())
```

Pairing as a device, and reaching a computer from anywhere, come next.
