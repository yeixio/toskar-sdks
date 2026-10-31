// Finding computers running Toskar Core on the home network, as the Toskar
// apps do: they advertise _localai._tcp over mDNS, with where their API is
// in the TXT record (Toskar Core's docs/connecting.md).
//
//     var computers = await ToskarClient.FindAsync();
//     var device = await ToskarClient.PairAsync(computers[0].Address, code, "Kitchen tablet");
//
// It asks with one mDNS query and reads the answers itself (RFC 6762): one
// service type needs a few dozen lines, not a library.

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace Toskar;

/// <summary>A Toskar Core found on the network.</summary>
/// <param name="Name">The computer's name.</param>
/// <param name="NodeId">The computer's node ID.</param>
/// <param name="Version">Toskar Core's version.</param>
/// <param name="Address">The API's host:port, to pair with: the first of <paramref name="Addresses"/> that answers.</param>
/// <param name="Addresses">
/// Every host:port found for the computer. A computer can have addresses
/// this device can't reach, such as a container network's.
/// </param>
/// <param name="OnNetwork">
/// False when the API answers only on that computer: say to turn on Connect
/// a device there, rather than that it's unreachable.
/// </param>
public sealed record DiscoveredComputer(
    string Name, string NodeId, string Version, string Address, IReadOnlyList<string> Addresses, bool OnNetwork);

internal static class Discovery
{
    internal const string ServiceType = ToskarClient.ServiceType;
    private static readonly IPEndPoint Group = new(IPAddress.Parse("224.0.0.251"), 5353);

    internal static async Task<IReadOnlyList<DiscoveredComputer>> FindAsync(TimeSpan timeout, CancellationToken cancellationToken)
    {
        List<Service> found;
        try
        {
            found = await BrowseAsync(timeout, cancellationToken).ConfigureAwait(false);
        }
        catch (SocketException e)
        {
            throw new ToskarException(0, "DISCOVERY_FAILED", $"Couldn't look for computers on the network: {e.Message}", inner: e);
        }
        var computers = await Task.WhenAll(found.Select(s => ComputerAsync(s.Txt, s.Instance, s.Hosts, ReachableAsync))).ConfigureAwait(false);
        return computers.OfType<DiscoveredComputer>()
            .GroupBy(c => c.NodeId + c.Address).Select(g => g.First())
            .OrderBy(c => c.Name, StringComparer.Ordinal)
            .ToList();
    }

    /// <summary>A service that answered: its instance name, TXT record, and its host's addresses.</summary>
    internal sealed record Service(string Instance, IReadOnlyDictionary<string, string> Txt, IReadOnlyList<IPAddress> Hosts);

    /// <summary>
    /// Asks on every interface that can reach a home network, at once and
    /// again a second later, and reads the answers for timeout. A computer
    /// with a container network or a VPN has more than one interface, and the
    /// home network's may not be first.
    /// </summary>
    private static async Task<List<Service>> BrowseAsync(TimeSpan timeout, CancellationToken cancellationToken)
    {
        var interfaces = NetworkInterface.GetAllNetworkInterfaces()
            .Where(ni => ni.OperationalStatus == OperationalStatus.Up && ni.SupportsMulticast &&
                ni.NetworkInterfaceType is not (NetworkInterfaceType.Loopback or NetworkInterfaceType.Ppp or NetworkInterfaceType.Tunnel))
            .SelectMany(ni => ni.GetIPProperties().UnicastAddresses)
            .Select(a => a.Address)
            .Where(a => a.AddressFamily == AddressFamily.InterNetwork && !IPAddress.IsLoopback(a))
            .ToList();
        var records = new Answers();
        using var socket = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, ProtocolType.Udp);
        // The computer's own mDNS responder has the port too.
        socket.SetSocketOption(SocketOptionLevel.Socket, SocketOptionName.ReuseAddress, true);
        socket.Bind(new IPEndPoint(IPAddress.Any, Group.Port));
        foreach (var local in interfaces)
        {
            try
            {
                socket.SetSocketOption(SocketOptionLevel.IP, SocketOptionName.AddMembership, new MulticastOption(Group.Address, local));
            }
            catch (SocketException)
            {
            }
        }
        var query = Query($"{ServiceType}.local");
        void Ask()
        {
            foreach (var local in interfaces)
            {
                try
                {
                    socket.SetSocketOption(SocketOptionLevel.IP, SocketOptionName.MulticastInterface, local.GetAddressBytes());
                    socket.SendTo(query, Group);
                }
                catch (SocketException)
                {
                }
            }
        }
        Ask();
        var askedAgain = false;
        var started = DateTime.UtcNow;
        var buffer = new byte[9000];
        while (true)
        {
            var elapsed = DateTime.UtcNow - started;
            if (elapsed >= timeout)
            {
                break;
            }
            if (!askedAgain && elapsed >= TimeSpan.FromSeconds(1))
            {
                Ask();
                askedAgain = true;
            }
            using var wait = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            wait.CancelAfter(TimeSpan.FromMilliseconds(Math.Clamp((timeout - elapsed).TotalMilliseconds, 1, 250)));
            int n;
            try
            {
                n = await socket.ReceiveAsync(buffer, SocketFlags.None, wait.Token).ConfigureAwait(false);
            }
            catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
            {
                continue;
            }
            // Anything that isn't a well-formed answer is someone else's to worry about.
            try
            {
                records.Read(buffer.AsSpan(0, n).ToArray());
            }
            catch (Exception e) when (e is IndexOutOfRangeException or ArgumentException or InvalidDataException)
            {
            }
        }
        return records.Services($"{ServiceType}.local");
    }

    private const int TypeA = 1;
    private const int TypePtr = 12;
    private const int TypeTxt = 16;
    private const int TypeAaaa = 28;
    private const int TypeSrv = 33;

    /// <summary>A query for name's PTR records, as a one-shot querier sends it.</summary>
    internal static byte[] Query(string name)
    {
        var message = new List<byte> { 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0 };
        foreach (var label in name.Split('.'))
        {
            var bytes = Encoding.UTF8.GetBytes(label);
            message.Add((byte)bytes.Length);
            message.AddRange(bytes);
        }
        message.AddRange(new byte[] { 0, 0, TypePtr, 0, 1 });
        return message.ToArray();
    }

    /// <summary>The records the answers held, by name, gathered across packets.</summary>
    internal sealed class Answers
    {
        private readonly Dictionary<string, List<string>> ptr = new();
        private readonly Dictionary<string, string> srv = new();
        private readonly Dictionary<string, Dictionary<string, string>> txt = new();
        private readonly Dictionary<string, List<IPAddress>> hosts = new();

        /// <summary>Reads one mDNS message's records: answers and additional ones alike.</summary>
        internal void Read(byte[] m)
        {
            var r = new Reader(m);
            if ((r.U16(2) & 0x8000) == 0)
            {
                return; // a query, not an answer
            }
            var questions = r.U16(4);
            var count = r.U16(6) + r.U16(8) + r.U16(10);
            r.At = 12;
            for (var i = 0; i < questions; i++)
            {
                r.Name();
                r.At += 4;
            }
            for (var i = 0; i < count; i++)
            {
                var name = r.Name().ToLowerInvariant();
                var type = r.U16(r.At);
                var length = r.U16(r.At + 8);
                var data = r.At + 10;
                r.At = data + length;
                if (r.At > m.Length)
                {
                    throw new InvalidDataException("a record past the message's end");
                }
                switch (type)
                {
                    case TypePtr:
                        Add(ptr, name, new Reader(m, data).Name());
                        break;
                    case TypeSrv:
                        srv[name] = new Reader(m, data + 6).Name().ToLowerInvariant();
                        break;
                    case TypeTxt:
                        txt[name] = Text(m, data, length);
                        break;
                    case TypeA when length == 4:
                    case TypeAaaa when length == 16:
                        Add(hosts, name, new IPAddress(m.AsSpan(data, length)));
                        break;
                }
            }
        }

        private static void Add<T>(Dictionary<string, List<T>> map, string key, T value)
        {
            if (!map.TryGetValue(key, out var list))
            {
                map[key] = list = new List<T>();
            }
            if (!list.Contains(value))
            {
                list.Add(value);
            }
        }

        /// <summary>The instances of a service type, with what their records say.</summary>
        internal List<Service> Services(string type)
        {
            var services = new List<Service>();
            var suffix = "." + type.ToLowerInvariant();
            foreach (var full in ptr.GetValueOrDefault(type.ToLowerInvariant()) ?? new List<string>())
            {
                var key = full.ToLowerInvariant();
                if (!srv.TryGetValue(key, out var target))
                {
                    continue;
                }
                var instance = key.EndsWith(suffix, StringComparison.Ordinal) ? full[..^suffix.Length] : full;
                services.Add(new Service(
                    instance,
                    txt.GetValueOrDefault(key) ?? new Dictionary<string, string>(),
                    hosts.GetValueOrDefault(target) ?? new List<IPAddress>()));
            }
            return services;
        }

        private static Dictionary<string, string> Text(byte[] m, int at, int length)
        {
            var entries = new Dictionary<string, string>();
            for (var i = at; i < at + length;)
            {
                var n = m[i];
                var entry = Encoding.UTF8.GetString(m, i + 1, n);
                if (entry.Length > 0)
                {
                    var eq = entry.IndexOf('=');
                    entries[(eq < 0 ? entry : entry[..eq]).ToLowerInvariant()] = eq < 0 ? "" : entry[(eq + 1)..];
                }
                i += 1 + n;
            }
            return entries;
        }
    }

    /// <summary>Reads DNS names, with their compression, and numbers from a message.</summary>
    private sealed class Reader
    {
        private readonly byte[] m;

        internal Reader(byte[] m, int at = 0)
        {
            this.m = m;
            At = at;
        }

        internal int At { get; set; }

        internal int U16(int i) => (m[i] << 8) | m[i + 1];

        internal string Name()
        {
            var labels = new List<string>();
            var i = At;
            var jumped = false;
            var jumps = 0;
            while (true)
            {
                int n = m[i];
                if (n == 0)
                {
                    if (!jumped)
                    {
                        At = i + 1;
                    }
                    return string.Join('.', labels);
                }
                if ((n & 0xc0) == 0xc0)
                {
                    if (!jumped)
                    {
                        At = i + 2;
                    }
                    jumped = true;
                    if (++jumps > 32)
                    {
                        throw new InvalidDataException("a name that points in circles");
                    }
                    i = ((n & 0x3f) << 8) | m[i + 1];
                }
                else
                {
                    labels.Add(Encoding.UTF8.GetString(m, i + 1, n));
                    i += 1 + n;
                }
            }
        }
    }

    /// <summary>
    /// The computer a service describes, with the API's port from its TXT
    /// record (the service's own port is for computers pairing with each
    /// other), or null without one or without an address.
    /// </summary>
    internal static async Task<DiscoveredComputer?> ComputerAsync(
        IReadOnlyDictionary<string, string> txt, string instance, IReadOnlyList<IPAddress> hosts,
        Func<IReadOnlyList<string>, Task<string?>> reachable)
    {
        if (!txt.TryGetValue("api_port", out var p) || !int.TryParse(p, out var port) || port <= 0)
        {
            return null;
        }
        var addresses = hosts
            // A link-local IPv6 address needs its interface, which a URL can't carry.
            .Where(a => !(a.AddressFamily == AddressFamily.InterNetworkV6 && a.IsIPv6LinkLocal))
            .OrderBy(a => a.AddressFamily == AddressFamily.InterNetworkV6)
            // .NET writes IPv6 in its short form (RFC 5952), as the other SDKs do.
            .Select(a => a.AddressFamily == AddressFamily.InterNetworkV6 ? $"[{a}]:{port}" : $"{a}:{port}")
            .Distinct()
            .ToList();
        if (addresses.Count == 0)
        {
            return null;
        }
        return new DiscoveredComputer(
            txt.GetValueOrDefault("name") is { Length: > 0 } name ? name : instance,
            txt.GetValueOrDefault("node_id") ?? "",
            txt.GetValueOrDefault("version") ?? "",
            await reachable(addresses).ConfigureAwait(false) ?? addresses[0],
            addresses,
            txt.GetValueOrDefault("api_lan") != "false");
    }

    /// <summary>The first of addresses that takes a TCP connection, tried together.</summary>
    private static async Task<string?> ReachableAsync(IReadOnlyList<string> addresses)
    {
        var tries = addresses.Select(async address =>
        {
            var url = Connect.BaseOf(address);
            using var client = new TcpClient(url.HostNameType == UriHostNameType.IPv6 ? AddressFamily.InterNetworkV6 : AddressFamily.InterNetwork);
            using var within = new CancellationTokenSource(TimeSpan.FromMilliseconds(700));
            try
            {
                await client.ConnectAsync(url.IdnHost, url.Port, within.Token).ConfigureAwait(false);
                return true;
            }
            catch (Exception e) when (e is SocketException or OperationCanceledException)
            {
                return false;
            }
        }).ToList();
        for (var i = 0; i < addresses.Count; i++)
        {
            if (await tries[i].ConfigureAwait(false))
            {
                return addresses[i];
            }
        }
        return null;
    }
}
