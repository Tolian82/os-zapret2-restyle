#!/bin/sh

cat > "${MOCK_BIN}/lockf" <<'MOCK'
#!/bin/sh
exit 0
MOCK

cat > "${MOCK_BIN}/daemon" <<'MOCK'
#!/bin/sh
log_file=""
pid_file=""
while [ "$#" -gt 0 ]
do
    case "$1" in
        -f) shift ;;
        -o) log_file="$2"; shift 2 ;;
        -p) pid_file="$2"; shift 2 ;;
        *) break ;;
    esac
done
"$@" >> "${log_file}" 2>&1 &
pid=$!
printf '%s\n' "${pid}" > "${pid_file}"
exit 0
MOCK


cat > "${MOCK_BIN}/curl" <<'MOCK'
#!/bin/sh
url=""
for argument in "$@"
do
    case "${argument}" in
        https://*) url="${argument}" ;;
    esac
done
case "${url}" in
    https://yandex.ru/)
        printf '%s\n' 'exit=0 remote_ip=77.88.55.88 http=1.1 code=200 bytes=100'
        exit 0
        ;;
    https://one.one.one.one/)
        printf '%s\n' 'exit=0 remote_ip=2606:4700:4700::1111 http=1.1 code=200 bytes=100'
        exit 0
        ;;
    *)
        printf '%s\n' 'curl: (28) Connection timed out' >&2
        printf '%s\n' 'exit=28 remote_ip= http=0 code=000 bytes=0'
        exit 28
        ;;
esac
MOCK

cat > "${MOCK_BIN}/drill" <<'MOCK'
#!/bin/sh
host="$1"
type="$2"
printf '%s\n' ';; ANSWER SECTION:'
case "${type}" in
    A) printf '%s. 60 IN A 203.0.113.10\n' "${host}" ;;
    AAAA) printf '%s. 60 IN AAAA 2001:db8::10\n' "${host}" ;;
esac
MOCK

cat > "${MOCK_BIN}/netstat" <<'MOCK'
#!/bin/sh
[ "${MOCK_IPV6_ROUTE:-0}" = 1 ] || exit 0
printf '%s\n' 'default 2001:db8::1 UGS vtnet0'
MOCK

cat > "${MOCK_BIN}/openssl" <<'MOCK'
#!/bin/sh
exit "${MOCK_QUIC_STATUS:-124}"
MOCK

cat > "${MOCK_BIN}/nc" <<'MOCK'
#!/bin/sh
exit "${MOCK_NC_STATUS:-1}"
MOCK

cat > "${MOCK_BIN}/candidate" <<'MOCK'
#!/bin/sh
job_id="$1"
result_file="$3"
epoch_file="${STRATEGY_LAB_JOBS_DIR}/${job_id}/search-epoch.json"
epoch_id=$("${STRATEGY_LAB_JQ}" -er '.epoch_id' "${epoch_file}")
"${STRATEGY_LAB_JQ}" -nc --arg epoch_id "${epoch_id}" '
    {
        id:"mock-candidate",
        strategy:"--lua-desync=multisplit:pos=1",
        endpoints:[],
        all_pass:false,
        search_epoch_id:$epoch_id
    }
' > "${result_file}"
exit 0
MOCK

cat > "${MOCK_BIN}/service" <<'MOCK'
#!/bin/sh
state=$(cat "${MOCK_STATE_FILE}")
case "${1:-}" in
    strategy-lab)
        STRATEGY_LAB_LIFECYCLE_OWNER=1
        STRATEGY_LAB_SERVICE_SCRIPT="$0"
        export STRATEGY_LAB_LIFECYCLE_OWNER STRATEGY_LAB_SERVICE_SCRIPT
        exec "${MOCK_WORKER}" "${2:-}"
        ;;
    strategy-lab-status)
        case "${state}" in
            RUNNING) exit 0 ;;
            STOPPED) exit 1 ;;
            *) exit 2 ;;
        esac
        ;;
    strategy-lab-stop)
        printf '%s\n' stop >> "${MOCK_CALLS_FILE}"
        [ ! -e "${MOCK_STOP_FAIL_FILE}" ] || exit 1
        printf '%s\n' STOPPED > "${MOCK_STATE_FILE}"
        exit 0
        ;;
    strategy-lab-start)
        printf '%s\n' start >> "${MOCK_CALLS_FILE}"
        [ ! -e "${MOCK_START_FAIL_FILE}" ] || exit 1
        printf '%s\n' RUNNING > "${MOCK_STATE_FILE}"
        exit 0
        ;;
    *)
        exit 64
        ;;
esac
MOCK
chmod +x "${MOCK_BIN}/lockf" "${MOCK_BIN}/daemon" "${MOCK_BIN}/service" \
    "${MOCK_BIN}/curl" "${MOCK_BIN}/drill" "${MOCK_BIN}/netstat" \
    "${MOCK_BIN}/openssl" "${MOCK_BIN}/nc" "${MOCK_BIN}/candidate"
