#!/bin/sh

firewall_remove_rules()
{
    _firewall_remove_rule="$1"
    _firewall_remove_max="$2"

    while [ "${_firewall_remove_rule}" -le "${_firewall_remove_max}" ]; do
        /sbin/ipfw -q delete "${_firewall_remove_rule}" 2>/dev/null || true
        _firewall_remove_rule=$((_firewall_remove_rule + 1))
    done
}

firewall_ensure_default_accept()
{
    _firewall_default=$(/sbin/sysctl -n \
        net.inet.ip.fw.default_to_accept 2>/dev/null)

    [ "${_firewall_default}" = "1" ] ||
        /sbin/ipfw -q add 65534 allow ip from any to any 2>/dev/null || true
}

firewall_configure_reinject()
{
    /sbin/sysctl net.inet.ip.fw.one_pass=1 >/dev/null 2>&1 || return 1
    /sbin/sysctl net.inet.ip.fw.enable=1 >/dev/null 2>&1 || return 1
    /sbin/pfctl -d >/dev/null 2>&1 || true
    /sbin/pfctl -e >/dev/null 2>&1 || return 1
}

firewall_prepare()
{
    kldstat -q -m ipdivert || kldload ipdivert || return 1
    kldstat -q -m ipfw || kldload ipfw || return 1
    firewall_ensure_default_accept || return 1
    firewall_configure_reinject
}

firewall_install_port_rules()
{
    _firewall_ports_tcp_file="$1"
    _firewall_ports_udp_file="$2"
    _firewall_ports_wan="$3"
    _firewall_ports_divert="$4"
    _firewall_ports_rule_base="$5"
    _firewall_ports_rule_max="$6"

    common_require_file \
        "${_firewall_ports_tcp_file}" "TCP port artifact" || return 1
    common_require_file \
        "${_firewall_ports_udp_file}" "UDP port artifact" || return 1

    _firewall_ports_tcp=$(tr -d '\r\n' < "${_firewall_ports_tcp_file}")
    _firewall_ports_udp=$(tr -d '\r\n' < "${_firewall_ports_udp_file}")

    if [ -z "${_firewall_ports_tcp}" ] &&
       [ -z "${_firewall_ports_udp}" ]; then
        common_error "both TCP and UDP port artifacts are empty"
        return 1
    fi

    firewall_remove_rules \
        "${_firewall_ports_rule_base}" "${_firewall_ports_rule_max}"
    _firewall_ports_rule="${_firewall_ports_rule_base}"

    if [ -n "${_firewall_ports_tcp}" ]; then
        /sbin/ipfw -qf add "${_firewall_ports_rule}" \
            divert "${_firewall_ports_divert}" \
            tcp from any to any "${_firewall_ports_tcp}" \
            out not diverted not sockarg \
            xmit "${_firewall_ports_wan}" || return 1
        _firewall_ports_rule=$((_firewall_ports_rule + 1))
    fi

    if [ -n "${_firewall_ports_udp}" ]; then
        /sbin/ipfw -qf add "${_firewall_ports_rule}" \
            divert "${_firewall_ports_divert}" \
            udp from any to any "${_firewall_ports_udp}" \
            out not diverted not sockarg \
            xmit "${_firewall_ports_wan}" || return 1
    fi
}

# Compatibility API retained for older callers.
firewall_install_rules()
{
    _firewall_compat_strategy="$1"
    _firewall_compat_wan="$2"
    _firewall_compat_divert="$3"
    _firewall_compat_rule_base="$4"
    _firewall_compat_rule_max="$5"
    _firewall_compat_work=$(mktemp -d /tmp/zapret-firewall.XXXXXX) ||
        return 1

    ports_extract_file \
        "${_firewall_compat_strategy}" \
        "${_firewall_compat_work}/tcp.txt" \
        "${_firewall_compat_work}/udp.txt" || {
            rm -rf "${_firewall_compat_work}"
            return 1
        }

    firewall_install_port_rules \
        "${_firewall_compat_work}/tcp.txt" \
        "${_firewall_compat_work}/udp.txt" \
        "${_firewall_compat_wan}" \
        "${_firewall_compat_divert}" \
        "${_firewall_compat_rule_base}" \
        "${_firewall_compat_rule_max}"
    _firewall_compat_status=$?
    rm -rf "${_firewall_compat_work}"
    return "${_firewall_compat_status}"
}


# Runtime state API used by Orchestrator and GUI status.
firewall_rules_present()
{
    _firewall_present_rule="$1"
    _firewall_present_max="$2"

    while [ "${_firewall_present_rule}" -le "${_firewall_present_max}" ]; do
        if /sbin/ipfw list "${_firewall_present_rule}" 2>/dev/null |
            grep -q ' divert '; then
            return 0
        fi
        _firewall_present_rule=$((_firewall_present_rule + 1))
    done

    return 1
}


# Save and restore the plugin-owned rule range during transactional reconfigure.
firewall_snapshot_rules()
{
    _firewall_snapshot_base="$1"
    _firewall_snapshot_max="$2"
    _firewall_snapshot_file="$3"
    _firewall_snapshot_tmp="${_firewall_snapshot_file}.tmp.$$"

    : > "${_firewall_snapshot_tmp}" || return 1
    /sbin/ipfw -q list 2>/dev/null |
        awk -v first="${_firewall_snapshot_base}" -v last="${_firewall_snapshot_max}" \
            '$1 >= first && $1 <= last { print }' \
            > "${_firewall_snapshot_tmp}" || {
                rm -f "${_firewall_snapshot_tmp}"
                return 1
            }
    mv -f "${_firewall_snapshot_tmp}" "${_firewall_snapshot_file}"
}

firewall_restore_rules()
{
    _firewall_restore_snapshot="$1"
    _firewall_restore_base="$2"
    _firewall_restore_max="$3"

    common_require_file \
        "${_firewall_restore_snapshot}" "firewall rule snapshot" || return 1
    firewall_remove_rules \
        "${_firewall_restore_base}" "${_firewall_restore_max}"

    (
        set -f
        while IFS= read -r _firewall_restore_line ||
              [ -n "${_firewall_restore_line}" ]; do
            [ -n "${_firewall_restore_line}" ] || continue
            set -- ${_firewall_restore_line}
            _firewall_restore_number="$1"
            shift
            /sbin/ipfw -q add "${_firewall_restore_number}" "$@" || exit 1
        done < "${_firewall_restore_snapshot}"
    )
}
