#!/usr/bin/env python3
"""Stage 3.42 CI-only signed CONSUMED proof under original FD9; not owner trust."""
import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("fd9_consumed_ci",HERE/"stage3-native-configd-operator-grant-ci.py")
guard=importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

HEAD="a"*40
NONCE="f"*32
OLD_BYTES=b"bounded-CI-published-archive"
NEW_BYTES=b"bounded-CI-genuine-Mk-successor"
OLD_SHA=hashlib.sha256(OLD_BYTES).hexdigest()
NEW_SHA=hashlib.sha256(NEW_BYTES).hexdigest()
ENV={"GITHUB_ACTIONS":"true",
     "ZAPRET2_STAGE3_NATIVE_SIGNED_CONSUMED":"1",
     "ZAPRET2_STAGE3_NATIVE_SIGNED_CONSUMED_CI":"1",
     "ZAPRET2_STAGE3_NATIVE_MUTATING_PKG_CI":"1"}


class SignedConsumedFD9(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix="fd9-signed-consumed-")
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.root.chmod(0o700)
        self.old=self.root/"os-zapret2-restyle-0.6.2_1.pkg"
        self.new=self.root/"os-zapret2-restyle-0.6.2_132.pkg"
        self.old.write_bytes(OLD_BYTES)
        self.new.write_bytes(NEW_BYTES)
        self.old.chmod(0o600)
        self.new.chmod(0o600)
        self.calls=0

    def fd9(self):
        self.calls+=1

    def issue(self):
        with mock.patch.dict(os.environ,ENV,clear=True):
            return guard.issue(self.root,HEAD,self.old,self.new,
                               OLD_SHA,NEW_SHA,"132",nonce=NONCE)

    def verify(self,ticket,nonce=NONCE):
        with mock.patch.dict(os.environ,ENV,clear=True):
            return guard.verify(self.root,ticket,HEAD,self.old,self.new,
                                OLD_SHA,NEW_SHA,"132",self.fd9,nonce=nonce)

    def test_signed_consumed_exact_scope_under_fd9(self):
        ticket=self.issue()
        result=self.verify(ticket)
        self.assertTrue(result["ci_operator_signature_verified"])
        self.assertFalse(result["ci_owner_approval_authenticated"])
        self.assertFalse(result["ci_remote_witness_deployed"])
        self.assertFalse(result["ci_pkg_one_use_commit_proven"])
        self.assertGreaterEqual(self.calls,7)

    def test_identical_grant_second_check_no_new_status_signing(self):
        ticket=self.issue()
        first=self.verify(ticket)
        second=self.verify(ticket)
        self.assertEqual(first,second)
        self.assertFalse((self.root/guard.ROOT_NAME/"status-private.pem").exists())

    def test_altered_consumed_bytes_refused(self):
        ticket=self.issue()
        f=self.root/guard.ROOT_NAME/"ci-consumed.json"
        signed=f.read_bytes()
        self.assertIn(b'"action":"CONSUMED"',signed)
        f.write_bytes(signed.replace(b'"action":"CONSUMED"',b'"action":"ABORTED"'))
        with self.assertRaisesRegex(Exception,"STATUS_RSA_SIGNATURE_INVALID"):
            self.verify(ticket)

    def test_altered_consumed_signature_refused(self):
        ticket=self.issue()
        f=self.root/guard.ROOT_NAME/"ci-consumed.sig"
        buf=bytearray(f.read_bytes());buf[0]^=1;f.write_bytes(bytes(buf))
        with self.assertRaisesRegex(Exception,"STATUS_RSA_SIGNATURE_INVALID"):
            self.verify(ticket)

    def test_wrong_original_transfer_nonce_refused(self):
        ticket=self.issue()
        with self.assertRaisesRegex(Exception,"STATUS_REQUEST_BINDING_MISMATCH"):
            self.verify(ticket,nonce="e"*32)

    def test_missing_signed_witness_refused(self):
        ticket=self.issue()
        (self.root/guard.ROOT_NAME/"ci-consumed.json").unlink()
        with self.assertRaises((OSError,Exception)):
            self.verify(ticket)

    def test_wrong_status_signer_key_refused(self):
        ticket=self.issue()
        self.assertFalse((self.root/guard.ROOT_NAME/"status-private.pem").exists())
        public=self.root/guard.ROOT_NAME/"status-public.pem"
        public.write_bytes(public.read_bytes()+b"\nFOREIGN")
        with self.assertRaisesRegex(Exception,"STATUS_WITNESS_KEY_FINGERPRINT_MISMATCH"):
            self.verify(ticket)

    def test_disposable_mode_requires_all_flags(self):
        with mock.patch.dict(os.environ,{"ZAPRET2_STAGE3_NATIVE_SIGNED_CONSUMED":"1"},clear=True):
            with self.assertRaisesRegex(guard.Refusal,"FD9_CI_CONSUMED_DISPOSABLE_OPTIN_REQUIRED"):
                guard.consumed_mode()
        with mock.patch.dict(os.environ,{"ZAPRET2_STAGE3_NATIVE_SIGNED_CONSUMED":"bad"},clear=True):
            with self.assertRaisesRegex(guard.Refusal,"FD9_CI_CONSUMED_MODE_INVALID"):
                guard.consumed_mode()

    def test_missing_nonce_refused_before_issuance(self):
        with mock.patch.dict(os.environ,ENV,clear=True):
            with self.assertRaisesRegex(guard.Refusal,"FD9_CI_CONSUMED_TRANSFER_NONCE_INVALID"):
                guard.issue(self.root,HEAD,self.old,self.new,OLD_SHA,NEW_SHA,"132")
        self.assertFalse((self.root/guard.ROOT_NAME).exists())

    def test_legacy_scope_no_consumed_artifact_or_mode_leak(self):
        with mock.patch.dict(os.environ,{},clear=True):
            ticket=guard.issue(self.root,HEAD,self.old,self.new,OLD_SHA,NEW_SHA,"132")
            result=guard.verify(self.root,ticket,HEAD,self.old,self.new,
                                OLD_SHA,NEW_SHA,"132",self.fd9)
            self.assertTrue(result["ci_operator_signature_verified"])
            self.assertFalse((self.root/guard.ROOT_NAME/"ci-consumed.json").exists())
            guard.cleanup(self.root)
        self.assertFalse((self.root/guard.ROOT_NAME).exists())

    def test_consumed_exact_cleanup_only_registered_private_files(self):
        ticket=self.issue()
        self.verify(ticket)
        with mock.patch.dict(os.environ,ENV,clear=True):
            guard.cleanup(self.root)
        self.assertFalse((self.root/guard.ROOT_NAME).exists())

    def test_ci_signed_consumed_never_promotes_product_authority(self):
        module=(HERE/"stage3-native-configd-fd9-handoff.py").read_text()
        worker=(HERE/"stage3-native-configd-mutating-pkg.py").read_text()
        workflow=(HERE.parent/".github/workflows/stage2-native-delegated-fd9-handoff.yml").read_text()
        self.assertIn("signed_consumed=signed_consumed_mode()",module)
        self.assertIn("ZAPRET2_STAGE3_NATIVE_SIGNED_CONSUMED_CI=1",workflow)
        self.assertIn("configd-native-signed-consumed-stdin:",workflow)
        # Both original-FD9 signed checks still bind the same configd ticket
        # nonce. A newer optional live-witness phase must not break _132.
        self.assertEqual(worker.count("nonce=ticket,live_phase="),2)
        self.assertIn("nonce=ticket,live_phase='consume' if live_witness else None",worker)
        self.assertIn("nonce=ticket,live_phase='status' if live_witness else None",worker)
        self.assertLess(worker.index("second=grant_guard.verify("),
                        worker.index("delegate.admitted_pkg_dispatch(archive,candidate,env)"))
        self.assertIn("'ci_operator_grant_is_owner_approved':False",module)
        self.assertIn("'lh08_ac11_accepted':False",module)


if __name__=="__main__":
    unittest.main()
