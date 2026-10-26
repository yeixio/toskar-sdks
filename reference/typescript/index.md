# index

## Classes

### Toskar

A connection to Toskar Core.

`api` reaches every route, typed from Core's API spec:

    const { data } = await toskar.api.GET('/api/v1/models')

and the methods here cover what's easier by hand: chat, streamed chat,
and the events stream.

#### Extended by

- [`Toskar`](node.md#toskar)

#### Constructors

##### Constructor

```ts
new Toskar(options?): Toskar;
```

###### Parameters

| Parameter | Type |
| ------ | ------ |
| `options` | [`ToskarOptions`](#toskaroptions) |

###### Returns

[`Toskar`](#toskar)

#### Properties

##### api

```ts
readonly api: Client<paths>;
```

Every route of the API, typed. Answers are {data} or {error}; see unwrap.

##### baseUrl

```ts
readonly baseUrl: string;
```

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
     finish_reason?: string;
     prompt_ms: number;
     prompt_tok_per_sec: number;
     prompt_tokens: number;
     reasoning_tokens?: number;
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
| `request` | [`ChatRequest`](#chatrequest) |
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
     `finish_reason?`: `string`;
     `prompt_ms`: `number`;
     `prompt_tok_per_sec`: `number`;
     `prompt_tokens`: `number`;
     `reasoning_tokens?`: `number`;
     `total_ms`: `number`;
     `total_tokens`: `number`;
     `ttft_ms`: `number`;
  \};
\}\>

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
| `request` | [`ChatRequest`](#chatrequest) |
| `init` | \{ `signal?`: `AbortSignal`; \} |
| `init.signal?` | `AbortSignal` |

###### Returns

`AsyncGenerator`\<[`ChatStreamEvent`](#chatstreamevent)\>

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

***

### ToskarError

An error from Toskar Core: {"error": {"code", "message", "details"}}.
`code` is stable, such as MODEL_NOT_INSTALLED (see ErrorCodes); `message`
is English text for logs; `details` has the values the message needs.

#### Extends

- `Error`

#### Constructors

##### Constructor

```ts
new ToskarError(
   status, 
   code, 
   message, 
   details?
): ToskarError;
```

###### Parameters

| Parameter | Type |
| ------ | ------ |
| `status` | `number` |
| `code` | [`ErrorCode`](#errorcode) |
| `message` | `string` |
| `details` | `Record`\<`string`, `unknown`\> |

###### Returns

[`ToskarError`](#toskarerror)

###### Overrides

```ts
Error.constructor
```

#### Properties

##### code

```ts
readonly code: ErrorCode;
```

##### details

```ts
readonly details: Record<string, unknown>;
```

##### status

```ts
readonly status: number;
```

#### Methods

##### from()

```ts
static from(status, body): ToskarError;
```

The error a response body describes, or a generic one for a body that isn't Toskar's.

###### Parameters

| Parameter | Type |
| ------ | ------ |
| `status` | `number` |
| `body` | `unknown` |

###### Returns

[`ToskarError`](#toskarerror)

## Type Aliases

### ChatRequest

```ts
type ChatRequest = Omit<NonNullable<paths["/api/v1/chat"]["post"]["requestBody"]>["content"]["application/json"], "stream">;
```

What POST /api/v1/chat takes, without `stream`, which chat and chatStream set.

***

### ChatStreamEvent

```ts
type ChatStreamEvent = 
  | {
  content: string;
  type: "token";
}
  | {
  metrics?: Schemas["GenerationMetrics"];
  type: "done";
};
```

One event of a streamed chat. A failure is thrown as a ToskarError instead.

***

### ErrorCode

```ts
type ErrorCode = 
  | typeof ErrorCodes[keyof typeof ErrorCodes]
  | string & object;
```

One of ErrorCodes, or a code from a newer Core.

***

### Schemas

```ts
type Schemas = components["schemas"];
```

The API's named types, such as Schemas['Model'] or Schemas['Message'].

***

### ServerSentEvent

```ts
type ServerSentEvent = object;
```

One server-sent event: its name ("message" without one) and its data.

#### Properties

##### data

```ts
data: string;
```

##### event

```ts
event: string;
```

***

### ToskarOptions

```ts
type ToskarOptions = object;
```

#### Properties

##### apiKey?

```ts
optional apiKey?: string;
```

An API key, for any address other than this computer's loopback. Default: TOSKAR_API_KEY.

##### baseUrl?

```ts
optional baseUrl?: string;
```

Where Toskar Core answers. Default: TOSKAR_URL, or http://127.0.0.1:7331, this computer.

##### fetch?

```ts
optional fetch?: typeof fetch;
```

A fetch to use in place of the global one.

##### headers?

```ts
optional headers?: Record<string, string>;
```

More headers for every request.

##### retries?

```ts
optional retries?: number;
```

Retries for safe requests that fail to connect or answer 502, 503, or 504. Default 2.

##### timeoutMs?

```ts
optional timeoutMs?: number;
```

Milliseconds to wait for an answer to start. Default 60000; 0 waits as long as it takes.

## Variables

### CONTRACT\_VERSION

```ts
const CONTRACT_VERSION: "1.59" = '1.59';
```

The client contract this SDK was built for.

***

### ErrorCodes

```ts
const ErrorCodes: object;
```

The stable error codes Toskar Core answers with. A newer Core may answer
with a code this list doesn't have yet.

#### Type Declaration

##### API\_KEY\_IN\_URL

```ts
readonly API_KEY_IN_URL: "API_KEY_IN_URL" = 'API_KEY_IN_URL';
```

Send the API key in the Authorization header, not in the address.

##### API\_KEY\_REQUIRED

```ts
readonly API_KEY_REQUIRED: "API_KEY_REQUIRED" = 'API_KEY_REQUIRED';
```

Create an API key or add a person before allowing access from other devices.

##### API\_KEYS\_LIST\_FAILED

```ts
readonly API_KEYS_LIST_FAILED: "API_KEYS_LIST_FAILED" = 'API_KEYS_LIST_FAILED';
```

{{detail}}

##### APPROVE\_FAILED

```ts
readonly APPROVE_FAILED: "APPROVE_FAILED" = 'APPROVE_FAILED';
```

{{detail}}

##### ATTEMPT\_NOT\_FOUND

```ts
readonly ATTEMPT_NOT_FOUND: "ATTEMPT_NOT_FOUND" = 'ATTEMPT_NOT_FOUND';
```

That attempt is gone.

##### AUTOMATION\_FAILED

```ts
readonly AUTOMATION_FAILED: "AUTOMATION_FAILED" = 'AUTOMATION_FAILED';
```

{{detail}}

##### AUTOMATION\_INTERRUPTED

```ts
readonly AUTOMATION_INTERRUPTED: "AUTOMATION_INTERRUPTED" = 'AUTOMATION_INTERRUPTED';
```

The run didn't finish because Toskar stopped while it ran. It runs again at its next time.

##### AUTOMATION\_INVALID

```ts
readonly AUTOMATION_INVALID: "AUTOMATION_INVALID" = 'AUTOMATION_INVALID';
```

{{detail}}

##### AUTOMATION\_NO\_RESULT

```ts
readonly AUTOMATION_NO_RESULT: "AUTOMATION_NO_RESULT" = 'AUTOMATION_NO_RESULT';
```

This run has no result to continue in chat.

##### AUTOMATION\_NOT\_WEBHOOK

```ts
readonly AUTOMATION_NOT_WEBHOOK: "AUTOMATION_NOT_WEBHOOK" = 'AUTOMATION_NOT_WEBHOOK';
```

This automation doesn't run from a webhook.

##### AUTOMATION\_PAUSED

```ts
readonly AUTOMATION_PAUSED: "AUTOMATION_PAUSED" = 'AUTOMATION_PAUSED';
```

This automation is paused.

##### AUTOMATION\_RUNNING

```ts
readonly AUTOMATION_RUNNING: "AUTOMATION_RUNNING" = 'AUTOMATION_RUNNING';
```

This automation is already running. Its result will appear here when it finishes.

##### AUTOMATION\_TIMEOUT

```ts
readonly AUTOMATION_TIMEOUT: "AUTOMATION_TIMEOUT" = 'AUTOMATION_TIMEOUT';
```

The run took longer than {{minutes}} minutes and was stopped. Try a faster model or a shorter prompt.

##### BAD\_REQUEST

```ts
readonly BAD_REQUEST: "BAD_REQUEST" = 'BAD_REQUEST';
```

{{detail}}

##### BAD\_RESPONSE

```ts
readonly BAD_RESPONSE: "BAD_RESPONSE" = 'BAD_RESPONSE';
```

The Toskar service sent an answer the app couldn't read (HTTP {{status}}). Try again; if it keeps happening, report it.

##### BENCHMARK\_LIST\_FAILED

```ts
readonly BENCHMARK_LIST_FAILED: "BENCHMARK_LIST_FAILED" = 'BENCHMARK_LIST_FAILED';
```

Couldn't list benchmarks.

##### BENCHMARK\_START\_FAILED

```ts
readonly BENCHMARK_START_FAILED: "BENCHMARK_START_FAILED" = 'BENCHMARK_START_FAILED';
```

{{detail}}

##### BENCHMARK\_UNSUPPORTED

```ts
readonly BENCHMARK_UNSUPPORTED: "BENCHMARK_UNSUPPORTED" = 'BENCHMARK_UNSUPPORTED';
```

Benchmarks aren't available on this computer.

##### BILLING\_UNAVAILABLE

```ts
readonly BILLING_UNAVAILABLE: "BILLING_UNAVAILABLE" = 'BILLING_UNAVAILABLE';
```

Billing couldn't be reached. Try again in a minute.

##### BROWSE\_FAILED

```ts
readonly BROWSE_FAILED: "BROWSE_FAILED" = 'BROWSE_FAILED';
```

{{detail}}

##### CACHE\_NOT\_FOUND

```ts
readonly CACHE_NOT_FOUND: "CACHE_NOT_FOUND" = 'CACHE_NOT_FOUND';
```

No cache has that name.

##### CAPABILITY\_OFF

```ts
readonly CAPABILITY_OFF: "CAPABILITY_OFF" = 'CAPABILITY_OFF';
```

This is turned off for your account. Ask {{admin}} or another Admin to turn it on.

##### CAPABILITY\_UNKNOWN

```ts
readonly CAPABILITY_UNKNOWN: "CAPABILITY_UNKNOWN" = 'CAPABILITY_UNKNOWN';
```

Toskar doesn't know that capability.

##### CHAT\_FAILED

```ts
readonly CHAT_FAILED: "CHAT_FAILED" = 'CHAT_FAILED';
```

{{detail}}

##### CLAIM\_FAILED

```ts
readonly CLAIM_FAILED: "CLAIM_FAILED" = 'CLAIM_FAILED';
```

{{detail}}

##### COMPACT\_FAILED

```ts
readonly COMPACT_FAILED: "COMPACT_FAILED" = 'COMPACT_FAILED';
```

The chat couldn't be compacted: {{detail}}

##### COMPUTER\_OFFLINE

```ts
readonly COMPUTER_OFFLINE: "COMPUTER_OFFLINE" = 'COMPUTER_OFFLINE';
```

The computer running this model is offline.

##### CONFIRM\_NAME

```ts
readonly CONFIRM_NAME: "CONFIRM_NAME" = 'CONFIRM_NAME';
```

To remove {{name}}, type their name to confirm.

##### CONFLICT

```ts
readonly CONFLICT: "CONFLICT" = 'CONFLICT';
```

{{detail}}

##### CONNECTION\_LOST

```ts
readonly CONNECTION_LOST: "CONNECTION_LOST" = 'CONNECTION_LOST';
```

The connection to the model was lost.

##### CONNECTOR\_FAILED

```ts
readonly CONNECTOR_FAILED: "CONNECTOR_FAILED" = 'CONNECTOR_FAILED';
```

{{detail}}

##### CONNECTOR\_NOT\_FOUND

```ts
readonly CONNECTOR_NOT_FOUND: "CONNECTOR_NOT_FOUND" = 'CONNECTOR_NOT_FOUND';
```

Toskar doesn't know that service.

##### CONNECTORS\_FAILED

```ts
readonly CONNECTORS_FAILED: "CONNECTORS_FAILED" = 'CONNECTORS_FAILED';
```

{{detail}}

##### CONTEXT\_TOO\_LONG

```ts
readonly CONTEXT_TOO_LONG: "CONTEXT_TOO_LONG" = 'CONTEXT_TOO_LONG';
```

This chat is too long for the model.

##### CONTRACT\_MISMATCH

```ts
readonly CONTRACT_MISMATCH: "CONTRACT_MISMATCH" = 'CONTRACT_MISMATCH';
```

{{detail}}

##### CONVERSATION\_CREATE\_FAILED

```ts
readonly CONVERSATION_CREATE_FAILED: "CONVERSATION_CREATE_FAILED" = 'CONVERSATION_CREATE_FAILED';
```

Couldn't start a new chat.

##### CONVERSATION\_DELETE\_FAILED

```ts
readonly CONVERSATION_DELETE_FAILED: "CONVERSATION_DELETE_FAILED" = 'CONVERSATION_DELETE_FAILED';
```

{{detail}}

##### CONVERSATION\_UPDATE\_FAILED

```ts
readonly CONVERSATION_UPDATE_FAILED: "CONVERSATION_UPDATE_FAILED" = 'CONVERSATION_UPDATE_FAILED';
```

{{detail}}

##### CONVERSATIONS\_LIST\_FAILED

```ts
readonly CONVERSATIONS_LIST_FAILED: "CONVERSATIONS_LIST_FAILED" = 'CONVERSATIONS_LIST_FAILED';
```

Couldn't list your chats.

##### CREATE\_FAILED

```ts
readonly CREATE_FAILED: "CREATE_FAILED" = 'CREATE_FAILED';
```

{{detail}}

##### CROSS\_SITE

```ts
readonly CROSS_SITE: "CROSS_SITE" = 'CROSS_SITE';
```

That change didn't come from Toskar's own pages, so it was refused.

##### DECIDE\_FAILED

```ts
readonly DECIDE_FAILED: "DECIDE_FAILED" = 'DECIDE_FAILED';
```

{{detail}}

##### DELETE\_FAILED

```ts
readonly DELETE_FAILED: "DELETE_FAILED" = 'DELETE_FAILED';
```

{{detail}}

##### DESTINATION\_NOT\_FOUND

```ts
readonly DESTINATION_NOT_FOUND: "DESTINATION_NOT_FOUND" = 'DESTINATION_NOT_FOUND';
```

That notification destination was removed.

##### DEVICE\_LIMIT

```ts
readonly DEVICE_LIMIT: "DEVICE_LIMIT" = 'DEVICE_LIMIT';
```

You have {{limit}} connected devices, the most you can. Disconnect one first.

##### DEVICE\_NOT\_ALLOWED

```ts
readonly DEVICE_NOT_ALLOWED: "DEVICE_NOT_ALLOWED" = 'DEVICE_NOT_ALLOWED';
```

A device's key can't do this. Use a key from API Access.

##### DEVICE\_NOT\_FOUND

```ts
readonly DEVICE_NOT_FOUND: "DEVICE_NOT_FOUND" = 'DEVICE_NOT_FOUND';
```

No device of yours has that id.

##### DEVICES\_FAILED

```ts
readonly DEVICES_FAILED: "DEVICES_FAILED" = 'DEVICES_FAILED';
```

Couldn't read or change your devices.

##### DIAGNOSTICS\_FAILED

```ts
readonly DIAGNOSTICS_FAILED: "DIAGNOSTICS_FAILED" = 'DIAGNOSTICS_FAILED';
```

Couldn't create a diagnostics bundle.

##### EGRESS\_FAILED

```ts
readonly EGRESS_FAILED: "EGRESS_FAILED" = 'EGRESS_FAILED';
```

{{detail}}

##### EMAIL\_INVALID

```ts
readonly EMAIL_INVALID: "EMAIL_INVALID" = 'EMAIL_INVALID';
```

That isn't an email address.

##### EMAIL\_TAKEN

```ts
readonly EMAIL_TAKEN: "EMAIL_TAKEN" = 'EMAIL_TAKEN';
```

Someone else has that email address.

##### EMPTY\_ANSWER

```ts
readonly EMPTY_ANSWER: "EMPTY_ANSWER" = 'EMPTY_ANSWER';
```

The model didn't write an answer. Try again, or choose another model.

##### EXAMPLES\_FULL

```ts
readonly EXAMPLES_FULL: "EXAMPLES_FULL" = 'EXAMPLES_FULL';
```

The profile has 20 example questions. Remove one to add this.

##### EXTERNAL\_BAD\_URL

```ts
readonly EXTERNAL_BAD_URL: "EXTERNAL_BAD_URL" = 'EXTERNAL_BAD_URL';
```

The base URL must start with http:// or https://, such as https://api.openai.com/v1.

##### EXTERNAL\_FAILED

```ts
readonly EXTERNAL_FAILED: "EXTERNAL_FAILED" = 'EXTERNAL_FAILED';
```

{{detail}}

##### EXTERNAL\_LOCAL\_ONLY

```ts
readonly EXTERNAL_LOCAL_ONLY: "EXTERNAL_LOCAL_ONLY" = 'EXTERNAL_LOCAL_ONLY';
```

This chat uses memories or knowledge marked This computer only, so it can't go to the external server. Choose a model on this computer.

##### EXTERNAL\_OFFLINE\_PROFILE

```ts
readonly EXTERNAL_OFFLINE_PROFILE: "EXTERNAL_OFFLINE_PROFILE" = 'EXTERNAL_OFFLINE_PROFILE';
```

This profile keeps work on this computer, so it doesn't use the external server. Choose a model on this computer or another profile.

##### FILE\_NOT\_FOUND

```ts
readonly FILE_NOT_FOUND: "FILE_NOT_FOUND" = 'FILE_NOT_FOUND';
```

That file isn't here anymore.

##### FIT\_FAILED

```ts
readonly FIT_FAILED: "FIT_FAILED" = 'FIT_FAILED';
```

{{detail}}

##### GPU\_SETUP\_FAILED

```ts
readonly GPU_SETUP_FAILED: "GPU_SETUP_FAILED" = 'GPU_SETUP_FAILED';
```

Couldn't check this computer's GPU setup.

##### HARDWARE\_DETECT\_FAILED

```ts
readonly HARDWARE_DETECT_FAILED: "HARDWARE_DETECT_FAILED" = 'HARDWARE_DETECT_FAILED';
```

Toskar couldn't fully detect this computer's hardware. Some details may be missing.

##### HARDWARE\_UNAVAILABLE

```ts
readonly HARDWARE_UNAVAILABLE: "HARDWARE_UNAVAILABLE" = 'HARDWARE_UNAVAILABLE';
```

Hardware detection isn't available.

##### HOOK\_TOO\_LARGE

```ts
readonly HOOK_TOO_LARGE: "HOOK_TOO_LARGE" = 'HOOK_TOO_LARGE';
```

The request body is larger than 64 KB.

##### HOOK\_TOO\_SOON

```ts
readonly HOOK_TOO_SOON: "HOOK_TOO_SOON" = 'HOOK_TOO_SOON';
```

This webhook was called a moment ago. Try again in a few seconds.

##### HOST\_NOT\_ALLOWED

```ts
readonly HOST_NOT_ALLOWED: "HOST_NOT_ALLOWED" = 'HOST_NOT_ALLOWED';
```

This address is not one of this computer's. Open Toskar at http://127.0.0.1 or http://localhost, or send an API key.

##### HUGGINGFACE\_TOKEN\_INVALID

```ts
readonly HUGGINGFACE_TOKEN_INVALID: "HUGGINGFACE_TOKEN_INVALID" = 'HUGGINGFACE_TOKEN_INVALID';
```

That isn't a Hugging Face token. Copy a read token from huggingface.co/settings/tokens; it starts with hf_.

##### INSTALL\_FAILED

```ts
readonly INSTALL_FAILED: "INSTALL_FAILED" = 'INSTALL_FAILED';
```

{{detail}}

##### INTERNAL\_ERROR

```ts
readonly INTERNAL_ERROR: "INTERNAL_ERROR" = 'INTERNAL_ERROR';
```

{{detail}}

##### INVALID\_BODY

```ts
readonly INVALID_BODY: "INVALID_BODY" = 'INVALID_BODY';
```

{{detail}}

##### INVALID\_BRANCH

```ts
readonly INVALID_BRANCH: "INVALID_BRANCH" = 'INVALID_BRANCH';
```

Send one of parent_id, retry_of, or edit_of, with the chat's conversation_id.

##### INVALID\_CONVERSATION\_IDS

```ts
readonly INVALID_CONVERSATION_IDS: "INVALID_CONVERSATION_IDS" = 'INVALID_CONVERSATION_IDS';
```

Name 1 to {{max}} chats to delete.

##### INVALID\_JSON

```ts
readonly INVALID_JSON: "INVALID_JSON" = 'INVALID_JSON';
```

{{detail}}

##### INVALID\_LOCALE

```ts
readonly INVALID_LOCALE: "INVALID_LOCALE" = 'INVALID_LOCALE';
```

That isn't a language Toskar recognizes.

##### INVALID\_PERSONALIZATION

```ts
readonly INVALID_PERSONALIZATION: "INVALID_PERSONALIZATION" = 'INVALID_PERSONALIZATION';
```

{{detail}}

##### INVALID\_RATING

```ts
readonly INVALID_RATING: "INVALID_RATING" = 'INVALID_RATING';
```

A rating is 1 to 5 stars, with reasons from the list.

##### INVALID\_RETENTION

```ts
readonly INVALID_RETENTION: "INVALID_RETENTION" = 'INVALID_RETENTION';
```

{{detail}}

##### INVALID\_SETTING

```ts
readonly INVALID_SETTING: "INVALID_SETTING" = 'INVALID_SETTING';
```

“{{value}}” isn't a valid value for {{setting}}.

##### INVITE\_INVALID

```ts
readonly INVITE_INVALID: "INVITE_INVALID" = 'INVITE_INVALID';
```

This link has expired or was already used. Ask for a new one.

##### JOIN\_BAD\_REQUEST

```ts
readonly JOIN_BAD_REQUEST: "JOIN_BAD_REQUEST" = 'JOIN_BAD_REQUEST';
```

{{detail}}

##### JOIN\_FAILED

```ts
readonly JOIN_FAILED: "JOIN_FAILED" = 'JOIN_FAILED';
```

{{detail}}

##### JOIN\_NOT\_REACHABLE

```ts
readonly JOIN_NOT_REACHABLE: "JOIN_NOT_REACHABLE" = 'JOIN_NOT_REACHABLE';
```

Other computers can't reach this one. Turn on Find other computers, then restart Toskar.

##### JOIN\_OTHER\_NETWORK

```ts
readonly JOIN_OTHER_NETWORK: "JOIN_OTHER_NETWORK" = 'JOIN_OTHER_NETWORK';
```

This computer is already in another Toskar network. Run toskarctl leave first to join this one.

##### JOIN\_RATE\_LIMITED

```ts
readonly JOIN_RATE_LIMITED: "JOIN_RATE_LIMITED" = 'JOIN_RATE_LIMITED';
```

Too many join attempts from this address. Wait a few minutes and try again.

##### JOIN\_TOKEN\_EXPIRED

```ts
readonly JOIN_TOKEN_EXPIRED: "JOIN_TOKEN_EXPIRED" = 'JOIN_TOKEN_EXPIRED';
```

This join token has expired. Make a new join command on a computer in the network.

##### JOIN\_TOKEN\_FAILED

```ts
readonly JOIN_TOKEN_FAILED: "JOIN_TOKEN_FAILED" = 'JOIN_TOKEN_FAILED';
```

{{detail}}

##### JOIN\_TOKEN\_INVALID

```ts
readonly JOIN_TOKEN_INVALID: "JOIN_TOKEN_INVALID" = 'JOIN_TOKEN_INVALID';
```

This join token isn't valid. Make a new join command on a computer in the network.

##### JOIN\_TOKEN\_NOT\_ACTIVE

```ts
readonly JOIN_TOKEN_NOT_ACTIVE: "JOIN_TOKEN_NOT_ACTIVE" = 'JOIN_TOKEN_NOT_ACTIVE';
```

That join token can't be revoked: it was already used, revoked, or expired.

##### JOIN\_TOKEN\_NOT\_FOUND

```ts
readonly JOIN_TOKEN_NOT_FOUND: "JOIN_TOKEN_NOT_FOUND" = 'JOIN_TOKEN_NOT_FOUND';
```

No join token has that ID.

##### JOIN\_TOKEN\_REVOKED

```ts
readonly JOIN_TOKEN_REVOKED: "JOIN_TOKEN_REVOKED" = 'JOIN_TOKEN_REVOKED';
```

This join token was revoked. Make a new join command on a computer in the network.

##### JOIN\_TOKEN\_USED

```ts
readonly JOIN_TOKEN_USED: "JOIN_TOKEN_USED" = 'JOIN_TOKEN_USED';
```

This join token has already been used. Make a new join command for each computer.

##### JOIN\_UNREACHABLE

```ts
readonly JOIN_UNREACHABLE: "JOIN_UNREACHABLE" = 'JOIN_UNREACHABLE';
```

Couldn't reach Toskar at {{server}}. Check the address, the firewall, and that Toskar is running there.

##### JOIN\_WRONG\_SERVER

```ts
readonly JOIN_WRONG_SERVER: "JOIN_WRONG_SERVER" = 'JOIN_WRONG_SERVER';
```

The computer at that address isn't the one the join command was made on. Nothing that proves the token was sent.

##### KEY\_CHAT\_ONLY

```ts
readonly KEY_CHAT_ONLY: "KEY_CHAT_ONLY" = 'KEY_CHAT_ONLY';
```

This key is for chat only, so it can't do this. Use another key from API Access.

##### KEY\_NOT\_FOUND

```ts
readonly KEY_NOT_FOUND: "KEY_NOT_FOUND" = 'KEY_NOT_FOUND';
```

They have no key with that id.

##### KEYS\_FAILED

```ts
readonly KEYS_FAILED: "KEYS_FAILED" = 'KEYS_FAILED';
```

Their keys couldn't be read: {{detail}}

##### KNOWLEDGE\_SOURCE\_NOT\_FOUND

```ts
readonly KNOWLEDGE_SOURCE_NOT_FOUND: "KNOWLEDGE_SOURCE_NOT_FOUND" = 'KNOWLEDGE_SOURCE_NOT_FOUND';
```

That knowledge source was removed.

##### KNOWLEDGE\_SYNC\_FAILED

```ts
readonly KNOWLEDGE_SYNC_FAILED: "KNOWLEDGE_SYNC_FAILED" = 'KNOWLEDGE_SYNC_FAILED';
```

{{detail}}

##### LAN\_ACCESS\_FAILED

```ts
readonly LAN_ACCESS_FAILED: "LAN_ACCESS_FAILED" = 'LAN_ACCESS_FAILED';
```

Local network access couldn't be turned on.

##### LAN\_ACCESS\_OFF

```ts
readonly LAN_ACCESS_OFF: "LAN_ACCESS_OFF" = 'LAN_ACCESS_OFF';
```

Local network access is off on this computer, so it only answers apps on it.

##### LIVE\_FIGURES\_FAILED

```ts
readonly LIVE_FIGURES_FAILED: "LIVE_FIGURES_FAILED" = 'LIVE_FIGURES_FAILED';
```

Couldn't read this computer's CPU, memory, and GPU figures.

##### LOG\_NOT\_FOUND

```ts
readonly LOG_NOT_FOUND: "LOG_NOT_FOUND" = 'LOG_NOT_FOUND';
```

That log file couldn't be opened.

##### LOGS\_LIST\_FAILED

```ts
readonly LOGS_LIST_FAILED: "LOGS_LIST_FAILED" = 'LOGS_LIST_FAILED';
```

Couldn't list the log files.

##### MARK\_FAILED

```ts
readonly MARK_FAILED: "MARK_FAILED" = 'MARK_FAILED';
```

Couldn't mark that as on topic.

##### MCP\_FAILED

```ts
readonly MCP_FAILED: "MCP_FAILED" = 'MCP_FAILED';
```

{{detail}}

##### MCP\_NOT\_FOUND

```ts
readonly MCP_NOT_FOUND: "MCP_NOT_FOUND" = 'MCP_NOT_FOUND';
```

There's no tool source with that name.

##### MEMORY\_LOOKS\_SECRET

```ts
readonly MEMORY_LOOKS_SECRET: "MEMORY_LOOKS_SECRET" = 'MEMORY_LOOKS_SECRET';
```

That looks like a password, key, or token, so Toskar didn't save it.

##### MEMORY\_NOT\_FOUND

```ts
readonly MEMORY_NOT_FOUND: "MEMORY_NOT_FOUND" = 'MEMORY_NOT_FOUND';
```

That memory was removed.

##### MESSAGE\_NOT\_FOUND

```ts
readonly MESSAGE_NOT_FOUND: "MESSAGE_NOT_FOUND" = 'MESSAGE_NOT_FOUND';
```

That message isn't in this chat anymore. Reload the chat and try again.

##### MESSAGES\_LIST\_FAILED

```ts
readonly MESSAGES_LIST_FAILED: "MESSAGES_LIST_FAILED" = 'MESSAGES_LIST_FAILED';
```

{{detail}}

##### METHOD\_NOT\_ALLOWED

```ts
readonly METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED" = 'METHOD_NOT_ALLOWED';
```

The Toskar service doesn't take that request ({{route}}). Update the app and the service to the same version.

##### MODEL\_BUSY

```ts
readonly MODEL_BUSY: "MODEL_BUSY" = 'MODEL_BUSY';
```

{{detail}}

##### MODEL\_FILE\_INVALID

```ts
readonly MODEL_FILE_INVALID: "MODEL_FILE_INVALID" = 'MODEL_FILE_INVALID';
```

This isn't a model Toskar can use: {{detail}}.

##### MODEL\_FILE\_NOT\_FOUND

```ts
readonly MODEL_FILE_NOT_FOUND: "MODEL_FILE_NOT_FOUND" = 'MODEL_FILE_NOT_FOUND';
```

There's no file at {{path}}.

##### MODEL\_FILE\_NOT\_PROJECTOR

```ts
readonly MODEL_FILE_NOT_PROJECTOR: "MODEL_FILE_NOT_PROJECTOR" = 'MODEL_FILE_NOT_PROJECTOR';
```

This is a model, not a vision projector.

##### MODEL\_FILE\_PROJECTOR

```ts
readonly MODEL_FILE_PROJECTOR: "MODEL_FILE_PROJECTOR" = 'MODEL_FILE_PROJECTOR';
```

This is a vision projector, which helps a model see pictures. Add the model it belongs to.

##### MODEL\_IMPORT\_FAILED

```ts
readonly MODEL_IMPORT_FAILED: "MODEL_IMPORT_FAILED" = 'MODEL_IMPORT_FAILED';
```

{{detail}}

##### MODEL\_NAME\_INVALID

```ts
readonly MODEL_NAME_INVALID: "MODEL_NAME_INVALID" = 'MODEL_NAME_INVALID';
```

Give the model a name of 1 to 120 characters.

##### MODEL\_NOT\_EDITABLE

```ts
readonly MODEL_NOT_EDITABLE: "MODEL_NOT_EDITABLE" = 'MODEL_NOT_EDITABLE';
```

Only a model you added can be renamed or tagged.

##### MODEL\_NOT\_FOUND

```ts
readonly MODEL_NOT_FOUND: "MODEL_NOT_FOUND" = 'MODEL_NOT_FOUND';
```

No model has that ID.

##### MODEL\_NOT\_INSTALLED

```ts
readonly MODEL_NOT_INSTALLED: "MODEL_NOT_INSTALLED" = 'MODEL_NOT_INSTALLED';
```

{{model_id}} isn't installed.

##### MODEL\_UNHEALTHY

```ts
readonly MODEL_UNHEALTHY: "MODEL_UNHEALTHY" = 'MODEL_UNHEALTHY';
```

The model stopped working.

##### MODEL\_UPDATE\_FAILED

```ts
readonly MODEL_UPDATE_FAILED: "MODEL_UPDATE_FAILED" = 'MODEL_UPDATE_FAILED';
```

{{detail}}

##### MODELS\_LIST\_FAILED

```ts
readonly MODELS_LIST_FAILED: "MODELS_LIST_FAILED" = 'MODELS_LIST_FAILED';
```

Couldn't list models.

##### NAME\_INVALID

```ts
readonly NAME_INVALID: "NAME_INVALID" = 'NAME_INVALID';
```

A name is 1 to 80 characters.

##### NEEDS\_APPROVAL

```ts
readonly NEEDS_APPROVAL: "NEEDS_APPROVAL" = 'NEEDS_APPROVAL';
```

This needs your approval before the automation can go on.

##### NEWS\_UNAVAILABLE

```ts
readonly NEWS_UNAVAILABLE: "NEWS_UNAVAILABLE" = 'NEWS_UNAVAILABLE';
```

The AI news couldn't be read from toskar.ai. Check the internet connection and try again.

##### NO\_MODEL\_ASSIGNED

```ts
readonly NO_MODEL_ASSIGNED: "NO_MODEL_ASSIGNED" = 'NO_MODEL_ASSIGNED';
```

No model is chosen for this. Install one in Models, or choose one in the profile.

##### NO\_MODEL\_INSTALLED

```ts
readonly NO_MODEL_INSTALLED: "NO_MODEL_INSTALLED" = 'NO_MODEL_INSTALLED';
```

No model is installed yet. Install one in Models to start chatting.

##### NO\_PASSWORD

```ts
readonly NO_PASSWORD: "NO_PASSWORD" = 'NO_PASSWORD';
```

You don't sign in with a password here.

##### NO\_TEXT\_FOUND

```ts
readonly NO_TEXT_FOUND: "NO_TEXT_FOUND" = 'NO_TEXT_FOUND';
```

No text found. Scanned PDFs need text recognition (OCR) before Toskar can read them.

##### NODES\_LIST\_FAILED

```ts
readonly NODES_LIST_FAILED: "NODES_LIST_FAILED" = 'NODES_LIST_FAILED';
```

Couldn't list computers.

##### NOT\_A\_DEVICE

```ts
readonly NOT_A_DEVICE: "NOT_A_DEVICE" = 'NOT_A_DEVICE';
```

Only a connected device can disconnect itself.

##### NOT\_FOUND

```ts
readonly NOT_FOUND: "NOT_FOUND" = 'NOT_FOUND';
```

{{detail}}

##### NOT\_IMPLEMENTED

```ts
readonly NOT_IMPLEMENTED: "NOT_IMPLEMENTED" = 'NOT_IMPLEMENTED';
```

{{detail}}

##### NOTHING\_TO\_COMPACT

```ts
readonly NOTHING_TO_COMPACT: "NOTHING_TO_COMPACT" = 'NOTHING_TO_COMPACT';
```

This chat is too short to compact.

##### NOTIFICATION\_NOT\_FOUND

```ts
readonly NOTIFICATION_NOT_FOUND: "NOTIFICATION_NOT_FOUND" = 'NOTIFICATION_NOT_FOUND';
```

That notification was removed.

##### NOTIFICATIONS\_DISABLED

```ts
readonly NOTIFICATIONS_DISABLED: "NOTIFICATIONS_DISABLED" = 'NOTIFICATIONS_DISABLED';
```

Notifications are turned off.

##### NOTIFICATIONS\_FAILED

```ts
readonly NOTIFICATIONS_FAILED: "NOTIFICATIONS_FAILED" = 'NOTIFICATIONS_FAILED';
```

{{detail}}

##### OFFER\_FAILED

```ts
readonly OFFER_FAILED: "OFFER_FAILED" = 'OFFER_FAILED';
```

{{detail}}

##### ORIGIN\_NOT\_ALLOWED

```ts
readonly ORIGIN_NOT_ALLOWED: "ORIGIN_NOT_ALLOWED" = 'ORIGIN_NOT_ALLOWED';
```

Websites cannot use Toskar without an API key.

##### OUT\_OF\_MEMORY

```ts
readonly OUT_OF_MEMORY: "OUT_OF_MEMORY" = 'OUT_OF_MEMORY';
```

The model ran out of memory.

##### OWNER\_FIXED

```ts
readonly OWNER_FIXED: "OWNER_FIXED" = 'OWNER_FIXED';
```

The Owner's role can't change, and nobody changes their own role or disables themselves.

##### PAIR\_FAILED

```ts
readonly PAIR_FAILED: "PAIR_FAILED" = 'PAIR_FAILED';
```

{{detail}}

##### PAIRING\_EXPIRED

```ts
readonly PAIRING_EXPIRED: "PAIRING_EXPIRED" = 'PAIRING_EXPIRED';
```

That code has expired. Choose Connect a device on the computer again.

##### PAIRING\_FAILED

```ts
readonly PAIRING_FAILED: "PAIRING_FAILED" = 'PAIRING_FAILED';
```

The device couldn't be connected.

##### PAIRING\_NOT\_LOCAL

```ts
readonly PAIRING_NOT_LOCAL: "PAIRING_NOT_LOCAL" = 'PAIRING_NOT_LOCAL';
```

A device can connect only from the computer's own network.

##### PAIRING\_NOT\_STARTED

```ts
readonly PAIRING_NOT_STARTED: "PAIRING_NOT_STARTED" = 'PAIRING_NOT_STARTED';
```

That computer isn't showing a code. Choose Connect a device on it first.

##### PAIRING\_RATE\_LIMITED

```ts
readonly PAIRING_RATE_LIMITED: "PAIRING_RATE_LIMITED" = 'PAIRING_RATE_LIMITED';
```

Too many pairing attempts from this address. Wait a few minutes and start pairing again.

##### PAIRING\_THROTTLED

```ts
readonly PAIRING_THROTTLED: "PAIRING_THROTTLED" = 'PAIRING_THROTTLED';
```

Too many tries. Wait a few minutes, then try again.

##### PAIRING\_WRONG\_CODE

```ts
readonly PAIRING_WRONG_CODE: "PAIRING_WRONG_CODE" = 'PAIRING_WRONG_CODE';
```

That isn't the code the computer shows. Check it and try again.

##### PASSWORD\_CHANGE\_REQUIRED

```ts
readonly PASSWORD_CHANGE_REQUIRED: "PASSWORD_CHANGE_REQUIRED" = 'PASSWORD_CHANGE_REQUIRED';
```

Change the password you were given first.

##### PASSWORD\_SAME

```ts
readonly PASSWORD_SAME: "PASSWORD_SAME" = 'PASSWORD_SAME';
```

Choose a password other than your current one.

##### PASSWORD\_TOO\_SHORT

```ts
readonly PASSWORD_TOO_SHORT: "PASSWORD_TOO_SHORT" = 'PASSWORD_TOO_SHORT';
```

A password needs at least 10 characters.

##### PASSWORD\_WRONG

```ts
readonly PASSWORD_WRONG: "PASSWORD_WRONG" = 'PASSWORD_WRONG';
```

That isn't your current password.

##### PEER\_FAILED

```ts
readonly PEER_FAILED: "PEER_FAILED" = 'PEER_FAILED';
```

{{detail}}

##### PEER\_TOO\_OLD

```ts
readonly PEER_TOO_OLD: "PEER_TOO_OLD" = 'PEER_TOO_OLD';
```

That computer needs a newer Toskar to run tools for others.

##### PEER\_UNAUTHORIZED

```ts
readonly PEER_UNAUTHORIZED: "PEER_UNAUTHORIZED" = 'PEER_UNAUTHORIZED';
```

That computer didn't accept this one's sign-in ({{detail}}). If it keeps happening, pair the two computers again in Computers.

##### PEER\_UNAVAILABLE

```ts
readonly PEER_UNAVAILABLE: "PEER_UNAVAILABLE" = 'PEER_UNAVAILABLE';
```

That computer doesn't offer this right now. It may still be starting, or need a newer Toskar.

##### PERFORMANCE\_LIST\_FAILED

```ts
readonly PERFORMANCE_LIST_FAILED: "PERFORMANCE_LIST_FAILED" = 'PERFORMANCE_LIST_FAILED';
```

Couldn't list performance measurements.

##### PERMISSIONS\_FAILED

```ts
readonly PERMISSIONS_FAILED: "PERMISSIONS_FAILED" = 'PERMISSIONS_FAILED';
```

{{detail}}

##### PERSON\_NOT\_FOUND

```ts
readonly PERSON_NOT_FOUND: "PERSON_NOT_FOUND" = 'PERSON_NOT_FOUND';
```

That person isn't here.

##### PERSONALIZATION\_FAILED

```ts
readonly PERSONALIZATION_FAILED: "PERSONALIZATION_FAILED" = 'PERSONALIZATION_FAILED';
```

{{detail}}

##### PIN\_INVALID

```ts
readonly PIN_INVALID: "PIN_INVALID" = 'PIN_INVALID';
```

That pin can't be saved. Only Members and Visitors are pinned, and only to profiles that exist.

##### PINS\_FAILED

```ts
readonly PINS_FAILED: "PINS_FAILED" = 'PINS_FAILED';
```

Couldn't read which profiles people are pinned to.

##### PORTAL\_BUSY

```ts
readonly PORTAL_BUSY: "PORTAL_BUSY" = 'PORTAL_BUSY';
```

This chat is busy. Try again in a moment.

##### PORTAL\_INVALID

```ts
readonly PORTAL_INVALID: "PORTAL_INVALID" = 'PORTAL_INVALID';
```

That portal setting can't be used.

##### PORTAL\_INVITE

```ts
readonly PORTAL_INVITE: "PORTAL_INVITE" = 'PORTAL_INVITE';
```

This chat is by invitation. Open the link you were sent, or ask for a new one.

##### PORTAL\_MEMBERS

```ts
readonly PORTAL_MEMBERS: "PORTAL_MEMBERS" = 'PORTAL_MEMBERS';
```

This chat is for the people who sign in to this Toskar.

##### PORTAL\_NOT\_FOUND

```ts
readonly PORTAL_NOT_FOUND: "PORTAL_NOT_FOUND" = 'PORTAL_NOT_FOUND';
```

There's no portal at this address, or it's turned off.

##### PORTAL\_OFF

```ts
readonly PORTAL_OFF: "PORTAL_OFF" = 'PORTAL_OFF';
```

This portal is turned off.

##### PORTAL\_ONLY

```ts
readonly PORTAL_ONLY: "PORTAL_ONLY" = 'PORTAL_ONLY';
```

A portal's visitor can only chat in the portal.

##### PORTAL\_PASSCODE

```ts
readonly PORTAL_PASSCODE: "PORTAL_PASSCODE" = 'PORTAL_PASSCODE';
```

That passcode isn't right.

##### PORTAL\_RATE

```ts
readonly PORTAL_RATE: "PORTAL_RATE" = 'PORTAL_RATE';
```

You've sent a lot of messages. Try again later.

##### PORTAL\_SLUG\_TAKEN

```ts
readonly PORTAL_SLUG_TAKEN: "PORTAL_SLUG_TAKEN" = 'PORTAL_SLUG_TAKEN';
```

Another portal has that address.

##### PORTAL\_TOO\_LONG

```ts
readonly PORTAL_TOO_LONG: "PORTAL_TOO_LONG" = 'PORTAL_TOO_LONG';
```

A message here can be {{max}} characters at most.

##### PREFERENCE\_CANNOT\_GRANT\_TOOLS

```ts
readonly PREFERENCE_CANNOT_GRANT_TOOLS: "PREFERENCE_CANNOT_GRANT_TOOLS" = 'PREFERENCE_CANNOT_GRANT_TOOLS';
```

Preferences and memories can't give permission to use tools. Change what tools may do in Settings → Tool permissions or in a profile.

##### PRIVACY\_FAILED

```ts
readonly PRIVACY_FAILED: "PRIVACY_FAILED" = 'PRIVACY_FAILED';
```

{{detail}}

##### PROFILE\_CREATE\_FAILED

```ts
readonly PROFILE_CREATE_FAILED: "PROFILE_CREATE_FAILED" = 'PROFILE_CREATE_FAILED';
```

{{detail}}

##### PROFILE\_NOT\_FOUND

```ts
readonly PROFILE_NOT_FOUND: "PROFILE_NOT_FOUND" = 'PROFILE_NOT_FOUND';
```

There's no such profile.

##### PROFILE\_PINNED

```ts
readonly PROFILE_PINNED: "PROFILE_PINNED" = 'PROFILE_PINNED';
```

This key answers only with its own profile. Leave out the profile and model, or name that profile.

##### PROFILE\_UPDATE\_FAILED

```ts
readonly PROFILE_UPDATE_FAILED: "PROFILE_UPDATE_FAILED" = 'PROFILE_UPDATE_FAILED';
```

{{detail}}

##### PROFILES\_LIST\_FAILED

```ts
readonly PROFILES_LIST_FAILED: "PROFILES_LIST_FAILED" = 'PROFILES_LIST_FAILED';
```

Couldn't list profiles.

##### PROXY\_REFUSED

```ts
readonly PROXY_REFUSED: "PROXY_REFUSED" = 'PROXY_REFUSED';
```

Your sign-in doesn't give you a role on this Toskar. Ask its Owner to add you to a group that does.

##### PUSH\_DEVICE\_ONLY

```ts
readonly PUSH_DEVICE_ONLY: "PUSH_DEVICE_ONLY" = 'PUSH_DEVICE_ONLY';
```

Only a paired phone or tablet can turn on notifications.

##### PUSH\_FAILED

```ts
readonly PUSH_FAILED: "PUSH_FAILED" = 'PUSH_FAILED';
```

{{detail}}

##### PUSH\_INVALID

```ts
readonly PUSH_INVALID: "PUSH_INVALID" = 'PUSH_INVALID';
```

{{detail}}

##### PUSH\_UNAVAILABLE

```ts
readonly PUSH_UNAVAILABLE: "PUSH_UNAVAILABLE" = 'PUSH_UNAVAILABLE';
```

Notifications in the Toskar app aren't available on this computer.

##### RATING\_FAILED

```ts
readonly RATING_FAILED: "RATING_FAILED" = 'RATING_FAILED';
```

{{detail}}

##### RATING\_NOT\_SHAREABLE

```ts
readonly RATING_NOT_SHAREABLE: "RATING_NOT_SHAREABLE" = 'RATING_NOT_SHAREABLE';
```

This model can't be compared with others' ratings, so its rating stays on this computer.

##### RATINGS\_UNREACHABLE

```ts
readonly RATINGS_UNREACHABLE: "RATINGS_UNREACHABLE" = 'RATINGS_UNREACHABLE';
```

Your rating is saved on this computer, but the ratings service couldn't be reached. Try again later.

##### RECOMMEND\_FAILED

```ts
readonly RECOMMEND_FAILED: "RECOMMEND_FAILED" = 'RECOMMEND_FAILED';
```

{{detail}}

##### REFRESH\_FAILED

```ts
readonly REFRESH_FAILED: "REFRESH_FAILED" = 'REFRESH_FAILED';
```

{{detail}}

##### RELAY\_INVALID

```ts
readonly RELAY_INVALID: "RELAY_INVALID" = 'RELAY_INVALID';
```

Enter the relay's name, such as relay.example.com, with a port only when it isn't 443.

##### RELAY\_SECRET\_INVALID

```ts
readonly RELAY_SECRET_INVALID: "RELAY_SECRET_INVALID" = 'RELAY_SECRET_INVALID';
```

That isn't an enrollment secret. Copy it from the relay's enroll.secret file.

##### RELAY\_SOLD\_OUT

```ts
readonly RELAY_SOLD_OUT: "RELAY_SOLD_OUT" = 'RELAY_SOLD_OUT';
```

Toskar's relay isn't taking new subscriptions right now. Try again in a few days.

##### RELAY\_TOKEN\_FAILED

```ts
readonly RELAY_TOKEN_FAILED: "RELAY_TOKEN_FAILED" = 'RELAY_TOKEN_FAILED';
```

Couldn't save the relay token on this computer.

##### RELAY\_TOKEN\_INVALID

```ts
readonly RELAY_TOKEN_INVALID: "RELAY_TOKEN_INVALID" = 'RELAY_TOKEN_INVALID';
```

That relay token isn't for this computer, or it has run out. Subscribe again from this device.

##### RELAY\_TOKEN\_NOT\_NEEDED

```ts
readonly RELAY_TOKEN_NOT_NEEDED: "RELAY_TOKEN_NOT_NEEDED" = 'RELAY_TOKEN_NOT_NEEDED';
```

This computer uses your organization's relay, so it doesn't need a subscription.

##### REMOTE\_ACCESS\_OFF

```ts
readonly REMOTE_ACCESS_OFF: "REMOTE_ACCESS_OFF" = 'REMOTE_ACCESS_OFF';
```

Access from anywhere is off, so there's nothing to check. Turn it on first.

##### REMOTE\_ADDRESS\_INVALID

```ts
readonly REMOTE_ADDRESS_INVALID: "REMOTE_ADDRESS_INVALID" = 'REMOTE_ADDRESS_INVALID';
```

Enter a host name or IP, with a port when it differs, such as home.example.com or 203.0.113.7:7333.

##### REMOTE\_DEVICES\_ONLY

```ts
readonly REMOTE_DEVICES_ONLY: "REMOTE_DEVICES_ONLY" = 'REMOTE_DEVICES_ONLY';
```

From outside the home network, only paired devices can connect.

##### REMOTE\_LISTEN\_FAILED

```ts
readonly REMOTE_LISTEN_FAILED: "REMOTE_LISTEN_FAILED" = 'REMOTE_LISTEN_FAILED';
```

Access from anywhere can't listen on port {{port}}. Another program may be using it.

##### REMOTE\_PORT\_INVALID

```ts
readonly REMOTE_PORT_INVALID: "REMOTE_PORT_INVALID" = 'REMOTE_PORT_INVALID';
```

The port is 1024 to 65535, and not the one the app or the computers use.

##### REMOTE\_THROTTLED

```ts
readonly REMOTE_THROTTLED: "REMOTE_THROTTLED" = 'REMOTE_THROTTLED';
```

Too many wrong keys came from this address. Try again later.

##### REMOTE\_TRAINING\_FAILED

```ts
readonly REMOTE_TRAINING_FAILED: "REMOTE_TRAINING_FAILED" = 'REMOTE_TRAINING_FAILED';
```

{{detail}}

##### REPLY\_INTERRUPTED

```ts
readonly REPLY_INTERRUPTED: "REPLY_INTERRUPTED" = 'REPLY_INTERRUPTED';
```

The reply stopped before it finished because the connection to the Toskar service was lost. Try again.

##### REPORT\_INVALID

```ts
readonly REPORT_INVALID: "REPORT_INVALID" = 'REPORT_INVALID';
```

That report can't be sent: it needs the error, and any email address has to be complete.

##### REPORT\_RATE\_LIMITED

```ts
readonly REPORT_RATE_LIMITED: "REPORT_RATE_LIMITED" = 'REPORT_RATE_LIMITED';
```

Too many reports were sent from here. Try again later, or send it by email.

##### REPORTS\_OFF

```ts
readonly REPORTS_OFF: "REPORTS_OFF" = 'REPORTS_OFF';
```

An Admin turned off sending problem reports to Toskar. Copy the report and give it to whoever runs Toskar here.

##### REPORTS\_UNAVAILABLE

```ts
readonly REPORTS_UNAVAILABLE: "REPORTS_UNAVAILABLE" = 'REPORTS_UNAVAILABLE';
```

The report couldn't be sent to Toskar right now. Send it by email instead.

##### REQUEST\_BAD\_TIME

```ts
readonly REQUEST_BAD_TIME: "REQUEST_BAD_TIME" = 'REQUEST_BAD_TIME';
```

That time is not valid.

##### REQUEST\_EMPTY

```ts
readonly REQUEST_EMPTY: "REQUEST_EMPTY" = 'REQUEST_EMPTY';
```

Describe the automation.

##### REQUEST\_NO\_SCHEDULE

```ts
readonly REQUEST_NO_SCHEDULE: "REQUEST_NO_SCHEDULE" = 'REQUEST_NO_SCHEDULE';
```

Describe when it should run, for example “every morning at 8:00 AM”.

##### REQUEST\_TIME\_ZONE

```ts
readonly REQUEST_TIME_ZONE: "REQUEST_TIME_ZONE" = 'REQUEST_TIME_ZONE';
```

A time zone is required.

##### RESET\_FAILED

```ts
readonly RESET_FAILED: "RESET_FAILED" = 'RESET_FAILED';
```

{{detail}}

##### RESET\_UNSUPPORTED

```ts
readonly RESET_UNSUPPORTED: "RESET_UNSUPPORTED" = 'RESET_UNSUPPORTED';
```

Resetting isn't available here.

##### REVOKE\_FAILED

```ts
readonly REVOKE_FAILED: "REVOKE_FAILED" = 'REVOKE_FAILED';
```

{{detail}}

##### ROLE\_INVALID

```ts
readonly ROLE_INVALID: "ROLE_INVALID" = 'ROLE_INVALID';
```

That isn't a role.

##### ROLE\_REQUIRED

```ts
readonly ROLE_REQUIRED: "ROLE_REQUIRED" = 'ROLE_REQUIRED';
```

This needs the {{role}} role.

##### ROTATE\_FAILED

```ts
readonly ROTATE_FAILED: "ROTATE_FAILED" = 'ROTATE_FAILED';
```

{{detail}}

##### ROUTE\_FAILED

```ts
readonly ROUTE_FAILED: "ROUTE_FAILED" = 'ROUTE_FAILED';
```

Couldn't set up access from anywhere on this computer.

##### ROUTE\_NOT\_FOUND

```ts
readonly ROUTE_NOT_FOUND: "ROUTE_NOT_FOUND" = 'ROUTE_NOT_FOUND';
```

This version of the Toskar service doesn't know that request ({{route}}). Update the app and the service to the same version.

##### ROUTE\_NOT\_LOCAL

```ts
readonly ROUTE_NOT_LOCAL: "ROUTE_NOT_LOCAL" = 'ROUTE_NOT_LOCAL';
```

Connect at home once to set up access from anywhere on this device.

##### RUN\_NOT\_FOUND

```ts
readonly RUN_NOT_FOUND: "RUN_NOT_FOUND" = 'RUN_NOT_FOUND';
```

That run isn't recorded, or its record was removed.

##### RUNNING\_LIST\_FAILED

```ts
readonly RUNNING_LIST_FAILED: "RUNNING_LIST_FAILED" = 'RUNNING_LIST_FAILED';
```

{{detail}}

##### RUNS\_FAILED

```ts
readonly RUNS_FAILED: "RUNS_FAILED" = 'RUNS_FAILED';
```

{{detail}}

##### RUNTIME\_ERROR

```ts
readonly RUNTIME_ERROR: "RUNTIME_ERROR" = 'RUNTIME_ERROR';
```

The model's engine ran into an error.

##### RUNTIME\_NOT\_INSTALLED

```ts
readonly RUNTIME_NOT_INSTALLED: "RUNTIME_NOT_INSTALLED" = 'RUNTIME_NOT_INSTALLED';
```

{{runtime}} isn't set up yet. Choose Start on a model in Models, and Toskar sets it up.

##### RUNTIME\_SETUP\_FAILED

```ts
readonly RUNTIME_SETUP_FAILED: "RUNTIME_SETUP_FAILED" = 'RUNTIME_SETUP_FAILED';
```

{{runtime}} couldn't be set up, so the model can't start ({{reason}}). Check this computer's internet connection, then choose Start again.

##### RUNTIMES\_LIST\_FAILED

```ts
readonly RUNTIMES_LIST_FAILED: "RUNTIMES_LIST_FAILED" = 'RUNTIMES_LIST_FAILED';
```

{{detail}}

##### SANDBOXED

```ts
readonly SANDBOXED: "SANDBOXED" = 'SANDBOXED';
```

This copy of Toskar runs in the macOS App Sandbox, which can't run a Python environment it downloads.

##### SERVICE\_UNREACHABLE

```ts
readonly SERVICE_UNREACHABLE: "SERVICE_UNREACHABLE" = 'SERVICE_UNREACHABLE';
```

Couldn't reach the local Toskar service ({{detail}}). If this is the desktop app, quit and reopen it so the service restarts.

##### SETTINGS\_READ\_FAILED

```ts
readonly SETTINGS_READ_FAILED: "SETTINGS_READ_FAILED" = 'SETTINGS_READ_FAILED';
```

Couldn't read settings.

##### SETTINGS\_UPDATE\_FAILED

```ts
readonly SETTINGS_UPDATE_FAILED: "SETTINGS_UPDATE_FAILED" = 'SETTINGS_UPDATE_FAILED';
```

Couldn't update settings.

##### SETUP\_REFUSED

```ts
readonly SETUP_REFUSED: "SETUP_REFUSED" = 'SETUP_REFUSED';
```

{{detail}}

##### SHELL\_ONLY

```ts
readonly SHELL_ONLY: "SHELL_ONLY" = 'SHELL_ONLY';
```

Only the Toskar Pro app on this computer can change this.

##### SIGN\_IN\_FAILED

```ts
readonly SIGN_IN_FAILED: "SIGN_IN_FAILED" = 'SIGN_IN_FAILED';
```

That username and password don't match.

##### SIGN\_IN\_THROTTLED

```ts
readonly SIGN_IN_THROTTLED: "SIGN_IN_THROTTLED" = 'SIGN_IN_THROTTLED';
```

Too many tries. Wait 15 minutes and try again.

##### SPEECH\_FAILED

```ts
readonly SPEECH_FAILED: "SPEECH_FAILED" = 'SPEECH_FAILED';
```

{{detail}}

##### SPEECH\_NO\_VOICE

```ts
readonly SPEECH_NO_VOICE: "SPEECH_NO_VOICE" = 'SPEECH_NO_VOICE';
```

There is no voice to read {{language}} aloud yet.

##### SPEECH\_SETUP\_FAILED

```ts
readonly SPEECH_SETUP_FAILED: "SPEECH_SETUP_FAILED" = 'SPEECH_SETUP_FAILED';
```

Speech (reading aloud and turning speech into text) couldn't be set up on this computer. Diagnostics shows what's missing.

##### SPEECH\_UNAVAILABLE

```ts
readonly SPEECH_UNAVAILABLE: "SPEECH_UNAVAILABLE" = 'SPEECH_UNAVAILABLE';
```

{{detail}}

##### SSE\_UNSUPPORTED

```ts
readonly SSE_UNSUPPORTED: "SSE_UNSUPPORTED" = 'SSE_UNSUPPORTED';
```

Streaming isn't supported here.

##### START\_FAILED

```ts
readonly START_FAILED: "START_FAILED" = 'START_FAILED';
```

{{detail}}

##### STOP\_FAILED

```ts
readonly STOP_FAILED: "STOP_FAILED" = 'STOP_FAILED';
```

{{detail}}

##### SUBSCRIPTION\_ACTIVE

```ts
readonly SUBSCRIPTION_ACTIVE: "SUBSCRIPTION_ACTIVE" = 'SUBSCRIPTION_ACTIVE';
```

This computer already has access from anywhere.

##### SUBSCRIPTION\_FAILED

```ts
readonly SUBSCRIPTION_FAILED: "SUBSCRIPTION_FAILED" = 'SUBSCRIPTION_FAILED';
```

Couldn't start the subscription.

##### SUBSCRIPTION\_IN\_APP\_ONLY

```ts
readonly SUBSCRIPTION_IN_APP_ONLY: "SUBSCRIPTION_IN_APP_ONLY" = 'SUBSCRIPTION_IN_APP_ONLY';
```

This copy of Toskar is from the App Store, so access from anywhere is sold in the Toskar app on your phone or tablet.

##### SUBSCRIPTION\_NONE

```ts
readonly SUBSCRIPTION_NONE: "SUBSCRIPTION_NONE" = 'SUBSCRIPTION_NONE';
```

This computer has no subscription bought in its settings. One bought in the Toskar app is managed in your phone's or tablet's store.

##### SUBSCRIPTION\_OWN\_RELAY

```ts
readonly SUBSCRIPTION_OWN_RELAY: "SUBSCRIPTION_OWN_RELAY" = 'SUBSCRIPTION_OWN_RELAY';
```

This computer uses your organization's relay, so it doesn't need a subscription to Toskar's.

##### SUBSCRIPTION\_PLAN\_INVALID

```ts
readonly SUBSCRIPTION_PLAN_INVALID: "SUBSCRIPTION_PLAN_INVALID" = 'SUBSCRIPTION_PLAN_INVALID';
```

Choose monthly or yearly.

##### SUMMARY\_EMPTY

```ts
readonly SUMMARY_EMPTY: "SUMMARY_EMPTY" = 'SUMMARY_EMPTY';
```

A summary can't be empty.

##### SUMMARY\_FAILED

```ts
readonly SUMMARY_FAILED: "SUMMARY_FAILED" = 'SUMMARY_FAILED';
```

The summary couldn't be read or saved: {{detail}}

##### SUMMARY\_NOT\_FOUND

```ts
readonly SUMMARY_NOT_FOUND: "SUMMARY_NOT_FOUND" = 'SUMMARY_NOT_FOUND';
```

This chat hasn't been compacted yet.

##### SUPPORT\_MODEL\_BUSY

```ts
readonly SUPPORT_MODEL_BUSY: "SUPPORT_MODEL_BUSY" = 'SUPPORT_MODEL_BUSY';
```

The supporting model can't run right now.

##### TASK\_CREATE\_FAILED

```ts
readonly TASK_CREATE_FAILED: "TASK_CREATE_FAILED" = 'TASK_CREATE_FAILED';
```

{{detail}}

##### TASK\_FAILED

```ts
readonly TASK_FAILED: "TASK_FAILED" = 'TASK_FAILED';
```

{{detail}}

##### TASK\_INTERRUPTED

```ts
readonly TASK_INTERRUPTED: "TASK_INTERRUPTED" = 'TASK_INTERRUPTED';
```

Toskar stopped before this finished.

##### TASKS\_LIST\_FAILED

```ts
readonly TASKS_LIST_FAILED: "TASKS_LIST_FAILED" = 'TASKS_LIST_FAILED';
```

{{detail}}

##### TOOL\_SOURCE\_ENTRY\_NOT\_FOUND

```ts
readonly TOOL_SOURCE_ENTRY_NOT_FOUND: "TOOL_SOURCE_ENTRY_NOT_FOUND" = 'TOOL_SOURCE_ENTRY_NOT_FOUND';
```

That gallery entry or app setting wasn't found.

##### TOOL\_TEST\_FAILED

```ts
readonly TOOL_TEST_FAILED: "TOOL_TEST_FAILED" = 'TOOL_TEST_FAILED';
```

{{detail}}

##### TOOL\_UPDATE\_FAILED

```ts
readonly TOOL_UPDATE_FAILED: "TOOL_UPDATE_FAILED" = 'TOOL_UPDATE_FAILED';
```

{{detail}}

##### TOOLS\_FAILED

```ts
readonly TOOLS_FAILED: "TOOLS_FAILED" = 'TOOLS_FAILED';
```

{{detail}}

##### TRAINING\_CANCELLED

```ts
readonly TRAINING_CANCELLED: "TRAINING_CANCELLED" = 'TRAINING_CANCELLED';
```

Training was cancelled.

##### TRANSFER\_INVALID

```ts
readonly TRANSFER_INVALID: "TRANSFER_INVALID" = 'TRANSFER_INVALID';
```

There's no active person to give their data to.

##### TRIAL\_FAILED

```ts
readonly TRIAL_FAILED: "TRIAL_FAILED" = 'TRIAL_FAILED';
```

Couldn't try that message. Check the topic controls and that a model is ready.

##### TRIAL\_NOT\_STARTED

```ts
readonly TRIAL_NOT_STARTED: "TRIAL_NOT_STARTED" = 'TRIAL_NOT_STARTED';
```

Start Toskar Pro's free 14-day trial to add models, automations, or people.

##### UNAUTHORIZED

```ts
readonly UNAUTHORIZED: "UNAUTHORIZED" = 'UNAUTHORIZED';
```

This Toskar needs an API key.

##### UNLOCK\_REQUIRED

```ts
readonly UNLOCK_REQUIRED: "UNLOCK_REQUIRED" = 'UNLOCK_REQUIRED';
```

Your Toskar Pro trial has ended. Unlock Toskar Pro to add models, automations, or people.

##### UNREADABLE\_FILE

```ts
readonly UNREADABLE_FILE: "UNREADABLE_FILE" = 'UNREADABLE_FILE';
```

Toskar can't read {{name}}: {{cause}}

##### UNSUPPORTED\_FILE

```ts
readonly UNSUPPORTED_FILE: "UNSUPPORTED_FILE" = 'UNSUPPORTED_FILE';
```

Toskar can't read {{name}} yet. Attach a document, spreadsheet, PDF, code file, audio, video, or a PNG or JPEG image.

##### USERNAME\_INVALID

```ts
readonly USERNAME_INVALID: "USERNAME_INVALID" = 'USERNAME_INVALID';
```

A username is 3 to 32 letters, digits, dots, dashes, or underscores.

##### USERNAME\_TAKEN

```ts
readonly USERNAME_TAKEN: "USERNAME_TAKEN" = 'USERNAME_TAKEN';
```

That username is taken.

##### WARM\_FAILED

```ts
readonly WARM_FAILED: "WARM_FAILED" = 'WARM_FAILED';
```

{{detail}}

## Functions

### readEvents()

```ts
function readEvents(body): AsyncGenerator<ServerSentEvent>;
```

Reads server-sent events from a response body as they arrive. Comments,
such as ": ping", are skipped.

#### Parameters

| Parameter | Type |
| ------ | ------ |
| `body` | `ReadableStream`\<`Uint8Array`\<`ArrayBufferLike`\>\> |

#### Returns

`AsyncGenerator`\<[`ServerSentEvent`](#serversentevent)\>

***

### unwrap()

```ts
function unwrap<T>(result): T;
```

The data of an `api` call, or its error thrown as a ToskarError:

    const models = unwrap(await toskar.api.GET('/api/v1/models'))

#### Type Parameters

| Type Parameter |
| ------ |
| `T` |

#### Parameters

| Parameter | Type |
| ------ | ------ |
| `result` | \{ `data?`: `T`; `error?`: `unknown`; `response`: `Response`; \} |
| `result.data?` | `T` |
| `result.error?` | `unknown` |
| `result.response` | `Response` |

#### Returns

`T`
