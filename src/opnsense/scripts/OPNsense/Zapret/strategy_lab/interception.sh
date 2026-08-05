#!/bin/sh

strategy_lab_candidate_bindings_file()
{
    printf '%s/endpoint-bindings.tsv\n' "$1"
}

strategy_lab_candidate_binding_field()
{
    _slint_workdir="$1"
    _slint_index="$2"
    _slint_field="$3"
    _slint_bindings=$(strategy_lab_candidate_bindings_file "${_slint_workdir}")
    [ -r "${_slint_bindings}" ] || return 1
    awk -F '\t' -v wanted="${_slint_index}" -v field="${_slint_field}" '
        $1 == wanted {
            print $field
            found=1
            exit
        }
        END { if (!found) exit 1 }
    ' "${_slint_bindings}"
}

strategy_lab_candidate_probe_begin()
{
    _slint_workdir="$1"
    _slint_index="$2"
    _slint_state="$3"
    _slint_selected=$(strategy_lab_candidate_binding_field "${_slint_workdir}" "${_slint_index}" 3) || return 1
    _slint_rule=$(strategy_lab_candidate_binding_field "${_slint_workdir}" "${_slint_index}" 4) || return 1
    _slint_counters=$(strategy_lab_firewall_rule_counters "${_slint_rule}") || return 1
    _slint_packets=$(printf '%s\n' "${_slint_counters}" | awk '{print $1}')
    _slint_bytes=$(printf '%s\n' "${_slint_counters}" | awk '{print $2}')
    case "${_slint_packets}:${_slint_bytes}" in
        *[!0-9:]*|:|*:) return 1 ;;
    esac
    {
        printf '%s\n' "${_slint_selected}"
        printf '%s\n' "${_slint_rule}"
        printf '%s\n' "${_slint_packets}"
        printf '%s\n' "${_slint_bytes}"
    } > "${_slint_state}"
}

strategy_lab_request_remote_ip_from_output()
{
    _slint_output="$1"
    _slint_remote=$(sed -n 's/.*remote_ip=\([^[:space:]]*\).*/\1/p' "${_slint_output}" | tail -1)
    [ -n "${_slint_remote}" ] || return 1
    printf '%s\n' "${_slint_remote}"
}

strategy_lab_candidate_endpoint_result_write()
{
    _slint_endpoint="$1"
    _slint_exit="$2"
    _slint_transport="$3"
    _slint_output="$4"
    _slint_remote="$5"
    _slint_state="$6"
    _slint_destination="$7"

    [ -r "${_slint_state}" ] || return 1
    _slint_selected=$(sed -n '1p' "${_slint_state}")
    _slint_rule=$(sed -n '2p' "${_slint_state}")
    _slint_before_packets=$(sed -n '3p' "${_slint_state}")
    _slint_before_bytes=$(sed -n '4p' "${_slint_state}")
    _slint_after=$(strategy_lab_firewall_rule_counters "${_slint_rule}") || return 1
    _slint_after_packets=$(printf '%s\n' "${_slint_after}" | awk '{print $1}')
    _slint_after_bytes=$(printf '%s\n' "${_slint_after}" | awk '{print $2}')
    _slint_detail=$(tail -20 "${_slint_output}" 2>/dev/null || true)

    _slint_endpoint_match=false
    [ "${_slint_remote}" = "${_slint_selected}" ] && _slint_endpoint_match=true
    _slint_intercepted=false
    if [ "${_slint_after_packets}" -gt "${_slint_before_packets}" ] 2>/dev/null; then
        _slint_intercepted=true
    fi
    _slint_status=FAIL
    if [ "${_slint_exit}" -eq 0 ] 2>/dev/null &&
       [ "${_slint_endpoint_match}" = true ] &&
       [ "${_slint_intercepted}" = true ]; then
        _slint_status=PASS
    fi

    "${STRATEGY_LAB_JQ}" -nc \
        --arg endpoint "${_slint_endpoint}" \
        --arg status "${_slint_status}" \
        --arg exit_code "${_slint_exit}" \
        --arg transport "${_slint_transport}" \
        --arg detail "${_slint_detail}" \
        --arg selected_ip "${_slint_selected}" \
        --arg remote_ip "${_slint_remote}" \
        --arg rule "${_slint_rule}" \
        --arg before_packets "${_slint_before_packets}" \
        --arg before_bytes "${_slint_before_bytes}" \
        --arg after_packets "${_slint_after_packets}" \
        --arg after_bytes "${_slint_after_bytes}" \
        --argjson endpoint_match "${_slint_endpoint_match}" \
        --argjson intercepted "${_slint_intercepted}" '
        {
            endpoint:$endpoint,
            status:$status,
            exit_code:($exit_code|tonumber),
            transport:$transport,
            detail:$detail,
            selected_ip:$selected_ip,
            remote_ip:$remote_ip,
            endpoint_match:$endpoint_match,
            firewall:{
                rule:($rule|tonumber),
                packets_before:($before_packets|tonumber),
                packets_after:($after_packets|tonumber),
                bytes_before:($before_bytes|tonumber),
                bytes_after:($after_bytes|tonumber),
                intercepted:$intercepted
            }
        }' > "${_slint_destination}"
}
