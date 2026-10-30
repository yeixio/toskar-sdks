package ai.toskar

import java.io.Closeable
import okhttp3.Response

/**
 * A stream of events, read as you iterate. Close it to stop early; it
 * closes itself when it ends. From Java:
 *
 *     try (EventStream<ChatEvent> events = toskar.chatStream(request)) {
 *         for (ChatEvent event : events) { … }
 *     }
 */
public class EventStream<T : Any> internal constructor(
    private val response: Response,
    private val read: () -> T?,
) : Iterable<T>, Closeable {
    private var next: T? = null
    private var ended = false

    override fun iterator(): Iterator<T> = object : Iterator<T> {
        override fun hasNext(): Boolean {
            if (next == null && !ended) {
                next = try {
                    read()
                } catch (e: Throwable) {
                    close()
                    throw e
                }
                if (next == null) {
                    close()
                }
            }
            return next != null
        }

        override fun next(): T {
            if (!hasNext()) throw NoSuchElementException()
            return next!!.also { next = null }
        }
    }

    override fun close() {
        ended = true
        response.close()
    }
}

/** One server-sent event. */
internal class ServerSentEvent(val name: String, val data: String)

/** Reads server-sent events from a response, one at a time. */
internal class ServerSentEvents(response: Response) {
    private val source = response.body.source()

    /** The next event, or null at the end of the stream. */
    fun next(): ServerSentEvent? {
        var name = "message"
        val data = StringBuilder()
        var any = false
        while (true) {
            val line = try {
                source.readUtf8Line()
            } catch (e: java.io.IOException) {
                throw ToskarException(200, "CONNECTION_LOST", "The answer stopped before it finished", cause = e)
            } ?: return if (any) ServerSentEvent(name, data.toString()) else null
            if (line.isEmpty()) {
                if (any) return ServerSentEvent(name, data.toString())
                continue
            }
            if (line.startsWith(":")) continue
            val field = line.substringBefore(':')
            val value = line.substringAfter(':', "").removePrefix(" ")
            when (field) {
                "event" -> { name = value; any = true }
                "data" -> { if (data.isNotEmpty()) data.append('\n'); data.append(value); any = true }
            }
        }
    }
}
