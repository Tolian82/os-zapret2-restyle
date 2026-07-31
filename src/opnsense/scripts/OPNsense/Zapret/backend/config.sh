#!/bin/sh

config_load()
{
    _config_path="$1"
    if [ ! -f "${_config_path}" ]; then
        echo "zapret is not running (configuration file not found — save settings first)"
        return 1
    fi
    . "${_config_path}"
}

config_resolve_interface()
{
    _config_iface="$1"

    [ -n "${_config_iface}" ] || {
        common_error "logical interface name is empty"
        return 1
    }

    if ifconfig "${_config_iface}" >/dev/null 2>&1; then
        printf '%s
' "${_config_iface}"
        return 0
    fi

    [ -x /usr/local/sbin/pluginctl ] || {
        common_error "pluginctl is unavailable; cannot resolve interface '${_config_iface}'"
        return 1
    }
    [ -x /usr/local/bin/jq ] || {
        common_error "jq is unavailable; cannot resolve interface '${_config_iface}'"
        return 1
    }

    _config_dev=$(
        /usr/local/sbin/pluginctl -4 "${_config_iface}" 2>/dev/null |
        /usr/local/bin/jq -r \
            --arg logical "${_config_iface}" \
            '.[$logical][0].device // empty'
    )

    [ -n "${_config_dev}" ] || {
        common_error "could not resolve logical interface '${_config_iface}'"
        return 1
    }

    ifconfig "${_config_dev}" >/dev/null 2>&1 || {
        common_error "resolved device '${_config_dev}' for '${_config_iface}' does not exist"
        return 1
    }

    printf '%s
' "${_config_dev}"
}

# Compatible Milestone 5 extensions.

config_reload_template()
{
    _config_reload_namespace="$1"
    _config_reload_bin="${CONFIGCTL_BIN:-/usr/local/sbin/configctl}"

    [ -n "${_config_reload_namespace}" ] || {
        common_error "config_reload_template requires a template namespace"
        return 1
    }

    [ -x "${_config_reload_bin}" ] || {
        common_error "configctl is unavailable: ${_config_reload_bin}"
        return 1
    }

    if _config_reload_response=$(
        "${_config_reload_bin}" template reload "${_config_reload_namespace}" 2>&1
    ); then
        if [ "${_config_reload_response}" = "OK" ]; then
            return 0
        fi
        common_error "template reload returned an unexpected response for '${_config_reload_namespace}'"
    else
        common_error "template reload failed for '${_config_reload_namespace}'"
    fi

    [ -z "${_config_reload_response}" ] || echo "${_config_reload_response}" >&2
    return 1
}
