#!/bin/sh
# Compatibility shell API for the single Python strategy-profile policy.
# Public API: parser_parse STRATEGY WORKDIR;
# parser_validate_placeholder_syntax NUMBER PROFILE;
# parser_index_placeholders PROFILE META_FILE.
# Does not interpret Zapret2 arguments or own runtime/state.

parser_policy_python()
{
    _parser_policy_backend="${BACKEND_DIR:-${BACKEND:-${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}/backend}}"
    _parser_policy_launcher="${PYTHON_RUNTIME:-${_parser_policy_backend%/backend}/python_runtime.sh}"
    [ -x "${_parser_policy_launcher}" ] && [ -f "${_parser_policy_backend}/profile_policy.py" ] || {
        common_error "qualified Python profile policy is unavailable"
        return 1
    }
}

parser_parse()
{
    _parser_input="$1"
    _parser_dir="$2"
    mkdir -p "${_parser_dir}" || {
        common_error "unable to create strategy work directory: ${_parser_dir}"
        return 1
    }
    printf '%s\n' "${_parser_input}" > "${_parser_dir}/traffic.input" || return 1
    parser_policy_python || return 1
    "${_parser_policy_launcher}" "${_parser_policy_backend}/profile_policy.py" parse "${_parser_dir}"
}

parser_validate_placeholder_syntax()
{
    _parser_no="$1"
    _parser_file="$2"
    parser_policy_python || return 1
    "${_parser_policy_launcher}" "${_parser_policy_backend}/profile_policy.py" validate "${_parser_no}" "${_parser_file}"
}

parser_index_placeholders()
{
    _parser_file="$1"
    _parser_meta="$2"
    parser_policy_python || return 1
    "${_parser_policy_launcher}" "${_parser_policy_backend}/profile_policy.py" index "${_parser_file}" "${_parser_meta}"
}
