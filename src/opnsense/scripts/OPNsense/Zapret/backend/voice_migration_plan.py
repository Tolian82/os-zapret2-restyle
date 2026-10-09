#!/usr/bin/env python3
"""Read-only, explicit legacy Telegram Voice PoC → native Voice migration plan.

Does not change config.xml, old marker, profile, firewall or process.
Migrating a running PoC is a one-way cutover requiring an independently
verified live transaction. Missing transient marker NEVER implies that the
operator explicitly selected OFF; only native persisted checkbox is authority.
"""
from __future__ import annotations

from pathlib import Path
import json
import sys
import xml.etree.ElementTree as ET

SERVICES = ("telegram", "discord", "x", "sip", "custom")
OLD_PROFILE = "telegram-voice-poc"
OLD_STATE = "telegram-voice-poc.state"


class VoiceMigrationError(ValueError):
    pass


def assess(config: Path, marker: Path, active: Path) -> dict:
    root = ET.parse(config).getroot()
    node = root.find("./OPNsense/Zapret")
    if node is None:
        raise VoiceMigrationError("OPNsense/Zapret XML settings are missing")
    voice = node.find("voice")
    # Only a genuine explicit persisted Voice subtree qualifies as a durable
    # preference. A model Default=0 returned by the form is not past intent.
    persistent = voice is not None and any(
        voice.find(f"./{name}/enabled") is not None for name in SERVICES
    )
    selected = {}
    if persistent:
        for name in SERVICES:
            text = voice.findtext(f"./{name}/enabled", "0")
            if text not in ("0", "1"):
                raise VoiceMigrationError(f"invalid persisted {name} Voice selection")
            selected[name] = text == "1"
    else:
        selected = {name: False for name in SERVICES}
    # A path/symlink to some other object is never a trusted marker.
    if marker.is_symlink() or (marker.exists() and not marker.is_file()):
        raise VoiceMigrationError("old PoC marker path is unsafe")
    if not marker.exists():
        old_request = "unknown-after-reboot"
    else:
        if marker.read_text(encoding="utf-8").strip() != "enabled":
            raise VoiceMigrationError("old PoC marker has unexpected content")
        old_request = "on"
    state_file = active / OLD_STATE
    if state_file.is_symlink():
        raise VoiceMigrationError("legacy runtime state is a symlink")
    if state_file.exists():
        state = state_file.read_text(encoding="utf-8").strip()
        if state not in ("enabled", "disabled"):
            raise VoiceMigrationError("legacy runtime state is invalid")
        old_runtime = "on" if state == "enabled" else "off"
    else:
        old_runtime = "unknown"
    if old_request != "on" and old_runtime == "on":
        # Runtime may still have active rules despite missing marker.
        condition = "unresolved-legacy-running"
        may_stage = False
    elif not persistent:
        condition = "operator-selection-required" if old_request == "on" or old_runtime == "on" \
            else "unselected-default-off"
        may_stage = condition == "unselected-default-off"
    elif old_request == "on" or old_runtime == "on":
        condition = "legacy-atomic-cutover-required"
        may_stage = True  # build-only, never activate without atomic handoff
    else:
        condition = "persisted-voice-preference"
        may_stage = True
    return {
        "schema": 1,
        "condition": condition,
        "legacy_request": old_request,
        "legacy_runtime": old_runtime,
        "has_persisted_selection": persistent,
        "services": selected,
        "may_stage_candidate": may_stage,
        "may_activate_without_lifecycle": False,
        "remove_legacy_only_after_confirmed_cutover": True,
    }


def main(args: list[str]) -> int:
    if len(args) != 4:
        print("usage: voice_migration_plan.py CONFIG.XML LEGACY_MARKER ACTIVE_DIR", file=sys.stderr)
        return 64
    try:
        report = assess(Path(args[1]), Path(args[2]), Path(args[3]))
    except (OSError, ValueError, ET.ParseError) as error:
        print(json.dumps({
            "schema": 1, "condition": "invalid-migration-source",
            "may_activate_without_lifecycle": False,
            "error": type(error).__name__
        }, sort_keys=True))
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
