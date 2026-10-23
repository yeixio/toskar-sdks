// Writes spec/openapi.sdk.json, the spec every SDK is generated from:
// Toskar Core's spec, with each enum turned into a note in its description.
//
// The client contract may add values to an enum in a minor version, and a
// client must accept what it doesn't know yet (toskar-core#666). Generated
// SDKs reject values outside an enum, so the SDKs see these as strings and
// document the values instead.
import { readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { parse } from 'yaml'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const spec = parse(readFileSync(join(root, 'spec', 'openapi.yaml'), 'utf8'))

const openEnums = (node) => {
  if (Array.isArray(node)) return node.forEach(openEnums)
  if (!node || typeof node !== 'object') return
  if (Array.isArray(node.enum) && node.type === 'string') {
    const values = node.enum.map((v) => `\`${v}\``).join(', ')
    node.description = [node.description, `Known values: ${values}; others may be added.`].filter(Boolean).join(' ')
    delete node.enum
  }
  Object.values(node).forEach(openEnums)
}
openEnums(spec)

writeFileSync(join(root, 'spec', 'openapi.sdk.json'), `${JSON.stringify(spec, null, 2)}\n`)
console.log(`spec/openapi.sdk.json: ${spec.info.title} ${spec.info.version}`)
