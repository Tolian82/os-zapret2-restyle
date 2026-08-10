#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
ADAPTER="${SCRIPT_DIR}/strategy_lab_model_b_adapter.sh"

fail(){ echo "FAIL: $*" >&2; exit 1; }

TMP=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-model-b-preflight.XXXXXX")
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
BIN="${TMP}/bin"
mkdir -p "${BIN}" "${TMP}/session"

cat > "${BIN}/kldstat" <<'EOF'
#!/bin/sh
exit 0
EOF

cat > "${BIN}/sysctl" <<'EOF'
#!/bin/sh
printf '%s\n' 1
EOF

cat > "${BIN}/ipfw" <<'EOF'
#!/bin/sh
case "${1:-}" in
    list)
        if [ -n "${MODEL_B_TEST_BUSY_RULE:-}" ] && [ "${2:-}" = "${MODEL_B_TEST_BUSY_RULE}" ]; then
            printf '%s allow ip from any to any\n' "${2}"
            exit 0
        fi
        exit 1
        ;;
esac
exit 0
EOF

cat > "${BIN}/sockstat" <<'EOF'
#!/bin/sh
if [ -n "${MODEL_B_TEST_BUSY_PORT:-}" ]; then
    printf 'nobody dvtws2 123 7 udp4 *:%s *:*\n' "${MODEL_B_TEST_BUSY_PORT}"
fi
exit 0
EOF

cat > "${BIN}/netstat" <<'EOF'
#!/bin/sh
exit 0
EOF

cat > "${BIN}/ps" <<'EOF'
#!/bin/sh
exit 0
EOF

chmod +x "${BIN}/kldstat" "${BIN}/sysctl" "${BIN}/ipfw" \
    "${BIN}/sockstat" "${BIN}/netstat" "${BIN}/ps"

run_preflight()
{
    env \
        SCRIPT_DIR="${SCRIPT_DIR}" \
        MODULE_DIR="${SCRIPT_DIR}/strategy_lab" \
        STRATEGY_LAB_MODEL_B_SESSION_DIR="${TMP}/session" \
        STRATEGY_LAB_MODEL_B_IPFW_BIN="${BIN}/ipfw" \
        STRATEGY_LAB_MODEL_B_KLDSTAT_BIN="${BIN}/kldstat" \
        STRATEGY_LAB_MODEL_B_SYSCTL_BIN="${BIN}/sysctl" \
        STRATEGY_LAB_MODEL_B_SOCKSTAT_BIN="${BIN}/sockstat" \
        STRATEGY_LAB_MODEL_B_NETSTAT_BIN="${BIN}/netstat" \
        STRATEGY_LAB_DVTWS_BIN=/bin/true \
        STRATEGY_LAB_DAEMON_BIN=/bin/true \
        STRATEGY_LAB_PS_BIN="${BIN}/ps" \
        MODEL_B_TEST_BUSY_RULE="${MODEL_B_TEST_BUSY_RULE:-}" \
        MODEL_B_TEST_BUSY_PORT="${MODEL_B_TEST_BUSY_PORT:-}" \
        sh "${ADAPTER}" preflight
}

unset MODEL_B_TEST_BUSY_RULE MODEL_B_TEST_BUSY_PORT || true
run_preflight || fail 'clean dedicated rules/ports must pass Model B preflight'

MODEL_B_TEST_BUSY_RULE=19129
export MODEL_B_TEST_BUSY_RULE
if run_preflight; then
    fail 'occupied dedicated rule must fail Model B preflight'
fi
unset MODEL_B_TEST_BUSY_RULE

MODEL_B_TEST_BUSY_PORT=9991
export MODEL_B_TEST_BUSY_PORT
if run_preflight; then
    fail 'occupied dedicated port must fail Model B preflight'
fi
unset MODEL_B_TEST_BUSY_PORT

sh -n "${ADAPTER}"
echo 'PASS: Model B preflight returns success when all dedicated rules/ports are free and rejects real conflicts'
