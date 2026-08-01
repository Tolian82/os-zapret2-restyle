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

restart_line=$(grep -n '"${CONFIGCTL}" zapret restart' "${SETUP_SCRIPT}" |
    cut -d: -f1)
ready_line=$(grep -n 'status_write "ready"' "${SETUP_SCRIPT}" |
    tail -1 |
    cut -d: -f1)

[ -n "${restart_line}" ] ||
    fail "setup does not refresh the service after runtime installation"
[ -n "${ready_line}" ] ||
    fail "setup no longer records ready state"
[ "${restart_line}" -lt "${ready_line}" ] ||
    fail "setup records ready before service refresh succeeds"
grep -q '\[ "${_service_output}" != "OK" \]' "${SETUP_SCRIPT}" ||
    fail "setup does not enforce the exact configd success response"

grep -q 'PRE_INSTALL_JSON=.*pkg/+PRE_INSTALL' scripts/build-pkg.sh ||
    fail "package builder does not embed the replacement pre-install hook"
grep -q '"pre-install":.*pre_install' scripts/build-pkg.sh ||
    fail "package manifest does not expose the replacement pre-install hook"

echo "PASS: package upgrade and runtime setup refresh the service safely"
