// Finding computers running Toskar Core on the home network, as the Toskar
// apps do: they advertise _localai._tcp over mDNS, with where their API is
// in the TXT record (Toskar Core's docs/connecting.md).
//
//     val computers = Toskar.find()
//     val device = Toskar.pair(computers[0].address, code, "Kitchen tablet")
//
// It asks with one mDNS query and reads the answers itself (RFC 6762): one
// service type needs a few dozen lines, not a library. On Android, the app
// holds a WifiManager.MulticastLock while it looks.

package ai.toskar

import java.io.IOException
import java.net.DatagramPacket
import java.net.Inet4Address
import java.net.Inet6Address
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.MulticastSocket
import java.net.NetworkInterface
import java.net.Socket
import java.net.SocketTimeoutException
import java.time.Duration
import java.util.concurrent.Callable
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import okhttp3.HttpUrl

/** A Toskar Core found on the network. */
public data class DiscoveredComputer(
    public val name: String,
    public val nodeID: String,
    /** Toskar Core's version. */
    public val version: String,
    /** The API's host:port, to pair with: the first of [addresses] that answers. */
    public val address: String,
    /**
     * Every host:port found for the computer. A computer can have addresses
     * this device can't reach, such as a container network's.
     */
    public val addresses: List<String>,
    /**
     * False when the API answers only on that computer: say to turn on
     * Connect a device there, rather than that it's unreachable.
     */
    public val onNetwork: Boolean,
)

internal object Discovery {
    const val SERVICE_TYPE = "_localai._tcp"
    private val GROUP = InetSocketAddress(InetAddress.getByAddress(byteArrayOf(224.toByte(), 0, 0, 251.toByte())), 5353)

    fun find(timeout: Duration): List<DiscoveredComputer> {
        val found = try {
            browse(timeout)
        } catch (e: IOException) {
            throw ToskarException(0, "DISCOVERY_FAILED", "Couldn't look for computers on the network: ${e.message}", cause = e)
        }
        if (found.isEmpty()) return emptyList()
        val pool = Executors.newFixedThreadPool(found.size) { r -> Thread(r, "toskar-find").apply { isDaemon = true } }
        try {
            return found.map { s -> pool.submit(Callable { computer(s.txt, s.instance, s.hosts, ::reachable) }) }
                .mapNotNull { it.get() }
                .associateBy { it.nodeID + it.address }.values.sortedBy { it.name }
        } finally {
            pool.shutdownNow()
        }
    }

    /** A service that answered: its instance name, TXT record, and its host's addresses. */
    internal class Service(val instance: String, val txt: Map<String, String>, val hosts: List<InetAddress>)

    /**
     * Asks on every interface that can reach a home network, at once and
     * again a second later, and reads the answers for timeout. A computer
     * with a container network or a VPN has more than one interface, and the
     * home network's may not be first.
     */
    private fun browse(timeout: Duration): List<Service> {
        val interfaces = NetworkInterface.getNetworkInterfaces().toList().filter {
            runCatching { it.isUp && it.supportsMulticast() && !it.isLoopback && !it.isPointToPoint }.getOrDefault(false) &&
                it.inetAddresses.toList().any { a -> a is Inet4Address }
        }
        val records = Answers()
        MulticastSocket(GROUP.port).use { socket ->
            for (ni in interfaces) runCatching { socket.joinGroup(GROUP, ni) }
            fun ask() {
                val query = query("$SERVICE_TYPE.local")
                for (ni in interfaces) runCatching {
                    socket.networkInterface = ni
                    socket.send(DatagramPacket(query, query.size, GROUP))
                }
            }
            ask()
            var askedAgain = false
            val start = System.nanoTime()
            val buffer = ByteArray(9000)
            while (true) {
                val elapsed = Duration.ofNanos(System.nanoTime() - start)
                if (elapsed >= timeout) break
                if (!askedAgain && elapsed >= Duration.ofSeconds(1)) {
                    ask()
                    askedAgain = true
                }
                socket.soTimeout = maxOf(1L, minOf(250L, (timeout - elapsed).toMillis())).toInt()
                val packet = DatagramPacket(buffer, buffer.size)
                try {
                    socket.receive(packet)
                } catch (e: SocketTimeoutException) {
                    continue
                }
                // Anything that isn't a well-formed answer is someone else's to worry about.
                runCatching { records.read(packet.data.copyOf(packet.length)) }
            }
        }
        return records.services("$SERVICE_TYPE.local")
    }

    /** A query for name's PTR records, as a one-shot querier sends it. */
    internal fun query(name: String): ByteArray {
        val out = java.io.ByteArrayOutputStream()
        out.write(byteArrayOf(0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0))
        for (label in name.split('.')) {
            val bytes = label.toByteArray()
            out.write(bytes.size)
            out.write(bytes)
        }
        out.write(byteArrayOf(0, 0, TYPE_PTR.toByte(), 0, 1))
        return out.toByteArray()
    }

    /** The records the answers held, by name, gathered across packets. */
    internal class Answers {
        private val ptr = mutableMapOf<String, MutableSet<String>>()
        private val srv = mutableMapOf<String, Pair<String, Int>>()
        private val txt = mutableMapOf<String, Map<String, String>>()
        private val hosts = mutableMapOf<String, MutableSet<InetAddress>>()

        /** Reads one mDNS message's records: answers and additional ones alike. */
        fun read(m: ByteArray) {
            val r = Reader(m)
            if (r.u16(2) and 0x8000 == 0) return // a query, not an answer
            val questions = r.u16(4)
            val records = r.u16(6) + r.u16(8) + r.u16(10)
            r.at = 12
            repeat(questions) {
                r.name()
                r.at += 4
            }
            repeat(records) {
                val name = r.name().lowercase()
                val type = r.u16(r.at)
                val length = r.u16(r.at + 8)
                val data = r.at + 10
                r.at = data + length
                when (type) {
                    TYPE_PTR -> ptr.getOrPut(name) { linkedSetOf() }.add(Reader(m, data).name())
                    TYPE_SRV -> srv[name] = Reader(m, data + 6).name().lowercase() to r.u16(data + 4)
                    TYPE_TXT -> txt[name] = text(m, data, length)
                    TYPE_A -> if (length == 4) hosts.getOrPut(name) { linkedSetOf() }.add(InetAddress.getByAddress(m.copyOfRange(data, data + 4)))
                    TYPE_AAAA -> if (length == 16) hosts.getOrPut(name) { linkedSetOf() }.add(InetAddress.getByAddress(m.copyOfRange(data, data + 16)))
                }
            }
        }

        /** The instances of a service type, with what their records say. */
        fun services(type: String): List<Service> = ptr[type.lowercase()].orEmpty().mapNotNull { full ->
            val key = full.lowercase()
            val target = srv[key]?.first ?: return@mapNotNull null
            val instance = if (key.endsWith(".${type.lowercase()}")) full.dropLast(type.length + 1) else full
            Service(instance, txt[key].orEmpty(), hosts[target].orEmpty().toList())
        }

        private fun text(m: ByteArray, at: Int, length: Int): Map<String, String> {
            val out = linkedMapOf<String, String>()
            var i = at
            while (i < at + length) {
                val n = m[i].toInt() and 0xff
                val entry = String(m, i + 1, n, Charsets.UTF_8)
                if (entry.isNotEmpty()) out[entry.substringBefore('=').lowercase()] = entry.substringAfter('=', "")
                i += 1 + n
            }
            return out
        }
    }

    /** Reads DNS names, with their compression, and numbers from a message. */
    private class Reader(private val m: ByteArray, var at: Int = 0) {
        fun u16(i: Int): Int = ((m[i].toInt() and 0xff) shl 8) or (m[i + 1].toInt() and 0xff)

        fun name(): String {
            val labels = mutableListOf<String>()
            var i = at
            var jumped = false
            var jumps = 0
            while (true) {
                val n = m[i].toInt() and 0xff
                when {
                    n == 0 -> {
                        if (!jumped) at = i + 1
                        return labels.joinToString(".")
                    }
                    n and 0xc0 == 0xc0 -> {
                        if (!jumped) at = i + 2
                        jumped = true
                        if (++jumps > 32) throw IOException("a name that points in circles")
                        i = ((n and 0x3f) shl 8) or (m[i + 1].toInt() and 0xff)
                    }
                    else -> {
                        labels.add(String(m, i + 1, n, Charsets.UTF_8))
                        i += 1 + n
                    }
                }
            }
        }
    }

    private const val TYPE_A = 1
    private const val TYPE_PTR = 12
    private const val TYPE_TXT = 16
    private const val TYPE_AAAA = 28
    private const val TYPE_SRV = 33

    /**
     * The computer a service describes, with the API's port from its TXT
     * record (the service's own port is for computers pairing with each
     * other), or null without one or without an address.
     */
    fun computer(
        txt: Map<String, String>,
        instance: String,
        hosts: List<InetAddress>,
        reachable: (List<String>) -> String?,
    ): DiscoveredComputer? {
        val port = txt["api_port"]?.toIntOrNull()?.takeIf { it > 0 } ?: return null
        val addresses = hosts
            // A link-local IPv6 address needs its interface, which a URL can't carry.
            .filterNot { it is Inet6Address && it.isLinkLocalAddress }
            .sortedBy { it is Inet6Address }
            .map { a ->
                // OkHttp writes IPv6 in its short form (RFC 5952), as the other SDKs do.
                val host = HttpUrl.Builder().scheme("http").host(a.hostAddress.substringBefore('%')).build().host
                if (a is Inet6Address) "[$host]:$port" else "$host:$port"
            }
            .distinct()
        val first = addresses.firstOrNull() ?: return null
        return DiscoveredComputer(
            name = txt["name"]?.takeIf { it.isNotEmpty() } ?: instance,
            nodeID = txt["node_id"].orEmpty(),
            version = txt["version"].orEmpty(),
            address = reachable(addresses) ?: first,
            addresses = addresses,
            onNetwork = txt["api_lan"] != "false",
        )
    }

    /** The first of addresses that takes a TCP connection, tried together. */
    private fun reachable(addresses: List<String>): String? {
        val pool = Executors.newFixedThreadPool(addresses.size) { r -> Thread(r, "toskar-find").apply { isDaemon = true } }
        try {
            val tries = addresses.map { address ->
                pool.submit(Callable {
                    val url = baseOf(address)
                    runCatching { Socket().use { it.connect(InetSocketAddress(url.host, url.port), 700) } }.isSuccess
                })
            }
            return addresses.zip(tries).firstOrNull { (_, ok) -> runCatching { ok.get(2, TimeUnit.SECONDS) }.getOrDefault(false) }?.first
        } finally {
            pool.shutdownNow()
        }
    }
}
