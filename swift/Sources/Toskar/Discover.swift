// Finding computers running Toskar Core on the home network, as the Toskar
// apps do: they advertise _localai._tcp over mDNS, with where their API is
// in the TXT record (Toskar Core's docs/connecting.md).
//
//     let computers = await Toskar.find()
//     let device = try await Toskar.pair(address: computers[0].address, code: code, deviceName: "Kitchen tablet")
//
// On iOS, tvOS, and visionOS, the app's Info.plist needs
// NSLocalNetworkUsageDescription and NSBonjourServices with _localai._tcp.

#if canImport(Network)
    import Foundation
    import Network

    /// A Toskar Core found on the network.
    public struct DiscoveredComputer: Sendable, Hashable {
        public let name: String
        public let nodeID: String
        /// Toskar Core's version.
        public let version: String
        /// The API's host:port, to pair with: the first of `addresses` that
        /// answers.
        public let address: String
        /// Every host:port found for the computer. A computer can have
        /// addresses this device can't reach, such as a container network's.
        public let addresses: [String]
        /// False when the API answers only on that computer: say to turn on
        /// Connect a device there, rather than that it's unreachable.
        public let onNetwork: Bool
    }

    extension Toskar {
        /// What Toskar Core advertises.
        public static let serviceType = "_localai._tcp"

        /// Browses for timeout seconds and returns the computers that
        /// answered, by name.
        public static func find(timeout: TimeInterval = 3) async -> [DiscoveredComputer] {
            let services = await browse(timeout: timeout)
            let found = await withTaskGroup(of: DiscoveredComputer?.self) { group in
                for service in services {
                    group.addTask { await resolve(service) }
                }
                var out: [DiscoveredComputer] = []
                for await c in group {
                    if let c { out.append(c) }
                }
                return out
            }
            var unique: [String: DiscoveredComputer] = [:]
            for c in found {
                unique[c.nodeID + c.address] = c
            }
            return unique.values.sorted { $0.name < $1.name }
        }
    }

    /// A browse result: where the service is, and its TXT record.
    struct Service: Sendable {
        let endpoint: NWEndpoint
        let instance: String
        let txt: [String: String]
    }

    /// The services that answered within timeout.
    func browse(timeout: TimeInterval) async -> [Service] {
        let browser = NWBrowser(for: .bonjourWithTXTRecord(type: Toskar.serviceType, domain: nil), using: .tcp)
        let queue = DispatchQueue(label: "toskar.discover")
        let results = Locked<[NWEndpoint: Service]>([:])
        browser.browseResultsChangedHandler = { all, _ in
            for result in all {
                guard case .service(let name, _, _, _) = result.endpoint else { continue }
                var txt: [String: String] = [:]
                if case .bonjour(let record) = result.metadata {
                    txt = record.dictionary
                }
                results.update { $0[result.endpoint] = Service(endpoint: result.endpoint, instance: name, txt: txt) }
            }
        }
        browser.start(queue: queue)
        try? await Task.sleep(nanoseconds: UInt64(timeout * 1_000_000_000))
        browser.cancel()
        return Array(results.value.values)
    }

    /// A service as a computer: its addresses with the API's port, from the
    /// TXT record. The service's own port is for computers pairing with each
    /// other; the API's is in api_port.
    func resolve(_ service: Service) async -> DiscoveredComputer? {
        guard let port = Int(service.txt["api_port"] ?? ""), port > 0 else { return nil }
        var hosts: [String] = []
        for version in [NWProtocolIP.Options.Version.v4, .v6] {
            if let host = await resolvedHost(service.endpoint, version: version) {
                hosts.append(host)
            }
        }
        let addresses = hosts.map { $0.contains(":") ? "[\($0)]:\(port)" : "\($0):\(port)" }
        return computer(service, addresses: addresses, reachable: await reachable(addresses))
    }

    /// The computer a service and its addresses describe, or nil without an
    /// address.
    func computer(_ service: Service, addresses: [String], reachable: String?) -> DiscoveredComputer? {
        guard let first = addresses.first else { return nil }
        let name = service.txt["name"].flatMap { $0.isEmpty ? nil : $0 } ?? service.instance
        return DiscoveredComputer(
            name: name, nodeID: service.txt["node_id"] ?? "", version: service.txt["version"] ?? "",
            address: reachable ?? first, addresses: addresses, onNetwork: service.txt["api_lan"] != "false")
    }

    /// The host a service resolves to on IP version, found by connecting to
    /// it, or nil within 2 seconds.
    func resolvedHost(_ endpoint: NWEndpoint, version: NWProtocolIP.Options.Version) async -> String? {
        let params = NWParameters.tcp
        (params.defaultProtocolStack.internetProtocol as? NWProtocolIP.Options)?.version = version
        guard let remote = await connected(NWConnection(to: endpoint, using: params), timeout: 2),
            case .hostPort(let host, _) = remote
        else {
            return nil
        }
        // Without the interface Network adds, as in 192.168.1.20%en0: a URL
        // can't carry it.
        func plain(_ text: String) -> String { String(text.split(separator: "%").first ?? "") }
        switch host {
        case .ipv4(let a):
            return plain("\(a)")
        case .ipv6(let a):
            // A link-local address needs its interface, so it's left out.
            return a.isLinkLocal ? nil : plain("\(a)")
        case .name(let n, _):
            return n
        @unknown default:
            return nil
        }
    }

    /// The first of addresses that takes a TCP connection, tried together.
    func reachable(_ addresses: [String]) async -> String? {
        await withTaskGroup(of: String?.self) { group in
            for address in addresses {
                group.addTask {
                    guard let colon = address.lastIndex(of: ":"), let port = NWEndpoint.Port(String(address[address.index(after: colon)...]))
                    else { return nil }
                    let host = address[..<colon].trimmingCharacters(in: CharacterSet(charactersIn: "[]"))
                    let conn = NWConnection(host: NWEndpoint.Host(host), port: port, using: .tcp)
                    return await connected(conn, timeout: 0.7) == nil ? nil : address
                }
            }
            for await a in group {
                if let a {
                    group.cancelAll()
                    return a
                }
            }
            return nil
        }
    }

    /// Where conn connected to, or nil when it didn't within timeout. It's
    /// closed either way.
    func connected(_ conn: NWConnection, timeout: TimeInterval) async -> NWEndpoint? {
        let queue = DispatchQueue(label: "toskar.discover.connect")
        let once = Locked(false)
        return await withCheckedContinuation { (done: CheckedContinuation<NWEndpoint?, Never>) in
            let finish: @Sendable (NWEndpoint?) -> Void = { endpoint in
                guard once.update({ was in defer { was = true }; return !was }) else { return }
                conn.cancel()
                done.resume(returning: endpoint)
            }
            conn.stateUpdateHandler = { state in
                switch state {
                case .ready:
                    finish(conn.currentPath?.remoteEndpoint)
                case .failed, .cancelled:
                    finish(nil)
                case .waiting:
                    finish(nil)
                default:
                    break
                }
            }
            conn.start(queue: queue)
            queue.asyncAfter(deadline: .now() + timeout) { finish(nil) }
        }
    }

    /// A value behind a lock.
    final class Locked<Value>: @unchecked Sendable {
        private let lock = NSLock()
        private var stored: Value
        init(_ value: Value) { stored = value }
        var value: Value { lock.withLock { stored } }
        @discardableResult
        func update<T>(_ change: (inout Value) -> T) -> T { lock.withLock { change(&stored) } }
    }
#endif
