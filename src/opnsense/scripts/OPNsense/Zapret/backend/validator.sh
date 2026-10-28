#!/bin/sh

# Public API:
#
#   validator_validate_build \
#       ARGS_FILE TRAFFIC_FILE TCP_PORTS_FILE UDP_PORTS_FILE \
#       MANAGED_ROOT RUNTIME_ROOT
#
# The validator is intentionally read-only. It never repairs, normalizes,
# installs, or launches anything.

validator_fail()
{
    common_error "$1"
    return 1
}

validator_require_regular_file()
{
    _validator_regular_path="$1"
    _validator_regular_label="$2"
    _validator_regular_nonempty="$3"

    [ -f "${_validator_regular_path}" ] || {
        validator_fail "${_validator_regular_label} does not exist: ${_validator_regular_path}"
        return 1
    }

    if [ "${_validator_regular_nonempty}" = "1" ] &&
       [ ! -s "${_validator_regular_path}" ]; then
        validator_fail "${_validator_regular_label} is empty: ${_validator_regular_path}"
        return 1
    fi
}

validator_reject_control_characters()
{
    _validator_control_file="$1"
    _validator_control_label="$2"

    # Text artifacts may contain tab, LF, and CR. All other C0 control bytes
    # are rejected. NUL is included in this range.
    LC_ALL=C awk '
        {
            line = $0
            for (i = 1; i <= length(line); i++) {
                c = substr(line, i, 1)
                if (c ~ /[[:cntrl:]]/ && c != "\t" && c != "\r") {
                    exit 1
                }
            }
        }
    ' "${_validator_control_file}" || {
        validator_fail "${_validator_control_label} contains unsupported control characters"
        return 1
    }

    # awk implementations can stop at NUL. A byte-count comparison catches
    # binary data that text processing might otherwise hide.
    _validator_control_bytes=$(wc -c < "${_validator_control_file}" | tr -d ' ')
    _validator_control_visible=$(tr -d '\000' < "${_validator_control_file}" |
        wc -c | tr -d ' ')

    [ "${_validator_control_bytes}" = "${_validator_control_visible}" ] || {
        validator_fail "${_validator_control_label} contains NUL bytes"
        return 1
    }
}

validator_reject_legacy_tokens()
{
    _validator_legacy_file="$1"

    if grep -nE '(^|[^A-Za-z0-9_])(HTTP_ARGS|HTTPS_ARGS|PORTS)([^A-Za-z0-9_]|$)' \
        "${_validator_legacy_file}" >/dev/null 2>&1; then
        validator_fail "generated arguments contain legacy HTTP_ARGS, HTTPS_ARGS, or PORTS tokens"
        return 1
    fi
}

validator_reject_unresolved_placeholders()
{
    _validator_placeholder_file="$1"

    if grep -nE '<[A-Za-z][A-Za-z0-9_]*:[A-Za-z0-9_.-]+>' \
        "${_validator_placeholder_file}" >/dev/null 2>&1; then
        validator_fail "resolved strategy still contains <TYPE:NAME> placeholders"
        return 1
    fi

    if grep -nE '<[^>]*$|^[^<]*>' "${_validator_placeholder_file}" \
        >/dev/null 2>&1; then
        validator_fail "resolved strategy contains malformed placeholder brackets"
        return 1
    fi
}

validator_has_filter()
{
    _validator_filter_file="$1"

    grep -Eq -- '(^|[[:space:]])--filter-(tcp|udp)=' \
        "${_validator_filter_file}"
}

validator_validate_port_csv()
{
    _validator_csv_file="$1"
    _validator_csv_label="$2"

    validator_require_regular_file \
        "${_validator_csv_file}" "${_validator_csv_label}" 0 || return 1

    [ -s "${_validator_csv_file}" ] || return 0

    _validator_csv_value=$(tr -d '\r\n' < "${_validator_csv_file}")

    [ -n "${_validator_csv_value}" ] || return 0

    printf '%s\n' "${_validator_csv_value}" | awk -F, '
        function valid_number(value, number) {
            if (value !~ /^[0-9]+$/) {
                return 0
            }
            number = value + 0
            return number >= 1 && number <= 65535
        }

        {
            for (i = 1; i <= NF; i++) {
                item = $i

                if (item ~ /^[0-9]+$/) {
                    if (!valid_number(item)) {
                        exit 1
                    }
                    continue
                }

                if (item ~ /^[0-9]+-[0-9]+$/) {
                    split(item, range, "-")
                    if (!valid_number(range[1]) ||
                        !valid_number(range[2]) ||
                        (range[1] + 0) > (range[2] + 0)) {
                        exit 1
                    }
                    continue
                }

                exit 1
            }
        }
    ' || {
        validator_fail "${_validator_csv_label} contains invalid ports: ${_validator_csv_value}"
        return 1
    }
}

validator_compare_ports()
{
    _validator_compare_traffic="$1"
    _validator_compare_tcp="$2"
    _validator_compare_udp="$3"
    _validator_compare_work=$(mktemp -d /tmp/zapret-validator-ports.XXXXXX) ||
        return 1

    _validator_compare_expected_tcp="${_validator_compare_work}/tcp.txt"
    _validator_compare_expected_udp="${_validator_compare_work}/udp.txt"

    ports_extract_file \
        "${_validator_compare_traffic}" \
        "${_validator_compare_expected_tcp}" \
        "${_validator_compare_expected_udp}" || {
            rm -rf "${_validator_compare_work}"
            validator_fail "cannot re-extract ports from resolved strategy"
            return 1
        }

    cmp -s "${_validator_compare_expected_tcp}" "${_validator_compare_tcp}" || {
        rm -rf "${_validator_compare_work}"
        validator_fail "TCP port artifact does not match resolved strategy"
        return 1
    }

    cmp -s "${_validator_compare_expected_udp}" "${_validator_compare_udp}" || {
        rm -rf "${_validator_compare_work}"
        validator_fail "UDP port artifact does not match resolved strategy"
        return 1
    }

    rm -rf "${_validator_compare_work}"
}

validator_path_is_allowed()
{
    _validator_allowed_path="$1"
    _validator_allowed_managed="$2"
    _validator_allowed_runtime="$3"

    case "${_validator_allowed_path}" in
        "${_validator_allowed_managed}"/*|"${_validator_allowed_runtime}"/*)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

validator_validate_reference()
{
    _validator_reference_path="$1"
    _validator_reference_kind="$2"
    _validator_reference_managed="$3"
    _validator_reference_runtime="$4"
    _validator_reference_nonempty="$5"

    case "${_validator_reference_path}" in
        /*) ;;
        *)
            validator_fail "${_validator_reference_kind} path is not absolute: ${_validator_reference_path}"
            return 1
            ;;
    esac

    validator_path_is_allowed \
        "${_validator_reference_path}" \
        "${_validator_reference_managed}" \
        "${_validator_reference_runtime}" || {
            validator_fail "${_validator_reference_kind} path is outside managed/runtime roots: ${_validator_reference_path}"
            return 1
        }

    validator_require_regular_file \
        "${_validator_reference_path}" \
        "${_validator_reference_kind}" \
        "${_validator_reference_nonempty}"
}

validator_validate_argument_references()
{
    _validator_refs_args="$1"
    _validator_refs_managed="$2"
    _validator_refs_runtime="$3"

    while IFS= read -r _validator_refs_line ||
          [ -n "${_validator_refs_line}" ]; do
        for _validator_refs_token in ${_validator_refs_line}; do
            case "${_validator_refs_token}" in
                --lua-init=@*)
                    validator_validate_reference \
                        "${_validator_refs_token#--lua-init=@}" \
                        "Lua initializer" \
                        "${_validator_refs_managed}" \
                        "${_validator_refs_runtime}" 1 || return 1
                    ;;
                --blob=*:*)
                    _validator_refs_blob=${_validator_refs_token#--blob=}
                    _validator_refs_blob_value=${_validator_refs_blob#*:}
                    case "${_validator_refs_blob_value}" in
                        @*)
                            validator_validate_reference \
                                "${_validator_refs_blob_value#@}" \
                                "blob file" \
                                "${_validator_refs_managed}" \
                                "${_validator_refs_runtime}" 1 || return 1
                            ;;
                    esac
                    ;;
                --hostlist=*)
                    validator_validate_reference \
                        "${_validator_refs_token#--hostlist=}" \
                        "hostlist" \
                        "${_validator_refs_managed}" \
                        "${_validator_refs_runtime}" 1 || return 1
                    ;;
                --ipset=*)
                    validator_validate_reference \
                        "${_validator_refs_token#--ipset=}" \
                        "ipset" \
                        "${_validator_refs_managed}" \
                        "${_validator_refs_runtime}" 1 || return 1
                    ;;
                --ipset-exclude=*)
                    validator_validate_reference \
                        "${_validator_refs_token#--ipset-exclude=}" \
                        "global Exclude IPSet" \
                        "${_validator_refs_managed}" \
                        "${_validator_refs_runtime}" 1 || return 1
                    ;;
                --hostlist-exclude=*)
                    validator_validate_reference \
                        "${_validator_refs_token#--hostlist-exclude=}" \
                        "Exclude Domains list" \
                        "${_validator_refs_managed}" \
                        "${_validator_refs_runtime}" 1 || return 1
                    ;;
            esac
        done
    done < "${_validator_refs_args}"
}

validator_validate_build()
{
    _validator_build_args="$1"
    _validator_build_traffic="$2"
    _validator_build_tcp="$3"
    _validator_build_udp="$4"
    _validator_build_managed="$5"
    _validator_build_runtime="$6"

    [ -d "${_validator_build_managed}" ] || {
        validator_fail "managed storage root does not exist: ${_validator_build_managed}"
        return 1
    }

    [ -d "${_validator_build_runtime}" ] || {
        validator_fail "runtime storage root does not exist: ${_validator_build_runtime}"
        return 1
    }

    validator_require_regular_file \
        "${_validator_build_args}" "generated argument file" 1 || return 1
    validator_require_regular_file \
        "${_validator_build_traffic}" "resolved traffic strategy" 1 || return 1

    validator_validate_port_csv \
        "${_validator_build_tcp}" "TCP port artifact" || return 1
    validator_validate_port_csv \
        "${_validator_build_udp}" "UDP port artifact" || return 1

    validator_reject_control_characters \
        "${_validator_build_args}" "generated argument file" || return 1
    validator_reject_control_characters \
        "${_validator_build_traffic}" "resolved traffic strategy" || return 1

    validator_reject_legacy_tokens "${_validator_build_args}" || return 1
    validator_reject_unresolved_placeholders "${_validator_build_traffic}" ||
        return 1

    validator_has_filter "${_validator_build_traffic}" || {
        validator_fail "resolved traffic strategy contains no --filter-tcp= or --filter-udp="
        return 1
    }

    if [ ! -s "${_validator_build_tcp}" ] &&
       [ ! -s "${_validator_build_udp}" ]; then
        validator_fail "both TCP and UDP port artifacts are empty"
        return 1
    fi

    validator_compare_ports \
        "${_validator_build_traffic}" \
        "${_validator_build_tcp}" \
        "${_validator_build_udp}" || return 1

    validator_validate_argument_references \
        "${_validator_build_args}" \
        "${_validator_build_managed}" \
        "${_validator_build_runtime}" || return 1
}

validator_validate_mapped_reference()
{
    _validator_mapped_path="$1"
    _validator_mapped_kind="$2"
    _validator_mapped_static_root="$3"
    _validator_mapped_reference_root="$4"
    _validator_mapped_source_root="$5"
    _validator_mapped_nonempty="$6"

    case "${_validator_mapped_path}" in
        "${_validator_mapped_reference_root}"/*)
            _validator_mapped_suffix=${_validator_mapped_path#"${_validator_mapped_reference_root}"/}
            _validator_mapped_real="${_validator_mapped_source_root}/${_validator_mapped_suffix}"
            ;;
        "${_validator_mapped_static_root}"/*)
            _validator_mapped_real="${_validator_mapped_path}"
            ;;
        *)
            validator_fail "${_validator_mapped_kind} path is outside allowed roots: ${_validator_mapped_path}"
            return 1
            ;;
    esac

    validator_require_regular_file \
        "${_validator_mapped_real}" \
        "${_validator_mapped_kind}" \
        "${_validator_mapped_nonempty}"
}

validator_validate_argument_references_mapped()
{
    _validator_mapped_args="$1"
    _validator_mapped_static_root="$2"
    _validator_mapped_reference_root="$3"
    _validator_mapped_source_root="$4"

    while IFS= read -r _validator_mapped_line ||
          [ -n "${_validator_mapped_line}" ]; do
        for _validator_mapped_token in ${_validator_mapped_line}; do
            case "${_validator_mapped_token}" in
                --lua-init=@*)
                    validator_validate_mapped_reference \
                        "${_validator_mapped_token#--lua-init=@}" \
                        "Lua initializer" \
                        "${_validator_mapped_static_root}" \
                        "${_validator_mapped_reference_root}" \
                        "${_validator_mapped_source_root}" 1 || return 1
                    ;;
                --blob=*:*)
                    _validator_mapped_blob=${_validator_mapped_token#--blob=}
                    _validator_mapped_blob_value=${_validator_mapped_blob#*:}
                    case "${_validator_mapped_blob_value}" in
                        @*)
                            validator_validate_mapped_reference \
                                "${_validator_mapped_blob_value#@}" \
                                "blob file" \
                                "${_validator_mapped_static_root}" \
                                "${_validator_mapped_reference_root}" \
                                "${_validator_mapped_source_root}" 1 || return 1
                            ;;
                    esac
                    ;;
                --hostlist=*)
                    validator_validate_mapped_reference \
                        "${_validator_mapped_token#--hostlist=}" \
                        "hostlist" \
                        "${_validator_mapped_static_root}" \
                        "${_validator_mapped_reference_root}" \
                        "${_validator_mapped_source_root}" 1 || return 1
                    ;;
                --ipset=*)
                    validator_validate_mapped_reference \
                        "${_validator_mapped_token#--ipset=}" \
                        "ipset" \
                        "${_validator_mapped_static_root}" \
                        "${_validator_mapped_reference_root}" \
                        "${_validator_mapped_source_root}" 1 || return 1
                    ;;
                --ipset-exclude=*)
                    validator_validate_mapped_reference \
                        "${_validator_mapped_token#--ipset-exclude=}" \
                        "global Exclude IPSet" \
                        "${_validator_mapped_static_root}" \
                        "${_validator_mapped_reference_root}" \
                        "${_validator_mapped_source_root}" 1 || return 1
                    ;;
                --hostlist-exclude=*)
                    validator_validate_mapped_reference \
                        "${_validator_mapped_token#--hostlist-exclude=}" \
                        "Exclude Domains list" \
                        "${_validator_mapped_static_root}" \
                        "${_validator_mapped_reference_root}" \
                        "${_validator_mapped_source_root}" 1 || return 1
                    ;;
            esac
        done
    done < "${_validator_mapped_args}"
}

validator_validate_build_mapped()
{
    _validator_build_mapped_args="$1"
    _validator_build_mapped_traffic="$2"
    _validator_build_mapped_tcp="$3"
    _validator_build_mapped_udp="$4"
    _validator_build_mapped_static_root="$5"
    _validator_build_mapped_reference_root="$6"
    _validator_build_mapped_source_root="$7"

    [ -d "${_validator_build_mapped_static_root}" ] || {
        validator_fail "static resource root does not exist: ${_validator_build_mapped_static_root}"
        return 1
    }
    [ -d "${_validator_build_mapped_source_root}" ] || {
        validator_fail "staged deployment root does not exist: ${_validator_build_mapped_source_root}"
        return 1
    }

    validator_require_regular_file \
        "${_validator_build_mapped_args}" "generated argument file" 1 || return 1
    validator_require_regular_file \
        "${_validator_build_mapped_traffic}" "resolved traffic strategy" 1 || return 1
    validator_validate_port_csv \
        "${_validator_build_mapped_tcp}" "TCP port artifact" || return 1
    validator_validate_port_csv \
        "${_validator_build_mapped_udp}" "UDP port artifact" || return 1
    validator_reject_control_characters \
        "${_validator_build_mapped_args}" "generated argument file" || return 1
    validator_reject_control_characters \
        "${_validator_build_mapped_traffic}" "resolved traffic strategy" || return 1
    validator_reject_legacy_tokens \
        "${_validator_build_mapped_args}" || return 1
    validator_reject_unresolved_placeholders \
        "${_validator_build_mapped_traffic}" || return 1
    validator_has_filter "${_validator_build_mapped_traffic}" || {
        validator_fail "resolved traffic strategy contains no --filter-tcp= or --filter-udp="
        return 1
    }

    if [ ! -s "${_validator_build_mapped_tcp}" ] &&
       [ ! -s "${_validator_build_mapped_udp}" ]; then
        validator_fail "both TCP and UDP port artifacts are empty"
        return 1
    fi

    validator_compare_ports \
        "${_validator_build_mapped_traffic}" \
        "${_validator_build_mapped_tcp}" \
        "${_validator_build_mapped_udp}" || return 1

    validator_validate_argument_references_mapped \
        "${_validator_build_mapped_args}" \
        "${_validator_build_mapped_static_root}" \
        "${_validator_build_mapped_reference_root}" \
        "${_validator_build_mapped_source_root}"
}

# Validate that a staged runtime tree will remain traversable/readable after
# dvtws2 drops privileges to nobody.
validator_validate_runtime_modes()
{
    _validator_modes_root="$1"
    _validator_modes_managed="${_validator_modes_root}/managed"

    [ "$(stat -f '%Lp' "${_validator_modes_root}")" = "755" ] || {
        validator_fail "runtime root must have mode 0755: ${_validator_modes_root}"
        return 1
    }

    [ "$(stat -f '%Lp' "${_validator_modes_managed}")" = "755" ] || {
        validator_fail "managed target directory must have mode 0755"
        return 1
    }

    for _validator_modes_file in \
        "${_validator_modes_managed}/hostlist-youtube.txt" \
        "${_validator_modes_managed}/ipset-telegram.txt" \
        "${_validator_modes_managed}/ipset-discord.txt" \
        "${_validator_modes_managed}/ipset-x.txt" \
        "${_validator_modes_managed}/ipset-sip.txt" \
        "${_validator_modes_managed}/ipset-custom.txt" \
        "${_validator_modes_managed}/ipset-exclude.txt" \
        "${_validator_modes_managed}/hostlist-user.txt" \
        "${_validator_modes_managed}/hostlist-exclude.txt"
    do
        # An immutable pre-Exclude-IPSet common release legitimately has
        # eight managed files, not nine. Only the native FD9 boot worker may
        # set this compatibility witness after the original sealed Config
        # has been matched in full. Never write into the sealed old release.
        # New-format Apply and any actual --ipset-exclude argument must still
        # provide the ninth file and the six-list staging manifest.
        if [ "${_validator_modes_file}" = "${_validator_modes_managed}/ipset-exclude.txt" ] &&
           [ "${SHARED_BOOT_LEGACY_EMPTY_EXCLUDE_IPSET:-0}" = 1 ] &&
           [ ! -e "${_validator_modes_file}" ] &&
           [ ! -L "${_validator_modes_file}" ] &&
           [ ! -e "${_validator_modes_root}/ipset-manifest.json" ] &&
           [ ! -L "${_validator_modes_root}/ipset-manifest.json" ] &&
           [ -f "${_validator_modes_root}/dvtws.args" ] &&
           [ ! -L "${_validator_modes_root}/dvtws.args" ] &&
           ! grep -Fq -- '--ipset-exclude' "${_validator_modes_root}/dvtws.args"; then
            continue
        fi
        [ -f "${_validator_modes_file}" ] || {
            validator_fail "required managed runtime file is missing: ${_validator_modes_file}"
            return 1
        }
        [ "$(stat -f '%Lp' "${_validator_modes_file}")" = "644" ] || {
            validator_fail "managed runtime file must have mode 0644: ${_validator_modes_file}"
            return 1
        }
    done
}

# Native parameter/file validation uses the candidate's lists, never old live
# lists. --dry-run does not launch interception or validate Lua execution.
validator_validate_engine_mapped()
{
    _validator_engine_bin="$1"
    _validator_engine_args="$2"
    _validator_engine_reference="$3"
    _validator_engine_source="$4"
    _validator_engine_python="$5"
    "${_validator_engine_python}" - "${_validator_engine_bin}" \
        "${_validator_engine_args}" "${_validator_engine_reference}" \
        "${_validator_engine_source}" <<'PY'
from pathlib import Path
import os
import re
import stat
import subprocess
import sys
import tempfile

binary, args_file, reference, source = sys.argv[1:]
tokens = Path(args_file).read_text(encoding="utf-8").split()
prefix = reference.rstrip("/") + "/"
source_root = Path(source)

# Native staging and candidate.xml/plan.json remain private under FD9.
# dvtws2 drops privileges before reading hostlists in --dry-run and cannot
# traverse shared-work (0700). Copy ONLY allowed public runtime lists into a
# short-lived, nobody-readable temp mirror. Never chmod the private work.
def validate_source(relative):
    parts = Path(relative).parts
    if len(parts) != 2 or parts[0] != "managed" or not re.fullmatch(
        r"(?:hostlist|ipset)-[a-z0-9-]+\.txt", parts[1]
    ):
        raise ValueError("unexpected staged engine reference")
    parent = source_root / "managed"
    if parent.is_symlink() or not parent.is_dir():
        raise ValueError("unsafe managed directory in native candidate")
    path = parent / parts[1]
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("unsafe staged hostlist or IPSET")
    return path

try:
    with tempfile.TemporaryDirectory(prefix="zapret-dvtws-validate-", dir="/tmp") as directory:
        public_root = Path(directory)
        os.chmod(public_root, 0o755)
        public_managed = public_root / "managed"
        public_managed.mkdir(mode=0o755)
        os.chmod(public_managed, 0o755)
        copied = set()

        def remap(value):
            if not value.startswith(prefix):
                return value
            relative = value[len(prefix):]
            source_file = validate_source(relative)
            destination = public_root / relative
            if relative not in copied:
                with source_file.open("rb") as old, destination.open("xb") as new:
                    while True:
                        chunk = old.read(65536)
                        if not chunk:
                            break
                        new.write(chunk)
                os.chmod(destination, 0o644)
                copied.add(relative)
            return str(destination)

        mapped = []
        for token in tokens:
            option, sep, value = token.partition("=")
            if sep and option in ("--ipset", "--ipset-exclude", "--hostlist", "--hostlist-exclude"):
                token = option + "=" + remap(value)
            elif sep and option == "--lua-init" and value.startswith("@"):
                token = option + "=@" + remap(value[1:])
            elif sep and option == "--blob" and ":@" in value:
                kind, path = value.split(":@", 1)
                token = option + "=" + kind + ":@" + remap(path)
            mapped.append(token)
        result = subprocess.run([binary, *mapped, "--dry-run"], capture_output=True, timeout=15)
except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
    print("ERROR: installed engine validation failed: " + str(exc), file=sys.stderr)
    raise SystemExit(1)
if result.returncode:
    detail = (result.stderr or result.stdout)[-4096:].decode("utf-8", errors="replace")
    print("ERROR: installed engine rejected candidate: " + detail, file=sys.stderr)
    raise SystemExit(1)
PY
}
