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

# Verify durable documentation authority relationships rather than mutable prose.
for file in \
    "${AGENTS}" \
    "${PRINCIPLES}" \
    "${START_HERE}" \
    "${PROJECT_STATE}" \
    "${ROADMAP}" \
    "${INDEX}" \
    "${OPERATIONAL_DECISION}" \
    "${ACTIVE_GITHUB_DECISION}" \
    "${OLD_GITHUB_DECISION}"
do
    test -s "${file}" || fail "required project authority is missing or empty: ${file}"
done

grep -Fq 'docs/PROJECT_PRINCIPLES.md' "${AGENTS}" || \
    fail 'AGENTS does not require canonical project principles'
grep -Fq 'docs/START_HERE.md' "${AGENTS}" || \
    fail 'AGENTS does not route to operational handoff'
grep -Fq 'docs/PROJECT_STATE.md' "${AGENTS}" || \
    fail 'AGENTS does not route to current project state'
grep -Fq 'docs/PROJECT_PRINCIPLES.md' "${START_HERE}" || \
    fail 'operational handoff does not route to canonical project principles'
grep -Fq 'docs/PROJECT_PRINCIPLES.md' "${PROJECT_STATE}" || \
    fail 'project state does not reference canonical project principles'
grep -Fq 'docs/PROJECT_PRINCIPLES.md' "${ROADMAP}" || \
    fail 'roadmap does not reference canonical project principles'
grep -Fq 'docs/PROJECT_PRINCIPLES.md' "${INDEX}" || \
    fail 'Engineering Memory index does not route to canonical project principles'
grep -Fq 'docs/START_HERE.md' "${INDEX}" || \
    fail 'Engineering Memory index does not route to operational handoff'

grep -Eq '^Status:[[:space:]]+\*\*CANONICAL / MANDATORY READING IN EVERY PROJECT CONTEXT\*\*$' "${PRINCIPLES}" || \
    fail 'project principles are not marked canonical mandatory reading'
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

echo 'Repository artifact and documentation authority hygiene tests passed.'
