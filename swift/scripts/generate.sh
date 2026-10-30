#!/usr/bin/env bash
# Regenerates the Swift SDK's generated code from spec/: every route and
# type (Sources/ToskarAPI, by swift-openapi-generator), and the error codes
# and contract (Sources/Toskar/Codes.swift). The sync workflow runs it in
# the swift image on Linux:
#
#   docker run --rm -v "$PWD":/w -w /w swift:6.2 swift/scripts/generate.sh
set -euo pipefail
cd "$(dirname "$0")/.."
swift run --package-path generator -c release swift-openapi-generator generate \
  --config generator/openapi-generator-config.yaml \
  --output-directory Sources/ToskarAPI \
  ../spec/openapi.sdk.json >/dev/null
swift scripts/codes.swift
