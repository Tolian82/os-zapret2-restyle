#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
AGENTS="${ROOT_DIR}/AGENTS.md"
INDEX="${ROOT_DIR}/docs/INDEX.md"
PUBLICATION="${ROOT_DIR}/docs/GITHUB_PUBLICATION.md"
WORKFLOW_SUMMARY="${ROOT_DIR}/docs/GITHUB_WORKFLOW.md"
CONVENTIONS="${ROOT_DIR}/docs/WORKING_CONVENTIONS.md"
DEVELOPMENT="${ROOT_DIR}/docs/DEVELOPMENT_GUIDE.md"
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
PLUGIN_FIRST_RULE='MANDATORY: Use the connected GitHub plugin first for every repository operation; use another transport only when the plugin lacks the required function or confirmed permission.'

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
  grep -Fq "${pattern}" "${file}" || fail "${description}"
}

for file in \
  "${AGENTS}" \
  "${INDEX}" \
  "${PUBLICATION}" \
  "${WORKFLOW_SUMMARY}" \
  "${CONVENTIONS}" \
  "${DEVELOPMENT}" \
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

[ "$(sed -n '1p' "${AGENTS}")" = "${PLUGIN_FIRST_RULE}" ] || \
  fail 'AGENTS first line does not require the GitHub plugin first'
[ "$(sed -n '1p' "${PUBLICATION}")" = "${PLUGIN_FIRST_RULE}" ] || \
  fail 'GitHub publication authority first line does not require the GitHub plugin first'
require_fixed 'GITHUB PLUGIN FIRST' "${PUBLICATION}" 'publication authority lacks the GitHub-plugin-first section'
require_fixed 'The connected GitHub plugin is the mandatory first transport' "${AGENTS}" 'AGENTS lacks the GitHub-plugin-first transport rule'
require_fixed 'The fallback covers only that missing operation' "${PUBLICATION}" 'fallback scope is not constrained'

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(sed -n 's/^PLUGIN_REVISION=[[:space:]]*//p' "${MAKEFILE}" | head -1)

printf '%s\n' "${version}" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' || fail 'VERSION is invalid'
printf '%s\n' "${revision}" | grep -Eq '^[0-9]+$' || fail 'PLUGIN_REVISION is invalid'

expected="v${version}"
if [ "${revision}" != "0" ]; then
  expected="${expected}_${revision}"
fi

grep -Eq '^Status:[[:space:]]+Active$' "${EVIDENCE_DECISION}" || fail 'evidence-first decision is not active'
grep -Eq '^Status:[[:space:]]+Active$' "${EFFICIENT_DECISION}" || fail 'efficient delivery decision is not active'
grep -Eq '^Status:[[:space:]]+Active$' "${TITLE_DECISION}" || fail 'universal title decision is not active'
grep -Eq '^Status:[[:space:]]+Superseded' "${OLD_DECISION}" || fail 'old atomic decision is not superseded'

require_fixed 'DEC-2026-08-06-evidence-first-github-operations.md' "${AGENTS}" 'AGENTS does not name evidence-first authority'
require_fixed 'PRE-MUTATION INVENTORY' "${AGENTS}" 'AGENTS lacks pre-mutation inventory'
require_fixed 'at most one unchanged rerun' "${AGENTS}" 'AGENTS lacks bounded infrastructure retry rule'
require_fixed 'Publishing an already verified candidate is a release operation, not a code PR.' "${AGENTS}" 'AGENTS does not separate candidate publication from code PRs'
require_fixed 'Duplicate trackers and unbounded' "${AGENTS}" 'AGENTS does not prohibit unbounded tracking'

require_fixed 'PRE-MUTATION INVENTORY' "${PUBLICATION}" 'publication authority lacks inventory gate'
require_fixed 'TESTING PRERELEASE PUBLICATION' "${PUBLICATION}" 'publication authority lacks candidate path'
require_fixed 'exact workflow run ID, artifact ID/name, and digest' "${PUBLICATION}" 'artifact identity contract is missing'
require_fixed 'make zero source changes' "${PUBLICATION}" 'external failure freeze is missing'
require_fixed 'at most one unchanged failed-job or' "${PUBLICATION}" 'bounded rerun rule is missing'
require_fixed 'Do not create a PR merely to attach an existing package asset.' "${PUBLICATION}" 'publication PR prohibition is missing'
require_fixed 'vX.Y.Z_1: Prepare release vX.Y.Z' "${PUBLICATION}" 'versioned release preparation title is missing'

require_fixed 'DEC-2026-08-06-evidence-first-github-operations.md' "${INDEX}" 'INDEX does not prioritize evidence-first decision'
require_fixed 'one active publication run' "${INDEX}" 'INDEX lacks one-run publication rule'
require_fixed 'GitHub sections of `docs/WORKING_CONVENTIONS.md` and `docs/DEVELOPMENT_GUIDE.md`' "${EVIDENCE_DECISION}" 'lower-priority GitHub sections are not explicitly superseded'
require_fixed 'mandatory Draft PRs' "${EVIDENCE_DECISION}" 'mandatory Draft conflict is not explicitly superseded'
require_fixed 'full-document rereading' "${EVIDENCE_DECISION}" 'full-reread conflict is not explicitly superseded'

# Active top-level GitHub authorities must not reintroduce superseded behavior.
if grep -Eq 'open one Draft PR|Draft PR creation|complete its full mandatory reading order|no substantive project response precedes complete documentation recovery' \
  "${AGENTS}" "${PUBLICATION}" "${WORKFLOW_SUMMARY}"
then
  fail 'active top-level GitHub authority contains superseded Draft/full-reread wording'
fi

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

require_fixed 'concurrency:' "${TITLE_WORKFLOW}" 'PR title concurrency is missing'
require_fixed 'Validate versioned PR and commit subjects' "${TITLE_WORKFLOW}" 'versioned PR/commit job is missing'
require_fixed 'Invalid pull-request title' "${TITLE_WORKFLOW}" 'PR title rejection is missing'
require_fixed 'Invalid commit subject' "${TITLE_WORKFLOW}" 'PR commit-subject rejection is missing'

require_fixed 'types: [closed]' "${CLEANUP_WORKFLOW}" 'cleanup workflow does not run on closed PRs'
require_fixed 'github.event.pull_request.merged == true' "${CLEANUP_WORKFLOW}" 'cleanup workflow does not require merged PRs'
require_fixed 'github.event.pull_request.head.repo.full_name == github.repository' "${CLEANUP_WORKFLOW}" 'cleanup workflow lacks same-repository guard'

echo "GitHub evidence-first governance tests passed for package candidate ${expected}."
