#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MATRIX="${ROOT_DIR}/docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md"
STATE="${ROOT_DIR}/docs/PROJECT_STATE.md"
INDEX="${ROOT_DIR}/docs/INDEX.md"
RELEASE_DOC="${ROOT_DIR}/docs/releases/v0.4.1.md"
RELEASE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.1-release-publication.md"
BLOB_PUBLICATION="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.1_3-blob-measurement-publication.md"
BLOB_LIVE="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.1_3-blob-startup-rss-live-pass.md"
BLOB4_PUBLICATION="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.1_4-blob-common-set-publication.md"
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
MODEL_B_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md"
MODEL_C_CORRECTIVE_PASS="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.0_25-source-port-live-pass.md"
PUBLICATION26="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.0_26-publication.md"
LIVE26="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.0_26-adaptive-budget-live-pass.md"
LUA_LIVE="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.1_2-lua-init-live-pass.md"
BUDGET_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/adaptive_budget.py"
LEASE_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_source_port_lease.py"
MODEL_C_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_model_c.py"
MODEL_B_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_parallel.py"
LIVE_GATE_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md"

fail(){ echo "FAIL: $*" >&2; exit 1; }
require(){ grep -Fq "$2" "$1" || fail "missing contract text in $1: $2"; }

for file in "${MATRIX}" "${STATE}" "${INDEX}" "${RELEASE_DOC}" "${RELEASE_EVIDENCE}" \
    "${BLOB_PUBLICATION}" "${BLOB_LIVE}" "${BLOB4_PUBLICATION}" "${VERSION_FILE}" "${MAKEFILE}" \
    "${LUA_DOC}" "${LUA_PATCH}" "${LUA_TEST}" "${LUA_PY}" "${BLOB_DOC}" "${BLOB_PATCH}" \
    "${BLOB_TEST}" "${BLOB_PY}" "${LUA_LIVE}" "${MODEL_B_EVIDENCE}" \
    "${MODEL_C_CORRECTIVE_PASS}" "${PUBLICATION26}" "${LIVE26}" "${BUDGET_PY}" \
    "${LEASE_PY}" "${MODEL_C_PY}" "${MODEL_B_PY}" "${LIVE_GATE_DECISION}"
do
    [ -s "${file}" ] || fail "missing Strategy Lab/release record: ${file}"
done

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(awk -F= '/^PLUGIN_REVISION=/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${MAKEFILE}")
case "${revision}" in ''|*[!0-9]*) fail 'invalid plugin revision' ;; esac
candidate="os-zapret2-restyle-${version}_${revision}.pkg"
[ "${version}" = '0.4.1' ] || fail 'BLOB measurement must remain on VERSION=0.4.1'
[ "${revision}" -eq 4 ] || fail 'BLOB common-set measurement must use PLUGIN_REVISION=4'
[ "${candidate}" = 'os-zapret2-restyle-0.4.1_4.pkg' ] || fail 'unexpected BLOB common-set package identity'

require "${STATE}" 'Current source line: `VERSION=0.4.1`, `PLUGIN_REVISION=4`'
require "${STATE}" 'Current source candidate: `os-zapret2-restyle-0.4.1_4.pkg`'
require "${STATE}" 'Current published stable package: `os-zapret2-restyle-0.4.1_1.pkg`'
require "${STATE}" 'Latest published testing prerelease: `v0.4.1_4` / `os-zapret2-restyle-0.4.1_4.pkg`'
require "${STATE}" 'Latest owner-tested testing candidate: `v0.4.1_3` — BLOB startup/readiness/RSS measurement PASS'
require "${STATE}" 'Latest detailed Strategy Lab runtime basis: `v0.4.0_26` — adaptive-budget owner-live PASS'
require "${STATE}" 'job.xhdgCU'
require "${STATE}" 'Stage 60 duration `34209 ms`'
require "${STATE}" 'total job duration `114644 ms`'
require "${STATE}" 'Policy: `blob-common-set-scaling-v1`, schema `2`.'
require "${STATE}" 'production_change_recommended=false'
require "${STATE}" 'publication workflow run `31633335688` — SUCCESS'

require "${INDEX}" 'docs/architecture/STRATEGY_LAB_BLOB_LOADING.md'
require "${INDEX}" 'docs/patches/v0.4.1_4.md'
require "${INDEX}" 'docs/verification/evidence/2026-08-12-v0.4.1_4-blob-common-set-publication.md'
require "${INDEX}" 'docs/verification/evidence/2026-08-12-v0.4.1_3-blob-measurement-publication.md'
require "${INDEX}" 'docs/verification/evidence/2026-08-12-v0.4.1_3-blob-startup-rss-live-pass.md'
require "${INDEX}" 'docs/verification/evidence/2026-08-12-v0.4.1_2-lua-init-live-pass.md'
require "${INDEX}" 'C-warm-bucket-source-port-dispatch -> B-warm-worker-parallel-batched -> A-cold-fallback'

require "${RELEASE_DOC}" '# os-zapret2-restyle v0.4.1'
require "${RELEASE_DOC}" '`os-zapret2-restyle-0.4.1_1.pkg`'
require "${RELEASE_EVIDENCE}" 'Status: **PUBLISHED**'
require "${RELEASE_EVIDENCE}" 'os-zapret2-restyle-0.4.1_1.pkg'
require "${BLOB_PUBLICATION}" 'Status: **PUBLISHED / OWNER-LIVE PENDING**'
require "${BLOB_PUBLICATION}" 'da427cd061df1f3cbc01ba11a14a6417f2e406b3'
require "${BLOB_PUBLICATION}" '31616501996'
require "${BLOB_PUBLICATION}" 'sha256:6efdb8e844bdec5cbe2fddffd77c1234cc53b939520c4648ed68da3126e7989b'
require "${BLOB_LIVE}" 'Status: **PASS**'
require "${BLOB_LIVE}" '27 complete worker starts'
require "${BLOB_LIVE}" 'Median ready and settled RSS was exactly `4360 KiB`'
require "${BLOB_LIVE}" 'Do **not** change production Model C BLOB loading.'
require "${BLOB4_PUBLICATION}" 'Status: **PUBLISHED / OWNER-LIVE PENDING**'
require "${BLOB4_PUBLICATION}" '461fe2d045b131f3400f285a9cb59808b5f33ce2'
require "${BLOB4_PUBLICATION}" '31633335688'
require "${BLOB4_PUBLICATION}" '369482221'
require "${BLOB4_PUBLICATION}" 'os-zapret2-restyle-0.4.1_4.pkg'
require "${BLOB4_PUBLICATION}" 'sha256:934fdd3a73117b3d914c9823f29eb7f2ca47196d97c30d94e3066a38159edbc9'

require "${MATRIX}" 'Current published release package: `os-zapret2-restyle-0.4.1_1.pkg`'
require "${MATRIX}" 'Latest owner-tested runtime package: `os-zapret2-restyle-0.4.0_26.pkg`'
require "${MATRIX}" '`v0.4.1` RELEASE-SELECTED LIVE BASIS — PASS ON `_26`'
require "${MATRIX}" 'job.xhdgCU'
require "${MATRIX}" '.parallel.fallbacks=[]'
require "${MATRIX}" 'policy=preferred-free-else-alternate'

scenario_one=$(awk -F'|' '$2 ~ /^[[:space:]]*1[[:space:]]*$/ && $6 ~ /PASS ON `_27` — v0.4.0 historical mandatory row/ {n++} END {print n+0}' "${MATRIX}")
[ "${scenario_one}" -eq 1 ] || fail 'historical v0.4.0 Scenario 1 PASS row mismatch'
scenario_seven=$(awk -F'|' '$2 ~ /^[[:space:]]*7[[:space:]]*$/ && $6 ~ /PASS ON `_26` — v0.4.1 selected live basis/ {n++} END {print n+0}' "${MATRIX}")
[ "${scenario_seven}" -eq 1 ] || fail 'Scenario 7 must retain _26 as v0.4.1 selected live basis'
pending_count=$(awk -F'|' '$2 ~ /^[[:space:]]*([2-6]|[8-9]|1[0-8])[[:space:]]*$/ && $6 ~ /PENDING REGRESSION/ {n++} END {print n+0}' "${MATRIX}")
[ "${pending_count}" -eq 16 ] || fail 'rows 2-6 and 8-18 must remain honest pending regression coverage'

require "${PUBLICATION26}" '8ada9cba28916fff506f19b34f5ef3de16e2008e'
require "${LIVE26}" 'Status: **PASS**'
require "${LIVE26}" 'job.xhdgCU'
require "${LIVE26}" 'C-warm-bucket-source-port-dispatch'
require "${LIVE26}" '.parallel.fallbacks=[]'
require "${MODEL_C_CORRECTIVE_PASS}" 'job.5yGde5'
require "${MODEL_B_EVIDENCE}" 'PRODUCTION STAGE-60 MODEL B OWNER-LIVE PASS'
require "${BUDGET_PY}" 'POLICY = "eligible-work-v1"'
require "${LEASE_PY}" 'preferred-free-else-alternate'
require "${MODEL_C_PY}" 'MODEL = "C-warm-bucket-source-port-dispatch"'
require "${MODEL_C_PY}" 'for name in spec.lua_dependencies'
require "${MODEL_B_PY}" 'MODEL = "B-warm-worker-parallel-batched"'
require "${LUA_PY}" 'POLICY = "lua-init-set-equivalence-v1"'
require "${LUA_PY}" 'resources.configured_lua_root()'
require "${LUA_LIVE}" 'Status: **PASS**'
require "${LUA_LIVE}" 'conclusion=equivalent_init_set'
require "${BLOB_PY}" 'SCHEMA = 2'
require "${BLOB_PY}" 'POLICY = "blob-common-set-scaling-v1"'
require "${BLOB_PY}" 'WORKER = "external"'
require "${BLOB_PY}" 'DIVERT_PORT = 9992'
require "${BLOB_PY}" 'EXTERNAL_COMMON = ('
require "${BLOB_PY}" 'PRODUCTION_CANDIDATE_WIDTH = 3'
require "${BLOB_PY}" 'production_change_recommended'
require "${BLOB_TEST}" 'PASS: BLOB common-set scaling measurement is single-worker, balanced, lifecycle-safe'
require "${BLOB_DOC}" '_3 ACCEPTED / _4 PUBLISHED — OWNER-LIVE PENDING / PRODUCTION MODEL C UNCHANGED'
require "${BLOB_PATCH}" 'SOURCE / CI / FREEBSD15 PACKAGE / PUBLICATION PASS / OWNER-LIVE PENDING'

require "${LIVE_GATE_DECISION}" 'all-or-nothing release checklist.'
if grep -Fq 'Stable release preparation and pkg-repository promotion remain blocked until every' "${MATRIX}"; then
    fail 'blanket all-row stable-release gate returned'
fi

sh -n "$0"
echo "PASS: ${candidate} is published for owner common-set measurement while owner-tested truth remains _3 and production live truth remains _26"
