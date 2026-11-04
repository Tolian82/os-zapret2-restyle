#!/usr/bin/env python3
"""Offline contract for a reviewed -c seed that pins external verifier bytes."""
import ast
import contextlib
import hashlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SEED = HERE / 'stage3-prepkg-trust-seed.py'
CODE = SEED.read_text()


def definitions():
    tree = ast.parse(CODE, str(SEED))
    if not isinstance(tree.body[-1], ast.Try):
        raise AssertionError('operator seed must invoke main last')
    tree.body.pop()
    module = types.ModuleType('_operator_trust_seed')
    exec(compile(tree, str(SEED), 'exec'), module.__dict__)
    return module


def spoof_root(st):
    fields = list(st)
    fields[4] = 0
    return os.stat_result(fields)


class TrustSeedContracts(unittest.TestCase):
    def setUp(self):
        self.m = definitions()

    def test_no_mutation_or_untrusted_module_imports(self):
        self.assertIn('os.O_NOFOLLOW', CODE)
        self.assertIn('hmac.compare_digest', CODE)
        self.assertIn('return bytes(payload)', CODE)
        self.assertIn('exec(compiled,', CODE)
        self.assertNotIn('subprocess', CODE)
        self.assertNotIn('pkg add', CODE)
        self.assertNotIn('os.system(', CODE)
        self.assertNotIn('os.execv(', CODE)

    def test_actual_c_rejects_unsupported_commands_before_open(self):
        for tail in ([], ['upgrade'], ['--verified-verifier'],
                     ['--verified-verifier', '0' * 64, '/root/verified.py',
                      'upgrade', *('x' for _ in range(12))]):
            with self.subTest(tail=tail):
                result = subprocess.run([sys.executable, '-I', '-B', '-c', CODE, *tail],
                                        text=True, capture_output=True, timeout=12)
                self.assertEqual(result.returncode, 78)
                self.assertIn('SIGNED_READ_ONLY_VERIFIER_COMMAND_REQUIRED', result.stderr)
                self.assertNotIn('VERIFIED_SHA256', result.stderr)

    def test_root_path_traversal_and_aliases_refused(self):
        for path in ('relative.py', '/tmp/stage3-prepkg-verified-eval.py',
                     '/root/../tmp/stage3-prepkg-verified-eval.py',
                     '/root/./stage3-prepkg-verified-eval.py',
                     '/root//stage3-prepkg-verified-eval.py',
                     '/root/not-the-verifier.py', '/root/'):
            with self.subTest(path=path), self.assertRaises(SystemExit):
                self.m.trusted_root_path(path)

    def test_malformed_source_commit_refused_before_verifier_open(self):
        base = ['-c', '--verified-verifier', 'a' * 64,
                '/root/stage3-prepkg-verified-eval.py', '--expected-source-commit',
                '1' * 40, '--signed-provenance', 'b' * 64,
                '/root/key.pem', '/root/claims.json', '/root/sig',
                '/root/native-prepkg-standalone.py', 'inspect-predecessor',
                '/root/os-zapret2-restyle-0.6.2_110.pkg', '0.6.2_110',
                '/root/os-zapret2-restyle-0.6.2_1.pkg', '0.6.2_1']
        mod = self.m
        for wrong in ('', '1' * 39, '1' * 41, 'Z' * 40, '../' + '1' * 40):
            with self.subTest(commit=wrong),                  patch.object(mod.sys, 'argv', list(base[:5] + [wrong] + base[6:])),                  patch.object(mod, 'verified_verifier') as loaded,                  self.assertRaises(SystemExit) as refusal:
                mod.main()
            self.assertEqual(refusal.exception.code, 78)
            loaded.assert_not_called()

    def test_freeze_single_open_in_memory_and_all_corruption_refused(self):
        raw_fstat, raw_lstat = os.fstat, os.lstat
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'stage3-prepkg-verified-eval.py'
            content = b'print("VERIFIED_ONLY")\n'
            path.write_bytes(content)
            path.chmod(0o600)
            digest = hashlib.sha256(content).hexdigest()
            with patch.object(self.m, 'trusted_root_path'), \
                 patch.object(self.m.os, 'fstat', side_effect=lambda fd: spoof_root(raw_fstat(fd))), \
                 patch.object(self.m.os, 'lstat', side_effect=lambda p: spoof_root(raw_lstat(p))):
                self.assertEqual(self.m.verified_verifier(str(path), digest), content)
                for wrong in ('bad-digest', '0' * 64):
                    with self.subTest(wrong=wrong), self.assertRaises(SystemExit):
                        self.m.verified_verifier(str(path), wrong)
                path.write_bytes(b'print("MALICIOUS")\n')
                with self.assertRaises(SystemExit):
                    self.m.verified_verifier(str(path), digest)
                self.assertEqual(content, b'print("VERIFIED_ONLY")\n')
                path.chmod(0o666)
                with self.assertRaises(SystemExit):
                    self.m.verified_verifier(str(path), hashlib.sha256(path.read_bytes()).hexdigest())
                path.unlink()
                path.symlink_to(Path(td) / 'nonexistent')
                with self.assertRaises(SystemExit):
                    self.m.verified_verifier(str(path), digest)

    def test_valid_main_executes_frozen_verifier_bytes_and_preserves_signed_argv(self):
        args = ['-c', '--verified-verifier', 'a' * 64,
                '/root/stage3-prepkg-verified-eval.py', '--expected-source-commit',
                '1' * 40, '--signed-provenance',
                'b' * 64, '/root/key.pem', '/root/claims.json', '/root/sig',
                '/root/native-prepkg-standalone.py', 'inspect-predecessor',
                '/root/os-zapret2-restyle-0.6.2_109.pkg', '0.6.2_109',
                '/root/os-zapret2-restyle-0.6.2_1.pkg', '0.6.2_1']
        stdout, stderr = io.StringIO(), io.StringIO()
        initial = list(self.m.sys.argv)
        try:
            with patch.object(self.m.sys, 'argv', list(args)), \
                 patch.object(self.m.os, 'geteuid', return_value=0), \
                 patch.object(self.m.os, 'uname', return_value=types.SimpleNamespace(sysname='FreeBSD', machine='amd64')), \
                 patch.object(self.m, 'verified_verifier',
                              return_value=b'import sys; print("VERIFIED_SOURCE", sys.argv)\n') as verify, \
                 contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                self.m.main()
            verify.assert_called_once_with(args[3], args[2])
            self.assertIn('VERIFIED_SOURCE', stdout.getvalue())
            self.assertIn('VERIFIED_SHA256:', stderr.getvalue())
            self.assertIn('--signed-provenance', stdout.getvalue())
            self.assertIn('--expected-source-commit', stdout.getvalue())
            self.assertIn('1111111111111111111111111111111111111111', stdout.getvalue())
            self.assertIn('inspect-predecessor', stdout.getvalue())
            self.assertNotIn('--verified-verifier', stdout.getvalue())
        finally:
            self.m.sys.argv = initial


if __name__ == '__main__':
    unittest.main()
