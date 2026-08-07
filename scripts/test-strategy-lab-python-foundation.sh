#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ZAPRET_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
LAUNCHER="${ZAPRET_DIR}/strategy_lab_python_launcher.sh"
ENTRY="${ZAPRET_DIR}/strategy_lab_python.py"
PACKAGE_DIR="${ZAPRET_DIR}/strategy_lab_py"
SERVICE="${ZAPRET_DIR}/zapret_service.sh"
PYTHON_BIN=${STRATEGY_LAB_TEST_PYTHON:-python3.13}
TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-python-foundation.XXXXXX")
trap 'rm -rf "${TEST_ROOT}"' EXIT HUP INT TERM

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

command -v "${PYTHON_BIN}" >/dev/null 2>&1 || fail "Python test interpreter is unavailable: ${PYTHON_BIN}"

python_version=$("${PYTHON_BIN}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
[ "${python_version}" = "3.13" ] || fail "expected Python 3.13, found ${python_version}"

[ -x "${LAUNCHER}" ] || fail 'Python compatibility launcher is not executable'
[ -r "${ENTRY}" ] || fail 'Python entry point is missing'
[ -r "${PACKAGE_DIR}/__init__.py" ] || fail 'Python package initializer is missing'
[ -r "${PACKAGE_DIR}/compat.py" ] || fail 'Python compatibility module is missing'

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${ZAPRET_DIR}" "${PYTHON_BIN}" - <<'PY'
import strategy_lab_py
from strategy_lab_py import compat

assert strategy_lab_py.SUPPORTED_PYTHON == (3, 13)
assert compat.DEFAULT_SHELL_WORKER.endswith("/strategy_lab_worker.sh")
PY

PYTHONDONTWRITEBYTECODE=1 "${PYTHON_BIN}" -m py_compile \
    "${ENTRY}" \
    "${PACKAGE_DIR}/__init__.py" \
    "${PACKAGE_DIR}/compat.py"

self_test=$(STRATEGY_LAB_PYTHON_BIN="${PYTHON_BIN}" "${LAUNCHER}" --self-test)
printf '%s\n' "${self_test}" | grep -Fq 'Strategy Lab Python foundation: OK (Python 3.13, revision 1)' ||
    fail 'launcher self-test output is unexpected'

cat > "${TEST_ROOT}/legacy-worker" <<'WORKER'
#!/bin/sh
printf '%s\n' "$1" > "${STRATEGY_LAB_TEST_CAPTURE}"
WORKER
chmod 0755 "${TEST_ROOT}/legacy-worker"

STRATEGY_LAB_TEST_CAPTURE="${TEST_ROOT}/capture" \
STRATEGY_LAB_PYTHON_BIN="${PYTHON_BIN}" \
STRATEGY_LAB_SHELL_WORKER="${TEST_ROOT}/legacy-worker" \
    "${LAUNCHER}" job.ABC123
[ "$(cat "${TEST_ROOT}/capture")" = 'job.ABC123' ] || fail 'compatibility delegation changed the job id'

set +e
STRATEGY_LAB_PYTHON_BIN="${PYTHON_BIN}" "${LAUNCHER}" bad-job >"${TEST_ROOT}/bad.out" 2>"${TEST_ROOT}/bad.err"
status=$?
set -e
[ "${status}" -eq 64 ] || fail "invalid job id returned ${status}, expected 64"
grep -Fq 'ERROR: invalid Strategy Lab job id' "${TEST_ROOT}/bad.err" || fail 'invalid job id error is not deterministic'

set +e
STRATEGY_LAB_PYTHON_BIN="${TEST_ROOT}/missing-python" "${LAUNCHER}" --self-test >"${TEST_ROOT}/missing.out" 2>"${TEST_ROOT}/missing.err"
status=$?
set -e
[ "${status}" -eq 70 ] || fail "missing Python returned ${status}, expected 70"
grep -Fq 'ERROR: Strategy Lab Python runtime could not start: interpreter is not executable:' "${TEST_ROOT}/missing.err" ||
    fail 'missing Python error is not deterministic'

cat > "${TEST_ROOT}/python312" <<'PYTHON'
#!/bin/sh
if [ "$1" = '-c' ]; then
    printf '%s\n' '3.12'
    exit 0
fi
exit 99
PYTHON
chmod 0755 "${TEST_ROOT}/python312"
set +e
STRATEGY_LAB_PYTHON_BIN="${TEST_ROOT}/python312" "${LAUNCHER}" --self-test >"${TEST_ROOT}/version.out" 2>"${TEST_ROOT}/version.err"
status=$?
set -e
[ "${status}" -eq 70 ] || fail "unsupported Python returned ${status}, expected 70"
grep -Fq 'unsupported interpreter version 3.12; expected 3.13' "${TEST_ROOT}/version.err" ||
    fail 'unsupported Python error is not deterministic'

grep -Fq 'STRATEGY_LAB_WORKER="/usr/local/opnsense/scripts/OPNsense/Zapret/strategy_lab_worker.sh"' "${SERVICE}" ||
    fail 'production Strategy Lab worker path changed during foundation patch'
! grep -Fq 'strategy_lab_python_launcher.sh' "${SERVICE}" ||
    fail 'Python launcher must remain outside the production call path in Migration Patch 1'

sh -n "${LAUNCHER}"
sh -n "$0"
echo 'PASS: Strategy Lab Python 3.13 compatibility foundation is packaged-ready without changing the production worker path'
