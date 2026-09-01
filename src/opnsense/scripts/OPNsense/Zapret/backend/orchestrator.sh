#!/bin/sh

# Milestone 5 Native Backend v2 Orchestrator.
#
# Orchestrator coordinates public module APIs only. It does not parse,
# normalize, copy, inspect, launch, or manipulate firewall state itself.

orchestrator_stage()
{
    _orchestrator_stage_file="$1"
    _orchestrator_stage_index="$2"
    _orchestrator_stage_total="$3"
    _orchestrator_stage_name="$4"
    _orchestrator_stage_state="$5"
    _orchestrator_stage_message="${6:-}"

    stage_write \
        "${_orchestrator_stage_file}" \
        "${_orchestrator_stage_index}" \
        "${_orchestrator_stage_total}" \
        "${_orchestrator_stage_name}" \
        "${_orchestrator_stage_state}" \
        "${_orchestrator_stage_message}"
}

orchestrator_fail_stage()
{
    stage_fail "$1" "$2" "$3" "$4" "$5"
}

orchestrator_last_error()
{
    _orchestrator_error_file="$1"
    _orchestrator_error_fallback="$2"
    _orchestrator_error_message=""

    if [ -s "${_orchestrator_error_file}" ]; then
        _orchestrator_error_message=$(awk 'NF { line=$0 } END { print line }' \
            "${_orchestrator_error_file}" | \
            sed 's/^ERROR:[[:space:]]*//')
    fi
    [ -n "${_orchestrator_error_message}" ] ||
        _orchestrator_error_message="${_orchestrator_error_fallback}"
    printf '%s\n' "${_orchestrator_error_message}"
}

orchestrator_fail_from_log()
{
    _orchestrator_fail_log_stage_file="$1"
    _orchestrator_fail_log_index="$2"
    _orchestrator_fail_log_total="$3"
    _orchestrator_fail_log_name="$4"
    _orchestrator_fail_log_file="$5"
    _orchestrator_fail_log_fallback="$6"

    [ ! -s "${_orchestrator_fail_log_file}" ] ||
        cat "${_orchestrator_fail_log_file}" >&2
    _orchestrator_fail_log_message=$(orchestrator_last_error \
        "${_orchestrator_fail_log_file}" \
        "${_orchestrator_fail_log_fallback}")
    orchestrator_fail_stage \
        "${_orchestrator_fail_log_stage_file}" \
        "${_orchestrator_fail_log_index}" \
        "${_orchestrator_fail_log_total}" \
        "${_orchestrator_fail_log_name}" \
        "${_orchestrator_fail_log_message}"
}

orchestrator_build_release()
{
    _orchestrator_build_config="$1"
    _orchestrator_build_zapret_dir="$2"
    _orchestrator_build_active_dir="$3"
    _orchestrator_build_workspace="$4"
    _orchestrator_build_release="$5"
    _orchestrator_build_stage_file="$6"
    _orchestrator_build_total=8
    _orchestrator_build_error="${_orchestrator_build_workspace}/stage-error.log"

    orchestrator_stage \
        "${_orchestrator_build_stage_file}" 1 "${_orchestrator_build_total}" \
        config running "loading generated configuration" || return 1
    : > "${_orchestrator_build_error}"
    config_load "${_orchestrator_build_config}" 2>"${_orchestrator_build_error}" || {
        orchestrator_fail_from_log \
            "${_orchestrator_build_stage_file}" 1 \
            "${_orchestrator_build_total}" config \
            "${_orchestrator_build_error}" \
            "configuration loading failed"
        return 1
    }

    [ "${ZAPRET_ENABLED}" = "1" ] || {
        orchestrator_fail_stage \
            "${_orchestrator_build_stage_file}" 1 \
            "${_orchestrator_build_total}" config \
            "service is disabled"
        return 2
    }
    [ -n "${TRAFFIC_ARGS}" ] || {
        common_error "Traffic Strategy is empty"
        orchestrator_fail_stage \
            "${_orchestrator_build_stage_file}" 1 \
            "${_orchestrator_build_total}" config \
            "Traffic Strategy is empty"
        return 1
    }
    orchestrator_stage \
        "${_orchestrator_build_stage_file}" 1 "${_orchestrator_build_total}" \
        config ok "configuration loaded" || return 1

    orchestrator_stage \
        "${_orchestrator_build_stage_file}" 2 "${_orchestrator_build_total}" \
        parser running "parsing and normalizing Traffic Strategy" || return 1
    _orchestrator_build_registry="${_orchestrator_build_workspace}/target-registry.tsv"
    _orchestrator_build_profile_count=0

    : > "${_orchestrator_build_error}"
    _orchestrator_build_profile_count=$(profile_pipeline_parse \
        "${_orchestrator_build_workspace}" \
        "${_orchestrator_build_profile_count}" \
        "${TRAFFIC_ARGS}" 2>"${_orchestrator_build_error}") || {
            orchestrator_fail_from_log \
                "${_orchestrator_build_stage_file}" 2 \
                "${_orchestrator_build_total}" parser \
                "${_orchestrator_build_error}" \
                "strategy parsing failed"
            return 1
        }

    : > "${_orchestrator_build_error}"
    _orchestrator_build_profile_count=$(profile_pipeline_registry \
        "${_orchestrator_build_workspace}" \
        "${_orchestrator_build_profile_count}" \
        "${_orchestrator_build_registry}" 2>"${_orchestrator_build_error}") || {
            orchestrator_fail_from_log \
                "${_orchestrator_build_stage_file}" 2 \
                "${_orchestrator_build_total}" parser \
                "${_orchestrator_build_error}" \
                "Target registry generation failed"
            return 1
        }

    : > "${_orchestrator_build_error}"
    _orchestrator_build_profile_count=$(profile_pipeline_target_mode \
        "${_orchestrator_build_workspace}" \
        "${_orchestrator_build_profile_count}" \
        "${HOSTLIST_MODE}" \
        "${_orchestrator_build_registry}" 2>"${_orchestrator_build_error}") || {
            orchestrator_fail_from_log \
                "${_orchestrator_build_stage_file}" 2 \
                "${_orchestrator_build_total}" parser \
                "${_orchestrator_build_error}" \
                "Target Mode processing failed"
            return 1
        }

    : > "${_orchestrator_build_error}"
    _orchestrator_build_profile_count=$(profile_pipeline_normalize \
        "${_orchestrator_build_workspace}" \
        "${_orchestrator_build_profile_count}" \
        2>"${_orchestrator_build_error}") || {
            orchestrator_fail_from_log \
                "${_orchestrator_build_stage_file}" 2 \
                "${_orchestrator_build_total}" parser \
                "${_orchestrator_build_error}" \
                "runtime profile normalization failed"
            return 1
        }

    : > "${_orchestrator_build_error}"
    _orchestrator_build_profile_count=$(profile_pipeline_index \
        "${_orchestrator_build_workspace}" \
        "${_orchestrator_build_profile_count}" \
        2>"${_orchestrator_build_error}") || {
            orchestrator_fail_from_log \
                "${_orchestrator_build_stage_file}" 2 \
                "${_orchestrator_build_total}" parser \
                "${_orchestrator_build_error}" \
                "placeholder indexing failed"
            return 1
        }

    orchestrator_stage \
        "${_orchestrator_build_stage_file}" 2 "${_orchestrator_build_total}" \
        parser ok "strategy parsed and normalized" || return 1

    orchestrator_stage \
        "${_orchestrator_build_stage_file}" 3 "${_orchestrator_build_total}" \
        targets running "preparing and resolving Targets" || return 1
    common_prepare_dir "${_orchestrator_build_release}" || return 1
    _orchestrator_build_managed_source="${_orchestrator_build_release}/managed"
    _orchestrator_build_managed_reference="${_orchestrator_build_active_dir}/managed"

    : > "${_orchestrator_build_error}"
    targets_prepare_managed \
        "${_orchestrator_build_managed_source}" \
        "${YOUTUBE_DOMAINS}" \
        "${TELEGRAM_IPS}" \
        "${USER_DOMAINS}" \
        2>"${_orchestrator_build_error}" || {
            orchestrator_fail_from_log \
                "${_orchestrator_build_stage_file}" 3 \
                "${_orchestrator_build_total}" targets \
                "${_orchestrator_build_error}" \
                "managed Target validation failed"
            return 1
        }
    : > "${_orchestrator_build_error}"
    _orchestrator_build_exclude_source=$(exclude_prepare \
        "${_orchestrator_build_managed_source}" \
        "${EXCLUDE_DOMAINS}" \
        2>"${_orchestrator_build_error}") || {
            orchestrator_fail_from_log \
                "${_orchestrator_build_stage_file}" 3 \
                "${_orchestrator_build_total}" targets \
                "${_orchestrator_build_error}" \
                "Exclude Domains validation failed"
            return 1
        }
    _orchestrator_build_exclude_reference="${_orchestrator_build_managed_reference}/hostlist-exclude.txt"

    _orchestrator_build_catalog="${_orchestrator_build_workspace}/storage-catalog.tsv"
    : > "${_orchestrator_build_error}"
    storage_catalog_build "${_orchestrator_build_catalog}" \
        2>"${_orchestrator_build_error}" || {
            orchestrator_fail_from_log \
                "${_orchestrator_build_stage_file}" 3 \
                "${_orchestrator_build_total}" targets \
                "${_orchestrator_build_error}" \
                "Target storage catalog generation failed"
            return 1
        }
    _orchestrator_build_targets="${_orchestrator_build_workspace}/traffic.targets.conf"
    : > "${_orchestrator_build_error}"
    targets_resolve_all_mapped \
        "${_orchestrator_build_workspace}" \
        "${_orchestrator_build_profile_count}" \
        "${_orchestrator_build_registry}" \
        "${_orchestrator_build_catalog}" \
        "${_orchestrator_build_managed_source}" \
        "${_orchestrator_build_managed_reference}" \
        "${_orchestrator_build_zapret_dir}" \
        "${_orchestrator_build_targets}" \
        2>"${_orchestrator_build_error}" || {
            orchestrator_fail_from_log \
                "${_orchestrator_build_stage_file}" 3 \
                "${_orchestrator_build_total}" targets \
                "${_orchestrator_build_error}" \
                "Target resolution failed"
            return 1
        }
    orchestrator_stage \
        "${_orchestrator_build_stage_file}" 3 "${_orchestrator_build_total}" \
        targets ok "Targets resolved" || return 1

    orchestrator_stage \
        "${_orchestrator_build_stage_file}" 4 "${_orchestrator_build_total}" \
        blobs running "resolving blob declarations" || return 1
    _orchestrator_build_blob_args="${_orchestrator_build_workspace}/blob-args.conf"
    _orchestrator_build_loaded_blobs="${_orchestrator_build_workspace}/loaded-blobs.txt"
    _orchestrator_build_user_traffic="${_orchestrator_build_release}/${TELEGRAM_VOICE_USER_TRAFFIC_FILE_NAME}"
    _orchestrator_build_traffic="${_orchestrator_build_release}/traffic.conf"
    _orchestrator_build_voice_state="${_orchestrator_build_release}/${TELEGRAM_VOICE_STATE_FILE_NAME}"
    : > "${_orchestrator_build_error}"
    blobs_resolve_file \
        "${_orchestrator_build_targets}" \
        "${_orchestrator_build_user_traffic}" \
        "${_orchestrator_build_blob_args}" \
        "${_orchestrator_build_loaded_blobs}" \
        "${_orchestrator_build_zapret_dir}/files/fake" \
        2>"${_orchestrator_build_error}" || {
            orchestrator_fail_from_log \
                "${_orchestrator_build_stage_file}" 4 \
                "${_orchestrator_build_total}" blobs \
                "${_orchestrator_build_error}" \
                "blob declaration resolution failed"
            return 1
        }
    : > "${_orchestrator_build_error}"
    telegram_voice_build_effective_traffic \
        "${TELEGRAM_VOICE_MARKER_FILE}" \
        "${_orchestrator_build_managed_source}/ipset-telegram.txt" \
        "${_orchestrator_build_managed_reference}/ipset-telegram.txt" \
        "${_orchestrator_build_user_traffic}" \
        "${_orchestrator_build_traffic}" \
        "${_orchestrator_build_voice_state}" \
        2>"${_orchestrator_build_error}" || {
            orchestrator_fail_from_log \
                "${_orchestrator_build_stage_file}" 4 \
                "${_orchestrator_build_total}" blobs \
                "${_orchestrator_build_error}" \
                "Telegram Voice profile generation failed"
            return 1
        }
    _orchestrator_build_extra_input="${_orchestrator_build_workspace}/extra.input.conf"
    _orchestrator_build_extra="${_orchestrator_build_release}/extra.conf"
    common_write_text_file \
        "${_orchestrator_build_extra_input}" "${EXTRA_ARGS}" || return 1
    : > "${_orchestrator_build_error}"
    blobs_resolve_file_append \
        "${_orchestrator_build_extra_input}" \
        "${_orchestrator_build_extra}" \
        "${_orchestrator_build_blob_args}" \
        "${_orchestrator_build_loaded_blobs}" \
        "${_orchestrator_build_zapret_dir}/files/fake" \
        2>"${_orchestrator_build_error}" || {
            orchestrator_fail_from_log \
                "${_orchestrator_build_stage_file}" 4 \
                "${_orchestrator_build_total}" blobs \
                "${_orchestrator_build_error}" \
                "Extra Arguments blob resolution failed"
            return 1
        }
    orchestrator_stage \
        "${_orchestrator_build_stage_file}" 4 "${_orchestrator_build_total}" \
        blobs ok "blob declarations resolved" || return 1

    orchestrator_stage \
        "${_orchestrator_build_stage_file}" 5 "${_orchestrator_build_total}" \
        ports running "extracting TCP and UDP ports" || return 1
    _orchestrator_build_tcp="${_orchestrator_build_release}/tcp-ports.txt"
    _orchestrator_build_udp="${_orchestrator_build_release}/udp-ports.txt"
    : > "${_orchestrator_build_error}"
    ports_extract_file \
        "${_orchestrator_build_user_traffic}" \
        "${_orchestrator_build_tcp}" \
        "${_orchestrator_build_udp}" \
        2>"${_orchestrator_build_error}" || {
            orchestrator_fail_from_log \
                "${_orchestrator_build_stage_file}" 5 \
                "${_orchestrator_build_total}" ports \
                "${_orchestrator_build_error}" \
                "port extraction failed"
            return 1
        }
    orchestrator_stage \
        "${_orchestrator_build_stage_file}" 5 "${_orchestrator_build_total}" \
        ports ok "ports extracted" || return 1

    orchestrator_stage \
        "${_orchestrator_build_stage_file}" 6 "${_orchestrator_build_total}" \
        generator running "generating dvtws2 arguments" || return 1
    _orchestrator_build_args="${_orchestrator_build_release}/dvtws.args"
    : > "${_orchestrator_build_error}"
    generator_build_args_mapped \
        "${_orchestrator_build_args}" \
        "${DIVERT_PORT}" \
        "${_orchestrator_build_traffic}" \
        "${_orchestrator_build_extra}" \
        "${_orchestrator_build_blob_args}" \
        "${_orchestrator_build_exclude_source}" \
        "${_orchestrator_build_exclude_reference}" \
        "${_orchestrator_build_zapret_dir}/lua/zapret-lib.lua" \
        "${_orchestrator_build_zapret_dir}/lua/zapret-antidpi.lua" \
        "${_orchestrator_build_zapret_dir}/lua/zapret-auto.lua" \
        2>"${_orchestrator_build_error}" || {
            orchestrator_fail_from_log \
                "${_orchestrator_build_stage_file}" 6 \
                "${_orchestrator_build_total}" generator \
                "${_orchestrator_build_error}" \
                "argument generation failed"
            return 1
        }
    orchestrator_stage \
        "${_orchestrator_build_stage_file}" 6 "${_orchestrator_build_total}" \
        generator ok "arguments generated" || return 1

    orchestrator_stage \
        "${_orchestrator_build_stage_file}" 7 "${_orchestrator_build_total}" \
        validator running "validating staged release" || return 1
    : > "${_orchestrator_build_error}"
    validator_validate_build_mapped \
        "${_orchestrator_build_args}" \
        "${_orchestrator_build_user_traffic}" \
        "${_orchestrator_build_tcp}" \
        "${_orchestrator_build_udp}" \
        "${_orchestrator_build_zapret_dir}" \
        "${_orchestrator_build_active_dir}" \
        "${_orchestrator_build_release}" \
        2>"${_orchestrator_build_error}" || {
            orchestrator_fail_from_log \
                "${_orchestrator_build_stage_file}" 7 \
                "${_orchestrator_build_total}" validator \
                "${_orchestrator_build_error}" \
                "staged release validation failed"
            return 1
        }
    orchestrator_stage \
        "${_orchestrator_build_stage_file}" 7 "${_orchestrator_build_total}" \
        validator ok "staged release validated" || return 1
    orchestrator_stage \
        "${_orchestrator_build_stage_file}" 8 "${_orchestrator_build_total}" \
        ready ok "release build is ready" || return 1
}

orchestrator_cleanup_runtime()
{
    _orchestrator_cleanup_child="$1"
    _orchestrator_cleanup_supervisor_daemon="$2"
    _orchestrator_cleanup_supervisor_monitor="$3"
    _orchestrator_cleanup_rule_base="$4"
    _orchestrator_cleanup_rule_max="$5"

    supervisor_stop \
        "${_orchestrator_cleanup_supervisor_daemon}" \
        "${_orchestrator_cleanup_supervisor_monitor}"
    firewall_remove_rules \
        "${_orchestrator_cleanup_rule_base}" \
        "${_orchestrator_cleanup_rule_max}"
    firewall_remove_telegram_voice_tables
    launcher_stop "${_orchestrator_cleanup_child}" 5
}

orchestrator_runtime_is_complete()
{
    _orchestrator_complete_child="$1"
    _orchestrator_complete_monitor="$2"
    _orchestrator_complete_rule_base="$3"
    _orchestrator_complete_rule_max="$4"
    _orchestrator_complete_active_dir="$5"

    launcher_is_running "${_orchestrator_complete_child}" &&
    supervisor_is_running "${_orchestrator_complete_monitor}" &&
    firewall_rules_present \
        "${_orchestrator_complete_rule_base}" \
        "${_orchestrator_complete_rule_max}" &&
    firewall_telegram_voice_runtime_complete \
        "${_orchestrator_complete_active_dir}/${TELEGRAM_VOICE_STATE_FILE_NAME}" \
        "${_orchestrator_complete_rule_base}"
}

orchestrator_native_start()
{
    _orchestrator_start_config="$1"
    _orchestrator_start_zapret_dir="$2"
    _orchestrator_start_active_dir="$3"
    _orchestrator_start_backup_root="$4"
    _orchestrator_start_dvtws_bin="$5"
    _orchestrator_start_child_pid="$6"
    _orchestrator_start_supervisor_daemon="$7"
    _orchestrator_start_supervisor_monitor="$8"
    _orchestrator_start_supervisor_loop="$9"
    shift 9
    _orchestrator_start_service_script="$1"
    _orchestrator_start_rule_base="$2"
    _orchestrator_start_rule_max="$3"
    _orchestrator_start_stage_file="$4"
    _orchestrator_start_log="$5"
    _orchestrator_start_supervisor_log="$6"
    _orchestrator_start_total=13

    if orchestrator_runtime_is_complete \
        "${_orchestrator_start_child_pid}" \
        "${_orchestrator_start_supervisor_monitor}" \
        "${_orchestrator_start_rule_base}" \
        "${_orchestrator_start_rule_max}" \
        "${_orchestrator_start_active_dir}"; then
        launcher_status "${_orchestrator_start_child_pid}"
        return 0
    fi

    orchestrator_cleanup_runtime \
        "${_orchestrator_start_child_pid}" \
        "${_orchestrator_start_supervisor_daemon}" \
        "${_orchestrator_start_supervisor_monitor}" \
        "${_orchestrator_start_rule_base}" \
        "${_orchestrator_start_rule_max}"

    _orchestrator_start_workspace=$(common_create_workspace \
        zapret-orchestrator) || return 1
    _orchestrator_start_release="${_orchestrator_start_workspace}/release"

    orchestrator_build_release \
        "${_orchestrator_start_config}" \
        "${_orchestrator_start_zapret_dir}" \
        "${_orchestrator_start_active_dir}" \
        "${_orchestrator_start_workspace}" \
        "${_orchestrator_start_release}" \
        "${_orchestrator_start_stage_file}"
    _orchestrator_start_build_status=$?

    if [ "${_orchestrator_start_build_status}" -eq 2 ]; then
        common_cleanup_dir "${_orchestrator_start_workspace}"
        echo "zapret is not running (disabled in settings)"
        return 0
    fi
    [ "${_orchestrator_start_build_status}" -eq 0 ] || {
        common_cleanup_dir "${_orchestrator_start_workspace}"
        return 1
    }

    common_set_directory_mode "${_orchestrator_start_release}" 0755 || {
        common_cleanup_dir "${_orchestrator_start_workspace}"
        return 1
    }
    validator_validate_runtime_modes "${_orchestrator_start_release}" || {
        common_cleanup_dir "${_orchestrator_start_workspace}"
        return 1
    }

    orchestrator_stage \
        "${_orchestrator_start_stage_file}" 9 "${_orchestrator_start_total}" \
        atomic running "activating validated release" || return 1

    _orchestrator_start_backup=$(atomic_install_tree \
        "${_orchestrator_start_release}" \
        "${_orchestrator_start_active_dir}" \
        "${_orchestrator_start_backup_root}") || {
            common_cleanup_dir "${_orchestrator_start_workspace}"
            orchestrator_fail_stage \
                "${_orchestrator_start_stage_file}" 9 \
                "${_orchestrator_start_total}" atomic \
                "atomic activation failed"
            return 1
        }
    common_cleanup_dir "${_orchestrator_start_workspace}"

    orchestrator_stage \
        "${_orchestrator_start_stage_file}" 10 "${_orchestrator_start_total}" \
        launcher running "starting one dvtws2 instance" || return 1

    if ! launcher_start_once \
        "${_orchestrator_start_dvtws_bin}" \
        "${_orchestrator_start_active_dir}/dvtws.args" \
        "${_orchestrator_start_child_pid}" \
        "${_orchestrator_start_log}" 5; then
        launcher_stop "${_orchestrator_start_child_pid}" 2
        atomic_restore_tree \
            "${_orchestrator_start_active_dir}" \
            "${_orchestrator_start_backup}" || true
        orchestrator_fail_stage \
            "${_orchestrator_start_stage_file}" 10 \
            "${_orchestrator_start_total}" launcher \
            "dvtws2 failed the startup stability check"
        return 1
    fi

    orchestrator_stage \
        "${_orchestrator_start_stage_file}" 10 "${_orchestrator_start_total}" \
        launcher ok "dvtws2 passed the stability window" || return 1
    orchestrator_stage \
        "${_orchestrator_start_stage_file}" 11 "${_orchestrator_start_total}" \
        firewall running "installing divert rules" || return 1

    if ! firewall_prepare; then
        orchestrator_cleanup_runtime \
            "${_orchestrator_start_child_pid}" \
            "${_orchestrator_start_supervisor_daemon}" \
            "${_orchestrator_start_supervisor_monitor}" \
            "${_orchestrator_start_rule_base}" \
            "${_orchestrator_start_rule_max}"
        atomic_restore_tree \
            "${_orchestrator_start_active_dir}" \
            "${_orchestrator_start_backup}" || true
        orchestrator_fail_stage \
            "${_orchestrator_start_stage_file}" 11 \
            "${_orchestrator_start_total}" firewall \
            "firewall preparation failed"
        return 1
    fi

    _orchestrator_start_wan=$(config_resolve_interface "${WAN_IF}") || {
        orchestrator_cleanup_runtime \
            "${_orchestrator_start_child_pid}" \
            "${_orchestrator_start_supervisor_daemon}" \
            "${_orchestrator_start_supervisor_monitor}" \
            "${_orchestrator_start_rule_base}" \
            "${_orchestrator_start_rule_max}"
        atomic_restore_tree \
            "${_orchestrator_start_active_dir}" \
            "${_orchestrator_start_backup}" || true
        orchestrator_fail_stage \
            "${_orchestrator_start_stage_file}" 11 \
            "${_orchestrator_start_total}" firewall \
            "WAN interface resolution failed for '${WAN_IF}'"
        return 1
    }

    if ! firewall_install_runtime_rules \
        "${_orchestrator_start_active_dir}/tcp-ports.txt" \
        "${_orchestrator_start_active_dir}/udp-ports.txt" \
        "${_orchestrator_start_wan}" \
        "${DIVERT_PORT}" \
        "${_orchestrator_start_rule_base}" \
        "${_orchestrator_start_rule_max}" \
        "${_orchestrator_start_active_dir}/${TELEGRAM_VOICE_STATE_FILE_NAME}" \
        "${_orchestrator_start_active_dir}/managed/ipset-telegram.txt"; then
        orchestrator_cleanup_runtime \
            "${_orchestrator_start_child_pid}" \
            "${_orchestrator_start_supervisor_daemon}" \
            "${_orchestrator_start_supervisor_monitor}" \
            "${_orchestrator_start_rule_base}" \
            "${_orchestrator_start_rule_max}"
        atomic_restore_tree \
            "${_orchestrator_start_active_dir}" \
            "${_orchestrator_start_backup}" || true
        orchestrator_fail_stage \
            "${_orchestrator_start_stage_file}" 11 \
            "${_orchestrator_start_total}" firewall \
            "divert rule installation failed"
        return 1
    fi

    orchestrator_stage \
        "${_orchestrator_start_stage_file}" 11 "${_orchestrator_start_total}" \
        firewall ok "WAN ${WAN_IF} resolved to ${_orchestrator_start_wan}" ||
        return 1
    orchestrator_stage \
        "${_orchestrator_start_stage_file}" 12 "${_orchestrator_start_total}" \
        supervisor running "starting runtime supervisor" || return 1

    if ! supervisor_start \
        "${_orchestrator_start_supervisor_loop}" \
        "${_orchestrator_start_supervisor_daemon}" \
        "${_orchestrator_start_supervisor_monitor}" \
        "${_orchestrator_start_child_pid}" \
        "${_orchestrator_start_service_script}" \
        "${_orchestrator_start_dvtws_bin}" \
        "${_orchestrator_start_supervisor_log}"; then
        orchestrator_cleanup_runtime \
            "${_orchestrator_start_child_pid}" \
            "${_orchestrator_start_supervisor_daemon}" \
            "${_orchestrator_start_supervisor_monitor}" \
            "${_orchestrator_start_rule_base}" \
            "${_orchestrator_start_rule_max}"
        atomic_restore_tree \
            "${_orchestrator_start_active_dir}" \
            "${_orchestrator_start_backup}" || true
        orchestrator_fail_stage \
            "${_orchestrator_start_stage_file}" 12 \
            "${_orchestrator_start_total}" supervisor \
            "runtime supervisor failed to start"
        return 1
    fi

    orchestrator_stage \
        "${_orchestrator_start_stage_file}" 12 "${_orchestrator_start_total}" \
        supervisor ok "runtime supervisor active" || return 1
    orchestrator_stage \
        "${_orchestrator_start_stage_file}" 13 "${_orchestrator_start_total}" \
        ready ok "zapret is ready" || return 1

    launcher_status "${_orchestrator_start_child_pid}"
}

orchestrator_restore_previous_runtime()
{
    _orchestrator_restore_active_dir="$1"
    _orchestrator_restore_backup="$2"
    _orchestrator_restore_old_complete="$3"
    _orchestrator_restore_dvtws_bin="$4"
    _orchestrator_restore_child_pid="$5"
    _orchestrator_restore_supervisor_daemon="$6"
    _orchestrator_restore_supervisor_monitor="$7"
    _orchestrator_restore_supervisor_loop="$8"
    _orchestrator_restore_service_script="$9"
    shift 9
    _orchestrator_restore_firewall_snapshot="$1"
    _orchestrator_restore_rule_base="$2"
    _orchestrator_restore_rule_max="$3"
    _orchestrator_restore_log="$4"
    _orchestrator_restore_supervisor_log="$5"

    supervisor_stop \
        "${_orchestrator_restore_supervisor_daemon}" \
        "${_orchestrator_restore_supervisor_monitor}"
    launcher_stop "${_orchestrator_restore_child_pid}" 2

    atomic_restore_tree \
        "${_orchestrator_restore_active_dir}" \
        "${_orchestrator_restore_backup}" || return 1

    if [ "${_orchestrator_restore_old_complete}" = "1" ]; then
        firewall_restore_telegram_voice_table \
            "${_orchestrator_restore_active_dir}/${TELEGRAM_VOICE_STATE_FILE_NAME}" \
            "${_orchestrator_restore_active_dir}/managed/ipset-telegram.txt" || return 1
        launcher_start_once \
            "${_orchestrator_restore_dvtws_bin}" \
            "${_orchestrator_restore_active_dir}/dvtws.args" \
            "${_orchestrator_restore_child_pid}" \
            "${_orchestrator_restore_log}" 5 || return 1
        firewall_restore_rules \
            "${_orchestrator_restore_firewall_snapshot}" \
            "${_orchestrator_restore_rule_base}" \
            "${_orchestrator_restore_rule_max}" || return 1
        supervisor_start \
            "${_orchestrator_restore_supervisor_loop}" \
            "${_orchestrator_restore_supervisor_daemon}" \
            "${_orchestrator_restore_supervisor_monitor}" \
            "${_orchestrator_restore_child_pid}" \
            "${_orchestrator_restore_service_script}" \
            "${_orchestrator_restore_dvtws_bin}" \
            "${_orchestrator_restore_supervisor_log}" || return 1
    else
        firewall_remove_rules \
            "${_orchestrator_restore_rule_base}" \
            "${_orchestrator_restore_rule_max}"
        firewall_remove_telegram_voice_tables
    fi
}

orchestrator_reconfigure_failure()
{
    _orchestrator_failure_stage_file="$1"
    _orchestrator_failure_index="$2"
    _orchestrator_failure_total="$3"
    _orchestrator_failure_name="$4"
    _orchestrator_failure_message="$5"
    shift 5

    if orchestrator_restore_previous_runtime "$@"; then
        orchestrator_fail_stage \
            "${_orchestrator_failure_stage_file}" \
            "${_orchestrator_failure_index}" \
            "${_orchestrator_failure_total}" \
            "${_orchestrator_failure_name}" \
            "${_orchestrator_failure_message}; previous runtime restored"
    else
        orchestrator_fail_stage \
            "${_orchestrator_failure_stage_file}" \
            "${_orchestrator_failure_index}" \
            "${_orchestrator_failure_total}" \
            rollback \
            "${_orchestrator_failure_message}; rollback failed"
        common_error "${_orchestrator_failure_message}; rollback failed"
    fi
    return 1
}

orchestrator_native_reconfigure()
{
    _orchestrator_reconfigure_config="$1"
    _orchestrator_reconfigure_zapret_dir="$2"
    _orchestrator_reconfigure_active_dir="$3"
    _orchestrator_reconfigure_backup_root="$4"
    _orchestrator_reconfigure_dvtws_bin="$5"
    _orchestrator_reconfigure_child_pid="$6"
    _orchestrator_reconfigure_supervisor_daemon="$7"
    _orchestrator_reconfigure_supervisor_monitor="$8"
    _orchestrator_reconfigure_supervisor_loop="$9"
    shift 9
    _orchestrator_reconfigure_service_script="$1"
    _orchestrator_reconfigure_rule_base="$2"
    _orchestrator_reconfigure_rule_max="$3"
    _orchestrator_reconfigure_stage_file="$4"
    _orchestrator_reconfigure_log="$5"
    _orchestrator_reconfigure_supervisor_log="$6"
    _orchestrator_reconfigure_total=13

    _orchestrator_reconfigure_workspace=$(common_create_workspace \
        zapret-reconfigure) || return 1
    _orchestrator_reconfigure_release="${_orchestrator_reconfigure_workspace}/release"
    _orchestrator_reconfigure_firewall_snapshot="${_orchestrator_reconfigure_workspace}/ipfw.rules"

    # Build and validate the complete candidate while the old process,
    # supervisor, firewall rules, and active tree remain untouched.
    orchestrator_build_release \
        "${_orchestrator_reconfigure_config}" \
        "${_orchestrator_reconfigure_zapret_dir}" \
        "${_orchestrator_reconfigure_active_dir}" \
        "${_orchestrator_reconfigure_workspace}" \
        "${_orchestrator_reconfigure_release}" \
        "${_orchestrator_reconfigure_stage_file}"
    _orchestrator_reconfigure_build_status=$?

    if [ "${_orchestrator_reconfigure_build_status}" -eq 2 ]; then
        common_cleanup_dir "${_orchestrator_reconfigure_workspace}"
        orchestrator_native_stop \
            "${_orchestrator_reconfigure_child_pid}" \
            "${_orchestrator_reconfigure_supervisor_daemon}" \
            "${_orchestrator_reconfigure_supervisor_monitor}" \
            "${_orchestrator_reconfigure_rule_base}" \
            "${_orchestrator_reconfigure_rule_max}" \
            "${_orchestrator_reconfigure_stage_file}"
        return $?
    fi
    [ "${_orchestrator_reconfigure_build_status}" -eq 0 ] || {
        common_cleanup_dir "${_orchestrator_reconfigure_workspace}"
        return 1
    }

    common_set_directory_mode \
        "${_orchestrator_reconfigure_release}" 0755 || {
            common_cleanup_dir "${_orchestrator_reconfigure_workspace}"
            orchestrator_fail_stage \
                "${_orchestrator_reconfigure_stage_file}" 7 \
                "${_orchestrator_reconfigure_total}" validator \
                "cannot set candidate runtime directory mode"
            return 1
        }
    validator_validate_runtime_modes \
        "${_orchestrator_reconfigure_release}" || {
            common_cleanup_dir "${_orchestrator_reconfigure_workspace}"
            orchestrator_fail_stage \
                "${_orchestrator_reconfigure_stage_file}" 7 \
                "${_orchestrator_reconfigure_total}" validator \
                "candidate runtime permissions are invalid"
            return 1
        }

    # Perform every preflight that can be completed without touching the
    # currently active runtime.
    firewall_prepare || {
        common_cleanup_dir "${_orchestrator_reconfigure_workspace}"
        orchestrator_fail_stage \
            "${_orchestrator_reconfigure_stage_file}" 11 \
            "${_orchestrator_reconfigure_total}" firewall \
            "firewall preflight failed"
        return 1
    }
    _orchestrator_reconfigure_wan=$(config_resolve_interface "${WAN_IF}") || {
        common_cleanup_dir "${_orchestrator_reconfigure_workspace}"
        orchestrator_fail_stage \
            "${_orchestrator_reconfigure_stage_file}" 11 \
            "${_orchestrator_reconfigure_total}" firewall \
            "WAN interface resolution failed for '${WAN_IF}'"
        return 1
    }
    firewall_snapshot_rules \
        "${_orchestrator_reconfigure_rule_base}" \
        "${_orchestrator_reconfigure_rule_max}" \
        "${_orchestrator_reconfigure_firewall_snapshot}" || {
            common_cleanup_dir "${_orchestrator_reconfigure_workspace}"
            orchestrator_fail_stage \
                "${_orchestrator_reconfigure_stage_file}" 11 \
                "${_orchestrator_reconfigure_total}" firewall \
                "cannot snapshot current firewall rules"
            return 1
        }

    _orchestrator_reconfigure_old_complete=0
    if orchestrator_runtime_is_complete \
        "${_orchestrator_reconfigure_child_pid}" \
        "${_orchestrator_reconfigure_supervisor_monitor}" \
        "${_orchestrator_reconfigure_rule_base}" \
        "${_orchestrator_reconfigure_rule_max}" \
        "${_orchestrator_reconfigure_active_dir}"; then
        _orchestrator_reconfigure_old_complete=1
    fi

    orchestrator_stage \
        "${_orchestrator_reconfigure_stage_file}" 9 \
        "${_orchestrator_reconfigure_total}" atomic running \
        "activating validated candidate" || {
            common_cleanup_dir "${_orchestrator_reconfigure_workspace}"
            return 1
        }
    _orchestrator_reconfigure_backup=$(atomic_install_tree \
        "${_orchestrator_reconfigure_release}" \
        "${_orchestrator_reconfigure_active_dir}" \
        "${_orchestrator_reconfigure_backup_root}") || {
            common_cleanup_dir "${_orchestrator_reconfigure_workspace}"
            orchestrator_fail_stage \
                "${_orchestrator_reconfigure_stage_file}" 9 \
                "${_orchestrator_reconfigure_total}" atomic \
                "atomic activation failed; previous runtime kept"
            return 1
        }
    orchestrator_stage \
        "${_orchestrator_reconfigure_stage_file}" 9 \
        "${_orchestrator_reconfigure_total}" atomic ok \
        "validated candidate activated" || true

    # Stop only the supervisor and process. Existing divert rules remain in
    # place until the replacement process has passed its stability window.
    supervisor_stop \
        "${_orchestrator_reconfigure_supervisor_daemon}" \
        "${_orchestrator_reconfigure_supervisor_monitor}"
    launcher_stop "${_orchestrator_reconfigure_child_pid}" 5

    orchestrator_stage \
        "${_orchestrator_reconfigure_stage_file}" 10 \
        "${_orchestrator_reconfigure_total}" launcher running \
        "starting replacement dvtws2 instance" || true
    if ! launcher_start_once \
        "${_orchestrator_reconfigure_dvtws_bin}" \
        "${_orchestrator_reconfigure_active_dir}/dvtws.args" \
        "${_orchestrator_reconfigure_child_pid}" \
        "${_orchestrator_reconfigure_log}" 5; then
        orchestrator_reconfigure_failure \
            "${_orchestrator_reconfigure_stage_file}" 10 \
            "${_orchestrator_reconfigure_total}" launcher \
            "replacement dvtws2 failed the startup stability check" \
            "${_orchestrator_reconfigure_active_dir}" \
            "${_orchestrator_reconfigure_backup}" \
            "${_orchestrator_reconfigure_old_complete}" \
            "${_orchestrator_reconfigure_dvtws_bin}" \
            "${_orchestrator_reconfigure_child_pid}" \
            "${_orchestrator_reconfigure_supervisor_daemon}" \
            "${_orchestrator_reconfigure_supervisor_monitor}" \
            "${_orchestrator_reconfigure_supervisor_loop}" \
            "${_orchestrator_reconfigure_service_script}" \
            "${_orchestrator_reconfigure_firewall_snapshot}" \
            "${_orchestrator_reconfigure_rule_base}" \
            "${_orchestrator_reconfigure_rule_max}" \
            "${_orchestrator_reconfigure_log}" \
            "${_orchestrator_reconfigure_supervisor_log}"
        _orchestrator_reconfigure_status=$?
        common_cleanup_dir "${_orchestrator_reconfigure_workspace}"
        return "${_orchestrator_reconfigure_status}"
    fi
    orchestrator_stage \
        "${_orchestrator_reconfigure_stage_file}" 10 \
        "${_orchestrator_reconfigure_total}" launcher ok \
        "replacement dvtws2 passed the stability window" || true

    orchestrator_stage \
        "${_orchestrator_reconfigure_stage_file}" 11 \
        "${_orchestrator_reconfigure_total}" firewall running \
        "replacing divert rules" || true
    if ! firewall_install_runtime_rules \
        "${_orchestrator_reconfigure_active_dir}/tcp-ports.txt" \
        "${_orchestrator_reconfigure_active_dir}/udp-ports.txt" \
        "${_orchestrator_reconfigure_wan}" \
        "${DIVERT_PORT}" \
        "${_orchestrator_reconfigure_rule_base}" \
        "${_orchestrator_reconfigure_rule_max}" \
        "${_orchestrator_reconfigure_active_dir}/${TELEGRAM_VOICE_STATE_FILE_NAME}" \
        "${_orchestrator_reconfigure_active_dir}/managed/ipset-telegram.txt"; then
        orchestrator_reconfigure_failure \
            "${_orchestrator_reconfigure_stage_file}" 11 \
            "${_orchestrator_reconfigure_total}" firewall \
            "replacement divert rule installation failed" \
            "${_orchestrator_reconfigure_active_dir}" \
            "${_orchestrator_reconfigure_backup}" \
            "${_orchestrator_reconfigure_old_complete}" \
            "${_orchestrator_reconfigure_dvtws_bin}" \
            "${_orchestrator_reconfigure_child_pid}" \
            "${_orchestrator_reconfigure_supervisor_daemon}" \
            "${_orchestrator_reconfigure_supervisor_monitor}" \
            "${_orchestrator_reconfigure_supervisor_loop}" \
            "${_orchestrator_reconfigure_service_script}" \
            "${_orchestrator_reconfigure_firewall_snapshot}" \
            "${_orchestrator_reconfigure_rule_base}" \
            "${_orchestrator_reconfigure_rule_max}" \
            "${_orchestrator_reconfigure_log}" \
            "${_orchestrator_reconfigure_supervisor_log}"
        _orchestrator_reconfigure_status=$?
        common_cleanup_dir "${_orchestrator_reconfigure_workspace}"
        return "${_orchestrator_reconfigure_status}"
    fi
    orchestrator_stage \
        "${_orchestrator_reconfigure_stage_file}" 11 \
        "${_orchestrator_reconfigure_total}" firewall ok \
        "divert rules replaced" || true

    orchestrator_stage \
        "${_orchestrator_reconfigure_stage_file}" 12 \
        "${_orchestrator_reconfigure_total}" supervisor running \
        "starting replacement runtime supervisor" || true
    if ! supervisor_start \
        "${_orchestrator_reconfigure_supervisor_loop}" \
        "${_orchestrator_reconfigure_supervisor_daemon}" \
        "${_orchestrator_reconfigure_supervisor_monitor}" \
        "${_orchestrator_reconfigure_child_pid}" \
        "${_orchestrator_reconfigure_service_script}" \
        "${_orchestrator_reconfigure_dvtws_bin}" \
        "${_orchestrator_reconfigure_supervisor_log}"; then
        orchestrator_reconfigure_failure \
            "${_orchestrator_reconfigure_stage_file}" 12 \
            "${_orchestrator_reconfigure_total}" supervisor \
            "replacement runtime supervisor failed to start" \
            "${_orchestrator_reconfigure_active_dir}" \
            "${_orchestrator_reconfigure_backup}" \
            "${_orchestrator_reconfigure_old_complete}" \
            "${_orchestrator_reconfigure_dvtws_bin}" \
            "${_orchestrator_reconfigure_child_pid}" \
            "${_orchestrator_reconfigure_supervisor_daemon}" \
            "${_orchestrator_reconfigure_supervisor_monitor}" \
            "${_orchestrator_reconfigure_supervisor_loop}" \
            "${_orchestrator_reconfigure_service_script}" \
            "${_orchestrator_reconfigure_firewall_snapshot}" \
            "${_orchestrator_reconfigure_rule_base}" \
            "${_orchestrator_reconfigure_rule_max}" \
            "${_orchestrator_reconfigure_log}" \
            "${_orchestrator_reconfigure_supervisor_log}"
        _orchestrator_reconfigure_status=$?
        common_cleanup_dir "${_orchestrator_reconfigure_workspace}"
        return "${_orchestrator_reconfigure_status}"
    fi

    orchestrator_stage \
        "${_orchestrator_reconfigure_stage_file}" 12 \
        "${_orchestrator_reconfigure_total}" supervisor ok \
        "replacement runtime supervisor active" || true
    orchestrator_stage \
        "${_orchestrator_reconfigure_stage_file}" 13 \
        "${_orchestrator_reconfigure_total}" ready ok \
        "zapret reconfigured successfully" || true

    common_cleanup_dir "${_orchestrator_reconfigure_workspace}"
    launcher_status "${_orchestrator_reconfigure_child_pid}"
}

orchestrator_native_stop()
{
    _orchestrator_stop_child="$1"
    _orchestrator_stop_supervisor_daemon="$2"
    _orchestrator_stop_supervisor_monitor="$3"
    _orchestrator_stop_rule_base="$4"
    _orchestrator_stop_rule_max="$5"
    _orchestrator_stop_stage="$6"

    orchestrator_stage "${_orchestrator_stop_stage}" 1 3 supervisor running \
        "stopping runtime supervisor" || return 1
    supervisor_stop \
        "${_orchestrator_stop_supervisor_daemon}" \
        "${_orchestrator_stop_supervisor_monitor}"

    orchestrator_stage "${_orchestrator_stop_stage}" 2 3 firewall running \
        "removing divert rules" || return 1
    firewall_remove_rules \
        "${_orchestrator_stop_rule_base}" \
        "${_orchestrator_stop_rule_max}"
    firewall_remove_telegram_voice_tables

    orchestrator_stage "${_orchestrator_stop_stage}" 3 3 launcher running \
        "stopping dvtws2" || return 1
    launcher_stop "${_orchestrator_stop_child}" 5

    orchestrator_stage "${_orchestrator_stop_stage}" 3 3 launcher stopped \
        "zapret stopped" || return 1
    echo "zapret is not running (stopped)"
}

orchestrator_native_status()
{
    _orchestrator_status_child="$1"
    _orchestrator_status_monitor="$2"
    _orchestrator_status_rule_base="$3"
    _orchestrator_status_rule_max="$4"
    _orchestrator_status_active_dir="$5"

    if orchestrator_runtime_is_complete \
        "${_orchestrator_status_child}" \
        "${_orchestrator_status_monitor}" \
        "${_orchestrator_status_rule_base}" \
        "${_orchestrator_status_rule_max}" \
        "${_orchestrator_status_active_dir}"; then
        launcher_status "${_orchestrator_status_child}"
        return 0
    fi

    if launcher_is_running "${_orchestrator_status_child}" ||
       supervisor_is_running "${_orchestrator_status_monitor}" ||
       firewall_rules_present \
            "${_orchestrator_status_rule_base}" \
            "${_orchestrator_status_rule_max}"; then
        echo "zapret is in an incomplete runtime state"
        return 2
    fi

    echo "zapret is not running"
    return 1
}

orchestrator_runtime_failure()
{
    _orchestrator_failure_child="$1"
    _orchestrator_failure_supervisor_daemon="$2"
    _orchestrator_failure_supervisor_monitor="$3"
    _orchestrator_failure_rule_base="$4"
    _orchestrator_failure_rule_max="$5"
    _orchestrator_failure_stage="$6"
    _orchestrator_failure_message="$7"

    firewall_remove_rules \
        "${_orchestrator_failure_rule_base}" \
        "${_orchestrator_failure_rule_max}"
    firewall_remove_telegram_voice_tables
    launcher_stop "${_orchestrator_failure_child}" 1
    rm -f \
        "${_orchestrator_failure_supervisor_daemon}" \
        "${_orchestrator_failure_supervisor_monitor}"
    orchestrator_fail_stage \
        "${_orchestrator_failure_stage}" 13 13 supervisor \
        "${_orchestrator_failure_message}"
}
