#!/bin/sh
# Telegram Voice independent laboratory: explicit A1/A2 one-shot Docker oracle.
# No plugin source edits, PFIL changes, Cron, second divert listener or real calls.
set -u
umask 077
PATH=/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/sbin:/usr/local/bin
export PATH

BASE=/root/tgvoice-lab
RESULTS="$BASE/results"
ROUTE_FIX="$BASE/ensure-tnas-routes.sh"
KEY=/root/.ssh/id_ed25519_tgvoice_lab
SSH=/usr/local/bin/ssh
DOCKER=/Volume1/@apps/DockerEngine/dockerd/bin/docker
BIN_SHA=7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc
ACTIVE=/usr/local/etc/zapret2/runtime-v2
TARGET=91.108.13.10
LOCK="$BASE/.a1-run.lock"
# Explicit A2 opt-in; historic default remains A1.
CANDIDATE=${TGVOICE_CANDIDATE:-A1}
case "$CANDIDATE" in
    A1)
        FAKE_LINE="--lua-desync=fake:payload=unknown:blob=0x00000000000000000000000000000000:badsum:repeats=2"
        OTHER_FAKE="--lua-desync=fake:payload=unknown:blob=0x00000000000000000000000000000000:repeats=2"
        PREFIX=a1
        ;;
    A2)
        FAKE_LINE="--lua-desync=fake:payload=unknown:blob=0x00000000000000000000000000000000:repeats=2"
        OTHER_FAKE="--lua-desync=fake:payload=unknown:blob=0x00000000000000000000000000000000:badsum:repeats=2"
        PREFIX=a2
        ;;
    *) echo "ERROR: unsupported TGVOICE_CANDIDATE (A1 or A2 only)" >&2; exit 2 ;;
esac
TGVOICE_CANDIDATE=$CANDIDATE
export TGVOICE_CANDIDATE

if [ "$(id -u)" != 0 ]; then
    echo 'ERROR: run this script as root on OPNsense' >&2
    exit 2
fi
mkdir -p "$RESULTS" || exit 2
if ! mkdir "$LOCK" 2>/dev/null; then
    echo "ERROR: A1 lock exists ($LOCK). Check for an active run before removing a stale lock." >&2
    exit 2
fi
RUN=$(mktemp -d "$RESULTS/$PREFIX-$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX") || {
    rmdir "$LOCK"
    exit 2
}
NAME=${RUN##*/}
ARCHIVE="$RESULTS/$NAME.tgz"
LAN_PID=
WAN_PID=
SSH_PID=
STARTED_CONTAINER=0
RESULT=PRECHECK_FAILED
exec 3>&1
exec >> "$RUN/driver.log" 2>&1

log() {
    line="[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"
    printf '%s\n' "$line"
    printf '%s\n' "$line" >&3
}
ssh_tnas() {
    "$SSH" -T -p 9222 -i "$KEY" \
        -o IdentitiesOnly=yes -o BatchMode=yes \
        -o StrictHostKeyChecking=yes -o ConnectTimeout=7 \
        -o ServerAliveInterval=5 -o ServerAliveCountMax=2 \
        tolian@192.168.1.100 /bin/sh -s
}
stop_capture() {
    cap_pid=$1
    if [ -n "$cap_pid" ] && kill -0 "$cap_pid" 2>/dev/null; then
        kill -INT "$cap_pid" 2>/dev/null || :
        wait "$cap_pid" 2>/dev/null || :
    fi
}
snapshot_after() {
    date -u +%Y-%m-%dT%H:%M:%SZ > "$RUN/after-utc.txt" 2>&1 || :
    configctl zapret telegram_voice_status > "$RUN/voice-after.txt" 2>&1 || :
    ipfw -a list > "$RUN/ipfw-after.txt" 2>&1 || :
    pfilctl heads > "$RUN/pfil-after.txt" 2>&1 || :
}
finish() {
    outcome=$1
    trap - 0 1 2 3 15
    if [ -n "$SSH_PID" ] && kill -0 "$SSH_PID" 2>/dev/null; then
        echo 'WARN: interrupting unfinished remote Docker command'
        kill -TERM "$SSH_PID" 2>/dev/null || :
        wait "$SSH_PID" 2>/dev/null || :
    fi
    stop_capture "$LAN_PID"
    stop_capture "$WAN_PID"
    LAN_PID=
    WAN_PID=
    snapshot_after
    if [ "$STARTED_CONTAINER" -eq 1 ]; then
        log 'Restoring initially stopped Docker container...'
        if ! ssh_tnas > "$RUN/docker-restore.log" 2>&1 <<'REMOTE_STOP'
DOCKER=/Volume1/@apps/DockerEngine/dockerd/bin/docker
"$DOCKER" stop tgvoice-lab
REMOTE_STOP
        then
            echo 'WARN: could not restore initially stopped Docker container; see docker-restore.log' >> "$RUN/driver.log"
            RESULT=RESTORE_WARNING
            outcome=2
        fi
    fi
    printf 'result=%s\nscript_exit=%s\n' "$RESULT" "$outcome" > "$RUN/result.txt"
    (cd "$RUN" && find . -type f ! -name SHA256SUMS -print | sort |
       while IFS= read -r file; do
           printf '%s  %s\n' "$(sha256 -q "$file")" "$file"
       done) > "$RUN/SHA256SUMS" 2>> "$RUN/driver.log" || :
    if tar -czf "$ARCHIVE" -C "$RESULTS" "$NAME" && tar -tzf "$ARCHIVE" > /dev/null; then
        checksum=$(sha256 -q "$ARCHIVE")
        rm -rf "$RUN"
        printf '\nRESULT=%s\nARCHIVE=%s\nSHA256=%s\n' "$RESULT" "$ARCHIVE" "$checksum" >&3
    else
        echo "ERROR: failed to create archive from $RUN" >&3
        outcome=2
    fi
    rmdir "$LOCK" 2>/dev/null || :
    exit "$outcome"
}
fail() {
    log "PRECHECK_FAILED: $*"
    RESULT=PRECHECK_FAILED
    exit 2
}
trap 'finish "$?"' 0
trap 'RESULT=INTERRUPTED; exit 130' 1 2 3 15

log "$CANDIDATE single-run preflight and acquisition; results directory: $RUN"
printf 'runner=voice-one-command-v4-a1-a2\ncandidate=%s\nendpoint=%s:596\nmode=reflector\nduration=15\n' "$CANDIDATE" "$TARGET" > "$RUN/manifest.txt"
date -u +%Y-%m-%dT%H:%M:%SZ > "$RUN/start-utc.txt"
uname -a > "$RUN/opnsense-uname.txt"
for bin in "$SSH" "$KEY" "$ROUTE_FIX" "$ACTIVE/traffic.conf" "$ACTIVE/managed/ipset-telegram.txt"; do
    [ -e "$bin" ] || fail "required file missing: $bin"
done
[ ! -e "$BASE/route-watch.disabled" ] || fail 'the existing route-repair pause flag is present'
[ -x "$SSH" ] || fail "SSH binary not executable: $SSH"

configctl zapret status > "$RUN/zapret-before.txt" 2>&1 || fail 'cannot query Zapret2 status'
grep -q 'zapret is running as pid ' "$RUN/zapret-before.txt" || fail 'normal Zapret2 is not reported running'
configctl zapret telegram_voice_status > "$RUN/voice-before.txt" 2>&1 || fail 'cannot query Voice status'
for field in 'requested=on' 'effective=on' 'service=running' 'active_profile=on' 'table_present=yes'; do
    grep -Fq "telegram_voice_poc.$field" "$RUN/voice-before.txt" || fail "Voice baseline missing $field"
done
ipfw -a list > "$RUN/ipfw-before.txt" 2>&1 || fail 'cannot snapshot IPFW rules'
pfilctl heads > "$RUN/pfil-before.txt" 2>&1 || fail 'cannot snapshot PFIL hook order'
configctl proxy status > "$RUN/squid-status.txt" 2>&1 || :
cp "$ACTIVE/traffic.conf" "$RUN/traffic-effective.txt" || fail 'cannot save effective traffic profile'
cp "$ACTIVE/managed/ipset-telegram.txt" "$RUN/ipset-telegram.txt" || fail 'cannot save managed IPSET'

# Read persisted GUI strategy WITHOUT archiving /conf/config.xml or printing credentials.
# An unreadable saved model is an honest UNKNOWN, not an assumption about GUI Apply.
if [ -x /usr/local/bin/python3 ] && [ -r /conf/config.xml ]; then
    /usr/local/bin/python3 - > "$RUN/a1-saved-diagnostics.txt" 2>&1 <<'SAVED_A1'
import os
import xml.etree.ElementTree as ET
try:
    root = ET.parse("/conf/config.xml").getroot()
    node = root.find("./OPNsense/Zapret/strategy/trafficargs")
    if node is None:
        print("saved_gui_model=NOT_FOUND")
    else:
        print("saved_gui_model=READ_OK")
        data = (node.text or "").replace("\r", "")
        need_port = "--filter-udp=596-599"
        need_payload = "--payload=unknown"
        need_fake = "--lua-desync=fake:payload=unknown:blob=0x00000000000000000000000000000000" + (":badsum" if os.environ["TGVOICE_CANDIDATE"] == "A1" else "") + ":repeats=2"
        other_fake = "--lua-desync=fake:payload=unknown:blob=0x00000000000000000000000000000000" + ("" if os.environ["TGVOICE_CANDIDATE"] == "A1" else ":badsum") + ":repeats=2"
        blocks = data.split("--new")
        valid = (sum(all(token in block for token in (need_port, need_payload, need_fake, "<IPSET:telegram>")) for block in blocks) == 1
                 and not any(all(token in block for token in (need_port, need_payload, other_fake, "<IPSET:telegram>")) for block in blocks))
        print("saved_gui_" + os.environ["TGVOICE_CANDIDATE"] + "=" + ("YES" if valid else "NO"))
        print("saved_gui_A1_port=" + ("YES" if need_port in data else "NO"))
        print("saved_gui_A1_payload=" + ("YES" if need_payload in data else "NO"))
        a1_fake = "--lua-desync=fake:payload=unknown:blob=0x00000000000000000000000000000000:badsum:repeats=2"
        print("saved_gui_A1_fake=" + ("YES" if a1_fake in data else "NO"))
        print("saved_gui_candidate_fake=" + ("YES" if need_fake in data else "NO"))
        print("saved_gui_A1_ipset=" + ("YES" if "<IPSET:telegram>" in data else "NO"))
except (OSError, ET.ParseError, UnicodeError) as e:
    print("saved_gui_model=UNREADABLE")
    print("saved_gui_error_class=" + type(e).__name__)
SAVED_A1
    if [ "$?" -ne 0 ]; then
        printf '%s\n' 'saved_gui_model=DIAGNOSTIC_ERROR' > "$RUN/a1-saved-diagnostics.txt"
    fi
else
    printf '%s\n' 'saved_gui_model=UNAVAILABLE_PYTHON_OR_XML' > "$RUN/a1-saved-diagnostics.txt"
fi
# Safe to report: this file contains ONLY boolean A1 flags; never XML contents.
cat "$RUN/a1-saved-diagnostics.txt"

# Verify exact active candidate profile, refusing competing fake variants.
# Verify the selected candidate exists in exactly ONE complete generated profile.
awk -v expected="$FAKE_LINE" -v competing="$OTHER_FAKE" '
function check() { if (l3 && udp && ipset && unknown) { if (fake) hits++; if (alt) conflicts++ } }
$0=="--new" { check(); l3=udp=ipset=unknown=fake=alt=0; next }
$0=="--filter-l3=ipv4" {l3=1}
$0=="--filter-udp=596-599" {udp=1}
$0=="--ipset=/usr/local/etc/zapret2/runtime-v2/managed/ipset-telegram.txt" {ipset=1}
$0=="--payload=unknown" {unknown=1}
$0==expected {fake=1}
$0==competing {alt=1}
END { check(); exit !(hits==1 && conflicts==0) }
' "$ACTIVE/traffic.conf" || {
    if grep -Fxq "saved_gui_${CANDIDATE}=NO" "$RUN/a1-saved-diagnostics.txt"; then
        RESULT="${CANDIDATE}_NOT_IN_SAVED_GUI"
        log "$RESULT: no unique saved candidate block (or competitor remains); Docker NOT started"
    elif grep -Fxq "saved_gui_${CANDIDATE}=YES" "$RUN/a1-saved-diagnostics.txt"; then
        RESULT="${CANDIDATE}_SAVED_BUT_NOT_EFFECTIVE"
        log "$RESULT: saved candidate does not match unique active profile; Docker NOT started"
    else
        RESULT="${CANDIDATE}_SAVED_STATUS_UNKNOWN"
        log "$RESULT: persisted candidate not proven; Docker NOT started"
    fi
    exit 2
}
grep -Fq -- '--name=telegram-voice-poc' "$ACTIVE/traffic.conf" || fail 'STUN helper effective profile missing'
grep -Fqx '91.108.12.0/22' "$ACTIVE/managed/ipset-telegram.txt" || fail 'known target-covering managed Telegram CIDR not found'
grep -F 'table(zapret2_tgvoice)' "$RUN/ipfw-before.txt" | grep -Eq 'divert [0-9]+ udp .*xmit vtnet1' || fail 'destination-scoped Voice IPFW rule missing'
ipfw table zapret2_tgvoice list > "$RUN/voice-ipfw-table.txt" 2>&1 || fail 'cannot read Voice IPFW table'
grep -Fq '91.108.12.0/22' "$RUN/voice-ipfw-table.txt" || fail 'fixed reflector missing from Voice IPFW table'
grep -F '596-599' "$RUN/ipfw-before.txt" | grep -Fq ' udp ' || { RESULT="${CANDIDATE}_ACTIVE_PROFILE_BUT_IPFW_RULE_MISSING"; log "$RESULT: actual numeric UDP port rule lacks 596-599; Docker NOT started"; exit 2; }
log "$CANDIDATE profile, helper interception, managed IPSET and IPFW preflight passed."

log 'Invoking existing owner-tested one-shot route guard on OPNsense.'
/bin/sh "$ROUTE_FIX" > "$RUN/route-guard.log" 2>&1 || fail 'existing TNAS route guard failed; see route-guard.log'
log 'Checking actual TNAS routes, Docker host networking and pinned binary over the saved SSH key.'
ssh_tnas > "$RUN/remote-preflight.txt" 2>&1 <<'REMOTE_PRE'
set -eu
DOCKER=/Volume1/@apps/DockerEngine/dockerd/bin/docker
SRC=192.168.1.100
GW=192.168.1.2
DEV=ovs_eth1
EXPECTED=7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc
# A route lookup with an explicit "from" may echo "from", not "src".
# Verify the expected source is assigned to the expected NIC independently.
if ! ip -4 -o addr show dev "$DEV" | awk '{print $4}' | grep -Eq "^$SRC/[0-9]+$"; then
    echo 'TNAS_SOURCE_ADDRESS_INVALID'
    exit 10
fi
for target in 91.108.13.10 149.154.167.99; do
    line=$(ip -4 route get "$target" from "$SRC")
    printf 'ROUTE %s: %s\n' "$target" "$line"
    case " $line " in
        *" via $GW dev $DEV "*) : ;;
        *) echo 'ROUTE_INVALID'; exit 11 ;;
    esac
done
[ -x "$DOCKER" ] || { echo 'DOCKER_NOT_INSTALLED'; exit 12; }
mode=$("$DOCKER" inspect -f '{{.HostConfig.NetworkMode}}' tgvoice-lab)
state=$("$DOCKER" inspect -f '{{.State.Running}}' tgvoice-lab)
printf 'DOCKER_MODE=%s\nINITIAL_DOCKER_RUNNING=%s\n' "$mode" "$state"
[ "$mode" = host ] || { echo 'DOCKER_NOT_HOST_NETWORK'; exit 13; }
case "$state" in true|false) : ;; *) exit 14;; esac
REMOTE_PRE
[ "$?" -eq 0 ] || fail 'TNAS route/Docker preflight failed; see remote-preflight.txt'
if grep -Fxq 'INITIAL_DOCKER_RUNNING=false' "$RUN/remote-preflight.txt"; then
    log 'Starting existing tgvoice-lab on demand (will stop on cleanup).'
    # Mark before startup so interruptions still attempt restoration.
    STARTED_CONTAINER=1
    ssh_tnas > "$RUN/docker-start.log" 2>&1 <<'REMOTE_START'
set -eu
/Volume1/@apps/DockerEngine/dockerd/bin/docker start tgvoice-lab
REMOTE_START
    [ "$?" -eq 0 ] || fail 'cannot start existing tgvoice-lab; see docker-start.log'
fi
ssh_tnas > "$RUN/binary-check.txt" 2>&1 <<'REMOTE_BIN'
set -eu
DOCKER=/Volume1/@apps/DockerEngine/dockerd/bin/docker
expected=7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc
attempt=0
while [ "$attempt" -lt 60 ]; do
    if checksum=$("$DOCKER" exec tgvoice-lab sha256sum /results/tgcalls_cli 2>/dev/null); then
        printf 'CLI_SHA256=%s\n' "$checksum"
        hash=${checksum%% *}
        [ "$hash" = "$expected" ] || exit 21
        echo 'CLI_BINARY_OK'
        exit 0
    fi
    attempt=$((attempt+1))
    sleep 2
done
echo 'CLI_BINARY_UNAVAILABLE'
exit 22
REMOTE_BIN
[ "$?" -eq 0 ] && grep -Fxq 'CLI_BINARY_OK' "$RUN/binary-check.txt" || fail 'Docker binary missing/not ready/wrong SHA; see binary-check.txt'
log 'Remote pinned oracle confirmed. Starting both owned packet captures.'
tcpdump -ni vtnet0 -s 0 -U -w "$RUN/lan.pcap" "host 192.168.1.100 and host $TARGET and ip" > "$RUN/tcpdump-lan.log" 2>&1 &
LAN_PID=$!
tcpdump -ni vtnet1 -s 0 -U -w "$RUN/wan.pcap" "host $TARGET and ip" > "$RUN/tcpdump-wan.log" 2>&1 &
WAN_PID=$!
sleep 2
kill -0 "$LAN_PID" 2>/dev/null || fail 'LAN tcpdump did not start'
kill -0 "$WAN_PID" 2>/dev/null || fail 'WAN tcpdump did not start'
log 'Running ONE fresh 15-second Docker reflector test via noninteractive SSH.'
printf '%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$RUN/cli-start-utc.txt"
ssh_tnas > "$RUN/tgcalls-cli.log" 2>&1 <<'REMOTE_TEST' &
set -u
DOCKER=/Volume1/@apps/DockerEngine/dockerd/bin/docker
if ! command -v timeout >/dev/null 2>&1; then
    echo 'TIMEOUT_UTILITY_MISSING'
    exit 125
fi
timeout -k 5 60 "$DOCKER" exec tgvoice-lab /results/tgcalls_cli --mode reflector --reflector 91.108.13.10:596 --duration 15
result=$?
printf 'tgcalls_exit=%s\n' "$result"
exit "$result"
REMOTE_TEST
SSH_PID=$!
wait "$SSH_PID"
CLI_RC=$?
SSH_PID=
printf 'ssh_and_tgcalls_exit=%s\n' "$CLI_RC" > "$RUN/cli-exit.txt"
date -u +%Y-%m-%dT%H:%M:%SZ > "$RUN/cli-end-utc.txt"
log "Docker test ended (SSH/client exit $CLI_RC); collecting packet-level evidence."
stop_capture "$LAN_PID"
stop_capture "$WAN_PID"
LAN_PID=
WAN_PID=
if [ "$CLI_RC" -eq 255 ] || [ "$CLI_RC" -eq 125 ] || [ "$CLI_RC" -eq 124 ]; then
    RESULT=RUNNER_OR_TRANSPORT_FAILURE
else
    RESULT=ACQUIRED_MEDIA_UNVERIFIED
fi
# Failure of the remote media oracle is evidence, not failure to collect diagnostics.
exit 0
