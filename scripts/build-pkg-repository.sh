#!/bin/sh
# Build the project-owned FreeBSD pkg repository from an existing package.

set -eu

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)
ABI=${ABI:-FreeBSD:15:amd64}
INPUT_DIR=${INPUT_DIR:-${REPO_ROOT}/dist}
OUTPUT_ROOT=${OUTPUT_ROOT:-${REPO_ROOT}/pages}
OUTPUT_DIR=${OUTPUT_ROOT}/${ABI}

command -v pkg >/dev/null 2>&1 || {
    echo "ERROR: pkg is required" >&2
    exit 1
}

PACKAGE=$(find "${INPUT_DIR}" -maxdepth 1 -type f -name 'os-zapret2-restyle-*.pkg' | sort | tail -1)
[ -n "${PACKAGE}" ] && [ -f "${PACKAGE}" ] || {
    echo "ERROR: os-zapret2-restyle package not found in ${INPUT_DIR}" >&2
    exit 1
}

rm -rf "${OUTPUT_ROOT}"
mkdir -p "${OUTPUT_DIR}"
cp "${PACKAGE}" "${OUTPUT_DIR}/"
cp "${REPO_ROOT}/repository/zapret2-restyle.conf" "${OUTPUT_ROOT}/zapret2-restyle.conf"

(
    cd "${OUTPUT_DIR}"
    sha256 "$(basename "${PACKAGE}")" > SHA256SUMS
)

pkg repo "${OUTPUT_DIR}"

cat > "${OUTPUT_ROOT}/index.html" <<EOF_INDEX
<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>os-zapret2-restyle repository</title></head>
<body>
<h1>os-zapret2-restyle pkg repository</h1>
<p>Repository ABI: ${ABI}</p>
<p>Install the repository configuration as documented in the project README.</p>
</body>
</html>
EOF_INDEX

find "${OUTPUT_ROOT}" -type f -maxdepth 3 -print | sort
