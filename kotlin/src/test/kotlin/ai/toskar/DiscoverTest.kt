package ai.toskar

import java.net.InetAddress
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
import java.io.ByteArrayOutputStream

class DiscoverTest {
    private val v4 = InetAddress.getByName("192.168.1.20")
    private val v6 = InetAddress.getByName("fd00::20")
    private val linkLocal = InetAddress.getByName("fe80::1")
    private val txt = mapOf("api_port" to "7331", "name" to "Studio", "node_id" to "n1", "version" to "1.12.0")

    @Test
    fun aServiceIsAComputerAtItsAPIPort() {
        val c = Discovery.computer(txt, "studio-instance", listOf(v6, linkLocal, v4)) { null }!!
        assertEquals("Studio", c.name)
        assertEquals("n1", c.nodeID)
        assertEquals("1.12.0", c.version)
        // IPv4 first, IPv6 in brackets, and no link-local address.
        assertEquals(listOf("192.168.1.20:7331", "[fd00::20]:7331"), c.addresses)
        assertEquals("192.168.1.20:7331", c.address)
        assertEquals(true, c.onNetwork)
    }

    @Test
    fun theAddressIsTheOneThatAnswers() {
        val c = Discovery.computer(txt, "x", listOf(v4, v6)) { it.last() }!!
        assertEquals("[fd00::20]:7331", c.address)
    }

    @Test
    fun withoutANameItsTheInstanceAndItCanBeOnlyOnItsComputer() {
        val c = Discovery.computer(txt - "name" + ("api_lan" to "false"), "studio-instance", listOf(v4)) { null }!!
        assertEquals("studio-instance", c.name)
        assertEquals(false, c.onNetwork)
    }

    @Test
    fun withoutAnAPIPortOrAddressItIsntOne() {
        assertNull(Discovery.computer(txt - "api_port", "x", listOf(v4)) { null })
        assertNull(Discovery.computer(txt, "x", listOf(linkLocal)) { null })
    }

    /** An mDNS answer as a responder sends one: PTR, then SRV, TXT, and A in the additional records, names compressed. */
    private fun answer(): ByteArray {
        val out = ByteArrayOutputStream()
        fun u16(v: Int) { out.write(v shr 8); out.write(v and 0xff) }
        fun labels(vararg l: String) { for (x in l) { out.write(x.length); out.write(x.toByteArray()) } }
        u16(0); u16(0x8400); u16(0); u16(1); u16(0); u16(3)
        // _localai._tcp.local PTR Studio._localai._tcp.local
        val typeAt = out.size()
        labels("_localai", "_tcp", "local"); out.write(0)
        u16(12); u16(1); u16(0); u16(120)
        u16(9); labels("Studio"); u16(0xc000 or typeAt)
        val instanceAt = out.size() - 9
        // Studio._localai._tcp.local SRV 0 0 7332 studio.local
        u16(0xc000 or instanceAt); u16(33); u16(0x8001); u16(0); u16(120)
        u16(6 + 7 + 2); u16(0); u16(0); u16(7332)
        val hostAt = out.size()
        labels("studio"); u16(0xc000 or (typeAt + 14))
        // TXT
        val txt = listOf("api_port=7331", "node_id=n1", "name=Studio", "version=1.12.0")
        u16(0xc000 or instanceAt); u16(16); u16(0x8001); u16(0); u16(120)
        u16(txt.sumOf { it.length + 1 }); for (t in txt) { out.write(t.length); out.write(t.toByteArray()) }
        // studio.local A 192.168.1.20
        u16(0xc000 or hostAt); u16(1); u16(0x8001); u16(0); u16(120); u16(4)
        out.write(byteArrayOf(192.toByte(), 168.toByte(), 1, 20))
        return out.toByteArray()
    }

    @Test
    fun readsAnAnswerWithCompressedNames() {
        val answers = Discovery.Answers()
        answers.read(answer())
        // A query on the network isn't an answer.
        answers.read(Discovery.query("_localai._tcp.local"))
        val services = answers.services("_localai._tcp.local")
        assertEquals(1, services.size)
        val s = services[0]
        assertEquals("Studio", s.instance)
        assertEquals("7331", s.txt["api_port"])
        assertEquals(listOf(v4), s.hosts)
        val c = Discovery.computer(s.txt, s.instance, s.hosts) { null }!!
        assertEquals("192.168.1.20:7331", c.address)
    }
}
