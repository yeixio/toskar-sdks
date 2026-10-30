using System.Collections.Generic;
using System.Linq;
using System.Net;
using System.Text;
using System.Threading.Tasks;
using Xunit;

namespace Toskar.Tests;

public class DiscoveryTests
{
    private static readonly IPAddress V4 = IPAddress.Parse("192.168.1.20");
    private static readonly IPAddress V6 = IPAddress.Parse("fd00::20");
    private static readonly IPAddress LinkLocal = IPAddress.Parse("fe80::1");

    private static Dictionary<string, string> Txt() =>
        new() { ["api_port"] = "7331", ["name"] = "Studio", ["node_id"] = "n1", ["version"] = "1.12.0" };

    private static Task<string?> NoneAnswer(IReadOnlyList<string> _) => Task.FromResult<string?>(null);

    [Fact]
    public async Task AServiceIsAComputerAtItsApiPort()
    {
        var c = (await Discovery.ComputerAsync(Txt(), "studio-instance", new[] { V6, LinkLocal, V4 }, NoneAnswer))!;
        Assert.Equal("Studio", c.Name);
        Assert.Equal("n1", c.NodeId);
        Assert.Equal("1.12.0", c.Version);
        // IPv4 first, IPv6 in brackets, and no link-local address.
        Assert.Equal(new[] { "192.168.1.20:7331", "[fd00::20]:7331" }, c.Addresses);
        Assert.Equal("192.168.1.20:7331", c.Address);
        Assert.True(c.OnNetwork);
    }

    [Fact]
    public async Task TheAddressIsTheOneThatAnswers()
    {
        var c = (await Discovery.ComputerAsync(Txt(), "x", new[] { V4, V6 }, a => Task.FromResult<string?>(a[^1])))!;
        Assert.Equal("[fd00::20]:7331", c.Address);
    }

    [Fact]
    public async Task WithoutANameItsTheInstanceAndItCanBeOnlyOnItsComputer()
    {
        var txt = Txt();
        txt.Remove("name");
        txt["api_lan"] = "false";
        var c = (await Discovery.ComputerAsync(txt, "studio-instance", new[] { V4 }, NoneAnswer))!;
        Assert.Equal("studio-instance", c.Name);
        Assert.False(c.OnNetwork);
    }

    [Fact]
    public async Task WithoutAnApiPortOrAddressItIsntOne()
    {
        var txt = Txt();
        txt.Remove("api_port");
        Assert.Null(await Discovery.ComputerAsync(txt, "x", new[] { V4 }, NoneAnswer));
        Assert.Null(await Discovery.ComputerAsync(Txt(), "x", new[] { LinkLocal }, NoneAnswer));
    }

    /// <summary>An mDNS answer as a responder sends one: PTR, then SRV, TXT, and A in the additional records, names compressed.</summary>
    private static byte[] Answer()
    {
        var m = new List<byte>();
        void U16(int v)
        {
            m.Add((byte)(v >> 8));
            m.Add((byte)(v & 0xff));
        }
        void Labels(params string[] labels)
        {
            foreach (var l in labels)
            {
                m.Add((byte)l.Length);
                m.AddRange(Encoding.ASCII.GetBytes(l));
            }
        }
        U16(0); U16(0x8400); U16(0); U16(1); U16(0); U16(3);
        // _localai._tcp.local PTR Studio._localai._tcp.local
        var typeAt = m.Count;
        Labels("_localai", "_tcp", "local");
        m.Add(0);
        U16(12); U16(1); U16(0); U16(120);
        U16(9); Labels("Studio"); U16(0xc000 | typeAt);
        var instanceAt = m.Count - 9;
        // Studio._localai._tcp.local SRV 0 0 7332 studio.local
        U16(0xc000 | instanceAt); U16(33); U16(0x8001); U16(0); U16(120);
        U16(6 + 7 + 2); U16(0); U16(0); U16(7332);
        var hostAt = m.Count;
        Labels("studio"); U16(0xc000 | (typeAt + 14));
        // TXT
        var txt = new[] { "api_port=7331", "node_id=n1", "name=Studio", "version=1.12.0" };
        U16(0xc000 | instanceAt); U16(16); U16(0x8001); U16(0); U16(120);
        U16(txt.Sum(t => t.Length + 1));
        foreach (var t in txt)
        {
            m.Add((byte)t.Length);
            m.AddRange(Encoding.ASCII.GetBytes(t));
        }
        // studio.local A 192.168.1.20
        U16(0xc000 | hostAt); U16(1); U16(0x8001); U16(0); U16(120); U16(4);
        m.AddRange(new byte[] { 192, 168, 1, 20 });
        return m.ToArray();
    }

    [Fact]
    public async Task ReadsAnAnswerWithCompressedNames()
    {
        var answers = new Discovery.Answers();
        answers.Read(Answer());
        // A query on the network isn't an answer.
        answers.Read(Discovery.Query("_localai._tcp.local"));
        var s = Assert.Single(answers.Services("_localai._tcp.local"));
        Assert.Equal("Studio", s.Instance);
        Assert.Equal("7331", s.Txt["api_port"]);
        Assert.Equal(new[] { V4 }, s.Hosts);
        var c = (await Discovery.ComputerAsync(s.Txt, s.Instance, s.Hosts, NoneAnswer))!;
        Assert.Equal("192.168.1.20:7331", c.Address);
    }
}
