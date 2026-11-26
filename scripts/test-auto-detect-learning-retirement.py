#!/usr/bin/env python3
"""Portable source-level crash/recovery tests for the real stopped FD9 path.

No fixture pretends to attest a running/stopped native OPNsense owner:
the OS attestation and fstat are injected. Physical nofollow inodes,
one P2a flock, immutable intent, rename, fsync and replay are real.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

BACKEND = Path(__file__).resolve().parents[1] / (
    "src/opnsense/scripts/OPNsense/Zapret/backend")
sys.path.insert(0, str(BACKEND))
from auto_detect_cursor_chain import CursorChain
from auto_detect_epoch_receipts import EpochReceipts
from auto_detect_fd import FDState, OwnerToken
from auto_detect_learning_retirement import (
    LearningRetirementRefused, retired_learning_stopped,
)
from auto_detect_owner import LearningGenerationProof
from auto_detect_queue import DurableInbox

GEN = "d" * 32
EMPTY = hashlib.sha256(b"").hexdigest()


class StoppedLearningRetirementTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix="schema3-retirement-")
        self.addCleanup(folder.cleanup)
        base = Path(folder.name)
        producer_parent = base / "producer-parent"
        producer_parent.mkdir(mode=0o711)
        self.root = producer_parent / "producer"
        self.root.mkdir(mode=0o710)
        private = base / "private"
        private.mkdir(mode=0o700)
        self.epoch_root = private / "epochs"
        self.epoch_root.mkdir(mode=0o700)
        self.gid = os.getegid() or 65534
        self.uid = os.geteuid()
        if self.uid == 0:
            os.chown(self.root, 0, self.gid)
        self.root.chmod(0o710)
        self.pending = self.root / "pending"
        self.pending.mkdir(mode=0o700)
        self._file(self.root / "inbox.txt", b"")
        self._file(self.root / "debug.log", b"diagnostic-only\n")
        self.native = self.root / f"learning-{GEN}-1.txt"
        self._file(self.native, b"video.example.test\n")
        self.queue = DurableInbox(self.root, owner_uid=self.uid,
                                  writer_gid=self.gid)
        self.receipts = EpochReceipts(self.epoch_root, owner_uid=self.uid,
                                      writer_gid=self.gid)
        self.epoch = self.epoch_root / GEN
        self.epoch.mkdir(mode=0o700)
        self.work = base / GEN
        self.work.mkdir(mode=0o700)
        self.proof = LearningGenerationProof(
            OwnerToken(1002, "Fri Nov 13 07:00:00 2026", "/usr/local/bin/dvtws2"),
            GEN, GEN, "a" * 64, "b" * 64, "c" * 64,
            ((1, "youtube", str(self.native)),))

    def _file(self, path, raw):
        path.write_bytes(raw)
        if self.uid == 0:
            os.chown(path, 0, self.gid)
        path.chmod(0o660)

    def _cursor(self, path, raw):
        st = path.stat()
        return dict(path=str(path), device=st.st_dev, inode=st.st_ino,
                    offset=len(raw), prefix_sha256=hashlib.sha256(raw).hexdigest())

    def tip(self):
        native = self._cursor(self.native, self.native.read_bytes())
        debug = self._cursor(self.root / "debug.log",
                             (self.root / "debug.log").read_bytes())
        return dict(root=self.epoch / "cursor-chain-v2",
                    sequence=5, cycle=1, state={
                        1: dict(native_number=1, hostlist="youtube",
                                path=str(self.native), streams=[native])},
                    debug=debug, previous_ack_sha256="e" * 64,
                    epoch_sha256="f" * 64, slot=None, intent=None)

    def run_retire(self, *, repair=True, tip=None, inspect=None):
        if tip is None:
            tip = self.tip()
        if inspect is None:
            inspect = lambda *args, **kwargs: FDState.DRAINED
        with self.queue.exclusive(), patch.object(
                CursorChain, "learning_tip", return_value=tip):
            return retired_learning_stopped(
                self.receipts, self.queue, self.proof, self.work,
                attest=lambda: self.proof, inspect=inspect, repair=repair)

    def test_user_installed_retirement_module_has_no_test_crash_hook(self):
        # The producer package must NEVER carry os._exit fault injection.
        from auto_detect_learning_retirement import __file__ as source_file
        code = Path(source_file).read_text(encoding="utf-8")
        self.assertNotIn("_ci_abrupt_retirement_fault", code)
        self.assertNotIn("ZAPRET2_TZ6V4_INJECT_RETIRE_CRASH", code)
        self.assertNotIn("os._exit(86)", code)

    def test_readonly_retirement_refuses_unsealed_cursor_without_cleanup(self):
        from auto_detect_cursor_chain import CHAIN, CursorChainRefused
        native = self.epoch / CHAIN / "00000000" / "native"
        native.mkdir(parents=True, mode=0o700)
        native.parent.chmod(0o700)
        native.parent.parent.chmod(0o700)
        staged = native / "001.json"
        staged.write_bytes(b"{}\n")
        staged.chmod(0o600)
        pin = staged.stat()
        tip = self.tip()
        cursor = tip["state"][1]["streams"][0]
        seed = {"learning": [dict(cursor, native_number=1)],
                "files": [{}, tip["debug"]]}
        with self.queue.exclusive(), patch.object(
                CursorChain, "learning_epoch", return_value=(self.epoch, seed, b"epoch")):
            with self.assertRaises((LearningRetirementRefused, CursorChainRefused)):
                retired_learning_stopped(
                    self.receipts, self.queue, self.proof, self.work,
                    attest=lambda: self.proof, inspect=lambda *a, **k: FDState.DRAINED,
                    repair=False)
        self.assertEqual(staged.read_bytes(), b"{}\n")
        self.assertEqual(staged.stat().st_ino, pin.st_ino)
        self.assertFalse((self.epoch / "learning-retirement").exists())

    def test_terminal_archive_and_readonly_boot_ready(self):
        tip = self.tip()
        self.assertFalse(self.run_retire(repair=False, tip=tip))
        self.assertTrue(self.run_retire(tip=tip))
        self.assertFalse(self.native.exists())
        self.assertEqual((self.root / "debug.log").read_bytes(), b"")
        retired = self.epoch / "learning-retirement"
        self.assertEqual((retired / ("old-" + self.native.name)).read_bytes(),
                         b"video.example.test\n")
        self.assertEqual((retired / "old-debug.log").read_bytes(),
                         b"diagnostic-only\n")
        self.assertTrue((retired / "intent.json").exists())
        self.assertTrue((retired / "ready.json").exists())
        self.assertTrue(self.run_retire(repair=False, tip=tip))
        self.assertFalse(any(path.name.startswith(".learning-retire-")
                             for path in self.root.iterdir()))

    def test_crash_after_first_native_rename_resumes_exact_plan(self):
        tip = self.tip()
        real_rename = os.rename
        hit = False

        def crash_after_native(src, dst):
            nonlocal hit
            real_rename(src, dst)
            if str(src) == str(self.native) and not hit:
                hit = True
                raise OSError("injected-after-fsync-boundary")
        with patch("auto_detect_learning_retirement.os.rename",
                   side_effect=crash_after_native):
            with self.assertRaises(OSError):
                self.run_retire(tip=tip)
        self.assertFalse(self.native.exists())
        self.assertFalse(self.run_retire(tip=tip, repair=False))
        self.assertTrue(self.run_retire(tip=tip))
        self.assertTrue(self.run_retire(tip=tip, repair=False))

    def test_crash_between_debug_archive_and_fresh_replace_recovers(self):
        tip = self.tip()
        real_rename = os.rename

        def crash_after_old_debug(src, dst):
            real_rename(src, dst)
            if Path(src).name == "debug.log":
                raise OSError("injected-before-fresh-debug")
        with patch("auto_detect_learning_retirement.os.rename",
                   side_effect=crash_after_old_debug):
            with self.assertRaises(OSError):
                self.run_retire(tip=tip)
        self.assertFalse((self.root / "debug.log").exists())
        self.assertFalse(self.run_retire(tip=tip, repair=False))
        self.assertTrue(self.run_retire(tip=tip))
        self.assertTrue(self.run_retire(tip=tip, repair=False))

    def test_unacked_late_debug_or_foreign_open_fd_fails_before_intent(self):
        tip = self.tip()
        with (self.root / "debug.log").open("ab") as out:
            out.write(b"new-unprocessed-line\n")
        with self.assertRaises(LearningRetirementRefused):
            self.run_retire(tip=tip)
        self.assertFalse((self.epoch / "learning-retirement" /
                          "intent.json").exists())

    def test_fd_close_race_rechecked_only_on_same_stopped_source(self):
        tip = self.tip()
        observed = []

        def closing_fd(path, device, inode, *, owner, writer_gid):
            observed.append((Path(path), device, inode, owner, writer_gid))
            # The first fstat races the last reader. Only a later complete
            # independently reattested P2b DRAINED can authorize archive.
            return (FDState.BUSY if len(observed) == 1
                    else FDState.DRAINED)

        with patch("auto_detect_learning_retirement.time.sleep") as sleep:
            self.assertTrue(self.run_retire(tip=tip, inspect=closing_fd))
        self.assertEqual(len(observed) > 1, True)
        self.assertEqual(observed[0], observed[1])
        sleep.assert_called_once_with(0.15)
        self.assertFalse(self.native.exists())

    def test_fd_closes_after_uncommitted_append_but_source_is_not_retired(self):
        tip = self.tip()
        saw_native = False

        def changed_then_closed(path, *args, **kwargs):
            nonlocal saw_native
            if Path(path) == self.native and not saw_native:
                saw_native = True
                with self.native.open("ab") as writer:
                    writer.write(b"uncommitted-after-stop\\n")
                return FDState.BUSY
            return FDState.DRAINED

        with patch("auto_detect_learning_retirement.time.sleep"):
            with self.assertRaisesRegex(
                    LearningRetirementRefused,
                    "stopped_learning_source_changed"):
                self.run_retire(tip=tip, inspect=changed_then_closed)
        self.assertTrue(saw_native)
        self.assertTrue(self.native.exists())
        self.assertFalse(
            (self.epoch / "learning-retirement" / "intent.json").exists())

    def test_fd_unknown_or_busy_never_authorizes_retirement(self):
        for observation, reason in (
                (FDState.BUSY, "stopped_learning_source_fd_busy"),
                (FDState.UNKNOWN, "stopped_learning_source_fd_unknown")):
            with self.subTest(observation=observation):
                calls = []
                def probe(*args, **kwargs):
                    calls.append((args, kwargs))
                    return observation
                with patch("auto_detect_learning_retirement.time.sleep") as sleep:
                    with self.assertRaisesRegex(LearningRetirementRefused, reason):
                        self.run_retire(inspect=probe)
                self.assertEqual(len(calls), 2)
                self.assertEqual(calls[0], calls[1])
                sleep.assert_called_once_with(0.15)
                self.assertTrue(self.native.exists())
                self.assertFalse((self.epoch / "learning-retirement" / "intent.json").exists())

    def test_busy_fd_refuses_without_source_change(self):
        tip = self.tip()
        with self.assertRaises(LearningRetirementRefused):
            self.run_retire(
                tip=tip, inspect=lambda *args, **kwargs: FDState.BUSY)
        self.assertEqual(self.native.read_bytes(), b"video.example.test\n")
        self.assertEqual((self.root / "debug.log").read_bytes(),
                         b"diagnostic-only\n")

    def test_archive_tamper_cannot_be_boot_ready(self):
        tip = self.tip()
        self.assertTrue(self.run_retire(tip=tip))
        archive = self.epoch / "learning-retirement" / "old-debug.log"
        self._file(archive, b"tampered\n")
        with self.assertRaises(LearningRetirementRefused):
            self.run_retire(tip=tip, repair=False)


    def _completed_learning_history(self, count=6):
        """Six physically retired old epochs; only tip/PID is test-injected."""
        from auto_detect_epoch_receipts import _canonical
        history = {}
        parent = self.work.parent
        # The base fixture has an unrelated native producer; never let it
        # masquerade as a source belonging to this six-generation journey.
        self.native.unlink()
        for idx in range(count):
            gen = f"{idx + 1:032x}"
            self.epoch = self.epoch_root / gen
            self.epoch.mkdir(mode=0o700)
            self.work = parent / gen
            self.work.mkdir(mode=0o700)
            self.native = self.root / f"learning-{gen}-1.txt"
            self._file(self.native, f"domain-{idx}.example.test\n".encode())
            self._file(self.root / "debug.log", b"diagnostic-only\n")
            self.proof = LearningGenerationProof(
                OwnerToken(1002, "Fri Nov 13 07:00:00 2026",
                           "/usr/local/bin/dvtws2"),
                gen, gen, "a" * 64, "b" * 64, "c" * 64,
                ((1, "youtube", str(self.native)),))
            tip = self.tip()
            self.assertTrue(self.run_retire(tip=tip))
            old = self.epoch / "learning-retirement"
            self.assertTrue((old / "ready.json").exists())
            epoch = {
                "schema": 3, "kind": "original-native-learning-epoch",
                "generation": gen, "operation_id": gen,
                "owner_candidate_sha256": "a" * 64,
                "final_args_sha256": "b" * 64,
                "native_map_sha256": "c" * 64,
                "pretraffic_sha256": "f" * 64,
                "owner_pid": self.proof.owner.pid,
                "owner_start": self.proof.owner.started,
                "owner_executable": self.proof.owner.executable,
                "files": [], "learning": [
                    {"native_number": 1, "hostlist": "youtube",
                     "path": str(self.native)}],
                "ack_authorized": False,
            }
            entry = self.epoch / "epoch.json"
            self._file(entry, _canonical(epoch))
            entry.chmod(0o600)
            # Stable independent ordering, not a wall-clock claim.
            stamp = 1_800_000_000_000_000_000 + idx * 1_000_000_000
            os.utime(self.epoch, ns=(stamp, stamp))
            history[gen] = tip
        return history

    def _prune_learning_history(self, tips):
        with self.queue.exclusive(), patch.object(
                CursorChain, "learning_tip",
                side_effect=lambda proof, workspace, **kw: tips[proof.generation]):
            return self.receipts.prune_completed(
                self.queue, protect="f" * 32, keep=4)

    def test_original_four_completed_learning_generations_retained(self):
        tips = self._completed_learning_history()
        self.assertEqual(self._prune_learning_history(tips), 2)
        names = list(tips)
        self.assertFalse((self.epoch_root / names[0]).exists())
        self.assertFalse((self.epoch_root / names[1]).exists())
        for gen in names[2:]:
            self.assertTrue((self.epoch_root / gen /
                             "learning-retirement" / "ready.json").exists())
        self.assertEqual(self._prune_learning_history(tips), 0)
        self.assertFalse(any(p.name.startswith(".gc3-")
                             for p in self.epoch_root.iterdir()))

    def test_original_bound_history_exact_digest_without_current_producer_rewrite(self):
        from auto_detect_learning_gc import qualified_completed_learning
        from auto_detect_epoch_receipts import ReceiptRefused
        from neutral_schema3_quiescent_preimage import (
            _verify_idle_producer, QuiescentPreimageRefused)
        tips = self._completed_learning_history(count=1)
        gen = next(iter(tips))
        ready = self.epoch_root / gen / "learning-retirement" / "ready.json"
        digest = hashlib.sha256(ready.read_bytes()).hexdigest()
        with self.queue.exclusive(), patch.object(
                CursorChain, "learning_tip",
                side_effect=lambda proof, workspace, **kw: tips[proof.generation]) as tip:
            def verify(**kw):
                args = dict(expected_candidate="a" * 64, expected_ready_sha256=digest)
                return qualified_completed_learning(self.receipts, self.queue, gen, **(args | kw))
            self.assertIsInstance(verify(), int)
            self.assertEqual(tip.call_args.kwargs, {"reclaim_unsealed": False})
            with self.assertRaises(ReceiptRefused):
                verify(expected_candidate="b" * 64)
            with self.assertRaises(ReceiptRefused):
                verify(expected_ready_sha256="0" * 64)
            idle = _verify_idle_producer(self.queue, self.receipts)
            self.assertEqual(len(idle), 2)
            self._file(self.root / "debug.log", b"new live bytes\n")
            # Historical proof remains valid AFTER a new producer starts.
            self.assertIsInstance(verify(), int)
            with self.assertRaises(QuiescentPreimageRefused):
                _verify_idle_producer(self.queue, self.receipts)
            self._file(self.root / "debug.log", b"")
            self._file(self.root / "foreign", b"")
            with self.assertRaises(QuiescentPreimageRefused):
                _verify_idle_producer(self.queue, self.receipts)
            (self.root / "foreign").unlink()
            self.assertEqual(_verify_idle_producer(self.queue, self.receipts), idle)

    def test_inert_original_idle_preimage_borrows_existing_queue_only(self):
        from neutral_schema3_quiescent_preimage import (
            _observe_idle_producer, QuiescentPreimageRefused)
        tips = self._completed_learning_history(count=1)
        self.assertTrue(tips)
        with patch("auto_detect_post_drop._original_epoch_queue",
                   return_value=(self.queue, self.receipts)), \
                patch.object(self.queue, "exclusive", wraps=self.queue.exclusive) as lock:
            idle = _observe_idle_producer(self.root, self.uid)
            self.assertEqual(len(idle), 2)
            lock.assert_called_once_with(existing_only=True)
            self._file(self.root / "debug.log", b"unexplained\n")
            with self.assertRaises(QuiescentPreimageRefused):
                _observe_idle_producer(self.root, self.uid)
            self._file(self.root / "debug.log", b"")
            self.assertEqual(_observe_idle_producer(self.root, self.uid), idle)

    def test_bound_history_pin_survives_original_gc_until_commit(self):
        tips = self._completed_learning_history()
        names = list(tips)
        record = {"phase": "activating", "detail": {"id": "f" * 32},
                  "previous": {"id": names[0]}, "previous_manifest": {"schema": 2}}
        with patch("sys.platform", "freebsd15"), \
                patch("voice_ipfw_adapter.require_lifecycle_lock"), \
                patch("shared_apply_operation.SharedApplyOperation.read", return_value=record):
            self.assertEqual(self._prune_learning_history(tips), 1)
            self.assertTrue((self.epoch_root / names[0]).exists())
            self.assertFalse((self.epoch_root / names[1]).exists())
        self.assertEqual(self._prune_learning_history(tips), 1)
        self.assertFalse((self.epoch_root / names[0]).exists())

    def test_changed_retired_learning_source_refuses_pruning(self):
        tips = self._completed_learning_history()
        first = next(iter(tips))
        archive = self.epoch_root / first / "learning-retirement" / (
            f"old-learning-{first}-1.txt")
        self._file(archive, b"foreign-change\n")
        with self.assertRaises(LearningRetirementRefused):
            # The qualified native snapshot may reject with its own
            # original model/receipt exception, not only this class.
            from auto_detect_learning_gc import qualified_completed_learning
            with self.queue.exclusive(), patch.object(
                    CursorChain, "learning_tip",
                    side_effect=lambda proof, workspace, **kw: tips[proof.generation]):
                qualified_completed_learning(self.receipts, self.queue, first)
        self.assertTrue((self.epoch_root / first).exists())

    def test_interrupted_learning_gc_tombstone_resumes_without_source(self):
        tips = self._completed_learning_history()
        first = next(iter(tips))
        original = __import__("auto_detect_learning_gc")._sync
        hit = False

        def crash_after_archive_sync(path):
            nonlocal hit
            original(path)
            if not hit and Path(path).name == "learning-retirement":
                hit = True
                raise OSError("injected-after-partial-retired-archive-delete")
        with patch("auto_detect_learning_gc._sync",
                   side_effect=crash_after_archive_sync):
            with self.assertRaises(OSError):
                self._prune_learning_history(tips)
        self.assertFalse((self.epoch_root / first).exists())
        self.assertTrue((self.epoch_root / (".gc3-" + first)).exists())
        self.assertEqual(self._prune_learning_history(tips), 1)
        self.assertFalse((self.epoch_root / (".gc3-" + first)).exists())
        self.assertEqual(len([
            name for name in tips if (self.epoch_root / name).exists()
        ]), 4)


    def test_tampered_surviving_old_inode_blocks_gc_replay(self):
        tips = self._completed_learning_history()
        from auto_detect_epoch_receipts import ReceiptRefused
        first = next(iter(tips))
        original_sync = __import__("auto_detect_learning_gc")._sync
        hit = False

        def interrupted_archive_unlink(path):
            nonlocal hit
            original_sync(path)
            if not hit and Path(path).name == "learning-retirement":
                hit = True
                raise OSError("injected-mid-archive-unlink")
        with patch("auto_detect_learning_gc._sync",
                   side_effect=interrupted_archive_unlink):
            with self.assertRaises(OSError):
                self._prune_learning_history(tips)
        tombstone = self.epoch_root / (".gc3-" + first)
        self.assertTrue(tombstone.exists())
        surviving = tombstone / "learning-retirement" / (
            f"old-learning-{first}-1.txt")
        self.assertTrue(surviving.exists())
        self._file(surviving, b"changed-surviving-old-inode\n")
        with self.assertRaises((ReceiptRefused, RuntimeError)):
            self._prune_learning_history(tips)
        self.assertTrue(tombstone.exists())
        self.assertTrue(surviving.exists())


if __name__ == "__main__":
    unittest.main()
