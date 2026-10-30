package ai.toskar

import java.io.File
import java.net.ServerSocket
import java.security.SecureRandom
import java.security.Signature
import java.time.Duration
import java.time.Instant
import java.util.Base64
import javax.crypto.Cipher
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec
import kotlin.test.AfterTest
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNull
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import mockwebserver3.Dispatcher
import mockwebserver3.MockResponse
import mockwebserver3.MockWebServer
import mockwebserver3.RecordedRequest
import okhttp3.OkHttpClient
import okhttp3.tls.HandshakeCertificates
import okhttp3.tls.HeldCertificate

/**
 * spec/connection-vectors.json, which Toskar Core's reference code keeps
 * true, so every SDK opens records as Core writes them.
 */
@Serializable
class Vectors(val routes: List<RouteCase>, val pins: List<PinCase>, val records: List<RecordCase>) {
    @Serializable
    class RouteCase(val secret: String, val route_id: String)

    @Serializable
    class PinCase(val cert_der_base64: String, val fingerprint: String, val short: String)

    @Serializable
    class RecordCase(
        val name: String,
        val blob_base64: String,
        val secret: String,
        val pin: String,
        val now: Long,
        val max_age_seconds: Long,
        val addresses: List<String>? = null,
        val at: Long? = null,
        val error: String? = null,
    )

    companion object {
        fun load(): Vectors = Json { ignoreUnknownKeys = true }
            .decodeFromString(File("../spec/connection-vectors.json").readText())
    }
}

class ConnectTest {
    @Test
    fun routeIDsAreCores() {
        for (r in Vectors.load().routes) assertEquals(r.route_id, Records.routeID(r.secret))
        assertEquals("BAD_ROUTE_SECRET", assertFailsWith<ToskarException> { Records.routeID("too-short") }.code)
    }

    @Test
    fun pinsAreCores() {
        val pins = Vectors.load().pins
        assertEquals(3, pins.size)
        for (p in pins) {
            assertEquals(p.fingerprint, Records.pinOf(Base64.getDecoder().decode(p.cert_der_base64)))
            assertEquals(p.short, Records.shortPin(p.fingerprint))
        }
    }

    @Test
    fun recordsOpenAsCoreSays() {
        for (r in Vectors.load().records) {
            val open = {
                Records.open(
                    Base64.getDecoder().decode(r.blob_base64), r.secret, r.pin,
                    Instant.ofEpochSecond(r.now), Duration.ofSeconds(r.max_age_seconds),
                )
            }
            if (r.error != null) {
                val want = mapOf("sealed" to "RECORD_SEALED", "pin" to "RECORD_PIN", "stale" to "RECORD_STALE")[r.error]
                assertEquals(want, assertFailsWith<ToskarException>(r.name) { open() }.code, r.name)
            } else {
                val record = open()
                assertEquals(r.addresses, record.addresses, r.name)
                assertEquals(r.at, record.at.epochSecond, r.name)
            }
        }
    }

    @Test
    fun savedDevicesAreTheOtherSDKsJSON() {
        val json = """{"address":"192.168.1.20:7331","api_key":"tk_1","pin":"sha256:ab","route":{"secret":"s","id":"i","relay":"relay.toskar.ai","token":"t"}}"""
        val device = Json.decodeFromString(Device.serializer(), json)
        assertEquals("tk_1", device.apiKey)
        assertEquals("t", device.route?.token)
        assertEquals(json, Json.encodeToString(Device.serializer(), device))
    }

    @Test
    fun hostsOfAddresses() {
        assertEquals("studio.local", hostOnly("studio.local:7331"))
        assertEquals("fe80::1", hostOnly("[fe80::1]:7331"))
        assertEquals("fe80::1", hostOnly("fe80::1"))
        assertEquals("relay.toskar.ai", hostOnly("relay.toskar.ai"))
    }
}

/** A computer away from home: its certificate, served over HTTPS, and a relay that keeps its address record. */
class AwayTest {
    private val computerCert = HeldCertificate.Builder().commonName("Studio").build()
    private val computer = MockWebServer().apply {
        useHttps(HandshakeCertificates.Builder().heldCertificate(computerCert).build().sslSocketFactory())
        dispatcher = object : Dispatcher() {
            override fun dispatch(request: RecordedRequest): MockResponse = when (request.url.encodedPath) {
                "/api/v1/health" -> json(if (request.headers["Authorization"] == "Bearer tk_away") """{"status":"ok"}""" else """{"error":{"code":"UNAUTHORIZED","message":"no"}}""")
                else -> json(VERSION)
            }
        }
        start()
    }
    private val relayCert = HeldCertificate.Builder().addSubjectAlternativeName("localhost").build()
    private val relay = MockWebServer().apply {
        useHttps(HandshakeCertificates.Builder().heldCertificate(relayCert).build().sslSocketFactory())
        start()
    }
    private val relayClient = OkHttpClient.Builder().apply {
        val trust = HandshakeCertificates.Builder().addTrustedCertificate(relayCert.certificate).build()
        sslSocketFactory(trust.sslSocketFactory(), trust.trustManager)
    }.build()

    private val secret = Base64.getUrlEncoder().withoutPadding().encodeToString(ByteArray(32) { it.toByte() })
    private val pin = Records.pinOf(computerCert.certificate.encoded)

    @AfterTest
    fun stop() {
        computer.close()
        relay.close()
    }

    private fun json(body: String) = MockResponse.Builder().setHeader("Content-Type", "application/json").body(body).build()

    /** An address that refuses connections: home, with the computer away. */
    private fun nowhere(): String = ServerSocket(0).use { "127.0.0.1:${it.localPort}" }

    /** A record as Core writes it: signed by the computer's certificate, sealed with the route secret. */
    private fun record(addresses: List<String>, at: Instant = Instant.now()): ByteArray {
        val route = Records.routeID(secret)
        val payload = buildJsonObject {
            put("v", 1)
            put("route", route)
            put("at", at.epochSecond)
            put("addresses", buildJsonArray { addresses.forEach { add(kotlinx.serialization.json.JsonPrimitive(it)) } })
        }.toString().toByteArray()
        val sig = Signature.getInstance("SHA256withECDSA").run {
            initSign(computerCert.keyPair.private)
            update(payload)
            sign()
        }
        val b64 = Base64.getEncoder()
        val signed = buildJsonObject {
            put("payload", b64.encodeToString(payload))
            put("cert", b64.encodeToString(computerCert.certificate.encoded))
            put("alg", "ecdsa-sha256")
            put("sig", b64.encodeToString(sig))
        }.toString().toByteArray()
        val nonce = ByteArray(12).also { SecureRandom().nextBytes(it) }
        val key = Records.hkdf(Records.routeSecret(secret), "toskar route key", 32)
        val sealed = Cipher.getInstance("AES/GCM/NoPadding").run {
            init(Cipher.ENCRYPT_MODE, SecretKeySpec(key, "AES"), GCMParameterSpec(128, nonce))
            updateAAD(route.toByteArray())
            doFinal(signed)
        }
        return nonce + sealed
    }

    private fun device(home: String, token: String? = "rt") =
        Device(home, "tk_away", pin, Route(secret, Records.routeID(secret), "localhost:${relay.port}", token))

    private fun toskar(device: Device) = Toskar(device, 0, Duration.ofSeconds(5), relayClient)

    @Test
    fun reachesItDirectlyFromItsRecord() {
        relay.enqueue(MockResponse.Builder().body(okio.Buffer().write(record(listOf("127.0.0.1:${computer.port}")))).build())
        val toskar = toskar(device(nowhere()))
        assertNull(toskar.path)
        assertEquals("1.12.0", toskar.version().version)
        assertEquals(ConnectionPath.DIRECT, toskar.path)
        val asked = relay.takeRequest()
        assertEquals("/v1/routes/${Records.routeID(secret)}/record", asked.url.encodedPath)
        assertEquals("Bearer rt", asked.headers["Authorization"])
    }

    @Test
    fun takesHomeWhenItAnswers() {
        val toskar = toskar(device("127.0.0.1:${computer.port}"))
        toskar.version()
        assertEquals(ConnectionPath.HOME, toskar.path)
        assertEquals(0, relay.requestCount)
    }

    @Test
    fun anotherCertificateAtHomeIsRefused() {
        val other = device("127.0.0.1:${computer.port}").copy(pin = "sha256:" + "ab".repeat(32))
        assertEquals("PIN_MISMATCH", assertFailsWith<ToskarException> { toskar(other).version() }.code)
    }

    @Test
    fun aRecordFromAnotherComputerIsRefused() {
        val stranger = HeldCertificate.Builder().build()
        relay.enqueue(MockResponse.Builder().body(okio.Buffer().write(record(listOf("127.0.0.1:${computer.port}")))).build())
        val toskar = toskar(device(nowhere()).copy(pin = Records.pinOf(stranger.certificate.encoded)))
        assertEquals("RECORD_PIN", assertFailsWith<ToskarException> { toskar.version() }.code)
    }

    @Test
    fun withNoRecordItSaysSo() {
        relay.enqueue(MockResponse.Builder().code(404).build())
        assertEquals("NO_RECORD", assertFailsWith<ToskarException> { toskar(device(nowhere())).version() }.code)
    }

    @Test
    fun toskarsRelayIsntAskedWithoutAToken() {
        val d = device(nowhere(), token = null).let { it.copy(route = it.route!!.copy(relay = "relay.toskar.ai")) }
        assertEquals("UNREACHABLE", assertFailsWith<ToskarException> { toskar(d).version() }.code)
    }
}
