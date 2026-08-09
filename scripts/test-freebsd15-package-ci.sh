#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
CI="${ROOT_DIR}/.github/workflows/ci.yml"
RELEASE="${ROOT_DIR}/.github/workflows/release.yml"
MATRIX="${ROOT_DIR}/docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md"
INTEGRATION="${ROOT_DIR}/scripts/test-strategy-lab-third-audit-integration-contract.sh"
VERSION_FILE="${ROOT_DIR}/VERSION"
MAKEFILE="${ROOT_DIR}/Makefile"
PATCH4_TEST="${ROOT_DIR}/scripts/test-strategy-lab-python-probes.sh"
PATCH5_TEST="${ROOT_DIR}/scripts/test-strategy-lab-python-candidate-family.sh"
PATCH6_TEST="${ROOT_DIR}/scripts/test-strategy-lab-python-search-extended.sh"
PATCH29_TEST="${ROOT_DIR}/scripts/test-strategy-lab-python-candidate-spec.sh"
PATCH30_TEST="${ROOT_DIR}/scripts/test-strategy-lab-python-search-graph.sh"
PATCH31_TEST="${ROOT_DIR}/scripts/test-strategy-lab-python-adaptive-planner.sh"
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
CANDIDATE_ADAPTER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_candidate_adapter.sh"

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

for file in "${CI}" "${RELEASE}" "${MATRIX}" "${INTEGRATION}" "${VERSION_FILE}" "${MAKEFILE}" \
    "${PATCH4_TEST}" "${PATCH5_TEST}" "${PATCH6_TEST}" "${PATCH29_TEST}" "${PATCH30_TEST}" "${PATCH31_TEST}" \
    "${REQUEST_PY}" "${PROBE_PY}" "${ENDPOINT_EPOCH_PY}" "${TELEMETRY_PY}" "${RESOURCES_PY}" "${CANDIDATE_SPEC_PY}" \
    "${CANDIDATE_PY}" "${FAMILY_PY}" "${SEARCH_GRAPH_PY}" "${SEARCH_PY}" "${EXTENDED_PY}" "${CANDIDATE_ADAPTER}"
do
    [ -s "${file}" ] || fail "required file is missing: ${file}"
done
[ -x "${PATCH4_TEST}" ] || fail 'Python request/probe focused test is not executable'
[ -x "${PATCH29_TEST}" ] || fail 'Python CandidateSpec/ResourceInventory focused test is not executable'
[ -x "${PATCH30_TEST}" ] || fail 'Python native search-graph focused test is not executable'
[ -x "${PATCH31_TEST}" ] || fail 'Python adaptive planner/search-epoch/telemetry focused test is not executable'

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(awk -F= '
    /^PLUGIN_REVISION=/ {
        gsub(/[[:space:]]/, "", $2)
        print $2
        exit
    }
' "${MAKEFILE}")

case "${revision}" in
    ''|*[!0-9]*) fail 'invalid plugin revision' ;;
esac

if [ "${revision}" -gt 0 ]; then
    candidate="os-zapret2-restyle-${version}_${revision}.pkg"
else
    candidate="os-zapret2-restyle-${version}.pkg"
fi

grep -Eq '^PLUGIN_DEPENDS=[[:space:]]+python313([[:space:]]|$)' "${MAKEFILE}" ||
    fail 'Python migration must declare the verified python313 package dependency'
grep -Fq 'python313)  echo "lang/python313"' "${ROOT_DIR}/scripts/build-pkg.sh" ||
    fail 'package builder does not map python313 to lang/python313'

grep -Fq 'release: "15.0"' "${CI}" || fail 'PR package build does not use FreeBSD 15.0'
grep -Fq "release: '15.0'" "${RELEASE}" || fail 'release package build does not use FreeBSD 15.0'

if grep -REn "release:[[:space:]]*['\"]?14([.]|['\"]|$)" \
    "${ROOT_DIR}/.github/workflows"
then
    fail 'a GitHub workflow still selects FreeBSD 14'
fi

grep -Fq 'python-version: "3.13"' "${CI}" || fail 'Linux validation does not select Python 3.13'
grep -Fq 'STRATEGY_LAB_PYTHON_BIN: python3.13' "${CI}" || fail 'Linux validation does not expose Python 3.13 to Strategy Lab compatibility tests'
grep -Fq 'pkg install -y jq python313' "${CI}" || fail 'FreeBSD 15 package job does not install python313'
grep -Fq 'STRATEGY_LAB_TEST_PYTHON=/usr/local/bin/python3.13 sh scripts/test-strategy-lab-python-foundation.sh' "${CI}" ||
    fail 'FreeBSD 15 package job does not execute the Python 3.13 foundation test'
grep -Fq 'STRATEGY_LAB_TEST_PYTHON=/usr/local/bin/python3.13 sh scripts/test-strategy-lab-python-state-persistence.sh' "${CI}" ||
    fail 'FreeBSD 15 package job does not execute the Python state persistence regression'
grep -Fq 'STRATEGY_LAB_TEST_PYTHON=/usr/local/bin/python3.13 sh scripts/test-strategy-lab-python-orchestration.sh' "${CI}" ||
    fail 'FreeBSD 15 package job does not execute the Python stage orchestration regression'
grep -Fq 'STRATEGY_LAB_TEST_PYTHON=/usr/local/bin/python3.13 sh scripts/test-strategy-lab-python-probes.sh' "${CI}" ||
    fail 'FreeBSD 15 package job does not execute the Python request/probe regression'
grep -Fq 'STRATEGY_LAB_TEST_PYTHON=/usr/local/bin/python3.13 sh scripts/test-strategy-lab-python-candidate-family.sh' "${CI}" ||
    fail 'FreeBSD 15 package job does not execute the Python candidate/family regression'
grep -Fq 'STRATEGY_LAB_TEST_PYTHON=/usr/local/bin/python3.13 sh scripts/test-strategy-lab-python-candidate-spec.sh' "${CI}" ||
    fail 'FreeBSD 15 package job does not execute the Python CandidateSpec/ResourceInventory regression'
grep -Fq 'STRATEGY_LAB_TEST_PYTHON=/usr/local/bin/python3.13 sh scripts/test-strategy-lab-python-search-graph.sh' "${CI}" ||
    fail 'FreeBSD 15 package job does not execute the native search-graph regression'
grep -Fq 'STRATEGY_LAB_TEST_PYTHON=/usr/local/bin/python3.13 sh scripts/test-strategy-lab-python-adaptive-planner.sh' "${CI}" ||
    fail 'FreeBSD 15 package job does not execute the adaptive planner/search-epoch/telemetry regression'
grep -Fq 'STRATEGY_LAB_TEST_PYTHON=/usr/local/bin/python3.13 sh scripts/test-strategy-lab-python-search-extended.sh' "${CI}" ||
    fail 'FreeBSD 15 package job does not execute the Python search/extended regression'
grep -Fq 'usr/local/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/state.py' "${CI}" ||
    fail 'package inspection does not require the Python state persistence module'
grep -Fq 'usr/local/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/orchestrator.py' "${CI}" ||
    fail 'package inspection does not require the Python stage orchestration module'
grep -Fq 'usr/local/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/request.py' "${CI}" ||
    fail 'package inspection does not require the Python finite request module'
grep -Fq 'usr/local/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/probe.py' "${CI}" ||
    fail 'package inspection does not require the Python network/baseline probe module'
grep -Fq 'usr/local/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/endpoint_epoch.py' "${CI}" ||
    fail 'package inspection does not require the fixed search-epoch module'
grep -Fq 'usr/local/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/telemetry.py' "${CI}" ||
    fail 'package inspection does not require the timing telemetry module'
grep -Fq 'usr/local/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/resources.py' "${CI}" ||
    fail 'package inspection does not require the Python resource inventory module'
grep -Fq 'usr/local/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/candidate_spec.py' "${CI}" ||
    fail 'package inspection does not require the Python CandidateSpec module'
grep -Fq 'usr/local/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/candidate.py' "${CI}" ||
    fail 'package inspection does not require the Python candidate runtime module'
grep -Fq 'usr/local/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/family.py' "${CI}" ||
    fail 'package inspection does not require the Python family screening module'
grep -Fq 'usr/local/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/search_graph.py' "${CI}" ||
    fail 'package inspection does not require the native search-graph module'
grep -Fq 'usr/local/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/search.py' "${CI}" ||
    fail 'package inspection does not require the Python search orchestration module'
grep -Fq 'usr/local/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/extended.py' "${CI}" ||
    fail 'package inspection does not require the Python extended-protocol orchestration module'
grep -Fq 'usr/local/opnsense/scripts/OPNsense/Zapret/strategy_lab_candidate_adapter.sh' "${CI}" ||
    fail 'package inspection does not require the narrow candidate system adapter'
grep -Fq 'usr/local/opnsense/scripts/OPNsense/Zapret/strategy_lab_stage_adapter.sh' "${CI}" ||
    fail 'package inspection does not require the Strategy Lab stage adapter'
grep -Fq '.deps.python313.origin == "lang/python313"' "${CI}" ||
    fail 'package inspection does not enforce the python313 dependency origin'

grep -Fq 'freebsd-version -u' "${CI}" || fail 'PR package build does not verify the VM major version'
grep -Fq '.abi == "FreeBSD:15:amd64"' "${CI}" || fail 'PR package inspection does not enforce FreeBSD 15 ABI'
grep -Fq '.arch == "freebsd:15:x86:64"' "${CI}" || fail 'PR package inspection does not enforce FreeBSD 15 architecture'
grep -Fq 'tar -tf dist/*.pkg > "${contents}"' "${CI}" || fail 'package contents are not captured without a truncation pipe'
grep -Fq 'tar -xOf dist/*.pkg +MANIFEST > "${manifest}"' "${CI}" || fail 'package manifest is not captured before inspection'

grep -Fq 'scripts/test-freebsd15-package-ci' "${CI}" ||
    fail 'integration-only package verification no longer forces the FreeBSD 15 PR build'
grep -Fq "find \"\${ROOT_DIR}/scripts\" -maxdepth 1 -type f -name 'test-strategy-lab-*.sh'" \
    "${ROOT_DIR}/scripts/test-strategy-lab-corrective-matrix.sh" ||
    fail 'canonical matrix no longer discovers the third-audit integration contract'

if grep -Fq 'Overall status: **PAUSED — THIRD-AUDIT CORRECTIVE SERIES IN PROGRESS**' "${MATRIX}"; then
    grep -Fq 'Current corrective candidate: **NOT DESIGNATED — PATCH 8 REQUIRED**' "${MATRIX}" ||
        fail 'paused third-audit matrix must not designate a live candidate before Patch 8'
elif grep -Fq 'Overall status: **RELEASE-SELECTED LIVE GATE PASS ON `_27`; ADAPTIVE `_28` FOCUSED PASS; FULL REGRESSION MATRIX OPEN**' "${MATRIX}"; then
    grep -Fq 'Latest published testing candidate: `os-zapret2-restyle-0.4.0_6.pkg`' "${MATRIX}" ||
        fail 'timeout-hierarchy live matrix does not preserve the latest published _6 candidate'
    grep -Fq 'Latest owner-tested candidate: `os-zapret2-restyle-0.4.0_6.pkg`' "${MATRIX}" ||
        fail 'timeout-hierarchy live matrix does not preserve the latest owner-tested _6 candidate'
    grep -Fq "Current adaptive-search source candidate: \`${candidate}\`" "${MATRIX}" ||
        fail 'adaptive live matrix does not select the current source candidate'
    grep -Fq '**PASS ON `_27` — v0.4.0 mandatory row**' "${MATRIX}" ||
        fail 'release-selected live matrix does not record the v0.4.0 mandatory Scenario 1 PASS'
    grep -Fq 'ADAPTIVE-SEARCH OWNER TEST — `_28`' "${MATRIX}" ||
        fail 'adaptive live matrix does not record the _28 focused owner test'
    grep -Fq 'TIMEOUT-HIERARCHY OWNER TEST — `v0.4.0_6`' "${MATRIX}" ||
        fail 'live matrix does not record the v0.4.0_6 timeout-hierarchy owner test'
elif grep -Fq 'Overall status: **FAILED ON `_26` — CORRECTIVE `_27` REQUIRED**' "${MATRIX}"; then
    [ "${revision}" -eq 27 ] || fail '_26 live failure must designate revision 27'
    grep -Fq 'Latest published testing candidate: `os-zapret2-restyle-0.3.3_26.pkg`' "${MATRIX}" ||
        fail 'post-migration live matrix does not preserve published _26 identity'
    grep -Fq 'Latest owner-tested candidate: `os-zapret2-restyle-0.3.3_26.pkg`' "${MATRIX}" ||
        fail 'post-migration live matrix does not preserve owner-tested _26 identity'
    grep -Fq "Current corrective source candidate: \`${candidate}\`" "${MATRIX}" ||
        fail "post-migration live matrix does not select current corrective source package ${candidate}"
elif grep -Fq 'Overall status: **FAILED ON `_25` — CORRECTIVE `_26` REQUIRED**' "${MATRIX}"; then
    [ "${revision}" -eq 26 ] || fail '_25 live failure must designate revision 26'
    grep -Fq 'Latest published testing candidate: `os-zapret2-restyle-0.3.3_25.pkg`' "${MATRIX}" ||
        fail 'post-migration live matrix does not preserve published _25 identity'
    grep -Fq 'Latest owner-tested candidate: `os-zapret2-restyle-0.3.3_25.pkg`' "${MATRIX}" ||
        fail 'post-migration live matrix does not preserve owner-tested _25 identity'
    grep -Fq "Current corrective source candidate: \`${candidate}\`" "${MATRIX}" ||
        fail "post-migration live matrix does not select current corrective source package ${candidate}"
elif grep -Fq 'Overall status: **FAILED ON `_17` — LIVE MATRIX PAUSED FOR PYTHON MIGRATION**' "${MATRIX}"; then
    [ "${revision}" -ge 17 ] || fail 'Python migration source revision cannot precede shell-era revision 17'
    grep -Fq 'Latest published testing candidate: `os-zapret2-restyle-0.3.3_17.pkg`' "${MATRIX}" ||
        fail 'Python migration does not preserve the published _17 package identity'
    grep -Fq 'Latest owner-tested candidate: `os-zapret2-restyle-0.3.3_17.pkg`' "${MATRIX}" ||
        fail 'Python migration does not preserve the owner-tested _17 package identity'
    if [ "${revision}" -gt 17 ]; then
        grep -Fq "Current migration source candidate: \`${candidate}\`" "${MATRIX}" ||
            fail "Python migration matrix does not select current source package ${candidate}"
    fi
elif grep -Fq 'Overall status: **FAILED ON _12 — STAGE-90 CORRECTION `_13` IN PROGRESS**' "${MATRIX}"; then
    grep -Fq "Current corrective source candidate: \`${candidate}\`" "${MATRIX}" || fail "matrix does not select ${candidate}"
elif grep -Fq 'Overall status: **FAILED ON _13 — STAGE-40 CORRECTION `_14` IN PROGRESS**' "${MATRIX}"; then
    grep -Fq "Current corrective source candidate: \`${candidate}\`" "${MATRIX}" || fail "matrix does not select ${candidate}"
elif grep -Fq 'Overall status: **FAILED ON _14 — STAGE-50 CORRECTION `_15` IN PROGRESS**' "${MATRIX}"; then
    grep -Fq "Current corrective source candidate: \`${candidate}\`" "${MATRIX}" || fail "matrix does not select ${candidate}"
elif grep -Fq 'Overall status: **FAILED ON _15 — STAGE-50 CORRECTION `_16` IN PROGRESS**' "${MATRIX}"; then
    grep -Fq "Current corrective source candidate: \`${candidate}\`" "${MATRIX}" || fail "matrix does not select ${candidate}"
elif grep -Fq 'Overall status: **FAILED ON _16 — STAGE-50 CORRECTION `_17` IN PROGRESS**' "${MATRIX}"; then
    grep -Fq "Current corrective source candidate: \`${candidate}\`" "${MATRIX}" ||
        fail "hostlist-access live matrix does not select the current corrective source package: ${candidate}"
else
    grep -Fq "Current corrective candidate: \`${candidate}\`" "${MATRIX}" ||
        fail "live matrix does not select the current corrective package: ${candidate}"
fi

grep -Fq 'Required package ABI: `FreeBSD:15:amd64`' "${MATRIX}" ||
    fail 'live matrix does not require the FreeBSD 15 ABI'
if grep -Fq 'Current corrective candidate: `os-zapret2-restyle-0.3.2_46.pkg`' "${MATRIX}"; then
    fail 'the incompatible revision 46 package remains selected for live verification'
fi

sh -n "$0"
echo "PASS: GitHub package builds stay on FreeBSD 15, Python 3.13 persistence/orchestration/request-probe/candidate-family/native-search-graph/adaptive-planner/search-extended layers are qualified, and live-candidate selection respects the active live gate for ${candidate}"
