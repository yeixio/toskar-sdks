// Address records: how a paired device finds its computer away from home
// (Toskar Core's docs/connecting.md). A record is sealed with the route
// secret only the computer and its paired devices have, and signed by the
// computer's own certificate, so a relay that keeps it can neither read it
// nor change it.

package ai.toskar

import java.io.ByteArrayInputStream
import java.security.MessageDigest
import java.security.Signature
import java.security.cert.CertificateFactory
import java.security.cert.X509Certificate
import java.time.Duration
import java.time.Instant
import java.util.Base64
import javax.crypto.Cipher
import javax.crypto.Mac
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec
import kotlinx.serialization.Serializable

/** What an address record says: the computer's ways in, and when it wrote them. */
public data class AddressRecord(public val addresses: List<String>, public val at: Instant)

/** Address records, and the route IDs and pins they're checked with. */
public object Records {
    /** The route ID a route secret names. */
    @JvmStatic
    public fun routeID(secret: String): String =
        lowerBase32(hkdf(routeSecret(secret), "toskar route id", 20))

    /** The pin of a certificate: "sha256:<hex>" of its DER. */
    @JvmStatic
    public fun pinOf(der: ByteArray): String =
        "sha256:" + MessageDigest.getInstance("SHA-256").digest(der).joinToString("") { "%02x".format(it) }

    /**
     * How a pin is shown for the person to compare: its first 8 hex digits,
     * as ABCD-1234.
     */
    @JvmStatic
    public fun shortPin(pin: String): String {
        val hex = pin.removePrefix("sha256:").uppercase()
        return if (hex.length < 8) hex else "${hex.substring(0, 4)}-${hex.substring(4, 8)}"
    }

    /**
     * Opens an address record as docs/connecting.md says: sealed with the
     * route secret, from the certificate with pin, for this route, and no
     * older than maxAge. It throws a [ToskarException] with `RECORD_SEALED`,
     * `RECORD_PIN`, or `RECORD_STALE` otherwise.
     */
    @JvmStatic
    @JvmOverloads
    public fun open(
        blob: ByteArray,
        secret: String,
        pin: String,
        now: Instant = Instant.now(),
        maxAge: Duration = Duration.ofHours(1),
    ): AddressRecord {
        val route = routeID(secret)
        val key = hkdf(routeSecret(secret), "toskar route key", 32)
        val sealed = ToskarException(0, "RECORD_SEALED", "The record doesn't open with this route secret")
        // The nonce, then the sealed record and its tag.
        if (blob.size < 12 + 16) throw sealed
        val plain = try {
            Cipher.getInstance("AES/GCM/NoPadding").run {
                init(Cipher.DECRYPT_MODE, SecretKeySpec(key, "AES"), GCMParameterSpec(128, blob, 0, 12))
                updateAAD(route.toByteArray())
                doFinal(blob, 12, blob.size - 12)
            }
        } catch (e: Exception) {
            throw sealed
        }
        val signed = runCatching { Toskar.JSON.decodeFromString<Signed>(plain.decodeToString()) }.getOrNull() ?: throw sealed
        val payload = Base64.getDecoder().decode(signed.payload)
        val cert = Base64.getDecoder().decode(signed.cert)
        val body = runCatching { Toskar.JSON.decodeFromString<Body>(payload.decodeToString()) }.getOrNull()
        if (!pinOf(cert).equals(pin, ignoreCase = true) ||
            !verify(Base64.getDecoder().decode(signed.sig), payload, signed.alg, cert) ||
            body == null || body.v != 1 || body.route != route
        ) {
            throw ToskarException(0, "RECORD_PIN", "The record isn't from the pinned computer")
        }
        val at = Instant.ofEpochSecond(body.at)
        if (Duration.between(at, now) > maxAge || Duration.between(now, at) > Duration.ofMinutes(5)) {
            throw ToskarException(0, "RECORD_STALE", "The record is too old")
        }
        return AddressRecord(body.addresses, at)
    }

    @Serializable
    private class Signed(val payload: String, val cert: String, val alg: String, val sig: String)

    @Serializable
    private class Body(val v: Int, val route: String, val at: Long, val addresses: List<String>)

    internal fun routeSecret(secret: String): ByteArray {
        val s = runCatching { Base64.getUrlDecoder().decode(secret.trimEnd('=')) }.getOrNull()
        if (s == null || s.size != 32) {
            throw ToskarException(0, "BAD_ROUTE_SECRET", "A route secret is 32 bytes, base64url")
        }
        return s
    }

    /** HKDF-SHA256 with no salt (RFC 5869). */
    internal fun hkdf(secret: ByteArray, info: String, length: Int): ByteArray {
        val prk = Mac.getInstance("HmacSHA256").run {
            init(SecretKeySpec(ByteArray(32), "HmacSHA256"))
            doFinal(secret)
        }
        val mac = Mac.getInstance("HmacSHA256").apply { init(SecretKeySpec(prk, "HmacSHA256")) }
        val out = java.io.ByteArrayOutputStream()
        var block = ByteArray(0)
        var i = 1
        while (out.size() < length) {
            mac.update(block)
            mac.update(info.toByteArray())
            mac.update(i.toByte())
            block = mac.doFinal()
            out.write(block)
            i++
        }
        return out.toByteArray().copyOf(length)
    }

    /** RFC 4648 base32 in lower case, without padding, as route IDs are. */
    internal fun lowerBase32(data: ByteArray): String {
        val alphabet = "abcdefghijklmnopqrstuvwxyz234567"
        val out = StringBuilder()
        var buffer = 0
        var bits = 0
        for (b in data) {
            buffer = (buffer shl 8) or (b.toInt() and 0xff)
            bits += 8
            while (bits >= 5) {
                out.append(alphabet[(buffer shr (bits - 5)) and 31])
                bits -= 5
            }
        }
        if (bits > 0) out.append(alphabet[(buffer shl (5 - bits)) and 31])
        return out.toString()
    }

    /**
     * Whether sig signs payload with the key in cert, by alg: ECDSA P-256
     * and RSA PKCS #1 v1.5 with SHA-256, and Ed25519, which needs Java 15
     * or later (Android 13).
     */
    internal fun verify(sig: ByteArray, payload: ByteArray, alg: String, cert: ByteArray): Boolean = try {
        val key = (CertificateFactory.getInstance("X.509").generateCertificate(ByteArrayInputStream(cert)) as X509Certificate).publicKey
        val algorithm = when {
            alg == "ecdsa-sha256" && key.algorithm == "EC" -> "SHA256withECDSA"
            alg == "rsa-pkcs1-sha256" && key.algorithm == "RSA" -> "SHA256withRSA"
            alg == "ed25519" && key.algorithm in setOf("Ed25519", "EdDSA") -> "Ed25519"
            else -> null
        }
        algorithm != null && Signature.getInstance(algorithm).run {
            initVerify(key)
            update(payload)
            verify(sig)
        }
    } catch (e: Exception) {
        false
    }
}
