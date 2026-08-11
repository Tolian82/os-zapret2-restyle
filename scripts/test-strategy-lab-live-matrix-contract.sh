#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MATRIX="${ROOT_DIR}/docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md"
STATE="${ROOT_DIR}/docs/PROJECT_STATE.md"
VERSION_FILE="${ROOT_DIR}/VERSION"
MAKEFILE="${ROOT_DIR}/Makefile"
RELEASE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-08-v0.3.3_27-scenario-01-pass.md"
ADAPTIVE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-09-v0.4.0_2-stage60-family-reachability-pass.md"
TIMEOUT_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-09-v0.4.0_6-stage60-timeout.md"
LATE_STAGE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-10-v0.4.0_7-late-stage-pass.md"
TIMEOUT_CLOSEOUT_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-10-v0.4.0_8-timeout-containment-pass.md"
ADAPTIVE_VALIDATION_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-10-v0.4.0_9-adaptive-validation-pass.md"
MODEL_A_REFERENCE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-10-v0.4.0_11-model-a-reference-collected.md"
MODEL_B_ACCEPT_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-10-v0.4.0_16-model-b-live-accept.md"
MODEL_B_REPRO_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-11-v0.4.0_17-model-b-reproducibility.md"
MODEL_B_EXHAUSTIVE_GAP_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-11-v0.4.0_18-model-b-exhaustive-multi-endpoint-gap.md"
MODEL_B_EXHAUSTIVE_REPRO_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-11-v0.4.0_19-model-b-exhaustive-reproducibility.md"
MODEL_B_PARALLEL_REJECT_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-11-v0.4.0_20-model-b-parallel-attribution-reject.md"
MODEL_B_PARALLEL_ACCEPT_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-11-v0.4.0_21-model-b-parallel-reproducibility.md"
MODEL_B_EXHAUSTIVE_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/model_b_exhaustive.py"
MODEL_B_PARALLEL_PATCH="${ROOT_DIR}/docs/patches/v0.4.0_20.md"
MODEL_B_PARALLEL_CORRECTIVE_PATCH="${ROOT_DIR}/docs/patches/v0.4.0_21.md"
STAGE60_PRODUCTION_PATCH="${ROOT_DIR}/docs/patches/v0.4.0_22.md"
MODEL_B_PARALLEL_TEST="${ROOT_DIR}/scripts/test-strategy-lab-model-b-parallel.sh"
MODEL_B_PARALLEL_ATTRIBUTION_TEST="${ROOT_DIR}/scripts/test-strategy-lab-model-b-parallel-attribution.sh"
STAGE60_PRODUCTION_TEST="${ROOT_DIR}/scripts/test-strategy-lab-stage60-parallel-production.sh"
MODEL_B_PARALLEL_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/model_b_parallel.py"
MODEL_B_PARALLEL_ATTRIBUTION_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/model_b_parallel_attribution.py"
STAGE60_PRODUCTION_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_parallel.py"
MODEL_B_PARALLEL_ADAPTER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_model_b_parallel_adapter.sh"
MODEL_B_PARALLEL_LAUNCHER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_model_b_parallel.sh"
MODEL_B_PARALLEL_WORKER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_model_b_parallel_worker.sh"
STAGE60_PRODUCTION_RUNNER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_stage60_parallel_runner.sh"
PYTHON_ENTRY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_python.py"
MODEL_B_SELECTION_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-11-strategy-lab-parallel-model-b-selection.md"
LIVE_GATE_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md"

fail(){ echo "FAIL: $*" >&2; exit 1; }
require(){ grep -Fq "$2" "$1" || fail "missing contract text in $1: $2"; }

for file in \
    "${MATRIX}" "${STATE}" "${VERSION_FILE}" "${MAKEFILE}" \
    "${RELEASE_EVIDENCE}" "${ADAPTIVE_EVIDENCE}" "${TIMEOUT_EVIDENCE}" \
    "${LATE_STAGE_EVIDENCE}" "${TIMEOUT_CLOSEOUT_EVIDENCE}" \
    "${ADAPTIVE_VALIDATION_EVIDENCE}" "${MODEL_A_REFERENCE_EVIDENCE}" \
    "${MODEL_B_ACCEPT_EVIDENCE}" "${MODEL_B_REPRO_EVIDENCE}" \
    "${MODEL_B_EXHAUSTIVE_GAP_EVIDENCE}" "${MODEL_B_EXHAUSTIVE_REPRO_EVIDENCE}" \
    "${MODEL_B_PARALLEL_REJECT_EVIDENCE}" "${MODEL_B_PARALLEL_ACCEPT_EVIDENCE}" \
    "${MODEL_B_EXHAUSTIVE_PY}" "${MODEL_B_PARALLEL_PATCH}" \
    "${MODEL_B_PARALLEL_CORRECTIVE_PATCH}" "${STAGE60_PRODUCTION_PATCH}" \
    "${MODEL_B_PARALLEL_TEST}" "${MODEL_B_PARALLEL_ATTRIBUTION_TEST}" \
    "${STAGE60_PRODUCTION_TEST}" "${MODEL_B_PARALLEL_PY}" \
    "${MODEL_B_PARALLEL_ATTRIBUTION_PY}" "${STAGE60_PRODUCTION_PY}" \
    "${MODEL_B_PARALLEL_ADAPTER}" "${MODEL_B_PARALLEL_LAUNCHER}" \
    "${MODEL_B_PARALLEL_WORKER}" "${STAGE60_PRODUCTION_RUNNER}" "${PYTHON_ENTRY}" \
    "${MODEL_B_SELECTION_DECISION}" "${LIVE_GATE_DECISION}"
do
    [ -s "${file}" ] || fail "missing Strategy Lab live-gate record: ${file}"
done

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(awk -F= '/^PLUGIN_REVISION=/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${MAKEFILE}")
case "${revision}" in ''|*[!0-9]*) fail 'invalid plugin revision' ;; esac
candidate="os-zapret2-restyle-${version}_${revision}.pkg"
[ "${version}" = '0.4.0' ] || fail "unexpected active Strategy Lab version ${version}"
[ "${revision}" -eq 22 ] || fail 'production Stage-60 parallel integration revision must be exactly 22'

# Historical live boundary and accepted baselines remain intact.
require "${MATRIX}" 'Required package ABI: `FreeBSD:15:amd64`'
require "${MATRIX}" 'job.tMYnFA'
require "${MATRIX}" 'web.telegram.org'
require "${MATRIX}" 'mean 74.8082 s'
require "${MATRIX}" 'about 15.96%'
require "${MATRIX}" 'about 144.125 s'
require "${MATRIX}" 'about 71.023 s'
require "${MATRIX}" 'about 86.5%'
require "${MATRIX}" 'roughly 62.0%'

scenario_one=$(awk -F'|' '$2 ~ /^[[:space:]]*1[[:space:]]*$/ && $6 ~ /PASS ON `_27` — v0.4.0 mandatory row/ {n++} END {print n+0}' "${MATRIX}")
[ "${scenario_one}" -eq 1 ] || fail 'v0.4.0 mandatory Scenario 1 PASS row mismatch'
pending_count=$(awk -F'|' '$2 ~ /^[[:space:]]*([2-9]|1[0-8])[[:space:]]*$/ && $6 ~ /PENDING REGRESSION/ {n++} END {print n+0}' "${MATRIX}")
[ "${pending_count}" -eq 17 ] || fail 'rows 2-18 must remain honest pending regression coverage'

# Historical live evidence remains retained rather than rewritten by production integration.
require "${RELEASE_EVIDENCE}" 'Result: **SCENARIO 1 PASS on `v0.3.3_27`**.'
require "${ADAPTIVE_EVIDENCE}" 'Result: **ADAPTIVE-SEARCH `_28` FOCUSED LIVE PASS on `v0.4.0_2`**.'
require "${TIMEOUT_EVIDENCE}" 'Stage-60 adapter duration was approximately `70.07 s`'
require "${LATE_STAGE_EVIDENCE}" '| Standard | PASS | PASS | 90.243 s | 16/16 |'
require "${LATE_STAGE_EVIDENCE}" '| Extended | PASS | PASS | 89.249 s | 16/16 |'
require "${TIMEOUT_CLOSEOUT_EVIDENCE}" 'Standard — `job.FgjRCR`'
require "${TIMEOUT_CLOSEOUT_EVIDENCE}" 'Extended — `job.pv2Q09`'
require "${ADAPTIVE_VALIDATION_EVIDENCE}" 'Standard no-winner: `job.tU3wiL`'
require "${ADAPTIVE_VALIDATION_EVIDENCE}" 'Extended no-winner: `job.hsP8Ro`'
require "${ADAPTIVE_VALIDATION_EVIDENCE}" 'Standard winner-path: `job.UPRDlc`'
require "${MODEL_A_REFERENCE_EVIDENCE}" 'Job: `job.TtZeaH`'
require "${MODEL_A_REFERENCE_EVIDENCE}" 'Model A conclusion: `reference_collected`'
require "${MODEL_A_REFERENCE_EVIDENCE}" 'median: 4332 KiB'
require "${MODEL_B_ACCEPT_EVIDENCE}" 'This is the first owner-live Model B `accept` result.'
require "${MODEL_B_ACCEPT_EVIDENCE}" 'aggregate RSS: `12964 KiB`'
require "${MODEL_B_REPRO_EVIDENCE}" 'acceptance: `5/5`'
require "${MODEL_B_REPRO_EVIDENCE}" '`86.5%` reduction'
require "${MODEL_B_REPRO_EVIDENCE}" '`62.0%` reduction'
require "${MODEL_B_EXHAUSTIVE_GAP_EVIDENCE}" '`error="exhaustive Model B requires one pinned endpoint"`'
require "${MODEL_B_EXHAUSTIVE_REPRO_EVIDENCE}" 'OWNER-LIVE ACCEPT 5/5'
require "${MODEL_B_EXHAUSTIVE_REPRO_EVIDENCE}" '`74808.2 ms`'
require "${MODEL_B_EXHAUSTIVE_REPRO_EVIDENCE}" '`15.957%`'
require "${MODEL_B_EXHAUSTIVE_PY}" 'projection_is_measured_full_job'
require "${MODEL_B_EXHAUSTIVE_PY}" 'all_reference_endpoints_replayed'

# `_20` false reject and `_21` accepted reproducibility remain explicit historical evidence.
require "${MODEL_B_PARALLEL_REJECT_EVIDENCE}" '`route_attribution=false`'
require "${MODEL_B_PARALLEL_REJECT_EVIDENCE}" 'parallel exhaustive search: `32977 ms`'
require "${MODEL_B_PARALLEL_REJECT_EVIDENCE}" '`62.952%` faster'
require "${MODEL_B_PARALLEL_REJECT_EVIDENCE}" '`38.642%`'
require "${MODEL_B_PARALLEL_REJECT_EVIDENCE}" 'Batches 1–5 each requested width'
require "${MODEL_B_PARALLEL_ACCEPT_EVIDENCE}" 'six accepted controlled-parallel'
require "${MODEL_B_PARALLEL_ACCEPT_EVIDENCE}" '33025.6 ms'
require "${MODEL_B_PARALLEL_ACCEPT_EVIDENCE}" '62.8976%'
require "${MODEL_B_PARALLEL_PATCH}" 'Controlled parallel Model B candidate probes'
require "${MODEL_B_PARALLEL_PATCH}" 'unique controlled TCP source port'
require "${MODEL_B_PARALLEL_PATCH}" 'No CPU-count gate is used.'
require "${MODEL_B_PARALLEL_CORRECTIVE_PATCH}" 'For route attribution of a failed/blocked probe'
require "${MODEL_B_PARALLEL_PY}" 'B-warm-worker-parallel-batched'
require "${MODEL_B_PARALLEL_PY}" 'ThreadPoolExecutor(max_workers=len(slots)'
require "${MODEL_B_PARALLEL_PY}" 'source_port_plan_unique'
require "${MODEL_B_PARALLEL_PY}" 'candidate_parallelism_observed'
require "${MODEL_B_PARALLEL_PY}" 'endpoints_sequential_per_candidate'
require "${MODEL_B_PARALLEL_PY}" 'measurement_only_no_cpu_gating'
require "${MODEL_B_PARALLEL_ATTRIBUTION_PY}" 'command_source_port_match'
require "${MODEL_B_PARALLEL_ATTRIBUTION_PY}" 'command_endpoint_match'
require "${MODEL_B_PARALLEL_ATTRIBUTION_PY}" 'result["intercepted"]'
require "${MODEL_B_PARALLEL_ADAPTER}" 'route-add-source'
require "${MODEL_B_PARALLEL_ADAPTER}" 'from me "${_mb_source_port}" to "${_mb_address}"'
require "${MODEL_B_PARALLEL_TEST}" 'PASS: controlled parallel Model B uses three isolated warm workers with unique source-port routing'
require "${MODEL_B_PARALLEL_ATTRIBUTION_TEST}" 'PASS: parallel Model B attributes blocked probes by exact command binding plus exact IPFW counter growth'
require "${MODEL_B_PARALLEL_LAUNCHER}" '9>"${LIFECYCLE_LOCK_FILE}"'
require "${MODEL_B_PARALLEL_WORKER}" 'model-b-parallel finalize'
require "${PYTHON_ENTRY}" 'model_b_parallel_attribution as model_b_parallel'

# `_22` is source/CI production integration, not owner-live production verification yet.
require "${MODEL_B_SELECTION_DECISION}" 'APPROVED FOR IMPLEMENTATION; NOT YET PRODUCTION-ACTIVE'
require "${STAGE60_PRODUCTION_PATCH}" 'This patch changes **Stage 60 only**.'
require "${STAGE60_PRODUCTION_PATCH}" 'No parallel endpoint probing is introduced'
require "${STAGE60_PRODUCTION_PATCH}" 'STRATEGY_LAB_STAGE60_MODEL=cold'
require "${STAGE60_PRODUCTION_TEST}" 'PASS: production Stage 60 uses bounded width-three controlled-parallel warm batches'
require "${STAGE60_PRODUCTION_PY}" 'MODEL = "B-warm-worker-parallel-batched"'
require "${STAGE60_PRODUCTION_PY}" 'WIDTH = 3'
require "${STAGE60_PRODUCTION_PY}" 'A-cold-fallback'
require "${STAGE60_PRODUCTION_PY}" 'no_cpu_gating'
require "${STAGE60_PRODUCTION_RUNNER}" 'trap on_signal HUP INT TERM'

# Project recovery state retains accepted baselines until `_22` gets owner-live production
# no-winner and winner-path evidence.
require "${STATE}" 'sequential exhaustive ACCEPT 5/5 on `v0.4.0_19`'
require "${STATE}" 'mean measured candidate-runtime speedup of about 15.96%'

require "${LIVE_GATE_DECISION}" 'all-or-nothing release checklist.'
if grep -Fq 'Stable release preparation and pkg-repository promotion remain blocked until every' "${MATRIX}"; then
    fail 'blanket all-row stable-release gate returned'
fi

sh -n "$0"
echo "PASS: live matrix retains accepted history while ${candidate} integrates width-three parallel Model B into production Stage 60 pending owner-live no-winner/winner verification"
