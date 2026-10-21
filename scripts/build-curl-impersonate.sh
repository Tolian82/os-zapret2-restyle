#!/bin/sh
# Bundle the current signed FreeBSD latest curl-impersonate package privately.
set -eu

DEST=${1:?usage: build-curl-impersonate.sh DEST}
command -v pkg >/dev/null 2>&1 || { echo 'ERROR: pkg is required' >&2; exit 1; }
command -v sha256 >/dev/null 2>&1 || { echo 'ERROR: sha256 is required' >&2; exit 1; }

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

# Version is diagnostic information only; no version is a selection criterion.
VERSION=$(basename "${PKG_FILE}" .pkg | sed 's/^curl-impersonate-//')
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
echo "==> curl-impersonate from signed FreeBSD latest: profile=${PROFILE} (version recorded, not pinned)"
echo "==> source pkg SHA256: $(cat "${DEST}/SOURCE_PKG_SHA256")"
