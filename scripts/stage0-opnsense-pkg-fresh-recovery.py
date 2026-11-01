#!/usr/bin/env python3
"""Stage 0 ONLY: restart a separate recovery interpreter after own child SIGKILL.

Disposable OPNsense 26.7 KVM ONLY. Genuine old os-zapret2-restyle-0.6.2_1
is authenticated and inspected read-only. ALL native pkg mutations are on
a distinct harmless temporary synthetic fixture inside PRIVATE PKG_DBDIR.
No production service, IPFW, native successor, boot hook or gateway mutation.
"""
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
NAME = "zapret2-stage0-sidecar-only-fixture"
OLD = NAME + "|0.6.2_1"
PAYLOAD = b"old\n"
SCENARIOS = ("unchanged", "direct_delete", "tampered_intent", "unknown_owner")
PREFIX = "stage0-fresh-process-recovery-"


class Refusal(Exception):
    pass


def require(ok, reason):
    if not ok:
        raise Refusal(reason)


def load(filename):
    spec = importlib.util.spec_from_file_location(
        filename.replace("-", "_").replace(".", "_"), HERE / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def original_cold(guard, archive):
    try:
        result = guard.snapshot(archive)
    except guard.Refusal as exc:
        raise Refusal("ORIGINAL_OWNER_SNAPSHOT_REFUSED:" + str(exc)) from None
    require(result.get("status") == "PASS_COLD_READ_ONLY_SNAPSHOT_ONLY" and
            result.get("old_package") == "os-zapret2-restyle-0.6.2_1" and
            result.get("real_old_status") == "STOPPED" and
            result.get("safe_pkg_transaction_authorized") is False,
            "UNQUALIFIED_GENUINE_OLD_OWNER")
    return result


def scope_root(scope):
    """Reject arbitrary filesystem targets before any synthetic pkg mutation."""
    require(scope.is_absolute() and not ".." in scope.parts and
            scope.name in SCENARIOS and scope.parent.name.startswith(PREFIX),
            "SCOPE_OUTSIDE_DISPOSABLE_TEST")
    for path in (scope.parent, scope, scope / "pkgdb", scope / "cache"):
        st = path.lstat()
        require(stat.S_ISDIR(st.st_mode) and not path.is_symlink() and
                st.st_uid == 0 and stat.S_IMODE(st.st_mode) == 0o700,
                "SCOPE_PRIVATE_ROOT_DIRECTORY_UNQUALIFIED:" + str(path))
    return scope


def private_pkg(scope):
    env = dict(os.environ, PKG_DBDIR=str(scope / "pkgdb"),
               PKG_CACHEDIR=str(scope / "cache"), ASSUME_ALWAYS_YES="yes")
    return ["pkg", "-o", "REPO_AUTOUPDATE=false"], env


def require_guest_root():
    require(os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
            os.uname().machine == "amd64",
            "ONLY_ROOT_DISPOSABLE_FREEBSD_AMD64")


def recover(scope, archive, guard, native, locks, orphan):
    """One NEW interpreter process, no in-memory state from killed controller."""
    require_guest_root()
    scope_root(scope)
    original_cold(guard, archive)
    try:
        record = orphan.read_intent(scope / "pending-unlock.json", scope / "pkgdb")
    except orphan.Refusal as exc:
        raise Refusal(str(exc)) from None
    pkg, env = private_pkg(scope)
    payload = scope / "payload" / "fixture"
    actual = locks.fixture_state(native, pkg, env, payload)
    is_locked = locks.is_locked(native, pkg, env)
    decision = orphan.recovery_decision(record, actual, is_locked)
    require(decision != "REFUSE_MUTATED_OR_ABSENT_SYNTHETIC_PKG",
            "REFUSE_CHANGED_OR_MISSING_PRIVATE_FIXTURE")
    if decision == "CANDIDATE_RELOCK_ONLY_AFTER_REAL_OWNER_RECHECK":
        original_cold(guard, archive)
        locks.lock_exact(native, pkg, env)
        outcome = "RECOVERED_UNCHANGED_PRIVATE_FIXTURE"
    elif decision == "ALREADY_LOCKED_UNCHANGED_SYNTHETIC_PKG":
        outcome = "ALREADY_LOCKED_UNCHANGED_PRIVATE_FIXTURE"
    else:
        raise Refusal("UNKNOWN_RECOVERY_DECISION")
    require(locks.is_locked(native, pkg, env) and
            locks.fixture_state(native, pkg, env, payload) == (OLD, PAYLOAD),
            "POST_RECOVERY_NATIVE_PKG_NOT_VERIFIED")
    original_cold(guard, archive)
    return {
        "schema": 1, "status": outcome,
        "separate_new_interpreter_process": True,
        "authenticated_old_published_package_readonly": True,
        "private_fixture_exact_identity_verified": True,
        "private_fixture_native_lock_verified": True,
        "actual_boot_or_power_loss_tested": False,
        "production_guard_implemented": False,
        "product_safety_acceptance_passed": False,
        "stage0_closed": False,
    }


def invoke_fresh_recovery(scope, archive):
    command = [sys.executable, str(Path(__file__).resolve()),
               "recover", str(scope), str(archive)]
    try:
        p = subprocess.run(command, capture_output=True, text=True,
                           timeout=95, check=False)
    except (OSError, subprocess.SubprocessError):
        raise Refusal("NEW_RECOVERY_INTERPRETER_UNAVAILABLE") from None
    require(p.returncode in (0, 2), "RECOVERY_PROCESS_UNEXPECTED_EXIT:" +
            str(p.returncode))
    stdout = p.stdout.strip()
    stderr = p.stderr.strip()
    if p.returncode == 0:
        require(stdout.startswith("STAGE0_FRESH_RECOVERY=") and not stderr,
                "SUCCESS_RECOVERY_REPORT_MISSING_OR_ERROR")
        return p.returncode, json.loads(stdout.split("=", 1)[1])
    require(not stdout and stderr.startswith("STAGE0_FRESH_RECOVERY=REFUSED:"),
            "REFUSAL_REPORT_MISSING")
    return p.returncode, {"status": "REFUSED", "reason": stderr.split("REFUSED:", 1)[1]}


def make_private_fixture(scope, native, fixture, locks):
    (scope / "pkgdb").mkdir(mode=0o700)
    (scope / "cache").mkdir(mode=0o700)
    pkg, env = private_pkg(scope)
    archive, marker = fixture.build_fixture(
        scope, "old", "0.6.2_1", scope / "hooks.trace", scope / "payload")
    installed = native.call(pkg + ["add", str(archive)], env)
    require(installed.returncode == 0, "PRIVATE_OLD_FIXTURE_INSTALL_FAILED")
    require(locks.fixture_state(native, pkg, env, marker) == (OLD, PAYLOAD),
            "PRIVATE_FIXTURE_NOT_AUTHENTIC")
    locks.lock_exact(native, pkg, env)
    return pkg, env, marker


def run_experiment(archive, guest, installed, guard, native, locks, orphan,
                   unknown, fixture):
    require_guest_root()
    require(guest.evaluate(guest.observe()).get("status") ==
            "PASS_ISOLATED_OPNSENSE_26_7_GUEST_IDENTITY",
            "NOT_DISPOSABLE_OPNSENSE_26_7")
    installed.install_and_verify(archive)
    pre = installed.pre
    hostname = pre.run("hostname", "-s").decode().strip()
    authentic = pre.run_guest(archive, hostname)
    require(authentic.get("status") == "PASS_READ_ONLY_PROVENANCE",
            "ORIGINAL_INSTALLED_PREDECESSOR_UNQUALIFIED")
    original_cold(guard, archive)
    results = {}
    with tempfile.TemporaryDirectory(prefix=PREFIX) as tmp:
        root = Path(tmp)
        for scenario in SCENARIOS:
            scope = root / scenario
            scope.mkdir(mode=0o700)
            pkg, env, marker = make_private_fixture(scope, native, fixture, locks)
            scope_root(scope)
            intent = scope / "pending-unlock.json"
            orphan.durable_intent(intent, scope / "pkgdb")
            orphan.read_intent(intent, scope / "pkgdb")
            require(locks.is_locked(native, pkg, env), "INITIAL_LOCK_NOT_PRESENT")
            original_cold(guard, archive)
            child = orphan.kill_owned_child_after_unlock(env)
            require(child["child_exit_signal"] == "SIGKILL" and
                    not locks.is_locked(native, pkg, env),
                    "ORPHANED_NATIVE_UNLOCK_NOT_VERIFIED")
            journal_created = False
            journal_parent = False
            try:
                if scenario == "direct_delete":
                    deleting = native.call(pkg + ["delete", "-y", NAME], env)
                    require(deleting.returncode == 0 and
                            locks.fixture_state(native, pkg, env, marker) == ("ABSENT", None),
                            "PRIVILEGED_DIRECT_PKG_RACE_NOT_OBSERVED")
                if scenario == "tampered_intent":
                    original = json.loads(intent.read_text(encoding="utf-8"))
                    original["package"] = "foreign-package"
                    intent.write_text(json.dumps(original, sort_keys=True) + "\n",
                                      encoding="utf-8")
                    require(locks.fixture_state(native, pkg, env, marker) == (OLD, PAYLOAD),
                            "TAMPER_CASE_PACKAGE_CHANGED")
                if scenario == "unknown_owner":
                    journal_parent = unknown.create_disposable_root_if_absent()
                    journal_created = unknown.create_owned_corrupt_journal()
                    unknown.verify_corrupt_journal()
                rc, report = invoke_fresh_recovery(scope, archive)
                if scenario == "unchanged":
                    require(rc == 0 and
                            report["status"] == "RECOVERED_UNCHANGED_PRIVATE_FIXTURE",
                            "NEW_PROCESS_FAILED_TO_RECOVER_IDENTICAL_PRIVATE_PKG")
                    require(locks.is_locked(native, pkg, env), "RECOVERED_LOCK_ABSENT")
                    refused = native.call(pkg + ["delete", "-y", NAME], env)
                    require(refused.returncode != 0 and
                            locks.fixture_state(native, pkg, env, marker) == (OLD, PAYLOAD),
                            "DIRECT_DELETE_BYPASSED_RESTORED_PKG_LOCK")
                    again_rc, again = invoke_fresh_recovery(scope, archive)
                    require(again_rc == 0 and
                            again["status"] == "ALREADY_LOCKED_UNCHANGED_PRIVATE_FIXTURE",
                            "RESTART_RECOVERY_NOT_IDEMPOTENT")
                else:
                    require(rc == 2 and report["status"] == "REFUSED",
                            "UNSAFE_FRESH_RECOVERY_FALSE_SUCCESS")
                    require(not locks.is_locked(native, pkg, env),
                            "UNSAFE_REFUSAL_MUTATED_PKG_LOCK")
                    require(locks.fixture_state(native, pkg, env, marker) ==
                            (("ABSENT", None) if scenario == "direct_delete"
                             else (OLD, PAYLOAD)),
                            "UNSAFE_REFUSAL_MUTATED_PRIVATE_PACKAGE")
                    if scenario == "direct_delete":
                        require(report["reason"] ==
                                "REFUSE_CHANGED_OR_MISSING_PRIVATE_FIXTURE",
                                "WRONG_DIRECT_DELETE_RECOVERY_REFUSAL")
                    if scenario == "tampered_intent":
                        require(report["reason"] ==
                                "DURABLE_RECORD_IDENTITY_NOT_QUALIFIED",
                                "WRONG_TAMPERED_RECORD_REFUSAL")
                    if scenario == "unknown_owner":
                        require(report["reason"].startswith(
                                "ORIGINAL_OWNER_SNAPSHOT_REFUSED:UNVERIFIED_JOURNAL_MARKER_OR_PIDFILE:"),
                                "WRONG_REAL_OLD_UNKNOWN_OWNER_REFUSAL")
                results[scenario] = {
                    "new_interpreter_exit": rc,
                    "classification": report["status"],
                    "record_tamper_or_unsafe_owner_denied": rc == 2,
                    "synthetic_locked_after": locks.is_locked(native, pkg, env),
                    "private_fixture_identity_after":
                    locks.fixture_state(native, pkg, env, marker)[0],
                }
            finally:
                if journal_created:
                    unknown.remove_only_owned_journal()
                if journal_parent:
                    require(unknown.JOURNAL.parent.is_dir() and
                            not unknown.JOURNAL.parent.is_symlink() and
                            stat.S_IMODE(unknown.JOURNAL.parent.stat().st_mode) == 0o700,
                            "FOREIGN_JOURNAL_PARENT_ON_CLEANUP")
                    unknown.JOURNAL.parent.rmdir()
            require(pre.run_guest(archive, hostname) == authentic,
                    "ORIGINAL_PUBLISHED_INSTALLED_PACKAGE_CHANGED")
            original_cold(guard, archive)
    return {
        "schema": 1,
        "status": "OBSERVED_FRESH_PROCESS_PRIVATE_ORPHAN_RECOVERY_AND_DENIAL",
        "native_scenarios": results,
        "actual_original_published_predecessor_unchanged": True,
        "original_service_cold_owner_rechecked": True,
        "separate_recovery_interpreter_invocations": True,
        "root_bypass_confirmed_for_unlocked_private_pkg": True,
        "automatic_boot_recovery_implemented": False,
        "actual_opnsense_reboot_or_power_loss_tested": False,
        "real_running_foreign_ipfw_tested": False,
        "real_original_plugin_replaced": False,
        "production_owner_guard_implemented": False,
        "product_safety_acceptance_passed": False,
        "stage0_closed": False,
    }


def main():
    try:
        require(len(sys.argv) >= 2, "SUBCOMMAND_REQUIRED")
        guest = load("stage0-opnsense-guest-readonly.py")
        installed = load("stage0-opnsense-installed-predecessor.py")
        guard = load("stage0-opnsense-prepkg-readonly.py")
        native = load("stage0-opnsense-native-pkg-lock.py")
        locks = load("stage0-opnsense-pkg-relock-failures.py")
        orphan = load("stage0-opnsense-pkg-orphaned-unlock.py")
        if sys.argv[1] == "recover":
            require(len(sys.argv) == 4, "RECOVER_SCOPE_AND_ARCHIVE_REQUIRED")
            report = recover(Path(sys.argv[2]), Path(sys.argv[3]),
                             guard, native, locks, orphan)
        elif sys.argv[1] == "experiment":
            require(len(sys.argv) == 3, "EXACT_PUBLISHED_ARCHIVE_REQUIRED")
            report = run_experiment(
                Path(sys.argv[2]), guest, installed, guard, native,
                locks, orphan, load("stage0-opnsense-old-unknown-owner.py"),
                load("stage0-opnsense-pkg-sidecar-bypass.py"))
        else:
            raise Refusal("UNKNOWN_SUBCOMMAND")
    except (Refusal, OSError, ValueError, TypeError, KeyError,
            json.JSONDecodeError) as exc:
        print("STAGE0_FRESH_RECOVERY=REFUSED:" + str(exc), file=sys.stderr)
        return 2
    print("STAGE0_FRESH_RECOVERY=" + json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
