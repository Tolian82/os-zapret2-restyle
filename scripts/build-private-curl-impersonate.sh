#!/bin/sh
# Bundle the current signed FreeBSD latest curl-impersonate package privately.
# This helper runs at package BUILD time, never during plugin installation.
set -eu

dest=${1:-}
[ -n "${dest}" ] || { echo 'usage: build-private-curl-impersonate.sh DEST' >&2; exit 64; }
command -v pkg >/dev/null 2>&1 || { echo 'pkg is required' >&2; exit 70; }
command -v sha256 >/dev/null 2>&1 || { echo 'sha256 is required' >&2; exit 70; }

abi=$(pkg config abi)
case "${abi}" in
    FreeBSD:15:amd64) ;;
    *) echo "unsupported build ABI: ${abi}" >&2; exit 70 ;;
esac

tmp=$(mktemp -d /tmp/zapret2-impersonate.XXXXXXXX)
trap 'rm -rf "${tmp}"' EXIT HUP INT TERM
repos="${tmp}/repos"
pkgs="${tmp}/pkgs"
root="${tmp}/root"
mkdir -p "${repos}" "${pkgs}" "${root}"

# Same signed FreeBSD latest acquisition pattern as ugorur/build-curl-h3.sh.
cat > "${repos}/FreeBSD.conf" <<'EOF'
FreeBSD: {
  url: "pkg+https://pkg.FreeBSD.org/${ABI}/latest",
  mirror_type: "srv",
  signature_type: "fingerprints",
  fingerprints: "/usr/share/keys/pkg",
  enabled: yes
}
EOF
pkg -o REPOS_DIR="${repos}" update -f -r FreeBSD
pkg -o REPOS_DIR="${repos}" fetch -y -r FreeBSD -o "${pkgs}" curl-impersonate

pkg_file=$(find "${pkgs}" -type f -name 'curl-impersonate-*.pkg' | head -1)
[ -n "${pkg_file}" ] && [ -s "${pkg_file}" ] || {
    echo 'signed FreeBSD latest curl-impersonate package was not fetched' >&2
    exit 70
}
tar -xf "${pkg_file}" -C "${root}"
src_bin="${root}/usr/local/bin/curl-impersonate"
[ -x "${src_bin}" ] || { echo 'package does not provide curl-impersonate' >&2; exit 70; }

# Wrapper names are generated from the presets supported by this exact package.
# Choose the numerically newest plain Chrome profile, not a pinned browser version.
profiles="${tmp}/chrome-profiles"
: > "${profiles}"
for wrapper in "${root}"/usr/local/bin/curl_chrome*; do
    [ -f "${wrapper}" ] || continue
    name=${wrapper##*/}
    suffix=${name#curl_chrome}
    case "${suffix}" in ''|*[!0-9]*) continue ;; esac
    grep -Fq -- '--impersonate' "${wrapper}" || continue
    printf '%s\n' "${suffix}" >> "${profiles}"
done
profile_number=$(sort -nr "${profiles}" | head -1)
[ -n "${profile_number}" ] || { echo 'no supported plain Chrome profile found' >&2; exit 70; }
profile="chrome${profile_number}"

license_dir=$(find "${root}/usr/local/share/licenses" -mindepth 1 -maxdepth 1 -type d -name 'curl-impersonate-*' | head -1)
[ -n "${license_dir}" ] || { echo 'curl-impersonate license directory is missing' >&2; exit 70; }
[ -d "${root}/usr/local/lib" ] || { echo 'curl-impersonate shared libraries are missing' >&2; exit 70; }

rm -rf "${dest}"
mkdir -p "${dest}/bin" "${dest}/libexec" "${dest}/lib" "${dest}/licenses"
cp "${src_bin}" "${dest}/libexec/curl-impersonate"
chmod 755 "${dest}/libexec/curl-impersonate"

# Keep the library private; do not install its soname into /usr/local/lib.
lib_count=0
for lib in "${root}"/usr/local/lib/libcurl-impersonate.so*; do
    [ -e "${lib}" ] || [ -L "${lib}" ] || continue
    cp -R "${lib}" "${dest}/lib/"
    lib_count=$((lib_count + 1))
done
[ "${lib_count}" -gt 0 ] || { echo 'private libcurl-impersonate is missing' >&2; exit 70; }
cp -R "${license_dir}/." "${dest}/licenses/"
printf '%s\n' "${profile}" > "${dest}/PROFILE"

# The entry point owns the profile and library search path. Callers do NOT need
# global linker paths, profile flags, curlrc, or a system curl replacement.
cat > "${dest}/bin/curl-impersonate" <<'EOF'
#!/bin/sh
set -eu
root=${0%/bin/curl-impersonate}
[ "${root}" != "${0}" ] || exit 70
profile=$(cat "${root}/PROFILE") || exit 70
case "${profile}" in chrome[0-9]*) ;; *) exit 70 ;; esac
export LD_LIBRARY_PATH="${root}/lib"
exec "${root}/libexec/curl-impersonate" -q --compressed --impersonate "${profile}" "$@"
EOF
chmod 755 "${dest}/bin/curl-impersonate"

# Human/audit record of WHAT was fetched, never a selection/version gate.
printf 'FreeBSD latest ABI: %s\nSource package: %s\nSource SHA256: %s\nBinary SHA256: %s\nChrome profile: %s\n' \
    "${abi}" "${pkg_file##*/}" "$(sha256 -q "${pkg_file}")" \
    "$(sha256 -q "${dest}/libexec/curl-impersonate")" "${profile}" > "${dest}/PROVENANCE"

version_output=$("${dest}/bin/curl-impersonate" --version) || {
    echo 'private curl-impersonate cannot execute with its bundled library' >&2
    exit 70
}
printf '%s\n' "${version_output}" | grep -q 'HTTP3' || {
    echo 'private curl-impersonate does not advertise HTTP3' >&2
    exit 70
}
echo "==> bundled curl-impersonate: ${abi}, ${profile}, HTTP3 advertised"
