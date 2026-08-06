#!/bin/sh

set -eu

ZAPRET_NATIVE_PS_BIN="${ZAPRET_NATIVE_PS_BIN:-/bin/ps}"
[ -x "${ZAPRET_NATIVE_PS_BIN}" ] || exit 1

exec "${ZAPRET_NATIVE_PS_BIN}" -xww "$@"
