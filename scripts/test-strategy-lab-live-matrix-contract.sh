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
VERSION_FILE="${ROOT_DIR}/VERSION"
MAKEFILE="${ROOT_DIR}/Makefile"
QUIC_DOC="${ROOT_DIR}/docs/architecture/STRATEGY_LAB_QUIC_CONTROL.md"
UDP_DOC="${ROOT_DIR}/docs/architecture/STRATEGY_LAB_UDP_INPUT.md"
READINESS12_LIVE="${ROOT_DIR}/docs/verification/evidence/2026-08-14-v0.4.1_12-warm-readiness-live-pass.md"
MODEL_C_OWNER_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_model_c_production.py"

fail(){ echo "FAIL: $*" >&2; exit 1; }
require(){ grep -Fq "$2" "$1" || fail "missing contract text in $1: $2"; }

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(awk -F= '/^PLUGIN_REVISION=/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${MAKEFILE}")
case "${version}" in *.*.*) ;; *) fail 'invalid project version' ;; esac
case "${revision}" in ''|*[!0-9]*) fail 'invalid plugin revision' ;; esac

major=$(printf '%s\n' "${version}" | cut -d. -f1)
second=$(printf '%s\n' "${version}" | cut -d. -f2)
line="v${major}.${second}.x"
current_ledger="${ROOT_DIR}/docs/history/current/${line}.md"
release_doc="${ROOT_DIR}/docs/releases/v${version}.md"
candidate_tag="v${version}_${revision}"
candidate_pkg="os-zapret2-restyle-${version}_${revision}.pkg"

for file in "${MATRIX}" "${STATE}" "${INDEX}" "${START_HERE}" "${PRINCIPLES}" "${DOC_RULES}" \
    "${CHAT_RULES}" "${GH_RULES}" "${ROADMAP}" "${current_ledger}" "${release_doc}" \
    "${READINESS12_LIVE}" "${VERSION_FILE}" "${MAKEFILE}" "${QUIC_DOC}" "${UDP_DOC}" \
    "${MODEL_C_OWNER_PY}"
do
    [ -s "${file}" ] || fail "missing Strategy Lab/current-state record: ${file}"
done

# Current authority follows VERSION/PLUGIN_REVISION and the active second-component line.
require "${STATE}" "State-line scope: **\`${line}\`**"
require "${STATE}" "package candidate: \`${candidate_pkg}\`"
require "${START_HERE}" "Current handoff identity:** \`${candidate_tag}\`"
require "${START_HERE}" "\`VERSION=${version}\`"
require "${START_HERE}" "\`PLUGIN_REVISION=${revision}\`"
require "${ROADMAP}" "\`${candidate_tag}\`"
require "${INDEX}" "history/current/${line}.md"
require "${release_doc}" "# os-zapret2-restyle v${version}"
require "${release_doc}" "\`${candidate_pkg}\`"

# Rule books remain the authority for state/documentation/publication handling.
require "${DOC_RULES}" 'DOC-015.'
require "${PRINCIPLES}" 'DEV-029.'
require "${PRINCIPLES}" 'DEV-031.'
require "${CHAT_RULES}" 'CHAT-001.'
require "${GH_RULES}" 'GH-001.'
require "${GH_RULES}" 'GH-060.'
require "${GH_RULES}" 'GH-061.'

# Current product direction stays Model-C-only across version-line rollover.
require "${MODEL_C_OWNER_PY}" 'model_c_only'
require "${MODEL_C_OWNER_PY}" 'cold_fallback_available'
require "${current_ledger}" 'Model-C-only normal Stage 60'

# Current live matrix retains accepted execution/feature boundaries without pinning an old package identity.
require "${MATRIX}" 'QUIC ON candidate execution/observability'
require "${MATRIX}" 'QUIC OFF execution suppresses QUIC catalog'
require "${MATRIX}" 'Generic UDP exact-byte path'
require "${MATRIX}" 'Enable QUIC saved state survives Laboratory reload/revisit'
require "${MATRIX}" 'IPv4 + real Host/SNI remains pinned to entered destination'
require "${MATRIX}" 'final working IP profile contains `--ipset-ip=<target>` and exact replay'
require "${MATRIX}" 'bare-IP QUIC without Host/SNI'
require "${MATRIX}" 'Stage-90 cleanup/restoration after selected IP runs'

# QUIC specialist contract remains owner-selected and observable.
require "${QUIC_DOC}" 'sole product decision that determines whether Stage 80 runs QUIC candidate tests'
require "${QUIC_DOC}" 'does not produce a capability-based skip'
require "${QUIC_DOC}" 'number of attempted QUIC candidates'
require "${QUIC_DOC}" 'attempted candidate IDs'
require "${QUIC_DOC}" '`QUIC открыт`'
require "${QUIC_DOC}" '`QUIC закрыт`'
require "${QUIC_DOC}" '`QUIC is open`'
require "${QUIC_DOC}" '`QUIC is blocked`'
require "${QUIC_DOC}" 'Raw/advanced output still retains the complete machine result.'

# Generic UDP specialist contract remains exact-byte and independently observable.
require "${UDP_DOC}" 'decoded size **`1..4096 bytes`**'
require "${UDP_DOC}" 'An exact 140-byte file is valid'
require "${UDP_DOC}" 'Generic UDP does **not** use a multipart upload directory.'
require "${UDP_DOC}" 'FileReader.readAsArrayBuffer'
require "${UDP_DOC}" 'application-owned staged state'
require "${UDP_DOC}" 'job_directory_not_writable'
require "${UDP_DOC}" 'the selected destination port'
require "${UDP_DOC}" 'exact job-local payload bytes'
require "${UDP_DOC}" '**UDP silence is not proof that a port is closed.**'
require "${UDP_DOC}" 'does not suppress the bypass candidate catalog'
require "${UDP_DOC}" 'actual candidate count/IDs'

# Accepted measurement proof remains retained even after its working ledger is archived.
require "${READINESS12_LIVE}" 'OWNER-LIVE PASS / READINESS CORRECTIVE VALIDATED / CROSS-BATCH REUSE CLOSED'
require "${INDEX}" 'history/archive/v0.4.x.md'
require "${INDEX}" 'verification/evidence/'

# INDEX remains navigation/integrity only and routes all four canonical rule books.
require "${INDEX}" 'DOCUMENTATION_RULES.md'
require "${INDEX}" 'PROJECT_PRINCIPLES.md'
require "${INDEX}" 'CHAT_RULES.md'
require "${INDEX}" 'GITHUB_PUBLICATION.md'
require "${INDEX}" 'STRATEGY_LAB_QUIC_CONTROL.md'
require "${INDEX}" 'STRATEGY_LAB_UDP_INPUT.md'

printf 'PASS: live-matrix contract follows active line %s and current candidate %s (%s) without stale version/revision pins\n' "${line}" "${candidate_tag}" "${candidate_pkg}"
