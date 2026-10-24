# toskar

The official Python SDK for [Toskar](https://toskar.ai), sync and async. It works on Python 3.10 and later.

```bash
pip install toskar
```

Every class, function, and type: [the reference](../reference/python/README.md).

## Quick start

```python
from toskar import Toskar

# This computer's Toskar Core, at http://127.0.0.1:7331, needs no key.
# Elsewhere: Toskar("http://studio.local:7331", api_key="tk_…"),
# or set TOSKAR_URL and TOSKAR_API_KEY.
toskar = Toskar()

# Stream an answer as it's written.
for event in toskar.chat_stream("Plan a three-day trip to Juneau"):
    if event.type == "token":
        print(event.content, end="", flush=True)

# Or wait for the whole answer.
answer = toskar.chat("Summarize this in one line: …")
print(answer.content)
```

For asyncio, use `AsyncToskar`, which has the same methods, awaited:

```python
import asyncio
from toskar import AsyncToskar

async def main():
    async with AsyncToskar() as toskar:
        async for event in toskar.chat_stream("Hi"):
            if event.type == "token":
                print(event.content, end="", flush=True)

asyncio.run(main())
```

## Every route, typed

`toskar.api` has a method for each operation of the API, named after its `operationId`. Answers are Pydantic models from Toskar Core's spec:

```python
models = toskar.api.list_models()               # list[models.Model]
chat = toskar.api.create_conversation(body={"title": "Trip"})
messages = toskar.api.list_conversation_messages(chat.id)  # list[models.Message]
```

The models keep fields a newer Toskar Core adds, and accept values for documented fields that a newer Core adds too.

## Errors

Toskar answers errors with a stable code. The SDK raises them as `ToskarError`:

```python
from toskar import ErrorCodes, ToskarError

try:
    toskar.chat("Hi")
except ToskarError as err:
    if err.code == ErrorCodes.NO_MODEL_INSTALLED:
        ...  # Install one: toskar.api.install_model("qwen2.5-7b-q4")
```

A streamed answer that fails raises too, with the code Toskar sent. One that stops before it finishes raises `CONNECTION_LOST`.

## Events

```python
for event in toskar.events():
    print(event.type)  # such as model.download.progress or automation.completed
```

## Retries and timeouts

Safe requests (GET, HEAD, OPTIONS) that fail to connect, or that Toskar answers with 502, 503, or 504, are retried twice with backoff. A chat is never retried, since it could answer twice. Each request waits 60 seconds for its answer, and a streamed answer then runs for as long as it takes. Change these with `retries` and `timeout`.

## Pairing, as the Toskar apps do

An app can pair as a device, with the code **Connect a device** shows on the computer, instead of using an API key. It then reaches its computer at home and, when the computer has access from anywhere, directly or through its relay, always pinned to the computer's own certificate ([how it works](https://github.com/yeixio/toskar-core/blob/main/docs/connecting.md)).

```bash
pip install "toskar[anywhere]"   # cryptography, to open the computer's address record away from home
```

```python
from toskar import Device, Toskar, pair

# On the computer's network, with the code it shows:
device = pair("192.168.1.20:7331", "123456", "Kitchen tablet",
              confirm=lambda short: ask_the_person(short))  # such as 9B80-D9D9: does the computer show the same?
saved = device.to_dict()  # keep it as a password is kept: its key and route are secrets

toskar = Toskar(device=Device.from_dict(saved))
models = toskar.api.list_models()
print(toskar.path)  # home, direct, or relay
```

`apair` and `AsyncToskar(device=...)` do the same for asyncio. Every connection checks the computer's certificate in the TLS handshake, before anything is sent. A different certificate raises `PinMismatch`, and is never accepted on its own: pair again to trust a new one. Away from home, the client opens the computer's sealed address record from its relay, tries its direct ways in at once and the relay a second later, and keeps the first that answers. `toskar.reconnect()` chooses again, as after the network changes. A device key reaches the routes a device needs. Scripts and servers that need the rest use a key from API Access.

## Find computers on the network

Computers running Toskar announce themselves on the home network (mDNS, `_localai._tcp`). `discover` lists them, so a person can pick one instead of typing an address. It needs the `discovery` extra (zeroconf, LGPL-2.1, imported only when you call it):

```sh
pip install "toskar[discovery]"
```

```python
from toskar import discover

for c in discover(timeout=3.0):
    print(c.name, c.address)
```

Pair with `c.address`. When `c.on_network` is false, the computer answers only on itself: tell the person to turn on Connect a device there, rather than that it's unreachable. A computer can advertise addresses this device can't reach, such as a container network's; `address` is the first one that answers, and `addresses` has them all.
