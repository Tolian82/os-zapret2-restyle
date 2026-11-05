#!/usr/bin/env python3
"""Portable, actual TLS/RSA/SQLite host separation tests. No OPNsense/pkg."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SRC=Path(__file__).with_name('stage3-offguest-checkpoint-ci.py')
spec=importlib.util.spec_from_file_location('offguest_ci',SRC)
w=importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)
HEAD='a'*40


class HostOnlyCheckpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='offguest-tests-')
        cls.prefix=Path(cls.temp.name)
        cls.private=cls.prefix/'not-exported';cls.workspace=cls.prefix/'shared'
        cls.public=cls.workspace/'.ci-offguest-public'
        for d in (cls.private,cls.workspace,cls.public):d.mkdir(mode=0o700)
        cls.env=mock.patch.dict(os.environ,{'GITHUB_ACTIONS':'true',
                  'ZAPRET2_STAGE3_OFFGUEST_CI':'1',
                  'GITHUB_WORKSPACE':str(cls.workspace)})
        cls.env.start()
        cls.server=subprocess.Popen([sys.executable,str(SRC),'serve',str(cls.private),str(cls.public),HEAD],
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=os.environ.copy())
        import select
        if not select.select([cls.server.stdout],[],[],30)[0]:
            raise AssertionError('host did not start')
        cls.ready=cls.server.stdout.readline()
        if 'CI_OFFGUEST_HOST_READY=' not in cls.ready:
            raise AssertionError('host refused: '+cls.ready+' '+cls.server.stderr.read())

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()
        try:cls.server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.server.kill();cls.server.wait()
        cls.server.stdout.close();cls.server.stderr.close()
        cls.env.stop();cls.temp.cleanup()

    def test_01_one_real_remote_tls_signed_checkpoint_and_replay(self):
        outcome=w.scenario(self.public,HEAD,host='127.0.0.1')
        self.assertEqual(outcome['status'],'PASS_CI_OFFGUEST_CHECKPOINT_TRANSPORT_ONLY')
        self.assertFalse(outcome['owner_approved_authority'])
        self.assertFalse(outcome['production_pkg_authorized'])
        report=w.audit_host(self.private,self.public,HEAD)
        self.assertFalse(report['pkg_invoked'])
        self.assertFalse((self.public/'tls.key').exists())
        self.assertFalse((self.public/'status.key').exists())
        self.assertFalse((self.public/'checkpoint.sqlite').exists())

    def test_02_missing_ci_optin_is_denied(self):
        with mock.patch.dict(os.environ,{'ZAPRET2_STAGE3_OFFGUEST_CI':''}):
            with self.assertRaisesRegex(w.Refusal,'CI_OFFGUEST_EXPLICIT_OPTIN_REQUIRED'):
                w.scenario(self.public,HEAD,'127.0.0.1')

    def test_03_wrong_head_refused_without_wire_request(self):
        with self.assertRaisesRegex(w.Refusal,'CI_OFFGUEST_CLIENT_SCOPE_INVALID'):
            w.status_request(self.public,'b'*40,secrets.token_hex(32),'127.0.0.1')

    def test_04_wrong_challenge_refused(self):
        with self.assertRaisesRegex(w.Refusal,'CI_OFFGUEST_CLIENT_SCOPE_INVALID'):
            w.status_request(self.public,HEAD,'not-a-hash','127.0.0.1')

    def test_05_public_manifest_additional_private_file_refused(self):
        foreign=self.public/'status.key';foreign.write_text('not a key');foreign.chmod(0o600)
        try:
            with self.assertRaisesRegex(w.Refusal,'CI_OFFGUEST_UNEXPECTED_PUBLIC_FILES'):
                w.read_public(self.public)
        finally:foreign.unlink()

    def test_06_cert_changed_refused_by_pin(self):
        name=self.public/'server.crt';original=name.read_bytes()
        name.write_bytes(original.replace(b'BEGIN CERTIFICATE',b'BEGIN CERTIFICATX'))
        try:
            with self.assertRaises((ValueError,w.Refusal)):
                w.read_public(self.public)
        finally:name.write_bytes(original)

    def test_07_signer_changed_refused_by_pin(self):
        path=self.public/'status-public.pem';original=path.read_bytes()
        path.write_bytes(original+b'\n')
        try:
            with self.assertRaisesRegex(w.Refusal,'CI_OFFGUEST_PUBLIC_PINS_INCONSISTENT'):
                w.read_public(self.public)
        finally:path.write_bytes(original)

    def test_08_public_world_readable_refused(self):
        path=self.public/'server.crt';path.chmod(0o644)
        try:
            with self.assertRaisesRegex(w.Refusal,'CI_OFFGUEST_PRIVATE_FILE_INVALID'):
                w.read_public(self.public)
        finally:path.chmod(0o600)

    def test_09_invalid_json_duplicate_key_rejected(self):
        with self.assertRaisesRegex(w.Refusal,'CI_OFFGUEST_DUPLICATE_KEY'):
            w.strict_json(b'{"action":"STATUS","action":"STATUS"}')

    def test_10_outside_shared_workspace_enforced(self):
        with mock.patch.dict(os.environ,{'GITHUB_WORKSPACE':str(self.private)}):
            with self.assertRaisesRegex(w.Refusal,'CI_OFFGUEST_HOST_PRIVATE_KEY_IN_SHARED_WORKSPACE'):
                w.external_root(self.private,self.public)

    def test_11_root_rollback_of_public_metadata_not_owner_trust(self):
        self.assertFalse(w.scenario.__doc__ is not None and 'owner approved' in w.scenario.__doc__)
        ep,_=w.read_public(self.public)
        self.assertIs(ep['production_pkg_authorized'],False)
        self.assertEqual(ep['status_pub_sha256'],hashlib.sha256((self.public/'status-public.pem').read_bytes()).hexdigest())

    def test_zz_host_outage_refuses_fresh_status(self):
        self.server.terminate();self.server.wait(timeout=5)
        with self.assertRaises(OSError):
            w.status_request(self.public,HEAD,secrets.token_hex(32),'127.0.0.1')
        self.assertEqual(w.audit_host(self.private,self.public,HEAD)['status'],
                         'PASS_CI_HOST_KEY_AND_SQLITE_NOT_SYNCED')


if __name__=='__main__':
    unittest.main()
