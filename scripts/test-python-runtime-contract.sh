#!/bin/sh
# Executed cross-platform contract test for the single installed Python resolver.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
DIR="${ROOT}/src/opnsense/scripts/OPNsense/Zapret"
RUNNER="${DIR}/python_runtime.sh"
MANIFEST="${DIR}/python_runtime.conf"
TEMP=$(mktemp -d "${TMPDIR:-/tmp}/zapret-python-contract.XXXXXX") || exit 1
trap 'rm -rf "${TEMP}"' EXIT HUP INT TERM
fail() { echo "FAIL: $*" >&2; exit 1; }
[ -r "${RUNNER}" ] && [ -r "${MANIFEST}" ] || fail 'runtime contract missing'
/bin/sh -n "${RUNNER}" || fail 'runner syntax invalid'
. "${MANIFEST}"
[ "${ZAPRET_PYTHON_MAJOR}" = 3 ] || fail 'Python major unsupported'
[ "${ZAPRET_PYTHON_MIN_MINOR}" -ge 13 ] || fail 'minimum must cover installed plugin grammar'
[ "${ZAPRET_PYTHON_PACKAGE}" = python313 ] || fail 'installed package dependency changed unexpectedly'
grep -Fq 'PLUGIN_DEPENDS=     ${ZAPRET_PYTHON_PACKAGE}' "${ROOT}/Makefile" ||
    fail 'Makefile dependency no longer manifest-derived'
PYTHON=${ZAPRET_RUNTIME_TEST_PYTHON:-}
[ -n "${PYTHON}" ] || PYTHON=$(command -v python3.13 2>/dev/null) || fail 'CI Python3.13 unavailable'
case "${PYTHON}" in /*) ;; *) PYTHON=$(command -v "${PYTHON}") || fail 'test interpreter unavailable' ;; esac
[ -x "${PYTHON}" ] || fail 'test interpreter non-executable'
printf 'print("CONTRACT_EXEC=PASS")\n' > "${TEMP}/check.py"
observed=$(ZAPRET_PYTHON_BIN="${PYTHON}" /bin/sh "${RUNNER}" --resolve) ||
    fail 'override valid runtime rejected'
[ "${observed}" = "${PYTHON}" ] || fail 'resolved different interpreter'
result=$(ZAPRET_PYTHON_BIN="${PYTHON}" /bin/sh "${RUNNER}" --exec "${TEMP}/check.py") ||
    fail 'exec valid runtime failed'
[ "${result}" = CONTRACT_EXEC=PASS ] || fail 'wrong Python entrypoint result'
if ZAPRET_PYTHON_BIN=/bin/sh /bin/sh "${RUNNER}" --resolve >/dev/null 2>&1; then
    fail 'non-Python binary accepted'
fi
if ZAPRET_PYTHON_BIN=python3 /bin/sh "${RUNNER}" --resolve >/dev/null 2>&1; then
    fail 'relative override accepted'
fi
if ZAPRET_PYTHON_BIN="${PYTHON}" /bin/sh "${RUNNER}" --exec "${TEMP}/missing.py" >/dev/null 2>&1; then
    fail 'missing target script executed'
fi
if /bin/sh "${RUNNER}" --unknown >/dev/null 2>&1; then
    fail 'invalid launch mode accepted'
fi
cp "${RUNNER}" "${TEMP}/python_runtime.sh"
if ZAPRET_PYTHON_BIN="${PYTHON}" /bin/sh "${TEMP}/python_runtime.sh" --resolve >/dev/null 2>&1; then
    fail 'missing compatibility manifest accepted'
fi
printf 'PYTHON_RUNTIME_CONTRACT=PASS\n'
