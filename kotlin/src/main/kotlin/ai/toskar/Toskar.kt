// The Kotlin and Java SDK for Toskar: local AI across your own computers.
//
//     Toskar().use { toskar ->
//         toskar.chatStream(ChatRequest(message = "Hi")).use { events ->
//             for (event in events) if (event is ChatEvent.Token) print(event.text)
//         }
//     }
//
// `api` reaches every route, typed from Toskar Core's API spec:
//
//     val models = toskar.api.listModels()

package ai.toskar

import ai.toskar.api.Api
import ai.toskar.api.ChatAnswer
import ai.toskar.api.ChatDone
import ai.toskar.api.ChatRequest
import ai.toskar.api.ChatToken
import ai.toskar.api.Event
import ai.toskar.api.GenerationMetrics
import ai.toskar.api.VersionResponse
import java.io.Closeable
import java.io.IOException
import java.time.Duration
import java.util.concurrent.ThreadLocalRandom
import kotlinx.serialization.json.Json
import kotlinx.serialization.serializer
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response

/**
 * A connection to Toskar Core. Every call waits for its answer, so call it
 * off the main thread. Close it when you're done, to free its connections.
 *
 * @param url Where Toskar Core answers. Default: `TOSKAR_URL`, or
 *   [DEFAULT_URL], this computer.
 * @param key The API key for any address other than this computer's
 *   loopback. Default: `TOSKAR_API_KEY`.
 * @param retries How many times a safe request (GET, HEAD, OPTIONS) that
 *   fails to connect or answers 502, 503, or 504 is retried. A chat is never
 *   retried: it could answer twice.
 * @param timeout How long to wait for an answer to start. A streamed answer
 *   then runs for as long as it takes.
 * @param httpClient The OkHttpClient to send requests with, in place of one
 *   made with [timeout]. Toskar doesn't close it.
 * @param headers Headers to add to every request.
 */
public class Toskar internal constructor(
    url: String?,
    key: String?,
    retries: Int,
    timeout: Duration,
    httpClient: OkHttpClient?,
    headers: Map<String, String>,
    private val router: Router?,
    owns: Boolean,
    env: (String) -> String?,
) : Closeable {
    internal constructor(
        url: String?, key: String?, retries: Int, timeout: Duration, httpClient: OkHttpClient?,
        headers: Map<String, String>, env: (String) -> String?,
    ) : this(url, key, retries, timeout, httpClient, headers, null, httpClient == null, env)

    @JvmOverloads
    public constructor(
        url: String? = null,
        key: String? = null,
        retries: Int = 2,
        timeout: Duration = Duration.ofSeconds(60),
        httpClient: OkHttpClient? = null,
        headers: Map<String, String> = emptyMap(),
    ) : this(url, key, retries, timeout, httpClient, headers, System::getenv)

    /**
     * Connects as a paired device: every connection pinned to its
     * computer's certificate, at home when it answers, and otherwise directly
     * or through its relay, from its address record.
     */
    @JvmOverloads
    public constructor(device: Device, retries: Int = 2, timeout: Duration = Duration.ofSeconds(60)) :
        this(device, retries, timeout, OkHttpClient())

    internal constructor(device: Device, retries: Int, timeout: Duration, relayClient: OkHttpClient) : this(
        "https://${device.address}", device.apiKey, retries, timeout,
        Pinning(device.pin).client(timeout, relayClient), emptyMap(),
        Router(device, Pinning(device.pin).client(timeout, relayClient), relayClient), true, { null },
    )

    /**
     * How the client reaches its paired computer now, or null before its
     * first request, or for a client that isn't a paired device.
     */
    public val path: ConnectionPath? get() = router?.path

    /** Chooses the way in again, as after the network changed, and says which it found. */
    public fun reconnect(): ConnectionPath? {
        val router = router ?: return null
        router.forget()
        router.current()
        return router.path
    }

    /** Where Toskar Core answers. */
    public val url: String

    /** Every route, typed from Toskar Core's API spec. */
    public val api: Api = Api(this)

    private val base: HttpUrl
    private val sent: List<Pair<String, String>>
    private val retries = maxOf(0, retries)
    private val ownsClient = owns
    internal val http: OkHttpClient

    init {
        val raw = url?.takeIf { it.isNotEmpty() } ?: env("TOSKAR_URL")?.takeIf { it.isNotEmpty() } ?: DEFAULT_URL
        base = raw.trimEnd('/').toHttpUrlOrNull()
            ?: throw ToskarException(0, "BAD_URL", "$raw isn't an http or https address")
        this.url = raw.trimEnd('/')
        sent = buildList {
            // Core answers 426 CONTRACT_MISMATCH to a client of another major version.
            add("Toskar-Client-Contract" to CONTRACT_VERSION)
            (key ?: env("TOSKAR_API_KEY"))?.takeIf { it.isNotEmpty() }?.let { add("Authorization" to "Bearer $it") }
            headers.entries.sortedBy { it.key }.forEach { add(it.key to it.value) }
        }
        http = httpClient ?: OkHttpClient.Builder()
            .connectTimeout(timeout)
            .readTimeout(timeout)
            .writeTimeout(timeout)
            .build()
    }

    /** Asks once and waits for the whole answer. */
    public fun chat(request: ChatRequest): ChatAnswer = api.chat(request.copy(stream = false))

    /**
     * Asks and yields the answer as it's written: tokens, then done. A
     * failure throws a [ToskarException] with its code, such as
     * [ErrorCodes.NO_MODEL_INSTALLED], and ends the stream. Close it to stop
     * early.
     */
    public fun chatStream(request: ChatRequest): EventStream<ChatEvent> {
        val response = send(
            "POST", "/api/v1/chat", emptyList(), emptyList(), emptyList(),
            json(request.copy(stream = true)), "text/event-stream", stream = true,
        )
        val events = ServerSentEvents(response)
        var finished = false
        return EventStream(response) {
            while (!finished) {
                val event = events.next()
                    // Every stream ends with done or an error, so one that just stops was cut off.
                    ?: throw ToskarException(200, "CONNECTION_LOST", "The answer stopped before it finished")
                when (event.name) {
                    "token" -> return@EventStream ChatEvent.Token(JSON.decodeFromString<ChatToken>(event.data).content)
                    "done" -> {
                        finished = true
                        val done = runCatching { JSON.decodeFromString<ChatDone>(event.data) }.getOrNull()
                        return@EventStream ChatEvent.Done(done?.metrics)
                    }
                    "error_code" -> throw ToskarException.of(200, event.data)
                    "error" -> throw ToskarException(200, ErrorCodes.CHAT_FAILED, event.data.ifEmpty { "The chat failed" })
                }
            }
            null
        }
    }

    /**
     * Yields what happens on Toskar as it happens, such as models loading
     * and automations running, until you close it.
     */
    public fun events(): EventStream<Event> {
        val response = send("GET", "/api/v1/events", emptyList(), emptyList(), emptyList(), null, "text/event-stream", stream = true)
        val events = ServerSentEvents(response)
        return EventStream(response) {
            while (true) {
                val event = events.next() ?: return@EventStream null
                if (event.data.isNotEmpty()) {
                    return@EventStream JSON.decodeFromString<Event>(event.data)
                }
            }
            @Suppress("UNREACHABLE_CODE")
            null
        }
    }

    /** Core's version and its client contract. */
    public fun version(): VersionResponse = api.getVersion()

    /** Frees the connections, unless the OkHttpClient was given. */
    public override fun close() {
        if (ownsClient) {
            http.dispatcher.executorService.shutdown()
            http.connectionPool.evictAll()
        }
    }

    // The generated Api calls these.

    @PublishedApi
    internal inline fun <reified T> call(
        method: String,
        path: String,
        params: List<String>,
        query: List<Pair<String, Any?>> = emptyList(),
        headers: List<Pair<String, Any?>> = emptyList(),
        body: RequestBody? = null,
    ): T {
        val accept = when (T::class) {
            Unit::class -> "*/*"
            ByteArray::class -> "*/*"
            else -> "application/json"
        }
        send(method, path, params, query, headers, body, accept, stream = false).use { response ->
            val bytes = response.body.bytes()
            return when (T::class) {
                Unit::class -> Unit as T
                ByteArray::class -> bytes as T
                else -> JSON.decodeFromString(serializer<T>(), bytes.decodeToString())
            }
        }
    }

    @PublishedApi
    internal inline fun <reified T> json(body: T): RequestBody =
        JSON.encodeToString(serializer<T>(), body).toRequestBody(JSON_TYPE)

    @PublishedApi
    internal fun raw(body: Any?, media: String): RequestBody? = when (body) {
        null -> null
        is ByteArray -> body.toRequestBody(media.toMediaType())
        else -> body.toString().toRequestBody(media.toMediaType())
    }

    /**
     * Sends a request, retrying a safe one, and throws a [ToskarException]
     * for an error answer. The caller closes the response.
     */
    @PublishedApi
    internal fun send(
        method: String,
        path: String,
        params: List<String>,
        query: List<Pair<String, Any?>>,
        headers: List<Pair<String, Any?>>,
        body: RequestBody?,
        accept: String,
        stream: Boolean,
    ): Response {
        fun target(root: HttpUrl) = root.newBuilder().apply {
            var next = 0
            for (segment in path.split('/').filter { it.isNotEmpty() }) {
                addPathSegment(if (segment.startsWith("{")) params[next++] else segment)
            }
            for ((name, value) in query) {
                when (value) {
                    null -> {}
                    is Iterable<*> -> value.forEach { addQueryParameter(name, it.toString()) }
                    else -> addQueryParameter(name, value.toString())
                }
            }
        }.build()
        val request = Request.Builder().url(target(base)).apply {
            sent.forEach { (name, value) -> header(name, value) }
            headers.forEach { (name, value) -> if (value != null) header(name, value.toString()) }
            header("Accept", accept)
            method(method, body ?: if (method == "POST" || method == "PUT" || method == "PATCH") ByteArray(0).toRequestBody() else null)
        }.build()
        // A stream waits for its answer to start, then for as long as it runs.
        val client = if (stream) http.newBuilder().readTimeout(Duration.ZERO).build() else http
        val attempts = if (method in SAFE) 1 + retries else 1
        var attempt = 1
        while (true) {
            // A paired device's way in, chosen again after one stops answering.
            val way = router?.current()
            val response = try {
                val call = if (way == null) request else request.newBuilder().url(target(baseOf(way))).build()
                client.newCall(call).execute()
            } catch (e: IOException) {
                if (e.isPinMismatch()) {
                    throw ToskarException(0, "PIN_MISMATCH", "The computer's certificate isn't the one paired with", cause = e)
                }
                way?.let { router?.forget(it) }
                if (attempt >= attempts) {
                    throw ToskarException(0, "CONNECTION_FAILED", "Couldn't reach Toskar at $url: ${e.message}", cause = e)
                }
                null
            }
            if (response != null) {
                if (response.code < 300) {
                    return response
                }
                if (attempt >= attempts || response.code !in RETRIED) {
                    val text = response.use { r -> r.body.source().apply { request(ERROR_LIMIT) }.buffer.readUtf8() }
                    throw ToskarException.of(response.code, text)
                }
                response.close()
            }
            Thread.sleep((200L shl (attempt - 1)) + ThreadLocalRandom.current().nextLong(100))
            attempt++
        }
    }

    public companion object {
        /**
         * Pairs with the computer at address (host:port, as found or typed)
         * using the code Connect a device shows on it. The device must be on
         * the computer's local network.
         *
         * @param confirm Shows the person the short pin, such as 9B80-D9D9,
         *   and says whether the computer shows the same. Null skips the
         *   check, as a script with no one to ask does.
         */
        @JvmStatic
        @JvmOverloads
        public fun pair(address: String, code: String, deviceName: String, confirm: ShortPinCheck? = null): Device =
            Pairing.pair(address, code, deviceName, confirm)

        /** This computer's Toskar Core, which needs no key. */
        public const val DEFAULT_URL: String = "http://127.0.0.1:7331"

        /** How the SDK reads and writes Core's JSON: a newer Core's fields and values are kept out, not failed on. */
        @PublishedApi
        internal val JSON: Json = Json {
            ignoreUnknownKeys = true
            explicitNulls = false
            coerceInputValues = true
        }

        @PublishedApi
        internal val JSON_TYPE: okhttp3.MediaType = "application/json".toMediaType()
        private val SAFE = setOf("GET", "HEAD", "OPTIONS")
        private val RETRIED = setOf(502, 503, 504)

        /** The most of an error answer read; Core's are small. */
        private const val ERROR_LIMIT = 1L shl 20
    }
}

/** One event of a streamed chat. */
public sealed class ChatEvent {
    /** The next piece of the answer. */
    public data class Token(public val text: String) : ChatEvent()

    /** The answer is finished and saved, with what the runtime measured when it reported it. */
    public data class Done(public val metrics: GenerationMetrics?) : ChatEvent()
}
