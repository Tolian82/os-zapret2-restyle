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

# The canonical ledger retains the accepted `_16` owner-live baseline while `_17` is now
# the qualified and published testing candidate awaiting owner installation.
grep -Fq 'Overall status: **RELEASE-SELECTED LIVE GATE PASS ON `_27`; ADAPTIVE `_28` FOCUSED PASS; `_32` TIMEOUT-CONTAINMENT LIVE PASS; `_33` ADAPTIVE-VALIDATION CHANGE-SPECIFIC LIVE PASS; MODEL A COLD REFERENCE COLLECTED ON `_11`; MODEL B `_16` OWNER-LIVE COEXISTENCE ACCEPT (EXPERIMENT ONLY); `_17` FAILED-READINESS FAIL-FAST PUBLISHED; FULL REGRESSION MATRIX OPEN**' "${MATRIX}"
grep -Fq 'Required package ABI: `FreeBSD:15:amd64`' "${MATRIX}"
grep -Fq 'AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md' "${MATRIX}"
grep -Fq 'Latest published testing candidate: `os-zapret2-restyle-0.4.0_17.pkg`' "${MATRIX}"
grep -Fq 'Latest owner-tested candidate: `os-zapret2-restyle-0.4.0_16.pkg`' "${MATRIX}"
grep -Fq "Current source candidate: \`${candidate}\`" "${MATRIX}"
grep -Fq 'Current source purpose: `_17` failed-readiness fail-fast corrective; published testing prerelease, owner installation pending' "${MATRIX}"
grep -Fq 'Latest owner-tested Model A job: `job.TtZeaH` (`rutracker.org`)' "${MATRIX}"
grep -Fq 'Latest owner-tested Standard winner job: `job.TtZeaH` (`rutracker.org`)' "${MATRIX}"
grep -Fq 'Latest owner-tested Standard no-winner job: `job.tU3wiL` (`telegram.org`)' "${MATRIX}"
grep -Fq 'Latest owner-tested Extended no-winner job: `job.hsP8Ro` (`telegram.org`)' "${MATRIX}"
grep -Fq 'docs/verification/evidence/2026-08-10-v0.4.0_11-model-a-reference-collected.md' "${MATRIX}"
grep -Fq 'docs/verification/evidence/2026-08-10-v0.4.0_16-model-b-live-accept.md' "${MATRIX}"
grep -Fq 'docs/patches/v0.4.0_17.md' "${MATRIX}"
grep -Fq 'MODEL A COLD REFERENCE — PASS ON `v0.4.0_11`' "${MATRIX}"
grep -Fq '`conclusion=reference_collected`' "${MATRIX}"
grep -Fq 'numeric RSS on all 25 samples' "${MATRIX}"
grep -Fq 'MODEL B `_16` OWNER-LIVE COEXISTENCE ACCEPT — EXPERIMENT ONLY' "${MATRIX}"
grep -Fq '`all_workers_ready=true`' "${MATRIX}"
grep -Fq '`unique_worker_identity=true`' "${MATRIX}"
grep -Fq '`rss_observed=true`' "${MATRIX}"
grep -Fq '`restoration_verified=true`' "${MATRIX}"
grep -Fq 'Aggregate warm RSS is 12964 KiB' "${MATRIX}"
grep -Fq 'pool startup is 1162 ms' "${MATRIX}"
grep -Fq '`downstream_actions_skipped=true`' "${MATRIX}"
grep -Fq '`experiment_only=true`, `parallel_probes=false` and `production_approved=false`' "${MATRIX}"

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

# Model B remains experimental. Historical reject/corrective evidence and the accepted
# `_16` live baseline are retained while `_17` is the qualified published corrective.
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

grep -Fq 'Model B experiment gate: **`v0.4.0_16` OWNER-LIVE COEXISTENCE ACCEPT; EXPERIMENT ONLY; `production_approved=false`**' "${STATE}"
grep -Fq 'Current phase: **Model B `_16` owner-live coexistence ACCEPT; `_17` failed-readiness fail-fast corrective qualified and published as testing prerelease; owner installation pending**' "${STATE}"
grep -Fq 'Latest published testing prerelease: `v0.4.0_17` / `os-zapret2-restyle-0.4.0_17.pkg`' "${STATE}"
grep -Fq 'Latest owner-tested testing candidate: `v0.4.0_16` / `os-zapret2-restyle-0.4.0_16.pkg`' "${STATE}"
grep -Fq "Current source candidate: \`${candidate}\`" "${STATE}"

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
[ "${revision}" -ge 17 ] || {
    echo 'FAIL: Model B failed-readiness source corrective revision must be at least 17' >&2
    exit 1
}

echo "PASS: _27/_28/_32/_33 and Model A/_16 live evidence remain retained, _17 is published, _16 remains owner-tested, ${candidate} is the failed-readiness corrective, and rows 2-18 remain regression backlog"
