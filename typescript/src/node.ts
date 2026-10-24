// Connecting as a paired device, as the Toskar apps do (Toskar Core's
// docs/connecting.md), in Node: pairing with the code Connect a device
// shows, the computer's certificate pinned on every connection, and
// reaching it at home or, with access from anywhere, directly or through
// its relay. Browsers can't pin a certificate, so this is Node's alone:
//
//     import { Toskar, pair } from 'toskar/node'

import { X509Certificate, createDecipheriv, createHash, hkdfSync, verify as verifySignature } from 'node:crypto'
import { connect as tlsConnect, type TLSSocket } from 'node:tls'

import { Agent, buildConnector, fetch as undiciFetch, type Dispatcher } from 'undici'

import { Toskar as Base, type ToskarOptions } from './client.js'
import { ToskarError } from './errors.js'
import { CONTRACT_VERSION } from './generated/contract.js'
import type { components } from './generated/api.js'

export * from './index.js'

/** Toskar's own relay. It's asked only with a route token. */
export const TOSKAR_RELAY = 'relay.toskar.ai'

/** How a paired device reaches its computer. */
export type Path = 'home' | 'direct' | 'relay'

/** How to find the computer away from home, when it has access from anywhere. */
export type Route = {
  /** The route secret, base64url without padding. */
  secret: string
  id: string
  /** The relay the computer uses, such as relay.toskar.ai. */
  relay: string
  /** Lets the device look the computer up on Toskar's relay. */
  token?: string
}

/**
 * What a paired device keeps, to connect again. Save it as a password is
 * saved: apiKey and the route's secret and token are secrets.
 */
export type Device = {
  /** The computer's host:port at home. */
  address: string
  apiKey: string
  /** sha256:<hex> of the computer's certificate. It only ever comes from pairing. */
  pin: string
  route?: Route
}

const HOME_TIMEOUT = 2_500
const TRY_TIMEOUT = 6_000
const RELAY_DELAY = 1_000
const RECORD_MAX_AGE = 3_600

/** The pin of a certificate: sha256:<hex> of its DER. */
export function pinOf(der: Uint8Array): string {
  return `sha256:${createHash('sha256').update(der).digest('hex')}`
}

/** How a pin is shown for the person to compare: its first 8 hex digits, as ABCD-1234. */
export function shortPin(pin: string): string {
  const h = pin.replace(/^sha256:/, '').toUpperCase()
  return h.length < 8 ? h : `${h.slice(0, 4)}-${h.slice(4, 8)}`
}

const pinMismatch = () => new ToskarError(0, 'PIN_MISMATCH', "The computer's certificate isn't the one paired with")

function split(address: string): { host: string; port: number } {
  const at = address.lastIndexOf(':')
  // A host alone, such as relay.toskar.ai, or a bare IPv6 address, has no port.
  if (at < 0 || address.endsWith(']') || (address.indexOf(':') !== at && !address.startsWith('['))) {
    return { host: address.replace(/^\[(.*)\]$/, '$1'), port: 443 }
  }
  return { host: address.slice(0, at).replace(/^\[(.*)\]$/, '$1'), port: Number(address.slice(at + 1)) }
}

/**
 * Fetch through an undici dispatcher. undici's own fetch, not Node's
 * global one: Node bundles its own undici, whose version needn't match
 * this package's dispatchers.
 */
const pinnedFetch = (url: string | URL, init: RequestInit, dispatcher: Dispatcher) =>
  undiciFetch(url, { ...(init as object), dispatcher } as Parameters<typeof undiciFetch>[1]) as unknown as Promise<Response>

/**
 * An undici dispatcher that trusts exactly the certificate with pin: names,
 * dates, and signers aren't checked, and the pin is checked once the TLS
 * handshake is done, before any request is sent.
 */
export function pinnedDispatcher(pin: string): Dispatcher {
  // No TLS session resumption: a resumed session shows no certificate to check.
  const base = buildConnector({ rejectUnauthorized: false, maxCachedSessions: 0 })
  return new Agent({
    connect(options, callback) {
      base(options, (err, socket) => {
        if (err || !socket) return callback(err ?? new Error('no socket'), null)
        const cert = (socket as TLSSocket).getPeerCertificate?.(true)
        if (!cert?.raw || pinOf(cert.raw).toLowerCase() !== pin.toLowerCase()) {
          socket.destroy()
          return callback(pinMismatch(), null)
        }
        callback(null, socket)
      })
    },
  })
}

/** The pin of the certificate the computer at address shows. */
function certificatePin(address: string, timeoutMs: number): Promise<string> {
  const { host, port } = split(address)
  return new Promise((resolve, reject) => {
    const socket = tlsConnect({ host, port, rejectUnauthorized: false, servername: /^[\d.:]+$/.test(host) ? undefined : host })
    socket.setTimeout(timeoutMs, () => socket.destroy(new Error(`${address} didn't answer`)))
    socket.once('secureConnect', () => {
      const raw = socket.getPeerCertificate(true).raw
      socket.end()
      resolve(pinOf(raw))
    })
    socket.once('error', reject)
  })
}

/**
 * Pairs with the computer at address (host:port, as found or typed) using
 * the code Connect a device shows on it. confirm gets the short pin to show
 * the person, and says whether the computer shows the same. The device must
 * be on the computer's local network.
 */
export async function pair(
  address: string,
  code: string,
  deviceName: string,
  confirm?: (shortPin: string) => boolean | Promise<boolean>,
): Promise<Device> {
  const pin = await certificatePin(address, 30_000)
  if (confirm && !(await confirm(shortPin(pin)))) {
    throw new ToskarError(0, 'NOT_CONFIRMED', "The short pin wasn't confirmed")
  }
  const response = await pinnedFetch(
    `https://${address}/api/v1/devices/pair`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Toskar-Client-Contract': CONTRACT_VERSION },
      body: JSON.stringify({ code, device_name: deviceName }),
    },
    pinnedDispatcher(pin),
  )
  const body = (await response.json().catch(() => null)) as components['schemas']['PairedDevice'] | null
  if (!response.ok || !body) throw ToskarError.from(response.status, body)
  if (body.tls_fingerprint.toLowerCase() !== pin.toLowerCase()) throw pinMismatch()
  const device: Device = { address, apiKey: body.api_key, pin }
  if (body.route_secret) {
    device.route = { secret: body.route_secret, id: body.route_id ?? '', relay: body.relay ?? '', token: body.token ?? undefined }
  }
  return device
}

// Route IDs and address records.

const BASE32 = 'abcdefghijklmnopqrstuvwxyz234567'

function base32(bytes: Uint8Array): string {
  let bits = 0
  let value = 0
  let out = ''
  for (const byte of bytes) {
    value = (value << 8) | byte
    bits += 8
    while (bits >= 5) {
      out += BASE32[(value >>> (bits - 5)) & 31]
      bits -= 5
    }
  }
  if (bits > 0) out += BASE32[(value << (5 - bits)) & 31]
  return out
}

function decodeSecret(secret: string): Buffer {
  const raw = Buffer.from(secret, 'base64url')
  if (raw.length !== 32) throw new Error('A route secret is 32 bytes, base64url')
  return raw
}

const hkdf = (secret: Buffer, info: string, length: number) =>
  new Uint8Array(hkdfSync('sha256', secret, Buffer.alloc(0), info, length))

/** The route ID a route secret names. */
export function routeId(secret: string): string {
  return base32(hkdf(decodeSecret(secret), 'toskar route id', 20))
}

/** What an address record says: the computer's ways in, and when it wrote them. */
export type AddressRecord = { addresses: string[]; at: number }

/** An address record that must be refused: reason is sealed, pin, or stale. */
export class RecordError extends Error {
  constructor(readonly reason: 'sealed' | 'pin' | 'stale') {
    super(`the address record was refused (${reason})`)
    this.name = 'RecordError'
  }
}

/** Opens an address record as docs/connecting.md says, or throws a RecordError. */
export function openRecord(blob: Uint8Array, secret: string, pin: string, now = Date.now() / 1000, maxAge = RECORD_MAX_AGE): AddressRecord {
  const raw = decodeSecret(secret)
  const route = routeId(secret)
  if (blob.length < 12 + 16) throw new RecordError('sealed')
  let rec: { payload: string; cert: string; alg: string; sig: string }
  try {
    const decipher = createDecipheriv('aes-256-gcm', hkdf(raw, 'toskar route key', 32), blob.subarray(0, 12))
    decipher.setAAD(Buffer.from(route))
    decipher.setAuthTag(blob.subarray(blob.length - 16))
    const plain = Buffer.concat([decipher.update(blob.subarray(12, blob.length - 16)), decipher.final()])
    rec = JSON.parse(plain.toString('utf8'))
  } catch {
    throw new RecordError('sealed')
  }
  const cert = Buffer.from(rec.cert ?? '', 'base64')
  if (pinOf(cert).toLowerCase() !== pin.toLowerCase()) throw new RecordError('pin')
  const payload = Buffer.from(rec.payload ?? '', 'base64')
  const sig = Buffer.from(rec.sig ?? '', 'base64')
  let body: { v?: number; route?: string; at?: number; addresses?: string[] }
  try {
    const key = new X509Certificate(cert).publicKey
    const kind = key.asymmetricKeyType
    const ok =
      (rec.alg === 'ecdsa-sha256' && kind === 'ec' && verifySignature('sha256', payload, { key, dsaEncoding: 'der' }, sig)) ||
      (rec.alg === 'rsa-pkcs1-sha256' && kind === 'rsa' && verifySignature('sha256', payload, key, sig)) ||
      (rec.alg === 'ed25519' && kind === 'ed25519' && verifySignature(null, payload, key, sig))
    if (!ok) throw new RecordError('pin')
    body = JSON.parse(payload.toString('utf8'))
  } catch {
    throw new RecordError('pin')
  }
  if (body.v !== 1 || body.route !== route || typeof body.at !== 'number') throw new RecordError('pin')
  if (now - body.at > maxAge || body.at - now > 300) throw new RecordError('stale')
  return { addresses: body.addresses ?? [], at: body.at }
}

// Choosing the way in.

const hostOf = (address: string) => split(address).host.toLowerCase()

/** Sends each request to the way in in use, choosing it again when it stops answering. */
class Router {
  way?: string
  path?: Path
  private choosing?: Promise<string>
  readonly dispatcher: Dispatcher
  /** Fetches address records from the relay, over its own certificate, checked as any website's is. */
  relayFetch: typeof fetch = (input, init) => fetch(input, init)

  constructor(readonly device: Device) {
    this.dispatcher = pinnedDispatcher(device.pin)
  }

  private async answers(address: string, timeoutMs: number): Promise<boolean> {
    try {
      // With the key: a computer that asks for one answers health only with it. The connection is pinned first.
      const response = await pinnedFetch(
        `https://${address}/api/v1/health`,
        { headers: { Authorization: `Bearer ${this.device.apiKey}` }, signal: AbortSignal.timeout(timeoutMs) },
        this.dispatcher,
      )
      return response.ok && ((await response.json()) as { status?: string }).status === 'ok'
    } catch (err) {
      if (isPinMismatch(err) && address === this.device.address) throw pinMismatch()
      return false
    }
  }

  async choose(): Promise<[Path, string]> {
    if (await this.answers(this.device.address, HOME_TIMEOUT)) return ['home', this.device.address]
    const route = this.device.route
    // Toskar's relay answers only for a subscription; without one, it isn't
    // asked, so nothing about this device reaches it.
    if (!route?.secret || (hostOf(route.relay) === TOSKAR_RELAY && !route.token)) {
      throw new ToskarError(0, 'UNREACHABLE', "The computer can't be reached")
    }
    let record: AddressRecord
    try {
      const response = await this.relayFetch(`https://${route.relay}/v1/routes/${route.id}/record`, {
        headers: route.token ? { Authorization: `Bearer ${route.token}` } : {},
        signal: AbortSignal.timeout(TRY_TIMEOUT),
      })
      if (!response.ok) throw new Error(`the relay answered ${response.status}`)
      record = openRecord(new Uint8Array(await response.arrayBuffer()), route.secret, this.device.pin)
    } catch (err) {
      throw new ToskarError(0, 'NO_RECORD', `No address record for the computer: ${(err as Error).message}`)
    }
    const relay = hostOf(route.relay)
    const ways = record.addresses.map((address): [Path, string] => [hostOf(address).endsWith(`.${relay}`) ? 'relay' : 'direct', address])
    const found = await new Promise<[Path, string] | null>((resolve) => {
      let left = ways.length
      let done = false
      if (left === 0) resolve(null)
      for (const [path, address] of ways) {
        void (async () => {
          if (path === 'relay') await new Promise((r) => setTimeout(r, RELAY_DELAY))
          // Another certificate at a way in is someone else's device there.
          const ok = !done && (await this.answers(address, TRY_TIMEOUT).catch(() => false))
          if (ok && !done) {
            done = true
            resolve([path, address])
          } else if (--left === 0 && !done) resolve(null)
        })()
      }
    })
    if (!found) throw new ToskarError(0, 'UNREACHABLE', "The computer can't be reached")
    return found
  }

  async current(): Promise<string> {
    if (this.way) return this.way
    this.choosing ??= this.choose()
      .then(([path, way]) => {
        this.path = path
        this.way = way
        return way
      })
      .finally(() => {
        this.choosing = undefined
      })
    return this.choosing
  }

  forget(way: string) {
    if (this.way === way) this.way = this.path = undefined
  }

  /** A fetch that reaches the computer by the way in use, pinned. */
  readonly fetch: typeof fetch = async (input, init) => {
    const way = await this.current()
    const request = new Request(input, init)
    const url = new URL(request.url)
    const { host, port } = split(way)
    url.hostname = host.includes(':') ? `[${host}]` : host
    url.port = String(port)
    const body = request.method === 'GET' || request.method === 'HEAD' ? undefined : await request.arrayBuffer()
    try {
      return await pinnedFetch(url, { method: request.method, headers: request.headers, body, signal: request.signal }, this.dispatcher)
    } catch (err) {
      if (isPinMismatch(err)) throw pinMismatch()
      this.forget(way)
      throw err
    }
  }
}

function isPinMismatch(err: unknown): boolean {
  for (let e = err as { code?: string; cause?: unknown } | undefined; e; e = e.cause as typeof e) {
    if (e instanceof ToskarError && e.code === 'PIN_MISMATCH') return true
  }
  return false
}

/**
 * Toskar, with pairing: as toskar's Toskar, and with { device } it connects
 * as a paired device, pinned, at home or away.
 *
 *     const device = await pair('192.168.1.20:7331', '123456', 'Kitchen tablet', confirm)
 *     const toskar = new Toskar({ device })
 */
export class Toskar extends Base {
  private readonly router?: Router

  constructor(options: ToskarOptions & { device?: Device } = {}) {
    const router = options.device ? new Router(options.device) : undefined
    super(
      router
        ? { ...options, baseUrl: `https://${options.device!.address}`, apiKey: options.device!.apiKey, fetch: router.fetch }
        : options,
    )
    this.router = router
  }

  /** How a paired device reaches its computer now: home, direct, or relay; undefined before its first request. */
  get path(): Path | undefined {
    return this.router?.path
  }

  /** Chooses the way in again, as after the network changed. */
  async reconnect(): Promise<Path | undefined> {
    if (!this.router) return undefined
    this.router.way = this.router.path = undefined
    await this.router.current()
    return this.router.path
  }
}

// Finding computers on the network.

/** A Toskar Core found on the network. */
export type Computer = {
  name: string
  nodeId: string
  version: string
  /** The API's host:port, to pair with: the first of addresses that answers. */
  address: string
  /** Every host:port the computer advertised. A computer can advertise addresses this device can't reach, such as a container network's. */
  addresses: string[]
  /** False when the API answers only on that computer: say to turn on Connect a device there, rather than that it's unreachable. */
  onNetwork: boolean
}

/** A computer from an mDNS answer, or null when it doesn't say where its API is. */
export function computerOf(instance: string, addresses: string[], txt: Record<string, unknown>): Computer | null {
  // The service's own port is for computers pairing with each other; the API's is in api_port.
  const port = Number(txt.api_port)
  if (!Number.isInteger(port) || port <= 0 || addresses.length === 0) return null
  const ways = [...addresses.filter((a) => !a.includes(':')), ...addresses.filter((a) => a.includes(':'))].map((ip) =>
    ip.includes(':') ? `[${ip}]:${port}` : `${ip}:${port}`,
  )
  return {
    name: String(txt.name ?? '') || instance,
    nodeId: String(txt.node_id ?? ''),
    version: String(txt.version ?? ''),
    address: ways[0],
    addresses: ways,
    onNetwork: String(txt.api_lan) !== 'false',
  }
}

/** The first of addresses that takes a TCP connection, tried together; the first, when none does. */
export async function reachable(addresses: string[]): Promise<string> {
  if (addresses.length < 2) return addresses[0]
  const { connect } = await import('node:net')
  const tries = addresses.map(
    (address) =>
      new Promise<string>((resolve, reject) => {
        const { host, port } = split(address)
        const socket = connect({ host, port, timeout: 700 })
        socket.once('connect', () => (socket.destroy(), resolve(address)))
        socket.once('timeout', () => (socket.destroy(), reject(new Error('timeout'))))
        socket.once('error', reject)
      }),
  )
  return Promise.any(tries).catch(() => addresses[0])
}

/**
 * Browses the network for computers running Toskar Core (_localai._tcp)
 * and returns those that answered within timeoutMs, by name. Needs the
 * optional bonjour-service package.
 */
export async function discover(timeoutMs = 3_000): Promise<Computer[]> {
  let Bonjour: new () => {
    find(opts: { type: string; protocol: 'tcp' }, onUp: (s: { name: string; addresses?: string[]; txt?: Record<string, unknown> }) => void): unknown
    destroy(): void
  }
  try {
    Bonjour = ((await import('bonjour-service')) as unknown as { Bonjour: typeof Bonjour }).Bonjour
  } catch {
    throw new Error('Finding computers on the network needs bonjour-service: npm install bonjour-service')
  }
  const found = new Map<string, Computer>()
  const bonjour = new Bonjour()
  try {
    bonjour.find({ type: 'localai', protocol: 'tcp' }, (s) => {
      const c = computerOf(s.name, s.addresses ?? [], s.txt ?? {})
      if (c) found.set(c.nodeId + c.address, c)
    })
    await new Promise((resolve) => setTimeout(resolve, timeoutMs))
  } finally {
    bonjour.destroy()
  }
  const computers = await Promise.all([...found.values()].map(async (c) => ({ ...c, address: await reachable(c.addresses) })))
  return computers.sort((a, b) => a.name.localeCompare(b.name))
}
