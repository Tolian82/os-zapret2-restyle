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
XREF_TEST="${ROOT_DIR}/scripts/test-rule-cross-references.py"
LINK_TEST="${ROOT_DIR}/scripts/test-markdown-links.py"
VERSION_FILE="${ROOT_DIR}/VERSION"
RULE_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-14-rule-cross-reference-integrity.md"
LIFECYCLE_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-14-rule-lifecycle-and-link-integrity.md"
MEMORY_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-14-three-level-versioned-documentation-memory.md"
ARCHIVE_01="${ROOT_DIR}/docs/history/archive/v0.1.x.md"
ARCHIVE_02="${ROOT_DIR}/docs/history/archive/v0.2.x.md"
ARCHIVE_03="${ROOT_DIR}/docs/history/archive/v0.3.x.md"
ARCHIVE_04="${ROOT_DIR}/docs/history/archive/v0.4.x.md"
CI="${ROOT_DIR}/.github/workflows/ci.yml"

fail(){ echo "FAIL: $*" >&2; exit 1; }
require_fixed(){ grep -Fq -- "$1" "$2" || fail "$3"; }

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
case "${version}" in *.*.*) ;; *) fail 'invalid project version' ;; esac
major=$(printf '%s\n' "${version}" | cut -d. -f1)
second=$(printf '%s\n' "${version}" | cut -d. -f2)
current_line="v${major}.${second}.x"
CURRENT_LEDGER="${ROOT_DIR}/docs/history/current/${current_line}.md"

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
    "${RULE_DECISION}" "${LIFECYCLE_DECISION}" "${MEMORY_DECISION}" \
    "${ARCHIVE_01}" "${ARCHIVE_02}" "${ARCHIVE_03}" "${XREF_TEST}" "${LINK_TEST}"
do
    test -s "${file}" || fail "required documentation/integrity file is missing: ${file}"
done

# v0.4.x is the first line using the final-state archive model and must be retained once
# the active line advances beyond it.
if [ "${major}" -gt 0 ] 2>/dev/null || [ "${second}" -ge 5 ] 2>/dev/null; then
    test -s "${ARCHIVE_04}" || fail "required completed v0.4.x archive is missing: ${ARCHIVE_04}"
fi

for removed in \
    "${ROOT_DIR}/docs/GITHUB_WORKFLOW.md" \
    "${ROOT_DIR}/docs/DEVELOPMENT_GUIDE.md" \
    "${ROOT_DIR}/docs/WORKING_CONVENTIONS.md"
do
    test ! -e "${removed}" || fail "obsolete duplicate quick-reference file still exists: ${removed}"
done

python3 "${XREF_TEST}"
python3 "${LINK_TEST}"

for file in "${DOC_RULES}" "${DEV_RULES}" "${CHAT_RULES}" "${GH_RULES}"
do
    require_fixed 'RULE-XREF-OUT-BEGIN' "${file}" "missing outbound rule registry in ${file}"
    require_fixed 'RULE-XREF-IN-BEGIN' "${file}" "missing inbound rule registry in ${file}"
done

require_fixed 'DOC-006.' "${DOC_RULES}" 'permanent rule-ID contract is missing'
require_fixed 'DOC-014. **[ОТМЕНЕНО]' "${DOC_RULES}" 'cancelled DOC-014 lifecycle marker is missing'
require_fixed 'DOC-024.' "${DOC_RULES}" 'current-work documentation flow is missing'
require_fixed 'START_HERE -> PROJECT_STATE -> archive' "${DOC_RULES}" 'current-work documentation flow is not explicit'
require_fixed 'DOC-031.' "${DOC_RULES}" 'roadmap commitment rule is missing'
require_fixed 'DOC-036.' "${DOC_RULES}" 'documentation reconciliation rule is missing'
require_fixed 'DOC-042.' "${DOC_RULES}" 'cross-reference registry rule is missing'
require_fixed 'DOC-045.' "${DOC_RULES}" 'cross-reference CI rule is missing'
require_fixed 'DOC-046.' "${DOC_RULES}" 'clean Markdown rule is missing'
require_fixed 'DOC-047.' "${DOC_RULES}" 'GitHub documentation-impact rule is missing'
require_fixed 'DOC-048. **[ОТМЕНЕНО]' "${DOC_RULES}" 'cancelled compatibility-pointer rule marker is missing'
require_fixed 'DOC-049.' "${DOC_RULES}" 'repository-state-scoped reading rule is missing'
require_fixed 'DOC-050.' "${DOC_RULES}" 'cancelled/replaced rule retention contract is missing'
require_fixed 'DOC-052.' "${DOC_RULES}" 'rule lifecycle validation contract is missing'
require_fixed 'DOC-053.' "${DOC_RULES}" 'Markdown link integrity rule is missing'
require_fixed 'DOC-054.' "${DOC_RULES}" 'rule lifecycle decision criteria are missing'
require_fixed 'DEV-001.' "${DEV_RULES}" 'owner-canon rule is missing'
require_fixed 'DEV-046.' "${DEV_RULES}" 'development-rule reconciliation rule is missing'
require_fixed '## Rule lifecycle' "${DEV_RULES}" 'development rule lifecycle section is not normalized'
require_fixed 'CHAT-001.' "${CHAT_RULES}" 'owner-facing Russian-language rule is missing'
require_fixed 'Build owner-facing explanations as Russian sentences.' "${CHAT_RULES}" 'Russian-sentence communication contract is missing'
require_fixed 'CHAT-008.' "${CHAT_RULES}" 'Stop rule is missing'
require_fixed 'CHAT-011.' "${CHAT_RULES}" 'explicit read-only boundary rule is missing'
require_fixed 'automatically impose read-only mode is explicitly cancelled' "${CHAT_RULES}" 'old automatic read-only interpretation is not explicitly cancelled'
require_fixed 'CHAT-026.' "${CHAT_RULES}" 'owner instruction consequence rule is missing'
require_fixed 'GH-009. **[ОТМЕНЕНО]' "${GH_RULES}" 'cancelled broad GitHub reconciliation rule is missing'
require_fixed 'GH-016.' "${GH_RULES}" 'scope-proportionate CI rule is missing'
require_fixed 'GH-027.' "${GH_RULES}" 'forward-only release identity rule is missing'
require_fixed 'GH-057.' "${GH_RULES}" 'tree consistency rule is missing'
require_fixed 'GH-058.' "${GH_RULES}" 'rule cross-reference merge gate is missing'
require_fixed 'GH-059.' "${GH_RULES}" 'documentation deletion/reference migration rule is missing'

require_fixed 'docs/START_HERE.md' "${AGENTS}" 'AGENTS does not route to START_HERE'
require_fixed 'docs/PROJECT_STATE.md' "${AGENTS}" 'AGENTS does not route to PROJECT_STATE'
require_fixed 'docs/DOCUMENTATION_RULES.md' "${AGENTS}" 'AGENTS does not route to DOC rules'
require_fixed 'docs/PROJECT_PRINCIPLES.md' "${AGENTS}" 'AGENTS does not route to DEV rules'
require_fixed 'docs/CHAT_RULES.md' "${AGENTS}" 'AGENTS does not route to CHAT rules'
require_fixed 'docs/GITHUB_PUBLICATION.md' "${AGENTS}" 'AGENTS does not route to GH rules'
require_fixed 'START_HERE.md -> PROJECT_STATE.md -> version-line archive' "${AGENTS}" 'AGENTS does not explain the current-work documentation flow'

for marker in PROJECT_STATE.md DOCUMENTATION_RULES.md PROJECT_PRINCIPLES.md CHAT_RULES.md GITHUB_PUBLICATION.md ROADMAP.md INDEX.md
do
    require_fixed "${marker}" "${START_HERE}" "START_HERE does not expose ${marker}"
done

for marker in \
    DOCUMENTATION_RULES.md PROJECT_PRINCIPLES.md CHAT_RULES.md GITHUB_PUBLICATION.md \
    START_HERE.md PROJECT_STATE.md ROADMAP.md "history/current/${current_line}.md" \
    history/archive/v0.1.x.md history/archive/v0.2.x.md history/archive/v0.3.x.md \
    'verification/evidence/' 'devlog/' 'patches/' 'decisions/' 'releases/'
do
    require_fixed "${marker}" "${INDEX}" "INDEX does not route to ${marker}"
done

if [ "${major}" -gt 0 ] 2>/dev/null || [ "${second}" -ge 5 ] 2>/dev/null; then
    require_fixed 'history/archive/v0.4.x.md' "${INDEX}" 'INDEX does not route to completed v0.4.x archive'
fi

for file in \
    "${AGENTS}" "${DOC_RULES}" "${DEV_RULES}" "${CHAT_RULES}" "${GH_RULES}" \
    "${START_HERE}" "${PROJECT_STATE}" "${ROADMAP}" "${INDEX}" "${CURRENT_LEDGER}" \
    "${RULE_DECISION}" "${LIFECYCLE_DECISION}" "${MEMORY_DECISION}"
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

require_fixed "State-line scope: **\`${current_line}\`**" "${PROJECT_STATE}" "PROJECT_STATE is not scoped to ${current_line}"
require_fixed 'START_HERE -> PROJECT_STATE -> version-line archive' "${PROJECT_STATE}" 'PROJECT_STATE does not record the current-work state-flow'
require_fixed 'v0.1.x archive' "${PROJECT_STATE}" 'PROJECT_STATE lacks v0.1.x archive link'
require_fixed 'v0.2.x archive' "${PROJECT_STATE}" 'PROJECT_STATE lacks v0.2.x archive link'
require_fixed 'v0.3.x archive' "${PROJECT_STATE}" 'PROJECT_STATE lacks v0.3.x archive link'
if [ "${major}" -gt 0 ] 2>/dev/null || [ "${second}" -ge 5 ] 2>/dev/null; then
    require_fixed 'v0.4.x archive' "${PROJECT_STATE}" 'PROJECT_STATE lacks v0.4.x archive link'
fi
require_fixed 'AGENTS -> START_HERE -> PROJECT_STATE' "${LIFECYCLE_DECISION}" 'context-first cold-start decision is missing'
require_fixed 'docs_only: ${{ steps.paths.outputs.docs_only }}' "${CI}" 'CI docs-only classifier output is missing'
require_fixed 'name: Validate documentation' "${CI}" 'focused documentation CI job is missing'
require_fixed 'scripts/test-repository-hygiene.sh' "${CI}" 'repository hygiene test is not wired into CI'

echo "Repository artifact, four-rule-book, rule lifecycle, current-work flow (${current_line}), scoped CI, cross-reference, Level-1, archive, style, whitespace, Markdown-link, and INDEX integrity tests passed."
