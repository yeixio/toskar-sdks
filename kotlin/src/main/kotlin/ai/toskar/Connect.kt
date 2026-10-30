// Connecting as a paired device, as the Toskar apps do (Toskar Core's
// docs/connecting.md): pairing with the code Connect a device shows, the
// computer's certificate pinned on every connection, and reaching it at
// home or, with access from anywhere, directly or through its relay.

package ai.toskar

import ai.toskar.api.PairedDevice
import java.io.IOException
import java.security.SecureRandom
import java.security.cert.CertificateException
import java.security.cert.X509Certificate
import java.time.Duration
import java.util.concurrent.ExecutorCompletionService
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import javax.net.ssl.SSLContext
import javax.net.ssl.X509TrustManager
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody

/**
 * What a paired device keeps, to connect again. Save it as a password is
 * saved: [apiKey] and the route's secret and token are secrets. It's
 * `@Serializable`, as the other SDKs' JSON:
 * `Json.encodeToString(Device.serializer(), device)`.
 */
@Serializable
public data class Device @JvmOverloads constructor(
    /** The computer's host:port at home. */
    @SerialName("address") public val address: String,
    @SerialName("api_key") public val apiKey: String,
    /** "sha256:<hex>" of the computer's certificate. It only ever comes from pairing. */
    @SerialName("pin") public val pin: String,
    /** How to find the computer away from home, when it has access from anywhere. */
    @SerialName("route") public val route: Route? = null,
)

/** How to find a computer away from home. */
@Serializable
public data class Route @JvmOverloads constructor(
    /** The route secret, base64url without padding. */
    @SerialName("secret") public val secret: String,
    @SerialName("id") public val id: String,
    /** The relay the computer uses, such as relay.toskar.ai. */
    @SerialName("relay") public val relay: String,
    /** Lets the device look the computer up on Toskar's relay. */
    @SerialName("token") public val token: String? = null,
)

/** How the client reaches its computer. */
public enum class ConnectionPath(public val value: String) {
    HOME("home"),
    DIRECT("direct"),
    RELAY("relay"),
}

/** Shows the person the short pin, such as 9B80-D9D9, and says whether the computer shows the same. */
public fun interface ShortPinCheck {
    public fun confirm(shortPin: String): Boolean
}

internal object Pairing {
    fun pair(address: String, code: String, deviceName: String, confirm: ShortPinCheck?): Device {
        val base = "https://$address".toHttpUrlOrNull()
            ?: throw ToskarException(0, "BAD_ADDRESS", "$address isn't host:port")
        // The certificate the computer shows, for the person to check.
        val seeing = Pinning(null)
        val timeout = Duration.ofSeconds(30)
        try {
            seeing.client(timeout).newCall(Request.Builder().url(base.resolve("/api/v1/health")!!).build()).execute().close()
        } catch (e: IOException) {
            throw ToskarException(0, "CONNECTION_FAILED", "Couldn't reach the computer at $address: ${e.message}", cause = e)
        }
        val seen = seeing.seen ?: throw ToskarException(0, "PIN_MISMATCH", "The computer showed no certificate")
        if (confirm != null && !confirm.confirm(Records.shortPin(seen))) {
            throw ToskarException(0, "NOT_CONFIRMED", "The short pin wasn't confirmed")
        }

        // Then the code, to that certificate alone.
        val body = buildJsonObject {
            put("code", code)
            put("device_name", deviceName)
        }.toString().toRequestBody("application/json".toMediaType())
        val request = Request.Builder().url(base.resolve("/api/v1/devices/pair")!!)
            .header("Toskar-Client-Contract", CONTRACT_VERSION)
            .post(body).build()
        val paired = pinned { Pinning(seen).client(timeout).newCall(request).execute() }.use { response ->
            val text = response.body.string()
            if (response.code >= 300) throw ToskarException.of(response.code, text)
            Toskar.JSON.decodeFromString<PairedDevice>(text)
        }
        if (!paired.tlsFingerprint.equals(seen, ignoreCase = true)) {
            throw ToskarException(0, "PIN_MISMATCH", "The computer's certificate isn't the one paired with")
        }
        val route = paired.routeSecret?.takeIf { it.isNotEmpty() }?.let {
            Route(it, paired.routeId.orEmpty(), paired.relay.orEmpty(), paired.token)
        }
        return Device(address, paired.apiKey, seen, route)
    }
}

/**
 * Trusts exactly the certificate with pin, checked before any request is
 * sent; names, dates, and signers aren't checked. With no pin, it trusts
 * any certificate and keeps its pin in seen, for pairing.
 */
internal class Pinning(private val pin: String?) : X509TrustManager {
    @Volatile
    var seen: String? = null
        private set

    override fun checkServerTrusted(chain: Array<out X509Certificate>, authType: String) {
        val got = Records.pinOf(chain.firstOrNull()?.encoded ?: throw PinMismatch())
        if (pin == null) {
            seen = got
        } else if (!got.equals(pin, ignoreCase = true)) {
            throw PinMismatch()
        }
    }

    override fun checkClientTrusted(chain: Array<out X509Certificate>, authType: String): Unit = throw CertificateException()

    override fun getAcceptedIssuers(): Array<X509Certificate> = emptyArray()

    /** A client whose connections are pinned. */
    fun client(timeout: Duration, from: OkHttpClient = OkHttpClient()): OkHttpClient {
        val tls = SSLContext.getInstance("TLS").apply { init(null, arrayOf(this@Pinning), SecureRandom()) }
        return from.newBuilder()
            .sslSocketFactory(tls.socketFactory, this)
            // The pin is the computer's identity; its name isn't.
            .hostnameVerifier { _, _ -> true }
            .connectTimeout(timeout)
            .readTimeout(timeout)
            .writeTimeout(timeout)
            .build()
    }
}

internal class PinMismatch : CertificateException("The computer's certificate isn't the one paired with")

/** Runs a call over a pinned client, with a refused certificate thrown as `PIN_MISMATCH`. */
internal inline fun <T> pinned(call: () -> T): T = try {
    call()
} catch (e: IOException) {
    if (e.isPinMismatch()) {
        throw ToskarException(0, "PIN_MISMATCH", "The computer's certificate isn't the one paired with", cause = e)
    }
    throw e
}

internal fun Throwable.isPinMismatch(): Boolean = generateSequence(this) { it.cause }.any { it is PinMismatch }

/**
 * Chooses the way in, and again when it stops answering: home first, then
 * the address record's ways, the direct ones at once and the relay's a
 * second later.
 */
internal class Router(
    private val device: Device,
    private val pinned: OkHttpClient,
    private val relayClient: OkHttpClient,
) {
    @Volatile
    var path: ConnectionPath? = null
        private set
    private var way: String? = null

    @Synchronized
    fun forget() {
        way = null
        path = null
    }

    @Synchronized
    fun forget(used: String) {
        if (way == used) forget()
    }

    /** The way in to use, host:port, choosing one when there's none. */
    @Synchronized
    fun current(): String {
        way?.let { return it }
        val (found, at) = choose()
        way = at
        path = found
        return at
    }

    /** Whether the computer answers health at address, pinned, within timeout. Another certificate throws `PIN_MISMATCH`. */
    private fun answers(address: String, timeout: Duration): Boolean {
        val url = "https://$address/api/v1/health".toHttpUrlOrNull() ?: return false
        // With the key: a computer that asks for one answers health only
        // with it. The connection is pinned before anything is sent.
        val request = Request.Builder().url(url).header("Authorization", "Bearer ${device.apiKey}").build()
        val client = pinned.newBuilder().callTimeout(timeout).build()
        return try {
            pinned { client.newCall(request).execute() }.use { r ->
                r.code == 200 && runCatching { Toskar.JSON.decodeFromString<Health>(r.body.string()).status == "ok" }.getOrDefault(false)
            }
        } catch (e: IOException) {
            false
        }
    }

    @Serializable
    private class Health(val status: String = "")

    private fun choose(): Pair<ConnectionPath, String> {
        // Home answering with another certificate means the computer's
        // changed, or it isn't the computer: say so; pairing again is the
        // way on.
        if (answers(device.address, HOME_TIMEOUT)) return ConnectionPath.HOME to device.address
        val route = device.route?.takeIf { it.secret.isNotEmpty() } ?: throw unreachable()
        val relay = hostOnly(route.relay).lowercase()
        // Toskar's relay answers only for a subscription; without one, it
        // isn't asked, so nothing about this device reaches it.
        if (relay == TOSKAR_RELAY && route.token.isNullOrEmpty()) throw unreachable()
        val record = record(route)
        if (record.addresses.isEmpty()) throw unreachable()
        val pool = Executors.newFixedThreadPool(record.addresses.size) { r -> Thread(r, "toskar-router").apply { isDaemon = true } }
        try {
            val tries = ExecutorCompletionService<Pair<ConnectionPath, String>?>(pool)
            for (address in record.addresses) {
                val isRelay = hostOnly(address).lowercase().endsWith(".$relay")
                tries.submit {
                    if (isRelay) Thread.sleep(RELAY_DELAY.toMillis())
                    // Another certificate at a way in is someone else's
                    // device there: that way just doesn't count.
                    val ok = try {
                        answers(address, TRY_TIMEOUT)
                    } catch (e: ToskarException) {
                        false
                    }
                    if (ok) (if (isRelay) ConnectionPath.RELAY else ConnectionPath.DIRECT) to address else null
                }
            }
            repeat(record.addresses.size) {
                tries.poll(TRY_TIMEOUT.toMillis() + RELAY_DELAY.toMillis() + 1000, TimeUnit.MILLISECONDS)?.get()?.let { return it }
            }
            throw unreachable()
        } finally {
            pool.shutdownNow()
        }
    }

    private fun record(route: Route): AddressRecord {
        val url = "https://${route.relay}/v1/routes/${route.id}/record".toHttpUrlOrNull() ?: throw noRecord()
        val request = Request.Builder().url(url).apply {
            route.token?.takeIf { it.isNotEmpty() }?.let { header("Authorization", "Bearer $it") }
        }.build()
        val data = try {
            relayClient.newBuilder().callTimeout(TRY_TIMEOUT).build().newCall(request).execute().use { r ->
                val body = r.body
                if (r.code != 200 || body.contentLength() > RECORD_LIMIT) throw noRecord()
                body.source().apply { request(RECORD_LIMIT + 1) }.buffer.let {
                    if (it.size > RECORD_LIMIT) throw noRecord()
                    it.readByteArray()
                }
            }
        } catch (e: IOException) {
            throw noRecord()
        }
        return Records.open(data, route.secret, device.pin, maxAge = RECORD_MAX_AGE)
    }

    companion object {
        val HOME_TIMEOUT: Duration = Duration.ofMillis(2500)
        val TRY_TIMEOUT: Duration = Duration.ofSeconds(6)
        val RELAY_DELAY: Duration = Duration.ofSeconds(1)
        val RECORD_MAX_AGE: Duration = Duration.ofHours(1)
        const val RECORD_LIMIT = 1L shl 20

        /** Toskar's own relay. It's asked only with a route token. */
        const val TOSKAR_RELAY = "relay.toskar.ai"

        fun unreachable() = ToskarException(0, "UNREACHABLE", "The computer can't be reached")
        fun noRecord() = ToskarException(
            0, "NO_RECORD", "No address record for the computer: it may be off or asleep, or have no access from anywhere",
        )
    }
}

/** The way in's address as a base URL. */
internal fun baseOf(way: String): HttpUrl =
    "https://$way".toHttpUrlOrNull() ?: throw ToskarException(0, "BAD_ADDRESS", "$way isn't host:port")

/** The host of host:port, [v6]:port, or a bare host or IPv6 address. */
internal fun hostOnly(address: String): String {
    if (address.startsWith("[")) {
        val end = address.indexOf(']')
        if (end > 0) return address.substring(1, end)
    }
    if (address.count { it == ':' } == 1) return address.substringBeforeLast(':')
    return address
}
