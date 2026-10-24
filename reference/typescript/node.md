# node

## Classes

### RecordError

An address record that must be refused: reason is sealed, pin, or stale.

#### Extends

- `Error`

#### Constructors

##### Constructor

```ts
new RecordError(reason): RecordError;
```

###### Parameters

| Parameter | Type |
| ------ | ------ |
| `reason` | `"sealed"` \| `"pin"` \| `"stale"` |

###### Returns

[`RecordError`](#recorderror)

###### Overrides

```ts
Error.constructor
```

#### Properties

##### reason

```ts
readonly reason: "sealed" | "pin" | "stale";
```

***

### Toskar

Toskar, with pairing: as toskar's Toskar, and with { device } it connects
as a paired device, pinned, at home or away.

    const device = await pair('192.168.1.20:7331', '123456', 'Kitchen tablet', confirm)
    const toskar = new Toskar({ device })

#### Extends

- [`Toskar`](index.md#toskar)

#### Constructors

##### Constructor

```ts
new Toskar(options?): Toskar;
```

###### Parameters

| Parameter | Type |
| ------ | ------ |
| `options` | [`ToskarOptions`](index.md#toskaroptions) & `object` |

###### Returns

[`Toskar`](#toskar)

###### Overrides

[`Toskar`](index.md#toskar).[`constructor`](index.md#constructor)

#### Properties

##### api

```ts
readonly api: Client<paths>;
```

Every route of the API, typed. Answers are {data} or {error}; see unwrap.

###### Inherited from

[`Toskar`](index.md#toskar).[`api`](index.md#api)

##### baseUrl

```ts
readonly baseUrl: string;
```

###### Inherited from

[`Toskar`](index.md#toskar).[`baseUrl`](index.md#baseurl)

#### Accessors

##### path

###### Get Signature

```ts
get path(): Path | undefined;
```

How a paired device reaches its computer now: home, direct, or relay; undefined before its first request.

###### Returns

[`Path`](#path-1) \| `undefined`

#### Methods

##### chat()

```ts
chat(request, init?): Promise<{
  content: string;
  metrics?: {
     cached_tokens?: number;
     completion_tokens: number;
     eval_ms: number;
     eval_tok_per_sec: number;
     prompt_ms: number;
     prompt_tok_per_sec: number;
     prompt_tokens: number;
     total_ms: number;
     total_tokens: number;
     ttft_ms: number;
  };
}>;
```

Asks once and waits for the whole answer.

###### Parameters

| Parameter | Type |
| ------ | ------ |
| `request` | [`ChatRequest`](index.md#chatrequest) |
| `init` | \{ `signal?`: `AbortSignal`; \} |
| `init.signal?` | `AbortSignal` |

###### Returns

`Promise`\<\{
  `content`: `string`;
  `metrics?`: \{
     `cached_tokens?`: `number`;
     `completion_tokens`: `number`;
     `eval_ms`: `number`;
     `eval_tok_per_sec`: `number`;
     `prompt_ms`: `number`;
     `prompt_tok_per_sec`: `number`;
     `prompt_tokens`: `number`;
     `total_ms`: `number`;
     `total_tokens`: `number`;
     `ttft_ms`: `number`;
  \};
\}\>

###### Inherited from

[`Toskar`](index.md#toskar).[`chat`](index.md#chat)

##### chatStream()

```ts
chatStream(request, init?): AsyncGenerator<ChatStreamEvent>;
```

Asks and yields the answer as it's written: token events, then done
once it's finished and saved. A failure is thrown as a ToskarError,
with its code, such as NO_MODEL_INSTALLED.

    for await (const e of toskar.chatStream({ message: 'Hi' })) {
      if (e.type === 'token') process.stdout.write(e.content)
    }

###### Parameters

| Parameter | Type |
| ------ | ------ |
| `request` | [`ChatRequest`](index.md#chatrequest) |
| `init` | \{ `signal?`: `AbortSignal`; \} |
| `init.signal?` | `AbortSignal` |

###### Returns

`AsyncGenerator`\<[`ChatStreamEvent`](index.md#chatstreamevent)\>

###### Inherited from

[`Toskar`](index.md#toskar).[`chatStream`](index.md#chatstream)

##### events()

```ts
events(init?): AsyncGenerator<{
  contract: string;
  id: string;
  node_id?: string;
  payload?: {
   [key: string]: unknown;
  };
  task_id?: string;
  timestamp: string;
  type: string;
}>;
```

Yields what happens on Toskar as it happens, such as models loading and
automations running, until the signal aborts.

###### Parameters

| Parameter | Type |
| ------ | ------ |
| `init` | \{ `signal?`: `AbortSignal`; \} |
| `init.signal?` | `AbortSignal` |

###### Returns

`AsyncGenerator`\<\{
  `contract`: `string`;
  `id`: `string`;
  `node_id?`: `string`;
  `payload?`: \{
   \[`key`: `string`\]: `unknown`;
  \};
  `task_id?`: `string`;
  `timestamp`: `string`;
  `type`: `string`;
\}\>

###### Inherited from

[`Toskar`](index.md#toskar).[`events`](index.md#events)

##### reconnect()

```ts
reconnect(): Promise<Path | undefined>;
```

Chooses the way in again, as after the network changed.

###### Returns

`Promise`\<[`Path`](#path-1) \| `undefined`\>

##### version()

```ts
version(): Promise<{
  build_date: string;
  commit: string;
  contract: {
     major: number;
     version: string;
  };
  license: string;
  product: string;
  source: string;
  version: string;
}>;
```

Core's version and its client contract.

###### Returns

`Promise`\<\{
  `build_date`: `string`;
  `commit`: `string`;
  `contract`: \{
     `major`: `number`;
     `version`: `string`;
  \};
  `license`: `string`;
  `product`: `string`;
  `source`: `string`;
  `version`: `string`;
\}\>

###### Inherited from

[`Toskar`](index.md#toskar).[`version`](index.md#version)

## Type Aliases

### AddressRecord

```ts
type AddressRecord = object;
```

What an address record says: the computer's ways in, and when it wrote them.

#### Properties

##### addresses

```ts
addresses: string[];
```

##### at

```ts
at: number;
```

***

### Computer

```ts
type Computer = object;
```

A Toskar Core found on the network.

#### Properties

##### address

```ts
address: string;
```

The API's host:port, to pair with: the first of addresses that answers.

##### addresses

```ts
addresses: string[];
```

Every host:port the computer advertised. A computer can advertise addresses this device can't reach, such as a container network's.

##### name

```ts
name: string;
```

##### nodeId

```ts
nodeId: string;
```

##### onNetwork

```ts
onNetwork: boolean;
```

False when the API answers only on that computer: say to turn on Connect a device there, rather than that it's unreachable.

##### version

```ts
version: string;
```

***

### Device

```ts
type Device = object;
```

What a paired device keeps, to connect again. Save it as a password is
saved: apiKey and the route's secret and token are secrets.

#### Properties

##### address

```ts
address: string;
```

The computer's host:port at home.

##### apiKey

```ts
apiKey: string;
```

##### pin

```ts
pin: string;
```

sha256:<hex> of the computer's certificate. It only ever comes from pairing.

##### route?

```ts
optional route?: Route;
```

***

### Path

```ts
type Path = "home" | "direct" | "relay";
```

How a paired device reaches its computer.

***

### Route

```ts
type Route = object;
```

How to find the computer away from home, when it has access from anywhere.

#### Properties

##### id

```ts
id: string;
```

##### relay

```ts
relay: string;
```

The relay the computer uses, such as relay.toskar.ai.

##### secret

```ts
secret: string;
```

The route secret, base64url without padding.

##### token?

```ts
optional token?: string;
```

Lets the device look the computer up on Toskar's relay.

## Variables

### TOSKAR\_RELAY

```ts
const TOSKAR_RELAY: "relay.toskar.ai" = 'relay.toskar.ai';
```

Toskar's own relay. It's asked only with a route token.

## Functions

### computerOf()

```ts
function computerOf(
   instance, 
   addresses, 
   txt
): Computer | null;
```

A computer from an mDNS answer, or null when it doesn't say where its API is.

#### Parameters

| Parameter | Type |
| ------ | ------ |
| `instance` | `string` |
| `addresses` | `string`[] |
| `txt` | `Record`\<`string`, `unknown`\> |

#### Returns

[`Computer`](#computer) \| `null`

***

### discover()

```ts
function discover(timeoutMs?): Promise<Computer[]>;
```

Browses the network for computers running Toskar Core (_localai._tcp)
and returns those that answered within timeoutMs, by name. Needs the
optional bonjour-service package.

#### Parameters

| Parameter | Type | Default value |
| ------ | ------ | ------ |
| `timeoutMs` | `number` | `3_000` |

#### Returns

`Promise`\<[`Computer`](#computer)[]\>

***

### openRecord()

```ts
function openRecord(
   blob, 
   secret, 
   pin, 
   now?, 
   maxAge?
): AddressRecord;
```

Opens an address record as docs/connecting.md says, or throws a RecordError.

#### Parameters

| Parameter | Type | Default value |
| ------ | ------ | ------ |
| `blob` | `Uint8Array` | `undefined` |
| `secret` | `string` | `undefined` |
| `pin` | `string` | `undefined` |
| `now` | `number` | `...` |
| `maxAge` | `number` | `RECORD_MAX_AGE` |

#### Returns

[`AddressRecord`](#addressrecord)

***

### pair()

```ts
function pair(
   address, 
   code, 
   deviceName, 
   confirm?
): Promise<Device>;
```

Pairs with the computer at address (host:port, as found or typed) using
the code Connect a device shows on it. confirm gets the short pin to show
the person, and says whether the computer shows the same. The device must
be on the computer's local network.

#### Parameters

| Parameter | Type |
| ------ | ------ |
| `address` | `string` |
| `code` | `string` |
| `deviceName` | `string` |
| `confirm?` | (`shortPin`) => `boolean` \| `Promise`\<`boolean`\> |

#### Returns

`Promise`\<[`Device`](#device)\>

***

### pinnedDispatcher()

```ts
function pinnedDispatcher(pin): Dispatcher;
```

An undici dispatcher that trusts exactly the certificate with pin: names,
dates, and signers aren't checked, and the pin is checked once the TLS
handshake is done, before any request is sent.

#### Parameters

| Parameter | Type |
| ------ | ------ |
| `pin` | `string` |

#### Returns

`Dispatcher`

***

### pinOf()

```ts
function pinOf(der): string;
```

The pin of a certificate: sha256:<hex> of its DER.

#### Parameters

| Parameter | Type |
| ------ | ------ |
| `der` | `Uint8Array` |

#### Returns

`string`

***

### reachable()

```ts
function reachable(addresses): Promise<string>;
```

The first of addresses that takes a TCP connection, tried together; the first, when none does.

#### Parameters

| Parameter | Type |
| ------ | ------ |
| `addresses` | `string`[] |

#### Returns

`Promise`\<`string`\>

***

### routeId()

```ts
function routeId(secret): string;
```

The route ID a route secret names.

#### Parameters

| Parameter | Type |
| ------ | ------ |
| `secret` | `string` |

#### Returns

`string`

***

### shortPin()

```ts
function shortPin(pin): string;
```

How a pin is shown for the person to compare: its first 8 hex digits, as ABCD-1234.

#### Parameters

| Parameter | Type |
| ------ | ------ |
| `pin` | `string` |

#### Returns

`string`

## References

### ChatRequest

Re-exports [ChatRequest](index.md#chatrequest)

***

### ChatStreamEvent

Re-exports [ChatStreamEvent](index.md#chatstreamevent)

***

### CONTRACT\_VERSION

Re-exports [CONTRACT_VERSION](index.md#contract_version)

***

### ErrorCode

Re-exports [ErrorCode](index.md#errorcode)

***

### ErrorCodes

Re-exports [ErrorCodes](index.md#errorcodes)

***

### readEvents

Re-exports [readEvents](index.md#readevents)

***

### Schemas

Re-exports [Schemas](index.md#schemas)

***

### ServerSentEvent

Re-exports [ServerSentEvent](index.md#serversentevent)

***

### ToskarError

Re-exports [ToskarError](index.md#toskarerror)

***

### ToskarOptions

Re-exports [ToskarOptions](index.md#toskaroptions)

***

### unwrap

Re-exports [unwrap](index.md#unwrap)
