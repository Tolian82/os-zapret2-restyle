#!/bin/sh

# Exclude Resolver
#
# Public API:
#   exclude_prepare BUILD_ROOT EXCLUDE_TEXT
#
# Exclude Domains are a global HOSTLIST exclusion. They are normalized with
# the same rules as managed HOSTLIST targets, but they are never registered as
# a placeholder and never applied to IPSET resources.
#
# On success, exclude_prepare prints the generated file path. An empty input
# is valid and produces an empty file; generator.sh then omits
# --hostlist-exclude automatically.

exclude_prepare()
{
    local build_root="$1"
    local exclude_text="$2"
    local input_dir
    local input_file
    local output_file

    [ -n "${build_root}" ] || {
        common_error "exclude_prepare requires a build root"
        return 1
    }

    input_dir="${build_root}/.exclude-input"
    input_file="${input_dir}/exclude-domains.txt"
    output_file="${build_root}/hostlist-exclude.txt"

    mkdir -p "${input_dir}" || {
        common_error "could not create Exclude Domains build directory: ${input_dir}"
        return 1
    }

    printf '%s\n' "${exclude_text}" > "${input_file}" || {
        rm -rf "${input_dir}"
        return 1
    }

    targets_normalize_hostlist \
        "${input_file}" "${output_file}" "Exclude Domains" || {
        rm -rf "${input_dir}"
        return 1
    }

    chmod 0755 "${build_root}" || {
        rm -rf "${input_dir}"
        common_error "could not set Exclude build directory permissions"
        return 1
    }

    chmod 0644 "${output_file}" || {
        rm -rf "${input_dir}"
        common_error "could not set Exclude file permissions"
        return 1
    }

    common_set_directory_mode "${build_root}" 0755 || {
        rm -rf "${input_dir}"
        return 1
    }
    common_set_file_mode "${output_file}" 0644 || {
        rm -rf "${input_dir}"
        return 1
    }

    rm -rf "${input_dir}"
    printf '%s\n' "${output_file}"
}
