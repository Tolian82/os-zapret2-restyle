#!/usr/bin/env python3
"""Native process-generation witness rehearsal in a disposable FreeBSD 15.1 VM.

Uses only two owned local sleep processes and temporary PID files; no OPNsense,
Internet, IPFW, dvtws2 engine, packet capture, GUI Apply, or Config changes.
Exercises the *production* baseline controller's process_witness() function.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

GUARD = "ZAPRET2_ISOLATED_FREEBSD_VM_WAN_PROCESS_TEST"
MARKER = "NATIVE_WAN_PROCESS_CONTINUITY"
HERE = Path(__file__).resolve().parent


def require_isolated_freebsd() -> None:
    if (os.getenv(GUARD) != "1" or platform.system() != "FreeBSD"
            or os.geteuid() != 0):
        raise RuntimeError("isolated FreeBSD root opt-in required")
    version = subprocess.run(
        ["/bin/freebsd-version", "-u"], text=True, capture_output=True,
        check=True, timeout=6).stdout.strip()
    if not version.startswith("15.1"):
        raise RuntimeError("isolated FreeBSD 15.1 guest required")
    if not Path("/bin/ps").is_file() or not Path("/bin/sleep").is_file():
        raise RuntimeError("native process tools missing")


def production_controller():
    path = HERE / "stage5-wan-baseline-capture.py"
    if not path.is_file():
        raise RuntimeError("production baseline controller missing")
    spec = importlib.util.spec_from_file_location("native_wan_process_controller", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import production baseline controller")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def spawn_owned_sleep() -> subprocess.Popen:
    return subprocess.Popen(["/bin/sleep", "30"], stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)


def expect_refusal(controller, files, reason: str) -> None:
    try:
        controller.process_witness(pid_files=files)
    except controller.CaptureError:
        return
    raise RuntimeError("native process witness accepted " + reason)


def verify_native_witness(controller) -> None:
    processes = []
    with tempfile.TemporaryDirectory(prefix="zapret2-native-proc-") as tmp:
        root = Path(tmp)
        engine_file, monitor_file = root / "engine.pid", root / "monitor.pid"
        files = (engine_file, monitor_file)
        try:
            engine = spawn_owned_sleep()
            processes.append(engine)
            monitor = spawn_owned_sleep()
            processes.append(monitor)
            engine_file.write_text(str(engine.pid) + "\n", encoding="ascii")
            monitor_file.write_text(str(monitor.pid) + "\n", encoding="ascii")
            first = controller.process_witness(pid_files=files)
            if first != controller.process_witness(pid_files=files):
                raise RuntimeError("unchanged real native process changed witness")
            if (len(first) != 2 or first[0][1] != engine.pid
                    or first[1][1] != monitor.pid or not first[0][2]
                    or not first[1][2]):
                raise RuntimeError("native ps start-time and PID identity mismatch")

            controller.terminate(monitor)
            if monitor.poll() is None:
                raise RuntimeError("first monitor process not terminated")
            expect_refusal(controller, files, "terminated monitor")
            replacement = spawn_owned_sleep()
            processes.append(replacement)
            monitor_file.write_text(str(replacement.pid) + "\n", encoding="ascii")
            changed = controller.process_witness(pid_files=files)
            if changed == first or changed[1][1] != replacement.pid:
                raise RuntimeError("native monitor replacement was not detected")
            if changed != controller.process_witness(pid_files=files):
                raise RuntimeError("new native process changed witness unexpectedly")

            monitor_file.write_text("not-a-pid\n", encoding="ascii")
            expect_refusal(controller, files, "malformed PID")
            monitor_file.unlink()
            monitor_file.symlink_to(engine_file)
            expect_refusal(controller, files, "symlinked PID file")
        finally:
            for proc in reversed(processes):
                controller.terminate(proc)
            if any(proc.poll() is None for proc in processes):
                raise RuntimeError("owned native process survived cleanup")


def main() -> int:
    require_isolated_freebsd()
    verify_native_witness(production_controller())
    print(MARKER + "=PASS: FreeBSD15.1 native PID/start-time, restart, refusal and cleanup")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(MARKER + "=FAIL: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
