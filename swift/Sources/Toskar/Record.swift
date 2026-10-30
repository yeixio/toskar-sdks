// Address records: how a paired device finds its computer away from home
// (Toskar Core's docs/connecting.md). A record is sealed with the route
// secret only the computer and its paired devices have, and signed by the
// computer's own certificate, so a relay that keeps it can neither read it
// nor change it.

#if canImport(CryptoKit) && canImport(Security)
    import CryptoKit
    import Foundation
    import Security

    /// What an address record says: the computer's ways in, and when it
    /// wrote them.
    public struct AddressRecord: Sendable, Hashable {
        public let addresses: [String]
        public let at: Date
    }

    extension Toskar {
        /// The route ID a route secret names.
        public static func routeID(_ secret: String) throws -> String {
            let s = try routeSecret(secret)
            let id = HKDF<SHA256>.deriveKey(
                inputKeyMaterial: SymmetricKey(data: s), info: Data("toskar route id".utf8), outputByteCount: 20)
            return id.withUnsafeBytes { lowerBase32(Data($0)) }
        }

        /// Opens an address record as docs/connecting.md says: sealed with
        /// the route secret, from the certificate with pin, for this route,
        /// and no older than maxAge. It throws `.recordSealed`,
        /// `.recordPin`, or `.recordStale` otherwise.
        public static func openRecord(
            _ blob: Data, secret: String, pin: String, now: Date = Date(), maxAge: TimeInterval = 3600
        ) throws -> AddressRecord {
            let s = try routeSecret(secret)
            let route = try routeID(secret)
            let key = HKDF<SHA256>.deriveKey(
                inputKeyMaterial: SymmetricKey(data: s), info: Data("toskar route key".utf8), outputByteCount: 32)
            // The nonce, then the sealed record and its tag: AES-GCM's combined form.
            guard blob.count >= 12 + 16, let box = try? AES.GCM.SealedBox(combined: blob),
                let plain = try? AES.GCM.open(box, using: key, authenticating: Data(route.utf8))
            else {
                throw ToskarError(status: 0, code: .recordSealed, message: "The record doesn't open with this route secret")
            }
            struct Signed: Decodable {
                let payload: Data
                let cert: Data
                let alg: String
                let sig: Data
            }
            struct Body: Decodable {
                let v: Int
                let route: String
                let at: Int64
                let addresses: [String]
            }
            guard let signed = try? JSONDecoder().decode(Signed.self, from: plain) else {
                throw ToskarError(status: 0, code: .recordSealed, message: "The record doesn't open with this route secret")
            }
            let notPinned = ToskarError(status: 0, code: .recordPin, message: "The record isn't from the pinned computer")
            guard pinOf(signed.cert).caseInsensitiveCompare(pin) == .orderedSame,
                verify(signed.sig, of: signed.payload, alg: signed.alg, cert: signed.cert),
                let body = try? JSONDecoder().decode(Body.self, from: signed.payload), body.v == 1, body.route == route
            else {
                throw notPinned
            }
            let at = Date(timeIntervalSince1970: TimeInterval(body.at))
            if now.timeIntervalSince(at) > maxAge || at.timeIntervalSince(now) > 5 * 60 {
                throw ToskarError(status: 0, code: .recordStale, message: "The record is too old")
            }
            return AddressRecord(addresses: body.addresses, at: at)
        }

        static func routeSecret(_ secret: String) throws -> Data {
            var b64 = secret.replacingOccurrences(of: "-", with: "+").replacingOccurrences(of: "_", with: "/")
            b64 += String(repeating: "=", count: (4 - b64.count % 4) % 4)
            guard let s = Data(base64Encoded: b64), s.count == 32 else {
                throw ToskarError(status: 0, code: .init("BAD_ROUTE_SECRET"), message: "A route secret is 32 bytes, base64url")
            }
            return s
        }
    }

    /// RFC 4648 base32 in lower case, without padding, as route IDs are.
    func lowerBase32(_ data: Data) -> String {
        let alphabet = Array("abcdefghijklmnopqrstuvwxyz234567")
        var out = ""
        var buffer = 0
        var bits = 0
        for byte in data {
            buffer = buffer << 8 | Int(byte)
            bits += 8
            while bits >= 5 {
                out.append(alphabet[(buffer >> (bits - 5)) & 31])
                bits -= 5
            }
        }
        if bits > 0 {
            out.append(alphabet[(buffer << (5 - bits)) & 31])
        }
        return out
    }

    /// Whether sig signs payload with the key in cert, by alg: ECDSA P-256
    /// and RSA PKCS #1 v1.5 with SHA-256, and Ed25519.
    func verify(_ sig: Data, of payload: Data, alg: String, cert: Data) -> Bool {
        if alg == "ed25519" {
            guard let raw = ed25519Key(cert), let key = try? Curve25519.Signing.PublicKey(rawRepresentation: raw) else {
                return false
            }
            return key.isValidSignature(sig, for: payload)
        }
        guard let certificate = SecCertificateCreateWithData(nil, cert as CFData),
            let key = SecCertificateCopyKey(certificate),
            let attributes = SecKeyCopyAttributes(key) as? [CFString: Any],
            let type = attributes[kSecAttrKeyType] as? String
        else {
            return false
        }
        let algorithm: SecKeyAlgorithm
        switch alg {
        case "ecdsa-sha256" where type == (kSecAttrKeyTypeECSECPrimeRandom as String):
            algorithm = .ecdsaSignatureMessageX962SHA256
        case "rsa-pkcs1-sha256" where type == (kSecAttrKeyTypeRSA as String):
            algorithm = .rsaSignatureMessagePKCS1v15SHA256
        default:
            return false
        }
        return SecKeyVerifySignature(key, algorithm, payload as CFData, sig as CFData, nil)
    }

    /// The raw Ed25519 public key in a certificate, which Security can't
    /// read: its SubjectPublicKeyInfo always starts with these 12 bytes.
    func ed25519Key(_ cert: Data) -> Data? {
        let prefix = Data([0x30, 0x2A, 0x30, 0x05, 0x06, 0x03, 0x2B, 0x65, 0x70, 0x03, 0x21, 0x00])
        guard let range = cert.range(of: prefix), cert.endIndex - range.upperBound >= 32 else {
            return nil
        }
        return cert[range.upperBound..<range.upperBound + 32]
    }
#endif
