#!/bin/sh

set -eu

ZAPRET_NATIVE_PS_BIN="${ZAPRET_NATIVE_PS_BIN:-/bin/ps}"
[ -x "${ZAPRET_NATIVE_PS_BIN}" ] || exit 1

if [ -n "${ZAPRET_PROCESS_QUERY_SYSTEM:-}" ]; then
    _zapret_process_query_system="${ZAPRET_PROCESS_QUERY_SYSTEM}"
else
    _zapret_process_query_system=$(uname -s)
fi

case "${_zapret_process_query_system}" in
    FreeBSD) exec "${ZAPRET_NATIVE_PS_BIN}" -xww "$@" ;;
    *) exec "${ZAPRET_NATIVE_PS_BIN}" "$@" ;;
esac
