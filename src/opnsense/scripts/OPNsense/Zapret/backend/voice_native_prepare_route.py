#!/usr/bin/env python3
"""Operator-only ORIGINAL FD9 native Voice PREPARED route.

This is NOT a configd/GUI/boot command. The existing zapret_service.sh
holds lockf FD9. One original Config inode flock is acquired here and held
until the existing initial-owner, five-previous-resource, release-qualified
schema-4 PREPARED writer has completed. No process/kernel/active runtime
changes are authorized. Detached source input uses fixed root-only paths:
the normal orchestrator's voice-native-candidate (8 exact files), shared
managed IPSET and ordinary Strategies plus an isolated installable runtime.
The producer of that detached input is still an explicitly open Stage-3 task.
"""
from __future__ import annotations

import fcntl
import os
from pathlib import Path
import pwd
import re
import stat
import sys

from voice_cutover_backup import _private_dir
from voice_cutover_journal import VoiceCutoverJournal
from voice_firewall_ledger import VoiceOwnershipStore
from voice_ipfw_adapter import FreeBSDIPFWAdapter
from voice_native_kernel_argv import FreeBSDKernelArgvReader, SYSTEM_PATHS
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_freebsd_process_security import FreeBSDProcessSecurityReader, FIELDS
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS, PIDFILES, _locked_config
from voice_native_prepare_one_lock import prepare_native_voice_one_lock
import voice_ipfw_runtime as native

INPUT = Path("/var/db/zapret2/voice-operator-input")
FILES = ("config.xml", "user-traffic.conf", "tcp-ports.txt", "udp-ports.txt")
DIRS = ("runtime", "voice-native-candidate", "managed")
_ALLOWED_WAN = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,63}$")


class NativePrepareRouteError(RuntimeError):
    pass


def _fixed_input() -> dict[str, Path]:
    """Do not accept CLI paths, unknown sibling files or symlink children."""
    _private_dir(INPUT)
    if set(os.listdir(INPUT)) != set(FILES + DIRS):
        raise NativePrepareRouteError("detached Voice source layout is incomplete or foreign")
    for name in FILES + DIRS:
        path = INPUT / name
        info = os.lstat(path)
        if info.st_uid != os.geteuid() or info.st_mode & 0o077 or (
            stat.S_ISREG(info.st_mode) and (
                info.st_nlink != 1 or info.st_size > 128 * 1048576
            )
        ) or (
            (name in FILES and not stat.S_ISREG(info.st_mode)) or
            (name in DIRS and not stat.S_ISDIR(info.st_mode))
        ):
            raise NativePrepareRouteError("detached Voice source must be private and regular")
    return {name: INPUT / name for name in FILES + DIRS}


def _expected_credentials() -> dict[str, dict[str, int]]:
    """No process-derived credential adoption: fixed root and installed nobody."""
    nobody = pwd.getpwnam("nobody")
    uid, gid = nobody.pw_uid, nobody.pw_gid
    if not 1 <= uid < 1 << 32 or not 1 <= gid < 1 << 32:
        raise NativePrepareRouteError("invalid installed nobody identity")
    return {
        role: {field: (uid if field.endswith("uid") else gid) if role == "engine" else 0
               for field in FIELDS}
        for role in ("engine", "daemon", "monitor")
    }


def prepare_operator_prebuilt(physical_wan: str, divert_port: int) -> dict:
    if not isinstance(physical_wan, str) or not _ALLOWED_WAN.fullmatch(physical_wan) or (
        type(divert_port) is not int or not 1 <= divert_port <= 65535
    ):
        raise NativePrepareRouteError("invalid resolved WAN or divert port")
    native.require_native_lock()
    paths = _fixed_input()
    # Do not create the ledger/whole directories for invalid operator input.
    for directory in (native.WHOLE.parent, native.WHOLE, native.LEDGER):
        _private_dir(directory)
    journal = VoiceCutoverJournal(native.WHOLE)
    ledger = VoiceOwnershipStore(native.LEDGER)
    probe = FreeBSDVoiceProcessProbe(
        EXPECTED_SCRIPTS, PIDFILES, native.WHOLE / "previous",
    )
    security = FreeBSDProcessSecurityReader(
        EXPECTED_SCRIPTS, SYSTEM_PATHS, _expected_credentials(), probe,
    )
    fd = os.open(native.CONFIG, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        owner = (os.geteuid(), os.getegid())
        native.require_native_lock()
        _locked_config(native.CONFIG, fd, owner)
        result = prepare_native_voice_one_lock(
            journal=journal, ledger=ledger,
            config_path=native.CONFIG, active_runtime=native.ACTIVE_ROOT,
            source_config=paths["config.xml"], source_runtime=paths["runtime"],
            release_dir=paths["voice-native-candidate"],
            managed_source=paths["managed"],
            ordinary_source=paths["user-traffic.conf"],
            tcp_ports=paths["tcp-ports.txt"], udp_ports=paths["udp-ports.txt"],
            physical_wan=physical_wan, divert_port=divert_port,
            probe=probe, kernel_reader=FreeBSDKernelArgvReader(),
            security_reader=security, ipfw_adapter=FreeBSDIPFWAdapter(19000,19010),
            config_fd=fd, config_owner=owner,
            require_lifecycle_owner=native.require_native_lock,
        )
        native.require_native_lock()
        _locked_config(native.CONFIG, fd, owner)
        if result["state"] != "native-voice-original-lock-prepared" or (
            result["safe_to_enable_voice"] is not False
            or result["public_voice_apply"] is not False
        ):
            raise NativePrepareRouteError("native PREPARED not sealed")
        return result
    finally:
        os.close(fd)


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[0] != "prepare-prebuilt":
        print("usage: voice_native_prepare_route.py prepare-prebuilt RESOLVED_WAN DIVERT_PORT",
              file=sys.stderr)
        return 64
    if not argv[2].isdecimal():
        return 64
    try:
        report = prepare_operator_prebuilt(argv[1], int(argv[2]))
        if report["state"] != "native-voice-original-lock-prepared":
            raise NativePrepareRouteError("prepared state not verified")
        print("native-voice-prepared=sealed")
        print("native-voice-public-apply=disabled")
        return 0
    except (OSError, ValueError, RuntimeError, KeyError):
        print("ERROR: native Voice preparation refused; inspect rollback/owner evidence",
              file=sys.stderr)
        return 69


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
