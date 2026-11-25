#!/usr/bin/env python3
"""TZ6v5 S10b2b2b3b2a: full old tree and real P2c process contract tests.

New candidate: original real P2e/S08c/S08d/Voice/schema3 S10a root and one
actual bound S10b1 journal. Active-tree unit tests use real original seal
and complete files. Prior-old fixture is a copy of genuinely sealed release
with a test-retargeted old owner identity; it does NOT attest an installed
old native generation. Native PID, ps/kernel argv and OPNsense Config/WAN
outcomes are injected ONLY at readers, never claimed as owner-live proof.
"""
import importlib.util
from dataclasses import replace
from pathlib import Path
import os
import shutil
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(B))
import neutral_schema3_previous_physical as gate
from neutral_schema3_saved_wan_preimage import SavedWanPreimageReceipt
from shared_apply_seal import create_seal, verify_seal
from shared_apply_operation import SharedOperationError

spec = importlib.util.spec_from_file_location(
    "actual_original_s10b3b1",
    ROOT / "scripts/test-tz6v5-s10b2b2b3b1-original-saved-wan-preimage.py")
if spec is None or spec.loader is None:
    raise RuntimeError("ORIGINAL_S10B3B1_SOURCE_REQUIRED")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

PID = 5432
MON = 6543
BIRTH = "Wed Nov 25 09:04:03 2026"
MONBIRTH = "Wed Nov 25 09:04:02 2026"


class FullPreviousOwnerReadOnly(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        m.SavedWanOriginalFd9.setUpClass()

    @classmethod
    def tearDownClass(cls):
        m.SavedWanOriginalFd9.tearDownClass()

    def setUp(self):
        self.f = m.SavedWanOriginalFd9("runTest")
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        current = self.f.f.f
        self.old_work = current.parent / self.f.f.old["id"]
        shutil.copytree(current.work, self.old_work, copy_function=shutil.copy2)
        (self.old_work / "bundle-seal.json").unlink()
        create_seal(self.old_work, owner=os.geteuid())
        self.active = Path(current.tmp.name) / "active"
        shutil.copytree(self.old_work / "release", self.active,
                        copy_function=shutil.copy2)
        self.pidfile = Path(current.tmp.name) / "child.pid"
        self.monitorfile = Path(current.tmp.name) / "monitor.pid"
        self.prior = gate.PriorRunningToken(PID, BIRTH, MON, MONBIRTH, "3" * 64)
        self.saved = SavedWanPreimageReceipt(
            current.generation, self.f.candidate.sha256, self.f.f.old["id"],
            "ready", self.f.pinned["detail"]["base"],
            self.f.pinned["detail"]["candidate"], "tun0")
        self.pinned = current.original.read()

    def attest(self):
        f = self.f.f.f
        return gate._attest_previous_physical(
            generation=f.generation, native=f.native,
            effective=f.effective, enabled=True, parent=f.parent,
            journal_root=f.journal_root, owner_uid=os.geteuid(),
            active=self.active, child_pidfile=self.pidfile,
            monitor_pidfile=self.monitorfile)

    def patches(self, saved=None, native=None):
        a = patch.object(gate, "_attest_saved_wan",
                         return_value=self.saved if saved is None else saved)
        b = patch.object(gate, "_running_native",
                         return_value=self.prior if native is None else native)
        return a, b

    def test_real_complete_sealed_release_matches_all_active_bytes(self):
        original = verify_seal(self.old_work, owner=os.geteuid())
        expect = original["sha256"]["release"]
        self.assertEqual(
            gate._full_prior_tree(self.old_work, self.active, os.geteuid()), expect)
        a, b = self.patches()
        with a as old, b as process:
            receipt = self.attest()
        self.assertEqual(receipt.old_release_sha256, expect)
        self.assertEqual(receipt.active_release_sha256, expect)
        self.assertEqual(receipt.root_sha256, self.f.candidate.sha256)
        self.assertEqual(receipt.prior_pid, PID)
        self.assertEqual(receipt.prior_birth, BIRTH)
        self.assertEqual(receipt.supervisor_pid, MON)
        self.assertEqual(receipt.supervisor_birth, MONBIRTH)
        self.assertEqual(receipt.resolved_wan_device, "tun0")
        self.assertEqual(old.call_count, 2)
        self.assertEqual(process.call_count, 2)
        self.assertEqual(self.f.f.f.original.read(), self.pinned)
        self.assertFalse(receipt.physical_transition_allowed)
        self.assertFalse(receipt.promotion_allowed)
        self.assertEqual(receipt.authorization, "NONE")
        self.assertTrue(receipt.stopped_epoch_pending)
        self.assertTrue(receipt.retired_observer_ack_pending)
        self.assertTrue(receipt.original_kernel_executable_inode_pending)
        with self.assertRaisesRegex(SharedOperationError, "preactivation gate"):
            self.f.f.f.original.advance("activating", self.f.f.f.detail)

    def test_all_active_bytes_including_noncritical_extra_enforced(self):
        target = self.active / "tcp-ports.txt"
        self.assertTrue(target.exists())
        original = target.read_bytes()
        a, b = self.patches()
        try:
            target.write_bytes(original + b"#tamper\n")
            with a, b, self.assertRaises(gate.PreviousPhysicalRefused):
                self.attest()
        finally:
            target.write_bytes(original)

    def test_extra_active_file_refused(self):
        extra = self.active / "foreign-injection.txt"
        extra.write_bytes(b"new")
        a, b = self.patches()
        with a, b, self.assertRaises(gate.PreviousPhysicalRefused):
            self.attest()

    def test_deleted_active_file_refused(self):
        (self.active / "tcp-ports.txt").unlink()
        a, b = self.patches()
        with a, b, self.assertRaises(gate.PreviousPhysicalRefused):
            self.attest()

    def test_symlink_and_hardlink_in_active_release_refused(self):
        target = self.active / "tcp-ports.txt"
        target.unlink()
        target.symlink_to("udp-ports.txt")
        with self.assertRaises(gate.SharedBundleError):
            gate._full_prior_tree(self.old_work, self.active, os.geteuid())
        target.unlink()
        os.link(self.active / "udp-ports.txt", target)
        with self.assertRaises(gate.SharedBundleError):
            gate._full_prior_tree(self.old_work, self.active, os.geteuid())

    def test_tampered_old_sealed_release_refused(self):
        (self.old_work / "release" / "udp-ports.txt").write_bytes(b"tampered\n")
        a, b = self.patches()
        with a, b, self.assertRaises(gate.PreviousPhysicalRefused):
            self.attest()

    def test_changed_original_journal_during_pid_read_refused(self):
        def race(*args, **kwargs):
            self.f.f.f.original.advance("restored", self.f.f.f.detail)
            return self.prior
        a, _ = self.patches()
        with a, patch.object(gate, "_running_native", side_effect=race), \
             self.assertRaises(gate.PreviousPhysicalRefused):
            self.attest()
        self.assertEqual(self.f.f.f.original.read()["phase"], "restored")

    def test_previous_process_birth_changed_between_double_check(self):
        a, _ = self.patches()
        with a, patch.object(
                gate, "_running_native", side_effect=(
                    self.prior, replace(self.prior, started="Thu Nov 26 01:00:00 2026"))), \
             self.assertRaises(gate.PreviousPhysicalRefused):
            self.attest()

    def test_stopped_or_unbound_old_and_claimed_authorization_refused(self):
        for candidate in (
            replace(self.saved, previous_state="stopped"),
            replace(self.saved, authorization="APPLY"),
            replace(self.saved, physical_transition_allowed=True),
            replace(self.saved, previous_generation="f" * 32),
            replace(self.saved, config_base_sha256="f" * 64),
        ):
            with self.subTest(candidate=candidate.status):
                a, b = self.patches(saved=candidate)
                with a, b, self.assertRaises(gate.PreviousPhysicalRefused):
                    self.attest()

    def test_absent_prior_is_not_cold_authorization(self):
        prior = self.f.f.f.original.read()
        prior.pop("previous")
        self.f.f.f.original._persist_record(prior)
        a, b = self.patches()
        with a, b, self.assertRaises(gate.PreviousPhysicalRefused):
            self.attest()

    def test_running_original_process_contract_reuses_native_p2c_kernel(self):
        old = self.old_work / "release"
        argv = (old / "dvtws.args").read_bytes()
        expected = [gate.CHILD_EXEC] + argv.decode("utf-8").split() + [
            "--sockarg=0x200", "--user=nobody"]
        monitor_args = [gate.MONITOR_EXEC, str(self.pidfile),
                        str(Path(gate.MONITOR_EXEC).with_name("zapret_service.sh")),
                        gate.CHILD_EXEC, str(PID)]
        args = dict(previous_release=old, owner_uid=os.geteuid(),
                    child_pidfile=self.pidfile,
                    monitor_pidfile=self.monitorfile, runner=Mock())
        def good(**changes):
            runner_values = {
                "_pid": (PID, MON, PID, MON),
                "_snapshot": ((BIRTH, [gate.CHILD_EXEC]),
                              (MONBIRTH, monitor_args),
                              (BIRTH, [gate.CHILD_EXEC]),
                              (MONBIRTH, monitor_args)),
                "_run": f"{PID} {gate.CHILD_EXEC} --example\n"
                        f"{MON} {gate.MONITOR_EXEC} {self.pidfile}\n",
                "_owner_snapshot": True,
                "argv": (expected, expected),
            }
            runner_values.update(changes)
            with patch.object(gate, "_pid",
                              side_effect=runner_values["_pid"]), \
                 patch.object(gate, "_snapshot",
                              side_effect=runner_values["_snapshot"]), \
                 patch.object(gate, "_run",
                              return_value=runner_values["_run"]), \
                 patch.object(gate, "_owner_snapshot",
                              return_value=runner_values["_owner_snapshot"]):
                return gate._running_native(
                    **args, argv_reader=Mock(side_effect=runner_values["argv"]))
        result = good()
        self.assertEqual(result.pid, PID)
        self.assertEqual(result.monitor_pid, MON)
        self.assertEqual(result.started, BIRTH)
        self.assertEqual(result.monitor_started, MONBIRTH)
        self.assertRegex(result.argv_sha256, "^[0-9a-f]{64}$")
        for changes in (
            {"_pid": (PID, PID)},
            {"_pid": (PID, MON, PID + 1, MON)},
            {"_snapshot": ((BIRTH, ["/evil/dvtws2"]),
                           (MONBIRTH, monitor_args))},
            {"_snapshot": ((BIRTH, [gate.CHILD_EXEC]),
                           (MONBIRTH, ["/bin/sh", "/unrelated"]))},
            {"_snapshot": (("not a timestamp", [gate.CHILD_EXEC]),
                           (MONBIRTH, monitor_args))},
            {"_snapshot": ((BIRTH, [gate.CHILD_EXEC]),
                           (MONBIRTH, monitor_args),
                           (BIRTH, [gate.CHILD_EXEC]),
                           ("Thu Nov 26 01:00:00 2026", monitor_args))},
            {"_run": f"{PID} {gate.CHILD_EXEC} old\n"
                     f"9999 {gate.CHILD_EXEC} foreign\n"
                     f"{MON} {gate.MONITOR_EXEC} x\n"},
            {"_run": f"{PID} {gate.CHILD_EXEC} old\n"
                     f"{MON} {gate.MONITOR_EXEC} x\n"
                     f"8888 /bin/sh {gate.MONITOR_EXEC} extra\n"},
            {"_owner_snapshot": False},
            {"argv": (expected + ["--bad"], expected)},
            {"argv": (expected, expected + ["--bad"])},
        ):
            with self.subTest(changes=changes), \
                 self.assertRaises(
                     (gate.PreviousPhysicalRefused, gate.GenerationRefused)):
                good(**changes)

    def test_public_fd9_refuses_without_reading_old_tree(self):
        with patch.object(gate, "require_lifecycle_lock",
                          side_effect=RuntimeError("no lock")), \
             patch.object(gate, "_attest_saved_wan") as saved, \
             patch.object(gate, "_full_prior_tree") as tree:
            with self.assertRaisesRegex(gate.PreviousPhysicalRefused, "FD9"):
                gate.attest_previous_physical_under_fd9(
                    generation=self.f.f.f.generation, native=self.f.f.f.native,
                    effective=self.f.f.f.effective, enabled=True)
            saved.assert_not_called()
            tree.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
