#!/usr/bin/env python3
"""P5b2a: import-only disposable native candidate build/validate coordinator.

This is NOT the public P5 endpoint. The caller must supply a complete, already
model-validated detached <opnsense> XML candidate. No Apply Config writer, new
strategy grammar, persistent operation record or service action exists here.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import platform
import re
import secrets
import shutil
import signal
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET

import shared_apply_render
from strategy_preview_native import validate_private_release

TEMP_ROOT = Path("/tmp")
BACKEND_ROOT = Path(__file__).resolve().parent
SCRIPT_ROOT = BACKEND_ROOT.parent
STATIC_ROOT = Path("/usr/local/etc/zapret2")
CONFIG = Path("/conf/config.xml")
MAX_XML = 16 * 1024 * 1024
RUN_TIMEOUT = 80
MAX_CAPTURE = 2 * 1024 * 1024
MODULES = (
    "common", "config", "parser", "registry", "storage", "targets",
    "target_mode", "profile_normalizer", "profile_pipeline", "exclude",
    "blobs", "ports", "firewall", "generator", "validator", "atomic",
    "stage", "launcher", "supervisor", "orchestrator", "apply_runtime",
)
# The same production modules as zapret_service.sh, without loading its
# command dispatcher or any mutation entrypoint. Only the declared work dir
# and stage file may be created by the original builder.
BUILD_SH = r'''
set -eu
SCRIPT_DIR="$1"
BACKEND_DIR="$2"
ZAPRET_DIR="$3"
ACTIVE_DIR="$ZAPRET_DIR/runtime-v2"
WORK="$4"
PYTHON_RUNTIME="$SCRIPT_DIR/python_runtime.sh"
STAGE_FILE="$WORK/build-stage.status"
RULE_BASE=19000
RULE_MAX=19010
DIVERT_PORT=989
for module in common config parser registry storage targets target_mode profile_normalizer profile_pipeline exclude blobs ports firewall generator validator atomic stage launcher supervisor orchestrator apply_runtime
do
    . "$BACKEND_DIR/$module.sh"
done
orchestrator_build_release \
    "$WORK/templates/usr/local/etc/zapret2/zapret.conf" \
    "$ZAPRET_DIR" "$ACTIVE_DIR" "$WORK" "$WORK/release" \
    "$STAGE_FILE" shared-candidate "$WORK/candidate.xml"
'''


class PrivateBuildRefused(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _checked_xml(data: bytes) -> None:
    if not isinstance(data, bytes) or not 0 < len(data) <= MAX_XML:
        raise PrivateBuildRefused("CANDIDATE_XML_SIZE_INVALID")
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise PrivateBuildRefused("CANDIDATE_XML_ENTITY_REFUSED")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise PrivateBuildRefused("CANDIDATE_XML_INVALID") from None
    if root.tag != "opnsense" or len(root.findall("OPNsense")) != 1 or (
        len(root.findall("./OPNsense/Zapret")) != 1
    ):
        raise PrivateBuildRefused("CANDIDATE_XML_MODEL_INVALID")


def _new_private_root() -> Path:
    # No arbitrary paths, shared-work operation IDs, or symlink-based reuse.
    for _ in range(4):
        work = TEMP_ROOT / ("zapret-p5b-" + secrets.token_hex(8))
        try:
            work.mkdir(mode=0o700)
        except FileExistsError:
            continue
        if stat.S_IMODE(work.lstat().st_mode) != 0o700 or work.is_symlink():
            raise PrivateBuildRefused("PRIVATE_ROOT_CREATION_UNSAFE")
        return work
    raise PrivateBuildRefused("PRIVATE_ROOT_COLLISION")


def _write_candidate(work: Path, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(work / "candidate.xml", flags, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)


def _run_builder(work: Path) -> None:
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin:/sbin:/usr/sbin",
        "LANG": "C", "LC_ALL": "C",
    }
    command = ["/bin/sh", "-c", BUILD_SH, "p5b2a-build",
               str(SCRIPT_ROOT), str(BACKEND_ROOT), str(STATIC_ROOT),
               str(work)]
    # An installed runtime source may contain user content in its diagnostics.
    # Discard it entirely rather than echoing a profile or private Config.
    try:
        proc = subprocess.Popen(
            command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, env=env, start_new_session=True)
        try:
            code = proc.wait(timeout=RUN_TIMEOUT)
        except subprocess.TimeoutExpired as exc:
            # Never leave the shell's grandchildren running on a timeout.
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
            raise PrivateBuildRefused("ORIGINAL_BUILDER_TIMEOUT") from None
    except OSError as exc:
        raise PrivateBuildRefused("ORIGINAL_BUILDER_UNAVAILABLE") from None
    if code:
        raise PrivateBuildRefused("ORIGINAL_BUILDER_REFUSED")


def _digest_file(path: Path) -> str:
    # Physical Config is read-only; symlinks are never resolved.
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_XML:
                raise PrivateBuildRefused("LIVE_CONFIG_UNSAFE")
            data = bytearray()
            while len(data) <= MAX_XML:
                block = os.read(fd, 65536)
                if not block:
                    break
                data.extend(block)
            if len(data) > MAX_XML:
                raise PrivateBuildRefused("LIVE_CONFIG_SIZE_UNSAFE")
            return hashlib.sha256(data).hexdigest()
        finally:
            os.close(fd)
    except OSError as exc:
        raise PrivateBuildRefused("LIVE_CONFIG_READ_UNAVAILABLE") from None


def _native_snapshot() -> dict[str, object]:
    """Narrow native no-mutation tripwires, NOT full A11 semantic proof.

    A later P5b2b witness must additionally qualify full process/Voice,
    owned/foreign IPFW tables and permanent resource equivalence on a VM.
    """
    def read_only(argv: list[str]) -> tuple[int, str]:
        try:
            result = subprocess.run(
                argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, timeout=5, check=False,
                env={"PATH": "/usr/local/bin:/usr/bin:/bin:/sbin:/usr/sbin",
                     "LANG": "C", "LC_ALL": "C"},
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise PrivateBuildRefused("NATIVE_SNAPSHOT_UNAVAILABLE") from None
        if len(result.stdout) > MAX_CAPTURE:
            raise PrivateBuildRefused("NATIVE_SNAPSHOT_TOO_LARGE")
        return result.returncode, hashlib.sha256(result.stdout).hexdigest()

    return {
        "config_sha": _digest_file(CONFIG),
        "ipfw_rules": read_only(["/sbin/ipfw", "-q", "list"]),
        # Native table metadata is independent of packet counters.
        "ipfw_tables": read_only(["/sbin/ipfw", "table", "all", "list"]),
        # No ps PID census yet: it would include our short-lived subprocesses.
        "runtime_inode": _runtime_stat(STATIC_ROOT / "runtime-v2"),
    }


def _runtime_stat(root: Path) -> tuple[str, int, int, int]:
    try:
        info = root.lstat()
    except FileNotFoundError:
        return ("absent", 0, 0, 0)
    if not stat.S_ISDIR(info.st_mode):
        raise PrivateBuildRefused("ACTIVE_RUNTIME_TYPE_UNSAFE")
    return ("directory", info.st_ino, info.st_mtime_ns, info.st_ctime_ns)


def preview_prepared_xml(
    candidate: bytes, *,
    native: bool = True,
    lock_check=None,
    snapshot=None,
    render=None,
    build=None,
    validator=None,
) -> dict[str, object]:
    """No public CLI/API. Dependency callbacks allowed ONLY for unit tests.

    In production the original FD9 and installed renderer/validator paths are
    mandatory. Even a successful candidate is discarded immediately.
    """
    _checked_xml(candidate)
    if native:
        if platform.system() != "FreeBSD" or os.geteuid() != 0 or any(
            callback is not None for callback in
            (lock_check, snapshot, render, build, validator)
        ):
            raise PrivateBuildRefused("NATIVE_OWNER_OR_OVERRIDE_REFUSED")
        from voice_ipfw_adapter import require_lifecycle_lock
        lock_check = require_lifecycle_lock
        snapshot = _native_snapshot
        render = lambda work: shared_apply_render.render_detached(
            work / "candidate.xml", work / "templates", owner=0)
        build = _run_builder
        validator = lambda work: validate_private_release(work, native=True)
    else:
        if not all(callable(x) for x in
                   (lock_check, snapshot, render, build, validator)):
            raise PrivateBuildRefused("TEST_DEPENDENCIES_REQUIRED")
    lock_check()
    before = snapshot()
    work = None
    result = None
    operation_error = None
    try:
        work = _new_private_root()
        _write_candidate(work, candidate)
        lock_check()
        render(work)
        lock_check()
        build(work)
        lock_check()
        result = validator(work)
    except Exception as exc:
        operation_error = exc
    finally:
        cleanup_error = False
        if work is not None:
            try:
                shutil.rmtree(work)
                cleanup_error = work.exists() or work.is_symlink()
            except OSError:
                cleanup_error = True
        # The native FD9 guard must still be true even on every error path.
        lock_check()
        after = snapshot()
        if cleanup_error:
            raise PrivateBuildRefused("PRIVATE_WORKSPACE_CLEANUP_FAILED")
        if before != after:
            raise PrivateBuildRefused("LIVE_STATE_CHANGED_DURING_PREVIEW")
    if operation_error is not None:
        if isinstance(operation_error, PrivateBuildRefused):
            raise operation_error
        # Never leak private XML, hostlists, generated args or process output.
        raise PrivateBuildRefused("PRIVATE_BUILD_OR_VALIDATION_REFUSED") from None
    if not isinstance(result, dict) or result.get("safe_to_apply") is not False:
        raise PrivateBuildRefused("VALIDATOR_REPORT_UNTRUSTED")
    return {
        "schema": "p5b2a-disposable-original-build-v1",
        "native_validation": result,
        "workspace_cleaned": True,
        "pre_post_narrow_snapshot_equal": True,
        "full_p5_semantic_witness": "not_run",
        "public_preview_action": False,
        "safe_to_apply": False,
    }
