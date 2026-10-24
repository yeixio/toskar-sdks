import { describe, expect, it } from 'vitest'

import { CONTRACT_VERSION, ErrorCodes, Toskar, ToskarError, readEvents, unwrap } from '../src/index.js'

type Call = { url: string; method: string; headers: Headers; body: string }

/** A fetch that answers like Toskar Core, recording what it was asked. */
function fake(answer: (call: Call, attempt: number) => Response | Promise<Response>) {
  const calls: Call[] = []
  const fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const request = new Request(input, init)
    const call = { url: request.url, method: request.method, headers: request.headers, body: await request.text() }
    calls.push(call)
    return answer(call, calls.length)
  }
  return { fetch: fetch as typeof globalThis.fetch, calls }
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

const stream = (...chunks: string[]) =>
  new Response(
    new ReadableStream({
      start(c) {
        for (const chunk of chunks) c.enqueue(new TextEncoder().encode(chunk))
        c.close()
      },
    }),
    { headers: { 'Content-Type': 'text/event-stream' } },
  )

describe('Toskar', () => {
  it('reaches this computer by default, says its contract, and sends a key when given one', async () => {
    const { fetch, calls } = fake(() => json({ version: '1.11.0', contract: { version: '1.56', major: 1 } }))
    const toskar = new Toskar({ fetch, apiKey: 'tk_test' })
    const v = await toskar.version()
    expect(v.version).toBe('1.11.0')
    expect(calls[0].url).toBe('http://127.0.0.1:7331/api/v1/version')
    expect(calls[0].headers.get('Toskar-Client-Contract')).toBe(CONTRACT_VERSION)
    expect(calls[0].headers.get('Authorization')).toBe('Bearer tk_test')
  })

  it('chats, waiting for the whole answer', async () => {
    const { fetch, calls } = fake(() => json({ content: 'Hello!', metrics: { prompt_tokens: 3 } }))
    const answer = await new Toskar({ fetch }).chat({ message: 'Hi', profile_id: 'default' })
    expect(answer.content).toBe('Hello!')
    expect(JSON.parse(calls[0].body)).toEqual({ message: 'Hi', profile_id: 'default', stream: false })
  })

  it('streams an answer as it is written, across chunk boundaries', async () => {
    const { fetch } = fake(() =>
      stream('event: token\ndata: {"content":"Hel"}\n\n: ping\n\nevent: tok', 'en\ndata: {"content":"lo"}\n\n', 'event: done\ndata: {}\n\n'),
    )
    const events = []
    for await (const e of new Toskar({ fetch }).chatStream({ message: 'Hi' })) events.push(e)
    expect(events).toEqual([{ type: 'token', content: 'Hel' }, { type: 'token', content: 'lo' }, { type: 'done' }])
  })

  it('throws a streamed failure with its code', async () => {
    const { fetch } = fake(() =>
      stream(
        'event: token\ndata: {"content":"Hi"}\n\n',
        'event: error_code\ndata: {"code":"MODEL_NOT_INSTALLED","message":"model x is not installed","details":{"model_id":"x"}}\n\n',
        'event: error\ndata: model x is not installed\n\n',
      ),
    )
    const run = async () => {
      for await (const _ of new Toskar({ fetch }).chatStream({ message: 'Hi' })) void _
    }
    await expect(run()).rejects.toMatchObject({ code: ErrorCodes.MODEL_NOT_INSTALLED, details: { model_id: 'x' } })
  })

  it('says when a stream was cut off before done', async () => {
    const { fetch } = fake(() => stream('event: token\ndata: {"content":"Hi"}\n\n'))
    const run = async () => {
      for await (const _ of new Toskar({ fetch }).chatStream({ message: 'Hi' })) void _
    }
    await expect(run()).rejects.toMatchObject({ code: 'CONNECTION_LOST' })
  })

  it('turns an error answer into a ToskarError', async () => {
    const { fetch } = fake(() => json({ error: { code: 'API_KEY_REQUIRED', message: 'an API key is required' } }, 401))
    const toskar = new Toskar({ fetch })
    const err = await toskar.chat({ message: 'Hi' }).catch((e) => e)
    expect(err).toBeInstanceOf(ToskarError)
    expect(err).toMatchObject({ status: 401, code: 'API_KEY_REQUIRED', message: 'an API key is required' })
    expect(() => unwrap({ error: { error: { code: 'NOT_FOUND', message: 'no' } }, response: new Response(null, { status: 404 }) })).toThrow(ToskarError)
  })

  it('retries a safe request that the computer could not answer, but never a chat', async () => {
    const flaky = fake((_, attempt) => (attempt < 3 ? new Response('', { status: 503 }) : json([])))
    const models = unwrap(await new Toskar({ fetch: flaky.fetch }).api.GET('/api/v1/models'))
    expect(models).toEqual([])
    expect(flaky.calls).toHaveLength(3)

    const down = fake(() => new Response('', { status: 503 }))
    await expect(new Toskar({ fetch: down.fetch }).chat({ message: 'Hi' })).rejects.toMatchObject({ status: 503 })
    expect(down.calls).toHaveLength(1)
  })

  it('reaches every route through api, typed', async () => {
    const { fetch, calls } = fake(() => json({ id: 'c1', title: 'New chat', memory_off: false, compact_off: false, created_at: '', updated_at: '' }, 201))
    const toskar = new Toskar({ fetch, baseUrl: 'https://studio.local:7331/' })
    const conv = unwrap(await toskar.api.POST('/api/v1/conversations', { body: { title: 'New chat' } }))
    expect(conv.id).toBe('c1')
    expect(calls[0].url).toBe('https://studio.local:7331/api/v1/conversations')
  })

  it('reads the events stream', async () => {
    const { fetch } = fake(() => stream('event: model.unloaded\ndata: {"type":"model.unloaded","data":{"model_id":"m"}}\n\n'))
    const seen = []
    for await (const e of new Toskar({ fetch }).events()) seen.push(e.type)
    expect(seen).toEqual(['model.unloaded'])
  })
})

describe('readEvents', () => {
  it('reads named events, data on several lines, and skips comments', async () => {
    const body = new Response('event: a\ndata: 1\ndata: 2\n\n: ping\n\ndata: plain\n').body!
    const out = []
    for await (const e of readEvents(body)) out.push(e)
    expect(out).toEqual([{ event: 'a', data: '1\n2' }, { event: 'message', data: 'plain' }])
  })
})
