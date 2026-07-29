#!/bin/sh

# Runtime Profile Normalizer
#
# Public API:
#   profile_normalizer_normalize_all WORKDIR PROFILE_COUNT
#
# The parser preserves user-authored --new boundaries. After Target Mode has
# added any implicit selectors, this module expands every profile containing
# multiple unique HOSTLIST/IPSET placeholders into one runtime profile per
# selector. All non-selector strategy text is copied to every generated
# profile. The module does not resolve targets or know target names.

profile_normalizer_validate_count()
{
    profile_normalizer_count=$1

    case "${profile_normalizer_count}" in
        ''|*[!0-9]*|0)
            common_error "profile_normalizer_normalize_all requires a positive profile count"
            return 1
            ;;
    esac
}

profile_normalizer_index_supported()
{
    profile_normalizer_profile=$1
    profile_normalizer_index=$2

    [ -f "${profile_normalizer_profile}" ] || {
        common_error "normalizer profile does not exist: ${profile_normalizer_profile}"
        return 1
    }

    # Metadata format:
    #   TYPE<TAB>NAME
    # Only the permanently supported selector families participate in profile
    # expansion. Duplicates are removed in first-use order.
    awk '
    {
        line = $0
        while (match(line, /<(HOSTLIST|IPSET):[A-Za-z0-9][A-Za-z0-9_.-]*>/)) {
            token = substr(line, RSTART + 1, RLENGTH - 2)
            separator = index(token, ":")
            type = substr(token, 1, separator - 1)
            name = substr(token, separator + 1)
            key = type SUBSEP name
            if (!seen[key]++)
                printf "%s\t%s\n", type, name
            line = substr(line, RSTART + RLENGTH)
        }
    }
    ' "${profile_normalizer_profile}" > "${profile_normalizer_index}" || {
        common_error "unable to index supported selectors: ${profile_normalizer_index}"
        return 1
    }
}

profile_normalizer_clone()
{
    profile_normalizer_source=$1
    profile_normalizer_output=$2
    profile_normalizer_selected_type=$3
    profile_normalizer_selected_name=$4

    # Preserve the selected selector exactly and remove every other supported
    # selector. Text outside supported selector tokens is emitted unchanged.
    awk \
        -v selected_type="${profile_normalizer_selected_type}" \
        -v selected_name="${profile_normalizer_selected_name}" '
    {
        remaining = $0
        output = ""
        while (match(remaining, /<(HOSTLIST|IPSET):[A-Za-z0-9][A-Za-z0-9_.-]*>/)) {
            output = output substr(remaining, 1, RSTART - 1)
            token = substr(remaining, RSTART + 1, RLENGTH - 2)
            separator = index(token, ":")
            type = substr(token, 1, separator - 1)
            name = substr(token, separator + 1)
            if (type == selected_type && name == selected_name)
                output = output substr(remaining, RSTART, RLENGTH)
            remaining = substr(remaining, RSTART + RLENGTH)
        }
        print output remaining
    }
    ' "${profile_normalizer_source}" > "${profile_normalizer_output}" || {
        rm -f "${profile_normalizer_output}"
        common_error "unable to generate normalized profile: ${profile_normalizer_output}"
        return 1
    }
}

profile_normalizer_restore()
{
    profile_normalizer_restore_workdir=$1
    profile_normalizer_restore_backup=$2

    rm -f "${profile_normalizer_restore_workdir}"/profile-*.conf \
        "${profile_normalizer_restore_workdir}/profile-count"

    for profile_normalizer_restore_file in \
        "${profile_normalizer_restore_backup}"/profile-*.conf
    do
        [ -f "${profile_normalizer_restore_file}" ] || continue
        mv -f "${profile_normalizer_restore_file}" \
            "${profile_normalizer_restore_workdir}/" || return 1
    done

    if [ -f "${profile_normalizer_restore_backup}/profile-count" ]; then
        mv -f "${profile_normalizer_restore_backup}/profile-count" \
            "${profile_normalizer_restore_workdir}/profile-count" || return 1
    fi
}

profile_normalizer_normalize_all()
{
    profile_normalizer_workdir=$1
    profile_normalizer_input_count=$2
    profile_normalizer_stage="${profile_normalizer_workdir}/.profiles-normalized.$$"
    profile_normalizer_backup="${profile_normalizer_workdir}/.profiles-before-normalize.$$"
    profile_normalizer_source_no=1
    profile_normalizer_output_no=0

    profile_normalizer_validate_count \
        "${profile_normalizer_input_count}" || return 1

    [ -d "${profile_normalizer_workdir}" ] || {
        common_error "normalizer work directory does not exist: ${profile_normalizer_workdir}"
        return 1
    }

    rm -rf "${profile_normalizer_stage}" "${profile_normalizer_backup}"
    mkdir -p "${profile_normalizer_stage}" || {
        common_error "unable to create normalizer staging directory"
        return 1
    }

    while [ "${profile_normalizer_source_no}" -le \
        "${profile_normalizer_input_count}" ]
    do
        profile_normalizer_source="${profile_normalizer_workdir}/profile-${profile_normalizer_source_no}.conf"
        profile_normalizer_index="${profile_normalizer_stage}/source-${profile_normalizer_source_no}.targets"

        parser_validate_placeholder_syntax \
            "${profile_normalizer_source_no}" \
            "${profile_normalizer_source}" || {
                rm -rf "${profile_normalizer_stage}"
                return 1
            }

        profile_normalizer_index_supported \
            "${profile_normalizer_source}" \
            "${profile_normalizer_index}" || {
                rm -rf "${profile_normalizer_stage}"
                return 1
            }

        profile_normalizer_target_count=$(awk 'END { print NR + 0 }' \
            "${profile_normalizer_index}") || {
                rm -rf "${profile_normalizer_stage}"
                return 1
            }

        if [ "${profile_normalizer_target_count}" -le 1 ]; then
            profile_normalizer_output_no=$((profile_normalizer_output_no + 1))
            cp "${profile_normalizer_source}" \
                "${profile_normalizer_stage}/profile-${profile_normalizer_output_no}.conf" || {
                    rm -rf "${profile_normalizer_stage}"
                    return 1
                }
        else
            while IFS="$(printf '\t')" read -r \
                profile_normalizer_type profile_normalizer_name || \
                [ -n "${profile_normalizer_type}${profile_normalizer_name}" ]
            do
                [ -n "${profile_normalizer_type}" ] || continue
                profile_normalizer_output_no=$((profile_normalizer_output_no + 1))
                profile_normalizer_clone \
                    "${profile_normalizer_source}" \
                    "${profile_normalizer_stage}/profile-${profile_normalizer_output_no}.conf" \
                    "${profile_normalizer_type}" \
                    "${profile_normalizer_name}" || {
                        rm -rf "${profile_normalizer_stage}"
                        return 1
                    }
            done < "${profile_normalizer_index}"
        fi

        profile_normalizer_source_no=$((profile_normalizer_source_no + 1))
    done

    [ "${profile_normalizer_output_no}" -gt 0 ] || {
        rm -rf "${profile_normalizer_stage}"
        common_error "normalizer produced no runtime profiles"
        return 1
    }

    printf '%s\n' "${profile_normalizer_output_no}" \
        > "${profile_normalizer_stage}/profile-count" || {
            rm -rf "${profile_normalizer_stage}"
            return 1
        }

    mkdir -p "${profile_normalizer_backup}" || {
        rm -rf "${profile_normalizer_stage}"
        return 1
    }

    for profile_normalizer_file in \
        "${profile_normalizer_workdir}"/profile-*.conf
    do
        [ -f "${profile_normalizer_file}" ] || continue
        mv -f "${profile_normalizer_file}" \
            "${profile_normalizer_backup}/" || {
                profile_normalizer_restore \
                    "${profile_normalizer_workdir}" \
                    "${profile_normalizer_backup}" || true
                rm -rf "${profile_normalizer_stage}" \
                    "${profile_normalizer_backup}"
                return 1
            }
    done

    if [ -f "${profile_normalizer_workdir}/profile-count" ]; then
        mv -f "${profile_normalizer_workdir}/profile-count" \
            "${profile_normalizer_backup}/profile-count" || {
                profile_normalizer_restore \
                    "${profile_normalizer_workdir}" \
                    "${profile_normalizer_backup}" || true
                rm -rf "${profile_normalizer_stage}" \
                    "${profile_normalizer_backup}"
                return 1
            }
    fi

    for profile_normalizer_file in \
        "${profile_normalizer_stage}"/profile-*.conf
    do
        [ -f "${profile_normalizer_file}" ] || continue
        mv -f "${profile_normalizer_file}" \
            "${profile_normalizer_workdir}/" || {
                profile_normalizer_restore \
                    "${profile_normalizer_workdir}" \
                    "${profile_normalizer_backup}" || true
                rm -rf "${profile_normalizer_stage}" \
                    "${profile_normalizer_backup}"
                return 1
            }
    done

    mv -f "${profile_normalizer_stage}/profile-count" \
        "${profile_normalizer_workdir}/profile-count" || {
            profile_normalizer_restore \
                "${profile_normalizer_workdir}" \
                "${profile_normalizer_backup}" || true
            rm -rf "${profile_normalizer_stage}" \
                "${profile_normalizer_backup}"
            return 1
        }

    rm -rf "${profile_normalizer_stage}" "${profile_normalizer_backup}"
    printf '%s\n' "${profile_normalizer_output_no}"
}
