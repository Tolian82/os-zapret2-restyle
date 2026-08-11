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
MODEL_B_EXHAUSTIVE_TEST="${ROOT_DIR}/scripts/test-strategy-lab-model-b-exhaustive.sh"
MODEL_B_EXHAUSTIVE_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/model_b_exhaustive.py"
MODEL_B_EXHAUSTIVE_LAUNCHER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_model_b_exhaustive.sh"
MODEL_B_EXHAUSTIVE_WORKER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_model_b_exhaustive_worker.sh"
LIVE_GATE_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md"
VERSION_FILE="${ROOT_DIR}/VERSION"
MAKEFILE="${ROOT_DIR}/Makefile"

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
    "${MODEL_B_EXHAUSTIVE_TEST}" "${MODEL_B_EXHAUSTIVE_PY}" \
    "${MODEL_B_EXHAUSTIVE_LAUNCHER}" "${MODEL_B_EXHAUSTIVE_WORKER}" \
    "${LIVE_GATE_DECISION}" "${VERSION_FILE}" "${MAKEFILE}"
do
    [ -s "${file}" ] || {
        echo "FAIL: missing Strategy Lab live-gate record: ${file}" >&2
        exit 1
    }
done

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(awk -F= '/^PLUGIN_REVISION=/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${MAKEFILE}")
case "${revision}" in
    ''|*[!0-9]*) echo 'FAIL: invalid plugin revision' >&2; exit 1 ;;
esac
candidate="os-zapret2-restyle-${version}_${revision}.pkg"

# The canonical ledger retains all accepted historical gates, records the `_18` owner-live
# exhaustive input-contract reject, and selects `_19` only as its narrow corrective.
grep -Fq 'Overall status: **RELEASE-SELECTED LIVE GATE PASS ON `_27`; ADAPTIVE `_28` FOCUSED PASS; `_32` TIMEOUT-CONTAINMENT LIVE PASS; `_33` ADAPTIVE-VALIDATION CHANGE-SPECIFIC LIVE PASS; MODEL A COLD REFERENCE COLLECTED ON `_11`; MODEL B `_17` REPEATED COEXISTENCE ACCEPT 5/5 (EXPERIMENT ONLY); `_18` EXHAUSTIVE INPUT-CONTRACT REJECT WITH RESTORATION PASS; `_19` MULTI-ENDPOINT EXHAUSTIVE CORRECTIVE SOURCE CANDIDATE; FULL REGRESSION MATRIX OPEN**' "${MATRIX}"
grep -Fq 'Required package ABI: `FreeBSD:15:amd64`' "${MATRIX}"
grep -Fq 'AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md' "${MATRIX}"
grep -Fq 'Latest published testing candidate: `os-zapret2-restyle-0.4.0_18.pkg`' "${MATRIX}"
grep -Fq 'Latest owner-tested candidate: `os-zapret2-restyle-0.4.0_18.pkg`' "${MATRIX}"
grep -Fq "Current source candidate: \`${candidate}\`" "${MATRIX}"
grep -Fq 'Current source purpose: `_19` narrow multi-endpoint corrective for the experiment-only Model B exhaustive `NO_CANDIDATE / graph_exhausted` benchmark; CI/publication pending' "${MATRIX}"
grep -Fq 'Latest owner-tested Model A job: `job.TtZeaH` (`rutracker.org`)' "${MATRIX}"
grep -Fq 'Latest owner-tested Standard winner job: `job.TtZeaH` (`rutracker.org`)' "${MATRIX}"
grep -Fq 'Latest owner-tested Standard no-winner job: `job.tMYnFA` (`telegram.org`, 16/16 `graph_exhausted`, measurement-only 210-second Standard budget override)' "${MATRIX}"
grep -Fq 'Latest owner-tested Extended no-winner job: `job.hsP8Ro` (`telegram.org`)' "${MATRIX}"
grep -Fq 'docs/verification/evidence/2026-08-10-v0.4.0_11-model-a-reference-collected.md' "${MATRIX}"
grep -Fq 'docs/verification/evidence/2026-08-10-v0.4.0_16-model-b-live-accept.md' "${MATRIX}"
grep -Fq 'docs/verification/evidence/2026-08-11-v0.4.0_17-model-b-reproducibility.md' "${MATRIX}"
grep -Fq 'docs/verification/evidence/2026-08-11-v0.4.0_18-model-b-exhaustive-multi-endpoint-gap.md' "${MATRIX}"
grep -Fq 'docs/patches/v0.4.0_19.md' "${MATRIX}"
grep -Fq 'MODEL A COLD REFERENCE — PASS ON `v0.4.0_11`' "${MATRIX}"
grep -Fq '`conclusion=reference_collected`' "${MATRIX}"
grep -Fq 'numeric RSS on all 25 samples' "${MATRIX}"
grep -Fq 'MODEL B `_17` REPEATED OWNER-LIVE COEXISTENCE ACCEPT — EXPERIMENT ONLY' "${MATRIX}"
grep -Fq '`all_workers_ready=true`' "${MATRIX}"
grep -Fq '`unique_worker_identity=true`' "${MATRIX}"
grep -Fq '`rss_observed=true`' "${MATRIX}"
grep -Fq '`restoration_verified=true`' "${MATRIX}"
grep -Fq 'Aggregate warm RSS is 12964 KiB' "${MATRIX}"
grep -Fq 'pool startup is 1162 ms' "${MATRIX}"
grep -Fq '`downstream_actions_skipped=true`' "${MATRIX}"
grep -Fq '`experiment_only=true`' "${MATRIX}"
grep -Fq '`parallel_probes=false`' "${MATRIX}"
grep -Fq '`production_approved=false`' "${MATRIX}"
grep -Fq 'about 144.125 s' "${MATRIX}"
grep -Fq 'about 71.023 s' "${MATRIX}"
grep -Fq 'about 86.5%' "${MATRIX}"
grep -Fq 'roughly 62.0%' "${MATRIX}"
grep -Fq 'required exactly one pinned endpoint' "${MATRIX}"
grep -Fq 'job.tMYnFA' "${MATRIX}"
grep -Fq 'web.telegram.org' "${MATRIX}"

scenario_one=$(awk -F'|' '$2 ~ /^[[:space:]]*1[[:space:]]*$/ && $6 ~ /PASS ON `_27` — v0.4.0 mandatory row/ {n++} END {print n+0}' "${MATRIX}")
[ "${scenario_one}" -eq 1 ] || {
    echo 'FAIL: v0.4.0 mandatory Scenario 1 PASS row mismatch' >&2
    exit 1
}
pending_count=$(awk -F'|' '$2 ~ /^[[:space:]]*([2-9]|1[0-8])[[:space:]]*$/ && $6 ~ /PENDING REGRESSION/ {n++} END {print n+0}' "${MATRIX}")
[ "${pending_count}" -eq 17 ] || {
    echo 'FAIL: rows 2-18 must remain honest pending regression coverage' >&2
    exit 1
}

grep -Fq 'Result: **SCENARIO 1 PASS on `v0.3.3_27`**.' "${RELEASE_EVIDENCE}"
grep -Fq 'Result: **ADAPTIVE-SEARCH `_28` FOCUSED LIVE PASS on `v0.4.0_2`**.' "${ADAPTIVE_EVIDENCE}"
grep -Fq '| Stage 50 | PASS; `total=7`, `completed=7`, `accepted=[]`' "${ADAPTIVE_EVIDENCE}"
grep -Fq '| Stage 60 | PASS; `total_available=14`, `completed=14`' "${ADAPTIVE_EVIDENCE}"
grep -Fq 'no temporary rule from the reserved `19100–19131` range remained' "${ADAPTIVE_EVIDENCE}"

grep -Fq 'Stage-50 adapter duration: about `39.065 s`' "${TIMEOUT_EVIDENCE}"
grep -Fq 'Stage-60 adapter duration was approximately `70.07 s`' "${TIMEOUT_EVIDENCE}"
grep -Fq 'no temporary Strategy Lab rule in `19100-19131` remained' "${TIMEOUT_EVIDENCE}"

grep -Fq 'Standard: `job.RFVs75`' "${LATE_STAGE_EVIDENCE}"
grep -Fq 'Extended: `job.QbUuYO`' "${LATE_STAGE_EVIDENCE}"
grep -Fq '| Standard | PASS | PASS | 90.243 s | 16/16 |' "${LATE_STAGE_EVIDENCE}"
grep -Fq '| Extended | PASS | PASS | 89.249 s | 16/16 |' "${LATE_STAGE_EVIDENCE}"
grep -Fq 'only the normal rule `19000`; no' "${LATE_STAGE_EVIDENCE}"

grep -Fq 'Standard — `job.FgjRCR`' "${TIMEOUT_CLOSEOUT_EVIDENCE}"
grep -Fq 'Extended — `job.pv2Q09`' "${TIMEOUT_CLOSEOUT_EVIDENCE}"
grep -Fq 'Stage 60: 0 working candidates, 16 candidates checked' "${TIMEOUT_CLOSEOUT_EVIDENCE}"
grep -Fq 'Stage 90: PASS' "${TIMEOUT_CLOSEOUT_EVIDENCE}"
grep -Fq 'no late-stage timeout was reported' "${TIMEOUT_CLOSEOUT_EVIDENCE}"

grep -Fq 'Result: **ADAPTIVE-SEARCH `_33` CHANGE-SPECIFIC LIVE PASS on `v0.4.0_9`**' "${ADAPTIVE_VALIDATION_EVIDENCE}"
grep -Fq 'Standard no-winner: `job.tU3wiL`' "${ADAPTIVE_VALIDATION_EVIDENCE}"
grep -Fq 'Extended no-winner: `job.hsP8Ro`' "${ADAPTIVE_VALIDATION_EVIDENCE}"
grep -Fq 'Standard winner-path: `job.UPRDlc`' "${ADAPTIVE_VALIDATION_EVIDENCE}"
grep -Fq 'stopped intentionally with `stopped_reason=enough_candidates` after checking `6` candidates' "${ADAPTIVE_VALIDATION_EVIDENCE}"
grep -Fq 'Each of the three candidates executed exactly three fresh attempts and passed all three.' "${ADAPTIVE_VALIDATION_EVIDENCE}"
grep -Fq '`classification=inconclusive`' "${ADAPTIVE_VALIDATION_EVIDENCE}"
grep -Fq '`temporary_runtime_clean=true`' "${ADAPTIVE_VALIDATION_EVIDENCE}"
grep -Fq 'fail-fast rejection branch remains automated-regression evidence only' "${ADAPTIVE_VALIDATION_EVIDENCE}"

# Model A remains the accepted correctness/performance reference.
grep -Fq 'Candidate: `os-zapret2-restyle-0.4.0_10.pkg`' "${MODEL_A_GAP_EVIDENCE}"
grep -Fq 'Job: `job.Oeq7Rc`' "${MODEL_A_GAP_EVIDENCE}"
grep -Fq 'It collected 25 cold candidate samples.' "${MODEL_A_GAP_EVIDENCE}"
grep -Fq 'RSS observed: false.' "${MODEL_A_GAP_EVIDENCE}"
grep -Fq '| readiness | 1046 ms | 1054 ms | 1178 ms |' "${MODEL_A_GAP_EVIDENCE}"

grep -Fq 'Job: `job.TtZeaH`' "${MODEL_A_REFERENCE_EVIDENCE}"
grep -Fq 'Model A conclusion: `reference_collected`' "${MODEL_A_REFERENCE_EVIDENCE}"
grep -Fq 'numeric `rss_kb`' "${MODEL_A_REFERENCE_EVIDENCE}"
grep -Fq 'median: 4332 KiB' "${MODEL_A_REFERENCE_EVIDENCE}"
grep -Fq 'Model B coexistence' "${MODEL_A_REFERENCE_EVIDENCE}"

grep -Fq 'propagate candidate RSS into Model A evidence' "${MODEL_A_PATCH}"
grep -Fq '`rss_kb=12345`' "${MODEL_A_PATCH}"
grep -Fq 'still does not approve Model B/C' "${MODEL_A_PATCH}"
grep -Fq 'model-a summarize' "${MODEL_A_TEST}"

# Model B historical safety/equivalence checks remain retained.
grep -Fq 'Model B warm-worker coexistence experiment harness' "${MODEL_B_PATCH}"
grep -Fq '9990' "${MODEL_B_PATCH}"
grep -Fq '19128' "${MODEL_B_PATCH}"
grep -Fq '`production_approved=false`' "${MODEL_B_PATCH}"
grep -Fq 'PASS: Model B experiment keeps three warm workers isolated' "${MODEL_B_TEST}"
grep -Fq 'Model B clean-preflight corrective' "${MODEL_B_PREFLIGHT_PATCH}"
grep -Fq 'explicit `return 0`' "${MODEL_B_PREFLIGHT_PATCH}"
grep -Fq 'PASS: Model B preflight returns success when all dedicated rules/ports are free' "${MODEL_B_PREFLIGHT_TEST}"
grep -Fq 'Candidate: `os-zapret2-restyle-0.4.0_13.pkg`' "${MODEL_B_WORKER_EVIDENCE}"
grep -Fq '`all_workers_ready=false`' "${MODEL_B_WORKER_EVIDENCE}"
grep -Fq '`Model B system adapter kill-owned failed`' "${MODEL_B_WORKER_EVIDENCE}"
grep -Fq '`restoration.verified=true`' "${MODEL_B_WORKER_EVIDENCE}"
grep -Fq 'bounded-access design' "${MODEL_B_WORKER_EVIDENCE}"
grep -Fq 'Model B post-drop worker access corrective' "${MODEL_B_ACCESS_PATCH}"
grep -Fq '`0711`' "${MODEL_B_ACCESS_PATCH}"
grep -Fq 'restore the retained Model B root to private `0700`' "${MODEL_B_ACCESS_PATCH}"

grep -Fq 'Candidate: `os-zapret2-restyle-0.4.0_16.pkg`' "${MODEL_B_ACCEPT_EVIDENCE}"
grep -Fq 'This is the first owner-live Model B `accept` result.' "${MODEL_B_ACCEPT_EVIDENCE}"
grep -Fq 'aggregate RSS: `12964 KiB`' "${MODEL_B_ACCEPT_EVIDENCE}"
grep -Fq 'pool startup: `1162 ms`' "${MODEL_B_ACCEPT_EVIDENCE}"
grep -Fq '`conclusion=accept`' "${MODEL_B_ACCEPT_EVIDENCE}"
grep -Fq '`production_approved=false`' "${MODEL_B_ACCEPT_EVIDENCE}"

grep -Fq 'Model B failed-readiness fail-fast' "${MODEL_B_FAILFAST_PATCH}"
grep -Fq '`downstream_actions_skipped=true`' "${MODEL_B_FAILFAST_PATCH}"
grep -Fq 'no route-add, probe, independent-stop, survivor check, controlled-death or `kill-owned` action is attempted' "${MODEL_B_FAILFAST_PATCH}"
grep -Fq 'PASS: Model B failed pool readiness rejects immediately, skips probes/stop/death, and still requests bounded cleanup' "${MODEL_B_FAILFAST_TEST}"

# `_17` reproducibility, `_18` live gap, and `_19` corrective extend rather than replace the
# accepted Model B contract.
grep -Fq 'acceptance: `5/5`' "${MODEL_B_REPRO_EVIDENCE}"
grep -Fq 'mean pool startup: `1163.6 ms`' "${MODEL_B_REPRO_EVIDENCE}"
grep -Fq '`86.5%` reduction' "${MODEL_B_REPRO_EVIDENCE}"
grep -Fq '`62.0%` reduction' "${MODEL_B_REPRO_EVIDENCE}"
grep -Fq 'Model B exhaustive no-candidate benchmark' "${MODEL_B_EXHAUSTIVE_PATCH}"
grep -Fq 'at most three warm dvtws2 workers at once' "${MODEL_B_EXHAUSTIVE_PATCH}"
grep -Fq 'job.tMYnFA' "${MODEL_B_EXHAUSTIVE_GAP_EVIDENCE}"
grep -Fq '`completed=16`' "${MODEL_B_EXHAUSTIVE_GAP_EVIDENCE}"
grep -Fq '`stopped_reason=graph_exhausted`' "${MODEL_B_EXHAUSTIVE_GAP_EVIDENCE}"
grep -Fq '`error="exhaustive Model B requires one pinned endpoint"`' "${MODEL_B_EXHAUSTIVE_GAP_EVIDENCE}"
grep -Fq '`restoration.verified=true`' "${MODEL_B_EXHAUSTIVE_GAP_EVIDENCE}"
grep -Fq 'Model B exhaustive multi-endpoint reference corrective' "${MODEL_B_MULTI_ENDPOINT_PATCH}"
grep -Fq 'all pinned reference endpoint names' "${MODEL_B_MULTI_ENDPOINT_PATCH}"
grep -Fq 'all_reference_endpoints_replayed=true' "${MODEL_B_MULTI_ENDPOINT_PATCH}"
grep -Fq 'projection_is_measured_full_job' "${MODEL_B_EXHAUSTIVE_PY}"
grep -Fq 'unique_worker_identity' "${MODEL_B_EXHAUSTIVE_PY}"
grep -Fq 'observed_ids == expected_ids' "${MODEL_B_EXHAUSTIVE_PY}"
grep -Fq 'reference_endpoint_bindings' "${MODEL_B_EXHAUSTIVE_PY}"
grep -Fq 'all_reference_endpoints_replayed' "${MODEL_B_EXHAUSTIVE_PY}"
grep -Fq 'endpoint_probes' "${MODEL_B_EXHAUSTIVE_PY}"
grep -Fq 'PASS: exhaustive Model B benchmark replays a complete graph-exhausted multi-endpoint corpus' "${MODEL_B_EXHAUSTIVE_TEST}"
grep -Fq '9>"${LIFECYCLE_LOCK_FILE}"' "${MODEL_B_EXHAUSTIVE_LAUNCHER}"
grep -Fq 'model-b-exhaustive finalize' "${MODEL_B_EXHAUSTIVE_WORKER}"

grep -Fq 'Model B experiment gate: **first owner-live coexistence ACCEPT on `v0.4.0_16`; repeated ACCEPT 5/5 on `v0.4.0_17`; `_18` exhaustive input-contract REJECT before warm batches; EXPERIMENT ONLY; `production_approved=false`**' "${STATE}"
grep -Fq 'Current phase: **`_18` exhaustive owner-live input-contract REJECT on multi-endpoint `telegram.org` with restoration PASS; `_19` narrow multi-endpoint exhaustive corrective in source, CI/publication pending**' "${STATE}"
grep -Fq 'Latest published testing prerelease: `v0.4.0_18` / `os-zapret2-restyle-0.4.0_18.pkg`' "${STATE}"
grep -Fq 'Latest owner-tested testing candidate: `v0.4.0_18` / `os-zapret2-restyle-0.4.0_18.pkg`' "${STATE}"
grep -Fq "Current source candidate: \`${candidate}\`" "${STATE}"
grep -Fq 'MODEL B EXHAUSTIVE NO-CANDIDATE BENCHMARK — `_18` / `_19`' "${STATE}"

grep -Fq 'It is not an' "${LIVE_GATE_DECISION}"
grep -Fq 'all-or-nothing release checklist.' "${LIVE_GATE_DECISION}"
if grep -Fq 'Stable release preparation and pkg-repository promotion remain blocked until every' "${MATRIX}"; then
    echo 'FAIL: blanket all-row stable-release gate returned' >&2
    exit 1
fi

[ "${version}" = '0.4.0' ] || {
    echo "FAIL: unexpected active Strategy Lab source version ${version}" >&2
    exit 1
}
[ "${revision}" -eq 19 ] || {
    echo 'FAIL: exhaustive multi-endpoint corrective revision must be exactly 19' >&2
    exit 1
}

echo "PASS: historical Strategy Lab live/Model A/Model B safety evidence remains retained, _18 exhaustive input-contract gap is recorded, ${candidate} is the multi-endpoint corrective, and rows 2-18 remain regression backlog"
