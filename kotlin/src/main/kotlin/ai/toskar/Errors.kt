package ai.toskar

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject

/**
 * An error from Toskar Core: `{"error": {"code", "message", "details"}}`.
 *
 * [code] is stable, such as [ErrorCodes.NO_MODEL_INSTALLED]; [message] is
 * English text for logs; [details] has the values the message needs.
 *
 *     try { … } catch (e: ToskarException) { if (e.code == ErrorCodes.NO_MODEL_INSTALLED) … }
 *
 * The SDK's own codes, for what goes wrong before Toskar Core answers, are
 * `CONNECTION_FAILED` (with the cause), `CONNECTION_LOST` (a stream cut off),
 * `BAD_URL`, and `HTTP_<status>` for an answer that isn't Toskar's.
 */
public class ToskarException @JvmOverloads constructor(
    /** The HTTP status Toskar answered with, or 0 when it didn't answer. */
    public val status: Int,
    public val code: String,
    message: String,
    public val details: JsonObject? = null,
    cause: Throwable? = null,
) : RuntimeException(message, cause) {
    override val message: String get() = super.message ?: code

    override fun toString(): String = "toskar: $message ($status $code)"

    @Serializable
    private class Envelope(val error: Inner? = null)

    @Serializable
    private class Inner(val code: String = "", val message: String? = null, val details: JsonObject? = null)

    internal companion object {
        /** The error a response body describes, or a generic one for a body that isn't Toskar's. */
        fun of(status: Int, body: String): ToskarException {
            // A stream's error_code event is the inner object itself.
            val e = runCatching { Toskar.JSON.decodeFromString<Envelope>(body).error }.getOrNull()
                ?: runCatching { Toskar.JSON.decodeFromString<Inner>(body) }.getOrNull()
            if (e != null && e.code.isNotEmpty()) {
                return ToskarException(status, e.code, e.message ?: e.code, e.details)
            }
            return ToskarException(status, "HTTP_$status", "Toskar answered $status")
        }
    }
}
