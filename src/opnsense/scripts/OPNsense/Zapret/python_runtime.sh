#!/bin/sh
# One native, policy-checked Python entrypoint. Never inserts a persistent
# process: the same PID/FD9 and argv proceed through exec after validation.
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHON_BIN="${ZAPRET_PYTHON_BIN:-/usr/local/bin/python3}"
PYTHON_POLICY="${ZAPRET_PYTHON_POLICY:-/usr/local/share/zapret2-restyle/compatibility.json}"

# An explicit test interpreter may be named via PATH only in a source fixture.
# Installed OPNsense always defaults to the qualified absolute generic link.
case "${PYTHON_BIN}" in
    */*) ;;
    *)
        if [ -n "${ZAPRET_PYTHON_BIN:-}" ] &&
           [ "${SCRIPT_DIR}" != /usr/local/opnsense/scripts/OPNsense/Zapret ]; then
            PYTHON_BIN=$(command -v "${PYTHON_BIN}" 2>/dev/null) || PYTHON_BIN=
        else
            PYTHON_BIN=
        fi
        ;;
esac

runtime_error()
{
    echo "ERROR: qualified Python runtime: $*" >&2
    exit 70
}

[ -n "${PYTHON_BIN}" ] && [ -x "${PYTHON_BIN}" ] ||
    runtime_error "interpreter is not executable: ${ZAPRET_PYTHON_BIN:-/usr/local/bin/python3}"

# The source manifest is a test/developer fixture only. Never allow fallback
# on an installed appliance when the installed compatibility policy is missing.
if [ -z "${ZAPRET_PYTHON_POLICY:-}" ] &&
   [ "${SCRIPT_DIR}" != /usr/local/opnsense/scripts/OPNsense/Zapret ] &&
   [ -r "${SCRIPT_DIR}/../../../../../compatibility.json" ]; then
    PYTHON_POLICY="${SCRIPT_DIR}/../../../../../compatibility.json"
fi

[ -r "${PYTHON_POLICY}" ] ||
    runtime_error "installed compatibility policy is unreadable: ${PYTHON_POLICY}"

if [ "${1:-}" != --check ]; then
    [ "$#" -ge 1 ] || runtime_error "missing Python program or module"
    case "$1" in
        -c|-m|-) [ "$#" -ge 2 ] || runtime_error "missing Python -c/-m argument" ;;
        *) [ -r "$1" ] || runtime_error "Python entry point is unreadable: $1" ;;
    esac
fi

# A single process validates schema, exact generic-entrypoint policy and its
# own interpreter branch. Diagnostics stay on stderr; stdout remains suitable
# for JSON/configd consumers. No package or runtime state changes here.
if _python_verification=$("${PYTHON_BIN}" -c '
import json
import sys
try:
    with open(sys.argv[1], encoding="utf-8") as stream:
        policy = json.load(stream)
    if policy.get("schema_version") != 1 or policy.get("target_product") != "OPNsense":
        raise ValueError("invalid OPNsense policy schema")
    branch = f"{sys.version_info.major}.{sys.version_info.minor}"
    entries = policy.get("supported_platforms")
    if not isinstance(entries, list):
        raise ValueError("missing supported platforms")
    candidates = [
        item["python"] for item in entries
        if isinstance(item, dict) and isinstance(item.get("python"), dict)
        and item["python"].get("policy") == "opnsense-PLUGIN_PYTHON"
        and item["python"].get("entrypoint") == "/usr/local/bin/python3"
    ]
    if not candidates:
        raise ValueError("qualified generic Python entrypoint not declared")
    if not any(branch in item.get("supported", []) for item in candidates):
        supported = sorted({version for item in candidates for version in item.get("supported", [])})
        supported_label = ", ".join(supported)
        raise ValueError(f"unsupported interpreter version {branch}; qualified branches: {supported_label}")
except (OSError, ValueError, KeyError, TypeError) as exc:
    print(str(exc), file=sys.stderr)
    sys.exit(70)
print("ZAPRET_RUNTIME_OK")
' "${PYTHON_POLICY}" 2>&1); then
    [ "${_python_verification}" = ZAPRET_RUNTIME_OK ] ||
        runtime_error "interpreter did not validate policy: ${_python_verification}"
else
    runtime_error "${_python_verification}"
fi

[ "${1:-}" = --check ] && exit 0
exec "${PYTHON_BIN}" "$@"
