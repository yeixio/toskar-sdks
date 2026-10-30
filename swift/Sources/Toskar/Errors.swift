import Foundation
import OpenAPIRuntime

/// An error from Toskar Core: `{"error": {"code", "message", "details"}}`.
///
/// `code` is stable, such as `.noModelInstalled`; `message` is English text
/// for logs; `details` has the values the message needs.
///
///     do { … } catch let error where error.toskar?.code == .noModelInstalled { … }
public struct ToskarError: Error, Sendable, CustomStringConvertible {
    /// A code Toskar Core answers errors with. A newer Core may answer with
    /// one the SDK doesn't name yet, so it's open.
    public struct Code: RawRepresentable, Hashable, Sendable, CustomStringConvertible {
        public let rawValue: String
        public init(rawValue: String) { self.rawValue = rawValue }
        public init(_ rawValue: String) { self.rawValue = rawValue }
        public var description: String { rawValue }
    }

    /// The HTTP status Toskar answered with.
    public let status: Int
    public let code: Code
    public let message: String
    public let details: OpenAPIObjectContainer?

    public init(status: Int, code: Code, message: String, details: OpenAPIObjectContainer? = nil) {
        self.status = status
        self.code = code
        self.message = message
        self.details = details
    }

    /// The error a response body describes, or a generic one for a body
    /// that isn't Toskar's.
    init(status: Int, body: Data) {
        struct Envelope: Decodable {
            struct Inner: Decodable {
                let code: String
                let message: String?
                let details: OpenAPIObjectContainer?
            }
            let error: Inner?
        }
        // A stream's error_code event is the inner object itself.
        if let e = (try? JSONDecoder().decode(Envelope.self, from: body))?.error
            ?? (try? JSONDecoder().decode(Envelope.Inner.self, from: body)), !e.code.isEmpty
        {
            self.init(status: status, code: Code(e.code), message: e.message ?? e.code, details: e.details)
        } else {
            self.init(status: status, code: Code("HTTP_\(status)"), message: "Toskar answered \(status)")
        }
    }

    static func badHeader(_ name: String) -> ToskarError {
        ToskarError(status: 0, code: Code("BAD_HEADER"), message: "\(name) isn't a header name")
    }

    public var description: String { "toskar: \(message) (\(status) \(code))" }
}

/// The SDK's own codes, for what goes wrong before Toskar Core answers.
extension ToskarError.Code {
    /// The computer's certificate isn't the one paired with: stop, and pair
    /// again to trust a new certificate.
    public static let pinMismatch = Self("PIN_MISMATCH")
    /// Pairing that the person stopped at the short pin.
    public static let notConfirmed = Self("NOT_CONFIRMED")
    /// No way in answered, at home or away.
    public static let unreachable = Self("UNREACHABLE")
    /// No address record to find the computer away from home: it may be off
    /// or asleep, or have no access from anywhere.
    public static let noRecord = Self("NO_RECORD")
    /// An address record that doesn't open with the route secret.
    public static let recordSealed = Self("RECORD_SEALED")
    /// An address record that isn't from the pinned computer, or is for
    /// another route.
    public static let recordPin = Self("RECORD_PIN")
    /// An address record too old, or from too far in the future.
    public static let recordStale = Self("RECORD_STALE")
}

extension Error {
    /// The `ToskarError` this is, or that a generated call wrapped, or nil.
    public var toskar: ToskarError? {
        if let e = self as? ToskarError {
            return e
        }
        if let e = self as? ClientError {
            return e.underlyingError.toskar
        }
        return nil
    }
}
