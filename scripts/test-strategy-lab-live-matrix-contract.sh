#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MATRIX="${ROOT_DIR}/docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md"
STATE="${ROOT_DIR}/docs/PROJECT_STATE.md"
INDEX="${ROOT_DIR}/docs/INDEX.md"
START_HERE="${ROOT_DIR}/docs/START_HERE.md"
PRINCIPLES="${ROOT_DIR}/docs/PROJECT_PRINCIPLES.md"
DOC_RULES="${ROOT_DIR}/docs/DOCUMENTATION_RULES.md"
CHAT_RULES="${ROOT_DIR}/docs/CHAT_RULES.md"
GH_RULES="${ROOT_DIR}/docs/GITHUB_PUBLICATION.md"
ROADMAP="${ROOT_DIR}/docs/ROADMAP.md"
CURRENT_LEDGER="${ROOT_DIR}/docs/history/current/v0.4.x.md"
RELEASE_DOC="${ROOT_DIR}/docs/releases/v0.4.1.md"
RELEASE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.1-release-publication.md"
BLOB_PUBLICATION="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.1_3-blob-measurement-publication.md"
BLOB_LIVE="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.1_3-blob-startup-rss-live-pass.md"
BLOB4_PUBLICATION="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.1_4-blob-common-set-publication.md"
BLOB4_LIVE="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.1_4-blob-common-set-live-pass.md"
DISCOVERY_PUBLICATION="${ROOT_DIR}/docs/verification/evidence/2026-08-13-v0.4.1_5-discovery-probe-publication.md"
DISCOVERY_ROOT_CAUSE="${ROOT_DIR}/docs/verification/evidence/2026-08-13-v0.4.1_5-cleanup-finalizer-root-cause.md"
DISCOVERY6_INPUT="${ROOT_DIR}/docs/verification/evidence/2026-08-13-v0.4.1_6-discovery-corrective-input.md"
DISCOVERY6_PLAN="${ROOT_DIR}/docs/verification/evidence/2026-08-13-v0.4.1_6-source-verification-plan.md"
DISCOVERY6_LIVE="${ROOT_DIR}/docs/verification/evidence/2026-08-13-v0.4.1_6-discovery-corrective-live-pass.md"
READINESS12_LIVE="${ROOT_DIR}/docs/verification/evidence/2026-08-14-v0.4.1_12-warm-readiness-live-pass.md"
VERSION_FILE="${ROOT_DIR}/VERSION"
MAKEFILE="${ROOT_DIR}/Makefile"
LUA_DOC="${ROOT_DIR}/docs/architecture/STRATEGY_LAB_LUA_INITIALIZATION.md"
LUA_PATCH="${ROOT_DIR}/docs/patches/v0.4.1_2.md"
LUA_TEST="${ROOT_DIR}/scripts/test-strategy-lab-lua-initialization-measurement.sh"
LUA_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/lua_initialization_measurement.py"
BLOB_DOC="${ROOT_DIR}/docs/architecture/STRATEGY_LAB_BLOB_LOADING.md"
BLOB_PATCH="${ROOT_DIR}/docs/patches/v0.4.1_4.md"
BLOB_TEST="${ROOT_DIR}/scripts/test-strategy-lab-blob-startup-measurement.sh"
BLOB_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/blob_startup_measurement.py"
DISCOVERY5_PATCH="${ROOT_DIR}/docs/patches/v0.4.1_5.md"
DISCOVERY6_PATCH="${ROOT_DIR}/docs/patches/v0.4.1_6.md"
DISCOVERY_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/discovery_probe_measurement.py"
LIFECYCLE7_PATCH="${ROOT_DIR}/docs/patches/v0.4.1_7.md"
LIFECYCLE7_TEST="${ROOT_DIR}/scripts/test-strategy-lab-model-c-lifecycle-measurement.sh"
LIFECYCLE7_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/model_c_lifecycle_measurement.py"
LIFECYCLE7_WRAPPER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_model_c_lifecycle_measurement.sh"
LIFECYCLE7_WORKER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_model_c_lifecycle_measurement_worker.sh"
MODEL_B_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md"
MODEL_C_CORRECTIVE_PASS="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.0_25-source-port-live-pass.md"
PUBLICATION26="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.0_26-publication.md"
LIVE26="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.0_26-adaptive-budget-live-pass.md"
LUA_LIVE="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.1_2-lua-init-live-pass.md"
BUDGET_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/adaptive_budget.py"
LEASE_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_source_port_lease.py"
MODEL_C_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_model_c.py"
MODEL_C_OWNER_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_model_c_production.py"
MODEL_B_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_parallel.py"
LIVE_GATE_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md"
QUIC_DOC="${ROOT_DIR}/docs/architecture/STRATEGY_LAB_QUIC_CONTROL.md"
UDP_DOC="${ROOT_DIR}/docs/architecture/STRATEGY_LAB_UDP_INPUT.md"
PATCH14="${ROOT_DIR}/docs/patches/v0.4.1_14.md"

fail(){ echo "FAIL: $*" >&2; exit 1; }
require(){ grep -Fq "$2" "$1" || fail "missing contract text in $1: $2"; }

for file in "${MATRIX}" "${STATE}" "${INDEX}" "${START_HERE}" "${PRINCIPLES}" "${DOC_RULES}" \
    "${CHAT_RULES}" "${GH_RULES}" "${ROADMAP}" "${CURRENT_LEDGER}" "${RELEASE_DOC}" \
    "${RELEASE_EVIDENCE}" "${BLOB_PUBLICATION}" "${BLOB_LIVE}" "${BLOB4_PUBLICATION}" \
    "${BLOB4_LIVE}" "${DISCOVERY_PUBLICATION}" "${DISCOVERY_ROOT_CAUSE}" "${DISCOVERY6_INPUT}" \
    "${DISCOVERY6_PLAN}" "${DISCOVERY6_LIVE}" "${READINESS12_LIVE}" "${VERSION_FILE}" "${MAKEFILE}" \
    "${LUA_DOC}" "${LUA_PATCH}" "${LUA_TEST}" "${LUA_PY}" "${BLOB_DOC}" "${BLOB_PATCH}" \
    "${BLOB_TEST}" "${BLOB_PY}" "${DISCOVERY5_PATCH}" "${DISCOVERY6_PATCH}" "${DISCOVERY_PY}" \
    "${LIFECYCLE7_PATCH}" "${LIFECYCLE7_TEST}" "${LIFECYCLE7_PY}" "${LIFECYCLE7_WRAPPER}" \
    "${LIFECYCLE7_WORKER}" "${LUA_LIVE}" "${MODEL_B_EVIDENCE}" "${MODEL_C_CORRECTIVE_PASS}" \
    "${PUBLICATION26}" "${LIVE26}" "${BUDGET_PY}" "${LEASE_PY}" "${MODEL_C_PY}" \
    "${MODEL_C_OWNER_PY}" "${MODEL_B_PY}" "${LIVE_GATE_DECISION}" "${QUIC_DOC}" "${UDP_DOC}" "${PATCH14}"
do
    [ -s "${file}" ] || fail "missing Strategy Lab/release record: ${file}"
done

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(awk -F= '/^PLUGIN_REVISION=/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${MAKEFILE}")
case "${revision}" in ''|*[!0-9]*) fail 'invalid plugin revision' ;; esac
candidate="os-zapret2-restyle-${version}_${revision}.pkg"
[ "${version}" = '0.4.1' ] || fail 'current Strategy Lab line must remain on VERSION=0.4.1'
[ "${revision}" -eq 14 ] || fail 'current source candidate must be PLUGIN_REVISION=14'
[ "${candidate}" = 'os-zapret2-restyle-0.4.1_14.pkg' ] || fail 'unexpected current source-candidate package identity'

# Level-1 authorities distinguish the current source candidate from the last published testing package.
require "${DOC_RULES}" 'DOC-015.'
require "${PRINCIPLES}" 'DEV-029.'
require "${PRINCIPLES}" 'DEV-031.'
require "${CHAT_RULES}" 'CHAT-001.'
require "${GH_RULES}" 'GH-001.'
require "${STATE}" 'State-line scope: **`v0.4.x`**'
require "${STATE}" 'current source candidate: `_14`'
require "${STATE}" 'current published testing package remains `_13` until `_14` is merged and persistently published'
require "${STATE}" 'No measured QUIC capability value may decide whether QUIC candidates run.'
require "${START_HERE}" 'Current source-candidate identity:** `v0.4.1_14`'
require "${START_HERE}" 'current published testing package remains `os-zapret2-restyle-0.4.1_13.pkg` / `v0.4.1_13` until `_14` source is merged'
require "${START_HERE}" 'this checkbox is the sole decision gate for running QUIC candidate tests'
require "${ROADMAP}" 'Current priority — publish and live-verify `_14`'
require "${ROADMAP}" 'ON → run QUIC candidates regardless of Stage-30 `quic_ipv4` control result'

# The _14 specialists must encode the owner-selected execution/input contract directly.
require "${QUIC_DOC}" 'default: **unchecked**'
require "${QUIC_DOC}" 'sole product decision that determines whether Stage 80 runs QUIC candidate tests'
require "${QUIC_DOC}" 'does not produce a capability-based QUIC skip'
require "${UDP_DOC}" 'decoded size **`1..4096` bytes**'
require "${UDP_DOC}" 'previous result is not cleared merely because Run was clicked'
require "${PATCH14}" 'source candidate: `v0.4.1_14`'
require "${PATCH14}" 'Stage-30 QUIC reachability/capability detection may remain diagnostic but cannot decide'

# Retained measurement evidence remains discoverable and immutable across the new source candidate.
require "${CURRENT_LEDGER}" 'job.xhdgCU'
require "${CURRENT_LEDGER}" 'Stage 60: `34209 ms`'
require "${CURRENT_LEDGER}" '5/5 `model_c_only=true`'
require "${CURRENT_LEDGER}" 'physical-segment startup median `82.5 ms`'
require "${CURRENT_LEDGER}" '2026-08-14-v0.4.1_12-warm-readiness-live-pass.md'
require "${CURRENT_LEDGER}" '2026-08-13-v0.4.1_6-discovery-corrective-live-pass.md'
require "${CURRENT_LEDGER}" '2026-08-12-v0.4.1_4-blob-common-set-live-pass.md'
require "${CURRENT_LEDGER}" '2026-08-12-v0.4.1_3-blob-startup-rss-live-pass.md'
require "${CURRENT_LEDGER}" '2026-08-12-v0.4.1_2-lua-init-live-pass.md'
require "${CURRENT_LEDGER}" '`v0.4.1_13` — Model-C-only production finalization'
require "${CURRENT_LEDGER}" 'cold_fallback_available=false'

# INDEX remains navigation/integrity only.
require "${INDEX}" 'DOCUMENTATION_RULES.md'
require "${INDEX}" 'PROJECT_PRINCIPLES.md'
require "${INDEX}" 'CHAT_RULES.md'
require "${INDEX}" 'GITHUB_PUBLICATION.md'
require "${INDEX}" 'STRATEGY_LAB_QUIC_CONTROL.md'
require "${INDEX}" 'STRATEGY_LAB_UDP_INPUT.md'
require "${INDEX}" 'history/current/v0.4.x.md'
require "${INDEX}" 'history/archive/v0.1.x.md'
require "${INDEX}" 'history/archive/v0.2.x.md'
require "${INDEX}" 'history/archive/v0.3.x.md'
require "${INDEX}" 'verification/evidence/'
require "${INDEX}" 'Historical statements remain historical'

# Historical source/build/live evidence remains checked at its immutable records.
require "${RELEASE_DOC}" '# os-zapret2-restyle v0.4.1'
require "${RELEASE_DOC}" '`os-zapret2-restyle-0.4.1_1.pkg`'
require "${RELEASE_EVIDENCE}" 'Status: **PUBLISHED**'
require "${RELEASE_EVIDENCE}" 'os-zapret2-restyle-0.4.1_1.pkg'
require "${BLOB_PUBLICATION}" 'Status: **PUBLISHED / OWNER-LIVE PENDING**'
require "${BLOB_LIVE}" 'Status: **PASS**'
require "${BLOB_LIVE}" 'Median ready and settled RSS was exactly `4360 KiB`'
require "${BLOB_LIVE}" 'Do **not** change production Model C BLOB loading.'
require "${BLOB4_PUBLICATION}" 'Status: **PUBLISHED / OWNER-LIVE PENDING**'
require "${BLOB4_LIVE}" 'Status: **PASS**'
require "${BLOB4_LIVE}" '`48` planned starts'
require "${BLOB4_LIVE}" '`+0.234 ms` / `+0.375%`'
require "${BLOB4_LIVE}" '`+2 KiB` / `+0.046%`'
require "${BLOB4_LIVE}" 'close the BLOB-loading startup/RSS optimization as a negative result for current width three'

require "${DISCOVERY_PY}" 'POLICY = "discovery-probe-agreement-v1"'
require "${DISCOVERY_PY}" 'VARIANTS = ("head", "get-1", "get-4k", "deep-16k")'
require "${DISCOVERY_PY}" 'production_discovery_policy_changed": False'
require "${DISCOVERY6_LIVE}" 'Status: **ACCEPTED / OWNER-LIVE PASS**'
require "${DISCOVERY6_LIVE}" 'Discovery probe measurement conclusion: measurement_accepted'
require "${DISCOVERY6_PATCH}" 'Production discovery remains the bounded 4 KiB GET'

require "${LIFECYCLE7_PATCH}" '# v0.4.1_7 — Measure Model-C per-batch lifecycle amortization'
require "${LIFECYCLE7_PY}" 'POLICY = "model-c-batch-lifecycle-amortization-v1"'
require "${LIFECYCLE7_PY}" '"production_model_changed": False'
require "${READINESS12_LIVE}" 'OWNER-LIVE PASS / READINESS CORRECTIVE VALIDATED / CROSS-BATCH REUSE CLOSED'
require "${READINESS12_LIVE}" 'fallback_detected=false'

# Current live matrix must preserve _13 evidence while selecting _14 explicit QUIC/UDP verification.
require "${MATRIX}" 'latest owner-tested package: `os-zapret2-restyle-0.4.1_13.pkg`'
require "${MATRIX}" 'current source candidate: `v0.4.1_14`'
require "${MATRIX}" 'It is not the current desired product behavior.'
require "${MATRIX}" 'Enable QUIC ON with ISP-blocked ordinary QUIC'
require "${MATRIX}" 'Oversized Generic UDP payload UX'
require "${MATRIX}" 'Valid configured Generic UDP → actual candidate search'
require "${MATRIX}" 'PASS ON `_13` — OWNER ACCEPTED'
require "${MATRIX}" 'SUPERSEDED AS PRODUCT RULE'
require "${MATRIX}" 'PENDING `_14` OWNER'

require "${PUBLICATION26}" '8ada9cba28916fff506f19b34f5ef3de16e2008e'
require "${LIVE26}" 'Status: **PASS**'
require "${MODEL_C_CORRECTIVE_PASS}" 'job.5yGde5'
require "${MODEL_B_EVIDENCE}" 'PRODUCTION STAGE-60 MODEL B OWNER-LIVE PASS'
require "${BUDGET_PY}" 'POLICY = "eligible-work-v1"'
require "${LEASE_PY}" 'preferred-free-else-alternate'
require "${MODEL_C_PY}" 'MODEL = "C-warm-bucket-source-port-dispatch"'
require "${MODEL_C_OWNER_PY}" 'parallel["cold_fallback_available"] = False'
require "${MODEL_C_OWNER_PY}" 'parallel["model_c_only"] = True'
require "${MODEL_B_PY}" 'MODEL = "B-warm-worker-parallel-batched"'
require "${LUA_PY}" 'POLICY = "lua-init-set-equivalence-v1"'
require "${LUA_LIVE}" 'Status: **PASS**'
require "${BLOB_PY}" 'POLICY = "blob-common-set-scaling-v1"'
require "${BLOB_PY}" 'PRODUCTION_CANDIDATE_WIDTH = 3'
require "${BLOB_TEST}" 'PASS: BLOB common-set scaling measurement is single-worker, balanced, lifecycle-safe'
require "${BLOB_DOC}" '_3 ACCEPTED / _4 ACCEPTED / BLOB-LOADING OPTIMIZATION CLOSED / PRODUCTION MODEL C UNCHANGED'
require "${BLOB_PATCH}" 'SOURCE / CI / FREEBSD15 PACKAGE / PUBLICATION / OWNER-LIVE PASS'

require "${LIVE_GATE_DECISION}" 'all-or-nothing release checklist.'
if grep -Fq 'Stable release preparation and pkg-repository promotion remain blocked until every' "${MATRIX}"; then
    fail 'blanket all-row stable-release gate returned'
fi

sh -n "$0"
echo "PASS: ${candidate} source-candidate state preserves accepted _13 history, selects explicit Enable QUIC/Generic UDP _14 verification, and keeps retained v0.4.x measurements discoverable"
