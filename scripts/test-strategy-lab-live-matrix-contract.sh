#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MATRIX="${ROOT_DIR}/docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md"
STATE="${ROOT_DIR}/docs/PROJECT_STATE.md"
RELEASE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-08-v0.3.3_27-scenario-01-pass.md"
TIMEOUT_CLOSEOUT_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-10-v0.4.0_8-timeout-containment-pass.md"
ADAPTIVE_VALIDATION_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-10-v0.4.0_9-adaptive-validation-pass.md"
MODEL_A_REFERENCE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-10-v0.4.0_11-model-a-reference-collected.md"
MODEL_B_ACCEPT_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-10-v0.4.0_16-model-b-live-accept.md"
MODEL_B_REPRO_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-11-v0.4.0_17-model-b-reproducibility.md"
MODEL_B_FAILFAST_PATCH="${ROOT_DIR}/docs/patches/v0.4.0_17.md"
MODEL_B_FAILFAST_TEST="${ROOT_DIR}/scripts/test-strategy-lab-model-b-failed-readiness.sh"
MODEL_B_EXHAUSTIVE_PATCH="${ROOT_DIR}/docs/patches/v0.4.0_18.md"
MODEL_B_EXHAUSTIVE_TEST="${ROOT_DIR}/scripts/test-strategy-lab-model-b-exhaustive.sh"
MODEL_B_EXHAUSTIVE_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/model_b_exhaustive.py"
MODEL_B_EXHAUSTIVE_LAUNCHER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_model_b_exhaustive.sh"
MODEL_B_EXHAUSTIVE_WORKER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_model_b_exhaustive_worker.sh"
LIVE_GATE_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md"
VERSION_FILE="${ROOT_DIR}/VERSION"
MAKEFILE="${ROOT_DIR}/Makefile"

for file in \
    "${MATRIX}" "${STATE}" "${RELEASE_EVIDENCE}" "${TIMEOUT_CLOSEOUT_EVIDENCE}" \
    "${ADAPTIVE_VALIDATION_EVIDENCE}" "${MODEL_A_REFERENCE_EVIDENCE}" \
    "${MODEL_B_ACCEPT_EVIDENCE}" "${MODEL_B_REPRO_EVIDENCE}" \
    "${MODEL_B_FAILFAST_PATCH}" "${MODEL_B_FAILFAST_TEST}" \
    "${MODEL_B_EXHAUSTIVE_PATCH}" "${MODEL_B_EXHAUSTIVE_TEST}" \
    "${MODEL_B_EXHAUSTIVE_PY}" "${MODEL_B_EXHAUSTIVE_LAUNCHER}" \
    "${MODEL_B_EXHAUSTIVE_WORKER}" "${LIVE_GATE_DECISION}" \
    "${VERSION_FILE}" "${MAKEFILE}"
do
    [ -s "${file}" ] || { echo "FAIL: missing Strategy Lab live-gate record: ${file}" >&2; exit 1; }
done

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(awk -F= '/^PLUGIN_REVISION=/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${MAKEFILE}")
case "${revision}" in ''|*[!0-9]*) echo 'FAIL: invalid plugin revision' >&2; exit 1 ;; esac
candidate="os-zapret2-restyle-${version}_${revision}.pkg"

[ "${version}" = '0.4.0' ] || { echo "FAIL: unexpected source version ${version}" >&2; exit 1; }
[ "${revision}" -eq 18 ] || { echo "FAIL: exhaustive Model B benchmark must be revision 18, found ${revision}" >&2; exit 1; }

grep -Fq 'MODEL B `_17` REPEATED COEXISTENCE ACCEPT 5/5 (EXPERIMENT ONLY); `_18` EXHAUSTIVE NO-CANDIDATE BENCHMARK SOURCE CANDIDATE' "${MATRIX}"
grep -Fq 'Required package ABI: `FreeBSD:15:amd64`' "${MATRIX}"
grep -Fq 'Latest published testing candidate: `os-zapret2-restyle-0.4.0_17.pkg`' "${MATRIX}"
grep -Fq 'Latest owner-installed testing candidate: `os-zapret2-restyle-0.4.0_17.pkg`' "${MATRIX}"
grep -Fq "Current source candidate: \`${candidate}\`" "${MATRIX}"
grep -Fq 'Current source purpose: `_18` experiment-only batched exhaustive Model B benchmark for Standard `NO_CANDIDATE / graph_exhausted`' "${MATRIX}"
grep -Fq 'Historical Standard no-winner timing job: `job.tU3wiL` (`telegram.org`)' "${MATRIX}"
grep -Fq 'all 16 Stage-60 candidates checked' "${MATRIX}"
grep -Fq 'total through restoration about `144.125 s`' "${MATRIX}"
grep -Fq 'total about `71.023 s`' "${MATRIX}"
grep -Fq 'roughly `62.0%` below the cold median' "${MATRIX}"
grep -Fq 'about `86.5%` below Model A' "${MATRIX}"
grep -Fq 'at most three warm workers per batch' "${MATRIX}"
grep -Fq '`production_approved=false`' "${MATRIX}"

scenario_one=$(awk -F'|' '$2 ~ /^[[:space:]]*1[[:space:]]*$/ && $6 ~ /PASS ON `_27` — v0.4.0 mandatory row/ {n++} END {print n+0}' "${MATRIX}")
[ "${scenario_one}" -eq 1 ] || { echo 'FAIL: mandatory Scenario 1 PASS row mismatch' >&2; exit 1; }
pending_count=$(awk -F'|' '$2 ~ /^[[:space:]]*([2-9]|1[0-8])[[:space:]]*$/ && $6 ~ /PENDING REGRESSION/ {n++} END {print n+0}' "${MATRIX}")
[ "${pending_count}" -eq 17 ] || { echo 'FAIL: rows 2-18 must remain pending regression coverage' >&2; exit 1; }

grep -Fq 'Result: **SCENARIO 1 PASS on `v0.3.3_27`**.' "${RELEASE_EVIDENCE}"
grep -Fq 'Stage 60: 0 working candidates, 16 candidates checked' "${TIMEOUT_CLOSEOUT_EVIDENCE}"
grep -Fq 'Standard no-winner: `job.tU3wiL`' "${ADAPTIVE_VALIDATION_EVIDENCE}"
grep -Fq 'Extended no-winner: `job.hsP8Ro`' "${ADAPTIVE_VALIDATION_EVIDENCE}"
grep -Fq 'Standard winner-path: `job.UPRDlc`' "${ADAPTIVE_VALIDATION_EVIDENCE}"
grep -Fq 'stopped intentionally with `stopped_reason=enough_candidates` after checking `6` candidates' "${ADAPTIVE_VALIDATION_EVIDENCE}"
grep -Fq 'Model A conclusion: `reference_collected`' "${MODEL_A_REFERENCE_EVIDENCE}"
grep -Fq 'median: 4332 KiB' "${MODEL_A_REFERENCE_EVIDENCE}"
grep -Fq 'This is the first owner-live Model B `accept` result.' "${MODEL_B_ACCEPT_EVIDENCE}"
grep -Fq 'aggregate RSS: `12964 KiB`' "${MODEL_B_ACCEPT_EVIDENCE}"
grep -Fq 'acceptance: `5/5`' "${MODEL_B_REPRO_EVIDENCE}"
grep -Fq 'mean pool startup: `1163.6 ms`' "${MODEL_B_REPRO_EVIDENCE}"
grep -Fq '`86.5%` reduction' "${MODEL_B_REPRO_EVIDENCE}"
grep -Fq '`62.0%` reduction' "${MODEL_B_REPRO_EVIDENCE}"

grep -Fq 'Model B failed-readiness fail-fast' "${MODEL_B_FAILFAST_PATCH}"
grep -Fq 'PASS: Model B failed pool readiness rejects immediately' "${MODEL_B_FAILFAST_TEST}"
grep -Fq 'Model B exhaustive no-candidate benchmark' "${MODEL_B_EXHAUSTIVE_PATCH}"
grep -Fq 'exact persisted Stage-60 candidate corpus' "${MODEL_B_EXHAUSTIVE_PATCH}"
grep -Fq 'at most three warm dvtws2 workers at once' "${MODEL_B_EXHAUSTIVE_PATCH}"
grep -Fq 'projection_is_measured_full_job' "${MODEL_B_EXHAUSTIVE_PY}"
grep -Fq 'unique_worker_identity' "${MODEL_B_EXHAUSTIVE_PY}"
grep -Fq 'observed_ids == expected_ids' "${MODEL_B_EXHAUSTIVE_PY}"
grep -Fq 'PASS: exhaustive Model B benchmark replays a complete graph-exhausted corpus' "${MODEL_B_EXHAUSTIVE_TEST}"
grep -Fq '9>"${LIFECYCLE_LOCK_FILE}"' "${MODEL_B_EXHAUSTIVE_LAUNCHER}"
grep -Fq 'model-b-exhaustive finalize' "${MODEL_B_EXHAUSTIVE_WORKER}"

grep -Fq 'Latest published testing prerelease: `v0.4.0_17` / `os-zapret2-restyle-0.4.0_17.pkg`' "${STATE}"
grep -Fq 'Latest owner-installed testing candidate: `v0.4.0_17` / `os-zapret2-restyle-0.4.0_17.pkg`' "${STATE}"
grep -Fq 'Current package revision: `PLUGIN_REVISION=18`' "${STATE}"
grep -Fq "Current source candidate: \`${candidate}\`" "${STATE}"
grep -Fq 'Model B coexistence gate: **first ACCEPT on `_16`; repeated ACCEPT 5/5 on `_17`; EXPERIMENT ONLY; `production_approved=false`**' "${STATE}"
grep -Fq 'MODEL B EXHAUSTIVE BENCHMARK — `_18` SOURCE CANDIDATE' "${STATE}"
grep -Fq 'fresh Standard `telegram.org` Strategy Lab job on `_18`' "${STATE}"

grep -Fq 'It is not an' "${LIVE_GATE_DECISION}"
grep -Fq 'all-or-nothing release checklist.' "${LIVE_GATE_DECISION}"
if grep -Fq 'Stable release preparation and pkg-repository promotion remain blocked until every' "${MATRIX}"; then
    echo 'FAIL: blanket all-row stable-release gate returned' >&2
    exit 1
fi

sh -n "$0"
echo "PASS: live matrix retains historical release/search evidence, records _17 repeated Model B acceptance, and selects ${candidate} only for the exhaustive no-candidate benchmark"
