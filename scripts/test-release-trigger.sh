#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TRIGGER_WORKFLOW="${ROOT_DIR}/.github/workflows/release-trigger.yml"
RELEASE_WORKFLOW="${ROOT_DIR}/.github/workflows/release.yml"
GH_RULES="${ROOT_DIR}/docs/GITHUB_PUBLICATION.md"
DEV_RULES="${ROOT_DIR}/docs/PROJECT_PRINCIPLES.md"
DOC_RULES="${ROOT_DIR}/docs/DOCUMENTATION_RULES.md"
README="${ROOT_DIR}/README.md"

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

require_fixed()
{
    grep -Fq -- "$1" "$2" || fail "$3"
}

for file in "${TRIGGER_WORKFLOW}" "${RELEASE_WORKFLOW}" "${GH_RULES}" "${DEV_RULES}" "${DOC_RULES}" "${README}"
do
    test -s "${file}" || fail "missing release/rule authority: ${file}"
done

# Release trigger classifies every main merge so a full release can use the current _N candidate.
require_fixed 'branches: [main]' "${TRIGGER_WORKFLOW}" 'release trigger is not limited to main'
if grep -Fq -- '- VERSION' "${TRIGGER_WORKFLOW}"; then
    fail 'release trigger is still path-limited to VERSION changes'
fi
require_fixed 'actions: write' "${TRIGGER_WORKFLOW}" 'actions write permission is missing'
require_fixed 'contents: write' "${TRIGGER_WORKFLOW}" 'contents write permission is missing'
require_fixed 'PREVIOUS_VERSION=$(git show "${GITHUB_SHA}^:VERSION"' "${TRIGGER_WORKFLOW}" 'previous VERSION classification is missing'
require_fixed 'RELEASE_PATTERN="^v${ESCAPED_VERSION}_${REVISION}: Prepare release v${ESCAPED_VERSION}' "${TRIGGER_WORKFLOW}" 'current-candidate release subject gate is missing'
require_fixed 'A third-component development-stage transition must begin at package revision _1.' "${TRIGGER_WORKFLOW}" 'third-component revision-reset gate is missing'
require_fixed 'A first/second-component transition requires an explicit full-release preparation merge.' "${TRIGGER_WORKFLOW}" 'second-component full-release gate is missing'
require_fixed "if: steps.release.outputs.publish == 'true'" "${TRIGGER_WORKFLOW}" 'release publication is not conditional on explicit release preparation'
require_fixed 'git rev-list -n 1 "refs/tags/${TAG}"' "${TRIGGER_WORKFLOW}" 'existing tag target is not verified'
require_fixed 'git tag -a "${TAG}" "${GITHUB_SHA}"' "${TRIGGER_WORKFLOW}" 'annotated tag creation is missing'
require_fixed 'gh release view "${TAG}"' "${TRIGGER_WORKFLOW}" 'published release idempotence check is missing'
require_fixed 'gh workflow run release.yml --ref "${TAG}"' "${TRIGGER_WORKFLOW}" 'release dispatch is missing'

# Full release pipeline remains a normal GitHub Release + OPNsense Pages/pkg repository.
require_fixed 'workflow_dispatch:' "${RELEASE_WORKFLOW}" 'release workflow cannot be dispatched'
require_fixed 'prerelease: false' "${RELEASE_WORKFLOW}" 'full release is still marked as a testing prerelease'
require_fixed 'Publish pkg repository' "${RELEASE_WORKFLOW}" 'full release does not deploy the pkg repository'
require_fixed 'pages/FreeBSD:15:amd64' "${RELEASE_WORKFLOW}" 'full release does not verify FreeBSD 15 pkg-repository outputs'

# Version semantics now live only in the DEV rule book; documentation rotation and GitHub execution
# reference those stable rule IDs instead of duplicating the policy in a second authority.
require_fixed 'DEV-029.' "${DEV_RULES}" 'second-component project-state-line rule is missing'
require_fixed 'DEV-030.' "${DEV_RULES}" 'third-component development-stage rule is missing'
require_fixed 'DEV-031.' "${DEV_RULES}" 'package revision boundary rule is missing'
require_fixed 'DEV-035.' "${DEV_RULES}" 'third-component non-release rule is missing'
require_fixed 'DEV-036.' "${DEV_RULES}" 'owner-controlled second-component transition rule is missing'
require_fixed 'DEV-037.' "${DEV_RULES}" 'second-component full-release implication rule is missing'
require_fixed 'DEV-038.' "${DEV_RULES}" 'exact-current-candidate full-release rule is missing'
require_fixed 'DEV-039.' "${DEV_RULES}" 'full OPNsense release definition is missing'

require_fixed 'DOC-026.' "${DOC_RULES}" 'PROJECT_STATE second-component scope rule is missing'
require_fixed 'DOC-028.' "${DOC_RULES}" 'second-component state archive rollover rule is missing'
require_fixed 'DOC-038.' "${DOC_RULES}" 'README full-release review rule is missing'

require_fixed 'GH-041.' "${GH_RULES}" 'GitHub exact-current-candidate release rule is missing'
require_fixed 'GH-047.' "${GH_RULES}" 'GitHub second-component transition guard is missing'
require_fixed 'GH-048.' "${GH_RULES}" 'GitHub third-component transition guard is missing'
require_fixed 'GH-049.' "${GH_RULES}" 'ordinary main release-classification rule is missing'
require_fixed 'GH-050.' "${GH_RULES}" 'third-component release-trigger rule is missing'
require_fixed 'GH-051.' "${GH_RULES}" 'second-component release-trigger rule is missing'
require_fixed 'GH-052.' "${GH_RULES}" 'explicit release-preparation dispatch rule is missing'

# README describes the user-visible publication distinction without becoming a second normative policy.
require_fixed 'Full Web/pkg release' "${README}" 'README does not expose the full Web/pkg release'
require_fixed 'Current development candidate' "${README}" 'README does not distinguish the development candidate'
require_fixed 'DEV-027' "${README}" 'README does not route version semantics to the DEV rule book'
require_fixed 'GH-034' "${README}" 'README does not route publication mechanics to the GH rule book'

echo 'Release trigger, four-rule-book version semantics, and full-release policy contract tests passed.'
