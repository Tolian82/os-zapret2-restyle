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
            # Simulated external writer/race, not an original recovery.
            self.f.f.f.original._persist_record({**self.f.f.f.original.read(), "phase": "restored"})
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
            replace(self.saved, previous_generation="0" * 32),
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


class FinalBoundRuntimeReadOnly(unittest.TestCase):
    """Existing native readers are injected; actual final IPFW comparison and
    temporary producer inode identities are exercised. Not FreeBSD acceptance.
    """

    def test_final_running_epoch_and_kernel_refusals(self):
        import json
        import tempfile
        from contextlib import ExitStack
        from types import SimpleNamespace
        from voice_firewall_transaction import TABLE_PREFIX

        generation, digest = "a" * 32, "b" * 64
        record = {"phase": "config-saved",
                  "detail": {"id": generation, "candidate": digest},
                  "manifest": {"schema": 1, "root_sha256": "c" * 64}}
        root = {"schema": 1, "generation": generation,
                "service": {"enabled": True, "target_mode": "list"}}
        manifest = {"rule_base": 19000, "rule_max": 19010,
                    "rules": {19000: ["divert"]}, "tables": {}}
        token = gate.PriorRunningToken(PID, BIRTH, MON, MONBIRTH, "d" * 64)
        adapter = SimpleNamespace(rule_base=19000, rule_max=19099,
            list_rules=Mock(return_value=manifest["rules"]),
            get_table=Mock(return_value=None))
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            producer = Path(tmp)
            pending = producer / "pending"
            files = []
            proof = SimpleNamespace(operation_id=generation, generation=generation,
                                    owner_candidate_sha256=digest,
                                    owner=SimpleNamespace(pid=PID, started=BIRTH))
            epoch = Mock(return_value={"files": files, "pretraffic_sha256": "a" * 64})
            queue = SimpleNamespace(pending=pending, _verify=Mock())
            # The independent platform, original locks, immutable receipts,
            # full tree and process readers are qualified separately. Inject
            # their outcomes here; never turn this test into a native PASS.
            stack.enter_context(patch("sys.platform", "freebsd15"))
            stack.enter_context(patch("os.geteuid", return_value=0))
            stack.enter_context(patch.object(gate, "require_lifecycle_lock"))
            cfg = stack.enter_context(patch(
                "auto_detect_original_lock_handoff.assert_inherited_config_fd"))
            stack.enter_context(patch.object(gate, "SharedApplyOperation",
                return_value=SimpleNamespace(read=lambda: record)))
            stack.enter_context(patch("neutral_root_stage.verify_original_operation_pins"))
            stack.enter_context(patch("neutral_root_stage._verify_original_pinned_root",
                side_effect=lambda **kw: json.dumps(root).encode()))
            stack.enter_context(patch.object(gate, "_full_prior_tree", return_value="e" * 64))
            process = stack.enter_context(patch.object(gate, "_running_native", return_value=token))
            stack.enter_context(patch("voice_ipfw_adapter.shared_release_manifest",
                                      return_value=manifest))
            factory = stack.enter_context(patch("voice_ipfw_adapter.FreeBSDIPFWAdapter",
                                                return_value=adapter))
            stack.enter_context(patch("auto_detect_minute.inspect_inert_release",
                                      return_value="inactive"))
            stack.enter_context(patch("auto_detect_owner.attest_learning_epoch_finalizing_generation",
                                      return_value=proof))
            stack.enter_context(patch("auto_detect_epoch_receipts.EpochReceipts",
                return_value=SimpleNamespace(verify_learning_stopped_epoch=epoch)))
            stack.enter_context(patch("pwd.getpwnam", return_value=SimpleNamespace(pw_gid=65534)))
            stack.enter_context(patch("auto_detect_storage.ROOT", producer))
            stack.enter_context(patch("auto_detect_storage._secure",
                                      side_effect=lambda path, **kw: path.lstat()))
            stack.enter_context(patch("auto_detect_queue.DurableInbox", return_value=queue))
            actual_uid = producer.stat().st_uid
            from neutral_schema3_quiescent_preimage import _safe_empty_directory
            stack.enter_context(patch("neutral_schema3_quiescent_preimage._safe_empty_directory",
                side_effect=lambda path, uid: _safe_empty_directory(path, actual_uid)))
            stack.enter_context(patch("neutral_schema3_quiescent_preimage._zero_processes"))
            stack.enter_context(patch("neutral_schema3_quiescent_preimage._empty_kernel",
                                      return_value="native-managed-kernel-empty"))

            def run(**kw):
                args = dict(config_fd=4, config_digest=digest, enabled=True, runtime_mode="1")
                return gate.attest_bound_candidate_final_under_fd9(record, **(args | kw))

            def refuses(**kw):
                with self.assertRaises(gate.PreviousPhysicalRefused):
                    run(**kw)

            result = run()
            self.assertEqual(result.running, token)
            self.assertEqual(result.authorization, "NONE")
            factory.assert_called_with(19000, 19099)
            adapter.list_rules.assert_called_with(19000, 19099)
            refuses(config_digest="f" * 64)
            record["phase"] = "activated"
            refuses()
            record["phase"] = "config-saved"
            adapter.get_table.side_effect = lambda name: [] if name == TABLE_PREFIX + "x_stage" else None
            refuses()
            adapter.get_table.side_effect = None
            adapter.list_rules.return_value = manifest["rules"] | {19099: ["foreign"]}
            refuses()
            adapter.list_rules.return_value = manifest["rules"]
            process.side_effect = [token, replace(token, pid=PID + 1)]
            refuses()
            process.side_effect = None
            cfg.side_effect = RuntimeError("foreign Config")
            refuses()
            cfg.side_effect = None

            (producer / "foreign").write_bytes(b"x")
            refuses()
            (producer / "foreign").unlink()
            pending.mkdir(mode=0o700)
            for name in ("inbox.txt", "debug.log", "learning-" + generation + "-1.txt"):
                path = producer / name
                path.write_bytes(b"")
                st = path.stat()
                files.append(dict(name=name, device=st.st_dev, inode=st.st_ino,
                                  nlink=st.st_nlink))
            record["phase"] = "epoch-finalizing"
            record["manifest"]["schema"] = root["schema"] = 2
            root["service"]["target_mode"] = "auto"
            self.assertRegex(run().epoch_sha256, "^[0-9a-f]{64}$")
            self.assertEqual(run().pretraffic_sha256, "a" * 64)
            epoch.side_effect = ValueError("missing epoch")
            refuses()
            epoch.side_effect = None
            proof.owner.pid += 1
            refuses()
            proof.owner.pid = PID
            (pending / "foreign").write_bytes(b"x")
            refuses()
            (pending / "foreign").unlink()
            source = producer / files[0]["name"]
            source.rename(producer / "old")
            source.write_bytes(b"")
            refuses()
            source.unlink()
            (producer / "old").rename(source)
            source.write_bytes(b"allowed append")
            self.assertRegex(run().epoch_sha256, "^[0-9a-f]{64}$")
            record["phase"] = "config-saved"
            record["manifest"]["schema"] = root["schema"] = 1
            root["service"] = {"enabled": False, "target_mode": "list"}
            refuses(enabled=False, runtime_mode="0")
            for row in files:
                (producer / row["name"]).unlink()
            pending.rmdir()
            self.assertEqual(run(enabled=False, runtime_mode="0").kernel_state,
                             "native-managed-kernel-empty")

    def test_native_terminal_writer_remains_internal(self):
        from types import SimpleNamespace
        from shared_apply_operation import SharedApplyOperation, DEFAULT_ROOT
        generation, digest = "a" * 32, "b" * 64
        from neutral_schema3_quiescent_preimage import StagedBoundRuntimeReceipt
        base = "b" * 64
        record = {"phase": "config-saved",
                  "detail": {"id": generation, "candidate": digest, "base": base},
                  "manifest": {"schema": 1, "root_sha256": "c" * 64}}
        activated = StagedBoundRuntimeReceipt(generation, "c" * 64, base,
            "d" * 64, None, None, "native-managed-kernel-empty", base)
        calls = []
        receipt = gate.FinalBoundRuntimeReceipt(generation, "c" * 64, digest,
            "d" * 64, None, None, "native-managed-kernel-empty")

        def advance(phase, expected, attest):
            self.assertEqual((phase, expected), ("committed", record))
            calls.append("wal-witness")
            if not attest():
                raise SharedOperationError("witness refused")
            return dict(record, phase=phase)

        store = SimpleNamespace(root=DEFAULT_ROOT, owner=0, read=lambda: record,
                                _advance_bound_ordinary=Mock(side_effect=advance))
        with patch("sys.platform", "freebsd15"), patch("os.geteuid", return_value=0), \
                patch("voice_ipfw_adapter.require_lifecycle_lock"), \
                patch("auto_detect_original_lock_handoff.assert_inherited_config_fd"), \
                patch("os.fsync", side_effect=lambda fd: calls.append(("fsync", fd))), \
                patch.object(gate, "attest_bound_candidate_final_under_fd9",
                             return_value=receipt) as physical:
            def finish():
                return SharedApplyOperation._finish_native_bound_ordinary(
                    store, record, config_fd=4, config_digest=digest, enabled=False,
                    runtime_mode="0", activated_receipt=activated)

            self.assertEqual(finish()["phase"], "committed")
            self.assertEqual(calls, [("fsync", 4), "wal-witness"])
            for foreign in (replace(receipt, root_sha256="e" * 64),
                            replace(receipt, release_sha256="e" * 64),
                            replace(receipt, running=SimpleNamespace(pid=5433)),
                            replace(receipt, pretraffic_sha256="f" * 64)):
                physical.return_value = foreign
                with self.assertRaises(SharedOperationError):
                    finish()
            record["found"] = {"runtime_mode": "0"}
            calls.clear()
            with self.assertRaises(SharedOperationError):
                finish()
            self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
