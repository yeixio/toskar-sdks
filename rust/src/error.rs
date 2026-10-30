use std::fmt;

use serde_json::{Map, Value};

/// What the SDK's calls answer.
pub type Result<T, E = Error> = std::result::Result<T, E>;

/// An error from Toskar Core: `{"error": {"code", "message", "details"}}`.
///
/// `code` is stable, such as [`crate::error_codes::NO_MODEL_INSTALLED`];
/// `message` is English text for logs; `details` has the values the message
/// needs.
///
/// The SDK's own codes, for what goes wrong before Toskar Core answers, are
/// `CONNECTION_FAILED` (with the cause as its source), `CONNECTION_LOST` (a
/// stream cut off), `BAD_URL`, and `HTTP_<status>` for an answer that isn't
/// Toskar's.
#[derive(Debug)]
pub struct Error {
    /// The HTTP status Toskar answered with, or 0 when it didn't answer.
    pub status: u16,
    /// The error's code, such as `NO_MODEL_INSTALLED`.
    pub code: String,
    /// English text for logs.
    pub message: String,
    /// The values the message needs, when Toskar sent them.
    pub details: Option<Map<String, Value>>,
    source: Option<Box<dyn std::error::Error + Send + Sync>>,
}

impl Error {
    /// An error with its code.
    pub fn new(status: u16, code: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            status,
            code: code.into(),
            message: message.into(),
            details: None,
            source: None,
        }
    }

    pub(crate) fn with_source(mut self, source: impl std::error::Error + Send + Sync + 'static) -> Self {
        self.source = Some(Box::new(source));
        self
    }

    /// The error a response body describes, or a generic one for a body that isn't Toskar's.
    pub(crate) fn from_body(status: u16, body: &[u8]) -> Self {
        let parsed: Option<Map<String, Value>> = serde_json::from_slice(body).ok();
        // A stream's error_code event is the inner object itself.
        let inner = parsed
            .as_ref()
            .and_then(|p| p.get("error"))
            .and_then(Value::as_object)
            .or(parsed.as_ref());
        if let Some(e) = inner {
            if let Some(code) = e.get("code").and_then(Value::as_str).filter(|c| !c.is_empty()) {
                let message = e.get("message").and_then(Value::as_str).unwrap_or(code);
                let mut out = Self::new(status, code, message);
                out.details = e.get("details").and_then(Value::as_object).cloned();
                return out;
            }
        }
        Self::new(status, format!("HTTP_{status}"), format!("Toskar answered {status}"))
    }
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "toskar: {} ({} {})", self.message, self.status, self.code)
    }
}

impl std::error::Error for Error {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        self.source.as_deref().map(|s| s as &(dyn std::error::Error + 'static))
    }
}
