#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
CI="${ROOT_DIR}/.github/workflows/ci.yml"
RELEASE="${ROOT_DIR}/.github/workflows/release.yml"
MATRIX="${ROOT_DIR}/docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md"
PROJECT_STATE="${ROOT_DIR}/docs/PROJECT_STATE.md"
INDEX="${ROOT_DIR}/docs/INDEX.md"
RELEASE_DOC="${ROOT_DIR}/docs/releases/v0.4.1.md"
RELEASE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.1-release-publication.md"
BUILD_PKG="${ROOT_DIR}/scripts/build-pkg.sh"
VERSION_FILE="${ROOT_DIR}/VERSION"
MAKEFILE="${ROOT_DIR}/Makefile"
CORRECTIVE_MATRIX="${ROOT_DIR}/scripts/test-strategy-lab-corrective-matrix.sh"
LUA_TEST="${ROOT_DIR}/scripts/test-strategy-lab-lua-initialization-measurement.sh"
LUA_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/lua_initialization_measurement.py"
LUA_DOC="${ROOT_DIR}/docs/architecture/STRATEGY_LAB_LUA_INITIALIZATION.md"
LUA_PATCH="${ROOT_DIR}/docs/patches/v0.4.1_2.md"
ADAPTIVE_BUDGET_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/adaptive_budget.py"
MODEL_C_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_model_c.py"
MODEL_B_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_parallel.py"
LEASE_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_source_port_lease.py"
PYTHON_ENTRY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_python.py"
PUBLICATION26="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.0_26-publication.md"
LIVE26="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.0_26-adaptive-budget-live-pass.md"
MODEL_C_CORRECTIVE_PASS="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.0_25-source-port-live-pass.md"
MODEL_B_LIVE="${ROOT_DIR}/docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md"

fail(){ echo "FAIL: $*" >&2; exit 1; }
require(){ grep -Fq "$2" "$1" || fail "missing contract text in $1: $2"; }

for file in \
    "${CI}" "${RELEASE}" "${MATRIX}" "${PROJECT_STATE}" "${INDEX}" "${RELEASE_DOC}" \
    "${RELEASE_EVIDENCE}" "${BUILD_PKG}" "${VERSION_FILE}" "${MAKEFILE}" "${CORRECTIVE_MATRIX}" \
    "${LUA_TEST}" "${LUA_PY}" "${LUA_DOC}" "${LUA_PATCH}" "${ADAPTIVE_BUDGET_PY}" \
    "${MODEL_C_PY}" "${MODEL_B_PY}" "${LEASE_PY}" "${PYTHON_ENTRY}" \
    "${PUBLICATION26}" "${LIVE26}" "${MODEL_C_CORRECTIVE_PASS}" "${MODEL_B_LIVE}"
do
    [ -s "${file}" ] || fail "required file is missing: ${file}"
done

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(awk -F= '/^PLUGIN_REVISION=/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${MAKEFILE}")
case "${revision}" in ''|*[!0-9]*) fail 'invalid plugin revision' ;; esac
candidate="os-zapret2-restyle-${version}_${revision}.pkg"
[ "${version}" = '0.4.1' ] || fail 'measurement line must retain VERSION=0.4.1'
[ "${revision}" -eq 2 ] || fail 'Lua measurement package must use PLUGIN_REVISION=2'
[ "${candidate}" = 'os-zapret2-restyle-0.4.1_2.pkg' ] || fail 'unexpected measurement package identity'

# Package construction and ABI/runtime requirements remain unchanged.
grep -Eq '^PLUGIN_DEPENDS=[[:space:]]+python313([[:space:]]|$)' "${MAKEFILE}" || fail 'python313 dependency is missing'
require "${BUILD_PKG}" 'python313)  echo "lang/python313"'
require "${BUILD_PKG}" 'cp -R src/opnsense "${STAGE}/usr/local/opnsense"'
require "${CI}" 'release: "15.0"'
require "${RELEASE}" "release: '15.0'"
if grep -REn "release:[[:space:]]*['\"]?14([.]|['\"]|$)" "${ROOT_DIR}/.github/workflows"; then
    fail 'a GitHub workflow still selects FreeBSD 14'
fi
require "${CI}" 'python-version: "3.13"'
require "${CI}" 'STRATEGY_LAB_PYTHON_BIN: python3.13'
require "${CI}" 'pkg install -y jq python313'
require "${CI}" 'tar -tf dist/*.pkg > "${contents}"'
require "${CI}" 'tar -xOf dist/*.pkg +MANIFEST > "${manifest}"'
require "${CI}" '.abi == "FreeBSD:15:amd64"'
require "${CI}" '.arch == "freebsd:15:x86:64"'
require "${CI}" '.deps.python313.origin == "lang/python313"'
require "${CI}" 'freebsd-version -u'
require "${CI}" 'scripts/test-freebsd15-package-ci'

# Stable release workflow remains version/revision-derived; `_2` must not rewrite v0.4.1 history.
require "${RELEASE}" 'VERSION_VALUE=$(tr -d '\''[:space:]'\'' < VERSION)'
require "${RELEASE}" 'REVISION=$(sed -n '\''s/^PLUGIN_REVISION=[[:space:]]*//p'\'' Makefile | head -1)'
require "${RELEASE}" 'PACKAGE_VERSION="${VERSION_VALUE}_${REVISION}"'
require "${RELEASE}" 'sh scripts/build-pkg.sh'
require "${RELEASE}" 'sh scripts/verify-release-package.sh'
require "${RELEASE}" 'sh scripts/build-pkg-repository.sh'
require "${RELEASE}" 'pages/FreeBSD:15:amd64/'
require "${RELEASE}" 'SHA256SUMS'
require "${RELEASE}" 'softprops/action-gh-release@v3'
require "${RELEASE}" 'actions/deploy-pages@v5'

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
    require "${CI}" "STRATEGY_LAB_TEST_PYTHON=/usr/local/bin/python3.13 sh scripts/${test}"
done

# Canonical matrix and new measurement contract.
require "${CORRECTIVE_MATRIX}" "find \"\${ROOT_DIR}/scripts\" -maxdepth 1 -type f -name 'test-strategy-lab-*.sh'"
require "${LUA_TEST}" 'PASS: Model C already uses the candidate-minimal Lua union'
require "${LUA_PY}" 'POLICY = "lua-init-set-equivalence-v1"'
require "${LUA_PY}" 'runtime_comparison_required = not all_batches_equivalent'
require "${LUA_PY}" 'not_applicable_equivalent_init_set'
require "${LUA_DOC}" 'MEASUREMENT-ONLY / PRODUCTION MODEL C UNCHANGED'
require "${LUA_PATCH}" 'SOURCE CANDIDATE / OWNER-LIVE PENDING'
require "${PYTHON_ENTRY}" 'from strategy_lab_py import lua_initialization_measurement'
require "${PYTHON_ENTRY}" 'lua-init-measure'

# Accepted production runtime must stay intact.
require "${ADAPTIVE_BUDGET_PY}" 'POLICY = "eligible-work-v1"'
require "${MODEL_C_PY}" 'MODEL = "C-warm-bucket-source-port-dispatch"'
require "${MODEL_C_PY}" 'for name in spec.lua_dependencies'
require "${MODEL_C_PY}" 'lua_names.append("zapret-auto.lua")'
require "${MODEL_C_PY}" 'arguments.append(f"--lua-init=@{selector_lua}")'
require "${MODEL_C_PY}" 'ThreadPoolExecutor(max_workers=len(decisions)'
require "${MODEL_B_PY}" 'MODEL = "B-warm-worker-parallel-batched"'
require "${MODEL_B_PY}" 'WIDTH = 3'
require "${MODEL_B_PY}" 'A-cold-fallback'
require "${LEASE_PY}" 'preferred-free-else-alternate'
require "${LEASE_PY}" 'original_model_b_batch'

for installed in \
    strategy_lab_py/state.py \
    strategy_lab_py/orchestrator.py \
    strategy_lab_py/adaptive_budget.py \
    strategy_lab_py/resources.py \
    strategy_lab_py/candidate_spec.py \
    strategy_lab_py/search_graph.py \
    strategy_lab_py/search.py \
    strategy_lab_py/extended.py \
    strategy_lab_py/stage60_parallel.py \
    strategy_lab_py/stage60_model_c.py \
    strategy_lab_py/stage60_source_port_lease.py \
    strategy_lab_py/lua_initialization_measurement.py \
    strategy_lab_model_c.lua \
    strategy_lab_python.py
do
    [ -e "${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/${installed}" ] || fail "packaged source path is missing: ${installed}"
done

# Current `_2` source boundary plus immutable stable publication/runtime evidence.
require "${PROJECT_STATE}" 'Current source line: `VERSION=0.4.1`, `PLUGIN_REVISION=2`'
require "${PROJECT_STATE}" 'Current source candidate: `os-zapret2-restyle-0.4.1_2.pkg`'
require "${PROJECT_STATE}" 'Current published release tag: `v0.4.1`'
require "${PROJECT_STATE}" 'Current published stable package: `os-zapret2-restyle-0.4.1_1.pkg`'
require "${PROJECT_STATE}" 'Latest owner-tested stable package: `os-zapret2-restyle-0.4.1_1.pkg` — upgrade/install smoke PASS'
require "${PROJECT_STATE}" 'Latest detailed Strategy Lab runtime basis: `v0.4.0_26` — adaptive-budget owner-live PASS'
require "${INDEX}" 'docs/architecture/STRATEGY_LAB_LUA_INITIALIZATION.md'
require "${INDEX}" 'docs/patches/v0.4.1_2.md'
require "${RELEASE_DOC}" '`v0.4.1_1: Prepare release v0.4.1`'

require "${RELEASE_EVIDENCE}" 'Status: **PUBLISHED**'
require "${RELEASE_EVIDENCE}" 'c53e1c1656517fa764f97a175bb82eea02dbc374'
require "${RELEASE_EVIDENCE}" 'os-zapret2-restyle-0.4.1_1.pkg'
require "${RELEASE_EVIDENCE}" 'sha256:cb481b37ed5ef6b57360ecbe7f1678b75d2d8e6520beb92e3d624b1bc9eb837e'
require "${PUBLICATION26}" '8ada9cba28916fff506f19b34f5ef3de16e2008e'
require "${LIVE26}" 'Status: **PASS**'
require "${LIVE26}" 'job.xhdgCU'
require "${LIVE26}" 'C-warm-bucket-source-port-dispatch'
require "${LIVE26}" '.parallel.fallbacks=[]'
require "${MODEL_C_CORRECTIVE_PASS}" 'job.5yGde5'
require "${MODEL_B_LIVE}" 'PRODUCTION STAGE-60 MODEL B OWNER-LIVE PASS'

sh -n "$0"
printf '%s\n' "PASS: FreeBSD 15 package CI qualifies ${candidate} while preserving stable v0.4.1 and _26 runtime evidence"
