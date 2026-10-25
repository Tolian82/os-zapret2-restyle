#!/bin/sh
# FreeBSD 15 CI only: prove isolation properties at the KERNEL level.
# Creates/removes an ephemeral jail inside disposable GitHub VM only.
# NEVER touches appliance IPFW/Config/installed dvtws2. NOT packaged.
set -eu
[ "$(uname -s)" = FreeBSD ] || {
    echo "SKIP: FreeBSD jail proof requires FreeBSD kernel"
    exit 0
}
[ "$(id -u)" -eq 0 ] || {
    echo "ERROR: test needs root to create temporary FreeBSD jail" >&2
    exit 1
}
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TMP=$(mktemp -d /tmp/zapret2-private-jail.XXXXXXXX)
NAME="zapret2luaprobe$$"
ACTIVE=0
cleanup()
{
    if [ "$ACTIVE" -eq 1 ]; then
        jail -r "$NAME" >/dev/null 2>&1 || true
    fi
    rm -rf "$TMP"
}
trap cleanup EXIT HUP INT TERM
mkdir -m 0700 "$TMP/root"
printf '%s\n' "CANARY_MUST_NOT_BE_VISIBLE_IN_JAIL" > "$TMP/host-only-secret"
cc -Wall -Wextra -Werror -static -o "$TMP/root/probe" \
   "$ROOT/scripts/fixtures/lua-jail-native-boundary.c"
chmod 0555 "$TMP/root/probe"
# The proof binary must refuse execution on the host even as root.
if "$TMP/root/probe" "$TMP/host-only-secret" >/dev/null 2>&1; then
    echo "ERROR: jail-bound probe falsely passed outside jail" >&2
    exit 1
fi
# Hard boundary: zero jail IP addresses, no raw sockets, no mounts or
# additional address families; private chroot excludes all host resources.
jail -c "name=$NAME" "path=$TMP/root" persist \
    "ip4=disable" "ip6=disable" \
    "allow.raw_sockets=0" "allow.socket_af=0" \
    "allow.mount=0" "allow.sysvipc=0" "exec.clean" >/dev/null
ACTIVE=1
jexec "$NAME" /probe "$TMP/host-only-secret" > "$TMP/proof.txt"
grep -Fxq "JAIL_PRIVATE_ROOT_NO_IP_NO_RAW_SOCKET_PASS" "$TMP/proof.txt"
# The jail must be removable without leaving even a persistent prison.
jail -r "$NAME"
ACTIVE=0
if jls -N 2>/dev/null | grep -Fq "$NAME"; then
    echo "ERROR: disposable jail was not destroyed" >&2
    exit 1
fi
echo "PASS: FreeBSD15 disposable private root jail blocks raw sockets and IP binding; kernel confirms jailed=true; teardown complete (NO ENGINE RUN)"
