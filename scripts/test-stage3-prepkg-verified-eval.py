#!/usr/bin/env python3
"""Offline fail-closed source-byte and read-only execution contracts."""
import ast
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
VERIFIER = HERE / 'stage3-prepkg-verified-eval.py'
CODE = VERIFIER.read_text()


def definitions():
    tree = ast.parse(CODE)
    if not isinstance(tree.body[-1], ast.Try):
        raise AssertionError('trusted -c must invoke main only at end')
    tree.body.pop()
    module = types.ModuleType('_trusted_eval_contracts')
    exec(compile(tree,str(VERIFIER),'exec'),module.__dict__)
    return module


class VerifiedPreexecContracts(unittest.TestCase):
    def setUp(self):
        self.m=definitions()

    def test_no_mutating_dispatch_or_automatic_digest_fallback(self):
        compile(CODE,str(VERIFIER),'exec')
        self.assertIn('os.O_NOFOLLOW',CODE)
        self.assertIn('exec(executable,',CODE)
        self.assertIn('return bytes(payload)',CODE)
        self.assertIn('SIGNED_READ_ONLY_PREDECESSOR_COMMAND_REQUIRED',CODE)
        self.assertIn('SIGNED_PROVENANCE_SIGNATURE_INVALID',CODE)
        self.assertNotIn('pkg add',CODE)
        self.assertNotIn('pkg upgrade',CODE)
        self.assertNotIn('pkg delete',CODE)

    def test_plain_unsigned_or_mutating_arguments_refuse_before_python_source(self):
        for args in ([],['upgrade'],['inspect-predecessor'],
                ['f'*64,'/root/standalone.py','inspect-predecessor','n','v','a'*64,'o','v','b'*64]):
            p=subprocess.run([sys.executable,'-I','-B','-c',CODE,*args],
                capture_output=True,text=True,timeout=10)
            self.assertEqual(p.returncode,78)
            self.assertIn('SIGNED_READ_ONLY_PREDECESSOR_COMMAND_REQUIRED',p.stderr)
            self.assertNotIn('VERIFIED_SIGNED_SHA256',p.stderr)

    def test_root_private_paths_required_and_no_traversal(self):
        for bad in ('/tmp/cli.py','relative.py','/root/../tmp/cli.py',
                    '/root//bad.py','/root/','/root/./cli.py'):
            with self.subTest(path=bad),self.assertRaises(SystemExit):
                self.m.trusted_root_path(bad)

    def test_opened_source_inode_and_signed_expected_sha_freezes_bytes(self):
        # Root-owned /root is available in isolated native CI. Off-target CI
        # can replace only the path-check, while keeping real fd/mode checks.
        with tempfile.TemporaryDirectory() as tmp:
            script=Path(tmp)/'script.py'
            script.write_bytes(b'print("TRUSTED")\n')
            script.chmod(0o600)
            expected=hashlib.sha256(script.read_bytes()).hexdigest()
            real=os.fstat
            def fake_fstat(fd):
                st=real(fd)
                a=list(st);a[4]=0
                return os.stat_result(a)
            real_lstat=os.lstat
            def fake_lstat(path):
                st=real_lstat(path)
                a=list(st);a[4]=0
                return os.stat_result(a)
            with patch.object(self.m,'trusted_root_path'), \
                 patch.object(self.m.os,'fstat',side_effect=fake_fstat), \
                 patch.object(self.m.os,'lstat',side_effect=fake_lstat):
                pinned=self.m.verify_source_bytes(str(script),expected)
                self.assertEqual(pinned,b'print("TRUSTED")\n')
                with self.assertRaises(SystemExit):
                    self.m.verify_source_bytes(str(script),'0'*64)
                script.write_bytes(b'print("CHANGED")\n')
                with self.assertRaises(SystemExit):
                    self.m.verify_source_bytes(str(script),expected)
                self.assertEqual(pinned,b'print("TRUSTED")\n')
                script.chmod(0o666)
                with self.assertRaises(SystemExit):
                    self.m.verify_source_bytes(str(script),hashlib.sha256(script.read_bytes()).hexdigest())
                script.unlink()
                script.symlink_to(Path(tmp)/'other.py')
                with self.assertRaises(SystemExit):
                    self.m.verify_source_bytes(str(script),expected)


if __name__=='__main__':
    unittest.main()
