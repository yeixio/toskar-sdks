from __future__ import annotations

from typing import Any


class ToskarError(Exception):
    """An error from Toskar Core: {"error": {"code", "message", "details"}}.

    ``code`` is stable, such as ``NO_MODEL_INSTALLED`` (see ErrorCodes);
    ``message`` is English text for logs; ``details`` has the values the
    message needs.
    """

    def __init__(self, status: int, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details or {}

    def __repr__(self) -> str:
        return f"ToskarError(status={self.status}, code={self.code!r}, message={self.message!r})"

    @classmethod
    def from_body(cls, status: int, body: Any) -> ToskarError:
        """The error a response body describes, or a generic one for a body that isn't Toskar's."""
        error = body.get("error") if isinstance(body, dict) else None
        if isinstance(error, dict) and error.get("code"):
            return cls(status, error["code"], error.get("message") or error["code"], error.get("details") or {})
        return cls(status, f"HTTP_{status}", f"Toskar answered {status}")
