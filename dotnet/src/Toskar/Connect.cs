// Connecting as a paired device, as the Toskar apps do (Toskar Core's
// docs/connecting.md): pairing with the code Connect a device shows, the
// computer's certificate pinned on every connection, and reaching it at
// home or, with access from anywhere, directly or through its relay.

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Net.Security;
using System.Security.Authentication;
using System.Security.Cryptography.X509Certificates;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading;
using System.Threading.Tasks;
using Toskar.Models;

namespace Toskar;

/// <summary>
/// What a paired device keeps, to connect again. Save it as a password is
/// saved: <see cref="ApiKey"/> and the route's secret and token are secrets.
/// <c>JsonSerializer</c> reads and writes it as the other SDKs' JSON.
/// </summary>
/// <param name="Address">The computer's host:port at home.</param>
/// <param name="ApiKey">The device's own key.</param>
/// <param name="Pin">"sha256:&lt;hex&gt;" of the computer's certificate. It only ever comes from pairing.</param>
/// <param name="Route">How to find the computer away from home, when it has access from anywhere.</param>
public sealed record Device(
    [property: JsonPropertyName("address")] string Address,
    [property: JsonPropertyName("api_key")] string ApiKey,
    [property: JsonPropertyName("pin")] string Pin,
    [property: JsonPropertyName("route"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] Route? Route = null);

/// <summary>How to find a computer away from home.</summary>
/// <param name="Secret">The route secret, base64url without padding.</param>
/// <param name="Id">The route's ID.</param>
/// <param name="Relay">The relay the computer uses, such as relay.toskar.ai.</param>
/// <param name="Token">Lets the device look the computer up on Toskar's relay.</param>
public sealed record Route(
    [property: JsonPropertyName("secret")] string Secret,
    [property: JsonPropertyName("id")] string Id,
    [property: JsonPropertyName("relay")] string Relay,
    [property: JsonPropertyName("token"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? Token = null);

/// <summary>How the client reaches its computer.</summary>
public enum ConnectionPath
{
    /// <summary>At its address at home.</summary>
    Home,

    /// <summary>Directly, at an address from its address record.</summary>
    Direct,

    /// <summary>Through its relay.</summary>
    Relay,
}

internal static class Pairing
{
    internal static async Task<Device> PairAsync(
        string address, string code, string deviceName, Func<string, Task<bool>>? confirm, CancellationToken cancellationToken)
    {
        var baseUri = Connect.BaseOf(address);
        var timeout = TimeSpan.FromSeconds(30);
        // The certificate the computer shows, for the person to check.
        var seeing = new Pinning(null);
        using (var http = seeing.Client(timeout))
        {
            try
            {
                using var _ = await http.GetAsync(new Uri(baseUri, "api/v1/health"), cancellationToken).ConfigureAwait(false);
            }
            catch (Exception e) when (e is HttpRequestException || (e is OperationCanceledException && !cancellationToken.IsCancellationRequested))
            {
                throw new ToskarException(0, "CONNECTION_FAILED", $"Couldn't reach the computer at {address}: {e.GetBaseException().Message}", inner: e);
            }
        }
        var seen = seeing.Seen ?? throw new ToskarException(0, "PIN_MISMATCH", "The computer showed no certificate");
        if (confirm is not null && !await confirm(Records.ShortPin(seen)).ConfigureAwait(false))
        {
            throw new ToskarException(0, "NOT_CONFIRMED", "The short pin wasn't confirmed");
        }

        // Then the code, to that certificate alone.
        PairedDevice paired;
        using (var http = new Pinning(seen).Client(timeout))
        {
            using var request = new HttpRequestMessage(HttpMethod.Post, new Uri(baseUri, "api/v1/devices/pair"))
            {
                Content = ToskarClient.JsonContent(new Dictionary<string, string> { ["code"] = code, ["device_name"] = deviceName }),
            };
            request.Headers.Add("Toskar-Client-Contract", Contract.Version);
            using var response = await Connect.Pinned(() => http.SendAsync(request, cancellationToken)).ConfigureAwait(false);
            var text = await response.Content.ReadAsStringAsync(cancellationToken).ConfigureAwait(false);
            if ((int)response.StatusCode >= 300)
            {
                throw ToskarException.Of((int)response.StatusCode, text);
            }
            paired = JsonSerializer.Deserialize<PairedDevice>(text, CoreJson.Options)!;
        }
        if (!string.Equals(paired.TlsFingerprint, seen, StringComparison.OrdinalIgnoreCase))
        {
            throw Connect.PinMismatch();
        }
        var route = string.IsNullOrEmpty(paired.RouteSecret)
            ? null
            : new Route(paired.RouteSecret, paired.RouteId ?? "", paired.Relay ?? "", paired.Token);
        return new Device(address, paired.ApiKey, seen, route);
    }
}

/// <summary>A certificate other than the paired one, refused before any request is sent.</summary>
internal sealed class PinMismatchException : AuthenticationException
{
    internal PinMismatchException()
        : base("The computer's certificate isn't the one paired with")
    {
    }
}

/// <summary>
/// Trusts exactly the certificate with pin, checked before any request is
/// sent; names, dates, and signers aren't checked. With no pin, it trusts
/// any certificate and keeps its pin in Seen, for pairing.
/// </summary>
internal sealed class Pinning
{
    private readonly string? pin;
    private volatile string? seen;

    internal Pinning(string? pin) => this.pin = pin;

    internal string? Seen => seen;

    private bool Check(object sender, X509Certificate? certificate, X509Chain? chain, SslPolicyErrors errors)
    {
        if (certificate is null)
        {
            throw new PinMismatchException();
        }
        var got = Records.PinOf(certificate.GetRawCertData());
        if (pin is null)
        {
            seen = got;
            return true;
        }
        // Thrown, not answered false, so a refused certificate can be told
        // from a computer that isn't there.
        return string.Equals(got, pin, StringComparison.OrdinalIgnoreCase) ? true : throw new PinMismatchException();
    }

    /// <summary>A handler whose connections are pinned.</summary>
    internal SocketsHttpHandler Handler(TimeSpan timeout) => new()
    {
        ConnectTimeout = timeout,
        // The way in changes, and a computer's restart drops its connections.
        PooledConnectionLifetime = TimeSpan.FromMinutes(5),
        SslOptions = new SslClientAuthenticationOptions { RemoteCertificateValidationCallback = Check },
    };

    internal HttpClient Client(TimeSpan timeout) => new(Handler(timeout)) { Timeout = timeout };
}

/// <summary>
/// Chooses the way in, and again when it stops answering: home first, then
/// the address record's ways, the direct ones at once and the relay's a
/// second later.
/// </summary>
internal sealed class Router
{
    internal static readonly TimeSpan HomeTimeout = TimeSpan.FromMilliseconds(2500);
    internal static readonly TimeSpan TryTimeout = TimeSpan.FromSeconds(6);
    internal static readonly TimeSpan RelayDelay = TimeSpan.FromSeconds(1);
    internal static readonly TimeSpan RecordMaxAge = TimeSpan.FromHours(1);
    internal const int RecordLimit = 1 << 20;

    /// <summary>Toskar's own relay. It's asked only with a route token.</summary>
    internal const string ToskarRelay = "relay.toskar.ai";

    private readonly Device device;
    private readonly HttpClient pinned;
    private readonly HttpClient relay;
    private readonly SemaphoreSlim choosing = new(1, 1);
    private volatile string? way;
    private ConnectionPath? path;

    internal Router(Device device, HttpClient pinned, HttpClient relay)
    {
        this.device = device;
        this.pinned = pinned;
        this.relay = relay;
    }

    internal ConnectionPath? Path => way is null ? null : path;

    internal void Forget() => way = null;

    internal void Forget(string used)
    {
        if (way == used)
        {
            way = null;
        }
    }

    /// <summary>The way in to use, host:port, choosing one when there's none.</summary>
    internal async Task<string> CurrentAsync(CancellationToken cancellationToken)
    {
        if (way is { } known)
        {
            return known;
        }
        await choosing.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            if (way is { } chosen)
            {
                return chosen;
            }
            var (found, at) = await ChooseAsync(cancellationToken).ConfigureAwait(false);
            path = found;
            way = at;
            return at;
        }
        finally
        {
            choosing.Release();
        }
    }

    /// <summary>Whether the computer answers health at address, pinned, within timeout. Another certificate throws <c>PIN_MISMATCH</c>.</summary>
    private async Task<bool> AnswersAsync(string address, TimeSpan timeout, CancellationToken cancellationToken)
    {
        Uri url;
        try
        {
            url = new Uri(Connect.BaseOf(address), "api/v1/health");
        }
        catch (ToskarException)
        {
            return false;
        }
        using var within = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        within.CancelAfter(timeout);
        // With the key: a computer that asks for one answers health only
        // with it. The connection is pinned before anything is sent.
        using var request = new HttpRequestMessage(HttpMethod.Get, url);
        request.Headers.TryAddWithoutValidation("Authorization", $"Bearer {device.ApiKey}");
        try
        {
            using var response = await Connect.Pinned(() => pinned.SendAsync(request, within.Token)).ConfigureAwait(false);
            if ((int)response.StatusCode != 200)
            {
                return false;
            }
            using var health = JsonDocument.Parse(await response.Content.ReadAsStringAsync(within.Token).ConfigureAwait(false));
            return health.RootElement.TryGetProperty("status", out var status) && status.ValueKind == JsonValueKind.String &&
                status.GetString() == "ok";
        }
        catch (Exception e) when (e is HttpRequestException or JsonException || (e is OperationCanceledException && !cancellationToken.IsCancellationRequested))
        {
            return false;
        }
    }

    private async Task<(ConnectionPath, string)> ChooseAsync(CancellationToken cancellationToken)
    {
        // Home answering with another certificate means the computer's
        // changed, or it isn't the computer: say so; pairing again is the
        // way on.
        if (await AnswersAsync(device.Address, HomeTimeout, cancellationToken).ConfigureAwait(false))
        {
            return (ConnectionPath.Home, device.Address);
        }
        var route = device.Route is { Secret.Length: > 0 } r ? r : throw Unreachable();
        var relayHost = Connect.HostOnly(route.Relay).ToLowerInvariant();
        // Toskar's relay answers only for a subscription; without one, it
        // isn't asked, so nothing about this device reaches it.
        if (relayHost == ToskarRelay && string.IsNullOrEmpty(route.Token))
        {
            throw Unreachable();
        }
        var record = await RecordAsync(route, cancellationToken).ConfigureAwait(false);
        if (record.Addresses.Count == 0)
        {
            throw Unreachable();
        }
        using var done = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        var tries = record.Addresses.Select(async address =>
        {
            var isRelay = Connect.HostOnly(address).ToLowerInvariant().EndsWith("." + relayHost, StringComparison.Ordinal);
            if (isRelay)
            {
                await Task.Delay(RelayDelay, done.Token).ConfigureAwait(false);
            }
            // Another certificate at a way in is someone else's device
            // there: that way just doesn't count.
            bool ok;
            try
            {
                ok = await AnswersAsync(address, TryTimeout, done.Token).ConfigureAwait(false);
            }
            catch (ToskarException)
            {
                ok = false;
            }
            return ok ? ((ConnectionPath, string)?)(isRelay ? ConnectionPath.Relay : ConnectionPath.Direct, address) : null;
        }).ToList();
        try
        {
            while (tries.Count > 0)
            {
                var first = await Task.WhenAny(tries).ConfigureAwait(false);
                tries.Remove(first);
                if (first.IsCompletedSuccessfully && first.Result is { } found)
                {
                    return found;
                }
            }
        }
        finally
        {
            done.Cancel();
        }
        cancellationToken.ThrowIfCancellationRequested();
        throw Unreachable();
    }

    private async Task<AddressRecord> RecordAsync(Route route, CancellationToken cancellationToken)
    {
        Uri url;
        try
        {
            url = new Uri(Connect.BaseOf(route.Relay), $"v1/routes/{Uri.EscapeDataString(route.Id)}/record");
        }
        catch (ToskarException)
        {
            throw NoRecord();
        }
        using var within = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        within.CancelAfter(TryTimeout);
        using var request = new HttpRequestMessage(HttpMethod.Get, url);
        if (!string.IsNullOrEmpty(route.Token))
        {
            request.Headers.TryAddWithoutValidation("Authorization", $"Bearer {route.Token}");
        }
        byte[] data;
        try
        {
            using var response = await relay.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, within.Token).ConfigureAwait(false);
            if ((int)response.StatusCode != 200 || response.Content.Headers.ContentLength > RecordLimit)
            {
                throw NoRecord();
            }
            await using var body = await response.Content.ReadAsStreamAsync(within.Token).ConfigureAwait(false);
            using var buffer = new MemoryStream();
            var chunk = new byte[16 * 1024];
            int n;
            while ((n = await body.ReadAsync(chunk, within.Token).ConfigureAwait(false)) > 0)
            {
                buffer.Write(chunk, 0, n);
                if (buffer.Length > RecordLimit)
                {
                    throw NoRecord();
                }
            }
            data = buffer.ToArray();
        }
        catch (Exception e) when (e is HttpRequestException or IOException || (e is OperationCanceledException && !cancellationToken.IsCancellationRequested))
        {
            throw NoRecord(e);
        }
        return Records.Open(data, route.Secret, device.Pin, maxAge: RecordMaxAge);
    }

    internal static ToskarException Unreachable() => new(0, "UNREACHABLE", "The computer can't be reached");

    /// <summary>inner, when there is one, says why the relay couldn't be asked, such as its certificate.</summary>
    internal static ToskarException NoRecord(Exception? inner = null) => new(
        0, "NO_RECORD", "No address record for the computer: it may be off or asleep, or have no access from anywhere", inner: inner);
}

internal static class Connect
{
    internal static ToskarException PinMismatch(Exception? inner = null) =>
        new(0, "PIN_MISMATCH", "The computer's certificate isn't the one paired with", inner: inner);

    internal static bool IsPinMismatch(Exception e)
    {
        for (Exception? x = e; x is not null; x = x.InnerException)
        {
            if (x is PinMismatchException)
            {
                return true;
            }
        }
        return false;
    }

    /// <summary>Sends over a pinned client, with a refused certificate thrown as <c>PIN_MISMATCH</c>.</summary>
    internal static async Task<HttpResponseMessage> Pinned(Func<Task<HttpResponseMessage>> send)
    {
        try
        {
            return await send().ConfigureAwait(false);
        }
        catch (HttpRequestException e) when (IsPinMismatch(e))
        {
            throw PinMismatch(e);
        }
    }

    /// <summary>The way in's address, host:port, as a base URL.</summary>
    internal static Uri BaseOf(string way) =>
        Uri.TryCreate($"https://{way}/", UriKind.Absolute, out var uri) && uri.AbsolutePath == "/" && uri.Query.Length == 0
            ? uri
            : throw new ToskarException(0, "BAD_ADDRESS", $"{way} isn't host:port");

    /// <summary>The host of host:port, [v6]:port, or a bare host or IPv6 address.</summary>
    internal static string HostOnly(string address)
    {
        if (address.StartsWith('['))
        {
            var end = address.IndexOf(']');
            if (end > 0)
            {
                return address[1..end];
            }
        }
        if (address.Count(c => c == ':') == 1)
        {
            return address[..address.LastIndexOf(':')];
        }
        return address;
    }
}
