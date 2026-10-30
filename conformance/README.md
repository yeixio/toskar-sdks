# Conformance

Every SDK has a small program that runs the same cases, so a test bed can
run each one and check what it did. Two do:

- `conformance/run.py` runs every case against a throwaway Toskar Core,
  which chats with a scripted model, so it needs no model: chat,
  streaming, events, files, errors, and pairing with a pinned
  certificate. CI runs it on every pull request and each night against
  toskar-core main (`.github/workflows/conformance.yml`).
- Toskar Core's outside-network check runs them as devices at home and
  away from home, with a real router and a real relay (toskar-core
  `tests/outside`).

Run the cases locally with a Core build (`go build ./cmd/daemon` in
toskar-core) after building the SDKs:

```sh
python3 conformance/run.py --core ../toskar-core/daemon \
  --program go=go/toskar-conformance \
  --program "python=python/.venv/bin/python python/conformance.py" \
  --program "node=node typescript/conformance.mjs" \
  --program kotlin=kotlin/conformance/build/install/toskar-conformance/bin/toskar-conformance
```

| SDK | Program | In the image |
|---|---|---|
| Go | `go/cmd/toskar-conformance` | `toskar-conformance-go` |
| Python | `python/conformance.py` | `toskar-conformance-python` |
| TypeScript | `typescript/conformance.mjs`, after `npm run build` | `toskar-conformance-node` |
| Kotlin | `kotlin/conformance`, `./gradlew :conformance:installDist` | `toskar-conformance-kotlin` |
| Swift | `swift build --product toskar-conformance`, on a Mac | — |

Swift's pinning uses Apple's Security framework, so its program runs on
a Mac, in the conformance workflow's `swift` job, and isn't in the image.
Build the image with the other four from the repository root:

```sh
docker build -f conformance/Dockerfile -t toskar-conformance .
```

## Commands

Each prints one line of JSON and exits 0, or prints
`{"error": {"code", "message"}}` and exits 1. `code` is Toskar's error code
(such as `PAIRING_WRONG_CODE`) or the SDK's own: `PIN_MISMATCH`,
`NOT_CONFIRMED`, `UNREACHABLE`, `NO_RECORD`, or `ERROR` for anything else.

`pair <address> <code>` pairs with the computer at `address` (host:port)
using the code Connect a device shows, confirming the short pin, and
prints:

```json
{"device": {"address": "…", "api_key": "…", "pin": "sha256:…", "route": {"secret": "…", "id": "…", "relay": "…", "token": "…"}}, "short_pin": "ABCD-1234"}
```

`call <device.json>` connects as the device in the file (the `device`
from `pair`) and asks for the computer's settings, then prints the way
in it took (`home`, `direct`, or `relay`) and the computer that answered:

```json
{"path": "relay", "node_name": "Studio"}
```

The rest connect as `TOSKAR_URL` and `TOSKAR_API_KEY` say:

- `chat <model> <message>` prints `{"content"}`, the whole answer.
- `stream <model> <message>` prints `{"content", "tokens", "done"}`: the tokens joined, how many there were, and whether the stream ended with done.
- `events <model> <message> <type>` listens to the events stream, asks, and prints `{"types"}`, every event's type up to the first of `type`.
- `upload <file>` prints the file Core keeps: `{"id", "name", "size_bytes"}`.
- `download <id>` prints `{"sha256", "size_bytes"}` of the file's content.

The relay's own certificate is checked as any website's is: a test bed
with its own certificate authority sets `SSL_CERT_FILE` (Go, Python, Kotlin) and
`NODE_EXTRA_CA_CERTS` (Node).
