# toskar

The official Python SDK for [Toskar](https://toskar.ai), sync and async. It works on Python 3.10 and later.

```bash
pip install toskar
```

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

## Not yet

- Pairing with a short code from Connect a device.
- Pinning a computer's certificate over its local-network HTTPS.
- Reaching it from anywhere through the relay, as the Toskar apps do.

They're coming next (toskar-core#666). For now, use an API key on the home network, or this computer's loopback.
