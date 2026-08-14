#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
GITIGNORE="${ROOT_DIR}/.gitignore"
CI="${ROOT_DIR}/.github/workflows/ci.yml"
AGENTS="${ROOT_DIR}/AGENTS.md"
PRINCIPLES="${ROOT_DIR}/docs/PROJECT_PRINCIPLES.md"
DOC_RULES="${ROOT_DIR}/docs/DOCUMENTATION_RULES.md"
START_HERE="${ROOT_DIR}/docs/START_HERE.md"
PROJECT_STATE="${ROOT_DIR}/docs/PROJECT_STATE.md"
ROADMAP="${ROOT_DIR}/docs/ROADMAP.md"
INDEX="${ROOT_DIR}/docs/INDEX.md"
CURRENT_LEDGER="${ROOT_DIR}/docs/history/current/v0.4.x.md"
ARCHIVE_01="${ROOT_DIR}/docs/history/archive/v0.1.x.md"
ARCHIVE_02="${ROOT_DIR}/docs/history/archive/v0.2.x.md"
ARCHIVE_03="${ROOT_DIR}/docs/history/archive/v0.3.x.md"
MEMORY_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-14-three-level-versioned-documentation-memory.md"
OPERATIONAL_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-14-operational-handoff-and-scope-first-preflight.md"
ACTIVE_GITHUB_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-05-efficient-github-delivery.md"
OLD_GITHUB_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-02-atomic-github-publication.md"

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

tracked=$(git -C "${ROOT_DIR}" ls-files)
bad=$(printf '%s\n' "${tracked}" | grep -E '(^|/)([^/]+\.(orig|rej|patch|diff|b64|base64|bak)|[^/]+\.part-[0-9]+|[^/]+~)$' || true)
[ -z "${bad}" ] || {
    printf '%s\n' 'Forbidden tracked repository artifacts:' >&2
    printf '%s\n' "${bad}" >&2
    exit 1
}

[ ! -e "${ROOT_DIR}/docs/PROJECT_STATE.md.orig" ] || fail 'stale PROJECT_STATE backup exists'

for pattern in '*.orig' '*.rej' '*.patch' '*.diff' '*.b64' '*.base64' '*.bak' '*.part-*' '*~'
do
    grep -Fqx "${pattern}" "${GITIGNORE}" || fail "missing ignore rule: ${pattern}"
done

# Verify durable authority/navigation relationships under the version-aware three-level memory model.
for file in \
    "${AGENTS}" \
    "${PRINCIPLES}" \
    "${DOC_RULES}" \
    "${START_HERE}" \
    "${PROJECT_STATE}" \
    "${ROADMAP}" \
    "${INDEX}" \
    "${CURRENT_LEDGER}" \
    "${ARCHIVE_01}" \
    "${ARCHIVE_02}" \
    "${ARCHIVE_03}" \
    "${MEMORY_DECISION}" \
    "${OPERATIONAL_DECISION}" \
    "${ACTIVE_GITHUB_DECISION}" \
    "${OLD_GITHUB_DECISION}"
do
    test -s "${file}" || fail "required project authority/memory file is missing or empty: ${file}"
done

# Mandatory Level-1 routes.
grep -Fq 'docs/PROJECT_PRINCIPLES.md' "${AGENTS}" || \
    fail 'AGENTS does not require canonical project principles'
grep -Fq 'docs/DOCUMENTATION_RULES.md' "${AGENTS}" || \
    fail 'AGENTS does not require canonical documentation rules'
grep -Fq 'docs/START_HERE.md' "${AGENTS}" || \
    fail 'AGENTS does not route to revision handoff'
grep -Fq 'docs/PROJECT_STATE.md' "${AGENTS}" || \
    fail 'AGENTS does not route to current project state'

grep -Fq 'PROJECT_STATE.md' "${START_HERE}" || \
    fail 'START_HERE does not route first to PROJECT_STATE'
grep -Fq 'DOCUMENTATION_RULES.md' "${START_HERE}" || \
    fail 'START_HERE does not route to canonical documentation rules'
grep -Fq 'PROJECT_PRINCIPLES.md' "${START_HERE}" || \
    fail 'START_HERE does not route to canonical project principles'
grep -Fq 'GITHUB_PUBLICATION.md' "${START_HERE}" || \
    fail 'START_HERE does not route to GitHub publication procedure'
grep -Fq 'ROADMAP.md' "${START_HERE}" || \
    fail 'START_HERE does not route to master development plan'
grep -Fq 'INDEX.md' "${START_HERE}" || \
    fail 'START_HERE does not route to documentation index'

# INDEX remains the global navigation/integrity map.
grep -Fq 'PROJECT_PRINCIPLES.md' "${INDEX}" || \
    fail 'Engineering Memory index does not route to canonical project principles'
grep -Fq 'DOCUMENTATION_RULES.md' "${INDEX}" || \
    fail 'Engineering Memory index does not route to documentation rules'
grep -Fq 'START_HERE.md' "${INDEX}" || \
    fail 'Engineering Memory index does not route to revision handoff'
grep -Fq 'PROJECT_STATE.md' "${INDEX}" || \
    fail 'Engineering Memory index does not route to current project state'
grep -Fq 'ROADMAP.md' "${INDEX}" || \
    fail 'Engineering Memory index does not route to master plan'
grep -Fq 'history/current/v0.4.x.md' "${INDEX}" || \
    fail 'Engineering Memory index does not route to current v0.4.x ledger'
grep -Fq 'history/archive/v0.1.x.md' "${INDEX}" || \
    fail 'Engineering Memory index does not route to the v0.1.x archive'
grep -Fq 'history/archive/v0.2.x.md' "${INDEX}" || \
    fail 'Engineering Memory index does not route to the v0.2.x archive'
grep -Fq 'history/archive/v0.3.x.md' "${INDEX}" || \
    fail 'Engineering Memory index does not route to the v0.3.x archive'

# Current role/status contracts.
grep -Eq '^Status:[[:space:]]+\*\*CANONICAL / MANDATORY READING IN EVERY PROJECT CONTEXT\*\*$' "${PRINCIPLES}" || \
    fail 'project principles are not marked canonical mandatory reading'
grep -Eq '^Status:[[:space:]]+\*\*CANONICAL / MANDATORY LEVEL 1\*\*$' "${DOC_RULES}" || \
    fail 'documentation rules are not marked canonical mandatory Level 1'
grep -Eq '^Status:[[:space:]]+\*\*AUTHORITATIVE REVISION HANDOFF / LEVEL 1\*\*$' "${START_HERE}" || \
    fail 'START_HERE is not marked authoritative revision handoff'
grep -Eq '^Status:[[:space:]]+\*\*CURRENT SECOND-COMPONENT STATE / LEVEL 1\*\*$' "${PROJECT_STATE}" || \
    fail 'PROJECT_STATE is not marked current second-component state'
grep -Eq '^Status:[[:space:]]+\*\*CURRENT / COMPLETE CONCISE PLAN\*\*$' "${ROADMAP}" || \
    fail 'ROADMAP is not marked complete concise master plan'
grep -Eq '^Status:[[:space:]]+\*\*CURRENT / LEVEL 2 / READ WHEN CURRENT-LINE DETAIL IS NEEDED\*\*$' "${CURRENT_LEDGER}" || \
    fail 'current v0.4.x ledger is not marked Level 2 on-demand'
grep -Eq '^Status:[[:space:]]+\*\*ARCHIVED / LEVEL 3 / READ ON DEMAND\*\*$' "${ARCHIVE_01}" || \
    fail 'v0.1.x archive is not marked Level 3 on-demand'
grep -Eq '^Status:[[:space:]]+\*\*ARCHIVED / LEVEL 3 / READ ON DEMAND\*\*$' "${ARCHIVE_02}" || \
    fail 'v0.2.x archive is not marked Level 3 on-demand'
grep -Eq '^Status:[[:space:]]+\*\*ARCHIVED / LEVEL 3 / READ ON DEMAND\*\*$' "${ARCHIVE_03}" || \
    fail 'v0.3.x archive is not marked Level 3 on-demand'
grep -Eq '^Status:[[:space:]]+\*\*ACTIVE / SUPERSEDING' "${MEMORY_DECISION}" || \
    fail 'three-level memory decision is not active/superseding'
grep -Eq '^Status:[[:space:]]+\*\*ACTIVE\*\*$' "${OPERATIONAL_DECISION}" || \
    fail 'operational handoff decision is not active'
grep -Eq '^Status:[[:space:]]+Active([,[:space:]].*)?$' "${ACTIVE_GITHUB_DECISION}" || \
    fail 'active GitHub delivery decision is not active'
grep -Eq '^Status:[[:space:]]+Superseded' "${OLD_GITHUB_DECISION}" || \
    fail 'old atomic GitHub decision is not marked superseded'

# State/archive and numbered-canon hygiene.
grep -Fq 'State-line scope: **`v0.4.x`**' "${PROJECT_STATE}" || \
    fail 'PROJECT_STATE is not scoped to the current second-component line'
grep -Fq 'v0.1.x archive' "${PROJECT_STATE}" || fail 'PROJECT_STATE lacks v0.1.x archive link'
grep -Fq 'v0.2.x archive' "${PROJECT_STATE}" || fail 'PROJECT_STATE lacks v0.2.x archive link'
grep -Fq 'v0.3.x archive' "${PROJECT_STATE}" || fail 'PROJECT_STATE lacks v0.3.x archive link'
rule_count=$(grep -Ec '^[0-9]+\. \*\*' "${DOC_RULES}")
[ "${rule_count}" -ge 50 ] || fail 'numbered documentation canon is incomplete'

grep -Eq 'Historical( delivery)? record' "${ROOT_DIR}/docs/audit/DIAG-001-strategy-lab.md" || \
    fail 'historical DIAG record has no authority banner'
grep -Fq 'scripts/test-repository-hygiene.sh' "${CI}" || \
    fail 'repository hygiene test is not wired into CI'

echo 'Repository artifact and version-aware documentation authority hygiene tests passed.'
