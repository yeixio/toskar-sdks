// Runs the shared conformance cases (conformance/README.md) with the
// TypeScript SDK, from its build (npm run build).
import { readFileSync } from 'node:fs'

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
  throw new Error('usage: conformance.mjs pair <address> <code> | call <device.json>')
}

try {
  console.log(JSON.stringify(await run(process.argv.slice(2))))
} catch (e) {
  const code = e instanceof ToskarError ? e.code : 'ERROR'
  console.log(JSON.stringify({ error: { code, message: String(e?.message ?? e) } }))
  process.exitCode = 1
}
