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
if not re.search(r"^PLUGIN_DEPENDS=\s*python313\s*$", makefile, re.MULTILINE):
    fail("python313 dependency is missing")

require("scripts/build-pkg.sh", 'python313)  echo "lang/python313"')
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
# CI-only FreeBSD jail programs must never quietly skip the only platform
# that can compile and execute them. Parse the actual change-classifier regex,
# not an independent approximation of its rules.
workflow = text(".github/workflows/ci.yml")
classifier_lines = [
    line for line in workflow.splitlines()
    if "elif printf '%s" in line and '"${changed}"' in line
    and "grep -Eq '" in line
]
if len(classifier_lines) != 1 or "'; then" not in classifier_lines[0]:
    fail("cannot locate unique actual FreeBSD/package change classifier")
selector = classifier_lines[0].split("grep -Eq '", 1)[1].split("'; then", 1)[0]
for path in (
    ".github/workflows/ci.yml",
    "src/opnsense/scripts/OPNsense/Zapret/extra_resources_jail_inputs.py",
    "scripts/test-freebsd15-package-ci.sh",
    "scripts/test-freebsd-lua-jail-upstream-engine.sh",
    "scripts/test-freebsd-lua-jail-shim-combined.sh",
    "scripts/test-freebsd-lua-no-network-shim.sh",
    "scripts/fixtures/lua-jail-native-boundary.c",
    "scripts/fixtures/lua-jail-stage-ci-elf.py",
    "scripts/fixtures/lua-init-no-network-shim.c",
):
    if not re.search(selector, path):
        fail(f"FreeBSD jail change bypasses FreeBSD CI: {path}")
for path in (
    "docs/START_HERE.md",
    "README.md",
    "scripts/test-extra-resources-jail-inputs.py",
    "scripts/test-strategy-lab-python-foundation.sh",
):
    if re.search(selector, path):
        fail(f"unrelated file unexpectedly triggers FreeBSD CI: {path}")

print(f"PASS: FreeBSD 15 package CI accepts current candidate {candidate} with Model-C-only production routing, retained lifecycle diagnostics, and explicit Model B/A reference tooling")
