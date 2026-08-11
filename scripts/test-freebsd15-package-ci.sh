#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
CI="${ROOT_DIR}/.github/workflows/ci.yml"
RELEASE="${ROOT_DIR}/.github/workflows/release.yml"
MATRIX="${ROOT_DIR}/docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md"
PROJECT_STATE="${ROOT_DIR}/docs/PROJECT_STATE.md"
BUILD_PKG="${ROOT_DIR}/scripts/build-pkg.sh"
INTEGRATION="${ROOT_DIR}/scripts/test-strategy-lab-third-audit-integration-contract.sh"
VERSION_FILE="${ROOT_DIR}/VERSION"
MAKEFILE="${ROOT_DIR}/Makefile"
PATCH4_TEST="${ROOT_DIR}/scripts/test-strategy-lab-python-probes.sh"
PATCH5_TEST="${ROOT_DIR}/scripts/test-strategy-lab-python-candidate-family.sh"
PATCH6_TEST="${ROOT_DIR}/scripts/test-strategy-lab-python-search-extended.sh"
PATCH29_TEST="${ROOT_DIR}/scripts/test-strategy-lab-python-candidate-spec.sh"
PATCH30_TEST="${ROOT_DIR}/scripts/test-strategy-lab-python-search-graph.sh"
PATCH31_TEST="${ROOT_DIR}/scripts/test-strategy-lab-python-adaptive-planner.sh"
PATCH32_TEST="${ROOT_DIR}/scripts/test-strategy-lab-late-stage-containment.sh"
PATCH33_TEST="${ROOT_DIR}/scripts/test-strategy-lab-adaptive-validation.sh"
MODEL_A_TEST="${ROOT_DIR}/scripts/test-strategy-lab-model-a-measurement.sh"
MODEL_B_TEST="${ROOT_DIR}/scripts/test-strategy-lab-model-b-experiment.sh"
MODEL_B_PREFLIGHT_TEST="${ROOT_DIR}/scripts/test-strategy-lab-model-b-preflight.sh"
MODEL_B_FAILFAST_TEST="${ROOT_DIR}/scripts/test-strategy-lab-model-b-failed-readiness.sh"
MODEL_B_EXHAUSTIVE_TEST="${ROOT_DIR}/scripts/test-strategy-lab-model-b-exhaustive.sh"
MODEL_B_PARALLEL_TEST="${ROOT_DIR}/scripts/test-strategy-lab-model-b-parallel.sh"
MODEL_B_PARALLEL_ATTRIBUTION_TEST="${ROOT_DIR}/scripts/test-strategy-lab-model-b-parallel-attribution.sh"
MODEL_B_PRODUCTION_TEST="${ROOT_DIR}/scripts/test-strategy-lab-stage60-parallel-production.sh"
MODEL_C_PRODUCTION_TEST="${ROOT_DIR}/scripts/test-strategy-lab-stage60-model-c-production.sh"
MODEL_B_EXHAUSTIVE_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/model_b_exhaustive.py"
MODEL_B_PARALLEL_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/model_b_parallel.py"
MODEL_B_PARALLEL_ATTRIBUTION_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/model_b_parallel_attribution.py"
MODEL_B_PRODUCTION_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_parallel.py"
MODEL_C_PRODUCTION_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_model_c.py"
MODEL_C_SELECTOR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_model_c.lua"
MODEL_B_ADAPTER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_model_b_adapter.sh"
MODEL_B_WORKER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_model_b_worker.sh"
MODEL_B_LAUNCHER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_model_b.sh"
MODEL_B_EXHAUSTIVE_WORKER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_model_b_exhaustive_worker.sh"
MODEL_B_EXHAUSTIVE_LAUNCHER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_model_b_exhaustive.sh"
MODEL_B_PARALLEL_ADAPTER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_model_b_parallel_adapter.sh"
MODEL_B_PARALLEL_WORKER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_model_b_parallel_worker.sh"
MODEL_B_PARALLEL_LAUNCHER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_model_b_parallel.sh"
STAGE60_RUNNER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_stage60_parallel_runner.sh"
EXPANSION_RUNNER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_expansion_runner.sh"
MODEL_B_PARALLEL_PATCH="${ROOT_DIR}/docs/patches/v0.4.0_21.md"
MODEL_B_PRODUCTION_PATCH="${ROOT_DIR}/docs/patches/v0.4.0_22.md"
MODEL_C_PRODUCTION_PATCH="${ROOT_DIR}/docs/patches/v0.4.0_23.md"
MODEL_C_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-11-strategy-lab-model-c-production-switch.md"
MODEL_C_ARCH="${ROOT_DIR}/docs/architecture/STRATEGY_LAB_MODEL_C.md"
MODEL_B_PARALLEL_REJECT_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-11-v0.4.0_20-model-b-parallel-attribution-reject.md"
MODEL_B_PARALLEL_ACCEPT_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-11-v0.4.0_21-model-b-parallel-reproducibility.md"
MODEL_B_SELECTION_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-11-strategy-lab-parallel-model-b-selection.md"
PYTHON_ENTRY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_python.py"

fail(){ echo "FAIL: $*" >&2; exit 1; }
require(){ grep -Fq "$2" "$1" || fail "missing contract text in $1: $2"; }

for file in \
    "${CI}" "${RELEASE}" "${MATRIX}" "${PROJECT_STATE}" "${BUILD_PKG}" "${INTEGRATION}" \
    "${VERSION_FILE}" "${MAKEFILE}" "${PATCH4_TEST}" "${PATCH5_TEST}" "${PATCH6_TEST}" \
    "${PATCH29_TEST}" "${PATCH30_TEST}" "${PATCH31_TEST}" "${PATCH32_TEST}" "${PATCH33_TEST}" \
    "${MODEL_A_TEST}" "${MODEL_B_TEST}" "${MODEL_B_PREFLIGHT_TEST}" "${MODEL_B_FAILFAST_TEST}" \
    "${MODEL_B_EXHAUSTIVE_TEST}" "${MODEL_B_PARALLEL_TEST}" "${MODEL_B_PARALLEL_ATTRIBUTION_TEST}" \
    "${MODEL_B_PRODUCTION_TEST}" "${MODEL_C_PRODUCTION_TEST}" "${MODEL_B_EXHAUSTIVE_PY}" \
    "${MODEL_B_PARALLEL_PY}" "${MODEL_B_PARALLEL_ATTRIBUTION_PY}" "${MODEL_B_PRODUCTION_PY}" \
    "${MODEL_C_PRODUCTION_PY}" "${MODEL_C_SELECTOR}" "${MODEL_B_ADAPTER}" "${MODEL_B_WORKER}" \
    "${MODEL_B_LAUNCHER}" "${MODEL_B_EXHAUSTIVE_WORKER}" "${MODEL_B_EXHAUSTIVE_LAUNCHER}" \
    "${MODEL_B_PARALLEL_ADAPTER}" "${MODEL_B_PARALLEL_WORKER}" "${MODEL_B_PARALLEL_LAUNCHER}" \
    "${STAGE60_RUNNER}" "${EXPANSION_RUNNER}" "${MODEL_B_PARALLEL_PATCH}" \
    "${MODEL_B_PRODUCTION_PATCH}" "${MODEL_C_PRODUCTION_PATCH}" "${MODEL_C_DECISION}" \
    "${MODEL_C_ARCH}" "${MODEL_B_PARALLEL_REJECT_EVIDENCE}" "${MODEL_B_PARALLEL_ACCEPT_EVIDENCE}" \
    "${MODEL_B_SELECTION_DECISION}" "${PYTHON_ENTRY}"
do
    [ -s "${file}" ] || fail "required file is missing: ${file}"
done

for executable in \
    "${PATCH4_TEST}" "${PATCH29_TEST}" "${PATCH30_TEST}" "${PATCH31_TEST}" \
    "${MODEL_A_TEST}" "${MODEL_B_TEST}" "${MODEL_B_EXHAUSTIVE_TEST}" "${MODEL_B_PARALLEL_TEST}" \
    "${MODEL_B_PRODUCTION_TEST}" "${MODEL_C_PRODUCTION_TEST}" "${MODEL_B_ADAPTER}" \
    "${MODEL_B_WORKER}" "${MODEL_B_LAUNCHER}" "${MODEL_B_EXHAUSTIVE_WORKER}" \
    "${MODEL_B_EXHAUSTIVE_LAUNCHER}" "${MODEL_B_PARALLEL_ADAPTER}" \
    "${MODEL_B_PARALLEL_WORKER}" "${MODEL_B_PARALLEL_LAUNCHER}" \
    "${STAGE60_RUNNER}" "${EXPANSION_RUNNER}"
do
    [ -x "${executable}" ] || fail "required executable lost mode: ${executable}"
done

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(awk -F= '/^PLUGIN_REVISION=/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${MAKEFILE}")
case "${revision}" in ''|*[!0-9]*) fail 'invalid plugin revision' ;; esac
if [ "${revision}" -gt 0 ]; then candidate="os-zapret2-restyle-${version}_${revision}.pkg"; else candidate="os-zapret2-restyle-${version}.pkg"; fi
[ "${version}" = '0.4.0' ] || fail "unexpected project version ${version}"
[ "${revision}" -eq 23 ] || fail 'Model-C production candidate revision must be exactly 23'

# Package construction and ABI/runtime requirements remain unchanged.
grep -Eq '^PLUGIN_DEPENDS=[[:space:]]+python313([[:space:]]|$)' "${MAKEFILE}" || fail 'python313 dependency is missing'
require "${BUILD_PKG}" 'python313)  echo "lang/python313"'
require "${BUILD_PKG}" 'cp -R src/opnsense "${STAGE}/usr/local/opnsense"'
require "${CI}" 'release: "15.0"'
require "${RELEASE}" "release: '15.0'"
if grep -REn "release:[[:space:]]*['\"]?14([.]|['\"]|$)" "${ROOT_DIR}/.github/workflows"; then fail 'a GitHub workflow still selects FreeBSD 14'; fi
require "${CI}" 'python-version: "3.13"'
require "${CI}" 'STRATEGY_LAB_PYTHON_BIN: python3.13'
require "${CI}" 'pkg install -y jq python313'
require "${CI}" 'tar -tf dist/*.pkg > "${contents}"'
require "${CI}" 'tar -xOf dist/*.pkg +MANIFEST > "${manifest}"'
require "${CI}" '.abi == "FreeBSD:15:amd64"'
require "${CI}" '.arch == "freebsd:15:x86:64"'
require "${CI}" '.deps.python313.origin == "lang/python313"'
require "${CI}" 'freebsd-version -u'
require "${CI}" 'scripts/test-freebsd15-package-ci'

for test in \
    test-strategy-lab-python-foundation.sh \
    test-strategy-lab-python-state-persistence.sh \
    test-strategy-lab-python-orchestration.sh \
    test-strategy-lab-python-probes.sh \
    test-strategy-lab-python-candidate-spec.sh \
    test-strategy-lab-python-candidate-family.sh \
    test-strategy-lab-python-search-graph.sh \
    test-strategy-lab-python-adaptive-planner.sh \
    test-strategy-lab-python-search-extended.sh
do
    require "${CI}" "STRATEGY_LAB_TEST_PYTHON=/usr/local/bin/python3.13 sh scripts/${test}"
done

# Canonical corrective matrix auto-discovers both new and retained focused contracts.
require "${ROOT_DIR}/scripts/test-strategy-lab-corrective-matrix.sh" "find \"\${ROOT_DIR}/scripts\" -maxdepth 1 -type f -name 'test-strategy-lab-*.sh'"
require "${MODEL_B_PREFLIGHT_TEST}" 'PASS: Model B preflight returns success when all dedicated rules/ports are free'
require "${MODEL_B_TEST}" 'preserves bounded post-drop hostlist access'
require "${MODEL_B_FAILFAST_TEST}" 'PASS: Model B failed pool readiness rejects immediately, skips probes/stop/death, and still requests bounded cleanup'
require "${MODEL_B_EXHAUSTIVE_TEST}" 'PASS: exhaustive Model B benchmark replays a complete graph-exhausted multi-endpoint corpus'
require "${MODEL_B_PARALLEL_TEST}" 'PASS: controlled parallel Model B uses three isolated warm workers with unique source-port routing'
require "${MODEL_B_PARALLEL_ATTRIBUTION_TEST}" 'PASS: parallel Model B attributes blocked probes by exact command binding plus exact IPFW counter growth'
require "${MODEL_B_PRODUCTION_TEST}" 'accepted width-three Model B remains a production fallback/reference'
require "${MODEL_C_PRODUCTION_TEST}" 'PASS: production Stage 60 defaults to one warm Model C bucket'

# Historical Model-B reproducibility surfaces remain packaged and intact.
require "${MODEL_B_EXHAUSTIVE_PY}" 'B-warm-worker-exhaustive-batched'
require "${MODEL_B_EXHAUSTIVE_PY}" 'reference_endpoint_bindings'
require "${MODEL_B_EXHAUSTIVE_PY}" 'all_reference_endpoints_replayed'
require "${MODEL_B_EXHAUSTIVE_PY}" 'endpoint_probes'
require "${MODEL_B_EXHAUSTIVE_WORKER}" 'model-b-exhaustive run'
require "${MODEL_B_EXHAUSTIVE_LAUNCHER}" '9>"${LIFECYCLE_LOCK_FILE}"'
require "${MODEL_B_PARALLEL_PY}" 'B-warm-worker-parallel-batched'
require "${MODEL_B_PARALLEL_PY}" 'ThreadPoolExecutor(max_workers=len(slots)'
require "${MODEL_B_PARALLEL_PY}" 'source_port_plan_unique'
require "${MODEL_B_PARALLEL_PY}" 'candidate_parallelism_observed'
require "${MODEL_B_PARALLEL_PY}" 'endpoints_sequential_per_candidate'
require "${MODEL_B_PARALLEL_PY}" 'measurement_only_no_cpu_gating'
require "${MODEL_B_PARALLEL_ATTRIBUTION_PY}" 'command_source_port_match'
require "${MODEL_B_PARALLEL_ATTRIBUTION_PY}" 'command_endpoint_match'
require "${MODEL_B_PARALLEL_ATTRIBUTION_PY}" 'result["intercepted"]'
require "${MODEL_B_PARALLEL_ADAPTER}" 'source-port-free'
require "${MODEL_B_PARALLEL_ADAPTER}" 'route-add-source'
require "${MODEL_B_PARALLEL_ADAPTER}" 'from me "${_mb_source_port}" to "${_mb_address}"'
require "${MODEL_B_PARALLEL_WORKER}" 'model-b-parallel run'
require "${MODEL_B_PARALLEL_WORKER}" 'model-b-parallel finalize'
require "${MODEL_B_PARALLEL_LAUNCHER}" '9>"${LIFECYCLE_LOCK_FILE}"'

# Accepted `_22` Model B stays the first fallback/reference and retains cold Model A.
require "${MODEL_B_PRODUCTION_PY}" 'MODEL = "B-warm-worker-parallel-batched"'
require "${MODEL_B_PRODUCTION_PY}" 'WIDTH = 3'
require "${MODEL_B_PRODUCTION_PY}" 'ThreadPoolExecutor(max_workers=len(slots)'
require "${MODEL_B_PRODUCTION_PY}" 'model_b_parallel_attribution._probe_endpoint'
require "${MODEL_B_PRODUCTION_PY}" 'return search.expand(job_id, endpoints_file, family_result_file, result_file)'
require "${MODEL_B_PRODUCTION_PY}" 'A-cold-fallback'
require "${MODEL_B_PRODUCTION_PY}" '_candidate_admission'
require "${MODEL_B_PRODUCTION_PY}" 'no_cpu_gating'

# `_23` normal Stage 60 is one Model-C bucket with exact dispatch and Model-B fallback.
require "${MODEL_C_PRODUCTION_PY}" 'MODEL = "C-warm-bucket-source-port-dispatch"'
require "${MODEL_C_PRODUCTION_PY}" 'MODEL_B = stage60_parallel.MODEL'
require "${MODEL_C_PRODUCTION_PY}" 'ThreadPoolExecutor(max_workers=len(decisions)'
require "${MODEL_C_PRODUCTION_PY}" 'physical_worker_count'
require "${MODEL_C_PRODUCTION_PY}" 'model_b_parallel_attribution._probe_endpoint'
require "${MODEL_C_PRODUCTION_PY}" 'fallback_execution_model'
require "${MODEL_C_PRODUCTION_PY}" 'original_batch'
require "${MODEL_C_PRODUCTION_PY}" 'STRATEGY_LAB_STAGE60_MODEL'
require "${MODEL_C_SELECTOR}" 'function strategy_lab_model_c_source_port(desync)'
require "${MODEL_C_SELECTOR}" 'tcp.th_sport'
require "${MODEL_C_SELECTOR}" 'tcp.th_dport'
require "${STAGE60_RUNNER}" 'stage60-parallel expand'
require "${STAGE60_RUNNER}" 'trap on_signal HUP INT TERM'
require "${EXPANSION_RUNNER}" 'strategy_lab_stage60_parallel_runner.sh'
require "${PYTHON_ENTRY}" 'from strategy_lab_py import stage60_model_c as stage60_parallel'

# Existing migration/adaptive validation continuity remains mandatory.
require "${PATCH6_TEST}" 'scripts/test-strategy-lab-late-stage-containment.sh'
require "${PATCH6_TEST}" 'scripts/test-strategy-lab-adaptive-validation.sh'

# The package builder stages the complete OPNsense tree. These current/retained source paths
# must therefore exist and will additionally be checked in the actual FreeBSD package job.
for installed in \
    strategy_lab_py/state.py \
    strategy_lab_py/orchestrator.py \
    strategy_lab_py/request.py \
    strategy_lab_py/probe.py \
    strategy_lab_py/endpoint_epoch.py \
    strategy_lab_py/telemetry.py \
    strategy_lab_py/resources.py \
    strategy_lab_py/candidate_spec.py \
    strategy_lab_py/candidate.py \
    strategy_lab_py/family.py \
    strategy_lab_py/search_graph.py \
    strategy_lab_py/search.py \
    strategy_lab_py/extended.py \
    strategy_lab_py/model_b_exhaustive.py \
    strategy_lab_py/model_b_parallel.py \
    strategy_lab_py/model_b_parallel_attribution.py \
    strategy_lab_py/stage60_parallel.py \
    strategy_lab_py/stage60_model_c.py \
    strategy_lab_model_c.lua \
    strategy_lab_candidate_adapter.sh \
    strategy_lab_model_b_parallel_adapter.sh \
    strategy_lab_stage60_parallel_runner.sh \
    strategy_lab_expansion_runner.sh \
    strategy_lab_stage_adapter.sh
do
    [ -e "${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/${installed}" ] || fail "packaged source path is missing: ${installed}"
done

# Historical evidence remains present while current docs point at `_23` without fake live PASS.
require "${MATRIX}" 'Adaptive `_28` focused evidence:'
require "${MATRIX}" '2026-08-09-v0.4.0_6-stage60-timeout.md'
require "${MATRIX}" '2026-08-10-v0.4.0_7-late-stage-pass.md'
require "${MATRIX}" '2026-08-10-v0.4.0_8-timeout-containment-pass.md'
require "${MATRIX}" 'MODEL A COLD REFERENCE — PASS ON `v0.4.0_11`'
require "${MATRIX}" 'MODEL B `_17` REPEATED OWNER-LIVE COEXISTENCE ACCEPT — EXPERIMENT ONLY'
require "${MATRIX}" 'mean 74.8082 s'
require "${MATRIX}" 'about 15.96%'
require "${MATRIX}" '**PASS ON `_27` — v0.4.0 mandatory row**'
require "${MATRIX}" 'Required package ABI: `FreeBSD:15:amd64`'
require "${MATRIX}" 'MODEL-C PRODUCTION CANDIDATE PENDING OWNER-LIVE VERIFICATION'
require "${MODEL_B_PARALLEL_REJECT_EVIDENCE}" '`route_attribution=false`'
require "${MODEL_B_PARALLEL_REJECT_EVIDENCE}" 'parallel exhaustive search: `32977 ms`'
require "${MODEL_B_PARALLEL_REJECT_EVIDENCE}" '`62.952%` faster'
require "${MODEL_B_PARALLEL_PATCH}" 'For route attribution of a failed/blocked probe'
require "${MODEL_B_PARALLEL_ACCEPT_EVIDENCE}" 'six accepted controlled-parallel'
require "${MODEL_B_PARALLEL_ACCEPT_EVIDENCE}" '33025.6 ms'
require "${MODEL_B_SELECTION_DECISION}" 'APPROVED FOR IMPLEMENTATION; NOT YET PRODUCTION-ACTIVE'
require "${MODEL_B_PRODUCTION_PATCH}" 'This patch changes **Stage 60 only**.'
require "${MODEL_C_PRODUCTION_PATCH}" 'This packaged patch changes **Stage 60 runtime execution only**.'
require "${MODEL_C_DECISION}" 'OWNER-AUTHORIZED FOR PRODUCTION CANDIDATE `_23`; OWNER-LIVE ACCEPTANCE PENDING'
require "${MODEL_C_ARCH}" 'Model C -> Model B -> Model A cold'
require "${PROJECT_STATE}" '`_32` timeout-containment: owner-live PASS through `v0.4.0_8`.'
require "${PROJECT_STATE}" '`_33` adaptive validation: change-specific owner-live PASS on `v0.4.0_9`.'
require "${PROJECT_STATE}" 'Model A cold reference: accepted on `v0.4.0_11` / `job.TtZeaH`.'
require "${PROJECT_STATE}" 'Model B sequential exhaustive: `_19` owner-live ACCEPT 5/5'

sh -n "$0"
printf '%s\n' "PASS: FreeBSD 15 package CI preserves accepted Strategy Lab history while ${candidate} packages Model C with Model-B/Model-A fail-closed fallback"
