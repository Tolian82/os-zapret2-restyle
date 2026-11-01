#!/usr/bin/env python3
"""Offline native-private-pkg fresh interpreter recovery refusal contracts."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

SOURCE = Path(__file__).with_name("stage0-opnsense-pkg-fresh-recovery.py")
spec = importlib.util.spec_from_file_location("stage0_fresh_process", SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
OLD = (m.OLD, m.PAYLOAD)
COLD = {"status": "PASS_COLD_READ_ONLY_SNAPSHOT_ONLY",
        "old_package": "os-zapret2-restyle-0.6.2_1",
        "real_old_status": "STOPPED",
        "safe_pkg_transaction_authorized": False}
INTENT = {"schema": 1, "package": m.NAME,
          "expected_pkgdb_identity": m.OLD,
          "expected_payload_sha256": "not-used-in-mock",
          "phase": "PENDING_PRIVATE_UNLOCK"}


def scaffolding(state=OLD, locked=False):
    guard = mock.Mock()
    guard.snapshot.return_value = COLD
    native = mock.Mock()
    locks = mock.Mock()
    locks.fixture_state.return_value = state
    locks.is_locked.return_value = locked
    orphan = mock.Mock()
    orphan.Refusal = m.Refusal  # Real imported module exposes exception class
    orphan.read_intent.return_value = INTENT
    if state != OLD:
        orphan.recovery_decision.return_value = "REFUSE_MUTATED_OR_ABSENT_SYNTHETIC_PKG"
    elif locked:
        orphan.recovery_decision.return_value = "ALREADY_LOCKED_UNCHANGED_SYNTHETIC_PKG"
    else:
        orphan.recovery_decision.return_value = "CANDIDATE_RELOCK_ONLY_AFTER_REAL_OWNER_RECHECK"
    return guard, native, locks, orphan


class FreshRecoveryContracts(unittest.TestCase):
    def test_unchanged_needs_cold_before_and_after_relock(self):
        guard, native, locks, orphan = scaffolding()
        locks.is_locked.side_effect = [False, True]
        with mock.patch.object(m, "require_guest_root"), \
             mock.patch.object(m, "scope_root"):
            r = m.recover(Path("/private/unchanged"), Path("/old.pkg"),
                          guard, native, locks, orphan)
        self.assertEqual(r["status"], "RECOVERED_UNCHANGED_PRIVATE_FIXTURE")
        self.assertEqual(guard.snapshot.call_count, 3)
        locks.lock_exact.assert_called_once()
        self.assertFalse(r["product_safety_acceptance_passed"])

    def test_idempotent_already_locked_does_not_lock_again(self):
        guard, native, locks, orphan = scaffolding(locked=True)
        with mock.patch.object(m, "require_guest_root"), \
             mock.patch.object(m, "scope_root"):
            r = m.recover(Path("/private/unchanged"), Path("/old.pkg"),
                          guard, native, locks, orphan)
        self.assertEqual(r["status"], "ALREADY_LOCKED_UNCHANGED_PRIVATE_FIXTURE")
        locks.lock_exact.assert_not_called()

    def test_removed_package_refuses_without_relock(self):
        guard, native, locks, orphan = scaffolding(("ABSENT", None))
        with mock.patch.object(m, "require_guest_root"), \
             mock.patch.object(m, "scope_root"), \
             self.assertRaisesRegex(m.Refusal, "REFUSE_CHANGED_OR_MISSING"):
            m.recover(Path("/private/direct_delete"), Path("/old.pkg"),
                      guard, native, locks, orphan)
        locks.lock_exact.assert_not_called()

    def test_changed_package_refuses_without_relock(self):
        guard, native, locks, orphan = scaffolding((m.NAME + "|0.6.2_43", b"other"))
        with mock.patch.object(m, "require_guest_root"), \
             mock.patch.object(m, "scope_root"), \
             self.assertRaises(m.Refusal):
            m.recover(Path("/private/direct_delete"), Path("/old.pkg"),
                      guard, native, locks, orphan)
        locks.lock_exact.assert_not_called()

    def test_invalid_real_old_owner_refuses_before_record_read(self):
        guard, native, locks, orphan = scaffolding()
        guard.snapshot.return_value = {**COLD, "real_old_status": "RUNNING"}
        with mock.patch.object(m, "require_guest_root"), \
             mock.patch.object(m, "scope_root"), \
             self.assertRaisesRegex(m.Refusal, "UNQUALIFIED_GENUINE_OLD_OWNER"):
            m.recover(Path("/private/unknown_owner"), Path("/old.pkg"),
                      guard, native, locks, orphan)
        orphan.read_intent.assert_not_called()
        locks.lock_exact.assert_not_called()

    def test_false_pkg_authorization_refused(self):
        guard = mock.Mock()
        guard.snapshot.return_value = {**COLD, "safe_pkg_transaction_authorized": True}
        with self.assertRaisesRegex(m.Refusal, "UNQUALIFIED_GENUINE_OLD_OWNER"):
            m.original_cold(guard, Path("/archive"))

    def test_tampered_durable_record_refuses_before_pkg_inspection(self):
        guard, native, locks, orphan = scaffolding()
        orphan.read_intent.side_effect = m.Refusal("FOREIGN_DURABLE_RECORD")
        with mock.patch.object(m, "require_guest_root"), \
             mock.patch.object(m, "scope_root"), \
             self.assertRaisesRegex(m.Refusal, "FOREIGN_DURABLE_RECORD"):
            m.recover(Path("/private/tampered_intent"), Path("/old.pkg"),
                      guard, native, locks, orphan)
        locks.fixture_state.assert_not_called()
        locks.lock_exact.assert_not_called()

    def test_relock_command_failed_never_returns_success(self):
        guard, native, locks, orphan = scaffolding()
        locks.lock_exact.side_effect = m.Refusal("NATIVE_RELOCK_FAILED")
        with mock.patch.object(m, "require_guest_root"), \
             mock.patch.object(m, "scope_root"), \
             self.assertRaisesRegex(m.Refusal, "NATIVE_RELOCK_FAILED"):
            m.recover(Path("/private/unchanged"), Path("/old.pkg"),
                      guard, native, locks, orphan)

    def test_relock_native_state_unverified_never_returns_success(self):
        guard, native, locks, orphan = scaffolding()
        locks.is_locked.side_effect = [False, False]
        with mock.patch.object(m, "require_guest_root"), \
             mock.patch.object(m, "scope_root"), \
             self.assertRaisesRegex(m.Refusal, "POST_RECOVERY_NATIVE_PKG_NOT_VERIFIED"):
            m.recover(Path("/private/unchanged"), Path("/old.pkg"),
                      guard, native, locks, orphan)

    def test_non_freebsd_gate_fails_before_any_pkg(self):
        class Linux:
            sysname = "Linux"
            machine = "x86_64"
        with mock.patch.object(m.os, "geteuid", return_value=0), \
             mock.patch.object(m.os, "uname", return_value=Linux()), \
             self.assertRaisesRegex(m.Refusal, "ONLY_ROOT_DISPOSABLE_FREEBSD"):
            m.require_guest_root()

    def test_scope_refuses_foreign_and_relative_targets_before_lstat(self):
        for scope in (Path("/etc/conf.d/unchanged"), Path("unchanged"),
                      Path("/tmp/stage0-fresh-process-recovery-abc/foreign"),
                      Path("/tmp/stage0-fresh-process-recovery-abc/../unchanged")):
            with self.subTest(scope=str(scope)), \
                 self.assertRaisesRegex(m.Refusal, "SCOPE_OUTSIDE_DISPOSABLE_TEST"):
                m.scope_root(scope)

    def test_fresh_recovery_command_must_report_exact_success(self):
        result = subprocess.CompletedProcess([], 0,
               'STAGE0_FRESH_RECOVERY={"status":"RECOVERED_UNCHANGED_PRIVATE_FIXTURE"}\n', "")
        with mock.patch.object(m.subprocess, "run", return_value=result) as called:
            rc, data = m.invoke_fresh_recovery(Path("/private/unchanged"),
                                               Path("/archive"))
        self.assertEqual(rc, 0)
        self.assertEqual(data["status"], "RECOVERED_UNCHANGED_PRIVATE_FIXTURE")
        args = called.call_args.args[0]
        self.assertEqual(args[2], "recover")

    def test_fresh_recovery_refusal_preserves_diagnostic(self):
        result = subprocess.CompletedProcess([], 2, "",
                     "STAGE0_FRESH_RECOVERY=REFUSED:UNQUALIFIED_GENUINE_OLD_OWNER\n")
        with mock.patch.object(m.subprocess, "run", return_value=result):
            rc, data = m.invoke_fresh_recovery(Path("/p"), Path("/archive"))
        self.assertEqual(rc, 2)
        self.assertEqual(data["reason"], "UNQUALIFIED_GENUINE_OLD_OWNER")

    def test_unexpected_subprocess_exit_refused(self):
        result = subprocess.CompletedProcess([], 73, "", "")
        with mock.patch.object(m.subprocess, "run", return_value=result), \
             self.assertRaisesRegex(m.Refusal, "RECOVERY_PROCESS_UNEXPECTED_EXIT"):
            m.invoke_fresh_recovery(Path("/p"), Path("/archive"))

    def test_product_safety_denials_and_private_scope_in_source(self):
        source = SOURCE.read_text(encoding="utf-8")
        for field in ('"actual_opnsense_reboot_or_power_loss_tested": False',
                      '"automatic_boot_recovery_implemented": False',
                      '"real_original_plugin_replaced": False',
                      '"product_safety_acceptance_passed": False',
                      '"stage0_closed": False',
                      "PKG_DBDIR", "scope_root(scope)"):
            self.assertIn(field, source)
        self.assertNotIn('["pkg", "delete", "os-zapret2-restyle"]', source)


if __name__ == "__main__":
    unittest.main()
