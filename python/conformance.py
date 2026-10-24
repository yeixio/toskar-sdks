"""Runs the shared conformance cases (conformance/README.md) with the Python SDK."""

from __future__ import annotations

import base64
import hashlib
import json
import sys
import threading
import time
from pathlib import Path
from typing import Any

from toskar import Device, Toskar, ToskarError, pair


def run(args: list[str]) -> Any:
    if len(args) == 3 and args[0] == "pair":
        shown: list[str] = []

        def confirm(short: str) -> bool:
            shown.append(short)
            return True

        device = pair(args[1], args[2], "Python conformance", confirm)
        return {"device": device.to_dict(), "short_pin": shown[0]}
    if len(args) == 2 and args[0] == "call":
        with open(args[1]) as f:
            device = Device.from_dict(json.load(f))
        with Toskar(device=device, retries=0) as toskar:
            settings = toskar.api.get_settings()
            return {"path": toskar.path, "node_name": settings.model_dump().get("node_name")}
    # The rest connect as TOSKAR_URL and TOSKAR_API_KEY say.
    with Toskar(retries=0) as toskar:
        if len(args) == 3 and args[0] == "chat":
            return {"content": toskar.chat(args[2], model_id=args[1]).content}
        if len(args) == 3 and args[0] == "stream":
            content, tokens, done = "", 0, False
            for event in toskar.chat_stream(args[2], model_id=args[1]):
                if event.type == "token":
                    content, tokens = content + event.content, tokens + 1
                elif event.type == "done":
                    done = True
            return {"content": content, "tokens": tokens, "done": done}
        if len(args) == 4 and args[0] == "events":
            return events(toskar, *args[1:])
        if len(args) == 2 and args[0] == "upload":
            path = Path(args[1])
            artifact = toskar.api.upload_artifact(body={"name": path.name, "content_base64": base64.b64encode(path.read_bytes()).decode()})
            return {"id": artifact.id, "name": artifact.name, "size_bytes": artifact.size_bytes}
        if len(args) == 2 and args[0] == "download":
            data = toskar.api.get_artifact_content(args[1])
            return {"sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}
    raise SystemExit(
        "usage: conformance.py pair <address> <code> | call <device.json> | chat|stream <model> <message>"
        " | events <model> <message> <until> | upload <file> | download <id>"
    )


def events(toskar: Toskar, model: str, message: str, until: str) -> Any:
    """Listens to the events stream, asks once, and lists the events' types
    until one of type ``until``."""
    types: list[str] = []
    failed: list[BaseException] = []
    finished = threading.Event()

    def listen() -> None:
        try:
            for event in Toskar(retries=0).events():
                types.append(event.type)
                if event.type == until:
                    break
        except BaseException as e:
            failed.append(e)
        finished.set()

    threading.Thread(target=listen, daemon=True).start()
    # Time to subscribe before asking.
    time.sleep(1)
    toskar.chat(message, model_id=model)
    if not finished.wait(30):
        raise TimeoutError(f"no {until} event")
    if failed:
        raise failed[0]
    return {"types": types}


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
