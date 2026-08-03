#!/bin/sh

# Transactional wrapper around setup.sh install. It keeps the previous upstream
# checkout, compiled binaries, active release marker, and complete service state
# available until the selected release has been built and activated successfully.

SETUP_SCRIPT="${SETUP_SCRIPT:-/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh}"
SERVICE_SCRIPT="${SERVICE_SCRIPT:-/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh}"
CONFIGCTL="${CONFIGCTL:-/usr/local/sbin/configctl}"
GIT_BIN="${GIT_BIN:-/usr/local/bin/git}"
FIND_BIN="${FIND_BIN:-/usr/bin/find}"
ZAPRET_DIR="${ZAPRET_DIR:-/usr/local/etc/zapret2}"
STATE_DIR="${STATE_DIR:-/var/db/zapret2-restyle}"
SETUP_STATUS="${SETUP_STATUS:-${STATE_DIR}/setup.status}"
ACTIVE_RELEASE_FILE="${ACTIVE_RELEASE_FILE:-${STATE_DIR}/runtime.release}"
ROLLBACK_DIR="${ROLLBACK_DIR:-${STATE_DIR}/runtime-rollback}"
MODE="${1:-install}"
VERSION="${2:-}"

set -eu
umask 022

release_tag_valid()
{
    printf '%s\n' "$1" | grep -Eq '^v[0-9]+(\.[0-9]+)+$'
}

status_write()
{
    mkdir -p "${STATE_DIR}"
    printf '%s\n' "$1" > "${SETUP_STATUS}"
}

write_active_release()
{
    _release="$1"
    release_tag_valid "${_release}" || return 1

    mkdir -p "${STATE_DIR}"
    _temporary=$(mktemp "${STATE_DIR}/runtime.release.XXXXXX") || return 1
    printf '%s\n' "${_release}" > "${_temporary}"
    chmod 0644 "${_temporary}"
    mv -f "${_temporary}" "${ACTIVE_RELEASE_FILE}"
}

read_active_release()
{
    _release=""
    if [ -r "${ACTIVE_RELEASE_FILE}" ]; then
        IFS= read -r _release < "${ACTIVE_RELEASE_FILE}" || true
        if release_tag_valid "${_release}"; then
            printf '%s\n' "${_release}"
            return 0
        fi
    fi

    if [ -x "${GIT_BIN}" ] && [ -d "${ZAPRET_DIR}/.git" ]; then
        _release=$("${GIT_BIN}" -C "${ZAPRET_DIR}" describe --tags --exact-match HEAD 2>/dev/null || true)
        if release_tag_valid "${_release}"; then
            printf '%s\n' "${_release}"
            return 0
        fi
    fi

    return 1
}

normalize_runtime_permissions()
{
    [ -d "${ZAPRET_DIR}" ] || return 1

    if [ -d "${ZAPRET_DIR}/lua" ]; then
        "${FIND_BIN}" "${ZAPRET_DIR}/lua" -type d -exec chmod 0755 {} +
        "${FIND_BIN}" "${ZAPRET_DIR}/lua" -type f -exec chmod 0644 {} +
    fi

    if [ -d "${ZAPRET_DIR}/files" ]; then
        "${FIND_BIN}" "${ZAPRET_DIR}/files" -type d -exec chmod 0755 {} +
        "${FIND_BIN}" "${ZAPRET_DIR}/files" -type f -exec chmod 0644 {} +
    fi

    if [ -d "${ZAPRET_DIR}/binaries/my" ]; then
        "${FIND_BIN}" "${ZAPRET_DIR}/binaries/my" -type d -exec chmod 0755 {} +
        "${FIND_BIN}" "${ZAPRET_DIR}/binaries/my" -type f -exec chmod 0755 {} +
    fi

    return 0
}

service_state()
{
    if "${SERVICE_SCRIPT}" status >/dev/null 2>&1; then
        return 0
    fi
    return $?
}

configctl_exact_ok()
{
    _output=$("${CONFIGCTL}" "$@" 2>&1) || {
        printf '%s\n' "${_output}" >&2
        return 1
    }

    if [ "${_output}" != "OK" ]; then
        printf '%s\n' "${_output}" >&2
        return 1
    fi

    return 0
}

prepare_rollback()
{
    PREVIOUS_COMMIT=""
    PREVIOUS_RELEASE=""
    PREVIOUS_BINARIES=0

    if _release=$(read_active_release); then
        PREVIOUS_RELEASE="${_release}"
        if [ ! -r "${ACTIVE_RELEASE_FILE}" ]; then
            write_active_release "${PREVIOUS_RELEASE}" || return 1
        fi
    fi

    if [ -x "${GIT_BIN}" ] && [ -d "${ZAPRET_DIR}/.git" ]; then
        PREVIOUS_COMMIT=$("${GIT_BIN}" -C "${ZAPRET_DIR}" rev-parse --verify HEAD 2>/dev/null || true)
    fi

    rm -rf "${ROLLBACK_DIR}"
    mkdir -p "${ROLLBACK_DIR}"

    if [ -d "${ZAPRET_DIR}/binaries/my" ]; then
        mkdir -p "${ROLLBACK_DIR}/binaries"
        cp -Rp "${ZAPRET_DIR}/binaries/my" "${ROLLBACK_DIR}/binaries/"
        PREVIOUS_BINARIES=1
    fi

    return 0
}

restore_previous_checkout()
{
    [ -n "${PREVIOUS_COMMIT}" ] || return 1
    [ -x "${GIT_BIN}" ] || return 1
    [ -d "${ZAPRET_DIR}/.git" ] || return 1

    "${GIT_BIN}" -C "${ZAPRET_DIR}" checkout --detach "${PREVIOUS_COMMIT}" >/dev/null 2>&1 || return 1
    "${GIT_BIN}" -C "${ZAPRET_DIR}" reset --hard "${PREVIOUS_COMMIT}" >/dev/null 2>&1 || return 1

    if [ "${PREVIOUS_BINARIES}" -eq 1 ] && [ -d "${ROLLBACK_DIR}/binaries/my" ]; then
        rm -rf "${ZAPRET_DIR}/binaries/my"
        mkdir -p "${ZAPRET_DIR}/binaries"
        cp -Rp "${ROLLBACK_DIR}/binaries/my" "${ZAPRET_DIR}/binaries/"
    fi

    normalize_runtime_permissions || return 1
    return 0
}

restore_previous_service_state()
{
    if service_state; then
        _current_state=0
    else
        _current_state=$?
    fi

    case "${_current_state}" in
        0|2)
            "${SERVICE_SCRIPT}" stop >/dev/null 2>&1 || return 1
            ;;
        1)
            ;;
        *)
            return 1
            ;;
    esac

    if [ "${SERVICE_WAS_RUNNING}" -eq 1 ]; then
        configctl_exact_ok zapret start || return 1
        service_state || return 1
    else
        if service_state; then
            return 1
        fi
        [ "$?" -eq 1 ] || return 1
    fi

    return 0
}

rollback_runtime()
{
    echo "Restoring the previously active bol-van/zapret2 runtime..."

    if ! restore_previous_checkout; then
        echo "ERROR: previous bol-van/zapret2 checkout could not be restored" >&2
        return 1
    fi

    if [ -n "${PREVIOUS_RELEASE}" ]; then
        write_active_release "${PREVIOUS_RELEASE}" || {
            echo "ERROR: previous active release marker could not be restored" >&2
            return 1
        }
    fi

    if ! restore_previous_service_state; then
        echo "ERROR: previous zapret service state could not be restored" >&2
        return 1
    fi

    status_write "failed"
    echo "Previous bol-van/zapret2 runtime and service state restored."
    return 0
}

install_transaction()
{
    [ -x "${SETUP_SCRIPT}" ] || {
        echo "ERROR: setup backend is unavailable: ${SETUP_SCRIPT}" >&2
        return 1
    }
    [ -x "${SERVICE_SCRIPT}" ] || {
        echo "ERROR: zapret service control is unavailable: ${SERVICE_SCRIPT}" >&2
        return 1
    }
    [ -x "${CONFIGCTL}" ] || {
        echo "ERROR: configctl is unavailable: ${CONFIGCTL}" >&2
        return 1
    }

    if service_state; then
        SERVICE_WAS_RUNNING=1
    else
        _initial_state=$?
        case "${_initial_state}" in
            1)
                SERVICE_WAS_RUNNING=0
                ;;
            *)
                echo "ERROR: zapret service is in an incomplete or unknown state" >&2
                return 1
                ;;
        esac
    fi

    prepare_rollback || {
        echo "ERROR: rollback state could not be prepared" >&2
        return 1
    }

    if [ -n "${VERSION}" ]; then
        if "${SETUP_SCRIPT}" install "${VERSION}"; then
            _setup_result=0
        else
            _setup_result=$?
        fi
    else
        if "${SETUP_SCRIPT}" install; then
            _setup_result=0
        else
            _setup_result=$?
        fi
    fi

    if [ "${_setup_result}" -eq 0 ]; then
        normalize_runtime_permissions || {
            status_write "failed"
            echo "ERROR: installed runtime permissions could not be normalized" >&2
            rollback_runtime || true
            return 1
        }

        _installed_release=$("${GIT_BIN}" -C "${ZAPRET_DIR}" describe --tags --exact-match HEAD 2>/dev/null || true)
        if ! release_tag_valid "${_installed_release}"; then
            status_write "failed"
            echo "ERROR: installed runtime does not resolve to a stable release tag" >&2
            rollback_runtime || true
            return 1
        fi

        write_active_release "${_installed_release}" || {
            status_write "failed"
            echo "ERROR: active runtime release marker could not be written" >&2
            rollback_runtime || true
            return 1
        }

        rm -rf "${ROLLBACK_DIR}"
        return 0
    fi

    if rollback_runtime; then
        return "${_setup_result}"
    fi

    status_write "failed"
    echo "ERROR: selected runtime failed and automatic rollback was unsuccessful" >&2
    return 1
}

case "${MODE}" in
    install)
        [ "$#" -le 2 ] || {
            echo "usage: setup_transaction.sh install [VERSION]" >&2
            exit 64
        }
        if [ -n "${VERSION}" ] && ! release_tag_valid "${VERSION}"; then
            echo "ERROR: invalid release version: ${VERSION}" >&2
            exit 64
        fi
        install_transaction
        ;;
    *)
        echo "usage: setup_transaction.sh install [VERSION]" >&2
        exit 64
        ;;
esac
