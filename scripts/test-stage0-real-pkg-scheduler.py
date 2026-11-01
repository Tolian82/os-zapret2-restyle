#!/usr/bin/env python3
"""Offline positive/negative contracts; only real FreeBSD VM runs pkg."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location("native", Path(__file__).with_name("stage0-real-pkg-scheduler.py"))
n = importlib.util.module_from_spec(spec)
spec.loader.exec_module(n)


class RealPkgSchedulerContract(unittest.TestCase):
    def test_actual_force_add_skips_old_deinstall_and_explicit_delete_invokes_new(self):
        self.assertEqual(n.EXPECTED_FORCED_ADD,
                         ("old:pre-install", "old:post-install",
                          "new:pre-install", "new:post-install"))
        self.assertNotIn("old:pre-deinstall", n.EXPECTED)
        self.assertNotIn("old:post-deinstall", n.EXPECTED)
        self.assertEqual(n.EXPECTED[-2:],
                         ("new:pre-deinstall", "new:post-deinstall"))
        self.assertTrue(n.check_trace(list(n.EXPECTED)))

    def test_swapped_or_missing_deinstall_is_not_accepted(self):
        for seq in [
            [*n.EXPECTED[:3], n.EXPECTED[4], n.EXPECTED[3], n.EXPECTED[5]],
            list(n.EXPECTED[:-1]),
            list(n.EXPECTED) + ["new:post-install"],
            [*n.EXPECTED[:2], "old:pre-deinstall", *n.EXPECTED[2:]],
        ]:
            with self.subTest(seq=seq):
                with self.assertRaisesRegex(n.Refusal, "ORDER_DIFFERENT"):
                    n.check_trace(seq)

    def test_fixture_hook_is_only_a_tracer_not_production_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = n.phase_script(Path(tmp) / "trace", "old", "pre-deinstall")
            self.assertIn("old:pre-deinstall", text)
            self.assertIn("exit 0", text)
            self.assertNotIn("zapret_service", text)
            with self.assertRaises(n.Refusal):
                n.phase_script(Path(tmp) / "trace", "bad;exit", "pre-install")

    def test_archive_wrong_digest_refused_before_tar(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "historical.pkg"
            bad.write_bytes(b"not an authentic package")
            with mock.patch.object(n.subprocess, "run") as runner:
                with self.assertRaisesRegex(n.Refusal, "ARCHIVE_SHA256_MISMATCH"):
                    n.check_archive(bad)
                runner.assert_not_called()

    def test_archive_positive_hook_digest_provenance(self):
        body = {p: "#!/bin/sh\nexit 0\n" for p in n.PHASES}
        m = {"name": "os-zapret2-restyle", "version": "0.6.2_1",
             "abi": "FreeBSD:15:amd64", "scripts": body}
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "old.pkg"
            archive.write_bytes(b"local fixture archive")
            result = type("Result", (), {"returncode": 0,
                      "stdout": json.dumps(m).encode("utf-8")})()
            with mock.patch.object(n, "ARCHIVE_SHA", hashlib.sha256(archive.read_bytes()).hexdigest()), \
                 mock.patch.object(n.subprocess, "run", return_value=result):
                out = n.check_archive(archive)
                self.assertEqual(set(out), set(n.PHASES))
                self.assertEqual(out["pre-deinstall"]["sha256"], n.digest(body["pre-deinstall"].encode()))

    def test_archive_missing_or_bad_hook_refused(self):
        m = {"name": "os-zapret2-restyle", "version": "0.6.2_1",
             "abi": "FreeBSD:15:amd64", "scripts": {p: "x" for p in n.PHASES}}
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "test.pkg"
            archive.write_bytes(b"test fixture")
            with mock.patch.object(n, "ARCHIVE_SHA", hashlib.sha256(archive.read_bytes()).hexdigest()):
                for item in ["scripts", "pre-deinstall", "post-install"]:
                    copy = json.loads(json.dumps(m))
                    if item == "scripts":
                        del copy["scripts"]
                    else:
                        del copy["scripts"][item]
                    result = type("Result", (), {"returncode": 0,
                              "stdout": json.dumps(copy).encode()})()
                    with mock.patch.object(n.subprocess, "run", return_value=result):
                        with self.subTest(item=item), self.assertRaisesRegex(n.Refusal, "HOOKS_MISSING"):
                            n.check_archive(archive)

    def test_wrong_archive_abi_and_name_refused(self):
        m = {"name": "os-zapret2-restyle", "version": "0.6.2_1",
             "abi": "FreeBSD:15:amd64", "scripts": {p: "x" for p in n.PHASES}}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.pkg"
            path.write_bytes(b"fixture")
            with mock.patch.object(n, "ARCHIVE_SHA", hashlib.sha256(path.read_bytes()).hexdigest()):
                for field, bad, code in [("name", "fake", "IDENTITY"), ("abi", "Linux:15:amd64", "ABI")]:
                    wrong = dict(m)
                    wrong[field] = bad
                    result = type("Result", (), {"returncode": 0, "stdout": json.dumps(wrong).encode()})()
                    with mock.patch.object(n.subprocess, "run", return_value=result):
                        with self.subTest(field=field), self.assertRaisesRegex(n.Refusal, code):
                            n.check_archive(path)

    def test_linux_and_nonroot_fail_before_archive_or_pkg(self):
        class FakeUnix:
            sysname = "Linux"
            machine = "x86_64"
        with mock.patch.object(n.os, "uname", return_value=FakeUnix()), \
             mock.patch.object(n, "check_archive") as archive:
            with self.assertRaisesRegex(n.Refusal, "ONLY_ROOT_DISPOSABLE_FREEBSD"):
                n.run_vm(Path("/tmp/not-present.pkg"), Path("/tmp/not-written.json"))
            archive.assert_not_called()


if __name__ == "__main__":
    unittest.main()
