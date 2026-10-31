#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SOURCE="${ROOT}/stage0-target-opnsense-readonly.sh"
sh -n "$SOURCE"
for fixed in 'opnsense-version -a' 'pkg config ABI' 'pkg which' 'REPO_AUTOUPDATE=false' 'elfdump -d' 'REPO_OWNERSHIP=NOT_PROVEN_BY_THIS_PROBE' '/var/db/zapret2-restyle/FreeBSD.conf.backup' 'ldconfig -r' 'libgcc_s.so.1' 'libc++.so.1' 'ELF_RUNTIME_LINK_AND_CAPABILITY=NOT_PROVEN_BY_THIS_PROBE' 'REPO_LEGACY_TEMPLATE_SHAPE=EXACT_UNPROVEN' 'SIGNED_REPOSITORY_AND_TARGET_ABI=NOT_PROVEN_BY_THIS_PROBE'
do
    grep -Fq "$fixed" "$SOURCE" || { echo "FAIL: missing audit witness $fixed" >&2; exit 1; }
done
if grep -Eq '^[[:space:]]*(pkg (install|add|update|upgrade|remove|delete)|ipfw |configctl |rm |mv |cp |chmod |chown |ln |mkdir |touch )' "$SOURCE"; then
    echo 'FAIL: target probe contains a modifying command' >&2
    exit 1
fi
TMPROOT=$(mktemp -d)
trap 'rm -rf "$TMPROOT"' EXIT HUP INT TERM
sh "$SOURCE" >"$TMPROOT/negative.log" 2>&1
for marker in 'STAGE0_TARGET_PROBE=READ_ONLY' 'REPO_OWNERSHIP=NOT_PROVEN_BY_THIS_PROBE' 'STAGE0_TARGET_PROBE=END_READ_ONLY' 'ELF_RUNTIME_LINK_AND_CAPABILITY=NOT_PROVEN_BY_THIS_PROBE' 'SIGNED_REPOSITORY_AND_TARGET_ABI=NOT_PROVEN_BY_THIS_PROBE'
do
    grep -Fxq "$marker" "$TMPROOT/negative.log" || { echo "FAIL: missing negative marker $marker" >&2; exit 1; }
done
# Run a second negative fixture with a fabricated ldconfig cache. A cache
# entry alone must never become a claimed target-compatible provider.
mkdir "$TMPROOT/bin"
cat >"$TMPROOT/bin/ldconfig" <<'MOCK'
#!/bin/sh
[ "$1" = -r ] || exit 2
printf 'hint: libgcc_s.so.1 => /lib/libgcc_s.so.1\n'
MOCK
chmod 755 "$TMPROOT/bin/ldconfig"
PATH="$TMPROOT/bin:$PATH" sh "$SOURCE" >"$TMPROOT/mock.log" 2>&1
grep -Fxq 'SONAME_LDCONFIG_CACHE=libgcc_s.so.1:LISTED_UNVERIFIED' "$TMPROOT/mock.log" || {
    echo 'FAIL: cache candidate was not marked unverified' >&2; exit 1;
}
grep -Fxq 'ELF_RUNTIME_LINK_AND_CAPABILITY=NOT_PROVEN_BY_THIS_PROBE' "$TMPROOT/mock.log" || {
    echo 'FAIL: mock cache incorrectly qualified target ELF' >&2; exit 1;
}
printf '%s\n' 'PASS: read-only OPNsense Stage 0 target probe, six SONAMEs, unsafe config shape refusal, negative and mocked linker-cache fixtures'
