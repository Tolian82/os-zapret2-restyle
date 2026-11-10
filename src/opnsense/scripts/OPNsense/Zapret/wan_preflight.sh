#!/bin/sh
# Read-only WAN-first prerequisite. The 'device' action returns exactly the
# verified physical interface behind saved OPNsense Config general.waninterface.
# Existing require/if-start status output is unchanged.
SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
. "${SCRIPT_DIR}/backend/common.sh"
. "${SCRIPT_DIR}/backend/config.sh"
_mode="${1:-require}"
case "${_mode}" in require|if-start|device) ;; *) exit 64 ;; esac
_php_mode="${_mode}"
[ "${_mode}" != device ] || _php_mode=require
[ -x /usr/local/bin/php ] || {
    if [ "${_mode}" = device ]; then echo 'wan-unavailable' >&2
    else echo 'wan-unavailable'; fi
    exit 69
}
_reply=$(/usr/local/bin/php "${SCRIPT_DIR}/wan_preflight.php" "${_php_mode}" 2>/dev/null) || {
    if [ "${_mode}" = device ]; then echo 'wan-unavailable' >&2
    else echo 'wan-unavailable'; fi
    exit 69
}
case "${_reply}" in
    wan-required|wan-invalid|wan-not-required)
        if [ "${_mode}" = device ]; then
            printf '%s\n' "${_reply}" >&2
            exit 65
        fi
        printf '%s\n' "${_reply}"
        ;;
    wan-selected=*)
        _name="${_reply#wan-selected=}"
        if [ "${_mode}" = device ]; then
            _device=$(config_resolve_interface "${_name}") || {
                echo 'wan-invalid' >&2
                exit 65
            }
            [ -n "${_device}" ] || { echo 'wan-invalid' >&2; exit 65; }
            printf '%s\n' "${_device}"
        else
            if config_resolve_interface "${_name}" >/dev/null 2>&1; then
                echo 'wan-ready'
            else
                echo 'wan-invalid'
            fi
        fi
        ;;
    *)
        if [ "${_mode}" = device ]; then echo 'wan-unavailable' >&2
        else echo 'wan-unavailable'; fi
        exit 69
        ;;
esac
