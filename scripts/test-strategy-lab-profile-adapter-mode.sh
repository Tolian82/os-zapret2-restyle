#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
WRAPPER="${STRATEGY_LAB_PROFILE_WRAPPER_UNDER_TEST:-${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_profile_candidate_adapter.sh}"
fail(){ echo "FAIL: $*" >&2; exit 1; }

[ -f "${WRAPPER}" ] || fail 'profile candidate wrapper is unavailable'
sh -n "${WRAPPER}" || fail 'profile candidate wrapper shell syntax is invalid'

TMP=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-profile-adapter-mode.XXXXXX")
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
BASE="${TMP}/base-adapter.sh"
cat > "${BASE}" <<'MOCK'
#!/bin/sh
printf '%s\n' "$*" >> "${STAGE85_MOCK_LOG}"
MOCK
chmod 0644 "${BASE}"
[ -f "${BASE}" ] && [ -r "${BASE}" ] && [ ! -x "${BASE}" ] ||
    fail 'fixture base adapter must be readable but non-executable'

: > "${TMP}/calls"
STAGE85_MOCK_LOG="${TMP}/calls" STRATEGY_LAB_BASE_CANDIDATE_SYSTEM_ADAPTER="${BASE}" \
    /bin/sh "${WRAPPER}" cleanup job.test ||
    fail 'Stage 85 rejected valid mode-0644 shell base adapter'
grep -qx 'cleanup job.test' "${TMP}/calls" ||
    fail 'base adapter did not receive the exact cleanup command'

if STRATEGY_LAB_BASE_CANDIDATE_SYSTEM_ADAPTER="${TMP}/missing" \
    /bin/sh "${WRAPPER}" cleanup job.test; then
    fail 'missing base adapter accepted'
else
    rc=$?
    [ "${rc}" -eq 69 ] || fail "missing base adapter returned ${rc}, expected 69"
fi

if STRATEGY_LAB_BASE_CANDIDATE_SYSTEM_ADAPTER="${TMP}" \
    /bin/sh "${WRAPPER}" cleanup job.test; then
    fail 'directory was accepted as base adapter'
else
    rc=$?
    [ "${rc}" -eq 69 ] || fail "directory base adapter returned ${rc}, expected 69"
fi

echo 'PASS: Stage 85 readable non-executable shell adapter handoff, with invalid paths refused'
