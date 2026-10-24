"""The official Python SDK for Toskar: local AI across your own computers.

    from toskar import Toskar

    toskar = Toskar()
    for event in toskar.chat_stream("Plan a three-day trip to Juneau"):
        if event.type == "token":
            print(event.content, end="", flush=True)
"""

from ._client import AsyncToskar, ChatStreamEvent, Done, Token, Toskar
from ._errors import ToskarError
from ._generated import models
from ._generated.codes import CONTRACT_VERSION, ErrorCodes
from ._sse import ServerSentEvent, aread_events, read_events

__all__ = [
    "CONTRACT_VERSION",
    "AsyncToskar",
    "ChatStreamEvent",
    "Done",
    "ErrorCodes",
    "ServerSentEvent",
    "Token",
    "Toskar",
    "ToskarError",
    "aread_events",
    "models",
    "read_events",
]
