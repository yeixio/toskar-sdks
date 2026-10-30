import Foundation
import OpenAPIRuntime

/// Toskar Core's times: RFC 3339, with any number of fraction digits (Go
/// writes up to nine), which Foundation's ISO 8601 parser reads only to
/// milliseconds.
struct CoreDates: DateTranscoder {
    func encode(_ date: Date) throws -> String {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f.string(from: date)
    }

    func decode(_ text: String) throws -> Date {
        var trimmed = text
        // Keep three fraction digits: 2026-10-29T16:04:05.123456789Z → .123Z
        if let dot = text.firstIndex(of: "."),
            let end = text[dot...].firstIndex(where: { !$0.isNumber && $0 != "." })
        {
            let digits = text[text.index(after: dot)..<end]
            trimmed = String(text[..<dot]) + "." + String((digits + "000").prefix(3)) + String(text[end...])
        }
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let d = f.date(from: trimmed) {
            return d
        }
        f.formatOptions = [.withInternetDateTime]
        if let d = f.date(from: trimmed) {
            return d
        }
        throw DecodingError.dataCorrupted(.init(codingPath: [], debugDescription: "\(text) isn't an RFC 3339 time"))
    }
}
