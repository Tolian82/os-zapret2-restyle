#!/bin/sh

# Launch the runtime setup backend outside configd. This entry point is kept
# for the future GUI maintenance action; package installation does not call it.

SETUP_SCRIPT="/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh"
LOG_DIR="/var/log/zapret2"
LOG_FILE="${LOG_DIR}/setup.log"
RUN_DIR="/var/run/zapret2-restyle"
PID_FILE="${RUN_DIR}/setup.pid"
MODE="${1:-install}"

[ "${MODE}" = "install" ] || {
    echo "ERROR: unsupported setup mode: ${MODE}" >&2
    exit 64
}

[ -x "${SETUP_SCRIPT}" ] || {
    echo "ERROR: setup backend is missing: ${SETUP_SCRIPT}" >&2
    exit 1
}

mkdir -p "${LOG_DIR}" "${RUN_DIR}"
rm -f "${PID_FILE}"

exec /usr/sbin/daemon -f -o "${LOG_FILE}" -p "${PID_FILE}" \
    "${SETUP_SCRIPT}" install
