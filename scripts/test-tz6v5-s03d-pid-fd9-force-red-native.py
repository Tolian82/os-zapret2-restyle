#!/usr/bin/env python3
"""TZ6v5 S03d: actual old PID/FD9/CLI behaviour, expected RED, native disposable.

Never run on owner's device. This test does NOT implement operator --force.
Only test-owned /bin/sleep may receive a signal. It proves the existing
common.sh/launcher.sh executable path lacks a sealed owner/birth/epoch guard,
and public service CLI is not yet V5-15/V5-16. The legacy engine is ABSENT.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src/opnsense/scripts/OPNsense/Zapret"
COMMON = SRC / "backend/common.sh"
LAUNCHER = SRC / "backend/launcher.sh"
SERVICE = SRC / "zapret_service.sh"
PROCESS_QUERY = SRC / "process_query.sh"
CONFIG = Path("/conf/config.xml")
ENGINE = Path("/usr/local/etc/zapret2/binaries/my/dvtws2")
PIDFILE = Path("/var/run/dvtws2.pid")
IPFW = Path("/sbin/ipfw")
LOCKF = Path("/usr/bin/lockf")
PS = Path("/bin/ps")


class Refusal(RuntimeError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise Refusal(reason)


def run(args: list[str], *, env=None, timeout=12) -> subprocess.CompletedProcess:
    return subprocess.run(args, env=env, text=True, capture_output=True,
                          timeout=timeout, check=False)


def snapshot(path: Path) -> tuple[bool, str]:
    need(not path.is_symlink(), "S03D_FOREIGN_SYMLINK_" + path.name)
    if not path.exists():
        return False, ""
    need(path.is_file(), "S03D_FOREIGN_NONREGULAR_" + path.name)
    return True, hashlib.sha256(path.read_bytes()).hexdigest()


def ipfw_state() -> tuple[int, str, str]:
    p = run([str(IPFW), "-q", "list"], timeout=8)
    return p.returncode, p.stdout, p.stderr


def inventory() -> list[str]:
    p = run([str(PS), "-ax", "-o", "command="])
    need(p.returncode == 0, "S03D_NATIVE_PS_FAILED")
    return p.stdout.splitlines()


def preflight() -> None:
    # Strong gate before ANY process, disk or IPFW tests.
    need(sys.platform.startswith("freebsd") and os.geteuid() == 0,
         "S03D_FREEBSD_ROOT_ONLY")
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_S03D_DISPOSABLE_NATIVE") == "1" and
         Path("/usr/local/opnsense").is_dir(),
         "S03D_DISPOSABLE_CI_OPT_IN_REQUIRED")
    need(all(p.is_file() for p in (COMMON, LAUNCHER, SERVICE, PROCESS_QUERY,
                                     IPFW, LOCKF, PS)) and
         os.access(PROCESS_QUERY, os.X_OK),
         "S03D_ACTUAL_SOURCE_OR_NATIVE_PROCESS_QUERY_MISSING")
    need(not ENGINE.exists() and not ENGINE.is_symlink() and
         not PIDFILE.exists() and not PIDFILE.is_symlink(),
         "S03D_REFUSE_INSTALLED_ENGINE_OR_REAL_PID")
    need(not any("binaries/my/dvtws2" in s or
                 "strategy_lab_worker.sh" in s
                 for s in inventory()),
         "S03D_REFUSE_REAL_ENGINE_OR_LAB_WORKER")


def source_shell(command: str, *args: str, timeout=10) -> subprocess.CompletedProcess:
    # Source REAL common.sh and launcher.sh, not extracted functions/mocks.
    # common.sh binds ps to the REAL process_query.sh under SCRIPT_DIR.
    # A bare source with default /usr/local/opnsense path (uninstalled on
    # this cold guest) would fail BEFORE checking ps/owner. Never replace
    # this native wrapper with a fake /bin/ps or mocked kill.
    env = {**os.environ, "SCRIPT_DIR": str(SRC),
           "BACKEND_DIR": str(SRC / "backend"),
           "ZAPRET_PROCESS_QUERY_BIN": str(PROCESS_QUERY),
           "COMMON_PS_BIN": str(PROCESS_QUERY),
           "PYTHONDONTWRITEBYTECODE": "1"}
    return run(["/bin/sh", "-c",
                '. "$1"; . "$2"; ' + command,
                "s03d-native", str(COMMON), str(LAUNCHER), *args],
               env=env, timeout=timeout)


def inspect_cli(lock: Path, original_config, original_ipfw) -> dict:
    env = {**os.environ, "SCRIPT_DIR": str(SRC),
           "BACKEND_DIR": str(SRC / "backend"),
           "LIFECYCLE_LOCK_FILE": str(lock),
           "LOCKF_BIN": str(LOCKF),
           "PYTHONDONTWRITEBYTECODE": "1"}
    # These are still read-only invalid option paths. The S05f1 strict
    # reload option now emits its own fixed INVALID_ARGUMENT instead of
    # the historical generic usage text; FD9/Config/IPFW remain untouched.
    help_result = run(["/bin/sh", str(SERVICE), "--help"], env=env)
    reload_result = run(["/bin/sh", str(SERVICE), "reload", "--help"],
                        env=env)
    need(help_result.returncode == 64 and
         reload_result.returncode == 64 and
         "usage: zapret_service.sh" in help_result.stderr and
         reload_result.stderr.strip() == "ERROR: INVALID_ARGUMENT",
         "S03D_OLD_ACTUAL_HELP_RED_CHANGED_REQUIRE_NEW_GREEN")
    need(not lock.exists(), "S03D_UNSUPPORTED_HELP_TOUCHED_FD9")
    need(snapshot(CONFIG) == original_config and
         ipfw_state() == original_ipfw,
         "S03D_HELP_MUTATED_FOREIGN_STATE")
    return {"global_help_expected_red_rc64": True,
            "reload_help_expected_red_rc64": True,
            "help_fd9_unmodified": True}


def pid_evidence(base: Path) -> dict:
    # One test-owned sleep only. It is NOT a plugin engine, and has NO
    # sealed Zapret owner. The interpreter's DVTWS_BIN is temporarily set
    # to the real observed sleep argv0 solely to show the old ps-match weakness.
    p = subprocess.Popen(["/bin/sleep", "90"], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    pidfile = base / "not-owned.pid"
    try:
        need(p.poll() is None, "S03D_OWN_TEST_PROCESS_NOT_RUNNING")
        pidfile.write_text(str(p.pid) + "\n", encoding="ascii")
        # FreeBSD ps may expose either the executed absolute argv0
        # (/bin/sleep) or its basename (sleep). Select only from this
        # one attested Popen child's REAL native ps command line, never
        # synthesize a foreign PID/argv. Whitelist either representation.
        observed = run([str(PS), "-p", str(p.pid), "-o", "command="])
        need(observed.returncode == 0 and observed.stdout.strip(),
             "S03D_NATIVE_CONTROLLED_CHILD_PS_MISSING")
        command = observed.stdout.strip()
        token = command.split()[0]
        need(token in ("/bin/sleep", "sleep") and
             command.split()[1:] == ["90"],
             "S03D_NATIVE_CONTROLLED_CHILD_ARGV_UNEXPECTED:" +
             repr(command[:90]))
        precheck = source_shell(
            'common_process_matches "$3" "$4"',
            str(p.pid), token)
        need(precheck.returncode == 0,
             "S03D_NATIVE_PS_DID_NOT_MATCH_OBSERVED_TEST_CHILD:" +
             repr(command[:90]))
        # A mismatch path must NOT signal the test-owned foreign process,
        # but the legacy launcher silently deletes the untrusted pidfile.
        mismatch = source_shell(
            'DVTWS_BIN=/bin/false; launcher_stop "$3" 0',
            str(pidfile))
        need(mismatch.returncode == 0 and not pidfile.exists() and
             p.poll() is None,
             "S03D_LEGACY_FOREIGN_PIDFILE_RED_CHANGED")
        pidfile.write_text(str(p.pid) + "\n", encoding="ascii")
        # This is a controlled process, so even old TERM is restricted to
        # a Popen child we created. An actual foreign router PID is NEVER
        # passed here. Missing sealed generation/birth/epoch is the RED.
        stop = source_shell(
            'DVTWS_BIN="$4"; launcher_stop "$3" 0',
            str(pidfile), token, timeout=12)
        need(stop.returncode == 0 and not pidfile.exists(),
             "S03D_LEGACY_MATCHING_PROCESS_RED_CHANGED")
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired as ex:
            raise Refusal("S03D_LEGACY_STOP_DID_NOT_TERMINATE_TEST_CHILD") from ex
        need(p.returncode in (-15, -9),
             "S03D_UNEXPECTED_TEST_CHILD_EXIT")
    finally:
        if p.poll() is None:
            # Terminate only the Popen child allocated above.
            p.terminate()
            try:
                p.wait(timeout=2)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait(timeout=2)
    stale = base / "stale.pid"
    stale.write_text("99999999\n", encoding="ascii")
    gone = source_shell(
        'DVTWS_BIN=/bin/sleep; launcher_stop "$3" 0',
        str(stale))
    need(gone.returncode == 0 and not stale.exists(),
         "S03D_LEGACY_STALE_PIDFILE_RED_CHANGED")
    return {"foreign_pidfile_silently_removed_red": True,
            "controlled_nonowner_process_terminated_without_seal_red": True,
            "stale_pidfile_silently_removed_red": True,
            "no_real_dvtws_or_foreign_process_was_signalled": True}


def lock_evidence(lock: Path, before_config, before_ipfw) -> dict:
    # Kernel lock is held by a single test-owned /bin/sleep under REAL
    # FreeBSD /usr/bin/lockf; no mock lock or synthetic FD9 is used.
    # The production service must never enter a start under FD9 BUSY,
    # even when the unimplemented --force token is present.
    env = {**os.environ, "SCRIPT_DIR": str(SRC),
           "BACKEND_DIR": str(SRC / "backend"),
           "LIFECYCLE_LOCK_FILE": str(lock),
           "LOCKF_BIN": str(LOCKF),
           "PYTHONDONTWRITEBYTECODE": "1"}
    # FreeBSD lockf has TWO distinct syntaxes: (file command) and
    # (-s -t n fd) WITHOUT command. Passing "9 /bin/true" would lock
    # a FILE named "9", not our open descriptor! Use the exact FD9
    # no-command form as the real service and prove positive/negative.
    free = run(["/bin/sh", "-c",
                'exec 9>"$1"; /usr/bin/lockf -s -t 0 9',
                "s03d-uncontended-positive-control", str(lock)], timeout=3)
    need(free.returncode == 0,
         "S03D_NATIVE_UNCONTENDED_LOCKF_CONTROL_FAILED:rc=" +
         str(free.returncode) + ":stderr=" + repr(free.stderr[:130]))
    # Shell retains fd9 (and its flock) while running its own sleep.
    # No command is supplied to lockf itself.
    holder = subprocess.Popen(
        ["/bin/sh", "-c",
         'exec 9>"$1"; /usr/bin/lockf -s -t 0 9 || exit $?; /bin/sleep 90',
         "s03d-lock-owner", str(lock)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        acquired = False
        for _ in range(20):
            need(holder.poll() is None, "S03D_NATIVE_LOCK_HOLDER_EXITED")
            attempt = run(
                ["/bin/sh", "-c",
                 'exec 9>"$1"; /usr/bin/lockf -s -t 0 9',
                 "s03d-competing-lock", str(lock)],
                timeout=2)
            if attempt.returncode != 0:
                acquired = True
                break
            time.sleep(0.1)
        need(acquired, "S03D_NATIVE_LOCK_NOT_VERIFIED_HELD")
        before = time.monotonic()
        denied = run(["/bin/sh", str(SERVICE), "start", "--force"],
                     env=env, timeout=38)
        elapsed = time.monotonic() - before
        expected_msg = "another zapret lifecycle operation is already running"
        need(denied.returncode == 75 and expected_msg in denied.stderr,
             "S03D_REAL_FD9_BUSY_FORCE_DID_NOT_REFUSE:rc=" +
             str(denied.returncode) + ":busy_msg=" +
             str(expected_msg in denied.stderr) + ":elapsed=" +
             str(round(elapsed, 1)) + ":stderr=" +
             repr(denied.stderr[-140:]))
        need(elapsed <= 37 and holder.poll() is None,
             "S03D_FD9_OWNER_DID_NOT_SURVIVE_REFUSAL")
        need(snapshot(CONFIG) == before_config and
             ipfw_state() == before_ipfw and
             not ENGINE.exists() and not PIDFILE.exists(),
             "S03D_BUSY_FORCE_MUTATED_CONFIG_IPFW_OR_ENGINE")
        return {"actual_fd9_busy_start_force_rc75_no_mutation": True,
                "force_parsed_or_authenticated": False}
    finally:
        if holder.poll() is None:
            holder.terminate()
            try:
                holder.wait(timeout=2)
            except subprocess.TimeoutExpired:
                holder.kill()
                holder.wait(timeout=2)


def main() -> None:
    preflight()
    old_config, old_ipfw = snapshot(CONFIG), ipfw_state()
    with tempfile.TemporaryDirectory(prefix="s03d-foreign-pid-fd9-",
                                      dir="/tmp") as dirname:
        root = Path(dirname)
        lock = root / "private-original-fd9.lock"
        cli = inspect_cli(lock, old_config, old_ipfw)
        pid = pid_evidence(root)
        print("S03D_REAL_OLD_COMMON_PROCESS_PID_ONLY_EXPECTED_RED=PASS", flush=True)
        need(snapshot(CONFIG) == old_config and ipfw_state() == old_ipfw,
             "S03D_PID_FIXTURE_MUTATED_CONFIG_OR_IPFW")
        busy = lock_evidence(lock, old_config, old_ipfw)
    need(snapshot(CONFIG) == old_config and ipfw_state() == old_ipfw and
         not ENGINE.exists() and not PIDFILE.exists(),
         "S03D_POST_NATIVE_FOREIGN_STATE_CHANGED")
    print("S03D_NATIVE_LEGACY_FORCE_RED=" +
          json.dumps({**cli, **pid, **busy}, sort_keys=True))
    print("S03D_ACTUAL_SOURCE_PID_FD9_EXPECTED_RED=PASS")
    print("S03D_V5_15_FORCE_IMPLEMENTATION_NOT_CLAIMED=1")
    print("S03D_ACTUAL_FOREIGN_ROUTER_PID_NEVER_USED=1")


if __name__ == "__main__":
    try:
        main()
    except (Refusal, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print("S03D_NATIVE_FAIL=" + str(exc)[:220], file=sys.stderr)
        raise SystemExit(1)
