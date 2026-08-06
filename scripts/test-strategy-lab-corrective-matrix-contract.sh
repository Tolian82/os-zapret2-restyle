#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MATRIX="${ROOT_DIR}/scripts/test-strategy-lab-corrective-matrix.sh"
DOMAIN="${ROOT_DIR}/scripts/test-domain-diagnostics-contract.sh"
WORKFLOW="${ROOT_DIR}/.github/workflows/ci.yml"

[ -s "${MATRIX}" ]
[ -s "${DOMAIN}" ]
[ -s "${WORKFLOW}" ]

grep -Fq "find \"\${ROOT_DIR}/scripts\" -maxdepth 1 -type f -name 'test-strategy-lab-*.sh'" "${MATRIX}"
grep -Fq '[ "${test_script}" = "${SELF}" ] && continue' "${MATRIX}"
grep -Fq "sh \"\${DOMAIN_TEST}\"" "${MATRIX}"
[ "$(grep -c "sh \"\${DOMAIN_TEST}\"" "${MATRIX}")" -eq 1 ]

# The focused domain contract must not recursively orchestrate Strategy Lab tests.
if grep -Fq 'test-strategy-lab-' "${DOMAIN}"; then
    echo 'FAIL: focused domain diagnostics test still orchestrates Strategy Lab tests' >&2
    exit 1
fi

# CI invokes the canonical matrix exactly once and does not bypass it with the old wrapper.
grep -Fq 'name: Test Strategy Lab corrective matrix' "${WORKFLOW}"
grep -Fq 'run: sh scripts/test-strategy-lab-corrective-matrix.sh' "${WORKFLOW}"
[ "$(grep -c 'run: sh scripts/test-strategy-lab-corrective-matrix.sh' "${WORKFLOW}")" -eq 1 ]
! grep -Fq 'run: sh scripts/test-domain-diagnostics-contract.sh' "${WORKFLOW}"

grep -Fq 'scripts/test-strategy-lab-corrective-matrix.sh' "${WORKFLOW}"
grep -Fq 'scripts/test-strategy-lab-corrective-matrix-contract.sh' "${WORKFLOW}"

sh -n "${MATRIX}"
sh -n "${DOMAIN}"
echo 'PASS: CI has one nonrecursive authoritative Strategy Lab corrective matrix'
