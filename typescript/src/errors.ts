import type { ErrorCode } from './generated/codes.js'

/**
 * An error from Toskar Core: {"error": {"code", "message", "details"}}.
 * `code` is stable, such as MODEL_NOT_INSTALLED (see ErrorCodes); `message`
 * is English text for logs; `details` has the values the message needs.
 */
export class ToskarError extends Error {
  readonly status: number
  readonly code: ErrorCode
  readonly details: Record<string, unknown>

  constructor(status: number, code: ErrorCode, message: string, details: Record<string, unknown> = {}) {
    super(message)
    this.name = 'ToskarError'
    this.status = status
    this.code = code
    this.details = details
  }

  /** The error a response body describes, or a generic one for a body that isn't Toskar's. */
  static from(status: number, body: unknown): ToskarError {
    const error = (body as { error?: { code?: string; message?: string; details?: Record<string, unknown> } } | null)?.error
    if (error?.code) return new ToskarError(status, error.code, error.message ?? error.code, error.details ?? {})
    return new ToskarError(status, `HTTP_${status}`, `Toskar answered ${status}`)
  }
}
