"""Finding computers running Toskar Core on the home network, as the Toskar
apps do: they advertise _localai._tcp over mDNS, with where their API is in
the TXT record (Toskar Core's docs/connecting.md)."""

from __future__ import annotations

import concurrent.futures
import ipaddress
import socket
import time
from dataclasses import dataclass, replace
from typing import Any

SERVICE_TYPE = "_localai._tcp.local."


@dataclass(frozen=True)
class Computer:
    """A Toskar Core found on the network."""

    name: str
    node_id: str
    version: str
    address: str
    """The API's host:port, to pair with: the first of ``addresses`` that answers."""
    on_network: bool
    """False when the API answers only on that computer: say to turn on
    Connect a device there, rather than that it's unreachable."""
    addresses: tuple[str, ...] = ()
    """Every host:port the computer advertised. A computer can advertise
    addresses this device can't reach, such as a container network's."""


def _computer(instance: str, addresses: list[str], txt: dict[str, str]) -> Computer | None:
    # The service's own port is for computers pairing with each other; the
    # API's is in api_port.
    try:
        port = int(txt.get("api_port", ""))
    except ValueError:
        return None
    if port <= 0 or not addresses:
        return None
    ips = sorted((ipaddress.ip_address(a) for a in addresses), key=lambda i: i.version)
    ways = tuple(f"[{ip}]:{port}" if ip.version == 6 else f"{ip}:{port}" for ip in ips)
    return Computer(
        name=txt.get("name") or instance,
        node_id=txt.get("node_id", ""),
        version=txt.get("version", ""),
        address=ways[0],
        on_network=txt.get("api_lan") != "false",
        addresses=ways,
    )


def _reachable(addresses: tuple[str, ...]) -> str:
    """The first of ``addresses`` that takes a TCP connection, tried together;
    the first, when none does."""
    if len(addresses) < 2:
        return addresses[0]

    def connects(address: str) -> str | None:
        host, _, port = address.rpartition(":")
        try:
            socket.create_connection((host.strip("[]"), int(port)), timeout=0.7).close()
            return address
        except OSError:
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(addresses)) as pool:
        for done in concurrent.futures.as_completed([pool.submit(connects, a) for a in addresses]):
            if (a := done.result()) is not None:
                return a
    return addresses[0]


def _txt(properties: dict[Any, Any]) -> dict[str, str]:
    def text(v: Any) -> str:
        return v.decode() if isinstance(v, bytes) else "" if v is None else str(v)

    return {text(k): text(v) for k, v in properties.items()}


def discover(timeout: float = 3.0) -> list[Computer]:
    """Browses the network for ``timeout`` seconds and returns the computers
    running Toskar Core that answered, by name. Needs the ``discovery``
    extra: pip install "toskar[discovery]"."""
    try:
        from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
    except ImportError as err:  # pragma: no cover
        raise ImportError('Finding computers on the network needs zeroconf: pip install "toskar[discovery]"') from err

    found: dict[str, Computer] = {}
    zc = Zeroconf()

    class Listener(ServiceListener):
        def add_service(self, zc: Zeroconf, kind: str, name: str) -> None:
            info = zc.get_service_info(kind, name, timeout=int(timeout * 1000))
            if info is None:
                return
            instance = name.removesuffix("." + kind)
            c = _computer(instance, info.parsed_addresses(), _txt(info.properties))
            if c is not None:
                found[c.node_id + c.address] = c

        def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            self.add_service(zc, type_, name)

        def remove_service(self, zc: Zeroconf, kind: str, name: str) -> None:
            pass

    try:
        ServiceBrowser(zc, SERVICE_TYPE, Listener())
        time.sleep(timeout)
    finally:
        zc.close()
    return sorted((replace(c, address=_reachable(c.addresses)) for c in found.values()), key=lambda c: c.name)
