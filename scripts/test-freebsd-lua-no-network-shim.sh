#!/bin/sh
# FreeBSD 15 TEST-ONLY shim feasibility. No installed engine, no jail,
# no upstream Lua, no network and no host firewall operation.
# The shim is NOT itself a security boundary; a real engine run MUST be
# performed later only in a proven isolated FreeBSD jail/root image.
set -eu
[ "$(uname -s)" = FreeBSD ] || {
  echo 'SKIP: FreeBSD-only socket interposer experiment'
  exit 0
}
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
WORK=$(mktemp -d "/tmp/zapret-lua-shim.XXXXXX")
trap 'rm -rf "$WORK"' EXIT HUP INT TERM

cc -Wall -Wextra -Werror -fPIC -shared -o "$WORK/no-net.so" \
  "$ROOT/scripts/fixtures/lua-init-no-network-shim.c"
cc -Wall -Wextra -Werror -o "$WORK/mock-engine" \
  "$ROOT/scripts/fixtures/lua-init-mock-engine.c"

# We NEVER run the mock without preload: doing so could open PF_DIVERT.
# This runs only the synthetic no-network fixture, not actual dvtws2.
env LD_PRELOAD="$WORK/no-net.so" "$WORK/mock-engine" > "$WORK/result"
grep -Fxq 'MOCK_LUA_INIT_REACHED_NO_NETWORK_SOCKET' "$WORK/result"
echo 'PASS: FreeBSD divert preinit shim makes inert AF_UNIX FDs; IP sockets and sendto denied (MOCK ONLY)'
