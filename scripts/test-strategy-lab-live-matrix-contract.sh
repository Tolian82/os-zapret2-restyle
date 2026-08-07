#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MATRIX="${ROOT_DIR}/docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md"
INSTALL_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-06-v0.3.3_1-installation.md"
FAILURE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-06-v0.3.3_1-scenario-01-stage10-failure.md"
BINDING_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-06-v0.3.3_2-scenario-01-semantic-inspector-binding.md"
PIDFILE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-06-v0.3.3_4-scenario-01-pidfile-eof.md"
RESTORE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-07-v0.3.3_5-scenario-01-candidate-runtime-restore-failure.md"
CLOSURE="${ROOT_DIR}/docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md"
STATE="${ROOT_DIR}/docs/PROJECT_STATE.md"
INDEX="${ROOT_DIR}/docs/INDEX.md"
VERSION_FILE="${ROOT_DIR}/VERSION"
MAKEFILE="${ROOT_DIR}/Makefile"

for file in "${MATRIX}" "${INSTALL_EVIDENCE}" "${FAILURE_EVIDENCE}" \
    "${BINDING_EVIDENCE}" "${PIDFILE_EVIDENCE}" "${RESTORE_EVIDENCE}" \
    "${CLOSURE}" "${STATE}" "${INDEX}" "${VERSION_FILE}" "${MAKEFILE}"
do
    [ -s "${file}" ] || {
        echo "FAIL: missing final hardening record: ${file}" >&2
        exit 1
    }
done

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(awk -F= '
    /^PLUGIN_REVISION=/ {
        gsub(/[[:space:]]/, "", $2)
        print $2
        exit
    }
' "${MAKEFILE}")

case "${revision}" in
    ''|*[!0-9]*) echo 'FAIL: invalid plugin revision' >&2; exit 1 ;;
esac

if [ "${revision}" -gt 0 ]; then
    candidate="os-zapret2-restyle-${version}_${revision}.pkg"
else
    candidate="os-zapret2-restyle-${version}.pkg"
fi

grep -Fq 'Overall status: **PENDING OWNER — SCENARIO 1 RETEST ON _6**' "${MATRIX}"

scenario_retest_count=$(awk -F'|' '
    $2 ~ /^[[:space:]]*1[[:space:]]*$/ &&
    $6 ~ /^[[:space:]]*\*\*PENDING OWNER — RETEST REQUIRED\*\*[[:space:]]*$/ { count++ }
    END { print count + 0 }
' "${MATRIX}")
[ "${scenario_retest_count}" -eq 1 ] || {
    echo "FAIL: expected scenario 1 to be the single owner-retest row, found ${scenario_retest_count}" >&2
    exit 1
}

scenario_blocked_count=$(awk -F'|' '
    $2 ~ /^[[:space:]]*[0-9]+[[:space:]]*$/ &&
    $6 ~ /^[[:space:]]*\*\*BLOCKED BY #1\*\*[[:space:]]*$/ { count++ }
    END { print count + 0 }
' "${MATRIX}")
[ "${scenario_blocked_count}" -eq 17 ] || {
    echo "FAIL: expected 17 rows blocked by scenario 1, found ${scenario_blocked_count}" >&2
    exit 1
}

grep -Fq 'Required package ABI: `FreeBSD:15:amd64`' "${MATRIX}"
grep -Fq "Current corrective candidate: \`${candidate}\`" "${MATRIX}"
grep -Fq 'Latest tested package: `os-zapret2-restyle-0.3.3_5.pkg`' "${MATRIX}"
! grep -Fq 'Current corrective candidate: `os-zapret2-restyle-0.3.2_46.pkg`' "${MATRIX}"
grep -Fq 'Architecture / ABI evidence: `docs/verification/evidence/2026-08-06-v0.3.3_1-installation.md`' "${MATRIX}"
grep -Fq 'Installation and service baseline for `0.3.3_1`: **PASS**.' "${MATRIX}"
grep -Fq '2026-08-06-v0.3.3_1-scenario-01-stage10-failure.md' "${MATRIX}"
grep -Fq '2026-08-06-v0.3.3_2-scenario-01-semantic-inspector-binding.md' "${MATRIX}"
grep -Fq '2026-08-06-v0.3.3_4-scenario-01-pidfile-eof.md' "${MATRIX}"
grep -Fq '2026-08-07-v0.3.3_5-scenario-01-candidate-runtime-restore-failure.md' "${MATRIX}"
grep -Fq 'The `_6` source corrective sequence for those later failures is now complete in `main`:' "${MATRIX}"
grep -Fq 'Scenario 1 is therefore pending owner retest on `_6`; dependent scenarios remain blocked until #1 passes.' "${MATRIX}"
grep -Fq 'artifact `8980876980`' "${MATRIX}"
grep -Fq 'Post-merge `main` CI run `31144323095` also passed.' "${MATRIX}"

grep -Fq 'Architecture   : FreeBSD:15:amd64' "${INSTALL_EVIDENCE}"
grep -Fq 'Version        : 0.3.3_1' "${INSTALL_EVIDENCE}"
grep -Fq 'Zapret2 service running after forced installation: **PASS**' "${INSTALL_EVIDENCE}"
grep -Fq 'Strategy Lab live scenarios: **NOT YET EXECUTED**' "${INSTALL_EVIDENCE}"

grep -Fq 'child_running": false' "${FAILURE_EVIDENCE}"
grep -Fq 'supervisor_running": false' "${FAILURE_EVIDENCE}"
grep -Fq 'This record is a failed live attempt, not a scenario PASS.' "${FAILURE_EVIDENCE}"

grep -Fq 'CHILD_MATCH=true' "${BINDING_EVIDENCE}"
grep -Fq 'SUPERVISOR_MATCH=true' "${BINDING_EVIDENCE}"
grep -Fq '"child_running":false,"supervisor_running":false' "${BINDING_EVIDENCE}"
grep -Fq 'overwrote `STRATEGY_LAB_SEMANTIC_PS_BIN` with the direct `/bin/ps` default' "${BINDING_EVIDENCE}"
grep -Fq 'Status: **FAILED ATTEMPT — NOT A SCENARIO PASS**' "${BINDING_EVIDENCE}"

grep -Fq 'PID files written by FreeBSD `daemon(8)` may end at EOF without a trailing newline' "${PIDFILE_EVIDENCE}"
grep -Fq 'IFS= read -r _strategy_lab_semantic_pid' "${PIDFILE_EVIDENCE}"
grep -Fq '"child_running":false,"supervisor_running":false' "${PIDFILE_EVIDENCE}"
grep -Fq 'Status: **FAILED ATTEMPT — NOT A SCENARIO PASS**' "${PIDFILE_EVIDENCE}"

grep -Fq '"state":"RUNNING","child_running":true,"supervisor_running":true' "${RESTORE_EVIDENCE}"
grep -Fq 'Temporary candidate runtime failed internally.' "${RESTORE_EVIDENCE}"
grep -Fq 'RESTORE_FAILED' "${RESTORE_EVIDENCE}"
grep -Fq '"state":"INCOMPLETE","child_running":false,"supervisor_running":false' "${RESTORE_EVIDENCE}"
grep -Fq 'Scenario 1 remains **FAILED / PENDING CORRECTION** for `_5`.' "${RESTORE_EVIDENCE}"

grep -Fq 'Standard blocked domain, initial Zapret2 RUNNING' "${MATRIX}"
grep -Fq 'Standard blocked domain, initial Zapret2 STOPPED' "${MATRIX}"
grep -Fq 'Generic UDP port and payload' "${MATRIX}"
grep -Fq 'User cancellation after service stop' "${MATRIX}"
grep -Fq 'Hard whole-worker timeout' "${MATRIX}"
grep -Fq 'Circular stale-worker recovery' "${MATRIX}"
grep -Fq 'Settings Apply during automated Strategy Lab' "${MATRIX}"
grep -Fq '| 15 | Diagnostics page reload |' "${MATRIX}"
grep -Fq 'reload after completed/error work opens the initial idle view without deleting retained evidence or starting a new job' "${MATRIX}"
grep -Fq 'Russian and English presentation' "${MATRIX}"
grep -Fq 'Retention with reduced test limits' "${MATRIX}"
grep -Fq 'Reboot after clean terminal completion' "${MATRIX}"
grep -Fq 'Stable release preparation and pkg-repository promotion remain blocked until every required row is marked `PASS` by the owner' "${MATRIX}"
grep -Fq 'The matrix contains no successful live scenario PASS claim yet.' "${MATRIX}"

if grep -Eq '^Overall status:.*PASS|\|[[:space:]]*\*\*PASS\*\*[[:space:]]*\|$' "${MATRIX}"; then
    echo 'FAIL: live matrix contains an unsupported scenario PASS claim' >&2
    exit 1
fi

grep -Fq 'Status: **COMPLETE**' "${CLOSURE}"
grep -Fq 'Status: **COMPLETE IN REVISION 47**' "${CLOSURE}"
grep -Fq 'Status: **PENDING OWNER**' "${CLOSURE}"
grep -Fq 'Status: **BLOCKED ON LIVE MATRIX**' "${CLOSURE}"
grep -Fq 'No live PASS is inferred from CI' "${CLOSURE}"
grep -Fq 'STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md' "${STATE}"
grep -Fq 'STRATEGY_LAB_HARDENING_CLOSURE.md' "${STATE}"
grep -Fq 'STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md' "${INDEX}"
grep -Fq 'STRATEGY_LAB_HARDENING_CLOSURE.md' "${INDEX}"
grep -Fq '2026-08-07-v0.3.3_6-repository-reconciliation.md' "${INDEX}"

echo 'PASS: final records preserve failed live evidence, require scenario 1 owner retest, and block dependents without unsupported PASS claims'
