#!/usr/bin/env python3
"""Stage 0 only: kill OWN controller child after private synthetic pkg unlock.

Runs on disposable KVM OPNsense 26.7. An authentic published old Zapret2
package is used only for read-only provenance/Status; all pkg mutations target
another synthetic name in a private PKG_DBDIR and temporary payload.
The experiment demonstrates orphaned lock windows, not production safety.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import select
import signal
import stat
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
NAME = "zapret2-stage0-sidecar-only-fixture"
OLD = NAME + "|0.6.2_1"
PAYLOAD = b"old\n"
EXPECTED_SHA = hashlib.sha256(PAYLOAD).hexdigest()
CHILD = r'''
import os, signal, subprocess, sys
name = sys.argv[1]
cmd = ["pkg", "-o", "REPO_AUTOUPDATE=false", "unlock", "-y", name]
result = subprocess.run(cmd, env=os.environ, capture_output=True,
                        text=True, timeout=40, check=False)
if result.returncode != 0:
    print("UNLOCK_FAILED:" + str(result.returncode), flush=True)
    sys.exit(2)
print("UNLOCKED", flush=True)
signal.pause()
'''


class Refusal(Exception):
    pass


def require(ok, reason):
    if not ok:
        raise Refusal(reason)


def load(path):
    spec = importlib.util.spec_from_file_location(
        path.replace("-", "_").replace(".", "_"), HERE / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def durable_intent(path, db):
    """Evidence is fsynced BEFORE an unlock attempt, not a security barrier."""
    intent = {
        "schema": 1, "experiment": "synthetic-private-pkgdb-only",
        "package": NAME, "expected_pkgdb_identity": OLD,
        "expected_payload_sha256": EXPECTED_SHA,
        "pkgdb_path": str(db), "phase": "PENDING_PRIVATE_UNLOCK",
        "production_guard": False,
    }
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(intent, f, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
    except Exception:
        raise
    directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return intent


def read_intent(path, expected_db):
    st = path.lstat()
    require(stat.S_ISREG(st.st_mode) and not path.is_symlink() and
            stat.S_IMODE(st.st_mode) == 0o600 and st.st_uid == 0,
            "UNTRUSTED_ORPHANED_UNLOCK_RECORD")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(value == {
        "schema": 1, "experiment": "synthetic-private-pkgdb-only",
        "package": NAME, "expected_pkgdb_identity": OLD,
        "expected_payload_sha256": EXPECTED_SHA,
        "pkgdb_path": str(expected_db), "phase": "PENDING_PRIVATE_UNLOCK",
        "production_guard": False,
    }, "DURABLE_RECORD_IDENTITY_NOT_QUALIFIED")
    return value


def recovery_decision(record, state, locked):
    require(record.get("schema") == 1 and record.get("package") == NAME and
            record.get("expected_pkgdb_identity") == OLD and
            record.get("expected_payload_sha256") == EXPECTED_SHA and
            record.get("phase") == "PENDING_PRIVATE_UNLOCK",
            "ORPHAN_RECOVERY_RECORD_MISSING_OR_FOREIGN")
    if state != (OLD, PAYLOAD):
        return "REFUSE_MUTATED_OR_ABSENT_SYNTHETIC_PKG"
    if locked:
        return "ALREADY_LOCKED_UNCHANGED_SYNTHETIC_PKG"
    return "CANDIDATE_RELOCK_ONLY_AFTER_REAL_OWNER_RECHECK"


def kill_owned_child_after_unlock(env, while_unlocked=None):
    """SIGKILL targets only the exact subprocess we created, never Zapret2."""
    child = subprocess.Popen(
        [sys.executable, "-c", CHILD, NAME], env=env, text=True,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    action_result = None
    try:
        readable, _, _ = select.select([child.stdout], [], [], 18)
        require(bool(readable), "OWN_CHILD_DID_NOT_REPORT_UNLOCK")
        line = child.stdout.readline().strip()
        require(line == "UNLOCKED", "OWN_CHILD_UNLOCK_REFUSED:" + line)
        require(child.poll() is None, "OWN_CHILD_EXITED_BEFORE_KILL")
        if while_unlocked is not None:
            action_result = while_unlocked()
        require(child.poll() is None, "OWN_CHILD_EXITED_DURING_PRIVATE_WINDOW")
        os.kill(child.pid, signal.SIGKILL)
        rc = child.wait(timeout=12)
        require(rc == -signal.SIGKILL, "OWN_CHILD_NOT_KILLED")
        return {"killed_child_pid_only": True,
                "child_exit_signal": "SIGKILL",
                "child_native_unlock_completed": True,
                "while_unlocked_result": action_result}
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=12)
        child.stdout.close()
        child.stderr.close()


def prepare_fixture(root, native, fixture):
    db, cache = root / "pkgdb", root / "cache"
    db.mkdir(mode=0o700)
    cache.mkdir(mode=0o700)
    env = dict(os.environ, PKG_DBDIR=str(db),
               PKG_CACHEDIR=str(cache), ASSUME_ALWAYS_YES="yes")
    pkg = ["pkg", "-o", "REPO_AUTOUPDATE=false"]
    old, marker = fixture.build_fixture(
        root, "old", "0.6.2_1", root / "trace", root / "payload")
    installed = native.call(pkg + ["add", str(old)], env)
    require(installed.returncode == 0,
            "PRIVATE_ORIGINAL_INSTALL_FAILED")
    return db, env, pkg, marker


def prove_original_cold(guard, archive):
    """A read-only owner check; never authorizes real package mutation."""
    state = guard.snapshot(archive)
    require(state.get("status") == "PASS_COLD_READ_ONLY_SNAPSHOT_ONLY" and
            state.get("old_package") == "os-zapret2-restyle-0.6.2_1" and
            state.get("real_old_status") == "STOPPED" and
            state.get("safe_pkg_transaction_authorized") is False,
            "ORIGINAL_COLD_OWNER_SNAPSHOT_CHANGED")
    return state


def prove(archive, guest, installed, guard, native, lock, fixture):
    require(os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
            os.uname().machine == "amd64", "ONLY_ROOT_DISPOSABLE_FREEBSD_AMD64")
    require(guest.evaluate(guest.observe()).get("status") ==
            "PASS_ISOLATED_OPNSENSE_26_7_GUEST_IDENTITY",
            "NOT_QUALIFIED_DISPOSABLE_OPNSENSE")
    installed.install_and_verify(archive)
    pre = installed.pre
    host = pre.run("hostname", "-s").decode().strip()
    original = pre.run_guest(archive, host)
    require(original["status"] == "PASS_READ_ONLY_PROVENANCE",
            "ORIGINAL_PUBLISHED_PREDECESSOR_NOT_AUTHENTIC")
    initial = prove_original_cold(guard, archive)
    results = {}
    with tempfile.TemporaryDirectory(prefix="stage0-orphan-unlock-") as folder:
        root = Path(folder)
        for label in ("unchanged", "direct_pkg_while_unlocked"):
            scope = root / label
            scope.mkdir(mode=0o700)
            db, env, pkg, marker = prepare_fixture(scope, native, fixture)
            require(lock.fixture_state(native, pkg, env, marker) == (OLD, PAYLOAD),
                    "EXACT_PRIVATE_FIXTURE_IDENTITY_FAILED")
            lock.lock_exact(native, pkg, env)
            record_file = scope / "pending-unlock.json"
            durable_intent(record_file, db)
            read_intent(record_file, db)
            require(lock.is_locked(native, pkg, env), "NATIVE_PKG_LOCK_NOT_INITIAL")
            # Read-only original-owner witness before opening an unrelated
            # private package's lock; NO real Zapret2 package operations.
            prove_original_cold(guard, archive)
            def uncoordinated_native_delete():
                r = lock.pkg_call(native, pkg, env, ["delete", "-y", NAME])
                return r.returncode
            proof = kill_owned_child_after_unlock(
                env, while_unlocked=uncoordinated_native_delete
                if label == "direct_pkg_while_unlocked" else None)
            require(not lock.is_locked(native, pkg, env),
                    "ORPHANED_UNLOCK_NOT_OBSERVED")
            entry = read_intent(record_file, db)
            state = lock.fixture_state(native, pkg, env, marker)
            decision = recovery_decision(entry, state, False)
            if label == "unchanged":
                require(decision == "CANDIDATE_RELOCK_ONLY_AFTER_REAL_OWNER_RECHECK",
                        "WRONG_UNCHANGED_ORPHAN_CLASSIFICATION")
                prove_original_cold(guard, archive)
                lock.lock_exact(native, pkg, env)
                require(lock.is_locked(native, pkg, env) and
                        lock.fixture_state(native, pkg, env, marker) == (OLD, PAYLOAD),
                        "UNCHANGED_ORPHAN_NOT_RELOCKED")
                refused = lock.pkg_call(native, pkg, env, ["delete", "-y", NAME])
                require(refused.returncode != 0 and
                        lock.fixture_state(native, pkg, env, marker) == (OLD, PAYLOAD),
                        "RELOCKED_PRIVATE_PKG_NOT_PRESERVED")
                results["unchanged_orphan"] = {
                    "owned_test_child_killed": proof["killed_child_pid_only"],
                    "durable_record_validated": True,
                    "classification": decision,
                    "external_recovery_relocked_original_fixture": True,
                    "direct_delete_after_recovery_refused_rc": refused.returncode,
                }
            else:
                require(proof["while_unlocked_result"] == 0,
                        "DIRECT_NATIVE_PKG_DID_NOT_EXECUTE_IN_UNLOCKED_WINDOW")
                require(state == ("ABSENT", None),
                        "DIRECT_NATIVE_PKG_DID_NOT_REMOVE_PRIVATE_FIXTURE")
                require(decision == "REFUSE_MUTATED_OR_ABSENT_SYNTHETIC_PKG",
                        "UNSAFE_ORPHAN_MUTATION_ACCEPTED_FOR_RECOVERY")
                require(not lock.is_locked(native, pkg, env),
                        "MISSING_PRIVATE_PACKAGE_MYSTERIOUSLY_LOCKED")
                results["direct_pkg_after_unlock"] = {
                    "owned_test_child_killed": proof["killed_child_pid_only"],
                    "durable_record_validated": True,
                    "privileged_pkg_delete_while_controller_alive": True,
                    "direct_pkg_delete_rc": proof["while_unlocked_result"],
                    "classification": decision,
                    "recovery_relock_attempted_on_absent_pkg": False,
                    "private_pkg_missing": True,
                }
            require(pre.run_guest(archive, host) == original,
                    "ACTUAL_PUBLISHED_PREDECESSOR_CHANGED")
            prove_original_cold(guard, archive)
    return {
        "schema": 1,
        "status": "OBSERVED_NATIVE_PRIVATE_UNLOCK_KILL_AND_ROOT_BYPASS",
        "authentic_original_installed_predecessor_unchanged": True,
        "authentic_original_cold_before_and_after": True,
        "original_published_package": original["package"],
        "native_experiments": results,
        "root_pkg_bypass_in_unlocked_window_confirmed": True,
        "external_supervisor_manual_relock_only": True,
        "automatic_power_loss_recovery_implemented": False,
        "actual_power_loss_or_automatic_boot_recovery_tested": False,
        "production_owner_guard_implemented": False,
        "real_running_or_foreign_ipfw_tested": False,
        "real_original_plugin_replaced": False,
        "product_safety_acceptance_passed": False,
        "stage0_closed": False,
    }


def main():
    if len(sys.argv) != 2:
        print("STAGE0_ORPHAN=REFUSED:EXACT_ARCHIVE_REQUIRED", file=sys.stderr)
        return 2
    try:
        report = prove(
            Path(sys.argv[1]),
            load("stage0-opnsense-guest-readonly.py"),
            load("stage0-opnsense-installed-predecessor.py"),
            load("stage0-opnsense-prepkg-readonly.py"),
            load("stage0-opnsense-native-pkg-lock.py"),
            load("stage0-opnsense-pkg-relock-failures.py"),
            load("stage0-opnsense-pkg-sidecar-bypass.py"),
        )
    except (Refusal, OSError, ValueError, KeyError, TypeError) as err:
        print("STAGE0_ORPHAN=REFUSED:" + str(err), file=sys.stderr)
        return 2
    print("STAGE0_ORPHAN=" + json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
