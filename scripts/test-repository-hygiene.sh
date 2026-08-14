#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
GITIGNORE="${ROOT_DIR}/.gitignore"
CI="${ROOT_DIR}/.github/workflows/ci.yml"
AGENTS="${ROOT_DIR}/AGENTS.md"
PRINCIPLES="${ROOT_DIR}/docs/PROJECT_PRINCIPLES.md"
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

# Verify durable documentation authority relationships under the three-level memory model rather than
# requiring every Level-1 role document to repeat links owned by AGENTS/START_HERE/INDEX.
for file in \
    "${AGENTS}" \
    "${PRINCIPLES}" \
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

grep -Fq 'docs/PROJECT_PRINCIPLES.md' "${AGENTS}" || \
    fail 'AGENTS does not require canonical project principles'
grep -Fq 'docs/START_HERE.md' "${AGENTS}" || \
    fail 'AGENTS does not route to operational handoff'
grep -Fq 'docs/PROJECT_STATE.md' "${AGENTS}" || \
    fail 'AGENTS does not route to current project state'
grep -Fq 'docs/PROJECT_PRINCIPLES.md' "${START_HERE}" || \
    fail 'operational handoff does not route to canonical project principles'

grep -Fq 'PROJECT_PRINCIPLES.md' "${INDEX}" || \
    fail 'Engineering Memory index does not route to canonical project principles'
grep -Fq 'START_HERE.md' "${INDEX}" || \
    fail 'Engineering Memory index does not route to operational handoff'
grep -Fq 'PROJECT_STATE.md' "${INDEX}" || \
    fail 'Engineering Memory index does not route to current project state'
grep -Fq 'history/current/v0.4.x.md' "${INDEX}" || \
    fail 'Engineering Memory index does not route to the current semantic-line ledger'
grep -Fq 'history/archive/v0.1.x.md' "${INDEX}" || \
    fail 'Engineering Memory index does not route to the v0.1.x archive'
grep -Fq 'history/archive/v0.2.x.md' "${INDEX}" || \
    fail 'Engineering Memory index does not route to the v0.2.x archive'
grep -Fq 'history/archive/v0.3.x.md' "${INDEX}" || \
    fail 'Engineering Memory index does not route to the v0.3.x archive'

grep -Eq '^Status:[[:space:]]+\*\*CANONICAL / MANDATORY READING IN EVERY PROJECT CONTEXT\*\*$' "${PRINCIPLES}" || \
    fail 'project principles are not marked canonical mandatory reading'
grep -Eq '^Status:[[:space:]]+\*\*AUTHORITATIVE OPERATIONAL HANDOFF / LEVEL 1\*\*$' "${START_HERE}" || \
    fail 'operational handoff is not marked Level 1 authoritative'
grep -Eq '^Status:[[:space:]]+\*\*CURRENT / LEVEL 1\*\*$' "${PROJECT_STATE}" || \
    fail 'project state is not marked current Level 1'
grep -Eq '^Status:[[:space:]]+\*\*CURRENT / FORWARD-LOOKING\*\*$' "${ROADMAP}" || \
    fail 'roadmap is not marked current forward-looking'
grep -Eq '^Status:[[:space:]]+\*\*CURRENT / LEVEL 2 / READ WHEN CURRENT-LINE DETAIL IS NEEDED\*\*$' "${CURRENT_LEDGER}" || \
    fail 'current semantic-line ledger is not marked Level 2 on-demand'
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

grep -Eq 'Historical( delivery)? record' "${ROOT_DIR}/docs/audit/DIAG-001-strategy-lab.md" || \
    fail 'historical DIAG record has no authority banner'
grep -Fq 'scripts/test-repository-hygiene.sh' "${CI}" || \
    fail 'repository hygiene test is not wired into CI'

echo 'Repository artifact and three-level documentation authority hygiene tests passed.'
