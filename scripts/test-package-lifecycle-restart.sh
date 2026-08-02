#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PRE_INSTALL_HOOK="${ROOT_DIR}/pkg/+PRE_INSTALL"
PRE_DEINSTALL_HOOK="${ROOT_DIR}/pkg/+PRE_DEINSTALL"
POST_INSTALL_HOOK="${ROOT_DIR}/pkg/+POST_INSTALL"
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

# Replacement-package upgrade state preservation remains fail-closed.
grep -q 'PKG_UPGRADE' "${PRE_INSTALL_HOOK}" ||
    fail "replacement pre-install does not distinguish package upgrade"
grep -q 'pkg-upgrade.restart' "${PRE_INSTALL_HOOK}" ||
    fail "replacement pre-install does not preserve the running-state marker"
grep -q 'stopped_status' "${PRE_INSTALL_HOOK}" ||
    fail "replacement pre-install does not verify complete service stop"
grep -q 'PKG_UPGRADE' "${PRE_DEINSTALL_HOOK}" ||
    fail "pre-deinstall does not distinguish package upgrade"
grep -q 'stopped_status' "${PRE_DEINSTALL_HOOK}" ||
    fail "pre-deinstall does not verify complete service stop"

if grep -Eq 'SERVICE_SCRIPT.*stop.*\|\|[[:space:]]*true' \
    "${PRE_INSTALL_HOOK}" "${PRE_DEINSTALL_HOOK}"; then
    fail "package lifecycle suppresses a service-stop failure"
fi

# New configd actions must be loaded before template rendering, service restore,
# or the final Web GUI restart.
grep -q '"${SERVICE_BIN}" configd restart' "${POST_INSTALL_HOOK}" ||
    fail "post-install does not restart configd after installing actions"
grep -q 'template reload OPNsense/Zapret' "${POST_INSTALL_HOOK}" ||
    fail "post-install does not render the Zapret template through refreshed configd"
grep -q '\[ "${template_output}" != "OK" \]' "${POST_INSTALL_HOOK}" ||
    fail "post-install does not require exact template reload success"
grep -q '"${CONFIGCTL}" zapret start' "${POST_INSTALL_HOOK}" ||
    fail "post-install no longer restores a previously running service"
grep -q '"${CONFIGCTL}" webgui restart 2' "${POST_INSTALL_HOOK}" ||
    fail "post-install no longer refreshes the Web GUI last"

configd_line=$(grep -n '"${SERVICE_BIN}" configd restart' "${POST_INSTALL_HOOK}" | cut -d: -f1)
template_line=$(grep -n 'template reload OPNsense/Zapret' "${POST_INSTALL_HOOK}" | cut -d: -f1)
zapret_line=$(grep -n '"${CONFIGCTL}" zapret start' "${POST_INSTALL_HOOK}" | cut -d: -f1)
webgui_line=$(grep -n '"${CONFIGCTL}" webgui restart 2' "${POST_INSTALL_HOOK}" | cut -d: -f1)
message_line=$(grep -n "cat <<'MESSAGE'" "${POST_INSTALL_HOOK}" | cut -d: -f1)

[ "${configd_line}" -lt "${template_line}" ] ||
    fail "template reload runs before replacement configd actions are loaded"
[ "${template_line}" -lt "${zapret_line}" ] ||
    fail "upgrade service restoration runs before template rendering"
[ "${zapret_line}" -lt "${webgui_line}" ] ||
    fail "Web GUI refresh runs before service-state restoration"
[ "${webgui_line}" -lt "${message_line}" ] ||
    fail "Web GUI refresh is not the final package integration action"

if grep -Eq 'configd restart.*\|\|[[:space:]]*true' "${POST_INSTALL_HOOK}"; then
    fail "post-install suppresses configd restart failure"
fi

# Clean boot without runtime must be a silent no-op.
CONFIGCTL_MOCK="${TMP_ROOT}/configctl"
CONFIGCTL_CALLS="${TMP_ROOT}/configctl.calls"
MISSING_DVTWS="${TMP_ROOT}/missing/dvtws2"
INSTALLED_DVTWS="${TMP_ROOT}/runtime/dvtws2"
cat > "${CONFIGCTL_MOCK}" <<'MOCK'
#!/bin/sh
printf '%s\n' "$*" >> "${CONFIGCTL_CALLS}"
exit 0
MOCK
chmod +x "${CONFIGCTL_MOCK}"

CONFIGCTL_CALLS="${CONFIGCTL_CALLS}" \
CONFIGCTL="${CONFIGCTL_MOCK}" \
DVTWS_BIN="${MISSING_DVTWS}" \
"${START_HOOK}"
[ ! -e "${CONFIGCTL_CALLS}" ] ||
    fail "boot hook called configd while dvtws2 was absent"

mkdir -p "$(dirname "${INSTALLED_DVTWS}")"
: > "${INSTALLED_DVTWS}"
chmod +x "${INSTALLED_DVTWS}"
CONFIGCTL_CALLS="${CONFIGCTL_CALLS}" \
CONFIGCTL="${CONFIGCTL_MOCK}" \
DVTWS_BIN="${INSTALLED_DVTWS}" \
"${START_HOOK}"
grep -Fxq 'zapret start' "${CONFIGCTL_CALLS}" ||
    fail "boot hook did not start an installed runtime"

# OPNsense must not register a startable service before runtime installation.
grep -q 'function zapret_runtime_installed()' "${PLUGIN_HOOK}" ||
    fail "plugin integration has no explicit runtime-installed predicate"
grep -q "is_executable('/usr/local/etc/zapret2/binaries/my/dvtws2')" "${PLUGIN_HOOK}" ||
    fail "plugin integration does not use executable dvtws2 as installation evidence"
grep -q 'zapret_enabled() && zapret_runtime_installed()' "${PLUGIN_HOOK}" ||
    fail "plugin service registration is not gated by runtime installation"

# Direct service start and supervisor launch remain protected by the binary gate.
ensure_line=$(grep -n '^ensure_runtime_components()' "${SERVICE_SCRIPT}" | cut -d: -f1)
start_line=$(grep -n '^start_service()' "${SERVICE_SCRIPT}" | cut -d: -f1)
start_guard_line=$(grep -n 'ensure_runtime_components || return 1' "${SERVICE_SCRIPT}" | head -1 | cut -d: -f1)
supervisor_guard_line=$(grep -n '\[ -x "${_supervisor_expected_child}" \]' "${SUPERVISOR}" | cut -d: -f1)
[ -n "${ensure_line}" ] && [ -n "${start_line}" ] && [ -n "${start_guard_line}" ] ||
    fail "service runtime guard is missing"
[ "${start_line}" -lt "${start_guard_line}" ] ||
    fail "service start does not check runtime before lifecycle work"
[ -n "${supervisor_guard_line}" ] ||
    fail "supervisor start does not require executable dvtws2"

echo "PASS: package lifecycle is silent without runtime and restores only valid runtime state"
