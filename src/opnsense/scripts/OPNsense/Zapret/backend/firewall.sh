#!/bin/sh

IPFW_BIN="${IPFW_BIN:-/sbin/ipfw}"

firewall_remove_rules()
{
    _firewall_remove_rule="$1"
    _firewall_remove_max="$2"

    while [ "${_firewall_remove_rule}" -le "${_firewall_remove_max}" ]; do
        "${IPFW_BIN}" -q delete "${_firewall_remove_rule}" 2>/dev/null || true
        _firewall_remove_rule=$((_firewall_remove_rule + 1))
    done
}

# Telegram Voice Phase B uses an atomically swapped, plugin-owned address table.
# The staging table keeps the previous contents available until rule
# installation succeeds, so reconfigure rollback never exposes a partial set.
firewall_table_exists()
{
    _firewall_table_exists_name="$1"
    "${IPFW_BIN}" table "${_firewall_table_exists_name}" info >/dev/null 2>&1
}

firewall_table_destroy()
{
    _firewall_table_destroy_name="$1"
    "${IPFW_BIN}" -q table "${_firewall_table_destroy_name}" destroy \
        >/dev/null 2>&1 || true
}

firewall_table_create_empty()
{
    _firewall_table_create_name="$1"

    firewall_table_destroy "${_firewall_table_create_name}"
    "${IPFW_BIN}" -q table "${_firewall_table_create_name}" \
        create type addr || return 1
}

firewall_table_load_ipv4()
{
    _firewall_table_load_name="$1"
    _firewall_table_load_file="$2"

    common_require_file \
        "${_firewall_table_load_file}" \
        "Telegram Voice IPv4 table source" || return 1
    [ -s "${_firewall_table_load_file}" ] || {
        common_error "Telegram Voice IPv4 table source is empty"
        return 1
    }

    while IFS= read -r _firewall_table_load_entry ||
          [ -n "${_firewall_table_load_entry}" ]; do
        [ -n "${_firewall_table_load_entry}" ] || continue
        "${IPFW_BIN}" -q table "${_firewall_table_load_name}" \
            add "${_firewall_table_load_entry}" || return 1
    done < "${_firewall_table_load_file}"
}

firewall_telegram_voice_state_enabled()
{
    telegram_voice_state_is_enabled "$1"
}

firewall_telegram_voice_rule_number()
{
    _firewall_telegram_rule_base="$1"
    printf '%s\n' "${_firewall_telegram_rule_base}"
}

firewall_prepare_telegram_voice_table()
{
    _firewall_telegram_prepare_state="$1"
    _firewall_telegram_prepare_ipset="$2"

    firewall_table_create_empty "${TELEGRAM_VOICE_STAGE_TABLE}" || return 1

    if firewall_telegram_voice_state_enabled \
        "${_firewall_telegram_prepare_state}"; then
        firewall_table_load_ipv4 \
            "${TELEGRAM_VOICE_STAGE_TABLE}" \
            "${_firewall_telegram_prepare_ipset}" || {
                firewall_table_destroy "${TELEGRAM_VOICE_STAGE_TABLE}"
                return 1
            }
    elif [ -r "${_firewall_telegram_prepare_state}" ] &&
         ! grep -qx 'disabled' "${_firewall_telegram_prepare_state}"; then
        common_error "invalid Telegram Voice runtime state"
        firewall_table_destroy "${TELEGRAM_VOICE_STAGE_TABLE}"
        return 1
    fi

    if ! firewall_table_exists "${TELEGRAM_VOICE_TABLE}"; then
        "${IPFW_BIN}" -q table "${TELEGRAM_VOICE_TABLE}" \
            create type addr || {
                firewall_table_destroy "${TELEGRAM_VOICE_STAGE_TABLE}"
                return 1
            }
    fi

    "${IPFW_BIN}" -q table "${TELEGRAM_VOICE_TABLE}" \
        swap "${TELEGRAM_VOICE_STAGE_TABLE}" || {
            firewall_table_destroy "${TELEGRAM_VOICE_STAGE_TABLE}"
            return 1
        }
}

firewall_rollback_telegram_voice_table()
{
    if firewall_table_exists "${TELEGRAM_VOICE_TABLE}" &&
       firewall_table_exists "${TELEGRAM_VOICE_STAGE_TABLE}"; then
        "${IPFW_BIN}" -q table "${TELEGRAM_VOICE_TABLE}" \
            swap "${TELEGRAM_VOICE_STAGE_TABLE}" || return 1
    fi
    firewall_table_destroy "${TELEGRAM_VOICE_STAGE_TABLE}"
}

firewall_commit_telegram_voice_table()
{
    _firewall_telegram_commit_state="$1"

    firewall_table_destroy "${TELEGRAM_VOICE_STAGE_TABLE}"
    if ! firewall_telegram_voice_state_enabled \
        "${_firewall_telegram_commit_state}"; then
        firewall_table_destroy "${TELEGRAM_VOICE_TABLE}"
    fi
}

firewall_remove_telegram_voice_tables()
{
    firewall_table_destroy "${TELEGRAM_VOICE_STAGE_TABLE}"
    firewall_table_destroy "${TELEGRAM_VOICE_TABLE}"
}

firewall_install_runtime_rules()
{
    _firewall_runtime_tcp_file="$1"
    _firewall_runtime_udp_file="$2"
    _firewall_runtime_wan="$3"
    _firewall_runtime_divert="$4"
    _firewall_runtime_rule_base="$5"
    _firewall_runtime_rule_max="$6"
    _firewall_runtime_voice_state="$7"
    _firewall_runtime_voice_ipset="$8"
    _firewall_runtime_voice_rule=$(firewall_telegram_voice_rule_number \
        "${_firewall_runtime_rule_base}") || return 1

    [ "${_firewall_runtime_voice_rule}" -le \
        "${_firewall_runtime_rule_max}" ] || {
        common_error "Telegram Voice rule is outside the plugin-owned range"
        return 1
    }

    firewall_prepare_telegram_voice_table \
        "${_firewall_runtime_voice_state}" \
        "${_firewall_runtime_voice_ipset}" || return 1

    _firewall_runtime_port_rule_base="${_firewall_runtime_rule_base}"
    if firewall_telegram_voice_state_enabled \
        "${_firewall_runtime_voice_state}"; then
        firewall_remove_rules \
            "${_firewall_runtime_rule_base}" \
            "${_firewall_runtime_rule_max}"
        if ! "${IPFW_BIN}" -qf add "${_firewall_runtime_voice_rule}" \
            divert "${_firewall_runtime_divert}" \
            udp from any to "table(${TELEGRAM_VOICE_TABLE})" \
            out not diverted not sockarg \
            xmit "${_firewall_runtime_wan}"; then
            firewall_rollback_telegram_voice_table || true
            return 1
        fi
        _firewall_runtime_port_rule_base=$((_firewall_runtime_rule_base + 1))
    fi

    if ! firewall_install_port_rules \
        "${_firewall_runtime_tcp_file}" \
        "${_firewall_runtime_udp_file}" \
        "${_firewall_runtime_wan}" \
        "${_firewall_runtime_divert}" \
        "${_firewall_runtime_port_rule_base}" \
        "${_firewall_runtime_rule_max}"; then
        firewall_remove_rules \
            "${_firewall_runtime_rule_base}" \
            "${_firewall_runtime_rule_max}"
        firewall_rollback_telegram_voice_table || true
        return 1
    fi

    firewall_commit_telegram_voice_table \
        "${_firewall_runtime_voice_state}"
}

firewall_restore_telegram_voice_table()
{
    _firewall_telegram_restore_state="$1"
    _firewall_telegram_restore_ipset="$2"

    if firewall_telegram_voice_state_enabled \
        "${_firewall_telegram_restore_state}"; then
        firewall_prepare_telegram_voice_table \
            "${_firewall_telegram_restore_state}" \
            "${_firewall_telegram_restore_ipset}" || return 1
        firewall_commit_telegram_voice_table \
            "${_firewall_telegram_restore_state}"
        return $?
    fi

    firewall_remove_telegram_voice_tables
}

firewall_telegram_voice_rule_present()
{
    _firewall_telegram_present_rule=$(firewall_telegram_voice_rule_number \
        "$1") || return 1
    "${IPFW_BIN}" list "${_firewall_telegram_present_rule}" 2>/dev/null |
        grep -Fq "table(${TELEGRAM_VOICE_TABLE})"
}

firewall_telegram_voice_table_count()
{
    if ! firewall_table_exists "${TELEGRAM_VOICE_TABLE}"; then
        printf '%s\n' 0
        return 0
    fi
    "${IPFW_BIN}" table "${TELEGRAM_VOICE_TABLE}" list 2>/dev/null |
        awk '$1 ~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+(\/[0-9]+)?$/ { count++ }
             END { print count + 0 }'
}

firewall_telegram_voice_rule_counters()
{
    _firewall_telegram_counter_rule=$(firewall_telegram_voice_rule_number \
        "$1") || return 1
    firewall_telegram_voice_rule_present "$1" || return 1
    _firewall_telegram_counter_line=$("${IPFW_BIN}" show \
        "${_firewall_telegram_counter_rule}" 2>/dev/null |
        awk -v rule="${_firewall_telegram_counter_rule}" \
            '$1 + 0 == rule + 0 { print $2, $3; exit }')
    [ -n "${_firewall_telegram_counter_line}" ] || return 1
    printf '%s\n' "${_firewall_telegram_counter_line}"
}

firewall_telegram_voice_runtime_complete()
{
    _firewall_telegram_complete_state="$1"
    _firewall_telegram_complete_rule_base="$2"

    if ! firewall_telegram_voice_state_enabled \
        "${_firewall_telegram_complete_state}"; then
        ! firewall_telegram_voice_rule_present \
            "${_firewall_telegram_complete_rule_base}" &&
        ! firewall_table_exists "${TELEGRAM_VOICE_TABLE}" &&
        ! firewall_table_exists "${TELEGRAM_VOICE_STAGE_TABLE}"
        return $?
    fi
    firewall_telegram_voice_rule_present \
        "${_firewall_telegram_complete_rule_base}" || return 1
    firewall_table_exists "${TELEGRAM_VOICE_TABLE}" || return 1
    [ "$(firewall_telegram_voice_table_count)" -gt 0 ] 2>/dev/null
}

firewall_ensure_default_accept()
{
    _firewall_default=$(/sbin/sysctl -n \
        net.inet.ip.fw.default_to_accept 2>/dev/null)

    [ "${_firewall_default}" = "1" ] ||
        "${IPFW_BIN}" -q add 65534 allow ip from any to any 2>/dev/null || true
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
    [ "${_firewall_prepared:-0}" = "1" ] && return 0

    kldstat -q -m ipdivert || kldload ipdivert || return 1
    kldstat -q -m ipfw || kldload ipfw || return 1
    firewall_ensure_default_accept || return 1
    firewall_configure_reinject || return 1

    _firewall_prepared=1
    return 0
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
        "${IPFW_BIN}" -qf add "${_firewall_ports_rule}" \
            divert "${_firewall_ports_divert}" \
            tcp from any to any "${_firewall_ports_tcp}" \
            out not diverted not sockarg \
            xmit "${_firewall_ports_wan}" || return 1
        _firewall_ports_rule=$((_firewall_ports_rule + 1))
    fi

    if [ -n "${_firewall_ports_udp}" ]; then
        "${IPFW_BIN}" -qf add "${_firewall_ports_rule}" \
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
        if "${IPFW_BIN}" list "${_firewall_present_rule}" 2>/dev/null |
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
    "${IPFW_BIN}" -q list 2>/dev/null |
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
            "${IPFW_BIN}" -q add "${_firewall_restore_number}" "$@" || exit 1
        done < "${_firewall_restore_snapshot}"
    )
}
