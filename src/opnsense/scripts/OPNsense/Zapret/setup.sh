#!/bin/sh

# zapret2 runtime setup backend for OPNsense/FreeBSD.
# Run explicitly after plugin installation or through the future GUI action.

ZAPRET_DIR="/usr/local/etc/zapret2"
ZAPRET_REPO="https://github.com/bol-van/zapret2.git"
ZAPRET_RELEASES_API="https://api.github.com/repos/bol-van/zapret2/releases?per_page=100"
STATE_DIR="${STATE_DIR:-/var/db/zapret2-restyle}"
SETUP_STATUS="${STATE_DIR}/setup.status"
RUN_DIR="${RUN_DIR:-/var/run/zapret2-restyle}"
LOCK_FILE="${RUN_DIR}/setup.lock"
CONFIGCTL="/usr/local/sbin/configctl"
SERVICE_SCRIPT="/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
FREEBSD_REPO_OVERRIDE="/usr/local/etc/pkg/repos/FreeBSD.conf"
FREEBSD_REPO_BACKUP="${STATE_DIR}/FreeBSD.conf.backup"
FETCH_BIN="${FETCH_BIN:-/usr/bin/fetch}"
PHP_BIN="${PHP_BIN:-/usr/local/bin/php}"
LOCKF_BIN="${LOCKF_BIN:-/usr/bin/lockf}"
ENABLED_FREEBSD_REPO=0

set -eu

usage()
{
    cat <<'USAGE_EOF'
Usage:
  setup.sh
  setup.sh install [VERSION]
  setup.sh show
  setup.sh --help

Commands:
  (no arguments)     Install the latest stable bol-van/zapret2 release.
  install [VERSION]  Install the latest stable release or an exact published
                     version, for example v1.0.3. The same command performs
                     installation, reinstallation, upgrade, or downgrade.
  show               Show the four latest stable releases.
  --help, -h         Show this help.
USAGE_EOF
}

usage_error()
{
    echo "ERROR: $1" >&2
    usage >&2
    return 64
}

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

release_tag_valid()
{
    printf '%s\n' "$1" | grep -Eq '^v[0-9]+(\.[0-9]+)+$'
}

fetch_stable_releases()
{
    _release_json=$(mktemp "${TMPDIR:-/tmp}/zapret2-releases.XXXXXX") || {
        echo "ERROR: could not create a temporary release file" >&2
        return 1
    }
    _release_list=$(mktemp "${TMPDIR:-/tmp}/zapret2-release-list.XXXXXX") || {
        rm -f "${_release_json}"
        echo "ERROR: could not create a temporary release list" >&2
        return 1
    }

    if ! "${FETCH_BIN}" -q -T 30 -o "${_release_json}" \
        --user-agent=os-zapret2-restyle \
        "${ZAPRET_RELEASES_API}"; then
        rm -f "${_release_json}" "${_release_list}"
        echo "ERROR: could not obtain bol-van/zapret2 releases from GitHub" >&2
        return 1
    fi

    if [ ! -x "${PHP_BIN}" ]; then
        rm -f "${_release_json}" "${_release_list}"
        echo "ERROR: OPNsense PHP CLI is unavailable" >&2
        return 1
    fi

    if ! "${PHP_BIN}" -r '
        $releases = json_decode(file_get_contents($argv[1]), true);
        if (!is_array($releases)) {
            exit(2);
        }
        foreach ($releases as $release) {
            if (!is_array($release) || !empty($release["draft"]) || !empty($release["prerelease"])) {
                continue;
            }
            $tag = $release["tag_name"] ?? "";
            if (is_string($tag) && preg_match("/^v[0-9]+(?:\\.[0-9]+)+$/D", $tag)) {
                echo $tag, PHP_EOL;
            }
        }
    ' "${_release_json}" > "${_release_list}"; then
        rm -f "${_release_json}" "${_release_list}"
        echo "ERROR: GitHub returned invalid release data" >&2
        return 1
    fi

    rm -f "${_release_json}"

    if [ ! -s "${_release_list}" ]; then
        rm -f "${_release_list}"
        echo "ERROR: GitHub returned no stable bol-van/zapret2 releases" >&2
        return 1
    fi

    cat "${_release_list}"
    rm -f "${_release_list}"
}

resolve_release()
{
    _requested_ref="${1:-}"

    if ! _stable_releases=$(fetch_stable_releases); then
        return 69
    fi

    if [ -z "${_requested_ref}" ]; then
        _requested_ref=$(printf '%s\n' "${_stable_releases}" | sed -n '1p')
    else
        if ! release_tag_valid "${_requested_ref}"; then
            echo "ERROR: invalid release version: ${_requested_ref}" >&2
            return 64
        fi

        if ! printf '%s\n' "${_stable_releases}" | grep -Fqx "${_requested_ref}"; then
            echo "ERROR: stable bol-van/zapret2 release not found: ${_requested_ref}" >&2
            return 65
        fi
    fi

    printf '%s\n' "${_requested_ref}"
}

show_releases()
{
    if ! _stable_releases=$(fetch_stable_releases); then
        return 69
    fi

    printf '%s\n' "${_stable_releases}" | sed -n '1,4p'
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
            echo "Installed dependency: ${_name}"
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
    _zapret_ref="$1"

    [ -x "${SERVICE_SCRIPT}" ] || {
        status_write "failed"
        echo "ERROR: zapret service control script is unavailable" >&2
        return 1
    }

    if "${SERVICE_SCRIPT}" status >/dev/null 2>&1; then
        _initial_service_status=0
    else
        _initial_service_status=$?
    fi
    case "${_initial_service_status}" in
        0)
            _service_was_running=1
            ;;
        1)
            _service_was_running=0
            ;;
        *)
            status_write "failed"
            echo "ERROR: zapret service is in an incomplete or unknown state" >&2
            return 1
            ;;
    esac

    status_write "installing"
    echo "=== os-zapret2-restyle runtime installation ==="
    echo "Selected bol-van/zapret2 release: ${_zapret_ref}"

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
        echo "Checking out bol-van/zapret2 ${_zapret_ref}..."
        git -C "${ZAPRET_DIR}" fetch --depth 1 origin tag "${_zapret_ref}"
        git -C "${ZAPRET_DIR}" checkout --detach FETCH_HEAD
        git -C "${ZAPRET_DIR}" reset --hard FETCH_HEAD
    else
        echo "Downloading bol-van/zapret2 ${_zapret_ref}..."
        rm -rf "${ZAPRET_DIR}"
        git clone --depth 1 --branch "${_zapret_ref}" "${ZAPRET_REPO}" "${ZAPRET_DIR}"
    fi

    echo "Compiling zapret2 runtime..."
    make -C "${ZAPRET_DIR}" clean >/dev/null 2>&1 || true
    make -C "${ZAPRET_DIR}"

    [ -x "${ZAPRET_DIR}/binaries/my/dvtws2" ] || {
        status_write "failed"
        echo "ERROR: dvtws2 was not produced by the build" >&2
        return 1
    }

    [ -x "${CONFIGCTL}" ] || {
        status_write "failed"
        echo "ERROR: configctl is unavailable; zapret service was not refreshed" >&2
        return 1
    }

    if [ "${_service_was_running}" -eq 1 ]; then
        echo "Refreshing the previously running zapret service..."
        if _service_output=$("${CONFIGCTL}" zapret restart 2>&1); then
            _service_status=0
        else
            _service_status=$?
        fi
        if [ "${_service_status}" -ne 0 ] || [ "${_service_output}" != "OK" ]; then
            status_write "failed"
            printf '%s\n' "${_service_output}" >&2
            echo "ERROR: zapret service refresh failed after runtime installation" >&2
            return 1
        fi

        if ! "${SERVICE_SCRIPT}" status >/dev/null 2>&1; then
            status_write "failed"
            echo "ERROR: zapret service did not return to running state" >&2
            return 1
        fi
        _completion_message="Runtime installation and service refresh completed successfully."
    else
        if "${SERVICE_SCRIPT}" status >/dev/null 2>&1; then
            _service_status=0
        else
            _service_status=$?
        fi
        if [ "${_service_status}" -ne 1 ]; then
            status_write "failed"
            echo "ERROR: zapret service state changed during runtime installation" >&2
            return 1
        fi
        _completion_message="Runtime installation completed successfully; zapret service remains stopped."
    fi

    status_write "ready"
    echo "${_completion_message}"
}

run_locked()
{
    _zapret_ref="$1"
    mkdir -p "${STATE_DIR}" "${RUN_DIR}"
    "${LOCKF_BIN}" -s -t 30 "${LOCK_FILE}" "$0" install-locked "${_zapret_ref}"
}

main()
{
    _mode="${1:-}"

    case "${_mode}" in
        "")
            [ "$#" -eq 0 ] || return 64
            _zapret_ref=$(resolve_release "") || return $?
            run_locked "${_zapret_ref}"
            ;;
        install)
            [ "$#" -le 2 ] || {
                usage_error "install accepts at most one VERSION argument"
                return $?
            }
            _zapret_ref=$(resolve_release "${2:-}") || return $?
            run_locked "${_zapret_ref}"
            ;;
        show)
            [ "$#" -eq 1 ] || {
                usage_error "show accepts no arguments"
                return $?
            }
            show_releases
            ;;
        --help|-h)
            [ "$#" -eq 1 ] || {
                usage_error "help accepts no arguments"
                return $?
            }
            usage
            ;;
        install-locked)
            [ "$#" -eq 2 ] || {
                usage_error "internal install mode requires one VERSION"
                return $?
            }
            release_tag_valid "$2" || {
                echo "ERROR: invalid release version: $2" >&2
                return 64
            }
            mkdir -p "${STATE_DIR}" "${RUN_DIR}"
            install_runtime "$2"
            ;;
        *)
            usage_error "unknown command: ${_mode}"
            return $?
            ;;
    esac
}

main "$@"
