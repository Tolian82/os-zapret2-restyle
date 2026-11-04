#!/usr/bin/env python3
"""Offline contracts for external trusted -c verify-before-execute boundary."""
import ast
import contextlib
import hashlib
import io
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
VERIFIER = HERE / "stage3-prepkg-verified-eval.py"
CODE = VERIFIER.read_text()
BOOTSTRAP = HERE / "native-prepkg-standalone.py"


def definitions():
    # Test functions in isolation: strip only the final unconditional
    # invoke statement from the AST. The exact -c text is separately
    # syntax checked, run as-is for invalid CLI and tested on real FreeBSD.
    tree = ast.parse(CODE, filename=str(VERIFIER))
    if not isinstance(tree.body[-1], ast.Try):
        raise AssertionError("trusted -c snippet must call main as last statement")
    tree.body.pop()
    ns = {"__name__": "_trusted_eval_contracts"}
    exec(compile(tree, str(VERIFIER), "exec"), ns)
    return types.SimpleNamespace(**ns)


def fake_root_stat(st):
    parts = list(st)
    parts[4] = 0
    return os.stat_result(parts)


class VerifiedPreexecContracts(unittest.TestCase):
    def setUp(self):
        self.m = definitions()

    def test_no_mutating_dispatch_or_local_provenance_inference(self):
        compile(CODE, str(VERIFIER), "exec")
        self.assertIn('os.O_NOFOLLOW', CODE)
        self.assertIn('hmac.compare_digest(observed, digest)', CODE)
        self.assertIn('exec(executable,', CODE)
        self.assertIn('return bytes(payload)', CODE)
        self.assertIn('sys.argv = [filename] + sys.argv[3:]', CODE)
        self.assertNotIn("pkg add", CODE)
        self.assertNotIn("pkg upgrade", CODE)
        self.assertNotIn("pkg delete", CODE)
        self.assertTrue(BOOTSTRAP.exists())

    def test_real_c_invocation_rejects_unsafe_dispatch_before_source_open(self):
        with tempfile.TemporaryDirectory() as td:
            marker = Path(td) / "marker"
            malicious = Path(td) / "exec-bad.py"
            malicious.write_text(f'open({str(marker)!r},"w").write("BAD")\n')
            for args in ([], ["upgrade"], ["reinstall"],
                         ["inspect-predecessor"],
                         ["inspect-predecessor", "missing", "parameters"]):
                with self.subTest(args=args):
                    p = subprocess.run([sys.executable, "-I", "-B", "-c", CODE,
                                        "0"*64, str(malicious), *args],
                                       capture_output=True, text=True, timeout=15)
                    self.assertEqual(p.returncode, 78)
                    self.assertIn("ONLY_READ_ONLY_PREDECESSOR_COMMAND_SUPPORTED",
                                  p.stderr)
                    self.assertNotIn("VERIFIED_SHA256:", p.stderr)
            self.assertFalse(marker.exists())

    def test_reject_unknown_digest_and_bad_platform(self):
        arr = ["-c", "not-a-sha", "/root/bad.py", "inspect-predecessor",
               "/tmp/a", "0.6.2_107", "a"*64, "/tmp/b", "0.6.2_1", "b"*64]
        with patch.object(self.m.sys, "argv", arr), \
             self.assertRaises(SystemExit) as result:
            self.m.main()
        self.assertEqual(result.exception.code, 78)
        arr[1] = "a"*64
        with patch.object(self.m.sys, "argv", arr), \
             patch.object(self.m.os, "geteuid", return_value=1001), \
             self.assertRaises(SystemExit) as result:
            self.m.main()
        self.assertEqual(result.exception.code, 78)

    def test_absolute_private_root_path_and_no_traversal(self):
        for bad in ("/tmp/cli.py", "relative.py", "/root/../tmp/cli.py",
                    "/root//bad.py", "/root/", "/root/./cli.py"):
            with self.subTest(bad=bad), self.assertRaises(SystemExit):
                self.m.trusted_root_path(bad)

    def test_exact_inode_and_digest_also_frozen_for_in_memory_compile(self):
        real_fstat = os.fstat
        real_lstat = os.lstat
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "trusted.py"
            script.write_bytes(b'print("SAFE-VERIFIED")\n')
            script.chmod(0o600)
            expected = hashlib.sha256(script.read_bytes()).hexdigest()
            def lstat(path, *args, **kwargs):
                return fake_root_stat(real_lstat(path, *args, **kwargs))
            with patch.object(self.m, "trusted_root_path"), \
                 patch.object(self.m.os, "fstat", side_effect=lambda fd:
                              fake_root_stat(real_fstat(fd))), \
                 patch.object(self.m.os, "lstat", side_effect=lstat):
                pinned = self.m.verify_source_bytes(str(script), expected)
                self.assertEqual(pinned, b'print("SAFE-VERIFIED")\n')
                with self.assertRaises(SystemExit) as result:
                    self.m.verify_source_bytes(str(script), "a"*64)
                self.assertEqual(result.exception.code, 78)
                script.write_bytes(b'print("CHANGED-SOURCE")\n')
                with self.assertRaises(SystemExit):
                    self.m.verify_source_bytes(str(script), expected)
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    exec(compile(pinned, str(script), "exec"), {})
                self.assertEqual(buf.getvalue(), "SAFE-VERIFIED\n")
                script.chmod(0o666)
                with self.assertRaises(SystemExit):
                    self.m.verify_source_bytes(str(script), hashlib.sha256(
                        script.read_bytes()).hexdigest())
                script.unlink()
                script.symlink_to(Path(tmp) / "other.py")
                with self.assertRaises(SystemExit):
                    self.m.verify_source_bytes(str(script), expected)

    def test_valid_main_compiles_verified_bytes_and_reports_only_after_sha(self):
        argv = ["-c", "f"*64, "/root/example/cli.py", "inspect-predecessor",
                "/tmp/new.pkg", "0.6.2_107", "a"*64,
                "/tmp/old.pkg", "0.6.2_1", "b"*64]
        payload = b'print("IN_MEMORY_VERIFIED_ENTRY")\n'
        stdout, stderr = io.StringIO(), io.StringIO()
        original = list(self.m.sys.argv)
        try:
            with patch.object(self.m.sys, "argv", list(argv)), \
                 patch.object(self.m.os, "geteuid", return_value=0), \
                 patch.object(self.m.os, "uname", return_value=
                              types.SimpleNamespace(sysname="FreeBSD",machine="amd64")), \
                 patch.object(self.m, "verify_source_bytes", return_value=payload) as checked, \
                 contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                self.m.main()
            checked.assert_called_once_with(argv[2], argv[1])
            self.assertIn("IN_MEMORY_VERIFIED_ENTRY", stdout.getvalue())
            self.assertIn("VERIFIED_SHA256:" + argv[1], stderr.getvalue())
        finally:
            self.m.sys.argv = original


if __name__ == "__main__":
    unittest.main()
