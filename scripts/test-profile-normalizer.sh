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

TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/zapret-profile-normalizer.XXXXXX")
trap 'rm -rf "${TEST_ROOT}"' EXIT HUP INT TERM

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

assert_equal()
{
    expected=$1
    actual=$2
    label=$3

    [ "${expected}" = "${actual}" ] ||
        fail "${label}: expected '${expected}', got '${actual}'"
}

assert_file_equal()
{
    expected=$1
    actual=$2
    label=$3

    cmp -s "${expected}" "${actual}" || {
        echo "--- expected: ${expected}" >&2
        cat "${expected}" >&2
        echo "--- actual: ${actual}" >&2
        cat "${actual}" >&2
        fail "${label}"
    }
}

parse_and_normalize()
{
    case_name=$1
    strategy=$2
    case_dir="${TEST_ROOT}/${case_name}"

    mkdir -p "${case_dir}"
    parsed_count=$(parser_parse "${strategy}" "${case_dir}")
    profile_normalizer_normalize_all "${case_dir}" "${parsed_count}"
}

test_no_selector()
{
    strategy='--filter-tcp=443
--filter-l7=tls'
    count=$(parse_and_normalize no-selector "${strategy}")

    assert_equal 1 "${count}" "profile without selector count"
    printf '%s\n' "${strategy}" > "${TEST_ROOT}/no-selector/expected.conf"
    assert_file_equal \
        "${TEST_ROOT}/no-selector/expected.conf" \
        "${TEST_ROOT}/no-selector/profile-1.conf" \
        "profile without selector changed"
}

test_single_hostlist()
{
    strategy='--filter-tcp=443
<HOSTLIST:youtube>
--filter-l7=tls'
    count=$(parse_and_normalize single-hostlist "${strategy}")

    assert_equal 1 "${count}" "single HOSTLIST count"
    printf '%s\n' "${strategy}" > "${TEST_ROOT}/single-hostlist/expected.conf"
    assert_file_equal \
        "${TEST_ROOT}/single-hostlist/expected.conf" \
        "${TEST_ROOT}/single-hostlist/profile-1.conf" \
        "single HOSTLIST profile changed"
}

test_single_ipset()
{
    strategy='--filter-tcp=443
<IPSET:telegram>
--filter-l7=unknown'
    count=$(parse_and_normalize single-ipset "${strategy}")

    assert_equal 1 "${count}" "single IPSET count"
    printf '%s\n' "${strategy}" > "${TEST_ROOT}/single-ipset/expected.conf"
    assert_file_equal \
        "${TEST_ROOT}/single-ipset/expected.conf" \
        "${TEST_ROOT}/single-ipset/profile-1.conf" \
        "single IPSET profile changed"
}

test_mixed_selectors()
{
    strategy='--filter-tcp=80,443
<IPSET:telegram>
<HOSTLIST:user>
--filter-l7=unknown
--lua-desync=fake'
    count=$(parse_and_normalize mixed-selectors "${strategy}")

    assert_equal 2 "${count}" "mixed selector count"

    cat > "${TEST_ROOT}/mixed-selectors/expected-1.conf" <<'EXPECTED'
--filter-tcp=80,443
<IPSET:telegram>

--filter-l7=unknown
--lua-desync=fake
EXPECTED
    cat > "${TEST_ROOT}/mixed-selectors/expected-2.conf" <<'EXPECTED'
--filter-tcp=80,443

<HOSTLIST:user>
--filter-l7=unknown
--lua-desync=fake
EXPECTED

    assert_file_equal \
        "${TEST_ROOT}/mixed-selectors/expected-1.conf" \
        "${TEST_ROOT}/mixed-selectors/profile-1.conf" \
        "first mixed selector profile differs"
    assert_file_equal \
        "${TEST_ROOT}/mixed-selectors/expected-2.conf" \
        "${TEST_ROOT}/mixed-selectors/profile-2.conf" \
        "second mixed selector profile differs"
}

test_same_family_and_three_selectors()
{
    strategy='<HOSTLIST:youtube>
--filter-tcp=443
<HOSTLIST:user>
<IPSET:telegram>'
    count=$(parse_and_normalize three-selectors "${strategy}")

    assert_equal 3 "${count}" "three selector count"
    grep -qx '<HOSTLIST:youtube>' "${TEST_ROOT}/three-selectors/profile-1.conf" ||
        fail "first selector order was not preserved"
    grep -qx '<HOSTLIST:user>' "${TEST_ROOT}/three-selectors/profile-2.conf" ||
        fail "second selector order was not preserved"
    grep -qx '<IPSET:telegram>' "${TEST_ROOT}/three-selectors/profile-3.conf" ||
        fail "third selector order was not preserved"

    for profile in "${TEST_ROOT}/three-selectors"/profile-*.conf; do
        selector_count=$(grep -Ec '<(HOSTLIST|IPSET):' "${profile}" || true)
        assert_equal 1 "${selector_count}" "selector count in ${profile}"
        grep -qx -- '--filter-tcp=443' "${profile}" ||
            fail "shared strategy line missing from ${profile}"
    done
}

test_user_new_boundaries()
{
    strategy='--filter-tcp=80
<HOSTLIST:youtube>

--new

--filter-tcp=443
<IPSET:telegram>
<HOSTLIST:user>'
    count=$(parse_and_normalize user-new "${strategy}")

    assert_equal 3 "${count}" "user --new expansion count"
    grep -qx '<HOSTLIST:youtube>' "${TEST_ROOT}/user-new/profile-1.conf" ||
        fail "first user profile was reordered"
    grep -qx '<IPSET:telegram>' "${TEST_ROOT}/user-new/profile-2.conf" ||
        fail "first generated profile has wrong selector"
    grep -qx '<HOSTLIST:user>' "${TEST_ROOT}/user-new/profile-3.conf" ||
        fail "second generated profile has wrong selector"
}

test_resolved_runtime_profiles()
{
    strategy='--filter-tcp=80,443
<IPSET:telegram>
<HOSTLIST:user>
--filter-l7=unknown'
    case_dir="${TEST_ROOT}/resolved-runtime"
    managed_source="${case_dir}/managed-source"
    managed_reference="/usr/local/etc/zapret2/runtime-v2/managed"
    runtime_root="${case_dir}/runtime"
    output="${case_dir}/traffic.targets.conf"

    mkdir -p "${case_dir}" "${runtime_root}"
    parsed_count=$(parser_parse "${strategy}" "${case_dir}")
    count=$(profile_normalizer_normalize_all "${case_dir}" "${parsed_count}")
    registry_build "${case_dir}/registry.tsv"
    storage_catalog_build "${case_dir}/storage.tsv"
    targets_prepare_managed         "${managed_source}"         'youtube.com'         '149.154.160.0/20'         'example.com'
    targets_index_all "${case_dir}" "${count}"
    targets_resolve_all_mapped         "${case_dir}"         "${count}"         "${case_dir}/registry.tsv"         "${case_dir}/storage.tsv"         "${managed_source}"         "${managed_reference}"         "${runtime_root}"         "${output}"

    assert_equal 1 "$(grep -c '^--new$' "${output}")"         "resolved runtime --new count"
    assert_equal 1 "$(grep -c '^--ipset=' "${output}")"         "resolved runtime IPSET count"
    assert_equal 1 "$(grep -c '^--hostlist=' "${output}")"         "resolved runtime HOSTLIST count"
    assert_equal 2 "$(grep -c '^--filter-tcp=80,443$' "${output}")"         "shared filter copy count"
    assert_equal 2 "$(grep -c '^--filter-l7=unknown$' "${output}")"         "shared L7 copy count"

    awk '
        /^--new$/ {
            if (target_count != 1 || target_type != "ipset")
                exit 1
            target_count = 0
            target_type = ""
            next
        }
        /^--ipset=/ {
            target_count++
            target_type = "ipset"
        }
        /^--hostlist=/ {
            target_count++
            target_type = "hostlist"
        }
        END {
            if (target_count != 1 || target_type != "hostlist")
                exit 1
        }
    ' "${output}" || fail "resolved profiles do not contain exactly one target option"
}

test_target_mode_generated_selectors()
{
    strategy='--filter-tcp=443
--filter-l7=tls'
    case_dir="${TEST_ROOT}/target-mode"
    mkdir -p "${case_dir}"

    parsed_count=$(parser_parse "${strategy}" "${case_dir}")
    registry_build "${case_dir}/registry.tsv"
    target_mode_apply_all         "${case_dir}" "${parsed_count}" list "${case_dir}/registry.tsv"
    count=$(profile_normalizer_normalize_all "${case_dir}" "${parsed_count}")

    assert_equal 3 "${count}" "Target Mode generated selector count"
    grep -qx '<HOSTLIST:youtube>' "${case_dir}/profile-1.conf" ||
        fail "Target Mode HOSTLIST:youtube order was not preserved"
    grep -qx '<IPSET:telegram>' "${case_dir}/profile-2.conf" ||
        fail "Target Mode IPSET:telegram order was not preserved"
    grep -qx '<HOSTLIST:user>' "${case_dir}/profile-3.conf" ||
        fail "Target Mode HOSTLIST:user order was not preserved"

    for profile in "${case_dir}"/profile-*.conf; do
        selector_count=$(grep -Ec '<(HOSTLIST|IPSET):' "${profile}" || true)
        assert_equal 1 "${selector_count}" "Target Mode selector count in ${profile}"
        grep -qx -- '--filter-tcp=443' "${profile}" ||
            fail "Target Mode shared strategy line missing from ${profile}"
    done
}

test_duplicate_selector_and_idempotence()
{
    strategy='<HOSTLIST:user>
--filter-tcp=443
<HOSTLIST:user>
<IPSET:telegram>'
    count=$(parse_and_normalize idempotent "${strategy}")

    assert_equal 2 "${count}" "duplicate selector deduplication count"
    mkdir "${TEST_ROOT}/idempotent/first-pass"
    cp "${TEST_ROOT}/idempotent"/profile-*.conf \
        "${TEST_ROOT}/idempotent/first-pass/"

    second_count=$(profile_normalizer_normalize_all \
        "${TEST_ROOT}/idempotent" "${count}")
    assert_equal "${count}" "${second_count}" "idempotent profile count"
    assert_file_equal \
        "${TEST_ROOT}/idempotent/first-pass/profile-1.conf" \
        "${TEST_ROOT}/idempotent/profile-1.conf" \
        "first profile changed on second normalization"
    assert_file_equal \
        "${TEST_ROOT}/idempotent/first-pass/profile-2.conf" \
        "${TEST_ROOT}/idempotent/profile-2.conf" \
        "second profile changed on second normalization"
}

test_no_selector
test_single_hostlist
test_single_ipset
test_mixed_selectors
test_same_family_and_three_selectors
test_user_new_boundaries
test_resolved_runtime_profiles
test_target_mode_generated_selectors
test_duplicate_selector_and_idempotence

echo "Profile normalizer tests passed."
