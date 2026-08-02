#!/bin/sh

set -eu

SETUP_SH="${SETUP_SH:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)/src/opnsense/scripts/OPNsense/Zapret/setup.sh}"
TMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/setup-release-test.XXXXXX")
trap 'rm -rf "${TMP_ROOT}"' EXIT INT TERM HUP

STATE_DIR="${TMP_ROOT}/state"
RUN_DIR="${TMP_ROOT}/run"
FIXTURE="${TMP_ROOT}/releases.json"
FETCH_MOCK="${TMP_ROOT}/fetch"
LOCKF_MOCK="${TMP_ROOT}/lockf"
FETCH_CALLS="${TMP_ROOT}/fetch.calls"
SETUP_LOCK_ARGS="${TMP_ROOT}/setup-lock.args"
CACHE="${STATE_DIR}/releases.cache"
PHP_BIN=$(command -v php)
FIND_BIN=$(command -v find)

cat > "${FIXTURE}" <<'JSON'
[
 {"tag_name":"v1.0.4","draft":false,"prerelease":false},
 {"tag_name":"v1.0.3","draft":false,"prerelease":false},
 {"tag_name":"v0.9.5.2","draft":false,"prerelease":false},
 {"tag_name":"v0.9.5.1","draft":false,"prerelease":false},
 {"tag_name":"v0.9.5","draft":false,"prerelease":false},
 {"tag_name":"v1.0.4","draft":false,"prerelease":false},
 {"tag_name":"v2.0.0-rc1","draft":false,"prerelease":false},
 {"tag_name":"v2.0.0","draft":true,"prerelease":false},
 {"tag_name":"v1.1.0","draft":false,"prerelease":true}
]
JSON

cat > "${FETCH_MOCK}" <<'EOF_FETCH'
#!/bin/sh
set -eu
printf 'fetch\n' >> "${TEST_FETCH_CALLS}"
[ "${TEST_FETCH_FAIL:-0}" = 0 ] || exit 1
output=
while [ "$#" -gt 0 ]; do
    case "$1" in
        -o) output=$2; shift 2 ;;
        -T) shift 2 ;;
        -q|--user-agent=*) shift ;;
        https://*) shift ;;
        *) echo "unexpected fetch argument: $1" >&2; exit 1 ;;
    esac
done
cp "${TEST_RELEASE_FIXTURE}" "${output}"
EOF_FETCH
chmod +x "${FETCH_MOCK}"

cat > "${LOCKF_MOCK}" <<'EOF_LOCK'
#!/bin/sh
set -eu
[ "$1" = -s ] && shift
[ "$1" = -t ] && shift 2
lock_file=$1
shift
case "${lock_file}" in
    *releases.lock) exec "$@" ;;
    *setup.lock) printf '%s\n' "$@" > "${TEST_SETUP_LOCK_ARGS}" ;;
    *) exit 1 ;;
esac
EOF_LOCK
chmod +x "${LOCKF_MOCK}"

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

run_setup()
{
    TEST_RELEASE_FIXTURE="${FIXTURE}" \
    TEST_FETCH_CALLS="${FETCH_CALLS}" \
    TEST_FETCH_FAIL="${TEST_FETCH_FAIL:-0}" \
    TEST_SETUP_LOCK_ARGS="${SETUP_LOCK_ARGS}" \
    FETCH_BIN="${FETCH_MOCK}" \
    PHP_BIN="${PHP_BIN}" \
    FIND_BIN="${FIND_BIN}" \
    LOCKF_BIN="${LOCKF_MOCK}" \
    STATE_DIR="${STATE_DIR}" \
    RUN_DIR="${RUN_DIR}" \
    RELEASE_CACHE_TTL_MINUTES=60 \
    TMPDIR="${TMP_ROOT}" \
    "${SETUP_SH}" "$@"
}

EXPECTED='v1.0.4
v1.0.3
v0.9.5.2
v0.9.5.1'

[ "$(run_setup show)" = "${EXPECTED}" ] || fail "first show returned wrong releases"
[ "$(wc -l < "${FETCH_CALLS}" | tr -d ' ')" -eq 1 ] || fail "first show did not fetch exactly once"
[ -s "${CACHE}" ] || fail "cache was not written"
[ "$(grep -Fc v1.0.4 "${CACHE}")" -eq 1 ] || fail "cache did not deduplicate tags"

[ "$(run_setup show)" = "${EXPECTED}" ] || fail "fresh cache changed output"
[ "$(wc -l < "${FETCH_CALLS}" | tr -d ' ')" -eq 1 ] || fail "fresh cache caused another fetch"

run_setup install v1.0.3
[ "$(tail -2 "${SETUP_LOCK_ARGS}")" = 'install-locked
v1.0.3' ] || fail "selected tag was not passed through setup lock"
[ "$(wc -l < "${FETCH_CALLS}" | tr -d ' ')" -eq 1 ] || fail "exact install repeated release API request"

run_setup
[ "$(tail -2 "${SETUP_LOCK_ARGS}")" = 'install-locked
v1.0.4' ] || fail "default install did not select latest cached tag"

# A failed stale refresh returns the old validated cache and does not replace it.
touch -t 200001010000 "${CACHE}"
CACHE_BEFORE=$(cat "${CACHE}")
TEST_FETCH_FAIL=1
export TEST_FETCH_FAIL
[ "$(run_setup show 2>/dev/null)" = "${EXPECTED}" ] || fail "stale cache fallback failed"
[ "$(cat "${CACHE}")" = "${CACHE_BEFORE}" ] || fail "failed refresh changed cache"
unset TEST_FETCH_FAIL

run_setup install v9.9.9 >/dev/null 2>&1 && fail "unpublished tag was accepted"
run_setup install release-1 >/dev/null 2>&1 && fail "malformed tag was accepted"
run_setup show extra >/dev/null 2>&1 && fail "show accepted arguments"

rm -f "${CACHE}"
TEST_FETCH_FAIL=1
export TEST_FETCH_FAIL
run_setup show >/dev/null 2>&1 && fail "missing cache plus API failure reported success"
unset TEST_FETCH_FAIL

grep -Fq 'RELEASE_CACHE="${RELEASE_CACHE:-${STATE_DIR}/releases.cache}"' "${SETUP_SH}" || fail "cache path missing"
grep -Fq 'RELEASE_LOCK_FILE="${RELEASE_LOCK_FILE:-${RUN_DIR}/releases.lock}"' "${SETUP_SH}" || fail "cache lock missing"
grep -Fq 'mv -f "${_release_list}" "${RELEASE_CACHE}"' "${SETUP_SH}" || fail "atomic cache replacement missing"
grep -Fq 'git -C "${ZAPRET_DIR}" fetch --depth 1 origin tag "${_zapret_ref}"' "${SETUP_SH}" || fail "existing-tree exact tag fetch missing"
grep -Fq 'git clone --depth 1 --branch "${_zapret_ref}"' "${SETUP_SH}" || fail "new-tree exact tag clone missing"

echo "PASS: setup release cache and selection contract"
