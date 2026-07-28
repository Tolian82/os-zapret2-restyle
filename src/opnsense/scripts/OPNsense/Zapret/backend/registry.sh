#!/bin/sh

# Target Registry
#
# Public API:
#   registry_build OUTPUT_FILE
#   registry_validate REGISTRY_FILE
#   registry_lookup REGISTRY_FILE TYPE NAME
#   registry_exists REGISTRY_FILE TYPE NAME
#   registry_list REGISTRY_FILE [TYPE]
#
# Registry rows are tab-separated:
#   TYPE  NAME  NATIVE_OPTION  STORAGE_KEY  CONTENT_REQUIRED
#
# The registry stores only target identity and abstract storage keys.
# Physical paths belong exclusively to storage.sh.

registry_build()
{
    registry_output=$1

    [ -n "${registry_output}" ] || {
        common_error "registry_build requires an output file"
        return 1
    }

    registry_tmp="${registry_output}.tmp.$$"

    {
        printf 'HOSTLIST\tyoutube\t--hostlist\thostlist.youtube\t1\n'
        printf 'HOSTLIST\tuser\t--hostlist\thostlist.user\t1\n'
        printf 'HOSTLIST\tauto\t--hostlist\thostlist.auto\t0\n'
        printf 'IPSET\ttelegram\t--ipset\tipset.telegram\t1\n'
    } > "${registry_tmp}" || {
        rm -f "${registry_tmp}"
        common_error "could not create target registry '${registry_output}'"
        return 1
    }

    registry_validate "${registry_tmp}" || {
        rm -f "${registry_tmp}"
        return 1
    }

    mv -f "${registry_tmp}" "${registry_output}" || {
        rm -f "${registry_tmp}"
        common_error "could not install target registry '${registry_output}'"
        return 1
    }
}

registry_validate()
{
    registry_file=$1

    [ -f "${registry_file}" ] || {
        common_error "target registry does not exist: ${registry_file}"
        return 1
    }

    awk -F '\t' '
        function fail(message) {
            print "ERROR: invalid target registry at line " NR ": " message > "/dev/stderr"
            invalid = 1
        }

        NF != 5 {
            fail("expected 5 tab-separated fields, got " NF)
            next
        }

        $1 !~ /^[A-Z][A-Z0-9_]*$/ {
            fail("invalid target type \047" $1 "\047")
        }

        $2 !~ /^[a-z][a-z0-9_-]*$/ {
            fail("invalid target name \047" $2 "\047")
        }

        $3 !~ /^--[a-z0-9-]+$/ {
            fail("invalid native option \047" $3 "\047")
        }

        $4 !~ /^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)+$/ {
            fail("invalid storage key \047" $4 "\047")
        }

        $5 != "0" && $5 != "1" {
            fail("content-required must be 0 or 1")
        }

        {
            identity = $1 SUBSEP $2
            if (seen_identity[identity]++) {
                fail("duplicate target identity <" $1 ":" $2 ">")
            }

            if (seen_storage[$4]++) {
                fail("duplicate storage key \047" $4 "\047")
            }
        }

        END {
            if (NR == 0) {
                print "ERROR: target registry is empty" > "/dev/stderr"
                invalid = 1
            }
            exit invalid ? 1 : 0
        }
    ' "${registry_file}"
}

registry_lookup()
{
    registry_file=$1
    registry_type=$2
    registry_name=$3

    [ -f "${registry_file}" ] || {
        common_error "target registry does not exist: ${registry_file}"
        return 1
    }

    [ -n "${registry_type}" ] && [ -n "${registry_name}" ] || {
        common_error "registry_lookup requires TYPE and NAME"
        return 1
    }

    awk -F '\t' -v type="${registry_type}" -v name="${registry_name}" '
        $1 == type && $2 == name {
            print $3 "\t" $4 "\t" $5
            found = 1
            exit
        }
        END { exit found ? 0 : 1 }
    ' "${registry_file}"
}

registry_exists()
{
    registry_file=$1
    registry_type=$2
    registry_name=$3

    registry_lookup "${registry_file}" "${registry_type}" "${registry_name}" >/dev/null 2>&1
}

registry_list()
{
    registry_file=$1
    registry_type=${2-}

    [ -f "${registry_file}" ] || {
        common_error "target registry does not exist: ${registry_file}"
        return 1
    }

    if [ -n "${registry_type}" ]; then
        awk -F '\t' -v type="${registry_type}" '$1 == type { print $1 "\t" $2 "\t" $3 "\t" $4 "\t" $5 }' "${registry_file}"
    else
        cat "${registry_file}"
    fi
}
