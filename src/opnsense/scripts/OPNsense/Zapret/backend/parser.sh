#!/bin/sh

# Public API:
#   parser_parse STRATEGY WORKDIR
#   parser_validate_placeholder_syntax PROFILE_NO PROFILE_FILE
#   parser_index_placeholders PROFILE_FILE META_FILE
#
# The parser only splits profiles and identifies generic <TYPE:NAME>
# placeholders. It does not know target types, storage paths or dvtws2
# options.

parser_parse()
{
    local input="$1"
    local workdir="$2"
    local input_file="${workdir}/traffic.input"
    local count_file="${workdir}/profile-count"

    mkdir -p "${workdir}" || {
        common_error "unable to create strategy work directory: ${workdir}"
        return 1
    }

    # A reused work directory must never retain profiles from an older parse.
    rm -f "${workdir}"/profile-*.conf "${count_file}"

    printf '%s\n' "${input}" > "${input_file}" || {
        common_error "unable to write parser input: ${input_file}"
        return 1
    }

    awk -v dir="${workdir}" -v count_file="${count_file}" '
    function fail(message) {
        print "ERROR: " message > "/dev/stderr"
        failed = 1
        exit 21
    }
    function is_blank(value, copy) {
        copy = value
        gsub(/[[:space:]]/, "", copy)
        return copy == ""
    }
    BEGIN {
        profile = 1
        output = dir "/profile-1.conf"
        content = 0
        failed = 0
    }
    {
        # OPNsense may receive CRLF text copied from Windows. Remove only the
        # carriage return; all other strategy text is preserved verbatim.
        sub(/\r$/, "")

        separator = $0
        sub(/^[[:space:]]+/, "", separator)
        sub(/[[:space:]]+$/, "", separator)

        if (separator == "--new") {
            if (!content)
                fail("empty strategy profile before --new at line " NR)
            close(output)
            profile++
            output = dir "/profile-" profile ".conf"
            content = 0
            next
        }

        print $0 >> output
        if (!is_blank($0))
            content = 1
    }
    END {
        if (failed)
            exit 21
        if (NR == 0 || (profile == 1 && !content))
            fail("Traffic Strategy contains no profiles")
        if (!content)
            fail("empty strategy profile after the final --new")
        print profile > count_file
    }
    ' "${input_file}" || return 1

    [ -s "${count_file}" ] || {
        common_error "parser did not produce a profile count"
        return 1
    }

    cat "${count_file}"
}

parser_validate_placeholder_syntax()
{
    local profile_no="$1"
    local profile_file="$2"

    [ -f "${profile_file}" ] || {
        common_error "strategy profile ${profile_no} does not exist: ${profile_file}"
        return 1
    }

    # Remove every valid generic placeholder from a copy of each line. Any
    # remaining angle bracket is malformed syntax, including legacy forms such
    # as <HOSTLIST>, missing names and unmatched brackets.
    awk -v profile="${profile_no}" '
    {
        original = $0
        clean = $0
        gsub(/<[A-Z][A-Z0-9_-]*:[A-Za-z0-9][A-Za-z0-9_.-]*>/, "", clean)
        if (clean ~ /[<>]/) {
            print "ERROR: invalid placeholder syntax in profile " profile ", line " NR > "/dev/stderr"
            print "       " original > "/dev/stderr"
            print "       expected <TYPE:NAME>, for example <HOSTLIST:youtube>" > "/dev/stderr"
            exit 22
        }
    }
    ' "${profile_file}"
}

parser_index_placeholders()
{
    local profile_file="$1"
    local meta_file="$2"

    [ -f "${profile_file}" ] || {
        common_error "cannot index placeholders; profile file does not exist: ${profile_file}"
        return 1
    }

    # The metadata format is intentionally small and stable:
    #   TYPE<TAB>NAME
    # Duplicates are removed while preserving first-use order.
    awk '
    {
        line = $0
        while (match(line, /<[A-Z][A-Z0-9_-]*:[A-Za-z0-9][A-Za-z0-9_.-]*>/)) {
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
    ' "${profile_file}" > "${meta_file}" || {
        common_error "unable to write placeholder index: ${meta_file}"
        return 1
    }
}
