"""Connecting as a paired device, as the Toskar apps do (Toskar Core's
docs/connecting.md): pairing with the code Connect a device shows, the
computer's certificate pinned on every connection, and reaching it at home
or, with access from anywhere, directly or through its relay."""

from __future__ import annotations

import asyncio
import base64
import concurrent.futures
import hashlib
import hmac
import json
import socket
import ssl
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

import httpx

from ._errors import ToskarError
from ._generated.codes import CONTRACT_VERSION

TOSKAR_RELAY = "relay.toskar.ai"
"""Toskar's own relay. It's asked only with a route token."""

Path = Literal["home", "direct", "relay"]

HOME_TIMEOUT = 2.5
TRY_TIMEOUT = 6.0
RELAY_DELAY = 1.0
RECORD_MAX_AGE = 3600


class PinMismatch(ToskarError):
    """The computer's certificate isn't the one paired with: stop, and pair
    again to trust a new certificate."""

    def __init__(self) -> None:
        super().__init__(0, "PIN_MISMATCH", "The computer's certificate isn't the one paired with")


class NotConfirmed(ToskarError):
    """Pairing the person stopped at the short pin."""

    def __init__(self) -> None:
        super().__init__(0, "NOT_CONFIRMED", "The short pin wasn't confirmed")


class Unreachable(ToskarError):
    """No way in answered, at home or away. ``code`` is NO_RECORD when there
    was no address record: the computer may be off or asleep, or have no
    access from anywhere."""

    def __init__(self, code: str = "UNREACHABLE", message: str = "The computer can't be reached") -> None:
        super().__init__(0, code, message)


class RecordError(Exception):
    """An address record that must be refused: ``reason`` is sealed, pin, or stale."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"the address record was refused ({reason})")
        self.reason = reason


@dataclass
class Route:
    """How to find the computer away from home, when it has access from anywhere."""

    secret: str
    """The route secret, base64url without padding."""
    id: str
    relay: str
    """The relay the computer uses, such as relay.toskar.ai."""
    token: str = ""
    """Lets the device look the computer up on Toskar's relay."""


@dataclass
class Device:
    """What a paired device keeps, to connect again. Save it as a password is
    saved: ``api_key`` and the route's secret and token are secrets."""

    address: str
    """The computer's host:port at home."""
    api_key: str
    pin: str
    """``sha256:<hex>`` of the computer's certificate. It only ever comes from pairing."""
    route: Route | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Device:
        route = data.get("route")
        return cls(data["address"], data["api_key"], data["pin"], Route(**route) if route else None)


def pin_of(der: bytes) -> str:
    """The pin of a certificate: ``sha256:<hex>`` of its DER."""
    return "sha256:" + hashlib.sha256(der).hexdigest()


def short_pin(pin: str) -> str:
    """How a pin is shown for the person to compare: its first 8 hex digits, as ABCD-1234."""
    h = pin.removeprefix("sha256:").upper()
    return h if len(h) < 8 else f"{h[:4]}-{h[4:8]}"


# Pinning: the handshake itself checks the certificate, before anything is sent.


class _PinnedSocket(ssl.SSLSocket):
    def do_handshake(self, block: bool = False) -> None:  # type: ignore[override]
        super().do_handshake(block)
        self.context.check(self.getpeercert(binary_form=True))  # type: ignore[attr-defined]


class _PinnedObject(ssl.SSLObject):
    def do_handshake(self) -> None:
        super().do_handshake()
        self.context.check(self.getpeercert(binary_form=True))  # type: ignore[attr-defined]


class _PinnedContext(ssl.SSLContext):
    pin: str = ""
    seen: Callable[[str], None] | None = None

    def check(self, der: bytes | None) -> None:
        got = pin_of(der or b"")
        if self.seen is not None:
            self.seen(got)
        elif got.lower() != self.pin.lower():
            raise ssl.SSLCertVerificationError(f"the computer's certificate isn't the one paired with ({short_pin(got)})")


def pinned_context(pin: str = "", seen: Callable[[str], None] | None = None) -> ssl.SSLContext:
    """An SSL context that trusts exactly the certificate with ``pin``; names,
    dates, and signers aren't checked. With ``seen``, any certificate is let
    through and its pin handed to ``seen``, for pairing."""
    ctx = _PinnedContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # the pin is the trust, checked in the handshake
    ctx.sslsocket_class = _PinnedSocket
    ctx.sslobject_class = _PinnedObject
    ctx.pin, ctx.seen = pin, seen
    return ctx


def _is_pin_mismatch(err: BaseException) -> bool:
    while err is not None:
        if isinstance(err, ssl.SSLCertVerificationError) and "paired with" in str(err):
            return True
        err = err.__cause__ or err.__context__  # type: ignore[assignment]
    return False


# Pairing.


def _split(address: str) -> tuple[str, int]:
    host, _, port = address.rpartition(":")
    return host.strip("[]"), int(port)


def _certificate_pin(address: str, timeout: float) -> str:
    seen: list[str] = []
    host, port = _split(address)
    with socket.create_connection((host, port), timeout=timeout) as raw:
        with pinned_context(seen=seen.append).wrap_socket(raw, server_hostname=host):
            pass
    return seen[0]


def _paired(address: str, pin: str, answer: dict[str, Any]) -> Device:
    if str(answer.get("tls_fingerprint", "")).lower() != pin.lower():
        raise PinMismatch()
    route = None
    if answer.get("route_secret"):
        route = Route(answer["route_secret"], answer.get("route_id", ""), answer.get("relay", ""), answer.get("token") or "")
    return Device(address, answer["api_key"], pin, route)


def pair(address: str, code: str, device_name: str, confirm: Callable[[str], bool] | None = None, *, timeout: float = 30.0) -> Device:
    """Pairs with the computer at ``address`` (host:port) using the code
    Connect a device shows on it. ``confirm`` gets the short pin to show the
    person, and says whether the computer shows the same. The device must be
    on the computer's local network."""
    pin = _certificate_pin(address, timeout)
    if confirm is not None and not confirm(short_pin(pin)):
        raise NotConfirmed()
    with httpx.Client(verify=pinned_context(pin), timeout=timeout) as http:
        response = http.post(
            f"https://{address}/api/v1/devices/pair",
            json={"code": code, "device_name": device_name},
            headers={"Toskar-Client-Contract": CONTRACT_VERSION},
        )
    if response.status_code >= 300:
        raise ToskarError.from_body(response.status_code, _json(response))
    return _paired(address, pin, response.json())


async def apair(address: str, code: str, device_name: str, confirm: Callable[[str], bool] | None = None, *, timeout: float = 30.0) -> Device:
    """pair(), for asyncio."""
    pin = await asyncio.to_thread(_certificate_pin, address, timeout)
    if confirm is not None and not confirm(short_pin(pin)):
        raise NotConfirmed()
    async with httpx.AsyncClient(verify=pinned_context(pin), timeout=timeout) as http:
        response = await http.post(
            f"https://{address}/api/v1/devices/pair",
            json={"code": code, "device_name": device_name},
            headers={"Toskar-Client-Contract": CONTRACT_VERSION},
        )
    if response.status_code >= 300:
        raise ToskarError.from_body(response.status_code, _json(response))
    return _paired(address, pin, response.json())


def _json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


# Route IDs, record keys, and address records.


def _hkdf(secret: bytes, info: bytes, length: int) -> bytes:
    prk = hmac.new(b"\0" * 32, secret, hashlib.sha256).digest()
    out, block, counter = b"", b"", 1
    while len(out) < length:
        block = hmac.new(prk, block + info + bytes([counter]), hashlib.sha256).digest()
        out += block
        counter += 1
    return out[:length]


def _secret(secret: str) -> bytes:
    raw = base64.urlsafe_b64decode(secret + "=" * (-len(secret) % 4))
    if len(raw) != 32:
        raise ValueError("a route secret is 32 bytes, base64url")
    return raw


def route_id(secret: str) -> str:
    """The route ID a route secret names."""
    return base64.b32encode(_hkdf(_secret(secret), b"toskar route id", 20)).decode().lower().rstrip("=")


@dataclass
class Record:
    """What an address record says: the computer's ways in, and when it wrote them."""

    addresses: list[str] = field(default_factory=list)
    at: int = 0


def open_record(blob: bytes, secret: str, pin: str, now: float | None = None, max_age: float = RECORD_MAX_AGE) -> Record:
    """Opens an address record as docs/connecting.md says, or raises
    RecordError. Needs the ``anywhere`` extra: pip install "toskar[anywhere]"."""
    try:
        from cryptography.exceptions import InvalidSignature, InvalidTag
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.x509 import load_der_x509_certificate
    except ImportError as err:  # pragma: no cover
        raise ImportError('Reaching a computer from anywhere needs the cryptography package: pip install "toskar[anywhere]"') from err

    now = time.time() if now is None else now
    raw = _secret(secret)
    route = route_id(secret)
    if len(blob) < 12 + 16:
        raise RecordError("sealed")
    try:
        plain = AESGCM(_hkdf(raw, b"toskar route key", 32)).decrypt(blob[:12], blob[12:], route.encode())
        rec = json.loads(plain)
        payload, cert, sig = (base64.b64decode(rec[k]) for k in ("payload", "cert", "sig"))
    except (InvalidTag, ValueError, KeyError, TypeError) as err:
        raise RecordError("sealed") from err
    if pin_of(cert).lower() != pin.lower():
        raise RecordError("pin")
    try:
        key = load_der_x509_certificate(cert).public_key()
        alg = rec.get("alg")
        if alg == "ecdsa-sha256" and isinstance(key, ec.EllipticCurvePublicKey):
            key.verify(sig, payload, ec.ECDSA(hashes.SHA256()))
        elif alg == "rsa-pkcs1-sha256" and isinstance(key, rsa.RSAPublicKey):
            key.verify(sig, payload, padding.PKCS1v15(), hashes.SHA256())
        elif alg == "ed25519" and isinstance(key, ed25519.Ed25519PublicKey):
            key.verify(sig, payload)
        else:
            raise RecordError("pin")
        body = json.loads(payload)
    except (InvalidSignature, ValueError) as err:
        raise RecordError("pin") from err
    if body.get("v") != 1 or body.get("route") != route:
        raise RecordError("pin")
    at = int(body["at"])
    if now - at > max_age or at - now > 300:
        raise RecordError("stale")
    return Record(list(body.get("addresses") or []), at)


# Choosing the way in.


def _host(address: str) -> str:
    return address.rpartition(":")[0].strip("[]").lower() if ":" in address else address.lower()


def _ways(device: Device, record: Record) -> list[tuple[Path, str]]:
    relay = _host(device.route.relay) if device.route else ""
    return [("relay" if _host(a).endswith("." + relay) else "direct", a) for a in record.addresses]


def _record_url(route: Route) -> tuple[str, dict[str, str]]:
    headers = {"Authorization": f"Bearer {route.token}"} if route.token else {}
    return f"https://{route.relay}/v1/routes/{route.id}/record", headers


def _asks_relay(route: Route | None) -> bool:
    # Toskar's relay answers only for a subscription; without one, it isn't
    # asked, so nothing about this device reaches it.
    return route is not None and bool(route.secret) and not (_host(route.relay) == TOSKAR_RELAY and not route.token)


def _healthy(response: httpx.Response) -> bool:
    try:
        return response.status_code == 200 and response.json().get("status") == "ok"
    except ValueError:
        return False


class _Router(httpx.BaseTransport):
    """Sends each request to the way in in use, choosing it again when it
    stops answering."""

    def __init__(self, device: Device, timeout: httpx.Timeout, relay_client: httpx.Client | None = None) -> None:
        self.device = device
        self.pinned = httpx.HTTPTransport(verify=pinned_context(device.pin))
        self.timeout = timeout
        self.relay_client = relay_client or httpx.Client(timeout=TRY_TIMEOUT)
        self.lock = threading.Lock()
        self.way: str | None = None
        self.path: Path | None = None

    def _answers(self, address: str, timeout: float) -> bool:
        request = httpx.Request("GET", f"https://{address}/api/v1/health", extensions={"timeout": httpx.Timeout(timeout).as_dict()})
        try:
            response = self.pinned.handle_request(request)
            response.read()
            return _healthy(response)
        except httpx.TransportError as err:
            if _is_pin_mismatch(err) and address == self.device.address:
                raise PinMismatch() from err
            return False

    def choose(self) -> tuple[Path, str]:
        if self._answers(self.device.address, HOME_TIMEOUT):
            return "home", self.device.address
        route = self.device.route
        if not _asks_relay(route):
            raise Unreachable()
        assert route is not None
        url, headers = _record_url(route)
        try:
            response = self.relay_client.get(url, headers=headers)
        except httpx.HTTPError as err:
            raise Unreachable("NO_RECORD", "No address record for the computer") from err
        if response.status_code != 200:
            raise Unreachable("NO_RECORD", "No address record for the computer")
        try:
            record = open_record(response.content, route.secret, self.device.pin)
        except RecordError as err:
            raise Unreachable("NO_RECORD", f"The computer's address record was refused ({err.reason})") from err
        ways = _ways(self.device, record)
        found: list[tuple[Path, str]] = []
        done = threading.Event()

        def attempt(path: Path, address: str) -> None:
            if path == "relay" and done.wait(RELAY_DELAY):
                return
            # Another certificate at a way in is someone else's device there.
            try:
                ok = self._answers(address, TRY_TIMEOUT)
            except PinMismatch:
                ok = False
            if ok and not done.is_set():
                found.append((path, address))
                done.set()

        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(ways))) as pool:
            futures = [pool.submit(attempt, p, a) for p, a in ways]
            for f in concurrent.futures.as_completed(futures):
                if done.is_set():
                    break
        if not found:
            raise Unreachable()
        return found[0]

    def current(self) -> str:
        with self.lock:
            if self.way is None:
                self.path, self.way = self.choose()
            return self.way

    def forget(self, way: str) -> None:
        with self.lock:
            if self.way == way:
                self.way, self.path = None, None

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        way = self.current()
        host, port = _split(way)
        request.url = request.url.copy_with(host=host, port=port)
        request.headers["Host"] = way
        try:
            return self.pinned.handle_request(request)
        except httpx.TransportError as err:
            if _is_pin_mismatch(err):
                raise PinMismatch() from err
            self.forget(way)
            raise

    def close(self) -> None:
        self.pinned.close()
        self.relay_client.close()


class _AsyncRouter(httpx.AsyncBaseTransport):
    """_Router, for asyncio."""

    def __init__(self, device: Device, timeout: httpx.Timeout, relay_client: httpx.AsyncClient | None = None) -> None:
        self.device = device
        self.pinned = httpx.AsyncHTTPTransport(verify=pinned_context(device.pin))
        self.relay_client = relay_client or httpx.AsyncClient(timeout=TRY_TIMEOUT)
        self.lock = asyncio.Lock()
        self.way: str | None = None
        self.path: Path | None = None

    async def _answers(self, address: str, timeout: float) -> bool:
        request = httpx.Request("GET", f"https://{address}/api/v1/health", extensions={"timeout": httpx.Timeout(timeout).as_dict()})
        try:
            response = await self.pinned.handle_async_request(request)
            await response.aread()
            return _healthy(response)
        except httpx.TransportError as err:
            if _is_pin_mismatch(err) and address == self.device.address:
                raise PinMismatch() from err
            return False

    async def choose(self) -> tuple[Path, str]:
        if await self._answers(self.device.address, HOME_TIMEOUT):
            return "home", self.device.address
        route = self.device.route
        if not _asks_relay(route):
            raise Unreachable()
        assert route is not None
        url, headers = _record_url(route)
        try:
            response = await self.relay_client.get(url, headers=headers)
        except httpx.HTTPError as err:
            raise Unreachable("NO_RECORD", "No address record for the computer") from err
        if response.status_code != 200:
            raise Unreachable("NO_RECORD", "No address record for the computer")
        try:
            record = open_record(response.content, route.secret, self.device.pin)
        except RecordError as err:
            raise Unreachable("NO_RECORD", f"The computer's address record was refused ({err.reason})") from err

        async def attempt(path: Path, address: str) -> tuple[Path, str] | None:
            if path == "relay":
                await asyncio.sleep(RELAY_DELAY)
            try:
                return (path, address) if await self._answers(address, TRY_TIMEOUT) else None
            except PinMismatch:
                return None

        tasks = [asyncio.create_task(attempt(p, a)) for p, a in _ways(self.device, record)]
        try:
            for next_done in asyncio.as_completed(tasks):
                if (result := await next_done) is not None:
                    return result
        finally:
            for t in tasks:
                t.cancel()
        raise Unreachable()

    async def current(self) -> str:
        async with self.lock:
            if self.way is None:
                self.path, self.way = await self.choose()
            return self.way

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        way = await self.current()
        host, port = _split(way)
        request.url = request.url.copy_with(host=host, port=port)
        request.headers["Host"] = way
        try:
            return await self.pinned.handle_async_request(request)
        except httpx.TransportError as err:
            if _is_pin_mismatch(err):
                raise PinMismatch() from err
            async with self.lock:
                if self.way == way:
                    self.way, self.path = None, None
            raise

    async def aclose(self) -> None:
        await self.pinned.aclose()
        await self.relay_client.aclose()
