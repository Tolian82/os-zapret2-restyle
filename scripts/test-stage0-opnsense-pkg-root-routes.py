#!/usr/bin/env python3
"""Offline exact bounded native pkg-root-entrypoint safety contracts."""
import importlib.util
from pathlib import Path
import unittest
from unittest import mock

SOURCE = Path(__file__).with_name("stage0-opnsense-pkg-root-routes.py")
spec = importlib.util.spec_from_file_location("stage0_root_routes", SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
GOOD = {"status": "PASS_COLD_READ_ONLY_SNAPSHOT_ONLY",
        "old_package": "os-zapret2-restyle-0.6.2_1",
        "real_old_status": "STOPPED",
        "safe_pkg_transaction_authorized": False}


class NativePkgRootRoutes(unittest.TestCase):
    def test_locked_force_delete_preserved_is_bounded_only(self):
        self.assertEqual(m.classify_force("delete", m.OLD, m.OLD),
                         "NATIVE_LOCK_PRESERVED_FOR_TESTED_FORCE_COMMAND")

    def test_locked_force_add_preserved_is_bounded_only(self):
        self.assertEqual(m.classify_force("add", m.OLD, m.OLD),
                         "NATIVE_LOCK_PRESERVED_FOR_TESTED_FORCE_COMMAND")

    def test_locked_force_delete_bypass_is_hazard(self):
        self.assertEqual(
            m.classify_force("delete", m.OLD, ("ABSENT", None)),
            "LOCK_BYPASSED_BY_FORCED_DELETE")

    def test_locked_force_add_bypass_is_hazard(self):
        self.assertEqual(m.classify_force("add", m.OLD, m.NEW),
                         "LOCK_BYPASSED_BY_FORCED_ADD")

    def test_partial_mutation_never_says_safe(self):
        self.assertEqual(m.classify_force("add", m.OLD, (m.OLD[0], b"bad\n")),
                         "UNEXPECTED_PARTIAL_OR_FOREIGN_PKG_MUTATION")

    def test_initial_identity_mismatch_refuses(self):
        with self.assertRaisesRegex(m.Refusal, "UNVERIFIED_PRIVATE_BASELINE"):
            m.classify_force("add", ("ABSENT", None), m.OLD)

    def test_real_cold_old_owner_readonly_matches_exact_identity(self):
        guard = mock.Mock()
        guard.snapshot.return_value = GOOD
        self.assertEqual(m.cold(guard, Path("/genuine")), GOOD)

    def test_unknown_old_process_refuses(self):
        guard = mock.Mock()
        guard.snapshot.return_value = {**GOOD, "real_old_status": "RUNNING"}
        with self.assertRaisesRegex(m.Refusal, "OLD_OWNER_NOT_PROVEN_COLD"):
            m.cold(guard, Path("/genuine"))

    def test_unexpected_owner_archive_refuses(self):
        guard = mock.Mock()
        guard.snapshot.return_value = {**GOOD, "old_package": "foreign"}
        with self.assertRaisesRegex(m.Refusal, "OLD_OWNER_NOT_PROVEN_COLD"):
            m.cold(guard, Path("/genuine"))

    def test_foreign_process_guard_exception_is_bounded(self):
        class Refusing(Exception):
            pass
        guard = mock.Mock()
        guard.Refusal = Refusing
        guard.snapshot.side_effect = Refusing("POSSIBLE_ZAPRET_PROCESS_PRESENT")
        with self.assertRaisesRegex(m.Refusal, "POSSIBLE_ZAPRET_PROCESS_PRESENT"):
            m.cold(guard, Path("/genuine"))

    def test_no_product_safety_claim_in_source(self):
        text = SOURCE.read_text()
        for item in ('"product_safety_acceptance_passed": False',
                     '"stage0_closed": False',
                     '"genuine_running_engine_tested": False',
                     '"foreign_ipfw_kernel_tested": False',
                     '"package_manager_pre_transaction_veto_proved": False',
                     '"uncoordinated_root_pkg_excluded": False',
                     "PKG_DBDIR"):
            self.assertIn(item, text)
        self.assertNotIn('["pkg", "delete", "os-zapret2-restyle"]', text)

    def test_non_freebsd_refuses_before_any_native_guest_setup(self):
        class Linux:
            sysname = "Linux"
            machine = "x86_64"
        with mock.patch.object(m.os, "geteuid", return_value=0), \
             mock.patch.object(m.os, "uname", return_value=Linux()), \
             self.assertRaisesRegex(m.Refusal, "ONLY_DISPOSABLE_ROOT_FREEBSD"):
            m.run(Path("/old.pkg"))


if __name__ == "__main__":
    unittest.main()
