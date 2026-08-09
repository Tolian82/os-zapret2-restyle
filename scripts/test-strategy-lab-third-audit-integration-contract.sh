#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MATRIX="${ROOT_DIR}/scripts/test-strategy-lab-corrective-matrix.sh"
E2E="${ROOT_DIR}/scripts/test-strategy-lab-e2e.sh"
STALE="${ROOT_DIR}/scripts/test-strategy-lab-stale-worker-recovery.sh"
STALE_CONTRACT="${ROOT_DIR}/scripts/test-strategy-lab-stale-recovery-contract.sh"
CIRCULAR_OWNER="${ROOT_DIR}/scripts/test-strategy-lab-circular-owner.sh"
CIRCULAR_CONTRACT="${ROOT_DIR}/scripts/test-strategy-lab-circular-recovery-contract.sh"
SHORTLIST="${ROOT_DIR}/scripts/test-strategy-lab-unified-shortlist.sh"
FINAL_RESULTS="${ROOT_DIR}/scripts/test-strategy-lab-python-final-results.sh"
STATE_RACE="${ROOT_DIR}/scripts/test-strategy-lab-state-race.sh"

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

for file in \
    "${MATRIX}" "${E2E}" "${STALE}" "${STALE_CONTRACT}" \
    "${CIRCULAR_OWNER}" "${CIRCULAR_CONTRACT}" "${SHORTLIST}" \
    "${FINAL_RESULTS}" "${STATE_RACE}"
do
    [ -s "${file}" ] || fail "missing third-audit integration surface: ${file}"
    sh -n "${file}"
done

# The authoritative matrix discovers focused Strategy Lab regressions directly.
# These third-audit component tests must not be delegated elsewhere or executed twice.
grep -Fq "find \"\${ROOT_DIR}/scripts\" -maxdepth 1 -type f -name 'test-strategy-lab-*.sh'" "${MATRIX}"
for test_name in \
    stale-worker-recovery stale-recovery-contract circular-owner \
    circular-recovery-contract unified-shortlist state-race python-final-results
do
    if grep -Fq "test-strategy-lab-${test_name}.sh" "${MATRIX}"; then
        fail "${test_name} must be discovered directly by the canonical matrix, not separately delegated"
    fi
done

# Base e2e owns the product-level invariants that must survive every corrective path.
grep -Fq 'run_job success standard RUNNING completed SUCCESS' "${E2E}"
grep -Fq 'run_job success standard STOPPED completed SUCCESS' "${E2E}"
grep -Fq 'run_job restore_failure standard RUNNING error RESTORE_FAILED' "${E2E}"
grep -Fq "fail 'saved Traffic Strategy changed'" "${E2E}"
grep -Fq 'strategy_lab_circular_start' "${E2E}"
grep -Fq 'strategy_lab_circular_stop' "${E2E}"
grep -Fq "fail 'active automated job marker remains'" "${E2E}"
grep -Fq "fail 'candidate pidfile residue remains'" "${E2E}"
grep -Fq "fail 'temporary integration process remains'" "${E2E}"

# SL3-001: ordinary stale recovery covers STOPPED, RUNNING mismatch, and failure.
grep -Fq 'make_job job.good STOPPED' "${STALE}"
grep -Fq 'make_job job.bad RUNNING' "${STALE}"
grep -Fq 'make_job job.fail RUNNING' "${STALE}"
grep -Fq '.restoration.strategy_unchanged==false' "${STALE}"
grep -Fq '.outcome=="RESTORE_FAILED"' "${STALE}"
grep -Fq '^strategy-lab-recover job\.' "${STALE}" || fail 'stale recovery no longer proves lifecycle-owned delegation'

# SL3-005: the synchronous recovery envelope is strictly increasing.
grep -Fq 'configd_seconds=180' "${STALE_CONTRACT}"
grep -Fq 'mvc_seconds=190' "${STALE_CONTRACT}"
grep -Fq 'browser_seconds=200' "${STALE_CONTRACT}"
grep -Fq '[ "${configd_seconds}" -lt "${mvc_seconds}" ]' "${STALE_CONTRACT}"
grep -Fq '[ "${mvc_seconds}" -lt "${browser_seconds}" ]' "${STALE_CONTRACT}"

# SL3-002: circular stale recovery delegates to the same lifecycle-owned semantic transaction.
grep -Fq 'strategy-lab-recover' "${CIRCULAR_OWNER}"
grep -Fq 'STRATEGY_LAB_LIFECYCLE_OWNER=1' "${CIRCULAR_OWNER}"
grep -Fq 'MOCK_RECOVERY_MODE=inconsistent' "${CIRCULAR_OWNER}"
grep -Fq '.state=="restore_failed"' "${CIRCULAR_OWNER}"
grep -Fq 'must contain the 180-second circular stale-recovery envelope' "${CIRCULAR_CONTRACT}"
grep -Fq 'private const BACKEND_TIMEOUT_SECONDS = 190;' "${CIRCULAR_CONTRACT}"
grep -Fq 'timeout:200000' "${CIRCULAR_CONTRACT}"

# SL3-003: Python verifies every multi-protocol finalist while publishing the
# normal three-winner cap; circular consumes only the frozen TLS 1.3 subset.
grep -Fq 'assert shortlist["count"] == 3' "${FINAL_RESULTS}"
grep -Fq 'assert shortlist["circular_count"] == 3' "${FINAL_RESULTS}"
grep -Fq '["tls13","tls12","http"]' "${FINAL_RESULTS}"
grep -Fq 'assert len(calls) == 21' "${FINAL_RESULTS}"
grep -Fq 'strategy_lab_circular_session_create job.test' "${SHORTLIST}"
grep -Fq 'strategy_lab_circular_build_profile "${CIRCULAR_SESSION_ID}"' "${SHORTLIST}"
grep -Fq 'private circular consumer mutated the parent Python-published shortlist' "${SHORTLIST}"
grep -Fq 'private circular profile does not contain exactly three frozen TLS 1.3 strategies' "${SHORTLIST}"

# SL3-004: cancel/skip/finalize state mutations share one Python lock/revision owner after
# the shell stage-machine retirement.
grep -Fq 'strategy_lab_request_cancel job.race cancel &' "${STATE_RACE}"
grep -Fq 'strategy_lab_skip_unfinished job.race skipped &' "${STATE_RACE}"
grep -Fq '.cancel_requested_at==$requested_at' "${STATE_RACE}"
grep -Fq '.revision==28' "${STATE_RACE}"
grep -Fq 'strategy_lab_state_python skip-unfinished' "${STATE_RACE}"
grep -Fq '[ ! -e "${RETIRED_STAGE_MACHINE}" ]' "${STATE_RACE}"
! grep -Fq 'strategy_lab_state_transform' "${STATE_RACE}"

# The integration contract binds coverage only; it must not recursively execute the matrix.
if grep -Eq '^[[:space:]]*sh[[:space:]]+"?\$\{MATRIX\}' "$0"; then
    fail 'third-audit integration contract recursively invokes the authoritative matrix'
fi

printf '%s\n' 'PASS: third-audit corrected paths are bound to one canonical matrix with integrated lifecycle, Python final shortlist, Python-owned race persistence, timeout, immutability, and cleanup coverage'
