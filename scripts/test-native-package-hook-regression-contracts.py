#!/usr/bin/env python3
"""Offline falsification contracts for Stage 2.26 actual native pkg hooks."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "native_hook_mock", HERE / "test-native-package-hook-regression.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class NativePackageHookContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "pkg").mkdir()
        (self.root / "VERSION").write_text("0.6.2\n")
        (self.root / "Makefile").write_text("PLUGIN_REVISION=    82\n")
        (self.root / "compatibility.json").write_text(json.dumps(
            {"supported_platforms": [{"freebsd_pkg_abi": "FreeBSD:15:amd64"}]}))
        self.source = {}
        for name, phase in m.HOOKS.items():
            body = ('#!/bin/sh\n'
                    '# ' + phase + '\n'
                    'printf "%s\\n" ' + phase + '\n').encode()
            (self.root / "pkg" / name).write_bytes(body)
            self.source[name] = body
        self.version, self.abi = m.identity(self.root)
        self.manifest = {
            "name": m.NAME,
            "version": self.version,
            "abi": self.abi,
            "arch": "freebsd:15:x86:64",
            "origin": "opnsense/os-zapret2-restyle",
            "scripts": {
                phase: self.source[name].replace(b"%", b"%25")[:-1].decode()
                for name, phase in m.HOOKS.items()
            }
        }

    def test_manifest_exact_real_source_bodies(self):
        self.assertEqual(self.version, "0.6.2_82")
        self.assertEqual(
            m.verify_hook_bodies(self.manifest, self.root, self.version, self.abi),
            self.source)

    def test_missing_extra_or_altered_hook_refused_before_execution(self):
        cases = [
            ("altered-script", lambda q: q["scripts"].__setitem__(
                "pre-install", q["scripts"]["pre-install"] + " exit 0")),
            ("missing-phase", lambda q: q["scripts"].pop("post-deinstall")),
            ("extra-phase", lambda q: q["scripts"].__setitem__("pre-upgrade", "x")),
            ("non-string", lambda q: q["scripts"].__setitem__("pre-install", None)),
            ("wrong-package", lambda q: q.__setitem__("name", "other-package")),
            ("wrong-abi", lambda q: q.__setitem__("abi", "FreeBSD:16:amd64")),
            ("wrong-origin", lambda q: q.__setitem__("origin", "foreign")),
        ]
        for label, change in cases:
            with self.subTest(label=label):
                data = json.loads(json.dumps(self.manifest))
                change(data)
                with self.assertRaisesRegex(
                    m.Refusal, "NATIVE_(PACKAGE|MANIFEST)"):
                    m.verify_hook_bodies(data, self.root, self.version, self.abi)

    def test_percent_encoding_exact_and_no_malformed_header(self):
        first = self.root / "pkg" / "+PRE_INSTALL"
        first.write_bytes(b'#!/bin/sh\nprintf "100%25 done\\n"\n')
        good = json.loads(json.dumps(self.manifest))
        good["scripts"]["pre-install"] = (
            first.read_bytes().replace(b"%", b"%25")[:-1].decode())
        self.assertEqual(
            m.verify_hook_bodies(good, self.root, self.version, self.abi)
            ["+PRE_INSTALL"], first.read_bytes())
        first.write_bytes(b'#!/bin/sh\nprintf "broken"\n\n')
        with self.assertRaisesRegex(m.Refusal, "SOURCE_HOOK_BOUNDARY_INVALID"):
            m.verify_hook_bodies(good, self.root, self.version, self.abi)

    def test_filename_and_report_never_claim_pkg_veto(self):
        good_pkg = self.root / (m.NAME + "-" + self.version + ".pkg")
        good_pkg.write_bytes(b"isolated fake bytes, not a real pkg")
        with patch.object(m, "fetch_manifest", return_value=self.manifest), \
             patch.object(m, "execute_mock_regressions", return_value={
                 "mock-only": "MOCK_BEHAVIOR_PASSED"}):
            report = m.run(good_pkg, self.root)
            self.assertTrue(report["source_equals_packaged_hooks"])
            for key in ("native_pkg_replacement_executed",
                        "pre_pkg_admission_enforced", "lh08_ac11_accepted",
                        "owner_appliance_modified"):
                self.assertIs(report[key], False)
            with self.assertRaisesRegex(
                m.Refusal, "NATIVE_PACKAGE_FILENAME_IDENTITY_MISMATCH"):
                other = self.root / "incorrect.pkg"
                other.write_bytes(b"x")
                m.run(other, self.root)

    def test_qualified_abi_is_not_a_synthetic_freebsd_guess(self):
        p = self.root / "compatibility.json"
        p.write_text(json.dumps(
            {"supported_platforms": [{"freebsd_pkg_abi": "FreeBSD:16:amd64"}]}))
        with self.assertRaisesRegex(m.Refusal, "UNQUALIFIED_TARGET_ABI"):
            m.identity(self.root)

    def test_source_only_sandbox_no_pkg_and_isolated_hook_override(self):
        src = (HERE / "test-native-package-hook-regression.py").read_text()
        for key in ("ZAPRET2_TEST_PRE_INSTALL", "ZAPRET2_TEST_PRE_DEINSTALL"):
            # Keys are synthesized from file name; verify test hooks consume them.
            target = "test-package-lifecycle-restart.sh"
            self.assertIn(key, (HERE / target).read_text())
        self.assertIn("PASS_NATIVE_PACKAGE_HOOK_MOCK_REGRESSION_ONLY", src)
        self.assertNotIn('["pkg", "add"', src)
        self.assertNotIn('["pkg", "delete"', src)
        self.assertNotIn('["pkg", "upgrade"', src)


if __name__ == "__main__":
    unittest.main()
