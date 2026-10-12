#!/usr/bin/env python3
"""Operator-only complete read-only legacy Telegram PoC live baseline.

The existing FD9 service owner and original Config inode flock are required.
This joins transient old marker+runtime state, independently pinned managed
Telegram IPv4 file, live three-process kernel argv/image, and exact historical
IPFW rule/table witness. NO legacy authority is removed or adopted. Neither
this module nor its service command writes Config, files, IPFW, or processes.
"""
from __future__ import annotations

import fcntl
import hashlib
import os
from pathlib import Path
import stat
import sys

from voice_native_legacy_poc_guard import _legacy_read
from voice_native_live_preflight import inspect_live_preflight, _owner_dir, DIR, READ
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS, PIDFILES, _locked_config
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_native_kernel_argv import FreeBSDKernelArgvReader
from voice_ipfw_adapter import FreeBSDIPFWAdapter, checked_ipv4, IPFWAdapterError
from voice_cutover_config_restore import _pinned_regular
import voice_ipfw_runtime as native

MAX_MANAGED = 256 * 1024
OLD_STATE = "telegram-voice-poc.state"
MANAGED_DIR = "managed"
MANAGED_NAME = "ipset-telegram.txt"


class LegacyLivePreflightError(RuntimeError):
    pass


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _managed_targets(runtime: Path):
    """Open all three directory/file levels with no symlinks or TOCTOU writes."""
    runtime_fd = os.open(runtime, DIR)
    try:
        root_identity = _owner_dir(runtime_fd)
        on_disk = os.lstat(runtime)
        if (on_disk.st_dev, on_disk.st_ino) != root_identity:
            raise LegacyLivePreflightError("legacy runtime root changed")
        managed_fd = os.open(MANAGED_DIR, DIR, dir_fd=runtime_fd)
        try:
            managed_identity = _owner_dir(managed_fd)
            managed_on_disk = os.stat(MANAGED_DIR, dir_fd=runtime_fd,
                                      follow_symlinks=False)
            if (managed_on_disk.st_dev, managed_on_disk.st_ino) != managed_identity:
                raise LegacyLivePreflightError("legacy managed directory changed")
            file_fd = os.open(MANAGED_NAME, READ, dir_fd=managed_fd)
            try:
                before = os.fstat(file_fd)
                if (not stat.S_ISREG(before.st_mode) or
                    before.st_uid != os.geteuid() or before.st_nlink != 1 or
                    before.st_mode & 0o022 or not 0 < before.st_size <= MAX_MANAGED):
                    raise LegacyLivePreflightError("untrusted managed Telegram IPSET")
                raw = os.read(file_fd, MAX_MANAGED + 1)
                after = os.fstat(file_fd)
                disk = os.stat(MANAGED_NAME, dir_fd=managed_fd,
                               follow_symlinks=False)
                if (_identity(before) != _identity(after) or
                    _identity(after) != _identity(disk) or
                    len(raw) != before.st_size):
                    raise LegacyLivePreflightError("managed Telegram IPSET changed")
            finally:
                os.close(file_fd)
            if (_owner_dir(managed_fd) != managed_identity or
                (os.stat(MANAGED_DIR, dir_fd=runtime_fd,
                         follow_symlinks=False).st_dev,
                 os.stat(MANAGED_DIR, dir_fd=runtime_fd,
                         follow_symlinks=False).st_ino) != managed_identity):
                raise LegacyLivePreflightError("managed directory changed during preflight")
        finally:
            os.close(managed_fd)
        if _owner_dir(runtime_fd) != root_identity:
            raise LegacyLivePreflightError("legacy runtime changed during preflight")
    finally:
        os.close(runtime_fd)
    if any(x not in (10, 13) and not 32 <= x <= 126 for x in raw):
        raise LegacyLivePreflightError("invalid bytes in managed Telegram IPSET")
    try:
        values = [checked_ipv4(line) for line in raw.decode("ascii").splitlines()
                  if line]
    except IPFWAdapterError as exc:
        raise LegacyLivePreflightError("invalid managed Telegram IPv4") from exc
    if not values or len(values) > 4096 or len(set(values)) != len(values):
        raise LegacyLivePreflightError("empty, oversized or duplicate managed IPv4")
    return {"ipv4": tuple(values), "sha256": hashlib.sha256(raw).hexdigest(),
            "file_identity": _identity(before), "runtime_inode": root_identity,
            "managed_inode": managed_identity}


def _old_poc_snapshot(marker: Path, runtime: Path) -> dict:
    if runtime.is_symlink():
        raise LegacyLivePreflightError("legacy runtime is a symlink")
    marker_data = _legacy_read(marker)
    old_data = _legacy_read(runtime / OLD_STATE)
    if marker_data is None or old_data not in (b"enabled", b"enabled\n"):
        raise LegacyLivePreflightError("active legacy Telegram PoC not proven")
    return {
        "marker": (marker_data, _identity(os.lstat(marker))),
        "state": (old_data, _identity(os.lstat(runtime / OLD_STATE))),
        "managed": _managed_targets(runtime),
    }


def inspect_running_legacy_poc(
    *, config_path, active_runtime, legacy_marker, whole_root, ledger_root,
    probe, kernel_reader, ipfw_adapter, config_fd, config_owner,
    require_lifecycle_owner,
) -> dict:
    """Attest pre-migration live PoC with ONE original FD9/Config flock.

    The kernel and old transient inputs are sampled on both sides of verified
    fixed kernel process argv/image. Any inconsistency prevents even a
    read-only 'ready for owner review' diagnostic.
    """
    config_path, active_runtime, legacy_marker = map(
        Path, (config_path, active_runtime, legacy_marker)
    )
    require_lifecycle_owner()
    _locked_config(config_path, config_fd, config_owner)
    _pinned_regular(config_path, config_fd, owner=config_owner)
    first = _old_poc_snapshot(legacy_marker, active_runtime)
    report = inspect_live_preflight(
        config_path=config_path, active_runtime=active_runtime,
        whole_root=whole_root, ledger_root=ledger_root,
        probe=probe, kernel_reader=kernel_reader,
        ipfw_adapter=ipfw_adapter, config_fd=config_fd,
        config_owner=config_owner, require_lifecycle_owner=require_lifecycle_owner,
        legacy_poc_ipv4=first["managed"]["ipv4"],
    )
    require_lifecycle_owner()
    _locked_config(config_path, config_fd, config_owner)
    if _old_poc_snapshot(legacy_marker, active_runtime) != first:
        raise LegacyLivePreflightError("legacy PoC sources changed during live observation")
    if (report["state"] !=
        "live-legacy-poc-process-ipfw-observed-not-readiness" or
        report["kernel_ipfw_legacy_table"] != "present"):
        raise LegacyLivePreflightError("legacy live process/IPFW baseline incomplete")
    return {
        "state": "legacy-poc-full-live-baseline-observed-not-owned",
        "marker": "present", "runtime_state": "enabled",
        "managed_ipv4_sha256": first["managed"]["sha256"],
        "legacy_ipfw_structure_sha256": report["kernel_ipfw_structure_sha256"],
        "legacy_ipfw_previous": report["legacy_ipfw_previous"],
        "active_argument_sha256": report["active_argument_sha256"],
        "instances": report["instances"],
        "kernel_ownership": "not-adopted",
        "durable_previous_backup": False,
        "safe_to_mutate": False, "safe_to_enable_voice": False,
        "public_voice_apply": False, "media_pass": False,
    }


def main(argv: list[str]) -> int:
    if argv != ["inspect"]:
        print("usage: voice_native_legacy_live_preflight.py inspect", file=sys.stderr)
        return 64
    fd = None
    try:
        native.require_native_lock()
        fd = os.open(native.CONFIG, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
        _pinned_regular(native.CONFIG, fd, owner=(0, 0))
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        report = inspect_running_legacy_poc(
            config_path=native.CONFIG, active_runtime=native.ACTIVE_ROOT,
            legacy_marker=native.LEGACY_MARKER,
            whole_root=native.WHOLE, ledger_root=native.LEDGER,
            probe=FreeBSDVoiceProcessProbe(EXPECTED_SCRIPTS, PIDFILES,
                                           native.WHOLE / "previous"),
            kernel_reader=FreeBSDKernelArgvReader(),
            ipfw_adapter=FreeBSDIPFWAdapter(19000, 19010),
            config_fd=fd, config_owner=(0, 0),
            require_lifecycle_owner=native.require_native_lock,
        )
        print("legacy-voice-preflight=" + report["state"])
        print("legacy-voice-ipfw-sha256=" + report["legacy_ipfw_structure_sha256"])
        print("legacy-voice-managed-sha256=" + report["managed_ipv4_sha256"])
        print("legacy-voice-ownership=not-adopted")
        print("voice-on=blocked")
        return 0
    except (OSError, ValueError, RuntimeError):
        print("ERROR: legacy Telegram PoC live evidence is incomplete or unsafe",
              file=sys.stderr)
        return 69
    finally:
        if fd is not None:
            os.close(fd)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
