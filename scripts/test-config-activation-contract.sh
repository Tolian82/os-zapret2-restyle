#!/bin/sh

set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BACKEND="${REPO_ROOT}/src/opnsense/scripts/OPNsense/Zapret/backend"
SETTINGS_CONTROLLER="${REPO_ROOT}/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SettingsController.php"
SERVICE_CONTROLLER="${REPO_ROOT}/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/ServiceController.php"
SERVICE_SCRIPT="${REPO_ROOT}/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"

. "${BACKEND}/common.sh"
. "${BACKEND}/config.sh"

TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/zapret-config-activation.XXXXXX")
trap 'rm -rf "${TEST_ROOT}"' EXIT HUP INT TERM

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

assert_equal()
{
    expected=$1
    actual=$2
    label=$3

    [ "${expected}" = "${actual}" ] ||
        fail "${label}: expected '${expected}', got '${actual}'"
}

CONFIGCTL_BIN="${TEST_ROOT}/configctl"
MOCK_CONFIGCTL_ARGS="${TEST_ROOT}/configctl.args"
MOCK_CONFIGCTL_MODE=ok
export CONFIGCTL_BIN MOCK_CONFIGCTL_ARGS MOCK_CONFIGCTL_MODE

cat > "${CONFIGCTL_BIN}" <<'MOCK'
#!/bin/sh

printf '%s\n' "$*" > "${MOCK_CONFIGCTL_ARGS}"

case "${MOCK_CONFIGCTL_MODE:-}" in
    ok)
        echo 'OK'
        exit 0
        ;;
    encoded-error)
        echo 'Error (1)'
        exit 0
        ;;
    process-error)
        echo 'configd transport failed' >&2
        exit 1
        ;;
    *)
        exit 64
        ;;
esac
MOCK
chmod 0755 "${CONFIGCTL_BIN}"

config_reload_template OPNsense/Zapret ||
    fail "exact OK template response was rejected"
assert_equal \
    'template reload OPNsense/Zapret' \
    "$(cat "${MOCK_CONFIGCTL_ARGS}")" \
    "template reload arguments"

MOCK_CONFIGCTL_MODE=encoded-error
if config_reload_template OPNsense/Zapret 2> "${TEST_ROOT}/encoded-error.log"; then
    fail "encoded configd error was accepted"
fi
grep -Fq 'Error (1)' "${TEST_ROOT}/encoded-error.log" ||
    fail "encoded configd error was not reported"

MOCK_CONFIGCTL_MODE=process-error
if config_reload_template OPNsense/Zapret 2> "${TEST_ROOT}/process-error.log"; then
    fail "non-zero configctl exit was accepted"
fi
grep -Fq 'configd transport failed' "${TEST_ROOT}/process-error.log" ||
    fail "configctl process error was not reported"

grep -Fq "if (\$reconfigureResponse !== 'OK')" "${SETTINGS_CONTROLLER}" ||
    fail "Settings Apply does not require exact configd OK"
grep -Fq "if (\$response !== 'OK')" "${SERVICE_CONTROLLER}" ||
    fail "service reconfigure API does not require exact configd OK"

refresh_count=$(grep -c '^[[:space:]]*refresh_generated_configuration || return 1$' "${SERVICE_SCRIPT}")
assert_equal 2 "${refresh_count}" "start and reconfigure template refresh count"

echo "Config activation contract tests passed."
