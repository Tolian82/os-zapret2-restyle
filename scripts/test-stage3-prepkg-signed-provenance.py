#!/usr/bin/env python3
"""Offline executable signed operator provenance contracts for the trusted -c path."""
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

CODE_PATH = Path(__file__).with_name('stage3-prepkg-verified-eval.py')
CODE = CODE_PATH.read_text()


def definitions():
    tree = ast.parse(CODE)
    assert isinstance(tree.body[-1], ast.Try)
    tree.body.pop()
    m = types.ModuleType('signed_provenance_trusted_c')
    exec(compile(tree, str(CODE_PATH), 'exec'), m.__dict__)
    return m


def fixture(root, claimed=None, payload=b'print("VERIFIED_PREPKG_ENTRY")\n'):
    root = Path(root)
    def write(name, data):
        dest = root / name
        dest.write_bytes(data)
        dest.chmod(0o600)
        return dest
    cli = write('native-prepkg-standalone.py', payload)
    key = root / 'private.pem'
    pub = root / 'public.pem'
    subprocess.run(['/usr/bin/openssl','genpkey','-algorithm','RSA',
        '-pkeyopt','rsa_keygen_bits:2048','-out',str(key)],
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
    subprocess.run(['/usr/bin/openssl','pkey','-in',str(key),
        '-pubout','-out',str(pub)],check=True,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    pub.chmod(0o600)
    fields = {
        'schema': 'zapret2-prepkg-provenance-v1',
        'repository': 'Tolian82/os-zapret2-restyle',
        'source_commit': '1'*40,
        'entrypoint_sha256': hashlib.sha256(payload).hexdigest(),
        'incoming_version': '0.6.2_110',
        'incoming_sha256': 'a'*64,
        'predecessor_version': '0.6.2_1',
        'predecessor_sha256': 'b'*64,
    }
    if claimed:fields.update(claimed)
    claims = write('claims.json', json.dumps(fields,sort_keys=True,separators=(',',':')).encode())
    signature = root / 'claims.sig'
    subprocess.run(['/usr/bin/openssl','dgst','-sha256','-sign',str(key),
        '-out',str(signature),str(claims)],check=True,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    signature.chmod(0o600)
    return dict(cli=cli,pub=pub,key=key,claims=claims,sig=signature,
                key_sha=hashlib.sha256(pub.read_bytes()).hexdigest(), data=fields)


class SignedProvenance(unittest.TestCase):
    def setUp(self):
        self.m=definitions()
        # Linux Actions runner is non-root; root ownership and inode refusal
        # remain separately checked by test-stage3-prepkg-verified-eval.py.
        self.m.STAGING_ROOT = tempfile.gettempdir()
        self.m.private_root_bytes = lambda path: Path(path).read_bytes()

    def signed(self, case):
        return self.m.signed_claims(str(case['pub']),case['key_sha'],
                                    str(case['claims']),str(case['sig']))

    def test_real_openssl_signature_and_independent_key_pin(self):
        with tempfile.TemporaryDirectory(prefix='zapret108-',dir=None) as d:
            c=fixture(d)
            self.assertEqual(self.signed(c),c['data'])
            with self.assertRaises(SystemExit) as x:
                self.m.signed_claims(str(c['pub']),'0'*64,str(c['claims']),str(c['sig']))
            self.assertEqual(x.exception.code,78)

    def test_invalid_signature_tampered_claims_and_other_key(self):
        with tempfile.TemporaryDirectory(prefix='zapret108-',dir=None) as d:
            c=fixture(d)
            c['sig'].write_bytes(b'broken-signature')
            with self.assertRaises(SystemExit):self.signed(c)
            c=fixture(d)
            c['claims'].write_bytes(c['claims'].read_bytes().replace(b'0.6.2_110',b'0.6.2_110'))
            with self.assertRaises(SystemExit):self.signed(c)
            c=fixture(d)
            other=Path(d)/'other'
            other.mkdir(mode=0o700)
            replacement=fixture(other)
            c['pub'].write_bytes(replacement['pub'].read_bytes())
            with self.assertRaises(SystemExit):self.signed(c)

    def test_authenticated_wrong_identity_or_ambiguous_claims_refused(self):
        for extras in ({'repository':'different/repository'},
                       {'source_commit':'not-a-commit'},
                       {'incoming_sha256':'0'},
                       {'incoming_version':'0.6.2_1'},
                       {'schema':'not-ours'}):
            with self.subTest(extras=extras),tempfile.TemporaryDirectory(prefix='zapret108-',dir=None) as d:
                c=fixture(d,extras)
                with self.assertRaises(SystemExit):self.signed(c)

    def test_malformed_json_and_duplicate_signed_keys_refused(self):
        with tempfile.TemporaryDirectory(prefix='zapret108-',dir=None) as d:
            c=fixture(d)
            for raw in (b'not-json',b'{"schema":"a","schema":"b"}'):
                c['claims'].write_bytes(raw)
                subprocess.run(['/usr/bin/openssl','dgst','-sha256','-sign',str(c['key']),
                    '-out',str(c['sig']),str(c['claims'])],check=True,capture_output=True)
                with self.assertRaises(SystemExit):self.signed(c)

    def test_bad_cli_mode_or_unsigned_legacy_rejected_before_read(self):
        for args in ([],['upgrade'],['inspect-predecessor'],
            ['a'*64,'/root/cli.py','inspect-predecessor','/tmp/n','0.6.2_110','a'*64,
                '/tmp/o','0.6.2_1','b'*64]):
            p=subprocess.run([sys.executable,'-I','-B','-c',CODE,*args],
                capture_output=True,text=True,timeout=8)
            self.assertEqual(p.returncode,78)
            self.assertIn('SIGNED_READ_ONLY_PREDECESSOR_COMMAND_REQUIRED',p.stderr)

    def test_signed_but_different_source_commit_is_not_operator_approved(self):
        with tempfile.TemporaryDirectory(prefix='zapret110-',dir=None) as d:
            c=fixture(d,{'source_commit':'2'*40})
            self.assertEqual(self.signed(c)['source_commit'],'2'*40)
            argv=['-c','--expected-source-commit','1'*40,
                  '--signed-provenance',c['key_sha'],str(c['pub']),
                  str(c['claims']),str(c['sig']),str(c['cli']),
                  'inspect-predecessor','/root/os-zapret2-restyle-0.6.2_110.pkg',
                  '0.6.2_110','/root/os-zapret2-restyle-0.6.2_1.pkg','0.6.2_1']
            with patch.object(self.m.sys,'argv',argv), \
                 patch.object(self.m.os,'uname',return_value=types.SimpleNamespace(sysname='FreeBSD',machine='amd64')), \
                 patch.object(self.m.os,'geteuid',return_value=0), \
                 patch.object(self.m,'verify_source_bytes') as executable, \
                 self.assertRaises(SystemExit) as refused:
                self.m.main()
            self.assertEqual(refused.exception.code,78)
            executable.assert_not_called()

    def test_pinned_verified_memory_only_and_bad_target_fails_before_exec(self):
        with tempfile.TemporaryDirectory(prefix='zapret108-',dir=None) as d:
            c=fixture(d)
            argv=['-c','--expected-source-commit','1'*40,
                '--signed-provenance',c['key_sha'],str(c['pub']),
                str(c['claims']),str(c['sig']),str(c['cli']),
                'inspect-predecessor','/root/os-zapret2-restyle-0.6.2_110.pkg',
                '0.6.2_110','/root/os-zapret2-restyle-0.6.2_1.pkg','0.6.2_1']
            original=list(self.m.sys.argv)
            fake_os=types.SimpleNamespace(sysname='FreeBSD',machine='amd64')
            try:
                with patch.object(self.m.sys,'argv',list(argv)), \
                     patch.object(self.m.os,'uname',return_value=fake_os), \
                     patch.object(self.m.os,'geteuid',return_value=0), \
                     contextlib.redirect_stdout(io.StringIO()) as stdout, \
                     contextlib.redirect_stderr(io.StringIO()) as stderr:
                    self.m.main()
                self.assertIn('VERIFIED_PREPKG_ENTRY',stdout.getvalue())
                self.assertIn('VERIFIED_SIGNED_SHA256:',stderr.getvalue())
                with patch.object(self.m.sys,'argv',list(argv[:10]+['/root/os-zapret2-restyle-0.6.2_110.pkg']+argv[11:])), \
                     patch.object(self.m.os,'uname',return_value=fake_os), \
                     patch.object(self.m.os,'geteuid',return_value=0), \
                     self.assertRaises(SystemExit):
                    self.m.main()
                # Correctly signed claims must still be rejected when the
                # separately expected operator commit differs from the signer.
                with patch.object(self.m.sys,'argv',list(argv[:2]+['f'*40]+argv[3:])), \
                     patch.object(self.m.os,'uname',return_value=fake_os), \
                     patch.object(self.m.os,'geteuid',return_value=0), \
                     self.assertRaises(SystemExit) as wrong_commit:
                    self.m.main()
                self.assertEqual(wrong_commit.exception.code,78)
                c['cli'].write_bytes(b'print("MALICIOUS")\n')
                with patch.object(self.m.sys,'argv',list(argv)), \
                     patch.object(self.m.os,'uname',return_value=fake_os), \
                     patch.object(self.m.os,'geteuid',return_value=0), \
                     self.assertRaises(SystemExit):
                    self.m.main()
            finally:
                self.m.sys.argv=original


if __name__=='__main__':
    unittest.main()
