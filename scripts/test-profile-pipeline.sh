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

named_strategy='--filter-tcp=443
--filter-l7=tls
--new=named-udp
--filter-udp=443
--filter-l7=quic'
named_root="${TEST_ROOT}/named-profiles"
mkdir -p "${named_root}"
named_count=$(profile_pipeline_parse "${named_root}" 0 "${named_strategy}")
assert_equal 2 "${named_count}" "named native --new count"
grep -qx -- '--name=named-udp' "${named_root}/profile-2.conf" ||
    fail "native named --new did not preserve the new profile name"
if grep -q -- '--name=named-udp' "${named_root}/profile-1.conf"; then
    fail "native named --new escaped into previous profile"
fi
named_count=$(profile_pipeline_normalize "${named_root}" "${named_count}")
assert_equal 2 "${named_count}" "named profiles after target normalization"

blank_root="${TEST_ROOT}/blank"
mkdir -p "${blank_root}"
# Reused workdir: parser zero must remove an earlier positive profile.
assert_equal 1 "$(profile_pipeline_parse "${blank_root}" 0 '--filter-tcp=443')" "blank fixture setup"
for blank_strategy in '' "$(printf ' \\t\\n  ')"; do
    blank_count=$(profile_pipeline_parse "${blank_root}" 0 "${blank_strategy}")
    assert_equal 0 "${blank_count}" "empty parser count"
    [ ! -e "${blank_root}/profile-1.conf" ] || fail "ghost ordinary profile"
    assert_equal 0 "$(cat "${blank_root}/profile-count")" "zero parser artifact"
    blank_count=$(profile_pipeline_registry "${blank_root}" "${blank_count}" "${blank_root}/registry.tsv")
    blank_count=$(profile_pipeline_target_mode "${blank_root}" "${blank_count}" all "${blank_root}/registry.tsv")
    blank_count=$(profile_pipeline_normalize "${blank_root}" "${blank_count}")
    blank_count=$(profile_pipeline_index "${blank_root}" "${blank_count}")
    assert_equal 0 "${blank_count}" "zero passed through complete pipeline"
    if target_mode_apply_all "${blank_root}" 0 invalid "${blank_root}/registry.tsv" >/dev/null 2>&1; then
        fail "zero profile bypassed invalid Target Mode"
    fi
done
for malformed in '--new' '--new=bad' '--filter-tcp=443
--new'; do
    if profile_pipeline_parse "${blank_root}" 0 "${malformed}" >/dev/null 2>&1; then
        fail "empty --new boundary accepted: ${malformed}"
    fi
done

echo "Profile pipeline tests passed."
