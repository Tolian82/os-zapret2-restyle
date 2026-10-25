#!/bin/sh
# FreeBSD15 CI only; synthetic mock + divert shim inside isolated kernel jail.
set -eu
[ "$(uname -s)" = FreeBSD ] || { echo "SKIP: FreeBSD only"; exit 0; }
[ "$(id -u)" -eq 0 ] || { echo "ERROR: needs root in CI" >&2; exit 1; }
REPO=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TMP=$(mktemp -d /tmp/zapret2-composed.XXXXXXXX)
NAME="zapretmock$$"
J="$TMP/root"
ACTIVE=0
cleanup() {
    if [ "$ACTIVE" -eq 1 ]; then jail -r "$NAME" >/dev/null 2>&1 || true; fi
    rm -rf "$TMP"
}
trap cleanup EXIT HUP INT TERM
mkdir -m 0700 "$J"
printf "HOST_CANARY\n" > "$TMP/secret"
cc -Wall -Wextra -Werror -static -o "$J/probe" "$REPO/scripts/fixtures/lua-jail-native-boundary.c"
cc -Wall -Wextra -Werror -o "$J/mock" "$REPO/scripts/fixtures/lua-init-mock-engine.c"
cc -Wall -Wextra -Werror -fPIC -shared -o "$J/shim.so" "$REPO/scripts/fixtures/lua-init-no-network-shim.c"
cat > "$TMP/launcher.c" <<'EOS'
#include <sys/types.h>
#include <sys/sysctl.h>
#include <stdlib.h>
#include <unistd.h>
int main(void) {
    int jailed=0; size_t len=sizeof(jailed);
    if (sysctlbyname("security.jail.jailed",&jailed,&len,NULL,0) || jailed!=1) return 40;
    if (setenv("LD_PRELOAD","/shim.so",1)) return 41;
    char *const args[]={"/mock",NULL};
    execv("/mock",args);
    return 42;
}
EOS
cc -Wall -Wextra -Werror -o "$J/launcher" "$TMP/launcher.c"
chmod 0555 "$J/probe" "$J/mock" "$J/shim.so" "$J/launcher"
copy_base() {
    p="$1"
    case "$p" in /lib/*|/usr/lib/*|/libexec/*) ;; *) echo "ERROR: unexpected dependency $p" >&2; exit 1;; esac
    [ -f "$p" ] || exit 1
    resolved=$(realpath "$p")
    case "$resolved" in /lib/*|/usr/lib/*|/libexec/*) ;; *) echo "ERROR: dependency escape" >&2; exit 1;; esac
    mkdir -p "$J/$(dirname "$p")"
    cp -L "$p" "$J$p"
}
copy_base /libexec/ld-elf.so.1
for binary in "$J/mock" "$J/shim.so" "$J/launcher"; do
    ldd "$binary" > "$TMP/ldd"
    if grep -q "not found" "$TMP/ldd"; then echo "ERROR: unresolved dependency" >&2; exit 1; fi
    awk '/=> \// { for(i=1;i<=NF;i++) if($(i-1)=="=>") print $i } /^\// { print $1 }' "$TMP/ldd" > "$TMP/paths"
    while IFS= read -r path; do [ -z "$path" ] || copy_base "$path"; done < "$TMP/paths"
done
if "$J/probe" "$TMP/secret" >/dev/null 2>&1; then echo "ERROR: host probe false positive" >&2; exit 1; fi
jail -c "name=$NAME" "path=$J" persist "ip4=disable" "ip6=disable" "allow.raw_sockets=0" "allow.socket_af=0" "allow.mount=0" "allow.sysvipc=0" "exec.clean" >/dev/null
ACTIVE=1
jexec "$NAME" /probe "$TMP/secret" > "$TMP/boundary"
grep -Fxq JAIL_PRIVATE_ROOT_NO_IP_NO_RAW_SOCKET_PASS "$TMP/boundary"
if jexec "$NAME" /mock > "$TMP/unshimmed" 2>&1; then echo "ERROR: unshimmed mock passed" >&2; exit 1; fi
jexec "$NAME" /launcher > "$TMP/result"
grep -Fxq MOCK_LUA_INIT_REACHED_NO_NETWORK_SOCKET "$TMP/result"
jail -r "$NAME"
ACTIVE=0
if jls -N 2>/dev/null | grep -Fq "$NAME"; then echo "ERROR: jail survived teardown" >&2; exit 1; fi
echo "PASS: jailed synthetic divert shim + mock (NO REAL ENGINE OR LUA)"
