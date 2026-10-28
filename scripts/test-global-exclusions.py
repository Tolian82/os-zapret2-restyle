#!/usr/bin/env python3
"""Stage 3 regression: exact final dvtws2 arguments with mixed-family exclusion."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

from global_exclusions import ExclusionError, compose, audit, segments
from ipset_policy import LISTS, parse_ipset


class GlobalExclusionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="global-exclude-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.release = self.root / "candidate"
        self.managed = self.release / "managed"
        self.managed.mkdir(parents=True)
        self.upstream = self.root / "upstream"
        self.upstream.mkdir()
        self.ref = Path("/usr/local/etc/zapret2/runtime-v2")
        self.domain_ref = str(self.ref / "managed/hostlist-exclude.txt")
        self.ip_ref = str(self.ref / "managed/ipset-exclude.txt")
        self.domain = self.managed / "hostlist-exclude.txt"
        self.ipset = self.managed / "ipset-exclude.txt"
        self.domain.write_text("unmodified.example\n", encoding="utf-8")
        manifest = {"schema_version": 1, "lists": {}}
        for name in LISTS:
            raw = "2001:db8:aaaa::/48\n198.51.100.0/24\n" if name == "exclude" else (
                "91.108.0.0/16\n" if name == "telegram" else ""
            )
            text, proof = parse_ipset(raw.encode(), name, collapse=name == "exclude")
            (self.managed / f"ipset-{name}.txt").write_text(text)
            manifest["lists"][name] = proof
        (self.release / "ipset-manifest.json").write_text(json.dumps(manifest))
        self.kw = (self.domain, self.domain_ref, self.ipset, self.ip_ref,
                   self.ref, self.release, self.upstream)

    def render(self, text):
        return compose(text, *self.kw)

    def test_first_middle_last_voice_and_hostless(self):
        raw = ("\n".join([
            "--port=989", "--filter-tcp=443", "--filter-l7=tls",
            "--new", "--name=voice-telegram",
            "--ipset=" + str(self.ref / "managed/ipset-telegram.txt"),
            "--filter-udp=*", "--filter-l7=stun", "--payload=stun",
            "--new", "--filter-udp=596-599", "--filter-l7=unknown",
            # Legacy generator mistakenly bound Exclude Domains to LAST only.
            "--hostlist-exclude=" + self.domain_ref, ""]))
        result = self.render(raw)
        profiles = segments(result)
        self.assertEqual(len(profiles), 3)
        for profile in profiles:
            self.assertEqual(profile.count("--ipset-exclude=" + self.ip_ref), 1)
        self.assertIn("--hostlist-exclude=" + self.domain_ref, profiles[0])
        self.assertNotIn("--hostlist-exclude=" + self.domain_ref, profiles[1])
        self.assertNotIn("--hostlist-exclude=" + self.domain_ref, profiles[2])
        self.assertEqual(result, self.render(result))
        audit(result, *self.kw)

    def test_templates_named_new_and_import_are_both_protected(self):
        raw = "\n".join([
            "--port=989", "--template=base", "--hostlist=/some/hostlist.txt",
            "--filter-l7=tls", "--new=name1", "--import=base",
            "--filter-tcp=443", "--new", "--filter-udp=443",
            "--filter-l7=quic", "--new", "--filter-udp=50000-50100",
            "--filter-l7=unknown",
        ])
        result = self.render(raw)
        rows = segments(result)
        self.assertEqual(len(rows), 4)
        self.assertTrue(rows[1][0] == "--new=name1")
        for row in rows:
            self.assertEqual(row.count("--ipset-exclude=" + self.ip_ref), 1)
        self.assertIn("--hostlist-exclude=" + self.domain_ref, rows[1])
        self.assertIn("--hostlist-exclude=" + self.domain_ref, rows[2])
        self.assertNotIn("--hostlist-exclude=" + self.domain_ref, rows[3])
        self.assertEqual(self.render(result), result)

    def test_empty_global_ipset_does_not_affect_profiles(self):
        self.ipset.write_text("")
        manifest = json.loads((self.release / "ipset-manifest.json").read_text())
        _, manifest["lists"]["exclude"] = parse_ipset(b"", "exclude")
        (self.release / "ipset-manifest.json").write_text(json.dumps(manifest))
        result = self.render("--port=989\n--filter-udp=443\n--filter-l7=quic\n")
        self.assertNotIn("--ipset-exclude=", result)
        self.assertIn("--hostlist-exclude=" + self.domain_ref, result)

    def test_user_inline_full_family_never_reaches_apply(self):
        cases = [
            "--ipset-ip=0.0.0.0/0",
            "--ipset-ip=::/0",
            "--ipset-ip=0.0.0.0/1,128.0.0.0/1",
            "--ipset-ip=::/1,8000::/1",
            "--ipset-exclude-ip=0.0.0.0/0",
            "--ipset-exclude-ip=::/1,8000::/1",
            "--ipset-ip=2001:db8::1/64",
            "--ipset-ip=fe80::1%vtnet1",
        ]
        for native in cases:
            with self.subTest(native=native), self.assertRaises(ExclusionError):
                self.render("--port=989\n--filter-tcp=443\n" + native + "\n")

    def test_external_ipset_file_and_union_are_validated_by_canonical_parser(self):
        file = self.upstream / "custom-ips.txt"
        file.write_text("0.0.0.0/1\n128.0.0.0/1\n")
        with self.assertRaises(ExclusionError):
            self.render("--filter-tcp=443\n--ipset=" + str(file))
        file.write_text("2001:db8::/32\n")
        result = self.render("--filter-tcp=443\n--ipset=" + str(file))
        self.assertIn("--ipset-exclude=" + self.ip_ref, result)
        with self.assertRaises(ExclusionError):
            self.render("--filter-tcp=443\n--ipset=/tmp/unverified-list.txt")

    def test_missing_or_redirected_domain_exclusion_is_never_ignored(self):
        self.domain.unlink()
        with self.assertRaisesRegex(ExclusionError, "missing domain"):
            self.render("--filter-tcp=443\n--filter-l7=tls")
        self.domain.symlink_to(self.upstream / "other-hostlist.txt")
        with self.assertRaisesRegex(ExclusionError, "domain/IP exclusion"):
            self.render("--filter-tcp=443\n--filter-l7=tls")

    def test_manifest_drift_and_template_cycle_fail_closed(self):
        self.ipset.write_text("192.0.2.0/24\n")
        with self.assertRaisesRegex(ExclusionError, "manifest mismatch"):
            self.render("--filter-tcp=443")
        self.ipset.write_text("2001:db8:aaaa::/48\n198.51.100.0/24\n")
        for raw in (
            "--template=a\n--import=b\n--new\n--template=b\n--import=a\n--new\n--filter-tcp=443",
            "--import=missing\n--filter-tcp=443",
            "--filter-tcp=443\n--new\n",
        ):
            with self.subTest(raw=raw), self.assertRaises(ExclusionError):
                self.render(raw)

    def test_user_hostlist_exclude_never_enters_voice_or_stun(self):
        for head in ("--name=voice-telegram", "--filter-l7=stun"):
            with self.subTest(head=head), self.assertRaisesRegex(
                ExclusionError, "hostlist exclusions forbidden"
            ):
                self.render(head + "\n--filter-udp=*\n--hostlist-exclude=/unverified/path\n")

    def test_cli_apply_audit_and_fail_closed(self):
        argv_file = self.root / "dvtws.args"
        argv_file.write_text("--port=989\n--filter-tcp=443\n--filter-l7=tls\n")
        base = [sys.executable, str(BACKEND / "global_exclusions.py")]
        arguments = [str(argv_file), *[str(arg) for arg in self.kw]]
        for action, expected in (("audit", 1), ("apply", 0), ("audit", 0)):
            result = subprocess.run([*base, action, *arguments],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, expected, result.stderr)
        self.assertIn("--ipset-exclude=" + self.ip_ref, argv_file.read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
