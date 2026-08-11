#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
CI="${ROOT_DIR}/.github/workflows/ci.yml"
RELEASE="${ROOT_DIR}/.github/workflows/release.yml"
MATRIX="${ROOT_DIR}/docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md"
PROJECT_STATE="${ROOT_DIR}/docs/PROJECT_STATE.md"
BUILD_PKG="${ROOT_DIR}/scripts/build-pkg.sh"
VERSION_FILE="${ROOT_DIR}/VERSION"
MAKEFILE="${ROOT_DIR}/Makefile"
CORRECTIVE_MATRIX="${ROOT_DIR}/scripts/test-strategy-lab-corrective-matrix.sh"
MODEL_B_TEST="${ROOT_DIR}/scripts/test-strategy-lab-model-b-experiment.sh"
MODEL_B_PREFLIGHT_TEST="${ROOT_DIR}/scripts/test-strategy-lab-model-b-preflight.sh"
MODEL_B_FAILFAST_TEST="${ROOT_DIR}/scripts/test-strategy-lab-model-b-failed-readiness.sh"
MODEL_B_EXHAUSTIVE_TEST="${ROOT_DIR}/scripts/test-strategy-lab-model-b-exhaustive.sh"
MODEL_B_EXHAUSTIVE_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/model_b_exhaustive.py"
MODEL_B_EXHAUSTIVE_LAUNCHER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_model_b_exhaustive.sh"
MODEL_B_EXHAUSTIVE_WORKER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_model_b_exhaustive_worker.sh"

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

for file in \
    "${CI}" "${RELEASE}" "${MATRIX}" "${PROJECT_STATE}" "${BUILD_PKG}" \
    "${VERSION_FILE}" "${MAKEFILE}" "${CORRECTIVE_MATRIX}" \
    "${MODEL_B_TEST}" "${MODEL_B_PREFLIGHT_TEST}" "${MODEL_B_FAILFAST_TEST}" \
    "${MODEL_B_EXHAUSTIVE_TEST}" "${MODEL_B_EXHAUSTIVE_PY}" \
    "${MODEL_B_EXHAUSTIVE_LAUNCHER}" "${MODEL_B_EXHAUSTIVE_WORKER}"
do
    [ -s "${file}" ] || fail "required file is missing: ${file}"
done

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(awk -F= '/^PLUGIN_REVISION=/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${MAKEFILE}")
case "${revision}" in ''|*[!0-9]*) fail 'invalid plugin revision' ;; esac
candidate="os-zapret2-restyle-${version}_${revision}.pkg"
[ "${version}" = '0.4.0' ] || fail "unexpected active version ${version}"
[ "${revision}" -eq 18 ] || fail "exhaustive benchmark must use revision 18, found ${revision}"

# Package construction and ABI/runtime requirements.
grep -Eq '^PLUGIN_DEPENDS=[[:space:]]+python313([[:space:]]|$)' "${MAKEFILE}" ||
    fail 'Python migration must declare python313'
grep -Fq 'python313)  echo "lang/python313"' "${BUILD_PKG}" ||
    fail 'package builder does not map python313 to lang/python313'
grep -Fq 'cp -R src/opnsense "${STAGE}/usr/local/opnsense"' "${BUILD_PKG}" ||
    fail 'package builder no longer stages the complete OPNsense tree'
grep -Fq 'find "${STAGE}" -type f -name "*.sh" -exec chmod 755 {} +' "${BUILD_PKG}" ||
    fail 'package builder no longer makes packaged shell entry points executable'

# The exhaustive module, worker and launcher live inside src/opnsense, so the complete-tree
# staging contract above includes them in every built package. Keep all three source paths
# mandatory so a packaging refactor cannot silently omit the experiment.
grep -Fq 'model-b-exhaustive' "${MODEL_B_EXHAUSTIVE_LAUNCHER}" ||
    fail 'exhaustive Model B launcher contract is unavailable'
grep -Fq 'model-b-exhaustive run' "${MODEL_B_EXHAUSTIVE_WORKER}" ||
    fail 'exhaustive Model B worker contract is unavailable'
grep -Fq 'B-warm-worker-exhaustive-batched' "${MODEL_B_EXHAUSTIVE_PY}" ||
    fail 'exhaustive Model B Python module is unavailable'

# CI platform contract.
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
grep -Fq 'freebsd-version -u' "${CI}" || fail 'PR package build does not verify VM major version'

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

# Canonical Linux corrective matrix discovers every focused Strategy Lab shell regression,
# including the new exhaustive benchmark contract.
grep -Fq "find \"\${ROOT_DIR}/scripts\" -maxdepth 1 -type f -name 'test-strategy-lab-*.sh'" \
    "${CORRECTIVE_MATRIX}" || fail 'corrective matrix no longer discovers focused tests'
grep -Fq 'PASS: Model B preflight returns success when all dedicated rules/ports are free' \
    "${MODEL_B_PREFLIGHT_TEST}" || fail 'Model B preflight regression is unavailable'
grep -Fq 'preserves bounded post-drop hostlist access' "${MODEL_B_TEST}" ||
    fail 'Model B post-drop access regression is unavailable'
grep -Fq 'PASS: Model B failed pool readiness rejects immediately' "${MODEL_B_FAILFAST_TEST}" ||
    fail 'Model B failed-readiness regression is unavailable'
grep -Fq 'PASS: exhaustive Model B benchmark replays a complete graph-exhausted corpus' \
    "${MODEL_B_EXHAUSTIVE_TEST}" || fail 'exhaustive Model B regression is unavailable'

# CI must inspect the built package and its manifest rather than infer ABI from source.
grep -Fq 'tar -tf dist/*.pkg > "${contents}"' "${CI}" ||
    fail 'package contents are not captured before inspection'
grep -Fq 'tar -xOf dist/*.pkg +MANIFEST > "${manifest}"' "${CI}" ||
    fail 'package manifest is not captured before inspection'
grep -Fq '.abi == "FreeBSD:15:amd64"' "${CI}" ||
    fail 'package inspection does not enforce FreeBSD 15 ABI'
grep -Fq '.arch == "freebsd:15:x86:64"' "${CI}" ||
    fail 'package inspection does not enforce FreeBSD 15 architecture'
grep -Fq '.deps.python313.origin == "lang/python313"' "${CI}" ||
    fail 'package inspection does not enforce python313 origin'
grep -Fq 'usr/local/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/state.py' "${CI}" ||
    fail 'package inspection no longer proves Strategy Lab Python content'
grep -Fq 'usr/local/opnsense/scripts/OPNsense/Zapret/strategy_lab_stage_adapter.sh' "${CI}" ||
    fail 'package inspection no longer proves Strategy Lab shell content'
grep -Fq 'scripts/test-freebsd15-package-ci' "${CI}" ||
    fail 'integration-only package verification no longer forces the FreeBSD 15 PR build'

# Current live/source selection must agree across canonical ledgers.
grep -Fq 'MODEL B `_17` REPEATED COEXISTENCE ACCEPT 5/5 (EXPERIMENT ONLY); `_18` EXHAUSTIVE NO-CANDIDATE BENCHMARK SOURCE CANDIDATE' "${MATRIX}" ||
    fail 'unexpected live-matrix experiment state'
grep -Fq '**PASS ON `_27` — v0.4.0 mandatory row**' "${MATRIX}" ||
    fail 'mandatory release row was lost'
grep -Fq 'Latest published testing candidate: `os-zapret2-restyle-0.4.0_17.pkg`' "${MATRIX}" ||
    fail 'live matrix does not retain published _17'
grep -Fq 'Latest owner-installed testing candidate: `os-zapret2-restyle-0.4.0_17.pkg`' "${MATRIX}" ||
    fail 'live matrix does not retain owner-installed _17'
grep -Fq "Current source candidate: \`${candidate}\`" "${MATRIX}" ||
    fail 'live matrix does not select the current _18 source candidate'
grep -Fq 'Current source purpose: `_18` experiment-only batched exhaustive Model B benchmark' "${MATRIX}" ||
    fail 'live matrix does not describe the exhaustive source purpose'
grep -Fq 'at most three warm workers per batch' "${MATRIX}" ||
    fail 'live matrix lost the proven three-worker width'
grep -Fq 'ordinary Strategy Lab still uses Model A' "${MATRIX}" ||
    fail 'live matrix accidentally implies production warm execution'

grep -Fq 'Latest published testing prerelease: `v0.4.0_17` / `os-zapret2-restyle-0.4.0_17.pkg`' "${PROJECT_STATE}" ||
    fail 'project state does not retain published _17'
grep -Fq 'Latest owner-installed testing candidate: `v0.4.0_17` / `os-zapret2-restyle-0.4.0_17.pkg`' "${PROJECT_STATE}" ||
    fail 'project state does not retain owner-installed _17'
grep -Fq 'Current package revision: `PLUGIN_REVISION=18`' "${PROJECT_STATE}" ||
    fail 'project state does not select revision 18'
grep -Fq "Current source candidate: \`${candidate}\`" "${PROJECT_STATE}" ||
    fail 'project state does not select the _18 source package'
grep -Fq 'repeated ACCEPT 5/5 on `_17`' "${PROJECT_STATE}" ||
    fail 'project state does not retain _17 repeated coexistence evidence'
grep -Fq 'MODEL B EXHAUSTIVE BENCHMARK — `_18` SOURCE CANDIDATE' "${PROJECT_STATE}" ||
    fail 'project state does not expose the exhaustive benchmark'
grep -Fq 'production Strategy Lab remains cold Model A' "${PROJECT_STATE}" ||
    fail 'project state accidentally approves warm production search'

sh -n "$0"
printf '%s\n' "PASS: FreeBSD 15 package/ABI contracts retain the established Strategy Lab validation and include ${candidate} exhaustive benchmark sources through complete-tree staging"
