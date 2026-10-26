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
               "# Restore the original sealed, STOPPED common runtime")
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
owner_gate = section(service, "extra_resources_native_previous_owner_service()",
                     "# Internal staging seam for Remove Additional Resources.")
for expected in ("preflight_shared_apply_journal strategy-lab-native",
                 'shared_apply_operation.py" owner-witness',
                 "shared_apply_inspect_service",
                 "shared_apply_bundle_service verify",
                 "shared_apply_native_config saved",
                 "atomic_verify_tree",
                 "apply_runtime_probe",
                 "shared_apply_status_observe_service"):
    require(expected in owner_gate, "prior owner bypasses native proof: " + expected)
for forbidden in ("apply_runtime_activate", "apply_runtime_commit",
                  "start_service", "stop_service"):
    require(forbidden not in owner_gate, "owner witness mutates runtime: " + forbidden)
require("shared_apply_native_config save " not in owner_gate,
        "owner witness must never save native Config")
require("extra-resources-native-previous-owner)" in service and
        "capture_previous_native_common_apply" in worker,
        "prior owner not connected to inherited-FD9 resource lifecycle")
restore_section = section(service, "extra_resources_native_restore_previous_service()",
                          "# Explicit operator-only closure of the FIRST failed Voice handoff.")
for must in ("EXTRA_RESOURCES_NATIVE_REMOVE_RESTORE", "remove-rollback-pair",
             "shared_apply_bundle_service verify", "shared_apply_native_config saved",
             "atomic_verify_tree", "shared_apply_boot_service",
             "apply_runtime_activate", "apply_runtime_attest_activated",
             "apply_runtime_commit", "apply_runtime_probe",
             "remove-revert-committed", "shared_apply_status_observe_service"):
    require(must in restore_section, "rollback does not use native common runtime: " + must)
for forbidden in ("shared_apply_native_config save ", "start_service",
                  "orchestrator_build_release", "hostlist-exclude", "--ipset-exclude"):
    require(forbidden not in restore_section, "rollback must not duplicate compiler or Config writer: " + forbidden)
require("def restore_previous_native_common_apply" in worker and
        "extra-resources-native-restore-previous" in worker and
        "extra-resources-native-restore-previous)" in service,
        "exact previous owner is not wired to existing FD9 service")
trial_gate = section(service, "extra_resources_native_trial_service()",
                     "# Internal root-only Apply phases; service_with_lifecycle_lock supplies FD9.")
for must in ("remove-trial-context", "extra_resources_native_build_saved_service",
             "shared_apply_native_config preflight", "apply_runtime_probe",
             "shared_apply_record_service prepared",
             "shared_apply_record_service activating",
             "apply_runtime_activate", "apply_runtime_attest_activated",
             "shared_apply_native_config saved",
             "shared_apply_record_service config-saved",
             "apply_runtime_commit", "shared_apply_record_service committed",
             "shared_apply_status_observe_service"):
    require(must in trial_gate, "native trial omits common Apply part: " + must)
for forbidden in ("shared_apply_native_config save ", "start_service",
                  "orchestrator_build_release ", "hostlist-exclude",
                  "--ipset-exclude", "strategy-lab-start"):
    require(forbidden not in trial_gate,
            "native trial duplicated compiler, Config writer or legacy Start: " + forbidden)
require('extra-resources-native-trial)' in service and
        'extra_resources_block_pending_start_service || return 69' in service and
        "def start_trial_native_common_apply" in worker,
        "trial is not bound to existing inherited FD9 or ordinary startup gate")
for cmd in (["php", "-l", str(SRC / "shared_apply_request.php")],
            ["sh", "-n", str(SRC / "zapret_service.sh")],
            ["php", str(ROOT / "scripts/test-shared-apply-request.php")]):
    p = subprocess.run(cmd, text=True, capture_output=True)
    require(p.returncode == 0, cmd[0] + " native syntax/candidate: " + p.stderr + p.stdout)
print("PASS: saved unchanged Strategies+Voice candidate reuses original GUI builder and inherited FD9")
