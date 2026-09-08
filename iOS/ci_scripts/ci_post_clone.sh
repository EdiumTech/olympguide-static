#!/bin/sh
set -eu

# Xcode must read this file before resolving build settings, not in a build phase.
IOS_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

: "${GOOGLE_CLIENT_ID:?Set GOOGLE_CLIENT_ID in the Xcode Cloud workflow}"
: "${GOOGLE_CLIENT_REVERSED_ID:?Set GOOGLE_CLIENT_REVERSED_ID in the Xcode Cloud workflow}"

# OAuth client identifiers must remain a single xcconfig value.
case "$GOOGLE_CLIENT_ID$GOOGLE_CLIENT_REVERSED_ID" in
    *[!a-zA-Z0-9._-]*)
        echo "Invalid Google client identifier format." >&2
        exit 1
        ;;
esac

mkdir -p "$IOS_DIR/Config"
umask 077
{
    printf '%s\n' '// Generated before the Xcode Cloud build. Do not commit local values.'
    printf 'GOOGLE_CLIENT_ID = %s\n' "$GOOGLE_CLIENT_ID"
    printf 'GOOGLE_CLIENT_REVERSED_ID = %s\n' "$GOOGLE_CLIENT_REVERSED_ID"
} > "$IOS_DIR/Config/Secrets.xcconfig"

# BASE_URL comes from the versioned App.xcconfig, including in Xcode Cloud.
echo "OAuth configuration prepared. API configuration: Config/App.xcconfig."
