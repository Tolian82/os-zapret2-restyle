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

# Simulate the failure of the critical backup -> active rename AFTER the
# current candidate has been parked. This must not strand or delete either.
if (
    mv() {
        if [ "$1" = "${backup}" ] && [ "$2" = "${active}" ]; then
            return 1
        fi
        command mv "$@"
    }
    atomic_restore_tree "${active}" "${backup}" 2>/dev/null
); then
    echo "FAIL: deliberately failed backup move unexpectedly succeeded" >&2
    exit 1
fi
assert_candidate
[ -f "${backup}/dvtws.args" ] || {
    echo "FAIL: backup was lost on failed rename" >&2
    exit 1
}
[ ! -e "${active}.rollback-old.$$" ] || {
    echo "FAIL: candidate remained stranded in rollback parking path" >&2
    exit 1
}

# An unknown pre-existing parked release must not be erased or overwritten.
park="${active}.rollback-old.$$"
mkdir "${park}"
printf '%s\n' sentinel > "${park}/keep"
if atomic_restore_tree "${active}" "${backup}" 2>/dev/null; then
    echo "FAIL: conflicting parked runtime was overwritten" >&2
    exit 1
fi
assert_candidate
[ "$(cat "${park}/keep")" = sentinel ] || {
    echo "FAIL: parked unknown runtime was modified" >&2
    exit 1
}
rm -rf "${park}"

# A crash leftover from another process and an old literal-$ park
# must not block PID-scoped rollback or be modified.
literal_park="${active}.rollback-old.$"
mkdir "${literal_park}"
printf '%s\n' old-literal-park > "${literal_park}/keep"
old_park="${active}.rollback-old.999999999"
mkdir "${old_park}"
printf '%s\n' abandoned > "${old_park}/keep"

atomic_restore_tree "${active}" "${backup}" || {
    echo "FAIL: valid saved runtime failed to restore" >&2
    exit 1
}
[ "$(cat "${active}/dvtws.args")" = original ] || {
    echo "FAIL: valid rollback returned incorrect runtime" >&2
    exit 1
}
[ "$(cat "${literal_park}/keep")" = old-literal-park ] || {
    echo "FAIL: old fixed-dollar park was modified or blocked rollback" >&2
    exit 1
}
[ "$(cat "${old_park}/keep")" = abandoned ] || {
    echo "FAIL: stale foreign park path was overwritten or deleted" >&2
    exit 1
}
[ ! -e "${active}.rollback-old.$$" ] || {
    echo "FAIL: successful rollback left a current-process parking tree" >&2
    exit 1
}
[ ! -e "${backup}" ] || {
    echo "FAIL: restore left old backup behind" >&2
    exit 1
}

# Existing staging/park/backup paths can be crash evidence after PID reuse.
# Verify the real installer refuses without invoking pax/copy.
source="${dir}/install-source"
destination="${dir}/install-destination"
backup_root="${dir}/install-backup-root"
mkdir -p "${source}" "${destination}" "${backup_root}"
printf '%s\n' proposed > "${source}/dvtws.args"
printf '%s\n' installed > "${destination}/dvtws.args"
assert_install_intact() {
    [ "$(cat "${source}/dvtws.args")" = proposed ] &&
    [ "$(cat "${destination}/dvtws.args")" = installed ] || {
        echo "FAIL: atomic install conflict changed source or active runtime" >&2
        exit 1
    }
}
stage="${dir}/.install-destination.stage.$$"
old="${dir}/.install-destination.old.$$"
mkdir "${stage}"
printf '%s\n' crash > "${stage}/keep"
if atomic_install_tree "${source}" "${destination}" "${backup_root}" 2>/dev/null; then
    echo "FAIL: existing staging directory accepted" >&2; exit 1
fi
assert_install_intact
[ "$(cat "${stage}/keep")" = crash ] || {
    echo "FAIL: staging crash evidence deleted" >&2; exit 1
}
rm -rf "${stage}"
mkdir "${old}"
printf '%s\n' crash > "${old}/keep"
if atomic_install_tree "${source}" "${destination}" "${backup_root}" 2>/dev/null; then
    echo "FAIL: parked previous runtime accepted" >&2; exit 1
fi
assert_install_intact
[ "$(cat "${old}/keep")" = crash ] || {
    echo "FAIL: previous runtime crash evidence deleted" >&2; exit 1
}
rm -rf "${old}"
# Freeze date only in this subshell so expected backup collision is exact.
if (
    date() { echo 20300101-000000; }
    occupied="${backup_root}/install-destination-20300101-000000-$$"
    mkdir "${occupied}"
    printf '%s\n' foreign > "${occupied}/keep"
    if atomic_install_tree "${source}" "${destination}" "${backup_root}" 2>/dev/null; then
        echo "FAIL: pre-existing backup name was accepted" >&2; exit 1
    fi
    [ "$(cat "${occupied}/keep")" = foreign ]
); then :; else
    echo "FAIL: backup collision evidence was overwritten" >&2; exit 1
fi
assert_install_intact

echo "PASS: atomic rollback and install preserve unknown crash artifacts"
