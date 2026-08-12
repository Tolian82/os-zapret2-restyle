#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
CI="${ROOT_DIR}/.github/workflows/ci.yml"
RELEASE="${ROOT_DIR}/.github/workflows/release.yml"
MATRIX="${ROOT_DIR}/docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md"
PROJECT_STATE="${ROOT_DIR}/docs/PROJECT_STATE.md"
INDEX="${ROOT_DIR}/docs/INDEX.md"
BUILD_PKG="${ROOT_DIR}/scripts/build-pkg.sh"
VERSION_FILE="${ROOT_DIR}/VERSION"
MAKEFILE="${ROOT_DIR}/Makefile"
CORRECTIVE_MATRIX="${ROOT_DIR}/scripts/test-strategy-lab-corrective-matrix.sh"
ADAPTIVE_BUDGET_TEST="${ROOT_DIR}/scripts/test-strategy-lab-adaptive-budget.sh"
ADAPTIVE_BUDGET_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/adaptive_budget.py"
ADAPTIVE_BUDGET_DOC="${ROOT_DIR}/docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md"
ADAPTIVE_BUDGET_PATCH="${ROOT_DIR}/docs/patches/v0.4.0_26.md"
COMPAT_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/compat.py"
MODEL_B_PRODUCTION_TEST="${ROOT_DIR}/scripts/test-strategy-lab-stage60-parallel-production.sh"
MODEL_C_PRODUCTION_TEST="${ROOT_DIR}/scripts/test-strategy-lab-stage60-model-c-production.sh"
SOURCE_PORT_LEASE_TEST="${ROOT_DIR}/scripts/test-strategy-lab-stage60-source-port-lease.sh"
MODEL_B_PRODUCTION_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_parallel.py"
MODEL_C_PRODUCTION_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_model_c.py"
SOURCE_PORT_LEASE_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_source_port_lease.py"
MODEL_B_PARALLEL_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/model_b_parallel.py"
MODEL_B_PARALLEL_ATTRIBUTION_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/model_b_parallel_attribution.py"
MODEL_B_PARALLEL_ADAPTER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_model_b_parallel_adapter.sh"
MODEL_C_SELECTOR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_model_c.lua"
STAGE60_RUNNER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_stage60_parallel_runner.sh"
EXPANSION_RUNNER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_expansion_runner.sh"
PYTHON_ENTRY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_python.py"
MODEL_B_PATCH="${ROOT_DIR}/docs/patches/v0.4.0_22.md"
MODEL_C_PATCH="${ROOT_DIR}/docs/patches/v0.4.0_23.md"
SOURCE_PORT_PATCH="${ROOT_DIR}/docs/patches/v0.4.0_25.md"
MODEL_B_LIVE="${ROOT_DIR}/docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md"
MODEL_C_LIVE="${ROOT_DIR}/docs/verification/evidence/2026-08-11-v0.4.0_23-model-c-live-hold.md"
MODEL_C_CORRECTIVE_PASS="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.0_25-source-port-live-pass.md"
MODEL_C_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-11-strategy-lab-model-c-production-switch.md"
MODEL_B_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-11-strategy-lab-parallel-model-b-selection.md"

fail(){ echo "FAIL: $*" >&2; exit 1; }
require(){ grep -Fq "$2" "$1" || fail "missing contract text in $1: $2"; }

for file in \
    "${CI}" "${RELEASE}" "${MATRIX}" "${PROJECT_STATE}" "${INDEX}" "${BUILD_PKG}" \
    "${VERSION_FILE}" "${MAKEFILE}" "${CORRECTIVE_MATRIX}" \
    "${ADAPTIVE_BUDGET_TEST}" "${ADAPTIVE_BUDGET_PY}" "${ADAPTIVE_BUDGET_DOC}" \
    "${ADAPTIVE_BUDGET_PATCH}" "${COMPAT_PY}" \
    "${MODEL_B_PRODUCTION_TEST}" "${MODEL_C_PRODUCTION_TEST}" "${SOURCE_PORT_LEASE_TEST}" \
    "${MODEL_B_PRODUCTION_PY}" "${MODEL_C_PRODUCTION_PY}" "${SOURCE_PORT_LEASE_PY}" \
    "${MODEL_B_PARALLEL_PY}" "${MODEL_B_PARALLEL_ATTRIBUTION_PY}" "${MODEL_B_PARALLEL_ADAPTER}" \
    "${MODEL_C_SELECTOR}" "${STAGE60_RUNNER}" "${EXPANSION_RUNNER}" "${PYTHON_ENTRY}" \
    "${MODEL_B_PATCH}" "${MODEL_C_PATCH}" "${SOURCE_PORT_PATCH}" "${MODEL_B_LIVE}" \
    "${MODEL_C_LIVE}" "${MODEL_C_CORRECTIVE_PASS}" "${MODEL_C_DECISION}" "${MODEL_B_DECISION}"
do
    [ -s "${file}" ] || fail "required file is missing: ${file}"
done

for executable in \
    "${MODEL_B_PRODUCTION_TEST}" "${MODEL_C_PRODUCTION_TEST}" \
    "${MODEL_B_PARALLEL_ADAPTER}" "${STAGE60_RUNNER}" "${EXPANSION_RUNNER}"
do
    [ -x "${executable}" ] || fail "required runtime executable lost mode: ${executable}"
done

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(awk -F= '/^PLUGIN_REVISION=/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${MAKEFILE}")
case "${revision}" in ''|*[!0-9]*) fail 'invalid plugin revision' ;; esac
if [ "${revision}" -gt 0 ]; then candidate="os-zapret2-restyle-${version}_${revision}.pkg"; else candidate="os-zapret2-restyle-${version}.pkg"; fi
[ "${version}" = '0.4.0' ] || fail "unexpected project version ${version}"
[ "${revision}" -eq 26 ] || fail 'adaptive-budget revision must be exactly 26'

# Package construction and ABI/runtime requirements.
grep -Eq '^PLUGIN_DEPENDS=[[:space:]]+python313([[:space:]]|$)' "${MAKEFILE}" || fail 'python313 dependency is missing'
require "${BUILD_PKG}" 'python313)  echo "lang/python313"'
require "${BUILD_PKG}" 'cp -R src/opnsense "${STAGE}/usr/local/opnsense"'
require "${CI}" 'release: "15.0"'
require "${RELEASE}" "release: '15.0'"
if grep -REn "release:[[:space:]]*['\"]?14([.]|['\"]|$)" "${ROOT_DIR}/.github/workflows"; then
    fail 'a GitHub workflow still selects FreeBSD 14'
fi
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

# One canonical matrix discovers the new adaptive-budget contract automatically.
require "${CORRECTIVE_MATRIX}" "find \"\${ROOT_DIR}/scripts\" -maxdepth 1 -type f -name 'test-strategy-lab-*.sh'"
require "${ADAPTIVE_BUDGET_TEST}" 'PASS: Strategy Lab derives finite parent budgets from measured endpoint/capability/protocol work'

# `_26` production orchestration owns finite workload-derived parent budgets.
require "${ADAPTIVE_BUDGET_PY}" 'POLICY = "eligible-work-v1"'
require "${ADAPTIVE_BUDGET_PY}" 'REFERENCE_ENDPOINTS = 2'
require "${ADAPTIVE_BUDGET_PY}" 'IPV6_BASELINE_SECONDS_PER_ENDPOINT = 5'
require "${ADAPTIVE_BUDGET_PY}" 'QUIC_CANDIDATE_COUNT = 4'
require "${ADAPTIVE_BUDGET_PY}" 'UDP_CANDIDATE_COUNT = 3'
require "${ADAPTIVE_BUDGET_PY}" 'budget.standard_deadline = budget.started_epoch + budget.standard_budget'
require "${ADAPTIVE_BUDGET_PY}" 'budget.overall_deadline = budget.started_epoch + budget.search_budget'
require "${ADAPTIVE_BUDGET_PY}" '"budget_adaptation"'
require "${ADAPTIVE_BUDGET_PY}" 'return AdaptiveBudgetOrchestrator(job_id).run()'
require "${COMPAT_PY}" 'return adaptive_budget.orchestrator_main(args)'
require "${ADAPTIVE_BUDGET_DOC}" 'bounded child operation <= stage parent <= finite job parent'
require "${ADAPTIVE_BUDGET_PATCH}" 'This packaged patch changes **Strategy Lab parent-budget calculation only**.'

# Accepted Stage-60 architecture remains C -> B -> cold A; `_25` source-port ownership stays intact.
require "${MODEL_C_PRODUCTION_TEST}" 'PASS: production Stage 60 defaults to one warm Model C bucket'
require "${SOURCE_PORT_LEASE_TEST}" 'PASS: Stage 60 keeps free preferred ports'
require "${MODEL_C_PRODUCTION_PY}" 'MODEL = "C-warm-bucket-source-port-dispatch"'
require "${MODEL_C_PRODUCTION_PY}" 'MODEL_B = stage60_parallel.MODEL'
require "${MODEL_C_PRODUCTION_PY}" 'ThreadPoolExecutor(max_workers=len(decisions)'
require "${MODEL_C_PRODUCTION_PY}" 'physical_worker_count'
require "${MODEL_C_PRODUCTION_PY}" 'model_b_parallel_attribution._probe_endpoint'
require "${MODEL_C_PRODUCTION_PY}" 'fallback_execution_model'
require "${MODEL_C_PRODUCTION_PY}" 'STRATEGY_LAB_STAGE60_MODEL'
require "${MODEL_B_PRODUCTION_PY}" 'MODEL = "B-warm-worker-parallel-batched"'
require "${MODEL_B_PRODUCTION_PY}" 'WIDTH = 3'
require "${MODEL_B_PRODUCTION_PY}" 'A-cold-fallback'
require "${MODEL_B_PRODUCTION_PY}" 'no_cpu_gating'
require "${MODEL_B_PARALLEL_PY}" 'source_port_plan_unique'
require "${MODEL_B_PARALLEL_ATTRIBUTION_PY}" 'command_source_port_match'
require "${MODEL_B_PARALLEL_ATTRIBUTION_PY}" 'command_endpoint_match'
require "${MODEL_B_PARALLEL_ATTRIBUTION_PY}" 'result["intercepted"]'
require "${MODEL_B_PARALLEL_ADAPTER}" 'source-port-free'
require "${MODEL_B_PARALLEL_ADAPTER}" 'route-add-source'
require "${MODEL_C_SELECTOR}" 'function strategy_lab_model_c_source_port(desync)'
require "${SOURCE_PORT_LEASE_PY}" 'preferred-free-else-alternate'
require "${SOURCE_PORT_LEASE_PY}" 'original_model_c_batch'
require "${SOURCE_PORT_LEASE_PY}" 'original_model_b_batch'
require "${STAGE60_RUNNER}" 'stage60-parallel expand'
require "${EXPANSION_RUNNER}" 'strategy_lab_stage60_parallel_runner.sh'
require "${PYTHON_ENTRY}" 'from strategy_lab_py import stage60_source_port_lease'

for installed in \
    strategy_lab_py/state.py \
    strategy_lab_py/orchestrator.py \
    strategy_lab_py/late_containment.py \
    strategy_lab_py/adaptive_budget.py \
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
    strategy_lab_py/model_b_parallel.py \
    strategy_lab_py/model_b_parallel_attribution.py \
    strategy_lab_py/stage60_parallel.py \
    strategy_lab_py/stage60_model_c.py \
    strategy_lab_py/stage60_source_port_lease.py \
    strategy_lab_model_c.lua \
    strategy_lab_model_b_parallel_adapter.sh \
    strategy_lab_stage60_parallel_runner.sh \
    strategy_lab_expansion_runner.sh \
    strategy_lab_stage_adapter.sh
do
    [ -e "${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/${installed}" ] || fail "packaged source path is missing: ${installed}"
done

# Current source/live boundary is truthful: `_26` source, `_25` latest owner-tested package.
require "${MATRIX}" 'Current source candidate: `os-zapret2-restyle-0.4.0_26.pkg`'
require "${MATRIX}" 'Current published/owner-tested package: `os-zapret2-restyle-0.4.0_25.pkg`'
require "${MATRIX}" '`_26` ADAPTIVE-BUDGET OWNER-LIVE GATE — PENDING'
require "${MATRIX}" 'policy=eligible-work-v1'
require "${PROJECT_STATE}" 'Current source line: `VERSION=0.4.0`, `PLUGIN_REVISION=26`'
require "${PROJECT_STATE}" 'Latest owner-tested testing candidate: `v0.4.0_25`'
require "${PROJECT_STATE}" 'adaptive-budget.json'
require "${INDEX}" 'docs/patches/v0.4.0_26.md'
require "${INDEX}" 'STRATEGY_LAB_ADAPTIVE_BUDGET.md'

# Accepted history remains intact and independently evidenced.
require "${MODEL_B_LIVE}" 'PRODUCTION STAGE-60 MODEL B OWNER-LIVE PASS'
require "${MODEL_C_LIVE}" 'job.FaLtIk'
require "${MODEL_C_LIVE}" 'job.G0wC5l'
require "${MODEL_C_CORRECTIVE_PASS}" 'job.5yGde5'
require "${MODEL_C_CORRECTIVE_PASS}" '.parallel.fallbacks=[]'
require "${MODEL_B_PATCH}" 'This patch changes **Stage 60 only**.'
require "${MODEL_C_PATCH}" 'This packaged patch changes **Stage 60 runtime execution only**.'
require "${SOURCE_PORT_PATCH}" 'This patch changes **Stage 60 source-port ownership only**.'
require "${SOURCE_PORT_PATCH}" 'No Stage-60 timeout is increased in this patch.'
require "${MODEL_C_DECISION}" 'OWNER-AUTHORIZED FOR PRODUCTION CANDIDATE `_23`; OWNER-LIVE ACCEPTANCE PENDING'
require "${MODEL_B_DECISION}" 'APPROVED FOR IMPLEMENTATION; NOT YET PRODUCTION-ACTIVE'

sh -n "$0"
printf '%s\n' "PASS: FreeBSD 15 package CI packages ${candidate} with adaptive finite budgets while preserving accepted Model-C/Model-B/source-port boundaries"
