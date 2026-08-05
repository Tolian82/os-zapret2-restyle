#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
AGENTS="${ROOT_DIR}/AGENTS.md"
INDEX="${ROOT_DIR}/docs/INDEX.md"
PUBLICATION="${ROOT_DIR}/docs/GITHUB_PUBLICATION.md"
WORKFLOW_SUMMARY="${ROOT_DIR}/docs/GITHUB_WORKFLOW.md"
ACTIVE_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-05-efficient-github-delivery.md"
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
printf '%s\n' "${revision}" | grep -Eq '^[1-9][0-9]*$'

grep -Eq '^Status:[[:space:]]+Active$' "${ACTIVE_DECISION}"
grep -Eq '^Status:[[:space:]]+Superseded' "${OLD_DECISION}"
grep -Fq 'docs/GITHUB_PUBLICATION.md' "${AGENTS}"
grep -Fq 'DEC-2026-08-05-efficient-github-delivery.md' "${INDEX}"
grep -Fq 'DEC-2026-08-05-efficient-github-delivery.md' "${WORKFLOW_SUMMARY}"

grep -Fq 'concurrency:' "${CI}"
grep -Fq 'cancel-in-progress:' "${CI}"
grep -Fq 'Classify changed paths' "${CI}"
grep -Fq "github.event_name == 'pull_request' && needs.changes.outputs.package == 'true'" "${CI}"
grep -Fq 'Verify main integrity' "${CI}"

grep -Fq 'concurrency:' "${TITLE_WORKFLOW}"
grep -Fq 'governance: ' "${TITLE_WORKFLOW}"
grep -Fq 'Detect packaged-plugin changes' "${CI}"

grep -Fq 'types: [closed]' "${CLEANUP_WORKFLOW}"
grep -Fq 'github.event.pull_request.merged == true' "${CLEANUP_WORKFLOW}"
grep -Fq 'github.event.pull_request.head.repo.full_name == github.repository' "${CLEANUP_WORKFLOW}"

echo "GitHub delivery governance tests passed for package candidate ${version}_${revision}."
