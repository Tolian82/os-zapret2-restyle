#!/bin/sh

set -eu

PRE_INSTALL_HOOK="pkg/+PRE_INSTALL"
PRE_HOOK="pkg/+PRE_DEINSTALL"
POST_HOOK="pkg/+POST_INSTALL"
SETUP_SCRIPT="src/opnsense/scripts/OPNsense/Zapret/setup.sh"

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

grep -q 'PKG_UPGRADE' "${PRE_INSTALL_HOOK}" ||
    fail "replacement pre-install does not distinguish package upgrade"
grep -q 'pkg-upgrade.restart' "${PRE_INSTALL_HOOK}" ||
    fail "replacement pre-install does not preserve the running-state marker"
grep -q 'stopped_status' "${PRE_INSTALL_HOOK}" ||
    fail "replacement pre-install does not verify complete service stop"

if grep -Eq 'SERVICE_SCRIPT.*stop.*\|\|[[:space:]]*true' "${PRE_INSTALL_HOOK}"; then
    fail "replacement pre-install suppresses service-stop failure"
fi

grep -q 'PKG_UPGRADE' "${PRE_HOOK}" ||
    fail "pre-deinstall does not distinguish package upgrade"
grep -q 'pkg-upgrade.restart' "${PRE_HOOK}" ||
    fail "pre-deinstall does not preserve the running-state marker"
grep -q 'service_status' "${PRE_HOOK}" ||
    fail "pre-deinstall does not inspect service state"
grep -q 'stopped_status' "${PRE_HOOK}" ||
    fail "pre-deinstall does not verify complete service stop"

if grep -Eq 'SERVICE_SCRIPT.*stop.*\|\|[[:space:]]*true' "${PRE_HOOK}"; then
    fail "pre-deinstall still suppresses service-stop failure"
fi

grep -q 'PKG_UPGRADE' "${POST_HOOK}" ||
    fail "post-install does not distinguish package upgrade"
grep -q 'pkg-upgrade.restart' "${POST_HOOK}" ||
    fail "post-install does not consume the running-state marker"
grep -q '"${CONFIGCTL}" zapret start' "${POST_HOOK}" ||
    fail "post-install does not start the replacement service through configd"
grep -q '"${SERVICE_SCRIPT}" status' "${POST_HOOK}" ||
    fail "post-install does not verify replacement service state"
grep -q 'register.php' "${POST_HOOK}" ||
    fail "post-install does not use the OPNsense plugin registration helper"
grep -q 'install os-zapret2-restyle' "${POST_HOOK}" ||
    fail "post-install does not register the correct plugin package name"
grep -q '"${CONFIGURE_PLUGINS}" POST_INSTALL' "${POST_HOOK}" ||
    fail "post-install does not invoke rc.configure_plugins with POST_INSTALL"

if grep -q 'rc.configure_plugins zapret2' "${POST_HOOK}"; then
    fail "post-install still passes the service namespace as lifecycle mode"
fi
if grep -Eq 'FIRMWARE_REGISTER.*\|\|[[:space:]]*true' "${POST_HOOK}"; then
    fail "post-install suppresses OPNsense registration failure"
fi
if grep -Eq 'CONFIGURE_PLUGINS.*\|\|[[:space:]]*true' "${POST_HOOK}"; then
    fail "post-install suppresses OPNsense POST_INSTALL failure"
fi

grep -q '"${CONFIGCTL}" webgui restart 2' "${POST_HOOK}" ||
    fail "post-install does not refresh the Web GUI through the canonical configd action"
grep -q '\[ "${webgui_output}" != "OK" \]' "${POST_HOOK}" ||
    fail "post-install does not enforce the exact Web GUI configd success response"
if grep -q 'webgui\.lighttpd_reload' "${POST_HOOK}"; then
    fail "post-install uses the obsolete webgui.lighttpd_reload plugin hook"
fi
if grep -Eq 'webgui restart.*\|\|[[:space:]]*true' "${POST_HOOK}"; then
    fail "post-install suppresses Web GUI refresh failure"
fi

register_line=$(grep -n 'install os-zapret2-restyle' "${POST_HOOK}" | cut -d: -f1)
configure_line=$(grep -n '"${CONFIGURE_PLUGINS}" POST_INSTALL' "${POST_HOOK}" | cut -d: -f1)
zapret_start_line=$(grep -n '"${CONFIGCTL}" zapret start' "${POST_HOOK}" | cut -d: -f1)
webgui_restart_line=$(grep -n '"${CONFIGCTL}" webgui restart 2' "${POST_HOOK}" | cut -d: -f1)
message_line=$(grep -n "cat <<'MESSAGE'" "${POST_HOOK}" | cut -d: -f1)

[ "${register_line}" -lt "${webgui_restart_line}" ] ||
    fail "Web GUI refresh runs before plugin registration"
[ "${configure_line}" -lt "${webgui_restart_line}" ] ||
    fail "Web GUI refresh runs before OPNsense POST_INSTALL configuration"
[ "${zapret_start_line}" -lt "${webgui_restart_line}" ] ||
    fail "Web GUI refresh runs before replacement zapret service restoration"
[ "${webgui_restart_line}" -lt "${message_line}" ] ||
    fail "Web GUI refresh is not the final package integration action"

state_line=$(grep -n '"${SERVICE_SCRIPT}" status' "${SETUP_SCRIPT}" |
    head -1 |
    cut -d: -f1)
build_line=$(grep -n 'make -C "${ZAPRET_DIR}"$' "${SETUP_SCRIPT}" |
    cut -d: -f1)
restart_condition_line=$(grep -n 'if \[ "${_service_was_running}" -eq 1 \]' "${SETUP_SCRIPT}" |
    cut -d: -f1)
restart_line=$(grep -n '"${CONFIGCTL}" zapret restart' "${SETUP_SCRIPT}" |
    cut -d: -f1)
ready_line=$(grep -n 'status_write "ready"' "${SETUP_SCRIPT}" |
    tail -1 |
    cut -d: -f1)

[ -n "${state_line}" ] ||
    fail "setup does not capture the initial service state"
[ -n "${build_line}" ] ||
    fail "setup runtime build location is unavailable"
[ "${state_line}" -lt "${build_line}" ] ||
    fail "setup captures service state after changing the runtime"
[ -n "${restart_condition_line}" ] ||
    fail "setup restart is not conditional on the initial running state"
[ -n "${restart_line}" ] ||
    fail "setup does not refresh the service after runtime installation"
[ "${restart_condition_line}" -lt "${restart_line}" ] ||
    fail "setup restart is outside the running-state condition"
[ -n "${ready_line}" ] ||
    fail "setup no longer records ready state"
[ "${restart_line}" -lt "${ready_line}" ] ||
    fail "setup records ready before service refresh succeeds"
grep -q '\[ "${_service_output}" != "OK" \]' "${SETUP_SCRIPT}" ||
    fail "setup does not enforce the exact configd success response"
grep -q 'Runtime installation completed successfully; zapret service remains stopped.' "${SETUP_SCRIPT}" ||
    fail "setup does not preserve and report the stopped service state"

grep -q 'PRE_INSTALL_JSON=.*pkg/+PRE_INSTALL' scripts/build-pkg.sh ||
    fail "package builder does not embed the replacement pre-install hook"
grep -q '"pre-install":.*pre_install' scripts/build-pkg.sh ||
    fail "package manifest does not expose the replacement pre-install hook"

echo "PASS: package lifecycle preserves service state and registers the plugin safely"
