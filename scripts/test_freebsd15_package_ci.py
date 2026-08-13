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
if not re.search(r"^PLUGIN_DEPENDS=\s*python313(?:\s|$)", makefile, re.MULTILINE):
    fail("python313 dependency is missing")

require("scripts/build-pkg.sh", 'python313)  echo "lang/python313"')
require("scripts/build-pkg.sh", 'cp -R src/opnsense "${STAGE}/usr/local/opnsense"')
require(".github/workflows/ci.yml", 'release: "15.0"')
require(".github/workflows/release.yml", "release: '15.0'")
require(".github/workflows/ci.yml", 'pkg install -y jq python313')
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
model_b = "src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_parallel.py"
require(entry, "_prepare_model_c_lifecycle_runtime_permissions")
require(entry, "path.chmod(0o711)")
require(entry, "model-c-lifecycle-measure")
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
require(model_b, 'MODEL = "B-warm-worker-parallel-batched"')
require("docs/decisions/DEC-2026-08-13-github-only-package-delivery.md", "Actions artifacts are build evidence, never final delivery")
for installed in (
    "strategy_lab_py/model_c_lifecycle_measurement.py",
    "strategy_lab_model_c_lifecycle_measurement.sh",
    "strategy_lab_model_c_lifecycle_measurement_worker.sh",
    "strategy_lab_python.py",
):
    if not (ROOT / "src/opnsense/scripts/OPNsense/Zapret" / installed).is_file():
        fail(f"packaged source path is missing: {installed}")
print(f"PASS: FreeBSD 15 package CI accepts current candidate {candidate} with lifecycle traversal/fallback diagnostics and unchanged production models")
