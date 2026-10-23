import createClient, { type Client } from 'openapi-fetch'

import { ToskarError } from './errors.js'
import { withRetries } from './fetch.js'
import { CONTRACT_VERSION } from './generated/contract.js'
import type { components, paths } from './generated/api.js'
import { readEvents } from './sse.js'

/** The API's named types, such as Schemas['Model'] or Schemas['Message']. */
export type Schemas = components['schemas']

/** What POST /api/v1/chat takes, without `stream`, which chat and chatStream set. */
export type ChatRequest = Omit<NonNullable<paths['/api/v1/chat']['post']['requestBody']>['content']['application/json'], 'stream'>

/** One event of a streamed chat. A failure is thrown as a ToskarError instead. */
export type ChatStreamEvent =
  | { type: 'token'; content: string }
  | { type: 'done'; metrics?: Schemas['GenerationMetrics'] }

export type ToskarOptions = {
  /** Where Toskar Core answers. Default: TOSKAR_URL, or http://127.0.0.1:7331, this computer. */
  baseUrl?: string
  /** An API key, for any address other than this computer's loopback. Default: TOSKAR_API_KEY. */
  apiKey?: string
  /** Retries for safe requests that fail to connect or answer 502, 503, or 504. Default 2. */
  retries?: number
  /** Milliseconds to wait for an answer to start. Default 60000; 0 waits as long as it takes. */
  timeoutMs?: number
  /** A fetch to use in place of the global one. */
  fetch?: typeof fetch
  /** More headers for every request. */
  headers?: Record<string, string>
}

const env = (name: string): string | undefined =>
  typeof process !== 'undefined' && process.env ? process.env[name] || undefined : undefined

/**
 * A connection to Toskar Core.
 *
 * `api` reaches every route, typed from Core's API spec:
 *
 *     const { data } = await toskar.api.GET('/api/v1/models')
 *
 * and the methods here cover what's easier by hand: chat, streamed chat,
 * and the events stream.
 */
export class Toskar {
  /** Every route of the API, typed. Answers are {data} or {error}; see unwrap. */
  readonly api: Client<paths>
  readonly baseUrl: string
  private readonly fetcher: typeof fetch
  private readonly headers: Record<string, string>

  constructor(options: ToskarOptions = {}) {
    this.baseUrl = (options.baseUrl ?? env('TOSKAR_URL') ?? 'http://127.0.0.1:7331').replace(/\/+$/, '')
    const apiKey = options.apiKey ?? env('TOSKAR_API_KEY')
    this.headers = {
      // Core answers 426 CONTRACT_MISMATCH to a client of another major version.
      'Toskar-Client-Contract': CONTRACT_VERSION,
      ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
      ...options.headers,
    }
    this.fetcher = withRetries(options.fetch ?? globalThis.fetch.bind(globalThis), {
      retries: options.retries ?? 2,
      timeoutMs: options.timeoutMs ?? 60_000,
    })
    this.api = createClient<paths>({ baseUrl: this.baseUrl, headers: this.headers, fetch: this.fetcher })
  }

  /** Asks once and waits for the whole answer. */
  async chat(request: ChatRequest, init: { signal?: AbortSignal } = {}): Promise<Schemas['ChatAnswer']> {
    const response = await this.post('/api/v1/chat', { ...request, stream: false }, init.signal)
    return (await response.json()) as Schemas['ChatAnswer']
  }

  /**
   * Asks and yields the answer as it's written: token events, then done
   * once it's finished and saved. A failure is thrown as a ToskarError,
   * with its code, such as NO_MODEL_INSTALLED.
   *
   *     for await (const e of toskar.chatStream({ message: 'Hi' })) {
   *       if (e.type === 'token') process.stdout.write(e.content)
   *     }
   */
  async *chatStream(request: ChatRequest, init: { signal?: AbortSignal } = {}): AsyncGenerator<ChatStreamEvent> {
    const response = await this.post('/api/v1/chat', { ...request, stream: true }, init.signal, 'text/event-stream')
    if (!response.body) throw new ToskarError(response.status, 'CHAT_FAILED', 'The answer had no body')
    let finished = false
    for await (const { event, data } of readEvents(response.body)) {
      switch (event) {
        case 'token':
          yield { type: 'token', content: (JSON.parse(data) as Schemas['ChatToken']).content }
          break
        case 'done':
          finished = true
          yield { type: 'done', ...(JSON.parse(data || '{}') as Schemas['ChatDone']) }
          return
        case 'error_code': {
          const body = JSON.parse(data) as Schemas['ErrorBody']
          throw new ToskarError(response.status, body.code, body.message, body.details ?? {})
        }
        case 'error':
          throw new ToskarError(response.status, 'CHAT_FAILED', data)
      }
    }
    // Every stream ends with done or an error, so one that just stops was cut off.
    if (!finished) throw new ToskarError(response.status, 'CONNECTION_LOST', 'The answer stopped before it finished')
  }

  /**
   * Yields what happens on Toskar as it happens, such as models loading and
   * automations running, until the signal aborts.
   */
  async *events(init: { signal?: AbortSignal } = {}): AsyncGenerator<Schemas['Event']> {
    const response = await this.fetcher(`${this.baseUrl}/api/v1/events`, {
      headers: { ...this.headers, Accept: 'text/event-stream' },
      signal: init.signal,
    })
    if (!response.ok || !response.body) throw ToskarError.from(response.status, await body(response))
    for await (const { data } of readEvents(response.body)) {
      yield JSON.parse(data) as Schemas['Event']
    }
  }

  /** Core's version and its client contract. */
  async version(): Promise<Schemas['VersionResponse']> {
    return unwrap(await this.api.GET('/api/v1/version'))
  }

  private async post(path: string, json: unknown, signal?: AbortSignal, accept = 'application/json'): Promise<Response> {
    const response = await this.fetcher(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: { ...this.headers, 'Content-Type': 'application/json', Accept: accept },
      body: JSON.stringify(json),
      signal,
    })
    if (!response.ok) throw ToskarError.from(response.status, await body(response))
    return response
  }
}

/**
 * The data of an `api` call, or its error thrown as a ToskarError:
 *
 *     const models = unwrap(await toskar.api.GET('/api/v1/models'))
 */
export function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.error !== undefined || !result.response.ok) throw ToskarError.from(result.response.status, result.error)
  return result.data as T
}

async function body(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch {
    return null
  }
}
