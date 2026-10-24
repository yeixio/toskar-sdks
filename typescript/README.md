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

## Pairing, as the Toskar apps do (Node)

An app can pair as a device, with the code **Connect a device** shows on the computer, instead of using an API key. It then reaches its computer at home and, when the computer has access from anywhere, directly or through its relay, always pinned to the computer's own certificate ([how it works](https://github.com/yeixio/toskar-core/blob/main/docs/connecting.md)). It's in `toskar/node`, for Node 18 and later: a browser can't check a certificate itself, and Bun and Deno don't take Node's TLS hooks yet. Elsewhere, use an API key.

```ts
import { pair, Toskar, unwrap, type Device } from 'toskar/node'

// On the computer's network, with the code it shows:
const device: Device = await pair('192.168.1.20:7331', '123456', 'Kitchen tablet', async (short) => {
  // Show short, such as 9B80-D9D9, and ask whether the computer shows the same.
  return askThePerson(short)
})
// Save device, as a password is saved: its key and route are secrets.

const toskar = new Toskar({ device })
const models = unwrap(await toskar.api.GET('/api/v1/models'))
console.log(toskar.path) // home, direct, or relay
```

Every connection checks the computer's certificate before anything is sent. A different certificate throws `PIN_MISMATCH`, and is never accepted on its own: pair again to trust a new one. Away from home, the client opens the computer's sealed address record from its relay, tries its direct ways in at once and the relay a second later, and keeps the first that answers. `toskar.reconnect()` chooses again, as after the network changes. A device key reaches the routes a device needs. Scripts and servers that need the rest use a key from API Access.

## Find computers on the network

Computers running Toskar announce themselves on the home network (mDNS, `_localai._tcp`). In Node, `discover` lists them, so a person can pick one instead of typing an address. It uses the optional dependency `bonjour-service`; browsers can't browse mDNS.

```ts
import { discover } from 'toskar/node'

for (const c of await discover(3000)) console.log(c.name, c.address)
```

Pair with `c.address`. When `c.onNetwork` is false, the computer answers only on itself: tell the person to turn on Connect a device there, rather than that it's unreachable. A computer can advertise addresses this device can't reach, such as a container network's; `address` is the first one that answers, and `addresses` has them all.
