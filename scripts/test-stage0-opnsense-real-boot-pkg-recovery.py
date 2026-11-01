#!/usr/bin/env python3
"""Offline safety contracts for native disposable OPNsense real boot witness."""
import importlib.util
import json
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

SOURCE = Path(__file__).with_name("stage0-opnsense-real-boot-pkg-recovery.py")
spec = importlib.util.spec_from_file_location("stage0_real_boot", SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class BootWitnessContracts(unittest.TestCase):
    def test_real_kernel_transition_and_syshook_marker_required(self):
        self.assertTrue(m.verify_boot_transition("sec=1", "sec=2", "sec=2"))

    def test_same_kern_boottime_refused(self):
        with self.assertRaisesRegex(m.Refusal, "ACTUAL_GUEST_REBOOT_NOT_PROVEN"):
            m.verify_boot_transition("sec=1", "sec=1", "sec=1")

    def test_syshook_from_wrong_boot_refused(self):
        with self.assertRaisesRegex(m.Refusal, "START_SYSHOOK_NOT_RUN"):
            m.verify_boot_transition("sec=1", "sec=2", "sec=3")

    def test_empty_boot_witness_refused(self):
        for args in (("", "b", "b"), ("a", "", "b"), ("a", "b", "")):
            with self.subTest(args=args), self.assertRaisesRegex(
                    m.Refusal, "BOOT_WITNESS_EMPTY"):
                m.verify_boot_transition(*args)

    def test_kernel_boot_id_is_native_not_python_process_time(self):
        p = subprocess.CompletedProcess([], 0, "{ sec = 2026, usec = 123 }\n", "")
        with mock.patch.object(m.subprocess, "run", return_value=p) as called:
            self.assertEqual(m.boot_id(), "{ sec = 2026, usec = 123 }")
        self.assertEqual(called.call_args.args[0],
                         ["sysctl", "-n", "kern.boottime"])

    def test_kernel_boot_id_bad_return_refused(self):
        p = subprocess.CompletedProcess([], 71, "", "error")
        with mock.patch.object(m.subprocess, "run", return_value=p), \
             self.assertRaisesRegex(m.Refusal, "KERN_BOOT_ID_NOT_OBSERVABLE"):
            m.boot_id()

    def test_boot_hook_only_observes_kernel_id_and_has_no_pkg_mutation(self):
        hook = m.BOOT_HOOK_BYTES.decode("ascii")
        self.assertIn("#!/bin/sh", hook)
        self.assertIn("sysctl -n kern.boottime", hook)
        self.assertIn(str(m.BOOT_MARKER), hook)
        for forbidden in ("pkg ", "ipfw ", "configctl ", "zapret_service.sh",
                          "rm -", "reboot", "shutdown"):
            self.assertNotIn(forbidden, hook)

    def test_durable_create_is_exclusive_and_exact_permissions(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "intent"
            m.write_exclusive(p, b"test\n")
            self.assertEqual(p.read_bytes(), b"test\n")
            self.assertEqual(stat.S_IMODE(p.stat().st_mode), 0o600)
            with self.assertRaises(FileExistsError):
                m.write_exclusive(p, b"overwrite")

    def test_untrusted_symlink_file_refuses_before_read(self):
        with tempfile.TemporaryDirectory() as folder:
            real = Path(folder) / "original"
            link = Path(folder) / "link"
            real.write_bytes(b"old")
            link.symlink_to(real)
            with self.assertRaisesRegex(m.Refusal, "UNTRUSTED_DISPOSABLE_FILE"):
                m.qualified_file(link, 0o600)

    def test_untrusted_wrong_mode_refuses(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "evidence"
            p.write_bytes(b"data")
            p.chmod(0o666)
            with self.assertRaisesRegex(m.Refusal, "UNTRUSTED_DISPOSABLE_FILE"):
                m.qualified_file(p, 0o600)

    def test_exact_verified_file_root_contract(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "evidence"
            p.write_bytes(b"data")
            p.chmod(0o600)
            stat_obj = SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_uid=0)
            with mock.patch.object(Path, "lstat", return_value=stat_obj):
                self.assertEqual(m.qualified_file(p, 0o600), b"data")

    def test_guest_must_be_root_freebsd_amd64(self):
        class Linux:
            sysname = "Linux"
            machine = "x86_64"
        with mock.patch.object(m.os, "geteuid", return_value=0), \
             mock.patch.object(m.os, "uname", return_value=Linux()), \
             self.assertRaisesRegex(m.Refusal, "ONLY_DISPOSABLE_ROOT_FREEBSD"):
            m.root_guest()

    def test_original_old_owner_cold_is_required(self):
        original = {"status": "PASS_READ_ONLY_PROVENANCE",
                    "package": "os-zapret2-restyle-0.6.2_1"}
        cold = {"status": "PASS_COLD_READ_ONLY_SNAPSHOT_ONLY",
                "old_package": "os-zapret2-restyle-0.6.2_1",
                "real_old_status": "STOPPED",
                "safe_pkg_transaction_authorized": False}
        installed = mock.Mock()
        installed.pre.run.return_value = b"guest\n"
        installed.pre.run_guest.return_value = original
        guard = mock.Mock()
        guard.snapshot.return_value = cold
        self.assertEqual(m.verify_original(Path("/old.pkg"), installed, guard),
                         original)
        for wrong in (
            {"real_old_status": "RUNNING"}, {"status": "UNKNOWN"},
            {"safe_pkg_transaction_authorized": True},
            {"old_package": "foreign"}):
            guard.snapshot.return_value = {**cold, **wrong}
            with self.subTest(wrong=wrong), self.assertRaisesRegex(
                    m.Refusal, "PUBLISHED_OLD_OWNER_NOT_COLD_AND_PROVEN"):
                m.verify_original(Path("/old.pkg"), installed, guard)

    def test_published_old_package_provenance_is_required(self):
        installed = mock.Mock()
        installed.pre.run.return_value = b"guest\n"
        installed.pre.run_guest.return_value = {
            "status": "FAIL", "package": "os-zapret2-restyle-0.6.2_1"}
        guard = mock.Mock()
        with self.assertRaisesRegex(m.Refusal, "PUBLISHED_OLD_PKG_PROVENANCE"):
            m.verify_original(Path("/old.pkg"), installed, guard)
        guard.snapshot.assert_not_called()

    def test_no_automatic_recovery_or_product_safety_false(self):
        code = SOURCE.read_text()
        for field in ('"automatic_recovery_during_boot_implemented": False',
                      '"power_loss_recovery_tested": False',
                      '"package_manager_enforced_owner_transaction": False',
                      '"product_safety_acceptance_passed": False',
                      '"stage0_closed": False',
                      "private_pkg", "PKG_NAME", "cache-after-prepare"):
            if field == "cache-after-prepare":
                continue
            self.assertIn(field, code)
        self.assertNotIn('["pkg", "delete", "os-zapret2-restyle"]', code)
        self.assertNotIn("subprocess.run([\"reboot\"", code)


if __name__ == "__main__":
    unittest.main()
