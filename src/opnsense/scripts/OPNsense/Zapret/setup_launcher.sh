#!/bin/sh

# Launch the runtime setup backend outside configd and expose a small read-only
# status adapter for the Zapret2 Service GUI block.

SETUP_SCRIPT="${SETUP_SCRIPT:-/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh}"
SERVICE_SCRIPT="${SERVICE_SCRIPT:-/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh}"
ZAPRET_DIR="${ZAPRET_DIR:-/usr/local/etc/zapret2}"
DAEMON_BIN="${DAEMON_BIN:-/usr/sbin/daemon}"
GIT_BIN="${GIT_BIN:-/usr/local/bin/git}"
STATE_DIR="${STATE_DIR:-/var/db/zapret2-restyle}"
SETUP_STATUS="${SETUP_STATUS:-${STATE_DIR}/setup.status}"
LOG_DIR="${LOG_DIR:-/var/log/zapret2}"
LOG_FILE="${LOG_FILE:-${LOG_DIR}/setup.log}"
RUN_DIR="${RUN_DIR:-/var/run/zapret2-restyle}"
PID_FILE="${PID_FILE:-${RUN_DIR}/setup.pid}"
MODE="${1:-install}"
VERSION="${2:-}"

set -eu

usage_error()
{
    echo "ERROR: $1" >&2
    echo "Usage: setup_launcher.sh {install [VERSION]|status}" >&2
    exit 64
}

release_tag_valid()
{
    printf '%s\n' "$1" | grep -Eq '^v[0-9]+(\.[0-9]+)+$'
}

setup_pid_running()
{
    [ -r "${PID_FILE}" ] || return 1
    _setup_pid=""
    IFS= read -r _setup_pid < "${PID_FILE}" || true
    case "${_setup_pid}" in
        ''|*[!0-9]*)
            return 1
            ;;
    esac
    kill -0 "${_setup_pid}" 2>/dev/null
}

show_status()
{
    _service="error"
    if [ -x "${SERVICE_SCRIPT}" ]; then
        if "${SERVICE_SCRIPT}" status >/dev/null 2>&1; then
            _service="started"
        else
            _service_rc=$?
            if [ "${_service_rc}" -eq 1 ]; then
                _service="stopped"
            fi
        fi
    fi

    _version=""
    if [ -x "${GIT_BIN}" ] && [ -d "${ZAPRET_DIR}/.git" ]; then
        _candidate=$("${GIT_BIN}" -C "${ZAPRET_DIR}" describe --tags --exact-match HEAD 2>/dev/null || true)
        if release_tag_valid "${_candidate}"; then
            _version="${_candidate}"
        fi
    fi

    _setup="unknown"
    if [ -r "${SETUP_STATUS}" ]; then
        IFS= read -r _candidate < "${SETUP_STATUS}" || true
        case "${_candidate}" in
            ready|installing|failed)
                _setup="${_candidate}"
                ;;
        esac
    fi

    _busy=0
    if setup_pid_running; then
        _busy=1
        _setup="installing"
    fi

    printf 'service=%s\n' "${_service}"
    printf 'version=%s\n' "${_version}"
    printf 'setup=%s\n' "${_setup}"
    printf 'busy=%s\n' "${_busy}"
}

launch_install()
{
    [ "$#" -le 2 ] || usage_error "install accepts at most one VERSION argument"

    if [ -n "${VERSION}" ] && ! release_tag_valid "${VERSION}"; then
        usage_error "invalid release version: ${VERSION}"
    fi

    [ -x "${SETUP_SCRIPT}" ] || {
        echo "ERROR: setup backend is missing: ${SETUP_SCRIPT}" >&2
        exit 1
    }

    [ -x "${DAEMON_BIN}" ] || {
        echo "ERROR: daemon launcher is missing: ${DAEMON_BIN}" >&2
        exit 1
    }

    if setup_pid_running; then
        echo "ERROR: a zapret2 runtime operation is already in progress" >&2
        exit 75
    fi

    mkdir -p "${LOG_DIR}" "${RUN_DIR}"
    rm -f "${PID_FILE}"

    if [ -n "${VERSION}" ]; then
        exec "${DAEMON_BIN}" -f -o "${LOG_FILE}" -p "${PID_FILE}" \
            "${SETUP_SCRIPT}" install "${VERSION}"
    fi

    exec "${DAEMON_BIN}" -f -o "${LOG_FILE}" -p "${PID_FILE}" \
        "${SETUP_SCRIPT}" install
}

case "${MODE}" in
    install)
        launch_install "$@"
        ;;
    status)
        [ "$#" -eq 1 ] || usage_error "status accepts no arguments"
        show_status
        ;;
    *)
        usage_error "unsupported setup mode: ${MODE}"
        ;;
esac
