#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MATRIX="${ROOT_DIR}/docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md"
THIRD_AUDIT="${ROOT_DIR}/docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md"
CLOSURE="${ROOT_DIR}/docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md"
STATE="${ROOT_DIR}/docs/PROJECT_STATE.md"
INDEX="${ROOT_DIR}/docs/INDEX.md"
RELEASE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-08-v0.3.3_27-scenario-01-pass.md"
ADAPTIVE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-09-v0.4.0_2-stage60-family-reachability-pass.md"
TIMEOUT_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-09-v0.4.0_6-stage60-timeout.md"
LATE_STAGE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-10-v0.4.0_7-late-stage-pass.md"
LIVE_GATE_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md"
VERSION_FILE="${ROOT_DIR}/VERSION"
MAKEFILE="${ROOT_DIR}/Makefile"

for file in \
    "${MATRIX}" "${THIRD_AUDIT}" "${CLOSURE}" "${STATE}" "${INDEX}" \
    "${RELEASE_EVIDENCE}" "${ADAPTIVE_EVIDENCE}" "${TIMEOUT_EVIDENCE}" \
    "${LATE_STAGE_EVIDENCE}" "${LIVE_GATE_DECISION}" "${VERSION_FILE}" "${MAKEFILE}"
do
    [ -s "${file}" ] || {
        echo "FAIL: missing Strategy Lab live-gate record: ${file}" >&2
        exit 1
    }
done

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(awk -F= '/^PLUGIN_REVISION=/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${MAKEFILE}")
case "${revision}" in
    ''|*[!0-9]*) echo 'FAIL: invalid plugin revision' >&2; exit 1 ;;
esac
candidate="os-zapret2-restyle-${version}_${revision}.pkg"

# The active current-source contract belongs to the current branch. Historical source
# revisions retain their own immutable copy of this script, so current CI does not need
# alternate branches for every superseded live-state fixture.
grep -Fq 'Overall status: **RELEASE-SELECTED LIVE GATE PASS ON `_27`; ADAPTIVE `_28` FOCUSED PASS; FULL REGRESSION MATRIX OPEN**' "${MATRIX}"
grep -Fq 'Required package ABI: `FreeBSD:15:amd64`' "${MATRIX}"
grep -Fq 'AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md' "${MATRIX}"
grep -Fq 'Latest published testing candidate: `os-zapret2-restyle-0.4.0_7.pkg`' "${MATRIX}"
grep -Fq 'Latest owner-tested candidate: `os-zapret2-restyle-0.4.0_7.pkg`' "${MATRIX}"
grep -Fq "Current adaptive-search source candidate: \`${candidate}\`" "${MATRIX}"
grep -Fq 'Latest owner-tested Standard job: `job.RFVs75`' "${MATRIX}"
grep -Fq 'Latest owner-tested diagnostic job: `job.QbUuYO`' "${MATRIX}"
grep -Fq 'Latest blocked-domain target: `telegram.org`' "${MATRIX}"
grep -Fq 'docs/verification/evidence/2026-08-10-v0.4.0_7-late-stage-pass.md' "${MATRIX}"

scenario_one=$(awk -F'|' '$2 ~ /^[[:space:]]*1[[:space:]]*$/ && $6 ~ /PASS ON `_27` — v0.4.0 mandatory row/ {n++} END {print n+0}' "${MATRIX}")
[ "${scenario_one}" -eq 1 ] || {
    echo 'FAIL: v0.4.0 mandatory Scenario 1 PASS row mismatch' >&2
    exit 1
}
pending_count=$(awk -F'|' '$2 ~ /^[[:space:]]*([2-9]|1[0-8])[[:space:]]*$/ && $6 ~ /PENDING REGRESSION/ {n++} END {print n+0}' "${MATRIX}")
[ "${pending_count}" -eq 17 ] || {
    echo 'FAIL: rows 2-18 must remain honest pending regression coverage' >&2
    exit 1
}

grep -Fq 'Result: **SCENARIO 1 PASS on `v0.3.3_27`**.' "${RELEASE_EVIDENCE}"
grep -Fq 'Result: **ADAPTIVE-SEARCH `_28` FOCUSED LIVE PASS on `v0.4.0_2`**.' "${ADAPTIVE_EVIDENCE}"
grep -Fq '| Stage 50 | PASS; `total=7`, `completed=7`, `accepted=[]`' "${ADAPTIVE_EVIDENCE}"
grep -Fq '| Stage 60 | PASS; `total_available=14`, `completed=14`' "${ADAPTIVE_EVIDENCE}"
grep -Fq 'no temporary rule from the reserved `19100–19131` range remained' "${ADAPTIVE_EVIDENCE}"

grep -Fq 'Stage-50 adapter duration: about `39.065 s`' "${TIMEOUT_EVIDENCE}"
grep -Fq 'Stage-60 adapter duration was approximately `70.07 s`' "${TIMEOUT_EVIDENCE}"
grep -Fq 'no temporary Strategy Lab rule in `19100-19131` remained' "${TIMEOUT_EVIDENCE}"

grep -Fq 'Standard: `job.RFVs75`' "${LATE_STAGE_EVIDENCE}"
grep -Fq 'Extended: `job.QbUuYO`' "${LATE_STAGE_EVIDENCE}"
grep -Fq '| Standard | PASS | PASS | 90.243 s | 16/16 |' "${LATE_STAGE_EVIDENCE}"
grep -Fq '| Extended | PASS | PASS | 89.249 s | 16/16 |' "${LATE_STAGE_EVIDENCE}"
grep -Fq 'Stage 85: 0.202 s, but `operation_timeout_seconds=null`' "${LATE_STAGE_EVIDENCE}"
grep -Fq 'Stage 90 restoration: 6.921 s, also with `operation_timeout_seconds=null`' "${LATE_STAGE_EVIDENCE}"
grep -Fq 'Stage 85: 0.203 s, but `operation_timeout_seconds=null`' "${LATE_STAGE_EVIDENCE}"
grep -Fq 'Stage 90 restoration: 6.945 s, also with `operation_timeout_seconds=null`' "${LATE_STAGE_EVIDENCE}"
grep -Fq 'only the normal rule `19000`; no' "${LATE_STAGE_EVIDENCE}"

grep -Fq 'It is not an' "${LIVE_GATE_DECISION}"
grep -Fq 'all-or-nothing release checklist.' "${LIVE_GATE_DECISION}"
if grep -Fq 'Stable release preparation and pkg-repository promotion remain blocked until every' "${MATRIX}"; then
    echo 'FAIL: blanket all-row stable-release gate returned' >&2
    exit 1
fi

# Current source must point forward from the latest owner-tested candidate. This check is
# intentionally metadata-driven so the next package revision cannot silently leave the
# canonical matrix behind.
[ "${version}" = '0.4.0' ] || {
    echo "FAIL: unexpected active Strategy Lab source version ${version}" >&2
    exit 1
}
[ "${revision}" -ge 8 ] || {
    echo "FAIL: late-stage containment source revision must be at least 8" >&2
    exit 1
}

echo "PASS: _27 remains the v0.4.0 release row, _28 keeps focused owner evidence, _7 closes the observed Stage-60 timeout, ${candidate} is the current late-stage source candidate, and rows 2-18 remain regression backlog"
