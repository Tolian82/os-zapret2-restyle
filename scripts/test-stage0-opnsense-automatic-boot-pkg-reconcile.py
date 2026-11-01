#!/usr/bin/env python3
"""Offline fail-closed contracts: disposable native OPNsense boot-only pkg guard."""
import importlib.util
import hashlib
import json
from pathlib import Path
import stat
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

SOURCE = Path(__file__).with_name("stage0-opnsense-automatic-boot-pkg-reconcile.py")
spec = importlib.util.spec_from_file_location("synthetic_auto_boot_guard", SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

BOOTTIME = {
    "schema": 1, "experiment": "private-pkgdb-opnsense-real-boot-only",
    "synthetic_name": "zapret2-stage0-sidecar-only-fixture",
    "scenarios": ["unchanged", "direct_delete", "tampered_intent"],
    "prepared_kern_boottime": "{ sec = 100, usec = 10 }",
}


class StartSyshookContracts(unittest.TestCase):
    def test_valid_new_kernel_boot_accepted(self):
        self.assertTrue(m.require_unchanged_boot(
            BOOTTIME, "{ sec = 200, usec = 20 }"))

    def test_original_boot_cannot_trigger_automatic_pkg_lock(self):
        with self.assertRaisesRegex(m.Refusal, "REAL_KERNEL_BOOT_NOT_PROVEN"):
            m.require_unchanged_boot(BOOTTIME, BOOTTIME["prepared_kern_boottime"])

    def test_untrusted_previous_boot_record_refused(self):
        for edit in ({"schema": 2}, {"experiment": "production"},
                     {"synthetic_name": "os-zapret2-restyle"},
                     {"scenarios": ["unchanged"]}):
            with self.subTest(edit=edit), self.assertRaisesRegex(
                    m.Refusal, "PRIOR_DISPOSABLE_BOOT_RECORD_UNQUALIFIED"):
                m.require_unchanged_boot(
                    {**BOOTTIME, **edit}, "{ sec = 200 }")

    def test_empty_new_kernel_identity_refused(self):
        with self.assertRaisesRegex(m.Refusal, "REAL_KERNEL_BOOT_NOT_PROVEN"):
            m.require_unchanged_boot(BOOTTIME, "")

    def test_boot_start_hook_is_only_test_named_and_fixed_scope(self):
        hook = m.HOOK_BYTES.decode()
        self.assertIn("rc.syshook.d/start/98-zapret2-stage0", str(m.AUTO_HOOK))
        self.assertIn("stage0-opnsense-automatic-boot-pkg-reconcile.py boot", hook)
        self.assertNotIn("os-zapret2-restyle pkg", hook)
        self.assertNotIn("ipfw", hook)
        self.assertNotIn("configctl", hook)
        self.assertIn("/root/stage0-fresh-process-recovery-", hook)

    def test_no_global_pkgdb_mutation_in_prepared_native_paths(self):
        source = SOURCE.read_text()
        self.assertIn('pkg + ["delete", "-y", fresh.NAME]', source)
        self.assertIn("private_pkg(scope)", source)
        self.assertIn('"product_safety_acceptance_passed": False', source)
        self.assertIn('"all_privileged_pkg_entrypoints_enforced": False', source)
        self.assertNotIn('["pkg", "delete", "os-zapret2-restyle"]', source)

    def test_code_manifest_must_bind_every_copied_file(self):
        self.assertEqual(len(set(m.SOURCE_FILES)), len(m.SOURCE_FILES))
        self.assertIn("stage0-opnsense-prepkg-readonly.py", m.SOURCE_FILES)
        self.assertIn("stage0-installed-predecessor-readonly.py", m.SOURCE_FILES)
        self.assertIn("stage0-opnsense-old-service-fd9.py", m.SOURCE_FILES)
        self.assertIn("stage0-opnsense-pkg-fresh-recovery.py", m.SOURCE_FILES)

    def test_changed_source_hash_refused_before_pkg_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code_dir = root / "boot-code"
            code_dir.mkdir(mode=0o700)
            files = {}
            for name in m.SOURCE_FILES:
                path = code_dir / name
                path.write_bytes(b"original")
                path.chmod(0o600)
                files[name] = hashlib.sha256(b"original").hexdigest()
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps(files))
            manifest.chmod(0o600)
            stat_root = SimpleNamespace(st_uid=0, st_mode=stat.S_IFDIR | 0o700)
            with mock.patch.object(m, "CODE_DIR", code_dir), \
                 mock.patch.object(m, "CODE_MANIFEST", manifest), \
                 mock.patch.object(m, "qualified", return_value=manifest.read_bytes()), \
                 mock.patch.object(Path, "stat", return_value=stat_root), \
                 mock.patch.object(Path, "lstat", return_value=SimpleNamespace(
                     st_uid=0, st_mode=stat.S_IFREG | 0o600)):
                self.assertTrue(m.copied_code_digest())
                (code_dir / m.SOURCE_FILES[0]).write_bytes(b"changed")
                with self.assertRaisesRegex(m.Refusal, "BOOT_CODE_HASH_CHANGED"):
                    m.copied_code_digest()

    def test_exact_root_owned_file_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "owned"
            p.write_bytes(b"test")
            p.chmod(0o600)
            with mock.patch.object(Path, "lstat", return_value=SimpleNamespace(
                st_mode=stat.S_IFREG | 0o600, st_uid=0)):
                self.assertEqual(m.qualified(p), b"test")

    def test_untrusted_test_owned_file_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "untrusted"
            p.write_bytes(b"x")
            p.chmod(0o644)
            with self.assertRaisesRegex(m.Refusal, "DISPOSABLE_ROOT_FILE_UNTRUSTED"):
                m.qualified(p)

    def test_symlink_file_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "real"
            q = Path(tmp) / "link"
            p.write_bytes(b"x")
            q.symlink_to(p)
            with self.assertRaisesRegex(m.Refusal, "DISPOSABLE_ROOT_FILE_UNTRUSTED"):
                m.qualified(q)

    def test_original_old_owner_must_be_proven(self):
        boot = mock.Mock()
        installed = mock.Mock()
        guard = mock.Mock()
        boot.verify_original.return_value = {
            "status": "PASS_READ_ONLY_PROVENANCE",
            "package": "os-zapret2-restyle-0.6.2_1",
        }
        self.assertEqual(
            m.require_old_cold(boot, installed, guard)["package"],
            "os-zapret2-restyle-0.6.2_1")
        boot.verify_original.return_value = {
            "status": "PASS_READ_ONLY_PROVENANCE",
            "package": "some-foreign-package",
        }
        with self.assertRaisesRegex(m.Refusal, "AUTHENTIC_OLD_OWNER_NOT_PROVEN"):
            m.require_old_cold(boot, installed, guard)

    def test_fail_closed_unmodified_missing_fixture(self):
        fresh = mock.Mock()
        fresh.Refusal = type("ForeignOriginal", (Exception,), {})
        fresh.recover.side_effect = fresh.Refusal(
            "REFUSE_CHANGED_OR_MISSING_PRIVATE_FIXTURE")
        locks = mock.Mock()
        locks.Refusal = type("LockRefusal", (Exception,), {})
        orphan = mock.Mock()
        orphan.Refusal = type("OrphanRefusal", (Exception,), {})
        boot = mock.Mock()
        boot.verify_original.return_value = {
            "status": "PASS_READ_ONLY_PROVENANCE",
            "package": "os-zapret2-restyle-0.6.2_1",
        }
        result = m.recover_one("direct_delete", fresh, boot, mock.Mock(),
                               mock.Mock(), mock.Mock(), locks, orphan)
        self.assertEqual(result["status"], "REFUSED")
        self.assertEqual(result["reason"],
                         "REFUSE_CHANGED_OR_MISSING_PRIVATE_FIXTURE")
        locks.lock_exact.assert_not_called()

    def test_positive_only_when_new_interpreter_verified_native_relock(self):
        fresh = mock.Mock()
        fresh.Refusal = type("ForeignOriginal", (Exception,), {})
        fresh.recover.return_value = {
            "status": "RECOVERED_UNCHANGED_PRIVATE_FIXTURE",
        }
        locks = mock.Mock()
        locks.Refusal = type("LockRefusal", (Exception,), {})
        orphan = mock.Mock()
        orphan.Refusal = type("OrphanRefusal", (Exception,), {})
        boot = mock.Mock()
        boot.verify_original.return_value = {
            "status": "PASS_READ_ONLY_PROVENANCE",
            "package": "os-zapret2-restyle-0.6.2_1",
        }
        result = m.recover_one("unchanged", fresh, boot, mock.Mock(),
                               mock.Mock(), mock.Mock(), locks, orphan)
        self.assertEqual(result["status"], "RECOVERED_UNCHANGED_PRIVATE_FIXTURE")

    def test_unknown_success_classification_refused(self):
        fresh = mock.Mock()
        fresh.Refusal = type("ForeignOriginal", (Exception,), {})
        fresh.recover.return_value = {"status": "UNVERIFIED"}
        locks = mock.Mock()
        locks.Refusal = type("LockRefusal", (Exception,), {})
        orphan = mock.Mock()
        orphan.Refusal = type("OrphanRefusal", (Exception,), {})
        boot = mock.Mock()
        boot.verify_original.return_value = {
            "status": "PASS_READ_ONLY_PROVENANCE",
            "package": "os-zapret2-restyle-0.6.2_1",
        }
        with self.assertRaisesRegex(m.Refusal, "RECOVERY_RETURNED_UNKNOWN_SUCCESS"):
            m.recover_one("unchanged", fresh, boot, mock.Mock(),
                          mock.Mock(), mock.Mock(), locks, orphan)

    def test_boot_report_is_not_product_acceptance(self):
        s = SOURCE.read_text()
        for claim in (
            '"production_boot_service_installed": False',
            '"direct_root_pkg_exclusion_proved": False',
            '"actual_power_loss_tested": False',
            '"production_owner_guard_implemented": False',
            '"real_original_plugin_replaced": False',
            '"product_safety_acceptance_passed": False',
            '"stage0_closed": False',
        ):
            self.assertIn(claim, s)


if __name__ == "__main__":
    unittest.main()
