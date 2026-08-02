#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
CONTROLLER="${ROOT_DIR}/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/ServiceController.php"
VIEW="${ROOT_DIR}/src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt"
LAUNCHER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/setup_launcher.sh"
ACTIONS="${ROOT_DIR}/src/opnsense/service/conf/actions.d/actions_zapret.conf"
TMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/zapret-gui-runtime-test.XXXXXX")
trap 'rm -rf "${TMP_ROOT}"' EXIT INT TERM HUP

SETUP_MOCK="${TMP_ROOT}/setup.sh"
DAEMON_MOCK="${TMP_ROOT}/daemon"
DAEMON_ARGS="${TMP_ROOT}/daemon.args"
RUN_DIR="${TMP_ROOT}/run"
LOG_DIR="${TMP_ROOT}/log"

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

DAEMON_ARGS_FILE="${DAEMON_ARGS}" \
SETUP_SCRIPT="${SETUP_MOCK}" \
DAEMON_BIN="${DAEMON_MOCK}" \
RUN_DIR="${RUN_DIR}" \
LOG_DIR="${LOG_DIR}" \
"${LAUNCHER}" install v1.0.4

tail -3 "${DAEMON_ARGS}" | grep -Fxq "${SETUP_MOCK}"
tail -2 "${DAEMON_ARGS}" | head -1 | grep -Fxq 'install'
tail -1 "${DAEMON_ARGS}" | grep -Fxq 'v1.0.4'

if DAEMON_ARGS_FILE="${DAEMON_ARGS}" SETUP_SCRIPT="${SETUP_MOCK}" DAEMON_BIN="${DAEMON_MOCK}" \
    RUN_DIR="${RUN_DIR}" LOG_DIR="${LOG_DIR}" "${LAUNCHER}" install release-1 >/dev/null 2>&1; then
    echo "FAIL: launcher accepted an invalid release" >&2
    exit 1
fi

if DAEMON_ARGS_FILE="${DAEMON_ARGS}" SETUP_SCRIPT="${SETUP_MOCK}" DAEMON_BIN="${DAEMON_MOCK}" \
    RUN_DIR="${RUN_DIR}" LOG_DIR="${LOG_DIR}" "${LAUNCHER}" install v1.0.4 extra >/dev/null 2>&1; then
    echo "FAIL: launcher accepted extra arguments" >&2
    exit 1
fi

SERVICE_MOCK="${TMP_ROOT}/service"
GIT_MOCK="${TMP_ROOT}/git"
ZAPRET_DIR="${TMP_ROOT}/zapret2"
STATE_DIR="${TMP_ROOT}/state"
mkdir -p "${ZAPRET_DIR}/.git" "${STATE_DIR}" "${RUN_DIR}"

cat > "${SERVICE_MOCK}" <<'MOCK'
#!/bin/sh
exit "${SERVICE_RESULT:-0}"
MOCK
chmod +x "${SERVICE_MOCK}"

cat > "${GIT_MOCK}" <<'MOCK'
#!/bin/sh
printf '%s\n' "${GIT_RELEASE:-v1.0.4}"
MOCK
chmod +x "${GIT_MOCK}"
printf '%s\n' ready > "${STATE_DIR}/setup.status"

STATUS_OUTPUT=$(SERVICE_RESULT=0 GIT_RELEASE=v1.0.4 \
    SERVICE_SCRIPT="${SERVICE_MOCK}" GIT_BIN="${GIT_MOCK}" ZAPRET_DIR="${ZAPRET_DIR}" \
    STATE_DIR="${STATE_DIR}" RUN_DIR="${RUN_DIR}" "${LAUNCHER}" status)
printf '%s\n' "${STATUS_OUTPUT}" | grep -Fxq 'service=started'
printf '%s\n' "${STATUS_OUTPUT}" | grep -Fxq 'version=v1.0.4'
printf '%s\n' "${STATUS_OUTPUT}" | grep -Fxq 'setup=ready'
printf '%s\n' "${STATUS_OUTPUT}" | grep -Fxq 'busy=0'

STATUS_OUTPUT=$(SERVICE_RESULT=1 GIT_RELEASE=not-a-release \
    SERVICE_SCRIPT="${SERVICE_MOCK}" GIT_BIN="${GIT_MOCK}" ZAPRET_DIR="${ZAPRET_DIR}" \
    STATE_DIR="${STATE_DIR}" RUN_DIR="${RUN_DIR}" "${LAUNCHER}" status)
printf '%s\n' "${STATUS_OUTPUT}" | grep -Fxq 'service=stopped'
printf '%s\n' "${STATUS_OUTPUT}" | grep -Fxq 'version='

sleep 30 &
BUSY_PID=$!
printf '%s\n' "${BUSY_PID}" > "${RUN_DIR}/setup.pid"
STATUS_OUTPUT=$(SERVICE_RESULT=2 GIT_RELEASE=v1.0.4 \
    SERVICE_SCRIPT="${SERVICE_MOCK}" GIT_BIN="${GIT_MOCK}" ZAPRET_DIR="${ZAPRET_DIR}" \
    STATE_DIR="${STATE_DIR}" RUN_DIR="${RUN_DIR}" "${LAUNCHER}" status)
kill "${BUSY_PID}" >/dev/null 2>&1 || true
wait "${BUSY_PID}" 2>/dev/null || true
printf '%s\n' "${STATUS_OUTPUT}" | grep -Fxq 'service=error'
printf '%s\n' "${STATUS_OUTPUT}" | grep -Fxq 'setup=installing'
printf '%s\n' "${STATUS_OUTPUT}" | grep -Fxq 'busy=1'

grep -Fq "private const RELEASE_PATTERN" "${CONTROLLER}"
grep -Fq "configdRun('zapret setup_releases'" "${CONTROLLER}"
grep -Fq "configdRun('zapret setup_status'" "${CONTROLLER}"
grep -Fq "'zapret setup install ' . \$version" "${CONTROLLER}"
grep -Fq "in_array(\$version, \$this->getReleaseList(\$backend), true)" "${CONTROLLER}"
grep -Fq "public function releasesAction(): array" "${CONTROLLER}"
grep -Fq "public function runtimeAction(): array" "${CONTROLLER}"

grep -Fq 'id="zapretServiceHeader"' "${VIEW}"
if grep -Fq "zapretServiceHeader').off" "${VIEW}"; then
    echo "FAIL: view duplicates the global OPNsense collapsible-header handler" >&2
    exit 1
fi
grep -Fq '/api/zapret/service/runtime' "${VIEW}"
grep -Fq '/api/zapret/service/releases' "${VIEW}"
grep -Fq '/api/zapret/service/install' "${VIEW}"
grep -Fq "url: '/api/zapret/service/' + action" "${VIEW}"
grep -Fq "isRussian ? 'Служба Zapret2' : 'Zapret2 Service'" "${VIEW}"
grep -Fq "isRussian ? 'Релизы репозитория' : 'Repository Releases'" "${VIEW}"
grep -Fq 'const releaseAvailable =' "${VIEW}"
grep -Fq 'renderRuntimeRequestFailure' "${VIEW}"

grep -Fq '[setup_releases]' "${ACTIONS}"
grep -Fq 'command:/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh show' "${ACTIONS}"
grep -Fq '[setup_status]' "${ACTIONS}"
grep -Fq 'command:/usr/local/opnsense/scripts/OPNsense/Zapret/setup_launcher.sh status' "${ACTIONS}"
grep -Fq 'parameters:%s' "${ACTIONS}"

grep -Fq 'service=%s' "${LAUNCHER}"
grep -Fq 'version=%s' "${LAUNCHER}"
grep -Fq 'setup=%s' "${LAUNCHER}"
grep -Fq 'busy=%s' "${LAUNCHER}"

echo "GUI runtime management tests passed"
