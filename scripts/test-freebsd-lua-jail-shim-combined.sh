#!/bin/sh
# FreeBSD 15 CI-only: combined kernel jail + dynamic mock divert interposer.
# NEVER runs dvtws2 or real Lua. Do not use on live OPNsense.
set -eu
if [ "$(uname -s)" != FreeBSD ]; then
    echo "SKIP: FreeBSD-only combined jail/mock experiment"
    exit 0
fi
if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: CI-only private jail needs root" >&2
    exit 1
fi

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TMP=$(mktemp -d /tmp/zapret2-jail-shim.XXXXXXXX)
NAME="zapret2shim$$"
ACTIVE=0
cleanup()
{
    if [ "$ACTIVE" -eq 1 ]; then
        jail -r "$NAME" >/dev/null 2>&1 || true
    fi
    rm -rf "$TMP"
}
trap cleanup EXIT HUP INT TERM

# The jail has its own root and ONLY a static boundary probe, a synthetic
# mock, a CI-built test-only shim and the dynamic loader + C runtime.
mkdir -m 0700 "$TMP/root"
mkdir -m 0755 "$TMP/root/lib" "$TMP/root/libexec"
printf '%s\n' "HOST_ONLY" > "$TMP/host-only-secret"
cc -Wall -Wextra -Werror -static -o "$TMP/root/probe" \
    "$ROOT/scripts/fixtures/lua-jail-native-boundary.c"
cc -Wall -Wextra -Werror -fPIC -shared -o "$TMP/root/no-net.so" \
    "$ROOT/scripts/fixtures/lua-init-no-network-shim.c"
cc -Wall -Wextra -Werror -o "$TMP/root/mock-engine" \
    "$ROOT/scripts/fixtures/lua-init-mock-engine.c"
# No host /etc, /usr, devices or live Lua/BIN/runtime are mounted. These
# FreeBSD base ABI objects allow the controlled dynamic mock to load in jail.
cp -L /libexec/ld-elf.so.1 "$TMP/root/libexec/ld-elf.so.1"
cp -L /lib/libc.so.7 "$TMP/root/lib/libc.so.7"
chmod 0555 "$TMP/root/probe" "$TMP/root/no-net.so" "$TMP/root/mock-engine"

# Negative host control: even with the --exec-mock flag this launcher must
# refuse to run outside an actual kernel jail.
if "$TMP/root/probe" "$TMP/host-only-secret" --exec-mock > "$TMP/host.txt" 2>&1; then
    echo "ERROR: host probe accepted --exec-mock without jail" >&2
    exit 1
fi
grep -Fq "NOT_A_JAIL" "$TMP/host.txt"

jail -c "name=$NAME" "path=$TMP/root" persist \
    "ip4=disable" "ip6=disable" \
    "allow.raw_sockets=0" "allow.socket_af=0" \
    "allow.mount=0" "allow.sysvipc=0" "exec.clean" >/dev/null
ACTIVE=1

# First prove the kernel denies the same operations WITHOUT any LD_PRELOAD.
jexec "$NAME" /probe "$TMP/host-only-secret" > "$TMP/kernel.txt"
grep -Fxq "JAIL_PRIVATE_ROOT_NO_IP_NO_RAW_SOCKET_PASS" "$TMP/kernel.txt"

# Without the shim, synthetic PF_DIVERT must FAIL inside the private jail.
# Assert the exact mock failure to avoid treating a missing ELF loader as PASS.
if jexec "$NAME" /mock-engine > "$TMP/without-shim.txt" 2>&1; then
    echo "ERROR: jailed divert mock unexpectedly passed without shim" >&2
    exit 1
fi
grep -Fq "divert shim failed step 1" "$TMP/without-shim.txt"

# Static probe checks the KERNEL boundary again, then execs the mock with a
# jail-relative LD_PRELOAD. The shim is never loaded by jexec on the host.
jexec "$NAME" /probe "$TMP/host-only-secret" --exec-mock > "$TMP/with-shim.txt"
grep -Fxq "JAIL_PRIVATE_ROOT_NO_IP_NO_RAW_SOCKET_PASS" "$TMP/with-shim.txt"
grep -Fxq "MOCK_LUA_INIT_REACHED_NO_NETWORK_SOCKET" "$TMP/with-shim.txt"

jail -r "$NAME"
ACTIVE=0
if jls -N 2>/dev/null | grep -Fq "$NAME"; then
    echo "ERROR: combined CI jail remains after teardown" >&2
    exit 1
fi
echo "PASS: FreeBSD15 kernel jail + synthetic divert shim combined; no real engine or Lua; teardown complete"
