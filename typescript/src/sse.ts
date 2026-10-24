/** One server-sent event: its name ("message" without one) and its data. */
export type ServerSentEvent = { event: string; data: string }

/**
 * Reads server-sent events from a response body as they arrive. Comments,
 * such as ": ping", are skipped.
 */
export async function* readEvents(body: ReadableStream<Uint8Array>): AsyncGenerator<ServerSentEvent> {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  try {
    for (;;) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n')
      let end: number
      while ((end = buffer.indexOf('\n\n')) >= 0) {
        const event = parseBlock(buffer.slice(0, end))
        buffer = buffer.slice(end + 2)
        if (event) yield event
      }
    }
    const last = parseBlock(buffer)
    if (last) yield last
  } finally {
    reader.releaseLock()
  }
}

function parseBlock(block: string): ServerSentEvent | null {
  let event = 'message'
  const data: string[] = []
  for (const line of block.split('\n')) {
    const colon = line.indexOf(':')
    if (colon === 0) continue
    const field = colon < 0 ? line : line.slice(0, colon)
    const value = colon < 0 ? '' : line.slice(colon + 1).replace(/^ /, '')
    if (field === 'event') event = value
    else if (field === 'data') data.push(value)
  }
  return data.length ? { event, data: data.join('\n') } : null
}
