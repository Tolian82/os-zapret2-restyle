#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
AGENTS="${ROOT_DIR}/AGENTS.md"
README="${ROOT_DIR}/README.md"
PRINCIPLES="${ROOT_DIR}/docs/PROJECT_PRINCIPLES.md"
DOC_RULES="${ROOT_DIR}/docs/DOCUMENTATION_RULES.md"
START_HERE="${ROOT_DIR}/docs/START_HERE.md"
STATE="${ROOT_DIR}/docs/PROJECT_STATE.md"
ROADMAP="${ROOT_DIR}/docs/ROADMAP.md"
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
  "${AGENTS}" "${README}" "${PRINCIPLES}" "${DOC_RULES}" "${START_HERE}" "${STATE}" \
  "${ROADMAP}" "${INDEX}" "${CURRENT_LEDGER}" "${ARCHIVE_01}" "${ARCHIVE_02}" "${ARCHIVE_03}" \
  "${PUBLICATION}" "${WORKFLOW_SUMMARY}" "${MEMORY_DECISION}" "${OPERATIONAL_DECISION}" \
  "${EVIDENCE_DECISION}" "${EFFICIENT_DECISION}" "${TITLE_DECISION}" "${OLD_DECISION}" \
  "${CI}" "${TITLE_WORKFLOW}" "${CLEANUP_WORKFLOW}" "${PRERELEASE_WORKFLOW}" \
  "${RELEASE_TRIGGER}" "${RELEASE_WORKFLOW}"
do
  test -s "${file}" || fail "missing or empty GitHub/documentation authority: ${file}"
done

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(sed -n 's/^PLUGIN_REVISION=[[:space:]]*//p' "${MAKEFILE}" | head -1)
printf '%s\n' "${version}" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' || fail 'VERSION is invalid'
printf '%s\n' "${revision}" | grep -Eq '^[0-9]+$' || fail 'PLUGIN_REVISION is invalid'
expected="v${version}"
[ "${revision}" = "0" ] || expected="${expected}_${revision}"

# Active decision status remains explicit.
grep -Eq '^Status:[[:space:]]+\*\*ACTIVE / SUPERSEDING' "${MEMORY_DECISION}" || fail 'three-level memory decision is not active/superseding'
grep -Eq '^Status:[[:space:]]+\*\*ACTIVE\*\*$' "${OPERATIONAL_DECISION}" || fail 'operational handoff decision is not active'
grep -Eq '^Status:[[:space:]]+Active([,[:space:]].*)?$' "${EVIDENCE_DECISION}" || fail 'evidence-first decision is not active'
grep -Eq '^Status:[[:space:]]+Active([,[:space:]].*)?$' "${EFFICIENT_DECISION}" || fail 'efficient delivery decision is not active'
grep -Eq '^Status:[[:space:]]+Active([,[:space:]].*)?$' "${TITLE_DECISION}" || fail 'universal title decision is not active'
grep -Eq '^Status:[[:space:]]+Superseded' "${OLD_DECISION}" || fail 'old atomic decision is not superseded'

# Level-1 and navigation integrity.
require_doc_marker 'docs/PROJECT_PRINCIPLES.md' "${AGENTS}" 'AGENTS does not require project principles'
require_doc_marker 'docs/DOCUMENTATION_RULES.md' "${AGENTS}" 'AGENTS does not require documentation rules'
require_doc_marker 'docs/START_HERE.md' "${AGENTS}" 'AGENTS does not require START_HERE'
require_doc_marker 'docs/PROJECT_STATE.md' "${AGENTS}" 'AGENTS does not require PROJECT_STATE'
require_doc_marker 'PROJECT_STATE.md' "${START_HERE}" 'START_HERE does not link PROJECT_STATE at startup'
require_doc_marker 'DOCUMENTATION_RULES.md' "${START_HERE}" 'START_HERE does not link documentation rules'
require_doc_marker 'GITHUB_PUBLICATION.md' "${START_HERE}" 'START_HERE does not link GitHub publication rules'
require_doc_marker 'ROADMAP.md' "${START_HERE}" 'START_HERE does not link master plan'
require_doc_marker 'INDEX.md' "${START_HERE}" 'START_HERE does not link INDEX'
require_doc_marker 'DOCUMENTATION_RULES.md' "${INDEX}" 'INDEX does not route to documentation rules'
require_doc_marker 'history/current/v0.4.x.md' "${INDEX}" 'INDEX does not route to current line ledger'
require_doc_marker 'history/archive/v0.1.x.md' "${INDEX}" 'INDEX does not route to v0.1.x archive'
require_doc_marker 'history/archive/v0.2.x.md' "${INDEX}" 'INDEX does not route to v0.2.x archive'
require_doc_marker 'history/archive/v0.3.x.md' "${INDEX}" 'INDEX does not route to v0.3.x archive'
require_doc_marker 'verification/evidence/' "${INDEX}" 'INDEX does not route to deep verification proof'
require_doc_marker 'navigation / integrity map' "${INDEX}" 'INDEX is no longer explicitly navigation/integrity only'
require_doc_marker 'Archiving never deletes' "${INDEX}" 'INDEX omits archive-integrity guarantee'

# Numbered documentation canon and explicit version roles.
rule_count=$(grep -Ec '^[0-9]+\. \*\*' "${DOC_RULES}")
[ "${rule_count}" -ge 50 ] || fail "documentation rules are not fully numbered"
require_doc_marker 'owner-canon “Суслик” rule' "${DOC_RULES}" 'documentation rules omit Суслик canon'
require_doc_marker '`Зафиксируй`' "${DOC_RULES}" 'documentation rules omit fix/record contract'
require_doc_marker 'second numeric component defines the long-lived project-state line' "${DOC_RULES}" 'second-component PROJECT_STATE role is missing'
require_doc_marker 'third numeric component identifies the current development stage' "${DOC_RULES}" 'third-component stage role is missing'
require_doc_marker 'package revision suffix `_N` identifies the concrete patch/iteration' "${DOC_RULES}" 'revision START_HERE role is missing'
require_doc_marker 'third-component transition is not a full release by itself' "${DOC_RULES}" 'third-component release distinction is missing'
require_doc_marker 'final old `PROJECT_STATE.md` content flows into' "${DOC_RULES}" 'PROJECT_STATE archive-flow rule is missing'
require_doc_marker 'Every current `PROJECT_STATE.md` ends with direct links to every completed version-line archive' "${DOC_RULES}" 'PROJECT_STATE archive-link rule is missing'
require_doc_marker 'Do not retroactively rewrite `v0.4.0` or older history' "${DOC_RULES}" 'legacy non-rewrite boundary is missing'
require_doc_marker '`ROADMAP.md` is the master development plan' "${DOC_RULES}" 'master-plan rule is missing'
require_doc_marker 'every known future intention' "${DOC_RULES}" 'future-plan completeness rule is missing'
require_doc_marker 'Owner-facing communication is normal understandable Russian' "${DOC_RULES}" 'human Russian communication rule is missing'

# Current Level-1 role application.
require_doc_marker 'State-line scope: **`v0.4.x`**' "${STATE}" 'PROJECT_STATE is not bound to current second-component line'
require_doc_marker 'v0.1.x archive' "${STATE}" 'PROJECT_STATE lacks v0.1.x archive link'
require_doc_marker 'v0.2.x archive' "${STATE}" 'PROJECT_STATE lacks v0.2.x archive link'
require_doc_marker 'v0.3.x archive' "${STATE}" 'PROJECT_STATE lacks v0.3.x archive link'
require_doc_marker 'Current handoff identity: **`v0.4.1_12`**' "${START_HERE}" 'START_HERE is not bound to exact current revision'
require_doc_marker 'What was just established under `v0.4.1_12`' "${START_HERE}" 'START_HERE does not record current revision effect'
require_doc_marker 'Whole-project path' "${ROADMAP}" 'master plan lacks whole-project path'
require_doc_marker 'Model A baseline' "${ROADMAP}" 'master plan lost Model A history'
require_doc_marker 'Model B testing' "${ROADMAP}" 'master plan lost Model B history'
require_doc_marker 'Model C testing' "${ROADMAP}" 'master plan lost Model C history'
require_doc_marker 'Additional BLOB repository GUI' "${ROADMAP}" 'master plan lost deferred BLOB GUI intention'

# Project/release canon reflects the same semantics.
require_doc_marker 'full release may use the current exact package candidate' "${PRINCIPLES}" 'principles still force release-only revision reset'
require_doc_marker 'third-component stage transition' "${PUBLICATION}" 'publication procedure lacks third-component transition'
require_doc_marker 'full release does not reset `PLUGIN_REVISION` merely because it is a release' "${PUBLICATION}" 'publication procedure still forces release-only revision reset'
require_doc_marker 'final old `PROJECT_STATE` content' "${PUBLICATION}" 'publication procedure lacks state archive rollover'
require_doc_marker 'DOCUMENTATION_RULES.md' "${MEMORY_DECISION}" 'active memory decision does not include documentation rules'

# Generic testing publisher remains separate from full Web/pkg release.
version_specific=$(find "${ROOT_DIR}/.github/workflows" -maxdepth 1 -type f -name 'publish-v*-prerelease.yml' -print)
[ -z "${version_specific}" ] || {
  echo "${version_specific}" >&2
  fail 'version-specific prerelease workflow remains in authoritative tree'
}
require_fixed "- 'publish/v*_*'" "${PRERELEASE_WORKFLOW}" 'generic testing publisher branch contract is missing'
require_fixed 'workflow_dispatch:' "${PRERELEASE_WORKFLOW}" 'generic testing publisher lacks manual dispatch fallback'
require_fixed "release: '15.0'" "${PRERELEASE_WORKFLOW}" 'generic testing publisher does not build on FreeBSD 15'
require_fixed 'prerelease == true' "${PRERELEASE_WORKFLOW}" 'generic testing publisher lacks prerelease verification'
if grep -Eq 'pages:[[:space:]]*write|actions/deploy-pages|build-pkg-repository' "${PRERELEASE_WORKFLOW}"; then
  fail 'testing package publisher must not publish Pages/pkg repository'
fi

# Full release trigger classifies every main commit and only publishes on explicit release preparation.
require_fixed 'Classify version transition / release' "${RELEASE_TRIGGER}" 'release trigger lacks version-transition classifier'
require_fixed 'PREVIOUS_VERSION=$(git show "${GITHUB_SHA}^:VERSION"' "${RELEASE_TRIGGER}" 'release trigger does not compare previous VERSION'
require_fixed 'A third-component development-stage transition must begin at package revision _1.' "${RELEASE_TRIGGER}" 'release trigger lacks third-stage reset guard'
require_fixed 'A first/second-component transition requires an explicit full-release preparation merge.' "${RELEASE_TRIGGER}" 'release trigger lacks second-component release guard'
require_fixed 'if: steps.release.outputs.publish == '\''true'\''' "${RELEASE_TRIGGER}" 'release publication is not conditional'
require_fixed 'prerelease: false' "${RELEASE_WORKFLOW}" 'full release workflow still marks releases as testing prereleases'
require_fixed 'Publish pkg repository' "${RELEASE_WORKFLOW}" 'full release workflow does not publish pkg repository'
require_fixed 'pages/FreeBSD:15:amd64' "${RELEASE_WORKFLOW}" 'full release workflow does not verify Web/pkg outputs'

# Existing ordinary PR/main controls remain mandatory.
require_fixed 'concurrency:' "${CI}" 'CI concurrency is missing'
require_fixed 'cancel-in-progress:' "${CI}" 'CI cancel-in-progress is missing'
require_fixed 'Classify changed paths' "${CI}" 'CI path classification is missing'
require_fixed 'workflow_dispatch:' "${CI}" 'CI lacks manual dispatch fallback'
require_fixed 'Verify main integrity' "${CI}" 'main integrity job is missing'
require_fixed 'Invalid main commit subject' "${CI}" 'main squash-subject validation is missing'
require_fixed 'Validate versioned PR and commit subjects' "${TITLE_WORKFLOW}" 'versioned PR/commit validation is missing'
require_fixed 'git log --format=%s "${BASE_SHA}..${HEAD_SHA}"' "${TITLE_WORKFLOW}" 'PR commit-range validation is missing'
require_fixed 'Invalid pull-request title' "${TITLE_WORKFLOW}" 'PR title rejection is missing'
require_fixed 'Invalid commit subject' "${TITLE_WORKFLOW}" 'PR commit-subject rejection is missing'
require_fixed 'types: [closed]' "${CLEANUP_WORKFLOW}" 'branch cleanup workflow does not run on closed PRs'
require_fixed 'github.event.pull_request.merged == true' "${CLEANUP_WORKFLOW}" 'branch cleanup does not require merged PRs'
require_fixed 'github.event.pull_request.head.repo.full_name == github.repository' "${CLEANUP_WORKFLOW}" 'branch cleanup lacks same-repository guard'

if grep -Eq '"(governance|docs|ci|chore): "\*' "${TITLE_WORKFLOW}"; then
  fail 'unversioned conventional-title exception remains in PR title validation'
fi

require_doc_marker 'Strategy Lab' "${README}" 'README does not present current Strategy Lab capability'

echo "GitHub delivery, numbered documentation, version-stage, archive, release, and repository-integrity tests passed for candidate ${expected}."
