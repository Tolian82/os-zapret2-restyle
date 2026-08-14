#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TRIGGER_WORKFLOW="${ROOT_DIR}/.github/workflows/release-trigger.yml"
RELEASE_WORKFLOW="${ROOT_DIR}/.github/workflows/release.yml"
PUBLICATION="${ROOT_DIR}/docs/GITHUB_PUBLICATION.md"
PRINCIPLES="${ROOT_DIR}/docs/PROJECT_PRINCIPLES.md"
README="${ROOT_DIR}/README.md"

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

test -f "${TRIGGER_WORKFLOW}" || fail "release trigger workflow is missing"
test -f "${RELEASE_WORKFLOW}" || fail "release workflow is missing"
test -s "${PUBLICATION}" || fail "release publication authority is missing"
test -s "${PRINCIPLES}" || fail "project principles are missing"
test -s "${README}" || fail "README is missing"

grep -Fq 'branches: [main]' "${TRIGGER_WORKFLOW}" || fail "trigger is not limited to main"
grep -Fq -- '- VERSION' "${TRIGGER_WORKFLOW}" || fail "trigger is not limited to VERSION changes"
grep -Fq 'actions: write' "${TRIGGER_WORKFLOW}" || fail "actions write permission is missing"
grep -Fq 'contents: write' "${TRIGGER_WORKFLOW}" || fail "contents write permission is missing"
grep -Fq '[[ "${REVISION}" == "1" ]]' "${TRIGGER_WORKFLOW}" || fail "release revision gate is missing"
grep -Fq '^v${ESCAPED_VERSION}_1:\ Prepare\ release\ v${ESCAPED_VERSION}' "${TRIGGER_WORKFLOW}" || fail "versioned release commit subject gate is missing"
grep -Fq 'git rev-list -n 1 "refs/tags/${TAG}"' "${TRIGGER_WORKFLOW}" || fail "existing tag target is not verified"
grep -Fq 'git tag -a "${TAG}" "${GITHUB_SHA}"' "${TRIGGER_WORKFLOW}" || fail "annotated tag creation is missing"
grep -Fq 'gh release view "${TAG}"' "${TRIGGER_WORKFLOW}" || fail "published release idempotence check is missing"
grep -Fq 'gh workflow run release.yml --ref "${TAG}"' "${TRIGGER_WORKFLOW}" || fail "release dispatch is missing"
grep -Fq 'workflow_dispatch:' "${RELEASE_WORKFLOW}" || fail "release workflow cannot be dispatched"
grep -Fq 'prerelease: false' "${RELEASE_WORKFLOW}" || fail "full release is still published as a testing prerelease"
grep -Fq 'Publish pkg repository' "${RELEASE_WORKFLOW}" || fail "full release does not deploy the pkg repository"
grep -Fq 'pages/FreeBSD:15:amd64' "${RELEASE_WORKFLOW}" || fail "full release does not verify FreeBSD 15 pkg-repository outputs"

grep -Fiq 'second numeric component' "${PRINCIPLES}" || fail "canonical second-version-component authority is missing"
grep -Fiq 'assistant must never initiate' "${PRINCIPLES}" || fail "second-version-component owner gate is missing"
grep -Fiq 'full release != second-component change' "${PRINCIPLES}" || fail "release/second-component implication is not explicit"
grep -Fiq 'README.md' "${PRINCIPLES}" || fail "canonical full-release README revision gate is missing"
grep -Fiq 'Owner-controlled second numeric component' "${PUBLICATION}" || fail "publication procedure lacks second-component authority"
grep -Fiq 'Every full release preparation must also perform a complete `README.md` revision' "${PUBLICATION}" || fail "publication procedure lacks README release review"
grep -Fiq 'Full Web/pkg release' "${README}" || fail "README does not expose the full Web/pkg release"
grep -Fiq 'Current development candidate' "${README}" || fail "README does not distinguish the development candidate"

echo "Release trigger and full-release policy contract tests passed."
