#!/bin/sh

set -eu

SETUP_SH="${SETUP_SH:-$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/setup.sh}"
TMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/setup-release-test.XXXXXX")
TEST_STATE_DIR="${TMP_ROOT}/state"
TEST_RUN_DIR="${TMP_ROOT}/run"
trap 'rm -rf "${TMP_ROOT}"' EXIT INT TERM HUP

FIXTURE="${TMP_ROOT}/releases.json"
FETCH_MOCK="${TMP_ROOT}/fetch"
FETCH_CALLS="${TMP_ROOT}/fetch.calls"
LOCKF_MOCK="${TMP_ROOT}/lockf"
LOCK_ARGS="${TMP_ROOT}/lock.args"
PHP_TEST_BIN=$(command -v php)
FIND_TEST_BIN=$(command -v find)
CACHE_FILE="${TEST_STATE_DIR}/releases.cache"

cat > "${FIXTURE}" <<'JSON_EOF'
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
JSON_EOF

cat > "${FETCH_MOCK}" <<'FETCH_EOF'
#!/bin/sh
set -eu
printf '%s\n' fetch >> "${SETUP_FETCH_CALLS}"
[ "${SETUP_FETCH_FAIL:-0}" = 0 ] || exit 1
_output=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        -o) _output="$2"; shift 2 ;;
        -T) shift 2 ;;
        -q|--user-agent=*) shift ;;
        https://*) shift ;;
        *) echo "unexpected fetch argument: $1" >&2; exit 1 ;;
    esac
done
[ -n "${_output}" ] || exit 1
cp "${SETUP_RELEASE_FIXTURE}" "${_output}"
FETCH_EOF
chmod +x "${FETCH_MOCK}"

cat > "${LOCKF_MOCK}" <<'LOCKF_EOF'
#!/bin/sh
set -eu
[ "$1" = -s ] && shift
[ "$1" = -t ] && shift 2
_lock_file="$1"
shift
case "${_lock_file}" in
    *releases.lock)
        exec "$@"
        ;;
    *setup.lock)
        printf '%s\n' "$@" > "${SETUP_LOCK_ARGS}"
        ;;
    *)
        echo "unexpected lock file: ${_lock_file}" >&2
        exit 1
        ;;
esac
LOCKF_EOF
chmod +x "${LOCKF_MOCK}"

assert_equals()
{
    _expected="$1"
    _actual="$2"
    _message="$3"
    if [ "${_expected}" != "${_actual}" ]; then
        echo "FAIL: ${_message}" >&2
        echo "Expected:" >&2
        printf '%s\n' "${_expected}" >&2
        echo "Actual:" >&2
        printf '%s\n' "${_actual}" >&2
        exit 1
    fi
}

run_setup()
{
    SETUP_RELEASE_FIXTURE="${FIXTURE}" \
    SETUP_FETCH_CALLS="${FETCH_CALLS}" \
    SETUP_FETCH_FAIL="${SETUP_FETCH_FAIL:-0}" \
    FETCH_BIN="${FETCH_MOCK}" \
    PHP_BIN="${PHP_TEST_BIN}" \
    FIND_BIN="${FIND_TEST_BIN}" \
    LOCKF_BIN="${LOCKF_MOCK}" \
    SETUP_LOCK_ARGS="${LOCK_ARGS}" \
    STATE_DIR="${TEST_STATE_DIR}" \
    RUN_DIR="${TEST_RUN_DIR}" \
    RELEASE_CACHE_TTL_MINUTES=60 \
    TMPDIR="${TMP_ROOT}" \
    "${SETUP_SH}" "$@"
}

SHOW_OUTPUT=$(run_setup show)
assert_equals "v1.0.4
v1.0.3
v0.9.5.2
v0.9.5.1" "${SHOW_OUTPUT}" "show must print the four latest stable releases"
[ "$(wc -l < "${FETCH_CALLS}" | tr -d ' ')" -eq 1 ] || { echo "FAIL: first show must fetch once" >&2; exit 1; }
[ -s "${CACHE_FILE}" ] || { echo "FAIL: release cache was not written" >&2; exit 1; }
[ "$(grep -Fc v1.0.4 "${CACHE_FILE}")" -eq 1 ] || { echo "FAIL: cache did not deduplicate releases" >&2; exit 1; }

SECOND_SHOW=$(run_setup show)
assert_equals "${SHOW_OUTPUT}" "${SECOND_SHOW}" "fresh cache changed release output"
[ "$(wc -l < "${FETCH_CALLS}" | tr -d ' ')" -eq 1 ] || { echo "FAIL: fresh cache caused another GitHub request" >&2; exit 1; }

run_setup install v1.0.3
INSTALL_ARGS=$(tail -2 "${LOCK_ARGS}")
assert_equals "install-locked
v1.0.3" "${INSTALL_ARGS}" "install must pass the selected version through lockf"
[ "$(wc -l < "${FETCH_CALLS}" | tr -d ' ')" -eq 1 ] || { echo "FAIL: exact cached install caused another GitHub request" >&2; exit 1; }

run_setup
DEFAULT_ARGS=$(tail -2 "${LOCK_ARGS}")
assert_equals "install-locked
v1.0.4" "${DEFAULT_ARGS}" "no-argument setup must select the latest stable release"
[ "$(wc -l < "${FETCH_CALLS}" | tr -d ' ')" -eq 1 ] || { echo "FAIL: latest install ignored fresh cache" >&2; exit 1; }

# A stale cache survives a temporary API failure and remains usable by show.
touch -t 200001010000 "${CACHE_FILE}"
SETUP_FETCH_FAIL=1
export SETUP_FETCH_FAIL
STALE_SHOW=$(run_setup show 2>/dev/null)
assert_equals "${SHOW_OUTPUT}" "${STALE_SHOW}" "stale cache fallback did not preserve releases"
[ "$(wc -l < "${FETCH_CALLS}" | tr -d ' ')" -eq 2 ] || { echo "FAIL: stale cache refresh attempt count is wrong" >&2; exit 1; }
unset SETUP_FETCH_FAIL

# Failed refresh must never overwrite the validated stale cache.
assert_equals "v1.0.4
v1.0.3
v0.9.5.2
v0.9.5.1
v0.9.5" "$(cat "${CACHE_FILE}")" "failed refresh changed the cache"

if run_setup install v9.9.9 >/dev/null 2>&1; then
    echo "FAIL: unpublhed release must be rejected" >&2
    exit 1
fi
if run_setup install release-1 >/dev/null 2>&1; then
    echo "FAIL: invalid release syntax must be rejected" >&2
    exit 1
fi
if run_setup show extra >/dev/null 2>&1; then
    echo "FAIL: show arguments must be rejected" >&2
    exit 1
fi

# With no cache and no API, discovery must fail visibly.
rm -f "${CACHE_FILE}"
SETUP_FETCH_FAIL=1
export SETUP_FETCH_FAIL
if run_setup show >/dev/null 2>&1; then
    echo "FAIL: empty-cache API failure must not report success" >&2
    exit 1
fi
unset SETUP_FETCH_FAIL

HELP_OUTPUT=$("${SETUP_SH}" --help)
printf '%s\n' "${HELP_OUTPUT}" | grep -Fq 'setup.sh install [VERSION]'
printf '%s\n' "${HELP_OUTPUT}" | grep -Fq 'show'
printf '%s\n' "${HELP_OUTPUT}" | grep -Fq 'reinstallation, upgrade, or downgrade'

if grep -Eq '(^|[[:space:]])-H([[:space:]]|$)' "${SETUP_SH}"; then
    echo "FAIL: setup must not use curl-style -H with FreeBSD fetch" >&2
    exit 1
fi
grep -Fq -- '--user-agent=os-zapret2-restyle' "${SETUP_SH}"
grep -Fq 'RELEASE_CACHE="${RELEASE_CACHE:-${STATE_DIR}/releases.cache}"' "${SETUP_SH}"
grep -Fq 'RELEASE_LOCK_FILE="${RELEASE_LOCK_FILE:-${RUN_DIR}/releases.lock}"' "${SETUP_SH}"
grep -Fq 'mv -f "${_release_list}" "${RELEASE_CACHE}"' "${SETUP_SH}"
grep -Fq 'git -C "${ZAPRET_DIR}" fetch --depth 1 origin tag "${_zapret_ref}"' "${SETUP_SH}"
grep -Fq 'git clone --depth 1 --branch "${_zapret_ref}"' "${SETUP_SH}"

echo "setup release cache and selection tests passed"
