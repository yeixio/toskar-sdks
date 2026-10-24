import socket

from toskar._discover import _computer, _reachable, _txt


def test_reads_where_the_api_is():
    txt = _txt({b"node_id": b"n1", b"name": b"Studio", b"version": b"1.11.0", b"api_port": b"7331", b"api_lan": b"true"})
    c = _computer("studio", ["fe80::1", "192.168.1.20"], txt)
    assert (c.name, c.address, c.on_network, c.version) == ("Studio", "192.168.1.20:7331", True, "1.11.0")
    c = _computer("studio", ["fe80::1"], {"node_id": "n2", "api_port": "7331", "api_lan": "false"})
    assert (c.name, c.address, c.on_network) == ("studio", "[fe80::1]:7331", False)
    assert _computer("studio", ["192.168.1.20"], {"node_id": "n3"}) is None


def test_prefers_an_address_that_answers():
    with socket.create_server(("127.0.0.1", 0)) as server:
        here = f"127.0.0.1:{server.getsockname()[1]}"
        # 10.255.255.1 stands for an address that doesn't route from here, such as a container network's.
        assert _reachable(("10.255.255.1:7331", here)) == here
