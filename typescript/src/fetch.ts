/** How a request is retried and timed out. */
export type RetryOptions = {
  /** Retries for safe requests (GET, HEAD, OPTIONS) that fail to connect or answer 502, 503, or 504. */
  retries: number
  /** Milliseconds a request may take before it's aborted; 0 waits as long as it takes. */
  timeoutMs: number
}

const safe = new Set(['GET', 'HEAD', 'OPTIONS'])
const retryable = new Set([502, 503, 504])

/**
 * Wraps fetch with a timeout and, for safe requests, retries with backoff.
 * Streams aren't cut off: the timeout covers waiting for the response, not
 * reading it.
 */
export function withRetries(base: typeof fetch, { retries, timeoutMs }: RetryOptions): typeof fetch {
  return async (input, init) => {
    const request = new Request(input, init)
    const attempts = safe.has(request.method) ? retries + 1 : 1
    for (let attempt = 1; ; attempt++) {
      const timer = timeoutMs > 0 ? new AbortController() : undefined
      const timeout = timer && setTimeout(() => timer.abort(new DOMException('Toskar took too long to answer', 'TimeoutError')), timeoutMs)
      const signal = timer ? anySignal([request.signal, timer.signal]) : request.signal
      try {
        const response = await base(request.clone(), { signal })
        if (attempt < attempts && retryable.has(response.status)) {
          await response.body?.cancel()
        } else {
          return response
        }
      } catch (error) {
        if (attempt >= attempts || request.signal.aborted) throw error
      } finally {
        if (timeout) clearTimeout(timeout)
      }
      await new Promise((resolve) => setTimeout(resolve, 200 * 2 ** (attempt - 1) + Math.random() * 100))
    }
  }
}

function anySignal(signals: AbortSignal[]): AbortSignal {
  if ('any' in AbortSignal) return AbortSignal.any(signals)
  const controller = new AbortController()
  for (const s of signals) {
    if (s.aborted) controller.abort(s.reason)
    else s.addEventListener('abort', () => controller.abort(s.reason), { once: true })
  }
  return controller.signal
}
