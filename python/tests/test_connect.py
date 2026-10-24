import base64
import datetime
import hashlib
import ipaddress
import json
import os
import socket
import ssl
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.x509.oid import NameOID

from toskar import (
    AsyncToskar,
    Device,
    NotConfirmed,
    PinMismatch,
    RecordError,
    Route,
    TOSKAR_RELAY,
    Toskar,
    Unreachable,
    open_record,
    pair,
    pin_of,
    route_id,
    short_pin,
)
from toskar._connect import _hkdf, _secret

VECTORS = json.loads((Path(__file__).resolve().parents[2] / "spec" / "connection-vectors.json").read_text())
SECRET = "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8"


def test_connection_vectors():
    for r in VECTORS["routes"]:
        assert route_id(r["secret"]) == r["route_id"]
    for p in VECTORS["pins"]:
        pin = pin_of(base64.b64decode(p["cert_der_base64"]))
        assert (pin, short_pin(pin)) == (p["fingerprint"], p["short"])
    for r in VECTORS["records"]:
        blob = base64.b64decode(r["blob_base64"])
        if r.get("error"):
            with pytest.raises(RecordError) as err:
                open_record(blob, r["secret"], r["pin"], r["now"], r["max_age_seconds"])
            assert err.value.reason == r["error"], r["name"]
        else:
            rec = open_record(blob, r["secret"], r["pin"], r["now"], r["max_age_seconds"])
            assert (rec.addresses, rec.at) == (r["addresses"], r["at"]), r["name"]


class Computer:
    """A Toskar Core on TLS with a certificate of its own, as a computer's API
    listener is, counting the keys it's sent."""

    def __init__(self, pair_answer=None, record=None):
        self.keys = 0
        self.tokens: list[str] = []
        key = ec.generate_private_key(ec.SECP256R1())
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Toskar test")])
        now = datetime.datetime.now(datetime.timezone.utc)
        cert = (
            x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - datetime.timedelta(hours=1))
            .not_valid_after(now + datetime.timedelta(hours=1))
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), critical=False)
            .sign(key, hashes.SHA256())
        )
        self.key, self.der = key, cert.public_bytes(serialization.Encoding.DER)
        self.pin = pin_of(self.der)
        computer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def answer(self, status, body, kind="application/json"):
                data = body if isinstance(body, bytes) else json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                if self.headers.get("Authorization"):
                    computer.keys += 1
                if self.path == "/api/v1/health":
                    self.answer(200, {"status": "ok"})
                elif record is not None and self.path.endswith("/record"):
                    computer.tokens.append(self.headers.get("Authorization", ""))
                    self.answer(200, record(), "application/octet-stream")
                else:
                    self.answer(200, [])

            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                self.answer(201, pair_answer(computer.pin))

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        # A client that refuses the certificate hangs up mid-handshake, as it should.
        self.server.handle_error = lambda *args: None
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        with tempfile.TemporaryDirectory() as d:
            certfile, keyfile = os.path.join(d, "c.pem"), os.path.join(d, "k.pem")
            Path(certfile).write_bytes(cert.public_bytes(serialization.Encoding.PEM))
            Path(keyfile).write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
            ctx.load_cert_chain(certfile, keyfile)
        self.server.socket = ctx.wrap_socket(self.server.socket, server_side=True)
        self.address = f"127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()

    def seal(self, secret, addresses):
        """An address record, as the computer writes it."""
        route = route_id(secret)
        payload = json.dumps({"v": 1, "route": route, "at": int(time.time()), "addresses": addresses}).encode()
        sig = self.key.sign(payload, ec.ECDSA(hashes.SHA256()))
        plain = json.dumps({k: base64.b64encode(v).decode() for k, v in {"payload": payload, "cert": self.der, "sig": sig}.items()} | {"alg": "ecdsa-sha256"}).encode()
        nonce = os.urandom(12)
        return nonce + AESGCM(_hkdf(_secret(secret), b"toskar route key", 32)).encrypt(nonce, plain, route.encode())


def unused():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return f"127.0.0.1:{s.getsockname()[1]}"


@pytest.fixture
def computers():
    made = []

    def make(**kw):
        c = Computer(**kw)
        made.append(c)
        return c

    yield make
    for c in made:
        c.close()


def paired_answer(pin):
    return {"api_key": "tk_device", "tls_fingerprint": pin, "tls_short": short_pin(pin), "key": {"id": "k"},
            "route_secret": SECRET, "route_id": route_id(SECRET), "relay": "relay.toskar.ai", "token": "rt"}


def test_pair_pins_the_computers_certificate(computers):
    c = computers(pair_answer=paired_answer)
    shown = []
    device = pair(c.address, "123456", "Test", lambda short: shown.append(short) or True)
    assert shown == [short_pin(c.pin)] and device.pin == c.pin and device.api_key == "tk_device"
    assert device.route == Route(SECRET, route_id(SECRET), "relay.toskar.ai", "rt")
    assert Device.from_dict(device.to_dict()) == device
    with pytest.raises(NotConfirmed):
        pair(c.address, "123456", "Test", lambda short: False)


def test_pair_refuses_a_fingerprint_that_isnt_the_certificates(computers):
    c = computers(pair_answer=lambda pin: paired_answer("sha256:" + "ab" * 32))
    with pytest.raises(PinMismatch):
        pair(c.address, "123456", "Test")


def test_another_certificate_never_sees_the_key(computers):
    mine, other = computers(), computers()
    with pytest.raises(PinMismatch):
        Toskar(device=Device(other.address, "tk_device", mine.pin), retries=0).api.list_models()
    assert other.keys == 0


def test_home_first(computers):
    c = computers()
    toskar = Toskar(device=Device(c.address, "tk_device", c.pin))
    assert toskar.api.list_models() == [] and toskar.path == "home" and c.keys == 1


def test_away_through_the_record(computers):
    c = computers()
    relay = computers(record=lambda: c.seal(SECRET, [c.address, route_id(SECRET) + ".relay.test:4443"]))
    device = Device(unused(), "tk_device", c.pin, Route(SECRET, route_id(SECRET), relay.address, "rt"))
    toskar = Toskar(device=device)
    # The test relay's certificate is its own; a real relay's is checked as any website's.
    toskar._router.relay_client = httpx.Client(verify=False)
    assert toskar.api.list_models() == [] and toskar.path == "direct" and relay.tokens == ["Bearer rt"]


def test_toskars_relay_isnt_asked_without_a_token(computers):
    c = computers()
    toskar = Toskar(device=Device(unused(), "tk", c.pin, Route(SECRET, route_id(SECRET), TOSKAR_RELAY)), retries=0)
    asked = []
    toskar._router.relay_client = httpx.Client(transport=httpx.MockTransport(lambda r: asked.append(r) or httpx.Response(500)))
    with pytest.raises(Unreachable):
        toskar.api.list_models()
    assert asked == []


@pytest.mark.asyncio
async def test_async_pins_too(computers):
    mine, other = computers(), computers()
    async with AsyncToskar(device=Device(mine.address, "tk_device", mine.pin)) as toskar:
        assert await toskar.api.list_models() == [] and toskar.path == "home"
    async with AsyncToskar(device=Device(other.address, "tk_device", mine.pin), retries=0) as toskar:
        with pytest.raises(PinMismatch):
            await toskar.api.list_models()
    assert other.keys == 0
