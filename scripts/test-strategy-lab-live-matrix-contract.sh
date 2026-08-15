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
READINESS12_LIVE="${ROOT_DIR}/docs/verification/evidence/2026-08-14-v0.4.1_12-warm-readiness-live-pass.md"
VERSION_FILE="${ROOT_DIR}/VERSION"
MAKEFILE="${ROOT_DIR}/Makefile"
QUIC_DOC="${ROOT_DIR}/docs/architecture/STRATEGY_LAB_QUIC_CONTROL.md"
UDP_DOC="${ROOT_DIR}/docs/architecture/STRATEGY_LAB_UDP_INPUT.md"
MODEL_C_OWNER_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_model_c_production.py"

fail(){ echo "FAIL: $*" >&2; exit 1; }
require(){ grep -Fq "$2" "$1" || fail "missing contract text in $1: $2"; }

for file in "${MATRIX}" "${STATE}" "${INDEX}" "${START_HERE}" "${PRINCIPLES}" "${DOC_RULES}" \
    "${CHAT_RULES}" "${GH_RULES}" "${ROADMAP}" "${CURRENT_LEDGER}" "${RELEASE_DOC}" \
    "${READINESS12_LIVE}" "${VERSION_FILE}" "${MAKEFILE}" "${QUIC_DOC}" "${UDP_DOC}" \
    "${MODEL_C_OWNER_PY}"
do
    [ -s "${file}" ] || fail "missing Strategy Lab/current-state record: ${file}"
done

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(awk -F= '/^PLUGIN_REVISION=/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${MAKEFILE}")
case "${revision}" in ''|*[!0-9]*) fail 'invalid plugin revision' ;; esac
[ "${version}" = '0.4.1' ] || fail 'current Strategy Lab line must remain on VERSION=0.4.1'

candidate_suffix="_${revision}"
candidate_tag="v${version}_${revision}"
candidate_pkg="os-zapret2-restyle-${version}_${revision}.pkg"

# Current authority follows the package identity that actually exists in source.
# Never hard-code yesterday's _N as the allowed future source candidate: owner-selected
# source truth advances first and documentation/tests must reconcile to it.
require "${STATE}" "current source candidate: \`${candidate_suffix}\`"
require "${START_HERE}" "Current handoff identity:** \`${candidate_tag}"
require "${START_HERE}" "current source candidate: \`PLUGIN_REVISION=${revision}\`"
require "${ROADMAP}" "\`${candidate_tag}\`"
require "${CURRENT_LEDGER}" "current source candidate: \`${candidate_suffix}\`"
require "${MATRIX}" "current source candidate: \`${candidate_tag}\`"

# Rule books remain the authority for state/documentation/publication handling.
require "${DOC_RULES}" 'DOC-015.'
require "${PRINCIPLES}" 'DEV-029.'
require "${PRINCIPLES}" 'DEV-031.'
require "${CHAT_RULES}" 'CHAT-001.'
require "${GH_RULES}" 'GH-001.'
require "${GH_RULES}" 'GH-060.'
require "${GH_RULES}" 'GH-061.'
require "${STATE}" 'State-line scope: **`v0.4.x`**'

# Current product direction stays Model-C-only; old B/A production fallback must not
# re-enter through a stale live-matrix fixture.
require "${MODEL_C_OWNER_PY}" 'model_c_only'
require "${MODEL_C_OWNER_PY}" 'cold_fallback_available'
require "${CURRENT_LEDGER}" 'Model C is the only normal production Stage-60 runtime'
require "${CURRENT_LEDGER}" 'cold_fallback_available=false'

# The live matrix must retain accepted history but describe the current selected work.
require "${MATRIX}" '`v0.4.1_13` ACCEPTED BASELINE'
require "${MATRIX}" '`v0.4.1_14` PUBLISHED/INSTALLED'
require "${MATRIX}" '`_14` owner-live observations that selected `_15`'
require "${MATRIX}" 'QUIC tested count/IDs ordinary output'
require "${MATRIX}" 'exact 140-byte binary input'
require "${MATRIX}" 'selected-port/payload direct UDP observation'
require "${MATRIX}" 'no-reply does not mean closed / does not gate candidates'
require "${MATRIX}" 'terminal payload cleanup and Zapret2 restoration PASS.'

# QUIC specialist contract: owner-selected checkbox is the execution gate and normal
# output proves real attempts instead of exposing only an opaque not_found enum.
require "${QUIC_DOC}" 'sole product decision that determines whether Stage 80 runs QUIC candidate tests'
require "${QUIC_DOC}" 'does not produce a capability-based skip'
require "${QUIC_DOC}" 'number of attempted QUIC candidates'
require "${QUIC_DOC}" 'attempted candidate IDs'
require "${QUIC_DOC}" '`QUIC открыт`'
require "${QUIC_DOC}" '`QUIC закрыт`'
require "${QUIC_DOC}" '`QUIC is open`'
require "${QUIC_DOC}" '`QUIC is blocked`'
require "${QUIC_DOC}" 'Raw/advanced output still retains the complete machine result.'

# Generic UDP specialist contract: exact decoded bytes, direct observation with the
# chosen port/payload, and UDP silence must remain non-gating.
require "${UDP_DOC}" 'decoded size **`1..4096` bytes**'
require "${UDP_DOC}" 'An exact 140-byte file is valid'
require "${UDP_DOC}" 'FileReader.readAsArrayBuffer'
require "${UDP_DOC}" 'the exact selected destination port'
require "${UDP_DOC}" 'the exact job-local payload bytes'
require "${UDP_DOC}" '**UDP silence is not proof that a port is closed.**'
require "${UDP_DOC}" 'never suppresses or short-circuits the bypass candidate catalog'
require "${UDP_DOC}" 'number and IDs of actual UDP candidates'

# Current docs preserve accepted measurement decisions; this source task is a
# protocol-observability/input correction, not an excuse to reopen unrelated work.
require "${CURRENT_LEDGER}" 'job.xhdgCU'
require "${CURRENT_LEDGER}" 'Stage 60: `34209 ms`'
require "${CURRENT_LEDGER}" '5/5 `model_c_only=true`'
require "${CURRENT_LEDGER}" 'physical-segment startup median `82.5 ms`'
require "${CURRENT_LEDGER}" 'BLOB startup/RSS/common set: no lazy-BLOB production change justified'
require "${CURRENT_LEDGER}" 'discovery: retain bounded GET-4K'
require "${READINESS12_LIVE}" 'OWNER-LIVE PASS / READINESS CORRECTIVE VALIDATED / CROSS-BATCH REUSE CLOSED'

# INDEX remains navigation/integrity only and links to current authority.
require "${INDEX}" 'DOCUMENTATION_RULES.md'
require "${INDEX}" 'PROJECT_PRINCIPLES.md'
require "${INDEX}" 'CHAT_RULES.md'
require "${INDEX}" 'GITHUB_PUBLICATION.md'
require "${INDEX}" 'STRATEGY_LAB_QUIC_CONTROL.md'
require "${INDEX}" 'STRATEGY_LAB_UDP_INPUT.md'
require "${INDEX}" 'history/current/v0.4.x.md'
require "${INDEX}" 'verification/evidence/'
require "${INDEX}" 'Historical statements remain historical'

# Full-release identity remains historical/current independently from testing _N.
require "${RELEASE_DOC}" '# os-zapret2-restyle v0.4.1'
require "${RELEASE_DOC}" '`os-zapret2-restyle-0.4.1_1.pkg`'

printf 'PASS: live-matrix contract follows current source identity %s (%s), preserves accepted history, Model-C-only direction, and the selected QUIC/UDP live-verification semantics\n' "${candidate_tag}" "${candidate_pkg}"
