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
GH_POINTER="${ROOT_DIR}/docs/GITHUB_WORKFLOW.md"
DEV_POINTER="${ROOT_DIR}/docs/DEVELOPMENT_GUIDE.md"
WORK_POINTER="${ROOT_DIR}/docs/WORKING_CONVENTIONS.md"
XREF_TEST="${ROOT_DIR}/scripts/test-rule-cross-references.py"
CURRENT_LEDGER="${ROOT_DIR}/docs/history/current/v0.4.x.md"
RULE_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-14-rule-cross-reference-integrity.md"
ARCHIVE_01="${ROOT_DIR}/docs/history/archive/v0.1.x.md"
ARCHIVE_02="${ROOT_DIR}/docs/history/archive/v0.2.x.md"
ARCHIVE_03="${ROOT_DIR}/docs/history/archive/v0.3.x.md"
CI="${ROOT_DIR}/.github/workflows/ci.yml"

fail(){ echo "FAIL: $*" >&2; exit 1; }
require_fixed(){ grep -Fq -- "$1" "$2" || fail "$3"; }

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
    "${RULE_DECISION}" "${ARCHIVE_01}" "${ARCHIVE_02}" "${ARCHIVE_03}" "${GH_POINTER}" \
    "${DEV_POINTER}" "${WORK_POINTER}" "${XREF_TEST}"
do
    test -s "${file}" || fail "required documentation/integrity file is missing: ${file}"
done

python3 "${XREF_TEST}"
for file in "${DOC_RULES}" "${DEV_RULES}" "${CHAT_RULES}" "${GH_RULES}"
do
    require_fixed 'RULE-XREF-OUT-BEGIN' "${file}" "missing outbound rule registry in ${file}"
    require_fixed 'RULE-XREF-IN-BEGIN' "${file}" "missing inbound rule registry in ${file}"
done

require_fixed 'DOC-006.' "${DOC_RULES}" 'persistent rule-ID contract is missing'
require_fixed 'DOC-042.' "${DOC_RULES}" 'cross-reference registry rule is missing'
require_fixed 'DOC-045.' "${DOC_RULES}" 'cross-reference CI rule is missing'
require_fixed 'DOC-046.' "${DOC_RULES}" 'clean Markdown rule is missing'
require_fixed 'DOC-047.' "${DOC_RULES}" 'GitHub documentation-impact rule is missing'
require_fixed 'DOC-048.' "${DOC_RULES}" 'compatibility-pointer rule is missing'
require_fixed 'DOC-049.' "${DOC_RULES}" 'repository-state-scoped reading rule is missing'
require_fixed 'DEV-001.' "${DEV_RULES}" 'owner-canon rule is missing'
require_fixed 'DEV-046.' "${DEV_RULES}" 'development-rule reconciliation rule is missing'
require_fixed 'CHAT-008.' "${CHAT_RULES}" 'Stop rule is missing'
require_fixed 'CHAT-011.' "${CHAT_RULES}" 'explicit read-only boundary rule is missing'
require_fixed 'CHAT-026.' "${CHAT_RULES}" 'owner instruction consequence rule is missing'
require_fixed 'GH-057.' "${GH_RULES}" 'tree consistency rule is missing'
require_fixed 'GH-058.' "${GH_RULES}" 'rule cross-reference merge gate is missing'

require_fixed 'docs/START_HERE.md' "${AGENTS}" 'AGENTS does not route to START_HERE'
require_fixed 'docs/PROJECT_STATE.md' "${AGENTS}" 'AGENTS does not route to PROJECT_STATE'
require_fixed 'docs/DOCUMENTATION_RULES.md' "${AGENTS}" 'AGENTS does not route to DOC rules'
require_fixed 'docs/PROJECT_PRINCIPLES.md' "${AGENTS}" 'AGENTS does not route to DEV rules'
require_fixed 'docs/CHAT_RULES.md' "${AGENTS}" 'AGENTS does not route to CHAT rules'
require_fixed 'docs/GITHUB_PUBLICATION.md' "${AGENTS}" 'AGENTS does not route to GH rules'

for marker in PROJECT_STATE.md DOCUMENTATION_RULES.md PROJECT_PRINCIPLES.md CHAT_RULES.md GITHUB_PUBLICATION.md ROADMAP.md INDEX.md
do
    require_fixed "${marker}" "${START_HERE}" "START_HERE does not expose ${marker}"
done

for marker in \
    DOCUMENTATION_RULES.md PROJECT_PRINCIPLES.md CHAT_RULES.md GITHUB_PUBLICATION.md \
    START_HERE.md PROJECT_STATE.md ROADMAP.md history/current/v0.4.x.md \
    GITHUB_WORKFLOW.md DEVELOPMENT_GUIDE.md WORKING_CONVENTIONS.md \
    history/archive/v0.1.x.md history/archive/v0.2.x.md history/archive/v0.3.x.md \
    'verification/evidence/' 'devlog/' 'patches/' 'decisions/' 'releases/'
do
    require_fixed "${marker}" "${INDEX}" "INDEX does not route to ${marker}"
done
require_fixed 'Compatibility pointers — not active authority' "${INDEX}" 'INDEX does not isolate legacy pointers'

for pointer in "${GH_POINTER}" "${DEV_POINTER}" "${WORK_POINTER}"
do
    require_fixed 'LEGACY COMPATIBILITY POINTER' "${pointer}" "legacy pointer has wrong status: ${pointer}"
    require_fixed 'DOC-048' "${pointer}" "legacy pointer does not bind itself to DOC-048: ${pointer}"
done

for file in \
    "${AGENTS}" "${DOC_RULES}" "${DEV_RULES}" "${CHAT_RULES}" "${GH_RULES}" \
    "${START_HERE}" "${PROJECT_STATE}" "${ROADMAP}" "${INDEX}" "${CURRENT_LEDGER}" \
    "${RULE_DECISION}" "${GH_POINTER}" "${DEV_POINTER}" "${WORK_POINTER}"
do
    if grep -Eq '^={8,}$' "${file}"; then
        fail "decorative equals-sign banner remains in current/active documentation: ${file}"
    fi
    if grep -nE '[[:blank:]]+$' "${file}" >/dev/null; then
        echo "Trailing whitespace in current/active documentation: ${file}" >&2
        grep -nE '[[:blank:]]+$' "${file}" >&2 || true
        exit 1
    fi
done

require_fixed 'State-line scope: **`v0.4.x`**' "${PROJECT_STATE}" 'PROJECT_STATE is not scoped to v0.4.x'
require_fixed 'v0.1.x archive' "${PROJECT_STATE}" 'PROJECT_STATE lacks v0.1.x archive link'
require_fixed 'v0.2.x archive' "${PROJECT_STATE}" 'PROJECT_STATE lacks v0.2.x archive link'
require_fixed 'v0.3.x archive' "${PROJECT_STATE}" 'PROJECT_STATE lacks v0.3.x archive link'

require_fixed 'scripts/test-repository-hygiene.sh' "${CI}" 'repository hygiene test is not wired into CI'

echo 'Repository artifact, four-rule-book, cross-reference, Level-1, compatibility, archive, style, whitespace, and INDEX integrity tests passed.'
