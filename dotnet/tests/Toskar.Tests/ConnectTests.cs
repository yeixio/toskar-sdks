using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.Security;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Threading;
using System.Threading.Tasks;
using Xunit;

namespace Toskar.Tests;

/// <summary>
/// spec/connection-vectors.json, which Toskar Core's reference code keeps
/// true, so every SDK opens records as Core writes them.
/// </summary>
public class ConnectTests
{
    private static JsonNode Vectors() =>
        JsonNode.Parse(File.ReadAllText(Path.Combine(Repo.Root, "spec", "connection-vectors.json")))!;

    [Fact]
    public void RouteIdsAreCores()
    {
        foreach (var r in Vectors()["routes"]!.AsArray())
        {
            Assert.Equal((string)r!["route_id"]!, Records.RouteId((string)r["secret"]!));
        }
        Assert.Equal("BAD_ROUTE_SECRET", Assert.Throws<ToskarException>(() => Records.RouteId("too-short")).Code);
    }

    [Fact]
    public void PinsAreCores()
    {
        var pins = Vectors()["pins"]!.AsArray();
        Assert.Equal(3, pins.Count);
        foreach (var p in pins)
        {
            var fingerprint = (string)p!["fingerprint"]!;
            Assert.Equal(fingerprint, Records.PinOf(Convert.FromBase64String((string)p["cert_der_base64"]!)));
            Assert.Equal((string)p["short"]!, Records.ShortPin(fingerprint));
        }
    }

    [Fact]
    public void RecordsOpenAsCoreSays()
    {
        var errors = new Dictionary<string, string> { ["sealed"] = "RECORD_SEALED", ["pin"] = "RECORD_PIN", ["stale"] = "RECORD_STALE" };
        foreach (var r in Vectors()["records"]!.AsArray())
        {
            var name = (string)r!["name"]!;
            AddressRecord Open() => Records.Open(
                Convert.FromBase64String((string)r["blob_base64"]!), (string)r["secret"]!, (string)r["pin"]!,
                DateTimeOffset.FromUnixTimeSeconds((long)r["now"]!), TimeSpan.FromSeconds((long)r["max_age_seconds"]!));
            if (r["error"] is { } error)
            {
                var e = Assert.Throws<ToskarException>(Open);
                Assert.True(errors[(string)error!] == e.Code, $"{name}: {e.Code}");
            }
            else
            {
                var record = Open();
                Assert.Equal(r["addresses"]!.AsArray().Select(a => (string)a!), record.Addresses);
                Assert.Equal((long)r["at"]!, record.At.ToUnixTimeSeconds());
            }
        }
    }

    [Fact]
    public void SavedDevicesAreTheOtherSdksJson()
    {
        const string json = """{"address":"192.168.1.20:7331","api_key":"tk_1","pin":"sha256:ab","route":{"secret":"s","id":"i","relay":"relay.toskar.ai","token":"t"}}""";
        var device = JsonSerializer.Deserialize<Device>(json)!;
        Assert.Equal("tk_1", device.ApiKey);
        Assert.Equal("t", device.Route?.Token);
        Assert.Equal(json, JsonSerializer.Serialize(device));
        // One without access from anywhere has no route.
        Assert.Equal("""{"address":"a:1","api_key":"k","pin":"p"}""", JsonSerializer.Serialize(new Device("a:1", "k", "p")));
    }

    [Fact]
    public void HostsOfAddresses()
    {
        Assert.Equal("studio.local", Connect.HostOnly("studio.local:7331"));
        Assert.Equal("fe80::1", Connect.HostOnly("[fe80::1]:7331"));
        Assert.Equal("fe80::1", Connect.HostOnly("fe80::1"));
        Assert.Equal("relay.toskar.ai", Connect.HostOnly("relay.toskar.ai"));
    }
}

internal static class Repo
{
    /// <summary>The repository, above the test's build output.</summary>
    internal static string Root
    {
        get
        {
            for (var dir = new DirectoryInfo(AppContext.BaseDirectory); dir is not null; dir = dir.Parent)
            {
                if (Directory.Exists(Path.Combine(dir.FullName, "spec")) && Directory.Exists(Path.Combine(dir.FullName, "dotnet")))
                {
                    return dir.FullName;
                }
            }
            throw new DirectoryNotFoundException("No repository above " + AppContext.BaseDirectory);
        }
    }
}

/// <summary>A computer that answers HTTPS with its own certificate: just enough HTTP/1.1 for a client's requests.</summary>
internal sealed class Computer : IDisposable
{
    private readonly TcpListener listener = new(IPAddress.Loopback, 0);
    private readonly X509Certificate2 certificate;
    private readonly Func<string, string?, (int, string)> answer;
    private readonly CancellationTokenSource stop = new();

    internal Computer(X509Certificate2 certificate, Func<string, string?, (int Status, string Body)> answer)
    {
        this.certificate = certificate;
        this.answer = answer;
        listener.Start();
        _ = Task.Run(AcceptAsync);
    }

    internal string Address => $"127.0.0.1:{((IPEndPoint)listener.LocalEndpoint).Port}";

    internal List<string> Paths { get; } = new();

    private async Task AcceptAsync()
    {
        while (!stop.IsCancellationRequested)
        {
            TcpClient client;
            try
            {
                client = await listener.AcceptTcpClientAsync(stop.Token);
            }
            catch (Exception)
            {
                return;
            }
            _ = Task.Run(() => ServeAsync(client));
        }
    }

    private async Task ServeAsync(TcpClient client)
    {
        using var _ = client;
        try
        {
            await using var tls = new SslStream(client.GetStream());
            await tls.AuthenticateAsServerAsync(certificate);
            using var reader = new StreamReader(tls, Encoding.ASCII, leaveOpen: true);
            while (await reader.ReadLineAsync() is { Length: > 0 } line)
            {
                var path = line.Split(' ')[1];
                string? authorization = null;
                var length = 0;
                while (await reader.ReadLineAsync() is { Length: > 0 } header)
                {
                    var (name, value) = (header[..header.IndexOf(':')].ToLowerInvariant(), header[(header.IndexOf(':') + 1)..].Trim());
                    if (name == "authorization")
                    {
                        authorization = value;
                    }
                    else if (name == "content-length")
                    {
                        length = int.Parse(value);
                    }
                }
                var body = new char[length];
                for (var read = 0; read < length;)
                {
                    read += await reader.ReadAsync(body.AsMemory(read));
                }
                lock (Paths)
                {
                    Paths.Add(path);
                }
                var (status, text) = answer(path, authorization);
                var bytes = Encoding.UTF8.GetBytes(text);
                await tls.WriteAsync(Encoding.ASCII.GetBytes(
                    $"HTTP/1.1 {status} X\r\nContent-Type: application/json\r\nContent-Length: {bytes.Length}\r\n\r\n"));
                await tls.WriteAsync(bytes);
                await tls.FlushAsync();
            }
        }
        catch (Exception)
        {
            // A client that refused the certificate, or hung up.
        }
    }

    public void Dispose()
    {
        stop.Cancel();
        listener.Stop();
    }

    /// <summary>A self-signed ECDSA P-256 certificate, as Core makes.</summary>
    internal static X509Certificate2 Certificate(string name = "Studio")
    {
        using var key = ECDsa.Create(ECCurve.NamedCurves.nistP256);
        var request = new CertificateRequest($"CN={name}", key, HashAlgorithmName.SHA256);
        using var made = request.CreateSelfSigned(DateTimeOffset.UtcNow.AddDays(-1), DateTimeOffset.UtcNow.AddDays(30));
        // Through PKCS #12, so the key isn't ephemeral, which macOS's TLS refuses.
#pragma warning disable SYSLIB0057
        return new X509Certificate2(made.Export(X509ContentType.Pkcs12));
#pragma warning restore SYSLIB0057
    }
}

/// <summary>A computer away from home: its certificate, served over HTTPS, and a relay that keeps its address record.</summary>
public sealed class AwayTests : IDisposable
{
    private readonly X509Certificate2 computerCert = Computer.Certificate();
    private readonly Computer computer;
    private readonly string secret = Convert.ToBase64String(Enumerable.Range(0, 32).Select(i => (byte)i).ToArray())
        .TrimEnd('=').Replace('+', '-').Replace('/', '_');
    private readonly string pin;

    public AwayTests()
    {
        computer = new Computer(computerCert, (path, authorization) => path switch
        {
            "/api/v1/health" => authorization == "Bearer tk_away"
                ? (200, """{"status":"ok"}""")
                : (401, """{"error":{"code":"UNAUTHORIZED","message":"no"}}"""),
            _ => (200, ClientTests.Version),
        });
        pin = Records.PinOf(computerCert.RawData);
    }

    public void Dispose()
    {
        computer.Dispose();
        computerCert.Dispose();
    }

    /// <summary>An address that refuses connections: home, with the computer away.</summary>
    private static string Nowhere()
    {
        var l = new TcpListener(IPAddress.Loopback, 0);
        l.Start();
        var port = ((IPEndPoint)l.LocalEndpoint).Port;
        l.Stop();
        return $"127.0.0.1:{port}";
    }

    /// <summary>A record as Core writes it: signed by the computer's certificate, sealed with the route secret.</summary>
    private byte[] Record(IEnumerable<string> addresses, DateTimeOffset? at = null)
    {
        var route = Records.RouteId(secret);
        var payload = JsonSerializer.SerializeToUtf8Bytes(new Dictionary<string, object>
        {
            ["v"] = 1,
            ["route"] = route,
            ["at"] = (at ?? DateTimeOffset.UtcNow).ToUnixTimeSeconds(),
            ["addresses"] = addresses.ToArray(),
        });
        using var key = computerCert.GetECDsaPrivateKey()!;
        var sig = key.SignData(payload, HashAlgorithmName.SHA256, DSASignatureFormat.Rfc3279DerSequence);
        var signed = JsonSerializer.SerializeToUtf8Bytes(new Dictionary<string, string>
        {
            ["payload"] = Convert.ToBase64String(payload),
            ["cert"] = Convert.ToBase64String(computerCert.RawData),
            ["alg"] = "ecdsa-sha256",
            ["sig"] = Convert.ToBase64String(sig),
        });
        var nonce = RandomNumberGenerator.GetBytes(12);
        var sealedBytes = new byte[signed.Length];
        var tag = new byte[16];
        using var gcm = new AesGcm(Records.Hkdf(Records.RouteSecret(secret), "toskar route key", 32), 16);
        gcm.Encrypt(nonce, signed, sealedBytes, tag, Encoding.UTF8.GetBytes(route));
        return nonce.Concat(sealedBytes).Concat(tag).ToArray();
    }

    private Device Device(string home, string? token = "rt", string relay = "relay.test") =>
        new(home, "tk_away", pin, new Route(secret, Records.RouteId(secret), relay, token));

    /// <summary>A relay that answers with a record.</summary>
    private static FakeCore Relay(byte[] record) => new(new FakeCore.Answer(Bytes: record));

    private static ToskarClient Toskar(Device device, FakeCore relay) =>
        new(device, new ToskarOptions { Retries = 0, Timeout = TimeSpan.FromSeconds(5) }, new HttpClient(relay));

    [Fact]
    public async Task ReachesItDirectlyFromItsRecord()
    {
        var relay = Relay(Record(new[] { computer.Address }));
        using var toskar = Toskar(Device(Nowhere()), relay);
        Assert.Null(toskar.Path);
        Assert.Equal("1.12.0", (await toskar.VersionAsync()).Version);
        Assert.Equal(ConnectionPath.Direct, toskar.Path);
        var asked = relay.Sent.Single().Request;
        Assert.Equal($"https://relay.test/v1/routes/{Records.RouteId(secret)}/record", asked.RequestUri!.ToString());
        Assert.Equal("Bearer rt", asked.Headers.Authorization?.ToString());
    }

    [Fact]
    public async Task TakesHomeWhenItAnswers()
    {
        var relay = new FakeCore();
        using var toskar = Toskar(Device(computer.Address), relay);
        await toskar.VersionAsync();
        Assert.Equal(ConnectionPath.Home, toskar.Path);
        Assert.Empty(relay.Sent);
        Assert.Equal(ConnectionPath.Home, await toskar.ReconnectAsync());
    }

    [Fact]
    public async Task AnotherCertificateAtHomeIsRefused()
    {
        var other = Device(computer.Address) with { Pin = "sha256:" + string.Concat(Enumerable.Repeat("ab", 32)) };
        using var toskar = Toskar(other, new FakeCore());
        Assert.Equal("PIN_MISMATCH", (await Assert.ThrowsAsync<ToskarException>(() => toskar.VersionAsync())).Code);
    }

    [Fact]
    public async Task ARecordFromAnotherComputerIsRefused()
    {
        using var stranger = Computer.Certificate("Stranger");
        var relay = Relay(Record(new[] { computer.Address }));
        using var toskar = Toskar(Device(Nowhere()) with { Pin = Records.PinOf(stranger.RawData) }, relay);
        Assert.Equal("RECORD_PIN", (await Assert.ThrowsAsync<ToskarException>(() => toskar.VersionAsync())).Code);
    }

    [Fact]
    public async Task WithNoRecordItSaysSo()
    {
        using var toskar = Toskar(Device(Nowhere()), new FakeCore(new FakeCore.Answer(404)));
        Assert.Equal("NO_RECORD", (await Assert.ThrowsAsync<ToskarException>(() => toskar.VersionAsync())).Code);
    }

    [Fact]
    public async Task ToskarsRelayIsntAskedWithoutAToken()
    {
        var relay = new FakeCore();
        using var toskar = Toskar(Device(Nowhere(), token: null, relay: "relay.toskar.ai"), relay);
        Assert.Equal("UNREACHABLE", (await Assert.ThrowsAsync<ToskarException>(() => toskar.VersionAsync())).Code);
        Assert.Empty(relay.Sent);
    }

    [Fact]
    public async Task PairsAndPinsWhatItSaw()
    {
        var paired = new Computer(computerCert, (path, _) => path switch
        {
            "/api/v1/devices/pair" => (200, $$$"""{"api_key":"tk_new","key":{"id":"k1","name":"Phone","prefix":"tk_n","created_at":"2026-10-30T00:00:00Z","revoked":false,"person_id":"p1","permissions":{"memory":"read","knowledge":"read","tools":"none","placement":false}},"tls_fingerprint":"{{{pin}}}","tls_short":"{{{Records.ShortPin(pin)}}}"}"""),
            _ => (200, """{"status":"ok"}"""),
        });
        using var _ = paired;
        string? shown = null;
        var device = await ToskarClient.PairAsync(paired.Address, "123456", "Test", s => { shown = s; return true; });
        Assert.Equal(new Device(paired.Address, "tk_new", pin), device);
        Assert.Equal(Records.ShortPin(pin), shown);
        Assert.Equal("NOT_CONFIRMED", (await Assert.ThrowsAsync<ToskarException>(
            () => ToskarClient.PairAsync(paired.Address, "123456", "Test", _ => false))).Code);
    }
}
