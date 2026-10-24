from __future__ import annotations

from collections.abc import AsyncIterator, Iterable, Iterator
from dataclasses import dataclass


@dataclass(frozen=True)
class ServerSentEvent:
    """One server-sent event: its name ("message" without one) and its data."""

    event: str
    data: str


class _Parser:
    def __init__(self) -> None:
        self.event = "message"
        self.data: list[str] = []

    def line(self, line: str) -> ServerSentEvent | None:
        line = line.rstrip("\r")
        if not line:
            out = ServerSentEvent(self.event, "\n".join(self.data)) if self.data else None
            self.event, self.data = "message", []
            return out
        if line.startswith(":"):
            return None  # a comment, such as ": ping"
        field, _, value = line.partition(":")
        value = value[1:] if value.startswith(" ") else value
        if field == "event":
            self.event = value
        elif field == "data":
            self.data.append(value)
        return None

    def end(self) -> ServerSentEvent | None:
        return self.line("")


def read_events(lines: Iterable[str]) -> Iterator[ServerSentEvent]:
    """Reads server-sent events from a stream's lines, as they arrive."""
    parser = _Parser()
    for line in lines:
        if (event := parser.line(line)) is not None:
            yield event
    if (event := parser.end()) is not None:
        yield event


async def aread_events(lines: AsyncIterator[str]) -> AsyncIterator[ServerSentEvent]:
    """Reads server-sent events from a stream's lines, for asyncio."""
    parser = _Parser()
    async for line in lines:
        if (event := parser.line(line)) is not None:
            yield event
    if (event := parser.end()) is not None:
        yield event
