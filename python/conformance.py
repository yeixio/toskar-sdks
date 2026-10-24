"""Runs the shared conformance cases (conformance/README.md) with the Python SDK."""

from __future__ import annotations

import json
import sys
from typing import Any

from toskar import Device, Toskar, ToskarError, pair


def run(args: list[str]) -> Any:
    if len(args) == 3 and args[0] == "pair":
        shown: list[str] = []
        device = pair(args[1], args[2], "Python conformance", lambda short: shown.append(short) or True)
        return {"device": device.to_dict(), "short_pin": shown[0]}
    if len(args) == 2 and args[0] == "call":
        with open(args[1]) as f:
            device = Device.from_dict(json.load(f))
        with Toskar(device=device, retries=0) as toskar:
            settings = toskar.api.get_settings()
            return {"path": toskar.path, "node_name": settings.node_name}
    raise SystemExit("usage: conformance.py pair <address> <code> | call <device.json>")


def main() -> None:
    try:
        out = run(sys.argv[1:])
    except ToskarError as e:
        print(json.dumps({"error": {"code": e.code, "message": str(e)}}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": {"code": "ERROR", "message": repr(e)}}))
        sys.exit(1)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
