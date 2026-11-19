#!/bin/sh
# Fail-closed private-curl signed version drift; fixture never touches FreeBSD.
set -eu
BASE=$(mktemp -d /tmp/curl-drift-test.XXXXXXXX)
trap 'rm -rf "$BASE"' EXIT HUP INT TERM
mkdir -p "$BASE/bin" "$BASE/fixture/usr/local/bin"
printf 'mock ELF bytes for digest only\n' > "$BASE/fixture/usr/local/bin/curl-impersonate"
printf 'fixture Chrome wrapper\n' > "$BASE/fixture/usr/local/bin/curl_chrome150"
tar -cf "$BASE/curl-impersonate-fixture.pkg" -C "$BASE/fixture" .
cat > "$BASE/bin/pkg" <<'EOF'
#!/bin/sh
set -eu
mode=none
output=
need_output=0
for arg in "$@"; do
    if [ "$need_output" -eq 1 ]; then
        case "$arg" in REPOS_DIR=*) ;; *) output=$arg ;; esac
        need_output=0
    elif [ "$arg" = -o ]; then
        need_output=1
    fi
    case "$arg" in
        update|rquery|fetch) mode=$arg ;;
    esac
done
printf '%s\n' "$mode" >> "$TEST_CALLS"
case "$mode" in
    update) exit 0 ;;
    rquery) printf '2.3.2\n'; exit 0 ;;
    fetch) [ -n "$output" ] && cp "$TEST_ARCHIVE" "$output/curl-impersonate-fixture.pkg" ;;
    *) exit 92 ;;
esac
EOF
cat > "$BASE/bin/sha256" <<'EOF'
#!/bin/sh
[ "$1" = -q ] && shift
sha256sum "$1" | cut -d' ' -f1
EOF
chmod 755 "$BASE/bin/pkg" "$BASE/bin/sha256"
export PATH="$BASE/bin:$PATH" TEST_ARCHIVE="$BASE/curl-impersonate-fixture.pkg" TEST_CALLS="$BASE/calls"
BUILDER=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)/scripts/build-curl-impersonate.sh
run() {
    : > "$TEST_CALLS"
    set +e
    ZAPRET2_CURL_PIN_VERSION=2.2.3_1 ZAPRET2_CURL_SIGNED_DISCOVERY="$1" \
        sh "$BUILDER" "$BASE/dest" > "$BASE/out" 2> "$BASE/err"
    result=$?
    set -e
    [ "$result" -ne 0 ] || { echo 'FAIL: signed-version mismatch accepted' >&2; exit 1; }
    grep -Fq 'ERROR: pinned curl-impersonate 2.2.3_1 unavailable (got 2.3.2)' "$BASE/err" || {
        echo 'FAIL: pinned-source refusal missing' >&2; exit 1;
    }
}
run 0
! grep -qx fetch "$TEST_CALLS" || { echo 'FAIL: unrequested package discovery' >&2; exit 1; }
! grep -q '^CURL_SIGNED_LATEST_OBSERVATION=' "$BASE/err" || {
    echo 'FAIL: unsolicited provenance claim' >&2; exit 1;
}
run 1
grep -qx fetch "$TEST_CALLS"
pkg_sha=$(sha256sum "$TEST_ARCHIVE" | cut -d' ' -f1)
elf_sha=$(sha256sum "$BASE/fixture/usr/local/bin/curl-impersonate" | cut -d' ' -f1)
grep -Fx "CURL_SIGNED_LATEST_OBSERVATION=unqualified version=2.3.2 source_pkg_sha256=$pkg_sha elf_sha256=$elf_sha chrome_profile=chrome150" "$BASE/err"
[ ! -e "$BASE/dest" ] || { echo 'FAIL: exploratory binary escaped into production destination' >&2; exit 1; }
printf '%s\n' 'PASS: signed-source observation never authorizes an unpinned build'