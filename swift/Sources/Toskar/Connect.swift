// Connecting as a paired device, as the Toskar apps do (Toskar Core's
// docs/connecting.md): pairing with the code Connect a device shows, the
// computer's certificate pinned on every connection, and reaching it at
// home or, with access from anywhere, directly or through its relay. It
// needs Apple's Security framework, so it's on Apple's platforms.

#if canImport(CryptoKit) && canImport(Security)
    import CryptoKit
    import Foundation
    import HTTPTypes
    import OpenAPIRuntime
    import OpenAPIURLSession
    import Security

    /// What a paired device keeps, to connect again. Save it as a password
    /// is saved, such as in the Keychain: `apiKey` and the route's secret
    /// and token are secrets. It's Codable, as the other SDKs' JSON.
    public struct Device: Codable, Sendable, Hashable {
        /// The computer's host:port at home.
        public var address: String
        public var apiKey: String
        /// "sha256:<hex>" of the computer's certificate. It only ever comes
        /// from pairing.
        public var pin: String
        /// How to find the computer away from home, when it has access from
        /// anywhere.
        public var route: Route?

        public init(address: String, apiKey: String, pin: String, route: Route? = nil) {
            self.address = address
            self.apiKey = apiKey
            self.pin = pin
            self.route = route
        }

        enum CodingKeys: String, CodingKey {
            case address
            case apiKey = "api_key"
            case pin, route
        }
    }

    /// How to find a computer away from home.
    public struct Route: Codable, Sendable, Hashable {
        /// The route secret, base64url without padding.
        public var secret: String
        public var id: String
        /// The relay the computer uses, such as relay.toskar.ai.
        public var relay: String
        /// Lets the device look the computer up on Toskar's relay.
        public var token: String?

        public init(secret: String, id: String, relay: String, token: String? = nil) {
            self.secret = secret
            self.id = id
            self.relay = relay
            self.token = token
        }
    }

    /// How the client reaches its computer.
    public enum ConnectionPath: String, Sendable {
        case home, direct, relay
    }

    extension Toskar {
        /// Toskar's own relay. It's asked only with a route token.
        public static let toskarRelay = "relay.toskar.ai"

        /// The pin of a certificate: "sha256:<hex>" of its DER.
        public static func pinOf(_ der: Data) -> String {
            "sha256:" + SHA256.hash(data: der).map { String(format: "%02x", $0) }.joined()
        }

        /// How a pin is shown for the person to compare: its first 8 hex
        /// digits, as ABCD-1234.
        public static func shortPin(_ pin: String) -> String {
            let hex = String(pin.dropFirst(pin.hasPrefix("sha256:") ? 7 : 0)).uppercased()
            guard hex.count >= 8 else { return hex }
            return "\(hex.prefix(4))-\(hex.dropFirst(4).prefix(4))"
        }

        /// Pairs with the computer at address (host:port, as found or typed)
        /// using the code Connect a device shows on it. The device must be on
        /// the computer's local network.
        ///
        /// - Parameter confirm: Shows the person the short pin, such as
        ///   9B80-D9D9, and says whether the computer shows the same. Nil
        ///   skips the check, as a script with no one to ask does.
        public static func pair(
            address: String, code: String, deviceName: String,
            confirm: (@Sendable (String) async -> Bool)? = nil
        ) async throws -> Device {
            guard let base = URL(string: "https://\(address)") else {
                throw ToskarError(status: 0, code: .init("BAD_ADDRESS"), message: "\(address) isn't host:port")
            }
            // The certificate the computer shows, for the person to check.
            let seeing = Pinning(pin: nil)
            let look = URLSession(configuration: .ephemeral, delegate: seeing, delegateQueue: nil)
            defer { look.invalidateAndCancel() }
            var probe = URLRequest(url: base.appendingPathComponent("api/v1/health"))
            probe.timeoutInterval = 30
            _ = try await look.data(for: probe)
            guard let seen = seeing.seen else {
                throw ToskarError(status: 0, code: .pinMismatch, message: "The computer showed no certificate")
            }
            if let confirm, await !confirm(shortPin(seen)) {
                throw ToskarError(status: 0, code: .notConfirmed, message: "The short pin wasn't confirmed")
            }

            // Then the code, to that certificate alone.
            let pinning = Pinning(pin: seen)
            let pinned = URLSession(configuration: .ephemeral, delegate: pinning, delegateQueue: nil)
            defer { pinned.invalidateAndCancel() }
            var request = URLRequest(url: base.appendingPathComponent("api/v1/devices/pair"))
            request.httpMethod = "POST"
            request.timeoutInterval = 30
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.setValue(contractVersion, forHTTPHeaderField: "Toskar-Client-Contract")
            request.httpBody = try JSONEncoder().encode(["code": code, "device_name": deviceName])
            let (data, response) = try await pinnedCall(pinning, host: address) { try await pinned.data(for: request) }
            let status = (response as? HTTPURLResponse)?.statusCode ?? 0
            guard status < 300 else { throw ToskarError(status: status, body: data) }
            let paired = try decoder.decode(Components.Schemas.PairedDevice.self, from: data)
            guard paired.tlsFingerprint.caseInsensitiveCompare(seen) == .orderedSame else {
                throw ToskarError(status: 0, code: .pinMismatch, message: "The computer's certificate isn't the one paired with")
            }
            var device = Device(address: address, apiKey: paired.apiKey, pin: seen)
            if let secret = paired.routeSecret, !secret.isEmpty {
                device.route = Route(secret: secret, id: paired.routeId ?? "", relay: paired.relay ?? "", token: paired.token)
            }
            return device
        }

        /// Connects as a paired device: every connection pinned to its
        /// computer's certificate, at home when it answers, and otherwise
        /// directly or through its relay, from its address record.
        public convenience init(device: Device, retries: Int = 2, timeout: TimeInterval = 60) throws {
            let config = URLSessionConfiguration.ephemeral
            config.timeoutIntervalForRequest = timeout > 0 ? timeout : .infinity
            config.timeoutIntervalForResource = .infinity
            let pinning = Pinning(pin: device.pin)
            let session = URLSession(configuration: config, delegate: pinning, delegateQueue: nil)
            let router = Router(device: device, session: session, pinning: pinning)
            try self.init(
                url: URL(string: "https://\(device.address)"), key: device.apiKey, retries: retries,
                transport: URLSessionTransport(configuration: .init(session: session)), routing: Routing(router: router))
        }

        /// How the client reaches its paired computer now, or nil before its
        /// first request, or for a client that isn't a paired device.
        public var path: ConnectionPath? {
            get async { await router?.path }
        }

        /// Chooses the way in again, as after the network changed, and says
        /// which it found.
        @discardableResult
        public func reconnect() async throws -> ConnectionPath? {
            guard let router else { return nil }
            await router.forget()
            _ = try await router.current()
            return await router.path
        }
    }

    /// Trusts exactly the certificate with pin, checked before any request
    /// is sent; names, dates, and signers aren't checked. With no pin, it
    /// trusts any certificate and keeps its pin in seen, for pairing.
    final class Pinning: NSObject, URLSessionDelegate, @unchecked Sendable {
        let pin: String?
        private let lock = NSLock()
        private var seenPin: String?
        private var mismatches: Set<String> = []

        init(pin: String?) { self.pin = pin }

        var seen: String? { lock.withLock { seenPin } }

        /// Whether host just showed another certificate; asking clears it.
        func mismatched(_ host: String) -> Bool {
            lock.withLock { mismatches.remove(host.lowercased()) != nil }
        }

        func urlSession(
            _ session: URLSession, didReceive challenge: URLAuthenticationChallenge,
            completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void
        ) {
            guard challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
                let trust = challenge.protectionSpace.serverTrust,
                let leaf = (SecTrustCopyCertificateChain(trust) as? [SecCertificate])?.first
            else {
                completionHandler(.performDefaultHandling, nil)
                return
            }
            let got = Toskar.pinOf(SecCertificateCopyData(leaf) as Data)
            guard let pin else {
                lock.withLock { seenPin = got }
                completionHandler(.useCredential, URLCredential(trust: trust))
                return
            }
            if got.caseInsensitiveCompare(pin) == .orderedSame {
                completionHandler(.useCredential, URLCredential(trust: trust))
            } else {
                _ = lock.withLock { mismatches.insert(challenge.protectionSpace.host.lowercased()) }
                completionHandler(.cancelAuthenticationChallenge, nil)
            }
        }
    }

    /// A call over a pinned session to host, with a refused certificate
    /// thrown as `.pinMismatch`.
    func pinnedCall<T>(_ pinning: Pinning, host: String, _ call: () async throws -> T) async throws -> T {
        do {
            return try await call()
        } catch {
            if pinning.mismatched(hostOnly(host)) {
                throw ToskarError(status: 0, code: .pinMismatch, message: "The computer's certificate isn't the one paired with")
            }
            throw error
        }
    }

    /// Sends each request to the way in in use, choosing it again when it
    /// stops answering: home first, then the address record's ways, the
    /// direct ones at once and the relay's a second later.
    actor Router {
        static let homeTimeout: TimeInterval = 2.5
        static let tryTimeout: TimeInterval = 6
        static let relayDelay: UInt64 = 1_000_000_000
        static let recordMaxAge: TimeInterval = 3600

        let device: Device
        let session: URLSession
        let pinning: Pinning
        /// Fetches address records from the relay, over its own certificate,
        /// checked as any website's is.
        let relaySession: URLSession
        private(set) var path: ConnectionPath?
        private var way: String?

        init(device: Device, session: URLSession, pinning: Pinning, relaySession: URLSession = .shared) {
            self.device = device
            self.session = session
            self.pinning = pinning
            self.relaySession = relaySession
        }

        func forget() {
            way = nil
            path = nil
        }

        func forget(_ used: String) {
            if way == used {
                forget()
            }
        }

        func current() async throws -> String {
            if let way {
                return way
            }
            let (found, at) = try await choose()
            way = at
            path = found
            return at
        }

        /// Whether the computer answers health at address, pinned, within
        /// timeout. Another certificate throws `.pinMismatch`.
        nonisolated func answers(_ address: String, timeout: TimeInterval) async throws -> Bool {
            guard let url = URL(string: "https://\(address)/api/v1/health") else { return false }
            var request = URLRequest(url: url)
            request.timeoutInterval = timeout
            // With the key: a computer that asks for one answers health only
            // with it. The connection is pinned before anything is sent.
            request.setValue("Bearer \(device.apiKey)", forHTTPHeaderField: "Authorization")
            do {
                let (data, response) = try await pinnedCall(pinning, host: address) { try await session.data(for: request) }
                struct Health: Decodable { let status: String }
                return (response as? HTTPURLResponse)?.statusCode == 200
                    && (try? JSONDecoder().decode(Health.self, from: data))?.status == "ok"
            } catch let error where error.toskar?.code == .pinMismatch {
                throw error
            } catch {
                return false
            }
        }

        private func choose() async throws -> (ConnectionPath, String) {
            // Home answering with another certificate means the computer's
            // changed, or it isn't the computer: say so; pairing again is the
            // way on.
            if try await answers(device.address, timeout: Self.homeTimeout) {
                return (.home, device.address)
            }
            guard let route = device.route, !route.secret.isEmpty else { throw Self.unreachable }
            let relay = hostOnly(route.relay).lowercased()
            // Toskar's relay answers only for a subscription; without one, it
            // isn't asked, so nothing about this device reaches it.
            if relay == Toskar.toskarRelay && (route.token ?? "").isEmpty {
                throw Self.unreachable
            }
            let record = try await self.record(route)
            return try await withThrowingTaskGroup(of: (ConnectionPath, String)?.self) { group in
                for address in record.addresses {
                    let isRelay = hostOnly(address).lowercased().hasSuffix("." + relay)
                    group.addTask {
                        if isRelay {
                            try await Task.sleep(nanoseconds: Self.relayDelay)
                        }
                        // Another certificate at a way in is someone else's
                        // device there: that way just doesn't count.
                        let ok = (try? await self.answers(address, timeout: Self.tryTimeout)) ?? false
                        return ok ? (isRelay ? .relay : .direct, address) : nil
                    }
                }
                for try await found in group {
                    if let found {
                        group.cancelAll()
                        return found
                    }
                }
                throw Self.unreachable
            }
        }

        private func record(_ route: Route) async throws -> AddressRecord {
            guard let url = URL(string: "https://\(route.relay)/v1/routes/\(route.id)/record") else {
                throw Self.noRecord
            }
            var request = URLRequest(url: url)
            request.timeoutInterval = Self.tryTimeout
            if let token = route.token, !token.isEmpty {
                request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            }
            let data: Data
            do {
                let (body, response) = try await relaySession.data(for: request)
                guard (response as? HTTPURLResponse)?.statusCode == 200, body.count <= 1 << 20 else { throw Self.noRecord }
                data = body
            } catch {
                throw Self.noRecord
            }
            return try Toskar.openRecord(data, secret: route.secret, pin: device.pin, maxAge: Self.recordMaxAge)
        }

        static let unreachable = ToskarError(status: 0, code: .unreachable, message: "The computer can't be reached")
        static let noRecord = ToskarError(
            status: 0, code: .noRecord,
            message: "No address record for the computer: it may be off or asleep, or have no access from anywhere")
    }

    /// Points each request at the way in the router chose, and has it choose
    /// again when that way stops answering.
    struct Routing: ClientMiddleware {
        let router: Router

        func intercept(
            _ request: HTTPRequest, body: HTTPBody?, baseURL: URL, operationID: String,
            next: @Sendable (HTTPRequest, HTTPBody?, URL) async throws -> (HTTPResponse, HTTPBody?)
        ) async throws -> (HTTPResponse, HTTPBody?) {
            let way = try await router.current()
            guard let url = URL(string: "https://\(way)") else { throw Router.unreachable }
            do {
                return try await pinnedCall(router.pinning, host: way) { try await next(request, body, url) }
            } catch let error where error.toskar?.code != .pinMismatch {
                // Choose again for the next request; a safe one is retried.
                await router.forget(way)
                throw error
            }
        }
    }

    func hostOnly(_ address: String) -> String {
        if address.hasPrefix("["), let end = address.firstIndex(of: "]") {
            return String(address[address.index(after: address.startIndex)..<end])
        }
        if address.filter({ $0 == ":" }).count == 1, let colon = address.lastIndex(of: ":") {
            return String(address[..<colon])
        }
        return address
    }
#endif
