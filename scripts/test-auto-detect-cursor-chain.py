#!/usr/bin/env python3
"""#1052 P2k8n: physical two-minute cursor, destination and pending ACK journal.

Uses real P2a/2k1/2k2a/2k2b file operations. Only the original live P2c
attestation and P2b FD inspection are injected for portable tests.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

BACKEND = Path(__file__).resolve().parents[1] / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

from auto_detect_cursor_chain import CursorChain, CursorChainRefused, main
from auto_detect_debug_window import empty_epoch, propose_window, Cursor
from auto_detect_destination_commit import DestinationCommit
from auto_detect_epoch_receipts import EpochReceipts, ReceiptRefused
from auto_detect_fd import FDState, OwnerToken
from auto_detect_owner import GenerationProof
from auto_detect_queue import DurableInbox


class CursorChainTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="p2k8n-")
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
        self.receipts = EpochReceipts(self.base / "epochs", owner_uid=os.geteuid())
        self.receipts.begin(self.proof, empty_epoch(self.proof, owner_uid=os.geteuid()))
        self.chain = CursorChain(self.receipts, self.queue)
        self.lists = self.base / "lists"
        self.lists.mkdir(mode=0o700)
        self.target = self.lists / "auto-domains.txt"
        self.target.write_text("!manual.invalid\n")
        self.target.chmod(0o600)
        self.lock = self.lists / ".writer.lock"
        self.writer = DestinationCommit(
            self.receipts, self.queue, {"auto": self.target}, self.lock)
        self.drains = 0

    def attest(self):
        return self.proof

    def drained(self, path, dev, ino, *, owner, writer_gid):
        self.drains += 1
        self.assertEqual(path.parent, self.queue.pending)
        self.assertEqual((dev, ino), (path.stat().st_dev, path.stat().st_ino))
        self.assertEqual(owner, self.proof.owner)
        self.assertIsNone(writer_gid)
        return FDState.DRAINED

    def emit(self, host: str):
        self.queue.inbox.write_bytes((host + "\n").encode("ascii"))
        with self.debug.open("a", encoding="ascii") as f:
            f.write(f"2026-11-14 11:10:00 : {host} : profile 2 (tail) : "
                    f"client 127.0.0.1:1234 : proto http : adding to {self.queue.inbox}\n")

    def rotate(self):
        return self.queue.rotate(generation=self.generation)

    def stage(self, path):
        return self.chain.prepare(self.proof, path, attest=self.attest,
                                  inspect=self.drained)

    def commit(self, path, host):
        return self.chain.commit(
            self.proof, path,
            {"auto": {"add": [host], "remove": []}}, self.writer,
            attest=self.attest, inspect=self.drained)

    def ack(self, path, completion, *, inspect=None, attest=None):
        return self.chain.acknowledge(
            self.proof, path, completion, self.writer,
            attest=attest or self.attest, inspect=inspect or self.drained)

    def complete_one(self, host: str):
        self.emit(host)
        with self.queue.exclusive():
            path = self.rotate()
            folder = self.stage(path)
            cp = self.commit(path, host)
            self.assertTrue(self.ack(path, cp))
            self.assertFalse(path.exists())
            return path, folder, cp

    def test_two_sequential_minutes_share_epoch_but_not_checkpoint(self):
        first, f1, _ = self.complete_one("one.example.com")
        second, f2, _ = self.complete_one("two.example.com")
        self.assertNotEqual(first, second)
        self.assertNotEqual(f1, f2)
        with self.queue.exclusive():
            tip = self.chain.tip(self.proof)
            self.assertEqual(tip.next_sequence, 2)
            self.assertIsNone(tip.open_folder)
            self.assertGreater(tip.cursor.offset, 0)
            self.assertEqual(len(tip.used_pending_names), 2)
        self.assertEqual(self.target.read_text(),
                         "!manual.invalid\none.example.com\ntwo.example.com\n")
        self.assertTrue((f1 / "ack.json").exists())
        self.assertTrue((f2 / "ack.json").exists())
        self.assertTrue((f1 / "destination" / "checkpoint.json").exists())
        self.assertTrue((f2 / "destination" / "checkpoint.json").exists())
        epoch = self.base / "epochs" / self.generation / "epoch.json"
        self.assertEqual(__import__("json").loads(epoch.read_text())["committed_cursor_offset"], 0)

    def test_busy_pending_after_commit_keeps_exact_cursor_open(self):
        self.emit("one.example.com")
        with self.queue.exclusive():
            path = self.rotate()
            self.stage(path)
            cp = self.commit(path, "one.example.com")
            self.assertFalse(self.ack(path, cp, inspect=lambda *args, **kw: FDState.BUSY))
            self.assertTrue(path.exists())
            self.assertEqual(self.chain.tip(self.proof).cursor.offset, 0)
            self.assertFalse((self.base / "epochs" / self.generation /
                              "cursor-chain-v2" / "00000000" / "ack.json").exists())
            self.assertTrue(self.ack(path, cp))
            self.assertGreater(self.chain.tip(self.proof).cursor.offset, 0)

    def test_retry_existing_intent_when_native_debug_has_later_events(self):
        self.emit("one.example.com")
        with self.queue.exclusive():
            p = self.rotate()
            slot = self.stage(p)
            self.emit("two.example.com")  # second event remains in NEW inbox
            self.assertEqual(self.stage(p), slot)
            cp = self.commit(p, "one.example.com")
            self.assertTrue(self.ack(p, cp))
            p2 = self.rotate()
            self.stage(p2)
            cp2 = self.commit(p2, "two.example.com")
            self.assertTrue(self.ack(p2, cp2))
        self.assertIn("two.example.com\n", self.target.read_text())

    def test_crash_after_pending_unlink_before_ack_receipt_recovers(self):
        self.emit("one.example.com")
        with self.queue.exclusive():
            p = self.rotate()
            self.stage(p)
            cp = self.commit(p, "one.example.com")
            with patch("auto_detect_cursor_chain._write_once",
                       side_effect=OSError("simulated ack fsync interruption")):
                with self.assertRaisesRegex(CursorChainRefused, "original_cursor_ack_evidence"):
                    self.ack(p, cp)
            self.assertFalse(p.exists())
            self.assertEqual(self.chain.tip(self.proof).cursor.offset, 0)
            self.assertTrue(self.ack(p, cp))
            self.assertTrue(self.ack(p, cp))
            self.assertEqual(self.chain.tip(self.proof).next_sequence, 1)
        self.assertEqual(self.target.read_text().count("one.example.com"), 1)

    def test_checkpoint_replay_does_not_restore_later_manual_gui_delete(self):
        self.emit("one.example.com")
        with self.queue.exclusive():
            p = self.rotate()
            self.stage(p)
            cp = self.commit(p, "one.example.com")
            self.target.write_text("!manual.invalid\n")
            self.assertEqual(self.commit(p, "one.example.com"), cp)
            self.assertTrue(self.ack(p, cp))
        self.assertEqual(self.target.read_text(), "!manual.invalid\n")

    def test_unacknowledged_predecessor_blocks_next_cursor(self):
        self.emit("one.example.com")
        with self.queue.exclusive():
            p = self.rotate()
            self.stage(p)
            self.commit(p, "one.example.com")
            self.assertEqual(self.chain.tip(self.proof).cursor.offset, 0)
            self.assertIsNotNone(self.chain.tip(self.proof).open_folder)
            self.assertTrue(p.exists())
        # No second rotation is attempted while the first pending is unacked.

    def test_unknown_fd_retains_prepared_pending(self):
        self.emit("one.example.com")
        with self.queue.exclusive():
            p = self.rotate()
            with self.assertRaisesRegex(CursorChainRefused, "original_pending_fd_not_drained"):
                self.chain.prepare(self.proof, p, attest=self.attest,
                    inspect=lambda *args, **kw: FDState.UNKNOWN)
            self.assertEqual(self.chain.tip(self.proof).next_sequence, 0)
            self.assertTrue(p.exists())

    def test_different_previous_generation_blocks_prepare(self):
        self.emit("one.example.com")
        with self.queue.exclusive():
            p = self.rotate()
            old = self.queue.pending / ("f" * 32 + "-" + "b" * 32 + ".txt")
            old.write_text("old.example.com\n")
            old.chmod(0o600)
            with self.assertRaisesRegex(CursorChainRefused, "historical_or_ambiguous_pending"):
                self.stage(p)
            self.assertTrue(p.exists())
            self.assertTrue(old.exists())

    def test_corrupted_ack_cannot_roll_cursor_forward(self):
        _, folder, _ = self.complete_one("one.example.com")
        ack = folder / "ack.json"
        ack.write_text('{"schema":2}\n')
        with self.queue.exclusive():
            with self.assertRaisesRegex(CursorChainRefused, "cursor_ack_not_bound_to_checkpoint"):
                self.chain.tip(self.proof)

    def test_replaced_debug_inode_blocks_destination_or_ack(self):
        self.emit("one.example.com")
        with self.queue.exclusive():
            p = self.rotate()
            self.stage(p)
            cp = self.commit(p, "one.example.com")
            self.debug.unlink()
            self.debug.write_bytes(b"")
            self.debug.chmod(0o600)
            with self.assertRaisesRegex(CursorChainRefused, "debug_changed_before_original_ack"):
                self.ack(p, cp)
            self.assertTrue(p.exists())

    def test_legacy_intent_and_chain_cannot_coexist(self):
        self.emit("one.example.com")
        with self.queue.exclusive():
            p = self.rotate()
            self.stage(p)
            with self.assertRaisesRegex(ReceiptRefused, "legacy_historical_reader_cannot_consume"):
                self.receipts.historical(self.generation)
            cursor = Cursor(self.generation, self.debug.stat().st_dev,
                            self.debug.stat().st_ino, 0, hashlib.sha256(b"").hexdigest())
            window = propose_window(self.proof, cursor, p.read_bytes(),
                                    owner_uid=os.geteuid())
            with self.assertRaisesRegex(ReceiptRefused, "legacy_intent_cannot_mix"):
                self.receipts.stage(self.proof, cursor, window, p)

    def test_corrupt_checkpoint_prevents_ack(self):
        self.emit("one.example.com")
        with self.queue.exclusive():
            p = self.rotate()
            self.stage(p)
            cp = self.commit(p, "one.example.com")
            folder = self.chain.tip(self.proof).open_folder
            f = folder / "destination" / "checkpoint.json"
            f.write_text('{"schema":1}\n')
            with self.assertRaisesRegex(CursorChainRefused, "checkpoint_not_original"):
                self.ack(p, cp)
            self.assertTrue(p.exists())

    def test_reuse_of_already_acked_pending_name_is_refused(self):
        first, _, _ = self.complete_one("one.example.com")
        self.emit("two.example.com")
        with self.queue.exclusive():
            # A synthetic trusted-root collision cannot claim new cursor slot.
            first.write_text("two.example.com\n")
            first.chmod(0o600)
            with self.assertRaisesRegex(CursorChainRefused, "completed_pending_name_reused"):
                self.stage(first)

    def test_no_unlocked_writer_and_public_entry(self):
        with self.assertRaisesRegex(CursorChainRefused, "original_queue_lock_required"):
            self.chain.tip(self.proof)
        with self.assertRaisesRegex(CursorChainRefused, "original_fd9_multiminute_worker_not_enabled"):
            main()

    def test_partial_debug_prefix_retains_current_segment(self):
        self.emit("one.example.com")
        with self.queue.exclusive():
            p = self.rotate()
            self.stage(p)
            with self.debug.open("a", encoding="ascii") as f:
                f.write("next native log\n")
            self.assertEqual(self.stage(p).name, "00000000")
            cp = self.commit(p, "one.example.com")
            self.assertTrue(self.ack(p, cp))


if __name__ == "__main__":
    unittest.main()
