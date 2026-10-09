#!/bin/sh
# Regression: an absent or untrusted rollback backup must NEVER delete the
# current active release. Uses the real FreeBSD-compatible atomic.sh helpers
# in a temporary directory; no router state or IPFW are touched.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
. "${ROOT}/src/opnsense/scripts/OPNsense/Zapret/backend/atomic.sh"
common_error() { printf '%s\n' "$*" >&2; }
dir=$(mktemp -d /tmp/zapret-voice-rollback.XXXXXX) || exit 1
trap 'rm -rf "${dir}"' EXIT HUP INT TERM
active="${dir}/runtime-v2"
backup="${dir}/backup-runtime"
mkdir -p "${active}"
printf '%s\n' candidate > "${active}/dvtws.args"
assert_candidate() {
    [ -f "${active}/dvtws.args" ] &&
    [ "$(cat "${active}/dvtws.args")" = candidate ] || {
        echo "FAIL: incomplete rollback destroyed active candidate" >&2
        exit 1
    }
}
if atomic_restore_tree "${active}" "${dir}/absent-backup" 2>/dev/null; then
    echo "FAIL: missing backup was accepted" >&2
    exit 1
fi
assert_candidate

mkdir -p "${dir}/original"
printf '%s\n' original > "${dir}/original/dvtws.args"
ln -s "${dir}/original" "${backup}"
if atomic_restore_tree "${active}" "${backup}" 2>/dev/null; then
    echo "FAIL: symlinked rollback backup was accepted" >&2
    exit 1
fi
assert_candidate
[ -f "${dir}/original/dvtws.args" ] || {
    echo "FAIL: symlinked backup target was modified" >&2
    exit 1
}
rm "${backup}"
mkdir "${backup}"
cp "${dir}/original/dvtws.args" "${backup}/dvtws.args"
atomic_restore_tree "${active}" "${backup}" || {
    echo "FAIL: valid saved runtime failed to restore" >&2
    exit 1
}
[ "$(cat "${active}/dvtws.args")" = original ] || {
    echo "FAIL: valid rollback returned incorrect runtime" >&2
    exit 1
}
[ ! -e "${backup}" ] || {
    echo "FAIL: restore left old backup behind" >&2
    exit 1
}
echo "PASS: missing/symlinked backup preserves active runtime, valid rollback restores previous"
