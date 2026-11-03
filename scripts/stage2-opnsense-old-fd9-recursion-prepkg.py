#!/usr/bin/env python3
"""Stage 2.23: genuine old service FD9 recursion and pre-pkg negative refusal.

Disposable native OPNsense 26.7 only. The protected package entrypoint is
NOT implemented. This deliberately NEVER invokes destructive pkg after
admission, even for a healthy old owner; no product acceptance is possible.
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
REVISION = "80"
NAME = "os-zapret2-restyle"
OPTIN = "ZAPRET2_STAGE2_REAL_OLD_FD9_RECURSION"
FD9 = Path("/var/run/zapret2-lifecycle.lock")

def load(filename):
    spec = importlib.util.spec_from_file_location(
        filename.replace("-", "_").replace(".", "_"), HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

held = load("stage2-opnsense-real-held-fd9-pkg.py")
prior = held.prior
locked, unsafe, stopped, native, clean, old = (
    held.locked, held.unsafe, held.stopped, held.native, held.clean, held.old)
foreign = unsafe.foreign

class Refusal(Exception):
    pass

def need(ok, code):
    if not ok:
        raise Refusal(code)

def qualify():
    need(os.geteuid() == 0 and os.environ.get("GITHUB_ACTIONS") == "true"
         and os.environ.get(OPTIN) == "1"
         and os.environ.get("ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK") == "1"
         and os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1",
         "DISPOSABLE_OLD_FD9_RECURSION_OPTIN_REQUIRED")
    native.gate()
    need(all(m.REVISION == REVISION for m in
             (held, prior, locked, unsafe, stopped, native, clean)),
         "CURRENT_NATIVE_SOURCE_REVISION_MISMATCH")
    held.check_lock_file(FD9)
    need(os.path.isfile("/usr/bin/lockf"), "REAL_FREEBSD_LOCKF_MISSING")

# A *negative-only* candidate at a future protected boundary. It does not
# claim Web/firmware integration or an allowed path. In particular no callback
# can reach pkg from this function even when status says STOPPED.
def refuse_before_pkg(lock_available, old_status, candidate_sha, invoke_pkg):
    need(len(candidate_sha) == 64 and
         all(c in "0123456789abcdef" for c in candidate_sha),
         "CANDIDATE_ARCHIVE_SHA_UNVERIFIED")
    if not lock_available:
        return "REFUSED_BUSY_OR_INHERITED_FD9_BEFORE_PKG"
    if old_status != 1:
        return "REFUSED_UNVERIFIED_OLD_OWNER_BEFORE_PKG"
    return "REFUSED_NO_SUPPORTED_MANAGED_PKG_ADAPTER"

STATUS_UNDER_HELD_FD9 = (
    'set -eu; exec 9>"$1"; '
    '/usr/bin/lockf -s -t 1 9 || exit 75; '
    'printf "HELD\\n" > "$2"; '
    '/bin/sleep 1; '
    'printf "ENTER_OLD_STATUS\\n" > "$3"; '
    '"$4" status'
)
CHALLENGE_FD9 = 'exec 9>"$1"; /usr/bin/lockf -s -t 0 9'

def challenge(lockfile):
    r = subprocess.run(
        ["/bin/sh", "-c", CHALLENGE_FD9, "sh", str(lockfile)],
        capture_output=True, text=True, timeout=8, check=False)
    need(r.returncode in (0, 75), "FD9_CHALLENGE_UNEXPECTED_EXIT")
    return r.returncode

def marker(path, proc, *, bound=8, sleep=time.sleep):
    need(0 < bound <= 8, "UNBOUNDED_MARKER_WAIT")
    limit = time.monotonic() + bound
    while not path.exists() and time.monotonic() < limit:
        need(proc.poll() is None, "HOLDER_DIED_BEFORE_MARKER")
        sleep(0.05)
    need(path.is_file() and not path.is_symlink()
         and proc.poll() is None, "HOLDER_MARKER_NOT_QUALIFIED")
    return True

def historical_status_under_held_fd9(lockfile, service):
    with tempfile.TemporaryDirectory(prefix="stage2-old-fd9-recursion-") as td:
        ready = Path(td) / "held"
        entered = Path(td) / "entered"
        proc = None
        try:
            proc = subprocess.Popen(
                ["/bin/sh", "-c", STATUS_UNDER_HELD_FD9, "sh",
                 str(lockfile), str(ready), str(entered), str(service)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                start_new_session=True)
            marker(ready, proc)
            need(challenge(lockfile) == 75, "OUTER_FD9_NOT_EXCLUSIVE")
            marker(entered, proc)
            # This is the REAL installed old executable, which opens its
            # own FD9 in service_with_lifecycle_lock. Do not wait 30s and
            # mistake an eventual 75 for a usable nonrecursive handoff.
            started = time.monotonic()
            try:
                output, error = proc.communicate(timeout=4.5)
                elapsed = time.monotonic() - started
                need(proc.returncode == 75, "OLD_STATUS_COMPLETED_WITH_LOCK_HELD:"
                     + str(proc.returncode))
                event = "OLD_STATUS_LOCK_REFUSAL_WHILE_OUTER_FD9_HELD"
            except subprocess.TimeoutExpired:
                elapsed = time.monotonic() - started
                event = "OLD_STATUS_BLOCKED_UNDER_OUTER_FD9_WITHIN_BOUNDED_WINDOW"
                output = ""
                error = ""
            need(elapsed >= 3.8, "LOCK_CONTENTION_OBSERVATION_TOO_SHORT")
        finally:
            # Only the process group WE created inside this disposable
            # test can be terminated; never signal any foreign process.
            if proc and proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.communicate(timeout=8)
        need(challenge(lockfile) == 0, "REAL_FD9_NOT_RELEASED_AFTER_SCOPED_CLEANUP")
        return {
            "outcome": event,
            "independent_lockf_exit_while_held": 75,
            "independent_lockf_exit_after_scoped_cleanup": 0,
            "observed_seconds_minimum": 3.8,
            "real_old_service_invocation": True,
            "subprocess_pg_scope_only": True
        }

def baseline(archive, inspector):
    return {
        "pkgdb": locked.installed_record(),
        "identity": unsafe.installed_identity(),
        "service_sha256": clean.digest(Path(old.SERVICE)),
        "config": Path("/conf/config.xml").read_bytes(),
        "markers_absent": all(not p.exists() and not p.is_symlink()
                              for p in inspector.MARKERS),
        "owner_process_census": inspector.checked_process_census(),
    }

def unchanged(previous, current, *, expected_ipfw=None):
    for field in ("pkgdb", "identity", "service_sha256", "config",
                  "markers_absent", "owner_process_census"):
        need(current[field] == previous[field],
             "PRE_PKG_NEGATIVE_MUTATED:" + field)
    need(current["markers_absent"], "RESTART_MARKER_CREATED")
    if expected_ipfw is not None:
        need(expected_ipfw, "TEST_ORPHAN_STATE_CHANGED")

def execute(archive):
    qualify()
    clean.plugin_absent()
    stopped.check_old_archive(archive)
    built = native.build()
    need(built["status"] == "PASS_OFFICIAL_NATIVE_BUILD_SOURCE_ONLY"
         and built["project_sha"] == os.environ.get("ZAPRET2_NATIVE_PROJECT_SHA"),
         "NATIVE_SOURCE_SHA_NOT_QUALIFIED")
    candidate = native.ROOT / built["output"]
    candidate_sha = built["real_native_pkg"]["sha256"]
    need(candidate.is_file() and not candidate.is_symlink()
         and clean.digest(candidate) == candidate_sha,
         "NATIVE_CANDIDATE_ARCHIVE_UNQUALIFIED")
    installer = stopped.load("stage0-opnsense-installed-predecessor.py")
    need(installer.install_and_verify(archive)["status"]
         == "PASS_OPNSENSE_26_7_REAL_PREDECESSOR_INSTALLED_PROVENANCE",
         "ORIGINAL_PUBLISHED_OLD_NOT_INSTALLED")
    inspector = stopped.load("stage0-opnsense-prepkg-readonly.py")
    need(inspector.snapshot(archive)["status"]
         == "PASS_COLD_READ_ONLY_SNAPSHOT_ONLY",
         "OLD_OWNER_NOT_COLD_AT_NATIVE_BASELINE")
    need(not prior.package_locked(), "PREEXISTING_PKG_METADATA_LOCK")
    need(unsafe.installed_identity() == NAME + "|0.6.2_1",
         "OLD_PACKAGE_IDENTITY_WRONG")
    before = baseline(archive, inspector)
    need(before["markers_absent"], "PREEXISTING_RESTART_MARKER")
    need(challenge(FD9) == 0, "PREEXISTING_FD9_HOLDER")

    collision = historical_status_under_held_fd9(FD9, old.SERVICE)
    need(foreign.command(old.SERVICE, "status").returncode == 1,
         "OLD_STATUS_NOT_STOPPED_AFTER_SCOPED_LOCK_RELEASE")
    after = baseline(archive, inspector)
    unchanged(before, after)
    need(inspector.snapshot(archive)["status"]
         == "PASS_COLD_READ_ONLY_SNAPSHOT_ONLY",
         "ORIGINAL_COLD_SNAPSHOT_NOT_RETAINED")

    # No pkg add is reachable from either negative branch. A callback trap
    # would count if a future regression mistakenly invoked destructive pkg.
    destructive_calls = []
    def forbidden_pkg():
        destructive_calls.append("destructive-pkg")
        raise Refusal("DESTRUCTIVE_PKG_REACHED_ON_NEGATIVE_PATH")
    busy_result = refuse_before_pkg(False, 1, candidate_sha, forbidden_pkg)
    need(busy_result == "REFUSED_BUSY_OR_INHERITED_FD9_BEFORE_PKG"
         and not destructive_calls, "BUSY_FD9_NEGATIVE_NOT_FAIL_CLOSED")

    foreign.activate_kernel(inspector)
    injected = False
    try:
        unsafe.add_test_orphan()
        injected = True
        need(unsafe.only_orphan_loopback_divert(),
             "TEST_ORPHAN_NOT_PROVEN_ISOLATED")
        status = foreign.command(old.SERVICE, "status")
        need(status.returncode == 2, "OLD_STATUS_2_NOT_OBSERVED")
        unsafe_before = baseline(archive, inspector)
        ipfw_before = foreign.command("/sbin/ipfw", "-q", "list")
        need(ipfw_before.returncode == 0,
             "IPFW_BEFORE_REFUSAL_UNREADABLE")
        reject = refuse_before_pkg(True, status.returncode, candidate_sha,
                                   forbidden_pkg)
        need(reject == "REFUSED_UNVERIFIED_OLD_OWNER_BEFORE_PKG"
             and not destructive_calls, "UNKNOWN_OLD_OWNER_NOT_REFUSED_PRE_PKG")
        unsafe_after = baseline(archive, inspector)
        ipfw_after = foreign.command("/sbin/ipfw", "-q", "list")
        unchanged(unsafe_before, unsafe_after,
                  expected_ipfw=(ipfw_after.returncode == 0
                                 and ipfw_before.stdout == ipfw_after.stdout
                                 and unsafe.only_orphan_loopback_divert()))
        need(candidate.is_file() and clean.digest(candidate) == candidate_sha,
             "SIGNED_CANDIDATE_CHANGED_WITHOUT_PKG")
        evidence = {
            "held_fd9_original_status": collision,
            "busy_fd9_pre_pkg_verdict": busy_result,
            "old_incomplete_owner_pre_pkg_verdict": reject,
            "old_service_incomplete_returncode": status.returncode,
            "destructive_pkg_callbacks_invoked": len(destructive_calls),
            "old_pkgdb_identity_after_both_refusals": unsafe.installed_identity(),
            "pkgdb_raw_unchanged_after_both": baseline(archive, inspector)["pkgdb"]
                                                == before["pkgdb"],
            "service_sha_unchanged_after_both": clean.digest(Path(old.SERVICE))
                                                == before["service_sha256"],
            "config_bytes_unchanged_after_both":
                Path("/conf/config.xml").read_bytes() == before["config"],
            "markers_unchanged_after_both":
                all(not p.exists() and not p.is_symlink() for p in inspector.MARKERS),
            "test_owned_ipfw_preserved_before_cleanup":
                unsafe.only_orphan_loopback_divert(),
            "published_old_sha256": old.ARCHIVE_SHA,
            "isolated_native_candidate_sha256": candidate_sha,
            "candidate_archive_unchanged": clean.digest(candidate) == candidate_sha
        }
        print("STAGE2_PREPKG_NEGATIVE_PRE_CLEANUP="
              + json.dumps(evidence, sort_keys=True), flush=True)
        need(evidence["destructive_pkg_callbacks_invoked"] == 0
             and evidence["pkgdb_raw_unchanged_after_both"]
             and evidence["config_bytes_unchanged_after_both"]
             and evidence["test_owned_ipfw_preserved_before_cleanup"],
             "PRE_PKG_NEGATIVE_POSTCONDITION_FAILED")
    finally:
        if injected:
            unsafe.remove_test_orphan()
    need(foreign.only_default(
         foreign.command("/sbin/ipfw", "-q", "list").stdout),
         "TEST_ONLY_IPFW_CLEANUP_FAILED")
    return {
        "schema": 1,
        "status": "PASS_REAL_OLD_FD9_RECURSION_AND_PREPKG_NEGATIVE_ONLY",
        "measured": evidence,
        "real_native_pkg_replacement_invoked": False,
        "installed_original_old_service_used": True,
        "supported_managed_entrypoint_integrated": False,
        "safe_positive_admission_implemented": False,
        "stock_firmware_web_gate_verified": False,
        "lh08_ac11_accepted": False,
        "production_hooks_changed": False,
        "published_pkg_changed": False,
        "owner_appliance_modified": False
    }

def main():
    if len(sys.argv) != 2:
        print("STAGE2_PREPKG_NEGATIVE=REFUSED:ORIGINAL_ARCHIVE_REQUIRED",
              file=sys.stderr)
        return 2
    try:
        report = execute(Path(sys.argv[1]))
    except (Refusal, held.Refusal, prior.Refusal, locked.Refusal,
            unsafe.Refusal, stopped.Refusal, native.Refusal, clean.Refusal,
            foreign.Refusal, old.Refusal, OSError, KeyError, ValueError,
            TypeError, subprocess.SubprocessError) as err:
        print("STAGE2_PREPKG_NEGATIVE=REFUSED:" + str(err), file=sys.stderr)
        return 2
    print("STAGE2_PREPKG_NEGATIVE=" + json.dumps(report, sort_keys=True))
    return 0

if __name__ == "__main__":
    sys.exit(main())
