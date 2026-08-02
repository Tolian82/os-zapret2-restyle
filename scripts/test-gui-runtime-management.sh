#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
CONTROLLER="${ROOT_DIR}/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/ServiceController.php"
VIEW="${ROOT_DIR}/src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt"
LAUNCHER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/setup_launcher.sh"
ACTIONS="${ROOT_DIR}/src/opnsense/service/conf/actions.d/actions_zapret.conf"
TMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/zapret-gui-runtime-test.XXXXXX")
trap 'rm -rf "${TMP_ROOT}"' EXIT INT TERM HUP

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

SETUP_MOCK="${TMP_ROOT}/setup.sh"
DAEMON_MOCK="${TMP_ROOT}/daemon"
DAEMON_ARGS="${TMP_ROOT}/daemon.args"
SERVICE_MOCK="${TMP_ROOT}/service"
SERVICE_CALLS="${TMP_ROOT}/service.calls"
GIT_MOCK="${TMP_ROOT}/git"
ZAPRET_DIR="${TMP_ROOT}/zapret2"
DVTWS_BIN="${ZAPRET_DIR}/binaries/my/dvtws2"
STATE_DIR="${TMP_ROOT}/state"
RUN_DIR="${TMP_ROOT}/run"
LOG_DIR="${TMP_ROOT}/log"

mkdir -p "${ZAPRET_DIR}/.git" "${STATE_DIR}" "${RUN_DIR}"
printf '%s\n' ready > "${STATE_DIR}/setup.status"

cat > "${SETUP_MOCK}" <<'MOCK'
#!/bin/sh
exit 0
MOCK
chmod +x "${SETUP_MOCK}"

cat > "${DAEMON_MOCK}" <<'MOCK'
#!/bin/sh
printf '%s\n' "$@" > "${DAEMON_ARGS_FILE}"
exit 0
MOCK
chmod +x "${DAEMON_MOCK}"

cat > "${SERVICE_MOCK}" <<'MOCK'
#!/bin/sh
printf '%s\n' "$*" >> "${SERVICE_CALLS_FILE}"
exit "${SERVICE_RESULT:-0}"
MOCK
chmod +x "${SERVICE_MOCK}"

cat > "${GIT_MOCK}" <<'MOCK'
#!/bin/sh
printf '%s\n' "${GIT_RELEASE:-v1.0.4}"
MOCK
chmod +x "${GIT_MOCK}"

# Selected release is propagated unchanged to the existing setup backend.
DAEMON_ARGS_FILE="${DAEMON_ARGS}" \
SETUP_SCRIPT="${SETUP_MOCK}" \
DAEMON_BIN="${DAEMON_MOCK}" \
RUN_DIR="${RUN_DIR}" \
LOG_DIR="${LOG_DIR}" \
"${LAUNCHER}" install v1.0.3

tail -3 "${DAEMON_ARGS}" | grep -Fxq "${SETUP_MOCK}" || fail "setup backend was not launched"
tail -2 "${DAEMON_ARGS}" | head -1 | grep -Fxq 'install' || fail "install mode was not propagated"
tail -1 "${DAEMON_ARGS}" | grep -Fxq 'v1.0.3' || fail "selected release was not propagated"

if DAEMON_ARGS_FILE="${DAEMON_ARGS}" SETUP_SCRIPT="${SETUP_MOCK}" DAEMON_BIN="${DAEMON_MOCK}" \
    RUN_DIR="${RUN_DIR}" LOG_DIR="${LOG_DIR}" "${LAUNCHER}" install release-1 >/dev/null 2>&1; then
    fail "launcher accepted an invalid release"
fi

# Missing executable runtime is a passive not-installed state and does not query service status.
rm -f "${SERVICE_CALLS}"
STATUS_OUTPUT=$(SERVICE_CALLS_FILE="${SERVICE_CALLS}" SERVICE_RESULT=0 \
    SERVICE_SCRIPT="${SERVICE_MOCK}" GIT_BIN="${GIT_MOCK}" ZAPRET_DIR="${ZAPRET_DIR}" \
    DVTWS_BIN="${DVTWS_BIN}" STATE_DIR="${STATE_DIR}" RUN_DIR="${RUN_DIR}" \
    "${LAUNCHER}" status)
printf '%s\n' "${STATUS_OUTPUT}" | grep -Fxq 'installed=0' || fail "missing runtime was not reported"
printf '%s\n' "${STATUS_OUTPUT}" | grep -Fxq 'service=error' || fail "missing runtime did not report Error"
printf '%s\n' "${STATUS_OUTPUT}" | grep -Fxq 'version=' || fail "missing runtime reported a release"
[ ! -e "${SERVICE_CALLS}" ] || fail "service status was queried without dvtws2"

# Installed runtime reports the canonical running/stopped service state and exact tag.
mkdir -p "$(dirname "${DVTWS_BIN}")"
: > "${DVTWS_BIN}"
chmod +x "${DVTWS_BIN}"

STATUS_OUTPUT=$(SERVICE_CALLS_FILE="${SERVICE_CALLS}" SERVICE_RESULT=0 GIT_RELEASE=v1.0.4 \
    SERVICE_SCRIPT="${SERVICE_MOCK}" GIT_BIN="${GIT_MOCK}" ZAPRET_DIR="${ZAPRET_DIR}" \
    DVTWS_BIN="${DVTWS_BIN}" STATE_DIR="${STATE_DIR}" RUN_DIR="${RUN_DIR}" \
    "${LAUNCHER}" status)
printf '%s\n' "${STATUS_OUTPUT}" | grep -Fxq 'installed=1' || fail "installed runtime was not reported"
printf '%s\n' "${STATUS_OUTPUT}" | grep -Fxq 'service=started' || fail "running dvtws2 was not reported"
printf '%s\n' "${STATUS_OUTPUT}" | grep -Fxq 'version=v1.0.4' || fail "exact runtime release was not reported"

STATUS_OUTPUT=$(SERVICE_CALLS_FILE="${SERVICE_CALLS}" SERVICE_RESULT=1 GIT_RELEASE=v1.0.4 \
    SERVICE_SCRIPT="${SERVICE_MOCK}" GIT_BIN="${GIT_MOCK}" ZAPRET_DIR="${ZAPRET_DIR}" \
    DVTWS_BIN="${DVTWS_BIN}" STATE_DIR="${STATE_DIR}" RUN_DIR="${RUN_DIR}" \
    "${LAUNCHER}" status)
printf '%s\n' "${STATUS_OUTPUT}" | grep -Fxq 'service=stopped' || fail "stopped dvtws2 was not reported"

# MVC starts the existing setup action asynchronously and accepts configd's detached UUID.
grep -Fq "'installed' => false" "${CONTROLLER}" || fail "runtime installed state is missing"
grep -Fq "case 'installed':" "${CONTROLLER}" || fail "installed status parsing is missing"
grep -Fq 'configdpRun(' "${CONTROLLER}" || fail "parameterized confid launch is missing"
grep -Fq "'zapret setup'" "${CONTROLLER}" || fail "setup action is not used"
grep -Fq "['install', \$version]" "${CONTROLLER}" || fail "selected release is not passed as parameters"
grep -Fq "'operation' => \$response" "${CONTROLLER}" || fail "detached operation UUID is not returned"
grep -Fq "[0-9a-f]{6}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}" "${CONTROLLER}" || fail "detached UUID is not validated"
if grep -Fq "'zapret setup install ' . \$version" "${CONTROLLER}"; then
    fail "unsafe synchronous setup command remains"
fi

# GUI uses stable slots, hides control when not installed, and does not duplicate HTTP errors.
grep -Fq "notInstalled: 'not installed'" "${VIEW}" || fail "not installed label is missing"
grep -Fq 'currentRuntimeInstalled = installed' "${VIEW}" || fail "installed state is not rendered"
grep -Fq 'serviceButton.hide()' "${VIEW}" || fail "service button is not hidden for Error/not installed"
grep -Fq 'id="zapretServiceControlSlot"' "${VIEW}" || fail "fixed service-button slot is missing"
grep -Fq 'grid-template-columns: max-content max-content 14ch 12ch 4ch' "${VIEW}" || fail "fixed desktop layout is missing"
grep -Fq '#zapretRuntimeVersion' "${VIEW}" || fail "fixed version slot is missing"
grep -Fq 'width: 14ch' "${VIEW}" || fail "version slot does not reserve not installed width"
grep -Fq 'width: 4ch' "${VIEW}" || fail "requested repository spacing is missing"
[ "$(grep -Fc "data.status !== 'ok'" "${VIEW}")" -eq 1 ] ||
    fail "base Start/Stop response is still treated as status=ok"
if grep -Fq 'apiErrorMessage' "${VIEW}"; then
    fail "duplicate AJAX error dialog helper remains"
fi
[ "$(grep -Fc 'showRuntimeError(' "${VIEW})" -eq 2 ] ||
    fail "GUI should retain only the async setup-failure dialog call"

grep -Fq '[setup]' "${ACTIONS}" || fail "setup configd action is missing"
grep -Fq '[setup_releases]' "${ACTIONS}" || fail "release-list action is missing"
grep -Fq '[setup_status]' "${ACTIONS}" || fail "runtime-status action is missing"

echo "GUI runtime state and release-operation tests passed"
