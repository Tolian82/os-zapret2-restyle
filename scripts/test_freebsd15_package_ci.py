#!/usr/bin/env python3
"""Stage 2 official native package CI contract plus preserved Model-C tests."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent

def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")

def text(path: str) -> str:
    target = ROOT / path
    if not target.is_file():
        fail(f"required file is missing: {path}")
    return target.read_text(encoding="utf-8")

def require(path: str, needle: str) -> None:
    if needle not in text(path):
        fail(f"missing contract text in {path}: {needle}")

version = text("VERSION").strip()
if not re.fullmatch(r"\d+\.\d+\.\d+", version):
    fail(f"invalid VERSION: {version}")
makefile = text("Makefile")
match = re.search(r"^PLUGIN_REVISION=\s*(\d+)\s*$", makefile, re.MULTILINE)
if not match:
    fail("invalid PLUGIN_REVISION")
revision = int(match.group(1))
candidate = f"os-zapret2-restyle-{version}_{revision}.pkg"
require("Makefile", 'PLUGIN_DEPENDS=     python${PLUGIN_PYTHON} gmake pkgconf luajit git jq ca_root_nss')
require("Makefile", '.include "../../Mk/plugins.mk"')
require("scripts/build-pkg.sh", 'exec /usr/local/bin/python3')
require("scripts/build-pkg.sh", "native-opnsense-package.py")
require("scripts/native-opnsense-package.py", 'private.old.clone_official(Path(scratch))')
require("scripts/native-opnsense-package.py", "private.prepare_private(plugin")
require("scripts/native-opnsense-package.py", 'native_make_variables(plugin, sha, py, installed, platform)')
require("scripts/native-opnsense-package.py", 'policy_sha = stage_policy(plugin)')
require("scripts/native-opnsense-package.py", 'platform = qualified_target(py)')
require("scripts/native-opnsense-package.py", "verify_native_package(")
require("scripts/native-opnsense-package.py", '"publication_approved": False')
require("scripts/test-package-lifecycle-restart.sh", "ZAPRET2_TEST_PRE_INSTALL")
require("scripts/test-package-cold-kernel.py", "ZAPRET2_TEST_PRE_INSTALL")
require(".github/workflows/ci.yml", "scripts/test-native-package-hook-regression-contracts.py")
require(".github/workflows/ci.yml", "python3 scripts/test-native-package-hook-regression.py dist/*.pkg")
require(".github/workflows/ci.yml", 'name: Build official OPNsense 26.7 native package (source-only CI)')
require(".github/workflows/ci.yml", 'uses: vmactions/opnsense-vm@abaa977e3dbc77a0d1eeed4d82c8d9914b018235')
require(".github/workflows/ci.yml", 'copyback: true')
require(".github/workflows/ci.yml", 'ZAPRET2_NATIVE_BUILD_CI=1')
require(".github/workflows/ci.yml", 'scripts/test-freebsd15-package-ci')
require(".github/workflows/release.yml", 'name: Build package and pkg repository inside qualified OPNsense 26.7')
require(".github/workflows/release.yml", "native-product-installed-acceptance.json")
require(".github/workflows/release.yml", 'sh scripts/verify-release-package.sh')
require(".github/workflows/ci.yml", 'tar -tf dist/*.pkg > "${contents}"')
require(".github/workflows/ci.yml", 'tar -xOf dist/*.pkg +MANIFEST > "${manifest}"')
require(".github/workflows/ci.yml", '.abi == "FreeBSD:15:amd64"')
require(".github/workflows/ci.yml", 'has("ca_root_nss")')
require(".github/workflows/release.yml", 'pages/FreeBSD:15:amd64')
require("src/opnsense/scripts/OPNsense/Zapret/shared_apply_lock.php", "['/usr/bin/id', '-u']")
require("scripts/test-shared-apply-lock.sh", 'php -n "$ROOT/scripts/test-shared-apply-uid.php"')
require("src/opnsense/scripts/OPNsense/Zapret/shared_apply_request.php", 'SharedApplyLifecycleLock::effectiveUid()')
require("src/opnsense/scripts/OPNsense/Zapret/shared_apply_config.php", 'SharedApplyLifecycleLock::effectiveUid()')
builder = text("scripts/build-pkg.sh") + text("scripts/native-opnsense-package.py")
for obsolete in ("pkg-static create", "dep_origin()", "jq -n", "version\":\"0",
                 "find \"${STAGE}\" -type f -name \"*.sh\" -exec chmod",
                 'sed -n "s/^'):
    if obsolete in builder:
        fail(f"retired private builder logic remains: {obsolete}")
entry = "src/opnsense/scripts/OPNsense/Zapret/strategy_lab_python.py"
measurement = "src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/model_c_lifecycle_measurement.py"
lifecycle_test = "scripts/test-strategy-lab-model-c-lifecycle-measurement.sh"
model_c = "src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_model_c.py"
model_c_production = "src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_model_c_production.py"
model_b = "src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_parallel.py"
require(entry, "_prepare_model_c_lifecycle_runtime_permissions")
require(entry, "path.chmod(0o711)")
require(entry, "model-c-lifecycle-measure")
require(entry, "from strategy_lab_py import stage60_model_c_production as stage60_parallel")
require(lifecycle_test, "cleanup.stat().st_mode & 0o777) == 0o700")
require(lifecycle_test, "unexpected lifecycle measurement directory layout accepted")
require(measurement, 'POLICY = "model-c-batch-lifecycle-amortization-v1"')
require(measurement, "def _fallback_evidence")
require(measurement, "def _batch_comparison")
require(measurement, '"instrumented_batch_count_match"')
require(measurement, '"fallback_detected"')
require(measurement, 'inspect_model_c_fallback_reason_before_any_lifecycle_cost_or_reuse_decision')
require(measurement, '"production_model_changed": False')
require(measurement, '"production_search_semantics_changed": False')
require(measurement, '"production_dispatch_width_changed": False')
require(model_c, 'MODEL = "C-warm-bucket-source-port-dispatch"')
require(model_c_production, 'ModelCOnlyInfrastructureError(stage60_parallel.Stage60ParallelError)')
require(model_c_production, 'parallel["cold_fallback_available"] = False')
require(model_c_production, 'parallel["model_c_only"] = True')
require(model_b, 'MODEL = "B-warm-worker-parallel-batched"')
require("docs/decisions/DEC-2026-08-13-github-only-package-delivery.md", "Actions artifacts are build evidence, never final delivery")
for installed in (
    "strategy_lab_py/model_c_lifecycle_measurement.py",
    "strategy_lab_py/stage60_model_c_production.py",
    "strategy_lab_model_c_lifecycle_measurement.sh",
    "strategy_lab_model_c_lifecycle_measurement_worker.sh",
    "strategy_lab_python.py",
):
    if not (ROOT / "src/opnsense/scripts/OPNsense/Zapret" / installed).is_file():
        fail(f"packaged source path is missing: {installed}")
# The cancelled Remove Jail prototype must not be revived in packaged source,
# tests, or CI. Successful native GUI-path service startup replaces it.
for obsolete in (
    "src/opnsense/scripts/OPNsense/Zapret/extra_resources_jail_inputs.py",
    "src/opnsense/scripts/OPNsense/Zapret/extra_resources_jail_path_gate.py",
    "scripts/test-freebsd-lua-jail-upstream-engine.sh",
    "scripts/test-freebsd-lua-no-network-shim.sh",
    "scripts/test-extra-resources-jail-inputs.py",
):
    if (ROOT / obsolete).exists():
        fail(f"cancelled Remove jail prototype still present: {obsolete}")
workflow = text(".github/workflows/ci.yml")
if "scripts/test-freebsd-lua-jail" in workflow or "scripts/test-extra-resources-jail" in workflow:
    fail("cancelled Jail trial remains wired to CI")
require("docs/architecture/ZAPRET2_EXTRA_RESOURCES_REMOVE_SPEC.md",
        "real installed Zapret2 service")
require("docs/architecture/ZAPRET2_EXTRA_RESOURCES_REMOVE_PLAN.md",
        "native GUI-path prechecks")
print(f"PASS: Official OPNsense 26.7 package CI accepts current candidate {candidate} with Model-C-only production routing, retained lifecycle diagnostics, and explicit Model B/A reference tooling")
