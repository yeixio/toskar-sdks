# Python reference

*Generated from the SDK's docstrings by `python/scripts/reference.py`.*

The official Python SDK for Toskar: local AI across your own computers.

```python
from toskar import Toskar

toskar = Toskar()
for event in toskar.chat_stream("Plan a three-day trip to Juneau"):
    if event.type == "token":
        print(event.content, end="", flush=True)
```

The routes themselves, with every field: [toskar.ai/developers/api](https://toskar.ai/developers/api).

## Contents

- **Connecting:** [Toskar](#toskar), [AsyncToskar](#asynctoskar)
- **Streamed answers:** [ChatStreamEvent](#chatstreamevent), [Token](#token), [Done](#done)
- **Errors:** [ToskarError](#toskarerror), [ErrorCodes](#errorcodes)
- **Pairing and reaching a computer from anywhere:** [pair](#pair), [apair](#apair), [Device](#device), [Route](#route), [TOSKAR_RELAY](#toskar_relay), [NotConfirmed](#notconfirmed), [PinMismatch](#pinmismatch), [Unreachable](#unreachable), [pin_of](#pin_of), [short_pin](#short_pin), [route_id](#route_id), [open_record](#open_record), [Record](#record), [RecordError](#recorderror)
- **Finding computers on the network:** [discover](#discover), [Computer](#computer)
- **Server-sent events:** [read_events](#read_events), [aread_events](#aread_events), [ServerSentEvent](#serversentevent)
- **The contract:** [CONTRACT_VERSION](#contract_version)
- [Every route on `toskar.api`](api.md)
- [Error codes](errors.md)

## Connecting

### Toskar

A connection to Toskar Core.

`api` reaches every route, typed from Core's API spec:

```python
models = toskar.api.list_models()
```

and the methods here cover what's easier by hand: chat, streamed chat,
and the events stream.

By default it reaches this computer's Toskar Core, at
http://127.0.0.1:7331, which needs no key; elsewhere, pass `base_url`
and `api_key`, or set TOSKAR_URL and TOSKAR_API_KEY.

```python
Toskar(base_url: str | None = None, *, api_key: str | None = None, retries: int = 2, timeout: float | None = 60.0, headers: dict[str, str] | None = None, http_client: httpx.Client | None = None, device: Device | None = None) -> None
```

#### Toskar.path

How a paired device reaches its computer now: home, direct, or
relay; None before its first request, or without a device.

#### Toskar.reconnect

```python
def reconnect() -> Path | None
```

Chooses the way in again, as after the network changed.

#### Toskar.close

```python
def close() -> None
```

#### Toskar.chat

```python
def chat(message: str, **fields: Any) -> models.ChatAnswer
```

Asks once and waits for the whole answer. `fields` are the rest of
POST /api/v1/chat's body, such as conversation_id or profile_id.

#### Toskar.chat_stream

```python
def chat_stream(message: str, **fields: Any) -> Iterator[ChatStreamEvent]
```

Asks and yields the answer as it's written: Token events, then Done
once it's finished and saved. A failure is raised as a ToskarError,
with its code, such as NO_MODEL_INSTALLED:

```python
for event in toskar.chat_stream("Hi"):
    if event.type == "token":
        print(event.content, end="", flush=True)
```

#### Toskar.events

```python
def events() -> Iterator[models.Event]
```

Yields what happens on Toskar as it happens, such as models loading
and automations running, until you stop iterating.

#### Toskar.version

```python
def version() -> models.VersionResponse
```

Core's version and its client contract.

#### Toskar.api

Every route of the API, one method each, such as `toskar.api.list_models()`: [api.md](api.md).

### AsyncToskar

A connection to Toskar Core, for asyncio: Toskar's methods, awaited.

async with AsyncToskar() as toskar:

```python
async for event in toskar.chat_stream("Hi"):
    ...
```

```python
AsyncToskar(base_url: str | None = None, *, api_key: str | None = None, retries: int = 2, timeout: float | None = 60.0, headers: dict[str, str] | None = None, http_client: httpx.AsyncClient | None = None, device: Device | None = None) -> None
```

#### AsyncToskar.path

How a paired device reaches its computer now.

#### AsyncToskar.reconnect

```python
async def reconnect() -> Path | None
```

Chooses the way in again, as after the network changed.

#### AsyncToskar.aclose

```python
async def aclose() -> None
```

#### AsyncToskar.chat

```python
async def chat(message: str, **fields: Any) -> models.ChatAnswer
```

Asks once and waits for the whole answer.

#### AsyncToskar.chat_stream

```python
async def chat_stream(message: str, **fields: Any) -> AsyncIterator[ChatStreamEvent]
```

Asks and yields the answer as it's written: Token events, then Done.

#### AsyncToskar.events

```python
async def events() -> AsyncIterator[models.Event]
```

Yields what happens on Toskar as it happens, until you stop iterating.

#### AsyncToskar.version

```python
async def version() -> models.VersionResponse
```

Core's version and its client contract.

#### AsyncToskar.api

Every route of the API, one method each, such as `toskar.api.list_models()`: [api.md](api.md).

## Streamed answers

### ChatStreamEvent

```python
ChatStreamEvent = toskar._client.Token | toskar._client.Done
```



### Token

The next piece of a streamed answer.

| Field | Type | |
| --- | --- | --- |
| `content` | `str` |  |
| `type` | `Literal['token']` |  |

### Done

A streamed answer finished and was saved.

| Field | Type | |
| --- | --- | --- |
| `metrics` | `models.GenerationMetrics \| None` |  |
| `type` | `Literal['done']` |  |

## Errors

### ToskarError

*Subclass of Exception.*

An error from Toskar Core: {"error": {"code", "message", "details"}}.

`code` is stable, such as `NO_MODEL_INSTALLED` (see ErrorCodes);
`message` is English text for logs; `details` has the values the
message needs.

### ErrorCodes

The codes Toskar Core answers errors with. A newer Core may answer with one this list doesn't have yet.

Every code, with what it means: [errors.md](errors.md).

## Pairing and reaching a computer from anywhere

### pair

```python
def pair(address: str, code: str, device_name: str, confirm: Callable[[str], bool] | None = None, *, timeout: float = 30.0) -> Device
```

Pairs with the computer at `address` (host:port) using the code
Connect a device shows on it. `confirm` gets the short pin to show the
person, and says whether the computer shows the same. The device must be
on the computer's local network.

### apair

```python
async def apair(address: str, code: str, device_name: str, confirm: Callable[[str], bool] | None = None, *, timeout: float = 30.0) -> Device
```

pair(), for asyncio.

### Device

What a paired device keeps, to connect again. Save it as a password is
saved: `api_key` and the route's secret and token are secrets.

| Field | Type | |
| --- | --- | --- |
| `address` | `str` | The computer's host:port at home. |
| `api_key` | `str` |  |
| `pin` | `str` | `sha256:<hex>` of the computer's certificate. It only ever comes from pairing. |
| `route` | `Route \| None` |  |

#### Device.to_dict

```python
def to_dict() -> dict[str, Any]
```

### Route

How to find the computer away from home, when it has access from anywhere.

| Field | Type | |
| --- | --- | --- |
| `secret` | `str` | The route secret, base64url without padding. |
| `id` | `str` |  |
| `relay` | `str` | The relay the computer uses, such as relay.toskar.ai. |
| `token` | `str` | Lets the device look the computer up on Toskar's relay. |

### TOSKAR_RELAY

```python
TOSKAR_RELAY = 'relay.toskar.ai'
```

Toskar's own relay. It's asked only with a route token.

### NotConfirmed

*Subclass of ToskarError.*

Pairing the person stopped at the short pin.

### PinMismatch

*Subclass of ToskarError.*

The computer's certificate isn't the one paired with: stop, and pair
again to trust a new certificate.

### Unreachable

*Subclass of ToskarError.*

No way in answered, at home or away. `code` is NO_RECORD when there
was no address record: the computer may be off or asleep, or have no
access from anywhere.

### pin_of

```python
def pin_of(der: bytes) -> str
```

The pin of a certificate: `sha256:<hex>` of its DER.

### short_pin

```python
def short_pin(pin: str) -> str
```

How a pin is shown for the person to compare: its first 8 hex digits, as ABCD-1234.

### route_id

```python
def route_id(secret: str) -> str
```

The route ID a route secret names.

### open_record

```python
def open_record(blob: bytes, secret: str, pin: str, now: float | None = None, max_age: float = 3600) -> Record
```

Opens an address record as docs/connecting.md says, or raises
RecordError. Needs the `anywhere` extra: pip install "toskar[anywhere]".

### Record

What an address record says: the computer's ways in, and when it wrote them.

| Field | Type | |
| --- | --- | --- |
| `addresses` | `list[str]` |  |
| `at` | `int` |  |

### RecordError

*Subclass of Exception.*

An address record that must be refused: `reason` is sealed, pin, or stale.

## Finding computers on the network

### discover

```python
def discover(timeout: float = 3.0) -> list[Computer]
```

Browses the network for `timeout` seconds and returns the computers
running Toskar Core that answered, by name. Needs the `discovery`
extra: pip install "toskar[discovery]".

### Computer

A Toskar Core found on the network.

| Field | Type | |
| --- | --- | --- |
| `name` | `str` |  |
| `node_id` | `str` |  |
| `version` | `str` |  |
| `address` | `str` | The API's host:port, to pair with: the first of `addresses` that answers. |
| `on_network` | `bool` | False when the API answers only on that computer: say to turn on Connect a device there, rather than that it's unreachable. |
| `addresses` | `tuple[str, ...]` | Every host:port the computer advertised. A computer can advertise addresses this device can't reach, such as a container network's. |

## Server-sent events

### read_events

```python
def read_events(lines: Iterable[str]) -> Iterator[ServerSentEvent]
```

Reads server-sent events from a stream's lines, as they arrive.

### aread_events

```python
async def aread_events(lines: AsyncIterator[str]) -> AsyncIterator[ServerSentEvent]
```

Reads server-sent events from a stream's lines, for asyncio.

### ServerSentEvent

One server-sent event: its name ("message" without one) and its data.

| Field | Type | |
| --- | --- | --- |
| `event` | `str` |  |
| `data` | `str` |  |

## The contract

### CONTRACT_VERSION

```python
CONTRACT_VERSION = '1.59'
```

The client contract this SDK was built for.
