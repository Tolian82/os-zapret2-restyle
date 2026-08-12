#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
PYTHON="${STRATEGY_LAB_TEST_PYTHON:-python3.13}"
MODULE="${SCRIPT_DIR}/strategy_lab_py/lua_initialization_measurement.py"
ENTRY="${SCRIPT_DIR}/strategy_lab_python.py"
MODEL_C="${SCRIPT_DIR}/strategy_lab_py/stage60_model_c.py"

fail(){ echo "FAIL: $*" >&2; exit 1; }
command -v "${PYTHON}" >/dev/null 2>&1 || fail "Python test interpreter is unavailable: ${PYTHON}"

"${PYTHON}" -m py_compile "${MODULE}" "${ENTRY}"
grep -Fq 'lua-init-measure' "${ENTRY}" || fail 'packaged Python entry point does not expose Lua measurement'
grep -Fq 'MODEL = "C-warm-bucket-source-port-dispatch"' "${MODEL_C}" || fail 'production Model C identity changed'
grep -Fq 'for name in spec.lua_dependencies' "${MODEL_C}" || fail 'Model C no longer derives Lua dependencies from CandidateSpec'
grep -Fq 'lua_names.append("zapret-auto.lua")' "${MODEL_C}" || fail 'Model C auto Lua initialization changed'
grep -Fq 'arguments.append(f"--lua-init=@{selector_lua}")' "${MODEL_C}" || fail 'Model C selector Lua initialization changed'

TMP=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-lua-init.XXXXXX")
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
mkdir -p "${TMP}/lua"
printf '%s\n' '-- lib' > "${TMP}/lua/zapret-lib.lua"
printf '%s\n' '-- antidpi' > "${TMP}/lua/zapret-antidpi.lua"
printf '%s\n' '-- auto' > "${TMP}/lua/zapret-auto.lua"
printf '%s\n' '-- selector' > "${TMP}/strategy_lab_model_c.lua"

PYTHONPATH="${SCRIPT_DIR}" "${PYTHON}" "${ENTRY}" lua-init-measure \
    --lua-dir "${TMP}/lua" \
    --selector-lua "${TMP}/strategy_lab_model_c.lua" \
    --output "${TMP}/report.json" >/dev/null

"${PYTHON}" - "${TMP}/report.json" <<'PY'
import json
import sys

value = json.load(open(sys.argv[1], encoding="utf-8"))
assert value["schema"] == 1
assert value["policy"] == "lua-init-set-equivalence-v1"
assert value["experiment_only"] is True
assert value["production_model_changed"] is False
assert value["model"] == "C-warm-bucket-source-port-dispatch"
assert value["candidate_count"] == 16
assert value["batch_width"] == 3
assert len(value["batches"]) == 6
assert value["all_candidates_same_dependencies"] is True
assert value["declared_dependency_signatures"] == [["zapret-lib.lua", "zapret-antidpi.lua"]]
assert all(item["declared_lua_dependencies"] == ["zapret-lib.lua", "zapret-antidpi.lua"] for item in value["candidates"])
expected = ["zapret-lib.lua", "zapret-antidpi.lua", "zapret-auto.lua", "strategy_lab_model_c.lua"]
assert all(batch["current_model_c_init_set"] == expected for batch in value["batches"])
assert all(batch["candidate_minimal_union"] == expected for batch in value["batches"])
assert all(batch["equivalent_init_set"] is True for batch in value["batches"])
assert value["checks"]["all_batches_equivalent"] is True
assert value["checks"]["all_required_files_present"] is True
assert value["checks"]["production_model_unchanged"] is True
assert value["runtime_comparison_required"] is False
assert value["timing_claim"] == "not_applicable_equivalent_init_set"
assert value["rss_claim"] == "not_applicable_equivalent_init_set"
assert value["conclusion"] == "equivalent_init_set"
assert value["next_step"] == "close_lua_initialization_optimization_and_measure_blob_startup_rss"
PY

sh -n "$0"
echo 'PASS: Model C already uses the candidate-minimal Lua union for each native width-three batch, so equivalent init sets suppress fake timing/RSS claims'
