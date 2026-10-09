#!/usr/bin/env python3
"""Read only the persisted Voice configuration from native OPNsense config.xml.

This is a staging adapter, NOT an Apply action or a second runtime authority.
It reads the same on-disk model nodes managed by the OPNsense GUI and never
changes config.xml. The resulting JSON is input for the fail-closed compiler.
No access to unrelated Squid, pfSense, user or credential settings is needed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import xml.etree.ElementTree as ET

SERVICES = ("telegram", "discord", "x", "sip", "custom")


class VoiceModelError(ValueError):
    pass


def read_voice_model(xml_source: Path) -> dict:
    # Use the exact OPNsense/Zapret mount. Do not search for similarly named
    # keys elsewhere in config.xml (other plugins may have Voice settings).
    try:
        root = ET.parse(xml_source).getroot()
    except ET.ParseError as exc:
        raise VoiceModelError(f"invalid OPNsense XML: {exc}") from exc
    node = root.find("./OPNsense/Zapret")
    if node is None and root.tag == "OPNsense":
        node = root.find("./Zapret")
    if node is None:
        raise VoiceModelError("OPNsense/Zapret model is missing")

    def scalar(path: str, default: str = "") -> str:
        value = node.find(path)
        return default if value is None or value.text is None else value.text

    wan = scalar("./general/waninterface").strip()
    voice_wan = scalar("./voice/waninterface").strip()
    fields: dict[str, dict] = {}
    for name in SERVICES:
        enabled = scalar(f"./voice/{name}/enabled", "0").strip()
        if enabled not in ("0", "1"):
            raise VoiceModelError(f"voice.{name}.enabled: expected 0 or 1")
        fields[name] = {
            "enabled": enabled == "1",
            "args": scalar(f"./voice/{name}/args"),
            # Telegram is intentionally shared with ordinary Strategies.
            # Additional IPSETs live under the same hostlist model branch.
            "ips": scalar(f"./hostlist/{name}ips"),
        }
    return {
        "strategy_wan": wan,
        "voice_wan": voice_wan,
        "services": fields,
    }


def main(args: list[str]) -> int:
    if len(args) != 3:
        print("usage: voice_model_export.py CONFIG.XML CANDIDATE.json", file=sys.stderr)
        return 64
    xml_source, output_path = Path(args[1]), Path(args[2])
    try:
        state = read_voice_model(xml_source)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=output_path.parent,
            prefix=".voice-model.", delete=False
        ) as temporary:
            candidate = Path(temporary.name)
            os.chmod(candidate, 0o600)
            json.dump(state, temporary, ensure_ascii=False, indent=2)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(candidate, output_path)
        return 0
    except (OSError, VoiceModelError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
