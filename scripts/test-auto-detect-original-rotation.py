#!/usr/bin/env python3
"""#1052 P2k8m physical original queue/FD/debug/immutable intent preflight.

Only P2c owner and P2b FD witnesses are injected; no production caller,
sealed FD9 producer, cron, Config, destination write or pending ACK exists.
"""
from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
import sys
import tempfile
import unittest

BACKEND = Path(__file__).resolve().parents[1] / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

from auto_detect_debug_window import empty_epoch
from auto_detect_epoch_receipts import EpochReceipts
from auto_detect_fd import FDState, OwnerToken
from auto_detect_owner import GenerationProof
from auto_detect_original_rotation import (RotationStageRefused,
                                           run_native_stage_original_current_once,
                                           stage_original_current_locked, main)
from auto_detect_queue import DurableInbox


class OriginalRotationStageTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="p2k8m-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.base.chmod(0o700)
        self.root = self.base / "producer"
        self.root.mkdir(mode=0o700)
        (self.root / "pending").mkdir(mode=0o700)
        self.queue = DurableInbox(self.root, owner_uid=os.geteuid())
        self.queue.inbox.write_bytes(b"")
        self.queue.inbox.chmod(0o600)
        self.debug = self.root / "debug.log"
        self.debug.write_bytes(b"")
        self.debug.chmod(0o600)
        self.generation = "a" * 32
        self.proof = GenerationProof(
            OwnerToken(4321, "Fri Nov 13 10:00:00 2026", "/usr/local/sbin/dvtws2"),
            self.generation, self.generation, "b" * 64,
            str(self.queue.inbox), str(self.debug), 2,
            ((0, "unknown-native-default", None),
             (1, "known-hostlist", "youtube"), (2, "observer", None)))
        self.store = EpochReceipts(self.base / "epochs", owner_uid=os.geteuid())
        self.store.begin(self.proof, empty_epoch(self.proof, owner_uid=os.geteuid()))
        self.fd_count = 0

    def emit(self, host="video.example.com"):
        self.queue.inbox.write_bytes((host + "\n").encode("ascii"))
        line = (f"2026-11-14 11:10:00 : {host} : profile 2 (tail) : "
                f"client 127.0.0.1:1234 : proto http : adding to {self.queue.inbox}\n")
        self.debug.write_text(line, encoding="ascii")

    def attest(self):
        return self.proof

    def drained(self, segment, device, inode, *, owner, writer_gid):
        self.fd_count += 1
        self.assertEqual(segment.parent, self.queue.pending)
        self.assertEqual(owner, self.proof.owner)
        self.assertEqual((device, inode),
                         (segment.stat().st_dev, segment.stat().st_ino))
        self.assertIsNone(writer_gid)
        return FDState.DRAINED

    def tick(self, *, attest=None, inspect=None, store=None):
        with self.queue.exclusive():
            return stage_original_current_locked(
                self.queue, store or self.store, attest=attest or self.attest,
                inspect=inspect or self.drained)

    def test_empty_original_inbox_never_rotates_or_stages(self):
        self.assertIsNone(self.tick())
        self.assertEqual(self.fd_count, 0)
        self.assertEqual(list(self.queue.pending.iterdir()), [])
        self.assertIsNone(self.store.historical(self.generation).intent)

    def test_original_raw_to_rotated_inode_and_immutable_debug_intent(self):
        self.emit()
        old = self.queue.inbox.stat().st_ino
        p = self.tick()
        self.assertTrue(p.is_file())
        self.assertTrue(p.name.startswith(self.generation + "-"))
        self.assertNotEqual(old, self.queue.inbox.stat().st_ino)
        self.assertEqual(self.queue.inbox.read_bytes(), b"")
        self.assertEqual(p.read_bytes(), b"video.example.com\n")
        self.assertEqual(self.fd_count, 2)
        receipt = self.store.historical(self.generation)
        self.assertEqual(receipt.intent["pending_name"], p.name)
        self.assertEqual(receipt.intent["pending_inode"], p.stat().st_ino)
        self.assertEqual(receipt.intent["candidate_count"], 1)
        self.assertFalse(receipt.intent["ack_authorized"])
        self.assertFalse((self.base / "epochs" / self.generation / "destination").exists())

    def test_busy_fd_retains_unstaged_segment_and_drained_retry(self):
        self.emit()
        with self.assertRaisesRegex(RotationStageRefused, "original_writer_fd_not_drained"):
            self.tick(inspect=lambda *a, **kw: FDState.BUSY)
        items = list(self.queue.pending.iterdir())
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].read_bytes(), b"video.example.com\n")
        self.assertIsNone(self.store.historical(self.generation).intent)
        self.assertEqual(self.tick(), items[0])
        self.assertEqual(len(list(self.queue.pending.iterdir())), 1)

    def test_unknown_fd_retains_original_pending(self):
        self.emit()
        with self.assertRaisesRegex(RotationStageRefused, "original_writer_fd_not_drained"):
            self.tick(inspect=lambda *a, **kw: FDState.UNKNOWN)
        self.assertEqual(len(list(self.queue.pending.iterdir())), 1)

    def test_hardlink_before_replace_crash_recovers_exact_original_inode(self):
        self.emit()
        alias = self.queue.pending / (self.generation + "-" + "c" * 32 + ".txt")
        os.link(self.queue.inbox, alias)
        self.assertEqual(alias.stat().st_nlink, 2)
        self.assertEqual(self.tick(), alias)
        self.assertEqual(alias.stat().st_nlink, 1)
        self.assertNotEqual(alias.stat().st_ino, self.queue.inbox.stat().st_ino)
        self.assertEqual(self.store.historical(self.generation).intent["pending_name"], alias.name)

    def test_old_generation_pending_blocks_rotation_without_reassignment(self):
        self.emit()
        foreign = self.queue.pending / ("f" * 32 + "-" + "c" * 32 + ".txt")
        foreign.write_bytes(b"old.example.com\n")
        foreign.chmod(0o600)
        old_inbox = self.queue.inbox.stat().st_ino
        with self.assertRaisesRegex(RotationStageRefused, "historical_or_ambiguous_pending"):
            self.tick()
        self.assertEqual(self.queue.inbox.stat().st_ino, old_inbox)
        self.assertEqual(self.queue.inbox.read_bytes(), b"video.example.com\n")
        self.assertTrue(foreign.exists())
        self.assertEqual(self.fd_count, 0)

    def test_untrusted_missing_empty_epoch_refuses_before_rotation(self):
        self.emit()
        missing = EpochReceipts(self.base / "missing-epochs", owner_uid=os.geteuid())
        original = self.queue.inbox.stat().st_ino
        with self.assertRaisesRegex(RotationStageRefused, "original_raw_debug_epoch_unavailable"):
            self.tick(store=missing)
        self.assertEqual(self.queue.inbox.stat().st_ino, original)
        self.assertEqual(len(list(self.queue.pending.iterdir())), 0)

    def test_changed_live_engine_after_rotation_never_creates_intent(self):
        self.emit()
        calls = [0]
        def changed():
            calls[0] += 1
            return self.proof if calls[0] < 3 else replace(self.proof, generation="f" * 32)
        with self.assertRaisesRegex(RotationStageRefused, "owner_changed_after_rotation"):
            self.tick(attest=changed)
        self.assertEqual(len(list(self.queue.pending.iterdir())), 1)
        self.assertIsNone(self.store.historical(self.generation).intent)

    def test_debug_raw_mismatch_retains_original_pending(self):
        self.emit()
        self.debug.write_text("other.log\n", encoding="ascii")
        with self.assertRaisesRegex(RotationStageRefused, "original_raw_debug_epoch_unavailable"):
            self.tick()
        self.assertEqual(len(list(self.queue.pending.iterdir())), 1)
        self.assertIsNone(self.store.historical(self.generation).intent)

    def test_single_generation_intent_replay_is_idempotent(self):
        self.emit()
        first = self.tick()
        receipt = self.store.historical(self.generation).intent
        self.assertEqual(self.tick(), first)
        self.assertEqual(self.store.historical(self.generation).intent, receipt)
        self.assertTrue(first.exists())

    def test_second_raw_segment_for_same_epoch_is_blocked(self):
        self.emit()
        first = self.tick()
        # Simulates later downstream ACK, without authorizing one here.
        first.unlink()
        self.emit("second.example.com")
        original = self.queue.inbox.stat().st_ino
        with self.assertRaisesRegex(RotationStageRefused, "older_original_intent_requires_completion"):
            self.tick()
        self.assertEqual(self.queue.inbox.stat().st_ino, original)
        self.assertEqual(self.queue.inbox.read_bytes(), b"second.example.com\n")

    def test_wrong_epoch_owner_cannot_stage(self):
        self.emit()
        foreign = EpochReceipts(self.base / "epochs", owner_uid=os.geteuid(), writer_gid=22)
        with self.assertRaisesRegex(RotationStageRefused, "original_locked_queue_and_epoch"):
            self.tick(store=foreign)
        self.assertEqual(len(list(self.queue.pending.iterdir())), 0)

    def test_queue_lock_is_mandatory_and_cannot_be_replaced(self):
        self.emit()
        with self.assertRaisesRegex(RotationStageRefused, "original_locked_queue_and_epoch"):
            stage_original_current_locked(
                self.queue, self.store, attest=self.attest, inspect=self.drained)
        self.assertEqual(self.queue.inbox.read_bytes(), b"video.example.com\n")
        self.assertEqual(len(list(self.queue.pending.iterdir())), 0)

    def test_live_worker_and_public_cli_remain_disabled(self):
        with self.assertRaisesRegex(RotationStageRefused, "original_fd9_epoch_and_minute"):
            main()
        with self.assertRaisesRegex(RotationStageRefused, "native_original_root_required"):
            run_native_stage_original_current_once()


if __name__ == "__main__":
    unittest.main()
