#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MATRIX="${ROOT_DIR}/docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md"
THIRD_AUDIT="${ROOT_DIR}/docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md"
CLOSURE="${ROOT_DIR}/docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md"
STATE="${ROOT_DIR}/docs/PROJECT_STATE.md"
INDEX="${ROOT_DIR}/docs/INDEX.md"
RESTORE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-07-v0.3.3_5-scenario-01-candidate-runtime-restore-failure.md"
CURRENT_RESTORE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-07-v0.3.3_12-scenario-01-freebsd-timeout-restoration.md"
CURRENT_DNS_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-07-v0.3.3_13-scenario-01-stage40-freebsd-dns-timeout.md"
CURRENT_STAGE50_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-07-v0.3.3_14-scenario-01-stage50-family-runner-and-ui.md"
CURRENT_STAGE50_DAEMON_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-07-v0.3.3_15-scenario-01-stage50-freebsd-daemon-supervisor.md"
VERSION_FILE="${ROOT_DIR}/VERSION"
MAKEFILE="${ROOT_DIR}/Makefile"

for file in "${MATRIX}" "${THIRD_AUDIT}" "${CLOSURE}" "${STATE}" "${INDEX}" \
    "${RESTORE_EVIDENCE}" "${VERSION_FILE}" "${MAKEFILE}"
do
    [ -s "${file}" ] || { echo "FAIL: missing Strategy Lab live-gate record: ${file}" >&2; exit 1; }
done

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(awk -F= '/^PLUGIN_REVISION=/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${MAKEFILE}")
case "${revision}" in ''|*[!0-9]*) echo 'FAIL: invalid plugin revision' >&2; exit 1 ;; esac
candidate="os-zapret2-restyle-${version}_${revision}.pkg"

grep -Fq 'Required package ABI: `FreeBSD:15:amd64`' "${MATRIX}"
grep -Fq 'AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md' "${MATRIX}"
grep -Fq 'artifact `8980876980`' "${MATRIX}"
grep -Fq 'Post-merge `main` CI run `31144323095` also passed.' "${MATRIX}"

blocked_count=$(awk -F'|' '$2 ~ /^[[:space:]]*[0-9]+[[:space:]]*$/ && $6 ~ /BLOCKED BY #1/ {n++} END {print n+0}' "${MATRIX}")
[ "${blocked_count}" -eq 17 ] || { echo "FAIL: dependent live rows are not all blocked" >&2; exit 1; }

if grep -Eq '^Overall status:.*PASS|\|[[:space:]]*\*\*PASS\*\*[[:space:]]*\|$' "${MATRIX}"; then
    echo 'FAIL: live matrix contains an unsupported scenario PASS claim' >&2
    exit 1
fi

grep -Fq 'Temporary candidate runtime failed internally.' "${RESTORE_EVIDENCE}"
grep -Fq 'RESTORE_FAILED' "${RESTORE_EVIDENCE}"
grep -Fq 'Scenario 1 remains **FAILED / PENDING CORRECTION** for `_5`.' "${RESTORE_EVIDENCE}"

grep -Fq 'SL3-001' "${THIRD_AUDIT}"
grep -Fq 'SL3-007' "${THIRD_AUDIT}"
grep -Fq 'Patch 8 — Source/CI closure and live-test handoff' "${THIRD_AUDIT}"
grep -Fq 'AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md' "${STATE}"
grep -Fq 'AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md' "${INDEX}"

if grep -Fq 'Overall status: **PAUSED — THIRD-AUDIT CORRECTIVE SERIES IN PROGRESS**' "${MATRIX}"; then
    grep -Fq 'Current corrective candidate: **NOT DESIGNATED — PATCH 8 REQUIRED**' "${MATRIX}"
    grep -Fq 'Historical `_6` CI package: `os-zapret2-restyle-0.3.3_6.pkg`' "${MATRIX}"
    paused_count=$(awk -F'|' '$2 ~ /^[[:space:]]*1[[:space:]]*$/ && $6 ~ /PAUSED — PATCH 8 REQUIRED/ {n++} END {print n+0}' "${MATRIX}")
    [ "${paused_count}" -eq 1 ] || { echo "FAIL: scenario 1 pause row mismatch" >&2; exit 1; }
    grep -Fq 'Status: **CORRECTIVE SERIES OPEN**' "${THIRD_AUDIT}"
    grep -Fq 'Status: **REOPENED BY THIRD AUDIT — CORRECTIVE SERIES IN PROGRESS**' "${CLOSURE}"
    grep -Fq 'Status: **PAUSED PENDING THIRD-AUDIT SOURCE/CI COMPLETION**' "${CLOSURE}"
    grep -Fq 'Status: **BLOCKED ON CORRECTIVE SERIES AND LIVE MATRIX**' "${CLOSURE}"
    grep -Fq 'Live OPNsense matrix: **PAUSED PENDING THIRD-AUDIT SOURCE/CI COMPLETION**' "${STATE}"
    echo 'PASS: live matrix is paused for the third-audit corrective series without unsupported PASS claims'
    exit 0
fi

if grep -Fq 'Overall status: **FAILED ON _15 — STAGE-50 CORRECTION `_16` IN PROGRESS**' "${MATRIX}"; then
    [ "${revision}" -eq 16 ] || { echo 'FAIL: FreeBSD daemon live matrix must designate revision 16' >&2; exit 1; }
    [ -s "${CURRENT_STAGE50_DAEMON_EVIDENCE}" ] || { echo 'FAIL: current _15 stage-50 daemon evidence is missing' >&2; exit 1; }
    grep -Fq 'Latest owner-tested candidate: `os-zapret2-restyle-0.3.3_15.pkg`' "${MATRIX}"
    grep -Fq 'Current corrective source candidate: `os-zapret2-restyle-0.3.3_16.pkg`' "${MATRIX}"
    grep -Fq 'job `job.6eZM24`' "${MATRIX}"
    grep -Fq 'FreeBSD `daemon(8)` remains resident' "${MATRIX}"
    scenario_one=$(awk -F'|' '$2 ~ /^[[:space:]]*1[[:space:]]*$/ && $6 ~ /FAILED ON `_15` — `_16` STAGE-50 RETEST REQUIRED/ {n++} END {print n+0}' "${MATRIX}")
    [ "${scenario_one}" -eq 1 ] || { echo 'FAIL: scenario 1 _15/_16 live row mismatch' >&2; exit 1; }
    grep -Fq 'Live OPNsense matrix: **FAILED AT STAGE 50 ON `_15` — CORRECTIVE `_16` REQUIRED**.' "${STATE}"
    grep -Fq 'Current corrective package revision: `PLUGIN_REVISION=16`' "${STATE}"
    grep -Fq 'Job: `job.6eZM24`' "${CURRENT_STAGE50_DAEMON_EVIDENCE}"
    grep -Fq 'stage 40: PASS' "${CURRENT_STAGE50_DAEMON_EVIDENCE}"
    grep -Fq 'stage 90: PASS' "${CURRENT_STAGE50_DAEMON_EVIDENCE}"
    grep -Fq 'resident `daemon(8)` supervisor semantics' "${CURRENT_STAGE50_DAEMON_EVIDENCE}"
    echo 'PASS: live matrix records _15 stage-50 failure and gates Scenario 1 on the _16 FreeBSD candidate daemon startup correction'
    exit 0
fi

if grep -Fq 'Overall status: **FAILED ON _14 — STAGE-50 CORRECTION `_15` IN PROGRESS**' "${MATRIX}"; then
    [ "${revision}" -eq 15 ] || { echo 'FAIL: stage-50 live matrix must designate revision 15' >&2; exit 1; }
    [ -s "${CURRENT_STAGE50_EVIDENCE}" ] || { echo 'FAIL: current _14 stage-50 evidence is missing' >&2; exit 1; }
    grep -Fq 'Latest owner-tested candidate: `os-zapret2-restyle-0.3.3_14.pkg`' "${MATRIX}"
    grep -Fq 'Current corrective source candidate: `os-zapret2-restyle-0.3.3_15.pkg`' "${MATRIX}"
    grep -Fq 'job `job.mCqg7Y`' "${MATRIX}"
    grep -Fq 'STRATEGY_LAB_TIMEOUT_BIN: parameter not set' "${MATRIX}"
    grep -Fq 'Stage 40 completed PASS' "${MATRIX}"
    scenario_one=$(awk -F'|' '$2 ~ /^[[:space:]]*1[[:space:]]*$/ && $6 ~ /FAILED ON `_14` — `_15` STAGE-50 RETEST REQUIRED/ {n++} END {print n+0}' "${MATRIX}")
    [ "${scenario_one}" -eq 1 ] || { echo 'FAIL: scenario 1 stage-50 live row mismatch' >&2; exit 1; }
    grep -Fq 'Live OPNsense matrix: **FAILED AT STAGE 50 ON `_14` — CORRECTIVE `_15` REQUIRED**.' "${STATE}"
    grep -Fq 'Current corrective package revision: `PLUGIN_REVISION=15`' "${STATE}"
    grep -Fq 'Stage 40 and stage 90 are live PASS sub-gates' "${CURRENT_STAGE50_EVIDENCE}"
    grep -Fq '17:37:39 — stage 40 / 36%' "${CURRENT_STAGE50_EVIDENCE}"
    grep -Fq '17:37:48 — stage 99 / 100%' "${CURRENT_STAGE50_EVIDENCE}"
    grep -Fq 'completed:0' "${CURRENT_STAGE50_EVIDENCE}"
    echo 'PASS: live matrix records _14 stage-40/stage-90 success and gates Scenario 1 on the _15 stage-50 family-runner correction'
    exit 0
fi

if grep -Fq 'Overall status: **FAILED ON _13 — STAGE-40 CORRECTION `_14` IN PROGRESS**' "${MATRIX}"; then
    [ "${revision}" -eq 14 ] || { echo 'FAIL: stage-40 live matrix must designate revision 14' >&2; exit 1; }
    [ -s "${CURRENT_DNS_EVIDENCE}" ] || { echo 'FAIL: current _13 stage-40 DNS evidence is missing' >&2; exit 1; }
    grep -Fq 'Latest owner-tested candidate: `os-zapret2-restyle-0.3.3_13.pkg`' "${MATRIX}"
    grep -Fq 'Current corrective source candidate: `os-zapret2-restyle-0.3.3_14.pkg`' "${MATRIX}"
    grep -Fq 'job `job.3mc9c6`' "${MATRIX}"
    grep -Fq '/usr/bin/timeout 2 /usr/bin/drill rutracker.org A' "${MATRIX}"
    grep -Fq '/usr/bin/timeout -f 2 /usr/bin/drill rutracker.org A' "${MATRIX}"
    scenario_one=$(awk -F'|' '$2 ~ /^[[:space:]]*1[[:space:]]*$/ && $6 ~ /FAILED ON `_13` — `_14` STAGE-40 RETEST REQUIRED/ {n++} END {print n+0}' "${MATRIX}")
    [ "${scenario_one}" -eq 1 ] || { echo 'FAIL: scenario 1 stage-40 live row mismatch' >&2; exit 1; }
    grep -Fq 'Live OPNsense matrix: **FAILED AT STAGE 40 ON `_13` — CORRECTIVE `_14` REQUIRED**.' "${STATE}"
    grep -Fq 'Current corrective package revision: `PLUGIN_REVISION=14`' "${STATE}"
    grep -Fq 'Stage 90 passed' "${CURRENT_DNS_EVIDENCE}"
    grep -Fq 'result: `rc=124`' "${CURRENT_DNS_EVIDENCE}"
    grep -Fq 'result: `rc=0`' "${CURRENT_DNS_EVIDENCE}"
    echo 'PASS: live matrix records _13 stage-90 success and gates Scenario 1 on the _14 FreeBSD DNS timeout correction'
    exit 0
fi

if grep -Fq 'Overall status: **FAILED ON _12 — STAGE-90 CORRECTION `_13` IN PROGRESS**' "${MATRIX}"; then
    [ "${revision}" -eq 13 ] || { echo 'FAIL: reopened live matrix must designate revision 13' >&2; exit 1; }
    [ -s "${CURRENT_RESTORE_EVIDENCE}" ] || { echo 'FAIL: current _12 restoration evidence is missing' >&2; exit 1; }
    grep -Fq 'Latest owner-tested candidate: `os-zapret2-restyle-0.3.3_12.pkg`' "${MATRIX}"
    grep -Fq 'Current corrective source candidate: `os-zapret2-restyle-0.3.3_13.pkg`' "${MATRIX}"
    grep -Fq 'Job `job.sl7JGM`' "${MATRIX}"
    grep -Fq 'FreeBSD `timeout` without `-f` acts as a reaper' "${MATRIX}"
    scenario_one=$(awk -F'|' '$2 ~ /^[[:space:]]*1[[:space:]]*$/ && $6 ~ /FAILED ON `_12` — `_13` RESTORATION RETEST REQUIRED/ {n++} END {print n+0}' "${MATRIX}")
    [ "${scenario_one}" -eq 1 ] || { echo 'FAIL: scenario 1 reopened-live row mismatch' >&2; exit 1; }
    grep -Fq 'Live OPNsense matrix: **FAILED ON `_12` — CORRECTIVE `_13` REQUIRED**.' "${STATE}"
    grep -Fq 'Current corrective package revision: `PLUGIN_REVISION=13`' "${STATE}"
    grep -Fq '13:31:07' "${CURRENT_RESTORE_EVIDENCE}"
    grep -Fq '13:32:31' "${CURRENT_RESTORE_EVIDENCE}"
    grep -Fq 'daemonizing `strategy-lab-start` action on FreeBSD' "${CURRENT_RESTORE_EVIDENCE}"
    echo 'PASS: live matrix truthfully records _12 failure and gates dependent scenarios on the _13 restoration correction'
    exit 0
fi

# Patch 8 handoff state: source/CI is closed, but no appliance row is promoted to PASS.
grep -Fq "Overall status: **PENDING OWNER — SCENARIO 1 RETEST ON _${revision}**" "${MATRIX}"
grep -Fq "Current corrective candidate: \`${candidate}\`" "${MATRIX}"
grep -Fq 'Patch 7 source/CI qualification:' "${MATRIX}"
scenario_one=$(awk -F'|' '$2 ~ /^[[:space:]]*1[[:space:]]*$/ && $6 ~ /PENDING OWNER — RETEST REQUIRED/ {n++} END {print n+0}' "${MATRIX}")
[ "${scenario_one}" -eq 1 ] || { echo 'FAIL: scenario 1 handoff row mismatch' >&2; exit 1; }
grep -Fq 'Status: **SOURCE/CI CORRECTIVE SERIES COMPLETE — LIVE VERIFICATION PENDING**' "${THIRD_AUDIT}"
grep -Fq 'Status: **SOURCE/CI CLOSED AFTER THIRD AUDIT — LIVE MATRIX PENDING**' "${CLOSURE}"
grep -Fq 'Status: **READY — SCENARIO 1 PENDING OWNER**' "${CLOSURE}"
grep -Fq 'Status: **BLOCKED ON LIVE MATRIX**' "${CLOSURE}"
grep -Fq 'Live OPNsense matrix: **READY — SCENARIO 1 PENDING OWNER**' "${STATE}"

echo "PASS: source/CI handoff selects ${candidate} while all live PASS claims remain owner-gated"
