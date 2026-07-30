#!/bin/sh
# Verify metadata embedded in the release package before publication.

set -eu

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "${REPO_ROOT}"

fail()
{
    echo "ERROR: $*" >&2
    exit 1
}

[ -f VERSION ] || fail "VERSION file is missing"
[ -f Makefile ] || fail "Makefile is missing"

VERSION_VALUE=$(tr -d '[:space:]' < VERSION)
REVISION=$(sed -n 's/^PLUGIN_REVISION=[[:space:]]*//p' Makefile | head -1)

if [ -n "${REVISION}" ] && [ "${REVISION}" != "0" ]; then
    PACKAGE_VERSION="${VERSION_VALUE}_${REVISION}"
else
    PACKAGE_VERSION="${VERSION_VALUE}"
fi

PACKAGE_NAME="os-zapret2-restyle"
PACKAGE_PATH="${1:-dist/${PACKAGE_NAME}-${PACKAGE_VERSION}.pkg}"
EXPECTED_WWW="https://github.com/Tolian82/os-zapret2-restyle"

[ -f "${PACKAGE_PATH}" ] || fail "package is missing: ${PACKAGE_PATH}"
command -v jq >/dev/null 2>&1 || fail "jq is required"
command -v tar >/dev/null 2>&1 || fail "tar is required"

MANIFEST=$(tar -xOf "${PACKAGE_PATH}" +MANIFEST) ||
    fail "cannot read +MANIFEST from ${PACKAGE_PATH}"

ACTUAL_NAME=$(printf '%s\n' "${MANIFEST}" | jq -er '.name') ||
    fail "package manifest has no valid name"
ACTUAL_VERSION=$(printf '%s\n' "${MANIFEST}" | jq -er '.version') ||
    fail "package manifest has no valid version"
ACTUAL_WWW=$(printf '%s\n' "${MANIFEST}" | jq -er '.www') ||
    fail "package manifest has no valid www"

[ "${ACTUAL_NAME}" = "${PACKAGE_NAME}" ] ||
    fail "package name mismatch: expected ${PACKAGE_NAME}, got ${ACTUAL_NAME}"
[ "${ACTUAL_VERSION}" = "${PACKAGE_VERSION}" ] ||
    fail "package version mismatch: expected ${PACKAGE_VERSION}, got ${ACTUAL_VERSION}"
[ "${ACTUAL_WWW}" = "${EXPECTED_WWW}" ] ||
    fail "package www mismatch: expected ${EXPECTED_WWW}, got ${ACTUAL_WWW}"

printf 'Verified package metadata: %s %s %s\n' \
    "${ACTUAL_NAME}" "${ACTUAL_VERSION}" "${ACTUAL_WWW}"
