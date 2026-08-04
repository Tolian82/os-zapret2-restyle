#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
AGENTS="${ROOT_DIR}/AGENTS.md"
PUBLICATION="${ROOT_DIR}/docs/GITHUB_PUBLICATION.md"
WORKFLOW="${ROOT_DIR}/.github/workflows/cleanup-merged-branch.yml"
CI="${ROOT_DIR}/.github/workflows/ci.yml"
MAKEFILE="${ROOT_DIR}/Makefile"
VERSION_FILE="${ROOT_DIR}/VERSION"

grep -Fq 'Exactly one remote task branch may be created' "${AGENTS}"
grep -Fq 'Branch creation is the last preparation step' "${AGENTS}"
grep -Fq '`-clean`, `-final`, `-atomic`, `-fixed`, `-retry`, or `-publish`' "${AGENTS}"
grep -Fq 'A package patch and a project release are different operations.' "${AGENTS}"

grep -Fq 'REMOTE BRANCH BUDGET' "${PUBLICATION}"
grep -Fq 'exactly one remote task branch' "${PUBLICATION}"
grep -Fq 'No remote branch is created during preparation.' "${PUBLICATION}"
grep -Fq 'verify that the task branch no longer exists' "${PUBLICATION}"
grep -Fq 'PATCH VERSUS RELEASE' "${PUBLICATION}"

grep -Fq 'push:' "${WORKFLOW}"
grep -Fq 'branches: [main]' "${WORKFLOW}"
grep -Fq 'contents: write' "${WORKFLOW}"
grep -Fq 'commits/${COMMIT_SHA}/pulls' "${WORKFLOW}"
grep -Fq '.head.repo.full_name == $repository' "${WORKFLOW}"
grep -Fq 'git/refs/heads/${head_ref}' "${WORKFLOW}"

grep -Fq 'Test GitHub branch hygiene contract' "${CI}"
grep -Fq 'scripts/test-github-branch-hygiene.sh' "${CI}"

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(sed -n 's/^PLUGIN_REVISION=[[:space:]]*//p' "${MAKEFILE}" | head -1)

[ "${version}" = "0.3.2" ]
printf '%s\n' "${revision}" | grep -Eq '^[1-9][0-9]*$'

echo 'GitHub branch hygiene contract tests passed.'
