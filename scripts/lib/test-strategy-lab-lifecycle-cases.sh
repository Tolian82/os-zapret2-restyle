#!/bin/sh

# RUNNING -> STOPPED during the job -> RUNNING after mandatory stage 90.
printf '%s\n' RUNNING > "${STATE_FILE}"
: > "${CALLS_FILE}"
job=$(start_job telegram.org en)
wait_for_state "${job}" completed
result=$(launcher result "${job}")
printf '%s\n' "${result}" | jq -e '.state=="completed" and .outcome=="NO_CANDIDATE" and .initial_service_state=="RUNNING"' >/dev/null ||
    fail "valid empty shortlist was not classified as NO_CANDIDATE"
printf '%s\n' "${result}" | jq -e '.stages[] | select(.number=="10" and .status=="PASS")' >/dev/null ||
    fail "snapshot stage did not pass"
printf '%s\n' "${result}" | jq -e '.stages[] | select(.number=="20" and .status=="PASS")' >/dev/null ||
    fail "service-stop stage did not pass"
printf '%s\n' "${result}" | jq -e '.stages[] | select(.number=="90" and .status=="PASS")' >/dev/null ||
    fail "restore stage did not pass"
[ "$(cat "${STATE_FILE}")" = RUNNING ] || fail "running service was not restored"
[ "$(cat "${CALLS_FILE}")" = "stop
start" ] || fail "running lifecycle did not stop then start exactly once"

# STOPPED -> STOPPED, without an accidental start.
printf '%s\n' STOPPED > "${STATE_FILE}"
: > "${CALLS_FILE}"
job=$(start_job stopped.example en)
wait_for_state "${job}" completed
result=$(launcher result "${job}")
printf '%s\n' "${result}" | jq -e '.initial_service_state=="STOPPED"' >/dev/null ||
    fail "stopped-state snapshot was not recorded"
[ "$(cat "${STATE_FILE}")" = STOPPED ] || fail "stopped service was promoted"
[ ! -s "${CALLS_FILE}" ] || fail "stopped service received lifecycle mutations"

# Cancel after service stop: skipped stages retain exact Russian text, stage 90 restores.
printf '%s\n' RUNNING > "${STATE_FILE}"
: > "${CALLS_FILE}"
WORKER_HOLD_SECONDS=10
export WORKER_HOLD_SECONDS
job=$(start_job cancel.example ru)
attempts=0
while [ "$(cat "${STATE_FILE}")" != STOPPED ] && [ "${attempts}" -lt 20 ]
do
    sleep 1
    attempts=$((attempts + 1))
done
[ "$(cat "${STATE_FILE}")" = STOPPED ] || fail "cancel test never reached stopped state"
busy=$(launcher start second.example standard en)
printf '%s\n' "${busy}" | jq -e '.status=="busy" and .job_id=="'"${job}"'"' >/dev/null ||
    fail "second start did not report the active job"
launcher cancel "${job}" >/dev/null
wait_for_state "${job}" completed
result=$(launcher result "${job}")
printf '%s\n' "${result}" | jq -e '.outcome=="PARTIAL" and .cancel_requested==true' >/dev/null ||
    fail "cancel did not return a partial result"
printf '%s\n' "${result}" | jq -e '[.stages[] | select(.number=="30" or .number=="40" or .number=="50" or .number=="60" or .number=="70" or .number=="80" or .number=="85")] | all(.status=="SKIPPED" and .message=="SKIPPED — отменено")' >/dev/null ||
    fail "canceled unexecuted stages do not use the approved Russian text"
printf '%s\n' "${result}" | jq -e '.stages[] | select(.number=="90" and .status=="PASS")' >/dev/null ||
    fail "cancel did not execute mandatory restoration"
[ "$(cat "${STATE_FILE}")" = RUNNING ] || fail "cancel did not restore running state"

# English cancellation uses the exact approved spelling and still restores.
printf '%s\n' RUNNING > "${STATE_FILE}"
: > "${CALLS_FILE}"
job=$(start_job english-cancel.example en)
attempts=0
while [ "$(cat "${STATE_FILE}")" != STOPPED ] && [ "${attempts}" -lt 20 ]
do
    sleep 1
    attempts=$((attempts + 1))
done
launcher cancel "${job}" >/dev/null
wait_for_state "${job}" completed
result=$(launcher result "${job}")
printf '%s\n' "${result}" | jq -e '[.stages[] | select(.number=="30" or .number=="40" or .number=="50" or .number=="60" or .number=="70" or .number=="80" or .number=="85")] | all(.status=="SKIPPED" and .message=="SKIPPED — canseled")' >/dev/null ||
    fail "canceled unexecuted stages do not use the approved English text"
[ "$(cat "${STATE_FILE}")" = RUNNING ] || fail "English cancel did not restore running state"

# Restore failure is explicit and never presented as a normal partial result.
unset WORKER_HOLD_SECONDS
printf '%s\n' RUNNING > "${STATE_FILE}"
: > "${CALLS_FILE}"
: > "${START_FAIL_FILE}"
job=$(start_job restore-failure.example en)
wait_for_state "${job}" error
result=$(launcher result "${job}")
printf '%s\n' "${result}" | jq -e '.state=="error" and .outcome=="RESTORE_FAILED"' >/dev/null ||
    fail "restore failure was not an explicit terminal error"
printf '%s\n' "${result}" | jq -e '.stages[] | select(.number=="90" and .status=="FAIL")' >/dev/null ||
    fail "restore stage did not fail"
rm -f "${START_FAIL_FILE}"

# Incomplete initial state aborts before mutation and leaves stage 90 as a no-op success.
printf '%s\n' INCOMPLETE > "${STATE_FILE}"
: > "${CALLS_FILE}"
job=$(start_job incomplete.example en)
wait_for_state "${job}" error
result=$(launcher result "${job}")
printf '%s\n' "${result}" | jq -e '.state=="error" and .outcome=="ERROR" and .initial_service_state==""' >/dev/null ||
    fail "incomplete initial state did not fail closed as a terminal error"
printf '%s\n' "${result}" | jq -e '.stages[] | select(.number=="10" and .status=="FAIL")' >/dev/null ||
    fail "incomplete snapshot stage did not fail"
[ ! -s "${CALLS_FILE}" ] || fail "incomplete initial state was mutated"

# The real service entry point owns the shared fd 9 transaction and permits only
# inherited internal lifecycle calls. Backend behavior is mocked, not the lock path.
SERVICE_ROOT="${TMP_ROOT}/service-root"
SERVICE_BACKEND="${SERVICE_ROOT}/backend"
SERVICE_WORKER="${SERVICE_ROOT}/strategy_lab_worker.sh"
SERVICE_LOCK="${TMP_ROOT}/real-service.lock"
mkdir -p "${SERVICE_BACKEND}"
for module in common config parser registry storage targets target_mode profile_normalizer profile_pipeline exclude blobs ports firewall generator validator atomic stage launcher supervisor
do
    : > "${SERVICE_BACKEND}/${module}.sh"
done
cat > "${SERVICE_BACKEND}/orchestrator.sh" <<'MOCK'
orchestrator_native_status()
{
    case "$(cat "${MOCK_STATE_FILE}")" in
        RUNNING) return 0 ;;
        STOPPED) return 1 ;;
        *) return 2 ;;
    esac
}
orchestrator_native_stop()
{
    printf '%s\n' service-stop >> "${MOCK_CALLS_FILE}"
    printf '%s\n' STOPPED > "${MOCK_STATE_FILE}"
}
orchestrator_native_start() { return 1; }
orchestrator_native_reconfigure() { return 1; }
orchestrator_runtime_failure() { return 0; }
MOCK
cat > "${SERVICE_WORKER}" <<'MOCK'
#!/bin/sh
[ "${STRATEGY_LAB_LIFECYCLE_OWNER:-0}" = 1 ] || exit 91
( : >&9 ) 2>/dev/null || exit 92
"${STRATEGY_LAB_SERVICE_SCRIPT}" strategy-lab-status || exit 93
"${STRATEGY_LAB_SERVICE_SCRIPT}" strategy-lab-stop || exit 94
exit 0
MOCK
chmod +x "${SERVICE_WORKER}"
printf '%s\n' RUNNING > "${STATE_FILE}"
: > "${CALLS_FILE}"
SCRIPT_DIR="${SERVICE_ROOT}" \
BACKEND_DIR="${SERVICE_BACKEND}" \
LOCKF_BIN="${MOCK_BIN}/lockf" \
LIFECYCLE_LOCK_FILE="${SERVICE_LOCK}" \
STRATEGY_LAB_WORKER="${SERVICE_WORKER}" \
MOCK_STATE_FILE="${STATE_FILE}" \
MOCK_CALLS_FILE="${CALLS_FILE}" \
    "${SERVICE_SOURCE}" strategy-lab job.ServiceLock
[ "$(cat "${STATE_FILE}")" = STOPPED ] || fail "service-owned transaction did not run under inherited lock"
grep -Fqx service-stop "${CALLS_FILE}" || fail "internal stop action was not dispatched"
set +e
SCRIPT_DIR="${SERVICE_ROOT}" BACKEND_DIR="${SERVICE_BACKEND}" \
LOCKF_BIN="${MOCK_BIN}/lockf" LIFECYCLE_LOCK_FILE="${SERVICE_LOCK}" \
STRATEGY_LAB_WORKER="${SERVICE_WORKER}" MOCK_STATE_FILE="${STATE_FILE}" \
MOCK_CALLS_FILE="${CALLS_FILE}" \
    "${SERVICE_SOURCE}" strategy-lab-stop >/dev/null 2>&1
unauthorized_status=$?
set -e
[ "${unauthorized_status}" -eq 77 ] || fail "internal lifecycle action worked without inherited lock ownership"

latest=$(launcher status)
printf '%s\n' "${latest}" | jq -e --arg job "${job}" '.job_id==$job' >/dev/null ||
    fail "latest persisted job was not recovered"
mv "${RUN_DIR}/jobs" "${RUN_DIR}/jobs.saved"
mkdir -p "${RUN_DIR}/jobs"
idle=$(launcher status)
printf '%s\n' "${idle}" | jq -e '.status=="idle"' >/dev/null || fail "empty job store did not report idle"
rm -rf "${RUN_DIR}/jobs"
mv "${RUN_DIR}/jobs.saved" "${RUN_DIR}/jobs"
set +e
invalid=$(launcher start 'bad/target' standard en 2>&1)
invalid_status=$?
set -e
[ "${invalid_status}" -eq 64 ] || fail "unsafe target was not rejected"
printf '%s\n' "${invalid}" | grep -Fq 'invalid target' || fail "invalid target reason is missing"

sh -n "${LAUNCHER}"
sh -n "${WORKER}"
sh -n "${MODULE_DIR}/lifecycle.sh"
sh -n "${MODULE_DIR}/state.sh"
sh -n "${MODULE_DIR}/worker_messages.sh"
sh -n "${MODULE_DIR}/worker_result.sh"
sh -n "${MODULE_DIR}/worker_control.sh"
sh -n "${MODULE_DIR}/worker_flow.sh"
sh -n "${SERVICE_SOURCE}"

grep -Fq 'TRANSACTION_SCRIPT="${TRANSACTION_SCRIPT:-${SCRIPT_DIR}/zapret_service.sh}"' "${LAUNCHER}" ||
    fail "launcher does not enter the service-owned lifecycle transaction"
grep -Fq 'service_with_lifecycle_lock "${STRATEGY_LAB_LOCK_TIMEOUT}"' "${SERVICE_SOURCE}" ||
    fail "Strategy Lab is not protected by the shared lifecycle lock"
grep -Fq 'strategy-lab-status|strategy-lab-evidence|strategy-lab-stop|strategy-lab-start' "${SERVICE_SOURCE}" ||
    fail "internal lock-owned service actions are missing"
grep -Fq 'STRATEGY_LAB_LIFECYCLE_OWNER=1' "${SERVICE_SOURCE}" ||
    fail "inherited lifecycle ownership is not marked"
grep -Fq '( : >&9 ) 2>/dev/null' "${SERVICE_SOURCE}" ||
    fail "internal service actions do not require inherited lock descriptor 9"
grep -Fq 'RESTORE_FAILED' "${MODULE_DIR}/worker_messages.sh" || fail "worker has no explicit restore failure result"

echo 'PASS: Strategy Lab lifecycle snapshot, stop, cancel, cleanup, and restoration contract'
