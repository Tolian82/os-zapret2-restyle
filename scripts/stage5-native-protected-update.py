#!/usr/bin/env python3
"""One disposable OPNsense: real native .pkg STOPPED protected reinstall.

Only genuine pkg/Mk hooks, installed source and installed native FD9 service;
no engine setup, no owner router, no synthetic service process.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
NAME = "os-zapret2-restyle"
SERVICE = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
ACTIVE = Path("/var/db/zapret2/pkg-update/operation.json")
MARKER = Path("/var/run/zapret2-restyle/pkg-replacement.restart")
JOURNAL = Path("/var/db/zapret2/shared-apply/operation.json")
EPOCHS = Path("/var/db/zapret2/auto-detect-epochs")
CONFIG = Path("/conf/config.xml")


def need(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def run(argv, timeout=120):
    return subprocess.run(argv, capture_output=True, text=True,
                          timeout=timeout, check=False)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def installed_version():
    p = run(["pkg", "query", "%v", NAME])
    need(p.returncode == 0, "PKGDB_MISSING")
    return p.stdout.strip()


def original_fixture(filename, module_name):
    spec = importlib.util.spec_from_file_location(module_name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def seed_qualified_stable_tag_for_disposable_guest(g03):
    """Reuse the already native-verified _85 public stable-release cache tactic.

    This is test-only setup metadata, never a runtime fallback. The installed
    setup worker still clones, verifies the exact upstream Git tag and compiles.
    """
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_PROTECTED_PKG_NATIVE_TEST") == "1" and
         os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         g03.RELEASE == "v1.0.7",
         "NATIVE_STABLE_RELEASE_CACHE_NOT_QUALIFIED")
    base = Path("/var/db/zapret2-restyle")
    base.mkdir(mode=0o755, parents=True, exist_ok=True)
    parent = base.lstat()
    need(stat.S_ISDIR(parent.st_mode) and not base.is_symlink() and
         parent.st_uid == 0 and not (parent.st_mode & 0o022),
         "NATIVE_STABLE_RELEASE_CACHE_PARENT_UNTRUSTED")
    cache = base / "releases.cache"
    need(not cache.exists() and not cache.is_symlink(),
         "NATIVE_STABLE_RELEASE_CACHE_PREEXISTS")
    fd = os.open(cache, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                 0o644)
    with os.fdopen(fd, "wb") as writer:
        writer.write(g03.RELEASE.encode("ascii") + b"\n")
        writer.flush()
        os.fsync(writer.fileno())
    meta = cache.lstat()
    need(stat.S_ISREG(meta.st_mode) and meta.st_uid == 0 and
         meta.st_mode & 0o777 == 0o644 and
         cache.read_bytes() == b"v1.0.7\n",
         "NATIVE_STABLE_RELEASE_CACHE_MISMATCH")
    print("NATIVE_PROTECTED_TEST_ONLY_STABLE_CACHE=VERIFIED_PUBLIC_v1.0.7",
          flush=True)


def native_running_reinstall(archive, target, candidate_sha):
    """Both LIST and AUTO on one genuinely installed native OPNsense guest.

    LIST has no obligation to create a P2 auto-detect epoch. Only AUTO
    requires the observer epoch/retirement receipts.
    """
    witness = original_fixture("p5b2b-native-witness.py", "protected_native_witness")
    old_bridge = original_fixture("test-own70-native-package-handoff.py",
                                  "protected_native_saved_strategies")
    g03 = original_fixture("stage2-opnsense-g03-first-install.py",
                           "protected_native_upstream_setup")
    witness.set_guest_lo0()
    # The Model defaults HOSTLIST mode to "all". Explicitly select real
    # manual List through the established native OPNsense Config Model.
    old_bridge.set_guest_list_mode()
    seed_qualified_stable_tag_for_disposable_guest(g03)
    try:
        setup = g03.dispatch_and_poll()
    except (g03.Refusal, OSError, subprocess.TimeoutExpired):
        # Log only the G03 helper's existing bounded/redacted state summary.
        g03.bounded_disposable_failure_evidence()
        raise
    need(setup["installed"] == "1" and setup["service"] == "stopped",
         "UPSTREAM_RUNTIME_NOT_READY_STOPPED")
    initial = run(["/usr/local/sbin/configctl", "zapret", "shared_apply",
                   "strategies", old_bridge.request("list")], timeout=240)
    initial_state = json.loads(JOURNAL.read_text())
    need(initial.returncode == 0 and "applied-id=" in initial.stdout and
         initial_state.get("phase") == "committed" and
         run([str(SERVICE), "status"]).returncode == 0,
         "REAL_LIST_SHARED_APPLY_NOT_COMMITTED")

    def check_running_replacement(label, observer_required):
        old = json.loads(JOURNAL.read_text())
        old_id = old["detail"]["id"]
        old_pid_path = Path("/var/run/dvtws2.pid")
        old_pid = old_pid_path.read_text().strip().split()[0]
        need(old.get("phase") == "committed" and old_pid.isdecimal() and
             run([str(SERVICE), "status"]).returncode == 0,
             "REAL_PREDECESSOR_NOT_RUNNING_" + label)
        old_epoch_present = (EPOCHS / old_id / "epoch.json").is_file()
        if observer_required:
            need(old_epoch_present, "AUTO_PREDECESSOR_EPOCH_MISSING")
        else:
            need(not old_epoch_present, "LIST_UNEXPECTED_OBSERVER_EPOCH")
        config_before = sha(CONFIG)
        replaced = run([str(SERVICE), "pkg-update", str(archive)], timeout=320)
        status_after = run([str(SERVICE), "status"], timeout=30)
        successor = json.loads(JOURNAL.read_text())
        new_id = successor.get("detail", {}).get("id", "")
        new_pid = (old_pid_path.read_text().strip().split()[0]
                   if old_pid_path.is_file() and not old_pid_path.is_symlink()
                   else "missing")
        why = re.search(r"(?m)^pkg-update-refused=([A-Z0-9_]+)$",
                        replaced.stderr)
        evidence = {
            "schema": 1, "scope": label, "observer_required": observer_required,
            "predecessor_epoch_exists": old_epoch_present,
            "protected_running_replacement_rc": replaced.returncode,
            "refusal": why.group(1) if why else "none",
            "verified_receipt":
                "pkg-update=verified-installed-and-restored" in replaced.stdout,
            "after_status_rc": status_after.returncode,
            "old_epoch_retired":
                (EPOCHS / old_id / "retired.json").is_file(),
            "journal_committed": successor.get("phase") == "committed",
            "generation_changed": new_id != old_id,
            # Ordinary common boot reuses the committed ID. Only a stopped
            # observer is retired and rebuilt under a NEW operation ID.
            "generation_semantics_verified":
                successor.get("phase") == "committed" and
                (new_id != old_id if observer_required else new_id == old_id),
            "successor_epoch_exists":
                (EPOCHS / new_id / "epoch.json").is_file(),
            "new_engine_pid_distinct":
                new_pid.isdecimal() and new_pid != old_pid,
            "config_unchanged": sha(CONFIG) == config_before,
            "pkgdb_current_version": installed_version() == target,
            "same_pkg_sha256": sha(archive) == candidate_sha,
            "no_guard_record":
                not ACTIVE.exists() and not ACTIVE.is_symlink(),
            "no_restart_marker": not MARKER.exists(),
            "owner_appliance_modified": False,
        }
        print("NATIVE_PROTECTED_RUNNING=" + json.dumps(evidence, sort_keys=True),
              flush=True)
        checks = (
            evidence["protected_running_replacement_rc"] == 0 and
            evidence["verified_receipt"] and evidence["after_status_rc"] == 0 and
            evidence["generation_semantics_verified"] and
            evidence["new_engine_pid_distinct"] and evidence["config_unchanged"] and
            evidence["pkgdb_current_version"] and
            evidence["same_pkg_sha256"] and evidence["no_guard_record"] and
            evidence["no_restart_marker"])
        if observer_required:
            checks = (checks and evidence["old_epoch_retired"] and
                      evidence["successor_epoch_exists"])
        else:
            # LIST has no observer and therefore cannot fabricate an epoch.
            checks = checks and not evidence["successor_epoch_exists"]
        need(checks, "PROTECTED_NATIVE_" + label + "_REINSTALL_NOT_CONFIRMED")
        print("NATIVE_PROTECTED_" + label + "=PASS_COMMON_STOP_PKG_BOOT",
              flush=True)

    check_running_replacement("LIST", observer_required=False)

    # Native user action explicitly turns on AUTO. Unlike LIST, AUTO must
    # produce a committed P2 observer epoch before pkg replacement.
    auto_apply = run(["/usr/local/sbin/configctl", "zapret", "shared_apply",
                      "strategies", old_bridge.request("auto")], timeout=240)
    auto_state = json.loads(JOURNAL.read_text())
    auto_id = auto_state.get("detail", {}).get("id", "")
    auto_epoch = (EPOCHS / auto_id / "epoch.json").is_file()
    print("NATIVE_PROTECTED_AUTO_PREFLIGHT=" + json.dumps({
        "configctl_rc": auto_apply.returncode,
        "native_applied_receipt": "applied-id=" in auto_apply.stdout,
        "journal_committed": auto_state.get("phase") == "committed",
        "native_service_running": run([str(SERVICE), "status"]).returncode == 0,
        "observer_epoch_present": auto_epoch,
    }, sort_keys=True), flush=True)
    need(auto_apply.returncode == 0 and
         "applied-id=" in auto_apply.stdout and
         auto_state.get("phase") == "committed" and auto_epoch and
         run([str(SERVICE), "status"]).returncode == 0,
         "NATIVE_AUTO_SHARED_APPLY_NOT_COMMITTED")
    check_running_replacement("AUTO", observer_required=True)


def interrupted_prepare_diagnostic(prepare, old_id, config_before):
    """Bounded, source-free test evidence; never alter the failed owner."""
    stderr = prepare.stderr
    if "another zapret lifecycle operation is already running" in stderr:
        reason = "lifecycle-lock-busy"
    elif "prior pkg restart marker needs review" in stderr:
        reason = "existing-pkg-marker"
    elif "protected package update refuses incomplete owner" in stderr:
        reason = "incomplete-current-owner"
    elif "original runtime did not reach verified STOPPED" in stderr:
        reason = "stop-proof-unavailable"
    elif "FD9" in stderr:
        reason = "fd9-ownership-refused"
    elif "ERROR:" in stderr or "REFUSED:" in stderr:
        reason = "other-safe-refusal"
    else:
        reason = "missing-or-unclassified-diagnostic"
    try:
        state = json.loads(ACTIVE.read_text()) if ACTIVE.is_file() else None
        phase = state.get("phase") if isinstance(state, dict) else None
    except (OSError, ValueError):
        phase = "unreadable"
    status = run([str(SERVICE), "status"], timeout=45).returncode
    return {
        "phase": phase if phase in ("prepared", "postinstall-attested", "unreadable") else "absent-or-invalid",
        "prepare_rc": prepare.returncode,
        "prepare_receipt": "zapret-pkg-update-prepared=1" in prepare.stdout,
        "stderr_category": reason,
        "active_record_exists": ACTIVE.is_file() and not ACTIVE.is_symlink(),
        "restart_marker_exists": MARKER.is_file(),
        "status_rc": status,
        "retired_epoch_exists": (EPOCHS / old_id / "retired.json").is_file(),
        "old_config_unchanged": CONFIG.is_file() and sha(CONFIG) == config_before,
        "owner_appliance_modified": False,
    }


def native_interrupted_handoff(archive, version, digest):
    """A real *inter-process* incomplete handoff, never owner recovery.

    Stop and record under FD9 using the installed service. Return to the
    caller with NO FD9 owner while native pkg runs. Stop the test process
    between installed pkg and protected finish; verify fail-closed guards
    after the installed successor reload, then explicitly finish under
    successor FD9 on this disposable OPNsense only. This does not model
    arbitrary power loss or corrupt package files.
    """
    module_path = SERVICE.parent / "protected_pkg_update.py"
    spec = importlib.util.spec_from_file_location("installed_protected_pkg_update", module_path)
    product = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(product)
    before = json.loads(JOURNAL.read_text())
    old_id = before["detail"]["id"]
    need(before.get("phase") == "committed" and
         (EPOCHS / old_id / "epoch.json").is_file() and
         run([str(SERVICE), "status"]).returncode == 0,
         "INTERRUPT_PREDECESSOR_AUTO_NOT_RUNNING")
    before_config = sha(CONFIG)
    old_pid = Path("/var/run/dvtws2.pid").read_text().strip().split()[0]
    need(old_pid.isdecimal(), "INTERRUPT_PREDECESSOR_PID_INVALID")
    stage, staged_sha, stage_version = product.stage_archive(archive)
    need(staged_sha == digest and stage_version == version and
         stage.parent == ACTIVE.parent, "INTERRUPT_STAGED_ARCHIVE_DRIFT")

    prepare = run([str(SERVICE), "pkg-update-prepare",
                   str(stage), staged_sha, stage_version], timeout=90)
    # Preserve the precise cause of a failed prepare before the VM exits.
    # This reads only guard/epoch/Config state and never retries or cleans up.
    prepared_ok = (prepare.returncode == 0 and
                   "zapret-pkg-update-prepared=1" in prepare.stdout and
                   ACTIVE.is_file() and not ACTIVE.is_symlink() and
                   MARKER.is_file() and
                   run([str(SERVICE), "status"]).returncode == 1)
    if not prepared_ok:
        print("NATIVE_PROTECTED_PREPARE_DIAGNOSTIC=" + json.dumps(
            interrupted_prepare_diagnostic(prepare, old_id, before_config),
            sort_keys=True), flush=True)
    need(prepared_ok, "INTERRUPT_PRE_PKG_PREPARE_FAILED")
    record_before = sha(ACTIVE)
    pkg_before = installed_version()
    # Crucial SAME-VERSION ambiguity: the preceding installed version is
    # already equal to the candidate, yet native pkg has NOT run. Finishing
    # now must be refused even with a valid prepared record and stopped FD9.
    premature = run([str(SERVICE), "pkg-update-finish",
                     staged_sha, stage_version], timeout=50)
    need(premature.returncode == 69 and
         json.loads(ACTIVE.read_text()).get("phase") == "prepared" and
         sha(ACTIVE) == record_before and
         run([str(SERVICE), "status"]).returncode == 1,
         "PREMATURE_FINISH_FALSELY_RESTORED_BEFORE_NATIVE_PKG")
    print("NATIVE_PROTECTED_PREMATURE_FINISH=PASS_REFUSED", flush=True)
    attempted_start = run([str(SERVICE), "start"], timeout=40)
    attempted_apply = run([str(SERVICE), "shared-apply-run"], timeout=40)
    attempted_again = run([str(SERVICE), "pkg-update", str(archive)], timeout=40)
    need(all(x.returncode == 69 for x in (
             attempted_start, attempted_apply, attempted_again)) and
         installed_version() == pkg_before and
         sha(CONFIG) == before_config and sha(ACTIVE) == record_before and
         run([str(SERVICE), "status"]).returncode == 1,
         "INTERRUPT_PRE_PKG_DID_NOT_FAIL_CLOSED")
    print("NATIVE_PROTECTED_INTERRUPTED_BEFORE_PKG=PASS_RECORD_GUARD_FD9",
          flush=True)

    # Run the genuine same-byte OPNsense package; deliberately OMIT finish.
    # No external process is permitted to silently complete restoration.
    replace = run(["/usr/sbin/pkg", "-o", "REPO_AUTOUPDATE=false",
                   "add", "-f", str(stage)], timeout=240)
    combined = replace.stdout + "\n" + replace.stderr
    need(replace.returncode == 0 and
         "zapret-pkg-postinstall-guarded=1" in combined and
         "script failed" not in combined and
         installed_version() == version and sha(CONFIG) == before_config,
         "INTERRUPT_REAL_NATIVE_PKG_FAILED")
    need(ACTIVE.is_file() and
         json.loads(ACTIVE.read_text()).get("phase") == "postinstall-attested" and
         sha(ACTIVE) != record_before and
         MARKER.is_file() and run([str(SERVICE), "status"]).returncode == 1,
         "INTERRUPT_POST_PKG_ATTESTED_GUARD_LOST")
    start_after = run([str(SERVICE), "start"], timeout=40)
    again_after = run([str(SERVICE), "pkg-update", str(archive)], timeout=40)
    need(start_after.returncode == 69 and again_after.returncode == 69 and
         ACTIVE.is_file() and
         json.loads(ACTIVE.read_text()).get("phase") == "postinstall-attested" and
         run([str(SERVICE), "status"]).returncode == 1,
         "INTERRUPT_POST_PKG_UNAUTHORISED_START_OR_PKG")
    print("NATIVE_PROTECTED_INTERRUPTED_AFTER_PKG=PASS_GUARDED_STOPPED",
          flush=True)

    finish = run([str(SERVICE), "pkg-update-finish", staged_sha, stage_version],
                 timeout=150)
    now = json.loads(JOURNAL.read_text())
    new_id = now.get("detail", {}).get("id", "")
    pid = Path("/var/run/dvtws2.pid").read_text().strip().split()[0]
    result = {
        "schema": 1,
        "exact_native_pkg": replace.returncode == 0,
        "finish_rc": finish.returncode,
        "final_receipt": "zapret-pkg-update-committed=1" in finish.stdout,
        "original_epoch_retired": (EPOCHS / old_id / "retired.json").is_file(),
        "successor_epoch_committed":
            now.get("phase") == "committed" and new_id != old_id and
            (EPOCHS / new_id / "epoch.json").is_file(),
        "different_running_pid": pid.isdecimal() and pid != old_pid,
        "native_running_rc": run([str(SERVICE), "status"]).returncode,
        "config_unchanged": before_config == sha(CONFIG),
        "package_identity_verified": installed_version() == version,
        "record_removed": not ACTIVE.exists() and not ACTIVE.is_symlink(),
        "marker_removed": not MARKER.exists(),
        "candidate_sha256_verified": sha(stage) == digest,
        "owner_appliance_modified": False,
    }
    print("NATIVE_PROTECTED_INTERRUPT_HANDOFF=" +
          json.dumps(result, sort_keys=True), flush=True)
    need(result["finish_rc"] == 0 and result["final_receipt"] and
         result["original_epoch_retired"] and
         result["successor_epoch_committed"] and
         result["different_running_pid"] and result["native_running_rc"] == 0 and
         result["config_unchanged"] and result["package_identity_verified"] and
         result["record_removed"] and result["marker_removed"] and
         result["candidate_sha256_verified"],
         "INTERRUPT_NATIVE_RECOVERY_NOT_VERIFIED")
    stage.unlink()
    print("NATIVE_PROTECTED_INTERRUPT_HANDOFF=PASS_REAL_NATIVE_PKG",
          flush=True)



def native_interrupt_during_postinstall(archive, version, digest):
    """Kill real pkg *inside* its POST_INSTALL on a disposable guest.

    The test-only register helper is reached after native pkg extraction;
    this proves an in-pkg hook interruption, NOT mid-extraction/power loss.
    Leave the guard intact, do not automatically finish/restart or repair.
    """
    module_path = SERVICE.parent / "protected_pkg_update.py"
    spec = importlib.util.spec_from_file_location("installed_abort_pkg_update", module_path)
    product = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(product)
    previous = json.loads(JOURNAL.read_text())
    old_id = previous["detail"]["id"]
    need(previous.get("phase") == "committed" and
         (EPOCHS / old_id / "epoch.json").is_file() and
         run([str(SERVICE), "status"]).returncode == 0,
         "ABORT_PREDECESSOR_NOT_VERIFIED_RUNNING_AUTO")
    previous_config = sha(CONFIG)
    stage, stage_sha, stage_version = product.stage_archive(archive)
    need(stage_sha == digest and stage_version == version,
         "ABORT_STAGED_CANDIDATE_MISMATCH")
    prepared = run([str(SERVICE), "pkg-update-prepare",
                    str(stage), stage_sha, stage_version], timeout=150)
    need(prepared.returncode == 0 and
         "zapret-pkg-update-prepared=1" in prepared.stdout and
         (EPOCHS / old_id / "retired.json").is_file() and
         run([str(SERVICE), "status"]).returncode == 1 and
         MARKER.is_file() and ACTIVE.is_file(),
         "ABORT_REAL_PREPARE_NOT_COMMITTED_STOPPED")
    before_record = sha(ACTIVE)
    need(json.loads(ACTIVE.read_text()).get("phase") == "prepared",
         "ABORT_RECORD_NOT_PREPARED")

    # The helper exists ONLY inside this disposable VM. The installed package
    # hook stays unchanged; it executes through its existing native variable.
    with tempfile.TemporaryDirectory(prefix="native-pkg-abort-", dir="/root") as temp:
        root = Path(temp)
        entered = root / "postinstall-entered"
        helper = root / "register-block.sh"
        helper.write_text(
            "#!/bin/sh\n"
            "[ \"${1:-}\" = install ] || exit 71\n"
            f"printf 'entered\\n' > '{entered}'\n"
            "while :; do /bin/sleep 1; done\n"
        )
        helper.chmod(0o700)
        env = dict(os.environ)
        env["FIRMWARE_REGISTER"] = str(helper)
        process = subprocess.Popen(
            ["/usr/sbin/pkg", "-o", "REPO_AUTOUPDATE=false",
             "add", "-f", str(stage)],
            env=env, start_new_session=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True,
        )
        try:
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                if entered.is_file():
                    break
                need(process.poll() is None, "ABORT_PKG_EXITED_BEFORE_TEST_HOOK")
                time.sleep(0.1)
            need(entered.is_file() and entered.read_text() == "entered\n" and
                 process.poll() is None, "ABORT_PKG_HOOK_NOT_OBSERVED")
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate(timeout=15)
            need(process.returncode == -signal.SIGKILL,
                 "ABORT_PKG_NOT_ACTUALLY_KILLED")
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate(timeout=15)

    need(ACTIVE.is_file() and sha(ACTIVE) == before_record and
         json.loads(ACTIVE.read_text()).get("phase") == "prepared" and
         MARKER.is_file() and sha(CONFIG) == previous_config and
         run([str(SERVICE), "status"]).returncode == 1,
         "ABORT_MID_PKG_GUARD_OR_CONFIG_LOST")
    denied = {
        "start": run([str(SERVICE), "start"], timeout=45).returncode,
        "apply": run([str(SERVICE), "shared-apply-run"], timeout=45).returncode,
        "repeat_pkg": run([str(SERVICE), "pkg-update", str(archive)], timeout=45).returncode,
        "premature_finish": run([str(SERVICE), "pkg-update-finish",
                                stage_sha, stage_version], timeout=45).returncode,
    }
    need(all(rc == 69 for rc in denied.values()) and
         run([str(SERVICE), "status"]).returncode == 1 and
         sha(ACTIVE) == before_record and
         (EPOCHS / old_id / "retired.json").is_file() and
         sha(CONFIG) == previous_config,
         "ABORT_UNAUTHORISED_START_OR_FINISH")
    print("NATIVE_PROTECTED_KILLED_IN_POSTINSTALL=" + json.dumps({
        "scope": "actual pkg process killed in native POST_INSTALL before attestation",
        "pkg_signal": "SIGKILL",
        "hook_entered": True,
        "operation_phase": "prepared",
        "previous_epoch_retired": True,
        "guarded_service_stopped": True,
        "config_unchanged": True,
        "all_mutating_actions_refused": True,
        "mid_extraction_or_power_loss_tested": False,
        "owner_appliance_modified": False,
    }, sort_keys=True), flush=True)
    print("NATIVE_PROTECTED_KILLED_IN_POSTINSTALL=PASS_FAIL_CLOSED", flush=True)



def native_partial_payload_interruption(archive, target, digest):
    """Genuine partial file extraction (test guest only), never a restore path."""
    fixture = original_fixture("stage5-native-pkg-midextract.py", "real_pkg_extraction")
    spec = importlib.util.spec_from_file_location(
        "installed_pkg_midextract_protection", SERVICE.parent / "protected_pkg_update.py")
    product = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(product)
    before = json.loads(JOURNAL.read_text())
    old_id = before.get("detail", {}).get("id", "")
    need(before.get("phase") == "committed" and
         (EPOCHS / old_id / "epoch.json").is_file() and
         run([str(SERVICE), "status"]).returncode == 0,
         "MIDEXTRACT_REQUIRES_REAL_RUNNING_AUTO")
    saved_config = sha(CONFIG)
    stage, stage_sha, stage_ver = product.stage_archive(archive)
    need(stage_sha == digest and stage_ver == target,
         "MIDEXTRACT_STAGED_ARCHIVE_DRIFT")
    prepared = run([str(SERVICE), "pkg-update-prepare", str(stage),
                    stage_sha, stage_ver], timeout=150)
    need(prepared.returncode == 0 and
         "zapret-pkg-update-prepared=1" in prepared.stdout and
         ACTIVE.is_file() and MARKER.is_file() and
         (EPOCHS / old_id / "retired.json").is_file() and
         run([str(SERVICE), "status"]).returncode == 1,
         "MIDEXTRACT_PREPARE_DID_NOT_STOP_OWNER")
    record_before = sha(ACTIVE)
    need(json.loads(ACTIVE.read_text()).get("phase") == "prepared",
         "MIDEXTRACT_RECORD_NOT_PREPARED")
    witnesses = fixture.select_native_witnesses(ROOT, stage, run, need)
    restored, still_marked, missing, foreign = fixture.interrupt_real_native_pkg_midextract(
        stage, witnesses, need)
    # The STOP/guard receipts exist independent of pkgdb's possibly torn state.
    need(restored > 0 and still_marked + missing > 0 and foreign == 0 and
         ACTIVE.is_file() and sha(ACTIVE) == record_before and
         MARKER.is_file() and sha(CONFIG) == saved_config and
         (EPOCHS / old_id / "retired.json").is_file() and
         sha(stage) == digest,
         "MIDEXTRACT_GUARD_OR_PRESERVATION_LOST")
    # Before executing an installed command, independently require its source
    # bytes match the qualified package, not untrusted partly extracted code.
    need(SERVICE.is_file() and not SERVICE.is_symlink() and
         sha(SERVICE) == sha(ROOT / "src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"),
         "MIDEXTRACT_INSTALLED_SERVICE_UNTRUSTED")
    status = run([str(SERVICE), "status"], timeout=45)
    denied = {
        "start": run([str(SERVICE), "start"], timeout=45).returncode,
        "apply": run([str(SERVICE), "shared-apply-run"], timeout=45).returncode,
        "repeat": run([str(SERVICE), "pkg-update", str(archive)], timeout=45).returncode,
        "finish": run([str(SERVICE), "pkg-update-finish",
                       stage_sha, stage_ver], timeout=45).returncode,
    }
    need(status.returncode == 1 and all(x == 69 for x in denied.values()) and
         sha(ACTIVE) == record_before and sha(CONFIG) == saved_config,
         "MIDEXTRACT_UNAUTHORIZED_LIFECYCLE_AFTER_KILL")
    print("NATIVE_PROTECTED_MIDEXTRACT=" + json.dumps({
        "schema": 1, "actual_pkg_killed": True,
        "partial_restored_files": restored,
        "partial_unrestored_files": still_marked + missing,
        "partial_missing_files": missing,
        "postinstall_unreached": True,
        "journal_still_prepared": True,
        "original_auto_retired": True,
        "config_unchanged": True,
        "service_guarded_stopped": True,
        "start_apply_pkg_finish_refused": True,
        "guest_disposable": True,
        "reboot_or_powercut_tested": False,
        "owner_appliance_modified": False,
    }, sort_keys=True), flush=True)
    print("NATIVE_PROTECTED_MIDEXTRACT=PASS_FAIL_CLOSED_REAL_PARTIAL_PAYLOAD",
          flush=True)


def main():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_PROTECTED_PKG_NATIVE_TEST") == "1" and
         os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         os.uname().machine == "amd64", "NOT_DISPOSABLE_NATIVE_GUEST")
    ver = run(["opnsense-version", "-a"])
    need(ver.returncode == 0 and ver.stdout.strip().startswith("26.7"),
         "NATIVE_OPNSENSE_26_7_REQUIRED")
    project = (ROOT / "VERSION").read_text().strip()
    mk = (ROOT / "Makefile").read_text()
    match = re.search(r"(?m)^PLUGIN_REVISION=\s*(\d+)$", mk)
    need(match is not None, "SOURCE_REVISION_MISSING")
    target = project + "_" + match.group(1)
    archive = ROOT / "dist" / (NAME + "-" + target + ".pkg")
    need(archive.is_file() and archive.stat().st_size > 0 and
         "FreeBSD:15:amd64" == run(["pkg", "config", "ABI"]).stdout.strip(),
         "EXACT_CURRENT_NATIVE_ARCHIVE_REQUIRED")
    candidate_sha = sha(archive)
    need(not ACTIVE.exists() and not ACTIVE.is_symlink(), "BASELINE_UPDATE_RECORD_PRESENT")
    need(not MARKER.exists(), "BASELINE_RESTART_MARKER_PRESENT")

    first = run(["pkg", "add", "-f", str(archive)], timeout=180)
    need(first.returncode == 0 and installed_version() == target,
         "REAL_NATIVE_INITIAL_INSTALL_FAILED")
    before = run([str(SERVICE), "status"])
    need(before.returncode == 1, "EXPECTED_CLEAN_STOPPED_RUNTIME")
    config_before = sha(CONFIG)
    package_before = installed_version()
    again = run([str(SERVICE), "pkg-update", str(archive)], timeout=320)
    installed_after = installed_version()
    state = run([str(SERVICE), "status"])
    reason = re.search(r"(?m)^pkg-update-refused=([A-Z0-9_]+)$",
                       again.stderr)
    evidence = {
        "schema": 1,
        "platform": ver.stdout.strip(), "installed_version": installed_after,
        "same_archive_sha256": candidate_sha, "previous_status": before.returncode,
        "protected_update_rc": again.returncode,
        "protected_refusal_code": reason.group(1) if reason else "none",
        "verified_receipt": "pkg-update=verified-installed-and-restored" in again.stdout,
        "native_status_after": state.returncode,
        "pkgdb_unchanged_identity": package_before == installed_after == target,
        "owner_config_unchanged": config_before == sha(CONFIG),
        "no_active_update_record": not ACTIVE.exists() and not ACTIVE.is_symlink(),
        "no_restart_marker": not MARKER.exists(),
        "owner_appliance_modified": False,
    }
    print("NATIVE_PROTECTED_STOPPED=" + json.dumps(evidence, sort_keys=True),
          flush=True)
    need(all([evidence["protected_update_rc"] == 0,
              evidence["verified_receipt"],
              evidence["native_status_after"] == 1,
              evidence["pkgdb_unchanged_identity"],
              evidence["owner_config_unchanged"],
              evidence["no_active_update_record"],
              evidence["no_restart_marker"]]),
         "PROTECTED_NATIVE_STOPPED_REINSTALL_NOT_CONFIRMED")

    # Inject only one disposable plugin-owned INCOMPLETE update record;
    # prove it refuses before launching another pkg or touching Config.
    ACTIVE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    need(not ACTIVE.exists() and not ACTIVE.is_symlink(), "UNEXPECTED_RECORD")
    ACTIVE.write_text('{"schema":1,"phase":"requires-review"}\n')
    ACTIVE.chmod(0o600)
    try:
        pre = sha(CONFIG)
        blocked = run([str(SERVICE), "pkg-update", str(archive)], timeout=60)
        need(blocked.returncode != 0 and
             installed_version() == target and
             sha(CONFIG) == pre and
             ACTIVE.exists() and
             run([str(SERVICE), "status"]).returncode == 1,
             "UNSAFE_REPEAT_WITH_PENDING_UPDATE_RECORD")
        print("NATIVE_PROTECTED_PENDING_REFUSAL=PASS", flush=True)
    finally:
        # Fixture is an exact, test-owned disposable file; no owner cleanup.
        need(ACTIVE.read_text() == '{"schema":1,"phase":"requires-review"}\n',
             "TEST_RECORD_CHANGED_UNEXPECTEDLY")
        ACTIVE.unlink()
    need(not ACTIVE.exists(), "PENDING_TEST_CLEANUP_FAILED")
    print("NATIVE_PROTECTED_UPDATE=PASS_STOPPED_AND_PENDING_REFUSAL")
    native_running_reinstall(archive, target, candidate_sha)
    native_interrupted_handoff(archive, target, candidate_sha)
    # _86 proved in-hook SIGKILL. This exact guest instead tests the earlier,
    # physically observed partial-payload window and ends blocked/STOPPED.
    native_partial_payload_interruption(archive, target, candidate_sha)
    print("NATIVE_PROTECTED_UPDATE=PASS_STOPPED_RUNNING_AND_MIDEXTRACT")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print("NATIVE_PROTECTED_UPDATE=REFUSED:" + str(exc), file=sys.stderr)
        sys.exit(2)
