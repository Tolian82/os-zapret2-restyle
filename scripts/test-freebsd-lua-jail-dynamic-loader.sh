#!/bin/sh
# FreeBSD15 CI ONLY: actual ld-elf.so.1 loads a SYNTHETIC ELF behind existing
# STATIC kernel jail/no-IP preflight. NEVER installed dvtws2 or Lua.
set -eu
if [ "$(uname -s)" != FreeBSD ]; then
    echo "SKIP: native dynamic loader experiment requires FreeBSD"
    exit 0
fi
if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: private FreeBSD jail creation requires root in CI" >&2
    exit 1
fi

REPO=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
TMP=$(mktemp -d /tmp/zapret2-jail-real-loader.XXXXXXXX)
NAME="zapret2loader$$"
ACTIVE=0
PHASE=prepare
cleanup()
{
    status=$?
    trap - EXIT HUP INT TERM
    if [ "$status" -ne 0 ]; then
        echo "ERROR: private loader experiment failed in phase=$PHASE ($status)" >&2
        for file in host-negative.txt boundary.txt no-loader.txt no-libc.txt loaded.txt; do
            if [ -f "$TMP/$file" ]; then
                echo "--- $file ---" >&2
                cat "$TMP/$file" >&2
            fi
        done
    fi
    if [ "$ACTIVE" -eq 1 ]; then
        jail -r "$NAME" >/dev/null 2>&1 || true
    fi
    rm -rf "$TMP"
    exit "$status"
}
trap cleanup EXIT HUP INT TERM

mkdir -m 0700 "$TMP/root"
mkdir -m 0755 "$TMP/root/lib" "$TMP/root/libexec"
printf '%s\n' "HOST_ONLY" > "$TMP/host-only-secret"
cc -Wall -Wextra -Werror -static -o "$TMP/root/probe" \
    "$REPO/scripts/fixtures/lua-jail-native-boundary.c"
cc -Wall -Wextra -Werror -o "$TMP/root/loader-marker" \
    "$REPO/scripts/fixtures/lua-jail-loader-marker.c"
chmod 0555 "$TMP/root/probe" "$TMP/root/loader-marker"

# Source analysis only; never execute a dynamic marker on the host.
PHASE=static-ELF-attestation
REPO="$REPO" MARKER="$TMP/root/loader-marker" /usr/local/bin/python3.13 - <<'PY'
import os
import sys
from pathlib import Path
sys.path.insert(0, os.environ["REPO"] + "/src/opnsense/scripts/OPNsense/Zapret")
from extra_resources_jail_loader import _elf_interpreter, STANDARD_INTERPRETER
from extra_resources_engine_abi import _needed_libraries
data = Path(os.environ["MARKER"]).read_bytes()
if _elf_interpreter(data, dependency=False) != STANDARD_INTERPRETER:
    raise SystemExit("FAIL: marker lacks canonical FreeBSD PT_INTERP")
if "libc.so.7" not in _needed_libraries(data):
    raise SystemExit("FAIL: marker is not linked to libc")
print("PASS: actual FreeBSD synthetic ELF PT_INTERP/DT_NEEDED, without execution")
PY

PHASE=host-negative-control
if "$TMP/root/probe" "$TMP/host-only-secret" --exec-loader-test > "$TMP/host-negative.txt" 2>&1; then
    echo "ERROR: host kernel probe accepted loader dispatch" >&2
    exit 1
fi
grep -Fq "NOT_A_JAIL" "$TMP/host-negative.txt"

PHASE=private-jail-create
jail -c "name=$NAME" "path=$TMP/root" persist \
    "ip4=disable" "ip6=disable" \
    "allow.raw_sockets=0" "allow.socket_af=0" \
    "allow.mount=0" "allow.sysvipc=0" "exec.clean" >/dev/null
ACTIVE=1
PHASE=kernel-boundary
jexec "$NAME" /probe "$TMP/host-only-secret" > "$TMP/boundary.txt"
grep -Fxq "JAIL_PRIVATE_ROOT_NO_IP_NO_RAW_SOCKET_PASS" "$TMP/boundary.txt"

# FreeBSD base shared C runtime only; the host's /etc, /dev and Config
# are never mounted. Same minimal ABI objects as the already-qualified
# synthetic jail+shim test.
cp -L /lib/libc.so.7 "$TMP/root/lib/libc.so.7"
for soname in libsys.so.7 libthr.so.3; do
    if [ -f "/lib/$soname" ]; then
        cp -L "/lib/$soname" "$TMP/root/lib/$soname"
    fi
done

# Executing a marker whose ELF interpreter does not exist must FAIL.
PHASE=missing-interpreter-control
if jexec "$NAME" /probe "$TMP/host-only-secret" --exec-loader-test > "$TMP/no-loader.txt" 2>&1; then
    echo "ERROR: missing PT_INTERP unexpectedly succeeded" >&2
    exit 1
fi
# On FreeBSD 15 a missing PT_INTERP can abort the exec caller in-kernel
# (Abort trap) instead of returning ENOENT to perror. Require failed exit,
# the exact preceding static kernel boundary, and NO dynamic success marker.
grep -Fxq "JAIL_PRIVATE_ROOT_NO_IP_NO_RAW_SOCKET_PASS" "$TMP/no-loader.txt"
if grep -Fq "JAIL_REAL_DYNAMIC_LOADER_SYNTHETIC_ELF_PASS" "$TMP/no-loader.txt"; then
    echo "ERROR: false-positive success without loader" >&2
    exit 1
fi

PHASE=stage-FreeBSD-loader
cp -L /libexec/ld-elf.so.1 "$TMP/root/libexec/ld-elf.so.1"

# The real interpreter alone must not count as startup if libc is missing.
PHASE=missing-libc-control
mv "$TMP/root/lib/libc.so.7" "$TMP/libc-outside-jail"
if jexec "$NAME" /probe "$TMP/host-only-secret" --exec-loader-test > "$TMP/no-libc.txt" 2>&1; then
    echo "ERROR: missing libc unexpectedly succeeded" >&2
    exit 1
fi
if grep -Fq "JAIL_REAL_DYNAMIC_LOADER_SYNTHETIC_ELF_PASS" "$TMP/no-libc.txt"; then
    echo "ERROR: false-positive success without libc" >&2
    exit 1
fi
mv "$TMP/libc-outside-jail" "$TMP/root/lib/libc.so.7"

# The STATIC probe must once again prove kernel confinement and then
# execve the dynamic marker with PATH=/ and NO preload, no network.
PHASE=real-jailed-loader
jexec "$NAME" /probe "$TMP/host-only-secret" --exec-loader-test > "$TMP/loaded.txt" 2>&1
grep -Fxq "JAIL_PRIVATE_ROOT_NO_IP_NO_RAW_SOCKET_PASS" "$TMP/loaded.txt"
grep -Fxq "JAIL_REAL_DYNAMIC_LOADER_SYNTHETIC_ELF_PASS" "$TMP/loaded.txt"

PHASE=jail-teardown
jail -r "$NAME"
ACTIVE=0
if jls -N 2>/dev/null | grep -Fq "$NAME"; then
    echo "ERROR: synthetic FreeBSD dynamic-loader jail remains" >&2
    exit 1
fi
echo "PASS: FreeBSD real dynamic loader started SYNTHETIC ELF inside kernel no-IP private jail; missing loader/libc negative controls; NO dvtws2/Lua; teardown complete"
