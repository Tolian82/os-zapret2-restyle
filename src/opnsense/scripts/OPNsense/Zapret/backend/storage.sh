#!/bin/sh

# Storage Resolver
#
# Public API:
#   storage_catalog_build OUTPUT_FILE
#   storage_catalog_validate CATALOG_FILE
#   storage_lookup CATALOG_FILE STORAGE_KEY
#   storage_resolve STORAGE_KEY STORAGE_ROOT
#   storage_validate_resource TYPE NAME PATH CONTENT_REQUIRED
#
# Catalog rows are tab-separated:
#   STORAGE_KEY  PROVIDER  LOCATOR
#
# Registry owns target identity. Storage owns physical placement.
# Callers pass only abstract storage keys and roots.

storage_catalog_build()
{
    storage_output=$1

    [ -n "${storage_output}" ] || {
        common_error "storage_catalog_build requires an output file"
        return 1
    }

    storage_tmp="${storage_output}.tmp.$$"

    {
        printf 'hostlist.youtube\tmanaged\thostlist-youtube.txt\n'
        printf 'hostlist.user\tmanaged\thostlist-user.txt\n'
        printf 'hostlist.auto\truntime\tipset/zapret-hosts-auto.txt\n'
        printf 'ipset.telegram\tmanaged\tipset-telegram.txt\n'
    } > "${storage_tmp}" || {
        rm -f "${storage_tmp}"
        common_error "could not create storage catalog '${storage_output}'"
        return 1
    }

    storage_catalog_validate "${storage_tmp}" || {
        rm -f "${storage_tmp}"
        return 1
    }

    mv -f "${storage_tmp}" "${storage_output}" || {
        rm -f "${storage_tmp}"
        common_error "could not install storage catalog '${storage_output}'"
        return 1
    }
}

storage_catalog_validate()
{
    storage_catalog=$1

    [ -f "${storage_catalog}" ] || {
        common_error "storage catalog does not exist: ${storage_catalog}"
        return 1
    }

    awk -F '\t' '
        function fail(message) {
            print "ERROR: invalid storage catalog at line " NR ": " message > "/dev/stderr"
            invalid = 1
        }

        NF != 3 {
            fail("expected 3 tab-separated fields, got " NF)
            next
        }

        $1 !~ /^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)+$/ {
            fail("invalid storage key \047" $1 "\047")
        }

        $2 !~ /^[a-z][a-z0-9_-]*$/ {
            fail("invalid provider \047" $2 "\047")
        }

        $3 == "" {
            fail("invalid empty locator")
        }

        $3 ~ /^\// {
            fail("locator must be relative, got \047" $3 "\047")
        }

        $3 ~ /(^|\/)\.\.($|\/)/ {
            fail("locator must not contain parent traversal")
        }

        {
            if (seen_key[$1]++) {
                fail("duplicate storage key \047" $1 "\047")
            }
        }

        END {
            if (NR == 0) {
                print "ERROR: storage catalog is empty" > "/dev/stderr"
                invalid = 1
            }
            exit invalid ? 1 : 0
        }
    ' "${storage_catalog}"
}

storage_lookup()
{
    storage_catalog=$1
    storage_key=$2

    [ -f "${storage_catalog}" ] || {
        common_error "storage catalog does not exist: ${storage_catalog}"
        return 1
    }

    [ -n "${storage_key}" ] || {
        common_error "storage_lookup requires a storage key"
        return 1
    }

    awk -F '\t' -v key="${storage_key}" '
        $1 == key {
            print $2 "\t" $3
            found = 1
            exit
        }
        END { exit found ? 0 : 1 }
    ' "${storage_catalog}"
}

storage_join_path()
{
    storage_root=$1
    storage_locator=$2

    [ -n "${storage_root}" ] && [ -n "${storage_locator}" ] || {
        common_error "storage_join_path requires ROOT and LOCATOR"
        return 1
    }

    case "${storage_locator}" in
        /*|../*|*/../*|*/..)
            common_error "unsafe storage locator '${storage_locator}'"
            return 1
            ;;
    esac

    printf '%s/%s\n' "${storage_root%/}" "${storage_locator}"
}

storage_resolve()
{
    storage_key=$1
    storage_root=$2
    storage_catalog=${3-}
    storage_temp_catalog=""

    [ -n "${storage_key}" ] && [ -n "${storage_root}" ] || {
        common_error "storage_resolve requires STORAGE_KEY and STORAGE_ROOT"
        return 1
    }

    if [ -z "${storage_catalog}" ]; then
        storage_temp_catalog=$(mktemp /tmp/zapret-storage-catalog.XXXXXX) || return 1
        storage_catalog_build "${storage_temp_catalog}" || {
            rm -f "${storage_temp_catalog}"
            return 1
        }
        storage_catalog="${storage_temp_catalog}"
    fi

    storage_row=$(storage_lookup "${storage_catalog}" "${storage_key}") || {
        [ -n "${storage_temp_catalog}" ] && rm -f "${storage_temp_catalog}"
        common_error "unknown storage key '${storage_key}'"
        return 1
    }

    storage_provider=$(printf '%s\n' "${storage_row}" | awk -F '\t' '{print $1}')
    storage_locator=$(printf '%s\n' "${storage_row}" | awk -F '\t' '{print $2}')

    case "${storage_provider}" in
        managed|runtime)
            storage_join_path "${storage_root}" "${storage_locator}"
            storage_status=$?
            ;;
        *)
            common_error "unsupported storage provider '${storage_provider}' for key '${storage_key}'"
            storage_status=1
            ;;
    esac

    [ -n "${storage_temp_catalog}" ] && rm -f "${storage_temp_catalog}"
    return "${storage_status}"
}

storage_validate_resource()
{
    storage_type=$1
    storage_name=$2
    storage_path=$3
    storage_required_content=$4

    [ -n "${storage_type}" ] && [ -n "${storage_name}" ] && [ -n "${storage_path}" ] || {
        common_error "storage_validate_resource requires TYPE, NAME and PATH"
        return 1
    }

    case "${storage_required_content}" in
        0|1) ;;
        *)
            common_error "invalid content-required flag '${storage_required_content}' for <${storage_type}:${storage_name}>"
            return 1
            ;;
    esac

    if [ ! -f "${storage_path}" ]; then
        common_error "target <${storage_type}:${storage_name}> is registered but its resource file does not exist:"
        echo "       ${storage_path}" >&2
        return 1
    fi

    if [ "${storage_required_content}" = "1" ] && [ ! -s "${storage_path}" ]; then
        common_error "target <${storage_type}:${storage_name}> is registered but its resource file is empty:"
        echo "       ${storage_path}" >&2
        return 1
    fi
}

# Resolve a storage key with distinct roots for generated managed resources and
# upstream/runtime resources. This is a compatible extension; storage_resolve
# remains available for callers that intentionally use one common root.
storage_resolve_roots()
{
    storage_key=$1
    storage_managed_root=$2
    storage_runtime_root=$3
    storage_catalog=${4-}
    storage_temp_catalog=""

    [ -n "${storage_key}" ] && [ -n "${storage_managed_root}" ] && [ -n "${storage_runtime_root}" ] || {
        common_error "storage_resolve_roots requires STORAGE_KEY, MANAGED_ROOT and RUNTIME_ROOT"
        return 1
    }

    if [ -z "${storage_catalog}" ]; then
        storage_temp_catalog=$(mktemp /tmp/zapret-storage-catalog.XXXXXX) || return 1
        storage_catalog_build "${storage_temp_catalog}" || {
            rm -f "${storage_temp_catalog}"
            return 1
        }
        storage_catalog="${storage_temp_catalog}"
    fi

    storage_row=$(storage_lookup "${storage_catalog}" "${storage_key}") || {
        [ -n "${storage_temp_catalog}" ] && rm -f "${storage_temp_catalog}"
        common_error "unknown storage key '${storage_key}'"
        return 1
    }

    storage_provider=$(printf '%s\n' "${storage_row}" | awk -F '\t' '{print $1}')
    storage_locator=$(printf '%s\n' "${storage_row}" | awk -F '\t' '{print $2}')

    case "${storage_provider}" in
        managed)
            storage_join_path "${storage_managed_root}" "${storage_locator}"
            storage_status=$?
            ;;
        runtime)
            storage_join_path "${storage_runtime_root}" "${storage_locator}"
            storage_status=$?
            ;;
        *)
            common_error "unsupported storage provider '${storage_provider}' for key '${storage_key}'"
            storage_status=1
            ;;
    esac

    [ -n "${storage_temp_catalog}" ] && rm -f "${storage_temp_catalog}"
    return "${storage_status}"
}
