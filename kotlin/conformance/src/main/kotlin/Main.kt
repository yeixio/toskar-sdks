// Runs the shared conformance cases (conformance/README.md) with the Kotlin
// SDK. It prints one line of JSON and exits 0, or prints
// {"error": {"code", "message"}} and exits 1.

package ai.toskar.conformance

import ai.toskar.ChatEvent
import ai.toskar.Device
import ai.toskar.Toskar
import ai.toskar.ToskarException
import ai.toskar.api.ChatRequest
import ai.toskar.api.UploadArtifactRequest
import java.io.File
import java.security.KeyStore
import java.security.MessageDigest
import java.security.cert.CertificateFactory
import java.util.Base64
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import kotlin.system.exitProcess
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put

const val USAGE = "usage: toskar-conformance pair <address> <code> | call <device.json> | chat|stream <model> <message> | events <model> <message> <until> | upload <file> | download <id>"

fun run(args: List<String>): JsonElement {
    when (args.firstOrNull() to args.size) {
        "pair" to 3 -> {
            var short = ""
            val device = Toskar.pair(args[1], args[2], "Kotlin conformance") { short = it; true }
            return buildJsonObject {
                put("device", Json.encodeToJsonElement(Device.serializer(), device))
                put("short_pin", short)
            }
        }
        "call" to 2 -> {
            val device = Json.decodeFromString(Device.serializer(), File(args[1]).readText())
            Toskar(device, retries = 0).use { toskar ->
                val settings = toskar.api.getSettings()
                return buildJsonObject {
                    put("path", toskar.path?.value ?: "")
                    put("node_name", settings["node_name"]?.jsonPrimitive?.content ?: "")
                }
            }
        }
    }
    // The rest connect as TOSKAR_URL and TOSKAR_API_KEY say.
    Toskar(retries = 0).use { toskar ->
        return when (args.firstOrNull() to args.size) {
            "chat" to 3 -> buildJsonObject {
                put("content", toskar.chat(ChatRequest(message = args[2], modelId = args[1])).content)
            }
            "stream" to 3 -> {
                val content = StringBuilder()
                var tokens = 0
                var done = false
                toskar.chatStream(ChatRequest(message = args[2], modelId = args[1])).use { events ->
                    for (event in events) {
                        when (event) {
                            is ChatEvent.Token -> { tokens++; content.append(event.text) }
                            is ChatEvent.Done -> done = true
                        }
                    }
                }
                buildJsonObject {
                    put("content", content.toString())
                    put("tokens", tokens)
                    put("done", done)
                }
            }
            "events" to 4 -> events(toskar, args[1], args[2], args[3])
            "upload" to 2 -> {
                val file = File(args[1])
                val up = toskar.api.uploadArtifact(UploadArtifactRequest(file.name, contentBase64 = Base64.getEncoder().encodeToString(file.readBytes())))
                buildJsonObject {
                    put("id", up.id)
                    put("name", up.name)
                    put("size_bytes", up.sizeBytes)
                }
            }
            "download" to 2 -> {
                val data = toskar.api.getArtifactContent(args[1])
                buildJsonObject {
                    put("sha256", MessageDigest.getInstance("SHA-256").digest(data).joinToString("") { "%02x".format(it) })
                    put("size_bytes", data.size)
                }
            }
            else -> throw ToskarException(0, "ERROR", USAGE)
        }
    }
}

/** Listens to the events stream, asks once, and lists the events' types until one of type until. */
fun events(toskar: Toskar, model: String, message: String, until: String): JsonElement {
    val stream = toskar.events()
    val pool = Executors.newSingleThreadExecutor { r -> Thread(r).apply { isDaemon = true } }
    val listening = pool.submit<List<String>> {
        val types = mutableListOf<String>()
        for (event in stream) {
            types.add(event.type)
            if (event.type == until) break
        }
        types
    }
    // Time to subscribe before asking.
    Thread.sleep(1000)
    toskar.chat(ChatRequest(message = message, modelId = model))
    val types = try {
        listening.get(30, TimeUnit.SECONDS)
    } finally {
        stream.close()
        pool.shutdownNow()
    }
    return buildJsonObject { put("types", buildJsonArray { types.forEach { add(JsonPrimitive(it)) } }) }
}

/**
 * Trusts the certificate authorities in SSL_CERT_FILE, as Go and Python do,
 * in place of the JVM's own: a test bed's relay has its own.
 */
fun trustCertFile() {
    val path = System.getenv("SSL_CERT_FILE")?.takeIf { it.isNotEmpty() } ?: return
    val store = KeyStore.getInstance("PKCS12").apply { load(null, null) }
    File(path).inputStream().use { input ->
        CertificateFactory.getInstance("X.509").generateCertificates(input).forEachIndexed { i, cert ->
            store.setCertificateEntry("ca$i", cert)
        }
    }
    val file = File.createTempFile("toskar-ca", ".p12").apply { deleteOnExit() }
    file.outputStream().use { store.store(it, CharArray(0)) }
    System.setProperty("javax.net.ssl.trustStore", file.path)
    System.setProperty("javax.net.ssl.trustStorePassword", "")
    System.setProperty("javax.net.ssl.trustStoreType", "PKCS12")
}

fun main(args: Array<String>) {
    val out = try {
        trustCertFile()
        run(args.toList())
    } catch (e: ToskarException) {
        println(buildJsonObject { put("error", buildJsonObject { put("code", e.code); put("message", e.message) }) })
        exitProcess(1)
    } catch (e: Exception) {
        println(buildJsonObject { put("error", buildJsonObject { put("code", "ERROR"); put("message", e.toString()) }) })
        exitProcess(1)
    }
    println(out)
    exitProcess(0)
}
