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
CURRENT_STAGE50_HOSTLIST_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-07-v0.3.3_16-scenario-01-stage50-hostlist-access.md"
CURRENT_PYTHON_HANDOFF_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-07-v0.3.3_17-scenario-01-python-handoff.md"
CURRENT_POST_MIGRATION_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-08-v0.3.3_25-scenario-01-stage50-candidate-isolation.md"
CURRENT_DNS_DEADLINE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-08-v0.3.3_26-scenario-01-stage40-dns-deadline.md"
CURRENT_RELEASE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-08-v0.3.3_27-scenario-01-pass.md"
CURRENT_ADAPTIVE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-09-v0.4.0_2-stage60-family-reachability-pass.md"
LIVE_GATE_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md"
PYTHON_PLAN="${ROOT_DIR}/docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md"
PYTHON_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-07-strategy-lab-python-orchestration.md"
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

# Current policy: the full matrix is a regression inventory. v0.4.0 selects Scenario 1
# as its mandatory post-migration appliance row; adaptive _28 adds a focused
# change-specific PASS without promoting unrelated pending rows.
if grep -Fq 'Overall status: **RELEASE-SELECTED LIVE GATE PASS ON `_27`; ADAPTIVE `_28` FOCUSED PASS; FULL REGRESSION MATRIX OPEN**' "${MATRIX}"; then
    for file in "${CURRENT_RELEASE_EVIDENCE}" "${CURRENT_ADAPTIVE_EVIDENCE}" "${LIVE_GATE_DECISION}"
    do
        [ -s "${file}" ] || { echo "FAIL: current release live-gate record is missing: ${file}" >&2; exit 1; }
    done
    grep -Fq "Latest published testing candidate: \`${candidate}\`" "${MATRIX}"
    grep -Fq "Latest owner-tested candidate: \`${candidate}\`" "${MATRIX}"
    grep -Fq 'Latest owner-tested diagnostic job: `job.2HVQqr`' "${MATRIX}"
    scenario_one=$(awk -F'|' '$2 ~ /^[[:space:]]*1[[:space:]]*$/ && $6 ~ /PASS ON `_27` — v0.4.0 mandatory row/ {n++} END {print n+0}' "${MATRIX}")
    [ "${scenario_one}" -eq 1 ] || { echo 'FAIL: v0.4.0 mandatory Scenario 1 PASS row mismatch' >&2; exit 1; }
    pending_count=$(awk -F'|' '$2 ~ /^[[:space:]]*([2-9]|1[0-8])[[:space:]]*$/ && $6 ~ /PENDING REGRESSION/ {n++} END {print n+0}' "${MATRIX}")
    [ "${pending_count}" -eq 17 ] || { echo 'FAIL: rows 2-18 must remain honest pending regression coverage' >&2; exit 1; }
    grep -Fq 'Result: **SCENARIO 1 PASS on `v0.3.3_27`**.' "${CURRENT_RELEASE_EVIDENCE}"
    grep -Fq 'Result: **ADAPTIVE-SEARCH `_28` FOCUSED LIVE PASS on `v0.4.0_2`**.' "${CURRENT_ADAPTIVE_EVIDENCE}"
    grep -Fq '| Stage 50 | PASS; `total=7`, `completed=7`, `accepted=[]`' "${CURRENT_ADAPTIVE_EVIDENCE}"
    grep -Fq '| Stage 60 | PASS; `total_available=14`, `completed=14`' "${CURRENT_ADAPTIVE_EVIDENCE}"
    grep -Fq 'no temporary rule from the reserved `19100–19131` range remained' "${CURRENT_ADAPTIVE_EVIDENCE}"
    grep -Fq 'It is not an' "${LIVE_GATE_DECISION}"
    grep -Fq 'all-or-nothing release checklist.' "${LIVE_GATE_DECISION}"
    if grep -Fq 'Stable release preparation and pkg-repository promotion remain blocked until every' "${MATRIX}"; then
        echo 'FAIL: blanket all-row stable-release gate returned' >&2
        exit 1
    fi
    echo 'PASS: _27 remains the v0.4.0 release row, _28 has focused owner evidence, and rows 2-18 remain pending regression backlog'
    exit 0
fi

blocked_count=$(awk -F'|' '$2 ~ /^[[:space:]]*[0-9]+[[:space:]]*$/ && $6 ~ /BLOCKED BY #1/ {n++} END {print n+0}' "${MATRIX}")
[ "${blocked_count}" -eq 17 ] || { echo "FAIL: dependent live rows are not all blocked" >&2; exit 1; }

if grep -Eq '^Overall status:.*PASS|\|[[:space:]]*\*\*PASS\*\*[[:space:]]*\|$' "${MATRIX}"; then
    echo 'FAIL: live matrix contains an unsupported scenario PASS claim' >&2
    exit 1
fi

# Post-migration _26 is the latest published/owner-tested boundary. Corrective _27
# widens the Python DNS and enclosing Stage-40 deadlines without promoting Scenario 1.
if grep -Fq 'Overall status: **FAILED ON `_26` — CORRECTIVE `_27` REQUIRED**' "${MATRIX}"; then
    [ "${revision}" -eq 27 ] || { echo 'FAIL: _26 live failure must designate corrective revision 27' >&2; exit 1; }
    [ -s "${CURRENT_DNS_DEADLINE_EVIDENCE}" ] || { echo 'FAIL: _26 Stage-40 DNS evidence is missing' >&2; exit 1; }
    grep -Fq 'Latest published testing candidate: `os-zapret2-restyle-0.3.3_26.pkg`' "${MATRIX}"
    grep -Fq 'Latest owner-tested candidate: `os-zapret2-restyle-0.3.3_26.pkg`' "${MATRIX}"
    grep -Fq "Current corrective source candidate: \`${candidate}\`" "${MATRIX}"
    grep -Fq "Current corrective source candidate: \`${candidate}\`" "${STATE}"
    grep -Fq 'Latest owner-tested diagnostic job: `job.Cs5ryG`' "${MATRIX}"
    grep -Fq 'subprocess duration was `2024 ms`' "${MATRIX}"
    grep -Fq 'about 8–10 seconds' "${MATRIX}"
    grep -Fq 'DNS subprocess deadline: 15 seconds' "${MATRIX}"
    grep -Fq 'enclosing Stage-40 operation limit: 20 seconds' "${MATRIX}"
    scenario_one=$(awk -F'|' '$2 ~ /^[[:space:]]*1[[:space:]]*$/ && $6 ~ /FAILED ON `_26` — `_27` STAGE-40 RETEST REQUIRED/ {n++} END {print n+0}' "${MATRIX}")
    [ "${scenario_one}" -eq 1 ] || { echo 'FAIL: scenario 1 _26/_27 live row mismatch' >&2; exit 1; }
    grep -Fq 'Latest owner-tested testing candidate: `v0.3.3_26` / `os-zapret2-restyle-0.3.3_26.pkg`' "${STATE}"
    grep -Fq 'Current phase: **Strategy Lab post-migration live correction — Stage-40 DNS deadline**' "${STATE}"
    grep -Fq 'Candidate: `v0.3.3_26` / `os-zapret2-restyle-0.3.3_26.pkg`' "${CURRENT_DNS_DEADLINE_EVIDENCE}"
    grep -Fq '`duration_ms: 2024`' "${CURRENT_DNS_DEADLINE_EVIDENCE}"
    grep -Fq 'DNS subprocess: 15 seconds' "${CURRENT_DNS_DEADLINE_EVIDENCE}"
    grep -Fq 'Stage-40 operation envelope: 20 seconds' "${CURRENT_DNS_DEADLINE_EVIDENCE}"
    grep -Fq 'docs/patches/v0.3.3_27.md' "${INDEX}"
    echo "PASS: live matrix records _26 Stage-40 DNS deadline failure and gates Scenario 1 on corrective ${candidate}"
    exit 0
fi

# Post-migration _25 is the latest published/owner-tested boundary. Corrective _26
# isolates candidate-local failures without promoting Scenario 1 to PASS.
if grep -Fq 'Overall status: **FAILED ON `_25` — CORRECTIVE `_26` REQUIRED**' "${MATRIX}"; then
    [ "${revision}" -eq 26 ] || { echo 'FAIL: _25 live failure must designate corrective revision 26' >&2; exit 1; }
    [ -s "${CURRENT_POST_MIGRATION_EVIDENCE}" ] || { echo 'FAIL: _25 post-migration live evidence is missing' >&2; exit 1; }
    grep -Fq 'Latest published testing candidate: `os-zapret2-restyle-0.3.3_25.pkg`' "${MATRIX}"
    grep -Fq 'Latest owner-tested candidate: `os-zapret2-restyle-0.3.3_25.pkg`' "${MATRIX}"
    grep -Fq "Current corrective source candidate: \`${candidate}\`" "${MATRIX}"
    grep -Fq "Current corrective source candidate: \`${candidate}\`" "${STATE}"
    grep -Fq 'Latest owner-tested job: `job.c0oydv`' "${MATRIX}"
    grep -Fq '50 ERROR — visible message `Temporary candidate runtime failed internally.`' "${MATRIX}"
    grep -Fq '`accepted=["seqovl"]`' "${MATRIX}"
    grep -Fq '`process_identity=true`' "${MATRIX}"
    grep -Fq 'persisted progress was visible at 36%' "${MATRIX}"
    grep -Fq '90 PASS — temporary state removed and initial RUNNING Zapret2 restored healthy' "${MATRIX}"
    scenario_one=$(awk -F'|' '$2 ~ /^[[:space:]]*1[[:space:]]*$/ && $6 ~ /FAILED ON `_25` — `_26` STAGE-50 RETEST REQUIRED/ {n++} END {print n+0}' "${MATRIX}")
    [ "${scenario_one}" -eq 1 ] || { echo 'FAIL: scenario 1 _25/_26 live row mismatch' >&2; exit 1; }
    grep -Fq 'Latest owner-tested testing candidate: `v0.3.3_25` / `os-zapret2-restyle-0.3.3_25.pkg`' "${STATE}"
    grep -Fq 'Current phase: **Strategy Lab post-migration live correction — Stage-50 candidate isolation**' "${STATE}"
    grep -Fq 'Candidate: `v0.3.3_25` / `os-zapret2-restyle-0.3.3_25.pkg`' "${CURRENT_POST_MIGRATION_EVIDENCE}"
    grep -Fq '`accepted`: `["seqovl"]`' "${CURRENT_POST_MIGRATION_EVIDENCE}"
    grep -Fq 'Corrective source candidate `_26` implements and regression-tests that boundary.' "${CURRENT_POST_MIGRATION_EVIDENCE}"
    echo "PASS: live matrix records _25 partial Stage-50 success/failure and gates Scenario 1 on corrective ${candidate}"
    exit 0
fi

# During Python migration, _17 remains the frozen published/owner-tested shell-era
# evidence boundary while package-source revisions may advance before live parity.
if grep -Fq 'Overall status: **FAILED ON `_17` — LIVE MATRIX PAUSED FOR PYTHON MIGRATION**' "${MATRIX}"; then
    [ "${revision}" -ge 17 ] || { echo 'FAIL: Python migration source revision cannot precede revision 17' >&2; exit 1; }
    for file in "${CURRENT_PYTHON_HANDOFF_EVIDENCE}" "${PYTHON_PLAN}" "${PYTHON_DECISION}"
    do
        [ -s "${file}" ] || { echo "FAIL: Python migration handoff record is missing: ${file}" >&2; exit 1; }
    done
    grep -Fq 'Latest published testing candidate: `os-zapret2-restyle-0.3.3_17.pkg`' "${MATRIX}"
    grep -Fq 'Latest owner-tested candidate: `os-zapret2-restyle-0.3.3_17.pkg`' "${MATRIX}"
    if [ "${revision}" -gt 17 ]; then
        grep -Fq "Current migration source candidate: \`${candidate}\`" "${MATRIX}" || {
            echo "FAIL: live matrix does not select migration source candidate ${candidate}" >&2
            exit 1
        }
        grep -Fq "Current migration source candidate: \`${candidate}\`" "${STATE}" || {
            echo "FAIL: project state does not select migration source candidate ${candidate}" >&2
            exit 1
        }
    fi
    grep -Fq 'Latest owner-tested job: `job.w0nXxQ`' "${MATRIX}"
    grep -Fq '50 ERROR — `Temporary candidate runtime failed internally.`' "${MATRIX}"
    grep -Fq '90 PASS — temporary state removed and initial RUNNING Zapret2 restored healthy' "${MATRIX}"
    grep -Fq 'Strategy Lab returned no output.' "${MATRIX}"
    grep -Fq 'visible progress remained 0%' "${MATRIX}"
    scenario_one=$(awk -F'|' '$2 ~ /^[[:space:]]*1[[:space:]]*$/ && $6 ~ /FAILED ON `_17` — RETEST AFTER PYTHON PARITY/ {n++} END {print n+0}' "${MATRIX}")
    [ "${scenario_one}" -eq 1 ] || { echo 'FAIL: scenario 1 Python migration handoff row mismatch' >&2; exit 1; }
    grep -Fq 'Latest owner-tested testing candidate: `v0.3.3_17` / `os-zapret2-restyle-0.3.3_17.pkg`' "${STATE}"
    grep -Fq 'Current phase: **Strategy Lab' "${STATE}"
    grep -Fq 'Stage 50 remains ERROR on `_17`.' "${STATE}"
    grep -Fq 'STRATEGY_LAB_PYTHON_MIGRATION.md' "${INDEX}"
    grep -Fq 'Job shown in GUI: `job.w0nXxQ`' "${CURRENT_PYTHON_HANDOFF_EVIDENCE}"
    grep -Fq 'Stage 50 remains the backend blocker.' "${CURRENT_PYTHON_HANDOFF_EVIDENCE}"
    grep -Fq 'exact `_17` Stage-50 root cause is not yet established' "${PYTHON_DECISION}"
    echo "PASS: live matrix freezes the failed _17 shell-era evidence while Python migration source candidate ${candidate} may advance without unsupported PASS claims"
    exit 0
fi

# Historical live-state fixtures below remain accepted so older corrective states are
# still mechanically recognizable when replayed from their own source revisions.
grep -Fq 'artifact `8980876980`' "${MATRIX}"
grep -Fq 'Post-merge `main` CI run `31144323095` also passed.' "${MATRIX}"
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
    paused_count=$(awk -F'|' '$2 ~ /^[[:space:]]*1[[:space:]]*$/ && $6 ~ /PAUSED — PATCH 8 REQUIRED/ {n++} END {print n+0}' "${MATRIX}")
    [ "${paused_count}" -eq 1 ] || { echo "FAIL: scenario 1 pause row mismatch" >&2; exit 1; }
    echo 'PASS: live matrix is paused for the third-audit corrective series without unsupported PASS claims'
    exit 0
fi

if grep -Fq 'Overall status: **FAILED ON _16 — STAGE-50 CORRECTION `_17` IN PROGRESS**' "${MATRIX}"; then
    [ "${revision}" -eq 17 ] || { echo 'FAIL: hostlist-access live matrix must designate revision 17' >&2; exit 1; }
    [ -s "${CURRENT_STAGE50_HOSTLIST_EVIDENCE}" ] || { echo 'FAIL: current _16 hostlist evidence is missing' >&2; exit 1; }
    grep -Fq 'Latest owner-tested candidate: `os-zapret2-restyle-0.3.3_16.pkg`' "${MATRIX}"
    grep -Fq 'Current corrective source candidate: `os-zapret2-restyle-0.3.3_17.pkg`' "${MATRIX}"
    grep -Fq 'job `job.VmWk32`' "${MATRIX}"
    grep -Fq 'Running as UID=65534 GID=65534' "${MATRIX}"
    grep -Fq 'file_open_test: Permission denied' "${MATRIX}"
    scenario_one=$(awk -F'|' '$2 ~ /^[[:space:]]*1[[:space:]]*$/ && $6 ~ /FAILED ON `_16` — `_17` STAGE-50 RETEST REQUIRED/ {n++} END {print n+0}' "${MATRIX}")
    [ "${scenario_one}" -eq 1 ] || { echo 'FAIL: scenario 1 _16/_17 live row mismatch' >&2; exit 1; }
    grep -Fq 'Live OPNsense matrix: **FAILED AT STAGE 50 ON `_16` — CORRECTIVE `_17` REQUIRED**.' "${STATE}"
    grep -Fq 'Current corrective package revision: `PLUGIN_REVISION=17`' "${STATE}"
    grep -Fq 'Job: `job.VmWk32`' "${CURRENT_STAGE50_HOSTLIST_EVIDENCE}"
    grep -Fq 'stage 40: PASS' "${CURRENT_STAGE50_HOSTLIST_EVIDENCE}"
    grep -Fq 'stage 90: PASS' "${CURRENT_STAGE50_HOSTLIST_EVIDENCE}"
    grep -Fq 'file_open_test: Permission denied' "${CURRENT_STAGE50_HOSTLIST_EVIDENCE}"
    grep -Fq '`log_clean:true`' "${CURRENT_STAGE50_HOSTLIST_EVIDENCE}"
    echo 'PASS: live matrix records _16 post-drop hostlist failure and gates Scenario 1 on the _17 access correction'
    exit 0
fi

if grep -Fq 'Overall status: **FAILED ON _15 — STAGE-50 CORRECTION `_16` IN PROGRESS**' "${MATRIX}"; then
    [ "${revision}" -eq 16 ] || { echo 'FAIL: FreeBSD daemon live matrix must designate revision 16' >&2; exit 1; }
    [ -s "${CURRENT_STAGE50_DAEMON_EVIDENCE}" ] || { echo 'FAIL: current _15 stage-50 daemon evidence is missing' >&2; exit 1; }
    grep -Fq 'Latest owner-tested candidate: `os-zapret2-restyle-0.3.3_15.pkg`' "${MATRIX}"
    grep -Fq 'Current corrective source candidate: `os-zapret2-restyle-0.3.3_16.pkg`' "${MATRIX}"
    scenario_one=$(awk -F'|' '$2 ~ /^[[:space:]]*1[[:space:]]*$/ && $6 ~ /FAILED ON `_15` — `_16` STAGE-50 RETEST REQUIRED/ {n++} END {print n+0}' "${MATRIX}")
    [ "${scenario_one}" -eq 1 ] || { echo 'FAIL: scenario 1 _15/_16 live row mismatch' >&2; exit 1; }
    echo 'PASS: live matrix records _15 stage-50 failure and gates Scenario 1 on the _16 FreeBSD candidate daemon startup correction'
    exit 0
fi

if grep -Fq 'Overall status: **FAILED ON _14 — STAGE-50 CORRECTION `_15` IN PROGRESS**' "${MATRIX}"; then
    [ "${revision}" -eq 15 ] || { echo 'FAIL: stage-50 live matrix must designate revision 15' >&2; exit 1; }
    [ -s "${CURRENT_STAGE50_EVIDENCE}" ] || { echo 'FAIL: current _14 stage-50 evidence is missing' >&2; exit 1; }
    scenario_one=$(awk -F'|' '$2 ~ /^[[:space:]]*1[[:space:]]*$/ && $6 ~ /FAILED ON `_14` — `_15` STAGE-50 RETEST REQUIRED/ {n++} END {print n+0}' "${MATRIX}")
    [ "${scenario_one}" -eq 1 ] || { echo 'FAIL: scenario 1 stage-50 live row mismatch' >&2; exit 1; }
    echo 'PASS: live matrix records _14 stage-40/stage-90 success and gates Scenario 1 on the _15 stage-50 family-runner correction'
    exit 0
fi

if grep -Fq 'Overall status: **FAILED ON _13 — STAGE-40 CORRECTION `_14` IN PROGRESS**' "${MATRIX}"; then
    [ "${revision}" -eq 14 ] || { echo 'FAIL: stage-40 live matrix must designate revision 14' >&2; exit 1; }
    [ -s "${CURRENT_DNS_EVIDENCE}" ] || { echo 'FAIL: current _13 stage-40 DNS evidence is missing' >&2; exit 1; }
    scenario_one=$(awk -F'|' '$2 ~ /^[[:space:]]*1[[:space:]]*$/ && $6 ~ /FAILED ON `_13` — `_14` STAGE-40 RETEST REQUIRED/ {n++} END {print n+0}' "${MATRIX}")
    [ "${scenario_one}" -eq 1 ] || { echo 'FAIL: scenario 1 stage-40 live row mismatch' >&2; exit 1; }
    echo 'PASS: live matrix records _13 stage-90 success and gates Scenario 1 on the _14 FreeBSD DNS timeout correction'
    exit 0
fi

if grep -Fq 'Overall status: **FAILED ON _12 — STAGE-90 CORRECTION `_13` IN PROGRESS**' "${MATRIX}"; then
    [ "${revision}" -eq 13 ] || { echo 'FAIL: reopened live matrix must designate revision 13' >&2; exit 1; }
    [ -s "${CURRENT_RESTORE_EVIDENCE}" ] || { echo 'FAIL: current _12 restoration evidence is missing' >&2; exit 1; }
    scenario_one=$(awk -F'|' '$2 ~ /^[[:space:]]*1[[:space:]]*$/ && $6 ~ /FAILED ON `_12` — `_13` RESTORATION RETEST REQUIRED/ {n++} END {print n+0}' "${MATRIX}")
    [ "${scenario_one}" -eq 1 ] || { echo 'FAIL: scenario 1 reopened-live row mismatch' >&2; exit 1; }
    echo 'PASS: live matrix truthfully records _12 failure and gates dependent scenarios on the _13 restoration correction'
    exit 0
fi

# Patch 8 handoff state: source/CI is closed, but no appliance row is promoted to PASS.
grep -Fq "Overall status: **PENDING OWNER — SCENARIO 1 RETEST ON _${revision}**" "${MATRIX}"
grep -Fq "Current corrective candidate: \`${candidate}\`" "${MATRIX}"
scenario_one=$(awk -F'|' '$2 ~ /^[[:space:]]*1[[:space:]]*$/ && $6 ~ /PENDING OWNER — RETEST REQUIRED/ {n++} END {print n+0}' "${MATRIX}")
[ "${scenario_one}" -eq 1 ] || { echo 'FAIL: scenario 1 handoff row mismatch' >&2; exit 1; }
echo "PASS: source/CI handoff selects ${candidate} while all live PASS claims remain owner-gated"
