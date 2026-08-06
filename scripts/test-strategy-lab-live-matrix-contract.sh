#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MATRIX="${ROOT_DIR}/docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md"
INSTALL_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-06-v0.3.3_1-installation.md"
FAILURE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-06-v0.3.3_1-scenario-01-stage10-failure.md"
BINDING_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-06-v0.3.3_2-scenario-01-semantic-inspector-binding.md"
CLOSURE="${ROOT_DIR}/docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md"
STATE="${ROOT_DIR}/docs/PROJECT_STATE.md"
INDEX="${ROOT_DIR}/docs/INDEX.md"
VERSION_FILE="${ROOT_DIR}/VERSION"
MAKEFILE="${ROOT_DIR}/Makefile"

for file in "${MATRIX}" "${INSTALL_EVIDENCE}" "${FAILURE_EVIDENCE}" \
    "${BINDING_EVIDENCE}" "${CLOSURE}" "${STATE}" "${INDEX}" \
    "${VERSION_FILE}" "${MAKEFILE}"
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

grep -Fq 'Overall status: **PENDING OWNER**' "${MATRIX}"
scenario_pending_count=$(awk -F'|' '
    $2 ~ /^[[:space:]]*[0-9]+[[:space:]]*$/ &&
    $6 ~ /^[[:space:]]*\*\*PENDING OWNER\*\*[[:space:]]*$/ { count++ }
    END { print count + 0 }
' "${MATRIX}")
[ "${scenario_pending_count}" -eq 18 ] || {
    echo "FAIL: expected 18 pending scenario rows, found ${scenario_pending_count}" >&2
    exit 1
}

grep -Fq 'Required package ABI: `FreeBSD:15:amd64`' "${MATRIX}"
grep -Fq "Candidate package: \`${candidate}\`" "${MATRIX}"
! grep -Fq 'Candidate package: `os-zapret2-restyle-0.3.2_46.pkg`' "${MATRIX}"
grep -Fq 'Architecture / ABI evidence: `docs/verification/evidence/2026-08-06-v0.3.3_1-installation.md`' "${MATRIX}"
grep -Fq 'Installation and service baseline for `0.3.3_1`: **PASS**.' "${MATRIX}"
grep -Fq '2026-08-06-v0.3.3_1-scenario-01-stage10-failure.md' "${MATRIX}"
grep -Fq '2026-08-06-v0.3.3_2-scenario-01-semantic-inspector-binding.md' "${MATRIX}"
grep -Fq 'Scenario 1 remains pending and must be repeated on `0.3.3_4`.' "${MATRIX}"
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
grep -Fq 'The current matrix contains no live scenario PASS claims.' "${MATRIX}"

# Installation identity may be PASS after owner evidence, but no scenario row may
# be marked PASS before that scenario has its own linked evidence.
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

echo 'PASS: final records use the current FreeBSD 15 candidate, preserve populated owner evidence, and keep all 18 live scenarios pending'
