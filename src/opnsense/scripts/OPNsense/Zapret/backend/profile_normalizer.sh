#!/bin/sh
# Public API: profile_normalizer_normalize_all WORKDIR PROFILE_COUNT.
# The one Python profile policy owns selector expansion; this adapter preserves
# the profile pipeline's count and staged-file contract, not engine semantics.

profile_normalizer_normalize_all()
{
    _profile_normalizer_dir="$1"
    _profile_normalizer_count="$2"
    _profile_normalizer_backend="${BACKEND_DIR:-${BACKEND:-${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}/backend}}"
    case "${_profile_normalizer_count}" in
        ''|*[!0-9]*)
            common_error "profile normalizer requires a nonnegative profile count"
            return 1 ;;
    esac
    _profile_normalizer_binary="${PYTHON_RUNTIME:-${_profile_normalizer_backend%/backend}/python_runtime.sh}"
    [ -x "${_profile_normalizer_binary}" ] && [ -f "${_profile_normalizer_backend}/profile_policy.py" ] || {
        common_error "qualified Python profile policy is unavailable"
        return 1
    }
    "${_profile_normalizer_binary}" "${_profile_normalizer_backend}/profile_policy.py" normalize \
        "${_profile_normalizer_dir}" "${_profile_normalizer_count}"
}
