#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TRIGGER_WORKFLOW="${ROOT_DIR}/.github/workflows/release-trigger.yml"
RELEASE_WORKFLOW="${ROOT_DIR}/.github/workflows/release.yml"

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

test -f "${TRIGGER_WORKFLOW}" || fail "release trigger workflow is missing"
test -f "${RELEASE_WORKFLOW}" || fail "release workflow is missing"

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

echo "Release trigger contract tests passed."
