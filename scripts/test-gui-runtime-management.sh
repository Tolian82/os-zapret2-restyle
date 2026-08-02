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

SERVICE_MOCK="${TMP_ROOT}/service"
SERVICE_CALLS="${TMP_ROOT}/service.calls"
GIT_MOCK="${TMP_ROOT}/git"
ZAPRET_DIR="${TMP_ROOT}/zapret2"
DVTWS_BIN="${ZAPRET_DIR}/binaries/my/dvtws2"
STATE_DIR="${TMP_ROOT}/state"
RUN_DIR="${TMP_ROOT}/run"

mkdir -p "${ZAPRET_DIR}/.git" "${STATE_DIR}" "${RUN_DIR}"
printf '%s\n' ready > "${STATE_DIR}/setup.status"

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

runtime_status()
{
    SERVICE_CALLS_FILE="${SERVICE_CALLS}" \
    SERVICE_RESULT="${1}" \
    GIT_RELEASE=v1.0.4 \
    SERVICE_SCRIPT="${SERVICE_MOCK}" \
    GIT_BIN="${GIT_MOCK}" \
    ZAPRET_DIR="${ZAPRET_DIR}" \
    DVTWS_BIN="${DVTWS_BIN}" \
    STATE_DIR="${STATE_DIR}" \
    RUN_DIR="${RUN_DIR}" \
    "${LAUNCHER}" status
}

# Missing executable runtime is passive Error/not-installed and must not query service state.
rm -f "${DVTWS_BIN}" "${SERVICE_CALLS}"
STATUS_OUTPUT=$(runtime_status 0)
printf '%s\n' "${STATUS_OUTPUT}" | grep -Fqx 'installed=0' || fail "missing runtime was not reported"
printf '%s\n' "${STATUS_OUTPUT}" | grep -Fqx 'service=error' || fail "missing runtime did not report Error"
printf '%s\n' "${STATUS_OUTPUT}" | grep -Fqx 'version=' || fail "missing runtime reported a version"
[ ! -e "${SERVICE_CALLS}" ] || fail "service status was queried without dvtws2"

# Installed runtime reports the canonical running/stopped state and exact tag.
mkdir -p "$(dirname "${DVTWS_BIN}")"
: > "${DVTWS_BIN}"
chmod +x "${DVTWS_BIN}"
STATUS_OUTPUT=$(runtime_status 0)
printf '%s\n' "${STATUS_OUTPUT}" | grep -Fqx 'installed=1' || fail "installed runtime was not reported"
printf '%s\n' "${STATUS_OUTPUT}" | grep -Fqx 'service=started' || fail "running dvtws2 was not reported"
printf '%s\n' "${STATUS_OUTPUT}" | grep -Fqx 'version=v1.0.4' || fail "exact runtime tag was not reported"
STATUS_OUTPUT=$(runtime_status 1)
printf '%s\n' "${STATUS_OUTPUT}" | grep -Fqx 'service=stopped' || fail "stopped dvtws2 was not reported"

# Selected release uses the parameterized detached configd contract and validates its UUID.
grep -Fq 'configdpRun(' "${CONTROLLER}" || fail "detached configd launch is missing"
grep -Fq "'zapret setup'" "${CONTROLLER}" || fail "setup action is not used"
grep -Fq "['install', \$version]" "${CONTROLLER}" || fail "selected release is not passed as parameters"
grep -Fq "'operation' => \$response" "${CONTROLLER}" || fail "operation UUID is not returned"
grep -Fq "[0-9a-f]{8}" "${CONTROLLER}" || fail "operation UUID is not validated"
if grep -Fq "'zapret setup install ' . \$version" "${CONTROLLER}"; then
    fail "unsafe synchronous setup command remains"
fi

# GUI state and geometry contract.
grep -Fq "notInstalled: 'not installed'" "${VIEW}" || fail "not installed label is missing"
grep -Fq 'serviceButton.hide()' "${VIEW}" || fail "service control is not hidden without runtime"
grep -Fq 'id="zapretServiceControlSlot"' "${VIEW}" || fail "fixed service-control slot is missing"
grep -Fq 'max-content max-content 14ch 12ch 4ch' "${VIEW}" || fail "fixed runtime layout is missing"
grep -Fq 'width: 14ch' "${VIEW}" || fail "version slot width is not reserved"
grep -Fq 'width: 4ch' "${VIEW}" || fail "requested repository gap is missing"
[ "$(grep -Fc "data.status !== 'ok'" "${VIEW}")" -eq 1 ] || fail "Start/Stop still expects status=ok"
if grep -Fq 'apiErrorMessage' "${VIEW}"; then
    fail "duplicate AJAX error dialog helper remains"
fi
[ "$(grep -Fc 'showRuntimeError(' "${VIEW}")" -eq 2 ] || fail "unexpected runtime error dialogs remain"

grep -Fq '[setup]' "${ACTIONS}" || fail "setup action is missing"
grep -Fq '[setup_releases]' "${ACTIONS}" || fail "release-list action is missing"
grep -Fq '[setup_status]' "${ACTIONS}" || fail "runtime-status action is missing"

echo "PASS: GUI runtime state and selected-release operation contract"
