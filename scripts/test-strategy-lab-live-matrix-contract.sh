#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MATRIX="${ROOT_DIR}/docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md"
STATE="${ROOT_DIR}/docs/PROJECT_STATE.md"
INDEX="${ROOT_DIR}/docs/INDEX.md"
VERSION_FILE="${ROOT_DIR}/VERSION"
MAKEFILE="${ROOT_DIR}/Makefile"
TIMEOUT_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-09-v0.4.0_6-stage60-timeout.md"
LATE_STAGE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-10-v0.4.0_7-late-stage-pass.md"
TIMEOUT_CLOSEOUT_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-10-v0.4.0_8-timeout-containment-pass.md"
ADAPTIVE_VALIDATION_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-10-v0.4.0_9-adaptive-validation-pass.md"
MODEL_A_REFERENCE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-10-v0.4.0_11-model-a-reference-collected.md"
MODEL_B_EXHAUSTIVE_REPRO_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-11-v0.4.0_19-model-b-exhaustive-reproducibility.md"
MODEL_B_PARALLEL_REJECT_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-11-v0.4.0_20-model-b-parallel-attribution-reject.md"
MODEL_B_PARALLEL_ACCEPT_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-11-v0.4.0_21-model-b-parallel-reproducibility.md"
MODEL_B_PRODUCTION_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md"
MODEL_B_PATCH="${ROOT_DIR}/docs/patches/v0.4.0_22.md"
MODEL_C_PATCH="${ROOT_DIR}/docs/patches/v0.4.0_23.md"
MODEL_C_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-11-strategy-lab-model-c-production-switch.md"
MODEL_C_ARCH="${ROOT_DIR}/docs/architecture/STRATEGY_LAB_MODEL_C.md"
MODEL_C_TEST="${ROOT_DIR}/scripts/test-strategy-lab-stage60-model-c-production.sh"
MODEL_C_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_model_c.py"
MODEL_B_TEST="${ROOT_DIR}/scripts/test-strategy-lab-stage60-parallel-production.sh"
MODEL_B_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_parallel.py"
MODEL_B_SELECTION_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-11-strategy-lab-parallel-model-b-selection.md"
LIVE_GATE_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md"

fail(){ echo "FAIL: $*" >&2; exit 1; }
require(){ grep -Fq "$2" "$1" || fail "missing contract text in $1: $2"; }

for file in \
    "${MATRIX}" "${STATE}" "${INDEX}" "${VERSION_FILE}" "${MAKEFILE}" \
    "${TIMEOUT_EVIDENCE}" "${LATE_STAGE_EVIDENCE}" "${TIMEOUT_CLOSEOUT_EVIDENCE}" \
    "${ADAPTIVE_VALIDATION_EVIDENCE}" "${MODEL_A_REFERENCE_EVIDENCE}" \
    "${MODEL_B_EXHAUSTIVE_REPRO_EVIDENCE}" "${MODEL_B_PARALLEL_REJECT_EVIDENCE}" \
    "${MODEL_B_PARALLEL_ACCEPT_EVIDENCE}" "${MODEL_B_PRODUCTION_EVIDENCE}" \
    "${MODEL_B_PATCH}" "${MODEL_C_PATCH}" "${MODEL_C_DECISION}" "${MODEL_C_ARCH}" \
    "${MODEL_C_TEST}" "${MODEL_C_PY}" "${MODEL_B_TEST}" "${MODEL_B_PY}" \
    "${MODEL_B_SELECTION_DECISION}" "${LIVE_GATE_DECISION}"
do
    [ -s "${file}" ] || fail "missing Strategy Lab live-gate record: ${file}"
done

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(awk -F= '/^PLUGIN_REVISION=/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${MAKEFILE}")
case "${revision}" in ''|*[!0-9]*) fail 'invalid plugin revision' ;; esac
candidate="os-zapret2-restyle-${version}_${revision}.pkg"
[ "${version}" = '0.4.0' ] || fail "unexpected active Strategy Lab version ${version}"
[ "${revision}" -eq 23 ] || fail 'Model-C production candidate revision must be exactly 23'

# Historical correction/evidence boundaries stay immutable and available.
require "${TIMEOUT_EVIDENCE}" 'Stage-60 adapter duration was approximately `70.07 s`'
require "${LATE_STAGE_EVIDENCE}" '| Standard | PASS | PASS | 90.243 s | 16/16 |'
require "${LATE_STAGE_EVIDENCE}" '| Extended | PASS | PASS | 89.249 s | 16/16 |'
require "${TIMEOUT_CLOSEOUT_EVIDENCE}" 'Standard — `job.FgjRCR`'
require "${TIMEOUT_CLOSEOUT_EVIDENCE}" 'Extended — `job.pv2Q09`'
require "${ADAPTIVE_VALIDATION_EVIDENCE}" 'Standard winner-path: `job.UPRDlc`'
require "${MODEL_A_REFERENCE_EVIDENCE}" 'Job: `job.TtZeaH`'
require "${MODEL_A_REFERENCE_EVIDENCE}" 'Model A conclusion: `reference_collected`'
require "${MODEL_B_EXHAUSTIVE_REPRO_EVIDENCE}" 'OWNER-LIVE ACCEPT 5/5'
require "${MODEL_B_EXHAUSTIVE_REPRO_EVIDENCE}" '`74808.2 ms`'
require "${MODEL_B_PARALLEL_REJECT_EVIDENCE}" '`route_attribution=false`'
require "${MODEL_B_PARALLEL_ACCEPT_EVIDENCE}" 'six accepted controlled-parallel'
require "${MODEL_B_PARALLEL_ACCEPT_EVIDENCE}" '33025.6 ms'
require "${MODEL_B_SELECTION_DECISION}" 'IMPLEMENTED IN `v0.4.0_22`; PRODUCTION-ACTIVE WITH COLD MODEL A FALLBACK'

# `_23` current-state authority must be explicit and must not fabricate owner-live PASS.
require "${STATE}" 'Current source line: `VERSION=0.4.0`, `PLUGIN_REVISION=23`'
require "${STATE}" 'Current source candidate: `os-zapret2-restyle-0.4.0_23.pkg`'
require "${STATE}" 'Latest owner-tested testing candidate: `v0.4.0_22`'
require "${STATE}" 'C-warm-bucket-source-port-dispatch'
require "${STATE}" 'B-warm-worker-parallel-batched'
require "${STATE}" 'Model C has not yet been owner-live tested'
require "${STATE}" 'job.KpLHgb'
require "${STATE}" 'job.GK0X66'
require "${STATE}" 'job.d5XV82'

require "${INDEX}" 'For a current diagnosis, **do not start from an old evidence file**.'
require "${INDEX}" 'docs/patches/v0.4.0_23.md'
require "${INDEX}" 'DEC-2026-08-11-strategy-lab-model-c-production-switch.md'
require "${INDEX}" '2026-08-11-v0.4.0_22-production-model-b-live.md'

require "${MATRIX}" 'Current source candidate: `os-zapret2-restyle-0.4.0_23.pkg`'
require "${MATRIX}" 'Latest owner-tested candidate: `os-zapret2-restyle-0.4.0_22.pkg`'
require "${MATRIX}" 'C-warm-bucket-source-port-dispatch'
require "${MATRIX}" 'MODEL-C PRODUCTION CANDIDATE PENDING OWNER-LIVE VERIFICATION'
require "${MATRIX}" 'physical_worker_count=1'
require "${MATRIX}" 'job.KpLHgb'
require "${MATRIX}" 'job.GK0X66'
require "${MATRIX}" 'job.d5XV82'
require "${MATRIX}" 'Stage 60 `34227 ms`'
require "${MATRIX}" 'Stage 60 `28151 ms`'
require "${MATRIX}" 'controlled source port is already in use: 42003'
require "${MATRIX}" 'Adaptive `_28` focused evidence:'
require "${MATRIX}" 'about 144.125 s'
require "${MATRIX}" 'about 71.023 s'
require "${MATRIX}" 'about 86.5%'
require "${MATRIX}" 'roughly 62.0%'
require "${MATRIX}" 'mean 74.8082 s'
require "${MATRIX}" 'about 15.96%'

scenario_one=$(awk -F'|' '$2 ~ /^[[:space:]]*1[[:space:]]*$/ && $6 ~ /PASS ON `_27` — v0.4.0 mandatory row/ {n++} END {print n+0}' "${MATRIX}")
[ "${scenario_one}" -eq 1 ] || fail 'v0.4.0 mandatory Scenario 1 PASS row mismatch'
pending_count=$(awk -F'|' '$2 ~ /^[[:space:]]*([2-9]|1[0-8])[[:space:]]*$/ && $6 ~ /PENDING REGRESSION/ {n++} END {print n+0}' "${MATRIX}")
[ "${pending_count}" -eq 17 ] || fail 'rows 2-18 must remain honest pending regression coverage'

# `_22` remains the accepted owner-live fallback/reference evidence.
require "${MODEL_B_PRODUCTION_EVIDENCE}" 'PRODUCTION STAGE-60 MODEL B OWNER-LIVE PASS'
require "${MODEL_B_PRODUCTION_EVIDENCE}" 'job.KpLHgb'
require "${MODEL_B_PRODUCTION_EVIDENCE}" '`34227 ms`'
require "${MODEL_B_PRODUCTION_EVIDENCE}" 'job.GK0X66'
require "${MODEL_B_PRODUCTION_EVIDENCE}" '`28151 ms`'
require "${MODEL_B_PRODUCTION_EVIDENCE}" 'job.d5XV82'
require "${MODEL_B_PRODUCTION_EVIDENCE}" '`controlled source port is already in use: 42003`'
require "${MODEL_B_PRODUCTION_EVIDENCE}" 'must be read before drawing conclusions from an older run'
require "${MODEL_B_PATCH}" 'This patch changes **Stage 60 only**.'

# `_23` source contract: Model C first, accepted Model B second, cold A last.
require "${MODEL_C_PATCH}" 'This packaged patch changes **Stage 60 runtime execution only**.'
require "${MODEL_C_PATCH}" 'C-warm-bucket-source-port-dispatch'
require "${MODEL_C_PATCH}" 'Model C -> Model B -> cold Model A'
require "${MODEL_C_DECISION}" 'OWNER-AUTHORIZED FOR PRODUCTION CANDIDATE `_23`; OWNER-LIVE ACCEPTANCE PENDING'
require "${MODEL_C_ARCH}" 'Model C -> Model B -> Model A cold'
require "${MODEL_C_TEST}" 'PASS: production Stage 60 defaults to one warm Model C bucket'
require "${MODEL_C_PY}" 'MODEL = "C-warm-bucket-source-port-dispatch"'
require "${MODEL_C_PY}" 'physical_worker_count'
require "${MODEL_C_PY}" 'model_b_parallel_attribution._probe_endpoint'
require "${MODEL_B_TEST}" 'accepted width-three Model B remains a production fallback/reference'
require "${MODEL_B_PY}" 'MODEL = "B-warm-worker-parallel-batched"'
require "${MODEL_B_PY}" 'A-cold-fallback'

require "${LIVE_GATE_DECISION}" 'all-or-nothing release checklist.'
if grep -Fq 'Stable release preparation and pkg-repository promotion remain blocked until every' "${MATRIX}"; then
    fail 'blanket all-row stable-release gate returned'
fi

sh -n "$0"
echo "PASS: live matrix records ${candidate} as Model-C source/package candidate while preserving the accepted _22 owner-live Model-B baseline"
