#!/usr/bin/env python3
"""Offline safety contracts for orphaned synthetic pkg unlock and child SIGKILL."""
import importlib.util
from pathlib import Path
import stat
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "stage0-opnsense-pkg-orphaned-unlock.py"
spec = importlib.util.spec_from_file_location("orphaned_pkg", SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

RECORD = {
    "schema": 1, "experiment": "synthetic-private-pkgdb-only",
    "package": m.NAME, "expected_pkgdb_identity": m.OLD,
    "expected_payload_sha256": m.EXPECTED_SHA,
    "pkgdb_path": "/tmp/synthetic-db",
    "phase": "PENDING_PRIVATE_UNLOCK",
    "production_guard": False,
}


_ORIGINAL_LSTAT = Path.lstat


def _as_root_lstat(path):
    # Offline CI is unprivileged; model only st_uid while retaining real
    # file type and mode. The actual FreeBSD guest uses true root lstat().
    st = _ORIGINAL_LSTAT(path)
    return SimpleNamespace(st_mode=st.st_mode, st_uid=0)


class OrphanedUnlockContracts(unittest.TestCase):
    def test_exact_original_state_unlocked_only_candidate(self):
        self.assertEqual(
            m.recovery_decision(RECORD, (m.OLD, m.PAYLOAD), False),
            "CANDIDATE_RELOCK_ONLY_AFTER_REAL_OWNER_RECHECK")

    def test_exact_old_state_already_locked_not_recovered(self):
        self.assertEqual(
            m.recovery_decision(RECORD, (m.OLD, m.PAYLOAD), True),
            "ALREADY_LOCKED_UNCHANGED_SYNTHETIC_PKG")

    def test_absent_private_pkg_refuses_relock(self):
        self.assertEqual(
            m.recovery_decision(RECORD, ("ABSENT", None), False),
            "REFUSE_MUTATED_OR_ABSENT_SYNTHETIC_PKG")

    def test_same_version_wrong_payload_refuses_relock(self):
        self.assertEqual(
            m.recovery_decision(RECORD, (m.OLD, b"evil\n"), False),
            "REFUSE_MUTATED_OR_ABSENT_SYNTHETIC_PKG")

    def test_successor_pkg_not_relocked_as_original(self):
        self.assertEqual(
            m.recovery_decision(RECORD, (m.NAME + "|0.6.2_41", b"direct\n"), False),
            "REFUSE_MUTATED_OR_ABSENT_SYNTHETIC_PKG")

    def test_foreign_journal_identity_refused(self):
        for item in ("package", "expected_pkgdb_identity",
                     "expected_payload_sha256", "phase", "schema"):
            bad = dict(RECORD)
            bad[item] = "foreign"
            with self.subTest(item=item), self.assertRaises(m.Refusal):
                m.recovery_decision(bad, (m.OLD, m.PAYLOAD), False)

    def test_durable_record_created_before_unlock_and_verified(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "intent.json"
            expected = m.durable_intent(path, Path("/tmp/synthetic-db"))
            self.assertEqual(expected, RECORD)
            with mock.patch.object(Path, "lstat", _as_root_lstat):
                self.assertEqual(m.read_intent(path, Path("/tmp/synthetic-db")), RECORD)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            with self.assertRaises(FileExistsError):
                m.durable_intent(path, Path("/tmp/synthetic-db"))

    def test_wrong_durable_db_identity_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "intent.json"
            m.durable_intent(path, Path("/tmp/synthetic-db"))
            with mock.patch.object(Path, "lstat", _as_root_lstat):
                with self.assertRaisesRegex(m.Refusal, "DURABLE_RECORD_IDENTITY"):
                    m.read_intent(path, Path("/tmp/different-db"))

    def test_symlink_durable_record_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "record"
            m.durable_intent(target, Path("/tmp/synthetic-db"))
            link = Path(folder) / "link"
            link.symlink_to(target)
            with mock.patch.object(Path, "lstat", _as_root_lstat):
                with self.assertRaisesRegex(m.Refusal, "UNTRUSTED_ORPHANED"):
                    m.read_intent(link, Path("/tmp/synthetic-db"))

    def test_loose_mode_durable_record_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "intent.json"
            m.durable_intent(path, Path("/tmp/synthetic-db"))
            path.chmod(0o666)
            with mock.patch.object(Path, "lstat", _as_root_lstat):
                with self.assertRaisesRegex(m.Refusal, "UNTRUSTED_ORPHANED"):
                    m.read_intent(path, Path("/tmp/synthetic-db"))

    def test_kill_only_owned_controller_child(self):
        class FakeChild:
            def __init__(self):
                import io
                self.pid = 76543
                self.stdout = io.StringIO("UNLOCKED\n")
                self.stderr = io.StringIO("")
                self.alive = True
            def poll(self):
                return None if self.alive else -9
            def wait(self, timeout=None):
                return -9
            def kill(self):
                self.alive = False
        child = FakeChild()
        actions = []
        def fake_kill(pid, sig):
            self.assertEqual(pid, child.pid)
            self.assertEqual(sig, m.signal.SIGKILL)
            child.alive = False
        with mock.patch.object(m.subprocess, "Popen", return_value=child), \
             mock.patch.object(m.select, "select",
                               return_value=([child.stdout], [], [])), \
             mock.patch.object(m.os, "kill", side_effect=fake_kill):
            report = m.kill_owned_child_after_unlock(
                {}, lambda: actions.append("private pkg") or 0)
        self.assertEqual(actions, ["private pkg"])
        self.assertEqual(report["child_exit_signal"], "SIGKILL")
        self.assertTrue(report["killed_child_pid_only"])

    def test_unknown_child_unlock_message_refuses_and_reaps(self):
        class FakeChild:
            def __init__(self):
                import io
                self.stdout = io.StringIO("UNLOCK_FAILED:71\n")
                self.stderr = io.StringIO("")
                self.alive = True
            def poll(self):
                return None if self.alive else -9
            def kill(self):
                self.alive = False
            def wait(self, timeout=None):
                return -9
        child = FakeChild()
        with mock.patch.object(m.subprocess, "Popen", return_value=child), \
             mock.patch.object(m.select, "select",
                               return_value=([child.stdout], [], [])):
            with self.assertRaisesRegex(m.Refusal, "OWN_CHILD_UNLOCK_REFUSED"):
                m.kill_owned_child_after_unlock({})
        self.assertFalse(child.alive)

    def test_original_predecessor_exact_cold_owner_required(self):
        good = {
            "status": "PASS_COLD_READ_ONLY_SNAPSHOT_ONLY",
            "old_package": "os-zapret2-restyle-0.6.2_1",
            "real_old_status": "STOPPED",
            "safe_pkg_transaction_authorized": False,
        }
        guard = mock.Mock()
        guard.snapshot.return_value = good
        self.assertEqual(m.prove_original_cold(guard, Path("/old.pkg")), good)
        for changed in (
                {"status": "FOREIGN"},
                {"real_old_status": "RUNNING"},
                {"old_package": "os-zapret2-restyle-0.6.2_43"},
                {"safe_pkg_transaction_authorized": True}):
            with self.subTest(changed=changed):
                guard.snapshot.return_value = {**good, **changed}
                with self.assertRaisesRegex(
                        m.Refusal, "ORIGINAL_COLD_OWNER_SNAPSHOT_CHANGED"):
                    m.prove_original_cold(guard, Path("/old.pkg"))

    def test_only_disposable_freebsd_is_accepted(self):
        class Linux:
            sysname = "Linux"
            machine = "x86_64"
        guest = mock.Mock()
        with mock.patch.object(m.os, "geteuid", return_value=0), \
             mock.patch.object(m.os, "uname", return_value=Linux()), \
             self.assertRaisesRegex(m.Refusal, "ONLY_ROOT_DISPOSABLE"):
            m.prove(Path("/invalid"), guest, mock.Mock(), mock.Mock(),
                    mock.Mock(), mock.Mock(), mock.Mock())
        guest.observe.assert_not_called()

    def test_no_real_plugin_package_mutation_or_false_acceptance(self):
        s = SOURCE.read_text(encoding="utf-8")
        for marker in ('"product_safety_acceptance_passed": False',
                       '"production_owner_guard_implemented": False',
                       '"automatic_power_loss_recovery_implemented": False',
                       '"real_original_plugin_replaced": False',
                       '"actual_power_loss_or_automatic_boot_recovery_tested": False',
                       'PKG_DBDIR'):
            self.assertIn(marker, s)
        self.assertIn("os.kill(child.pid, signal.SIGKILL)", s)
        self.assertNotIn("pkg delete -f os-zapret2", s)


if __name__ == "__main__":
    unittest.main()
