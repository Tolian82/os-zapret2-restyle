#!/usr/bin/env python3
"""Regression: Remove builds a SAVED, UNCHANGED candidate in the GUI pipeline."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/opnsense/scripts/OPNsense/Zapret"
service = (SRC / "zapret_service.sh").read_text()
request = (SRC / "shared_apply_request.php").read_text()
worker = (SRC / "extra_resources_operation.py").read_text()


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise AssertionError(reason)


def section(text: str, begin: str, end: str) -> str:
    require(text.count(begin) == 1, "missing or ambiguous anchor: " + begin)
    return text.split(begin, 1)[1].split(end, 1)[0]


saved = section(request, "public static function prepareSavedUnchanged(",
                "private static function secureDir(")
require("self::prepare([" in saved and "'fields' => []" in saved and
        "'page' => 'strategies'" in saved,
        "saved candidate bypasses original Strategies Apply candidate API")
require("SettingsApply::renderCandidateXml" not in saved and
        "VoiceSettingsSnapshot::digest($current)" in saved,
        "saved candidate changed the normal preparation or generation witness")
require("$prepared['plan']['candidate'] !== $current" in saved and
        "$prepared['xml'] !== $activeXml" in saved,
        "saved candidate can rewrite persisted Config")
require("'saved-unchanged'" in request and
        "self::materialize($prepared)" in request,
        "original detached workspace writer is not reused")
gate = section(service, "extra_resources_native_build_saved_service()",
               "# Internal root-only Apply phases;")
require('EXTRA_RESOURCES_SETUP_LOCK_OWNER:-0' in gate and
        'EXTRA_RESOURCES_NATIVE_REMOVE_TRIAL:-0' in gate and
        'preflight_shared_apply_journal common-apply' in gate,
        "saved native trial omitted inherited lock/owner gate")
require('shared_apply_request.php" saved-unchanged' in gate and
        'shared_apply_prepare_service "$_extra_saved_id"' in gate and
        'shared_apply_bundle_service verify "$_extra_saved_id"' in gate and
        'shared_apply_native_config preflight' in gate,
        "trial does not use the exact full GUI common Apply compiler/validator")
for forbidden in ("apply_runtime_activate", "shared_apply_native_config save",
                  "start_service", "strategy-lab-start", "orchestrator_build_release ",
                  "hostlist-exclude", "--ipset-exclude"):
    require(forbidden not in gate, "saved compiler seam rewrites or activates: " + forbidden)
require('extra-resources-native-build-saved)' in service and
        'strategy_lab_internal_dispatch "$@"' in service and
        'EXTRA_RESOURCES_NATIVE_REMOVE_TRIAL:-0' in service,
        "saved build is not restricted to original inherited FD9 path")
require("def start_trial_native_common_apply" not in worker,
        "builder mistakenly granted destructive Remove authorization")
for cmd in (["php", "-l", str(SRC / "shared_apply_request.php")],
            ["sh", "-n", str(SRC / "zapret_service.sh")],
            ["php", str(ROOT / "scripts/test-shared-apply-request.php")]):
    p = subprocess.run(cmd, text=True, capture_output=True)
    require(p.returncode == 0, cmd[0] + " native syntax/candidate: " + p.stderr + p.stdout)
print("PASS: saved unchanged Strategies+Voice candidate reuses original GUI builder and inherited FD9")
