#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PRE_INSTALL="${ROOT_DIR}/pkg/+PRE_INSTALL"
PRE_DEINSTALL="${ROOT_DIR}/pkg/+PRE_DEINSTALL"
POST_INSTALL="${ROOT_DIR}/pkg/+POST_INSTALL"
START_HOOK="${ROOT_DIR}/src/etc/rc.syshook.d/start/20-zapret"
PLUGIN_HOOK="${ROOT_DIR}/src/etc/inc/plugins.inc.d/zapret.inc"
SERVICE_SCRIPT="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
SUPERVISOR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/backend/supervisor.sh"
TMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/zapret-lifecycle-test.XXXXXX")
trap 'rm -rf "${TMP_ROOT}"' EXIT INT TERM HUP

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

# Upgrade state transfer remains fail-closed.
for file in "${PRE_INSTALL}" "${PRE_DEINSTALL}"; do
    grep -q 'PKG_UPGRADE' "${file}" || fail "${file} does not distinguish upgrade"
    grep -q 'stopped_status' "${file}" || fail "${file} does not verify complete stop"
done
grep -q 'pkg-upgrade.restart' "${PRE_INSTALL}" || fail "upgrade restart marker is missing"
if grep -Eq 'SERVICE_SCRIPT.*stop.*\|\|[[:space:]]*true' "${PRE_INSTALL}" "${PRE_DEINSTALL}"; then
    fail "package lifecycle suppresses a service-stop failure"
fi

# Static guards supplement the behavioral execution below.
grep -Fq 'CONFIGD_PID_FILE="${CONFIGD_PID_FILE:-/var/run/configd.pid}"' "${POST_INSTALL}" ||
    fail "configd watcher pid file is missing"
grep -Fq '"${KILL_BIN}" -TERM "${configd_old_worker}"' "${POST_INSTALL}" ||
    fail "configd worker reload is missing"
grep -Fq '"${CONFIGCTL}" system status' "${POST_INSTALL}" ||
    fail "replacement configd worker readiness probe is missing"
grep -Fq 'template reload OPNsense/Zapret' "${POST_INSTALL}" ||
    fail "Zapret template reload is missing"
grep -Fq '"${CONFIGCTL}" zapret start' "${POST_INSTALL}" ||
    fail "running-state restoration is missing"
if grep -Eq '(^|[[:space:]])(service[[:space:]]+configd|[^[:space:]]*/rc\.d/configd[[:space:]]+restart)|webgui[[:space:]]+restart|rc\.restart_webgui' "${POST_INSTALL}"; then
    fail "package lifecycle must not restart configd watcher or global Web GUI"
fi

# Execute +POST_INSTALL with a pre-existing watcher and behavioral process mocks.
# TERM is sent only to the old worker; the same watcher exposes a replacement worker.
TRACE="${TMP_ROOT}/trace"
RELOADED="${TMP_ROOT}/worker.reloaded"
PID_FILE="${TMP_ROOT}/configd.pid"
MARKER="${TMP_ROOT}/restart.marker"
printf '%s\n' 4242 > "${PID_FILE}"

write_mock()
{
    path=$1
    shift
    printf '%s\n' '#!/bin/sh' "$@" > "${path}"
    chmod +x "${path}"
}

write_mock "${TMP_ROOT}/pgrep" \
    'printf "%s\n" "pgrep:$*" >> "${TRACE}"' \
    'if [ -e "${RELOADED}" ]; then printf "%s\n" 4444; else printf "%s\n" 4343; fi'
write_mock "${TMP_ROOT}/kill" \
    'printf "%s\n" "kill:$*" >> "${TRACE}"' \
    'case "$*" in' \
    '  "-0 4242") exit 0 ;;' \
    '  "-TERM 4343") : > "${RELOADED}"; exit 0 ;;' \
    '  *) exit 64 ;;' \
    'esac'
write_mock "${TMP_ROOT}/configctl" \
    'printf "%s\n" "configctl:$*" >> "${TRACE}"' \
    'case "$*" in' \
    '  "system status") [ -e "${RELOADED}" ] ;;' \
    '  "template reload OPNsense/Zapret"|"zapret start") printf "%s\n" OK ;;' \
    '  webgui*) exit 99 ;;' \
    '  *) exit 64 ;;' \
    'esac'
write_mock "${TMP_ROOT}/register" \
    'printf "%s\n" "firmware:$*" >> "${TRACE}"' \
    '[ "$*" = "install os-zapret2-restyle" ]'
write_mock "${TMP_ROOT}/configure" \
    'printf "%s\n" "configure:$*" >> "${TRACE}"' \
    '[ "$*" = POST_INSTALL ]'
write_mock "${TMP_ROOT}/service" \
    'printf "%s\n" "service:$*" >> "${TRACE}"' \
    '[ "$*" = status ]'
write_mock "${TMP_ROOT}/sleep" \
    'printf "%s\n" "sleep:$*" >> "${TRACE}"'
: > "${MARKER}"

TRACE="${TRACE}" RELOADED="${RELOADED}" \
CONFIGD_PID_FILE="${PID_FILE}" CONFIGD_WORKER_PATTERN='configd.py console' \
PGREP_BIN="${TMP_ROOT}/pgrep" KILL_BIN="${TMP_ROOT}/kill" \
CONFIGCTL="${TMP_ROOT}/configctl" FIRMWARE_REGISTER="${TMP_ROOT}/register" \
CONFIGURE_PLUGINS="${TMP_ROOT}/configure" SERVICE_SCRIPT="${TMP_ROOT}/service" \
SLEEP_BIN="${TMP_ROOT}/sleep" UPGRADE_RESTART_MARKER="${MARKER}" PKG_UPGRADE=1 \
"${POST_INSTALL}" >/dev/null

[ -e "${RELOADED}" ] || fail "configd worker was not reloaded"
[ ! -e "${MARKER}" ] || fail "upgrade restart marker was not consumed"
if grep -Eq 'configctl:webgui|rc\.restart_webgui|configd:restart' "${TRACE}"; then
    fail "executed lifecycle restarted a global OPNsense service"
fi
[ "$(grep -Fc 'kill:-TERM 4343' "${TRACE}")" -eq 1 ] ||
    fail "old configd worker was not signalled exactly once"
if grep -Fq 'kill:-TERM 4242' "${TRACE}"; then
    fail "configd watcher was signalled"
fi

line_of()
{
    grep -n -F "$1" "${TRACE}" | head -1 | cut -d: -f1
}

old_worker_line=$(line_of 'pgrep:-P 4242 -f configd.py console')
parent_probe_line=$(line_of 'kill:-0 4242')
worker_term_line=$(line_of 'kill:-TERM 4343')
ready_line=$(line_of 'configctl:system status')
configure_line=$(line_of 'configure:POST_INSTALL')
template_line=$(line_of 'configctl:template reload OPNsense/Zapret')
start_line=$(line_of 'configctl:zapret start')
status_line=$(line_of 'service:status')
[ "${parent_probe_line}" -lt "${old_worker_line}" ] || fail "worker discovery preceded watcher validation"
[ "${old_worker_line}" -lt "${worker_term_line}" ] || fail "worker was signalled before worker discovery"
[ "${worker_term_line}" -lt "${ready_line}" ] || fail "readiness preceded worker reload"
[ "${ready_line}" -lt "${configure_line}" ] || fail "plugin refresh preceded readiness"
[ "${configure_line}" -lt "${template_line}" ] || fail "template preceded plugin refresh"
[ "${template_line}" -lt "${start_line}" ] || fail "service restore preceded template"
[ "${start_line}" -lt "${status_line}" ] || fail "status verification preceded start"

# Clean boot without runtime is a silent no-op; installed runtime uses configctl zapret start.
BOOT_CTL="${TMP_ROOT}/boot-configctl"
BOOT_CALLS="${TMP_ROOT}/boot.calls"
write_mock "${BOOT_CTL}" 'printf "%s\n" "$*" >> "${CONFIGCTL_CALLS}"'
CONFIGCTL_CALLS="${BOOT_CALLS}" CONFIGCTL="${BOOT_CTL}" DVTWS_BIN="${TMP_ROOT}/missing" "${START_HOOK}"
[ ! -e "${BOOT_CALLS}" ] || fail "boot queried configd without dvtws2"
DVTWS="${TMP_ROOT}/runtime/dvtws2"
mkdir -p "$(dirname "${DVTWS}")"
: > "${DVTWS}"
chmod +x "${DVTWS}"
CONFIGCTL_CALLS="${BOOT_CALLS}" CONFIGCTL="${BOOT_CTL}" DVTWS_BIN="${DVTWS}" "${START_HOOK}"
grep -Fxq 'zapret start' "${BOOT_CALLS}" || fail "boot did not start installed runtime"

# Service registration, direct start, and supervisor launch retain the dvtws2 executable gate.
grep -q 'zapret_enabled() && zapret_runtime_installed()' "${PLUGIN_HOOK}" ||
    fail "service registration is not runtime-gated"
grep -q "is_executable('/usr/local/etc/zapret2/binaries/my/dvtws2')" "${PLUGIN_HOOK}" ||
    fail "runtime installation evidence is not executable dvtws2"
grep -q 'ensure_runtime_components || return 1' "${SERVICE_SCRIPT}" ||
    fail "direct service start has no runtime guard"
grep -q '\[ -x "${_supervisor_expected_child}" \]' "${SUPERVISOR}" ||
    fail "supervisor has no executable-child guard"

echo "PASS: package lifecycle reloads configd actions through the existing watcher"
