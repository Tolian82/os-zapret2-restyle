#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
GITIGNORE="${ROOT_DIR}/.gitignore"
AGENTS="${ROOT_DIR}/AGENTS.md"
DOC_RULES="${ROOT_DIR}/docs/DOCUMENTATION_RULES.md"
DEV_RULES="${ROOT_DIR}/docs/PROJECT_PRINCIPLES.md"
CHAT_RULES="${ROOT_DIR}/docs/CHAT_RULES.md"
GH_RULES="${ROOT_DIR}/docs/GITHUB_PUBLICATION.md"
START_HERE="${ROOT_DIR}/docs/START_HERE.md"
PROJECT_STATE="${ROOT_DIR}/docs/PROJECT_STATE.md"
ROADMAP="${ROOT_DIR}/docs/ROADMAP.md"
INDEX="${ROOT_DIR}/docs/INDEX.md"
CURRENT_LEDGER="${ROOT_DIR}/docs/history/current/v0.4.x.md"
ARCHIVE_01="${ROOT_DIR}/docs/history/archive/v0.1.x.md"
ARCHIVE_02="${ROOT_DIR}/docs/history/archive/v0.2.x.md"
ARCHIVE_03="${ROOT_DIR}/docs/history/archive/v0.3.x.md"
CI="${ROOT_DIR}/.github/workflows/ci.yml"

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

require_fixed()
{
    grep -Fq -- "$1" "$2" || fail "$3"
}

check_numbered_book()
{
    prefix=$1
    file=$2
    awk -v p="${prefix}" '
      BEGIN { n=0; ok=1 }
      $0 ~ "^" p "-[0-9][0-9][0-9]\\. \\*\\*" {
        n++
        id=$1
        sub("^" p "-", "", id)
        sub("\\.$", "", id)
        id=id+0
        if (id != n) ok=0
      }
      END { if (n == 0 || ok == 0) exit 1 }
    ' "${file}" || fail "${file} does not contain one continuous ${prefix}-001.. rule sequence"
}

tracked=$(git -C "${ROOT_DIR}" ls-files)
bad=$(printf '%s\n' "${tracked}" | grep -E '(^|/)([^/]+\.(orig|rej|patch|diff|b64|base64|bak)|[^/]+\.part-[0-9]+|[^/]+~)$' || true)
[ -z "${bad}" ] || {
    printf '%s\n' 'Forbidden tracked repository artifacts:' >&2
    printf '%s\n' "${bad}" >&2
    exit 1
}

for pattern in '*.orig' '*.rej' '*.patch' '*.diff' '*.b64' '*.base64' '*.bak' '*.part-*' '*~'
do
    grep -Fqx "${pattern}" "${GITIGNORE}" || fail "missing ignore rule: ${pattern}"
done

for file in \
    "${AGENTS}" "${DOC_RULES}" "${DEV_RULES}" "${CHAT_RULES}" "${GH_RULES}" \
    "${START_HERE}" "${PROJECT_STATE}" "${ROADMAP}" "${INDEX}" "${CURRENT_LEDGER}" \
    "${ARCHIVE_01}" "${ARCHIVE_02}" "${ARCHIVE_03}"
do
    test -s "${file}" || fail "required authority/memory file is missing or empty: ${file}"
done

# Exactly four canonical general rule books, each with its own numbered domain.
check_numbered_book DOC "${DOC_RULES}"
check_numbered_book DEV "${DEV_RULES}"
check_numbered_book CHAT "${CHAT_RULES}"
check_numbered_book GH "${GH_RULES}"

require_fixed 'Exactly four canonical rule books exist.' "${DOC_RULES}" 'documentation canon does not define the four-book boundary'
require_fixed 'one normative home' "${DOC_RULES}" 'documentation canon does not enforce single-home rules'
require_fixed 'Specialist technical contracts stay specialist.' "${DOC_RULES}" 'documentation canon does not protect specialist technical contracts'

# AGENTS is a bootstrap map and routes to all four books.
require_fixed 'docs/DOCUMENTATION_RULES.md' "${AGENTS}" 'AGENTS does not route to DOC rules'
require_fixed 'docs/PROJECT_PRINCIPLES.md' "${AGENTS}" 'AGENTS does not route to DEV rules'
require_fixed 'docs/CHAT_RULES.md' "${AGENTS}" 'AGENTS does not route to CHAT rules'
require_fixed 'docs/GITHUB_PUBLICATION.md' "${AGENTS}" 'AGENTS does not route to GH rules'

# START_HERE contains direct orientation links to all four books and current state.
require_fixed 'PROJECT_STATE.md' "${START_HERE}" 'START_HERE does not link current state'
require_fixed 'DOCUMENTATION_RULES.md' "${START_HERE}" 'START_HERE does not link DOC rules'
require_fixed 'PROJECT_PRINCIPLES.md' "${START_HERE}" 'START_HERE does not link DEV rules'
require_fixed 'CHAT_RULES.md' "${START_HERE}" 'START_HERE does not link CHAT rules'
require_fixed 'GITHUB_PUBLICATION.md' "${START_HERE}" 'START_HERE does not link GH rules'
require_fixed 'ROADMAP.md' "${START_HERE}" 'START_HERE does not link master plan'
require_fixed 'INDEX.md' "${START_HERE}" 'START_HERE does not link INDEX'

# INDEX independently preserves navigation integrity.
for marker in \
    DOCUMENTATION_RULES.md PROJECT_PRINCIPLES.md CHAT_RULES.md GITHUB_PUBLICATION.md \
    START_HERE.md PROJECT_STATE.md ROADMAP.md history/current/v0.4.x.md \
    history/archive/v0.1.x.md history/archive/v0.2.x.md history/archive/v0.3.x.md \
    'verification/evidence/' 'devlog/' 'patches/' 'decisions/' 'releases/'
do
    require_fixed "${marker}" "${INDEX}" "INDEX does not route to ${marker}"
done

# Current state stays factual and exposes the archive chain.
require_fixed 'State-line scope: **`v0.4.x`**' "${PROJECT_STATE}" 'PROJECT_STATE is not scoped to v0.4.x'
require_fixed 'v0.1.x archive' "${PROJECT_STATE}" 'PROJECT_STATE lacks v0.1.x archive link'
require_fixed 'v0.2.x archive' "${PROJECT_STATE}" 'PROJECT_STATE lacks v0.2.x archive link'
require_fixed 'v0.3.x archive' "${PROJECT_STATE}" 'PROJECT_STATE lacks v0.3.x archive link'

# Status roles remain explicit.
grep -Eq '^Status:[[:space:]]+\*\*CANONICAL / MANDATORY LEVEL 1\*\*$' "${DOC_RULES}" || fail 'DOC rules status is wrong'
grep -Eq '^Status:[[:space:]]+\*\*CANONICAL / MANDATORY LEVEL 1\*\*$' "${DEV_RULES}" || fail 'DEV rules status is wrong'
grep -Eq '^Status:[[:space:]]+\*\*CANONICAL / MANDATORY LEVEL 1\*\*$' "${CHAT_RULES}" || fail 'CHAT rules status is wrong'
grep -Eq '^Status:[[:space:]]+\*\*CANONICAL / MANDATORY LEVEL 1\*\*$' "${GH_RULES}" || fail 'GH rules status is wrong'
grep -Eq '^Status:[[:space:]]+\*\*AUTHORITATIVE REVISION HANDOFF / LEVEL 1\*\*$' "${START_HERE}" || fail 'START_HERE role is wrong'
grep -Eq '^Status:[[:space:]]+\*\*CURRENT SECOND-COMPONENT STATE / LEVEL 1\*\*$' "${PROJECT_STATE}" || fail 'PROJECT_STATE role is wrong'
grep -Eq '^Status:[[:space:]]+\*\*CURRENT / COMPLETE CONCISE PLAN\*\*$' "${ROADMAP}" || fail 'ROADMAP role is wrong'

require_fixed 'scripts/test-repository-hygiene.sh' "${CI}" 'repository hygiene test is not wired into CI'

echo 'Repository artifact, four-rule-book, Level-1, archive, and INDEX integrity tests passed.'
