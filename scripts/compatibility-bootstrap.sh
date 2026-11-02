#!/bin/sh
# Read-only, Python-independent diagnostic for the earliest usable boundary.
# Does NOT read a future installed compatibility manifest or admit platform ABI.
# The native builder subsequently performs the authoritative policy match.
set -eu
if [ ! -x /usr/local/bin/python3 ]; then
    echo 'COMPATIBILITY=REFUSED:GENERIC_PYTHON3_MISSING_OR_NOT_EXECUTABLE' >&2
    exit 2
fi
if ! command -v pkg >/dev/null 2>&1; then
    echo 'COMPATIBILITY=REFUSED:PKG_COMMAND_MISSING' >&2
    exit 2
fi
if ! command -v opnsense-version >/dev/null 2>&1; then
    echo 'COMPATIBILITY=REFUSED:OPNSENSE_IDENTITY_COMMAND_MISSING' >&2
    exit 2
fi
echo 'COMPATIBILITY=PASS_BOOTSTRAP_TOOLS_PRESENT_NOT_PLATFORM_ADMISSION'
