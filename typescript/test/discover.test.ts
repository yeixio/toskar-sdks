import { describe, expect, it } from 'vitest'

import { createServer } from 'node:net'
import type { AddressInfo } from 'node:net'

import { computerOf, reachable } from '../src/node.js'

describe('discover', () => {
  it('reads where the API is from the TXT record', () => {
    const txt = { node_id: 'n1', name: 'Studio', version: '1.11.0', pairing: 'false', api_port: '7331', api_lan: 'true' }
    expect(computerOf('studio', ['fe80::1', '192.168.1.20'], txt)).toEqual({ name: 'Studio', nodeId: 'n1', version: '1.11.0', address: '192.168.1.20:7331', addresses: ['192.168.1.20:7331', '[fe80::1]:7331'], onNetwork: true })
    expect(computerOf('studio', ['fe80::1'], { node_id: 'n2', api_port: '7331', api_lan: 'false' })).toMatchObject({ name: 'studio', address: '[fe80::1]:7331', onNetwork: false })
    expect(computerOf('studio', ['192.168.1.20'], { node_id: 'n3' })).toBeNull()
  })

  it('prefers an address that answers', async () => {
    const server = createServer((s) => s.destroy())
    await new Promise<void>((r) => server.listen(0, '127.0.0.1', r))
    const here = `127.0.0.1:${(server.address() as AddressInfo).port}`
    // 10.255.255.1 stands for an address that doesn't route from here, such as a container network's.
    expect(await reachable(['10.255.255.1:7331', here])).toBe(here)
    await new Promise((r) => server.close(r))
  })
})
