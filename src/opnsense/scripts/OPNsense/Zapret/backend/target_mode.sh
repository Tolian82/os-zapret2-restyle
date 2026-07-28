#!/bin/sh

# Target Mode Resolver
#
# Public API:
#   target_mode_policy MODE
#   target_mode_apply_profile PROFILE_NO WORKDIR MODE REGISTRY_FILE
#   target_mode_apply_all WORKDIR PROFILE_COUNT MODE REGISTRY_FILE
#
# Target Mode is a default policy only. A profile containing any explicit
# <TYPE:NAME> placeholder is preserved unchanged.

target_mode_validate_mode()
{
    case "$1" in
        all|list|auto)
            return 0
            ;;
        *)
            common_error "unsupported Target Mode '$1'"
            return 1
            ;;
    esac
}

target_mode_policy()
{
    target_mode=$1

    case "${target_mode}" in
        all)
            return 0
            ;;
        list)
            printf 'HOSTLIST\tyoutube\n'
            printf 'IPSET\ttelegram\n'
            printf 'HOSTLIST\tuser\n'
            ;;
        auto)
            printf 'HOSTLIST\tyoutube\n'
            printf 'IPSET\ttelegram\n'
            printf 'HOSTLIST\tuser\n'
            printf 'HOSTLIST\tauto\n'
            ;;
        *)
            common_error "unsupported Target Mode '${target_mode}'"
            return 1
            ;;
    esac
}

target_mode_profile_has_explicit_targets()
{
    target_mode_profile=$1

    [ -f "${target_mode_profile}" ] || {
        common_error "Target Mode profile does not exist: ${target_mode_profile}"
        return 2
    }

    awk '
        /<[A-Z][A-Z0-9_]*:[a-z][a-z0-9_-]*>/ { found = 1; exit }
        END { exit found ? 0 : 1 }
    ' "${target_mode_profile}"
}

target_mode_validate_policy()
{
    target_mode_policy_file=$1
    target_mode_registry=$2

    [ -f "${target_mode_policy_file}" ] || {
        common_error "Target Mode policy file does not exist: ${target_mode_policy_file}"
        return 1
    }

    while IFS="$(printf '\t')" read -r target_mode_type target_mode_name || \
        [ -n "${target_mode_type}${target_mode_name}" ]; do
        [ -n "${target_mode_type}" ] || continue

        registry_exists \
            "${target_mode_registry}" "${target_mode_type}" "${target_mode_name}" || {
            common_error "Target Mode policy references an unregistered target <${target_mode_type}:${target_mode_name}>"
            return 1
        }
    done < "${target_mode_policy_file}"
}

target_mode_apply_profile()
{
    target_mode_profile_no=$1
    target_mode_workdir=$2
    target_mode_value=$3
    target_mode_registry=$4
    target_mode_profile="${target_mode_workdir}/profile-${target_mode_profile_no}.conf"
    target_mode_policy_file="${target_mode_workdir}/profile-${target_mode_profile_no}.target-mode.tsv"
    target_mode_tmp="${target_mode_profile}.target-mode.tmp.$$"

    [ -f "${target_mode_profile}" ] || {
        common_error "Target Mode profile ${target_mode_profile_no} does not exist: ${target_mode_profile}"
        return 1
    }

    [ -f "${target_mode_registry}" ] || {
        common_error "Target Mode registry does not exist: ${target_mode_registry}"
        return 1
    }

    # Validate the configured mode even when the profile has explicit targets.
    # Explicit targets suppress policy injection, but they must not hide an
    # invalid global configuration value.
    target_mode_validate_mode "${target_mode_value}" || return 1

    # Explicit selectors are authoritative. Target Mode must never add to or
    # reinterpret a profile where the user already selected any target.
    if target_mode_profile_has_explicit_targets "${target_mode_profile}"; then
        return 0
    else
        target_mode_status=$?
        [ "${target_mode_status}" -eq 1 ] || return "${target_mode_status}"
    fi

    target_mode_policy "${target_mode_value}" > "${target_mode_policy_file}" || {
        rm -f "${target_mode_policy_file}"
        return 1
    }

    # All traffic intentionally produces an empty policy and leaves the
    # profile byte-for-byte unchanged.
    if [ ! -s "${target_mode_policy_file}" ]; then
        rm -f "${target_mode_policy_file}"
        return 0
    fi

    target_mode_validate_policy "${target_mode_policy_file}" "${target_mode_registry}" || {
        rm -f "${target_mode_policy_file}"
        return 1
    }

    cat "${target_mode_profile}" > "${target_mode_tmp}" || {
        rm -f "${target_mode_tmp}" "${target_mode_policy_file}"
        return 1
    }

    # Keep the user's strategy intact and append only the generated default
    # selectors. The later Target Resolver handles them exactly like explicit
    # placeholders.
    while IFS="$(printf '\t')" read -r target_mode_type target_mode_name || \
        [ -n "${target_mode_type}${target_mode_name}" ]; do
        [ -n "${target_mode_type}" ] || continue
        printf '<%s:%s>\n' "${target_mode_type}" "${target_mode_name}" >> "${target_mode_tmp}" || {
            rm -f "${target_mode_tmp}" "${target_mode_policy_file}"
            return 1
        }
    done < "${target_mode_policy_file}"

    mv -f "${target_mode_tmp}" "${target_mode_profile}" || {
        rm -f "${target_mode_tmp}" "${target_mode_policy_file}"
        common_error "could not apply Target Mode to profile ${target_mode_profile_no}"
        return 1
    }

    rm -f "${target_mode_policy_file}"
}

target_mode_apply_all()
{
    target_mode_workdir=$1
    target_mode_profile_count=$2
    target_mode_value=$3
    target_mode_registry=$4
    target_mode_profile_no=1

    case "${target_mode_profile_count}" in
        ''|*[!0-9]*|0)
            common_error "target_mode_apply_all requires a positive profile count"
            return 1
            ;;
    esac

    while [ "${target_mode_profile_no}" -le "${target_mode_profile_count}" ]; do
        target_mode_apply_profile \
            "${target_mode_profile_no}" "${target_mode_workdir}" \
            "${target_mode_value}" "${target_mode_registry}" || return 1
        target_mode_profile_no=$((target_mode_profile_no + 1))
    done
}
