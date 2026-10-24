import { createCipheriv, createPrivateKey, hkdfSync, randomBytes, sign, X509Certificate } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { createServer, type Server } from 'node:https'
import type { AddressInfo } from 'node:net'
import { createServer as createTcpServer } from 'node:net'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { afterEach, describe, expect, it } from 'vitest'

import { fetch as undiciFetch } from 'undici'

import { openRecord, pair, pinnedDispatcher, pinOf, RecordError, routeId, shortPin, TOSKAR_RELAY, Toskar, unwrap, type Device } from '../src/node.js'

const here = dirname(fileURLToPath(import.meta.url))
const vectors = JSON.parse(readFileSync(join(here, '..', '..', 'spec', 'connection-vectors.json'), 'utf8'))
const SECRET = 'AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8'

describe('connection test vectors', () => {
  it('derives route IDs and pins, and opens or refuses every record', () => {
    for (const r of vectors.routes) expect(routeId(r.secret)).toBe(r.route_id)
    for (const p of vectors.pins) {
      const pin = pinOf(Buffer.from(p.cert_der_base64, 'base64'))
      expect([pin, shortPin(pin)]).toEqual([p.fingerprint, p.short])
    }
    for (const r of vectors.records) {
      const open = () => openRecord(Buffer.from(r.blob_base64, 'base64'), r.secret, r.pin, r.now, r.max_age_seconds)
      if (r.error) {
        expect(open, r.name).toThrow(RecordError)
        try {
          open()
        } catch (err) {
          expect((err as RecordError).reason, r.name).toBe(r.error)
        }
      } else {
        expect(open(), r.name).toEqual({ addresses: r.addresses, at: r.at })
      }
    }
  })
})

/** A Toskar Core on TLS with a certificate of its own, counting the keys it's sent. It asks for a key, as a computer that's connected devices does, so health answers only with one. */
type Computer = { address: string; pin: string; keys: number; tokens: string[]; der: Buffer; keyPem: string; server: Server }
const running: Server[] = []

async function computer(name: 'mine' | 'other', pairAnswer?: (pin: string) => unknown, record?: () => Buffer): Promise<Computer> {
  const cert = readFileSync(join(here, 'fixtures', `${name}.crt`), 'utf8')
  const keyPem = readFileSync(join(here, 'fixtures', `${name}.key`), 'utf8')
  const der = Buffer.from(new X509Certificate(cert).raw)
  const c = { pin: pinOf(der), keys: 0, tokens: [] as string[], der, keyPem } as Computer
  c.server = createServer({ cert, key: keyPem }, (req, res) => {
    if (req.headers.authorization) c.keys++
    const send = (status: number, body: unknown, type = 'application/json') => {
      res.writeHead(status, { 'Content-Type': type })
      res.end(Buffer.isBuffer(body) ? body : JSON.stringify(body))
    }
    if (req.url === '/api/v1/health') return req.headers.authorization ? send(200, { status: 'ok' }) : send(401, { error: { code: 'UNAUTHORIZED', message: 'A key is needed' } })
    if (record && req.url?.endsWith('/record')) {
      c.tokens.push(String(req.headers.authorization ?? ''))
      return send(200, record(), 'application/octet-stream')
    }
    if (req.method === 'POST' && pairAnswer) {
      req.resume()
      return req.on('end', () => send(201, pairAnswer(c.pin)))
    }
    send(200, [])
  })
  running.push(c.server)
  await new Promise<void>((resolve) => c.server.listen(0, '127.0.0.1', resolve))
  c.address = `127.0.0.1:${(c.server.address() as AddressInfo).port}`
  return c
}

afterEach(async () => {
  await Promise.all(running.splice(0).map((s) => new Promise((r) => s.close(r))))
})

async function unused(): Promise<string> {
  const s = createTcpServer()
  await new Promise<void>((r) => s.listen(0, '127.0.0.1', r))
  const port = (s.address() as AddressInfo).port
  await new Promise((r) => s.close(r))
  return `127.0.0.1:${port}`
}

/** An address record, as the computer writes it. */
function seal(c: Computer, secret: string, addresses: string[]): Buffer {
  const route = routeId(secret)
  const payload = Buffer.from(JSON.stringify({ v: 1, route, at: Math.floor(Date.now() / 1000), addresses }))
  const sig = sign('sha256', payload, { key: createPrivateKey(c.keyPem), dsaEncoding: 'der' })
  const plain = Buffer.from(JSON.stringify({ payload: payload.toString('base64'), cert: c.der.toString('base64'), alg: 'ecdsa-sha256', sig: sig.toString('base64') }))
  const key = Buffer.from(hkdfSync('sha256', Buffer.from(secret, 'base64url'), Buffer.alloc(0), 'toskar route key', 32))
  const nonce = randomBytes(12)
  const cipher = createCipheriv('aes-256-gcm', key, nonce)
  cipher.setAAD(Buffer.from(route))
  return Buffer.concat([nonce, cipher.update(plain), cipher.final(), cipher.getAuthTag()])
}

const paired = (pin: string) => ({
  api_key: 'tk_device', tls_fingerprint: pin, tls_short: shortPin(pin), key: { id: 'k' },
  route_secret: SECRET, route_id: routeId(SECRET), relay: 'relay.toskar.ai', token: 'rt',
})

describe('pairing', () => {
  it('pins the certificate the person confirmed', async () => {
    const c = await computer('mine', paired)
    const shown: string[] = []
    const device = await pair(c.address, '123456', 'Test', (short) => (shown.push(short), true))
    expect(shown).toEqual([shortPin(c.pin)])
    expect(device).toEqual({ address: c.address, apiKey: 'tk_device', pin: c.pin, route: { secret: SECRET, id: routeId(SECRET), relay: 'relay.toskar.ai', token: 'rt' } })
    await expect(pair(c.address, '123456', 'Test', () => false)).rejects.toMatchObject({ code: 'NOT_CONFIRMED' })
  })

  it("refuses a fingerprint that isn't the certificate's", async () => {
    const c = await computer('mine', () => paired(`sha256:${'ab'.repeat(32)}`))
    await expect(pair(c.address, '123456', 'Test')).rejects.toMatchObject({ code: 'PIN_MISMATCH' })
  })
})

describe('a paired device', () => {
  it('never sends its key to another certificate', async () => {
    const mine = await computer('mine')
    const other = await computer('other')
    const toskar = new Toskar({ device: { address: other.address, apiKey: 'tk_device', pin: mine.pin }, retries: 0 })
    await expect(toskar.api.GET('/api/v1/models')).rejects.toMatchObject({ code: 'PIN_MISMATCH' })
    expect(other.keys).toBe(0)
  })

  it('checks the certificate on every connection, including resumed ones', async () => {
    const c = await computer('mine')
    const dispatcher = pinnedDispatcher(c.pin)
    // A new connection each time: a resumed TLS session shows no certificate to check.
    for (let i = 0; i < 4; i++) {
      const r = await undiciFetch(`https://${c.address}/api/v1/models`, { dispatcher, headers: { connection: 'close' } })
      expect(r.status).toBe(200)
      await r.text()
    }
  })

  it('reaches its computer at home first', async () => {
    const c = await computer('mine')
    const toskar = new Toskar({ device: { address: c.address, apiKey: 'tk_device', pin: c.pin } })
    expect(unwrap(await toskar.api.GET('/api/v1/models'))).toEqual([])
    expect(toskar.path).toBe('home')
    // The health check and the call.
    expect(c.keys).toBe(2)
  })

  it('finds it away from home through its address record, and prefers a direct way', async () => {
    const c = await computer('mine')
    const relay = await computer('other', undefined, () => seal(c, SECRET, [c.address, `${routeId(SECRET)}.relay.test:4443`]))
    const device: Device = { address: await unused(), apiKey: 'tk_device', pin: c.pin, route: { secret: SECRET, id: routeId(SECRET), relay: relay.address, token: 'rt' } }
    const toskar = new Toskar({ device })
    // The test relay's certificate is its own; a real relay's is checked as any website's.
    ;(toskar as unknown as { router: { relayFetch: typeof fetch } }).router.relayFetch = async (input, init) => {
      const { Agent, fetch: undiciFetch } = await import('undici')
      return undiciFetch(input as string, { ...(init as object), dispatcher: new Agent({ connect: { rejectUnauthorized: false } }) }) as unknown as Response
    }
    expect(unwrap(await toskar.api.GET('/api/v1/models'))).toEqual([])
    expect(toskar.path).toBe('direct')
    expect(relay.tokens).toEqual(['Bearer rt'])
  })

  it("doesn't ask Toskar's relay without a token", async () => {
    const c = await computer('mine')
    const toskar = new Toskar({ device: { address: await unused(), apiKey: 'tk', pin: c.pin, route: { secret: SECRET, id: 'x', relay: TOSKAR_RELAY } }, retries: 0 })
    let asked = false
    ;(toskar as unknown as { router: { relayFetch: typeof fetch } }).router.relayFetch = async () => ((asked = true), new Response(null, { status: 500 }))
    await expect(toskar.api.GET('/api/v1/models')).rejects.toMatchObject({ code: 'UNREACHABLE' })
    expect(asked).toBe(false)
  })
})

