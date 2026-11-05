#!/bin/sh

# zapret2 runtime setup backend for OPNsense/FreeBSD.
# Run explicitly after plugin installation or through the GUI maintenance action.

ZAPRET_DIR="/usr/local/etc/zapret2"
ZAPRET_REPO="https://github.com/bol-van/zapret2.git"
ZAPRET_RELEASES_API="https://api.github.com/repos/bol-van/zapret2/releases?per_page=100"
STATE_DIR="${STATE_DIR:-/var/db/zapret2-restyle}"
SETUP_STATUS="${STATE_DIR}/setup.status"
RELEASE_CACHE="${RELEASE_CACHE:-${STATE_DIR}/releases.cache}"
RELEASE_CACHE_TTL_MINUTES="${RELEASE_CACHE_TTL_MINUTES:-60}"
RUN_DIR="${RUN_DIR:-/var/run/zapret2-restyle}"
LOCK_FILE="${RUN_DIR}/setup.lock"
RELEASE_LOCK_FILE="${RELEASE_LOCK_FILE:-${RUN_DIR}/releases.lock}"
CONFIGCTL="/usr/local/sbin/configctl"
SERVICE_SCRIPT="/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
FREEBSD_REPO_OVERRIDE="${FREEBSD_REPO_OVERRIDE:-/usr/local/etc/pkg/repos/FreeBSD.conf}"
FREEBSD_REPO_BACKUP="${FREEBSD_REPO_BACKUP:-${STATE_DIR}/FreeBSD.conf.backup}"
FETCH_BIN="${FETCH_BIN:-/usr/bin/fetch}"
PHP_BIN="${PHP_BIN:-/usr/local/bin/php}"
LOCKF_BIN="${LOCKF_BIN:-/usr/bin/lockf}"
FIND_BIN="${FIND_BIN:-/usr/bin/find}"
EXTRA_GUARD="${EXTRA_GUARD:-/usr/local/opnsense/scripts/OPNsense/Zapret/extra_resources_upstream_guard.py}"
EXTRA_PYTHON="${EXTRA_PYTHON:-/usr/local/bin/python3.13}"
ROLLBACK_DIR="${ROLLBACK_DIR:-${STATE_DIR}/runtime-rollback}"

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

finish()
{
    _status="$1"
    trap - EXIT INT TERM HUP

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

release_cache_valid()
{
    [ -s "${RELEASE_CACHE}" ] || return 1

    if grep -Ev '^v[0-9]+(\.[0-9]+)+$' "${RELEASE_CACHE}" | grep -q .; then
        return 1
    fi

    return 0
}

release_cache_fresh()
{
    release_cache_valid || return 1

    case "${RELEASE_CACHE_TTL_MINUTES}" in
        ''|*[!0-9]*)
            return 1
            ;;
    esac

    "${FIND_BIN}" "${RELEASE_CACHE}" -prune -mmin "-${RELEASE_CACHE_TTL_MINUTES}" -print 2>/dev/null | grep -q .
}

refresh_release_cache_locked()
{
    mkdir -p "${STATE_DIR}" "${RUN_DIR}"

    # Another request may have refreshed the cache while this process waited for lockf.
    if release_cache_fresh; then
        return 0
    fi

    _release_json=$(mktemp "${RUN_DIR}/releases.json.XXXXXX") || {
        echo "ERROR: could not create a temporary release file" >&2
        return 1
    }
    _release_list=$(mktemp "${STATE_DIR}/releases.cache.XXXXXX") || {
        rm -f "${_release_json}"
        echo "ERROR: could not create a temporary release cache" >&2
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
        $seen = [];
        foreach ($releases as $release) {
            if (!is_array($release) || !empty($release["draft"]) || !empty($release["prerelease"])) {
                continue;
            }
            $tag = $release["tag_name"] ?? "";
            if (is_string($tag) && preg_match("/^v[0-9]+(?:\\.[0-9]+)+$/D", $tag) && !isset($seen[$tag])) {
                $seen[$tag] = true;
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

    chmod 0644 "${_release_list}"
    mv -f "${_release_list}" "${RELEASE_CACHE}"
    return 0
}

refresh_release_cache()
{
    mkdir -p "${STATE_DIR}" "${RUN_DIR}"
    "${LOCKF_BIN}" -s -t 30 "${RELEASE_LOCK_FILE}" "$0" refresh-releases-locked
}

load_stable_releases()
{
    if release_cache_fresh; then
        cat "${RELEASE_CACHE}"
        return 0
    fi

    if refresh_release_cache; then
        cat "${RELEASE_CACHE}"
        return 0
    fi

    # A validated stale cache is preferable to breaking the GUI on a transient API failure.
    if release_cache_valid; then
        cat "${RELEASE_CACHE}"
        return 0
    fi

    echo "ERROR: no cached stable bol-van/zapret2 releases are available" >&2
    return 69
}

load_cached_releases_for_exact_install()
{
    if release_cache_valid; then
        cat "${RELEASE_CACHE}"
        return 0
    fi

    load_stable_releases
}

resolve_release()
{
    _requested_ref="${1:-}"

    if [ -n "${_requested_ref}" ] && ! release_tag_valid "${_requested_ref}"; then
        echo "ERROR: invalid release version: ${_requested_ref}" >&2
        return 64
    fi

    if [ -n "${_requested_ref}" ]; then
        if ! _stable_releases=$(load_cached_releases_for_exact_install); then
            return 69
        fi

        if ! printf '%s\n' "${_stable_releases}" | grep -Fqx "${_requested_ref}"; then
            echo "ERROR: stable bol-van/zapret2 release not found: ${_requested_ref}" >&2
            return 65
        fi
    else
        if ! _stable_releases=$(load_stable_releases); then
            return 69
        fi
        _requested_ref=$(printf '%s\n' "${_stable_releases}" | sed -n '1p')
    fi

    printf '%s\n' "${_requested_ref}"
}

show_releases()
{
    if ! _stable_releases=$(load_stable_releases); then
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

# Native system dependencies are installed by OPNsense pkg via Makefile
# PLUGIN_DEPENDS. Older setup-side FreeBSD repo edits are not repeated.
verify_stock_freebsd_repository()
{
    if [ -e "${FREEBSD_REPO_BACKUP}" ] || [ -L "${FREEBSD_REPO_BACKUP}" ]; then
        echo "ERROR: legacy FreeBSD repository backup remains at ${FREEBSD_REPO_BACKUP}; inspect it and ${FREEBSD_REPO_OVERRIDE} manually before setup (nothing was modified)" >&2
        return 69
    fi
    if [ -r "${FREEBSD_REPO_OVERRIDE}" ] &&
       grep -v '^[[:space:]]*#' "${FREEBSD_REPO_OVERRIDE}" |
       grep -Eq 'enabled:[[:space:]]*yes([[:space:],}]|$)'; then
        echo "ERROR: stock FreeBSD repository is enabled in ${FREEBSD_REPO_OVERRIDE}; review/disable it manually and use the qualified OPNsense repository (nothing was modified)" >&2
        return 69
    fi
}

verify_native_dependencies()
{
    command -v pkg >/dev/null 2>&1 || {
        echo "ERROR: system pkg command is unavailable; install this plugin through OPNsense firmware/pkg" >&2
        return 69
    }
    # Presence checks only: this script never installs/upgrades system packages.
    for _native_dep in gmake pkgconf luajit git jq ca_root_nss; do
        if ! pkg info -q "${_native_dep}" >/dev/null 2>&1; then
            echo "ERROR: missing OPNsense package ${_native_dep} required by zapret2-restyle PLUGIN_DEPENDS; repair/install through the official OPNsense package repository" >&2
            return 69
        fi
    done
    for _native_tool in gmake pkgconf luajit git jq; do
        if ! command -v "${_native_tool}" >/dev/null 2>&1; then
            echo "ERROR: installed OPNsense dependency ${_native_tool} has no executable in PATH; repair the native plugin dependencies before setup" >&2
            return 69
        fi
    done
}

all_resources_upstream_guard()
{
    [ -x "${EXTRA_PYTHON}" ] && [ -r "${EXTRA_GUARD}" ] || {
        echo "ERROR: upstream resource reconciliation guard is unavailable" >&2
        return 69
    }
    ZAPRET_DIR="${ZAPRET_DIR}" STATE_DIR="${STATE_DIR}" ROLLBACK_DIR="${ROLLBACK_DIR}" \
        GIT_BIN="$(command -v git)" "${EXTRA_PYTHON}" "${EXTRA_GUARD}" "$@"
}

extra_resources_upstream_guard()
{
    [ -f "${STATE_DIR}/extra-resources/installed.json" ] ||
        [ -L "${STATE_DIR}/extra-resources/installed.json" ] || return 0
    [ -x "${EXTRA_PYTHON}" ] && [ -r "${EXTRA_GUARD}" ] || {
        echo "ERROR: additional resource preservation guard is unavailable" >&2
        return 69
    }
    ZAPRET_DIR="${ZAPRET_DIR}" STATE_DIR="${STATE_DIR}" GIT_BIN="$(command -v git)" \
        "${EXTRA_PYTHON}" "${EXTRA_GUARD}" "$@"
}

install_runtime()
{
    _zapret_ref="$1"

    # Preflight before any status write, runtime checkout or service mutation.
    wait_for_outer_pkg || return $?
    verify_stock_freebsd_repository || return $?
    verify_native_dependencies || return $?

    [ -x "${SERVICE_SCRIPT}" ] || {
        status_write "failed"
        echo "ERROR: zapret service control script is unavailable" >&2
        return 1
    }

    # The parent holds original FD9; a normal 'status' would try to acquire
    # that same lock recursively. Inspect through the inherited-FD9 path.
    _setup_status_mode=status
    if [ "${UPSTREAM_RUNTIME_LIFECYCLE_OWNER:-0}" = 1 ]; then
        _setup_status_mode=strategy-lab-status
    fi
    if "${SERVICE_SCRIPT}" "${_setup_status_mode}" >/dev/null 2>&1; then
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

    trap 'finish $?' EXIT
    trap 'finish 130' INT
    trap 'finish 143' TERM
    trap 'finish 129' HUP

    if [ -d "${ZAPRET_DIR}/.git" ]; then
        echo "Checking out bol-van/zapret2 ${_zapret_ref}..."
        git -C "${ZAPRET_DIR}" fetch --depth 1 origin tag "${_zapret_ref}"
        _target_sha=$(git -C "${ZAPRET_DIR}" rev-parse --verify "FETCH_HEAD^{commit}") || return 69
        printf '%s\n' "${_target_sha}" | grep -Eq '^[0-9a-f]{40}$' || return 69
        if [ "${SETUP_TRANSACTION_LOCK_OWNER:-0}" = 1 ]; then
            # Target identity must be durable before Lua/BIN pruning or Git checkout.
            all_resources_upstream_guard bind-target "${_zapret_ref}" "${_target_sha}" || {
                status_write "failed"
                return 1
            }
        fi
        extra_resources_upstream_guard preflight "${_target_sha}" || {
            status_write "failed"
            return 1
        }
        if [ "${SETUP_TRANSACTION_LOCK_OWNER:-0}" = 1 ]; then
            # Only the wrapper arms a durable mutating checkpoint and seals
            # the original non-Git bytes. All pruning is restricted to it.
            all_resources_upstream_guard preflight-switch "${_target_sha}" || {
                status_write "failed"
                return 1
            }
            all_resources_upstream_guard prune-orphans "${_target_sha}" || {
                status_write "failed"
                return 1
            }
        else
            # Preserve direct setup.sh compatibility on *already exact*
            # runtimes. Direct use cannot prune orphans without rollback.
            echo "Direct setup: verifying exact resources; cleanup requires the transaction wrapper."
        fi
        all_resources_upstream_guard preflight-exact "${_target_sha}" || {
            status_write "failed"
            return 1
        }
        git -C "${ZAPRET_DIR}" checkout --detach "${_target_sha}"
        git -C "${ZAPRET_DIR}" reset --hard "${_target_sha}"
    else
        echo "Downloading bol-van/zapret2 ${_zapret_ref}..."
        [ ! -e "${STATE_DIR}/extra-resources/installed.json" ] &&
        [ ! -L "${STATE_DIR}/extra-resources/installed.json" ] || {
            echo "ERROR: installed extra resources require the existing tracked runtime" >&2
            status_write "failed"
            return 1
        }
        rm -rf "${ZAPRET_DIR}"
        git clone --depth 1 --branch "${_zapret_ref}" "${ZAPRET_REPO}" "${ZAPRET_DIR}"
    fi

    echo "Compiling zapret2 runtime..."
    make -C "${ZAPRET_DIR}" clean >/dev/null 2>&1 || true
    make -C "${ZAPRET_DIR}"

    extra_resources_upstream_guard verify || {
        status_write "failed"
        echo "ERROR: managed Additional Resources changed during upstream setup" >&2
        return 1
    }
    all_resources_upstream_guard verify-exact || {
        status_write "failed"
        echo "ERROR: installed upstream/extras set diverged after checkout" >&2
        return 1
    }

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

    if [ "${UPSTREAM_RUNTIME_LIFECYCLE_OWNER:-0}" = 1 ] &&
       [ "${_service_was_running}" -ne 0 ]; then
        echo "ERROR: upstream build requires an already STOPPED native owner" >&2
        status_write "failed"
        return 75
    fi

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
        if "${SERVICE_SCRIPT}" "${_setup_status_mode}" >/dev/null 2>&1; then
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

extra_resources_require_transaction()
{
    # Direct setup.sh must not bypass setup_transaction.sh's managed-resource
    # snapshot/rollback. The internal parent-locked mode is used by that wrapper.
    if [ -e "${STATE_DIR}/extra-resources/installed.json" ] ||
       [ -L "${STATE_DIR}/extra-resources/installed.json" ]; then
        echo "ERROR: installed extra resources require setup_transaction.sh; direct setup.sh installation is unsafe" >&2
        return 75
    fi
}

run_locked()
{
    extra_resources_require_transaction || return $?
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
        refresh-releases-locked)
            [ "$#" -eq 1 ] || return 64
            refresh_release_cache_locked
            ;;
        install-under-parent-lock)
            [ "${SETUP_TRANSACTION_LOCK_OWNER:-0}" = 1 ] &&
            [ "${UPSTREAM_RUNTIME_LIFECYCLE_OWNER:-0}" = 1 ] &&
            [ "${STRATEGY_LAB_LIFECYCLE_OWNER:-0}" = 1 ] &&
            ( : >&9 ) 2>/dev/null || {
                echo "ERROR: missing setup transaction lock owner" >&2
                return 75
            }
            [ "$#" -le 2 ] || return 64
            _zapret_ref=$(resolve_release "${2:-}") || return $?
            install_runtime "${_zapret_ref}"
            ;;
        install-locked)
            extra_resources_require_transaction || return $?
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
