#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MATRIX="${ROOT_DIR}/docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md"
STATE="${ROOT_DIR}/docs/PROJECT_STATE.md"
INDEX="${ROOT_DIR}/docs/INDEX.md"
RELEASE_DOC="${ROOT_DIR}/docs/releases/v0.4.1.md"
RELEASE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.1-release-publication.md"
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

for file in "${MATRIX}" "${STATE}" "${INDEX}" "${RELEASE_DOC}" "${RELEASE_EVIDENCE}" \
    "${VERSION_FILE}" "${MAKEFILE}" "${MODEL_B_EVIDENCE}" "${MODEL_C_LIVE}" \
    "${MODEL_C_CORRECTIVE_PASS}" "${PUBLICATION26}" "${LIVE26}" "${PATCH25}" "${PATCH26}" \
    "${BUDGET_DOC}" "${BUDGET_TEST}" "${BUDGET_PY}" "${COMPAT_PY}" "${LEASE_TEST}" \
    "${LEASE_PY}" "${MODEL_C_PY}" "${MODEL_B_PY}" "${LIVE_GATE_DECISION}"
do
    [ -s "${file}" ] || fail "missing Strategy Lab/release record: ${file}"
done

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(awk -F= '/^PLUGIN_REVISION=/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${MAKEFILE}")
case "${revision}" in ''|*[!0-9]*) fail 'invalid plugin revision' ;; esac
candidate="os-zapret2-restyle-${version}_${revision}.pkg"
[ "${version}" = '0.4.1' ] || fail "published release must use VERSION=0.4.1"
[ "${revision}" -eq 1 ] || fail 'published v0.4.1 must retain PLUGIN_REVISION=1'
[ "${candidate}" = 'os-zapret2-restyle-0.4.1_1.pkg' ] || fail 'unexpected v0.4.1 package identity'

# Engineering Memory must describe the completed release while retaining the unchanged
# `_26` owner-live runtime basis truthfully.
require "${STATE}" 'Current source line: `VERSION=0.4.1`, `PLUGIN_REVISION=1`'
require "${STATE}" 'Current published release tag: `v0.4.1`'
require "${STATE}" 'Current published package: `os-zapret2-restyle-0.4.1_1.pkg`'
require "${STATE}" 'Latest owner-tested runtime basis: `v0.4.0_26` — adaptive-budget owner-live PASS'
require "${STATE}" 'c53e1c1656517fa764f97a175bb82eea02dbc374'
require "${STATE}" '31596979559'
require "${STATE}" '180305'
require "${STATE}" 'sha256:cb481b37ed5ef6b57360ecbe7f1678b75d2d8e6520beb92e3d624b1bc9eb837e'
require "${STATE}" '5869308071'
require "${STATE}" '2026-08-12-v0.4.1-release-publication.md'
require "${STATE}" 'job.xhdgCU'
require "${STATE}" 'Stage 60 duration `34209 ms`'
require "${STATE}" 'total job duration `114644 ms`'

require "${INDEX}" 'docs/releases/v0.4.1.md'
require "${INDEX}" '2026-08-12-v0.4.1-release-publication.md'
require "${INDEX}" 'Current v0.4.1 boundary'
require "${INDEX}" 'C-warm-bucket-source-port-dispatch -> B-warm-worker-parallel-batched -> A-cold-fallback'

require "${RELEASE_DOC}" '# os-zapret2-restyle v0.4.1'
require "${RELEASE_DOC}" '`os-zapret2-restyle-0.4.1_1.pkg`'
require "${RELEASE_DOC}" '`v0.4.1_1: Prepare release v0.4.1`'
require "${RELEASE_DOC}" 'immutable stable release tag remains the semantic tag `v0.4.1`'
require "${RELEASE_DOC}" 'job.xhdgCU'

# Durable publication evidence binds exact merge, tag, workflows, assets and Pages.
require "${RELEASE_EVIDENCE}" 'Status: **PUBLISHED**'
require "${RELEASE_EVIDENCE}" 'c53e1c1656517fa764f97a175bb82eea02dbc374'
require "${RELEASE_EVIDENCE}" '8c860a01def48a3b84943a43ba0c5a30d9f37055'
require "${RELEASE_EVIDENCE}" '31596967737'
require "${RELEASE_EVIDENCE}" '31596979559'
require "${RELEASE_EVIDENCE}" '369226460'
require "${RELEASE_EVIDENCE}" '511554024'
require "${RELEASE_EVIDENCE}" '511554025'
require "${RELEASE_EVIDENCE}" '180305'
require "${RELEASE_EVIDENCE}" 'sha256:cb481b37ed5ef6b57360ecbe7f1678b75d2d8e6520beb92e3d624b1bc9eb837e'
require "${RELEASE_EVIDENCE}" '5869308071'
require "${RELEASE_EVIDENCE}" 'Final deployment state: SUCCESS'

# Canonical live matrix must distinguish published package identity from the actual
# appliance-tested `_26` runtime basis.
require "${MATRIX}" 'Current published release package: `os-zapret2-restyle-0.4.1_1.pkg`'
require "${MATRIX}" 'Current published release tag: `v0.4.1`'
require "${MATRIX}" 'Latest owner-tested runtime package: `os-zapret2-restyle-0.4.0_26.pkg`'
require "${MATRIX}" '`v0.4.1` RELEASE-SELECTED LIVE BASIS — PASS ON `_26`'
require "${MATRIX}" 'policy=eligible-work-v1'
require "${MATRIX}" 'phase=budget_adaptation'
require "${MATRIX}" 'job.xhdgCU'
require "${MATRIX}" 'Stage 60 duration `34209 ms`'
require "${MATRIX}" 'total job `114644 ms`'
require "${MATRIX}" '.parallel.fallbacks=[]'
require "${MATRIX}" 'policy=preferred-free-else-alternate'
require "${MATRIX}" 'foreign_port_action=skip-only'
require "${MATRIX}" 'job.5yGde5'
require "${MATRIX}" 'job.FaLtIk'
require "${MATRIX}" 'physical_worker_count=1'
require "${MATRIX}" 'job.KpLHgb'
require "${MATRIX}" 'job.GK0X66'

scenario_one=$(awk -F'|' '$2 ~ /^[[:space:]]*1[[:space:]]*$/ && $6 ~ /PASS ON `_27` — v0.4.0 historical mandatory row/ {n++} END {print n+0}' "${MATRIX}")
[ "${scenario_one}" -eq 1 ] || fail 'historical v0.4.0 Scenario 1 PASS row mismatch'
scenario_seven=$(awk -F'|' '$2 ~ /^[[:space:]]*7[[:space:]]*$/ && $6 ~ /PASS ON `_26` — v0.4.1 selected live basis/ {n++} END {print n+0}' "${MATRIX}")
[ "${scenario_seven}" -eq 1 ] || fail 'Scenario 7 must retain _26 as v0.4.1 selected live basis'
pending_count=$(awk -F'|' '$2 ~ /^[[:space:]]*([2-6]|[8-9]|1[0-8])[[:space:]]*$/ && $6 ~ /PENDING REGRESSION/ {n++} END {print n+0}' "${MATRIX}")
[ "${pending_count}" -eq 16 ] || fail 'rows 2-6 and 8-18 must remain honest pending regression coverage'

# Accepted runtime evidence remains immutable input to the published version-only promotion.
require "${PUBLICATION26}" '8ada9cba28916fff506f19b34f5ef3de16e2008e'
require "${PUBLICATION26}" 'sha256:f5466c21c014bf594afcc80aac49b948db45513b33fe46d4857eded75bc8af8c'
require "${LIVE26}" 'Status: **PASS**'
require "${LIVE26}" 'job.xhdgCU'
require "${LIVE26}" 'policy=eligible-work-v1'
require "${LIVE26}" 'C-warm-bucket-source-port-dispatch'
require "${LIVE26}" '.parallel.fallbacks=[]'
require "${LIVE26}" '34209 ms'
require "${LIVE26}" '114644 ms'
require "${MODEL_C_CORRECTIVE_PASS}" 'job.5yGde5'
require "${MODEL_C_LIVE}" 'job.FaLtIk'
require "${MODEL_B_EVIDENCE}" 'PRODUCTION STAGE-60 MODEL B OWNER-LIVE PASS'

require "${PATCH26}" 'policy=eligible-work-v1'
require "${BUDGET_DOC}" 'bounded child operation <= stage parent <= finite job parent'
require "${BUDGET_TEST}" 'PASS: Strategy Lab derives finite parent budgets from measured endpoint/capability/protocol work'
require "${BUDGET_PY}" 'POLICY = "eligible-work-v1"'
require "${COMPAT_PY}" 'return adaptive_budget.orchestrator_main(args)'
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
echo "PASS: published ${candidate} keeps exact release evidence and truthful _26 owner-live runtime basis"
