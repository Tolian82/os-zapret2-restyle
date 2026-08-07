#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
CI="${ROOT_DIR}/.github/workflows/ci.yml"
RELEASE="${ROOT_DIR}/.github/workflows/release.yml"
MATRIX="${ROOT_DIR}/docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md"
VERSION_FILE="${ROOT_DIR}/VERSION"
MAKEFILE="${ROOT_DIR}/Makefile"

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

for file in "${CI}" "${RELEASE}" "${MATRIX}" "${VERSION_FILE}" "${MAKEFILE}"
do
    [ -s "${file}" ] || fail "required file is missing: ${file}"
done

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(awk -F= '
    /^PLUGIN_REVISION=/ {
        gsub(/[[:space:]]/, "", $2)
        print $2
        exit
    }
' "${MAKEFILE}")

case "${revision}" in
    ''|*[!0-9]*) fail 'invalid plugin revision' ;;
esac

if [ "${revision}" -gt 0 ]; then
    candidate="os-zapret2-restyle-${version}_${revision}.pkg"
else
    candidate="os-zapret2-restyle-${version}.pkg"
fi

grep -Fq 'release: "15.0"' "${CI}" || fail 'PR package build does not use FreeBSD 15.0'
grep -Fq "release: '15.0'" "${RELEASE}" || fail 'release package build does not use FreeBSD 15.0'

if grep -REn "release:[[:space:]]*['\"]?14([.]|['\"]|$)" \
    "${ROOT_DIR}/.github/workflows"
then
    fail 'a GitHub workflow still selects FreeBSD 14'
fi

grep -Fq 'freebsd-version -u' "${CI}" || fail 'PR package build does not verify the VM major version'
grep -Fq '.abi == "FreeBSD:15:amd64"' "${CI}" || fail 'PR package inspection does not enforce FreeBSD 15 ABI'
grep -Fq '.arch == "freebsd:15:x86:64"' "${CI}" || fail 'PR package inspection does not enforce FreeBSD 15 architecture'
grep -Fq 'tar -tf dist/*.pkg > "${contents}"' "${CI}" || fail 'package contents are not captured without a truncation pipe'
grep -Fq 'tar -xOf dist/*.pkg +MANIFEST > "${manifest}"' "${CI}" || fail 'package manifest is not captured before inspection'

grep -Fq "Current corrective candidate: \`${candidate}\`" "${MATRIX}" ||
    fail "live matrix does not select the current corrective package: ${candidate}"
grep -Fq 'Required package ABI: `FreeBSD:15:amd64`' "${MATRIX}" ||
    fail 'live matrix does not require the FreeBSD 15 ABI'
if grep -Fq 'Current corrective candidate: `os-zapret2-restyle-0.3.2_46.pkg`' "${MATRIX}"; then
    fail 'the incompatible revision 46 package remains selected for live verification'
fi

sh -n "$0"
echo "PASS: all GitHub package builds and ${candidate} are restricted to FreeBSD 15 amd64"
