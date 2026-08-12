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
PATCH="${ROOT_DIR}/docs/patches/v0.4.0_25.md"
LEASE_TEST="${ROOT_DIR}/scripts/test-strategy-lab-stage60-source-port-lease.sh"
LEASE_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_source_port_lease.py"
MODEL_C_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_model_c.py"
MODEL_B_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_parallel.py"
LIVE_GATE_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md"

fail(){ echo "FAIL: $*" >&2; exit 1; }
require(){ grep -Fq "$2" "$1" || fail "missing contract text in $1: $2"; }

for file in "${MATRIX}" "${STATE}" "${INDEX}" "${VERSION_FILE}" "${MAKEFILE}" \
    "${MODEL_B_EVIDENCE}" "${MODEL_C_LIVE}" "${MODEL_C_CORRECTIVE_PASS}" "${PATCH}" \
    "${LEASE_TEST}" "${LEASE_PY}" "${MODEL_C_PY}" "${MODEL_B_PY}" "${LIVE_GATE_DECISION}"
do
    [ -s "${file}" ] || fail "missing Strategy Lab live-gate record: ${file}"
done

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(awk -F= '/^PLUGIN_REVISION=/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${MAKEFILE}")
case "${revision}" in ''|*[!0-9]*) fail 'invalid plugin revision' ;; esac
candidate="os-zapret2-restyle-${version}_${revision}.pkg"
[ "${version}" = '0.4.0' ] || fail "unexpected active Strategy Lab version ${version}"
[ "${revision}" -eq 25 ] || fail 'Stage-60 source-port corrective revision must be exactly 25'

# Current `_25` Engineering Memory must record the accepted owner-live corrective. Historical
# `_23` job literals are validated in their immutable evidence record below, not duplicated as
# exact prose requirements in the current-state handoff.
require "${STATE}" 'Current source line: `VERSION=0.4.0`, `PLUGIN_REVISION=25`'
require "${STATE}" 'Current source candidate: `os-zapret2-restyle-0.4.0_25.pkg`'
require "${STATE}" 'Latest owner-tested testing candidate: `v0.4.0_25`'
require "${STATE}" '2026-08-12-v0.4.0_25-source-port-live-pass.md'
require "${STATE}" 'job.5yGde5'
require "${STATE}" '.parallel.fallbacks=[]'
require "${STATE}" 'Stage 60 duration `34198 ms`'
require "${STATE}" 'total job duration `114759 ms`'
require "${STATE}" 'fresh independent lease'
require "${STATE}" 'number of endpoints × IPv4/IPv6 × TLS/QUIC × Generic UDP × Standard/Extended mode'

require "${INDEX}" 'For a current diagnosis, **do not start from an old evidence file**.'
require "${INDEX}" 'docs/patches/v0.4.0_25.md'
require "${INDEX}" '2026-08-12-v0.4.0_25-source-port-live-pass.md'
require "${INDEX}" '2026-08-11-v0.4.0_23-model-c-live-hold.md'
require "${INDEX}" 'DEC-2026-08-05-efficient-github-delivery.md'
require "${INDEX}" 'DEC-2026-08-05-universal-versioned-github-titles.md'

require "${MATRIX}" 'Current published/owner-tested package: `os-zapret2-restyle-0.4.0_25.pkg`'
require "${MATRIX}" 'job.5yGde5'
require "${MATRIX}" '.parallel.fallbacks=[]'
require "${MATRIX}" 'Stage 60 duration `34198 ms`'
require "${MATRIX}" 'total job duration `114759 ms`'
require "${MATRIX}" 'policy=preferred-free-else-alternate'
require "${MATRIX}" 'foreign_port_action=skip-only'
require "${MATRIX}" 'job.FaLtIk'
require "${MATRIX}" 'job.G0wC5l'
require "${MATRIX}" 'physical_worker_count=1'
require "${MATRIX}" 'controlled source port is already in use: 42004'
require "${MATRIX}" 'Adaptive `_28` focused evidence:'
require "${MATRIX}" 'about 144.125 s'
require "${MATRIX}" 'about 71.023 s'
require "${MATRIX}" 'about 86.5%'
require "${MATRIX}" 'roughly 62.0%'
require "${MATRIX}" 'mean 74.8082 s'
require "${MATRIX}" 'about 15.96%'
require "${MATRIX}" 'number of endpoints × IPv4/IPv6 × TLS/QUIC × Generic UDP × Standard/Extended mode'

scenario_one=$(awk -F'|' '$2 ~ /^[[:space:]]*1[[:space:]]*$/ && $6 ~ /PASS ON `_27` — v0.4.0 mandatory row/ {n++} END {print n+0}' "${MATRIX}")
[ "${scenario_one}" -eq 1 ] || fail 'v0.4.0 mandatory Scenario 1 PASS row mismatch'
scenario_seven=$(awk -F'|' '$2 ~ /^[[:space:]]*7[[:space:]]*$/ && $6 ~ /PASS ON `_25` FOR CURRENT CHANGE/ {n++} END {print n+0}' "${MATRIX}")
[ "${scenario_seven}" -eq 1 ] || fail 'Scenario 7 _25 live PASS row mismatch'
pending_count=$(awk -F'|' '$2 ~ /^[[:space:]]*([2-6]|[8-9]|1[0-8])[[:space:]]*$/ && $6 ~ /PENDING REGRESSION/ {n++} END {print n+0}' "${MATRIX}")
[ "${pending_count}" -eq 16 ] || fail 'rows 2-6 and 8-18 must remain honest pending regression coverage'

# `_23` live evidence remains immutable corrective input.
require "${MODEL_C_LIVE}" 'job.FaLtIk'
require "${MODEL_C_LIVE}" 'job.G0wC5l'
require "${MODEL_C_LIVE}" 'controlled source port is already in use: 42004'
require "${MODEL_C_LIVE}" 'RUNNING -> RUNNING'
require "${MODEL_C_LIVE}" 'number of endpoints × IPv4/IPv6 × TLS/QUIC × Generic UDP × Standard/Extended mode'

# `_25` durable owner-live evidence must stay current and must not invent a collision.
require "${MODEL_C_CORRECTIVE_PASS}" 'Status: **PASS**'
require "${MODEL_C_CORRECTIVE_PASS}" 'job.5yGde5'
require "${MODEL_C_CORRECTIVE_PASS}" 'C-warm-bucket-source-port-dispatch'
require "${MODEL_C_CORRECTIVE_PASS}" '.parallel.fallbacks=[]'
require "${MODEL_C_CORRECTIVE_PASS}" '34198 ms'
require "${MODEL_C_CORRECTIVE_PASS}" '114759 ms'
require "${MODEL_C_CORRECTIVE_PASS}" 'collisions=[]'
require "${MODEL_C_CORRECTIVE_PASS}" 'replacement_count=0'
require "${MODEL_C_CORRECTIVE_PASS}" 'does **not** prove an alternate-port replacement under a real foreign'

# `_25` source contract: lease exact free ports without weakening attribution or touching owners.
require "${PATCH}" 'This patch changes **Stage 60 source-port ownership only**.'
require "${PATCH}" 'foreign socket/process completely untouched'
require "${PATCH}" 'fresh lease'
require "${PATCH}" 'No Stage-60 timeout is increased in this patch.'
require "${PATCH}" 'Selected `_25` owner-live gate: **PASS**.'
require "${PATCH}" 'number of endpoints × IPv4/IPv6 × TLS/QUIC × Generic UDP × Standard/Extended mode'
require "${LEASE_TEST}" 'PASS: Stage 60 keeps free preferred ports'
require "${LEASE_PY}" 'foreign_port_action'
require "${LEASE_PY}" 'source-port-free'
require "${LEASE_PY}" 'original_model_c_batch'
require "${LEASE_PY}" 'original_model_b_batch'

# Preferred/fallback architecture remains intact.
require "${MODEL_C_PY}" 'MODEL = "C-warm-bucket-source-port-dispatch"'
require "${MODEL_B_PY}" 'MODEL = "B-warm-worker-parallel-batched"'
require "${MODEL_B_EVIDENCE}" 'PRODUCTION STAGE-60 MODEL B OWNER-LIVE PASS'

require "${LIVE_GATE_DECISION}" 'all-or-nothing release checklist.'
if grep -Fq 'Stable release preparation and pkg-repository promotion remain blocked until every' "${MATRIX}"; then
    fail 'blanket all-row stable-release gate returned'
fi

sh -n "$0"
echo "PASS: live matrix records ${candidate} as owner-live accepted for the source-port corrective while retaining _23 defect input and _22 Model-B fallback baseline"
