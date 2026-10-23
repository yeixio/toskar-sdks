#!/usr/bin/env bash
# Copies Toskar Core's API spec and error codes at a git ref (a release tag,
# or a commit) into spec/, then writes the SDKs' normalized spec.
#
#   scripts/sync-spec.sh v1.11.0
set -euo pipefail
ref="${1:?usage: scripts/sync-spec.sh <core tag or commit>}"
root="$(cd "$(dirname "$0")/.." && pwd)"
raw="https://raw.githubusercontent.com/yeixio/toskar-core/$ref"
curl -fsSL "$raw/api/openapi.yaml" -o "$root/spec/openapi.yaml"
curl -fsSL "$raw/i18n/locales/en/errors.json" -o "$root/spec/errors.json"
sha="$(gh api "repos/yeixio/toskar-core/commits/$ref" --jq .sha)"
printf 'ref: %s\ncommit: %s\n' "$ref" "$sha" > "$root/spec/SOURCE"
node "$root/scripts/normalize-spec.mjs"
