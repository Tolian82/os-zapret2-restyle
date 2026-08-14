#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TRIGGER_WORKFLOW="${ROOT_DIR}/.github/workflows/release-trigger.yml"
RELEASE_WORKFLOW="${ROOT_DIR}/.github/workflows/release.yml"
PUBLICATION="${ROOT_DIR}/docs/GITHUB_PUBLICATION.md"
PRINCIPLES="${ROOT_DIR}/docs/PROJECT_PRINCIPLES.md"
DOC_RULES="${ROOT_DIR}/docs/DOCUMENTATION_RULES.md"
README="${ROOT_DIR}/README.md"

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

for file in "${TRIGGER_WORKFLOW}" "${RELEASE_WORKFLOW}" "${PUBLICATION}" "${PRINCIPLES}" "${DOC_RULES}" "${README}"
do
    test -s "${file}" || fail "missing release/documentation authority: ${file}"
done

# Release trigger classifies every main merge so a full release can use the current _N candidate.
grep -Fq 'branches: [main]' "${TRIGGER_WORKFLOW}" || fail "release trigger is not limited to main"
if grep -Fq -- '- VERSION' "${TRIGGER_WORKFLOW}"; then
    fail "release trigger is still path-limited to VERSION changes"
fi
grep -Fq 'actions: write' "${TRIGGER_WORKFLOW}" || fail "actions write permission is missing"
grep -Fq 'contents: write' "${TRIGGER_WORKFLOW}" || fail "contents write permission is missing"
grep -Fq 'PREVIOUS_VERSION=$(git show "${GITHUB_SHA}^:VERSION"' "${TRIGGER_WORKFLOW}" || fail "previous VERSION classification is missing"
grep -Fq 'RELEASE_PATTERN="^v${ESCAPED_VERSION}_${REVISION}: Prepare release v${ESCAPED_VERSION}' "${TRIGGER_WORKFLOW}" || fail "current-candidate release subject gate is missing"
grep -Fq 'A third-component development-stage transition must begin at package revision _1.' "${TRIGGER_WORKFLOW}" || fail "third-component revision-reset gate is missing"
grep -Fq 'A first/second-component transition requires an explicit full-release preparation merge.' "${TRIGGER_WORKFLOW}" || fail "second-component full-release gate is missing"
grep -Fq 'if: steps.release.outputs.publish == '\''true'\''' "${TRIGGER_WORKFLOW}" || fail "release publication is not conditional on explicit release preparation"
grep -Fq 'git rev-list -n 1 "refs/tags/${TAG}"' "${TRIGGER_WORKFLOW}" || fail "existing tag target is not verified"
grep -Fq 'git tag -a "${TAG}" "${GITHUB_SHA}"' "${TRIGGER_WORKFLOW}" || fail "annotated tag creation is missing"
grep -Fq 'gh release view "${TAG}"' "${TRIGGER_WORKFLOW}" || fail "published release idempotence check is missing"
grep -Fq 'gh workflow run release.yml --ref "${TAG}"' "${TRIGGER_WORKFLOW}" || fail "release dispatch is missing"

# Full release pipeline remains a normal GitHub Release + OPNsense Pages/pkg repository.
grep -Fq 'workflow_dispatch:' "${RELEASE_WORKFLOW}" || fail "release workflow cannot be dispatched"
grep -Fq 'prerelease: false' "${RELEASE_WORKFLOW}" || fail "full release is still marked as a testing prerelease"
grep -Fq 'Publish pkg repository' "${RELEASE_WORKFLOW}" || fail "full release does not deploy the pkg repository"
grep -Fq 'pages/FreeBSD:15:amd64' "${RELEASE_WORKFLOW}" || fail "full release does not verify FreeBSD 15 pkg-repository outputs"

# Canonical documentation rules encode the three-level version semantics.
grep -Fiq 'second numeric component defines the long-lived project-state line' "${DOC_RULES}" || fail "second-component PROJECT_STATE rule is missing"
grep -Fiq 'third numeric component identifies the current development stage' "${DOC_RULES}" || fail "third-component stage rule is missing"
grep -Fiq 'package revision suffix `_N` identifies the concrete patch/iteration' "${DOC_RULES}" || fail "revision START_HERE rule is missing"
grep -Fiq 'third-component transition is not a full release by itself' "${DOC_RULES}" || fail "third-component non-release rule is missing"
grep -Fiq 'full-release publication is independent of the package revision suffix' "${DOC_RULES}" || fail "current-revision full-release rule is missing"
grep -Fiq 'full release may use the current exact package candidate' "${PRINCIPLES}" || fail "project principles still force release-only revision reset"
grep -Fiq 'full release does not reset `PLUGIN_REVISION` merely because it is a release' "${PUBLICATION}" || fail "publication procedure still forces release revision reset"

grep -Fiq 'Full Web/pkg release' "${README}" || fail "README does not expose the full Web/pkg release"
grep -Fiq 'Current development candidate' "${README}" || fail "README does not distinguish the development candidate"

echo "Release trigger, version-stage, and full-release policy contract tests passed."
