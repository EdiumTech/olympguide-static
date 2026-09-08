#!/bin/sh
set -eu

IOS_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
APP_DIR="$IOS_DIR/olympguide/Application"
TEST_DIR=$(mktemp -d "${TMPDIR:-/tmp}/olympguide-network.XXXXXX")
trap 'rm -f "$TEST_DIR/network-tests"; rmdir "$TEST_DIR"' EXIT

swiftc -swift-version 5 \
    "$APP_DIR/Network/APIConfiguration.swift" \
    "$APP_DIR/Network/HTTPResponseDecoder.swift" \
    "$APP_DIR/Errors/NetworkError.swift" \
    "$APP_DIR/Models/ResponseModels/BaseServerResponse.swift" \
    "$APP_DIR/Models/ResponseModels/Benefits/BenefitModel.swift" \
    "$APP_DIR/Models/ResponseModels/Programs/ProgramShortModel.swift" \
    "$APP_DIR/Models/ViewModels/Programs/ProgramViewModel.swift" \
    "$IOS_DIR/tests/network/main.swift" \
    -o "$TEST_DIR/network-tests"
"$TEST_DIR/network-tests"
