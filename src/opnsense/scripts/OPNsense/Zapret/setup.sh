#!/bin/sh

# Package-managed zapret2 runtime bootstrap for OPNsense/FreeBSD.
# This is an internal lifecycle backend. Users must not run it manually.

ZAPRET_DIR="/usr/local/etc/zapret2"
ZAPRET_REPO="https://github.com/bol-van/zapret2.git"
STATE_DIR="/var/db/zapret2-restyle"
MANAGED_PACKAGES="${STATE_DIR}/managed-packages"
SETUP_STATUS="${STATE_DIR}/setup.status"
RUN_DIR="/var/run/zapret2-restyle"
LOCK_FILE="${RUN_DIR}/setup.lock"
PACKAGE_NAME="os-zapret2-restyle"
FREEBSD_REPO_OVERRIDE="/usr/local/etc/pkg/repos/FreeBSD.conf"
FREEBSD_REPO_BACKUP="${STATE_DIR}/FreeBSD.conf.backup"
ENABLED_FREEBSD_REPO=0
MODE="${1:-install}"

set -eu

mkdir -p "${STATE_DIR}" "${RUN_DIR}"

status_write()
{
    printf '%s\n' "$1" > "${SETUP_STATUS}"
}

restore_freebsd_repo()
{
    if [ "${ENABLED_FREEBSD_REPO}" = "1" ] && [ -f "${FREEBSD_REPO_BACKUP}" ]; then
        cp "${FREEBSD_REPO_BACKUP}" "${FREEBSD_REPO_OVERRIDE}"
        rm -f "${FREEBSD_REPO_BACKUP}"
        ENABLED_FREEBSD_REPO=0
        echo "Restored FreeBSD pkg repository configuration."
    fi
}

finish()
{
    _status="$1"
    trap - EXIT INT TERM HUP

    restore_freebsd_repo || true

    if [ "${_status}" -ne 0 ] && [ -f "${SETUP_STATUS}" ]; then
        _phase=""
        IFS= read -r _phase < "${SETUP_STATUS}" || true

        case "${_phase}" in
            installing|removing)
                status_write "failed" || true
                ;;
        esac
    fi

    exit "${_status}"
}

wait_for_outer_pkg()
{
    _waited=0
    while pgrep -f '(^|/)(pkg|pkg-static)([[:space:]]|$)' >/dev/null 2>&1; do
        if [ "${_waited}" -ge 300 ]; then
            echo "ERROR: timed out waiting for the outer pkg transaction" >&2
            return 1
        fi
        sleep 1
        _waited=$((_waited + 1))
    done

    # The pkg process may disappear slightly before its database lock and
    # repository state are fully released.
    sleep 3
}

record_managed_package()
{
    _package="$1"
    touch "${MANAGED_PACKAGES}"
    grep -qx "${_package}" "${MANAGED_PACKAGES}" 2>/dev/null ||
        printf '%s\n' "${_package}" >> "${MANAGED_PACKAGES}"
}

install_dep()
{
    for _name in "$@"; do
        if pkg info -q "${_name}"; then
            echo "Dependency already installed: ${_name}"
            return 0
        fi
    done

    for _name in "$@"; do
        if pkg install -y "${_name}"; then
            record_managed_package "${_name}"
            echo "Installed managed dependency: ${_name}"
            return 0
        fi
    done

    echo "ERROR: could not install dependency (tried: $*)" >&2
    return 1
}

enable_freebsd_repo_temporarily()
{
    if [ -f "${FREEBSD_REPO_BACKUP}" ]; then
        echo "Restoring repository configuration left by an interrupted setup."
        cp "${FREEBSD_REPO_BACKUP}" "${FREEBSD_REPO_OVERRIDE}"
        rm -f "${FREEBSD_REPO_BACKUP}"
    fi

    if [ -f "${FREEBSD_REPO_OVERRIDE}" ] &&
        grep -q 'enabled:[[:space:]]*no' "${FREEBSD_REPO_OVERRIDE}"; then
        cp "${FREEBSD_REPO_OVERRIDE}" "${FREEBSD_REPO_BACKUP}"
        ENABLED_FREEBSD_REPO=1
        cat > "${FREEBSD_REPO_OVERRIDE}" <<'REPO_EOF'
FreeBSD-ports: { enabled: yes }
REPO_EOF
        echo "Temporarily enabled the FreeBSD package repository."
    fi
}

install_runtime()
{
    status_write "installing"
    echo "=== os-zapret2-restyle runtime installation ==="

    wait_for_outer_pkg
    enable_freebsd_repo_temporarily
    trap 'finish $?' EXIT
    trap 'finish 130' INT
    trap 'finish 143' TERM
    trap 'finish 129' HUP

    pkg update -q
    install_dep pkgconf
    install_dep luajit
    install_dep git-lite git
    install_dep jq

    restore_freebsd_repo

    if [ -d "${ZAPRET_DIR}/.git" ]; then
        echo "Updating existing bol-van/zapret runtime tree..."
        git -C "${ZAPRET_DIR}" pull --ff-only
    else
        echo "Downloading bol-van/zapret runtime tree..."
        rm -rf "${ZAPRET_DIR}"
        git clone --depth 1 "${ZAPRET_REPO}" "${ZAPRET_DIR}"
    fi

    echo "Compiling zapret2 runtime..."
    make -C "${ZAPRET_DIR}" clean >/dev/null 2>&1 || true
    make -C "${ZAPRET_DIR}"

    [ -x "${ZAPRET_DIR}/binaries/my/dvtws2" ] || {
        status_write "failed"
        echo "ERROR: dvtws2 was not produced by the build" >&2
        return 1
    }

    status_write "ready"
    echo "Runtime installation completed successfully."
}

remove_managed_packages()
{
    [ -s "${MANAGED_PACKAGES}" ] || return 0

    _remaining="${MANAGED_PACKAGES}.remaining"
    : > "${_remaining}"

    while IFS= read -r _package; do
        [ -n "${_package}" ] || continue
        if ! pkg info -q "${_package}"; then
            continue
        fi
        if pkg delete -y "${_package}"; then
            echo "Removed managed dependency: ${_package}"
        else
            echo "Keeping dependency still required by another package: ${_package}"
            printf '%s\n' "${_package}" >> "${_remaining}"
        fi
    done < "${MANAGED_PACKAGES}"

    if [ -s "${_remaining}" ]; then
        mv "${_remaining}" "${MANAGED_PACKAGES}"
    else
        rm -f "${_remaining}" "${MANAGED_PACKAGES}"
    fi
}

uninstall_runtime()
{
    status_write "removing"
    echo "=== os-zapret2-restyle runtime removal ==="

    while pkg info -q "${PACKAGE_NAME}" >/dev/null 2>&1; do
        sleep 1
    done
    wait_for_outer_pkg

    if pkg info -q "${PACKAGE_NAME}" >/dev/null 2>&1; then
        echo "Package is installed again; destructive uninstall cleanup was cancelled."
        return 0
    fi

    rm -rf "${ZAPRET_DIR}"
    rm -rf /var/log/zapret2
    rm -f /var/run/dvtws2.pid
    rm -f /var/run/zapret2-supervisor-daemon.pid
    rm -f /var/run/zapret2-supervisor-monitor.pid
    rm -f /var/run/zapret2-execution.status
    rm -f /var/run/zapret2-lifecycle.lock

    remove_managed_packages

    if [ -x /usr/local/etc/rc.configure_plugins ]; then
        /usr/local/etc/rc.configure_plugins zapret2 >/dev/null 2>&1 || true
    fi
    if [ -x /usr/local/etc/rc.d/configd ]; then
        /usr/local/etc/rc.d/configd restart >/dev/null 2>&1 || true
    fi

    rm -rf "${RUN_DIR}"
    rm -rf "${STATE_DIR}"
    echo "Runtime removal completed successfully."
}

run_locked()
{
    /usr/bin/lockf -s -t 30 "${LOCK_FILE}" "$0" "${MODE}-locked"
}

case "${MODE}" in
    install)
        run_locked
        ;;
    install-locked)
        install_runtime
        ;;
    uninstall)
        run_locked
        ;;
    uninstall-locked)
        uninstall_runtime
        ;;
    *)
        echo "usage: setup.sh {install|uninstall}" >&2
        exit 64
        ;;
esac
