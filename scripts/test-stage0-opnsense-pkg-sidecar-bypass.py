#!/usr/bin/env python3
"""Offline contract tests for separate pkg guard and direct-native-pkg bypass."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

SRC = Path(__file__).with_name("stage0-opnsense-pkg-sidecar-bypass.py")
spec = importlib.util.spec_from_file_location("stage0_sidecar", SRC)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
FIXTURE = m.FIXTURE
TRACE = ["old:pre-install", "old:post-install",
         "guarded:pre-install:OLD_STATUS_STOPPED",
         "guarded:post-install:OLD_STATUS_STOPPED",
         "direct:pre-install", "direct:post-install"]
GUARDED = (FIXTURE + "|0.6.2_40", b"guarded\n")
DIRECT = (FIXTURE + "|0.6.2_41", b"direct\n")


class SidecarContracts(unittest.TestCase):
    def test_fixture_name_not_real_predecessor(self):
        self.assertNotEqual(FIXTURE, "os-zapret2-restyle")
        self.assertIn("stage0", FIXTURE)

    def test_classify_two_native_pkg_successes_with_bypass(self):
        self.assertEqual(m.classify(0, 0, GUARDED, DIRECT, TRACE),
                         "SIDECAR_COMPATIBLE_BUT_DIRECT_PKG_BYPASSES_LOCK")

    def test_cooperating_pkg_failure_refused(self):
        with self.assertRaisesRegex(m.Refusal, "GUARDED_FIXTURE"):
            m.classify(73, 0, GUARDED, DIRECT, TRACE)

    def test_wrong_payload_refused(self):
        with self.assertRaisesRegex(m.Refusal, "GUARDED_FIXTURE"):
            m.classify(0, 0, (GUARDED[0], b"other\n"), DIRECT, TRACE)

    def test_direct_pkg_did_not_bypass_refused(self):
        with self.assertRaisesRegex(m.Refusal, "DIRECT_PKG"):
            m.classify(0, 1, GUARDED, DIRECT, TRACE)

    def test_missing_real_status_hook_observation_refused(self):
        with self.assertRaisesRegex(m.Refusal, "GENUINE_OLD_SERVICE_HOOK"):
            m.classify(0, 0, GUARDED, DIRECT,
                       [x for x in TRACE if x != "guarded:post-install:OLD_STATUS_STOPPED"])

    def test_double_status_hook_observation_refused(self):
        with self.assertRaisesRegex(m.Refusal, "GENUINE_OLD_SERVICE_HOOK"):
            m.classify(0, 0, GUARDED, DIRECT,
                       TRACE + ["guarded:pre-install:OLD_STATUS_STOPPED"])

    def test_old_fixture_order_refused(self):
        with self.assertRaisesRegex(m.Refusal, "INITIAL_OLD_FIXTURE_HOOK"):
            m.classify(0, 0, GUARDED, DIRECT, TRACE[1:])

    def test_direct_hooks_not_traced_refused(self):
        with self.assertRaisesRegex(m.Refusal, "DIRECT_PKG_HOOK"):
            m.classify(0, 0, GUARDED, DIRECT, TRACE[:-1])

    def test_non_target_refused_before_original_pkg_install(self):
        class Linux:
            sysname = "Linux"
            machine = "x86_64"
        guest = mock.Mock()
        installed = mock.Mock()
        fd9 = mock.Mock()
        with mock.patch.object(m.os, "geteuid", return_value=0), \
             mock.patch.object(m.os, "uname", return_value=Linux()):
            with self.assertRaisesRegex(m.Refusal, "REQUIRES_ROOT_FREEBSD"):
                m.prove(Path("/never"), guest, installed, fd9)
        installed.install_and_verify.assert_not_called()
        guest.observe.assert_not_called()

    def test_synthetic_hook_template_uses_genuine_old_status_readonly(self):
        source = SRC.read_text()
        self.assertIn('status >/dev/null 2>&1', source)
        self.assertIn('OLD_STATUS_STOPPED', source)
        self.assertIn('OLD_STATUS_REFUSED', source)
        self.assertNotIn('"pkg", "delete"', source)
        self.assertNotIn('SERVICE + \'" stop', source)

    def test_report_refuses_product_safety_claim(self):
        source = SRC.read_text()
        for field in ('"transaction_guard_enforced_for_direct_pkg": False',
                      '"product_safety_acceptance_passed": False',
                      '"stage0_closed": False',
                      '"real_predecessor_replaced": False'):
            self.assertIn(field, source)

    def test_identification_and_synthetic_manifest_only(self):
        self.assertEqual(m.PHASES,
                         ("pre-install", "post-install", "pre-deinstall", "post-deinstall"))
        for role in ("old", "guarded", "direct"):
            self.assertIn(role, ("old", "guarded", "direct"))
        self.assertIn("PKG_DBDIR", SRC.read_text())
        self.assertIn("os.O_NOFOLLOW", SRC.read_text())


if __name__ == "__main__":
    unittest.main()
