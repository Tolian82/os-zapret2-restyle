#!/usr/bin/env python3
"""Real bound schema3 root + stopped/cold source contracts, no native install."""
from contextlib import ExitStack
from dataclasses import replace
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"))
import neutral_schema3_quiescent_preimage as gate
from shared_apply_operation import SharedOperationError
from voice_firewall_transaction import VoiceFirewallError

spec = importlib.util.spec_from_file_location(
    "original_full_prior", ROOT / "scripts/test-tz6v5-s10b2b2b3b2a-original-prior-full-tree-pid.py")
if spec is None or spec.loader is None:
    raise RuntimeError("ORIGINAL_PRIOR_FIXTURE_REQUIRED")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class OriginalQuiescentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        m.FullPreviousOwnerReadOnly.setUpClass()

    @classmethod
    def tearDownClass(cls):
        m.FullPreviousOwnerReadOnly.tearDownClass()

    def setUp(self):
        self.fixture = m.FullPreviousOwnerReadOnly("runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.f = self.fixture.f.f.f
        self.active = self.fixture.active
        self.root = Path(self.f.tmp.name)
        self.backups = self.root / "backups"
        self.producer = self.root / "producer"
        self.epochs = self.root / "epochs"
        self.pidfiles = (self.fixture.pidfile, self.fixture.monitorfile,
                         self.root / "daemon.pid")
        self.saved = replace(self.fixture.saved, previous_state="stopped")
        self.config = self.fixture.f.config(self.f.generation, self.f.detail["page"])
        self.runner = Mock(return_value=Mock(
            returncode=0, stderr="", stdout="0 [kernel]\n1 /sbin/init\n123 /bin/sh\n"))
        self.adapter = Mock(spec=["rule_base", "rule_max", "list_rules", "get_table"])
        self.adapter.rule_base = 19000
        self.adapter.rule_max = 19099
        self.adapter.list_rules.return_value = {}
        self.adapter.get_table.return_value = None

    def call(self):
        return gate._attest_quiescent(
            generation=self.f.generation, native=self.f.native,
            effective=self.f.effective, enabled=True, parent=self.f.parent,
            journal_root=self.f.journal_root, owner_uid=os.geteuid(),
            active=self.active, backups=self.backups, producer=self.producer,
            epochs=self.epochs, pidfiles=self.pidfiles, runner=self.runner)

    def native_seams(self, stack, *, cold_kernel=False):
        stack.enter_context(patch.object(gate, "_native_preflight", return_value=self.config))
        stack.enter_context(patch.object(gate, "_native_wan", return_value="tun0"))
        stack.enter_context(patch.object(gate, "_attest_saved_wan", return_value=self.saved))
        stack.enter_context(patch.object(gate, "_ipfw_kernel_confirmed_absent",
                                         return_value=cold_kernel))
        stack.enter_context(patch.object(gate, "FreeBSDIPFWAdapter",
                                         return_value=self.adapter))
        return stack.enter_context(patch.object(gate, "_native_call",
                                  return_value=b"auto-detect-retire=ready\n"))

    def cold(self):
        shutil.rmtree(self.active)
        shutil.rmtree(self.fixture.old_work)
        record = self.f.original.read()
        record.pop("previous")
        self.f.original._persist_record(record)

    def lock(self):
        self.producer.mkdir(mode=0o700)
        lock = self.producer / "worker.lock"
        lock.touch(mode=0o600)
        if os.geteuid() == 0:
            os.chown(lock, 0, 0)
        lock.chmod(0o600)

    def test_real_bound_cold_root_with_actual_empty_manifest_check(self):
        self.cold()
        record = self.f.original.read()
        with ExitStack() as stack:
            retired = self.native_seams(stack)
            receipt = self.call()
            retired.assert_not_called()
        self.assertEqual(receipt.old_state, "first-install-empty")
        self.assertEqual(receipt.kernel_state, "native-managed-kernel-empty")
        self.assertEqual(receipt.retirement_state, "no-prior-data")
        self.assertEqual(receipt.root_sha256, record["manifest"]["root_sha256"])
        self.assertIsNone(receipt.previous_generation)
        self.assertFalse(receipt.physical_transition_allowed)
        self.assertEqual(receipt.authorization, "NONE")
        self.adapter.list_rules.assert_called_with(19000, 19099)
        self.assertEqual(self.f.original.read(), record)
        with self.assertRaisesRegex(SharedOperationError, "preactivation gate"):
            self.f.original.advance("activating", self.f.detail)

    def test_bound_inert_cold_restore_requires_saved_old_config_and_exact_artifacts(self):
        import json
        old = {"id": "a" * 32, "page": "strategies", "base": "b" * 64,
               "candidate": "c" * 64, "changed_fields": []}
        new = {"id": "d" * 32, "page": "strategies", "base": old["candidate"],
               "candidate": "e" * 64, "changed_fields": []}
        pin = lambda d: dict(schema=1, generation=d["id"],
                             root_sha256="f" * 64, seal_sha256="0" * 64,
                             candidate_sha256=d["candidate"])
        record = dict(schema=1, phase="activating", detail=new,
                      previous=old, manifest=pin(new), previous_manifest=pin(old))
        saved = {"result": "committed", "snapshot": old["candidate"], "enabled": "0"}
        classified = dict(result="read-only-ordinary-config-classification",
            image="base-image", base=new["base"], candidate=new["candidate"],
            snapshot=new["base"], enabled="0", commit_authorized=False,
            restore_authorized=False, save_attested=False, runtime_attested=False)
        old_hash, new_hash = "1" * 64, "2" * 64
        stage = self.active.parent / f".{self.active.name}.stage.{new['id']}"
        stage.mkdir()
        def seal(work, **_):
            return {"sha256": {"release": old_hash if work.name == old["id"] else new_hash}}
        with ExitStack() as stack:
            stack.enter_context(patch.object(gate, "require_lifecycle_lock"))
            stack.enter_context(patch.object(gate, "SharedApplyOperation",
                return_value=Mock(read=Mock(return_value=record))))
            stack.enter_context(patch.object(gate, "COMMON_ACTIVE", self.active))
            stack.enter_context(patch.object(gate, "_observe_idle_producer", return_value=None))
            stack.enter_context(patch.object(gate, "_zero_processes"))
            stack.enter_context(patch.object(gate, "inspect_inert_release",
                                             return_value="inactive"))
            pins = stack.enter_context(patch("neutral_root_stage.verify_original_operation_pins"))
            stack.enter_context(patch("neutral_root_stage._original_plan_matches", return_value=True))
            stack.enter_context(patch("shared_apply_seal.verify_seal", side_effect=seal))
            stack.enter_context(patch("shared_apply_seal._stat"))
            artifact = stack.enter_context(patch("shared_apply_seal._release_hash",
                side_effect=lambda path, uid: old_hash if path == self.active else new_hash))
            def read_config(argv):
                row = saved if argv[2] == "saved" else classified
                return (json.dumps(row) + "\n").encode()
            native = stack.enter_context(patch.object(gate, "_native_call",
                                                       side_effect=read_config))
            full = stack.enter_context(patch.object(gate, "_full_prior_tree", return_value=old_hash))
            kernel = stack.enter_context(patch.object(gate, "_empty_kernel",
                                                       return_value="native-managed-kernel-empty"))
            gate.attest_inert_bound_cold_recovery(record, restored=False)
            full.assert_not_called()
            kernel.assert_not_called()
            gate.attest_inert_bound_cold_recovery(record, restored=True)
            self.assertEqual(pins.call_count, 4)
            self.assertEqual([call.args[0][2:] for call in native.call_args_list],
                [("saved", old["id"], old["page"]),
                 ("ordinary-cold", new["id"], new["page"])] * 4)
            artifact.assert_called_with(stage, 0)
            # Terminal child inherits Config rather than invoking PHP while
            # it owns FD4, and borrows (never acquires) the original queue.
            with patch.object(sys, "platform", "freebsd15"), \
                    patch.object(os, "geteuid", return_value=0), \
                    patch("auto_detect_original_lock_handoff.assert_inherited_config_fd") as lock, \
                    patch.object(gate, "_cold_locked_producer", return_value=(None, None)) as producer:
                native.reset_mock()
                gate.attest_inert_bound_cold_recovery(
                    record, restored=True, config_fd=4, config_digest=new["base"], queue_fd=3)
                native.assert_not_called()
                self.assertEqual(producer.call_count, 2)
                self.assertGreaterEqual(lock.call_count, 5)
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    gate.attest_inert_bound_cold_recovery(
                        record, restored=True, config_fd=4, config_digest=new["candidate"], queue_fd=3)
            # An apparently saved old Config is insufficient if the original
            # successor plan reports a different image. Both recovery gates
            # must refuse it (old implementation never read this receipt).
            classified.update(image="candidate-image", snapshot=new["candidate"])
            for restored in (False, True):
                with self.assertRaises(ValueError):
                    gate.attest_inert_bound_cold_recovery(record, restored=restored)
            classified.update(image="base-image", snapshot=new["base"])
            classified["enabled"] = "1"
            with self.assertRaises(gate.QuiescentPreimageRefused):
                gate.attest_inert_bound_cold_recovery(record, restored=False)
            classified["enabled"] = "0"
            # Only ACTIVATING can use an equal model image: native save has
            # not been attempted in that phase. ACTIVATED stays ambiguous.
            equal_new = {**new, "candidate": new["base"]}
            equal = {**record, "detail": equal_new, "manifest": pin(equal_new)}
            gate.SharedApplyOperation.return_value.read.return_value = equal
            classified.update(image="base-equals-candidate", candidate=new["base"])
            gate.attest_inert_bound_cold_recovery(equal, restored=False)
            ambiguous = {**equal, "phase": "activated"}
            gate.SharedApplyOperation.return_value.read.return_value = ambiguous
            for restored in (False, True):
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    gate.attest_inert_bound_cold_recovery(ambiguous, restored=restored)
            gate.SharedApplyOperation.return_value.read.return_value = record
            classified.update(image="base-image", candidate=new["candidate"])
            # An inert candidate can roll back to an already retired Auto
            # owner, but only on its full immutable history and idle proof.
            retired = {**record, "previous_manifest": {**record["previous_manifest"], "schema": 2}}
            store = gate.SharedApplyOperation.return_value
            store.read.return_value = retired
            with patch.object(gate, "_observe_cold_retired_predecessor",
                              return_value=("a" * 64, ((1, 2, 0, "b" * 64),
                                                       (1, 3, 0, "b" * 64)))) as epoch:
                gate.attest_inert_bound_cold_recovery(retired, restored=False)
                gate.attest_inert_bound_cold_recovery(retired, restored=True)
                self.assertEqual(epoch.call_count, 4)
                epoch.side_effect = ValueError("missing retirement")
                with self.assertRaises(ValueError):
                    gate.attest_inert_bound_cold_recovery(retired, restored=False)
            store.read.return_value = record
            # A partial/corrupted stage is not terminal old-owner evidence.
            artifact.side_effect = lambda path, uid: old_hash if path == self.active else "3" * 64
            for restored in (False, True):
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    gate.attest_inert_bound_cold_recovery(record, restored=restored)
            artifact.side_effect = lambda path, uid: old_hash if path == self.active else new_hash
            saved["snapshot"] = new["candidate"]
            with self.assertRaises(gate.QuiescentPreimageRefused):
                gate.attest_inert_bound_cold_recovery(record, restored=False)
            # Bound learning, Found and post-save uncertainty cannot enter
            # the ordinary inert cold rollback route.
            for forbidden in (
                    {**record, "manifest": {**record["manifest"], "schema": 2}},
                    {**record, "found": {}}, {**record, "phase": "config-saved"}):
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    gate.attest_inert_bound_cold_recovery(forbidden, restored=False)

    def test_pristine_stage_cleanup_uses_exact_original_atomic_helper(self):
        import subprocess
        import tempfile

        # Exercise actual files and production atomic_remove_tree, while
        # mocking the native FD9/FD4 and sealed bundle readers only.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            active = root / "runtime-v2"
            active.mkdir()
            generation = "d" * 32
            old = {"id": "a" * 32}
            record = {"phase": "activating", "detail": {"id": generation},
                      "previous": old}
            stage = root / f".runtime-v2.stage.{generation}"
            parked = root / f".runtime-v2.old.{generation}"
            stage.mkdir()
            (stage / "sealed").write_text("candidate")
            store = Mock(read=Mock(return_value=record))
            actual_run = subprocess.run

            def shell(argv, **kwargs):
                self.assertEqual(kwargs.pop("pass_fds"), (9, 4, 3))
                self.assertEqual(argv[-1], str(stage))
                return actual_run(argv, **kwargs)

            with ExitStack() as stack:
                stack.enter_context(patch.object(gate, "COMMON_ACTIVE", active))
                stack.enter_context(patch.object(gate, "SCRIPT",
                    ROOT / "src/opnsense/scripts/OPNsense/Zapret"))
                stack.enter_context(patch.object(gate, "require_lifecycle_lock"))
                lock = stack.enter_context(patch(
                    "auto_detect_original_lock_handoff.assert_inherited_config_fd"))
                stack.enter_context(patch.object(gate, "SharedApplyOperation",
                                                   return_value=store))
                stack.enter_context(patch("shared_apply_seal.verify_seal", side_effect=[
                    {"sha256": {"release": "old"}}, {"sha256": {"release": "new"}},
                    {"sha256": {"release": "old"}}, {"sha256": {"release": "new"}}]))
                trees = stack.enter_context(patch.object(gate, "_cold_recovery_trees",
                    return_value=("old", "new", None, None)))
                run = stack.enter_context(patch.object(subprocess, "run", side_effect=shell))
                self.assertTrue(gate._remove_bound_pristine_stage_locked(
                    record, config_fd=4, queue_fd=3))
                self.assertFalse(stage.exists())
                self.assertTrue(active.exists())
                self.assertGreaterEqual(lock.call_count, 3)
                run.assert_called_once()
                stage.mkdir()
                parked.mkdir()
                self.assertFalse(gate._remove_bound_pristine_stage_locked(
                    record, config_fd=4, queue_fd=3))
                self.assertTrue(stage.exists())
                parked.rmdir()
                trees.return_value = ("old", "foreign", None, None)
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    gate._remove_bound_pristine_stage_locked(record, config_fd=4, queue_fd=3)
                self.assertTrue(stage.exists())
                run.assert_called_once()

    def test_bound_cold_restore_terminal_handoff_retains_native_locks(self):
        import json
        import subprocess
        from contextlib import contextmanager

        base = "b" * 64
        new = {"id": "d" * 32, "page": "strategies", "base": base,
               "candidate": "c" * 64}
        old = {"id": "a" * 32, "candidate": base}
        record = dict(phase="activated", detail=new, previous=old,
                      manifest={"schema": 1}, previous_manifest={"schema": 2})
        terminal = {**record, "phase": "restored"}
        store = Mock()
        store.read.return_value = record
        queue = Mock(root=gate.PRODUCER_ROOT, uid=0, locked_fd=7)
        receipts = Mock(root=gate.EPOCH_ROOT)
        held = [False]

        @contextmanager
        def exclusive(*, existing_only):
            self.assertTrue(existing_only)
            held[0] = True
            try:
                yield
            finally:
                held[0] = False

        queue.exclusive.side_effect = exclusive

        def advance(phase, expected, attest):
            self.assertTrue(held[0])
            self.assertEqual((phase, expected), ("restored", record))
            self.assertTrue(attest())
            store.read.return_value = terminal
            return terminal

        def invoke(argv, **kwargs):
            self.assertTrue(held[0])
            self.assertEqual(argv[-4:], ["ordinary-restore-finish", new["id"],
                                          "strategies", "--queue-fd=7"])
            self.assertEqual(kwargs["pass_fds"], (7, 9))
            result = gate.finish_bound_cold_restore_locked(
                new["id"], base, config_fd=4, queue_fd=3)
            return Mock(returncode=0, stdout=(json.dumps(result) + "\n").encode())

        with ExitStack() as stack:
            stack.enter_context(patch.object(sys, "platform", "freebsd15"))
            stack.enter_context(patch.object(os, "geteuid", return_value=0))
            stack.enter_context(patch.object(gate, "require_lifecycle_lock"))
            stack.enter_context(patch.object(gate, "SharedApplyOperation", return_value=store))
            stack.enter_context(patch.object(gate, "_present", return_value=False))
            stack.enter_context(patch("auto_detect_post_drop._original_epoch_queue",
                                       return_value=(queue, receipts)))
            config_lock = stack.enter_context(patch(
                "auto_detect_original_lock_handoff.assert_inherited_config_fd"))
            proof = stack.enter_context(patch.object(gate, "attest_inert_bound_cold_recovery"))
            run = stack.enter_context(patch.object(subprocess, "run", side_effect=invoke))
            store._advance_bound_ordinary.side_effect = advance
            self.assertEqual(gate.native_finish_bound_cold_restore(record), terminal)
            proof.assert_called_once_with(record, restored=True, config_fd=4,
                                          config_digest=base, queue_fd=3)
            self.assertEqual(config_lock.call_count, 3)
            store._advance_bound_ordinary.assert_called_once()
            self.assertFalse(held[0])
            store.read.return_value = record
            store._advance_bound_ordinary.reset_mock()
            with self.assertRaises(gate.QuiescentPreimageRefused):
                gate.finish_bound_cold_restore_locked(
                    new["id"], new["candidate"], config_fd=4, queue_fd=3)
            store._advance_bound_ordinary.assert_not_called()
            run.side_effect = subprocess.TimeoutExpired("php", 90)
            with self.assertRaisesRegex(gate.QuiescentPreimageRefused, "OUTCOME_UNCERTAIN"):
                gate.native_finish_bound_cold_restore(record)
            self.assertFalse(held[0])
            store._advance_bound_ordinary.assert_not_called()

    def test_cold_retired_predecessor_requires_existing_queue_and_complete_history(self):
        from contextlib import contextmanager
        record = {"previous": {"id": "a" * 32, "candidate": "b" * 64},
                  "previous_manifest": {"schema": 2}}
        queue = Mock(root=gate.PRODUCER_ROOT, uid=0)
        receipts = Mock(root=gate.EPOCH_ROOT)
        held = [False]

        @contextmanager
        def lock(*, existing_only):
            self.assertTrue(existing_only)
            self.assertFalse(held[0])
            held[0] = True
            try:
                yield
            finally:
                held[0] = False

        queue.exclusive.side_effect = lock
        ready = "c" * 64
        idle = ((1, 2, 0, "d" * 64), (1, 3, 0, "d" * 64))
        def verify(*args):
            self.assertTrue(held[0])
            self.assertEqual(args, (record, queue, receipts, ready))
        with ExitStack() as stack:
            stack.enter_context(patch("auto_detect_post_drop._original_epoch_queue",
                                       return_value=(queue, receipts)))
            digest = stack.enter_context(patch.object(gate, "_retired_ready_digest",
                                                        return_value=ready))
            history = stack.enter_context(patch.object(gate, "_verify_retired_history",
                                                         side_effect=verify))
            producer = stack.enter_context(patch.object(gate, "_verify_idle_producer",
                                                          return_value=idle))
            self.assertEqual(gate._observe_cold_retired_predecessor(record), (ready, idle))
            history.assert_called_once()
            producer.assert_called_once_with(queue, receipts)
            self.assertEqual(digest.call_count, 2)
            digest.side_effect = (ready, "e" * 64)
            with self.assertRaises(gate.QuiescentPreimageRefused):
                gate._observe_cold_retired_predecessor(record)
            digest.side_effect = None
            history.side_effect = ValueError("missing ACK")
            with self.assertRaises(ValueError):
                gate._observe_cold_retired_predecessor(record)
            history.side_effect = verify
            producer.side_effect = ValueError("nonempty producer")
            with self.assertRaises(ValueError):
                gate._observe_cold_retired_predecessor(record)
            producer.side_effect = None
            receipts.root = Path("/foreign")
            with self.assertRaises(gate.QuiescentPreimageRefused):
                gate._observe_cold_retired_predecessor(record)
            self.assertFalse(held[0])

    def test_bound_cold_atomic_images_are_checked_before_mutation(self):
        from tempfile import TemporaryDirectory
        from shared_apply_seal import _release_hash, SharedBundleError

        with TemporaryDirectory() as tmp:
            parent = Path(tmp)
            active = parent / "runtime-v2"
            generation = "a" * 32
            stage = parent / f".runtime-v2.stage.{generation}"
            parked = parent / f".runtime-v2.old.{generation}"
            backup_root = parent / "runtime-v2-backups"
            backup = backup_root / f"runtime-v2-{generation}"
            old, new, foreign = (parent / name for name in ("old", "new", "foreign"))
            for path, content in ((old, b"old"), (new, b"new"), (foreign, b"foreign")):
                path.mkdir()
                (path / "data").write_bytes(content)
            uid = os.geteuid()
            old_hash, new_hash = _release_hash(old, uid), _release_hash(new, uid)

            def clear():
                for path in (active, stage, parked, backup_root):
                    if path.is_symlink():
                        path.unlink()
                    elif path.exists():
                        shutil.rmtree(path)

            def run(mapping, allowed, *, phase="activating", restored=False):
                clear()
                for path, source in mapping:
                    path.parent.mkdir(exist_ok=True)
                    shutil.copytree(source, path)
                before = {str(p): p.lstat().st_ino for p in parent.rglob("*")}
                def observe():
                    return gate._cold_recovery_trees(
                        active, generation, old_hash, new_hash, phase=phase,
                        restored=restored, owner_uid=uid)
                if allowed:
                    observe()
                else:
                    with self.assertRaises((gate.QuiescentPreimageRefused, SharedBundleError)):
                        observe()
                self.assertEqual(before, {str(p): p.lstat().st_ino for p in parent.rglob("*")})

            run(((active, old),), True)
            run(((active, old), (stage, new)), True)
            run(((stage, new), (parked, old)), True)
            run(((stage, new), (backup, old)), True)
            run(((active, new), (backup, old)), True, phase="activated")
            run(((active, old), (stage, new), (parked, old)), True, restored=True)
            run(((active, new),), False)
            run(((active, foreign),), False)
            run(((active, old), (stage, foreign)), False)
            run(((active, new), (backup, foreign)), False)
            run(((active, old), (parked, old), (backup, old)), False)
            run(((stage, new),), False)
            run(((stage, new), (parked, old)), False, phase="activated")
            run(((active, new), (backup, old)), False, restored=True)
            run(((active, new), (backup, old), (stage, new)), False)
            clear()
            shutil.copytree(old, active)
            backup_root.symlink_to(old, target_is_directory=True)
            with self.assertRaises(SharedBundleError):
                gate._cold_recovery_trees(
                    active, generation, old_hash, new_hash, phase="activating",
                    restored=False, owner_uid=uid)

    def test_cold_native_absent_kernel_never_loads_adapter(self):
        self.cold()
        with ExitStack() as stack:
            self.native_seams(stack, cold_kernel=True)
            receipt = self.call()
        self.assertEqual(receipt.kernel_state, "native-kernel-absent")
        self.adapter.list_rules.assert_not_called()

    def test_cold_orphan_rule_or_managed_stage_table_refused(self):
        self.cold()
        with ExitStack() as stack:
            self.native_seams(stack)
            self.adapter.list_rules.return_value = {19095: ["foreign"]}
            with self.assertRaises(gate.QuiescentPreimageRefused):
                self.call()
            self.adapter.list_rules.return_value = {}
            self.adapter.get_table.side_effect = lambda name: (
                ["192.0.2.1"] if name.endswith("_stage") else None)
            with self.assertRaises(gate.QuiescentPreimageRefused):
                self.call()

    def test_no_previous_with_active_tree_is_not_cold(self):
        record = self.f.original.read()
        record.pop("previous")
        self.f.original._persist_record(record)
        with ExitStack() as stack:
            self.native_seams(stack, cold_kernel=True)
            with self.assertRaises(gate.QuiescentPreimageRefused):
                self.call()

    def test_cold_pidfile_foreign_process_and_malformed_census(self):
        self.cold()
        with ExitStack() as stack:
            self.native_seams(stack, cold_kernel=True)
            for path in self.pidfiles:
                path.write_text("5432\n")
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    self.call()
                path.unlink()
            for line in (f"999 {gate.CHILD_EXEC}", f"999 /bin/sh {gate.MONITOR_EXEC}",
                         "999 daemon: supervisor_loop.sh[123] (daemon)",
                         "999 daemon: dvtws2[123] (daemon)", "malformed", "999"):
                self.runner.return_value.stdout = "1 /sbin/init\n" + line + "\n"
                with self.subTest(line=line), self.assertRaises(gate.QuiescentPreimageRefused):
                    self.call()

    def test_cold_residual_producer_epoch_backup_atomic_stage_and_old_work(self):
        self.cold()
        with ExitStack() as stack:
            self.native_seams(stack, cold_kernel=True)
            for path in (self.producer, self.epochs, self.backups, self.active,
                         self.f.parent / ("0" * 32)):
                path.mkdir()
                (path / "evidence").touch()
                with self.subTest(path=path.name), self.assertRaises(gate.QuiescentPreimageRefused):
                    self.call()
                shutil.rmtree(path)
            stage = self.active.parent / (f".{self.active.name}.stage." + "0" * 32)
            stage.mkdir()
            with self.assertRaises(gate.QuiescentPreimageRefused):
                self.call()

    def test_stopped_old_tree_plus_existing_retired_ready_command(self):
        self.lock()
        record = self.f.original.read()
        with ExitStack() as stack:
            cmd = self.native_seams(stack)
            receipt = self.call()
        self.assertEqual(receipt.old_state, "committed-stopped")
        self.assertEqual(receipt.previous_generation, record["previous"]["id"])
        self.assertEqual(receipt.retirement_state, "original-epoch-ack-retired")
        self.assertEqual(cmd.call_count, 2)
        cmd.assert_called_with((str(gate.SCRIPT / "python_runtime.sh"),
            str(gate.SCRIPT / "backend/auto_detect_minute.py"), "--retired-ready"))
        self.assertEqual(record, self.f.original.read())
        self.assertEqual(receipt.authorization, "NONE")

    def test_stopped_native_retirement_must_be_complete_no_lock_creation(self):
        with ExitStack() as stack:
            cmd = self.native_seams(stack)
            with self.assertRaises(gate.QuiescentPreimageRefused):
                self.call()
            cmd.assert_not_called()
            self.assertFalse(self.producer.exists())
            self.lock()
            for response in (b"auto-detect-retire=processed\n",
                             b"auto-detect-retire=idle\n", b"", b"foreign\n"):
                cmd.return_value = response
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    self.call()

    def test_stopped_old_tree_mutation_and_running_refused(self):
        self.lock()
        with ExitStack() as stack:
            self.native_seams(stack)
            (self.active / "tcp-ports.txt").write_bytes(b"tampered\n")
            with self.assertRaises(gate.QuiescentPreimageRefused):
                self.call()
        with ExitStack() as stack:
            self.saved = replace(self.saved, previous_state="ready")
            cmd = self.native_seams(stack)
            with self.assertRaises(gate.QuiescentPreimageRefused):
                self.call()
            cmd.assert_not_called()

    def test_second_observation_wan_or_kernel_changed_refused(self):
        self.cold()
        with ExitStack() as stack:
            self.native_seams(stack)
            with patch.object(gate, "_native_wan", side_effect=("tun0", "tun1")):
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    self.call()
            with patch.object(gate, "_ipfw_kernel_confirmed_absent",
                              side_effect=(True, False)):
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    self.call()

    def test_retired_readonly_native_source_still_uses_repair_false(self):
        minute = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend/auto_detect_minute.py"
        text = minute.read_text().split("def native_retired_ready()", 1)[1]
        self.assertIn("repair=False", text)
        self.assertIn("verify_retired(previous, queue)", text)
        self.assertNotIn("retire_stopped(", text)

    def test_public_wrapper_refuses_absent_original_fd9(self):
        with patch.object(gate, "require_lifecycle_lock",
                          side_effect=RuntimeError("no FD9")), \
             patch.object(gate, "_attest_quiescent") as read:
            with self.assertRaisesRegex(gate.QuiescentPreimageRefused, "FD9"):
                gate.attest_quiescent_under_fd9(
                    generation=self.f.generation, native=self.f.native,
                    effective=self.f.effective, enabled=True)
            read.assert_not_called()


    def test_disabled_cold_all_list_auto_schema1_mode_dispatch_without_wan(self):
        # Genuine filesystem/process/kernel cold guards remain exercised.
        # Inject ONLY original bound-root proof + WAL schema because this
        # existing real candidate fixture is specifically schema2 Auto ON.
        from types import SimpleNamespace
        self.cold()
        real = self.f.original.read()
        schema1 = {**real, "manifest": {**real["manifest"], "schema": 1}}
        for mode in ("all", "list", "auto"):
            with self.subTest(mode=mode), ExitStack() as stack:
                self.native_seams(stack)
                stack.enter_context(patch.object(
                    gate, "SharedApplyOperation",
                    return_value=Mock(read=Mock(return_value=schema1))))
                root = stack.enter_context(patch.object(
                    gate, "_attest_bound_candidate",
                    return_value=SimpleNamespace(
                        root_sha256=schema1["manifest"]["root_sha256"])))
                stack.enter_context(patch.object(
                    gate, "_native_preflight",
                    return_value={**self.config, "enabled": "0"}))
                wan = stack.enter_context(patch.object(
                    gate, "_native_wan",
                    side_effect=AssertionError("OFF must not require WAN")))
                proof = gate._attest_quiescent(
                    generation=self.f.generation,
                    native=replace(self.f.native, mode=mode),
                    effective=self.f.effective, enabled=False,
                    parent=self.f.parent, journal_root=self.f.journal_root,
                    owner_uid=os.geteuid(), active=self.active,
                    backups=self.backups, producer=self.producer,
                    epochs=self.epochs, pidfiles=self.pidfiles,
                    runner=self.runner)
                self.assertEqual(proof.old_state, "first-install-empty")
                self.assertIsNone(proof.verified_wan_device)
                self.assertEqual(root.call_count, 3)
                self.assertEqual(root.call_args.kwargs["mode"], mode)
                self.assertFalse(root.call_args.kwargs["schema3"])
                self.assertEqual(proof.authorization, "NONE")
                self.assertFalse(proof.physical_transition_allowed)
                wan.assert_not_called()

    def test_disabled_schema_mismatch_refuses_before_bound_read(self):
        self.cold()
        with ExitStack() as stack:
            self.native_seams(stack)
            bound = stack.enter_context(patch.object(
                gate, "_attest_bound_candidate"))
            for mode, enabled in (("all", True), ("list", False),
                                  ("auto", False)):
                with self.subTest(mode=mode, enabled=enabled), \
                     self.assertRaises(gate.QuiescentPreimageRefused):
                    gate._attest_quiescent(
                        generation=self.f.generation,
                        native=replace(self.f.native, mode=mode),
                        effective=self.f.effective, enabled=enabled,
                        parent=self.f.parent, journal_root=self.f.journal_root,
                        owner_uid=os.geteuid(), active=self.active,
                        backups=self.backups, producer=self.producer,
                        epochs=self.epochs, pidfiles=self.pidfiles,
                        runner=self.runner)
            bound.assert_not_called()


class StagedQuiescentTests(unittest.TestCase):
    def test_exact_stopped_preimage_and_rollback_stage_required(self):
        import json
        import tempfile
        from types import SimpleNamespace
        from voice_firewall_transaction import TABLE_PREFIX
        from shared_apply_seal import _stat
        generation, old, base, candidate = "a" * 32, "b" * 32, "c" * 64, "d" * 64
        record = {"phase": "activating",
                  "detail": {"id": generation, "base": base, "candidate": candidate},
                  "previous": {"id": old, "candidate": base},
                  "manifest": {"schema": 1, "root_sha256": "e" * 64}}
        preimage = gate.QuiescentPreimage(generation, "e" * 64, old, "f" * 64,
            base, candidate, "tun0", "committed-stopped",
            "native-managed-kernel-empty", "inert-no-producer-data")
        root = {"schema": 1, "generation": generation,
                "service": {"enabled": True, "target_mode": "list"}}
        key = TABLE_PREFIX + "telegram"
        manifest = {"rule_base": 19000, "rule_max": 19010,
                    "rules": {19000: ["divert"]}, "tables": {key: ["192.0.2.1"]}}
        tables = {key: ["192.0.2.1"], key + "_stage": []}
        adapter = SimpleNamespace(rule_base=19000, rule_max=19099,
            list_rules=Mock(return_value=manifest["rules"]),
            get_table=Mock(side_effect=lambda name: tables.get(name)))
        token = SimpleNamespace(pid=5432, started="original")

        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            active = Path(tmp) / "runtime-v2"
            backup = active.with_name("runtime-v2-backups") / f"runtime-v2-{generation}"
            active.mkdir()
            backup.mkdir(parents=True)
            actual_uid = active.stat().st_uid
            stack.enter_context(patch("sys.platform", "freebsd15"))
            stack.enter_context(patch("os.geteuid", return_value=0))
            stack.enter_context(patch.object(gate, "require_lifecycle_lock"))
            stack.enter_context(patch("auto_detect_original_lock_handoff.assert_inherited_config_fd"))
            stack.enter_context(patch.object(gate, "SharedApplyOperation",
                return_value=SimpleNamespace(read=lambda: record)))
            stack.enter_context(patch.object(gate, "COMMON_ACTIVE", active))
            stack.enter_context(patch("neutral_root_stage.verify_original_operation_pins"))
            stack.enter_context(patch("neutral_root_stage._verify_original_pinned_root",
                side_effect=lambda **kw: json.dumps(root).encode()))
            stack.enter_context(patch("neutral_root_stage._original_plan_matches", return_value=True))
            stack.enter_context(patch("shared_apply_seal._stat",
                side_effect=lambda path, uid, **kw: _stat(path, actual_uid, **kw)))
            tree = stack.enter_context(patch.object(gate, "_full_prior_tree",
                side_effect=lambda work, target, uid: "f" * 64 if target == backup else "2" * 64))
            stack.enter_context(patch.object(gate, "inspect_inert_release", return_value="inactive"))
            stack.enter_context(patch.object(gate, "_safe_empty_directory"))
            stack.enter_context(patch.object(gate, "shared_release_manifest", return_value=manifest))
            stack.enter_context(patch.object(gate, "FreeBSDIPFWAdapter", return_value=adapter))
            process = stack.enter_context(patch(
                "neutral_schema3_previous_physical._running_native", return_value=token))

            def run(**kw):
                args = dict(preimage=preimage, config_fd=4, config_digest=base)
                return gate.attest_bound_quiescent_staged_under_fd9(record, **(args | kw))

            def refuses(**kw):
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    run(**kw)

            result = run()
            self.assertEqual((result.backup_sha256, result.running), ("f" * 64, token))
            adapter.list_rules.assert_called_with(19000, 19099)
            refuses(config_digest=candidate)
            refuses(preimage=replace(preimage, retirement_state="original-epoch-ack-retired"))
            del tables[key + "_stage"]
            refuses()
            tables[key + "_stage"] = ["192.0.2.2"]
            refuses()
            tables[key + "_stage"] = []
            stage = active.parent / f".runtime-v2.stage.{generation}"
            stage.mkdir()
            refuses()
            stage.rmdir()
            tree.side_effect = lambda work, target, uid: "3" * 64
            refuses()
            tree.side_effect = lambda work, target, uid: "f" * 64 if target == backup else "2" * 64
            parent = backup.parent
            parked = parent.with_name("other-backups")
            parent.rename(parked)
            parent.symlink_to(parked, target_is_directory=True)
            refuses()
            parent.unlink()
            parked.rename(parent)
            process.side_effect = [token, SimpleNamespace(pid=5433)]
            refuses()
            process.side_effect = None
            record["phase"] = "activated"
            self.assertEqual(run().kernel_state, "native-managed-kernel-staged")
            self.assertEqual(run(saved=True, config_digest=candidate).observed_config_sha256,
                             candidate)
            refuses(saved=True)
            refuses(queue_fd=3)
            # Same original stopped predecessor, now a pinned learning
            # generation with a genuine old retirement receipt identity.
            from contextlib import nullcontext
            idle_identity = ((1, 2, 0, "0" * 64), (1, 3, 0, "0" * 64))
            retired = replace(preimage, retirement_state="original-epoch-ack-retired",
                              retired_ready_sha256="9" * 64, idle_producer=idle_identity)
            record["previous_manifest"] = {"schema": 2}
            queue = SimpleNamespace(inherited_exclusive=Mock(return_value=nullcontext()))
            receipts = object()
            stack.enter_context(patch("auto_detect_post_drop._original_epoch_queue",
                                      return_value=(queue, receipts)))
            history = stack.enter_context(patch.object(gate, "_verify_retired_history"))
            idle = stack.enter_context(patch.object(gate, "_verify_idle_producer",
                                                    return_value=idle_identity))
            refuses(preimage=retired)
            self.assertEqual(run(preimage=retired, queue_fd=3).retired_ready_sha256,
                             "9" * 64)
            self.assertEqual(run(preimage=retired, queue_fd=3).idle_producer,
                             idle_identity)
            queue.inherited_exclusive.assert_called_with(3)
            history.assert_called_with(record, queue, receipts, "9" * 64)
            history.side_effect = ValueError("archive drift")
            refuses(preimage=retired, queue_fd=3)
            history.side_effect = None
            idle.side_effect = ValueError("retired root data")
            refuses(preimage=retired, queue_fd=3)
            idle.side_effect = None
            # Next inert Apply still sees the same canonical idle producer;
            # it must not require deleting it or inventing a second epoch.
            record.pop("previous_manifest")
            inert_idle = replace(preimage, retirement_state="inert-idle-producer",
                                 idle_producer=idle_identity)
            history.reset_mock()
            self.assertEqual(run(preimage=inert_idle, queue_fd=3).idle_producer, idle_identity)
            history.assert_not_called()
            idle.return_value = ((1, 4, 0, "0" * 64), idle_identity[1])
            refuses(preimage=inert_idle, queue_fd=3)
            record["phase"] = "config-saved"
            refuses(preimage=retired, queue_fd=3)

    def test_internal_activated_writer_cannot_accept_foreign_receipt(self):
        from types import SimpleNamespace
        from shared_apply_operation import SharedApplyOperation, DEFAULT_ROOT
        generation, base = "a" * 32, "b" * 64
        record = {"phase": "activating", "detail": {"id": generation, "base": base},
                  "manifest": {"schema": 1, "root_sha256": "c" * 64}}
        receipt = gate.StagedBoundRuntimeReceipt(generation, "c" * 64, base,
            "d" * 64, None, None, "native-managed-kernel-empty", base)
        def advance(phase, expected, attest):
            self.assertEqual((phase, expected), ("activated", record))
            if not attest():
                raise SharedOperationError("witness refused")
            return dict(record, phase=phase)
        store = SimpleNamespace(root=DEFAULT_ROOT, owner=0, read=lambda: record,
                                _advance_bound_ordinary=Mock(side_effect=advance))
        with patch.object(gate, "attest_bound_quiescent_staged_under_fd9",
                          return_value=receipt) as physical:
            def activate():
                return SharedApplyOperation._record_native_bound_activated(
                    store, record, preimage=None, config_fd=4, config_digest=base)
            activated, evidence = activate()
            self.assertEqual(activated["phase"], "activated")
            self.assertEqual(evidence, receipt)
            physical.return_value = replace(receipt, root_sha256="e" * 64)
            with self.assertRaises(SharedOperationError):
                activate()
            record["found"] = {"runtime_mode": "0"}
            physical.reset_mock()
            with self.assertRaises(SharedOperationError):
                activate()
            physical.assert_not_called()


    def test_internal_saved_writer_requires_same_activated_runtime(self):
        from types import SimpleNamespace
        from shared_apply_operation import SharedApplyOperation, DEFAULT_ROOT
        generation, base, candidate, root = "a" * 32, "b" * 64, "c" * 64, "d" * 64
        record = {"phase": "activated", "detail": {"id": generation, "base": base,
                                                   "candidate": candidate},
                  "manifest": {"schema": 1, "root_sha256": root}}
        calls = []
        receipt = gate.StagedBoundRuntimeReceipt(generation, root, base,
            "e" * 64, None, SimpleNamespace(pid=5432), "native-managed-kernel-staged", base)
        def advance(phase, expected, attest):
            self.assertEqual(expected, record)
            calls.append(phase)
            if not attest():
                raise SharedOperationError("witness refused")
            return dict(record, phase=phase)
        store = SimpleNamespace(root=DEFAULT_ROOT, owner=0, read=lambda: record,
                                _advance_bound_ordinary=Mock(side_effect=advance))
        with patch("sys.platform", "freebsd15"), patch("os.geteuid", return_value=0), \
                patch("voice_ipfw_adapter.require_lifecycle_lock"), \
                patch("auto_detect_original_lock_handoff.assert_inherited_config_fd"), \
                patch("os.fsync", side_effect=lambda fd: calls.append(("fsync", fd))), \
                patch.object(gate, "attest_bound_quiescent_staged_under_fd9",
                             return_value=replace(receipt, observed_config_sha256=candidate)) as physical:
            def saved(evidence=receipt, digest=candidate, queue_fd=None):
                return SharedApplyOperation._record_native_bound_saved(
                    store, record, preimage=None, activated_receipt=evidence,
                    config_fd=4, config_digest=digest, queue_fd=queue_fd)
            self.assertEqual(saved()["phase"], "config-saved")
            self.assertEqual(calls, [("fsync", 4), "config-saved"])
            physical.assert_called_with(record, preimage=None, config_fd=4,
                                       config_digest=candidate, queue_fd=None, saved=True)
            calls.clear()
            with self.assertRaises(SharedOperationError):
                saved(digest=base)
            self.assertEqual(calls, [])
            physical.return_value = replace(receipt, observed_config_sha256=candidate,
                                            running=SimpleNamespace(pid=5433))
            with self.assertRaises(SharedOperationError):
                saved()
            record["manifest"]["schema"] = 2
            learning = replace(receipt, pretraffic_sha256="f" * 64)
            physical.return_value = replace(learning, observed_config_sha256=candidate)
            self.assertEqual(saved(learning, queue_fd=3)["phase"], "epoch-finalizing")
            physical.return_value = replace(learning, observed_config_sha256=candidate,
                                            pretraffic_sha256="0" * 64)
            with self.assertRaises(SharedOperationError):
                saved(learning, queue_fd=3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
