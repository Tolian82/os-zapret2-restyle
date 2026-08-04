#!/bin/sh

strategy_lab_request_exit_from_output()
{
    _strategy_lab_output="$1"
    _strategy_lab_exit=$(sed -n 's/.*exit=\([0-9][0-9]*\).*/\1/p' "${_strategy_lab_output}" | tail -1)
    case "${_strategy_lab_exit}" in
        ''|*[!0-9]*)
            return 1
            ;;
    esac
    printf '%s\n' "${_strategy_lab_exit}"
}

strategy_lab_endpoint_result_write()
{
    _strategy_lab_endpoint="$1"
    _strategy_lab_status="$2"
    _strategy_lab_exit="$3"
    _strategy_lab_transport="$4"
    _strategy_lab_output="$5"
    _strategy_lab_destination="$6"
    _strategy_lab_detail=$(tail -20 "${_strategy_lab_output}" 2>/dev/null || true)

    "${STRATEGY_LAB_JQ}" -nc \
        --arg endpoint "${_strategy_lab_endpoint}" \
        --arg status "${_strategy_lab_status}" \
        --arg exit_code "${_strategy_lab_exit}" \
        --arg transport "${_strategy_lab_transport}" \
        --arg detail "${_strategy_lab_detail}" \
        '{endpoint:$endpoint,status:$status,exit_code:($exit_code|tonumber),transport:$transport,detail:$detail}' \
        > "${_strategy_lab_destination}"
}

strategy_lab_baseline_all_accessible()
{
    "${STRATEGY_LAB_JQ}" -e \
        '.endpoints | length > 0 and all(.status == "PASS")' "$1" >/dev/null
}

strategy_lab_baseline_total_count()
{
    "${STRATEGY_LAB_JQ}" -r '.endpoints | length' "$1"
}

strategy_lab_baseline_failed_count()
{
    "${STRATEGY_LAB_JQ}" -r '[.endpoints[] | select(.status != "PASS")] | length' "$1"
}

strategy_lab_baseline_dns_ok()
{
    "${STRATEGY_LAB_JQ}" -e '.dns_a == "PASS" or .dns_a == "SKIPPED"' "$1" >/dev/null
}

strategy_lab_domain_endpoint_result_write()
{
    _strategy_lab_endpoint="$1"
    _strategy_lab_ipv4_status="$2"
    _strategy_lab_ipv4_exit="$3"
    _strategy_lab_ipv4_output="$4"
    _strategy_lab_ipv6_status="$5"
    _strategy_lab_ipv6_exit="$6"
    _strategy_lab_ipv6_output="$7"
    _strategy_lab_destination="$8"
    _strategy_lab_ipv4_detail=$(tail -20 "${_strategy_lab_ipv4_output}" 2>/dev/null || true)
    _strategy_lab_ipv6_detail=""
    if [ -n "${_strategy_lab_ipv6_output}" ]; then
        _strategy_lab_ipv6_detail=$(tail -20 "${_strategy_lab_ipv6_output}" 2>/dev/null || true)
    fi

    "${STRATEGY_LAB_JQ}" -nc \
        --arg endpoint "${_strategy_lab_endpoint}" \
        --arg status "${_strategy_lab_ipv4_status}" \
        --arg ipv4_exit "${_strategy_lab_ipv4_exit}" \
        --arg ipv4_detail "${_strategy_lab_ipv4_detail}" \
        --arg ipv6_status "${_strategy_lab_ipv6_status}" \
        --arg ipv6_exit "${_strategy_lab_ipv6_exit}" \
        --arg ipv6_detail "${_strategy_lab_ipv6_detail}" \
        '{
            endpoint:$endpoint,
            status:$status,
            exit_code:($ipv4_exit|tonumber),
            transport:"tls13-ipv4",
            detail:$ipv4_detail,
            ipv4:{status:$status,exit_code:($ipv4_exit|tonumber),detail:$ipv4_detail},
            ipv6:{
                status:$ipv6_status,
                exit_code:(if $ipv6_exit=="" then null else ($ipv6_exit|tonumber) end),
                detail:$ipv6_detail
            }
        }' > "${_strategy_lab_destination}"
}
