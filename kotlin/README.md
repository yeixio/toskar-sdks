# Toskar for Kotlin and Java

The official Kotlin and Java SDK for [Toskar](https://toskar.ai). It needs Java 11 or later, or Android 8 (API 26) or later, and works the same from Kotlin and from Java.

<!-- snippet: skip -->
```kotlin
// build.gradle.kts
dependencies {
    implementation("ai.toskar:toskar:0.3.0")
}
```

It isn't on Maven Central yet. Until it is, build it from this repository with `cd kotlin && ./gradlew publishToMavenLocal`, and add `mavenLocal()` to your repositories.

## Quick start

<!-- snippet: run -->
```kotlin
import ai.toskar.ChatEvent
import ai.toskar.Toskar
import ai.toskar.api.ChatRequest

// This computer's Toskar Core, at http://127.0.0.1:7331, needs no key.
// Elsewhere: Toskar("http://studio.local:7331", "tk_…"),
// or set TOSKAR_URL and TOSKAR_API_KEY.
val toskar = Toskar()

// Stream an answer as it's written.
toskar.chatStream(ChatRequest(message = "Plan a three-day trip to Juneau")).use { events ->
    for (event in events) {
        if (event is ChatEvent.Token) print(event.text)
    }
}

// Or wait for the whole answer.
val answer = toskar.chat(ChatRequest(message = "Summarize this in one line: …"))
println(answer.content)
toskar.close()
```

From Java:

<!-- snippet: run -->
```java
import ai.toskar.ChatEvent;
import ai.toskar.EventStream;
import ai.toskar.Toskar;
import ai.toskar.api.ChatRequest;

try (Toskar toskar = new Toskar()) {
    try (EventStream<ChatEvent> events = toskar.chatStream(new ChatRequest("Plan a three-day trip to Juneau"))) {
        for (ChatEvent event : events) {
            if (event instanceof ChatEvent.Token) {
                System.out.print(((ChatEvent.Token) event).getText());
            }
        }
    }
    System.out.println(toskar.chat(new ChatRequest("Summarize this in one line: …")).getContent());
}
```

Every call waits for its answer, so on Android, or anywhere a thread mustn't block, call it from a background thread or a coroutine on `Dispatchers.IO`.

## Every route, typed

`toskar.api` is generated from Toskar Core's API spec, so every operation is a method named after it, and every answer is a data class:

```kotlin
val models = toskar.api.listModels() // List<Model>
val chat = toskar.api.createConversation(CreateConversationRequest(title = "Trip"))
val messages = toskar.api.listConversationMessages(chat.id)
```

Fields are camelCase (`modelId` for `model_id`). A field that Core may leave out is nullable, and a newer Core's new fields and values are passed over, not failed on. Values that only a few are known for, such as `effort`, are strings, so a new one doesn't break your build.

## Errors

Toskar answers errors with a stable code. Any call that gets one throws a `ToskarException`, with the code, a message for logs, and the details:

```kotlin
try {
    toskar.chat(ChatRequest(message = "Hi"))
} catch (e: ToskarException) {
    if (e.code == ErrorCodes.NO_MODEL_INSTALLED) {
        toskar.api.installModel("qwen2.5-7b-q4")
    }
}
```

A streamed answer that fails throws its error, with the code Toskar sent. One that stops before it finishes throws `CONNECTION_LOST`, and a computer that doesn't answer throws `CONNECTION_FAILED`, with the network error as its cause. `ToskarException` is unchecked, so Java needs no `throws`.

## Events

```kotlin
toskar.events().use { events -> // until you close it
    for (event in events) {
        println(event.type) // such as model.download.progress or automation.completed
    }
}
```

## Retries and timeouts

Safe requests (GET, HEAD, OPTIONS) that fail to connect, or that Toskar answers with 502, 503, or 504, are retried twice with backoff. A chat is never retried, since it could answer twice. Each request waits 60 seconds for its answer to start, and a streamed answer then runs for as long as it takes. Change these with `retries` and `timeout`, or bring your own `httpClient` ([OkHttp](https://square.github.io/okhttp/)):

```kotlin
val patient = Toskar(retries = 5, timeout = java.time.Duration.ofMinutes(5))
```

## Pairing, as the Toskar apps do

An app can pair as a device, with the code **Connect a device** shows on the computer, instead of using an API key. It then reaches its computer at home and, when the computer has access from anywhere, directly or through its relay, always pinned to the computer's own certificate ([how it works](https://github.com/yeixio/toskar-core/blob/main/docs/connecting.md)).

```kotlin
// On the computer's network, with the code it shows:
val device = Toskar.pair("192.168.1.20:7331", "123456", "Kitchen tablet") { short ->
    // Show short, such as 9B80-D9D9, and ask whether the computer shows the same.
    askThePerson(short)
}
// Save device as a password is saved: its key and route are secrets. It's
// @Serializable, in the same JSON as the other SDKs':
val saved = kotlinx.serialization.json.Json.encodeToString(Device.serializer(), device)

val paired = Toskar(device)
val models = paired.api.listModels()
println(paired.path) // HOME, DIRECT, or RELAY
```

Every connection checks the computer's certificate before anything is sent. A different certificate throws `PIN_MISMATCH`, and is never accepted on its own: pair again to trust a new one. Away from home, the client opens the computer's sealed address record from its relay, tries its direct ways in at once and the relay a second later, and keeps the first that answers. `paired.reconnect()` chooses again, as after the network changes. A device key reaches the routes a device needs. Scripts and servers that need the rest use a key from API Access.

Address records signed with an Ed25519 certificate need Java 15 or later (Android 13); Toskar Core's own certificates are ECDSA.

## Find computers on the network

Computers running Toskar announce themselves on the home network (mDNS, `_localai._tcp`). `Toskar.find` lists them, so a person can pick one instead of typing an address. It needs no other library:

```kotlin
for (computer in Toskar.find(java.time.Duration.ofSeconds(3))) {
    println("${computer.name} ${computer.address}")
}
```

Pair with `computer.address`. When `computer.onNetwork` is false, the computer answers only on itself: tell the person to turn on Connect a device there, rather than that it's unreachable. A computer can have addresses this device can't reach, such as a container network's; `address` is the first one that answers, and `addresses` has them all.

On Android, hold a `WifiManager.MulticastLock` while it looks, and ask for the `CHANGE_WIFI_MULTICAST_STATE` permission; without the lock, the system drops the answers.
