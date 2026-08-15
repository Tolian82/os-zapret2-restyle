#!/bin/sh

strategy_lab_ipv4_valid()
{
    printf '%s\n' "$1" | awk -F. '
        NF != 4 { exit 1 }
        {
            for (i = 1; i <= 4; i++) {
                if ($i !~ /^[0-9]+$/ || $i < 0 || $i > 255) exit 1
                if (length($i) > 1 && substr($i, 1, 1) == "0") exit 1
            }
        }
    '
}

strategy_lab_domain_valid()
{
    _strategy_lab_domain="$1"
    [ -n "${_strategy_lab_domain}" ] || return 1
    [ "${#_strategy_lab_domain}" -le 253 ] || return 1
    strategy_lab_ipv4_valid "${_strategy_lab_domain}" && return 1
    printf '%s\n' "${_strategy_lab_domain}" | awk '
        BEGIN { FS="." }
        NF < 2 { exit 1 }
        {
            for (i = 1; i <= NF; i++) {
                if (length($i) < 1 || length($i) > 63) exit 1
                if ($i !~ /^[a-z0-9-]+$/) exit 1
                if ($i ~ /^-/ || $i ~ /-$/) exit 1
            }
            if ($NF !~ /[a-z]/) exit 1
        }
    '
}

strategy_lab_normalize_domain()
{
    _strategy_lab_input="$1"
    [ -n "${_strategy_lab_input}" ] || return 1
    [ "${#_strategy_lab_input}" -le 254 ] || return 1
    _strategy_lab_normalized=$(printf '%s' "${_strategy_lab_input}" |
        tr '[:upper:]' '[:lower:]' | sed 's/\.$//')
    strategy_lab_domain_valid "${_strategy_lab_normalized}" || return 1
    printf '%s\n' "${_strategy_lab_normalized}"
}

strategy_lab_normalize_target()
{
    _strategy_lab_input="$1"
    [ -n "${_strategy_lab_input}" ] || return 1
    if strategy_lab_ipv4_valid "${_strategy_lab_input}"; then
        printf '%s\n' "${_strategy_lab_input}"
        return 0
    fi
    strategy_lab_normalize_domain "${_strategy_lab_input}"
}

strategy_lab_normalize_service_host()
{
    strategy_lab_normalize_domain "$1"
}

strategy_lab_target_type()
{
    if strategy_lab_ipv4_valid "$1"; then
        printf '%s\n' ip
        return 0
    fi
    strategy_lab_domain_valid "$1" || return 1
    printf '%s\n' domain
}

strategy_lab_service_host()
{
    _strategy_lab_job="${JOB_ID:-}"
    [ -n "${_strategy_lab_job}" ] || return 0
    _strategy_lab_file="$(strategy_lab_job_dir "${_strategy_lab_job}")/service-host"
    [ -r "${_strategy_lab_file}" ] || return 0
    _strategy_lab_value=''
    IFS= read -r _strategy_lab_value < "${_strategy_lab_file}" || true
    [ -n "${_strategy_lab_value}" ] || return 0
    strategy_lab_normalize_service_host "${_strategy_lab_value}"
}

strategy_lab_write_endpoints()
{
    _strategy_lab_target="$1"
    _strategy_lab_type="$2"
    _strategy_lab_output="$3"

    case "${_strategy_lab_type}" in
        domain)
            strategy_lab_domain_valid "${_strategy_lab_target}" || return 1
            case "${_strategy_lab_target}" in
                telegram.org)
                    printf '%s\n' telegram.org web.telegram.org > "${_strategy_lab_output}"
                    ;;
                *)
                    printf '%s\n' "${_strategy_lab_target}" > "${_strategy_lab_output}"
                    ;;
            esac
            ;;
        ip)
            strategy_lab_ipv4_valid "${_strategy_lab_target}" || return 1
            _strategy_lab_service_host=$(strategy_lab_service_host 2>/dev/null || true)
            if [ -n "${_strategy_lab_service_host}" ]; then
                printf '%s\n' "${_strategy_lab_service_host}" > "${_strategy_lab_output}"
            else
                printf '%s\n' "${_strategy_lab_target}" > "${_strategy_lab_output}"
            fi
            ;;
        *) return 1 ;;
    esac
}

strategy_lab_endpoints_csv()
{
    awk '
        NF {
            if (out != "") out = out ", "
            out = out $0
        }
        END { print out }
    ' "$1"
}
