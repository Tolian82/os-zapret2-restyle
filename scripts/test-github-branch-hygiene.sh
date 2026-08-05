#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
AGENTS="${ROOT_DIR}/AGENTS.md"
INDEX="${ROOT_DIR}/docs/INDEX.md"
PUBLICATION="${ROOT_DIR}/docs/GITHUB_PUBLICATION.md"
WORKFLOW_SUMMARY="${ROOT_DIR}/docs/GITHUB_WORKFLOW.md"
ACTIVE_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-05-efficient-github-delivery.md"
TITLE_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md"
OLD_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-02-atomic-github-publication.md"
CI="${ROOT_DIR}/.github/workflows/ci.yml"
TITLE_WORKFLOW="${ROOT_DIR}/.github/workflows/pr-title.yml"
CLEANUP_WORKFLOW="${ROOT_DIR}/.github/workflows/cleanup-merged-branch.yml"
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
  grep -Fq "${pattern}" "${file}" || fail "${description}"
}

for file in \
  "${AGENTS}" \
  "${INDEX}" \
  "${PUBLICATION}" \
  "${WORKFLOW_SUMMARY}" \
  "${ACTIVE_DECISION}" \
  "${TITLE_DECISION}" \
  "${OLD_DECISION}" \
  "${CI}" \
  "${TITLE_WORKFLOW}" \
  "${CLEANUP_WORKFLOW}"
do
  test -s "${file}" || fail "missing or empty GitHub governance file: ${file}"
done

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(sed -n 's/^PLUGIN_REVISION=[[:space:]]*//p' "${MAKEFILE}" | head -1)

printf '%s\n' "${version}" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' || fail 'VERSION is invalid'
printf '%s\n' "${revision}" | grep -Eq '^[0-9]+$' || fail 'PLUGIN_REVISION is invalid'

expected="v${version}"
if [ -n "${revision}" ] && [ "${revision}" != "0" ]; then
  expected="${expected}_${revision}"
fi

grep -Eq '^Status:[[:space:]]+Active$' "${ACTIVE_DECISION}" || fail 'efficient delivery decision is not active'
grep -Eq '^Status:[[:space:]]+Active$' "${TITLE_DECISION}" || fail 'universal title decision is not active'
grep -Eq '^Status:[[:space:]]+Superseded' "${OLD_DECISION}" || fail 'old atomic decision is not superseded'

require_fixed 'docs/GITHUB_PUBLICATION.md' "${AGENTS}" 'AGENTS does not name publication authority'
require_fixed 'DEC-2026-08-05-universal-versioned-github-titles.md' "${AGENTS}" 'AGENTS does not name universal title decision'
require_fixed 'DEC-2026-08-05-universal-versioned-github-titles.md' "${INDEX}" 'INDEX does not name universal title decision'
require_fixed 'DEC-2026-08-05-universal-versioned-github-titles.md' "${WORKFLOW_SUMMARY}" 'workflow summary does not name universal title decision'

require_fixed 'every work or repair commit subject' "${AGENTS}" 'AGENTS does not require versioned work and repair commits'
require_fixed 'squash commit subject in `main`' "${AGENTS}" 'AGENTS does not require a versioned squash subject'
require_fixed 'pull-request titles' "${PUBLICATION}" 'publication rules do not cover pull-request titles'
require_fixed 'same-scope repair commit subjects' "${PUBLICATION}" 'publication rules do not cover repair commit subjects'
require_fixed 'final squash commit subjects in `main`' "${PUBLICATION}" 'publication rules do not cover squash commit subjects'
require_fixed 'Governance/documentation/CI-only work' "${PUBLICATION}" 'publication rules do not cover non-packaged changes'

require_fixed 'concurrency:' "${CI}" 'CI concurrency is missing'
require_fixed 'cancel-in-progress:' "${CI}" 'CI cancel-in-progress is missing'
require_fixed 'Classify changed paths' "${CI}" 'CI path classification is missing'
require_fixed "github.event_name == 'pull_request' && needs.changes.outputs.package == 'true'" "${CI}" 'package build is not path-gated'
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

if grep -Eq 'Governance, documentation, (and )?CI-only changes may use conventional' "${ACTIVE_DECISION}"; then
  fail 'active decision still permits unversioned conventional titles'
fi

require_fixed 'types: [closed]' "${CLEANUP_WORKFLOW}" 'cleanup workflow does not run on closed PRs'
require_fixed 'github.event.pull_request.merged == true' "${CLEANUP_WORKFLOW}" 'cleanup workflow does not require merged PRs'
require_fixed 'github.event.pull_request.head.repo.full_name == github.repository' "${CLEANUP_WORKFLOW}" 'cleanup workflow lacks same-repository guard'

echo "GitHub delivery governance tests passed for package candidate ${expected}."
