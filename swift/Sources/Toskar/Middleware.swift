import Foundation
import HTTPTypes
import OpenAPIRuntime

/// Adds the SDK's headers to every request.
struct Headers: ClientMiddleware {
    let fields: [HTTPField]

    func intercept(
        _ request: HTTPRequest, body: HTTPBody?, baseURL: URL, operationID: String,
        next: @Sendable (HTTPRequest, HTTPBody?, URL) async throws -> (HTTPResponse, HTTPBody?)
    ) async throws -> (HTTPResponse, HTTPBody?) {
        var request = request
        for field in fields {
            request.headerFields[field.name] = field.value
        }
        return try await next(request, body, baseURL)
    }
}

/// Retries safe requests that fail to connect or answer 502, 503, or 504,
/// with backoff. A chat is never retried: it could answer twice.
struct Retrying: ClientMiddleware {
    let retries: Int

    func intercept(
        _ request: HTTPRequest, body: HTTPBody?, baseURL: URL, operationID: String,
        next: @Sendable (HTTPRequest, HTTPBody?, URL) async throws -> (HTTPResponse, HTTPBody?)
    ) async throws -> (HTTPResponse, HTTPBody?) {
        let safe = [HTTPRequest.Method.get, .head, .options].contains(request.method)
        let attempts = safe ? 1 + retries : 1
        var attempt = 1
        while true {
            do {
                let (response, responseBody) = try await next(request, body, baseURL)
                if attempt >= attempts || ![502, 503, 504].contains(response.status.code) {
                    return (response, responseBody)
                }
            } catch {
                if attempt >= attempts || error is CancellationError {
                    throw error
                }
            }
            try await Task.sleep(nanoseconds: UInt64(200 << (attempt - 1) + Int.random(in: 0..<100)) * 1_000_000)
            attempt += 1
        }
    }
}

/// Turns an error answer, {"error": {"code", "message", "details"}}, into
/// a thrown `ToskarError`.
struct Errors: ClientMiddleware {
    /// The most of an error answer read; Core's are small.
    static let limit = 1 << 20

    func intercept(
        _ request: HTTPRequest, body: HTTPBody?, baseURL: URL, operationID: String,
        next: @Sendable (HTTPRequest, HTTPBody?, URL) async throws -> (HTTPResponse, HTTPBody?)
    ) async throws -> (HTTPResponse, HTTPBody?) {
        let (response, responseBody) = try await next(request, body, baseURL)
        guard response.status.code >= 300 else {
            return (response, responseBody)
        }
        var data = Data()
        if let responseBody {
            data = (try? await Data(collecting: responseBody, upTo: Self.limit)) ?? Data()
        }
        throw ToskarError(status: response.status.code, body: data)
    }
}
