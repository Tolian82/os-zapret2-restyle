#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MODULE_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab"
SERVICE_SOURCE="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-semantic-restoration.XXXXXX")
trap 'rm -rf "${TEST_ROOT}"' EXIT HUP INT TERM

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

JOB_ID=job.SEMANTIC
JOB_DIR="${TEST_ROOT}/job"
STATUS_FILE="${JOB_DIR}/status.json"
STATE_FILE="${TEST_ROOT}/service.state"
CONFIG_FILE="${TEST_ROOT}/zapret.conf"
ARGS_FILE="${TEST_ROOT}/dvtws.args"
RULES_FILE="${TEST_ROOT}/normal.rules"
TEMP_CLEAN_FILE="${TEST_ROOT}/temporary.clean"
SERVICE="${TEST_ROOT}/service"
STRATEGY_LAB_JQ=$(command -v jq)
STRATEGY_LAB_TIMEOUT_BIN=$(command -v timeout)
STRATEGY_LAB_SERVICE_SCRIPT="${SERVICE}"
STRATEGY_LAB_STOP_TIMEOUT=2
STRATEGY_LAB_RESTORE_TIMEOUT=2
mkdir -p "${JOB_DIR}"

cat > "${SERVICE}" <<'SERVICE'
#!/bin/sh
state=$(cat "${MOCK_STATE_FILE}")
hash_file()
{
    sha256sum "$1" | awk '{print $1}'
}
case "${1:-}" in
    strategy-lab-status)
        case "${state}" in RUNNING) exit 0 ;; STOPPED) exit 1 ;; *) exit 2 ;; esac
        ;;
    strategy-lab-stop)
        printf '%s\n' STOPPED > "${MOCK_STATE_FILE}"
        exit 0
        ;;
    strategy-lab-start)
        printf '%s\n' RUNNING > "${MOCK_STATE_FILE}"
        exit 0
        ;;
    strategy-lab-evidence)
        config_hash=$(hash_file "${MOCK_CONFIG_FILE}")
        args_hash=$(hash_file "${MOCK_ARGS_FILE}")
        if [ "${state}" = RUNNING ]; then
            child=true
            supervisor=true
            firewall_hash=$(hash_file "${MOCK_RULES_FILE}")
        elif [ "${state}" = STOPPED ]; then
            child=false
            supervisor=false
            firewall_hash=empty
        else
            child=false
            supervisor=false
            firewall_hash=empty
        fi
        printf '{"schema":1,"source":"zapret_service","state":"%s",' "${state}"
        printf '"child_running":%s,"supervisor_running":%s,' "${child}" "${supervisor}"
        printf '"runtime_args_hash":"%s","effective_config_hash":"%s",' "${args_hash}" "${config_hash}"
        printf '"normal_firewall_hash":"%s"}\n' "${firewall_hash}"
        ;;
    *) exit 64 ;;
esac
SERVICE
chmod 0755 "${SERVICE}"

export MOCK_STATE_FILE="${STATE_FILE}"
export MOCK_CONFIG_FILE="${CONFIG_FILE}"
export MOCK_ARGS_FILE="${ARGS_FILE}"
export MOCK_RULES_FILE="${RULES_FILE}"

strategy_lab_status_file()
{
    printf '%s\n' "${STATUS_FILE}"
}
strategy_lab_candidate_cleanup(){ :; }
strategy_lab_firewall_range_empty()
{
    [ "$(cat "${TEMP_CLEAN_FILE}")" = clean ]
}

. "${MODULE_DIR}/lifecycle.sh"

reset_fixture()
{
    printf '%s\n' '{"job_id":"job.SEMANTIC","lifecycle_snapshot":{},"restoration":{}}' > "${STATUS_FILE}"
    printf '%s\n' 'TRAFFIC_ARGS=--lua-desync=multisplit:pos=1' > "${CONFIG_FILE}"
    printf '%s\n' '--filter-tcp=443' '--lua-desync=multisplit:pos=1' > "${ARGS_FILE}"
    printf '%s\n' '19000 divert 989 tcp from any to any 443 out' > "${RULES_FILE}"
    printf '%s\n' clean > "${TEMP_CLEAN_FILE}"
    STRATEGY_LAB_INITIAL_SERVICE_STATE=''
    STRATEGY_LAB_INITIAL_EVIDENCE_SOURCE=''
}

reset_fixture
printf '%s\n' RUNNING > "${STATE_FILE}"
strategy_lab_capture_initial_service_state || fail 'healthy RUNNING snapshot was rejected'
"${STRATEGY_LAB_JQ}" -e '
    .lifecycle_snapshot.source=="zapret_service" and
    .lifecycle_snapshot.state=="RUNNING" and
    .lifecycle_snapshot.child_running==true and
    .lifecycle_snapshot.supervisor_running==true
' "${STATUS_FILE}" >/dev/null || fail 'RUNNING semantic snapshot was not persisted'
strategy_lab_stop_normal_service || fail 'RUNNING service did not stop'
[ "$(cat "${STATE_FILE}")" = STOPPED ] || fail 'mock service did not enter STOPPED state'
strategy_lab_restore_initial_service_state || fail 'matching RUNNING semantics did not restore'
[ "$(cat "${STATE_FILE}")" = RUNNING ] || fail 'RUNNING state was not restored'
"${STRATEGY_LAB_JQ}" -e '
    .restoration.verified==true and
    .restoration.source=="zapret_service" and
    .restoration.strategy_unchanged==true and
    .restoration.temporary_runtime_clean==true
' "${STATUS_FILE}" >/dev/null || fail 'successful semantic restoration evidence is invalid'

reset_fixture
printf '%s\n' RUNNING > "${STATE_FILE}"
strategy_lab_capture_initial_service_state || fail 'mutation scenario snapshot failed'
strategy_lab_stop_normal_service || fail 'mutation scenario stop failed'
printf '%s\n' 'TRAFFIC_ARGS=--lua-desync=fake' > "${CONFIG_FILE}"
if strategy_lab_restore_initial_service_state; then
    fail 'effective strategy mutation was accepted as restored'
fi
"${STRATEGY_LAB_JQ}" -e '
    .restoration.verified==false and .restoration.strategy_unchanged==false
' "${STATUS_FILE}" >/dev/null || fail 'strategy mutation failure was not persisted'

reset_fixture
printf '%s\n' RUNNING > "${STATE_FILE}"
strategy_lab_capture_initial_service_state || fail 'temporary residue scenario snapshot failed'
strategy_lab_stop_normal_service || fail 'temporary residue scenario stop failed'
printf '%s\n' dirty > "${TEMP_CLEAN_FILE}"
if strategy_lab_restore_initial_service_state; then
    fail 'temporary Strategy Lab firewall residue was accepted'
fi
"${STRATEGY_LAB_JQ}" -e '
    .restoration.verified==false and .restoration.temporary_runtime_clean==false
' "${STATUS_FILE}" >/dev/null || fail 'temporary residue failure was not persisted'

reset_fixture
printf '%s\n' STOPPED > "${STATE_FILE}"
strategy_lab_capture_initial_service_state || fail 'healthy STOPPED snapshot was rejected'
strategy_lab_restore_initial_service_state || fail 'STOPPED semantics did not restore'
[ "$(cat "${STATE_FILE}")" = STOPPED ] || fail 'initial STOPPED state was changed'
"${STRATEGY_LAB_JQ}" -e '
    .restoration.verified==true and .restoration.final_state=="STOPPED"
' "${STATUS_FILE}" >/dev/null || fail 'STOPPED restoration evidence is invalid'

grep -Fq 'strategy-lab-evidence)' "${SERVICE_SOURCE}" || fail 'service evidence action is missing'
grep -Fq 'runtime_args_hash' "${SERVICE_SOURCE}" || fail 'runtime identity evidence is missing'
grep -Fq 'effective_config_hash' "${SERVICE_SOURCE}" || fail 'effective strategy evidence is missing'
grep -Fq 'normal_firewall_hash' "${SERVICE_SOURCE}" || fail 'normal firewall evidence is missing'
grep -Fq 'strategy_lab_firewall_range_empty' "${MODULE_DIR}/lifecycle.sh" || fail 'temporary firewall cleanup is not verified'

sh -n "${MODULE_DIR}/lifecycle.sh"
sh -n "${SERVICE_SOURCE}"

echo 'PASS: Strategy Lab captures and verifies semantic Zapret2 restoration evidence'
