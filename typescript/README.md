# toskar

The official TypeScript and JavaScript SDK for [Toskar](https://toskar.ai). It works in Node 18 and later, Deno, Bun, and browsers.

```bash
npm install toskar
```

## Quick start

```ts
import { Toskar } from 'toskar'

// This computer's Toskar Core, at http://127.0.0.1:7331, needs no key.
// Elsewhere: new Toskar({ baseUrl: 'http://studio.local:7331', apiKey: 'tk_…' }),
// or set TOSKAR_URL and TOSKAR_API_KEY.
const toskar = new Toskar()

// Stream an answer as it's written.
for await (const event of toskar.chatStream({ message: 'Plan a three-day trip to Juneau' })) {
  if (event.type === 'token') process.stdout.write(event.content)
}

// Or wait for the whole answer.
const answer = await toskar.chat({ message: 'Summarize this in one line: …' })
console.log(answer.content)
```

## Every route, typed

`toskar.api` reaches every route of the API, with request and answer types from Toskar Core's spec. `unwrap` returns the data, or throws the error:

```ts
import { Toskar, unwrap, type Schemas } from 'toskar'

const toskar = new Toskar()
const models: Schemas['Model'][] = unwrap(await toskar.api.GET('/api/v1/models'))
const chat = unwrap(await toskar.api.POST('/api/v1/conversations', { body: { title: 'Trip' } }))
const messages = unwrap(await toskar.api.GET('/api/v1/conversations/{id}/messages', { params: { path: { id: chat.id } } }))
```

## Errors

Toskar answers errors with a stable code. The SDK throws them as `ToskarError`:

```ts
import { ErrorCodes, ToskarError } from 'toskar'

try {
  await toskar.chat({ message: 'Hi' })
} catch (err) {
  if (err instanceof ToskarError && err.code === ErrorCodes.NO_MODEL_INSTALLED) {
    // Install one: POST /api/v1/models/{id}/install
  }
}
```

A streamed answer that fails throws too, with the code Toskar sent, and one that stops before it finishes throws `CONNECTION_LOST`.

## Events

```ts
const stop = new AbortController()
for await (const event of toskar.events({ signal: stop.signal })) {
  console.log(event.type) // such as model.download.progress or automation.completed
}
```

## Retries and timeouts

Safe requests (GET, HEAD, OPTIONS) that fail to connect, or that Toskar answers with 502, 503, or 504, are retried twice with backoff. A chat is never retried, since it could answer twice. Each request waits 60 seconds for its answer to start, and a streamed answer then runs for as long as it takes. Change these with `retries` and `timeoutMs`.

## Not yet

- Pairing with a short code from Connect a device.
- Pinning a computer's certificate over its local-network HTTPS.
- Reaching it from anywhere through the relay, as the Toskar apps do.

They're coming next (toskar-core#666). For now, use an API key on the home network, or this computer's loopback.
