"""Runs the shared conformance cases against a throwaway Toskar Core, with
every SDK's conformance program, and checks each answers the same.

    python3 conformance/run.py --core <toskar daemon> \\
        --program go=go/toskar-conformance \\
        --program "python=python/.venv/bin/python python/conformance.py" \\
        --program "node=node typescript/conformance.mjs"

Core chats with a scripted model: an OpenAI-compatible server here that
answers "You said: <message>", a word at a time when streaming. Keep the
messages short: a long one makes Core plan, and the model then echoes
the plan's prompts too. So the
cases need no model, and their answers are known. Standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

MODEL = "ext:echo"
NODE_NAME = "conformance"


class ScriptedModel(BaseHTTPRequestHandler):
    """An OpenAI-compatible server with one model, echo."""

    def log_message(self, *args: Any) -> None:
        pass

    def _json(self, body: Any) -> None:
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        self._json({"object": "list", "data": [{"id": "echo", "object": "model", "owned_by": "conformance"}]})

    def do_POST(self) -> None:
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        last = [m for m in req["messages"] if m["role"] == "user"][-1]["content"]
        if isinstance(last, list):
            last = " ".join(p.get("text", "") for p in last if isinstance(p, dict))
        text = "You said: " + last
        usage = {"prompt_tokens": 3, "completion_tokens": len(text.split()), "total_tokens": 3 + len(text.split())}
        if not req.get("stream"):
            message = {"role": "assistant", "content": text}
            self._json({"id": "c", "object": "chat.completion", "created": 0, "model": "echo",
                        "choices": [{"index": 0, "message": message, "finish_reason": "stop"}], "usage": usage})
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        words = text.split(" ")
        for i, word in enumerate(words):
            piece = word if i == len(words) - 1 else word + " "
            self._chunk({"delta": {"content": piece}, "finish_reason": None})
            time.sleep(0.02)
        self._chunk({"delta": {}, "finish_reason": "stop"}, usage)
        self.wfile.write(b"data: [DONE]\n\n")

    def _chunk(self, choice: dict[str, Any], usage: dict[str, int] | None = None) -> None:
        body: dict[str, Any] = {"id": "c", "object": "chat.completion.chunk", "created": 0, "model": "echo",
                                "choices": [{"index": 0, **choice}]}
        if usage:
            body["usage"] = usage
        self.wfile.write(f"data: {json.dumps(body)}\n\n".encode())
        self.wfile.flush()


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class Core:
    """A throwaway Toskar Core on loopback, with a data folder of its own."""

    def __init__(self, binary: str, data: Path) -> None:
        self.binary = binary
        self.port = free_port()
        self.url = f"http://127.0.0.1:{self.port}"
        env = {**os.environ, "TOSKAR_API_PORT": str(self.port), "TOSKAR_DISCOVERY_ENABLED": "false", "TOSKAR_NODE_NAME": NODE_NAME}
        # Its own node port too, so a Core already on this computer isn't disturbed.
        env["TOSKAR_INTERNAL_PORT"] = str(free_port())
        self.log = open(data / "core.log", "w")
        self.proc = subprocess.Popen([binary, "-data-dir", str(data / "core")], env=env, stdout=self.log, stderr=subprocess.STDOUT)
        deadline = time.time() + 60
        while time.time() < deadline:
            try:
                self.api("GET", "/api/v1/health")
                return
            except OSError:
                if self.proc.poll() is not None:
                    break
                time.sleep(0.3)
        self.stop()
        raise SystemExit(f"Core didn't start; its log:\n{(data / 'core.log').read_text()[-4000:]}")

    def api(self, method: str, path: str, body: Any = None) -> Any:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.url + path, data=data, method=method, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read() or b"null")

    def stop(self) -> None:
        self.proc.terminate()
        try:
            self.proc.wait(10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.log.close()


class Program:
    def __init__(self, name: str, command: str, env: dict[str, str]) -> None:
        self.name, self.command, self.env = name, shlex.split(command), env

    def __call__(self, *args: str) -> dict[str, Any]:
        r = subprocess.run([*self.command, *args], env=self.env, capture_output=True, text=True, timeout=120)
        lines = r.stdout.strip().splitlines()
        try:
            out: dict[str, Any] = json.loads(lines[-1])
        except (IndexError, json.JSONDecodeError):
            raise AssertionError(f"no JSON from {' '.join(args)}: exit {r.returncode}\n{r.stdout}{r.stderr}") from None
        if (r.returncode == 0) == ("error" in out):
            raise AssertionError(f"exit {r.returncode} with {out}")
        return out


def expect(ok: bool, what: str, got: Any) -> None:
    if not ok:
        raise AssertionError(f"{what}; got {json.dumps(got)}")


# The cases. Each takes the program, Core, and a folder of its own.

def chat(p: Program, core: Core, work: Path) -> None:
    out = p("chat", MODEL, "hello there")
    expect(out == {"content": "You said: hello there"}, "the whole answer", out)


def stream(p: Program, core: Core, work: Path) -> None:
    out = p("stream", MODEL, "one two three")
    expect(out.get("content") == "You said: one two three", "the tokens, joined, are the answer", out)
    # Core may hold a short answer back and send it as one token.
    expect(out.get("tokens", 0) >= 1 and out.get("done") is True, "tokens, then done", out)


def events(p: Program, core: Core, work: Path) -> None:
    out = p("events", MODEL, "ping", "chat.complete")
    types = out.get("types", [])
    expect("chat.token" in types and types[-1] == "chat.complete" and types.index("chat.token") < len(types) - 1,
           "the chat's tokens, then chat.complete, on the events stream", out)


def files(p: Program, core: Core, work: Path) -> None:
    content = "Héllo, wörld ✓\nA second line.\n".encode()
    path = work / "notes.txt"
    path.write_bytes(content)
    up = p("upload", str(path))
    expect(up.get("name") == "notes.txt" and up.get("size_bytes") == len(content) and up.get("id"), "the uploaded file", up)
    down = p("download", up["id"])
    expect(down == {"sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content)}, "the same bytes back", down)


def errors(p: Program, core: Core, work: Path) -> None:
    out = p("download", "no-such-file")
    expect(out.get("error", {}).get("code") == "FILE_NOT_FOUND", "Toskar's error code", out)


def pairing(p: Program, shared: Core, work: Path) -> None:
    # A Core of its own: Core blocks a source after 5 wrong codes, and every
    # program pairs from 127.0.0.1.
    core = Core(shared.binary, work)
    try:
        pair_with(p, core, work)
    finally:
        core.stop()


def pair_with(p: Program, core: Core, work: Path) -> None:
    address = f"127.0.0.1:{core.port}"
    started = core.api("POST", "/api/v1/devices/pairing", {})
    wrong = "000000" if started["code"] != "000000" else "111111"
    out = p("pair", address, wrong)
    expect(out.get("error", {}).get("code") == "PAIRING_WRONG_CODE", "a wrong code is refused", out)
    out = p("pair", address, started["code"])
    expect(out.get("short_pin") == started["tls_short"], "the short pin the computer shows", out)
    device = out["device"]
    (work / "device.json").write_text(json.dumps(device))
    out = p("call", str(work / "device.json"))
    expect(out == {"path": "home", "node_name": NODE_NAME}, "the paired device reaches its computer", out)
    (work / "other.json").write_text(json.dumps({**device, "pin": "sha256:" + "ab" * 32}))
    out = p("call", str(work / "other.json"))
    expect(out.get("error", {}).get("code") == "PIN_MISMATCH", "another certificate is refused", out)


CASES: list[tuple[str, Callable[[Program, Core, Path], None]]] = [
    ("chat", chat), ("stream", stream), ("events", events), ("files", files), ("errors", errors), ("pairing", pairing),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--core", required=True, help="the Toskar Core daemon to run")
    ap.add_argument("--program", action="append", required=True, metavar="NAME=COMMAND", help="an SDK's conformance program")
    ap.add_argument("--case", action="append", help="run only these cases")
    args = ap.parse_args()

    model = ThreadingHTTPServer(("127.0.0.1", 0), ScriptedModel)
    threading.Thread(target=model.serve_forever, daemon=True).start()
    with tempfile.TemporaryDirectory(prefix="toskar-conformance-") as tmp:
        core = Core(args.core, Path(tmp))
        failed = 0
        try:
            core.api("PUT", "/api/v1/external-server", {"base_url": f"http://127.0.0.1:{model.server_address[1]}/v1"})
            env = {**os.environ, "TOSKAR_URL": core.url}
            env.pop("TOSKAR_API_KEY", None)
            for spec in args.program:
                name, _, command = spec.partition("=")
                program = Program(name, command, env)
                for case, run in CASES:
                    if args.case and case not in args.case:
                        continue
                    work = Path(tmp) / name / case
                    work.mkdir(parents=True)
                    started = time.time()
                    try:
                        run(program, core, work)
                        print(f"ok   {name:8} {case:10} {time.time() - started:5.1f}s")
                    except Exception as e:
                        failed += 1
                        print(f"FAIL {name:8} {case:10} {e}")
        finally:
            core.stop()
            model.shutdown()
        if failed:
            print(f"Core's log ends:\n{(Path(tmp) / 'core.log').read_text()[-3000:]}", file=sys.stderr)
    print(f"{failed} failed" if failed else "all passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
