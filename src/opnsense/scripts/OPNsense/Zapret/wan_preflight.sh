#!/bin/sh
# Read-only WAN-first prerequisite. Reuse the existing native device resolver.
SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
. "${SCRIPT_DIR}/backend/common.sh"
. "${SCRIPT_DIR}/backend/config.sh"
case "${1:-require}" in require|if-start) ;; *) exit 64 ;; esac
[ -x /usr/local/bin/php ] || { echo 'wan-unavailable'; exit 69; }
_reply=$(/usr/local/bin/php "${SCRIPT_DIR}/wan_preflight.php" "${1:-require}" 2>/dev/null) || {
    echo 'wan-unavailable'
    exit 69
}
case "${_reply}" in
    wan-required|wan-invalid|wan-not-required) printf '%s\n' "${_reply}" ;;
    wan-selected=*)
        _name="${_reply#wan-selected=}"
        if config_resolve_interface "${_name}" >/dev/null 2>&1; then echo 'wan-ready'
        else echo 'wan-invalid'; fi
        ;;
    *) echo 'wan-unavailable'; exit 69 ;;
esac
