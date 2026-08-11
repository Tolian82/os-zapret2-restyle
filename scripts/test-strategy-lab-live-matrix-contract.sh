#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MATRIX="${ROOT_DIR}/docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md"
THIRD_AUDIT="${ROOT_DIR}/docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md"
CLOSURE="${ROOT_DIR}/docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md"
STATE="${ROOT_DIR}/docs/PROJECT_STATE.md"
INDEX="${ROOT_DIR}/docs/INDEX.md"
RELEASE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-08-v0.3.3_27-scenario-01-pass.md"
ADAPTIVE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-09-v0.4.0_2-stage60-family-reachability-pass.md"
TIMEOUT_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-09-v0.4.0_6-stage60-timeout.md"
LATE_STAGE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-10-v0.4.0_7-late-stage-pass.md"
TIMEOUT_CLOSEOUT_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-10-v0.4.0_8-timeout-containment-pass.md"
ADAPTIVE_VALIDATION_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-10-v0.4.0_9-adaptive-validation-pass.md"
MODEL_A_GAP_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-10-v0.4.0_10-model-a-rss-gap.md"
MODEL_A_REFERENCE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-10-v0.4.0_11-model-a-reference-collected.md"
MODEL_A_PATCH="${ROOT_DIR}/docs/patches/v0.4.0_11.md"
MODEL_A_TEST="${ROOT_DIR}/scripts/test-strategy-lab-model-a-measurement.sh"
MODEL_B_PATCH="${ROOT_DIR}/docs/patches/v0.4.0_12.md"
MODEL_B_TEST="${ROOT_DIR}/scripts/test-strategy-lab-model-b-experiment.sh"
MODEL_B_PREFLIGHT_PATCH="${ROOT_DIR}/docs/patches/v0.4.0_13.md"
MODEL_B_PREFLIGHT_TEST="${ROOT_DIR}/scripts/test-strategy-lab-model-b-preflight.sh"
MODEL_B_WORKER_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-10-v0.4.0_13-model-b-worker-access-reject.md"
MODEL_B_ACCESS_PATCH="${ROOT_DIR}/docs/patches/v0.4.0_14.md"
MODEL_B_ACCEPT_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-10-v0.4.0_16-model-b-live-accept.md"
MODEL_B_FAILFAST_PATCH="${ROOT_DIR}/docs/patches/v0.4.0_17.md"
MODEL_B_FAILFAST_TEST="${ROOT_DIR}/scripts/test-strategy-lab-model-b-failed-readiness.sh"
MODEL_B_REPRO_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-11-v0.4.0_17-model-b-reproducibility.md"
MODEL_B_EXHAUSTIVE_PATCH="${ROOT_DIR}/docs/patches/v0.4.0_18.md"
MODEL_B_EXHAUSTIVE_GAP_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-11-v0.4.0_18-model-b-exhaustive-multi-endpoint-gap.md"
MODEL_B_MULTI_ENDPOINT_PATCH="${ROOT_DIR}/docs/patches/v0.4.0_19.md"
MODEL_B_EXHAUSTIVE_REPRO_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-11-v0.4.0_19-model-b-exhaustive-reproducibility.md"
MODEL_B_EXHAUSTIVE_TEST="${ROOT_DIR}/scripts/test-strategy-lab-model-b-exhaustive.sh"
MODEL_B_EXHAUSTIVE_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/model_b_exhaustive.py"
MODEL_B_EXHAUSTIVE_LAUNCHER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_model_b_exhaustive.sh"
MODEL_B_EXHAUSTIVE_WORKER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_model_b_exhaustive_worker.sh"
MODEL_B_PARALLEL_PATCH="${ROOT_DIR}/docs/patches/v0.4.0_20.md"
MODEL_B_PARALLEL_TEST="${ROOT_DIR}/scripts/test-strategy-lab-model-b-parallel.sh"
MODEL_B_PARALLEL_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/model_b_parallel.py"
MODEL_B_PARALLEL_ADAPTER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_model_b_parallel_adapter.sh"
MODEL_B_PARALLEL_LAUNCHER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_model_b_parallel.sh"
MODEL_B_PARALLEL_WORKER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_model_b_parallel_worker.sh"
LIVE_GATE_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md"
VERSION_FILE="${ROOT_DIR}/VERSION"
MAKEFILE="${ROOT_DIR}/Makefile"

fail(){ echo "FAIL: $*" >&2; exit 1; }
require(){ grep -Fq "$2" "$1" || fail "missing contract text in $1: $2"; }

for file in \
    "${MATRIX}" "${THIRD_AUDIT}" "${CLOSURE}" "${STATE}" "${INDEX}" \
    "${RELEASE_EVIDENCE}" "${ADAPTIVE_EVIDENCE}" "${TIMEOUT_EVIDENCE}" \
    "${LATE_STAGE_EVIDENCE}" "${TIMEOUT_CLOSEOUT_EVIDENCE}" \
    "${ADAPTIVE_VALIDATION_EVIDENCE}" "${MODEL_A_GAP_EVIDENCE}" \
    "${MODEL_A_REFERENCE_EVIDENCE}" "${MODEL_A_PATCH}" "${MODEL_A_TEST}" \
    "${MODEL_B_PATCH}" "${MODEL_B_TEST}" "${MODEL_B_PREFLIGHT_PATCH}" \
    "${MODEL_B_PREFLIGHT_TEST}" "${MODEL_B_WORKER_EVIDENCE}" \
    "${MODEL_B_ACCESS_PATCH}" "${MODEL_B_ACCEPT_EVIDENCE}" \
    "${MODEL_B_FAILFAST_PATCH}" "${MODEL_B_FAILFAST_TEST}" \
    "${MODEL_B_REPRO_EVIDENCE}" "${MODEL_B_EXHAUSTIVE_PATCH}" \
    "${MODEL_B_EXHAUSTIVE_GAP_EVIDENCE}" "${MODEL_B_MULTI_ENDPOINT_PATCH}" \
    "${MODEL_B_EXHAUSTIVE_REPRO_EVIDENCE}" "${MODEL_B_EXHAUSTIVE_TEST}" \
    "${MODEL_B_EXHAUSTIVE_PY}" "${MODEL_B_EXHAUSTIVE_LAUNCHER}" \
    "${MODEL_B_EXHAUSTIVE_WORKER}" "${MODEL_B_PARALLEL_PATCH}" \
    "${MODEL_B_PARALLEL_TEST}" "${MODEL_B_PARALLEL_PY}" \
    "${MODEL_B_PARALLEL_ADAPTER}" "${MODEL_B_PARALLEL_LAUNCHER}" \
    "${MODEL_B_PARALLEL_WORKER}" "${LIVE_GATE_DECISION}" "${VERSION_FILE}" "${MAKEFILE}"
do
    [ -s "${file}" ] || fail "missing Strategy Lab live-gate record: ${file}"
done

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(awk -F= '/^PLUGIN_REVISION=/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${MAKEFILE}")
case "${revision}" in ''|*[!0-9]*) fail 'invalid plugin revision' ;; esac
candidate="os-zapret2-restyle-${version}_${revision}.pkg"

require "${MATRIX}" 'Overall status: **RELEASE-SELECTED LIVE GATE PASS ON `_27`; ADAPTIVE `_28` FOCUSED PASS; `_32` TIMEOUT-CONTAINMENT LIVE PASS; `_33` ADAPTIVE-VALIDATION CHANGE-SPECIFIC LIVE PASS; MODEL A COLD REFERENCE COLLECTED ON `_11`; MODEL B `_17` REPEATED COEXISTENCE ACCEPT 5/5 (EXPERIMENT ONLY); `_18` EXHAUSTIVE INPUT-CONTRACT REJECT WITH RESTORATION PASS; `_19` SEQUENTIAL EXHAUSTIVE ACCEPT 5/5; `_20` CONTROLLED PARALLEL-PROBE SOURCE CANDIDATE; FULL REGRESSION MATRIX OPEN**'
require "${MATRIX}" 'Required package ABI: `FreeBSD:15:amd64`'
require "${MATRIX}" 'Latest published testing candidate: `os-zapret2-restyle-0.4.0_19.pkg`'
require "${MATRIX}" 'Latest owner-tested candidate: `os-zapret2-restyle-0.4.0_19.pkg`'
require "${MATRIX}" "Current source candidate: \`${candidate}\`"
require "${MATRIX}" 'Current source purpose: `_20` experiment-only controlled parallel probing of up to three already-isolated warm Model B candidates; production Strategy Lab remains Model A'
require "${MATRIX}" 'Latest owner-tested Standard no-winner job: `job.tMYnFA` (`telegram.org`, 16/16 `graph_exhausted`, measurement-only 210-second Standard budget override)'
require "${MATRIX}" 'docs/verification/evidence/2026-08-11-v0.4.0_19-model-b-exhaustive-reproducibility.md'
require "${MATRIX}" 'MODEL B `_20` CONTROLLED PARALLEL CANDIDATE-PROBE EXPERIMENT — SOURCE CANDIDATE'
require "${MATRIX}" 'unique controlled TCP source port'
require "${MATRIX}" 'CPU count is measurement metadata only'
require "${MATRIX}" 'about 144.125 s'
require "${MATRIX}" 'about 71.023 s'
require "${MATRIX}" 'about 86.5%'
require "${MATRIX}" 'roughly 62.0%'
require "${MATRIX}" 'job.tMYnFA'
require "${MATRIX}" 'web.telegram.org'
require "${MATRIX}" 'mean 74808.2 ms'
require "${MATRIX}" 'about 15.96%'

scenario_one=$(awk -F'|' '$2 ~ /^[[:space:]]*1[[:space:]]*$/ && $6 ~ /PASS ON `_27` — v0.4.0 mandatory row/ {n++} END {print n+0}' "${MATRIX}")
[ "${scenario_one}" -eq 1 ] || fail 'v0.4.0 mandatory Scenario 1 PASS row mismatch'
pending_count=$(awk -F'|' '$2 ~ /^[[:space:]]*([2-9]|1[0-8])[[:space:]]*$/ && $6 ~ /PENDING REGRESSION/ {n++} END {print n+0}' "${MATRIX}")
[ "${pending_count}" -eq 17 ] || fail 'rows 2-18 must remain honest pending regression coverage'

# Historical release/adaptive/timeout gates remain exact.
require "${RELEASE_EVIDENCE}" 'Result: **SCENARIO 1 PASS on `v0.3.3_27`**.'
require "${ADAPTIVE_EVIDENCE}" 'Result: **ADAPTIVE-SEARCH `_28` FOCUSED LIVE PASS on `v0.4.0_2`**.'
require "${ADAPTIVE_EVIDENCE}" '| Stage 60 | PASS; `total_available=14`, `completed=14`'
require "${TIMEOUT_EVIDENCE}" 'Stage-60 adapter duration was approximately `70.07 s`'
require "${LATE_STAGE_EVIDENCE}" '| Standard | PASS | PASS | 90.243 s | 16/16 |'
require "${LATE_STAGE_EVIDENCE}" '| Extended | PASS | PASS | 89.249 s | 16/16 |'
require "${TIMEOUT_CLOSEOUT_EVIDENCE}" 'Standard — `job.FgjRCR`'
require "${TIMEOUT_CLOSEOUT_EVIDENCE}" 'Extended — `job.pv2Q09`'
require "${ADAPTIVE_VALIDATION_EVIDENCE}" 'Standard no-winner: `job.tU3wiL`'
require "${ADAPTIVE_VALIDATION_EVIDENCE}" 'Extended no-winner: `job.hsP8Ro`'
require "${ADAPTIVE_VALIDATION_EVIDENCE}" 'Standard winner-path: `job.UPRDlc`'
require "${ADAPTIVE_VALIDATION_EVIDENCE}" 'stopped intentionally with `stopped_reason=enough_candidates` after checking `6` candidates'
require "${ADAPTIVE_VALIDATION_EVIDENCE}" '`temporary_runtime_clean=true`'

# Model A remains the accepted cold correctness/performance reference.
require "${MODEL_A_GAP_EVIDENCE}" 'Job: `job.Oeq7Rc`'
require "${MODEL_A_GAP_EVIDENCE}" 'It collected 25 cold candidate samples.'
require "${MODEL_A_REFERENCE_EVIDENCE}" 'Job: `job.TtZeaH`'
require "${MODEL_A_REFERENCE_EVIDENCE}" 'Model A conclusion: `reference_collected`'
require "${MODEL_A_REFERENCE_EVIDENCE}" 'median: 4332 KiB'
require "${MODEL_A_PATCH}" 'propagate candidate RSS into Model A evidence'
require "${MODEL_A_TEST}" 'model-a summarize'

# Model B historical safety/equivalence evidence is retained.
require "${MODEL_B_PATCH}" 'Model B warm-worker coexistence experiment harness'
require "${MODEL_B_PATCH}" '`production_approved=false`'
require "${MODEL_B_TEST}" 'PASS: Model B experiment keeps three warm workers isolated'
require "${MODEL_B_PREFLIGHT_PATCH}" 'Model B clean-preflight corrective'
require "${MODEL_B_PREFLIGHT_TEST}" 'PASS: Model B preflight returns success when all dedicated rules/ports are free'
require "${MODEL_B_WORKER_EVIDENCE}" '`all_workers_ready=false`'
require "${MODEL_B_WORKER_EVIDENCE}" '`restoration.verified=true`'
require "${MODEL_B_ACCESS_PATCH}" 'restore the retained Model B root to private `0700`'
require "${MODEL_B_ACCEPT_EVIDENCE}" 'This is the first owner-live Model B `accept` result.'
require "${MODEL_B_ACCEPT_EVIDENCE}" 'aggregate RSS: `12964 KiB`'
require "${MODEL_B_ACCEPT_EVIDENCE}" '`production_approved=false`'
require "${MODEL_B_FAILFAST_PATCH}" '`downstream_actions_skipped=true`'
require "${MODEL_B_FAILFAST_TEST}" 'PASS: Model B failed pool readiness rejects immediately, skips probes/stop/death, and still requests bounded cleanup'
require "${MODEL_B_REPRO_EVIDENCE}" 'acceptance: `5/5`'
require "${MODEL_B_REPRO_EVIDENCE}" '`86.5%` reduction'
require "${MODEL_B_REPRO_EVIDENCE}" '`62.0%` reduction'

# Exhaustive sequential Model B progressed from the `_18` gap to `_19` 5/5 acceptance.
require "${MODEL_B_EXHAUSTIVE_PATCH}" 'Model B exhaustive no-candidate benchmark'
require "${MODEL_B_EXHAUSTIVE_PATCH}" 'at most three warm dvtws2 workers at once'
require "${MODEL_B_EXHAUSTIVE_GAP_EVIDENCE}" 'job.tMYnFA'
require "${MODEL_B_EXHAUSTIVE_GAP_EVIDENCE}" '`completed=16`'
require "${MODEL_B_EXHAUSTIVE_GAP_EVIDENCE}" '`stopped_reason=graph_exhausted`'
require "${MODEL_B_EXHAUSTIVE_GAP_EVIDENCE}" '`error="exhaustive Model B requires one pinned endpoint"`'
require "${MODEL_B_MULTI_ENDPOINT_PATCH}" 'Model B exhaustive multi-endpoint reference corrective'
require "${MODEL_B_EXHAUSTIVE_REPRO_EVIDENCE}" 'OWNER-LIVE ACCEPT 5/5'
require "${MODEL_B_EXHAUSTIVE_REPRO_EVIDENCE}" '`74808.2 ms`'
require "${MODEL_B_EXHAUSTIVE_REPRO_EVIDENCE}" '`15.957%`'
require "${MODEL_B_EXHAUSTIVE_PY}" 'projection_is_measured_full_job'
require "${MODEL_B_EXHAUSTIVE_PY}" 'all_reference_endpoints_replayed'
require "${MODEL_B_EXHAUSTIVE_TEST}" 'PASS: exhaustive Model B benchmark replays a complete graph-exhausted multi-endpoint corpus'
require "${MODEL_B_EXHAUSTIVE_LAUNCHER}" '9>"${LIFECYCLE_LOCK_FILE}"'
require "${MODEL_B_EXHAUSTIVE_WORKER}" 'model-b-exhaustive finalize'

# `_20` changes only the experiment harness: three candidate tasks may overlap, while
# each candidate retains sequential endpoints and deterministic source-port traffic ownership.
require "${MODEL_B_PARALLEL_PATCH}" 'Controlled parallel Model B candidate probes'
require "${MODEL_B_PARALLEL_PATCH}" 'unique controlled TCP source port'
require "${MODEL_B_PARALLEL_PATCH}" 'No CPU-count gate is used.'
require "${MODEL_B_PARALLEL_PY}" 'B-warm-worker-parallel-batched'
require "${MODEL_B_PARALLEL_PY}" 'ThreadPoolExecutor'
require "${MODEL_B_PARALLEL_PY}" 'source_port_plan_unique'
require "${MODEL_B_PARALLEL_PY}" 'candidate_parallelism_observed'
require "${MODEL_B_PARALLEL_PY}" 'endpoints_sequential_per_candidate'
require "${MODEL_B_PARALLEL_PY}" 'measurement_only_no_cpu_gating'
require "${MODEL_B_PARALLEL_ADAPTER}" 'route-add-source'
require "${MODEL_B_PARALLEL_ADAPTER}" 'from me "${_mb_source_port}" to "${_mb_address}"'
require "${MODEL_B_PARALLEL_TEST}" 'PASS: controlled parallel Model B uses three isolated warm workers with unique source-port routing'
require "${MODEL_B_PARALLEL_LAUNCHER}" '9>"${LIFECYCLE_LOCK_FILE}"'
require "${MODEL_B_PARALLEL_WORKER}" 'model-b-parallel finalize'

require "${STATE}" 'Latest published testing prerelease: `v0.4.0_19` / `os-zapret2-restyle-0.4.0_19.pkg`'
require "${STATE}" 'Latest owner-tested testing candidate: `v0.4.0_19` / `os-zapret2-restyle-0.4.0_19.pkg`'
require "${STATE}" "Current source candidate: \`${candidate}\`"
require "${STATE}" 'sequential exhaustive ACCEPT 5/5 on `v0.4.0_19`'
require "${STATE}" '`_20` controlled parallel candidate probes selected'
require "${STATE}" 'mean measured candidate-runtime speedup of about 15.96%'

require "${LIVE_GATE_DECISION}" 'It is not an'
require "${LIVE_GATE_DECISION}" 'all-or-nothing release checklist.'
if grep -Fq 'Stable release preparation and pkg-repository promotion remain blocked until every' "${MATRIX}"; then
    fail 'blanket all-row stable-release gate returned'
fi

[ "${version}" = '0.4.0' ] || fail "unexpected active Strategy Lab source version ${version}"
[ "${revision}" -eq 20 ] || fail 'controlled parallel Model B experiment revision must be exactly 20'

echo "PASS: historical Strategy Lab live/Model A/Model B safety evidence remains retained, _19 sequential exhaustive is owner-live reproducible 5/5, ${candidate} is the controlled parallel experiment, and rows 2-18 remain regression backlog"
