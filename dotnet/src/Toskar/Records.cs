// Address records: how a paired device finds its computer away from home
// (Toskar Core's docs/connecting.md). A record is sealed with the route
// secret only the computer and its paired devices have, and signed by the
// computer's own certificate, so a relay that keeps it can neither read it
// nor change it.

using System;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace Toskar;

/// <summary>What an address record says: the computer's ways in, and when it wrote them.</summary>
public sealed record AddressRecord(IReadOnlyList<string> Addresses, DateTimeOffset At);

/// <summary>Address records, and the route IDs and pins they're checked with.</summary>
public static class Records
{
    /// <summary>The route ID a route secret names.</summary>
    public static string RouteId(string secret) =>
        LowerBase32(Hkdf(RouteSecret(secret), "toskar route id", 20));

    /// <summary>The pin of a certificate: "sha256:&lt;hex&gt;" of its DER.</summary>
    public static string PinOf(byte[] der) => "sha256:" + Convert.ToHexString(SHA256.HashData(der)).ToLowerInvariant();

    /// <summary>How a pin is shown for the person to compare: its first 8 hex digits, as ABCD-1234.</summary>
    public static string ShortPin(string pin)
    {
        var hex = (pin.StartsWith("sha256:", StringComparison.Ordinal) ? pin["sha256:".Length..] : pin).ToUpperInvariant();
        return hex.Length < 8 ? hex : $"{hex[..4]}-{hex[4..8]}";
    }

    /// <summary>
    /// Opens an address record as docs/connecting.md says: sealed with the
    /// route secret, from the certificate with pin, for this route, and no
    /// older than maxAge (an hour by default). It throws a
    /// <see cref="ToskarException"/> with <c>RECORD_SEALED</c>,
    /// <c>RECORD_PIN</c>, or <c>RECORD_STALE</c> otherwise.
    /// </summary>
    public static AddressRecord Open(byte[] blob, string secret, string pin, DateTimeOffset? now = null, TimeSpan? maxAge = null)
    {
        var route = RouteId(secret);
        var key = Hkdf(RouteSecret(secret), "toskar route key", 32);
        var sealedError = new ToskarException(0, "RECORD_SEALED", "The record doesn't open with this route secret");
        // The nonce, then the sealed record and its tag.
        if (blob.Length < 12 + 16)
        {
            throw sealedError;
        }
        var plain = new byte[blob.Length - 12 - 16];
        try
        {
            using var gcm = new AesGcm(key, 16);
            gcm.Decrypt(blob.AsSpan(0, 12), blob.AsSpan(12, plain.Length), blob.AsSpan(blob.Length - 16), plain, Encoding.UTF8.GetBytes(route));
        }
        catch (CryptographicException)
        {
            throw sealedError;
        }
        Signed? signed;
        try
        {
            signed = JsonSerializer.Deserialize<Signed>(plain);
        }
        catch (JsonException)
        {
            throw sealedError;
        }
        if (signed?.Payload is null || signed.Cert is null || signed.Alg is null || signed.Sig is null)
        {
            throw sealedError;
        }
        var fromPinned = new ToskarException(0, "RECORD_PIN", "The record isn't from the pinned computer");
        byte[] payload, cert, sig;
        Body? body;
        try
        {
            payload = Convert.FromBase64String(signed.Payload);
            cert = Convert.FromBase64String(signed.Cert);
            sig = Convert.FromBase64String(signed.Sig);
            body = JsonSerializer.Deserialize<Body>(payload);
        }
        catch (Exception e) when (e is FormatException or JsonException)
        {
            throw fromPinned;
        }
        if (!string.Equals(PinOf(cert), pin, StringComparison.OrdinalIgnoreCase) ||
            !Verify(sig, payload, signed.Alg, cert) ||
            body is null || body.V != 1 || body.Route != route)
        {
            throw fromPinned;
        }
        var at = DateTimeOffset.FromUnixTimeSeconds(body.At);
        var time = now ?? DateTimeOffset.UtcNow;
        if (time - at > (maxAge ?? TimeSpan.FromHours(1)) || at - time > TimeSpan.FromMinutes(5))
        {
            throw new ToskarException(0, "RECORD_STALE", "The record is too old");
        }
        return new AddressRecord(body.Addresses ?? new List<string>(), at);
    }

    private sealed record Signed(
        [property: JsonPropertyName("payload")] string? Payload,
        [property: JsonPropertyName("cert")] string? Cert,
        [property: JsonPropertyName("alg")] string? Alg,
        [property: JsonPropertyName("sig")] string? Sig);

    private sealed record Body(
        [property: JsonPropertyName("v")] int V,
        [property: JsonPropertyName("route")] string? Route,
        [property: JsonPropertyName("at")] long At,
        [property: JsonPropertyName("addresses")] List<string>? Addresses);

    internal static byte[] RouteSecret(string secret)
    {
        try
        {
            var s = Base64Url(secret);
            if (s.Length == 32)
            {
                return s;
            }
        }
        catch (FormatException)
        {
        }
        throw new ToskarException(0, "BAD_ROUTE_SECRET", "A route secret is 32 bytes, base64url");
    }

    private static byte[] Base64Url(string s)
    {
        var b64 = s.TrimEnd('=').Replace('-', '+').Replace('_', '/');
        return Convert.FromBase64String(b64 + new string('=', (4 - b64.Length % 4) % 4));
    }

    /// <summary>HKDF-SHA256 with no salt (RFC 5869).</summary>
    internal static byte[] Hkdf(byte[] secret, string info, int length) =>
        HKDF.DeriveKey(HashAlgorithmName.SHA256, secret, length, Array.Empty<byte>(), Encoding.UTF8.GetBytes(info));

    /// <summary>RFC 4648 base32 in lower case, without padding, as route IDs are.</summary>
    internal static string LowerBase32(byte[] data)
    {
        const string alphabet = "abcdefghijklmnopqrstuvwxyz234567";
        var text = new StringBuilder();
        int buffer = 0, bits = 0;
        foreach (var b in data)
        {
            buffer = (buffer << 8) | b;
            bits += 8;
            while (bits >= 5)
            {
                text.Append(alphabet[(buffer >> (bits - 5)) & 31]);
                bits -= 5;
            }
        }
        if (bits > 0)
        {
            text.Append(alphabet[(buffer << (5 - bits)) & 31]);
        }
        return text.ToString();
    }

    /// <summary>
    /// Whether sig signs payload with the key in cert, by alg: ECDSA P-256
    /// and RSA PKCS #1 v1.5 with SHA-256, and Ed25519, which .NET doesn't
    /// have, so BouncyCastle checks it.
    /// </summary>
    internal static bool Verify(byte[] sig, byte[] payload, string alg, byte[] cert)
    {
        try
        {
            using var x509 = new X509Certificate2(cert);
            switch (alg)
            {
                case "ecdsa-sha256":
                    using (var ec = x509.GetECDsaPublicKey())
                    {
                        return ec is not null && ec.VerifyData(payload, sig, HashAlgorithmName.SHA256, DSASignatureFormat.Rfc3279DerSequence);
                    }
                case "rsa-pkcs1-sha256":
                    using (var rsa = x509.GetRSAPublicKey())
                    {
                        return rsa is not null && rsa.VerifyData(payload, sig, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);
                    }
                case "ed25519":
                    var key = x509.PublicKey.EncodedKeyValue.RawData;
                    // The key is a BIT STRING's 32 bytes.
                    return x509.PublicKey.Oid.Value == "1.3.101.112" && key.Length == 32 && sig.Length == 64 &&
                        Org.BouncyCastle.Math.EC.Rfc8032.Ed25519.Verify(sig, 0, key, 0, payload, 0, payload.Length);
                default:
                    return false;
            }
        }
        catch (CryptographicException)
        {
            return false;
        }
    }
}
