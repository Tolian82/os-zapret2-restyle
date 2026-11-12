#!/usr/bin/env python3
"""P5b1 import-only native validator for a PREBUILT private candidate.

The original orchestrator must build the candidate before this adapter runs.
This calls the EXISTING validator.sh functions and installed dvtws2 --dry-run;
it neither compiles native strategy grammar nor owns FD9/Apply/IPFW/Config.
Not an authenticated GUI or public configd endpoint.
"""
from __future__ import annotations

import os
from pathlib import Path
import platform
import re
import signal
import stat
import subprocess
import sys

PREVIEW_ROOT = Path("/tmp")
CANDIDATE_NAME = re.compile(r"zapret-p5b-[a-f0-9]{16}\Z")
ENGINE_ROOT = Path("/usr/local/etc/zapret2")
MODULE_ROOT = Path(__file__).resolve().parent
MAX_FILE = 8 * 1024 * 1024
MAX_TOTAL = 32 * 1024 * 1024
MAX_OUTPUT = 4096
TIMEOUT = 24

# No untrusted path interpolated into scripts. Every location is positional.
CHECK_MAPPED = r'''
set -eu
. "$1/common.sh"
. "$1/ports.sh"
. "$1/validator.sh"
validator_validate_build_mapped "$2" "$3" "$4" "$5" "$6" "$7" "$8"
'''
CHECK_ENGINE = r'''
set -eu
. "$1/common.sh"
. "$1/validator.sh"
validator_validate_engine_mapped "$2" "$3" "$4" "$5" "$6"
'''


class NativePreviewRefused(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _secure(path: Path, *, directory: bool, owner: int,
            maximum: int = MAX_FILE) -> os.stat_result:
    try:
        info = path.lstat()
    except OSError as exc:
        raise NativePreviewRefused("PRIVATE_CANDIDATE_MISSING") from exc
    if not (stat.S_ISDIR(info.st_mode) if directory else
            stat.S_ISREG(info.st_mode) and info.st_nlink == 1):
        raise NativePreviewRefused("PRIVATE_CANDIDATE_TYPE_UNSAFE")
    if info.st_uid != owner or info.st_mode & 0o022:
        raise NativePreviewRefused("PRIVATE_CANDIDATE_OWNER_UNSAFE")
    if not directory and (not 0 <= info.st_size <= maximum):
        raise NativePreviewRefused("PRIVATE_CANDIDATE_SIZE_UNSAFE")
    return info


def _private_candidate(work: Path, owner: int) -> dict[str, Path]:
    """No write or auto-create. Caller must have built a disposable release."""
    work = Path(work)
    if not work.is_absolute() or work.parent != PREVIEW_ROOT or (
        not CANDIDATE_NAME.fullmatch(work.name)
    ):
        raise NativePreviewRefused("PRIVATE_PREVIEW_ROOT_INVALID")
    root = _secure(work, directory=True, owner=owner)
    if stat.S_IMODE(root.st_mode) != 0o700:
        raise NativePreviewRefused("PRIVATE_PREVIEW_NOT_PRIVATE")
    release = work / "release"
    _secure(release, directory=True, owner=owner)
    _secure(release / "managed", directory=True, owner=owner)
    files = {
        "args": release / "dvtws.args",
        "traffic": release / "traffic-user.conf",
        "tcp": release / "tcp-ports.txt",
        "udp": release / "udp-ports.txt",
    }
    total = 0
    for key, path in files.items():
        info = _secure(path, directory=False, owner=owner)
        total += info.st_size
        if key == "args" and info.st_size == 0:
            raise NativePreviewRefused("PRIVATE_ARGS_EMPTY")
    if total > MAX_TOTAL:
        raise NativePreviewRefused("PRIVATE_CANDIDATE_TOO_LARGE")
    return {"release": release, **files}


def _execute(script: str, args: list[str], env: dict[str, str]) -> int:
    """Kill ONLY our dedicated child process group on outer timeout.

    The native validator already applies its own 15 second engine timeout.
    Never forward stderr/stdout: it may contain user strategy data.
    """
    proc = subprocess.Popen(
        ["/bin/sh", "-c", script, "p5b-native", *args],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, env=env, start_new_session=True,
    )
    try:
        proc.wait(timeout=TIMEOUT)
    except subprocess.TimeoutExpired as exc:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
        raise NativePreviewRefused("PRIVATE_VALIDATOR_TIMEOUT") from exc
    return proc.returncode


def validate_private_release(
    work: Path, *,
    native: bool = True,
    static_root: Path = ENGINE_ROOT,
    module_root: Path = MODULE_ROOT,
    runner=_execute,
    check_lock=None,
    owner: int | None = None,
) -> dict[str, object]:
    """Validate prebuilt private release only; never stage Config or Apply.

    Injection parameters are solely for unit tests; no production CLI exposes
    them. The live branch pins module, binary and ref roots and requires FD9.
    """
    if owner is None:
        owner = os.geteuid()
    if native:
        if platform.system() != "FreeBSD" or os.geteuid() != 0 or (
            Path(static_root) != ENGINE_ROOT or Path(module_root) != MODULE_ROOT
        ):
            raise NativePreviewRefused("NATIVE_OWNER_OR_ROOT_REFUSED")
        from voice_ipfw_adapter import require_lifecycle_lock
        check_lock = require_lifecycle_lock
    if not callable(check_lock):
        raise NativePreviewRefused("NATIVE_LIFECYCLE_GUARD_MISSING")
    check_lock()
    entries = _private_candidate(work, owner)
    static_root = Path(static_root)
    module_root = Path(module_root)
    _secure(static_root, directory=True, owner=owner)
    _secure(module_root / "validator.sh", directory=False, owner=owner)
    _secure(module_root / "common.sh", directory=False, owner=owner)
    _secure(module_root / "ports.sh", directory=False, owner=owner)
    engine = static_root / "binaries/my/dvtws2"
    reference = static_root / "runtime-v2"
    if not reference.is_absolute() or reference == entries["release"]:
        raise NativePreviewRefused("NATIVE_REFERENCE_ROOT_INVALID")
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin:/sbin:/usr/sbin",
        "LANG": "C", "LC_ALL": "C",
        "SCRIPT_DIR": str(module_root.parent),
        "BACKEND_DIR": str(module_root),
        "PYTHON_RUNTIME": sys.executable,
    }
    args = [
        str(module_root),
        str(entries["args"]), str(entries["traffic"]),
        str(entries["tcp"]), str(entries["udp"]),
        str(static_root), str(reference), str(entries["release"]),
    ]
    check_lock()
    if runner(CHECK_MAPPED, args, env) != 0:
        check_lock()
        return _report("native_mapped_validation_failed", "not_run")
    check_lock()
    try:
        _secure(engine, directory=False, owner=owner)
        installed = os.access(engine, os.X_OK)
    except NativePreviewRefused:
        installed = False
    if not installed:
        check_lock()
        return _report("native_mapped_valid", "unavailable")
    engine_args = [
        str(module_root), str(engine), str(entries["args"]),
        str(reference), str(entries["release"]), sys.executable,
    ]
    dry_run_code = runner(CHECK_ENGINE, engine_args, env)
    check_lock()
    return _report("native_mapped_valid",
                   "passed" if dry_run_code == 0 else "failed")


def _report(mapped: str, engine: str) -> dict[str, object]:
    return {
        "schema": "p5b1-private-native-validator-v1",
        "mapped_validation": mapped,
        "engine_native_dry_run": engine,
        "effective_lifecycle_state": "not_attested",
        "saved_config_changed": "not_measured_by_adapter",
        "ipfw_fd9_process_voice_resources": "not_measured_by_adapter",
        "real_network_bypass": "not_tested",
        "safe_to_apply": False,
        "public_preview_action": False,
    }
