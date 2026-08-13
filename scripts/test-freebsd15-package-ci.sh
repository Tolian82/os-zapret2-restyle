#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
CI="${ROOT_DIR}/.github/workflows/ci.yml"
RELEASE="${ROOT_DIR}/.github/workflows/release.yml"
PROJECT_STATE="${ROOT_DIR}/docs/PROJECT_STATE.md"
INDEX="${ROOT_DIR}/docs/INDEX.md"
GITHUB_ONLY_PACKAGE_DECISION="${ROOT_DIR}/docs/decisions/DEC-2026-08-13-github-only-package-delivery.md"
RELEASE_DOC="${ROOT_DIR}/docs/releases/v0.4.1.md"
RELEASE_EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.1-release-publication.md"
LUA_PUBLICATION="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.1_2-lua-init-publication.md"
LUA_LIVE="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.1_2-lua-init-live-pass.md"
BLOB_PUBLICATION="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.1_3-blob-measurement-publication.md"
BLOB_LIVE="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.1_3-blob-startup-rss-live-pass.md"
BLOB4_PUBLICATION="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.1_4-blob-common-set-publication.md"
BLOB4_LIVE="${ROOT_DIR}/docs/verification/evidence/2026-08-12-v0.4.1_4-blob-common-set-live-pass.md"
DISCOVERY_PUBLICATION="${ROOT_DIR}/docs/verification/evidence/2026-08-13-v0.4.1_5-discovery-probe-publication.md"
BUILD_PKG="${ROOT_DIR}/scripts/build-pkg.sh"
VERSION_FILE="${ROOT_DIR}/VERSION"
MAKEFILE="${ROOT_DIR}/Makefile"
CORRECTIVE_MATRIX="${ROOT_DIR}/scripts/test-strategy-lab-corrective-matrix.sh"
LUA_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/lua_initialization_measurement.py"
BLOB_TEST="${ROOT_DIR}/scripts/test-strategy-lab-blob-startup-measurement.sh"
BLOB_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/blob_startup_measurement.py"
BLOB_WRAPPER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_blob_measurement.sh"
BLOB_WORKER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_blob_measurement_worker.sh"
BLOB_DOC="${ROOT_DIR}/docs/architecture/STRATEGY_LAB_BLOB_LOADING.md"
BLOB_PATCH="${ROOT_DIR}/docs/patches/v0.4.1_4.md"
DISCOVERY_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/discovery_probe_measurement.py"
DISCOVERY_WRAPPER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_discovery_probe_measurement.sh"
DISCOVERY_WORKER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_discovery_probe_measurement_worker.sh"
DISCOVERY_PATCH="${ROOT_DIR}/docs/patches/v0.4.1_5.md"
RESOURCES_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/resources.py"
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
    "${CI}" "${RELEASE}" "${PROJECT_STATE}" "${INDEX}" "${GITHUB_ONLY_PACKAGE_DECISION}" "${RELEASE_DOC}" \
    "${RELEASE_EVIDENCE}" "${LUA_PUBLICATION}" "${LUA_LIVE}" "${BLOB_PUBLICATION}" "${BLOB_LIVE}" \
    "${BLOB4_PUBLICATION}" "${BLOB4_LIVE}" "${DISCOVERY_PUBLICATION}" "${BUILD_PKG}" "${VERSION_FILE}" "${MAKEFILE}" "${CORRECTIVE_MATRIX}" \
    "${LUA_PY}" "${BLOB_TEST}" "${BLOB_PY}" "${BLOB_WRAPPER}" "${BLOB_WORKER}" \
    "${BLOB_DOC}" "${BLOB_PATCH}" "${DISCOVERY_PY}" "${DISCOVERY_WRAPPER}" "${DISCOVERY_WORKER}" "${DISCOVERY_PATCH}" \
    "${RESOURCES_PY}" "${ADAPTIVE_BUDGET_PY}" "${MODEL_C_PY}" "${MODEL_B_PY}" "${LEASE_PY}" "${PYTHON_ENTRY}" \
    "${PUBLICATION26}" "${LIVE26}" "${MODEL_C_CORRECTIVE_PASS}" "${MODEL_B_LIVE}"
do
    [ -s "${file}" ] || fail "required file is missing: ${file}"
done

version=$(tr -d '[:space:]' < "${VERSION_FILE}")
revision=$(awk -F= '/^PLUGIN_REVISION=/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${MAKEFILE}")
case "${revision}" in ''|*[!0-9]*) fail 'invalid plugin revision' ;; esac
candidate="os-zapret2-restyle-${version}_${revision}.pkg"
[ "${version}" = '0.4.1' ] || fail 'measurement line must retain VERSION=0.4.1'
[ "${revision}" -eq 5 ] || fail 'discovery measurement package must use PLUGIN_REVISION=5'
[ "${candidate}" = 'os-zapret2-restyle-0.4.1_5.pkg' ] || fail 'unexpected discovery measurement package identity'

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

require "${RELEASE}" 'VERSION_VALUE=$(tr -d '\''[:space:]'\'' < VERSION)'
require "${RELEASE}" 'REVISION=$(sed -n '\''s/^PLUGIN_REVISION=[[:space:]]*//p'\'' Makefile | head -1)'
require "${RELEASE}" 'PACKAGE_VERSION="${VERSION_VALUE}_${REVISION}"'
require "${RELEASE}" 'sh scripts/build-pkg.sh'
require "${RELEASE}" 'sh scripts/verify-release-package.sh'
require "${RELEASE}" 'sh scripts/build-pkg-repository.sh'
require "${RELEASE}" 'pages/FreeBSD:15:amd64/'

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

require "${CORRECTIVE_MATRIX}" "find \"\${ROOT_DIR}/scripts\" -maxdepth 1 -type f -name 'test-strategy-lab-*.sh'"
require "${RESOURCES_PY}" 'DEFAULT_LUA_ROOT = Path("/usr/local/etc/zapret2/lua")'
require "${RESOURCES_PY}" 'DEFAULT_FAKE_ROOT = Path("/usr/local/etc/zapret2/files/fake")'
require "${RESOURCES_PY}" 'def configured_lua_root()'
require "${LUA_PY}" 'resources.configured_lua_root()'
require "${BLOB_PY}" 'SCHEMA = 2'
require "${BLOB_PY}" 'POLICY = "blob-common-set-scaling-v1"'
require "${BLOB_PY}" 'CACHE_POLICY = "natural-cache-no-drop"'
require "${BLOB_PY}" 'WORKER = "external"'
require "${BLOB_PY}" 'DIVERT_PORT = 9992'
require "${BLOB_PY}" 'PRODUCTION_CANDIDATE_WIDTH = 3'
require "${BLOB_PY}" 'production_change_recommended'
require "${BLOB_TEST}" 'PASS: BLOB common-set scaling measurement is single-worker, balanced, lifecycle-safe'
require "${BLOB_DOC}" '_3 ACCEPTED / _4 ACCEPTED / BLOB-LOADING OPTIMIZATION CLOSED / PRODUCTION MODEL C UNCHANGED'
require "${BLOB_PATCH}" 'SOURCE / CI / FREEBSD15 PACKAGE / PUBLICATION / OWNER-LIVE PASS'
require "${BLOB_WRAPPER}" 'zapret2-lifecycle.lock'
require "${BLOB_WRAPPER}" 'TRIALS="${2:-12}"'
require "${BLOB_WORKER}" 'strategy-lab-evidence'
if grep -Fq 'route-add' "${BLOB_WORKER}" || grep -Fq 'strategy-lab-stop' "${BLOB_WORKER}"; then
    fail 'BLOB measurement worker must not route traffic or stop production Zapret'
fi
require "${PYTHON_ENTRY}" 'from strategy_lab_py import blob_startup_measurement'
require "${PYTHON_ENTRY}" 'blob-startup-measure'

require "${DISCOVERY_PY}" 'POLICY = "discovery-probe-agreement-v1"'
require "${DISCOVERY_PY}" 'VARIANTS = ("head", "get-1", "get-4k", "deep-16k")'
require "${DISCOVERY_PY}" 'production_discovery_policy_changed": False'
require "${DISCOVERY_PY}" 'production_change_recommended": False'
require "${DISCOVERY_WRAPPER}" 'zapret2-lifecycle.lock'
require "${DISCOVERY_WORKER}" 'strategy-lab-evidence'
require "${DISCOVERY_WORKER}" 'strategy-lab-stop'
require "${PYTHON_ENTRY}" 'from strategy_lab_py import discovery_probe_measurement'
require "${PYTHON_ENTRY}" 'discovery-probe-measure'
require "${DISCOVERY_PATCH}" 'GitHub Actions FreeBSD-15 build artifact'
require "${DISCOVERY_PATCH}" 'not** a tag, GitHub Release, prerelease, Pages update, or package-repository publication'
require "${DISCOVERY_PATCH}" 'Persistent GitHub test package publication'

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
    strategy_lab_py/blob_startup_measurement.py \
    strategy_lab_py/discovery_probe_measurement.py \
    strategy_lab_model_c.lua \
    strategy_lab_blob_measurement.sh \
    strategy_lab_blob_measurement_worker.sh \
    strategy_lab_discovery_probe_measurement.sh \
    strategy_lab_discovery_probe_measurement_worker.sh \
    strategy_lab_python.py
do
    [ -e "${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/${installed}" ] || fail "packaged source path is missing: ${installed}"
done

require "${PROJECT_STATE}" 'Current source line: `VERSION=0.4.1`, `PLUGIN_REVISION=5`'
require "${PROJECT_STATE}" 'Current source candidate: `os-zapret2-restyle-0.4.1_5.pkg`'
require "${PROJECT_STATE}" 'Current published stable package: `os-zapret2-restyle-0.4.1_1.pkg`'
require "${PROJECT_STATE}" 'Latest persistently published testing package: `v0.4.1_5` / `os-zapret2-restyle-0.4.1_5.pkg`'
require "${PROJECT_STATE}" 'Latest owner-tested testing candidate: `v0.4.1_4` — BLOB common-set scaling measurement PASS'
require "${PROJECT_STATE}" 'Latest detailed Strategy Lab runtime basis: `v0.4.0_26` — adaptive-budget owner-live PASS'
require "${PROJECT_STATE}" 'V0.4.1_5 DISCOVERY PROBE AGREEMENT — PUBLISHED / OWNER-LIVE PENDING'
require "${PROJECT_STATE}" 'publication workflow run `31652568754` / #42 — SUCCESS'
require "${PROJECT_STATE}" 'sha256:f3c55966658d336a3f51a76d0847f194f79ba13d9e140553e7fa9c308ec5f6ce'
require "${GITHUB_ONLY_PACKAGE_DECISION}" 'Actions artifacts are build evidence, never final delivery'
require "${GITHUB_ONLY_PACKAGE_DECISION}" 'Every owner-facing package is delivered from GitHub'
require "${INDEX}" 'docs/decisions/DEC-2026-08-13-github-only-package-delivery.md'
require "${INDEX}" 'docs/verification/evidence/2026-08-13-v0.4.1_5-discovery-probe-publication.md'
require "${INDEX}" 'docs/architecture/STRATEGY_LAB_BLOB_LOADING.md'
require "${INDEX}" 'docs/patches/v0.4.1_4.md'
require "${INDEX}" 'docs/verification/evidence/2026-08-12-v0.4.1_4-blob-common-set-publication.md'
require "${INDEX}" 'docs/verification/evidence/2026-08-12-v0.4.1_4-blob-common-set-live-pass.md'
require "${INDEX}" 'docs/verification/evidence/2026-08-12-v0.4.1_3-blob-measurement-publication.md'
require "${INDEX}" 'docs/verification/evidence/2026-08-12-v0.4.1_3-blob-startup-rss-live-pass.md'
require "${RELEASE_DOC}" '`v0.4.1_1: Prepare release v0.4.1`'

require "${RELEASE_EVIDENCE}" 'Status: **PUBLISHED**'
require "${RELEASE_EVIDENCE}" 'os-zapret2-restyle-0.4.1_1.pkg'
require "${LUA_PUBLICATION}" '462c55b291ac737eb368ee9ec5e4f139bd239665'
require "${LUA_PUBLICATION}" 'os-zapret2-restyle-0.4.1_2.pkg'
require "${LUA_LIVE}" 'Status: **PASS**'
require "${LUA_LIVE}" 'checks.all_required_files_present=true'
require "${LUA_LIVE}" 'conclusion=equivalent_init_set'
require "${BLOB_PUBLICATION}" 'Status: **PUBLISHED / OWNER-LIVE PENDING**'
require "${BLOB_PUBLICATION}" 'da427cd061df1f3cbc01ba11a14a6417f2e406b3'
require "${BLOB_PUBLICATION}" '31616501996'
require "${BLOB_PUBLICATION}" '369373181'
require "${BLOB_PUBLICATION}" 'os-zapret2-restyle-0.4.1_3.pkg'
require "${BLOB_PUBLICATION}" 'sha256:6efdb8e844bdec5cbe2fddffd77c1234cc53b939520c4648ed68da3126e7989b'
require "${BLOB_LIVE}" 'Status: **PASS**'
require "${BLOB_LIVE}" 'Final report conclusion: `measurement_accepted`.'
require "${BLOB_LIVE}" 'Median ready and settled RSS was exactly `4360 KiB` for all three variants.'
require "${BLOB_LIVE}" 'Do **not** change production Model C BLOB loading.'
require "${BLOB4_PUBLICATION}" 'Status: **PUBLISHED / OWNER-LIVE PENDING**'
require "${BLOB4_PUBLICATION}" '461fe2d045b131f3400f285a9cb59808b5f33ce2'
require "${BLOB4_PUBLICATION}" '31633335688'
require "${BLOB4_PUBLICATION}" '369482221'
require "${BLOB4_PUBLICATION}" 'os-zapret2-restyle-0.4.1_4.pkg'
require "${BLOB4_PUBLICATION}" 'sha256:934fdd3a73117b3d914c9823f29eb7f2ca47196d97c30d94e3066a38159edbc9'
require "${BLOB4_LIVE}" 'Status: **PASS**'
require "${BLOB4_LIVE}" 'Final report conclusion: `measurement_accepted`.'
require "${BLOB4_LIVE}" '`48` planned starts'
require "${BLOB4_LIVE}" '`+0.234 ms` / `+0.375%`'
require "${BLOB4_LIVE}" '`+2 KiB` / `+0.046%`'
require "${BLOB4_LIVE}" 'close the BLOB-loading startup/RSS optimization as a negative result for current width three'
require "${DISCOVERY_PUBLICATION}" 'Status: **PUBLISHED / OWNER-LIVE PENDING**'
require "${DISCOVERY_PUBLICATION}" '31652568754'
require "${DISCOVERY_PUBLICATION}" '369590644'
require "${DISCOVERY_PUBLICATION}" '512227845'
require "${DISCOVERY_PUBLICATION}" 'os-zapret2-restyle-0.4.1_5.pkg'
require "${DISCOVERY_PUBLICATION}" 'sha256:f3c55966658d336a3f51a76d0847f194f79ba13d9e140553e7fa9c308ec5f6ce'
require "${PUBLICATION26}" '8ada9cba28916fff506f19b34f5ef3de16e2008e'
require "${LIVE26}" 'Status: **PASS**'
require "${LIVE26}" 'job.xhdgCU'
require "${LIVE26}" '.parallel.fallbacks=[]'
require "${MODEL_C_CORRECTIVE_PASS}" 'job.5yGde5'
require "${MODEL_B_LIVE}" 'PRODUCTION STAGE-60 MODEL B OWNER-LIVE PASS'

sh -n "$0"
printf '%s\n' "PASS: FreeBSD 15 package CI accepts published measurement-only ${candidate}; Actions remains build evidence, persistent GitHub package publication is owner delivery, and production runtime truth remains unchanged"
