#!/bin/sh
# Unified fail-closed Python resolver. No generic python3 symlink is assumed.
# Usage: python_runtime.sh --resolve | python_runtime.sh --exec SCRIPT [args...]
set -eu
RUNTIME_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 69
COMPAT="${RUNTIME_DIR}/python_runtime.conf"
[ -f "$COMPAT" ] && [ -r "$COMPAT" ] || {
    echo 'ERROR: Python runtime compatibility manifest is missing' >&2
    exit 69
}
. "$COMPAT"
case "$ZAPRET_PYTHON_MAJOR:$ZAPRET_PYTHON_MIN_MINOR" in
    *[!0-9:]*|:*|*:) echo 'ERROR: invalid Python compatibility manifest' >&2; exit 69 ;;
esac
[ "$ZAPRET_PYTHON_MAJOR" = 3 ] && [ "$ZAPRET_PYTHON_MIN_MINOR" -ge 0 ] || {
    echo 'ERROR: unsupported Python compatibility manifest' >&2
    exit 69
}
[ "$#" -ge 1 ] || { echo 'ERROR: Python launcher mode is required' >&2; exit 64; }
mode=$1
case "$mode" in
    --resolve) [ "$#" -eq 1 ] || exit 64 ;;
    --exec) [ "$#" -ge 2 ] || exit 64; shift; [ -r "$1" ] || exit 66 ;;
    *) echo 'ERROR: unsupported Python launcher mode' >&2; exit 64 ;;
esac
runtime_valid()
{
    [ -f "$1" ] && [ -x "$1" ] &&
    "$1" -c 'import sys; x=sys.version_info; sys.exit(0 if x.major == int(sys.argv[1]) and x.minor >= int(sys.argv[2]) else 1)' \
        "$ZAPRET_PYTHON_MAJOR" "$ZAPRET_PYTHON_MIN_MINOR" >/dev/null 2>&1
}
python_bin=
if [ "${ZAPRET_PYTHON_BIN+x}" = x ]; then
    candidate=$ZAPRET_PYTHON_BIN
    # Explicit override is for controlled testing only and must be absolute.
    case "$candidate" in /*) ;; *) echo 'ERROR: Python override must be an absolute path' >&2; exit 69 ;; esac
    runtime_valid "$candidate" || { echo 'ERROR: overridden Python runtime is incompatible' >&2; exit 69; }
    python_bin=$candidate
else
    # Prefer a canonical generic path when it exists, then installed minor paths.
    # An unmatched POSIX glob is harmlessly rejected by -f.
    for candidate in /usr/local/bin/python3 /usr/local/bin/python3.[0-9]*; do
        if runtime_valid "$candidate"; then
            python_bin=$candidate
            break
        fi
    done
fi
[ -n "$python_bin" ] || { echo 'ERROR: no compatible installed Python runtime found' >&2; exit 69; }
case "$mode" in
    --resolve) printf '%s\n' "$python_bin" ;;
    --exec) exec "$python_bin" "$@" ;;
esac
