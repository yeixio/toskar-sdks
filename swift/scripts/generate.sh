#!/usr/bin/env bash
# Regenerates the Swift SDK's generated code from spec/: every route and
# type (Sources/ToskarAPI, by swift-openapi-generator), and the error codes
# and contract (Sources/Toskar/Codes.swift). The sync workflow runs it in
# the swift image on Linux:
#
#   docker run --rm -v "$PWD":/w -w /w -e SWIFT_SCRATCH=/tmp/swift-generator swift:6.2 swift/scripts/generate.sh
#
# SWIFT_SCRATCH keeps the generator's build out of the checkout: the image
# runs as root, and a root-owned .build there breaks that runner's next
# checkout, for every job.
set -euo pipefail
cd "$(dirname "$0")/.."
swift run --package-path generator ${SWIFT_SCRATCH:+--scratch-path "$SWIFT_SCRATCH"} -c release swift-openapi-generator generate \
  --config generator/openapi-generator-config.yaml \
  --output-directory Sources/ToskarAPI \
  ../spec/openapi.sdk.json >/dev/null
swift scripts/codes.swift
