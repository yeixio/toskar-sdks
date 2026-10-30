// Runs the shared conformance cases (conformance/README.md) with the Swift
// SDK. It prints one line of JSON and exits 0, or prints
// {"error": {"code", "message"}} and exits 1.
import CryptoKit
import Foundation
import Toskar

func run(_ args: [String]) async throws -> [String: Any] {
    switch (args.first, args.count) {
    case ("pair", 3):
        let short = Box()
        let device = try await Toskar.pair(address: args[1], code: args[2], deviceName: "Swift conformance") {
            short.value = $0
            return true
        }
        let saved = try JSONSerialization.jsonObject(with: JSONEncoder().encode(device))
        return ["device": saved, "short_pin": short.value]
    case ("call", 2):
        let device = try JSONDecoder().decode(Device.self, from: Data(contentsOf: URL(fileURLWithPath: args[1])))
        let toskar = try Toskar(device: device, retries: 0)
        let settings = try await toskar.api.getSettings().ok.body.json
        return [
            "path": await toskar.path?.rawValue ?? "",
            "node_name": settings.additionalProperties.value["node_name"] as? String ?? "",
        ]
    default:
        break
    }
    // The rest connect as TOSKAR_URL and TOSKAR_API_KEY say.
    let toskar = try Toskar(retries: 0)
    switch (args.first, args.count) {
    case ("chat", 3):
        let answer = try await toskar.chat(ChatRequest(message: args[2], modelId: args[1]))
        return ["content": answer.content]
    case ("stream", 3):
        var content = ""
        var tokens = 0
        var done = false
        for try await event in toskar.chatStream(ChatRequest(message: args[2], modelId: args[1])) {
            switch event {
            case .token(let t):
                tokens += 1
                content += t
            case .done:
                done = true
            }
        }
        return ["content": content, "tokens": tokens, "done": done]
    case ("events", 4):
        return try await events(toskar, model: args[1], message: args[2], until: args[3])
    case ("upload", 2):
        let url = URL(fileURLWithPath: args[1])
        let raw = try Data(contentsOf: url)
        let file = try await toskar.api.uploadArtifact(
            body: .json(.init(name: url.lastPathComponent, contentBase64: raw.base64EncodedString()))
        ).ok.body.json
        return ["id": file.id, "name": file.name, "size_bytes": file.sizeBytes]
    case ("download", 2):
        let body = try await toskar.api.getArtifactContent(path: .init(id: args[1])).ok.body.any
        let data = try await Data(collecting: body, upTo: 1 << 30)
        let sum = SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
        return ["sha256": sum, "size_bytes": data.count]
    default:
        throw ToskarError(
            status: 0, code: .init("ERROR"),
            message: "usage: toskar-conformance pair <address> <code> | call <device.json> | chat|stream <model> <message> | events <model> <message> <until> | upload <file> | download <id>")
    }
}

/// Listens to the events stream, asks once, and lists the events' types
/// until one of type until.
func events(_ toskar: Toskar, model: String, message: String, until: String) async throws -> [String: Any] {
    let listening = Task { () -> [String] in
        var types: [String] = []
        for try await event in toskar.events() {
            types.append(event._type)
            if event._type == until {
                return types
            }
        }
        return types
    }
    // Time to subscribe before asking.
    try await Task.sleep(nanoseconds: 1_000_000_000)
    _ = try await toskar.chat(ChatRequest(message: message, modelId: model))
    let timeout = Task {
        try await Task.sleep(nanoseconds: 30_000_000_000)
        listening.cancel()
    }
    defer { timeout.cancel() }
    return ["types": try await listening.value]
}

final class Box: @unchecked Sendable {
    var value = ""
}

do {
    let out = try await run(Array(CommandLine.arguments.dropFirst()))
    print(String(data: try JSONSerialization.data(withJSONObject: out), encoding: .utf8)!)
} catch {
    let code = error.toskar?.code.rawValue ?? "ERROR"
    let message = error.toskar?.message ?? "\(error)"
    let out = ["error": ["code": code, "message": message]]
    print(String(data: try JSONSerialization.data(withJSONObject: out), encoding: .utf8)!)
    exit(1)
}
