// Runs the shared conformance cases (conformance/README.md) with the
// TypeScript SDK, from its build (npm run build).
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { basename } from 'node:path'

import { pair, Toskar, ToskarError, unwrap } from './dist/node.js'

/** The device as conformance/README.md writes it: snake_case, as the Go and Python SDKs keep it. */
const toFile = (d) => ({ address: d.address, api_key: d.apiKey, pin: d.pin, ...(d.route && { route: d.route }) })
const fromFile = (d) => ({ address: d.address, apiKey: d.api_key, pin: d.pin, ...(d.route && { route: d.route }) })

async function run([command, ...args]) {
  if (command === 'pair' && args.length === 2) {
    let short = ''
    const device = await pair(args[0], args[1], 'Node conformance', (s) => ((short = s), true))
    return { device: toFile(device), short_pin: short }
  }
  if (command === 'call' && args.length === 1) {
    const toskar = new Toskar({ device: fromFile(JSON.parse(readFileSync(args[0], 'utf8'))), retries: 0 })
    const settings = unwrap(await toskar.api.GET('/api/v1/settings'))
    return { path: toskar.path, node_name: settings.node_name }
  }
  // The rest connect as TOSKAR_URL and TOSKAR_API_KEY say.
  const toskar = new Toskar({ retries: 0 })
  if (command === 'chat' && args.length === 2) {
    return { content: (await toskar.chat({ model_id: args[0], message: args[1] })).content }
  }
  if (command === 'stream' && args.length === 2) {
    let content = ''
    let tokens = 0
    let done = false
    for await (const e of toskar.chatStream({ model_id: args[0], message: args[1] })) {
      if (e.type === 'token') (content += e.content), tokens++
      if (e.type === 'done') done = true
    }
    return { content, tokens, done }
  }
  if (command === 'events' && args.length === 3) return events(toskar, ...args)
  if (command === 'upload' && args.length === 1) {
    const content_base64 = readFileSync(args[0]).toString('base64')
    const a = unwrap(await toskar.api.POST('/api/v1/artifacts', { body: { name: basename(args[0]), content_base64 } }))
    return { id: a.id, name: a.name, size_bytes: a.size_bytes }
  }
  if (command === 'download' && args.length === 1) {
    const bytes = Buffer.from(
      unwrap(await toskar.api.GET('/api/v1/artifacts/{id}/content', { params: { path: { id: args[0] } }, parseAs: 'arrayBuffer' })),
    )
    return { sha256: createHash('sha256').update(bytes).digest('hex'), size_bytes: bytes.length }
  }
  throw new Error(
    'usage: conformance.mjs pair <address> <code> | call <device.json> | chat|stream <model> <message> | events <model> <message> <until> | upload <file> | download <id>',
  )
}

/** Listens to the events stream, asks once, and lists the events' types until one of type until. */
async function events(toskar, model, message, until) {
  const stop = new AbortController()
  const timer = setTimeout(() => stop.abort(), 30_000)
  const types = []
  const listening = (async () => {
    for await (const e of toskar.events({ signal: stop.signal })) {
      types.push(e.type)
      if (e.type === until) return
    }
  })()
  // Time to subscribe before asking.
  await new Promise((r) => setTimeout(r, 1_000))
  await toskar.chat({ model_id: model, message })
  try {
    await listening
  } finally {
    clearTimeout(timer)
    stop.abort()
  }
  return { types }
}

try {
  console.log(JSON.stringify(await run(process.argv.slice(2))))
} catch (e) {
  const code = e instanceof ToskarError ? e.code : 'ERROR'
  console.log(JSON.stringify({ error: { code, message: String(e?.message ?? e) } }))
  process.exitCode = 1
}
