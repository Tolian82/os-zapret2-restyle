#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
GITIGNORE="${ROOT_DIR}/.gitignore"
CI="${ROOT_DIR}/.github/workflows/ci.yml"
PROJECT_STATE="${ROOT_DIR}/docs/PROJECT_STATE.md"
INDEX="${ROOT_DIR}/docs/INDEX.md"
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

# Verify durable authority relationships instead of exact mutable prose.
test -s "${PROJECT_STATE}" || fail 'current project state is missing'
test -s "${ACTIVE_GITHUB_DECISION}" || fail 'active GitHub delivery decision is missing'
test -s "${OLD_GITHUB_DECISION}" || fail 'superseded GitHub decision record is missing'

grep -Fq 'docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md' "${PROJECT_STATE}" || \
    fail 'project state does not name the current Strategy Lab authority'
grep -Fq 'DEC-2026-08-05-efficient-github-delivery.md' "${PROJECT_STATE}" || \
    fail 'project state does not name the active GitHub delivery authority'
grep -Eq '^Status:[[:space:]]+Active$' "${ACTIVE_GITHUB_DECISION}" || \
    fail 'new GitHub delivery decision is not active'
grep -Eq '^Status:[[:space:]]+Superseded' "${OLD_GITHUB_DECISION}" || \
    fail 'old atomic GitHub decision is not marked superseded'
grep -Fq 'DEC-2026-08-05-efficient-github-delivery.md' "${INDEX}" || \
    fail 'Engineering Memory index does not route to the active GitHub decision'
grep -Eq 'Historical( delivery)? record' "${ROOT_DIR}/docs/audit/DIAG-001-strategy-lab.md" || \
    fail 'historical DIAG record has no authority banner'
grep -Fq 'scripts/test-repository-hygiene.sh' "${CI}" || \
    fail 'repository hygiene test is not wired into CI'

echo 'Repository artifact and documentation authority hygiene tests passed.'
