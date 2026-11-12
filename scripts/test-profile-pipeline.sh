#!/bin/sh

set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BACKEND="${REPO_ROOT}/src/opnsense/scripts/OPNsense/Zapret/backend"

# Source-fixture tests use an explicit Python interpreter; production uses
# the native policy-checked python_runtime.sh adapter.
BACKEND_DIR="${BACKEND}"
PYTHON_RUNTIME=$(command -v python3)
export BACKEND_DIR PYTHON_RUNTIME

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
for blank_strategy in '' "$(printf ' \t\n  ')"; do
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

# #1052 P0: observe the ACTUAL as-is Target Mode profile pipeline with
# valid native --blob= shorthand (not an unsupported <BLOB:...> placeholder).
# This is a source-stage witness, not a claim of final dvtws2 attribution.
fixture_strategy='--filter-tcp=443
--filter-l7=tls
--blob=http_iana_org
--lua-desync=fake'
auto_root="${TEST_ROOT}/p0-auto-actual"
mkdir -p "${auto_root}"
auto_count=$(profile_pipeline_parse "${auto_root}" 0 "${fixture_strategy}")
auto_count=$(profile_pipeline_target_mode "${auto_root}" "${auto_count}" auto "${registry}")
auto_count=$(profile_pipeline_normalize "${auto_root}" "${auto_count}")
# Existing implementation injects legacy <HOSTLIST:auto> as ordinary hostlist.
# P3 must deliberately update this assertion when removing that injection.
assert_equal 4 "${auto_count}" "as-is auto expanded profile count"
auto_no=1
for selected in '<HOSTLIST:youtube>' '<IPSET:telegram>' '<HOSTLIST:user>' '<HOSTLIST:auto>'; do
    grep -Fxq -- "${selected}" "${auto_root}/profile-${auto_no}.conf" ||
        fail "as-is auto profile ${auto_no} has wrong selector"
    grep -Fxq -- '--blob=http_iana_org' "${auto_root}/profile-${auto_no}.conf" ||
        fail "as-is auto profile ${auto_no} lost native BLOB shorthand"
    auto_no=$((auto_no + 1))
done

list_root="${TEST_ROOT}/p0-list-actual"
mkdir -p "${list_root}"
list_count=$(profile_pipeline_parse "${list_root}" 0 "${fixture_strategy}")
list_count=$(profile_pipeline_target_mode "${list_root}" "${list_count}" list "${registry}")
list_count=$(profile_pipeline_normalize "${list_root}" "${list_count}")
assert_equal 3 "${list_count}" "list mode expanded profile count"
if grep -Fxq -- '<HOSTLIST:auto>' "${list_root}/profile-3.conf"; then
    fail "list mode injected implicit Auto HOSTLIST"
fi

all_root="${TEST_ROOT}/p0-all-actual"
mkdir -p "${all_root}"
all_count=$(profile_pipeline_parse "${all_root}" 0 "${fixture_strategy}")
all_before=$(cat "${all_root}/profile-1.conf")
all_count=$(profile_pipeline_target_mode "${all_root}" "${all_count}" all "${registry}")
all_count=$(profile_pipeline_normalize "${all_root}" "${all_count}")
assert_equal 1 "${all_count}" "all mode profile count"
assert_equal "${all_before}" "$(cat "${all_root}/profile-1.conf")" "all mode strategy changed"

# Auto defaults are applied per ORIGINAL source profile, not globally:
# --new with an explicit HOSTLIST preserves its selector (and source order).
new_root="${TEST_ROOT}/p0-auto-explicit-new"
mkdir -p "${new_root}"
new_strategy='--filter-tcp=443
--filter-l7=tls
--blob=http_iana_org
--lua-desync=fake
--new=known-user
--filter-tcp=443
<HOSTLIST:user>
--lua-desync=fake'
new_count=$(profile_pipeline_parse "${new_root}" 0 "${new_strategy}")
assert_equal 2 "${new_count}" "source --new count"
new_count=$(profile_pipeline_target_mode "${new_root}" "${new_count}" auto "${registry}")
new_count=$(profile_pipeline_normalize "${new_root}" "${new_count}")
assert_equal 5 "${new_count}" "auto source and explicit native profile count"
grep -Fxq -- '--name=known-user' "${new_root}/profile-5.conf" ||
    fail "explicit named --new lost after auto expansion"
grep -Fxq -- '<HOSTLIST:user>' "${new_root}/profile-5.conf" ||
    fail "explicit source HOSTLIST lost after auto expansion"
if grep -Fxq -- '<HOSTLIST:auto>' "${new_root}/profile-5.conf"; then
    fail "auto mode injected shared list into explicit source"
fi

# A mixed HOSTLIST+IPSET SOURCE becomes two final profiles. P0 attribution
# MUST retain source identity; looking only at a final HOSTLIST row is unsafe.
mixed_root="${TEST_ROOT}/p0-source-mixed"
mkdir -p "${mixed_root}"
mixed_strategy='--filter-tcp=443
<HOSTLIST:youtube>
<IPSET:telegram>
--lua-desync=fake'
mixed_count=$(profile_pipeline_parse "${mixed_root}" 0 "${mixed_strategy}")
mixed_count=$(profile_pipeline_target_mode "${mixed_root}" "${mixed_count}" auto "${registry}")
mixed_count=$(profile_pipeline_normalize "${mixed_root}" "${mixed_count}")
assert_equal 2 "${mixed_count}" "mixed source expanded profile count"
grep -Fxq -- '<HOSTLIST:youtube>' "${mixed_root}/profile-1.conf" ||
    fail "mixed source HOSTLIST first-match order lost"
grep -Fxq -- '<IPSET:telegram>' "${mixed_root}/profile-2.conf" ||
    fail "mixed source IPSET second profile lost"

echo "P0_GENERATED_SOURCE_PROFILE_MATRIX=PASS"

echo "Profile pipeline tests passed."
