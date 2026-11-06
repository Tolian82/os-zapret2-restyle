#!/bin/sh
# Bundle signed FreeBSD curl privately; pinned release inputs must match.
set -eu

DEST=${1:?usage: build-curl-impersonate.sh DEST}
command -v pkg >/dev/null 2>&1 || { echo 'ERROR: pkg is required' >&2; exit 1; }
command -v sha256 >/dev/null 2>&1 || { echo 'ERROR: sha256 is required' >&2; exit 1; }
# Qualified native builder passes this exact version from compatibility.json.
# Exploratory historical callers may omit it, but cannot publish a release.
PINNED_VERSION=${ZAPRET2_CURL_PIN_VERSION:-}
if [ -n "${PINNED_VERSION}" ]; then
    printf '%s\n' "${PINNED_VERSION}" |
        LC_ALL=C grep -Eq '^[0-9A-Za-z][0-9A-Za-z._,+~$-]{0,127}$' || {
        echo 'ERROR: invalid curl pin version' >&2
        exit 1
    }
fi

TMP=$(mktemp -d /tmp/restyle-curl-impersonate.XXXXXX)
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
mkdir -p "${TMP}/repos" "${TMP}/packages" "${TMP}/root"

cat > "${TMP}/repos/FreeBSD.conf" <<'CONFIG'
FreeBSD: {
  url: "pkg+https://pkg.FreeBSD.org/${ABI}/latest",
  mirror_type: "srv",
  signature_type: "fingerprints",
  fingerprints: "/usr/share/keys/pkg",
  enabled: yes
}
CONFIG

# FreeBSD latest package metadata may target a newer 15.x userland.
# Permit OSVERSION drift only for signed catalog access and package fetch;
# the fetched binary must still actually run on the 15.0 appliance/CI.
IGNORE_OSVERSION=yes pkg -o REPOS_DIR="${TMP}/repos" update -f -r FreeBSD
# Signed repository metadata carries the semantic version. FreeBSD archive
# names may append a repository-specific ~N$build suffix: do not mistake
# that filename suffix for the pkg version. SHA-256 still pins exact bytes.
CATALOG_VERSION=$(IGNORE_OSVERSION=yes pkg -o REPOS_DIR="${TMP}/repos" \
    rquery -r FreeBSD '%v' curl-impersonate)
printf '%s\n' "${CATALOG_VERSION}" |
    LC_ALL=C grep -Eq '^[0-9A-Za-z][0-9A-Za-z._,+~$-]{0,127}$' || {
    echo 'ERROR: curl-impersonate signed catalog version invalid or missing' >&2
    exit 1
}
if [ -n "${PINNED_VERSION}" ] &&
   [ "${CATALOG_VERSION}" != "${PINNED_VERSION}" ]; then
    echo "ERROR: pinned curl-impersonate ${PINNED_VERSION} unavailable (got ${CATALOG_VERSION})" >&2
    exit 1
fi
IGNORE_OSVERSION=yes pkg -o REPOS_DIR="${TMP}/repos" fetch -y -r FreeBSD -o "${TMP}/packages" curl-impersonate

PKG_FILE=$(find "${TMP}/packages" -type f -name 'curl-impersonate-*.pkg' | head -n 1)
[ -n "${PKG_FILE}" ] && [ -f "${PKG_FILE}" ] || {
    echo 'ERROR: signed FreeBSD latest curl-impersonate package not found' >&2
    exit 1
}
tar -xf "${PKG_FILE}" -C "${TMP}/root"
ROOT="${TMP}/root/usr/local"
BIN="${ROOT}/bin/curl-impersonate"
[ -f "${BIN}" ] || { echo 'ERROR: private curl binary missing' >&2; exit 1; }
[ -x "${BIN}" ] || { echo 'ERROR: private curl binary is not executable' >&2; exit 1; }

# Select a concrete Chrome wrapper shipped by the actual package. Never pin
# a browser version; this is a package-local discovery, not a network fallback.
PROFILE=$(find "${ROOT}/bin" -type f -name 'curl_chrome[0-9]*' |
    sed -n 's|.*/curl_\(chrome[0-9][0-9]*\)$|\1|p' |
    awk '{v=$0; sub(/^chrome/, "", v); print v " " $0}' |
    sort -nr | head -n 1 | awk '{print $2}')
[ -n "${PROFILE}" ] || {
    echo 'ERROR: FreeBSD curl-impersonate has no supported Chrome wrapper' >&2
    exit 1
}
LICENSE_DIR=$(find "${ROOT}/share/licenses" -mindepth 1 -maxdepth 1 -type d -name 'curl-impersonate-*' | head -n 1)
[ -n "${LICENSE_DIR}" ] || { echo 'ERROR: curl-impersonate licenses are missing' >&2; exit 1; }

# The signed pkg catalogue, not the archive filename's build suffix, owns
# semantic version. Exact fetched archive identity is separately SHA-pinned.
VERSION="${CATALOG_VERSION}"
ABI=$(pkg config abi)
VERSION_OUT=$("${BIN}" -V)
printf '%s\n' "${VERSION_OUT}" | grep -q 'HTTP3' || {
    echo 'ERROR: private curl does not advertise HTTP3 support' >&2
    exit 1
}
printf '%s\n' "${VERSION_OUT}" | grep -Eiq '^Protocols:.*(^|[[:space:]])https([[:space:]]|$)' || {
    echo 'ERROR: private curl does not advertise HTTPS support' >&2
    exit 1
}
rm -rf "${DEST}"
mkdir -p "${DEST}/bin" "${DEST}/licenses"
cp "${BIN}" "${DEST}/bin/curl-impersonate"
chmod 755 "${DEST}/bin/curl-impersonate"
cp -R "${LICENSE_DIR}/." "${DEST}/licenses/"
printf '%s\n' "${PROFILE}" > "${DEST}/CHROME_PROFILE"
printf '%s\n' "${VERSION}" > "${DEST}/UPSTREAM_VERSION"
printf '%s\n' "${ABI}" > "${DEST}/FREEBSD_ABI"
sha256 -q "${PKG_FILE}" > "${DEST}/SOURCE_PKG_SHA256"
sha256 -q "${DEST}/bin/curl-impersonate" > "${DEST}/BINARY_SHA256"
echo "==> signed FreeBSD curl-impersonate: version=${VERSION}, profile=${PROFILE}, pinned=$([ -n "${PINNED_VERSION}" ] && echo yes || echo no)"
echo "==> source pkg SHA256: $(cat "${DEST}/SOURCE_PKG_SHA256")"
