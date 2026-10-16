#!/usr/bin/env python3
"""OPNsense GUI XML and original template-rendered zapret.conf must agree."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"))
from voice_native_saved_pair_guard import require_saved_pair, SavedPairError, SCALARS, BLOCKS, SERVICES


def make_pair(directory: Path) -> tuple[Path, Path]:
    root = ET.Element("opnsense")
    zapret = ET.SubElement(ET.SubElement(root, "OPNsense"), "Zapret")
    general = ET.SubElement(zapret, "general")
    for key, value in (("enabled", "1"), ("waninterface", "vtnet1"), ("divertport", "989")):
        ET.SubElement(general, key).text = value
    strategy = ET.SubElement(zapret, "strategy")
    ET.SubElement(strategy, "trafficargs").text = "--filter-tcp=443\n--filter-l7=tls"
    ET.SubElement(strategy, "extraargs").text = "--dpi-desync=fake"
    hostlist = ET.SubElement(zapret, "hostlist")
    ET.SubElement(hostlist, "mode").text = "ipset"
    ET.SubElement(hostlist, "telegramips").text = "91.108.13.10\n91.108.0.0/16"
    voice = ET.SubElement(zapret, "voice")
    telegram = ET.SubElement(voice, "telegram")
    ET.SubElement(telegram, "enabled").text = "1"
    xml = directory / "config.xml"
    ET.ElementTree(root).write(xml, encoding="utf-8")
    lines = ["# original OPNsense template"]
    for name, path, _ in SCALARS:
        node = zapret.find(path)
        text = node.text if node is not None else ""
        lines.append(name + '="' + (text or "") + '"')
    for name, path in BLOCKS:
        node = zapret.find(path)
        text = node.text if node is not None else ""
        marker = "__ZAPRET_" + name + "__"
        lines.extend([name + "=$(cat <<'" + marker + "'", text or "", marker, ")"])
    for service in SERVICES:
        lines.append("VOICE_" + service.upper() + '_REQUESTED="' +
                     ("1" if service == "telegram" else "0") + '"')
    config = directory / "zapret.conf"
    config.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return xml, config


class SavedPairTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="voice-pair-")
        self.addCleanup(tmp.cleanup)
        self.xml, self.conf = make_pair(Path(tmp.name))

    def test_real_template_fields_agree(self):
        require_saved_pair(self.xml, self.conf)

    def test_reject_wrong_voice_enable_before_generating(self):
        self.conf.write_text(self.conf.read_text().replace(
            'VOICE_TELEGRAM_REQUESTED="1"', 'VOICE_TELEGRAM_REQUESTED="0"'
        ))
        with self.assertRaisesRegex(SavedPairError, "Voice enable"):
            require_saved_pair(self.xml, self.conf)

    def test_reject_stale_wan_or_divert(self):
        for source, replacement in (('WAN_IF="vtnet1"', 'WAN_IF="vtnet2"'),
                                     ('DIVERT_PORT="989"', 'DIVERT_PORT="990"')):
            old = self.conf.read_text()
            self.conf.write_text(old.replace(source, replacement))
            with self.assertRaises(SavedPairError):
                require_saved_pair(self.xml, self.conf)
            self.conf.write_text(old)

    def test_reject_different_strategy_or_hostlist(self):
        for old, new in (("--filter-tcp=443", "--filter-tcp=80"),
                         ("91.108.0.0/16", "1.1.1.1/32")):
            original = self.conf.read_text()
            self.conf.write_text(original.replace(old, new))
            with self.assertRaises(SavedPairError):
                require_saved_pair(self.xml, self.conf)
            self.conf.write_text(original)

    def test_reject_foreign_extra_shell_assignments(self):
        original = self.conf.read_text()
        self.conf.write_text(original + 'WAN_IF="vtnet1"\n')
        with self.assertRaises(SavedPairError):
            require_saved_pair(self.xml, self.conf)

    def test_reject_dtd_and_ambiguous_saved_field(self):
        original = self.xml.read_bytes()
        self.xml.write_bytes(b'<!DOCTYPE opnsense [<!ENTITY x SYSTEM "file:///etc/passwd">]>' + original)
        with self.assertRaises(SavedPairError):
            require_saved_pair(self.xml, self.conf)
        self.xml.write_bytes(original.replace(b"<enabled>1</enabled>",
                                              b"<enabled>1</enabled><enabled>1</enabled>", 1))
        with self.assertRaises(SavedPairError):
            require_saved_pair(self.xml, self.conf)


if __name__ == "__main__":
    unittest.main(verbosity=2)
