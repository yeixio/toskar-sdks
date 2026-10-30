// The Swift SDK for Toskar: local AI across your own computers.
//
//     let toskar = try Toskar()
//     for try await event in toskar.chatStream(ChatRequest(message: "Hi")) {
//         if case .token(let text) = event { print(text, terminator: "") }
//     }
//
// `api` reaches every route, typed from Toskar Core's API spec:
//
//     let models = try await toskar.api.listModels().ok.body.json

import Foundation
import HTTPTypes
import OpenAPIRuntime
import OpenAPIURLSession
@_exported import ToskarAPI

#if canImport(FoundationNetworking)
    import FoundationNetworking
#endif

/// A chat message to send: what `chat` and `chatStream` take.
public typealias ChatRequest = Operations.Chat.Input.Body.JsonPayload

/// A connection to Toskar Core.
public final class Toskar: Sendable {
    /// This computer's Toskar Core, which needs no key.
    public static let defaultURL = URL(string: "http://127.0.0.1:7331")!

    /// Every route, typed from Toskar Core's API spec. An error answer
    /// throws, and `error.toskar` is its `ToskarError`.
    public let api: Client
    /// Where Toskar Core answers.
    public let url: URL

    /// Connects to Toskar Core.
    ///
    /// - Parameters:
    ///   - url: Where Toskar Core answers. Default: `TOSKAR_URL`, or
    ///     `Toskar.defaultURL`, this computer.
    ///   - key: The API key for any address other than this computer's
    ///     loopback. Default: `TOSKAR_API_KEY`.
    ///   - retries: How many times a safe request (GET, HEAD, OPTIONS) that
    ///     fails to connect or answers 502, 503, or 504 is retried. A chat
    ///     is never retried: it could answer twice.
    ///   - timeout: How long to wait for an answer to start. A streamed
    ///     answer then runs for as long as it takes.
    ///   - session: The URLSession to send requests with, in place of one
    ///     made with `timeout`.
    ///   - transport: What sends requests, in place of URLSession, such as
    ///     AsyncHTTPClientTransport on Linux, where URLSession doesn't
    ///     stream answers.
    ///   - headers: Headers to add to every request.
    public init(
        url: URL? = nil,
        key: String? = nil,
        retries: Int = 2,
        timeout: TimeInterval = 60,
        session: URLSession? = nil,
        transport: (any ClientTransport)? = nil,
        headers: [String: String] = [:]
    ) throws {
        let env = ProcessInfo.processInfo.environment
        var base = url ?? env["TOSKAR_URL"].flatMap { $0.isEmpty ? nil : URL(string: $0) } ?? Self.defaultURL
        if base.absoluteString.hasSuffix("/") {
            base = URL(string: String(base.absoluteString.dropLast()))!
        }
        self.url = base

        var sent: [HTTPField] = []
        for (name, value) in headers.sorted(by: { $0.key < $1.key }) {
            guard let field = HTTPField.Name(name) else { throw ToskarError.badHeader(name) }
            sent.append(HTTPField(name: field, value: value))
        }
        // Core answers 426 CONTRACT_MISMATCH to a client of another major version.
        sent.append(HTTPField(name: .toskarClientContract, value: contractVersion))
        if let key = key ?? env["TOSKAR_API_KEY"], !key.isEmpty {
            sent.append(HTTPField(name: .authorization, value: "Bearer \(key)"))
        }

        let sender: any ClientTransport
        if let transport {
            sender = transport
        } else if let session {
            sender = URLSessionTransport(configuration: .init(session: session))
        } else {
            let config = URLSessionConfiguration.default
            config.timeoutIntervalForRequest = timeout > 0 ? timeout : .infinity
            config.timeoutIntervalForResource = .infinity
            sender = URLSessionTransport(configuration: .init(session: URLSession(configuration: config)))
        }
        api = Client(
            serverURL: base,
            configuration: Configuration(dateTranscoder: CoreDates()),
            transport: sender,
            middlewares: [
                Headers(fields: sent),
                // Outside the retries, so they see Core's 502, 503, and 504.
                Errors(),
                Retrying(retries: max(0, retries)),
            ]
        )
    }

    /// Asks once and waits for the whole answer.
    public func chat(_ request: ChatRequest) async throws -> Components.Schemas.ChatAnswer {
        var request = request
        request.stream = false
        return try await api.chat(headers: .init(accept: [.init(contentType: .json)]), body: .json(request)).ok.body.json
    }

    /// One event of a streamed chat.
    public enum ChatEvent: Sendable, Hashable {
        /// The next piece of the answer.
        case token(String)
        /// The answer is finished and saved, with what the runtime
        /// measured when it reported it.
        case done(Components.Schemas.GenerationMetrics?)
    }

    /// Asks and yields the answer as it's written: tokens, then done. A
    /// failure throws a `ToskarError` with its code, such as
    /// `.noModelInstalled`, and ends the stream.
    public func chatStream(_ request: ChatRequest) -> AsyncThrowingStream<ChatEvent, Error> {
        var request = request
        request.stream = true
        return AsyncThrowingStream { continuation in
            let task = Task {
                do {
                    let body = try await api.chat(
                        headers: .init(accept: [.init(contentType: .textEventStream)]), body: .json(request)
                    ).ok.body.textEventStream
                    let decoder = Self.decoder
                    for try await event in body.asDecodedServerSentEvents() {
                        let data = Data((event.data ?? "").utf8)
                        switch event.event {
                        case "token":
                            continuation.yield(.token(try decoder.decode(Components.Schemas.ChatToken.self, from: data).content))
                        case "done":
                            let done = try? decoder.decode(Components.Schemas.ChatDone.self, from: data)
                            continuation.yield(.done(done?.metrics))
                            continuation.finish()
                            return
                        case "error_code":
                            throw ToskarError(status: 200, body: data)
                        case "error":
                            throw ToskarError(status: 200, code: .chatFailed, message: event.data ?? "The chat failed")
                        default:
                            continue
                        }
                    }
                    // Every stream ends with done or an error, so one that just stops was cut off.
                    throw ToskarError(status: 200, code: ToskarError.Code("CONNECTION_LOST"), message: "The answer stopped before it finished")
                } catch {
                    continuation.finish(throwing: (error.toskar as Error?) ?? error)
                }
            }
            continuation.onTermination = { _ in task.cancel() }
        }
    }

    /// Yields what happens on Toskar as it happens, such as models loading
    /// and automations running, until you stop.
    public func events() -> AsyncThrowingStream<Components.Schemas.Event, Error> {
        AsyncThrowingStream { continuation in
            let task = Task {
                do {
                    let body = try await api.eventStream().ok.body.textEventStream
                    for try await event in body.asDecodedServerSentEventsWithJSONData(
                        of: Components.Schemas.Event.self, decoder: Self.decoder)
                    {
                        if let data = event.data {
                            continuation.yield(data)
                        }
                    }
                    continuation.finish()
                } catch {
                    if Task.isCancelled {
                        continuation.finish()
                    } else {
                        continuation.finish(throwing: (error.toskar as Error?) ?? error)
                    }
                }
            }
            continuation.onTermination = { _ in task.cancel() }
        }
    }

    /// Core's version and its client contract.
    public func version() async throws -> Components.Schemas.VersionResponse {
        try await api.getVersion().ok.body.json
    }

    static var decoder: JSONDecoder {
        let d = JSONDecoder()
        d.dateDecodingStrategy = .custom { decoder in
            let text = try decoder.singleValueContainer().decode(String.self)
            return try CoreDates().decode(text)
        }
        return d
    }
}

extension HTTPField.Name {
    static let toskarClientContract = HTTPField.Name("Toskar-Client-Contract")!
}
