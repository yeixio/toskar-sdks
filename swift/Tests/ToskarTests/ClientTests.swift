import Foundation
import HTTPTypes
import OpenAPIRuntime
import Testing

@testable import Toskar

/// A scripted Toskar Core: answers each request with the next reply, and
/// keeps the requests.
final class FakeCore: ClientTransport, @unchecked Sendable {
    struct Reply {
        var status = 200
        var contentType = "application/json"
        var body = ""
        var fails = false
    }

    private let lock = NSLock()
    private var replies: [Reply]
    private(set) var requests: [HTTPRequest] = []

    init(_ replies: [Reply]) { self.replies = replies }

    var sent: [HTTPRequest] { lock.withLock { requests } }

    func send(_ request: HTTPRequest, body: HTTPBody?, baseURL: URL, operationID: String) async throws -> (HTTPResponse, HTTPBody?) {
        let reply = lock.withLock {
            requests.append(request)
            return replies.isEmpty ? Reply(status: 500) : replies.removeFirst()
        }
        if reply.fails {
            throw URLError(.cannotConnectToHost)
        }
        var response = HTTPResponse(status: .init(code: reply.status))
        response.headerFields[.contentType] = reply.contentType
        return (response, HTTPBody(reply.body))
    }
}

func toskar(_ core: FakeCore, retries: Int = 2, key: String? = nil) throws -> Toskar {
    try Toskar(url: URL(string: "http://core.test:7331")!, key: key, retries: retries, transport: core)
}

let sse = "text/event-stream"

@Test func saysItsContractAndSendsTheKey() async throws {
    let core = FakeCore([.init(body: #"{"version":"1.12.0","contract":{"version":"1.60","major":1},"commit":"abc","build_date":"2026-10-29","license":"AGPL-3.0","product":"Toskar","source":"https://github.com/yeixio/toskar-core"}"#)])
    _ = try await toskar(core, key: "secret").version()
    let r = try #require(core.sent.first)
    #expect(r.headerFields[HTTPField.Name("Toskar-Client-Contract")!] == contractVersion)
    #expect(r.headerFields[.authorization] == "Bearer secret")
}

@Test func chatsWaitingForTheWholeAnswer() async throws {
    let core = FakeCore([.init(body: #"{"content":"Hello there","metrics":null}"#)])
    let answer = try await toskar(core).chat(ChatRequest(message: "Hi"))
    #expect(answer.content == "Hello there")
    #expect(core.sent.first?.headerFields[.accept] == "application/json")
}

@Test func streamsAnAnswerAsItIsWritten() async throws {
    let body = """
        : ping

        event: token
        data: {"content":"Hel"}

        event: token
        data: {"content":"lo"}

        event: done
        data: {"metrics":{"prompt_tokens":3,"completion_tokens":2,"total_tokens":5,"ttft_ms":1,"prompt_ms":1,"eval_ms":1,"total_ms":2,"prompt_tok_per_sec":3,"eval_tok_per_sec":2}}


        """
    let core = FakeCore([.init(contentType: sse, body: body)])
    var text = ""
    var metrics: Components.Schemas.GenerationMetrics?
    for try await event in try toskar(core).chatStream(ChatRequest(message: "Hi")) {
        switch event {
        case .token(let t): text += t
        case .done(let m): metrics = m
        }
    }
    #expect(text == "Hello")
    #expect(metrics?.completionTokens == 2)
    #expect(core.sent.first?.headerFields[.accept] == sse)
}

@Test func aStreamedFailureHasItsCode() async throws {
    let body = "event: error_code\ndata: {\"code\":\"NO_MODEL_INSTALLED\",\"message\":\"Install a model\"}\n\n"
    let core = FakeCore([.init(contentType: sse, body: body)])
    await #expect {
        for try await _ in try toskar(core).chatStream(ChatRequest(message: "Hi")) {}
    } throws: { ($0 as? ToskarError)?.code == .noModelInstalled }
}

@Test func aCutOffStreamSaysSo() async throws {
    let core = FakeCore([.init(contentType: sse, body: "event: token\ndata: {\"content\":\"Hel\"}\n\n")])
    await #expect {
        for try await _ in try toskar(core).chatStream(ChatRequest(message: "Hi")) {}
    } throws: { ($0 as? ToskarError)?.code.rawValue == "CONNECTION_LOST" }
}

@Test func anErrorAnswerIsAToskarError() async throws {
    let core = FakeCore([.init(status: 404, body: #"{"error":{"code":"MODEL_NOT_FOUND","message":"No such model","details":{"model_id":"x"}}}"#)])
    do {
        _ = try await toskar(core).api.listModels()
        Issue.record("no error")
    } catch {
        let e = try #require(error.toskar)
        #expect(e.status == 404)
        #expect(e.code == .modelNotFound)
        #expect(e.message == "No such model")
        #expect(e.details?.value["model_id"] as? String == "x")
    }
    // A body that isn't Toskar's still says what happened.
    let other = FakeCore([.init(status: 500, contentType: "text/plain", body: "oops")])
    await #expect { _ = try await toskar(other).version() } throws: { $0.toskar?.code.rawValue == "HTTP_500" }
}

@Test func retriesASafeRequestButNeverAChat() async throws {
    let version = #"{"version":"1.12.0","contract":{"version":"1.60","major":1},"commit":"abc","build_date":"2026-10-29","license":"AGPL-3.0","product":"Toskar","source":"https://github.com/yeixio/toskar-core"}"#
    let core = FakeCore([.init(fails: true), .init(status: 503), .init(body: version)])
    _ = try await toskar(core).version()
    #expect(core.sent.count == 3)

    let busy = FakeCore([.init(status: 503), .init(status: 503), .init(status: 503), .init(body: version)])
    await #expect { _ = try await toskar(busy).version() } throws: { $0.toskar?.status == 503 }
    #expect(busy.sent.count == 3)

    let chat = FakeCore([.init(status: 503), .init(body: #"{"content":"twice"}"#)])
    await #expect { _ = try await toskar(chat).chat(ChatRequest(message: "Hi")) } throws: { $0.toskar?.status == 503 }
    #expect(chat.sent.count == 1)
}

@Test func readsTheEventsStream() async throws {
    let body = """
        data: {"id":"e1","type":"model.loaded","contract":"1.60","timestamp":"2026-10-29T16:04:05.123456789Z","payload":{"model_id":"m1"}}

        data: {"id":"e2","type":"model.unloaded","contract":"1.60","timestamp":"2026-10-29T16:04:06Z","payload":{}}


        """
    let core = FakeCore([.init(contentType: sse, body: body)])
    var seen: [Components.Schemas.Event] = []
    for try await e in try toskar(core).events() {
        seen.append(e)
    }
    #expect(seen.map(\._type) == ["model.loaded", "model.unloaded"])
    let first = try #require(seen.first?.timestamp.timeIntervalSince1970)
    #expect(abs(first - 1_793_289_845.123) < 0.001)
}

@Test func readsCoreTimes() throws {
    let d = CoreDates()
    #expect(try d.decode("2026-10-29T16:04:05Z").timeIntervalSince1970 == 1_793_289_845)
    #expect(abs(try d.decode("2026-10-29T16:04:05.5-08:00").timeIntervalSince1970 - 1_793_318_645.5) < 0.001)
    #expect(throws: DecodingError.self) { try d.decode("yesterday") }
}
