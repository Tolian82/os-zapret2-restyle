#!/bin/sh

# Count-carrying profile transformation pipeline.
#
# Every public step uses the same contract:
#   profile_pipeline_<step> WORKDIR PROFILE_COUNT [STEP ARGUMENTS...]
#
# A successful step prints the resulting positive PROFILE_COUNT to stdout.
# Steps that do not change the number of profiles return the input count.

profile_pipeline_validate_count()
{
    _profile_pipeline_count="$1"
    _profile_pipeline_label="${2:-profile pipeline}"

    case "${_profile_pipeline_count}" in
        ''|*[!0-9]*|0)
            common_error "${_profile_pipeline_label} returned an invalid profile count"
            return 1
            ;;
    esac
}

profile_pipeline_parse()
{
    _profile_pipeline_workdir="$1"
    _profile_pipeline_count="$2"
    _profile_pipeline_strategy="$3"

    [ "${_profile_pipeline_count}" = "0" ] || {
        common_error "profile parser requires an initial profile count of 0"
        return 1
    }

    _profile_pipeline_result=$(parser_parse \
        "${_profile_pipeline_strategy}" \
        "${_profile_pipeline_workdir}") || return 1
    profile_pipeline_validate_count "${_profile_pipeline_result}" parser || return 1
    printf '%s\n' "${_profile_pipeline_result}"
}

profile_pipeline_registry()
{
    _profile_pipeline_workdir="$1"
    _profile_pipeline_count="$2"
    _profile_pipeline_registry="$3"

    profile_pipeline_validate_count "${_profile_pipeline_count}" registry || return 1
    registry_build "${_profile_pipeline_registry}" || return 1
    printf '%s\n' "${_profile_pipeline_count}"
}

profile_pipeline_target_mode()
{
    _profile_pipeline_workdir="$1"
    _profile_pipeline_count="$2"
    _profile_pipeline_mode="$3"
    _profile_pipeline_registry="$4"

    profile_pipeline_validate_count "${_profile_pipeline_count}" "Target Mode" || return 1
    target_mode_apply_all \
        "${_profile_pipeline_workdir}" \
        "${_profile_pipeline_count}" \
        "${_profile_pipeline_mode}" \
        "${_profile_pipeline_registry}" || return 1
    printf '%s\n' "${_profile_pipeline_count}"
}

profile_pipeline_normalize()
{
    _profile_pipeline_workdir="$1"
    _profile_pipeline_count="$2"

    profile_pipeline_validate_count "${_profile_pipeline_count}" normalizer || return 1
    _profile_pipeline_result=$(profile_normalizer_normalize_all \
        "${_profile_pipeline_workdir}" \
        "${_profile_pipeline_count}") || return 1
    profile_pipeline_validate_count "${_profile_pipeline_result}" normalizer || return 1
    printf '%s\n' "${_profile_pipeline_result}"
}

profile_pipeline_index()
{
    _profile_pipeline_workdir="$1"
    _profile_pipeline_count="$2"

    profile_pipeline_validate_count "${_profile_pipeline_count}" "placeholder index" || return 1
    targets_index_all \
        "${_profile_pipeline_workdir}" \
        "${_profile_pipeline_count}" || return 1
    printf '%s\n' "${_profile_pipeline_count}"
}
