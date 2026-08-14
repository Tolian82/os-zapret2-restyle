#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
AGENTS="${ROOT_DIR}/AGENTS.md"
README="${ROOT_DIR}/README.md"
PRINCIPLES="${ROOT_DIR}/docs/PROJECT_PRINCIPLES.md"
START_HERE="${ROOT_DIR}/docs/START_HERE.md"
STATE="${ROOT_DIR}/docs/PROJECT_STATE.md"
INDEX="${ROOT_DIR}/docs/INDEX.md"
CURRENT_LEDGER="${ROOT_DIR}/docs/history/current/v0.4.x.md"
ARCHIVE_01="${ROOT_DIR}/docs/history/archive/v0.1.x.md"
ARCHIVE_02="${ROOT_DIR}/docs/history/archive/v0.2.x.md"
ARCHIVE_03="${ROOT_DIR}/docs/history/archive/v0.3.x.md"
PUBLICATION="${ROOT_DIR}/docs/GITHUB_PUBLICATION.md"
WORKFLOW_SUMMARY="${ROOT_DIR}/docs/GITHUB_WORKFLOW.md"
MEMORY_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-14-three-level-versioned-documentation-memory.md"
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
RELEASE_WORKFLOW="${ROOT_DIR}/.github/workflows/release.yml"
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
  "${README}" \
  "${PRINCIPLES}" \
  "${START_HERE}" \
  "${STATE}" \
  "${INDEX}" \
  "${CURRENT_LEDGER}" \
  "${ARCHIVE_01}" \
  "${ARCHIVE_02}" \
  "${ARCHIVE_03}" \
  "${PUBLICATION}" \
  "${WORKFLOW_SUMMARY}" \
  "${MEMORY_DECISION}" \
  "${OPERATIONAL_DECISION}" \
  "${EVIDENCE_DECISION}" \
  "${EFFICIENT_DECISION}" \
  "${TITLE_DECISION}" \
  "${OLD_DECISION}" \
  "${CI}" \
  "${TITLE_WORKFLOW}" \
  "${CLEANUP_WORKFLOW}" \
  "${PRERELEASE_WORKFLOW}" \
  "${RELEASE_TRIGGER}" \
  "${RELEASE_WORKFLOW}"
do
  test -s "${file}" || fail "missing or empty GitHub governance/memory file: ${file}"
done

# Documentation checks guard authority relationships and required semantics, not mutable line placement
# or a requirement that INDEX duplicate individual deep-record links.
version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(sed -n 's/^PLUGIN_REVISION=[[:space:]]*//p' "${MAKEFILE}" | head -1)

printf '%s\n' "${version}" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' || fail 'VERSION is invalid'
printf '%s\n' "${revision}" | grep -Eq '^[0-9]+$' || fail 'PLUGIN_REVISION is invalid'

expected="v${version}"
if [ -n "${revision}" ] && [ "${revision}" != "0" ]; then
  expected="${expected}_${revision}"
fi

grep -Eq '^Status:[[:space:]]+\*\*ACTIVE / SUPERSEDING' "${MEMORY_DECISION}" || fail 'three-level memory decision is not active/superseding'
grep -Eq '^Status:[[:space:]]+\*\*ACTIVE\*\*$' "${OPERATIONAL_DECISION}" || fail 'operational handoff decision is not active'
grep -Eq '^Status:[[:space:]]+Active([,[:space:]].*)?$' "${EVIDENCE_DECISION}" || fail 'evidence-first decision is not active'
grep -Eq '^Status:[[:space:]]+Active([,[:space:]].*)?$' "${EFFICIENT_DECISION}" || fail 'efficient delivery decision is not active'
grep -Eq '^Status:[[:space:]]+Active([,[:space:]].*)?$' "${TITLE_DECISION}" || fail 'universal title decision is not active'
grep -Eq '^Status:[[:space:]]+Superseded' "${OLD_DECISION}" || fail 'old atomic decision is not superseded'

# Level-1 recovery and three-level memory routing.
require_doc_marker 'docs/PROJECT_PRINCIPLES.md' "${AGENTS}" 'AGENTS does not require canonical project principles'
require_doc_marker 'docs/START_HERE.md' "${AGENTS}" 'AGENTS does not require operational handoff'
require_doc_marker 'docs/PROJECT_STATE.md' "${AGENTS}" 'AGENTS does not require current project state'
require_doc_marker 'docs/GITHUB_PUBLICATION.md' "${AGENTS}" 'AGENTS does not name publication authority'
require_doc_marker 'history/current/v0.4.x.md' "${INDEX}" 'INDEX does not route to current version-line ledger'
require_doc_marker 'history/archive/v0.1.x.md' "${INDEX}" 'INDEX does not route to v0.1.x archive'
require_doc_marker 'history/archive/v0.2.x.md' "${INDEX}" 'INDEX does not route to v0.2.x archive'
require_doc_marker 'history/archive/v0.3.x.md' "${INDEX}" 'INDEX does not route to v0.3.x archive'
require_doc_marker 'PROJECT_PRINCIPLES.md' "${INDEX}" 'INDEX does not route to canonical principles'
require_doc_marker 'START_HERE.md' "${INDEX}" 'INDEX does not route to operational handoff'
require_doc_marker 'PROJECT_STATE.md' "${INDEX}" 'INDEX does not route to current state'
require_doc_marker 'verification/evidence/' "${INDEX}" 'INDEX does not route to deep verification evidence'
require_doc_marker 'decisions/' "${INDEX}" 'INDEX does not route to deep decisions'
require_doc_marker 'navigation only' "${INDEX}" 'INDEX is no longer explicitly navigation-only'
require_doc_marker 'Archiving never deletes' "${INDEX}" 'INDEX omits archive-integrity guarantee'
require_doc_marker 'Level 1' "${STATE}" 'PROJECT_STATE does not expose current memory-level state'
require_doc_marker 'v0.4.x' "${CURRENT_LEDGER}" 'current version-line ledger identity is missing'
require_doc_marker 'Handoff to v0.2.x' "${ARCHIVE_01}" 'v0.1.x archive lacks next-line handoff'
require_doc_marker 'Handoff to v0.3.x' "${ARCHIVE_02}" 'v0.2.x archive lacks next-line handoff'
require_doc_marker 'Handoff to v0.4.x' "${ARCHIVE_03}" 'v0.3.x archive lacks next-line handoff'

# Owner-controlled second numeric component and full-release semantics.
require_doc_marker 'second numeric component' "${PRINCIPLES}" 'canonical principles omit explicit second-version-component terminology'
require_doc_marker 'assistant must never initiate' "${PRINCIPLES}" 'canonical principles omit owner gate for second-version-component changes'
require_doc_marker 'second-component change => full release' "${PRINCIPLES}" 'canonical principles omit second-component-to-release implication'
require_doc_marker 'full release != second-component change' "${PRINCIPLES}" 'canonical principles omit one-way release implication'
require_doc_marker 'Every full release includes a complete human-facing `README.md` revision' "${PRINCIPLES}" 'canonical principles omit README release gate'
require_doc_marker 'Owner-controlled second numeric component' "${PUBLICATION}" 'publication rules omit explicit second-version-component authority'
require_doc_marker 'assistant must never initiate a second-component change' "${PUBLICATION}" 'publication rules permit inferred second-version-component changes'
require_doc_marker 'full release =/=> second numeric component changes' "${PUBLICATION}" 'publication rules omit one-way release implication'
require_doc_marker 'complete `README.md` revision' "${PUBLICATION}" 'publication rules omit full-release README revision'
require_doc_marker 'history/archive/v0.4.x.md' "${PUBLICATION}" 'publication rules do not demonstrate old-line archive creation'
require_doc_marker 'no extra owner' "${PUBLICATION}" 'publication rules do not make authorized rollover self-contained'
require_doc_marker 'second numeric component' "${MEMORY_DECISION}" 'active memory decision still lacks explicit second-version-component terminology'
require_doc_marker 'Full Web/pkg release' "${README}" 'README does not expose the full Web/pkg release'
require_doc_marker 'Current development candidate' "${README}" 'README does not distinguish current development package'
require_doc_marker 'Strategy Lab' "${README}" 'README does not present current Strategy Lab capability'
require_doc_marker 'second numeric component' "${README}" 'README does not explain the project version/release boundary'

# Publication/governance semantics remain mandatory while deep decision records are loaded on demand.
require_doc_marker 'PR/branch commit/final squash subjects begin' "${AGENTS}" 'AGENTS does not require versioned project delivery identity'
require_doc_marker 'final squash subject' "${AGENTS}" 'AGENTS does not require versioned squash identity'
require_doc_marker 'every PR title' "${PUBLICATION}" 'publication rules do not cover PR title identity'
require_doc_marker 'PR-branch commit subject' "${PUBLICATION}" 'publication rules do not cover branch commit identity'
require_doc_marker 'final squash subject' "${PUBLICATION}" 'publication rules do not cover squash identity'
require_doc_marker 'Docs/governance/CI-only changes' "${PUBLICATION}" 'publication rules do not cover non-packaged changes'
require_doc_marker 'what changes and why' "${PRINCIPLES}" 'canonical principles omit delivery documentation scope/reason'
require_doc_marker 'expected result' "${PRINCIPLES}" 'canonical principles omit expected result requirement'
require_doc_marker 'long-term' "${PRINCIPLES}" 'canonical principles omit long-term plan requirement'
require_doc_marker 'three memory levels' "${PRINCIPLES}" 'canonical principles omit three-level documentation memory'
require_doc_marker 'one primary home' "${PRINCIPLES}" 'canonical principles omit one-primary-home rule'
require_doc_marker 'reconcile' "${PUBLICATION}" 'publication procedure omits plan reconciliation'

# One generic testing-package publisher is allowed; version-specific publishers in main are forbidden.
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
require_fixed 'prerelease == true' "${PRERELEASE_WORKFLOW}" 'generic publisher lacks testing-prerelease verification'

if grep -Eq 'pages:[[:space:]]*write|actions/deploy-pages|build-pkg-repository' "${PRERELEASE_WORKFLOW}"; then
  fail 'testing prerelease publisher must not publish GitHub Pages or pkg repository'
fi

# Full release trigger/workflow must obey version identity and publish a normal Web/pkg release.
require_fixed '[[ "${REVISION}" == "1" ]]' "${RELEASE_TRIGGER}" 'release trigger does not require revision 1'
require_fixed '^v${ESCAPED_VERSION}_1:\ Prepare\ release\ v${ESCAPED_VERSION}' "${RELEASE_TRIGGER}" 'release trigger still expects an unversioned squash subject'
require_fixed 'prerelease: false' "${RELEASE_WORKFLOW}" 'full release workflow still marks full releases as testing prereleases'
require_fixed 'Publish pkg repository' "${RELEASE_WORKFLOW}" 'full release workflow does not publish the pkg repository'
require_fixed 'pages/FreeBSD:15:amd64' "${RELEASE_WORKFLOW}" 'full release workflow does not verify the Web/pkg repository outputs'

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

echo "GitHub delivery, workflow, release-authority, README, and documentation-memory tests passed for package candidate ${expected}."
