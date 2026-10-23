#!/bin/sh

# Stop the service before pkg removes or replaces the service scripts. A marker
# created by the incoming package's pre-install is preserved even when a forced
# reinstall does not export PKG_UPGRADE. The legacy upgrade marker remains as a
# compatibility fallback for ordinary upgrades from older package revisions.

SERVICE_SCRIPT="${SERVICE_SCRIPT:-/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh}"
UPGRADE_STATE_DIR="${UPGRADE_STATE_DIR:-/var/run/zapret2-restyle}"
UPGRADE_RESTART_MARKER="${UPGRADE_RESTART_MARKER:-${UPGRADE_STATE_DIR}/pkg-upgrade.restart}"
REPLACEMENT_RESTART_MARKER="${REPLACEMENT_RESTART_MARKER:-${UPGRADE_STATE_DIR}/pkg-replacement.restart}"

if [ -x "${SERVICE_SCRIPT}" ]; then
    "${SERVICE_SCRIPT}" status >/dev/null 2>&1
    service_status=$?

    case "${service_status}" in
        0)
            if [ -n "${PKG_UPGRADE:-}" ]; then
                mkdir -p "${UPGRADE_STATE_DIR}" || exit 1
                : > "${UPGRADE_RESTART_MARKER}" || exit 1
            fi
            ;;
        1)
            # Preserve either marker from a preceding incoming pre-install or
            # an interrupted replacement retry.
            ;;
        2)
            rm -f "${UPGRADE_RESTART_MARKER}" "${REPLACEMENT_RESTART_MARKER}"
            ;;
        *)
            echo "ERROR: cannot determine zapret service state before package removal" >&2
            exit 1
            ;;
    esac

    if [ "${service_status}" -ne 1 ]; then
        if ! "${SERVICE_SCRIPT}" stop >/dev/null 2>&1; then
            rm -f "${UPGRADE_RESTART_MARKER}" "${REPLACEMENT_RESTART_MARKER}"
            echo "ERROR: zapret service could not be stopped; package operation aborted" >&2
            exit 1
        fi

        "${SERVICE_SCRIPT}" status >/dev/null 2>&1
        stopped_status=$?
        if [ "${stopped_status}" -ne 1 ]; then
            rm -f "${UPGRADE_RESTART_MARKER}" "${REPLACEMENT_RESTART_MARKER}"
            echo "ERROR: zapret service still owns runtime state; package operation aborted" >&2
            exit 1
        fi
    fi
fi

exit 0
