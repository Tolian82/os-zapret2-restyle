#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN="${STRATEGY_LAB_TEST_PYTHON:-python3}"
ENTRY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_python.py"
WRAPPER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_blob_measurement.sh"
WORKER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_blob_measurement_worker.sh"
MODULE="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/blob_startup_measurement.py"
RESOURCES="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/resources.py"
LUA_MODULE="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/lua_initialization_measurement.py"

TMP=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-blob-test.XXXXXX")
trap 'rm -rf "${TMP}"' EXIT INT TERM HUP
LUA_DIR="${TMP}/lua"
FAKE_DIR="${TMP}/fake"
SESSION="${TMP}/session"
ADAPTER="${TMP}/adapter.sh"
SELECTOR="${TMP}/strategy_lab_model_c.lua"
REPORT="${TMP}/blob.json"
INITIAL="${TMP}/initial.json"
FINAL="${TMP}/final.json"
LUA_REPORT="${TMP}/lua.json"
mkdir -p "${LUA_DIR}" "${FAKE_DIR}" "${SESSION}"

for name in zapret-lib.lua zapret-antidpi.lua zapret-auto.lua
do
    printf '%s\n' '-- test lua' > "${LUA_DIR}/${name}"
done
printf '%s\n' '-- selector' > "${SELECTOR}"
printf '%s\n' 'external fake bytes' > "${FAKE_DIR}/fake_tls_7.bin"
printf '%s\n' 'rutracker kyber external fake bytes' > "${FAKE_DIR}/tls_clienthello_rutracker_org_kyber.bin"
printf '%s\n' 'vk kyber external fake bytes' > "${FAKE_DIR}/tls_clienthello_vk_com_kyber.bin"

cat > "${ADAPTER}" <<'SH'
#!/bin/sh
set -eu
session=${STRATEGY_LAB_MODEL_B_SESSION_DIR:?}
action=${1:-}
shift || true
case "${action}" in
    preflight)
        for worker in pass builtin external; do
            [ ! -e "${session}/${worker}.running" ] || exit 1
        done
        ;;
    cleanup-all)
        rm -f "${session}"/*.running
        ;;
    launch)
        worker=$1
        port=$2
        printf '%s\n' "${port}" > "${session}/${worker}.running"
        ;;
    snapshot)
        worker=$1
        port=$2
        [ -e "${session}/${worker}.running" ] || exit 1
        args="${session}/workers/${worker}/dvtws.args"
        [ -r "${args}" ] || exit 1
        if grep -Fq 'tls_clienthello_vk_com_kyber' "${args}"; then
            rss=4600
        elif grep -Fq -- '--blob=fake_tls_7:@' "${args}"; then
            rss=4300
        elif grep -Fq 'seqovl_pattern=0x1603' "${args}"; then
            rss=4100
        else
            rss=4000
        fi
        printf '{"worker":"%s","pid":1,"command":"fake --port=%s","divert_port":%s,"process_identity":true,"socket_ready":true,"log_clean":true,"rss_kb":%s}\n' \
            "${worker}" "${port}" "${port}" "${rss}"
        ;;
    stop)
        worker=$1
        rm -f "${session}/${worker}.running"
        ;;
    *) exit 64 ;;
esac
SH
chmod +x "${ADAPTER}"

export STRATEGY_LAB_LUA_DIR="${LUA_DIR}"
export STRATEGY_LAB_FAKE_DIR="${FAKE_DIR}"
export STRATEGY_LAB_MODEL_C_SELECTOR_LUA="${SELECTOR}"
export STRATEGY_LAB_MODEL_B_SESSION_DIR="${SESSION}"
export STRATEGY_LAB_BLOB_MEASUREMENT_ADAPTER="${ADAPTER}"

"${PYTHON_BIN}" "${ENTRY}" blob-startup-measure run "${REPORT}" 4 >/dev/null

cat > "${INITIAL}" <<'JSON'
{"schema":1,"source":"zapret_service","state":"RUNNING","child_running":true,"supervisor_running":true,"runtime_args_hash":"a","effective_config_hash":"b","normal_firewall_hash":"c"}
JSON
cp "${INITIAL}" "${FINAL}"
"${PYTHON_BIN}" "${ENTRY}" blob-startup-measure finalize "${REPORT}" "${INITIAL}" "${FINAL}" true >/dev/null

"${PYTHON_BIN}" - "${REPORT}" <<'PY'
import json, sys
value=json.load(open(sys.argv[1], encoding="utf-8"))
assert value["schema"] == 2
assert value["policy"] == "blob-common-set-scaling-v1"
assert value["cache_policy"] == "natural-cache-no-drop"
assert value["measurement_design"] == "balanced-interleaved-four-variant-common-set-startup"
assert value["worker_identity_policy"] == "single-worker-single-port-all-variants"
assert value["worker"] == "external"
assert value["divert_port"] == 9992
assert value["production_candidate_width"] == 3
assert value["trials_per_variant"] == 4
assert value["sample_count"] == 16
assert set(value["summaries"]) == {"blob-free", "inline-small", "external-single", "external-common-3"}
assert set(value["comparisons"]) == {
    "inline_small_vs_blob_free",
    "external_single_vs_blob_free",
    "external_common_3_vs_external_single",
    "external_common_3_vs_blob_free",
}
assert value["summaries"]["blob-free"]["settled_rss_kb"]["median"] == 4000.0
assert value["summaries"]["inline-small"]["settled_rss_kb"]["median"] == 4100.0
assert value["summaries"]["external-single"]["settled_rss_kb"]["median"] == 4300.0
assert value["summaries"]["external-common-3"]["settled_rss_kb"]["median"] == 4600.0
for variant in value["summaries"].values():
    assert "mean" in variant["stable_ready_ms"]
    assert "stdev" in variant["stable_ready_ms"]
assert value["checks"]["expected_sample_count"] is True
assert value["checks"]["balanced_trial_count"] is True
assert value["checks"]["single_worker_identity"] is True
assert value["checks"]["all_samples_ready"] is True
assert value["checks"]["lifecycle_restored"] is True
assert value["checks"]["cleanup_ok"] is True
assert value["production_change_recommended"] is False
assert value["conclusion"] == "measurement_accepted"
assert value["next_step"] == "evaluate_common_set_scaling_reproducibility_before_any_production_blob_change"
assert {(sample["worker"], sample["divert_port"]) for sample in value["samples"]} == {("external", 9992)}
resource_sets=value["variant_resource_sets"]
assert resource_sets["inline-small"]["active_pattern"] == "0x1603"
assert resource_sets["inline-small"]["declared_bytes"] == 2
assert resource_sets["external-single"]["declaration_count"] == 1
assert resource_sets["external-common-3"]["declaration_count"] == 3
assert len(resource_sets["external-common-3"]["unused_eager_declarations"]) == 2
assert resource_sets["external-common-3"]["declared_bytes"] > resource_sets["external-single"]["declared_bytes"]
free=value["variant_arguments"]["blob-free"]
inline=value["variant_arguments"]["inline-small"]
single=value["variant_arguments"]["external-single"]
common=value["variant_arguments"]["external-common-3"]
assert not any(item.startswith("--blob=") for item in free)
assert not any(item.startswith("--blob=") for item in inline)
assert any("seqovl_pattern=0x1603" in item for item in inline)
assert sum(item.startswith("--blob=") for item in single) == 1
assert sum(item.startswith("--blob=") for item in common) == 3
assert any(item.startswith("--blob=fake_tls_7:@") for item in single)
assert any(item.startswith("--blob=tls_clienthello_rutracker_org_kyber:@") for item in common)
assert any(item.startswith("--blob=tls_clienthello_vk_com_kyber:@") for item in common)
assert all("seqovl_pattern=fake_tls_7" in item for item in (single[-1], common[-1]))
PY

# `_3` fixed `_2` by deriving Lua evidence from the same canonical ResourceInventory root.
"${PYTHON_BIN}" "${ENTRY}" lua-init-measure --selector-lua "${SELECTOR}" --output "${LUA_REPORT}" >/dev/null
"${PYTHON_BIN}" - "${LUA_REPORT}" "${LUA_DIR}" <<'PY'
import json, sys
value=json.load(open(sys.argv[1], encoding="utf-8"))
assert value["checks"]["all_required_files_present"] is True
assert all(item["path"].startswith(sys.argv[2] + "/") or item["name"] == "strategy_lab_model_c.lua" for item in value["effective_lua_files"])
assert value["runtime_comparison_required"] is False
PY

# Mutation/lifecycle boundary: measurement owns no traffic route and does not stop production.
grep -Fq 'lockf' "${WRAPPER}" || { echo 'FAIL: lifecycle lock missing' >&2; exit 1; }
grep -Fq 'TRIALS="${2:-12}"' "${WRAPPER}" || { echo 'FAIL: balanced default trial count missing' >&2; exit 1; }
grep -Fq 'TRIALS % 4' "${WRAPPER}" || { echo 'FAIL: four-variant balance guard missing' >&2; exit 1; }
grep -Fq 'strategy-lab-evidence' "${WORKER}" || { echo 'FAIL: semantic lifecycle evidence missing' >&2; exit 1; }
if grep -Fq 'strategy-lab-stop' "${WORKER}" || grep -Fq 'strategy-lab-start' "${WORKER}"; then
    echo 'FAIL: BLOB measurement must not mutate production service state' >&2
    exit 1
fi
if grep -Fq 'route-add' "${WORKER}" || grep -Fq 'route-add' "${MODULE}"; then
    echo 'FAIL: BLOB measurement must not install traffic routes' >&2
    exit 1
fi
grep -Fq 'DEFAULT_LUA_ROOT = Path("/usr/local/etc/zapret2/lua")' "${RESOURCES}" || { echo 'FAIL: canonical Lua root missing' >&2; exit 1; }
grep -Fq 'resources.configured_lua_root()' "${LUA_MODULE}" || { echo 'FAIL: Lua measurement does not use canonical resource root' >&2; exit 1; }

printf '%s\n' 'PASS: BLOB common-set scaling measurement is single-worker, balanced, lifecycle-safe, and resource-inventory-bound'
