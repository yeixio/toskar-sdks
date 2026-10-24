#!/usr/bin/env bash
# Sets every SDK's version, for a release: the npm and PyPI packages, and
# (from the release tag) the Go module's go/vX.Y.Z tag. See RELEASING.md.
#
#   scripts/set-version.sh 0.2.0
set -euo pipefail
version="${1:?usage: scripts/set-version.sh <version, such as 0.2.0>}"
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$ ]] || { echo "not a version: $version" >&2; exit 2; }
root="$(cd "$(dirname "$0")/.." && pwd)"
(cd "$root/typescript" && npm version "$version" --no-git-tag-version --allow-same-version >/dev/null)
sed -i.bak -E "s/^version = \".*\"/version = \"$version\"/" "$root/python/pyproject.toml" && rm "$root/python/pyproject.toml.bak"
echo "TypeScript $(node -p "require('$root/typescript/package.json').version"), Python $(sed -n -E 's/^version = "(.*)"/\1/p' "$root/python/pyproject.toml")"
