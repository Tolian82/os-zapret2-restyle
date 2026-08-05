#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
MODULE_DIR="${SCRIPT_DIR}/strategy_lab"
SERVICE_SCRIPT="${SCRIPT_DIR}/zapret_service.sh"
WORKER_SCRIPT="${SCRIPT_DIR}/strategy_lab_circular_worker.sh"
ACTIONS="${ROOT_DIR}/src/opnsense/service/conf/actions.d/actions_zapret.conf"
TMP=$(mktemp -d /tmp/strategy-lab-circular-test.XXXXXX)
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
mkdir -p "${TMP}/run/jobs/job.test" "${TMP}/lua" "${TMP}/bin"
printf '%s\n' '-- lua' > "${TMP}/lua/zapret-auto.lua"
printf '%s\n' telegram.org web.telegram.org > "${TMP}/run/jobs/job.test/endpoints.txt"
printf '%s\n' '{"state":"completed","target_type":"ipv4"}' > "${TMP}/run/jobs/job.test/status.json"
cat > "${TMP}/run/jobs/job.test/shortlist.json" <<'JSON'
{"count":3,"items":[
 {"id":"c1","family":"multisplit","strategy":"--payload=tls_client_hello\n--lua-desync=multisplit:pos=1\n"},
 {"id":"c2","family":"fake+split","strategy":"--payload=tls_client_hello\n--lua-desync=fake:blob=fake_default_tls\n--lua-desync=multisplit:pos=host\n"},
 {"id":"c3","family":"hostfakesplit","strategy":"--payload=tls_client_hello\n--lua-desync=hostfakesplit:midhost=midsld\n"}
]}
JSON
cat > "${TMP}/bin/kldstat" <<'MOCK'
#!/bin/sh
exit 0
MOCK
cat > "${TMP}/bin/sysctl" <<'MOCK'
#!/bin/sh
printf '%s\n' 1
MOCK
cat > "${TMP}/bin/ipfw" <<'MOCK'
#!/bin/sh
log=${MOCK_IPFW_LOG}
state=${MOCK_IPFW_STATE}
printf '%s\n' "$*" >> "${log}"
case "$*" in
 *' delete '*) number=$(printf '%s\n' "$*" | awk '{print $NF}'); grep -v "^${number} " "${state}" > "${state}.tmp" || :; mv "${state}.tmp" "${state}" ;;
 *' add '*) set -- $*; while [ "$1" != add ]; do shift; done; shift; printf '%s %s\n' "$1" "$*" >> "${state}" ;;
 *' list '*) number=$(printf '%s\n' "$*" | awk '{print $NF}'); grep "^${number} " "${state}" || : ;;
esac
MOCK
chmod +x "${TMP}/bin/"*
: > "${TMP}/ipfw.log"
: > "${TMP}/ipfw.state"
export STRATEGY_LAB_JQ=$(command -v jq)
export STRATEGY_LAB_RUN_DIR="${TMP}/run" STRATEGY_LAB_JOBS_DIR="${TMP}/run/jobs"
export STRATEGY_LAB_LUA_DIR="${TMP}/lua" STRATEGY_LAB_IPFW_BIN="${TMP}/bin/ipfw"
export STRATEGY_LAB_KLDSTAT_BIN="${TMP}/bin/kldstat" STRATEGY_LAB_SYSCTL_BIN="${TMP}/bin/sysctl"
export STRATEGY_LAB_RULE_BASE=19100 STRATEGY_LAB_RULE_MAX=19131 STRATEGY_LAB_DIVERT_PORT=9989
export MOCK_IPFW_LOG="${TMP}/ipfw.log" MOCK_IPFW_STATE="${TMP}/ipfw.state"
. "${MODULE_DIR}/common.sh"
. "${MODULE_DIR}/state.sh"
. "${MODULE_DIR}/firewall.sh"
. "${MODULE_DIR}/runtime.sh"
. "${MODULE_DIR}/circular.sh"

! strategy_lab_circular_validate_job job.test
printf '%s\n' '{"state":"completed","target_type":"domain"}' > "${TMP}/run/jobs/job.test/status.json"
strategy_lab_circular_validate_job job.test
strategy_lab_circular_build_profile job.test
ARGS=$(strategy_lab_candidate_args_file job.test)
grep -Fxq -- '--lua-desync=circular:fails=1:time=60' "${ARGS}"
grep -Fxq -- '--in-range=-s34228' "${ARGS}"
grep -Fxq -- '--lua-desync=multisplit:pos=1:strategy=1' "${ARGS}"
grep -Fxq -- '--lua-desync=fake:blob=fake_default_tls:strategy=2' "${ARGS}"
grep -Fxq -- '--lua-desync=multisplit:pos=host:strategy=2' "${ARGS}"
grep -Fxq -- '--lua-desync=hostfakesplit:midhost=midsld:strategy=3' "${ARGS}"
! grep -Fq -- '--new' "${ARGS}"
printf '%s\n' 203.0.113.10 > "${TMP}/addresses.txt"
strategy_lab_circular_install_firewall "${TMP}/addresses.txt" mock0
grep -Fq 'add 19100 divert 9989 tcp from any to 203.0.113.10 443 out not diverted not sockarg xmit mock0' "${TMP}/ipfw.log"
grep -Fq 'add 19101 divert 9989 tcp from 203.0.113.10 443 to any in not diverted not sockarg recv mock0' "${TMP}/ipfw.log"
grep -Fq 'strategy-lab-circular)' "${SERVICE_SCRIPT}"
grep -Fq '[strategy_lab_circular_start]' "${ACTIONS}"
grep -Fq '[strategy_lab_circular_stop]' "${ACTIONS}"

set +e
STRATEGY_LAB_LIFECYCLE_LOCK_FAILED=1 \
SCRIPT_DIR="${SCRIPT_DIR}" MODULE_DIR="${MODULE_DIR}" \
STRATEGY_LAB_RUN_DIR="${TMP}/run" STRATEGY_LAB_JOBS_DIR="${TMP}/run/jobs" \
STRATEGY_LAB_JQ="${STRATEGY_LAB_JQ}" \
    sh "${WORKER_SCRIPT}" job.test >/dev/null 2>&1
WORKER_STATUS=$?
set -e
[ "${WORKER_STATUS}" -eq 75 ]
jq -e '.state=="error" and .reason=="lifecycle_lock"' \
    "${TMP}/run/circular/state.json" >/dev/null

echo 'PASS: Strategy Lab circular validation is domain-only, target-scoped, and fail-closed'
