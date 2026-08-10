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
    FreeBSD)
        # Strategy Lab historically uses the BSD shorthand `ax` for an all-process
        # command listing.  This wrapper already owns FreeBSD's `-xww` selection/output
        # flags, and mixing that dashed form with a later bare `ax` is rejected by
        # FreeBSD ps.  Normalize only that legacy leading selector at this platform
        # boundary; all other caller arguments remain untouched.
        if [ "${1:-}" = ax ]; then
            shift
            set -- -A "$@"
        fi
        exec "${ZAPRET_NATIVE_PS_BIN}" -xww "$@"
        ;;
    *) exec "${ZAPRET_NATIVE_PS_BIN}" "$@" ;;
esac
