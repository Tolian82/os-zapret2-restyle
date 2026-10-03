#!/bin/sh
# v0.5.0_3: read-only OPNsense -> TNAS independent-egress discovery.
# Deliberately NO media probe, new gateway, host route, VPN setup or Docker start.
set -eu
umask 077
PATH=/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/sbin:/usr/local/bin
export PATH

BASE=/root/tgvoice-lab
RESULTS="$BASE/results"
KEY=/root/.ssh/id_ed25519_tgvoice_lab
SSH=/usr/local/bin/ssh
TARGET=91.108.13.10
LOCK="$BASE/.control-inventory.lock"

[ "$(id -u)" -eq 0 ] || { echo 'ERROR: execute as root on OPNsense' >&2; exit 2; }
[ -d "$BASE" ] || { echo 'ERROR: existing lab directory not found' >&2; exit 2; }
mkdir -p "$RESULTS"
[ -x "$SSH" ] && [ -r "$KEY" ] || { echo 'ERROR: existing SSH client/key unavailable; no repair attempted' >&2; exit 2; }
if ! mkdir "$LOCK" 2>/dev/null; then
    echo 'ERROR: inventory already running or stale lock; inspect before removal' >&2
    exit 2
fi
RUN=$(mktemp -d "$RESULTS/control-inventory-$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX") || {
    rmdir "$LOCK"
    exit 2
}
ARCHIVE="$RUN.tgz"
RESULT=INVENTORY_INCOMPLETE
exec 3>&1
exec >> "$RUN/driver.log" 2>&1
finish() {
    code=$1
    trap - 0 1 2 3 15
    printf 'result=%s\nscript_exit=%s\nindependent_same_endpoint_media_path=UNVERIFIED\n' "$RESULT" "$code" > "$RUN/result.txt"
    (cd "$RUN" && find . -type f ! -name SHA256SUMS -print | sort |
        while IFS= read -r item; do printf '%s  %s\n' "$(sha256 -q "$item")" "$item"; done) > "$RUN/SHA256SUMS" || :
    if tar -czf "$ARCHIVE" -C "$RESULTS" "${RUN##*/}" && tar -tzf "$ARCHIVE" >/dev/null; then
        digest=$(sha256 -q "$ARCHIVE")
        rm -rf "$RUN"
        printf 'RESULT=%s\nARCHIVE=%s\nSHA256=%s\n' "$RESULT" "$ARCHIVE" "$digest" >&3
    else
        printf 'ERROR: archive creation failed; raw private data remains at %s\n' "$RUN" >&3
        code=2
    fi
    rmdir "$LOCK" 2>/dev/null || :
    exit "$code"
}
trap 'finish "$?"' 0
trap 'RESULT=INTERRUPTED; exit 130' 1 2 3 15

printf 'mode=READ_ONLY_TOPOLOGY_INVENTORY\nrunner=voice-independent-control-preflight-v1\ntarget=%s:596\n' "$TARGET" > "$RUN/manifest.txt"
date -u +%Y-%m-%dT%H:%M:%SZ > "$RUN/start-utc.txt"
uname -sm > "$RUN/opnsense-platform.txt"
ifconfig -l > "$RUN/opnsense-interface-names.txt" 2>&1 || :
route -n get "$TARGET" > "$RUN/opnsense-route-target.txt" 2>&1 || :
netstat -rn -f inet > "$RUN/opnsense-ipv4-routes-private.txt" 2>&1 || :
{
    for command in tailscale wg wireguard-go openvpn; do
        if command -v "$command" >/dev/null 2>&1; then
            printf '%s=INSTALLED\n' "$command"
        else
            printf '%s=NOT_FOUND\n' "$command"
        fi
    done
} > "$RUN/opnsense-vpn-tool-presence.txt"

printf 'Collecting read-only TNAS inventory over existing restricted SSH. No routes or services will change.\n' >&3
if ! "$SSH" -T -p 9222 -i "$KEY" -o IdentitiesOnly=yes -o BatchMode=yes \
    -o StrictHostKeyChecking=yes -o ConnectTimeout=7 \
    -o ServerAliveInterval=5 -o ServerAliveCountMax=2 \
    tolian@192.168.1.100 /bin/sh -s > "$RUN/tnas-inventory-private.txt" 2>&1 <<'REMOTE_INVENTORY'
set -eu
DOCKER=/Volume1/@apps/DockerEngine/dockerd/bin/docker
SRC=192.168.1.100
TARGET=91.108.13.10
printf 'platform='; uname -sm
printf 'identity_uid='; id -u
printf '\n=== IPv4 interface inventory (private) ===\n'
ip -4 -o addr show
printf '\n=== Link interface names (private) ===\n'
ip -o link show | sed -n 's/^[0-9][0-9]*: \([^:]*\):.*/\1/p'
printf '\n=== Policy routes BEFORE (private) ===\n'
ip -4 rule show
ip -4 route show table all
printf '\n=== Exact reflector route BEFORE ===\n'
before=$(ip -4 route get "$TARGET" from "$SRC") || { echo 'TARGET_ROUTE_QUERY_FAILED'; exit 10; }
printf '%s\n' "$before"
# We inventory only the accepted CURRENT OPNsense baseline; never test via
# the retired .140 default or route around the documented /32.
if ! ip -4 -o addr show dev ovs_eth1 | awk '{print $4}' | grep -Eq '^192[.]168[.]1[.]100/[0-9]+$'; then
    echo 'CURRENT_SOURCE_INTERFACE_NOT_VERIFIED'
    exit 11
fi
case " $before " in
    *" via 192.168.1.2 dev ovs_eth1 "*) : ;;
    *) echo 'CURRENT_OPNSENSE_BASELINE_CHANGED'; exit 12 ;;
esac
printf '\n=== Available tunnel program presence; NOT connectivity ===\n'
for tool in tailscale wg wireguard-go openvpn ip; do
    if command -v "$tool" >/dev/null 2>&1; then
        printf '%s=INSTALLED\n' "$tool"
    else
        printf '%s=NOT_FOUND\n' "$tool"
    fi
done
printf 'tun_device='
if [ -c /dev/net/tun ]; then echo PRESENT; else echo ABSENT; fi
printf '\n=== Known external TCP parent route; NOT UDP evidence ===\n'
ip -4 route get 185.203.117.88 from "$SRC" || :
printf '\n=== Existing Docker (inspect only; never start) ===\n'
if [ -x "$DOCKER" ]; then
    if "$DOCKER" inspect -f 'network={{.HostConfig.NetworkMode}} running={{.State.Running}} restart={{.HostConfig.RestartPolicy.Name}}' tgvoice-lab; then
        if [ "$("$DOCKER" inspect -f '{{.State.Running}}' tgvoice-lab)" = true ]; then
            "$DOCKER" exec tgvoice-lab sha256sum /results/tgcalls_cli || :
        else
            echo 'PINNED_BINARY_CHECK=SKIPPED_CONTAINER_STOPPED'
        fi
    else
        echo 'DOCKER_INSPECT=UNAVAILABLE'
    fi
else
    echo 'DOCKER_BINARY=NOT_FOUND'
fi
printf '\n=== Policy routes AFTER (private) ===\n'
ip -4 rule show
ip -4 route show table all
after=$(ip -4 route get "$TARGET" from "$SRC") || { echo 'AFTER_ROUTE_QUERY_FAILED'; exit 13; }
printf 'reflector_route_after=%s\n' "$after"
[ "$before" = "$after" ] || { echo 'ROUTE_CHANGED_DURING_INVENTORY'; exit 14; }
echo 'CURRENT_BASELINE_READ_ONLY_PASS'
echo 'INDEPENDENT_PATH=NOT_VALIDATED'
REMOTE_INVENTORY
then
    RESULT=TNAS_INVENTORY_FAILED
    printf 'TNAS inventory failed: preserve the one archive; no changes attempted.\n' >&3
    exit 2
fi

if ! grep -Fxq 'CURRENT_BASELINE_READ_ONLY_PASS' "$RUN/tnas-inventory-private.txt"; then
    RESULT=CURRENT_BASELINE_UNVERIFIED
    printf 'Current baseline was not proven; no alternative test attempted.\n' >&3
    exit 2
fi
RESULT=INVENTORY_ONLY_NO_INDEPENDENT_PATH_VALIDATED
date -u +%Y-%m-%dT%H:%M:%SZ > "$RUN/end-utc.txt"
printf 'Read-only discovery complete. Presence of a VPN binary does NOT prove a working independent exit.\n' >&3
exit 0
