#!/bin/sh
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "${SCRIPT_DIR}/strategy_lab_cancellable_runner.sh" "${SCRIPT_DIR}/strategy_lab_quic_runner.sh" "$@"
