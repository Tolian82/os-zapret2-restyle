#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SELF="${ROOT_DIR}/scripts/test-strategy-lab-corrective-matrix.sh"
DOMAIN_TEST="${ROOT_DIR}/scripts/test-domain-diagnostics-contract.sh"
STRATEGY_LAB_JQ=$(command -v jq)
export STRATEGY_LAB_JQ

[ -x "${STRATEGY_LAB_JQ}" ] || {
    echo 'FAIL: jq is unavailable for the Strategy Lab corrective matrix' >&2
    exit 1
}
[ -s "${DOMAIN_TEST}" ] || {
    echo 'FAIL: focused domain diagnostics contract is missing' >&2
    exit 1
}

strategy_lab_test_delegated_to_e2e()
{
    case "$(basename "$1")" in
        test-strategy-lab-active-cancel.sh|test-strategy-lab-candidate-runtime.sh|test-strategy-lab-semantic-restoration.sh|test-strategy-lab-time-budget.sh)
            return 0
            ;;
    esac
    return 1
}

# Validate every Strategy Lab test before execution. Four focused contracts are
# delegated to e2e, which invokes them once as part of its integration cleanup gate.
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
        if strategy_lab_test_delegated_to_e2e "${test_script}"; then
            printf 'MATRIX: delegated-to-e2e %s\n' "$(basename "${test_script}" .sh)"
            continue
        fi
        test_name=$(basename "${test_script}" .sh)
        printf 'MATRIX: %s\n' "${test_name#test-strategy-lab-}"
        case "${test_name}" in
            test-strategy-lab-live-matrix-contract) sh -x "${test_script}" ;;
            *) sh "${test_script}" ;;
        esac
    done

echo 'PASS: final Strategy Lab corrective matrix completed without duplicate orchestration'
