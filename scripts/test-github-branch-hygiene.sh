#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
AGENTS="${ROOT_DIR}/AGENTS.md"
PRINCIPLES="${ROOT_DIR}/docs/PROJECT_PRINCIPLES.md"
START_HERE="${ROOT_DIR}/docs/START_HERE.md"
INDEX="${ROOT_DIR}/docs/INDEX.md"
PUBLICATION="${ROOT_DIR}/docs/GITHUB_PUBLICATION.md"
WORKFLOW_SUMMARY="${ROOT_DIR}/docs/GITHUB_WORKFLOW.md"
OPERATIONAL_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-14-operational-handoff-and-scope-first-preflight.md"
EVIDENCE_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md"
EFFICIENT_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-05-efficient-github-delivery.md"
TITLE_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md"
OLD_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-02-atomic-github-publication.md"
CI="${ROOT_DIR}/.github/workflows/ci.yml"
TITLE_WORKFLOW="${ROOT_DIR}/.github/workflows/pr-title.yml"
CLEANUP_WORKFLOW="${ROOT_DIR}/.github/workflows/cleanup-merged-branch.yml"
PRERELEASE_WORKFLOW="${ROOT_DIR}/.github/workflows/publish-prerelease.yml"
RELEASE_TRIGGER="${ROOT_DIR}/.github/workflows/release-trigger.yml"
MAKEFILE="${ROOT_DIR}/Makefile"
VERSION_FILE="${ROOT_DIR}/VERSION"

fail()
{
  echo "FAIL: $*" >&2
  exit 1
}

require_fixed()
{
  pattern=$1
  file=$2
  description=$3
  grep -Fq -- "${pattern}" "${file}" || fail "${description}"
}

require_doc_marker()
{
  pattern=$1
  file=$2
  description=$3
  grep -Fiq -- "${pattern}" "${file}" || fail "${description}"
}

for file in \
  "${AGENTS}" \
  "${PRINCIPLES}" \
  "${START_HERE}" \
  "${INDEX}" \
  "${PUBLICATION}" \
  "${WORKFLOW_SUMMARY}" \
  "${OPERATIONAL_DECISION}" \
  "${EVIDENCE_DECISION}" \
  "${EFFICIENT_DECISION}" \
  "${TITLE_DECISION}" \
  "${OLD_DECISION}" \
  "${CI}" \
  "${TITLE_WORKFLOW}" \
  "${CLEANUP_WORKFLOW}" \
  "${PRERELEASE_WORKFLOW}" \
  "${RELEASE_TRIGGER}"
do
  test -s "${file}" || fail "missing or empty GitHub governance file: ${file}"
done

# Documentation checks guard authority relationships and required semantics, not mutable line placement.
version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(sed -n 's/^PLUGIN_REVISION=[[:space:]]*//p' "${MAKEFILE}" | head -1)

printf '%s\n' "${version}" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' || fail 'VERSION is invalid'
printf '%s\n' "${revision}" | grep -Eq '^[0-9]+$' || fail 'PLUGIN_REVISION is invalid'

expected="v${version}"
if [ -n "${revision}" ] && [ "${revision}" != "0" ]; then
  expected="${expected}_${revision}"
fi

grep -Eq '^Status:[[:space:]]+\*\*ACTIVE\*\*$' "${OPERATIONAL_DECISION}" || fail 'operational handoff decision is not active'
grep -Eq '^Status:[[:space:]]+Active([,[:space:]].*)?$' "${EVIDENCE_DECISION}" || fail 'evidence-first decision is not active'
grep -Eq '^Status:[[:space:]]+Active([,[:space:]].*)?$' "${EFFICIENT_DECISION}" || fail 'efficient delivery decision is not active'
grep -Eq '^Status:[[:space:]]+Active([,[:space:]].*)?$' "${TITLE_DECISION}" || fail 'universal title decision is not active'
grep -Eq '^Status:[[:space:]]+Superseded' "${OLD_DECISION}" || fail 'old atomic decision is not superseded'

require_doc_marker 'docs/PROJECT_PRINCIPLES.md' "${AGENTS}" 'AGENTS does not require canonical project principles'
require_doc_marker 'docs/START_HERE.md' "${AGENTS}" 'AGENTS does not require operational handoff'
require_doc_marker 'docs/GITHUB_PUBLICATION.md' "${AGENTS}" 'AGENTS does not name publication authority'
require_doc_marker 'docs/PROJECT_PRINCIPLES.md' "${INDEX}" 'INDEX does not route to canonical principles'
require_doc_marker 'docs/START_HERE.md' "${INDEX}" 'INDEX does not route to operational handoff'
require_doc_marker 'DEC-2026-08-05-universal-versioned-github-titles.md' "${INDEX}" 'INDEX does not name universal title decision'
require_doc_marker 'DEC-2026-08-14-operational-handoff-and-scope-first-preflight.md' "${PUBLICATION}" 'publication procedure does not name operational handoff decision'
require_doc_marker 'package-candidate prefix' "${AGENTS}" 'AGENTS does not require versioned project delivery identity'
require_doc_marker 'final squash subject' "${AGENTS}" 'AGENTS does not require versioned squash identity'
require_doc_marker 'every PR title' "${PUBLICATION}" 'publication rules do not cover PR title identity'
require_doc_marker 'PR-branch commit subject' "${PUBLICATION}" 'publication rules do not cover branch commit identity'
require_doc_marker 'final squash subject' "${PUBLICATION}" 'publication rules do not cover squash identity'
require_doc_marker 'Docs/governance/CI-only changes' "${PUBLICATION}" 'publication rules do not cover non-packaged changes'
require_doc_marker 'what changes and why' "${PRINCIPLES}" 'canonical principles omit delivery documentation scope/reason'
require_doc_marker 'expected result' "${PRINCIPLES}" 'canonical principles omit expected result requirement'
require_doc_marker 'long-term' "${PRINCIPLES}" 'canonical principles omit long-term plan requirement'
require_doc_marker 'reconcile' "${PUBLICATION}" 'publication procedure omits plan reconciliation'

# One generic publisher is allowed; version-specific publishers in main are forbidden.
version_specific=$(find "${ROOT_DIR}/.github/workflows" -maxdepth 1 -type f \
  -name 'publish-v*-prerelease.yml' -print)
[ -z "${version_specific}" ] || {
  echo "${version_specific}" >&2
  fail 'version-specific prerelease workflow remains in the authoritative tree'
}

require_fixed "- 'publish/v*_*'" "${PRERELEASE_WORKFLOW}" 'generic publisher branch contract is missing'
require_fixed 'workflow_dispatch:' "${PRERELEASE_WORKFLOW}" 'generic publisher lacks manual dispatch fallback'
require_fixed "release: '15.0'" "${PRERELEASE_WORKFLOW}" 'generic publisher does not build on FreeBSD 15'
require_fixed 'FreeBSD:15:amd64' "${PRERELEASE_WORKFLOW}" 'generic publisher does not validate ABI'
require_fixed 'freebsd:15:x86:64' "${PRERELEASE_WORKFLOW}" 'generic publisher does not validate architecture'
require_fixed 'gh release create' "${PRERELEASE_WORKFLOW}" 'generic publisher does not use repository release API'
require_fixed 'Delete temporary publication branch' "${PRERELEASE_WORKFLOW}" 'generic publisher lacks branch cleanup'
require_fixed 'prerelease == true' "${PRERELEASE_WORKFLOW}" 'generic publisher lacks release verification'

if grep -Eq 'pages:[[:space:]]*write|actions/deploy-pages|build-pkg-repository' "${PRERELEASE_WORKFLOW}"; then
  fail 'testing prerelease publisher must not publish GitHub Pages or pkg repository'
fi

# Full release trigger must obey universal versioned titles.
require_fixed '[[ "${REVISION}" == "1" ]]' "${RELEASE_TRIGGER}" 'release trigger does not require revision 1'
require_fixed '^v${ESCAPED_VERSION}_1:\ Prepare\ release\ v${ESCAPED_VERSION}' "${RELEASE_TRIGGER}" 'release trigger still expects an unversioned squash subject'

# Existing ordinary PR and main-integrity controls remain mandatory.
require_fixed 'concurrency:' "${CI}" 'CI concurrency is missing'
require_fixed 'cancel-in-progress:' "${CI}" 'CI cancel-in-progress is missing'
require_fixed 'Classify changed paths' "${CI}" 'CI path classification is missing'
require_fixed 'workflow_dispatch:' "${CI}" 'CI lacks the manual dispatch fallback'
require_fixed 'github.event_name == '\''pull_request'\'' || github.event_name == '\''workflow_dispatch'\''' "${CI}" 'manual CI does not execute project validation'
require_fixed 'EVENT_NAME}" == "workflow_dispatch"' "${CI}" 'manual CI event is not classified'
require_fixed '(github.event_name == '\''pull_request'\'' || github.event_name == '\''workflow_dispatch'\'') && needs.changes.outputs.package == '\''true'\''' "${CI}" 'manual CI does not build the FreeBSD package'
require_fixed 'Verify main integrity' "${CI}" 'main integrity job is missing'
require_fixed 'Invalid main commit subject' "${CI}" 'main squash-subject validation is missing'
require_fixed 'Required format: ${EXPECTED}: <logical change>' "${CI}" 'main title error contract is missing'

require_fixed 'concurrency:' "${TITLE_WORKFLOW}" 'PR title concurrency is missing'
require_fixed 'Validate versioned PR and commit subjects' "${TITLE_WORKFLOW}" 'versioned PR/commit job is missing'
require_fixed 'git log --format=%s "${BASE_SHA}..${HEAD_SHA}"' "${TITLE_WORKFLOW}" 'PR commit-range validation is missing'
require_fixed 'Invalid pull-request title' "${TITLE_WORKFLOW}" 'PR title rejection is missing'
require_fixed 'Invalid commit subject' "${TITLE_WORKFLOW}" 'PR commit-subject rejection is missing'
require_fixed 'Required format: ${expected}: <logical change>' "${TITLE_WORKFLOW}" 'PR title error contract is missing'

if grep -Eq '"(governance|docs|ci|chore): "\*' "${TITLE_WORKFLOW}"; then
  fail 'unversioned conventional-title exception remains in PR title validation'
fi

if grep -Eq 'Governance, documentation, (and )?CI-only changes may use conventional' "${EFFICIENT_DECISION}"; then
  fail 'active decision still permits unversioned conventional titles'
fi

require_fixed 'types: [closed]' "${CLEANUP_WORKFLOW}" 'cleanup workflow does not run on closed PRs'
require_fixed 'github.event.pull_request.merged == true' "${CLEANUP_WORKFLOW}" 'cleanup workflow does not require merged PRs'
require_fixed 'github.event.pull_request.head.repo.full_name == github.repository' "${CLEANUP_WORKFLOW}" 'cleanup workflow lacks same-repository guard'

echo "GitHub delivery and workflow tests passed for package candidate ${expected}."
