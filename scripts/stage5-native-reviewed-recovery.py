#!/usr/bin/env python3
"""Disposable OPNsense only: operator-reviewed native recovery after torn pkg.

Does NOT ship in the plugin, run at boot, repair pkgdb directly, own FD9,
write Config or execute untrusted installed service. The existing protected
original-FD9 transaction is the ONLY owner of final lifecycle restoration.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
NAME = "os-zapret2-restyle"
ORIGINAL = ROOT / "src/opnsense/scripts/OPNsense/Zapret/protected_pkg_update.py"
FIXTURE = ROOT / "scripts/stage5-native-hard-reset.py"
RECOVERY_APPROVAL = "disposable-guest-reviewed-reinstall"
FINISH_APPROVAL = "disposable-guest-reviewed-finish"


def need(value, reason):
    if not value:
        raise RuntimeError(reason)


def load_file(name, source):
    need(source.is_file() and not source.is_symlink(), "TRUSTED_SOURCE_UNAVAILABLE")
    spec = importlib.util.spec_from_file_location(name, source)
    need(spec is not None and spec.loader is not None, "TRUSTED_SOURCE_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cmd(argv, timeout=30):
    return subprocess.run(argv, capture_output=True, text=True,
                          check=False, timeout=timeout)


def isolation(command):
    need(sys.platform.startswith("freebsd") and os.geteuid() == 0 and
         os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_NATIVE_HARDRESET_TEST") == "1" and
         os.environ.get("ZAPRET2_NATIVE_REVIEWED_RECOVERY_TEST") ==
            (RECOVERY_APPROVAL if command == "reinstall" else FINISH_APPROVAL),
         "NOT_EXPLICITLY_REVIEWED_DISPOSABLE_FREEBSD")


# Keep the pre-existing error vocabulary exactly unchanged; only split its
# read-only per-probe diagnosis into finite categories without leaking stderr.
PKGDB_ERROR_SIGNATURES = (
    ("locked", "database is locked"),
    ("malformed", "malformed"),
    ("corrupt", "corrupt"),
    ("sql_error", "sql error"),
    ("io_error", "io error"),
)


def pkgdb_error_categories(stderr):
    low = stderr.lower()
    return [label for label, pattern in PKGDB_ERROR_SIGNATURES
            if pattern in low]


def absent_pkgdb():
    query = cmd(["/usr/sbin/pkg", "query", "%v", NAME])
    info = cmd(["/usr/sbin/pkg", "info", "-e", NAME])
    query_db_errors = pkgdb_error_categories(query.stderr)
    info_db_errors = pkgdb_error_categories(info.stderr)
    bad_db = bool(query_db_errors or info_db_errors)
    # Diagnostic only: never print stderr/stdout or silently override a
    # disagreement between the two independent native pkg observations.
    print("NATIVE_REVIEWED_RECOVERY_PKGDB_READONLY=" + json.dumps({
        "query_rc": query.returncode, "info_exists_rc": info.returncode,
        "query_stdout_nonempty": bool(query.stdout.strip()),
        "info_stdout_nonempty": bool(info.stdout.strip()),
        "possible_db_error": bad_db,
        "query_db_error_categories": query_db_errors,
        "info_db_error_categories": info_db_errors,
        "no_write": True,
    }, sort_keys=True), flush=True)
    need(query.returncode == 1 and not query.stdout.strip() and
         info.returncode == 1 and not info.stdout.strip() and not bad_db,
         "PKGDB_NOT_UNAMBIGUOUSLY_ABSENT")
    return True


def original_journal(fixture, protected, receipt, phase):
    need(protected.BASE.exists() and not protected.BASE.is_symlink(),
         "PROTECTED_BASE_MISSING")
    protected.root_and_private_base()
    data = protected.read_active()  # strict root/0600/schema/phase
    need(data.get("phase") == phase and
         data.get("sha256") == receipt["archive_sha256"] and
         data.get("to_version") == receipt["version"] and
         data.get("was_running") is True,
         "PROTECTED_RECORD_NOT_EXACT_OR_WRONG_PHASE")
    stage = protected.validated_stage(data["stage"], data["sha256"],
                                       data["to_version"])
    need(stage.parent == protected.BASE, "STAGE_NOT_ORIGINAL_PRIVATE_ARCHIVE")
    return data, stage


def read_only_baseline(fixture, *, prepared):
    fixture.guest_gate()  # exact disposable OPNsense 26.7 / FreeBSD 15 / root
    receipt = fixture.read_receipt()
    need(fixture.guest_boot() > receipt["boot_seconds"],
         "NO_PROVEN_HARD_RESET")
    state = fixture.postboot_readonly_classification(receipt) if prepared else {}
    if prepared:
        need(state["prepared_guard_present_unchanged"] and
             state["old_auto_retired"] and state["process_table_available"] and
             state["dvtws2_absent"] and
             state["guard_private_staged_package_unchanged"] and
             state["zapret_section_present"] and
             state["interfaces_section_present"],
             "POSTBOOT_NOT_FAIL_CLOSED")
    else:
        state["installed_service_source_trusted"] = fixture.trusted_service()
    snapshot = fixture.config_snapshot()
    need(snapshot["plugin"] == receipt["config_snapshot"]["plugin"] and
         snapshot["interfaces"] == receipt["config_snapshot"]["interfaces"],
         "SAVED_CONFIG_NOT_PRESERVED")
    need((fixture.EPOCHS / receipt["original_epoch_id"] / "retired.json").is_file(),
         "OLD_AUTO_NOT_RETIRED")
    return receipt, state, snapshot


def assert_no_engine(fixture):
    ps = cmd(["/bin/ps", "-axo", "comm="])
    need(ps.returncode == 0 and
         not any(line.strip() == "dvtws2" for line in ps.stdout.splitlines()),
         "ENGINE_RUNNING_IN_REVIEW_STATE")



def interrupt_for_reset(native, archive, target, expected_digest):
    """Real native partial extraction, followed by NO installed code execution.

    This is a disposable guest fixture only. It reuses native original FD9
    prepare and the independently qualified physical mid-extract SIGKILL,
    but DOES NOT probe a possibly torn installed service afterwards.
    """
    witness = native.original_fixture("stage5-native-pkg-midextract.py",
                                      "reviewed_physical_pkg_extract")
    installed_source = native.SERVICE.parent / "protected_pkg_update.py"
    product = load_file("reviewed_original_pre_extract", installed_source)
    prior = json.loads(native.JOURNAL.read_text())
    old_id = prior.get("detail", {}).get("id", "")
    need(prior.get("phase") == "committed" and
         (native.EPOCHS / old_id / "epoch.json").is_file() and
         native.run([str(native.SERVICE), "status"]).returncode == 0,
         "MIDEXTRACT_REQUIRES_REAL_RUNNING_AUTO")
    before_config = native.sha(native.CONFIG)
    stage, stage_digest, stage_version = product.stage_archive(archive)
    need(stage_digest == expected_digest and stage_version == target,
         "NATIVE_PRIVATE_STAGE_IDENTITY_DRIFT")
    prepared = native.run([str(native.SERVICE), "pkg-update-prepare",
                           str(stage), stage_digest, stage_version], timeout=150)
    need(prepared.returncode == 0 and
         "zapret-pkg-update-prepared=1" in prepared.stdout and
         native.ACTIVE.is_file() and native.MARKER.is_file() and
         (native.EPOCHS / old_id / "retired.json").is_file() and
         native.run([str(native.SERVICE), "status"]).returncode == 1,
         "ORIGINAL_FD9_PREPARE_NOT_STOPPED")
    record_digest = native.sha(native.ACTIVE)
    need(json.loads(native.ACTIVE.read_text()).get("phase") == "prepared",
         "ORIGINAL_PREPARED_RECORD_MISSING")
    paths = witness.select_native_witnesses(native.ROOT, stage,
                                            native.run, native.need)
    restored, marked, missing, foreign = witness.interrupt_real_native_pkg_midextract(
        stage, paths, native.need)
    need(restored > 0 and marked + missing > 0 and foreign == 0 and
         native.ACTIVE.is_file() and native.sha(native.ACTIVE) == record_digest and
         native.MARKER.is_file() and native.sha(native.CONFIG) == before_config and
         (native.EPOCHS / old_id / "retired.json").is_file() and
         native.sha(stage) == expected_digest,
         "PHYSICAL_EXTRACTION_OR_GUARD_PROOF_MISSING")
    ps = native.run(["/bin/ps", "-axo", "comm="], timeout=20)
    need(ps.returncode == 0 and not any(
         line.strip() == "dvtws2" for line in ps.stdout.splitlines()),
         "ENGINE_NOT_PHYSICALLY_STOPPED_AFTER_INTERRUPT")
    print("NATIVE_REVIEWED_MIDEXTRACT=" + json.dumps({
        "genuine_pkg_killed": True,
        "restored": restored, "unrestored": marked + missing,
        "foreign": foreign, "original_fd9_prepared": True,
        "old_auto_retired": True, "config_unchanged": True,
        "dvtws2_absent": True, "postkill_installed_code_executed": False,
        "owner_appliance_modified": False,
    }, sort_keys=True), flush=True)
    print("NATIVE_REVIEWED_MIDEXTRACT=PASS_GENUINE_PARTIAL_PAYLOAD_NO_UNTRUSTED_EXECUTION",
          flush=True)


def reinstall():
    isolation("reinstall")
    fixture = load_file("review_recovery_fixture", FIXTURE)
    protected = load_file("review_original_source", ORIGINAL)
    receipt, state, config_before = read_only_baseline(fixture, prepared=True)
    assert_no_engine(fixture)
    # Existing service may be missing/untrusted or exact source trusted.
    # Never execute it here; pkgdb must independently report ABSENT.
    absent_pkgdb()  # intentionally restrict scope; never run old untrusted hooks
    before, stage = original_journal(fixture, protected, receipt, "prepared")
    need(fixture.digest(fixture.GUARD) == receipt["guard_sha256"],
         "PENDING_RECORD_CHANGED")
    print("NATIVE_REVIEWED_RECOVERY_REINSTALL_PRECHECK=" + json.dumps({
        "explicit_disposable_review": True,
        "phase": "prepared", "pkgdb_absent": True,
        "installed_service_source_trusted_before":
            state["installed_service_source_trusted"],
        "original_auto_retired": True,
        "saved_settings_preserved": True, "protected_archive_validated": True,
        "dvtws2_absent": True, "manual_reinstall_only": True,
    }, sort_keys=True), flush=True)
    # Only this ONE call may modify installed package files and pkgdb; its
    # native hooks own any reentry into the original FD9. No service call here.
    pkg = cmd(["/usr/sbin/pkg", "-o", "REPO_AUTOUPDATE=false",
               "add", "-f", str(stage)], timeout=300)
    combined = pkg.stdout + "\n" + pkg.stderr
    need(pkg.returncode == 0 and
         not any(marker in combined for marker in protected.FAILURE_MARKERS) and
         "zapret-pkg-postinstall-guarded=1" in combined,
         "NATIVE_REINSTALL_HOOK_OR_PKG_FAILED")
    _, stage_after = original_journal(fixture, protected, receipt,
                                       "postinstall-attested")
    need(stage_after == stage and fixture.trusted_service() and
         fixture.digest(protected.SCRIPT_DIR / "zapret_service.sh") ==
            fixture.digest(fixture.SERVICE),
         "REINSTALLED_SERVICE_NOT_SOURCE_TRUSTED")
    installed = protected.installed_version()
    need(installed == receipt["version"], "REINSTALLED_PKGDB_NOT_CANDIDATE")
    assert_no_engine(fixture)
    after = fixture.config_snapshot()
    need(after["plugin"] == config_before["plugin"] and
         after["interfaces"] == config_before["interfaces"],
         "SETTINGS_CHANGED_DURING_REINSTALL")
    print("NATIVE_REVIEWED_RECOVERY_REINSTALL=PASS_NATIVE_POSTINSTALL_ATTESTED_STOPPED",
          flush=True)


def finish():
    isolation("finish")
    fixture = load_file("review_recovery_fixture", FIXTURE)
    protected = load_file("review_original_source", ORIGINAL)
    receipt, state, before_config = read_only_baseline(fixture, prepared=False)
    assert_no_engine(fixture)
    need(fixture.trusted_service(), "CANNOT_EXECUTE_UNTRUSTED_SERVICE")
    original_journal(fixture, protected, receipt, "postinstall-attested")
    need(protected.installed_version() == receipt["version"],
         "CANDIDATE_NOT_INSTALLED")
    # No separate updater, writer or secondary FD9. Explicit reviewed
    # lifecycle authority is delegated to the already verified successor.
    outcome = cmd([str(fixture.SERVICE), "pkg-update-finish",
                   receipt["archive_sha256"], receipt["version"]], timeout=210)
    need(outcome.returncode == 0 and
         "zapret-pkg-update-committed=1" in outcome.stdout,
         "ORIGINAL_FD9_FINISH_REFUSED")
    need(not fixture.GUARD.exists() and not fixture.GUARD.is_symlink(),
         "ORIGINAL_PENDING_RECORD_NOT_COMPLETED")
    status = cmd([str(fixture.SERVICE), "status"], timeout=35)
    need(status.returncode == 0, "RESTORED_SERVICE_NOT_RUNNING")
    after = fixture.config_snapshot()
    need(after["plugin"] == before_config["plugin"] and
         after["interfaces"] == before_config["interfaces"],
         "RESTORED_CONFIG_CHANGED")
    journal = json.loads(fixture.JOURNAL.read_text())
    epoch = journal.get("detail", {}).get("id")
    need(journal.get("phase") == "committed" and
         isinstance(epoch, str) and re.fullmatch("[a-f0-9]{32}", epoch) and
         epoch != receipt["original_epoch_id"] and
         (fixture.EPOCHS / epoch / "epoch.json").is_file(),
         "NEW_AUTO_EPOCH_NOT_VERIFIED")
    print("NATIVE_REVIEWED_RECOVERY_FINISH=PASS_ORIGINAL_FD9_NEW_RUNNING_EPOCH",
          flush=True)


def main():
    need(len(sys.argv) == 2, "EXPECTED_REINSTALL_OR_FINISH")
    if sys.argv[1] == "reinstall":
        reinstall()
    elif sys.argv[1] == "finish":
        finish()
    else:
        raise RuntimeError("UNSUPPORTED_REVIEWED_RECOVERY_ACTION")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError,
            subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        # Fail closed. No untrusted pkg output, config content or hostlists.
        reason = str(exc) if isinstance(exc, RuntimeError) else "REVIEWED_RECOVERY_UNAVAILABLE"
        print("NATIVE_REVIEWED_RECOVERY_REFUSED=" + reason, file=sys.stderr)
        sys.exit(1)
