#!/bin/sh

set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BACKEND="${REPO_ROOT}/src/opnsense/scripts/OPNsense/Zapret/backend"

. "${BACKEND}/common.sh"
. "${BACKEND}/parser.sh"
. "${BACKEND}/registry.sh"
. "${BACKEND}/storage.sh"
. "${BACKEND}/targets.sh"
. "${BACKEND}/target_mode.sh"
. "${BACKEND}/profile_normalizer.sh"
. "${BACKEND}/profile_pipeline.sh"

TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/zapret-profile-pipeline.XXXXXX")
trap 'rm -rf "${TEST_ROOT}"' EXIT HUP INT TERM

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

assert_equal()
{
    [ "$1" = "$2" ] || fail "$3: expected '$1', got '$2'"
}

strategy='--filter-tcp=443
<HOSTLIST:youtube>
<IPSET:telegram>
--filter-l7=tls'
registry="${TEST_ROOT}/target-registry.tsv"

count=$(profile_pipeline_parse "${TEST_ROOT}" 0 "${strategy}")
assert_equal 1 "${count}" "parser count"

count=$(profile_pipeline_registry "${TEST_ROOT}" "${count}" "${registry}")
assert_equal 1 "${count}" "registry count"
[ -s "${registry}" ] || fail "registry was not created"

count=$(profile_pipeline_target_mode "${TEST_ROOT}" "${count}" list "${registry}")
assert_equal 1 "${count}" "Target Mode count"

count=$(profile_pipeline_normalize "${TEST_ROOT}" "${count}")
assert_equal 2 "${count}" "normalizer count"

count=$(profile_pipeline_index "${TEST_ROOT}" "${count}")
assert_equal 2 "${count}" "index count"
[ -s "${TEST_ROOT}/profile-1.placeholders" ] || fail "profile 1 index is missing"
[ -s "${TEST_ROOT}/profile-2.placeholders" ] || fail "profile 2 index is missing"

if profile_pipeline_parse "${TEST_ROOT}" 1 "${strategy}" >/dev/null 2>&1; then
    fail "parser accepted a non-zero initial count"
fi

if profile_pipeline_registry "${TEST_ROOT}" invalid "${registry}" >/dev/null 2>&1; then
    fail "registry accepted an invalid count"
fi

echo "Profile pipeline tests passed."
