#if canImport(Network)
    import Network
    import Testing

    @testable import Toskar

    let rig = NWEndpoint.service(name: "linux-rig", type: "_localai._tcp", domain: "local.", interface: nil)

    @Test func aComputerIsItsTXTRecord() throws {
        let service = Service(
            endpoint: rig, instance: "linux-rig",
            txt: ["node_id": "n1", "name": "Rig", "version": "1.12.0", "api_port": "7331", "api_lan": "true"])
        let c = try #require(computer(service, addresses: ["10.42.0.1:7331", "192.168.1.20:7331"], reachable: "192.168.1.20:7331"))
        #expect(c.name == "Rig")
        #expect(c.nodeID == "n1")
        #expect(c.version == "1.12.0")
        // The address that answered, not the first found.
        #expect(c.address == "192.168.1.20:7331")
        #expect(c.addresses.count == 2)
        #expect(c.onNetwork)
    }

    @Test func aComputerOnlyOnItselfSaysSo() throws {
        let service = Service(endpoint: rig, instance: "linux-rig", txt: ["api_port": "7331", "api_lan": "false"])
        let c = try #require(computer(service, addresses: ["192.168.1.20:7331"], reachable: nil))
        #expect(c.name == "linux-rig") // the instance, with no name in the record
        #expect(c.address == "192.168.1.20:7331") // the first, when none answered
        #expect(!c.onNetwork)
    }

    @Test func aServiceWithoutAnAPIPortIsntAComputer() async {
        #expect(await resolve(Service(endpoint: rig, instance: "x", txt: ["name": "x"])) == nil)
        #expect(computer(Service(endpoint: rig, instance: "x", txt: ["api_port": "7331"]), addresses: [], reachable: nil) == nil)
    }
#endif
