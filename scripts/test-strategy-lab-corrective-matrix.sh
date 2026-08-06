#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SELF="${ROOT_DIR}/scripts/test-strategy-lab-corrective-matrix.sh"
DOMAIN_TEST="${ROOT_DIR}/scripts/test-domain-diagnostics-contract.sh"

[ -s "${DOMAIN_TEST}" ] || {
    echo 'FAIL: focused domain diagnostics contract is missing' >&2
    exit 1
}

# Validate every Strategy Lab test before execution and run every discovered
# focused contract exactly once. The matrix itself is the only exclusion.
find "${ROOT_DIR}/scripts" -maxdepth 1 -type f -name 'test-strategy-lab-*.sh' |
    LC_ALL=C sort |
    while IFS= read -r test_script
    do
        [ "${test_script}" = "${SELF}" ] && continue
        sh -n "${test_script}"
    done

printf '%s\n' 'MATRIX: domain-diagnostics-contract'
sh "${DOMAIN_TEST}"

find "${ROOT_DIR}/scripts" -maxdepth 1 -type f -name 'test-strategy-lab-*.sh' |
    LC_ALL=C sort |
    while IFS= read -r test_script
    do
        [ "${test_script}" = "${SELF}" ] && continue
        test_name=$(basename "${test_script}" .sh)
        printf 'MATRIX: %s\n' "${test_name#test-strategy-lab-}"
        sh "${test_script}"
    done

echo 'PASS: final Strategy Lab corrective matrix completed without duplicate orchestration'
