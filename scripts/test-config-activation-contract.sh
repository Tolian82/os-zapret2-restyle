#!/bin/sh

set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BACKEND="${REPO_ROOT}/src/opnsense/scripts/OPNsense/Zapret/backend"
FIREWALL="${BACKEND}/firewall.sh"
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

prepare_count=$(grep -c '^[[:space:]]*prepare_firewall_prerequisites || return 1$' "${SERVICE_SCRIPT}")
assert_equal 2 "${prepare_count}" "start and reconfigure firewall prerequisite count"

grep -Fq '[ "${_firewall_prepared:-0}" = "1" ] && return 0' "${FIREWALL}" ||
    fail "firewall preparation is not idempotent within one lifecycle operation"
grep -Fq '_firewall_prepared=1' "${FIREWALL}" ||
    fail "successful firewall preparation is not remembered"

start_prepare_line=$(awk '
    /^start_service\(\)/ { inside=1 }
    inside && /prepare_firewall_prerequisites \|\| return 1/ { print NR; exit }
    inside && /^}/ { inside=0 }
' "${SERVICE_SCRIPT}")
start_orchestrator_line=$(awk '
    /^start_service\(\)/ { inside=1 }
    inside && /orchestrator_native_start/ { print NR; exit }
    inside && /^}/ { inside=0 }
' "${SERVICE_SCRIPT}")
reconfigure_prepare_line=$(awk '
    /^reconfigure_service\(\)/ { inside=1 }
    inside && /prepare_firewall_prerequisites \|\| return 1/ { print NR; exit }
    inside && /^}/ { inside=0 }
' "${SERVICE_SCRIPT}")
reconfigure_orchestrator_line=$(awk '
    /^reconfigure_service\(\)/ { inside=1 }
    inside && /orchestrator_native_reconfigure/ { print NR; exit }
    inside && /^}/ { inside=0 }
' "${SERVICE_SCRIPT}")

[ -n "${start_prepare_line}" ] && [ -n "${start_orchestrator_line}" ] ||
    fail "start lifecycle ordering could not be determined"
[ -n "${reconfigure_prepare_line}" ] && [ -n "${reconfigure_orchestrator_line}" ] ||
    fail "reconfigure lifecycle ordering could not be determined"
[ "${start_prepare_line}" -lt "${start_orchestrator_line}" ] ||
    fail "start launches dvtws2 before firewall prerequisites"
[ "${reconfigure_prepare_line}" -lt "${reconfigure_orchestrator_line}" ] ||
    fail "reconfigure launches dvtws2 before firewall prerequisites"

echo "Config activation contract tests passed."
