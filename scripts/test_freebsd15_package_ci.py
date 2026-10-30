#!/usr/bin/env python3
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
if not re.search(r"^PLUGIN_NAME=\s*zapret2-restyle\s*$", makefile, re.MULTILINE):
    fail("plugin name mismatch")
compat = text("src/opnsense/scripts/OPNsense/Zapret/python_runtime.conf")
if not re.search(r"^ZAPRET_PYTHON_PACKAGE=python313$", compat, re.MULTILINE):
    fail("central dependency manifest missing current native package")
if not re.search(r"^PLUGIN_DEPENDS=\s*\$\{ZAPRET_PYTHON_PACKAGE\}\s*$", makefile, re.MULTILINE):
    fail("Makefile must derive the Python dependency from the manifest")

require("scripts/build-pkg.sh", 'python3[0-9][0-9]) echo "lang/$1"')
require("scripts/build-pkg.sh", 'PLUGIN_DEPENDS="${ZAPRET_PYTHON_PACKAGE}"')
require("scripts/build-pkg.sh", 'cp -R src/opnsense "${STAGE}/usr/local/opnsense"')
require(".github/workflows/ci.yml", 'release: "15.0"')
require(".github/workflows/release.yml", "release: '15.0'")
require(".github/workflows/ci.yml", 'pkg install -y jq python313')
require(".github/workflows/ci.yml", 'and (.deps | has("php85-posix") | not)')
require(".github/workflows/release.yml", 'prepare: pkg install -y jq')
require("src/opnsense/scripts/OPNsense/Zapret/shared_apply_lock.php", "['/usr/bin/id', '-u']")
require("scripts/test-shared-apply-lock.sh", 'php -n "$ROOT/scripts/test-shared-apply-uid.php"')
require("src/opnsense/scripts/OPNsense/Zapret/shared_apply_request.php", 'SharedApplyLifecycleLock::effectiveUid()')
require("src/opnsense/scripts/OPNsense/Zapret/shared_apply_config.php", 'SharedApplyLifecycleLock::effectiveUid()')
require(".github/workflows/ci.yml", 'tar -tf dist/*.pkg > "${contents}"')
require(".github/workflows/ci.yml", 'tar -xOf dist/*.pkg +MANIFEST > "${manifest}"')
require(".github/workflows/ci.yml", '.abi == "FreeBSD:15:amd64"')
require(".github/workflows/ci.yml", '.arch == "freebsd:15:x86:64"')
require(".github/workflows/ci.yml", '.deps.python313.origin == "lang/python313"')
require(".github/workflows/ci.yml", 'freebsd-version -u')
require(".github/workflows/ci.yml", 'scripts/test-freebsd15-package-ci')

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
print(f"PASS: FreeBSD 15 package CI accepts current candidate {candidate} with Model-C-only production routing, retained lifecycle diagnostics, and explicit Model B/A reference tooling")
