#!/bin/sh
# Single official OPNsense Mk/plugins.mk build entrypoint.
# Stage 2 safety: accepts only qualified isolated OPNsense CI; no publishing
# or installing candidate packages. Output contract: dist/os-zapret2-restyle-<version>[_revision].pkg
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
[ "$#" -eq 0 ] || { echo "ERROR: usage: sh scripts/build-pkg.sh" >&2; exit 2; }
[ "${ZAPRET2_NATIVE_BUILD_CI:-}" = 1 ] || {
    echo "ERROR: official native builder requires isolated OPNsense CI opt-in" >&2
    exit 2
}
[ -x /usr/local/bin/python3 ] || {
    echo "ERROR: target OPNsense-managed generic python3 is unavailable" >&2
    exit 2
}
exec /usr/local/bin/python3 "$ROOT/scripts/native-opnsense-package.py"
