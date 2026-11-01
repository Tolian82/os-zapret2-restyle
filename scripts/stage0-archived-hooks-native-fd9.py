#!/usr/bin/env python3
"""Unmodified published pkg hooks + native FreeBSD lockf FD9, isolated VM only.

Executes all four real 0.6.2_1 +MANIFEST hook bodies with a *fake* service
and fake configd/firmware commands in a private temp directory. No real
package is installed. This is NOT acceptance of actual OPNsense service.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

SHA = "1e21fbcac847529b94fea940241b4da7f86a42d33c129b7003ad04a72f4e5a0f"
PHASES = ("pre-install", "post-install", "pre-deinstall", "post-deinstall")


class Refusal(Exception):
    pass


def execute(args, env=None, timeout=20):
    try:
        return subprocess.run(args, env=env, capture_output=True, text=True,
                              timeout=timeout, close_fds=True, check=False)
    except (OSError, subprocess.SubprocessError):
        raise Refusal("COMMAND_FAILED_OR_TIMED_OUT") from None


def load_old_hooks(archive):
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA:
        raise Refusal("PUBLISHED_ARCHIVE_DIGEST_MISMATCH")
    response = execute(["tar", "-xOf", str(archive), "+MANIFEST"])
    if response.returncode:
        raise Refusal("ARCHIVE_MANIFEST_UNREADABLE")
    try:
        m = json.loads(response.stdout)
    except ValueError:
        raise Refusal("ARCHIVE_MANIFEST_INVALID") from None
    if (m.get("name"), m.get("version"), m.get("abi")) != (
        "os-zapret2-restyle", "0.6.2_1", "FreeBSD:15:amd64"
    ):
        raise Refusal("OLD_PACKAGE_IDENTITY_OR_ABI_MISMATCH")
    scripts = m.get("scripts")
    if not isinstance(scripts, dict):
        raise Refusal("OLD_FOUR_HOOKS_MISSING")
    hooks = {}
    for p in PHASES:
        x = scripts.get(p)
        if not isinstance(x, str) or not x.startswith("#!/bin/sh\n"):
            raise Refusal("OLD_HOOK_MISSING_OR_NOT_SHELL")
        hooks[p] = x
    return hooks


def mock(path, body):
    path.write_text(body)
    path.chmod(0o700)
    return str(path)


def fixture(root, hooks):
    root = Path(root)
    state, journal, trace = [root / x for x in ("state", "journal", "trace")]
    state.write_text("stopped\n")
    trace.write_text("")
    runtime = root / "runtime"
    runtime.mkdir()
    hdir = root / "old-hooks"
    hdir.mkdir()
    originals = {p: mock(hdir / p, content) for p, content in hooks.items()}
    service = mock(root / "mock-service", r'''#!/bin/sh
case "$1" in
status)
  if [ "$FD9_REQUIRED" = 1 ] && [ -r "$SHARED_APPLY_JOURNAL" ]; then
    if ! (: >&9) 2>/dev/null; then
      echo status:no-fd9 >> "$TRACE"
      exit 2
    fi
    echo status:fd9 >> "$TRACE"
  else
    echo status:ordinary >> "$TRACE"
  fi
  case "$(cat "$STATE")" in
    running) exit 0 ;; stopped) exit 1 ;; incomplete) exit 2 ;; *) exit 64 ;;
  esac ;;
stop)
  echo stop >> "$TRACE"
  [ ! -e "$STOP_FAIL" ] || exit 1
  echo stopped > "$STATE" ;;
*) exit 64 ;;
esac
''')
    pgrep = mock(root / "mock-pgrep", r'''#!/bin/sh
[ "$1" = -P ] && [ "$2" = 4242 ] || exit 64
if [ -f "$RELOADED" ]; then echo 4444; else echo 4343; fi
''')
    kill = mock(root / "mock-kill", r'''#!/bin/sh
echo "kill:$*" >> "$TRACE"
case "$*" in
  '-0 4242') exit 0 ;;
  '-TERM 4343') : > "$RELOADED" ;;
  *) exit 64 ;;
esac
''')
    configctl = mock(root / "mock-configctl", r'''#!/bin/sh
echo "configctl:$*" >> "$TRACE"
case "$*" in
  'system status') [ -f "$RELOADED" ] ;;
  'template reload OPNsense/Zapret') echo OK ;;
  'zapret start') echo running > "$STATE"; echo OK ;;
  *) exit 64 ;;
esac
''')
    register = mock(root / "mock-register", r'''#!/bin/sh
[ "$*" = "install os-zapret2-restyle" ] || exit 64
echo register >> "$TRACE"
''')
    configure = mock(root / "mock-configure", r'''#!/bin/sh
[ "$*" = POST_INSTALL ] || exit 64
echo configure >> "$TRACE"
''')
    pid = root / "pid"
    pid.write_text("4242\n")
    env = os.environ.copy()
    env.update(
        SERVICE_SCRIPT=service, STATE=str(state), TRACE=str(trace),
        SHARED_APPLY_JOURNAL=str(journal), LOCKF_BIN="/usr/bin/lockf",
        LIFECYCLE_LOCK_FILE=str(root / "lock"),
        UPGRADE_STATE_DIR=str(runtime),
        UPGRADE_RESTART_MARKER=str(runtime / "pkg-upgrade.restart"),
        REPLACEMENT_RESTART_MARKER=str(runtime / "pkg-replacement.restart"),
        COLD_INSPECT_BIN=str(root / "nonexistent-inspector"),
        CONFIGD_PID_FILE=str(pid), PGREP_BIN=pgrep, KILL_BIN=kill,
        CONFIGCTL=configctl, FIRMWARE_REGISTER=register,
        CONFIGURE_PLUGINS=configure, SLEEP_BIN="/bin/true",
        RELOADED=str(root / "reloaded"), STOP_FAIL=str(root / "stop-fail"),
        EXTRA_INVENTORY_CACHE=str(root / "nonexistent-inventory"),
        FD9_REQUIRED="1"
    )
    return dict(root=root, env=env, hooks=originals, state=state,
                journal=journal, trace=trace,
                marker=runtime / "pkg-replacement.restart")


def call(f, phase, success=True):
    r = execute(["/bin/sh", f["hooks"][phase]], f["env"])
    if (r.returncode == 0) != success:
        raise Refusal("HOOK_RETURN_UNEXPECTED:" + phase + ":rc=" +
                      str(r.returncode) + ":" + " ".join(r.stderr.split())[:100])


def expect(value, reason):
    if not value:
        raise Refusal(reason)


def verify(f):
    state, journal, trace, marker, root = (f[x] for x in ("state", "journal", "trace", "marker", "root"))
    # RUNNING: real old hook retries under real FD9, Stops and preserves marker.
    state.write_text("running\n")
    journal.write_text("{}\n")
    call(f, "pre-install")
    entries = trace.read_text()
    expect(entries.count("status:no-fd9") >= 2 and
           entries.count("status:fd9") >= 2,
           "REAL_FD9_RETRY_MISSING")
    expect(state.read_text().strip() == "stopped" and marker.exists() and
           "stop\n" in entries, "RUNNING_PRE_INSTALL_INVALID")
    # A strictly OLD Status implementation still demands inherited FD9:
    # historical POST_INSTALL calls direct Status, so it must refuse final
    # success and preserve the marker. This failure is an observed NEGATIVE.
    call(f, "post-install", success=False)
    expect(marker.exists() and "status:no-fd9" in trace.read_text(),
           "LEGACY_POST_INSTALL_MUST_REFUSE_UNVERIFIED_STATUS")
    # Replacement installs the new service before incoming POST_INSTALL.
    # Model the explicit change of service generation, not a silent fix to
    # the immutable original hook body. This is a MOCKED successor only.
    state.write_text("stopped\n")
    (root / "reloaded").unlink(missing_ok=True)
    f["env"]["FD9_REQUIRED"] = "0"
    call(f, "post-install")
    entries = trace.read_text()
    expect(state.read_text().strip() == "running" and not marker.exists() and
           "kill:-TERM 4343" in entries and "configctl:zapret start" in entries and
           "register" in entries and "configure" in entries,
           "SUCCESSOR_MOCK_POST_INSTALL_NOT_RESTORED")
    # STOPPED: no restart marker or automatic Start.
    trace.write_text("")
    (root / "reloaded").unlink(missing_ok=True)
    journal.unlink()
    state.write_text("stopped\n")
    call(f, "pre-install")
    expect(not marker.exists(), "STOPPED_MARKER_INVENTED")
    call(f, "post-install")
    expect("configctl:zapret start" not in trace.read_text() and
           state.read_text().strip() == "stopped", "STOPPED_AUTOSTARTED")
    # OLD PRE_DEINSTALL: old service again, no FD9 retry.
    f["env"]["FD9_REQUIRED"] = "1"
    trace.write_text("")
    journal.write_text("{}\n")
    state.write_text("running\n")
    marker.touch()
    call(f, "pre-deinstall", success=False)
    entries = trace.read_text()
    expect("status:no-fd9" in entries and "status:fd9" not in entries and
           "stop\n" not in entries and marker.exists() and
           state.read_text().strip() == "running",
           "OLD_DEINSTALL_DID_NOT_REFUSE_WITHOUT_FD9")
    # INCOMPLETE even under real FD9 remains refuse-before-Stop.
    trace.write_text("")
    state.write_text("incomplete\n")
    marker.unlink()
    call(f, "pre-install", success=False)
    expect("status:fd9" in trace.read_text() and
           "stop\n" not in trace.read_text() and
           state.read_text().strip() == "incomplete",
           "INCOMPLETE_OWNERSHIP_MUTATED")
    # Failed STOP must refuse, clear intent, leave engine running.
    trace.write_text("")
    journal.unlink()
    state.write_text("running\n")
    (root / "stop-fail").touch()
    call(f, "pre-install", success=False)
    expect("stop\n" in trace.read_text() and not marker.exists() and
           state.read_text().strip() == "running",
           "STOP_FAILURE_MUTATED")
    (root / "stop-fail").unlink()
    # True historical post-deinstall is a no-op.
    state.write_text("stopped\n")
    marker.touch()
    trace.write_text("")
    call(f, "post-deinstall")
    expect(marker.exists() and trace.read_text() == "",
           "HISTORICAL_POST_DEINSTALL_NOT_NOOP")
    return ("FD9_RUNNING_PRE_INSTALL", "LEGACY_POST_INSTALL_STATUS_REFUSAL", "MOCKED_SUCCESSOR_WORKER_RUNNING_RESTORE",
            "STOPPED_NO_AUTOSTART", "OLD_PRE_DEINSTALL_FD9_REFUSAL",
            "INCOMPLETE_REFUSAL", "STOP_FAILURE_REFUSAL",
            "POST_DEINSTALL_NOOP")


def run(archive, output):
    if os.uname().sysname != "FreeBSD" or os.uname().machine != "amd64" or os.geteuid() != 0:
        raise Refusal("ONLY_DISPOSABLE_ROOT_FREEBSD_AMD64")
    ver = execute(["freebsd-version", "-u"])
    if ver.returncode or not ver.stdout.startswith("15.1-") or not Path("/usr/bin/lockf").is_file():
        raise Refusal("FREEBSD_15_1_NATIVE_LOCKF_REQUIRED")
    hooks = load_old_hooks(archive)
    with tempfile.TemporaryDirectory(prefix="stage0-archived-hooks-fd9-") as temp:
        scenarios = verify(fixture(temp, hooks))
        report = dict(status="PASS_ARCHIVED_HOOKS_REAL_FD9",
                      archive_sha256=SHA,
                      hook_sha256={p: hashlib.sha256(x.encode()).hexdigest() for p, x in hooks.items()},
                      scenarios=scenarios, actual_historical_hook_bodies=True,
                      real_freebsd_lockf=True, old_service_actual=False,
                      configd_and_signals_mocked=True, actual_pkg_transaction=False,
                      opnsense_native_acceptance=False, stage0_closed=False)
        output.write_text(json.dumps(report, sort_keys=True))
    return scenarios


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--archive", required=True, type=Path)
    p.add_argument("--json", required=True, type=Path)
    a = p.parse_args()
    try:
        scenarios = run(a.archive, a.json)
        print("STAGE0_HISTORICAL_FD9=PASS:" + ",".join(scenarios))
        return 0
    except Refusal as e:
        print("STAGE0_HISTORICAL_FD9=NOT_VERIFIED:" + str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
