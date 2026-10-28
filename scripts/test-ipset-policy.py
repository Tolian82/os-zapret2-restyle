#!/usr/bin/env python3
"""Stage 1 dual-stack and full-family guards (no live OPNsense mutation)."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

MODULE = Path(__file__).resolve().parent.parent / "src/opnsense/scripts/OPNsense/Zapret/backend/ipset_policy.py"
spec = importlib.util.spec_from_file_location("ipset_policy", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class PolicyTests(unittest.TestCase):
    def test_ipv4_compat_order_host_dedup(self):
        text, proof = mod.parse_ipset(b"91.108.0.0/16\n91.108.13.10/32\n91.108.13.10\n", "Telegram")
        self.assertEqual(text, "91.108.0.0/16\n91.108.13.10\n")
        self.assertEqual(proof["family_counts"], {"ipv4": 2, "ipv6": 0})

    def test_ipv6_hosts_and_double_colon(self):
        text, proof = mod.parse_ipset(b"::\n::/128\n2001:DB8::1/128\n2001:db8::1\n", "IPv6")
        self.assertEqual(text, "::\n2001:db8::1\n")
        self.assertEqual(proof["family_counts"]["ipv6"], 2)

    def test_exclude_collapse_and_hash(self):
        raw = b"192.0.2.128/25\n2001:db8:abcd::1\n192.0.2.0/25\n2001:db8:abcd::/48\n"
        text, proof = mod.parse_ipset(raw, "Exclude IPSet", collapse=True)
        self.assertEqual(text, "192.0.2.0/24\n2001:db8:abcd::/48\n")
        self.assertEqual(proof["sha256"], hashlib.sha256(text.encode()).hexdigest())

    def test_each_list_rejects_full_family_and_pairs(self):
        for name in mod.LISTS:
            for raw in ("0.0.0.0/0", "::/0", "0.0.0.0/1\n128.0.0.0/1",
                        "::/1\n8000::/1"):
                with self.subTest(name=name, raw=raw):
                    with self.assertRaises(mod.IPSetError):
                        mod.parse_ipset(raw.encode(), name, collapse=name == "exclude")

    def test_malformed_and_host_bits(self):
        for entry in ("not-host", "https://example.org", "192.0.2.2/24",
                      "2001:db8::1/64", "fe80::1%vtnet1", "192.0.2.1-192.0.2.4",
                      "::ffff:192.0.2.4", "192.0.2.1/33", "2001:db8::/129"):
            with self.subTest(entry=entry), self.assertRaises(mod.IPSetError):
                mod.parse_ipset(entry.encode(), "Sample")

    def test_readonly_inspect_uses_same_semantics_and_family_overlap(self):
        raw = {name: "" for name in mod.LISTS}
        raw["telegram"] = "91.108.0.0/16\n2001:db8:0:1::/64\n"
        raw["discord"] = "91.108.13.10\n2001:db8:2::/48\n"
        raw["exclude"] = "192.0.2.0/25\n192.0.2.128/25\n::\n"
        report = mod.inspect(raw)
        self.assertEqual(report["lists"]["exclude"]["normalized"], "192.0.2.0/24\n::")
        self.assertEqual(report["lists"]["telegram"]["family_counts"]["ipv6"], 1)
        self.assertIn(["telegram", "discord"], report["overlaps"])
        self.assertNotIn(["telegram", "exclude"], report["overlaps"])
        import json
        outcome = subprocess.run(
            [sys.executable, str(MODULE), "inspect"], input=json.dumps(raw),
            capture_output=True, text=True, check=False
        )
        self.assertEqual(outcome.returncode, 0, outcome.stderr)
        self.assertEqual(json.loads(outcome.stdout), report)
        self.assertEqual(list(json.loads(outcome.stdout)["lists"]), list(mod.LISTS))
        for name in mod.LISTS:
            broken = dict(raw)
            broken[name] = "::/1\n8000::/1"
            with self.subTest(name=name), self.assertRaises(mod.IPSetError):
                mod.inspect(broken)

    def test_limits(self):
        with self.assertRaises(mod.IPSetError):
            mod.parse_ipset(b"1" * (mod.MAX_BYTES + 1), "large")
        with self.assertRaises(mod.IPSetError):
            mod.parse_ipset(b"\n" * (mod.MAX_ENTRIES + 1), "many")

    def test_atomic_invalid_batch_and_determinism(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            inputs = base / "input"; inputs.mkdir()
            managed = base / "managed"; managed.mkdir()
            manifest = base / "ipset-manifest.json"
            for name in mod.LISTS:
                (inputs / (name + ".txt")).write_text("192.0.2.5\n")
            (inputs / "exclude.txt").write_text("2001:db8::/32\n")
            mod.batch(inputs, managed, manifest)
            first = manifest.read_bytes()
            self.assertEqual(json.loads(first)["schema_version"], 1)
            self.assertIn("ipv6", json.loads(first)["lists"]["exclude"]["union"])
            mod.batch(inputs, managed, manifest)
            self.assertEqual(first, manifest.read_bytes())
            existing = {f.name: f.read_bytes() for f in managed.iterdir()}
            (inputs / "sip.txt").write_text("::/1\n8000::/1\n")
            with self.assertRaises(mod.IPSetError):
                mod.batch(inputs, managed, manifest)
            self.assertEqual(existing, {f.name: f.read_bytes() for f in managed.iterdir()})
            self.assertEqual(first, manifest.read_bytes())

    def test_compat_cli_and_failure_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = Path(tmp) / "in"; out = Path(tmp) / "out"
            inp.write_text("::\n192.0.2.1\n")
            result = subprocess.run([sys.executable, str(MODULE), "single", str(inp), str(out), "check"],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(out.read_text(), "::\n192.0.2.1\n")
            inp.write_text("192.0.2.1\n192.0.2.2/24\n")
            result = subprocess.run([sys.executable, str(MODULE), "single", str(inp), str(out), "check"],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("check, line 2", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
