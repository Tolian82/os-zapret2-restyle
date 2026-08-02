#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SETUP_SH="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/setup.sh"
TMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/setup-release-test.XXXXXX")
trap 'rm -rf "${TMP_ROOT}"' EXIT INT TERM HUP

FIXTURE="${TMP_ROOT}/releases.json"
FETCH_MOCK="${TMP_ROOT}/fetch"
LOCKF_MOCK="${TMP_ROOT}/lockf"
LOCK_ARGS="${TMP_ROOT}/lock.args"

cat > "${FIXTURE}" <<'JSON_EOF'
[
  {
    "tag_name": "v1.0.4",
    "draft": false,
    "prerelease": false
  },
  {
    "tag_name": "v1.0.3",
    "draft": false,
    "prerelease": false
  },
  {
    "tag_name": "v0.9.5.2",
    "draft": false,
    "prerelease": false
  },
  {
    "tag_name": "v0.9.5.1",
    "draft": false,
    "prerelease": false
  },
  {
    "tag_name": "v0.9.5",
    "draft": false,
    "prerelease": false
  },
  {
    "tag_name": "v2.0.0-rc1",
    "draft": false,
    "prerelease": false
  },
  {
    "tag_name": "v2.0.0",
    "draft": true,
    "prerelease": false
  },
  {
    "tag_name": "v1.1.0",
    "draft": false,
    "prerelease": true
  }
]
JSON_EOF

cat > "${FETCH_MOCK}" <<'FETCH_EOF'
#!/bin/sh
set -eu

_output=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        -o)
            _output="$2"
            shift 2
            ;;
        -H|-T)
            shift 2
            ;;
        -q)
            shift
            ;;
        *)
            shift
            ;;
    esac
done

[ -n "${_output}" ] || exit 1
cp "${SETUP_RELEASE_FIXTURE}" "${_output}"
FETCH_EOF
chmod +x "${FETCH_MOCK}"

cat > "${LOCKF_MOCK}" <<'LOCKF_EOF'
#!/bin/sh
set -eu
printf '%s\n' "$@" > "${SETUP_LOCK_ARGS}"
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

SHOW_OUTPUT=$(SETUP_RELEASE_FIXTURE="${FIXTURE}" FETCH_BIN="${FETCH_MOCK}" \
    TMPDIR="${TMP_ROOT}" "${SETUP_SH}" show)
assert_equals "v1.0.4
v1.0.3
v0.9.5.2
v0.9.5.1" "${SHOW_OUTPUT}" "show must print the four latest stable releases"

HELP_OUTPUT=$("${SETUP_SH}" --help)
printf '%s\n' "${HELP_OUTPUT}" | grep -Fq 'setup.sh install [VERSION]'
printf '%s\n' "${HELP_OUTPUT}" | grep -Fq 'show'
printf '%s\n' "${HELP_OUTPUT}" | grep -Fq 'reinstallation, upgrade, or downgrade'

SETUP_RELEASE_FIXTURE="${FIXTURE}" FETCH_BIN="${FETCH_MOCK}" \
    LOCKF_BIN="${LOCKF_MOCK}" SETUP_LOCK_ARGS="${LOCK_ARGS}" \
    TMPDIR="${TMP_ROOT}" "${SETUP_SH}" install v1.0.3
INSTALL_ARGS=$(tail -2 "${LOCK_ARGS}")
assert_equals "install-locked
v1.0.3" "${INSTALL_ARGS}" "install must pass the selected version through lockf"

SETUP_RELEASE_FIXTURE="${FIXTURE}" FETCH_BIN="${FETCH_MOCK}" \
    LOCKF_BIN="${LOCKF_MOCK}" SETUP_LOCK_ARGS="${LOCK_ARGS}" \
    TMPDIR="${TMP_ROOT}" "${SETUP_SH}"
DEFAULT_ARGS=$(tail -2 "${LOCK_ARGS}")
assert_equals "install-locked
v1.0.4" "${DEFAULT_ARGS}" "no-argument setup must select the latest stable release"

if SETUP_RELEASE_FIXTURE="${FIXTURE}" FETCH_BIN="${FETCH_MOCK}" \
    LOCKF_BIN="${LOCKF_MOCK}" SETUP_LOCK_ARGS="${LOCK_ARGS}" \
    TMPDIR="${TMP_ROOT}" "${SETUP_SH}" install v9.9.9 >/dev/null 2>&1; then
    echo "FAIL: unpublished release must be rejected" >&2
    exit 1
fi

if SETUP_RELEASE_FIXTURE="${FIXTURE}" FETCH_BIN="${FETCH_MOCK}" \
    LOCKF_BIN="${LOCKF_MOCK}" SETUP_LOCK_ARGS="${LOCK_ARGS}" \
    TMPDIR="${TMP_ROOT}" "${SETUP_SH}" install release-1 >/dev/null 2>&1; then
    echo "FAIL: invalid release syntax must be rejected" >&2
    exit 1
fi

if "${SETUP_SH}" show extra >/dev/null 2>&1; then
    echo "FAIL: show arguments must be rejected" >&2
    exit 1
fi

# Static contract: the resolved version must control both checkout paths.
grep -Fq 'git -C "${ZAPRET_DIR}" fetch --depth 1 origin tag "${_zapret_ref}"' "${SETUP_SH}"
grep -Fq 'git clone --depth 1 --branch "${_zapret_ref}"' "${SETUP_SH}"

echo "setup release selection tests passed"
