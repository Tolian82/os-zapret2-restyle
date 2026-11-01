#!/usr/bin/env python3
"""Stage 0 only: controlled native pkg unlock and re-lock failure characterization.

Authentic installed 0.6.2_1 is read-only Status/provenance evidence ONLY.
All pkg add/lock/unlock/delete actions touch ONE private synthetic fixture
in a disposable OPNsense 26.7 KVM guest with private PKG_DBDIR/payload.
No production entrypoint, owner Stop/Start, IPFW or real package mutation.
"""
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile

HERE = Path(__file__).resolve().parent
NAME = "zapret2-stage0-sidecar-only-fixture"
OLD = NAME + "|0.6.2_1"
NEW = NAME + "|0.6.2_41"


class Refusal(Exception):
    pass


def require(ok, msg):
    if not ok:
        raise Refusal(msg)


def load(filename):
    spec = importlib.util.spec_from_file_location(
        filename.replace("-", "_").replace(".", "_"), HERE / filename)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def pkg_call(native, pkg, env, action):
    return native.call(pkg + action, env)


def fixture_state(native, pkg, env, marker):
    # Explicitly query THIS private package; the borrowed _41 probe has
    # a different fixed synthetic package name. Never read its pkgdb.
    probe = pkg_call(native, pkg, env, ["query", "%n|%v", NAME])
    require(probe.returncode in (0, 1),
            "EXACT_PRIVATE_PKGDB_QUERY_UNAVAILABLE")
    identity = probe.stdout.strip() if probe.returncode == 0 else "ABSENT"
    require(not marker.is_symlink(), "PRIVATE_FIXTURE_PAYLOAD_IS_SYMLINK")
    payload = marker.read_bytes() if marker.is_file() else None
    return identity, payload


def is_locked(native, pkg, env):
    result = pkg_call(native, pkg, env, ["lock", "-l"])
    # Measured on native OPNsense 26.7: pkg lock -l reports empty lockdb
    # with rc=1 and this EXACT stdout. Any other nonzero result is refused.
    if (result.returncode == 1 and
            result.stdout.strip() == "No locked packages were found" and
            not result.stderr.strip()):
        return False
    require(result.returncode == 0, "NATIVE_LOCK_LIST_UNAVAILABLE:rc=" +
            str(result.returncode) + ":stdout=" + result.stdout.strip()[:160] +
            ":stderr=" + result.stderr.strip()[:160])
    return NAME in result.stdout


def lock_exact(native, pkg, env, required=True):
    result = pkg_call(native, pkg, env, ["lock", "-y", NAME])
    require(result.returncode == 0, "NATIVE_RELOCK_FAILED")
    require(is_locked(native, pkg, env), "NATIVE_RELOCK_NOT_VERIFIED")
    return required


def snapshot_verified(probe):
    observed = probe()
    require(observed.get("status") == "PASS_COLD_READ_ONLY_SNAPSHOT_ONLY" and
            observed.get("old_package") == "os-zapret2-restyle-0.6.2_1" and
            observed.get("real_old_status") == "STOPPED" and
            observed.get("safe_pkg_transaction_authorized") is False,
            "GENUINE_OLD_COLD_SNAPSHOT_NOT_QUALIFIED")
    return observed


def controlled_fixture_replace(native, pkg, env, marker, replacement,
                               probe, *, inject_after_unlock=False):
    """Bounded one-guest fixture experiment, NOT an atomic production wrapper.

    The separate owner snapshot and pkg lock cannot stop a privileged
    concurrent direct pkg process during this temporary unlocked window.
    """
    require(is_locked(native, pkg, env), "PACKAGE_NOT_INITIALLY_LOCKED")
    require(fixture_state(native, pkg, env, marker) == (OLD, b"old\n"),
            "INITIAL_PRIVATE_FIXTURE_NOT_VERIFIED")
    snapshot_verified(probe)  # unknown owner refuses BEFORE unlock
    opened = pkg_call(native, pkg, env, ["unlock", "-y", NAME])
    require(opened.returncode == 0, "PKG_UNLOCK_UNAVAILABLE")
    try:
        require(not is_locked(native, pkg, env), "UNLOCK_NOT_EFFECTIVE")
        snapshot_verified(probe)  # second check, STILL not atomic
        if inject_after_unlock:
            raise Refusal("INJECTED_PRE_PKG_FAILURE_AFTER_UNLOCK")
        installed = pkg_call(native, pkg, env, ["add", "-f", str(replacement)])
        require(installed.returncode == 0, "PRIVATE_REPLACEMENT_FAILED")
        require(fixture_state(native, pkg, env, marker) == (NEW, b"direct\n"),
                "PRIVATE_REPLACEMENT_IDENTITY_NOT_VERIFIED")
    finally:
        # Bounded recovery works only if the private fixture still exists.
        # Unknown/absent package is NOT a restored or safe state.
        actual = fixture_state(native, pkg, env, marker)
        require(actual[0] in (OLD, NEW) and actual[1] in (b"old\n", b"direct\n"),
                "NO_VERIFIED_PKG_TO_RELOCK")
        lock_exact(native, pkg, env)
    return {"status": "PASS_SYNTHETIC_UNLOCK_REPLACE_RELOCK",
            "result": fixture_state(native, pkg, env, marker)[0],
            "relocked": is_locked(native, pkg, env),
            "unprotected_unlocked_window_exists": True,
            "full_product_transaction_authorized": False}


def verify_actual_guest(archive, guest, installed, guard, unknown, native, fixture):
    require(os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
            os.uname().machine == "amd64", "ONLY_ROOT_DISPOSABLE_FREEBSD_AMD64")
    guest.evaluate(guest.observe())
    installed.install_and_verify(archive)  # exact immutable published original
    pre = installed.pre
    hostname = pre.run("hostname", "-s").decode().strip()
    original = pre.run_guest(archive, hostname)
    require(original["status"] == "PASS_READ_ONLY_PROVENANCE",
            "ORIGINAL_PREDECESSOR_IDENTITY_FAILED")
    with tempfile.TemporaryDirectory(prefix="stage0-relock-fault-") as t:
        root = Path(t)
        db, cache = root / "pkgdb", root / "cache"
        db.mkdir(mode=0o700)
        cache.mkdir(mode=0o700)
        env = dict(os.environ, PKG_DBDIR=str(db), PKG_CACHEDIR=str(cache),
                   ASSUME_ALWAYS_YES="yes")
        pkg = ["pkg", "-o", "REPO_AUTOUPDATE=false"]
        old, marker = fixture.build_fixture(
            root, "old", "0.6.2_1", root / "trace", root / "payload")
        new, same_marker = fixture.build_fixture(
            root, "direct", "0.6.2_41", root / "trace", root / "payload")
        require(marker == same_marker, "FIXTURE_PAYLOAD_CHANGED")
        created = pkg_call(native, pkg, env, ["add", str(old)])
        require(created.returncode == 0 and
                fixture_state(native, pkg, env, marker) == (OLD, b"old\n"),
                "SYNTHETIC_ORIGINAL_NOT_INSTALLED")
        lock_exact(native, pkg, env)
        probe = lambda: guard.snapshot(archive)
        initial = snapshot_verified(probe)
        created_parent = False
        journal_created = False
        try:
            created_parent = unknown.create_disposable_root_if_absent()
            journal_created = unknown.create_owned_corrupt_journal()
            unknown.prove_unknown_status(
                guard.load("stage0-opnsense-old-service-fd9.py").call_status(
                    root / "old-status-fd9.lock"))
            try:
                controlled_fixture_replace(
                    native, pkg, env, marker, new, probe)
            except guard.Refusal as ex:
                denied = str(ex)
            else:
                raise Refusal("UNKNOWN_OLD_OWNER_ALLOWED_UNLOCK")
            require(denied.startswith("UNVERIFIED_JOURNAL_MARKER_OR_PIDFILE:"),
                    "WRONG_UNKNOWN_OWNER_REFUSAL:" + denied)
            require(is_locked(native, pkg, env) and
                    fixture_state(native, pkg, env, marker) == (OLD, b"old\n"),
                    "DENIED_PREFLIGHT_CHANGED_LOCK_OR_PACKAGE")
            unknown.verify_corrupt_journal()
        finally:
            if journal_created:
                unknown.remove_only_owned_journal()
            if created_parent:
                require(unknown.JOURNAL.parent.is_dir() and
                        not unknown.JOURNAL.parent.is_symlink() and
                        stat.S_IMODE(unknown.JOURNAL.parent.stat().st_mode) == 0o700,
                        "SYNTHETIC_JOURNAL_PARENT_UNQUALIFIED")
                unknown.JOURNAL.parent.rmdir()
        snapshot_verified(probe)
        try:
            controlled_fixture_replace(
                native, pkg, env, marker, new, probe, inject_after_unlock=True)
        except Refusal as ex:
            fault = str(ex)
        else:
            raise Refusal("INJECTED_FAILURE_DID_NOT_ABORT")
        require(fault == "INJECTED_PRE_PKG_FAILURE_AFTER_UNLOCK",
                "UNEXPECTED_INJECTED_FAILURE_REASON:" + fault)
        require(is_locked(native, pkg, env) and
                fixture_state(native, pkg, env, marker) == (OLD, b"old\n"),
                "INJECTED_FAILURE_NOT_RELOCKED_OLD")
        completed = controlled_fixture_replace(
            native, pkg, env, marker, new, probe)
        require(completed["relocked"] and
                fixture_state(native, pkg, env, marker) == (NEW, b"direct\n"),
                "SUCCESSOR_NOT_RELOCKED")
        # Actual independent native pkg cannot delete locked successor in
        # this private pkgdb. Not general protection against a root unlock.
        direct = pkg_call(native, pkg, env, ["delete", "-y", NAME])
        require(direct.returncode != 0 and is_locked(native, pkg, env) and
                fixture_state(native, pkg, env, marker) == (NEW, b"direct\n"),
                "DIRECT_PKG_REMOVED_RELOCKED_FIXTURE")
        require(pre.run_guest(archive, hostname) == original,
                "ORIGINAL_PUBLISHED_PREDECESSOR_CHANGED")
        snapshot_verified(probe)
    return {
        "schema": 1, "status": "PASS_STAGE0_SYNTHETIC_NATIVE_RELOCK_LIFECYCLE",
        "authentic_old_package": original["package"],
        "initial_cold_status": initial["real_old_status"],
        "unknown_owner_refusal": denied,
        "unknown_owner_denied_before_unlock": True,
        "injected_after_unlock_failure": fault,
        "old_fixture_relocked_after_injected_failure": True,
        "successor_fixture_relocked_after_replace": True,
        "direct_pkg_delete_locked_successor_rc": direct.returncode,
        "native_pkg_lock_after_success": True,
        "old_service_and_package_unchanged": True,
        "temporary_unlocked_window_unprotected": True,
        "concurrent_root_pkg_race_tested": False,
        "real_plugin_pkg_replaced": False,
        "real_running_foreign_ipfw_tested": False,
        "production_transaction_guard_implemented": False,
        "product_safety_acceptance_passed": False,
        "stage0_closed": False,
    }


def main():
    if len(sys.argv) != 2:
        print("STAGE0_RELOCK=REFUSED:EXACT_PUBLISHED_ARCHIVE_REQUIRED", file=sys.stderr)
        return 2
    try:
        guest = load("stage0-opnsense-guest-readonly.py")
        installed = load("stage0-opnsense-installed-predecessor.py")
        guard = load("stage0-opnsense-prepkg-readonly.py")
        unknown = load("stage0-opnsense-old-unknown-owner.py")
        native = load("stage0-opnsense-native-pkg-lock.py")
        fixture = load("stage0-opnsense-pkg-sidecar-bypass.py")
        report = verify_actual_guest(
            Path(sys.argv[1]), guest, installed, guard, unknown, native, fixture)
    except (Refusal, OSError, ValueError, TypeError, KeyError) as ex:
        print("STAGE0_RELOCK=REFUSED:" + str(ex), file=sys.stderr)
        return 2
    print("STAGE0_RELOCK=" + json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
