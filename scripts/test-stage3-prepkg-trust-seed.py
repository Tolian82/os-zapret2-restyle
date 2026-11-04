#!/usr/bin/env python3
"""Off-target source-only receipt-to-first-executable seed contracts."""
import ast
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SEED = HERE / "stage3-prepkg-trust-seed.py"
CODE = SEED.read_text()


def definitions():
    tree = ast.parse(CODE, str(SEED))
    assert isinstance(tree.body[-1], ast.Try)
    tree.body.pop()
    module = types.ModuleType("receipt_bound_trust_seed")
    exec(compile(tree, str(SEED), "exec"), module.__dict__)
    return module


def spoof_root(st):
    fields = list(st)
    fields[4] = 0
    return os.stat_result(fields)


def pins():
    return {
        "schema": "zapret2-prepkg-operator-pins-v1",
        "repository": "Tolian82/os-zapret2-restyle",
        "trust_status": "PINS_RECORDED_NOT_AUTHENTICATED",
        "seed_sha256": "a" * 64,
        "verifier_sha256": "b" * 64,
        "public_key_sha256": "c" * 64,
        "source_commit": "1" * 40,
        "incoming_version": "0.6.2_112",
        "incoming_sha256": "d" * 64,
        "predecessor_version": "0.6.2_1",
        "predecessor_sha256": "e" * 64,
    }


def argv():
    return ["-c", "--operator-receipt", "/root/review/operator-pins.json",
            "--verified-verifier", "/root/review/stage3-prepkg-verified-eval.py",
            "--signed-provenance", "/root/review/approved-public.pem",
            "/root/review/claims.json", "/root/review/sig",
            "/root/review/native-prepkg-standalone.py", "inspect-predecessor",
            "/root/review/os-zapret2-restyle-0.6.2_112.pkg", "0.6.2_112",
            "/root/review/os-zapret2-restyle-0.6.2_1.pkg", "0.6.2_1"]


class TrustSeedContracts(unittest.TestCase):
    def setUp(self):
        self.m = definitions()

    def test_no_pkg_mutation_or_untrusted_imports(self):
        self.assertIn("os.O_NOFOLLOW", CODE)
        self.assertIn("hmac.compare_digest", CODE)
        self.assertIn("exec(compiled,", CODE)
        self.assertIn("RECEIPT_PINS_BOUND_NOT_AUTHENTICATED", CODE)
        for forbidden in ("subprocess", "pkg add", "pkg upgrade", "os.system(",
                          "os.execv(", "operator_source_authenticated=True"):
            self.assertNotIn(forbidden, CODE)

    def test_actual_c_rejects_legacy_and_mutating_argv(self):
        for tail in ([], ["upgrade"], ["--verified-verifier"],
                     ["--verified-verifier", "a" * 64,
                      "/root/review/stage3-prepkg-verified-eval.py",
                      "--expected-source-commit", "1" * 40,
                      "--signed-provenance", "b" * 64,
                      "/root/review/key.pem", "claims", "sig", "cli",
                      "inspect-predecessor", "incoming", "v", "old", "old-v"],
                     argv()[1:] + ["upgrade"]):
            with self.subTest(tail=tail[:3]):
                result = subprocess.run([sys.executable, "-I", "-B", "-c", CODE,
                                         *tail], capture_output=True,
                                        text=True, timeout=12)
                self.assertEqual(result.returncode, 78)
                self.assertIn("SIGNED_READ_ONLY_VERIFIER_COMMAND_REQUIRED",
                              result.stderr)
                self.assertNotIn("VERIFIED_SHA256:", result.stderr)

    def test_root_verifier_aliases_rejected(self):
        for bad in ("relative.py", "/tmp/stage3-prepkg-verified-eval.py",
                    "/root/../tmp/stage3-prepkg-verified-eval.py",
                    "/root//stage3-prepkg-verified-eval.py",
                    "/root/not-verifier.py"):
            with self.subTest(path=bad), self.assertRaises(SystemExit):
                self.m.trusted_root_path(bad)

    def test_receipt_root_path_denial_before_open(self):
        for bad in ("relative.json", "/tmp/operator-pins.json",
                    "/root/../tmp/operator-pins.json",
                    "/root//operator-pins.json", "/root/other.json",
                    "/root/review/operator-pins.json/"):
            with self.subTest(path=bad), \
                 patch.object(self.m.os, "open") as opened, \
                 self.assertRaises(SystemExit):
                self.m.operator_receipt(bad)
            opened.assert_not_called()

    def test_single_fd_receipt_and_schema_refusals(self):
        raw_open, raw_lstat, raw_fstat = os.open, os.lstat, os.fstat
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "review"
            root.mkdir(mode=0o700)
            record = root / "operator-pins.json"
            def lstat(path):
                if path == "/root":
                    return spoof_root(raw_lstat(td))
                if path == "/root/review":
                    return spoof_root(raw_lstat(root))
                if path == "/root/review/operator-pins.json":
                    return spoof_root(raw_lstat(record))
                return spoof_root(raw_lstat(path))
            def openfile(path, flags, *args, **kw):
                if path == "/root/review/operator-pins.json":
                    return raw_open(record, flags, *args, **kw)
                return raw_open(path, flags, *args, **kw)
            def write(data):
                record.unlink(missing_ok=True)
                record.write_bytes(data)
                record.chmod(0o600)
            valid = pins()
            with patch.object(self.m.os, "lstat", side_effect=lstat), \
                 patch.object(self.m.os, "fstat",
                              side_effect=lambda fd: spoof_root(raw_fstat(fd))), \
                 patch.object(self.m.os, "open", side_effect=openfile):
                write(json.dumps(valid).encode())
                self.assertEqual(
                    self.m.operator_receipt("/root/review/operator-pins.json"),
                    valid)
                failures = [
                    json.dumps(dict(valid, source_commit="z" * 40)).encode(),
                    json.dumps(dict(valid, trust_status="AUTHENTICATED")).encode(),
                    json.dumps(dict(valid, repository="different/repo")).encode(),
                    json.dumps(dict(valid, public_key_sha256="0" * 64)).encode(),
                    json.dumps(dict(valid, incoming_version="0.6.2_1")).encode(),
                    json.dumps(valid).rstrip().rstrip(b"}") +
                        b',"source_commit":"2"}',
                    b"not-json",
                    b" " * 4096,
                ]
                for data in failures:
                    with self.subTest(raw=data[:50]):
                        write(data)
                        with self.assertRaises(SystemExit) as exit_code:
                            self.m.operator_receipt(
                                "/root/review/operator-pins.json")
                        self.assertEqual(exit_code.exception.code, 78)
                write(json.dumps(valid).encode())
                record.chmod(0o666)
                with self.assertRaises(SystemExit):
                    self.m.operator_receipt("/root/review/operator-pins.json")
                record.unlink()
                record.symlink_to(root / "somewhere")
                with self.assertRaises(SystemExit):
                    self.m.operator_receipt("/root/review/operator-pins.json")

    def test_verified_verifier_bytes_freeze_and_tamper_refusal(self):
        raw_fstat, raw_lstat = os.fstat, os.lstat
        with tempfile.TemporaryDirectory() as td:
            script = Path(td) / "stage3-prepkg-verified-eval.py"
            code = b'print("VERIFIED_ONLY")\n'
            script.write_bytes(code)
            script.chmod(0o600)
            digest = hashlib.sha256(code).hexdigest()
            with patch.object(self.m, "trusted_root_path"), \
                 patch.object(self.m.os, "fstat",
                              side_effect=lambda fd: spoof_root(raw_fstat(fd))), \
                 patch.object(self.m.os, "lstat",
                              side_effect=lambda p: spoof_root(raw_lstat(p))):
                self.assertEqual(
                    self.m.verified_verifier(str(script), digest), code)
                with self.assertRaises(SystemExit):
                    self.m.verified_verifier(str(script), "0" * 64)
                script.write_bytes(b"print('ATTACKER')\n")
                with self.assertRaises(SystemExit):
                    self.m.verified_verifier(str(script), digest)
                script.chmod(0o666)
                with self.assertRaises(SystemExit):
                    self.m.verified_verifier(
                        str(script), hashlib.sha256(script.read_bytes()).hexdigest())
                script.unlink()
                script.symlink_to(Path(td) / "other")
                with self.assertRaises(SystemExit):
                    self.m.verified_verifier(str(script), digest)

    def test_receipt_target_version_refuses_before_verifier(self):
        args = argv()
        args[12] = "0.6.2_999"
        with patch.object(self.m.sys, "argv", args), \
             patch.object(self.m.os, "geteuid", return_value=0), \
             patch.object(self.m.os, "uname", return_value=types.SimpleNamespace(
                 sysname="FreeBSD", machine="amd64")), \
             patch.object(self.m, "operator_receipt", return_value=pins()), \
             patch.object(self.m, "verified_verifier") as source, \
             self.assertRaises(SystemExit) as refusal:
            self.m.main()
        self.assertEqual(refusal.exception.code, 78)
        source.assert_not_called()

    def test_seed_exec_receipt_derived_values_without_caller_pins(self):
        args = argv()
        stdout, stderr = io.StringIO(), io.StringIO()
        original = list(self.m.sys.argv)
        try:
            with patch.object(self.m.sys, "argv", list(args)), \
                 patch.object(self.m.os, "geteuid", return_value=0), \
                 patch.object(self.m.os, "uname", return_value=types.SimpleNamespace(
                     sysname="FreeBSD", machine="amd64")), \
                 patch.object(self.m, "operator_receipt", return_value=pins()) as receipt, \
                 patch.object(self.m, "verified_verifier",
                     return_value=b'import sys; print("VERIFIED_EXEC", sys.argv)\n') as verifier, \
                 contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                self.m.main()
            receipt.assert_called_once_with(args[2])
            verifier.assert_called_once_with(args[4], pins()["verifier_sha256"])
            self.assertIn("VERIFIED_EXEC", stdout.getvalue())
            self.assertIn("--expected-source-commit", stdout.getvalue())
            self.assertIn(pins()["source_commit"], stdout.getvalue())
            self.assertIn("--expected-archive-pins", stdout.getvalue())
            self.assertIn(pins()["incoming_sha256"], stdout.getvalue())
            self.assertIn(pins()["predecessor_sha256"], stdout.getvalue())
            self.assertIn(pins()["public_key_sha256"], stdout.getvalue())
            self.assertNotIn("--operator-receipt", stdout.getvalue())
            self.assertNotIn("--verified-verifier", stdout.getvalue())
            self.assertIn("RECEIPT_PINS_BOUND_NOT_AUTHENTICATED", stderr.getvalue())
        finally:
            self.m.sys.argv = original


if __name__ == "__main__":
    unittest.main()
