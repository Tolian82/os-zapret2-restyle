#!/bin/sh

set -eu

RELEASE_WORKFLOW=".github/workflows/release.yml"
TRIGGER_WORKFLOW=".github/workflows/release-trigger.yml"

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

[ "$(grep -c 'actions/checkout@v6' "${RELEASE_WORKFLOW}")" -eq 2 ] ||
    fail "release workflow does not use checkout v6 in both jobs"
grep -q 'actions/checkout@v6' "${TRIGGER_WORKFLOW}" ||
    fail "release trigger does not use checkout v6"
grep -q 'actions/upload-artifact@v7' "${RELEASE_WORKFLOW}" ||
    fail "release workflow does not use upload-artifact v7"
grep -q 'actions/download-artifact@v8' "${RELEASE_WORKFLOW}" ||
    fail "release workflow does not use download-artifact v8"
grep -q 'softprops/action-gh-release@v3' "${RELEASE_WORKFLOW}" ||
    fail "release workflow does not use Node 24 action-gh-release v3"
grep -q 'actions/deploy-pages@v5' "${RELEASE_WORKFLOW}" ||
    fail "release workflow does not use Node 24 deploy-pages v5"

if grep -q 'actions/upload-pages-artifact@v4' "${RELEASE_WORKFLOW}"; then
    fail "release workflow still uses upload-pages-artifact v4 with an internal Node 20 uploader"
fi

grep -q 'name: github-pages' "${RELEASE_WORKFLOW}" ||
    fail "release workflow does not upload the Pages artifact with the required name"
grep -q 'artifact.tar' "${RELEASE_WORKFLOW}" ||
    fail "release workflow does not prepare the required Pages tar artifact"

echo "PASS: release workflows use Node.js 24-compatible actions"
