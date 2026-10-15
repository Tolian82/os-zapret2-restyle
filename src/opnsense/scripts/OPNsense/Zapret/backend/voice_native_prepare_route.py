#!/usr/bin/env python3
"""Operator-only ORIGINAL FD9 native Voice PREPARED route.

This is NOT a configd/GUI/boot command. The existing zapret_service.sh
holds lockf FD9. One original Config inode flock is acquired here and held
until the existing initial-owner, five-previous-resource, release-qualified
schema-4 PREPARED writer has completed. No process/kernel/active runtime
changes are authorized. Detached source input uses fixed root-only paths:
the normal orchestrator's voice-native-candidate (8 exact files), shared
managed IPSET and ordinary Strategies plus an isolated installable runtime.
The historical route only prepares sealed evidence and cannot activate
Config/runtime/IPFW. Its input remains operator-supplied and is not a GUI
Apply route; normal ON/OFF uses the shared Voice/Strategies Apply.
"""
from __future__ import annotations

import fcntl
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

from voice_cutover_backup import _private_dir
from voice_cutover_checkpoint import _private_dir as _ensure_private_dir
from voice_cutover_journal import VoiceCutoverJournal
from voice_firewall_ledger import VoiceOwnershipStore
from voice_ipfw_adapter import FreeBSDIPFWAdapter
from voice_native_kernel_argv import FreeBSDKernelArgvReader, SYSTEM_PATHS
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_freebsd_process_security import FreeBSDProcessSecurityReader, expected_native_process_credentials as _expected_credentials
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS, PIDFILES, _locked_config
from voice_native_prepare_one_lock import prepare_native_voice_one_lock
from voice_native_operator_input_stage import stage_native_operator_input
from voice_native_saved_pair_guard import require_saved_pair
from voice_native_saved_draft_candidate import prepare_saved_draft_candidate
from voice_native_legacy_poc_guard import NativePrepareRouteError, _require_no_legacy_poc
import voice_ipfw_runtime as native

INPUT = Path("/var/db/zapret2/voice-operator-input")
BUILD_INPUT = Path("/var/db/zapret2/voice-build-input")
BUILD_ENTRIES = frozenset(("config.xml", "release"))
SAVED_ENTRIES = frozenset(("config.xml", "zapret.conf"))
BUILT_ENTRIES = frozenset(("config.xml", "zapret.conf", "release", ".voice-build-workspace"))
BUILD_WORKER = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/voice_native_build_release.sh")
RENDER_WORKER = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/voice_native_render_saved.sh")
XML_ONLY_ENTRIES = frozenset(("config.xml",))
RENDERED_ENTRIES = frozenset(("config.xml", "zapret.conf", ".voice-template-root"))
BUILT_XML_ENTRIES = frozenset((*BUILT_ENTRIES, ".voice-template-root"))
FILES = ("config.xml", "user-traffic.conf", "tcp-ports.txt", "udp-ports.txt")
DIRS = ("runtime", "voice-native-candidate", "managed")
_ALLOWED_WAN = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,63}$")


def _fixed_input() -> dict[str, Path]:
    """Do not accept CLI paths, unknown sibling files or symlink children."""
    _private_dir(INPUT)
    if set(os.listdir(INPUT)) != set(FILES + DIRS):
        raise NativePrepareRouteError("detached Voice source layout is incomplete or foreign")
    for name in FILES + DIRS:
        path = INPUT / name
        info = os.lstat(path)
        # The outer 0700 input remains private. Only the inner
        # installable runtime root requires 0755 for the nobody engine.
        install_root = name == "runtime" and stat.S_ISDIR(info.st_mode) and (
            stat.S_IMODE(info.st_mode) == 0o755
        )
        if info.st_uid != os.geteuid() or (
            info.st_mode & 0o077 and not install_root
        ) or (name == "runtime" and not install_root) or (
            stat.S_ISREG(info.st_mode) and (
                info.st_nlink != 1 or info.st_size > 128 * 1048576
            )
        ) or (
            (name in FILES and not stat.S_ISREG(info.st_mode)) or
            (name in DIRS and not stat.S_ISDIR(info.st_mode))
        ):
            raise NativePrepareRouteError("detached Voice source must be private and regular")
    return {name: INPUT / name for name in FILES + DIRS}


def prepare_operator_prebuilt(
    physical_wan: str, divert_port: int, *, from_release: bool = False,
    from_saved: bool = False, from_xml: bool = False,
    from_draft: bool = False, draft_mask: str = "",
    expected_config_sha: str = "",
) -> dict:
    if not isinstance(physical_wan, str) or not _ALLOWED_WAN.fullmatch(physical_wan) or (
        type(divert_port) is not int or not 1 <= divert_port <= 65535
    ):
        raise NativePrepareRouteError("invalid resolved WAN or divert port")
    if sum((bool(from_release), bool(from_saved), bool(from_xml),
            bool(from_draft))) > 1:
        raise NativePrepareRouteError("ambiguous native Voice operator mode")
    native.require_native_lock()
    # Draft-only mode creates the entire fixed input inside the original
    # Config flock. It cannot accept a caller filesystem path or arbitrary XML.
    if from_draft:
        _private_dir(BUILD_INPUT.parent)
        if os.path.lexists(BUILD_INPUT):
            raise NativePrepareRouteError("prior saved-draft source must be inspected")
        if not BUILD_WORKER.is_file() or BUILD_WORKER.is_symlink() or (
            not RENDER_WORKER.is_file() or RENDER_WORKER.is_symlink()
        ):
            raise NativePrepareRouteError("native draft generation workers not installed")
        _ensure_private_dir(native.WHOLE.parent)
    elif from_release or from_saved or from_xml:
        _private_dir(BUILD_INPUT)
        expected = (XML_ONLY_ENTRIES if from_xml else
                    SAVED_ENTRIES if from_saved else BUILD_ENTRIES)
        if set(os.listdir(BUILD_INPUT)) != expected:
            raise NativePrepareRouteError("untrusted detached build input layout")
        if from_saved or from_xml:
            for name in expected:
                candidate = os.lstat(BUILD_INPUT / name)
                if not stat.S_ISREG(candidate.st_mode) or (
                    candidate.st_uid != os.geteuid() or candidate.st_nlink != 1
                    or candidate.st_mode & 0o077 or candidate.st_size > 4 * 1048576
                ):
                    raise NativePrepareRouteError("saved build source must be private regular")
            if not BUILD_WORKER.is_file() or BUILD_WORKER.is_symlink() or (
                from_xml and (not RENDER_WORKER.is_file() or RENDER_WORKER.is_symlink())
            ):
                raise NativePrepareRouteError("native saved XML workers not installed")
        _ensure_private_dir(native.WHOLE.parent)
    else:
        paths = _fixed_input()
        # Preserve the earlier fail-before-journal behavior for bad input.
        for directory in (native.WHOLE.parent, native.WHOLE, native.LEDGER):
            _ensure_private_dir(directory)
    fd = os.open(native.CONFIG, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        owner = (os.geteuid(), os.getegid())
        native.require_native_lock()
        _locked_config(native.CONFIG, fd, owner)
        _require_no_legacy_poc()
        if from_draft:
            result = prepare_saved_draft_candidate(
                config_path=native.CONFIG, destination=BUILD_INPUT,
                mask=draft_mask, expected_sha=expected_config_sha,
                config_fd=fd, config_owner=owner,
                require_lifecycle_owner=native.require_native_lock,
            )
            if result.get("state") != "native-voice-private-saved-draft-xml" or (
                result.get("safe_to_enable_voice") is not False
                or result.get("public_voice_apply") is not False
            ):
                raise NativePrepareRouteError("GUI saved OFF draft was not privately sealed")
            if set(os.listdir(BUILD_INPUT)) != XML_ONLY_ENTRIES:
                raise NativePrepareRouteError("native draft source has foreign files")
        if from_xml or from_draft:
            # Render with OPNsense's OWN template engine and alternate
            # private target root; the active config files are NEVER touched.
            native.require_native_lock()
            _locked_config(native.CONFIG, fd, owner)
            try:
                subprocess.run(
                    ["/bin/sh", str(RENDER_WORKER)], check=True, timeout=60,
                    pass_fds=tuple(sorted({9, fd})),
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                raise NativePrepareRouteError("detached OPNsense template rendering failed") from exc
            native.require_native_lock()
            _locked_config(native.CONFIG, fd, owner)
            if set(os.listdir(BUILD_INPUT)) != RENDERED_ENTRIES:
                raise NativePrepareRouteError("detached OPNsense renderer left foreign files")
            rendered_stat = os.lstat(BUILD_INPUT / "zapret.conf")
            if not stat.S_ISREG(rendered_stat.st_mode) or (
                rendered_stat.st_uid != os.geteuid() or rendered_stat.st_nlink != 1
                or rendered_stat.st_mode & 0o077 or rendered_stat.st_size > 4 * 1048576
            ):
                raise NativePrepareRouteError("detached template output is not private/regular")
            _private_dir(BUILD_INPUT / ".voice-template-root")
        if from_saved or from_xml or from_draft:
            # A saved candidate XML and the OPNsense template output MUST
            # describe the same generation, not two separate GUI saves.
            require_saved_pair(BUILD_INPUT / "config.xml", BUILD_INPUT / "zapret.conf")
            native.require_native_lock()
            _locked_config(native.CONFIG, fd, owner)
            # The parent holds original FD9 and the original Config flock
            # throughout this child. The worker sources the same existing
            # orchestrator modules; it cannot launch or install the runtime.
            require_lock = native.require_native_lock
            require_lock()
            _locked_config(native.CONFIG, fd, owner)
            try:
                subprocess.run(
                    ["/bin/sh", str(BUILD_WORKER)],
                    check=True, timeout=180,
                    pass_fds=tuple(sorted({9, fd})),
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                raise NativePrepareRouteError("native detached orchestrator build failed") from exc
            require_lock()
            _locked_config(native.CONFIG, fd, owner)
            if set(os.listdir(BUILD_INPUT)) != (
                BUILT_XML_ENTRIES if (from_xml or from_draft) else BUILT_ENTRIES
            ):
                raise NativePrepareRouteError("native release build left unexpected artifacts")
        if from_release or from_saved or from_xml or from_draft:
            result = stage_native_operator_input(
                config_path=native.CONFIG,
                source_config=BUILD_INPUT / "config.xml",
                staged_release=BUILD_INPUT / "release",
                destination=INPUT, physical_wan=physical_wan,
                divert_port=divert_port, config_fd=fd,
                config_owner=owner,
                require_lifecycle_owner=native.require_native_lock,
            )
            if result.get("state") != "native-voice-detached-operator-input-published" or (
                result.get("safe_to_enable_voice") is not False
                or result.get("public_voice_apply") is not False
            ):
                raise NativePrepareRouteError("native detached release not sealed")
            paths = _fixed_input()
            for directory in (native.WHOLE, native.LEDGER):
                _ensure_private_dir(directory)
        journal = VoiceCutoverJournal(native.WHOLE)
        ledger = VoiceOwnershipStore(native.LEDGER)
        probe = FreeBSDVoiceProcessProbe(
            EXPECTED_SCRIPTS, PIDFILES, native.WHOLE / "previous",
        )
        security = FreeBSDProcessSecurityReader(
            EXPECTED_SCRIPTS, SYSTEM_PATHS, _expected_credentials(), probe,
        )
        native.require_native_lock()
        _locked_config(native.CONFIG, fd, owner)
        _require_no_legacy_poc()
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
        # Historical PREPARED output is never a second runtime/Config Apply.
        return result
    finally:
        os.close(fd)


def main(argv: list[str]) -> int:
    draft_actions = ("prepare-from-draft",)
    if not argv or (
        (argv[0] in draft_actions and len(argv) != 5) or
        (argv[0] not in draft_actions and len(argv) != 3)
    ) or argv[0] not in (
        "prepare-prebuilt", "prepare-from-release", "prepare-from-saved",
        "prepare-from-xml", *draft_actions,
    ):
        print("usage: voice_native_prepare_route.py {prepare-prebuilt|prepare-from-release|prepare-from-saved|prepare-from-xml|prepare-from-draft} RESOLVED_WAN DIVERT_PORT [FIVE_BIT_MASK BASE_CONFIG_SHA256]",
              file=sys.stderr)
        return 64
    if not argv[2].isdecimal():
        return 64
    try:
        report = prepare_operator_prebuilt(
            argv[1], int(argv[2]),
            from_release=argv[0] == "prepare-from-release",
            from_saved=argv[0] == "prepare-from-saved",
            from_xml=argv[0] == "prepare-from-xml",
            from_draft=argv[0] in draft_actions,
            draft_mask=argv[3] if len(argv) == 5 else "",
            expected_config_sha=argv[4] if len(argv) == 5 else "",
        )
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
