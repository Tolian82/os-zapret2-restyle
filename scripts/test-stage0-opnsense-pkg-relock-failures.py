#!/usr/bin/env python3
"""Offline fail-closed native private pkg lock lifecycle contracts."""
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest import mock

SRC = Path(__file__).with_name("stage0-opnsense-pkg-relock-failures.py")
spec = importlib.util.spec_from_file_location("relock", SRC)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
REAL_FIXTURE_STATE = m.fixture_state


def cp(rc=0, output=""):
    return subprocess.CompletedProcess([], rc, output, "")


class NativeFixture:
    def __init__(self):
        self.locked = True
        self.state = (m.OLD, b"old\n")
        self.calls = []
        self.replace_rc = 0
        self.unlock_rc = 0
        self.relock_rc = 0
        self.erase_when_replacing = False

    def call(self, args, env=None):
        self.calls.append(tuple(args))
        op = args[3]
        if op == "lock" and args[4] == "-l":
            return cp(0, m.NAME + "\n" if self.locked else "")
        if op == "lock" and args[4] == "-y":
            if self.relock_rc == 0:
                self.locked = True
            return cp(self.relock_rc)
        if op == "unlock":
            if self.unlock_rc == 0:
                self.locked = False
            return cp(self.unlock_rc)
        if op == "add":
            if self.erase_when_replacing:
                self.state = ("ABSENT", None)
            elif self.replace_rc == 0:
                self.state = (m.NEW, b"direct\n")
            return cp(self.replace_rc)
        raise AssertionError(args)

    def status(self, pkg, env, marker):
        return self.state


GOOD = {"status": "PASS_COLD_READ_ONLY_SNAPSHOT_ONLY",
        "old_package": "os-zapret2-restyle-0.6.2_1",
        "real_old_status": "STOPPED",
        "safe_pkg_transaction_authorized": False}


class ReLockContracts(unittest.TestCase):
    def setUp(self):
        # These tests model atomic fixture state without writing a pkgdb.
        # The real name-qualified pkg query is tested separately below.
        patcher = mock.patch.object(
            m, "fixture_state", side_effect=lambda native, pkg, env, marker: native.state)
        patcher.start()
        self.addCleanup(patcher.stop)

    def args(self, native, probe, fail=False):
        return (native, ["pkg", "-o", "REPO_AUTOUPDATE=false"], {},
                Path("/synthetic-only"), Path("/private-new.pkg"), probe)

    def test_exact_private_fixture_name_used_in_real_pkgdb_query(self):
        class QueryNative:
            def __init__(self):
                self.args = []
            def call(self, args, env=None):
                self.args.append(args)
                return cp(0, m.OLD + "\n")
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder) / "fixture"
            marker.write_bytes(b"old\n")
            native = QueryNative()
            self.assertEqual(
                REAL_FIXTURE_STATE(
                    native, ["pkg", "-o", "REPO_AUTOUPDATE=false"], {}, marker),
                (m.OLD, b"old\n"))
            self.assertEqual(
                native.args[0][-3:], ["query", "%n|%v", m.NAME])
            self.assertNotIn("zapret2-stage0-fd9-hook-fixture",
                             native.args[0][-1])

    def test_native_pkg_empty_lock_list_exact_rc1_is_not_an_error(self):
        native = mock.Mock()
        native.call.return_value = cp(1, "No locked packages were found\n")
        self.assertFalse(m.is_locked(
            native, ["pkg", "-o", "REPO_AUTOUPDATE=false"], {}))
        self.assertEqual(native.call.call_args.args[0][-2:], ["lock", "-l"])

    def test_native_pkg_unexpected_rc1_is_refused_not_treated_as_empty(self):
        native = mock.Mock()
        native.call.return_value = cp(1, "unrelated command failed\n")
        with self.assertRaisesRegex(m.Refusal, "NATIVE_LOCK_LIST_UNAVAILABLE"):
            m.is_locked(native, ["pkg", "-o", "REPO_AUTOUPDATE=false"], {})

    def test_native_pkg_list_contains_exact_fixture_lock(self):
        native = mock.Mock()
        native.call.return_value = cp(0, m.NAME + "\n")
        self.assertTrue(m.is_locked(
            native, ["pkg", "-o", "REPO_AUTOUPDATE=false"], {}))

    def test_success_relocks_new_native_pkg(self):
        n = NativeFixture()
        p = mock.Mock(return_value=GOOD)
        out = m.controlled_fixture_replace(*self.args(n, p))
        self.assertEqual(out["result"], m.NEW)
        self.assertTrue(out["relocked"])
        self.assertTrue(n.locked)
        self.assertEqual(p.call_count, 2)
        self.assertTrue(out["unprotected_unlocked_window_exists"])

    def test_unknown_owner_refuses_before_pkg_unlock(self):
        n = NativeFixture()
        with self.assertRaisesRegex(m.Refusal, "GENUINE_OLD_COLD"):
            m.controlled_fixture_replace(*self.args(
                n, lambda: {**GOOD, "status": "UNKNOWN"}))
        self.assertTrue(n.locked)
        self.assertFalse(any("unlock" in a for a in n.calls))
        self.assertFalse(any("add" in a for a in n.calls))

    def test_running_owner_refuses_before_unlock(self):
        n = NativeFixture()
        with self.assertRaisesRegex(m.Refusal, "GENUINE_OLD_COLD"):
            m.controlled_fixture_replace(*self.args(
                n, lambda: {**GOOD, "real_old_status": "RUNNING"}))
        self.assertTrue(n.locked)

    def test_bogus_archive_identity_refuses(self):
        n = NativeFixture()
        with self.assertRaisesRegex(m.Refusal, "GENUINE_OLD_COLD"):
            m.controlled_fixture_replace(*self.args(
                n, lambda: {**GOOD, "old_package": "foreign"}))
        self.assertTrue(n.locked)

    def test_proof_must_not_misstate_transaction_authorization(self):
        n = NativeFixture()
        with self.assertRaisesRegex(m.Refusal, "GENUINE_OLD_COLD"):
            m.controlled_fixture_replace(*self.args(
                n, lambda: {**GOOD, "safe_pkg_transaction_authorized": True}))
        self.assertTrue(n.locked)

    def test_injected_failure_relocks_original(self):
        n = NativeFixture()
        with self.assertRaisesRegex(m.Refusal, "INJECTED_PRE_PKG"):
            m.controlled_fixture_replace(*self.args(n, lambda: GOOD),
                                        inject_after_unlock=True)
        self.assertTrue(n.locked)
        self.assertEqual(n.state, (m.OLD, b"old\n"))
        self.assertFalse(any("add" in a for a in n.calls))

    def test_second_preflight_failure_also_relocks(self):
        n = NativeFixture()
        count = [0]
        def unstable():
            count[0] += 1
            return GOOD if count[0] == 1 else {**GOOD, "status": "FOREIGN"}
        with self.assertRaisesRegex(m.Refusal, "GENUINE_OLD_COLD"):
            m.controlled_fixture_replace(*self.args(n, unstable))
        self.assertTrue(n.locked)
        self.assertEqual(count[0], 2)
        self.assertEqual(n.state, (m.OLD, b"old\n"))

    def test_pkg_replacement_failure_relocks_old(self):
        n = NativeFixture()
        n.replace_rc = 70
        with self.assertRaisesRegex(m.Refusal, "PRIVATE_REPLACEMENT_FAILED"):
            m.controlled_fixture_replace(*self.args(n, lambda: GOOD))
        self.assertTrue(n.locked)
        self.assertEqual(n.state, (m.OLD, b"old\n"))

    def test_unlock_failure_keeps_old_locked(self):
        n = NativeFixture()
        n.unlock_rc = 7
        with self.assertRaisesRegex(m.Refusal, "PKG_UNLOCK_UNAVAILABLE"):
            m.controlled_fixture_replace(*self.args(n, lambda: GOOD))
        self.assertTrue(n.locked)
        self.assertEqual(n.state, (m.OLD, b"old\n"))

    def test_initial_unlocked_fixture_refuses(self):
        n = NativeFixture()
        n.locked = False
        with self.assertRaisesRegex(m.Refusal, "PACKAGE_NOT_INITIALLY_LOCKED"):
            m.controlled_fixture_replace(*self.args(n, lambda: GOOD))
        self.assertFalse(any("unlock" in a for a in n.calls))

    def test_initial_missing_pkg_refuses(self):
        n = NativeFixture()
        n.state = ("ABSENT", None)
        with self.assertRaisesRegex(m.Refusal, "INITIAL_PRIVATE_FIXTURE"):
            m.controlled_fixture_replace(*self.args(n, lambda: GOOD))
        self.assertTrue(n.locked)

    def test_relock_failure_refuses_even_if_pkg_succeeded(self):
        n = NativeFixture()
        n.relock_rc = 71
        with self.assertRaisesRegex(m.Refusal, "NATIVE_RELOCK_FAILED"):
            m.controlled_fixture_replace(*self.args(n, lambda: GOOD))
        self.assertFalse(n.locked)
        self.assertEqual(n.state[0], m.NEW)

    def test_missing_package_after_replacement_is_not_safe(self):
        n = NativeFixture()
        n.erase_when_replacing = True
        with self.assertRaisesRegex(m.Refusal, "NO_VERIFIED_PKG_TO_RELOCK"):
            m.controlled_fixture_replace(*self.args(n, lambda: GOOD))
        self.assertFalse(n.locked)

    def test_native_relock_response_must_be_verified(self):
        n = NativeFixture()
        n.relock_rc = 0
        with mock.patch.object(m, "is_locked", side_effect=[True, False, False]):
            with self.assertRaisesRegex(m.Refusal, "NATIVE_RELOCK_NOT_VERIFIED"):
                m.controlled_fixture_replace(*self.args(n, lambda: GOOD))

    def test_not_a_product_service_or_package_manager_integration(self):
        source = SRC.read_text()
        for phrase in ('"product_safety_acceptance_passed": False',
                       '"production_transaction_guard_implemented": False',
                       '"concurrent_root_pkg_race_tested": False',
                       '"real_plugin_pkg_replaced": False'):
            self.assertIn(phrase, source)
        self.assertIn("PKG_DBDIR", source)
        self.assertNotIn("pkg autoremove", source)

    def test_non_freebsd_never_installs_original(self):
        class Linux:
            sysname = "Linux"
            machine = "x86_64"
        inst = mock.Mock()
        guest = mock.Mock()
        with mock.patch.object(m.os, "geteuid", return_value=0), \
             mock.patch.object(m.os, "uname", return_value=Linux()), \
             self.assertRaisesRegex(m.Refusal, "ONLY_ROOT_DISPOSABLE"):
            m.verify_actual_guest(Path("/untrusted"), guest, inst,
                                  mock.Mock(), mock.Mock(), mock.Mock(), mock.Mock())
        inst.install_and_verify.assert_not_called()
        guest.observe.assert_not_called()


if __name__ == "__main__":
    unittest.main()
