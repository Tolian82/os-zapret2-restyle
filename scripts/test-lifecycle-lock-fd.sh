#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
LAUNCHER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/backend/launcher.sh"
SUPERVISOR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/backend/supervisor.sh"

assert_daemon_closes_fd9()
{
    _test_file="$1"
    _test_start="$2"
    _test_end="$3"

    sed -n "/${_test_start}/,/${_test_end}/p" "${_test_file}" |
        grep -q '9>&-' || {
        echo "FAIL: daemon launch does not close lifecycle lock FD 9: ${_test_file}" >&2
        exit 1
    }
}

assert_daemon_closes_fd9 \
    "${LAUNCHER}" \
    '"${_launcher_once_daemon}"' \
    'failed to launch dvtws2'

assert_daemon_closes_fd9 \
    "${SUPERVISOR}" \
    '"${_supervisor_daemon}"' \
    'failed to start runtime supervisor'

(
    /bin/sh -c '
        if (: >&9) 2>/dev/null; then
            echo "FAIL: lifecycle lock FD 9 remained open in child" >&2
            exit 1
        fi
    ' 9>&-
) 9>"${TMPDIR:-/tmp}/zapret2-lifecycle-fd-test.$$"

rm -f "${TMPDIR:-/tmp}/zapret2-lifecycle-fd-test.$$"
echo "PASS: long-lived daemon launches close lifecycle lock FD 9"
