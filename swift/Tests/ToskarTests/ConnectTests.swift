#if canImport(CryptoKit) && canImport(Security)
    import Foundation
    import Testing

    @testable import Toskar

    /// spec/connection-vectors.json, which Toskar Core's reference code
    /// keeps true, so every SDK opens records as Core writes them.
    struct Vectors: Decodable {
        struct RouteCase: Decodable {
            let secret: String
            let route_id: String
        }
        struct PinCase: Decodable {
            let cert_der_base64: String
            let fingerprint: String
            let short: String
        }
        struct RecordCase: Decodable {
            let name: String
            let blob_base64: String
            let secret: String
            let pin: String
            let now: Int64
            let max_age_seconds: Int64
            let addresses: [String]?
            let at: Int64?
            let error: String?
        }
        let routes: [RouteCase]
        let pins: [PinCase]
        let records: [RecordCase]

        static func load() throws -> Vectors {
            let url = URL(fileURLWithPath: #filePath)
                .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
                .deletingLastPathComponent().appendingPathComponent("spec/connection-vectors.json")
            return try JSONDecoder().decode(Vectors.self, from: Data(contentsOf: url))
        }
    }

    @Test func routeIDsAreCores() throws {
        for r in try Vectors.load().routes {
            #expect(try Toskar.routeID(r.secret) == r.route_id)
        }
        #expect(throws: ToskarError.self) { try Toskar.routeID("too-short") }
    }

    @Test func pinsAreCores() throws {
        let pins = try Vectors.load().pins
        #expect(pins.count == 3)
        for p in pins {
            let der = try #require(Data(base64Encoded: p.cert_der_base64))
            #expect(Toskar.pinOf(der) == p.fingerprint)
            #expect(Toskar.shortPin(p.fingerprint) == p.short)
        }
    }

    @Test(arguments: try Vectors.load().records)
    func recordsOpenAsCoreSays(_ r: Vectors.RecordCase) throws {
        let blob = try #require(Data(base64Encoded: r.blob_base64))
        let open = {
            try Toskar.openRecord(
                blob, secret: r.secret, pin: r.pin, now: Date(timeIntervalSince1970: TimeInterval(r.now)),
                maxAge: TimeInterval(r.max_age_seconds))
        }
        if let want = r.error {
            let code = ["sealed": ToskarError.Code.recordSealed, "pin": .recordPin, "stale": .recordStale][want]
            #expect(throws: ToskarError.self, "\(r.name)") {
                do { _ = try open() } catch let e as ToskarError {
                    #expect(e.code == code, "\(r.name)")
                    throw e
                }
            }
        } else {
            let record = try open()
            #expect(record.addresses == r.addresses, "\(r.name)")
            #expect(Int64(record.at.timeIntervalSince1970) == r.at, "\(r.name)")
        }
    }

    extension Vectors.RecordCase: CustomTestStringConvertible {
        var testDescription: String { name }
    }

    @Test func savedDevicesAreTheOtherSDKsJSON() throws {
        let json = #"{"address":"192.168.1.20:7331","api_key":"tk_1","pin":"sha256:ab","route":{"secret":"s","id":"i","relay":"relay.toskar.ai","token":"t"}}"#
        let device = try JSONDecoder().decode(Device.self, from: Data(json.utf8))
        #expect(device.apiKey == "tk_1")
        #expect(device.route?.token == "t")
        let again = try JSONSerialization.jsonObject(with: JSONEncoder().encode(device)) as? [String: Any]
        #expect(again?["api_key"] as? String == "tk_1")
    }

    @Test func hostsOfAddresses() {
        #expect(hostOnly("studio.local:7331") == "studio.local")
        #expect(hostOnly("[fe80::1]:7331") == "fe80::1")
        #expect(hostOnly("fe80::1") == "fe80::1")
        #expect(hostOnly("relay.toskar.ai") == "relay.toskar.ai")
    }
#endif
