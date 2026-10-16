#!/usr/bin/env python3
"""Read-only saved Voice model and candidate preview under the common FD9 owner.

There is exactly one common Voice+Strategies Apply journal. Neither old PoC
cutover roots nor private Voice IPFW journals can authorize this route.
The inspector never changes Config, runtime, processes or kernel IPFW.
"""
from __future__ import annotations

import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import xml.etree.ElementTree as ET

from shared_apply_operation import native_lifecycle_gate
from voice_ipfw_adapter import require_lifecycle_lock
from voice_profile_compiler import compile_candidate

SERVICES = ("telegram", "discord", "x", "sip", "custom")
MAX_CONFIG = 128 * 1048576


class VoiceLifecycleRouteError(RuntimeError):
    pass


CONFIG = Path("/conf/config.xml")


def _pinned_regular(path: Path, fd: int, *, owner: tuple[int, int]) -> os.stat_result:
    """Read only the locked original Config inode, never follow a replacement."""
    by_path, opened = os.lstat(path), os.fstat(fd)
    if (not stat.S_ISREG(by_path.st_mode) or
        not stat.S_ISREG(opened.st_mode) or
        by_path.st_nlink != 1 or opened.st_nlink != 1 or
        (by_path.st_dev, by_path.st_ino) != (opened.st_dev, opened.st_ino) or
        (opened.st_uid, opened.st_gid) != owner):
        raise VoiceLifecycleRouteError("unsafe or replaced native Config inode")
    return opened


def _locked_config(path: Path, fd: int, owner: tuple[int, int]) -> None:
    _pinned_regular(path, fd, owner=owner)
    # A separate open must contend with the caller's original exclusive flock.
    probe = os.open(path, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
    try:
        try:
            fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno not in (errno.EWOULDBLOCK, errno.EAGAIN):
                raise
        else:
            fcntl.flock(probe, fcntl.LOCK_UN)
            raise VoiceLifecycleRouteError("OPNsense Config exclusive flock not held")
    finally:
        os.close(probe)


def _shared_gate(whole_root: Path) -> dict:
    # whole_root is a historical argument retained for independent callers;
    # only the adjacent COMMON journal is read, never old cutover evidence.
    return native_lifecycle_gate("common-apply", root=whole_root.with_name("shared-apply"))



def _read_saved_config(config_path: Path, fd: int, owner: tuple[int, int],
                       *, include_candidate: bool = False) -> dict:
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
    candidate_profiles = {}
    hostlists = model.findall("./hostlist") if include_candidate else []
    if len(hostlists) > 1:
        raise VoiceLifecycleRouteError("duplicate managed hostlist model")
    hostlist = hostlists[0] if hostlists else None
    for service in SERVICES:
        matches = v.findall(service) if v is not None else []
        if len(matches) > 1:
            raise VoiceLifecycleRouteError("duplicate Voice profile")
        requested = unique(matches[0], "enabled", "0") if matches else "0"
        if requested not in ("0", "1"):
            raise VoiceLifecycleRouteError("invalid saved Voice profile enablement")
        profiles[service] = requested == "1"
        if include_candidate:
            candidate_profiles[service] = {
                "enabled": profiles[service],
                "args": unique(matches[0], "args") if matches else "",
                "ips": unique(hostlist, service + "ips") if hostlist is not None else "",
            }
    result = {
        "global_enabled": enabled == "1",
        "saved_voice_profiles": profiles,
        "saved_voice_on": any(profiles.values()),
        "wan_matches": not voice_wan or voice_wan == main_wan,
    }
    if include_candidate:
        result["_candidate"] = {
            "strategy_wan": main_wan,
            "voice_wan": voice_wan,
            "services": candidate_profiles,
        }
    return result


def inspect_lifecycle(config_path: Path, whole_root: Path, ledger_root: Path,
                      *, config_fd: int, config_owner: tuple[int, int],
                      require_lifecycle_owner) -> dict:
    """One FD9/Config-flock read-only policy decision; no implicit activation."""
    require_lifecycle_owner()
    _locked_config(config_path, config_fd, config_owner)
    pending = _shared_gate(whole_root)
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
    if _shared_gate(whole_root) != pending:
        raise VoiceLifecycleRouteError("shared Apply journal changed during lifecycle inspect")
    if saved["saved_voice_on"] and not saved["global_enabled"]:
        state = "voice-saved-on-global-service-off"
    elif saved["saved_voice_on"] and not saved["wan_matches"]:
        state = "voice-saved-on-wan-mismatch"
    elif saved["saved_voice_on"]:
        state = "voice-saved-on-common-apply-configured"
    else:
        state = "voice-saved-off-common-apply-available"
    return {
        "state": state,
        **saved,
        "safe_to_mutate": False,
        "safe_to_enable_voice": False,
        "public_voice_apply": False,
    }


def inspect_candidate(config_path: Path, whole_root: Path, ledger_root: Path,
                      *, config_fd: int, config_owner: tuple[int, int],
                      require_lifecycle_owner) -> dict:
    """Bridge the locked saved model to the EXISTING pure compiler.

    Do not make another path-based/unlocked config.xml read. This only
    proves syntax and deterministic profile planning; it does not stage
    files, observe the running engine, prepare journals or authorize Apply.
    """
    status = inspect_lifecycle(
        config_path, whole_root, ledger_root, config_fd=config_fd,
        config_owner=config_owner,
        require_lifecycle_owner=require_lifecycle_owner,
    )
    if status["state"] != "voice-saved-on-common-apply-configured":
        return {
            "state": "native-voice-candidate-not-eligible",
            "reason": status["state"],
            "safe_to_enable_voice": False,
            "public_voice_apply": False,
        }
    saved = _read_saved_config(
        config_path, config_fd, config_owner, include_candidate=True,
    )
    if saved["saved_voice_profiles"] != status["saved_voice_profiles"] or (
        saved["global_enabled"] is not True or not saved["wan_matches"]
    ):
        raise VoiceLifecycleRouteError("saved Voice selection changed")
    # Exactly the same absolute candidate IPSET path used by the existing
    # inactive release-stage compiler. No filesystem writes are performed.
    profile, plan = compile_candidate(
        saved["_candidate"], Path("/usr/local/etc/zapret2/runtime-v2/managed"),
    )
    if not profile or not plan["profiles"]:
        raise VoiceLifecycleRouteError("enabled Voice has no compiled profiles")
    require_lifecycle_owner()
    _locked_config(config_path, config_fd, config_owner)
    if _shared_gate(whole_root) != {
        "state": "clear", "safe_to_mutate": True,
    }:
        raise VoiceLifecycleRouteError("common Apply journal changed during candidate compilation")
    return {
        "state": "native-voice-candidate-syntax-qualified",
        "profile_count": len(plan["profiles"]),
        "services": [item["service"] for item in plan["profiles"]],
        "profile_sha256": hashlib.sha256(profile.encode("utf-8")).hexdigest(),
        "plan_sha256": hashlib.sha256(json.dumps(
            plan, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")).hexdigest(),
        "safe_to_enable_voice": False,
        "public_voice_apply": False,
    }


def main(argv: list[str]) -> int:
    if argv not in (["inspect"], ["candidate-preflight"]):
        print("usage: voice_native_lifecycle_router.py {inspect|candidate-preflight}", file=sys.stderr)
        return 64
    fd = None
    try:
        require_lifecycle_lock()
        fd = os.open(CONFIG, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
        _pinned_regular(CONFIG, fd, owner=(0, 0))
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        arguments = dict(
            config_fd=fd, config_owner=(0, 0),
            require_lifecycle_owner=require_lifecycle_lock,
        )
        route = inspect_lifecycle if argv == ["inspect"] else inspect_candidate
        result = route(
            CONFIG, Path("/var/db/zapret2/shared-apply"), Path("/var/db/zapret2/shared-apply"), **arguments,
        )
        prefix = "native-voice-lifecycle=" if argv == ["inspect"] else "native-voice-candidate="
        print(prefix + json.dumps(
            result, sort_keys=True, separators=(",", ":"),
        ))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print("ERROR: native Voice candidate/lifecycle preflight refused", file=sys.stderr)
        return 69
    finally:
        if fd is not None:
            os.close(fd)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
