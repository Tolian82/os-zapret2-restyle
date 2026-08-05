#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MODULE="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab/udp_input.sh"
CONTROLLER="${ROOT_DIR}/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/StrategyLabController.php"
VIEW="${ROOT_DIR}/src/opnsense/mvc/app/views/OPNsense/Zapret/diagnostics.volt"
ACTIONS="${ROOT_DIR}/src/opnsense/service/conf/actions.d/actions_zapret.conf"
LAUNCHER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_launcher.sh"
LAUNCH="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab/launch.sh"
WORKER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_worker.sh"
CONTROL="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab/worker_control.sh"

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

for file in "${MODULE}" "${CONTROLLER}" "${VIEW}" "${ACTIONS}" \
    "${LAUNCHER}" "${LAUNCH}" "${WORKER}" "${CONTROL}"
do
    [ -s "${file}" ] || fail "missing UDP input contract file: ${file}"
done

TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-udp-input.XXXXXX")
trap 'rm -rf "${TEST_ROOT}"' EXIT HUP INT TERM
STRATEGY_LAB_JOBS_DIR="${TEST_ROOT}/jobs"
STRATEGY_LAB_JQ=$(command -v jq)
STRATEGY_LAB_BASE64_BIN=$(command -v base64)
STRATEGY_LAB_UDP_PAYLOAD_MAX_BYTES=4096
export STRATEGY_LAB_JOBS_DIR STRATEGY_LAB_JQ STRATEGY_LAB_BASE64_BIN
export STRATEGY_LAB_UDP_PAYLOAD_MAX_BYTES

strategy_lab_job_dir()
{
    printf '%s/%s\n' "${STRATEGY_LAB_JOBS_DIR}" "$1"
}

strategy_lab_status_file()
{
    printf '%s/status.json\n' "$(strategy_lab_job_dir "$1")"
}

strategy_lab_state_transform()
{
    job="$1"
    filter="$2"
    shift 2
    status=$(strategy_lab_status_file "${job}")
    tmp="${status}.tmp"
    "${STRATEGY_LAB_JQ}" "$@" "${filter}" "${status}" > "${tmp}" || {
        rm -f "${tmp}"
        return 1
    }
    mv -f "${tmp}" "${status}"
}

. "${MODULE}"

job=job.ABC123
jobdir=$(strategy_lab_job_dir "${job}")
mkdir -p "${jobdir}"
printf '%s\n' '{"udp_request":{}}' > "$(strategy_lab_status_file "${job}")"

strategy_lab_udp_input_prepare "${job}" extended 5353 cGluZw== ||
    fail 'valid extended UDP input was rejected'
[ "$(cat "$(strategy_lab_udp_port_file "${job}")")" = 5353 ] ||
    fail 'UDP port was not persisted'
[ "$(cat "$(strategy_lab_udp_payload_file "${job}")")" = ping ] ||
    fail 'UDP payload was not decoded exactly'
[ "$(stat -c '%a' "$(strategy_lab_udp_port_file "${job}")")" = 600 ] ||
    fail 'UDP port metadata is not private'
[ "$(stat -c '%a' "$(strategy_lab_udp_payload_file "${job}")")" = 600 ] ||
    fail 'UDP payload is not private'
"${STRATEGY_LAB_JQ}" -e '
    .udp_request.configured==true and
    .udp_request.port==5353 and
    .udp_request.payload_bytes==4
' "$(strategy_lab_status_file "${job}")" >/dev/null ||
    fail 'public UDP request metadata is invalid'

strategy_lab_udp_input_export "${job}" ||
    fail 'valid job-local UDP input was not exported'
[ "${STRATEGY_LAB_UDP_PORT}" = 5353 ] ||
    fail 'exported UDP port is invalid'
[ "${STRATEGY_LAB_UDP_PAYLOAD_FILE}" = "$(strategy_lab_udp_payload_file "${job}")" ] ||
    fail 'worker received a non-job-local payload path'

strategy_lab_udp_input_cleanup "${job}"
[ ! -e "$(strategy_lab_udp_port_file "${job}")" ] ||
    fail 'UDP port metadata survived cleanup'
[ ! -e "$(strategy_lab_udp_payload_file "${job}")" ] ||
    fail 'UDP payload survived cleanup'

printf '%s\n' '{"udp_request":{}}' > "$(strategy_lab_status_file "${job}")"
strategy_lab_udp_input_prepare "${job}" extended - - ||
    fail 'disabled generic UDP input was rejected'
"${STRATEGY_LAB_JQ}" -e '
    .udp_request.configured==false and
    .udp_request.port==null and
    .udp_request.payload_bytes==0
' "$(strategy_lab_status_file "${job}")" >/dev/null ||
    fail 'disabled UDP request metadata is invalid'

expect_rejected()
{
    description="$1"
    shift
    if strategy_lab_udp_input_prepare "${job}" "$@"; then
        fail "${description}"
    fi
    strategy_lab_udp_input_cleanup "${job}"
}

expect_rejected 'standard mode accepted generic UDP input' standard 53 cGluZw==
expect_rejected 'missing UDP payload was accepted' extended 53 -
expect_rejected 'missing UDP port was accepted' extended - cGluZw==
expect_rejected 'out-of-range UDP port was accepted' extended 65536 cGluZw==
expect_rejected 'noncanonical Base64 payload was accepted' extended 53 'cGluZw='

oversize=$(dd if=/dev/zero bs=4097 count=1 2>/dev/null |
    "${STRATEGY_LAB_BASE64_BIN}" | tr -d '\n')
expect_rejected 'oversized UDP payload was accepted' extended 53 "${oversize}"

grep -Fq 'UDP_PAYLOAD_MAX_BYTES = 4096' "${CONTROLLER}" ||
    fail 'API payload size limit is missing'
grep -Fq 'base64_decode($payload, true)' "${CONTROLLER}" ||
    fail 'API strict Base64 decoding is missing'
grep -Fq "Generic UDP requires both a port and a payload file." "${CONTROLLER}" ||
    fail 'API pair validation is missing'
grep -Fq "\$udpInput['port']" "${CONTROLLER}" ||
    fail 'API does not pass validated UDP input to configd'
grep -Fq 'parameters:%s %s %s %s %s' "${ACTIONS}" ||
    fail 'configd start action does not carry the UDP contract'
grep -Fq 'strategyLabUdpPort' "${VIEW}" ||
    fail 'GUI UDP port field is missing'
grep -Fq 'strategyLabUdpPayload' "${VIEW}" ||
    fail 'GUI payload file field is missing'
grep -Fq 'readAsDataURL(payloadFile)' "${VIEW}" ||
    fail 'GUI does not encode the selected payload file'
grep -Fq 'udp_input launch query' "${LAUNCHER}" ||
    fail 'launcher does not load the UDP input module'
grep -Fq 'case "$#" in' "${LAUNCH}" ||
    fail 'launcher start contract is not backward compatible'
grep -Fq 'strategy_lab_udp_input_prepare' "${LAUNCH}" ||
    fail 'launcher does not create job-local UDP input'
grep -Fq 'udp udp_input preflight' "${WORKER}" ||
    fail 'worker does not load the UDP input module'
grep -Fq 'strategy_lab_udp_input_export' "${WORKER}" ||
    fail 'worker does not import job-local UDP input'
grep -Fq 'strategy_lab_udp_input_cleanup "${JOB_ID}"' "${CONTROL}" ||
    fail 'terminal cleanup does not remove the payload'

sh -n "${MODULE}"
sh -n "${LAUNCHER}"
sh -n "${LAUNCH}"
sh -n "${WORKER}"
sh -n "${CONTROL}"

echo 'PASS: validated generic UDP GUI/API input becomes private job-local worker state and is always cleaned'
