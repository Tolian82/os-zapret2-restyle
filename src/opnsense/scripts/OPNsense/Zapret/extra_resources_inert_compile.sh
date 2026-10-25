#!/bin/sh
# Privileged internal Stage-2 read-only compiler. Called only from the root
# native setup.lock -> original FD9 -> Config flock saved-input route.
# No service dispatch, configctl reload, Stop/Start, kernel or active runtime.
# Compiler inputs (including upstream-only Lua/BIN and native rendered Config)
# are separate copies in an exclusively owned ephemeral workspace.
set -eu
[ "$#" -eq 6 ] || exit 64
_NATIVE_TEMPLATE="$1"
_NATIVE_UPSTREAM="$2"
_NATIVE_XML="$3"
_NATIVE_ACTIVE="$4"
_NATIVE_WORK="$5"
_NATIVE_RELEASE="$6"
case "$_NATIVE_TEMPLATE:$_NATIVE_UPSTREAM:$_NATIVE_XML:$_NATIVE_ACTIVE:$_NATIVE_WORK:$_NATIVE_RELEASE" in
    /*) ;;
    *) echo "ERROR: native prospective candidate requires absolute paths" >&2; exit 69 ;;
esac

_SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
BACKEND_DIR="$_SCRIPT_DIR/backend"
for _native_module in \
    common config parser registry storage targets target_mode \
    profile_normalizer profile_pipeline exclude blobs ports generator \
    validator stage orchestrator
do
    [ -r "$BACKEND_DIR/$_native_module.sh" ] || exit 69
    . "$BACKEND_DIR/$_native_module.sh"
done

# Shared candidate is the authoritative common compiler, even when all
# Voice services are disabled. It does not activate or persist the output.
# Engine execution/Lua export proof is explicitly a SEPARATE required gate.
orchestrator_build_release \
    "$_NATIVE_TEMPLATE" "$_NATIVE_UPSTREAM" "$_NATIVE_ACTIVE" \
    "$_NATIVE_WORK" "$_NATIVE_RELEASE" "$_NATIVE_WORK/stages" \
    shared-candidate "$_NATIVE_XML"
