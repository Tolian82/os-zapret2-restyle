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
        case "${worker}" in
            pass) rss=4000 ;;
            builtin) rss=4100 ;;
            external) rss=4300 ;;
            *) exit 64 ;;
        esac
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

"${PYTHON_BIN}" "${ENTRY}" blob-startup-measure run "${REPORT}" 3 >/dev/null

cat > "${INITIAL}" <<'JSON'
{"schema":1,"source":"zapret_service","state":"RUNNING","child_running":true,"supervisor_running":true,"runtime_args_hash":"a","effective_config_hash":"b","normal_firewall_hash":"c"}
JSON
cp "${INITIAL}" "${FINAL}"
"${PYTHON_BIN}" "${ENTRY}" blob-startup-measure finalize "${REPORT}" "${INITIAL}" "${FINAL}" true >/dev/null

"${PYTHON_BIN}" - "${REPORT}" <<'PY'
import json, sys
value=json.load(open(sys.argv[1], encoding="utf-8"))
assert value["policy"] == "blob-startup-rss-v1"
assert value["cache_policy"] == "natural-cache-no-drop"
assert value["trials_per_variant"] == 3
assert value["sample_count"] == 9
assert set(value["summaries"]) == {"blob-free", "builtin", "external"}
assert set(value["comparisons"]) == {"builtin_vs_blob_free", "external_vs_blob_free", "external_vs_builtin"}
assert value["summaries"]["blob-free"]["settled_rss_kb"]["median"] == 4000.0
assert value["summaries"]["builtin"]["settled_rss_kb"]["median"] == 4100.0
assert value["summaries"]["external"]["settled_rss_kb"]["median"] == 4300.0
assert value["checks"]["expected_sample_count"] is True
assert value["checks"]["all_samples_ready"] is True
assert value["checks"]["lifecycle_restored"] is True
assert value["checks"]["cleanup_ok"] is True
assert value["production_change_recommended"] is False
assert value["conclusion"] == "measurement_accepted"
assert value["next_step"] == "evaluate_reproducibility_before_any_production_blob_change"
external=value["variant_arguments"]["external"]
assert any(item.startswith("--blob=fake_tls_7:@") for item in external)
assert not any(item.startswith("--blob=") for item in value["variant_arguments"]["builtin"])
assert not any(item.startswith("--blob=") for item in value["variant_arguments"]["blob-free"])
PY

# `_3` fixes `_2` by deriving Lua evidence from the same canonical ResourceInventory root.
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

printf '%s\n' 'PASS: BLOB startup/RSS measurement is isolated, balanced, lifecycle-safe, and fixes canonical Lua resource discovery'
