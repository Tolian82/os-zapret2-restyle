#!/bin/sh

# Public API:
#   ports_extract_file INPUT TCP_OUTPUT UDP_OUTPUT
#
# Each output file contains a single comma-separated list. Empty output means
# that the corresponding protocol is not intercepted by the strategy.

ports_validate_number()
{
    _ports_number="$1"

    case "${_ports_number}" in
        ''|*[!0-9]*)
            common_error "invalid port '${_ports_number}'"
            return 1
            ;;
    esac

    # Force decimal interpretation and reject values outside the valid TCP/UDP
    # port range. Leading zeroes are accepted and normalized.
    _ports_value=$(printf '%s\n' "${_ports_number}" | awk '
        /^[0-9]+$/ {
            value = $0 + 0
            if (value >= 1 && value <= 65535) {
                print value
                exit 0
            }
        }
        END {
            if (NR == 0) {
                exit 1
            }
        }
    ')

    [ -n "${_ports_value}" ] || {
        common_error "port outside valid range: ${_ports_number}"
        return 1
    }

    printf '%s\n' "${_ports_value}"
}

ports_normalize_item()
{
    _ports_item="$1"

    case "${_ports_item}" in
        *-*)
            # Exactly one dash is allowed in a range.
            case "${_ports_item}" in
                *-*-*)
                    common_error "invalid port range '${_ports_item}'"
                    return 1
                    ;;
            esac

            _ports_start=${_ports_item%%-*}
            _ports_end=${_ports_item#*-}

            _ports_start=$(ports_validate_number "${_ports_start}") || return 1
            _ports_end=$(ports_validate_number "${_ports_end}") || return 1

            [ "${_ports_start}" -le "${_ports_end}" ] || {
                common_error "reversed port range '${_ports_item}'"
                return 1
            }

            if [ "${_ports_start}" -eq "${_ports_end}" ]; then
                printf '%s\n' "${_ports_start}"
            else
                printf '%s-%s\n' "${_ports_start}" "${_ports_end}"
            fi
            ;;
        *)
            ports_validate_number "${_ports_item}"
            ;;
    esac
}

ports_append_unique()
{
    _ports_item="$1"
    _ports_file="$2"

    if [ -f "${_ports_file}" ] && grep -Fxq "${_ports_item}" "${_ports_file}"; then
        return 0
    fi

    printf '%s\n' "${_ports_item}" >> "${_ports_file}"
}

ports_collect_spec()
{
    _ports_spec="$1"
    _ports_file="$2"

    [ -n "${_ports_spec}" ] || {
        common_error "empty port filter"
        return 1
    }

    _ports_old_ifs=${IFS}
    IFS=,
    set -- ${_ports_spec}
    IFS=${_ports_old_ifs}

    [ "$#" -gt 0 ] || {
        common_error "empty port filter"
        return 1
    }

    for _ports_raw_item in "$@"; do
        [ -n "${_ports_raw_item}" ] || {
            common_error "empty item in port filter '${_ports_spec}'"
            return 1
        }

        _ports_item=$(ports_normalize_item "${_ports_raw_item}") || return 1
        ports_append_unique "${_ports_item}" "${_ports_file}" || return 1
    done
}

ports_write_csv()
{
    _ports_items_file="$1"
    _ports_output="$2"
    _ports_tmp="${_ports_output}.tmp.$$"

    : > "${_ports_tmp}" || return 1

    if [ -s "${_ports_items_file}" ]; then
        awk '
            NF {
                if (count++) {
                    printf ","
                }
                printf "%s", $0
            }
            END {
                if (count) {
                    printf "\n"
                }
            }
        ' "${_ports_items_file}" > "${_ports_tmp}" || {
            rm -f "${_ports_tmp}"
            return 1
        }
    fi

    mv -f "${_ports_tmp}" "${_ports_output}" || {
        rm -f "${_ports_tmp}"
        return 1
    }
}

ports_extract_file()
{
    _ports_input="$1"
    _ports_tcp_output="$2"
    _ports_udp_output="$3"
    _ports_work_dir=$(mktemp -d /tmp/zapret-ports.XXXXXX) || return 1
    _ports_tcp_items="${_ports_work_dir}/tcp.items"
    _ports_udp_items="${_ports_work_dir}/udp.items"

    common_require_file "${_ports_input}" "port extractor input" || {
        rm -rf "${_ports_work_dir}"
        return 1
    }

    : > "${_ports_tcp_items}"
    : > "${_ports_udp_items}"

    while IFS= read -r _ports_line || [ -n "${_ports_line}" ]; do
        for _ports_token in ${_ports_line}; do
            case "${_ports_token}" in
                --filter-tcp=*)
                    ports_collect_spec \
                        "${_ports_token#--filter-tcp=}" \
                        "${_ports_tcp_items}" || {
                            rm -rf "${_ports_work_dir}"
                            return 1
                        }
                    ;;
                --filter-udp=*)
                    ports_collect_spec \
                        "${_ports_token#--filter-udp=}" \
                        "${_ports_udp_items}" || {
                            rm -rf "${_ports_work_dir}"
                            return 1
                        }
                    ;;
            esac
        done
    done < "${_ports_input}"

    ports_write_csv "${_ports_tcp_items}" "${_ports_tcp_output}" || {
        rm -rf "${_ports_work_dir}"
        return 1
    }
    ports_write_csv "${_ports_udp_items}" "${_ports_udp_output}" || {
        rm -rf "${_ports_work_dir}"
        return 1
    }

    rm -rf "${_ports_work_dir}"
}
