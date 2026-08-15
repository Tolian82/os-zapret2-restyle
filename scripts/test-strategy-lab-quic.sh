#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd); SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"; MODULE_DIR="${SCRIPT_DIR}/strategy_lab"
VIEW="${ROOT_DIR}/src/opnsense/mvc/app/views/OPNsense/Zapret/diagnostics.volt"
MODEL="${ROOT_DIR}/src/opnsense/mvc/app/models/OPNsense/Zapret/Zapret.xml"
SETTINGS_API="${ROOT_DIR}/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/StrategyLabSettingsController.php"
START_API="${ROOT_DIR}/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/StrategyLabController.php"
LAUNCH="${MODULE_DIR}/launch.sh"
STAGE_ADAPTER="${SCRIPT_DIR}/strategy_lab_stage_adapter.sh"
PY_EXTENDED="${SCRIPT_DIR}/strategy_lab_py/extended.py"
TMP=$(mktemp -d /tmp/strategy-lab-quic-test.XXXXXX); trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
mkdir -p "${TMP}/bin" "${TMP}/run/jobs/job.test"
cat > "${TMP}/bin/timeout" <<'MOCK'
#!/bin/sh
shift
exec "$@"
MOCK
cat > "${TMP}/bin/candidate" <<'MOCK'
#!/bin/sh
result=$3; id=$4; family=$5; strategy=$6
printf '%s\n' "${id}" >> "${MOCK_QUIC_ORDER}"
case "${id}" in quic-fake-1) pass=false; status=FAIL ;; *) pass=true; status=PASS ;; esac
jq -n --arg id "${id}" --arg family "${family}" --rawfile strategy "${strategy}" --arg status "${status}" --argjson pass "${pass}" '{id:$id,family:$family,strategy:$strategy,endpoints:[{endpoint:"example.org",status:$status}],all_pass:$pass}' > "${result}"
MOCK
chmod +x "${TMP}/bin/"*
printf 'example.org\n' > "${TMP}/endpoints.txt"
export SCRIPT_DIR MODULE_DIR STRATEGY_LAB_JQ=$(command -v jq) STRATEGY_LAB_RUN_DIR="${TMP}/run" STRATEGY_LAB_JOBS_DIR="${TMP}/run/jobs"
export STRATEGY_LAB_TIMEOUT_BIN="${TMP}/bin/timeout" STRATEGY_LAB_QUIC_CANDIDATE_RUNNER="${TMP}/bin/candidate" MOCK_QUIC_ORDER="${TMP}/order"
. "${MODULE_DIR}/common.sh"; . "${MODULE_DIR}/quic.sh"

# A blocked control probe must no longer suppress QUIC candidates.
printf '%s\n' '{"quic_ipv4":"closed"}' > "${TMP}/closed.json"
strategy_lab_quic_run job.test "${TMP}/endpoints.txt" "${TMP}/closed.json" "${TMP}/closed-result.json"
jq -e '.enabled==true and .status=="working" and .working.id=="quic-fake-2" and (.tested|length)==2' "${TMP}/closed-result.json" >/dev/null
[ "$(paste -sd, "${MOCK_QUIC_ORDER}")" = 'quic-fake-1,quic-fake-2' ]

! grep -Fq 'quic_ipv4' "${MODULE_DIR}/quic.sh" || { echo 'FAIL: legacy QUIC runner still gates on network capability' >&2; exit 1; }
! grep -Fq 'capability = _load_json(network_path)' "${PY_EXTENDED}" || { echo 'FAIL: Python QUIC runner still gates on network capability' >&2; exit 1; }
grep -Fq '"enabled": True' "${PY_EXTENDED}" || { echo 'FAIL: Python QUIC result does not record enabled execution' >&2; exit 1; }

grep -Fq '<enablequic type="BooleanField">' "${MODEL}" || { echo 'FAIL: persisted Enable QUIC model field is missing' >&2; exit 1; }
grep -Fq '<Default>0</Default>' "${MODEL}" || { echo 'FAIL: Enable QUIC default-off contract is missing' >&2; exit 1; }
grep -Fq 'class StrategyLabSettingsController extends ApiMutableModelControllerBase' "${SETTINGS_API}" || { echo 'FAIL: Strategy Lab setting API is not persistent model-backed state' >&2; exit 1; }
grep -Fq "model->strategylab->enablequic" "${SETTINGS_API}" || { echo 'FAIL: setting API does not persist Enable QUIC' >&2; exit 1; }
grep -Fq "getPost('enable_quic'" "${START_API}" || { echo 'FAIL: Strategy Lab start API does not accept explicit Enable QUIC' >&2; exit 1; }
grep -Fq 'strategyLabEnableQuic' "${VIEW}" || { echo 'FAIL: Enable QUIC checkbox is missing from Diagnostics' >&2; exit 1; }
grep -Fq '/api/zapret/strategy_lab_settings/quic' "${VIEW}" || { echo 'FAIL: Enable QUIC checkbox is not persisted through the setting API' >&2; exit 1; }
grep -Fq 'quic-enabled' "${LAUNCH}" || { echo 'FAIL: launcher does not persist per-job Enable QUIC evidence' >&2; exit 1; }
grep -Fq 'QUIC_ENABLED=$(cat "${JOB_DIR}/quic-enabled"' "${STAGE_ADAPTER}" || { echo 'FAIL: Stage 80 is not gated by the explicit per-job Enable QUIC setting' >&2; exit 1; }
grep -Fq 'reason:"disabled"' "${STAGE_ADAPTER}" || { echo 'FAIL: disabled QUIC path is not reported explicitly' >&2; exit 1; }

grep -Fxq -- '--payload=quic_initial' "${MODULE_DIR}/catalog/quic/quic-fake-1.args"
grep -Fxq -- '--lua-desync=send:ipfrag:ipfrag_pos_udp=8' "${MODULE_DIR}/catalog/quic/quic-ipfrag-8.args"
grep -Fxq -- '--lua-desync=drop' "${MODULE_DIR}/catalog/quic/quic-ipfrag-8.args"

echo 'PASS: Strategy Lab QUIC execution is controlled only by persisted Enable QUIC state, not network capability gating'
