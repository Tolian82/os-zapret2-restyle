#!/bin/sh
# FreeBSD 15 CI ONLY. Compile genuine pinned upstream v1.0.6 dvtws2 and run
# its real Lua init/export checks only in a disposable kernel no-IP jail.
# NOT the owner's installed binary; NOT an authorization to remove resources.
set -eu
if [ "$(uname -s)" != FreeBSD ]; then
    echo "SKIP: FreeBSD CI upstream-engine jail trial only"
    exit 0
fi
if [ "$(id -u)" -ne 0 ]; then
    echo "FAIL: jailed upstream-engine CI experiment needs root" >&2
    exit 1
fi
REPO=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
TMP=$(mktemp -d /tmp/zapret2-ci-upstream-lua.XXXXXXXX)
NAME="zapret2ciupstream$$"
UPSTREAM_REV=221d7dff24bfec0cd5ac0a5070b8acef2008af3d
ACTIVE=0
PHASE=prepare
cleanup()
{
    result=$?
    trap - EXIT HUP INT TERM
    if [ "$result" -ne 0 ]; then
        echo "FAIL: pinned CI upstream dvtws2 Lua jail trial phase=$PHASE exit=$result" >&2
        for file in build.txt host.txt boundary.txt missing-lua.txt missing-export.txt positive.txt; do
            if [ -f "$TMP/$file" ]; then
                echo "--- $file ---" >&2
                tail -n 35 "$TMP/$file" >&2
            fi
        done
    fi
    if [ "$ACTIVE" -eq 1 ]; then
        jail -r "$NAME" >/dev/null 2>&1 || true
    fi
    rm -rf "$TMP"
    exit "$result"
}
trap cleanup EXIT HUP INT TERM
mkdir -m 0700 "$TMP/root"
mkdir -m 0755 "$TMP/root/upstream" "$TMP/root/upstream/lua" \
    "$TMP/root/lib" "$TMP/root/libexec" "$TMP/root/usr" \
    "$TMP/root/usr/lib" "$TMP/root/usr/local" "$TMP/root/usr/local/lib"
printf '%s\n' "HOST_ONLY" > "$TMP/host-only-secret"

PHASE=pinned-upstream-git-acquisition
git clone --quiet --depth 1 --single-branch --branch v1.0.6 \
    https://github.com/bol-van/zapret2.git "$TMP/upstream"
[ "$(git -C "$TMP/upstream" rev-parse HEAD)" = "$UPSTREAM_REV" ] || {
    echo "FAIL: CI upstream tag did not match pinned SHA" >&2
    exit 1
}
[ -z "$(git -C "$TMP/upstream" status --porcelain)" ] || {
    echo "FAIL: CI upstream source has worktree modifications" >&2
    exit 1
}

# This is a REAL upstream engine, unlike earlier synthetic markers. It is
# CI-built from pinned Git source, not read from the OPNsense appliance.
PHASE=build-pinned-upstream-FreeBSD-engine
gmake -C "$TMP/upstream/nfq2" bsd OPTIMIZE=-O1 MINSIZE= LDFLAGS=-pie \
    > "$TMP/build.txt" 2>&1
[ -s "$TMP/upstream/nfq2/dvtws2" ] || {
    echo "FAIL: CI upstream FreeBSD dvtws2 build absent" >&2
    exit 1
}
cc -Wall -Wextra -Werror -static -o "$TMP/root/probe" \
    "$REPO/scripts/fixtures/lua-jail-native-boundary.c"
cc -Wall -Wextra -Werror -fPIC -shared -o "$TMP/root/no-net.so" \
    "$REPO/scripts/fixtures/lua-init-no-network-shim.c"
cp "$TMP/upstream/nfq2/dvtws2" "$TMP/root/ci-engine"
cp "$TMP/upstream/lua/zapret-lib.lua" \
    "$TMP/root/upstream/lua/zapret-lib.lua"
chmod 0555 "$TMP/root/probe" "$TMP/root/no-net.so" "$TMP/root/ci-engine"
chmod 0444 "$TMP/root/upstream/lua/zapret-lib.lua"
cmp "$TMP/upstream/lua/zapret-lib.lua" "$TMP/root/upstream/lua/zapret-lib.lua"

PHASE=static-FreeBSD-ELF-dependency-stage
/usr/local/bin/python3.13 "$REPO/scripts/fixtures/lua-jail-stage-ci-elf.py" \
    stage "$TMP/root" "$TMP/elf-digests.json" \
    "$TMP/upstream/nfq2/dvtws2" "$TMP/root/no-net.so"

PHASE=unjailed-host-negative
if "$TMP/root/probe" "$TMP/host-only-secret" --exec-ci-upstream-positive \
    > "$TMP/host.txt" 2>&1; then
    echo "FAIL: static native boundary probe allowed host engine execution" >&2
    exit 1
fi
grep -Fq "NOT_A_JAIL" "$TMP/host.txt"

# The REAL upstream engine drops root privileges before reading Lua.
# Permit traversal inside the jail only; TMP (its HOST parent) stays 0700,
# and the jail has no host mounts/Config/devices or network capabilities.
chmod 0755 "$TMP/root"
PHASE=create-disposable-kernel-jail
jail -c "name=$NAME" "path=$TMP/root" persist \
    "ip4=disable" "ip6=disable" \
    "allow.raw_sockets=0" "allow.socket_af=0" \
    "allow.mount=0" "allow.sysvipc=0" "exec.clean" >/dev/null
ACTIVE=1
PHASE=kernel-confinement-evidence
jexec "$NAME" /probe "$TMP/host-only-secret" > "$TMP/boundary.txt"
grep -Fxq "JAIL_PRIVATE_ROOT_NO_IP_NO_RAW_SOCKET_PASS" "$TMP/boundary.txt"

# Negative controls must fail for real Lua input reasons, not a missing
# interpreter, broken dependencies, sandbox bypass or false success.
PHASE=missing-upstream-Lua-negative
if timeout 20 jexec "$NAME" /probe "$TMP/host-only-secret" \
    --exec-ci-upstream-missing-lua > "$TMP/missing-lua.txt" 2>&1; then
    echo "FAIL: real engine accepted absent Lua initializer" >&2
    exit 1
fi
grep -Fxq "JAIL_PRIVATE_ROOT_NO_IP_NO_RAW_SOCKET_PASS" "$TMP/missing-lua.txt"
if grep -Fq "LUA INIT DONE" "$TMP/missing-lua.txt"; then
    echo "FAIL: Lua initialized without upstream script" >&2
    exit 1
fi

PHASE=missing-Lua-export-negative
if timeout 20 jexec "$NAME" /probe "$TMP/host-only-secret" \
    --exec-ci-upstream-missing-export > "$TMP/missing-export.txt" 2>&1; then
    echo "FAIL: real engine accepted a nonexistent Lua export" >&2
    exit 1
fi
grep -Fxq "JAIL_PRIVATE_ROOT_NO_IP_NO_RAW_SOCKET_PASS" "$TMP/missing-export.txt"
grep -Fq "desync function '__ci_export_absent__' does not exist" "$TMP/missing-export.txt"
if grep -Fq "LUA INIT DONE" "$TMP/missing-export.txt"; then
    echo "FAIL: missing export was misclassified as Lua init success" >&2
    exit 1
fi

PHASE=genuine-upstream-Lua-init-export-positive
timeout 20 jexec "$NAME" /probe "$TMP/host-only-secret" \
    --exec-ci-upstream-positive > "$TMP/positive.txt" 2>&1
grep -Fxq "JAIL_PRIVATE_ROOT_NO_IP_NO_RAW_SOCKET_PASS" "$TMP/positive.txt"
grep -Eq "Running as UID=[1-9][0-9]* GID=[1-9][0-9]*" "$TMP/positive.txt"
grep -Fq "LUA INIT DONE" "$TMP/positive.txt"
grep -Fq "no intercept quit" "$TMP/positive.txt"

PHASE=after-run-static-attestation
cmp "$TMP/upstream/lua/zapret-lib.lua" "$TMP/root/upstream/lua/zapret-lib.lua"
/usr/local/bin/python3.13 "$REPO/scripts/fixtures/lua-jail-stage-ci-elf.py" \
    verify "$TMP/root" "$TMP/elf-digests.json"

PHASE=kernel-jail-teardown
jail -r "$NAME"
ACTIVE=0
if jls -N 2>/dev/null | grep -Fq "$NAME"; then
    echo "FAIL: native CI engine test jail survived teardown" >&2
    exit 1
fi
echo "PASS: REAL pinned CI-built upstream v1.0.6 dvtws2 ran actual Lua init/export checks in private no-IP FreeBSD jail; negatives + teardown; NOT installed engine/removal proof"
