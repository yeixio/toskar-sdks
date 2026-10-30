package ai.toskar

import ai.toskar.api.ChatRequest
import ai.toskar.api.GenerationMetrics
import java.time.Duration
import java.time.Instant
import kotlin.test.AfterTest
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNull
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.jsonPrimitive
import mockwebserver3.MockResponse
import mockwebserver3.MockWebServer

const val VERSION = """{"version":"1.12.0","contract":{"version":"1.60","major":1},"commit":"abc","build_date":"2026-10-29","license":"AGPL-3.0","product":"Toskar","source":"https://github.com/yeixio/toskar-core"}"""
const val SSE = "text/event-stream"

class ClientTest {
    private val core = MockWebServer().apply { start() }

    @AfterTest
    fun stop() = core.close()

    private fun toskar(retries: Int = 2, key: String? = null, env: Map<String, String> = emptyMap()) =
        Toskar(core.url("/").toString(), key, retries, Duration.ofSeconds(5), null, emptyMap(), env::get)

    private fun answer(body: String, status: Int = 200, type: String = "application/json") =
        core.enqueue(MockResponse.Builder().code(status).setHeader("Content-Type", type).body(body).build())

    @Test
    fun saysItsContractAndSendsTheKey() {
        answer(VERSION)
        assertEquals("1.12.0", toskar(key = "secret").version().version)
        val r = core.takeRequest()
        assertEquals(CONTRACT_VERSION, r.headers["Toskar-Client-Contract"])
        assertEquals("Bearer secret", r.headers["Authorization"])
        assertEquals("/api/v1/version", r.url.encodedPath)
    }

    @Test
    fun readsTheKeyAndAddressFromTheEnvironment() {
        answer(VERSION)
        val t = Toskar(null, null, 0, Duration.ofSeconds(5), null, emptyMap(), mapOf("TOSKAR_URL" to core.url("/").toString(), "TOSKAR_API_KEY" to "env")::get)
        t.version()
        assertEquals("Bearer env", core.takeRequest().headers["Authorization"])
        assertEquals(Toskar.DEFAULT_URL, Toskar(null, null, 0, Duration.ofSeconds(5), null, emptyMap()) { null }.url)
    }

    @Test
    fun chatsWaitingForTheWholeAnswer() {
        answer("""{"content":"Hello there","metrics":null}""")
        assertEquals("Hello there", toskar().chat(ChatRequest(message = "Hi")).content)
        val r = core.takeRequest()
        assertEquals("application/json", r.headers["Accept"])
        // Unset fields stay out of the request, and stream says how it's answered.
        assertEquals("""{"message":"Hi","stream":false}""", r.body!!.utf8())
    }

    @Test
    fun streamsAnAnswerAsItIsWritten() {
        answer(
            """
            : ping

            event: token
            data: {"content":"Hel"}

            event: token
            data: {"content":"lo"}

            event: done
            data: {"metrics":{"prompt_tokens":3,"completion_tokens":2,"total_tokens":5,"ttft_ms":1,"prompt_ms":1,"eval_ms":1,"total_ms":2,"prompt_tok_per_sec":3,"eval_tok_per_sec":2}}


            """.trimIndent(),
            type = SSE,
        )
        var text = ""
        var metrics: GenerationMetrics? = null
        toskar().chatStream(ChatRequest(message = "Hi")).use { events ->
            for (event in events) {
                when (event) {
                    is ChatEvent.Token -> text += event.text
                    is ChatEvent.Done -> metrics = event.metrics
                }
            }
        }
        assertEquals("Hello", text)
        assertEquals(2L, metrics?.completionTokens)
        assertEquals(SSE, core.takeRequest().headers["Accept"])
    }

    @Test
    fun aStreamedFailureHasItsCode() {
        answer("event: error_code\ndata: {\"code\":\"NO_MODEL_INSTALLED\",\"message\":\"Install a model\"}\n\n", type = SSE)
        val e = assertFailsWith<ToskarException> { toskar().chatStream(ChatRequest(message = "Hi")).toList() }
        assertEquals(ErrorCodes.NO_MODEL_INSTALLED, e.code)
        assertEquals("Install a model", e.message)
    }

    @Test
    fun aCutOffStreamSaysSo() {
        answer("event: token\ndata: {\"content\":\"Hel\"}\n\n", type = SSE)
        val e = assertFailsWith<ToskarException> { toskar().chatStream(ChatRequest(message = "Hi")).toList() }
        assertEquals("CONNECTION_LOST", e.code)
    }

    @Test
    fun anErrorAnswerIsAToskarException() {
        answer("""{"error":{"code":"MODEL_NOT_FOUND","message":"No such model","details":{"model_id":"x"}}}""", status = 404)
        val e = assertFailsWith<ToskarException> { toskar().api.listModels() }
        assertEquals(404, e.status)
        assertEquals(ErrorCodes.MODEL_NOT_FOUND, e.code)
        assertEquals("No such model", e.message)
        assertEquals("x", e.details?.get("model_id")?.jsonPrimitive?.content)

        // A body that isn't Toskar's still says what happened.
        answer("oops", status = 500, type = "text/plain")
        assertEquals("HTTP_500", assertFailsWith<ToskarException> { toskar().version() }.code)
    }

    @Test
    fun retriesASafeRequestButNeverAChat() {
        answer("", status = 503)
        answer("", status = 502)
        answer(VERSION)
        toskar().version()
        assertEquals(3, core.requestCount)

        repeat(4) { answer("", status = 503) }
        assertEquals(503, assertFailsWith<ToskarException> { toskar().version() }.status)
        assertEquals(6, core.requestCount)

        answer("", status = 503)
        answer("""{"content":"twice"}""")
        assertEquals(503, assertFailsWith<ToskarException> { toskar().chat(ChatRequest(message = "Hi")) }.status)
        assertEquals(7, core.requestCount)
    }

    @Test
    fun aComputerThatIsntThereSaysSo() {
        val gone = core.url("/").toString()
        core.close()
        val e = assertFailsWith<ToskarException> {
            Toskar(gone, null, 1, Duration.ofSeconds(5), null, emptyMap()) { null }.version()
        }
        assertEquals("CONNECTION_FAILED", e.code)
        assertEquals(0, e.status)
    }

    @Test
    fun readsTheEventsStream() {
        answer(
            """
            data: {"id":"e1","type":"model.loaded","contract":"1.60","timestamp":"2026-10-29T16:04:05.123456789Z","payload":{"model_id":"m1"}}

            data: {"id":"e2","type":"model.unloaded","contract":"1.60","timestamp":"2026-10-29T16:04:06Z","payload":{}}


            """.trimIndent(),
            type = SSE,
        )
        val seen = toskar().events().use { it.toList() }
        assertEquals(listOf("model.loaded", "model.unloaded"), seen.map { it.type })
        assertEquals(Instant.parse("2026-10-29T16:04:05.123456789Z"), seen.first().timestamp)
    }

    @Test
    fun putsParametersInThePathAndQuery() {
        answer("[]")
        toskar().api.listModels()
        core.takeRequest()
        answer("""{"error":{"code":"NOT_FOUND","message":"x"}}""", status = 404)
        assertFailsWith<ToskarException> { toskar(retries = 0).api.deleteMemory("a/b c") }
        val r = core.takeRequest()
        assertEquals("DELETE", r.method)
        assertEquals("/api/v1/memory/a%2Fb%20c", r.url.encodedPath)
    }

    @Test
    fun readsCoreTimes() {
        val json = Toskar.JSON
        fun read(text: String) = json.decodeFromJsonElement(CoreInstant, JsonPrimitive(text))
        assertEquals(1_793_289_845L, read("2026-10-29T16:04:05Z").epochSecond)
        assertEquals(Instant.ofEpochSecond(1_793_318_645L, 500_000_000), read("2026-10-29T16:04:05.5-08:00"))
        assertFailsWith<Exception> { read("yesterday") }
    }

    @Test
    fun keepsOutWhatANewerCoreAdds() {
        answer("""{"content":"Hi","metrics":null,"new_field":{"a":1}}""")
        val a = toskar().chat(ChatRequest(message = "Hi"))
        assertEquals("Hi", a.content)
        assertNull(a.metrics)
    }
}
