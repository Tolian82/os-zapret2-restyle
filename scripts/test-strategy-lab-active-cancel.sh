#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
WRAPPER="${SCRIPT_DIR}/strategy_lab_cancellable_runner.sh"
WORKER="${SCRIPT_DIR}/strategy_lab_worker.sh"
TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-active-cancel.XXXXXX")

cleanup()
{
    rm -rf "${TEST_ROOT}"
}
trap cleanup EXIT HUP INT TERM

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

cat > "${TEST_ROOT}/runner.sh" <<'RUNNER'
#!/bin/sh
label="$1"
state_dir="$2"
mkdir -p "${state_dir}"
sleep 300 &
child=$!
printf '%s\n' "$$" > "${state_dir}/${label}.runner.pid"
printf '%s\n' "${child}" > "${state_dir}/${label}.child.pid"
trap 'kill -TERM "${child}" 2>/dev/null || true; wait "${child}" 2>/dev/null || true; exit 0' HUP INT TERM
wait "${child}"
RUNNER

cat > "${TEST_ROOT}/harness.sh" <<'HARNESS'
#!/bin/sh
wrapper="$1"
runner="$2"
cancel_file="$3"
state_dir="$4"
label="$5"
marker="$6"
CANCEL_FILE="${cancel_file}"
STRATEGY_LAB_WORKER_PID=$$
STRATEGY_LAB_CANCEL_POLL_SECONDS=1
STRATEGY_LAB_CANCEL_GRACE_SECONDS=2
STRATEGY_LAB_PGREP_BIN="$(command -v pgrep)"
export CANCEL_FILE STRATEGY_LAB_WORKER_PID STRATEGY_LAB_CANCEL_POLL_SECONDS
export STRATEGY_LAB_CANCEL_GRACE_SECONDS STRATEGY_LAB_PGREP_BIN
trap 'printf "%s\n" canceled > "${marker}"; exit 0' TERM
"${wrapper}" "${runner}" "${label}" "${state_dir}"
status=$?
printf '%s\n' "${status}" > "${marker}.status"
exit "${status}"
HARNESS

cat > "${TEST_ROOT}/exit.sh" <<'EXITRUNNER'
#!/bin/sh
exit "${1:-0}"
EXITRUNNER

chmod 0755 "${TEST_ROOT}/runner.sh" "${TEST_ROOT}/harness.sh" "${TEST_ROOT}/exit.sh"

wait_for_file()
{
    _file="$1"
    _attempt=0
    while [ ! -s "${_file}" ] && [ "${_attempt}" -lt 50 ]
    do
        sleep 0.1
        _attempt=$((_attempt + 1))
    done
    [ -s "${_file}" ] || fail "timed out waiting for ${_file}"
}

assert_dead()
{
    _pid="$1"
    if kill -0 "${_pid}" 2>/dev/null; then
        fail "process ${_pid} remained alive after cancellation"
    fi
}

run_cancel_case()
{
    _label="$1"
    _cancel="${TEST_ROOT}/${_label}.cancel"
    _marker="${TEST_ROOT}/${_label}.marker"
    rm -f "${_cancel}" "${_marker}" "${_marker}.status"

    started=$(date +%s)
    "${TEST_ROOT}/harness.sh" "${WRAPPER}" "${TEST_ROOT}/runner.sh" \
        "${_cancel}" "${TEST_ROOT}" "${_label}" "${_marker}" &
    harness_pid=$!

    wait_for_file "${TEST_ROOT}/${_label}.runner.pid"
    wait_for_file "${TEST_ROOT}/${_label}.child.pid"
    runner_pid=$(cat "${TEST_ROOT}/${_label}.runner.pid")
    child_pid=$(cat "${TEST_ROOT}/${_label}.child.pid")

    : > "${_cancel}"
    if wait "${harness_pid}"; then
        :
    else
        fail "worker harness did not complete through its TERM trap for ${_label}"
    fi

    [ "$(cat "${_marker}")" = canceled ] || fail "worker cancellation trap was not invoked for ${_label}"
    sleep 1
    assert_dead "${runner_pid}"
    assert_dead "${child_pid}"
    elapsed=$(( $(date +%s) - started ))
    [ "${elapsed}" -le 8 ] || fail "cancellation exceeded the bounded window for ${_label}: ${elapsed}s"
}

for label in stage60 stage70 stage80-tcp stage80-quic stage80-udp
do
    run_cancel_case "${label}"
done

unset CANCEL_FILE STRATEGY_LAB_WORKER_PID
export STRATEGY_LAB_PGREP_BIN="$(command -v pgrep)"
if "${WRAPPER}" "${TEST_ROOT}/exit.sh" 7; then
    fail "normal non-zero runner status was lost"
else
    status=$?
fi
[ "${status}" -eq 7 ] || fail "expected status 7, got ${status}"

while IFS='|' read -r expected script
do
    grep -Fq "${expected}" "${WORKER}" || fail "worker does not select ${script}"
done <<'MAPPINGS'
EXPANSION_RUNNER="${EXPANSION_RUNNER:-${SCRIPT_DIR}/strategy_lab_cancellable_expansion_runner.sh}"|strategy_lab_cancellable_expansion_runner.sh
STABILITY_RUNNER="${STABILITY_RUNNER:-${SCRIPT_DIR}/strategy_lab_cancellable_stability_runner.sh}"|strategy_lab_cancellable_stability_runner.sh
EXTENDED_RUNNER="${EXTENDED_RUNNER:-${SCRIPT_DIR}/strategy_lab_cancellable_extended_runner.sh}"|strategy_lab_cancellable_extended_runner.sh
QUIC_RUNNER="${QUIC_RUNNER:-${SCRIPT_DIR}/strategy_lab_cancellable_quic_runner.sh}"|strategy_lab_cancellable_quic_runner.sh
UDP_RUNNER="${UDP_RUNNER:-${SCRIPT_DIR}/strategy_lab_cancellable_udp_runner.sh}"|strategy_lab_cancellable_udp_runner.sh
MAPPINGS

grep -Fq 'export CANCEL_FILE STRATEGY_LAB_WORKER_PID' "${WORKER}" ||
    fail "worker cancellation context is not exported"

for wrapper in expansion stability extended quic udp
do
    file="${SCRIPT_DIR}/strategy_lab_cancellable_${wrapper}_runner.sh"
    [ -x "${file}" ] || fail "missing executable ${file}"
    grep -Fq 'strategy_lab_cancellable_runner.sh' "${file}" || fail "${file} bypasses the common cancellation runner"
done

echo 'PASS: active Strategy Lab runners terminate their process trees and transfer cancellation to mandatory worker finalization'
