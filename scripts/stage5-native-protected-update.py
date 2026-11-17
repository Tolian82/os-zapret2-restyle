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
import stat
import subprocess
import sys

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
    setup = g03.dispatch_and_poll()
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
    need(prepare.returncode == 0 and
         "zapret-pkg-update-prepared=1" in prepare.stdout and
         ACTIVE.is_file() and not ACTIVE.is_symlink() and
         MARKER.is_file() and
         run([str(SERVICE), "status"]).returncode == 1,
         "INTERRUPT_PRE_PKG_PREPARE_FAILED")
    record_before = sha(ACTIVE)
    pkg_before = installed_version()
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
    need(ACTIVE.is_file() and sha(ACTIVE) == record_before and
         MARKER.is_file() and run([str(SERVICE), "status"]).returncode == 1,
         "INTERRUPT_POST_PKG_GUARD_LOST")
    start_after = run([str(SERVICE), "start"], timeout=40)
    again_after = run([str(SERVICE), "pkg-update", str(archive)], timeout=40)
    need(start_after.returncode == 69 and again_after.returncode == 69 and
         ACTIVE.is_file() and sha(ACTIVE) == record_before and
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
    print("NATIVE_PROTECTED_UPDATE=PASS_STOPPED_PENDING_RUNNING_AND_INTERRUPTED")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print("NATIVE_PROTECTED_UPDATE=REFUSED:" + str(exc), file=sys.stderr)
        sys.exit(2)
