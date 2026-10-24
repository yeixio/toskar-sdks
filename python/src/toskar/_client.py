from __future__ import annotations

import asyncio
import json
import os
import random
import time
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal, Union

import httpx
from pydantic import BaseModel, TypeAdapter

from ._connect import Device, Path, _AsyncRouter, _Router
from ._errors import ToskarError
from ._generated import models
from ._generated.codes import CONTRACT_VERSION
from ._generated.operations import Api, AsyncApi
from ._sse import aread_events, read_events

DEFAULT_URL = "http://127.0.0.1:7331"
SAFE = {"GET", "HEAD", "OPTIONS"}
RETRYABLE = {502, 503, 504}


@dataclass(frozen=True)
class Token:
    """The next piece of a streamed answer."""

    content: str
    type: Literal["token"] = "token"


@dataclass(frozen=True)
class Done:
    """A streamed answer finished and was saved."""

    metrics: models.GenerationMetrics | None = None
    type: Literal["done"] = "done"


ChatStreamEvent = Union[Token, Done]
"""One event of a streamed chat. A failure is raised as a ToskarError instead."""


@lru_cache(maxsize=None)
def _adapter(kind: Any) -> TypeAdapter[Any]:
    return TypeAdapter(kind)


def _parse(answer: Any, read: str, response: httpx.Response) -> Any:
    if read == "none":
        return None
    if read == "bytes":
        return response.content
    data = response.json()
    return data if answer is Any else _adapter(answer).validate_python(data)


def _json(body: Any) -> Any:
    if isinstance(body, BaseModel):
        return body.model_dump(mode="json", by_alias=True, exclude_none=True)
    return body


def _body(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


def _chat_body(message: str, fields: dict[str, Any], stream: bool) -> dict[str, Any]:
    return {**{k: v for k, v in fields.items() if v is not None}, "message": message, "stream": stream}


def _stream_event(event: str, data: str, status: int) -> ChatStreamEvent | None:
    if event == "token":
        return Token(content=json.loads(data)["content"])
    if event == "done":
        return Done(metrics=models.ChatDone.model_validate_json(data or "{}").metrics)
    if event == "error_code":
        body = json.loads(data)
        raise ToskarError(status, body.get("code", "CHAT_FAILED"), body.get("message", ""), body.get("details") or {})
    if event == "error":
        raise ToskarError(status, "CHAT_FAILED", data)
    return None


class _Options:
    def __init__(
        self,
        base_url: str | None,
        api_key: str | None,
        retries: int,
        timeout: float | None,
        headers: dict[str, str] | None,
    ) -> None:
        self.base_url = (base_url or os.environ.get("TOSKAR_URL") or DEFAULT_URL).rstrip("/")
        key = api_key or os.environ.get("TOSKAR_API_KEY")
        self.headers = {
            # Core answers 426 CONTRACT_MISMATCH to a client of another major version.
            "Toskar-Client-Contract": CONTRACT_VERSION,
            **({"Authorization": f"Bearer {key}"} if key else {}),
            **(headers or {}),
        }
        self.retries = retries
        self.timeout = httpx.Timeout(timeout)
        # A stream waits for its answer to start, then for as long as it runs.
        self.stream_timeout = httpx.Timeout(timeout, read=None)

    @staticmethod
    def query(query: dict[str, Any]) -> dict[str, Any]:
        return {k: (str(v).lower() if isinstance(v, bool) else v) for k, v in query.items() if v is not None}

    @staticmethod
    def backoff(attempt: int) -> float:
        return 0.2 * 2 ** (attempt - 1) + random.random() * 0.1


class Toskar:
    """A connection to Toskar Core.

    ``api`` reaches every route, typed from Core's API spec::

        models = toskar.api.list_models()

    and the methods here cover what's easier by hand: chat, streamed chat,
    and the events stream.

    By default it reaches this computer's Toskar Core, at
    http://127.0.0.1:7331, which needs no key; elsewhere, pass ``base_url``
    and ``api_key``, or set TOSKAR_URL and TOSKAR_API_KEY.
    """

    def __init__(
        self,
        base_url: str | None = None,
        *,
        api_key: str | None = None,
        retries: int = 2,
        timeout: float | None = 60.0,
        headers: dict[str, str] | None = None,
        http_client: httpx.Client | None = None,
        device: Device | None = None,
    ) -> None:
        if device is not None:
            base_url, api_key = f"https://{device.address}", device.api_key
        self._options = _Options(base_url, api_key, retries, timeout, headers)
        self.base_url = self._options.base_url
        # A paired device (pair()): pinned on every connection, reaching its
        # computer at home or away.
        self._router = _Router(device, self._options.timeout) if device is not None else None
        self._http = http_client or httpx.Client(transport=self._router)
        self.api = Api(self)

    @property
    def path(self) -> Path | None:
        """How a paired device reaches its computer now: home, direct, or
        relay; None before its first request, or without a device."""
        return self._router.path if self._router else None

    def reconnect(self) -> Path | None:
        """Chooses the way in again, as after the network changed."""
        if self._router is None:
            return None
        with self._router.lock:
            self._router.way, self._router.path = None, None
        self._router.current()
        return self._router.path

    def __enter__(self) -> Toskar:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    def chat(self, message: str, **fields: Any) -> models.ChatAnswer:
        """Asks once and waits for the whole answer. ``fields`` are the rest of
        POST /api/v1/chat's body, such as conversation_id or profile_id."""
        response = self._send("POST", "/api/v1/chat", json=_chat_body(message, fields, False))
        return models.ChatAnswer.model_validate(response.json())

    def chat_stream(self, message: str, **fields: Any) -> Iterator[ChatStreamEvent]:
        """Asks and yields the answer as it's written: Token events, then Done
        once it's finished and saved. A failure is raised as a ToskarError,
        with its code, such as NO_MODEL_INSTALLED::

            for event in toskar.chat_stream("Hi"):
                if event.type == "token":
                    print(event.content, end="", flush=True)
        """
        request = self._build("POST", "/api/v1/chat", json=_chat_body(message, fields, True), stream=True)
        response = self._http.send(request, stream=True)
        try:
            if response.status_code >= 400:
                response.read()
                raise ToskarError.from_body(response.status_code, _body(response))
            for e in read_events(response.iter_lines()):
                if (out := _stream_event(e.event, e.data, response.status_code)) is not None:
                    yield out
                    if out.type == "done":
                        return
        finally:
            response.close()
        # Every stream ends with done or an error, so one that just stops was cut off.
        raise ToskarError(response.status_code, "CONNECTION_LOST", "The answer stopped before it finished")

    def events(self) -> Iterator[models.Event]:
        """Yields what happens on Toskar as it happens, such as models loading
        and automations running, until you stop iterating."""
        with self._http.stream("GET", self.base_url + "/api/v1/events", headers={**self._options.headers, "Accept": "text/event-stream"}, timeout=self._options.stream_timeout) as response:
            if response.status_code >= 400:
                response.read()
                raise ToskarError.from_body(response.status_code, _body(response))
            for e in read_events(response.iter_lines()):
                yield models.Event.model_validate_json(e.data)

    def version(self) -> models.VersionResponse:
        """Core's version and its client contract."""
        return self.api.get_version()

    def _build(self, method: str, path: str, *, params: dict[str, Any] | None = None, json: Any = None, stream: bool = False) -> httpx.Request:
        headers = {**self._options.headers, "Accept": "text/event-stream" if stream else "application/json"}
        timeout = self._options.stream_timeout if stream else self._options.timeout
        return self._http.build_request(method, self.base_url + path, params=params, json=json, headers=headers, timeout=timeout)

    def _send(self, method: str, path: str, *, params: dict[str, Any] | None = None, json: Any = None) -> httpx.Response:
        attempts = self._options.retries + 1 if method in SAFE else 1
        for attempt in range(1, attempts + 1):
            try:
                response = self._http.send(self._build(method, path, params=params, json=json))
            except httpx.TransportError:
                if attempt >= attempts:
                    raise
            else:
                if attempt >= attempts or response.status_code not in RETRYABLE:
                    if response.status_code >= 400:
                        raise ToskarError.from_body(response.status_code, _body(response))
                    return response
            time.sleep(self._options.backoff(attempt))
        raise AssertionError("unreachable")

    def _request(self, method: str, path: str, *, query: dict[str, Any], body: Any, answer: Any, read: str) -> Any:
        response = self._send(method, path, params=self._options.query(query), json=_json(body))
        return _parse(answer, read, response)


class AsyncToskar:
    """A connection to Toskar Core, for asyncio: Toskar's methods, awaited.

        async with AsyncToskar() as toskar:
            async for event in toskar.chat_stream("Hi"):
                ...
    """

    def __init__(
        self,
        base_url: str | None = None,
        *,
        api_key: str | None = None,
        retries: int = 2,
        timeout: float | None = 60.0,
        headers: dict[str, str] | None = None,
        http_client: httpx.AsyncClient | None = None,
        device: Device | None = None,
    ) -> None:
        if device is not None:
            base_url, api_key = f"https://{device.address}", device.api_key
        self._options = _Options(base_url, api_key, retries, timeout, headers)
        self.base_url = self._options.base_url
        self._router = _AsyncRouter(device, self._options.timeout) if device is not None else None
        self._http = http_client or httpx.AsyncClient(transport=self._router)
        self.api = AsyncApi(self)

    @property
    def path(self) -> Path | None:
        """How a paired device reaches its computer now."""
        return self._router.path if self._router else None

    async def reconnect(self) -> Path | None:
        """Chooses the way in again, as after the network changed."""
        if self._router is None:
            return None
        async with self._router.lock:
            self._router.way, self._router.path = None, None
        await self._router.current()
        return self._router.path

    async def __aenter__(self) -> AsyncToskar:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def chat(self, message: str, **fields: Any) -> models.ChatAnswer:
        """Asks once and waits for the whole answer."""
        response = await self._send("POST", "/api/v1/chat", json=_chat_body(message, fields, False))
        return models.ChatAnswer.model_validate(response.json())

    async def chat_stream(self, message: str, **fields: Any) -> AsyncIterator[ChatStreamEvent]:
        """Asks and yields the answer as it's written: Token events, then Done."""
        request = self._build("POST", "/api/v1/chat", json=_chat_body(message, fields, True), stream=True)
        response = await self._http.send(request, stream=True)
        try:
            if response.status_code >= 400:
                await response.aread()
                raise ToskarError.from_body(response.status_code, _body(response))
            async for e in aread_events(response.aiter_lines()):
                if (out := _stream_event(e.event, e.data, response.status_code)) is not None:
                    yield out
                    if out.type == "done":
                        return
        finally:
            await response.aclose()
        raise ToskarError(response.status_code, "CONNECTION_LOST", "The answer stopped before it finished")

    async def events(self) -> AsyncIterator[models.Event]:
        """Yields what happens on Toskar as it happens, until you stop iterating."""
        async with self._http.stream("GET", self.base_url + "/api/v1/events", headers={**self._options.headers, "Accept": "text/event-stream"}, timeout=self._options.stream_timeout) as response:
            if response.status_code >= 400:
                await response.aread()
                raise ToskarError.from_body(response.status_code, _body(response))
            async for e in aread_events(response.aiter_lines()):
                yield models.Event.model_validate_json(e.data)

    async def version(self) -> models.VersionResponse:
        """Core's version and its client contract."""
        return await self.api.get_version()

    def _build(self, method: str, path: str, *, params: dict[str, Any] | None = None, json: Any = None, stream: bool = False) -> httpx.Request:
        headers = {**self._options.headers, "Accept": "text/event-stream" if stream else "application/json"}
        timeout = self._options.stream_timeout if stream else self._options.timeout
        return self._http.build_request(method, self.base_url + path, params=params, json=json, headers=headers, timeout=timeout)

    async def _send(self, method: str, path: str, *, params: dict[str, Any] | None = None, json: Any = None) -> httpx.Response:
        attempts = self._options.retries + 1 if method in SAFE else 1
        for attempt in range(1, attempts + 1):
            try:
                response = await self._http.send(self._build(method, path, params=params, json=json))
            except httpx.TransportError:
                if attempt >= attempts:
                    raise
            else:
                if attempt >= attempts or response.status_code not in RETRYABLE:
                    if response.status_code >= 400:
                        raise ToskarError.from_body(response.status_code, _body(response))
                    return response
            await asyncio.sleep(self._options.backoff(attempt))
        raise AssertionError("unreachable")

    async def _request(self, method: str, path: str, *, query: dict[str, Any], body: Any, answer: Any, read: str) -> Any:
        response = await self._send(method, path, params=self._options.query(query), json=_json(body))
        return _parse(answer, read, response)
