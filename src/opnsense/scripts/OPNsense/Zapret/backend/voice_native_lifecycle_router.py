#!/usr/bin/env python3
"""Stage-3 read-only Voice Config/journal routing under the EXISTING FD9 owner.

The normal service, not this module, still controls ordinary start/stop.
This is a strictly non-activating bridge from the saved OPNsense XML voice
model to the same native cutover journal authority. There is no Apply command,
no autonomous daemon or boot hook. All results explicitly deny mutation.
"""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import stat
import sys
import xml.etree.ElementTree as ET

from voice_cutover_guard import check_pending
from voice_native_recovery_quiescence import _locked_config
from voice_cutover_config_restore import _pinned_regular
import voice_ipfw_runtime as native

SERVICES = ("telegram", "discord", "x", "sip", "custom")
MAX_CONFIG = 128 * 1048576


class VoiceLifecycleRouteError(RuntimeError):
    pass


def _read_saved_config(config_path: Path, fd: int, owner: tuple[int, int]) -> dict:
    """Snapshot the original locked inode, not a regenerated zapret.conf.

    Refuse malformed/oversized/changed XML, duplicate model tags and
    explicitly invalid Boolean values. Old configurations without a voice
    subtree have five default-OFF profiles, never an assumed Voice ON.
    """
    _locked_config(config_path, fd, owner)
    original = os.fstat(fd)
    if (not stat.S_ISREG(original.st_mode)
            or original.st_size < 1 or original.st_size > MAX_CONFIG):
        raise VoiceLifecycleRouteError("invalid original OPNsense Config size")
    xml = os.pread(fd, original.st_size + 1, 0)
    current = os.fstat(fd)
    if (len(xml) != original.st_size or (
        original.st_dev, original.st_ino, original.st_size,
        original.st_mtime_ns, original.st_ctime_ns
    ) != (
        current.st_dev, current.st_ino, current.st_size,
        current.st_mtime_ns, current.st_ctime_ns
    )):
        raise VoiceLifecycleRouteError("OPNsense Config changed during read")
    # Model settings never require DTDs or entity expansion.
    if b"<!DOCTYPE" in xml.upper() or b"<!ENTITY" in xml.upper():
        raise VoiceLifecycleRouteError("XML DTD is forbidden in native Voice routing")
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise VoiceLifecycleRouteError("invalid OPNsense XML configuration") from exc
    if root.tag != "opnsense":
        raise VoiceLifecycleRouteError("unexpected OPNsense XML root")
    nodes = root.findall("./OPNsense/Zapret")
    if len(nodes) != 1:
        raise VoiceLifecycleRouteError("missing or duplicate Zapret model")
    model = nodes[0]
    general = model.findall("./general")
    if len(general) != 1:
        raise VoiceLifecycleRouteError("invalid Zapret general model")
    voice = model.findall("./voice")
    if len(voice) > 1:
        raise VoiceLifecycleRouteError("duplicate Voice model")
    def unique(parent, key, default=""):
        nodes = parent.findall(key)
        if len(nodes) > 1 or (nodes and list(nodes[0])):
            raise VoiceLifecycleRouteError("duplicate or nested Voice setting")
        return (nodes[0].text or "").strip() if nodes else default
    enabled = unique(general[0], "enabled", "0")
    if enabled not in ("0", "1"):
        raise VoiceLifecycleRouteError("invalid global Zapret switch")
    main_wan = unique(general[0], "waninterface")
    v = voice[0] if voice else None
    voice_wan = unique(v, "waninterface") if v is not None else ""
    profiles = {}
    for service in SERVICES:
        matches = v.findall(service) if v is not None else []
        if len(matches) > 1:
            raise VoiceLifecycleRouteError("duplicate Voice profile")
        requested = unique(matches[0], "enabled", "0") if matches else "0"
        if requested not in ("0", "1"):
            raise VoiceLifecycleRouteError("invalid saved Voice profile enablement")
        profiles[service] = requested == "1"
    return {
        "global_enabled": enabled == "1",
        "saved_voice_profiles": profiles,
        "saved_voice_on": any(profiles.values()),
        "wan_matches": not voice_wan or voice_wan == main_wan,
    }


def inspect_lifecycle(config_path: Path, whole_root: Path, ledger_root: Path,
                      *, config_fd: int, config_owner: tuple[int, int],
                      require_lifecycle_owner) -> dict:
    """One FD9/Config-flock read-only policy decision; no implicit activation."""
    require_lifecycle_owner()
    _locked_config(config_path, config_fd, config_owner)
    pending = check_pending(whole_root, ledger_root)
    if not pending["safe_to_mutate"]:
        # Config can be a partially-written XML prefix after power loss:
        # do not parse it before showing the retained durable journal.
        return {
            "state": "native-transaction-review-required",
            "reason": pending["reason"],
            "saved_voice_on": None,
            "safe_to_mutate": False, "safe_to_enable_voice": False,
            "public_voice_apply": False,
        }
    saved = _read_saved_config(config_path, config_fd, config_owner)
    require_lifecycle_owner()
    _locked_config(config_path, config_fd, config_owner)
    if check_pending(whole_root, ledger_root) != pending:
        raise VoiceLifecycleRouteError("Voice journal changed during lifecycle inspect")
    if saved["saved_voice_on"] and not saved["global_enabled"]:
        state = "voice-saved-on-global-service-off"
    elif saved["saved_voice_on"] and not saved["wan_matches"]:
        state = "voice-saved-on-wan-mismatch"
    elif saved["saved_voice_on"]:
        state = "voice-saved-on-native-apply-not-wired"
    else:
        state = "voice-saved-off-legacy-guard-still-authoritative"
    return {
        "state": state,
        **saved,
        "safe_to_mutate": False,
        "safe_to_enable_voice": False,
        "public_voice_apply": False,
    }


def main(argv: list[str]) -> int:
    if argv != ["inspect"]:
        print("usage: voice_native_lifecycle_router.py inspect", file=sys.stderr)
        return 64
    fd = None
    try:
        native.require_native_lock()
        fd = os.open(native.CONFIG, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
        _pinned_regular(native.CONFIG, fd, owner=(0, 0))
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = inspect_lifecycle(
            native.CONFIG, native.WHOLE, native.LEDGER,
            config_fd=fd, config_owner=(0, 0),
            require_lifecycle_owner=native.require_native_lock,
        )
        print("native-voice-lifecycle=" + json.dumps(
            result, sort_keys=True, separators=(",", ":"),
        ))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print("ERROR: native Voice lifecycle inspect refused: " + str(exc),
              file=sys.stderr)
        return 69
    finally:
        if fd is not None:
            os.close(fd)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
