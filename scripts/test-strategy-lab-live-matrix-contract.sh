#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MATRIX="${ROOT_DIR}/docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md"
CLOSURE="${ROOT_DIR}/docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md"
STATE="${ROOT_DIR}/docs/PROJECT_STATE.md"
INDEX="${ROOT_DIR}/docs/INDEX.md"

for file in "${MATRIX}" "${CLOSURE}" "${STATE}" "${INDEX}"
do
    [ -s "${file}" ] || {
        echo "FAIL: missing final hardening record: ${file}" >&2
        exit 1
    }
done

grep -Fq 'Overall status: **PENDING OWNER**' "${MATRIX}"
[ "$(grep -c '\*\*PENDING OWNER\*\*' "${MATRIX}")" -ge 19 ]

grep -Fq 'Required package ABI: `FreeBSD:15:amd64`' "${MATRIX}"
grep -Fq 'Candidate package: `os-zapret2-restyle-0.3.2_47.pkg`' "${MATRIX}"
! grep -Fq 'Candidate package: `os-zapret2-restyle-0.3.2_46.pkg`' "${MATRIX}"
grep -Fq 'Standard blocked domain, initial Zapret2 RUNNING' "${MATRIX}"
grep -Fq 'Standard blocked domain, initial Zapret2 STOPPED' "${MATRIX}"
grep -Fq 'Generic UDP port and payload' "${MATRIX}"
grep -Fq 'User cancellation after service stop' "${MATRIX}"
grep -Fq 'Hard whole-worker timeout' "${MATRIX}"
grep -Fq 'Circular stale-worker recovery' "${MATRIX}"
grep -Fq 'Settings Apply during automated Strategy Lab' "${MATRIX}"
grep -Fq 'Diagnostics page reload after terminal result' "${MATRIX}"
grep -Fq 'Russian and English presentation' "${MATRIX}"
grep -Fq 'Retention with reduced test limits' "${MATRIX}"
grep -Fq 'Reboot after clean terminal completion' "${MATRIX}"
grep -Fq 'Release preparation is blocked until every required row is marked `PASS` by the owner' "${MATRIX}"
grep -Fq 'The current matrix contains no live PASS claims.' "${MATRIX}"

# The prepared matrix must not contain a claimed PASS result before owner evidence exists.
if grep -Eq '^Overall status:.*PASS|\|[[:space:]]*\*\*PASS\*\*[[:space:]]*\|$' "${MATRIX}"; then
    echo 'FAIL: live matrix contains an unsupported PASS claim' >&2
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

echo 'PASS: final records require a FreeBSD 15 candidate and distinguish complete source/CI work from pending live OPNsense evidence'
