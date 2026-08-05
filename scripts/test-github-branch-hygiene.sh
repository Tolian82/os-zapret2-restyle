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
  test -s "${file}" || {
    echo "Missing or empty GitHub governance file: ${file}" >&2
    exit 1
  }
done

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(sed -n 's/^PLUGIN_REVISION=[[:space:]]*//p' "${MAKEFILE}" | head -1)

printf '%s\n' "${version}" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$'
printf '%s\n' "${revision}" | grep -Eq '^[0-9]+$'

expected="v${version}"
if [ -n "${revision}" ] && [ "${revision}" != "0" ]; then
  expected="${expected}_${revision}"
fi

grep -Eq '^Status:[[:space:]]+Active$' "${ACTIVE_DECISION}"
grep -Eq '^Status:[[:space:]]+Active$' "${TITLE_DECISION}"
grep -Eq '^Status:[[:space:]]+Superseded' "${OLD_DECISION}"
grep -Fq 'docs/GITHUB_PUBLICATION.md' "${AGENTS}"
grep -Fq 'DEC-2026-08-05-universal-versioned-github-titles.md' "${AGENTS}"
grep -Fq 'DEC-2026-08-05-universal-versioned-github-titles.md' "${INDEX}"
grep -Fq 'DEC-2026-08-05-universal-versioned-github-titles.md' "${WORKFLOW_SUMMARY}"

grep -Fq 'every work or repair commit subject' "${AGENTS}"
grep -Fq 'final squash commit subject' "${AGENTS}"
grep -Fq 'pull-request titles' "${PUBLICATION}"
grep -Fq 'same-scope repair commit subjects' "${PUBLICATION}"
grep -Fq 'final squash commit subjects in `main`' "${PUBLICATION}"
grep -Fq 'Governance/documentation/CI-only work' "${PUBLICATION}"

grep -Fq 'concurrency:' "${CI}"
grep -Fq 'cancel-in-progress:' "${CI}"
grep -Fq 'Classify changed paths' "${CI}"
grep -Fq "github.event_name == 'pull_request' && needs.changes.outputs.package == 'true'" "${CI}"
grep -Fq 'Verify main integrity' "${CI}"
grep -Fq 'Invalid main commit subject' "${CI}"
grep -Fq 'Required format: ${EXPECTED}: <logical change>' "${CI}"

grep -Fq 'concurrency:' "${TITLE_WORKFLOW}"
grep -Fq 'Validate versioned PR and commit subjects' "${TITLE_WORKFLOW}"
grep -Fq 'git log --format=%s "${BASE_SHA}..${HEAD_SHA}"' "${TITLE_WORKFLOW}"
grep -Fq 'Invalid pull-request title' "${TITLE_WORKFLOW}"
grep -Fq 'Invalid commit subject' "${TITLE_WORKFLOW}"
grep -Fq 'Required format: ${expected}: <logical change>' "${TITLE_WORKFLOW}"

if grep -Eq '"(governance|docs|ci|chore): "\*' "${TITLE_WORKFLOW}"; then
  echo 'Unversioned conventional-title exception remains in PR title validation.' >&2
  exit 1
fi

if grep -Eq 'Governance, documentation, (and )?CI-only changes may use conventional' "${ACTIVE_DECISION}"; then
  echo 'Active decision still permits unversioned conventional titles.' >&2
  exit 1
fi

grep -Fq 'types: [closed]' "${CLEANUP_WORKFLOW}"
grep -Fq 'github.event.pull_request.merged == true' "${CLEANUP_WORKFLOW}"
grep -Fq 'github.event.pull_request.head.repo.full_name == github.repository' "${CLEANUP_WORKFLOW}"

echo "GitHub delivery governance tests passed for package candidate ${expected}."
