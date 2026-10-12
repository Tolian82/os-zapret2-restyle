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

from voice_native_legacy_poc_guard import NativePrepareRouteError, _legacy_read

SERVICES = ("telegram", "discord", "x", "sip", "custom")
OLD_PROFILE = "telegram-voice-poc"
OLD_STATE = "telegram-voice-poc.state"


class VoiceMigrationError(ValueError):
    pass


def _read_old_poc_file(path: Path) -> bytes | None:
    """Reuse the native Apply no-follow/ownership/inode guard for PoC evidence.

    This read-only assessment is never an authorization for live migration.
    The real cutover must reobserve under FD9 and the original Config flock.
    """
    try:
        return _legacy_read(path)
    except NativePrepareRouteError as exc:
        raise VoiceMigrationError("unsafe or changing legacy PoC file") from exc


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
    # The old telegram_voice.sh tests -f, not marker contents. A present
    # regular marker (including an empty marker) explicitly requests ON.
    if active.is_symlink():
        raise VoiceMigrationError("legacy runtime root is unsafe")
    marker_data = _read_old_poc_file(marker)
    old_request = "on" if marker_data is not None else "unknown-after-reboot"
    state_data = _read_old_poc_file(active / OLD_STATE)
    if state_data is None:
        old_runtime = "unknown"
    elif state_data in (b"enabled", b"enabled\n"):
        old_runtime = "on"
    elif state_data in (b"disabled", b"disabled\n"):
        old_runtime = "off"
    else:
        raise VoiceMigrationError("legacy runtime state is invalid")
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
        # Production native PREPARED refuses ANY active legacy PoC; do not
        # advertise staging as feasible before the reviewed cutover exists.
        may_stage = False
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
