#!/usr/bin/env python3
"""Disposable OPNsense 26.7 native evidence: outer FD9 held through real pkg.

This is a feasibility / negative-safety investigation, NEVER an updater.
Actual published 0.6.2_1 and its unmodified hooks remain authoritative.
The test's real pkg may replace the old package in one-use CI VM only.
"""
import importlib.util
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
REVISION = "81"
OPTIN = "ZAPRET2_STAGE2_REAL_HELD_FD9_PKG"
LIFECYCLE_LOCK = Path("/var/run/zapret2-lifecycle.lock")
LOCKF = "/usr/bin/lockf"
NAME = "os-zapret2-restyle"

def load(filename):
    spec = importlib.util.spec_from_file_location(
        filename.replace("-", "_").replace(".", "_"), HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

prior = load("stage2-opnsense-real-firmware-unlock-bypass.py")
locked, unsafe, stopped, native, clean, old = (
    prior.locked, prior.unsafe, prior.stopped, prior.native,
    prior.clean, prior.old)

class Refusal(Exception):
    pass

def need(ok, why):
    if not ok:
        raise Refusal(why)

# Do not use 'lockf file command': the stock service uses inherited FD9.
# The shell owns FD9 across real pkg execution, including the incoming hooks.
HELD_PKG_SHELL = (
    'set -eu; '
    'exec 9>"$1"; '
    '/usr/bin/lockf -s -t 1 9 || exit 75; '
    'printf "LOCKED\\n" > "$2"; '
    '/bin/sleep 1; '
    'printf "ENTER_PKG\\n" > "$3"; '
    'pkg -o REPO_AUTOUPDATE=false add -f "$4"'
)
CHALLENGER_SHELL = (
    'exec 9>"$1"; /usr/bin/lockf -s -t 0 9'
)

def qualify():
    need(os.geteuid() == 0 and os.environ.get("GITHUB_ACTIONS") == "true"
         and os.environ.get(OPTIN) == "1"
         and os.environ.get("ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK") == "1"
         and os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1",
         "DISPOSABLE_HELD_FD9_OPTIN_REQUIRED")
    native.gate()
    need(all(m.REVISION == REVISION for m in
             (prior, locked, unsafe, stopped, native, clean)),
         "CURRENT_NATIVE_SOURCE_REVISION_MISMATCH")
    need(os.path.isfile(LOCKF) and os.access(LOCKF, os.X_OK),
         "REAL_FREEBSD_LOCKF_NOT_EXECUTABLE")

def check_lock_file(path):
    need(path == LIFECYCLE_LOCK, "NOT_THE_HISTORICAL_FD9_LOCK_PATH")
    need(not path.is_symlink(), "LIFECYCLE_LOCK_SYMLINK")
    if path.exists():
        st = path.lstat()
        need(stat.S_ISREG(st.st_mode) and st.st_nlink == 1
             and st.st_uid == 0, "FOREIGN_LIFECYCLE_LOCK_INODE")
    # Missing lock file is permitted: the authentic service creates it
    # on its first default-path FD9 acquisition, without unlinking it.

def wait_marker(path, process, *, seconds=8, sleep=time.sleep):
    need(0 < seconds <= 8, "UNBOUNDED_MARKER_WAIT")
    until = time.monotonic() + seconds
    while not path.exists() and time.monotonic() < until:
        need(process.poll() is None, "HELD_FD9_SHELL_EARLY_EXIT")
        sleep(0.05)
    need(path.is_file() and not path.is_symlink()
         and process.poll() is None, "HELD_FD9_MARKER_OR_PROCESS_MISSING")
    return True

def independent_fd9_challenge(path):
    # FreeBSD lockf -t 0 returns EX_TEMPFAIL (75) when another process
    # owns a BSD flock; check the real file, not a temporary lookalike.
    p = subprocess.run(["/bin/sh", "-c", CHALLENGER_SHELL, "sh", str(path)],
                       capture_output=True, text=True, timeout=8, check=False)
    need(p.returncode == 75, "FD9_HOLD_NOT_EXCLUSIVE:" + str(p.returncode))
    return True

def classify(before, after, rc, old_identity, new_identity, hook_refused):
    need(before == old_identity, "OLD_IDENTITY_NOT_PROVEN")
    need(after in (old_identity, new_identity),
         "UNKNOWN_INSTALLED_PACKAGE_IDENTITY")
    if after == new_identity:
        need(rc == 0, "NEW_PKGDB_WITH_UNSUCCESSFUL_NATIVE_PKG")
        need(hook_refused, "GENUINE_PREINSTALL_REFUSAL_NOT_OBSERVED")
        return "OBSERVED_HELD_FD9_NOT_A_NATIVE_PKG_VETO"
    # An unchanged pkgdb says nothing about whether other files mutated.
    return "OBSERVED_OLD_PKGDB_RETAINED_WITH_OUTER_FD9"

def execute_pkg_with_held_fd9(successor, lockfile):
    with tempfile.TemporaryDirectory(prefix="stage2-held-fd9-") as folder:
        marker = Path(folder) / "held"
        entered = Path(folder) / "enter-pkg"
        proc = None
        try:
            proc = subprocess.Popen(
                ["/bin/sh", "-c", HELD_PKG_SHELL, "sh", str(lockfile),
                 str(marker), str(entered), str(successor)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, start_new_session=True)
            wait_marker(marker, proc)
            pre_pkg_contended = independent_fd9_challenge(lockfile)
            wait_marker(entered, proc)
            # This is an independent process lock attempt while the real
            # pkg shell is active; neither FD9 nor pkg is a mock.
            during_pkg_contended = independent_fd9_challenge(lockfile)
            need(proc.poll() is None, "PKG_FINISHED_BEFORE_FD9_CHECK")
            out, err = proc.communicate(timeout=220)
        except subprocess.TimeoutExpired:
            raise Refusal("REAL_HELD_FD9_PKG_TIMEOUT") from None
        finally:
            if proc and proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.communicate(timeout=8)
        need(marker.is_file() and entered.is_file(),
             "NO_VERIFIED_PKG_ENTRY_UNDER_FD9")
        return {"rc": proc.returncode, "stdout": out, "stderr": err,
                "contended_before_pkg": pre_pkg_contended,
                "contended_during_pkg": during_pkg_contended}

def execute(archive):
    qualify()
    clean.plugin_absent()
    stopped.check_old_archive(archive)
    built = native.build()
    need(built["status"] == "PASS_OFFICIAL_NATIVE_BUILD_SOURCE_ONLY"
         and built["project_sha"] == os.environ.get("ZAPRET2_NATIVE_PROJECT_SHA"),
         "NATIVE_SUCCESSOR_UNQUALIFIED")
    successor = native.ROOT / built["output"]
    successor_sha = built["real_native_pkg"]["sha256"]
    need(successor.is_file() and not successor.is_symlink()
         and clean.digest(successor) == successor_sha,
         "SUCCESSOR_SHA_NOT_QUALIFIED")
    installer = stopped.load("stage0-opnsense-installed-predecessor.py")
    need(installer.install_and_verify(archive)["status"]
         == "PASS_OPNSENSE_26_7_REAL_PREDECESSOR_INSTALLED_PROVENANCE",
         "OLD_PACKAGE_PROVENANCE_NOT_QUALIFIED")
    inspector = stopped.load("stage0-opnsense-prepkg-readonly.py")
    need(inspector.snapshot(archive)["status"]
         == "PASS_COLD_READ_ONLY_SNAPSHOT_ONLY",
         "COLD_REAL_OWNER_NOT_PROVEN")
    check_lock_file(LIFECYCLE_LOCK)
    old_id = NAME + "|0.6.2_1"
    new_id = NAME + "|" + native.VERSION + "_" + REVISION
    need(unsafe.installed_identity() == old_id,
         "REAL_OLD_INSTALLED_IDENTITY_MISMATCH")
    need(not prior.package_locked(), "PREEXISTING_PACKAGE_METADATA_LOCK")
    old_record = locked.installed_record()
    service_before = clean.digest(Path(old.SERVICE))
    config_before = Path("/conf/config.xml").read_bytes()
    need(all(not x.exists() and not x.is_symlink() for x in inspector.MARKERS),
         "PREEXISTING_PACKAGE_RESTART_MARKER")

    result = execute_pkg_with_held_fd9(successor, LIFECYCLE_LOCK)
    observed_id = unsafe.installed_identity()
    hook_output = result["stdout"] + "\n" + result["stderr"]
    hook_refused = any(t in hook_output for t in
                       ("incomplete zapret lifecycle",
                        "cannot determine zapret service state",
                        "controlled recovery before package replacement",
                        "could not be stopped"))
    config_unchanged = Path("/conf/config.xml").read_bytes() == config_before
    service_unchanged = (Path(old.SERVICE).is_file()
                         and clean.digest(Path(old.SERVICE)) == service_before)
    old_record_unchanged = (locked.installed_record() == old_record
                            if observed_id == old_id else False)
    before_cleanup = {
        "authentic_old_identity": old_id,
        "installed_after_pkg": observed_id,
        "real_pkg_exit": result["rc"],
        "outer_fd9_contended_before_pkg": result["contended_before_pkg"],
        "outer_fd9_contended_during_pkg": result["contended_during_pkg"],
        "incoming_hook_refusal_observed": hook_refused,
        "original_pkgdb_unchanged": old_record_unchanged,
        "original_service_unchanged": service_unchanged,
        "config_bytes_unchanged": config_unchanged,
        "restart_markers_absent_after_pkg": all(
            not x.exists() and not x.is_symlink() for x in inspector.MARKERS),
        "successor_pkg_sha256": successor_sha,
        "successor_pkg_unchanged": clean.digest(successor) == successor_sha,
        "published_predecessor_sha256": old.ARCHIVE_SHA,
    }
    print("STAGE2_HELD_FD9_PKG_PRE_DISPOSAL="
          + json.dumps(before_cleanup, sort_keys=True), flush=True)
    need(before_cleanup["successor_pkg_unchanged"],
         "NATIVE_SUCCESSOR_ARCHIVE_MUTATED")
    verdict = classify(old_id, observed_id, result["rc"], old_id,
                       new_id, hook_refused)
    return {
        "schema": 1, "status": "PASS_REAL_OUTER_FD9_PKG_FEASIBILITY_HAZARD_ONLY",
        "verdict": verdict, "measured": before_cleanup,
        "real_historical_fd9_held_during_pkg": True,
        "real_historical_old_hook_bytes_untouched": True,
        "no_outer_fd9_safe_upgrade_claim": True,
        "supported_owner_pre_pkg_admission_implemented": False,
        "lh08_ac11_accepted": False,
        "production_hooks_modified": False,
        "owner_appliance_modified": False,
        "published_package_changed": False,
    }

def main():
    if len(sys.argv) != 2:
        print("STAGE2_HELD_FD9_PKG=REFUSED:OLD_ARCHIVE_REQUIRED", file=sys.stderr)
        return 2
    try:
        value = execute(Path(sys.argv[1]))
    except (Refusal, prior.Refusal, locked.Refusal, unsafe.Refusal,
            stopped.Refusal, native.Refusal, clean.Refusal,
            old.Refusal, OSError, ValueError, KeyError,
            subprocess.SubprocessError) as exc:
        print("STAGE2_HELD_FD9_PKG=REFUSED:" + str(exc), file=sys.stderr)
        return 2
    print("STAGE2_HELD_FD9_PKG="
          + json.dumps(value, sort_keys=True))
    return 0

if __name__ == "__main__":
    sys.exit(main())
