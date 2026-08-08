#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
READINESS_UNDER_TEST="${READINESS_UNDER_TEST:-${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab/readiness.sh}"
CANDIDATE_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/candidate.py"
ROOT=$(mktemp -d /tmp/strategy-lab-readiness.XXXXXX)
trap 'rm -rf "${ROOT}"' EXIT HUP INT TERM

STRATEGY_LAB_JQ=$(command -v jq)
STRATEGY_LAB_DVTWS_BIN=/mock/dvtws2
STRATEGY_LAB_DIVERT_PORT=9989
IDENTITY=true
SOCKET=true
LOG_CLEAN=true

strategy_lab_job_dir() { printf '%s/jobs/%s\n' "${ROOT}" "$1"; }
strategy_lab_candidate_runtime_dir() { printf '%s/candidate-runtime\n' "$(strategy_lab_job_dir "$1")"; }
strategy_lab_candidate_pid_file() { printf '%s/dvtws2.pid\n' "$(strategy_lab_candidate_runtime_dir "$1")"; }
strategy_lab_candidate_log_file() { printf '%s/dvtws2.log\n' "$(strategy_lab_candidate_runtime_dir "$1")"; }
strategy_lab_candidate_pid_read() { printf '%s\n' 4242; }
strategy_lab_candidate_pid_identity() { [ "${IDENTITY}" = true ]; }
strategy_lab_candidate_command() { printf '%s\n' '/mock/dvtws2 --port=9989 --hostlist=/tmp/job.test/hostlist.txt'; }
strategy_lab_candidate_divert_port_in_use() { [ "${SOCKET}" = true ]; }
strategy_lab_candidate_log_clean() { [ "${LOG_CLEAN}" = true ]; }
strategy_lab_atomic_write() { cat > "$1"; }

. "${READINESS_UNDER_TEST}"

# Shell readiness remains a compatibility/system helper for QUIC/UDP and later
# extended protocol paths until Migration Patch 6.
mkdir -p "$(strategy_lab_candidate_runtime_dir job.test)"
: > "$(strategy_lab_candidate_log_file job.test)"
strategy_lab_candidate_readiness_write job.test true
READINESS=$(strategy_lab_candidate_readiness_file job.test)
"${STRATEGY_LAB_JQ}" -e '
    .job_id=="job.test" and .pid==4242 and
    .executable=="/mock/dvtws2" and .divert_port==9989 and
    .process_identity==true and .socket_ready==true and
    .log_clean==true and .stable==true and .ready==true
' "${READINESS}" >/dev/null

RESULT="${ROOT}/candidate.json"
printf '%s\n' '{"all_pass":true,"endpoints":[{"status":"PASS"}]}' > "${RESULT}"
strategy_lab_candidate_attach_runtime_evidence job.test "${RESULT}"
"${STRATEGY_LAB_JQ}" -e '.all_pass==true and .runtime.ready==true' "${RESULT}" >/dev/null

LOG_CLEAN=false
if strategy_lab_candidate_readiness_write job.test true; then
    echo 'readiness unexpectedly accepted a runtime startup error' >&2
    exit 1
fi
"${STRATEGY_LAB_JQ}" -e '.ready==false and .log_clean==false' "${READINESS}" >/dev/null

# Migration Patch 5 moves standard TLS13 readiness ownership to Python. It must
# require process identity + divert socket + clean log for two stable snapshots,
# persist readiness evidence, and reject classified fatal log text.
grep -Fq 'def _readiness(job_id: str)' "${CANDIDATE_PY}"
grep -Fq 'identity = bool(snapshot.get("process_identity"))' "${CANDIDATE_PY}"
grep -Fq 'socket_ready = bool(snapshot.get("socket_ready"))' "${CANDIDATE_PY}"
grep -Fq 'log_clean = not fatal' "${CANDIDATE_PY}"
grep -Fq 'if identity and socket_ready and log_clean:' "${CANDIDATE_PY}"
grep -Fq 'ready = stable >= 2' "${CANDIDATE_PY}"
grep -Fq '_atomic_json(output, last)' "${CANDIDATE_PY}"
grep -Fq 'fatal = _fatal_reason(log_text)' "${CANDIDATE_PY}"
grep -Fq 'runtime_evidence = _readiness(job_id)' "${CANDIDATE_PY}"
grep -Fq '"runtime": runtime_evidence' "${CANDIDATE_PY}"
grep -Fq 'candidate run' "${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_candidate_runner.sh"

# Protocol candidate paths scheduled for Patch 6 intentionally retain the
# existing shell readiness evidence contract for now.
for runner in \
    strategy_lab_quic_candidate_runner.sh \
    strategy_lab_udp_candidate_runner.sh
do
    file="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/${runner}"
    grep -Eq '(^|[[:space:]])readiness([[:space:]]|$)' "${file}"
    grep -Fq 'strategy_lab_candidate_attach_runtime_evidence' "${file}"
done

echo 'PASS: standard candidate readiness is Python-owned while remaining protocol candidates retain audited shell readiness until Patch 6'
