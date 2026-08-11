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
STAGE60_PRODUCTION_PATCH="${ROOT_DIR}/docs/patches/v0.4.0_22.md"
STAGE60_PRODUCTION_TEST="${ROOT_DIR}/scripts/test-strategy-lab-stage60-parallel-production.sh"
STAGE60_PRODUCTION_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_parallel.py"
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
    "${STAGE60_PRODUCTION_PATCH}" "${STAGE60_PRODUCTION_TEST}" \
    "${STAGE60_PRODUCTION_PY}" "${MODEL_B_SELECTION_DECISION}" "${LIVE_GATE_DECISION}"
do
    [ -s "${file}" ] || fail "missing Strategy Lab live-gate record: ${file}"
done

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(awk -F= '/^PLUGIN_REVISION=/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${MAKEFILE}")
case "${revision}" in ''|*[!0-9]*) fail 'invalid plugin revision' ;; esac
candidate="os-zapret2-restyle-${version}_${revision}.pkg"
[ "${version}" = '0.4.0' ] || fail "unexpected active Strategy Lab version ${version}"
[ "${revision}" -eq 22 ] || fail 'production Stage-60 parallel integration revision must be exactly 22'

# Historical boundaries remain available and are not silently rewritten by the current
# production evidence.
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

# Current `_22` documents and live evidence must be synchronized. Historical `_9` behavior
# is explicitly retained as comparison evidence, not as the current Stage-60 completion rule.
require "${STATE}" 'Current source line: `VERSION=0.4.0`, `PLUGIN_REVISION=22`'
require "${STATE}" 'Latest published testing prerelease: `v0.4.0_22`'
require "${STATE}" 'Current Strategy Lab production Stage-60 engine:'
require "${STATE}" 'job.KpLHgb'
require "${STATE}" 'job.GK0X66'
require "${STATE}" 'job.d5XV82'
require "${STATE}" 'Do not diagnose current behavior from the older `_9` run'
require "${STATE}" 'sequential exhaustive ACCEPT 5/5 on `v0.4.0_19`'
require "${STATE}" 'mean measured candidate-runtime speedup of about 15.96%'

require "${INDEX}" 'For a current diagnosis, **do not start from an old evidence file**.'
require "${INDEX}" '2026-08-11-v0.4.0_22-production-model-b-live.md'

require "${MATRIX}" 'Latest published testing candidate: `os-zapret2-restyle-0.4.0_22.pkg`'
require "${MATRIX}" 'Latest owner-tested candidate: `os-zapret2-restyle-0.4.0_22.pkg`'
require "${MATRIX}" 'job.KpLHgb'
require "${MATRIX}" 'job.GK0X66'
require "${MATRIX}" 'job.d5XV82'
require "${MATRIX}" 'Stage 60 `34227 ms`'
require "${MATRIX}" 'Stage 60 `28151 ms`'
require "${MATRIX}" 'controlled source port is already in use: 42003'
require "${MATRIX}" 'The explicit `_22` `early_stop.triggered=true` branch was not reached'
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

# Dedicated `_22` evidence must retain exact production-path facts and evidence limits.
require "${MODEL_B_PRODUCTION_EVIDENCE}" 'PRODUCTION STAGE-60 MODEL B OWNER-LIVE PASS'
require "${MODEL_B_PRODUCTION_EVIDENCE}" 'job.KpLHgb'
require "${MODEL_B_PRODUCTION_EVIDENCE}" '`34227 ms`'
require "${MODEL_B_PRODUCTION_EVIDENCE}" 'job.GK0X66'
require "${MODEL_B_PRODUCTION_EVIDENCE}" '`28151 ms`'
require "${MODEL_B_PRODUCTION_EVIDENCE}" 'job.d5XV82'
require "${MODEL_B_PRODUCTION_EVIDENCE}" '`controlled source port is already in use: 42003`'
require "${MODEL_B_PRODUCTION_EVIDENCE}" 'The explicit `early_stop.triggered=true` branch was not exercised'
require "${MODEL_B_PRODUCTION_EVIDENCE}" 'must be read before drawing conclusions from an older run'

require "${STAGE60_PRODUCTION_PATCH}" 'This patch changes **Stage 60 only**.'
require "${STAGE60_PRODUCTION_PATCH}" 'No parallel endpoint probing is introduced'
require "${STAGE60_PRODUCTION_PATCH}" 'STRATEGY_LAB_STAGE60_MODEL=cold'
require "${STAGE60_PRODUCTION_PATCH}" 'Owner-live result — 2026-08-11'
require "${STAGE60_PRODUCTION_TEST}" 'PASS: production Stage 60 uses bounded width-three controlled-parallel warm batches'
require "${STAGE60_PRODUCTION_PY}" 'MODEL = "B-warm-worker-parallel-batched"'
require "${STAGE60_PRODUCTION_PY}" 'WIDTH = 3'
require "${STAGE60_PRODUCTION_PY}" 'A-cold-fallback'

require "${LIVE_GATE_DECISION}" 'all-or-nothing release checklist.'
if grep -Fq 'Stable release preparation and pkg-repository promotion remain blocked until every' "${MATRIX}"; then
    fail 'blanket all-row stable-release gate returned'
fi

sh -n "$0"
echo "PASS: live matrix and current state record ${candidate} production Model B owner-live evidence while preserving historical comparison records"
