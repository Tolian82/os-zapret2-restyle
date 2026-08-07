#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MATRIX="${ROOT_DIR}/docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md"
THIRD_AUDIT="${ROOT_DIR}/docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md"
CLOSURE="${ROOT_DIR}/docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md"
STATE="${ROOT_DIR}/docs/PROJECT_STATE.md"
INDEX="${ROOT_DIR}/docs/INDEX.md"
RESTORE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-07-v0.3.3_5-scenario-01-candidate-runtime-restore-failure.md"

for file in "${MATRIX}" "${THIRD_AUDIT}" "${CLOSURE}" "${STATE}" "${INDEX}" "${RESTORE_EVIDENCE}"
do
    [ -s "${file}" ] || { echo "FAIL: missing Strategy Lab live-gate record: ${file}" >&2; exit 1; }
done

grep -Fq 'Overall status: **PAUSED — THIRD-AUDIT CORRECTIVE SERIES IN PROGRESS**' "${MATRIX}"
grep -Fq 'Current corrective candidate: **NOT DESIGNATED — PATCH 8 REQUIRED**' "${MATRIX}"
grep -Fq 'Historical `_6` CI package: `os-zapret2-restyle-0.3.3_6.pkg`' "${MATRIX}"
grep -Fq 'Latest tested package: `os-zapret2-restyle-0.3.3_5.pkg`' "${MATRIX}"
grep -Fq 'Required package ABI: `FreeBSD:15:amd64`' "${MATRIX}"
grep -Fq 'AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md' "${MATRIX}"
grep -Fq 'artifact `8980876980`' "${MATRIX}"
grep -Fq 'Post-merge `main` CI run `31144323095` also passed.' "${MATRIX}"

paused_count=$(awk -F'|' '$2 ~ /^[[:space:]]*1[[:space:]]*$/ && $6 ~ /PAUSED — PATCH 8 REQUIRED/ {n++} END {print n+0}' "${MATRIX}")
[ "${paused_count}" -eq 1 ] || { echo "FAIL: scenario 1 pause row mismatch" >&2; exit 1; }
blocked_count=$(awk -F'|' '$2 ~ /^[[:space:]]*[0-9]+[[:space:]]*$/ && $6 ~ /BLOCKED BY #1/ {n++} END {print n+0}' "${MATRIX}")
[ "${blocked_count}" -eq 17 ] || { echo "FAIL: dependent live rows are not all blocked" >&2; exit 1; }

if grep -Eq '^Overall status:.*PASS|\|[[:space:]]*\*\*PASS\*\*[[:space:]]*\|$' "${MATRIX}"; then
    echo 'FAIL: live matrix contains an unsupported scenario PASS claim' >&2
    exit 1
fi

grep -Fq 'Temporary candidate runtime failed internally.' "${RESTORE_EVIDENCE}"
grep -Fq 'RESTORE_FAILED' "${RESTORE_EVIDENCE}"
grep -Fq 'Scenario 1 remains **FAILED / PENDING CORRECTION** for `_5`.' "${RESTORE_EVIDENCE}"

grep -Fq 'Status: **CORRECTIVE SERIES OPEN**' "${THIRD_AUDIT}"
grep -Fq 'SL3-001' "${THIRD_AUDIT}"
grep -Fq 'SL3-007' "${THIRD_AUDIT}"
grep -Fq 'Patch 8 — Source/CI closure and live-test handoff' "${THIRD_AUDIT}"

grep -Fq 'Status: **REOPENED BY THIRD AUDIT — CORRECTIVE SERIES IN PROGRESS**' "${CLOSURE}"
grep -Fq 'Status: **PAUSED PENDING THIRD-AUDIT SOURCE/CI COMPLETION**' "${CLOSURE}"
grep -Fq 'Status: **BLOCKED ON CORRECTIVE SERIES AND LIVE MATRIX**' "${CLOSURE}"
grep -Fq 'Live OPNsense matrix: **PAUSED PENDING THIRD-AUDIT SOURCE/CI COMPLETION**' "${STATE}"
grep -Fq 'AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md' "${STATE}"
grep -Fq 'AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md' "${INDEX}"

echo 'PASS: live matrix is paused for the third-audit corrective series without unsupported PASS claims'
