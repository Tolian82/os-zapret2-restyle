#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
AGENTS="${ROOT_DIR}/AGENTS.md"
DOC_RULES="${ROOT_DIR}/docs/DOCUMENTATION_RULES.md"
DEV_RULES="${ROOT_DIR}/docs/PROJECT_PRINCIPLES.md"
CHAT_RULES="${ROOT_DIR}/docs/CHAT_RULES.md"
GH_RULES="${ROOT_DIR}/docs/GITHUB_PUBLICATION.md"
START_HERE="${ROOT_DIR}/docs/START_HERE.md"
INDEX="${ROOT_DIR}/docs/INDEX.md"
CI="${ROOT_DIR}/.github/workflows/ci.yml"
TITLE_WORKFLOW="${ROOT_DIR}/.github/workflows/pr-title.yml"
CLEANUP_WORKFLOW="${ROOT_DIR}/.github/workflows/cleanup-merged-branch.yml"
PRERELEASE_WORKFLOW="${ROOT_DIR}/.github/workflows/publish-prerelease.yml"
DELIVERY_CI="${ROOT_DIR}/.github/workflows/testing-package-delivery-ci.yml"
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
  grep -Fq -- "$1" "$2" || fail "$3"
}

for file in \
  "${AGENTS}" "${DOC_RULES}" "${DEV_RULES}" "${CHAT_RULES}" "${GH_RULES}" \
  "${START_HERE}" "${INDEX}" "${CI}" "${TITLE_WORKFLOW}" "${CLEANUP_WORKFLOW}" \
  "${PRERELEASE_WORKFLOW}" "${DELIVERY_CI}" "${RELEASE_TRIGGER}" "${RELEASE_WORKFLOW}"
do
  test -s "${file}" || fail "missing or empty GitHub/rule authority: ${file}"
done

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(sed -n 's/^PLUGIN_REVISION=[[:space:]]*//p' "${MAKEFILE}" | head -1)
printf '%s\n' "${version}" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' || fail 'VERSION is invalid'
printf '%s\n' "${revision}" | grep -Eq '^[0-9]+$' || fail 'PLUGIN_REVISION is invalid'
expected="v${version}"
[ "${revision}" = "0" ] || expected="${expected}_${revision}"

# Four canonical books are discoverable; GitHub-specific semantics live in GH, chat shorthand in CHAT.
require_fixed 'docs/GITHUB_PUBLICATION.md' "${AGENTS}" 'AGENTS does not route to GH rule book'
require_fixed 'CHAT_RULES.md' "${START_HERE}" 'START_HERE does not expose chat rule book'
require_fixed 'GITHUB_PUBLICATION.md' "${START_HERE}" 'START_HERE does not expose GitHub rule book'
require_fixed 'CHAT_RULES.md' "${INDEX}" 'INDEX does not route to chat rule book'
require_fixed 'GITHUB_PUBLICATION.md' "${INDEX}" 'INDEX does not route to GitHub rule book'

require_fixed 'GH-001.' "${GH_RULES}" 'GitHub connector-first rule is missing'
require_fixed 'GH-007.' "${GH_RULES}" 'scope/risk preflight rule is missing'
require_fixed 'GH-009. **[ОТМЕНЕНО]' "${GH_RULES}" 'cancelled broad-reconciliation rule marker is missing'
require_fixed 'GH-016.' "${GH_RULES}" 'scope-proportionate validation rule is missing'
require_fixed 'GH-021.' "${GH_RULES}" 'latest-head CI rule is missing'
require_fixed 'GH-024.' "${GH_RULES}" 'exact-head merge rule is missing'
require_fixed 'GH-027.' "${GH_RULES}" 'forward-only published-release identity rule is missing'
require_fixed 'GH-034.' "${GH_RULES}" 'testing-package GitHub boundary is missing'
require_fixed 'GH-039.' "${GH_RULES}" 'full-release GitHub boundary is missing'
require_fixed 'GH-047.' "${GH_RULES}" 'second-component transition GitHub guard is missing'
require_fixed 'GH-049.' "${GH_RULES}" 'release-trigger classification rule is missing'
require_fixed 'GH-055.' "${GH_RULES}" 'GitHub rule maintenance boundary is missing'
require_fixed 'GH-060.' "${GH_RULES}" 'direct GitHub package-completion rule is missing'
require_fixed 'GH-061.' "${GH_RULES}" 'post-publication record-PR rule is missing'

require_fixed 'CHAT-001.' "${CHAT_RULES}" 'owner-facing Russian-language rule is missing'
require_fixed 'CHAT-008.' "${CHAT_RULES}" 'chat Stop rule is missing'
require_fixed 'CHAT-009.' "${CHAT_RULES}" 'chat record/fix canon rule is missing'
require_fixed 'CHAT-010.' "${CHAT_RULES}" 'ordinary action authorization rule is missing'
require_fixed 'CHAT-015.' "${CHAT_RULES}" 'testing-package shorthand rule is missing'
require_fixed 'CHAT-017.' "${CHAT_RULES}" 'full-release shorthand rule is missing'
require_fixed 'CHAT-019.' "${CHAT_RULES}" 'owner csh command rule is missing'
require_fixed 'CHAT-027.' "${CHAT_RULES}" 'chat/sandbox package-delivery prohibition is missing'
require_fixed 'Project patches and packages are never delivered through chat/sandbox files.' "${CHAT_RULES}" 'chat transport prohibition wording is missing'

require_fixed 'DEV-033.' "${DEV_RULES}" 'docs/CI-only metadata rule is missing'
require_fixed 'DEV-034.' "${DEV_RULES}" 'third-component stage rule is missing'
require_fixed 'DEV-036.' "${DEV_RULES}" 'owner-controlled second-component rule is missing'
require_fixed 'DEV-038.' "${DEV_RULES}" 'exact-current-candidate release rule is missing'
require_fixed 'DEV-039.' "${DEV_RULES}" 'full OPNsense release definition is missing'
require_fixed 'DEV-040.' "${DEV_RULES}" 'testing-package product boundary is missing'
require_fixed 'DOC-037.' "${DOC_RULES}" 'post-publication documentation-tail rule is missing'
require_fixed 'DOC-038.' "${DOC_RULES}" 'README full-release gate is missing'

# Generic testing publisher remains separate from full Web/pkg release and enforces immutable source identity.
version_specific=$(find "${ROOT_DIR}/.github/workflows" -maxdepth 1 -type f -name 'publish-v*-prerelease.yml' -print)
[ -z "${version_specific}" ] || {
  echo "${version_specific}" >&2
  fail 'version-specific prerelease workflow remains in authoritative tree'
}
require_fixed "- 'publish/v*_*'" "${PRERELEASE_WORKFLOW}" 'generic testing publisher branch contract is missing'
require_fixed 'workflow_dispatch:' "${PRERELEASE_WORKFLOW}" 'generic testing publisher lacks manual dispatch fallback'
require_fixed 'pull-requests: write' "${PRERELEASE_WORKFLOW}" 'testing publisher cannot create publication-record PRs'
require_fixed "release: '15.0'" "${PRERELEASE_WORKFLOW}" 'generic testing publisher does not build on FreeBSD 15'
require_fixed 'git merge-base --is-ancestor "${TARGET_SHA}" origin/main' "${PRERELEASE_WORKFLOW}" 'testing publisher does not require source ancestry in main'
require_fixed 'PARENT_IDENTITY=$(identity_at "${TARGET_SHA}^")' "${PRERELEASE_WORKFLOW}" 'testing publisher does not verify candidate-defining parent identity'
require_fixed '[[ "${PARENT_IDENTITY}" != "${CURRENT_IDENTITY}" ]]' "${PRERELEASE_WORKFLOW}" 'testing publisher can publish from a later same-identity docs/governance commit'
require_fixed 'prerelease == true' "${PRERELEASE_WORKFLOW}" 'generic testing publisher lacks prerelease verification'
require_fixed 'publication-record/${TAG}' "${PRERELEASE_WORKFLOW}" 'testing publisher lacks deterministic publication-record branch'
require_fixed 'docs/verification/evidence/testing-publications/${TAG}.md' "${PRERELEASE_WORKFLOW}" 'testing publisher lacks machine-generated publication evidence path'
require_fixed 'gh pr create' "${PRERELEASE_WORKFLOW}" 'testing publisher does not open publication-record PR'
require_fixed '--draft' "${PRERELEASE_WORKFLOW}" 'publication-record PR is not deliberately Draft before bounded reconciliation'
require_fixed 'Direct package asset:' "${PRERELEASE_WORKFLOW}" 'publication-record PR does not expose the direct GitHub package URL'
if grep -Eq 'pages:[[:space:]]*write|actions/deploy-pages|build-pkg-repository' "${PRERELEASE_WORKFLOW}"; then
  fail 'testing package publisher must not publish Pages/pkg repository'
fi
if grep -Eq 'actions/upload-artifact|upload-artifact@' "${PRERELEASE_WORKFLOW}"; then
  fail 'testing package publisher must not use an Actions artifact as delivery'
fi

# Publisher-contract changes have their own CI gate and real FreeBSD 15 package qualification.
require_fixed 'name: Testing package delivery contract' "${DELIVERY_CI}" 'testing-package delivery CI workflow is missing its identity'
require_fixed "- '.github/workflows/publish-prerelease.yml'" "${DELIVERY_CI}" 'delivery CI does not trigger on publisher changes'
require_fixed "- 'scripts/test-github-branch-hygiene.sh'" "${DELIVERY_CI}" 'delivery CI does not trigger on governance-test changes'
require_fixed 'sh scripts/test-github-branch-hygiene.sh' "${DELIVERY_CI}" 'delivery CI does not execute the governance contract'
require_fixed "release: '15.0'" "${DELIVERY_CI}" 'delivery CI does not qualify package build on FreeBSD 15'
require_fixed '.abi == "FreeBSD:15:amd64"' "${DELIVERY_CI}" 'delivery CI does not verify FreeBSD 15 package ABI'

# Full release trigger/workflow enforce current version semantics.
require_fixed 'Classify version transition / release' "${RELEASE_TRIGGER}" 'release trigger lacks version-transition classifier'
require_fixed 'PREVIOUS_VERSION=$(git show "${GITHUB_SHA}^:VERSION"' "${RELEASE_TRIGGER}" 'release trigger does not compare previous VERSION'
require_fixed 'A third-component development-stage transition must begin at package revision _1.' "${RELEASE_TRIGGER}" 'release trigger lacks third-stage reset guard'
require_fixed 'A first/second-component transition requires an explicit full-release preparation merge.' "${RELEASE_TRIGGER}" 'release trigger lacks second-component release guard'
require_fixed "if: steps.release.outputs.publish == 'true'" "${RELEASE_TRIGGER}" 'release publication is not conditional'
require_fixed 'prerelease: false' "${RELEASE_WORKFLOW}" 'full release workflow still marks release as prerelease'
require_fixed 'Publish pkg repository' "${RELEASE_WORKFLOW}" 'full release workflow does not publish pkg repository'
require_fixed 'pages/FreeBSD:15:amd64' "${RELEASE_WORKFLOW}" 'full release workflow does not verify Web/pkg outputs'

# Ordinary PR/main controls remain mandatory, with a focused path for Markdown-only documentation changes.
require_fixed 'concurrency:' "${CI}" 'CI concurrency is missing'
require_fixed 'Classify changed paths' "${CI}" 'CI path classification is missing'
require_fixed 'docs_only: ${{ steps.paths.outputs.docs_only }}' "${CI}" 'CI does not expose docs-only classification'
require_fixed "grep -Ev '^(AGENTS\\.md|README\\.md|docs/.*\\.md)$'" "${CI}" 'docs-only path boundary is missing'
require_fixed 'name: Validate documentation' "${CI}" 'focused documentation validation job is missing'
require_fixed "needs.changes.outputs.docs_only == 'true'" "${CI}" 'documentation validation is not gated by docs-only classification'
require_fixed "needs.changes.outputs.docs_only != 'true'" "${CI}" 'full product validation is not skipped for docs-only PRs'
require_fixed 'run: sh scripts/test-release-trigger.sh' "${CI}" 'focused documentation validation lacks release-governance test'
require_fixed 'run: sh scripts/test-github-branch-hygiene.sh' "${CI}" 'focused documentation validation lacks GitHub-governance test'
require_fixed 'run: sh scripts/test-repository-hygiene.sh' "${CI}" 'focused documentation validation lacks repository-integrity test'
require_fixed 'Verify main integrity' "${CI}" 'main integrity job is missing'
require_fixed 'Invalid main commit subject' "${CI}" 'main squash-subject validation is missing'
require_fixed 'Validate versioned PR and commit subjects' "${TITLE_WORKFLOW}" 'versioned PR/commit validation is missing'
require_fixed 'git log --format=%s "${BASE_SHA}..${HEAD_SHA}"' "${TITLE_WORKFLOW}" 'PR commit-range validation is missing'
require_fixed 'types: [closed]' "${CLEANUP_WORKFLOW}" 'branch cleanup workflow does not run on closed PRs'
require_fixed 'github.event.pull_request.merged == true' "${CLEANUP_WORKFLOW}" 'branch cleanup does not require merged PRs'
require_fixed 'github.event.pull_request.head.repo.full_name == github.repository' "${CLEANUP_WORKFLOW}" 'branch cleanup lacks same-repository guard'

if grep -Eq '"(governance|docs|ci|chore): "\*' "${TITLE_WORKFLOW}"; then
  fail 'unversioned conventional-title exception remains in PR title validation'
fi

echo "GitHub four-book governance, scoped CI, direct testing-package delivery, release, and repository controls passed for candidate ${expected}."
