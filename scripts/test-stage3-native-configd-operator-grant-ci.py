#!/usr/bin/env python3
"""Source-level operator grant / real FD9 worker gate contracts (no pkg mutation)."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from unittest import mock
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
HEAD = "a"*40
OLD_SHA = hashlib.sha256(b"test-only-old-archive").hexdigest()
NEW_SHA = hashlib.sha256(b"test-only-new-archive").hexdigest()


def module(filename, name):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


guard = module("stage3-native-configd-operator-grant-ci.py", "test_ci_fd9_grant")
scope = module("stage3-prepkg-operator-operation-grant-ci.py", "test_ci_grant_scope")


class ExactSignedNativeDispatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ci-fd9-grant-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.root.chmod(0o700)
        self.old = self.root / "os-zapret2-restyle-0.6.2_1.pkg"
        self.new = self.root / "os-zapret2-restyle-0.6.2_124.pkg"
        self.old.write_bytes(b"test-only-old-archive")
        self.new.write_bytes(b"test-only-new-archive")
        self.old.chmod(0o600)
        self.new.chmod(0o600)
        self.ticket = guard.issue(self.root, HEAD, self.old, self.new,
                                  OLD_SHA, NEW_SHA, "124")
        self.calls = 0

    def checker(self):
        self.calls += 1

    def accepted(self, ticket=None, head=HEAD, checker=None):
        return guard.verify(self.root, self.ticket if ticket is None else ticket,
                            head, self.old, self.new, OLD_SHA, NEW_SHA, "124",
                            self.checker if checker is None else checker)

    def assert_scope_refused(self, expected_reason, operation):
        # The production-facing helper loads a fresh isolated verifier module
        # for each native request. Its Refusal class is not the separately
        # loaded unit module's class: assert the exact fail-closed reason.
        with self.assertRaises(Exception) as observed:
            operation()
        self.assertEqual(type(observed.exception).__name__, "Refusal")
        self.assertEqual(str(observed.exception), expected_reason)

    def test_signed_exact_archive_grant_accepted_with_bound_checker(self):
        result = self.accepted()
        self.assertTrue(result["ci_operator_signature_verified"])
        self.assertTrue(result["ci_real_old_and_new_archives_measured"])
        self.assertTrue(result["ci_resigned_false_old_new_head_denied"])
        self.assertFalse(result["ci_owner_approval_authenticated"])
        self.assertFalse(result["ci_remote_witness_deployed"])
        self.assertGreaterEqual(self.calls, 5)

    def test_invalid_grants_correctly_resigned_are_refused(self):
        policy = scope
        root = self.root / guard.ROOT_NAME
        args = (str(root / "operator-public.pem"),
                self.ticket["operator_sha256"], self.ticket["status_sha256"],
                self.ticket["client_sha256"], HEAD,
                str(self.old), str(self.new))
        for stem, error in (("wrong-old", "GRANT_ARCHIVE_BYTES_NOT_SIGNED_DIGEST"),
                            ("wrong-new", "GRANT_ARCHIVE_BYTES_NOT_SIGNED_DIGEST"),
                            ("wrong-head", "GRANT_SOURCE_COMMIT_NOT_EXPECTED")):
            with self.subTest(stem=stem), self.assertRaisesRegex(policy.Refusal, error):
                policy.load(str(root / (stem + ".json")),
                            str(root / (stem + ".sig")), *args)

    def test_changed_new_archive_after_issuance_refused(self):
        self.new.write_bytes(b"not-the-signed-native-archive")
        self.assert_scope_refused("GRANT_ARCHIVE_BYTES_NOT_SIGNED_DIGEST",
                                  self.accepted)

    def test_missing_old_archive_after_issuance_refused(self):
        self.old.unlink()
        with self.assertRaises(OSError):
            self.accepted()

    def test_operator_grant_bytes_tampered_refused(self):
        path = self.root / guard.ROOT_NAME / "signed-grant.json"
        path.write_bytes(path.read_bytes().replace(b'"sequence":1', b'"sequence":2'))
        self.assert_scope_refused("GRANT_OPERATOR_SIGNATURE_INVALID",
                                  self.accepted)

    def test_signed_ticket_wrong_authority_sha_refused(self):
        new = dict(self.ticket, operator_sha256="f"*64)
        self.assert_scope_refused(
            "GRANT_OPERATOR_AUTHORITY_FINGERPRINT_MISMATCH",
            lambda: self.accepted(ticket=new))

    def test_bogus_operation_ticket_refused_before_checker(self):
        new = dict(self.ticket, payload_sha256="f"*64)
        with self.assertRaisesRegex(guard.Refusal, "FD9_GRANT_ROOT_TICKET_ROLE_OR_OPERATION_UNTRUSTED"):
            self.accepted(ticket=new)
        self.assertEqual(self.calls, 0)

    def test_changed_expected_head_refused_before_checker(self):
        with self.assertRaisesRegex(guard.Refusal, "FD9_GRANT_ROOT_TICKET_ROLE_OR_OPERATION_UNTRUSTED"):
            self.accepted(head="b"*40)
        self.assertEqual(self.calls, 0)

    def test_missing_fd9_checker_refused(self):
        with self.assertRaisesRegex(guard.Refusal, "FD9_GRANT_CHECKER_REQUIRED"):
            self.accepted(checker=False)

    def test_fd9_checker_refusal_blocks_grant(self):
        def blocked():
            raise OSError("no real fd9")
        with self.assertRaisesRegex(OSError, "no real fd9"):
            self.accepted(checker=blocked)

    def test_operator_private_key_not_available_to_worker(self):
        secret = self.root / guard.ROOT_NAME / "operator-private.pem"
        self.assertFalse(secret.exists())
        self.assertFalse((self.root / guard.ROOT_NAME / "status-private.pem").exists())
        self.accepted()

    def test_foreign_file_prevents_cleanup_and_deletion(self):
        foreign = self.root / guard.ROOT_NAME / "foreign"
        foreign.write_bytes(b"another owner")
        with self.assertRaisesRegex(guard.Refusal, "FD9_GRANT_CLEANUP_FOREIGN_OR_MISSING_FILE"):
            guard.cleanup(self.root)
        self.assertTrue(foreign.exists())

    def test_signed_grant_cleanup_only_expected_files(self):
        guard.cleanup(self.root)
        self.assertFalse((self.root / guard.ROOT_NAME).exists())

    def test_real_ci_controller_mode_denies_unapproved_flags(self):
        handoff=module("stage3-native-configd-fd9-handoff.py",
                       "ci_handoff_negative_mode_contract")
        with mock.patch.dict(os.environ,
                {"ZAPRET2_STAGE3_NATIVE_GRANT_TAMPER":"wrong"},clear=True):
            with self.assertRaisesRegex(Exception,"NATIVE_GRANT_TAMPER_MODE_INVALID"):
                handoff.signed_grant_negative_mode()
        with mock.patch.dict(os.environ,
                {"ZAPRET2_STAGE3_NATIVE_GRANT_TAMPER":"1"},clear=True):
            with self.assertRaisesRegex(Exception,"NATIVE_GRANT_TAMPER_NOT_DISPOSABLE"):
                handoff.signed_grant_negative_mode()

    def test_ci_signed_byte_corruption_retains_original_signature_and_denies(self):
        handoff=module("stage3-native-configd-fd9-handoff.py",
                       "ci_handoff_signed_byte_corruption")
        signed=self.root / guard.ROOT_NAME / "signed-grant.json"
        signature=self.root / guard.ROOT_NAME / "signed-grant.sig"
        original_signature=signature.read_bytes()
        def local_fixture_read(path,maxsize=1024):
            self.assertTrue(path.is_file() and not path.is_symlink())
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
            self.assertLessEqual(path.stat().st_size,maxsize)
            return path.read_bytes()
        with mock.patch.object(handoff.base,"trusted",local_fixture_read):
            self.assertTrue(handoff.tamper_signed_grant_for_negative(self.root))
        self.assertEqual(signature.read_bytes(),original_signature)
        self.assertIn(b'"sequence":2',signed.read_bytes())
        self.assert_scope_refused("GRANT_OPERATOR_SIGNATURE_INVALID",self.accepted)
        self.assertGreaterEqual(self.calls,1)
        self.assertEqual(self.old.read_bytes(),b"test-only-old-archive")
        self.assertEqual(self.new.read_bytes(),b"test-only-new-archive")

    def test_ci_negative_refusal_ordered_before_real_pkg_and_no_fake_receipt(self):
        source=(HERE/"stage3-native-configd-fd9-handoff.py").read_text()
        worker=(HERE/"stage3-native-configd-mutating-pkg.py").read_text()
        self.assertIn("TAMPERED_SIGNED_GRANT_WRONG_WORKER_REFUSAL",source)
        self.assertIn("not AUTH_RESULT.exists() and not DONE.exists()",source)
        self.assertIn("HANDOFF_CHANGED_ORIGINAL_PKG_CONFIG_PROCESS_IPFW",source)
        self.assertIn("PASS_TEST_ONLY_SIGNED_GRANT_TAMPER_NO_PKG",source)
        self.assertIn("signed_grant_negative_mode()",source)
        self.assertLess(worker.index("grant_guard.verify("),
                        worker.index("delegate.admitted_pkg_dispatch(archive,candidate,env)"))

    def test_late_tamper_mode_denies_unapproved_and_conflicting_flags(self):
        handoff=module("stage3-native-configd-fd9-handoff.py","late_grant_mode")
        with mock.patch.dict(os.environ,
                {"ZAPRET2_STAGE3_NATIVE_LATE_GRANT_TAMPER":"bad"},clear=True):
            with self.assertRaisesRegex(Exception,"NATIVE_LATE_GRANT_TAMPER_MODE_INVALID"):
                handoff.late_signed_grant_mode()
        with mock.patch.dict(os.environ,
                {"ZAPRET2_STAGE3_NATIVE_LATE_GRANT_TAMPER":"1"},clear=True):
            with self.assertRaisesRegex(Exception,"NATIVE_LATE_GRANT_TAMPER_NOT_DISPOSABLE"):
                handoff.late_signed_grant_mode()
        env={"ZAPRET2_STAGE3_NATIVE_LATE_GRANT_TAMPER":"1",
             "ZAPRET2_STAGE3_NATIVE_LATE_GRANT_TAMPER_CI":"1",
             "GITHUB_ACTIONS":"true","ZAPRET2_STAGE3_NATIVE_MUTATING_PKG":"1",
             "ZAPRET2_STAGE3_NATIVE_MUTATING_PKG_CI":"1",
             "ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK":"1",
             "ZAPRET2_NATIVE_BUILD_CI":"1",
             "ZAPRET2_STAGE2_DELEGATED_FD9_HANDOFF":"1",
             "ZAPRET2_STAGE3_READONLY_PKG":"1",
             "ZAPRET2_STAGE3_READONLY_PKG_CI":"1"}
        with mock.patch.dict(os.environ,env,clear=True):
            self.assertTrue(handoff.late_signed_grant_mode())
        with mock.patch.dict(os.environ,{
                **env,"ZAPRET2_STAGE3_NATIVE_GRANT_TAMPER":"1",
                "ZAPRET2_STAGE3_NATIVE_GRANT_TAMPER_CI":"1"},clear=True):
            with self.assertRaisesRegex(Exception,"NATIVE_LATE_GRANT_TAMPER_NOT_DISPOSABLE"):
                handoff.late_signed_grant_mode()

    def test_first_valid_signature_then_late_byte_tamper_denies(self):
        handoff=module("stage3-native-configd-fd9-handoff.py","late_grant_bytes")
        self.assertTrue(self.accepted()["ci_operator_signature_verified"])
        signed=self.root / guard.ROOT_NAME / "signed-grant.json"
        signature=self.root / guard.ROOT_NAME / "signed-grant.sig"
        original_signature=signature.read_bytes()
        def read_owned(path,maxsize=1024):
            self.assertTrue(path.is_file() and not path.is_symlink())
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
            self.assertLessEqual(path.stat().st_size,maxsize)
            return path.read_bytes()
        with mock.patch.object(handoff.base,"trusted",read_owned):
            self.assertTrue(handoff.tamper_signed_grant_for_negative(self.root))
        self.assertEqual(signature.read_bytes(),original_signature)
        self.assertIn(b'"sequence":2',signed.read_bytes())
        self.assert_scope_refused("GRANT_OPERATOR_SIGNATURE_INVALID",self.accepted)

    def test_native_late_grant_barrier_between_two_checks(self):
        worker=(HERE/"stage3-native-configd-mutating-pkg.py").read_text()
        controller=(HERE/"stage3-native-configd-fd9-handoff.py").read_text()
        workflow=(HERE.parent/".github/workflows/stage2-native-delegated-fd9-handoff.yml").read_text()
        first=worker.index("approval=grant_guard.verify(")
        marker=worker.index("initial_signed_grant_verified':True")
        second=worker.index("second=grant_guard.verify(")
        dispatch=worker.index("delegate.admitted_pkg_dispatch(archive,candidate,env)",second)
        self.assertLess(first,marker)
        self.assertLess(marker,second)
        self.assertLess(second,dispatch)
        self.assertIn("LATE_GRANT_PRE_DISPATCH_BARRIER_UNQUALIFIED",controller)
        self.assertIn("LATE_GRANT_SIGNED_BYTES_NOT_CHANGED",controller)
        self.assertIn("HANDOFF_CHANGED_ORIGINAL_PKG_CONFIG_PROCESS_IPFW",controller)
        self.assertIn("PASS_TEST_ONLY_LATE_SIGNED_GRANT_TAMPER_NO_PKG",controller)
        self.assertIn("configd-native-late-signed-grant-no-pkg:",workflow)
        self.assertIn("ZAPRET2_STAGE3_NATIVE_LATE_GRANT_TAMPER_CI=1",workflow)

    def test_post_final_archive_mode_requires_disposable_optin_and_exclusion(self):
        handoff=module("stage3-native-configd-fd9-handoff.py",
                       "test_post_final_archive_mode")
        with mock.patch.dict(os.environ,
                {"ZAPRET2_STAGE3_NATIVE_POST_FINAL_ARCHIVE_TAMPER":"bogus"},clear=True):
            with self.assertRaisesRegex(Exception,
                    "NATIVE_POST_FINAL_ARCHIVE_MODE_INVALID"):
                handoff.post_final_archive_mode()
        with mock.patch.dict(os.environ,
                {"ZAPRET2_STAGE3_NATIVE_POST_FINAL_ARCHIVE_TAMPER":"1"},clear=True):
            with self.assertRaisesRegex(Exception,
                    "NATIVE_POST_FINAL_ARCHIVE_NOT_DISPOSABLE"):
                handoff.post_final_archive_mode()
        env={"ZAPRET2_STAGE3_NATIVE_POST_FINAL_ARCHIVE_TAMPER":"1",
             "ZAPRET2_STAGE3_NATIVE_POST_FINAL_ARCHIVE_TAMPER_CI":"1",
             "GITHUB_ACTIONS":"true",
             "ZAPRET2_STAGE3_NATIVE_MUTATING_PKG":"1",
             "ZAPRET2_STAGE3_NATIVE_MUTATING_PKG_CI":"1",
             "ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK":"1",
             "ZAPRET2_NATIVE_BUILD_CI":"1",
             "ZAPRET2_STAGE2_DELEGATED_FD9_HANDOFF":"1",
             "ZAPRET2_STAGE3_READONLY_PKG":"1",
             "ZAPRET2_STAGE3_READONLY_PKG_CI":"1"}
        with mock.patch.dict(os.environ,env,clear=True):
            self.assertTrue(handoff.post_final_archive_mode())
        with mock.patch.dict(os.environ,{
                **env,"ZAPRET2_STAGE3_NATIVE_LATE_ARCHIVE_TAMPER":"1",
                "ZAPRET2_STAGE3_NATIVE_LATE_ARCHIVE_TAMPER_CI":"1"},clear=True):
            with self.assertRaisesRegex(Exception,
                    "NATIVE_POST_FINAL_ARCHIVE_NOT_DISPOSABLE"):
                handoff.post_final_archive_mode()
        with mock.patch.dict(os.environ,{
                **env,"ZAPRET2_STAGE3_NATIVE_LATE_JOURNAL":"1",
                "ZAPRET2_STAGE3_NATIVE_LATE_JOURNAL_CI":"1"},clear=True):
            with self.assertRaisesRegex(Exception,
                    "NATIVE_POST_FINAL_ARCHIVE_NOT_DISPOSABLE"):
                handoff.post_final_archive_mode()

    def test_post_final_archive_barrier_after_signature_before_dispatch(self):
        worker=(HERE/"stage3-native-configd-mutating-pkg.py").read_text()
        controller=(HERE/"stage3-native-configd-fd9-handoff.py").read_text()
        workflow=(HERE.parent/".github/workflows/stage2-native-delegated-fd9-handoff.yml").read_text()
        signed=worker.index("second=grant_guard.verify(")
        final_ok=worker.index("need(second==approval",signed)
        barrier=worker.index("'final_signed_grant_verified':True",final_ok)
        recheck=worker.index("        # Dispatch-side last archive identity+SHA recheck",barrier)
        dispatch=worker.index("rc,out,err=delegate.admitted_pkg_dispatch(archive,candidate,env)",recheck)
        self.assertLess(signed,final_ok)
        self.assertLess(final_ok,barrier)
        self.assertLess(barrier,recheck)
        self.assertLess(recheck,dispatch)
        self.assertIn("attest_candidate_fd9(product,candidate,selected_sha,revision,expected_inode)\n        rc,out,err",worker)
        self.assertIn("POST_FINAL_ARCHIVE_BARRIER_IDENTITY_UNQUALIFIED",controller)
        self.assertIn("POST_FINAL_ARCHIVE_WRONG_WORKER_REFUSAL",controller)
        self.assertIn("NATIVE_PKG_ARCHIVE_SHA256_MISMATCH",controller)
        self.assertIn("PASS_TEST_ONLY_POST_FINAL_ARCHIVE_DISPATCH_VETO",controller)
        self.assertIn("configd-native-post-final-archive-veto-no-pkg:",workflow)
        self.assertIn("ZAPRET2_STAGE3_NATIVE_POST_FINAL_ARCHIVE_TAMPER_CI=1",workflow)

    def test_post_final_archive_must_not_report_pkg_or_product_acceptance(self):
        worker=(HERE/"stage3-native-configd-mutating-pkg.py").read_text()
        controller=(HERE/"stage3-native-configd-fd9-handoff.py").read_text()
        self.assertIn("'final_signed_grant_verified':True",worker)
        self.assertIn("RESUME_TEST_ONLY_AFTER_POST_FINAL_ARCHIVE_BYTE_TAMPER",worker)
        self.assertIn("not DONE.exists() and not DONE.is_symlink()",controller)
        self.assertIn("not AUTH_RESULT.exists() and not AUTH_RESULT.is_symlink()",controller)
        self.assertIn("HANDOFF_CHANGED_ORIGINAL_PKG_CONFIG_PROCESS_IPFW",controller)
        self.assertIn("base.check_original_fd9_busy()",controller)
        self.assertIn("'ci_dispatch_side_archive_refused_under_fd9':post_final",controller)
        self.assertIn("'final_valid_grant_then_dispatch_archive_veto':post_final",controller)
        self.assertIn("'final_owner_check_to_pkg_race_closed':False",controller)
        self.assertIn("'lh08_ac11_accepted':False",controller)
        self.assertIn("'root_pkg_bypass_protected':False",worker)

    def test_native_worker_requires_grant_before_pkg(self):
        source = (HERE / "stage3-native-configd-mutating-pkg.py").read_text()
        self.assertIn("SIGNED_OPERATOR_GRANT_TICKET_REQUIRED_BEFORE_PKG", source)
        first = source.index("grant_guard.verify(")
        pkg = source.index("delegate.admitted_pkg_dispatch(archive,candidate,env)")
        self.assertLess(first, pkg)
        self.assertIn("FD9_SIGNED_OPERATOR_GRANT_DRIFT_BEFORE_PKG", source)
        for forbidden in ("stock_firmware_web_protected':True",
                          "root_pkg_bypass_protected':True",
                          "lh08_ac11_accepted':True"):
            self.assertNotIn(forbidden, source)

    def test_controller_requires_grant_receipt_on_real_native_pkg(self):
        source = (HERE / "stage3-native-configd-fd9-handoff.py").read_text()
        self.assertIn("base.create_owned(AUTHORITY", source)
        self.assertIn("base.trusted(AUTHORITY,950)", source)
        self.assertIn("AUTHORITY.unlink()", source)
        self.assertIn("ci_operator_signature_verified", source)
        self.assertIn("issuer.cleanup(ROOT)", source)
        self.assertIn("base.create_owned(AUTH_RESULT", source)
        self.assertIn("base.trusted(AUTH_RESULT,1000)", source)
        self.assertIn("AUTH_RESULT.unlink()", source)
        self.assertIn("CI_SIGNED_PKG_GRANT_NATIVE_RECEIPT_UNQUALIFIED", source)
        self.assertIn("CI_SIGNED_PKG_GRANT_REPORT_INCONSISTENT", source)
        self.assertIn("'revision'} and", source)
        self.assertIn("base.trusted(TICKET,500)", source)


if __name__ == "__main__":
    unittest.main()
