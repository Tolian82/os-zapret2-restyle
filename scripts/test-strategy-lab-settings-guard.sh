#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
GUARD="${SCRIPT_DIR}/strategy_lab_guard.sh"
CONTROLLER="${ROOT_DIR}/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SettingsController.php"
ACTIONS="${ROOT_DIR}/src/opnsense/service/conf/actions.d/actions_zapret.conf"
TMP=$(mktemp -d /tmp/strategy-lab-settings-guard.XXXXXX)
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
mkdir -p "${TMP}/bin" "${TMP}/run/jobs" "${TMP}/log"

cat > "${TMP}/bin/lockf" <<'MOCK'
#!/bin/sh
[ "${MOCK_LOCK_BUSY:-0}" -eq 0 ]
MOCK
chmod 0755 "${TMP}/bin/lockf"

run_guard()
{
    STRATEGY_LAB_RUN_DIR="${TMP}/run" \
    STRATEGY_LAB_LOG_DIR="${TMP}/log" \
    STRATEGY_LAB_JOBS_DIR="${TMP}/run/jobs" \
    STRATEGY_LAB_JQ="$(command -v jq)" \
    LOCKF_BIN="${TMP}/bin/lockf" \
    LIFECYCLE_LOCK_FILE="${TMP}/lifecycle.lock" \
    MOCK_LOCK_BUSY="${MOCK_LOCK_BUSY:-0}" \
    SCRIPT_DIR="${SCRIPT_DIR}" \
    MODULE_DIR="${SCRIPT_DIR}/strategy_lab" \
        sh "${GUARD}"
}

idle=$(run_guard)
printf '%s\n' "${idle}" | jq -e '.status=="ok" and .busy==false and .owner=="none"' >/dev/null

mkdir -p "${TMP}/run/jobs/job.auto"
printf '%s\n' job.auto > "${TMP}/run/active.job"
printf '%s\n' '{"state":"running"}' > "${TMP}/run/jobs/job.auto/status.json"
automated=$(run_guard)
printf '%s\n' "${automated}" | jq -e '.busy==true and .owner=="automated" and .owner_id=="job.auto" and .state=="running"' >/dev/null
rm -f "${TMP}/run/active.job"

mkdir -p "${TMP}/run/circular/sessions/job.circle"
printf '%s\n' job.circle > "${TMP}/run/circular/active.session"
printf '%s\n' '{"state":"restore_failed"}' > "${TMP}/run/circular/sessions/job.circle/state.json"
circular=$(run_guard)
printf '%s\n' "${circular}" | jq -e '.busy==true and .owner=="circular" and .owner_id=="job.circle" and .state=="restore_failed"' >/dev/null
rm -f "${TMP}/run/circular/active.session"

MOCK_LOCK_BUSY=1 locked=$(run_guard)
printf '%s\n' "${locked}" | jq -e '.busy==true and .owner=="lifecycle" and .reason=="lifecycle_lock_busy"' >/dev/null

[ "$(grep -c '\$this->assertLifecycleAvailable();' "${CONTROLLER}")" -eq 2 ]
grep -Fq 'public function lifecycleAction(): array' "${CONTROLLER}"
grep -Fq "configdRun('zapret strategy_lab_guard')" "${CONTROLLER}"
grep -Fq 'Settings cannot be applied while Strategy Lab controls Zapret2' "${CONTROLLER}"
grep -Fq '[strategy_lab_guard]' "${ACTIONS}"
grep -Fq 'strategy_lab_guard.sh' "${ACTIONS}"
sh -n "${GUARD}"
php -l "${CONTROLLER}" >/dev/null
echo 'PASS: Settings Apply is rejected while automated, circular, or lifecycle ownership is active'
