#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MATRIX="${ROOT_DIR}/docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md"
STATE="${ROOT_DIR}/docs/PROJECT_STATE.md"
INDEX="${ROOT_DIR}/docs/INDEX.md"
VERSION_FILE="${ROOT_DIR}/VERSION"
MAKEFILE="${ROOT_DIR}/Makefile"
MODEL_B_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md"
MODEL_C_LIVE="${ROOT_DIR}/docs/verification/evidence/2026-08-11-v0.4.0_23-model-c-live-hold.md"
MODEL_C_CORRECTIVE_PASS="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.0_25-source-port-live-pass.md"
PUBLICATION26="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.0_26-publication.md"
LIVE26="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.0_26-adaptive-budget-live-pass.md"
PATCH25="${ROOT_DIR}/docs/patches/v0.4.0_25.md"
PATCH26="${ROOT_DIR}/docs/patches/v0.4.0_26.md"
BUDGET_DOC="${ROOT_DIR}/docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md"
BUDGET_TEST="${ROOT_DIR}/scripts/test-strategy-lab-adaptive-budget.sh"
BUDGET_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/adaptive_budget.py"
COMPAT_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/compat.py"
LEASE_TEST="${ROOT_DIR}/scripts/test-strategy-lab-stage60-source-port-lease.sh"
LEASE_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_source_port_lease.py"
MODEL_C_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_model_c.py"
MODEL_B_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_parallel.py"
LIVE_GATE_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md"

fail(){ echo "FAIL: $*" >&2; exit 1; }
require(){ grep -Fq "$2" "$1" || fail "missing contract text in $1: $2"; }

for file in "${MATRIX}" "${STATE}" "${INDEX}" "${VERSION_FILE}" "${MAKEFILE}" \
    "${MODEL_B_EVIDENCE}" "${MODEL_C_LIVE}" "${MODEL_C_CORRECTIVE_PASS}" "${PUBLICATION26}" \
    "${LIVE26}" "${PATCH25}" "${PATCH26}" "${BUDGET_DOC}" "${BUDGET_TEST}" "${BUDGET_PY}" \
    "${COMPAT_PY}" "${LEASE_TEST}" "${LEASE_PY}" "${MODEL_C_PY}" "${MODEL_B_PY}" \
    "${LIVE_GATE_DECISION}"
do
    [ -s "${file}" ] || fail "missing Strategy Lab live-gate record: ${file}"
done

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(awk -F= '/^PLUGIN_REVISION=/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${MAKEFILE}")
case "${revision}" in ''|*[!0-9]*) fail 'invalid plugin revision' ;; esac
candidate="os-zapret2-restyle-${version}_${revision}.pkg"
[ "${version}" = '0.4.0' ] || fail "unexpected active Strategy Lab version ${version}"
[ "${revision}" -eq 26 ] || fail 'adaptive-budget revision must be exactly 26'

# Engineering Memory must now identify published `_26` as the latest owner-tested candidate.
require "${STATE}" 'Current source line: `VERSION=0.4.0`, `PLUGIN_REVISION=26`'
require "${STATE}" 'Current source candidate: `os-zapret2-restyle-0.4.0_26.pkg`'
require "${STATE}" 'Latest published testing prerelease: `v0.4.0_26`'
require "${STATE}" 'Latest owner-tested testing candidate: `v0.4.0_26` — adaptive-budget owner-live PASS'
require "${STATE}" '8ada9cba28916fff506f19b34f5ef3de16e2008e'
require "${STATE}" 'sha256:f5466c21c014bf594afcc80aac49b948db45513b33fe46d4857eded75bc8af8c'
require "${STATE}" '2026-08-12-v0.4.0_26-publication.md'
require "${STATE}" '2026-08-12-v0.4.0_26-adaptive-budget-live-pass.md'
require "${STATE}" '`eligible-work-v1`'
require "${STATE}" 'adaptive-budget.json'
require "${STATE}" 'budget_adaptation'
require "${STATE}" 'number of endpoints × IPv4/IPv6 × TLS/QUIC × Generic UDP × Standard/Extended mode'
require "${STATE}" 'job.xhdgCU'
require "${STATE}" 'Stage 60 duration `34209 ms`'
require "${STATE}" 'total job duration `114644 ms`'

require "${INDEX}" 'For a current diagnosis, **do not start from an old evidence file**.'
require "${INDEX}" 'docs/patches/v0.4.0_26.md'
require "${INDEX}" 'STRATEGY_LAB_ADAPTIVE_BUDGET.md'
require "${INDEX}" '2026-08-12-v0.4.0_26-publication.md'
require "${INDEX}" '2026-08-12-v0.4.0_26-adaptive-budget-live-pass.md'
require "${INDEX}" '2026-08-12-v0.4.0_25-source-port-live-pass.md'

require "${MATRIX}" 'Current source candidate: `os-zapret2-restyle-0.4.0_26.pkg`'
require "${MATRIX}" 'Current published package: `os-zapret2-restyle-0.4.0_26.pkg`'
require "${MATRIX}" 'Latest owner-tested package: `os-zapret2-restyle-0.4.0_26.pkg`'
require "${MATRIX}" '`_26` ADAPTIVE-BUDGET OWNER-LIVE GATE — PASS'
require "${MATRIX}" 'SOURCE/CI/PUBLICATION/OWNER-LIVE PASS'
require "${MATRIX}" '2026-08-12-v0.4.0_26-publication.md'
require "${MATRIX}" '2026-08-12-v0.4.0_26-adaptive-budget-live-pass.md'
require "${MATRIX}" 'policy=eligible-work-v1'
require "${MATRIX}" 'phase=budget_adaptation'
require "${MATRIX}" 'job.xhdgCU'
require "${MATRIX}" 'Stage 60 duration `34209 ms`'
require "${MATRIX}" 'total job `114644 ms`'
require "${MATRIX}" '`150 s`'
require "${MATRIX}" '`120 s`'
require "${MATRIX}" '`270 s`'
require "${MATRIX}" 'job.5yGde5'
require "${MATRIX}" '.parallel.fallbacks=[]'
require "${MATRIX}" 'policy=preferred-free-else-alternate'
require "${MATRIX}" 'foreign_port_action=skip-only'
require "${MATRIX}" 'job.FaLtIk'
require "${MATRIX}" 'job.G0wC5l'
require "${MATRIX}" 'physical_worker_count=1'
require "${MATRIX}" 'controlled source port is already in use: 42004'
require "${MATRIX}" 'Adaptive `_28` focused evidence:'
require "${MATRIX}" 'mean 74.8082 s'
require "${MATRIX}" 'about 15.96%'

scenario_one=$(awk -F'|' '$2 ~ /^[[:space:]]*1[[:space:]]*$/ && $6 ~ /PASS ON `_27` — v0.4.0 mandatory row/ {n++} END {print n+0}' "${MATRIX}")
[ "${scenario_one}" -eq 1 ] || fail 'v0.4.0 mandatory Scenario 1 PASS row mismatch'
scenario_seven=$(awk -F'|' '$2 ~ /^[[:space:]]*7[[:space:]]*$/ && $6 ~ /PASS ON `_26`/ {n++} END {print n+0}' "${MATRIX}")
[ "${scenario_seven}" -eq 1 ] || fail 'Scenario 7 must record _26 adaptive-budget owner-live PASS'
pending_count=$(awk -F'|' '$2 ~ /^[[:space:]]*([2-6]|[8-9]|1[0-8])[[:space:]]*$/ && $6 ~ /PENDING REGRESSION/ {n++} END {print n+0}' "${MATRIX}")
[ "${pending_count}" -eq 16 ] || fail 'rows 2-6 and 8-18 must remain honest pending regression coverage'

# Publication evidence remains the immutable snapshot captured before owner-live acceptance.
require "${PUBLICATION26}" 'Status: **PUBLISHED; OWNER-LIVE VERIFICATION PENDING**'
require "${PUBLICATION26}" '8ada9cba28916fff506f19b34f5ef3de16e2008e'
require "${PUBLICATION26}" '31583257998'
require "${PUBLICATION26}" '31584348303'
require "${PUBLICATION26}" '9136236447'
require "${PUBLICATION26}" '369135019'
require "${PUBLICATION26}" '511384034'
require "${PUBLICATION26}" '180306'
require "${PUBLICATION26}" 'sha256:f5466c21c014bf594afcc80aac49b948db45513b33fe46d4857eded75bc8af8c'

# `_26` live evidence is the current acceptance authority.
require "${LIVE26}" 'Status: **PASS**'
require "${LIVE26}" 'job.xhdgCU'
require "${LIVE26}" 'policy=eligible-work-v1'
require "${LIVE26}" 'Standard `150 s`'
require "${LIVE26}" 'Extended increment `120 s`'
require "${LIVE26}" 'search/job parent `270 s`'
require "${LIVE26}" 'Stage 80 `120 s`'
require "${LIVE26}" 'C-warm-bucket-source-port-dispatch'
require "${LIVE26}" '.parallel.fallbacks=[]'
require "${LIVE26}" '34209 ms'
require "${LIVE26}" '114644 ms'
require "${LIVE26}" 'pid `78016`'

# Historical evidence remains immutable input rather than being copied into current prose.
require "${MODEL_C_LIVE}" 'job.FaLtIk'
require "${MODEL_C_LIVE}" 'job.G0wC5l'
require "${MODEL_C_LIVE}" 'controlled source port is already in use: 42004'
require "${MODEL_C_CORRECTIVE_PASS}" 'Status: **PASS**'
require "${MODEL_C_CORRECTIVE_PASS}" 'job.5yGde5'
require "${MODEL_C_CORRECTIVE_PASS}" '.parallel.fallbacks=[]'
require "${MODEL_C_CORRECTIVE_PASS}" '34198 ms'
require "${MODEL_C_CORRECTIVE_PASS}" '114759 ms'
require "${MODEL_B_EVIDENCE}" 'PRODUCTION STAGE-60 MODEL B OWNER-LIVE PASS'

# `_26` source contract: measured workload extends finite parents without altering search.
require "${PATCH26}" 'This packaged patch changes **Strategy Lab parent-budget calculation only**.'
require "${PATCH26}" 'SOURCE/CI/PUBLICATION/OWNER-LIVE PASS'
require "${PATCH26}" 'policy=eligible-work-v1'
require "${PATCH26}" 'adaptive-budget.json'
require "${PATCH26}" 'job.xhdgCU'
require "${BUDGET_DOC}" 'bounded child operation <= stage parent <= finite job parent'
require "${BUDGET_DOC}" 'Stage-30 PASS'
require "${BUDGET_TEST}" 'PASS: Strategy Lab derives finite parent budgets from measured endpoint/capability/protocol work'
require "${BUDGET_PY}" 'POLICY = "eligible-work-v1"'
require "${BUDGET_PY}" 'return AdaptiveBudgetOrchestrator(job_id).run()'
require "${COMPAT_PY}" 'return adaptive_budget.orchestrator_main(args)'

# `_25` source-port ownership and the preferred/fallback architecture stay intact.
require "${PATCH25}" 'fresh lease'
require "${LEASE_TEST}" 'PASS: Stage 60 keeps free preferred ports'
require "${LEASE_PY}" 'original_model_c_batch'
require "${LEASE_PY}" 'original_model_b_batch'
require "${MODEL_C_PY}" 'MODEL = "C-warm-bucket-source-port-dispatch"'
require "${MODEL_B_PY}" 'MODEL = "B-warm-worker-parallel-batched"'

require "${LIVE_GATE_DECISION}" 'all-or-nothing release checklist.'
if grep -Fq 'Stable release preparation and pkg-repository promotion remain blocked until every' "${MATRIX}"; then
    fail 'blanket all-row stable-release gate returned'
fi

sh -n "$0"
echo "PASS: live matrix records published ${candidate} as adaptive-budget owner-live PASS while retaining _25 and _22 historical baselines"
