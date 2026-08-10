#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
CI="${ROOT_DIR}/.github/workflows/ci.yml"
RELEASE="${ROOT_DIR}/.github/workflows/release.yml"
MATRIX="${ROOT_DIR}/docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md"
PROJECT_STATE="${ROOT_DIR}/docs/PROJECT_STATE.md"
BUILD_PKG="${ROOT_DIR}/scripts/build-pkg.sh"
INTEGRATION="${ROOT_DIR}/scripts/test-strategy-lab-third-audit-integration-contract.sh"
VERSION_FILE="${ROOT_DIR}/VERSION"
MAKEFILE="${ROOT_DIR}/Makefile"
PATCH4_TEST="${ROOT_DIR}/scripts/test-strategy-lab-python-probes.sh"
PATCH5_TEST="${ROOT_DIR}/scripts/test-strategy-lab-python-candidate-family.sh"
PATCH6_TEST="${ROOT_DIR}/scripts/test-strategy-lab-python-search-extended.sh"
PATCH29_TEST="${ROOT_DIR}/scripts/test-strategy-lab-python-candidate-spec.sh"
PATCH30_TEST="${ROOT_DIR}/scripts/test-strategy-lab-python-search-graph.sh"
PATCH31_TEST="${ROOT_DIR}/scripts/test-strategy-lab-python-adaptive-planner.sh"
PATCH32_TEST="${ROOT_DIR}/scripts/test-strategy-lab-late-stage-containment.sh"
PATCH33_TEST="${ROOT_DIR}/scripts/test-strategy-lab-adaptive-validation.sh"
REQUEST_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/request.py"
PROBE_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/probe.py"
ENDPOINT_EPOCH_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/endpoint_epoch.py"
TELEMETRY_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/telemetry.py"
RESOURCES_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/resources.py"
CANDIDATE_SPEC_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/candidate_spec.py"
CANDIDATE_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/candidate.py"
FAMILY_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/family.py"
SEARCH_GRAPH_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/search_graph.py"
SEARCH_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/search.py"
EXTENDED_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/extended.py"
LATE_CONTAINMENT_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/late_containment.py"
ADAPTIVE_VALIDATION_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/adaptive_validation.py"
ADAPTIVE_RESULT_COMPAT_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/adaptive_result_compat.py"
CANDIDATE_ADAPTER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_candidate_adapter.sh"

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

for file in \
    "${CI}" "${RELEASE}" "${MATRIX}" "${PROJECT_STATE}" "${BUILD_PKG}" "${INTEGRATION}" \
    "${VERSION_FILE}" "${MAKEFILE}" \
    "${PATCH4_TEST}" "${PATCH5_TEST}" "${PATCH6_TEST}" "${PATCH29_TEST}" \
    "${PATCH30_TEST}" "${PATCH31_TEST}" "${PATCH32_TEST}" "${PATCH33_TEST}" \
    "${REQUEST_PY}" "${PROBE_PY}" "${ENDPOINT_EPOCH_PY}" "${TELEMETRY_PY}" \
    "${RESOURCES_PY}" "${CANDIDATE_SPEC_PY}" "${CANDIDATE_PY}" "${FAMILY_PY}" \
    "${SEARCH_GRAPH_PY}" "${SEARCH_PY}" "${EXTENDED_PY}" "${LATE_CONTAINMENT_PY}" \
    "${ADAPTIVE_VALIDATION_PY}" "${ADAPTIVE_RESULT_COMPAT_PY}" "${CANDIDATE_ADAPTER}"
do
    [ -s "${file}" ] || fail "required file is missing: ${file}"
done

[ -x "${PATCH4_TEST}" ] || fail 'Python request/probe focused test is not executable'
[ -x "${PATCH29_TEST}" ] || fail 'Python CandidateSpec/ResourceInventory focused test is not executable'
[ -x "${PATCH30_TEST}" ] || fail 'Python native search-graph focused test is not executable'
[ -x "${PATCH31_TEST}" ] || fail 'Python adaptive planner/search-epoch/telemetry focused test is not executable'

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(awk -F= '/^PLUGIN_REVISION=/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${MAKEFILE}")
case "${revision}" in
    ''|*[!0-9]*) fail 'invalid plugin revision' ;;
esac
if [ "${revision}" -gt 0 ]; then
    candidate="os-zapret2-restyle-${version}_${revision}.pkg"
else
    candidate="os-zapret2-restyle-${version}.pkg"
fi

# Package construction and ABI/runtime requirements.
grep -Eq '^PLUGIN_DEPENDS=[[:space:]]+python313([[:space:]]|$)' "${MAKEFILE}" ||
    fail 'Python migration must declare the verified python313 package dependency'
grep -Fq 'python313)  echo "lang/python313"' "${BUILD_PKG}" ||
    fail 'package builder does not map python313 to lang/python313'
grep -Fq 'cp -R src/opnsense "${STAGE}/usr/local/opnsense"' "${BUILD_PKG}" ||
    fail 'package builder no longer stages the complete OPNsense source tree'

grep -Fq 'release: "15.0"' "${CI}" || fail 'PR package build does not use FreeBSD 15.0'
grep -Fq "release: '15.0'" "${RELEASE}" || fail 'release package build does not use FreeBSD 15.0'
if grep -REn "release:[[:space:]]*['\"]?14([.]|['\"]|$)" "${ROOT_DIR}/.github/workflows"; then
    fail 'a GitHub workflow still selects FreeBSD 14'
fi

grep -Fq 'python-version: "3.13"' "${CI}" || fail 'Linux validation does not select Python 3.13'
grep -Fq 'STRATEGY_LAB_PYTHON_BIN: python3.13' "${CI}" ||
    fail 'Linux validation does not expose Python 3.13 to Strategy Lab tests'
grep -Fq 'pkg install -y jq python313' "${CI}" ||
    fail 'FreeBSD 15 package job does not install python313'

for test in \
    test-strategy-lab-python-foundation.sh \
    test-strategy-lab-python-state-persistence.sh \
    test-strategy-lab-python-orchestration.sh \
    test-strategy-lab-python-probes.sh \
    test-strategy-lab-python-candidate-spec.sh \
    test-strategy-lab-python-candidate-family.sh \
    test-strategy-lab-python-search-graph.sh \
    test-strategy-lab-python-adaptive-planner.sh \
    test-strategy-lab-python-search-extended.sh
do
    grep -Fq "STRATEGY_LAB_TEST_PYTHON=/usr/local/bin/python3.13 sh scripts/${test}" "${CI}" ||
        fail "FreeBSD 15 package job does not execute ${test}"
done

# The search/extended continuity gate must include both corrective `_32` containment and
# the `_33` adaptive-validation source contract; the same gate runs on Linux and FreeBSD.
grep -Fq 'scripts/test-strategy-lab-late-stage-containment.sh' "${PATCH6_TEST}" ||
    fail 'Python search/extended continuity gate does not include late-stage containment'
grep -Fq 'scripts/test-strategy-lab-adaptive-validation.sh' "${PATCH6_TEST}" ||
    fail 'Python search/extended continuity gate does not include adaptive validation'

# CI must inspect the installed package rather than infer ABI or file contents from source.
grep -Fq 'tar -tf dist/*.pkg > "${contents}"' "${CI}" ||
    fail 'package contents are not captured before inspection'
grep -Fq 'tar -xOf dist/*.pkg +MANIFEST > "${manifest}"' "${CI}" ||
    fail 'package manifest is not captured before inspection'
grep -Fq '.abi == "FreeBSD:15:amd64"' "${CI}" ||
    fail 'PR package inspection does not enforce FreeBSD 15 ABI'
grep -Fq '.arch == "freebsd:15:x86:64"' "${CI}" ||
    fail 'PR package inspection does not enforce FreeBSD 15 architecture'
grep -Fq '.deps.python313.origin == "lang/python313"' "${CI}" ||
    fail 'package inspection does not enforce the python313 dependency origin'

# Existing explicit package-file checks remain authoritative for migration modules. The
# package builder stages the complete OPNsense tree, while the FreeBSD continuity test
# imports and executes the `_33` modules before the package is built.
for installed in \
    strategy_lab_py/state.py \
    strategy_lab_py/orchestrator.py \
    strategy_lab_py/request.py \
    strategy_lab_py/probe.py \
    strategy_lab_py/endpoint_epoch.py \
    strategy_lab_py/telemetry.py \
    strategy_lab_py/resources.py \
    strategy_lab_py/candidate_spec.py \
    strategy_lab_py/candidate.py \
    strategy_lab_py/family.py \
    strategy_lab_py/search_graph.py \
    strategy_lab_py/search.py \
    strategy_lab_py/extended.py \
    strategy_lab_candidate_adapter.sh \
    strategy_lab_stage_adapter.sh
do
    grep -Fq "usr/local/opnsense/scripts/OPNsense/Zapret/${installed}" "${CI}" ||
        fail "package inspection no longer requires ${installed}"
done

grep -Fq 'freebsd-version -u' "${CI}" || fail 'PR package build does not verify the VM major version'
grep -Fq 'scripts/test-freebsd15-package-ci' "${CI}" ||
    fail 'integration-only package verification no longer forces the FreeBSD 15 PR build'
grep -Fq "find \"\${ROOT_DIR}/scripts\" -maxdepth 1 -type f -name 'test-strategy-lab-*.sh'" \
    "${ROOT_DIR}/scripts/test-strategy-lab-corrective-matrix.sh" ||
    fail 'canonical Strategy Lab matrix no longer discovers focused regressions'

# Preserve the canonical historical live matrix while using PROJECT_STATE for the current
# already-observed `_8` live boundary and in-flight `_9` source candidate. The matrix is
# expanded with the next owner evidence bundle rather than being used as a source-build
# identity file.
grep -Fq 'Overall status: **RELEASE-SELECTED LIVE GATE PASS ON `_27`; ADAPTIVE `_28` FOCUSED PASS; FULL REGRESSION MATRIX OPEN**' "${MATRIX}" ||
    fail 'unexpected Strategy Lab live-matrix baseline'
grep -Fq '**PASS ON `_27` — v0.4.0 mandatory row**' "${MATRIX}" ||
    fail 'release-selected live matrix does not retain the v0.4.0 mandatory Scenario 1 PASS'
grep -Fq 'ADAPTIVE-SEARCH OWNER TEST — `_28`' "${MATRIX}" ||
    fail 'live matrix does not retain the _28 focused owner test'
grep -Fq 'TIMEOUT-HIERARCHY OWNER TEST — `v0.4.0_6`' "${MATRIX}" ||
    fail 'live matrix does not retain the v0.4.0_6 timeout-hierarchy evidence'
grep -Fq 'TIMEOUT-HIERARCHY OWNER TEST — `v0.4.0_7`' "${MATRIX}" ||
    fail 'live matrix does not retain the v0.4.0_7 timeout-hierarchy evidence'
grep -Fq 'Required package ABI: `FreeBSD:15:amd64`' "${MATRIX}" ||
    fail 'live matrix does not require the FreeBSD 15 ABI'

grep -Fq 'Latest published testing prerelease: `v0.4.0_8` / `os-zapret2-restyle-0.4.0_8.pkg`' "${PROJECT_STATE}" ||
    fail 'project state does not preserve the published _8 candidate'
grep -Fq 'Latest owner-tested testing candidate: `v0.4.0_8` / `os-zapret2-restyle-0.4.0_8.pkg`' "${PROJECT_STATE}" ||
    fail 'project state does not preserve the owner-tested _8 candidate'
grep -Fq "Current source candidate: \`${candidate}\`" "${PROJECT_STATE}" ||
    fail 'project state does not select the current source candidate'
grep -Fq '`_32` timeout-containment gate: **OWNER-LIVE PASS through `v0.4.0_8`**' "${PROJECT_STATE}" ||
    fail 'project state does not close the owner-live _32 boundary'

sh -n "$0"
printf '%s\n' "PASS: FreeBSD 15 package CI, Python 3.13 Strategy Lab layers, _32 containment, _33 adaptive validation, and current project-state selection are qualified for ${candidate}"
