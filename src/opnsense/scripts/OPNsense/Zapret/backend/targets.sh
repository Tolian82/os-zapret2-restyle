#!/bin/sh

# Target Processing
#
# Public API:
#   targets_normalize_hostlist INPUT_FILE OUTPUT_FILE LABEL
#   targets_normalize_ipset INPUT_FILE OUTPUT_FILE LABEL
#   targets_prepare_managed BUILD_ROOT YOUTUBE_TEXT TELEGRAM_TEXT USER_TEXT
#   targets_index_all WORKDIR PROFILE_COUNT
#   targets_resolve_profile PROFILE_NO WORKDIR REGISTRY CATALOG MANAGED_ROOT RUNTIME_ROOT
#   targets_resolve_all WORKDIR PROFILE_COUNT REGISTRY CATALOG MANAGED_ROOT RUNTIME_ROOT OUTPUT
#
# This module normalizes user-managed target data and resolves generic
# placeholders. It does not know GUI field names or permanent installation
# paths. Managed files are generated under a caller-provided build root.

targets_normalize_hostlist()
{
    local input_file="$1"
    local output_file="$2"
    local label="$3"

    [ -f "${input_file}" ] || {
        common_error "${label} input does not exist: ${input_file}"
        return 1
    }

    awk -v label="${label}" '
    function fail(message) {
        print "ERROR: " label ", line " NR ": " message > "/dev/stderr"
        invalid = 1
    }
    function trim(value) {
        sub(/^[[:space:]]+/, "", value)
        sub(/[[:space:]]+$/, "", value)
        return value
    }
    function valid_domain(domain, count, labels, i, part) {
        if (length(domain) < 1 || length(domain) > 253)
            return 0
        if (domain ~ /\.\./)
            return 0
        count = split(domain, labels, ".")
        for (i = 1; i <= count; i++) {
            part = labels[i]
            if (length(part) < 1 || length(part) > 63)
                return 0
            if (part !~ /^[a-z0-9]([a-z0-9-]*[a-z0-9])?$/)
                return 0
        }
        return 1
    }
    {
        value = $0
        sub(/\r$/, "", value)
        value = trim(value)
        if (value == "")
            next

        lower = tolower(value)
        if (lower ~ /^https?:\/\//)
            sub(/^[Hh][Tt][Tt][Pp][Ss]?:\/\//, "", value)

        # A pasted URL is reduced to its host. Query strings and fragments are
        # never meaningful in a HOSTLIST entry.
        sub(/[\/?#].*$/, "", value)
        value = trim(value)

        # Wildcard hostlists use the base domain because zapret host matching
        # covers that domain and its subdomains.
        sub(/^\*\./, "", value)

        # Remove punctuation commonly introduced by copied prose or CSV data.
        gsub(/^[,;:]+/, "", value)
        gsub(/[,;:]+$/, "", value)
        gsub(/^\.+/, "", value)
        gsub(/\.+$/, "", value)
        value = tolower(trim(value))

        if (value ~ /^[0-9.]+$/ || value ~ /\//) {
            fail("IP addresses and networks are not allowed in a domain list: \047" $0 "\047")
            next
        }
        if (!valid_domain(value)) {
            fail("invalid domain entry \047" $0 "\047 after normalization to \047" value "\047")
            next
        }

        if (!seen[value]++)
            print value
    }
    END { exit invalid ? 1 : 0 }
    ' "${input_file}" > "${output_file}.tmp" || {
        rm -f "${output_file}.tmp"
        return 1
    }

    mv -f "${output_file}.tmp" "${output_file}" || {
        rm -f "${output_file}.tmp"
        common_error "could not install normalized ${label}: ${output_file}"
        return 1
    }
}

targets_normalize_ipset()
{
    local input_file="$1"
    local output_file="$2"
    local label="$3"
    local python_bin

    [ -f "${input_file}" ] || {
        common_error "${label} input does not exist: ${input_file}"
        return 1
    }

    python_bin=$(command -v python3 2>/dev/null) || {
        common_error "python3 is required for strict IPv4/CIDR validation"
        return 1
    }

    "${python_bin}" - "${input_file}" "${output_file}.tmp" "${label}" <<'PY'
import ipaddress
import pathlib
import sys

source = pathlib.Path(sys.argv[1])
destination = pathlib.Path(sys.argv[2])
label = sys.argv[3]
seen: set[str] = set()
normalized: list[str] = []
errors: list[str] = []

for line_no, raw in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
    value = raw.strip().strip(",;:")
    if not value:
        continue
    try:
        if "/" in value:
            parsed = ipaddress.IPv4Network(value, strict=True)
        else:
            parsed = ipaddress.IPv4Address(value)
    except ValueError as exc:
        errors.append(f"ERROR: {label}, line {line_no}: invalid IPv4 address or CIDR '{raw}': {exc}")
        continue

    canonical = str(parsed)
    if canonical not in seen:
        seen.add(canonical)
        normalized.append(canonical)

if errors:
    print("\n".join(errors), file=sys.stderr)
    raise SystemExit(1)

destination.write_text("".join(f"{item}\n" for item in normalized), encoding="utf-8")
PY
    status=$?

    if [ "${status}" -ne 0 ]; then
        rm -f "${output_file}.tmp"
        return "${status}"
    fi

    mv -f "${output_file}.tmp" "${output_file}" || {
        rm -f "${output_file}.tmp"
        common_error "could not install normalized ${label}: ${output_file}"
        return 1
    }
}

targets_prepare_managed()
{
    local build_root="$1"
    local youtube_text="$2"
    local telegram_text="$3"
    local user_text="$4"
    local input_root

    [ -n "${build_root}" ] || {
        common_error "targets_prepare_managed requires a build root"
        return 1
    }

    input_root="${build_root}/.input"
    mkdir -p "${input_root}" || {
        common_error "could not create target build directory: ${build_root}"
        return 1
    }

    printf '%s\n' "${youtube_text}" > "${input_root}/youtube.txt" || return 1
    printf '%s\n' "${telegram_text}" > "${input_root}/telegram.txt" || return 1
    printf '%s\n' "${user_text}" > "${input_root}/user.txt" || return 1

    targets_normalize_hostlist \
        "${input_root}/youtube.txt" "${build_root}/hostlist-youtube.txt" "YouTube Domains" || return 1
    targets_normalize_ipset \
        "${input_root}/telegram.txt" "${build_root}/ipset-telegram.txt" "Telegram IPs" || return 1
    targets_normalize_hostlist \
        "${input_root}/user.txt" "${build_root}/hostlist-user.txt" "User Domains" || return 1

    chmod 0755 "${build_root}" || {
        common_error "could not set managed Target directory permissions"
        return 1
    }

    chmod 0644 \
        "${build_root}/hostlist-youtube.txt" \
        "${build_root}/ipset-telegram.txt" \
        "${build_root}/hostlist-user.txt" || {
            common_error "could not set managed Target file permissions"
            return 1
        }

    rm -rf "${input_root}"
}

targets_index_all()
{
    local workdir="$1"
    local profile_count="$2"
    local profile_no=1
    local profile_file
    local metadata_file

    while [ "${profile_no}" -le "${profile_count}" ]; do
        profile_file="${workdir}/profile-${profile_no}.conf"
        metadata_file="${workdir}/profile-${profile_no}.placeholders"
        parser_validate_placeholder_syntax "${profile_no}" "${profile_file}" || return 1
        parser_index_placeholders "${profile_file}" "${metadata_file}" || return 1
        profile_no=$((profile_no + 1))
    done
}

targets_resolve_profile()
{
    local profile_no="$1"
    local workdir="$2"
    local registry_file="$3"
    local storage_catalog="$4"
    local managed_root="$5"
    local runtime_root="$6"
    local profile_file="${workdir}/profile-${profile_no}.conf"
    local metadata_file="${workdir}/profile-${profile_no}.placeholders"
    local resolved_file="${workdir}/profile-${profile_no}.resolved.conf"
    local target_type
    local target_name
    local registry_row
    local native_option
    local storage_key
    local required_content
    local resource_path
    local token
    local replacement

    cp "${profile_file}" "${resolved_file}" || return 1

    while IFS="$(printf '\t')" read -r target_type target_name || \
        [ -n "${target_type}${target_name}" ]; do
        [ -n "${target_type}" ] || continue

        registry_row=$(registry_lookup \
            "${registry_file}" "${target_type}" "${target_name}") || {
            common_error "unknown target placeholder <${target_type}:${target_name}> in profile ${profile_no}"
            echo "       register this TYPE/NAME pair before using it" >&2
            return 1
        }

        native_option=$(printf '%s\n' "${registry_row}" | awk -F '\t' '{print $1}')
        storage_key=$(printf '%s\n' "${registry_row}" | awk -F '\t' '{print $2}')
        required_content=$(printf '%s\n' "${registry_row}" | awk -F '\t' '{print $3}')

        resource_path=$(storage_resolve_roots \
            "${storage_key}" "${managed_root}" "${runtime_root}" "${storage_catalog}") || return 1

        storage_validate_resource \
            "${target_type}" "${target_name}" "${resource_path}" "${required_content}" || return 1

        token="<${target_type}:${target_name}>"
        replacement="${native_option}=${resource_path}"
        sed "s|${token}|${replacement}|g" \
            "${resolved_file}" > "${resolved_file}.tmp" || return 1
        mv "${resolved_file}.tmp" "${resolved_file}" || return 1
    done < "${metadata_file}"
}

targets_resolve_all()
{
    local workdir="$1"
    local profile_count="$2"
    local registry_file="$3"
    local storage_catalog="$4"
    local managed_root="$5"
    local runtime_root="$6"
    local output_file="$7"
    local profile_no=1

    : > "${output_file}" || return 1

    while [ "${profile_no}" -le "${profile_count}" ]; do
        targets_resolve_profile \
            "${profile_no}" "${workdir}" "${registry_file}" "${storage_catalog}" \
            "${managed_root}" "${runtime_root}" || return 1

        [ "${profile_no}" -gt 1 ] && printf '%s\n' '--new' >> "${output_file}"
        cat "${workdir}/profile-${profile_no}.resolved.conf" >> "${output_file}" || return 1
        profile_no=$((profile_no + 1))
    done
}

# Resolve managed targets from a staged source root while emitting references
# to their stable post-install root. Runtime/upstream targets are unchanged.
targets_resolve_profile_mapped()
{
    local profile_no="$1"
    local workdir="$2"
    local registry_file="$3"
    local storage_catalog="$4"
    local managed_source_root="$5"
    local managed_reference_root="$6"
    local runtime_root="$7"
    local profile_file="${workdir}/profile-${profile_no}.conf"
    local metadata_file="${workdir}/profile-${profile_no}.placeholders"
    local resolved_file="${workdir}/profile-${profile_no}.resolved.conf"
    local target_type target_name registry_row native_option storage_key
    local required_content provider_row provider locator source_path reference_path
    local token replacement

    cp "${profile_file}" "${resolved_file}" || return 1

    while IFS="$(printf '\t')" read -r target_type target_name || \
        [ -n "${target_type}${target_name}" ]; do
        [ -n "${target_type}" ] || continue

        registry_row=$(registry_lookup \
            "${registry_file}" "${target_type}" "${target_name}") || {
            common_error "unknown target placeholder <${target_type}:${target_name}> in profile ${profile_no}"
            return 1
        }

        native_option=$(printf '%s\n' "${registry_row}" | awk -F '\t' '{print $1}')
        storage_key=$(printf '%s\n' "${registry_row}" | awk -F '\t' '{print $2}')
        required_content=$(printf '%s\n' "${registry_row}" | awk -F '\t' '{print $3}')

        provider_row=$(storage_lookup "${storage_catalog}" "${storage_key}") || {
            common_error "unknown storage key '${storage_key}'"
            return 1
        }
        provider=$(printf '%s\n' "${provider_row}" | awk -F '\t' '{print $1}')
        locator=$(printf '%s\n' "${provider_row}" | awk -F '\t' '{print $2}')

        case "${provider}" in
            managed)
                source_path=$(storage_join_path \
                    "${managed_source_root}" "${locator}") || return 1
                reference_path=$(storage_join_path \
                    "${managed_reference_root}" "${locator}") || return 1
                ;;
            runtime)
                source_path=$(storage_join_path \
                    "${runtime_root}" "${locator}") || return 1
                reference_path="${source_path}"
                ;;
            *)
                common_error "unsupported storage provider '${provider}'"
                return 1
                ;;
        esac

        storage_validate_resource \
            "${target_type}" "${target_name}" \
            "${source_path}" "${required_content}" || return 1

        token="<${target_type}:${target_name}>"
        replacement="${native_option}=${reference_path}"
        sed "s|${token}|${replacement}|g" \
            "${resolved_file}" > "${resolved_file}.tmp" || return 1
        mv "${resolved_file}.tmp" "${resolved_file}" || return 1
    done < "${metadata_file}"
}

targets_resolve_all_mapped()
{
    local workdir="$1"
    local profile_count="$2"
    local registry_file="$3"
    local storage_catalog="$4"
    local managed_source_root="$5"
    local managed_reference_root="$6"
    local runtime_root="$7"
    local output_file="$8"
    local profile_no=1

    : > "${output_file}" || return 1

    while [ "${profile_no}" -le "${profile_count}" ]; do
        targets_resolve_profile_mapped \
            "${profile_no}" "${workdir}" "${registry_file}" \
            "${storage_catalog}" "${managed_source_root}" \
            "${managed_reference_root}" "${runtime_root}" || return 1

        [ "${profile_no}" -gt 1 ] &&
            printf '%s\n' '--new' >> "${output_file}"
        cat "${workdir}/profile-${profile_no}.resolved.conf" \
            >> "${output_file}" || return 1
        profile_no=$((profile_no + 1))
    done
}
