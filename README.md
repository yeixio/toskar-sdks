# Toskar SDKs

Official packages for building on [Toskar](https://toskar.ai): local AI that runs across your own computers, with one API for chat, models, knowledge, automations, files, and events.

| Language | Package | Folder | Status |
| --- | --- | --- | --- |
| TypeScript and JavaScript | `toskar` on npm | [typescript/](typescript) | Preview |
| Python | `toskar` on PyPI | [python/](python) | Preview |
| Go | `github.com/yeixio/toskar-sdks/go` | [go/](go) | Preview |
| Swift | `https://github.com/yeixio/toskar-sdks`, product `Toskar` | [swift/](swift) | Preview |
| Kotlin and Java | `ai.toskar:toskar` (Maven Central soon) | [kotlin/](kotlin) | Preview |
| Rust | `toskar` (crates.io soon) | [rust/](rust) | Preview |
| C#/.NET | | | Later |

Docs: [toskar.ai/developers](https://toskar.ai/developers), and the [reference](reference/README.md) for every class and function.

## How they're made

Each SDK is generated from Toskar Core's API spec, [`api/openapi.yaml`](https://github.com/yeixio/toskar-core/blob/main/api/openapi.yaml), with a small hand-written layer for what generators do badly: streaming chat and the events stream, typed errors, retries, and timeouts.

- **The spec stays honest.** Core's tests check every response they see against it, and every named schema against the Go type it stands for. A route can't fall out of the spec.
- **[`spec/`](spec)** is the copy the SDKs are generated from. `SOURCE` names the core release or commit, and `errors.json` holds the stable error codes. `openapi.sdk.json` is the spec with each enum's values moved into its description: the client contract may add values in a minor version, and an SDK must accept a value it doesn't know yet.
- **The snippets work.** CI type-checks every code snippet in the READMEs against its SDK (Swift's on a Mac, Kotlin and Java's with Gradle, Rust's with cargo), and runs the ones marked `<!-- snippet: run -->` against a throwaway Core (`scripts/check_snippets.py`). Toskar Core's examples run with each change too.
- **`scripts/sync-spec.sh <core tag>`** syncs it. The `sync` workflow does that each day and opens a pull request when Core has a newer release.

## Versions

Releases: [RELEASING.md](RELEASING.md). One tag publishes every SDK at one version.

Each SDK release names the client contract it was built for (`CONTRACT_VERSION`, now 1.59) and sends it as `Toskar-Client-Contract`. Toskar Core answers `426 CONTRACT_MISMATCH` to a client built for another major version. A Core with an older minor version may lack newer routes and fields.

## License

Apache 2.0. Toskar Core itself is AGPL-3.0; these client packages are Apache 2.0 so you can use them in any app.
