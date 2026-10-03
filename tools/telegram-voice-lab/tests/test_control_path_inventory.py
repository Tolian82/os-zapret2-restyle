#!/usr/bin/env python3
"""Offline safeguards for the separate read-only topology inventory."""
from pathlib import Path
import re
import subprocess
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "run-control-inventory-opnsense.sh"

class ControlInventoryTests(unittest.TestCase):
    def test_shell_parses(self):
        subprocess.run(["/bin/sh", "-n", str(SCRIPT)], check=True)

    def test_read_only_and_privacy_contract(self):
        text = SCRIPT.read_text()
        # No live media test, route changes, Docker startup or VPN enablement.
        self.assertNotRegex(text, r"(?m)^\s*(?:ip (?:-4 )?route (?:add|replace|del)|docker (?:run|start)|configctl .*enable|tailscale (?:up|set)|wg set)\b")
        self.assertIn("independent_same_endpoint_media_path=UNVERIFIED", text)
        self.assertIn("CURRENT_OPNSENSE_BASELINE_CHANGED", text)
        self.assertIn("INDEPENDENT_PATH=NOT_VALIDATED", text)
        self.assertIn("-o StrictHostKeyChecking=yes", text)
        self.assertNotIn("/conf/config.xml", text)
        self.assertIn("sha256 -q", text)
        self.assertIn("REMOTE_INVENTORY", text)
        self.assertIn("tgvoice-lab", text)

    def test_remote_heredoc_parses_and_contains_only_inventory(self):
        text = SCRIPT.read_text()
        m = re.search(r"<<'REMOTE_INVENTORY'\n(.*?)\nREMOTE_INVENTORY\n", text, re.DOTALL)
        self.assertIsNotNone(m)
        remote = m.group(1)
        subprocess.run(["/bin/sh", "-n"], input=remote, text=True, check=True)
        self.assertNotRegex(remote, r"(?m)^\s*(?:ip .*route (?:replace|add|del)|.*(?:tailscale up|wg set|docker start|docker run))\b")
        self.assertIn('from "$SRC"', remote)
        self.assertIn('via 192.168.1.2 dev ovs_eth1', remote)
        self.assertIn('CURRENT_BASELINE_READ_ONLY_PASS', remote)
        self.assertNotIn("192.168.1.140 dev", remote)

if __name__ == "__main__":
    unittest.main()
