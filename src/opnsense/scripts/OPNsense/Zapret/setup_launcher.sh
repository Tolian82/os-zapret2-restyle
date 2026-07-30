#!/bin/sh

# Launch the package-managed zapret2 setup backend outside the pkg script
# process tree. configd executes this launcher, so pkg may safely finish its
# transaction before setup.sh performs any nested package operations.

SETUP_SCRIPT="/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh"
STATE_DIR="/var/db/zapret2-restyle"
RUN_DIR="/var/run/zapret2-restyle"
LOG_DIR="/var/log/zapret2"
LOG_FILE="${LOG_DIR}/setup.log"
PID_FILE="${RUN_DIR}/setup.pid"
MODE="${1:-install}"

case "${MODE}" in
    install|uninstall)
        ;;
    *)
        echo "ERROR: unsupported setup mode: ${MODE}" >&2
        exit 64
        ;;
esac

[ -x "${SETUP_SCRIPT}" ] || {
    echo "ERROR: setup backend is missing: ${SETUP_SCRIPT}" >&2
    exit 1
}

mkdir -p "${STATE_DIR}" "${RUN_DIR}" "${LOG_DIR}"
rm -f "${PID_FILE}"

_worker="${SETUP_SCRIPT}"
if [ "${MODE}" = "uninstall" ]; then
    _worker="${RUN_DIR}/setup-uninstall.sh"
    cp "${SETUP_SCRIPT}" "${_worker}"
    chmod 700 "${_worker}"
fi

/usr/sbin/daemon -f -o "${LOG_FILE}" -p "${PID_FILE}" \
    "${_worker}" "${MODE}"
