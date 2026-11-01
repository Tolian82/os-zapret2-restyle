#!/usr/bin/env python3
"""Actual installed 0.6.2_1 service Status + real lockf FD9 in isolated OPNsense.

Only original installed service 'status' is invoked, never start/stop/setup,
pkg replacement, configd, worker signals, IPFW mutation, or Python changes.
FD9 is redirected to a temporary lock in this disposable guest only.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "predecessor", ROOT / "stage0-installed-predecessor-readonly.py")
pre = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pre)

SERVICE = pre.SERVICE
LOCKF = "/usr/bin/lockf"
SHARED_JOURNAL = Path("/var/db/zapret2/shared-apply")
EXPECTED_STATUS = "zapret is not running"
HOLDER_SCRIPT = (
    'exec 9>"$1"; '
    '/usr/bin/lockf -s -t 1 9 || exit 75; '
    ': > "$2"; '
    '/bin/sleep 3'
)


def require(condition, reason):
    if not condition:
        raise pre.Refusal(reason)


def status_env(lockfile):
    env = os.environ.copy()
    env["LOCKF_BIN"] = LOCKF
    env["LIFECYCLE_LOCK_FILE"] = str(lockfile)
    return env


def call_status(lockfile):
    try:
        return subprocess.run([SERVICE, "status"], env=status_env(lockfile),
                              capture_output=True, text=True, timeout=38,
                              check=False)
    except (OSError, subprocess.SubprocessError):
        raise pre.Refusal("OLD_STATUS_UNAVAILABLE_OR_TIMEOUT") from None


def prove_stopped(result):
    require(result.returncode == 1 and result.stdout.strip() == EXPECTED_STATUS,
            "OLD_STATUS_NOT_VERIFIED_STOPPED:" + str(result.returncode))


def assert_fresh_no_shared_journal():
    require(not SHARED_JOURNAL.exists() and not SHARED_JOURNAL.is_symlink(),
            "GUEST_HAS_UNQUALIFIED_SHARED_RUNTIME_JOURNAL")


def prove_lock_serialization(lockfile, marker):
    """Hold same real FD9 with another process; old Status must wait and recover."""
    holder = None
    waiter = None
    try:
        holder = subprocess.Popen(
            ["/bin/sh", "-c", HOLDER_SCRIPT, "sh", str(lockfile), str(marker)],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        deadline = time.monotonic() + 7
        while not marker.exists() and time.monotonic() < deadline:
            if holder.poll() is not None:
                raise pre.Refusal("REAL_FD9_HOLDER_EARLY_EXIT:" + str(holder.returncode))
            time.sleep(0.05)
        require(marker.exists() and holder.poll() is None,
                "REAL_FD9_LOCK_NOT_HELD")
        waiter = subprocess.Popen(
            [SERVICE, "status"], env=status_env(lockfile),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        time.sleep(0.4)
        require(waiter.poll() is None, "OLD_STATUS_BYPASSED_BUSY_REAL_FD9")
        holder.wait(timeout=12)
        require(holder.returncode == 0, "REAL_FD9_HOLDER_FAILED")
        stdout, stderr = waiter.communicate(timeout=35)
        rc = waiter.returncode
        require(rc == 1 and stdout.strip() == EXPECTED_STATUS,
                "OLD_STATUS_AFTER_REAL_FD9_RELEASE_NOT_STOPPED:" + str(rc))
        return {"held_fd9_blocks_status": True,
                "old_status_after_release": "STOPPED",
                "real_lockf_used": True,
                "lockfile_isolated_in_temporary_directory": True}
    except subprocess.TimeoutExpired:
        raise pre.Refusal("REAL_FD9_TEST_TIMED_OUT") from None
    finally:
        for proc in (waiter, holder):
            if proc and proc.poll() is None:
                proc.kill()
                proc.wait(timeout=4)


def verify(archive):
    # Provenance is rechecked on THIS actual installed guest before invoking
    # even a read-only service command; the archived package SHA is pinned.
    hostname = pre.run("hostname", "-s").decode().strip()
    report = pre.run_guest(archive, hostname)
    require(report["status"] == "PASS_READ_ONLY_PROVENANCE", "OLD_BYTES_UNVERIFIED")
    require(report["virtual_guest_reported"].lower() not in ("none", "unknown"),
            "OLD_SERVICE_GUEST_NOT_VIRTUAL")
    assert_fresh_no_shared_journal()
    require(os.path.isfile(LOCKF) and os.access(LOCKF, os.X_OK),
            "REAL_FREEBSD_LOCKF_MISSING")
    with tempfile.TemporaryDirectory(prefix="stage0-old-fd9-") as directory:
        root = Path(directory)
        lockfile = root / "lifecycle.lock"
        marker = root / "held"
        initial = call_status(lockfile)
        prove_stopped(initial)
        contention = prove_lock_serialization(lockfile, marker)
        final = call_status(lockfile)
        prove_stopped(final)
    assert_fresh_no_shared_journal()
    return {
        "schema": 1,
        "status": "PASS_OPNSENSE_26_7_INSTALLED_OLD_SERVICE_COLD_FD9",
        "package": report["package"],
        "archived_service_sha256": report["service_sha256"],
        "initial_status": "STOPPED",
        "final_status": "STOPPED",
        **contention,
        "real_original_installed_service_invoked": True,
        "old_service_start_or_stop_invoked": False,
        "no_shared_runtime_journal": True,
        "real_runtime_running_tested": False,
        "real_predecessor_pre_deinstall_executed": False,
        "actual_pkg_replacement": False,
        "native_successor_tested": False,
        "stage0_closed": False,
    }


def main():
    if len(sys.argv) != 2:
        print("STAGE0_OLD_SERVICE_FD9=REFUSED:EXACT_ARCHIVE_REQUIRED", file=sys.stderr)
        return 2
    try:
        print("STAGE0_OLD_SERVICE_FD9=" + json.dumps(verify(Path(sys.argv[1])), sort_keys=True))
    except (pre.Refusal, OSError, ValueError, KeyError) as exc:
        print("STAGE0_OLD_SERVICE_FD9=REFUSED:" + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
