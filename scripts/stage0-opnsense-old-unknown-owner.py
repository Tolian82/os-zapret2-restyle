#!/usr/bin/env python3
"""Prove genuine old OPNsense pkg deletion REFUSES a corrupt shared Apply journal.

Only disposable OPNsense 26.7 guest. Real published old package, original
installed service and installed PRE_DEINSTALL; no mocked hook, Start, Stop,
kernel rule modification, configd reload, foreign repo changes, or successor.
"""
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile


def load(filename, name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


old = load("stage0-opnsense-old-deinstall.py", "old_deinstall")
pre = old.pre
fd9 = old.fd9
JOURNAL = fd9.SHARED_JOURNAL
INVALID_BYTES = b"{invalid common Apply json\n"
UNKNOWN_STATUS = "zapret is in an incomplete runtime state"
UNKNOWN_HOOK_DIAGNOSTIC = "ERROR: incomplete zapret lifecycle"
MARKERS = (
    Path("/var/run/zapret2-restyle/pkg-upgrade.restart"),
    Path("/var/run/zapret2-restyle/pkg-replacement.restart"),
)
DELETE = old.DELETE


def require(condition, reason):
    if not condition:
        raise pre.Refusal(reason)


def prove_unknown_status(result):
    require(result.returncode == 2 and result.stdout.strip() == UNKNOWN_STATUS,
            "OLD_INSTALLED_SERVICE_DID_NOT_REFUSE_UNKNOWN_OWNER:" +
            str(result.returncode))


def ensure_no_markers():
    require(all(not p.exists() and not p.is_symlink() for p in MARKERS),
            "HISTORICAL_RESTART_MARKER_WAS_CREATED_OR_ALREADY_PRESENT")


def ensure_no_journal():
    require(not JOURNAL.exists() and not JOURNAL.is_symlink(),
            "UNQUALIFIED_PREEXISTING_JOURNAL")


def create_disposable_root_if_absent():
    """Never touch an existing foreign root; create only in throwaway guest."""
    parent = JOURNAL.parent
    if parent.is_symlink():
        raise pre.Refusal("SHARED_RUNTIME_PARENT_SYMLINK")
    if parent.exists():
        require(parent.is_dir(), "SHARED_RUNTIME_PARENT_NOT_DIRECTORY")
        return False
    base = parent.parent
    require(base.is_dir() and not base.is_symlink(),
            "NO_TRUSTED_SHARED_RUNTIME_PARENT")
    parent.mkdir(mode=0o700)
    require(parent.is_dir() and not parent.is_symlink() and
            stat.S_IMODE(parent.stat().st_mode) == 0o700 and
            {p.name for p in parent.iterdir()} == set(),
            "NEW_TEST_RUNTIME_PARENT_IDENTITY_UNVERIFIED")
    return True


def create_owned_corrupt_journal():
    """Create one known-invalid record in disposable guest, refuse preexisting state."""
    ensure_no_journal()
    require(JOURNAL.parent.is_dir() and not JOURNAL.parent.is_symlink(),
            "JOURNAL_PARENT_NOT_ORIGINAL_DIRECTORY")
    JOURNAL.mkdir(mode=0o700)
    record = JOURNAL / "operation.json"
    try:
        with record.open("xb") as stream:
            stream.write(INVALID_BYTES)
        record.chmod(0o600)
    except (OSError, ValueError):
        raise pre.Refusal("COULD_NOT_PREPARE_ISOLATED_INVALID_JOURNAL") from None
    verify_corrupt_journal()
    return True


def verify_corrupt_journal():
    require(JOURNAL.is_dir() and not JOURNAL.is_symlink() and
            stat.S_IMODE(JOURNAL.stat().st_mode) == 0o700 and
            {p.name for p in JOURNAL.iterdir()} == {"operation.json"},
            "INVALID_JOURNAL_IDENTITY_CHANGED")
    record = JOURNAL / "operation.json"
    require(record.is_file() and not record.is_symlink() and
            stat.S_IMODE(record.stat().st_mode) == 0o600 and
            record.read_bytes() == INVALID_BYTES,
            "INVALID_JOURNAL_CONTENT_CHANGED")


def trace_original_unknown_predeinstall(hook_body, directory):
    env = os.environ.copy()
    env.pop("PKG_UPGRADE", None)
    env.update(
        LIFECYCLE_LOCK_FILE=str(directory / "lifecycle.lock"),
        LOCKF_BIN="/usr/bin/lockf",
        UPGRADE_STATE_DIR=str(directory / "restart"),
        UPGRADE_RESTART_MARKER=str(directory / "restart" / "pkg-upgrade.restart"),
        REPLACEMENT_RESTART_MARKER=str(directory / "restart" / "pkg-replacement.restart"),
    )
    result = old.run_command(("/bin/sh", "-x"), input=hook_body, env=env)
    trace = result.stderr
    require(result.returncode != 0, "ORIGINAL_PRE_DEINSTALL_ACCEPTED_UNKNOWN_JOURNAL")
    require(bool(old.STATUS_TRACE.search(trace)) and
            "service_status=2" in trace and
            UNKNOWN_HOOK_DIAGNOSTIC in trace,
            "ORIGINAL_PRE_DEINSTALL_UNKNOWN_REFUSAL_NOT_TRACED")
    require(not old.STOP_TRACE.search(trace),
            "ORIGINAL_PRE_DEINSTALL_CALLED_STOP_FOR_UNKNOWN_OWNER")
    require(not (directory / "restart").exists(),
            "ORIGINAL_PRE_DEINSTALL_CREATED_RESTART_MARKER")
    return True


def measure_native_pkg_delete_outcome():
    """Measure, never assume, whether FreeBSD pkg honored old pre-hook refusal."""
    result = old.run_command(DELETE)
    info = old.run_command(("pkg", "info", "-e", pre.NAME))
    service = Path(pre.SERVICE)
    require(info.returncode in (0, 1), "NATIVE_PACKAGE_DB_STATE_UNREADABLE")
    require(not service.is_symlink(), "NATIVE_SERVICE_BECAME_SYMLINK")
    diagnostic_seen = UNKNOWN_HOOK_DIAGNOSTIC in (
        result.stdout + "\n" + result.stderr)
    observed = {
        "native_pkg_delete_exit_code": result.returncode,
        "old_pkgdb_present": info.returncode == 0,
        "original_service_path_present": service.is_file(),
        "original_hook_refusal_diagnostic_seen": diagnostic_seen,
    }
    print("STAGE0_NATIVE_PKG_DELETE_OBSERVATION=" +
          json.dumps(observed, sort_keys=True), flush=True)
    # A green experiment means trustworthy diagnosis, NOT safe behavior.
    require(diagnostic_seen, "NATIVE_DELETE_HOOK_REFUSAL_NOT_OBSERVED")
    if (result.returncode == 0 and info.returncode == 1 and
            not service.exists() and not service.is_symlink()):
        return "REMOVED_DESPITE_PRE_DEINSTALL_REFUSAL", observed
    if (result.returncode != 0 and info.returncode == 0 and service.is_file()):
        return "REFUSED_WITH_PACKAGE_PRESERVED", observed
    raise pre.Refusal("AMBIGUOUS_NATIVE_PKG_DELETE_AND_PACKAGE_STATE")




def remove_only_owned_journal():
    """Cleanup only exact synthetic artifacts after validation; no recursive delete."""
    verify_corrupt_journal()
    (JOURNAL / "operation.json").unlink()
    JOURNAL.rmdir()


def run_negative(archive):
    hostname = pre.run("hostname", "-s").decode().strip()
    baseline = pre.run_guest(archive, hostname)
    require(baseline["status"] == "PASS_READ_ONLY_PROVENANCE",
            "OLD_PUBLISHED_PACKAGE_PROVENANCE_UNVERIFIED")
    fd9.assert_fresh_no_shared_journal()
    ensure_no_markers()
    manifest, _ = pre.archive_data(archive)
    original_hook = manifest["scripts"]["pre-deinstall"]
    with tempfile.TemporaryDirectory(prefix="stage0-unknown-old-owner-") as folder:
        directory = Path(folder)
        fd9.prove_stopped(fd9.call_status(directory / "clean.lock"))
        created = False
        created_root = False
        try:
            created_root = create_disposable_root_if_absent()
            created = create_owned_corrupt_journal()
            prove_unknown_status(fd9.call_status(directory / "unknown.lock"))
            traced = trace_original_unknown_predeinstall(original_hook, directory)
            outcome, native = measure_native_pkg_delete_outcome()
            verify_corrupt_journal()
            ensure_no_markers()
            if outcome == "REFUSED_WITH_PACKAGE_PRESERVED":
                prove_unknown_status(fd9.call_status(directory / "still-unknown.lock"))
                after = pre.run_guest(archive, hostname)
                require(after == baseline,
                        "PKG_REFUSAL_MUTATED_PUBLISHED_INSTALLED_BYTES")
            else:
                # This is a real historic package safety hazard. Do NOT
                # attempt rollback or reinterpret it as a successful refusal.
                require(outcome == "REMOVED_DESPITE_PRE_DEINSTALL_REFUSAL",
                        "INVALID_NATIVE_DELETE_OUTCOME")
        finally:
            if created:
                remove_only_owned_journal()
            if created_root:
                require(not JOURNAL.parent.is_symlink() and
                        JOURNAL.parent.is_dir() and
                        stat.S_IMODE(JOURNAL.parent.stat().st_mode) == 0o700,
                        "TEST_CREATED_PARENT_NO_LONGER_OWNED")
                JOURNAL.parent.rmdir()
        fd9.assert_fresh_no_shared_journal()
        if outcome == "REFUSED_WITH_PACKAGE_PRESERVED":
            fd9.prove_stopped(fd9.call_status(directory / "restored.lock"))
    unsafe = outcome == "REMOVED_DESPITE_PRE_DEINSTALL_REFUSAL"
    return {
        "schema": 1,
        "status": ("OBSERVED_UNSAFE_NATIVE_PKG_DELETE_IGNORED_OLD_HOOK_REFUSAL"
                   if unsafe else
                   "OBSERVED_SAFE_NATIVE_PKG_DELETE_REFUSED_UNKNOWN_OWNER"),
        "experiment_completed": True,
        "package_safety_acceptance_passed": not unsafe,
        "package": baseline["package"],
        "published_archive_sha256": pre.ARCHIVE_SHA,
        "installed_service_sha256_before": baseline["service_sha256"],
        "injected_state": "synthetic-corrupt-common-apply-journal-only",
        "real_installed_service_unknown_status": 2,
        "original_pre_deinstall_refused_unknown_owner": traced,
        "original_pre_deinstall_stop_invoked": False,
        "native_pkg_delete_outcome": outcome,
        **native,
        "journal_test_fixture_removed": True,
        "restart_markers_created": False,
        "actual_foreign_ipfw_owner_tested": False,
        "real_running_runtime_tested": False,
        "old_post_deinstall_independently_traced": False,
        "native_successor_tested": False,
        "stage0_closed": False,
    }


def main():
    if len(sys.argv) != 2:
        print("STAGE0_OLD_UNKNOWN_OWNER=REFUSED:EXACT_ARCHIVE_REQUIRED", file=sys.stderr)
        return 2
    try:
        witness = run_negative(Path(sys.argv[1]))
    except (pre.Refusal, OSError, ValueError, KeyError, TypeError) as exc:
        print("STAGE0_OLD_UNKNOWN_OWNER=REFUSED:" + str(exc), file=sys.stderr)
        return 2
    print("STAGE0_OLD_UNKNOWN_OWNER=" + json.dumps(witness, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
