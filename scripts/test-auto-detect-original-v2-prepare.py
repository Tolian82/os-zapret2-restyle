#!/usr/bin/env python3
"""#1052 P2k8o physical original queue rotation -> v2 same-generation intent.

Uses real P2a queue, P2k1 native-format debug, P2k2a immutable epoch,
P2k8n append-only journal and real per-slot P2k2b target/ACK. The test
injects only P2c actual-engine proof and P2b old writer-FD state.
"""
from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

BACKEND = Path(__file__).resolve().parents[1] / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

from auto_detect_cursor_chain import CursorChain
from auto_detect_destination_commit import DestinationCommit
from auto_detect_epoch_fixture import sealed_original_epoch
from auto_detect_epoch_receipts import EpochReceipts
from auto_detect_fd import FDState, OwnerToken
from auto_detect_original_v2_prepare import (OriginalV2PrepareRefused,
                                             prepare_original_v2_locked)
from auto_detect_owner import GenerationProof
from auto_detect_queue import DurableInbox


class OriginalV2PrepareTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="p2k8o-")
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
        self.proof = sealed_original_epoch(self.base, self.proof, self.queue, self.receipts)
        self.chain = CursorChain(self.receipts, self.queue)
        self.targets = self.base / "lists"
        self.targets.mkdir(mode=0o700)
        self.auto = self.targets / "auto-domains.txt"
        self.auto.write_text("!manual.invalid\n")
        self.auto.chmod(0o600)
        self.writer = DestinationCommit(
            self.receipts, self.queue, {"auto": self.auto}, self.targets / ".writer.lock")
        self.drains = 0

    def emit(self, host: str):
        self.queue.inbox.write_bytes((host + "\n").encode("ascii"))
        with self.debug.open("a", encoding="ascii") as out:
            out.write(f"2026-11-14 11:10:00 : {host} : profile 2 (tail) : "
                      f"client 127.0.0.1:1234 : proto http : adding to {self.queue.inbox}\n")

    def attest(self):
        return self.proof

    def drained(self, path, dev, ino, *, owner, writer_gid):
        self.drains += 1
        self.assertEqual(path.parent, self.queue.pending)
        self.assertEqual((dev, ino), (path.stat().st_dev, path.stat().st_ino))
        self.assertEqual(owner, self.proof.owner)
        self.assertIsNone(writer_gid)
        return FDState.DRAINED

    def stage(self, **kwargs):
        return prepare_original_v2_locked(
            self.queue, kwargs.pop("receipts", self.receipts),
            attest=kwargs.pop("attest", self.attest),
            inspect=kwargs.pop("inspect", self.drained), **kwargs)

    def commit_and_ack(self, path, host):
        cp = self.chain.commit(
            self.proof, path, {"auto": {"add": [host], "remove": []}},
            self.writer, attest=self.attest, inspect=self.drained)
        self.assertTrue(self.chain.acknowledge(
            self.proof, path, cp, self.writer,
            attest=self.attest, inspect=self.drained))
        self.assertFalse(path.exists())
        return cp

    def test_empty_raw_preserves_live_inode_and_keeps_chain_empty(self):
        before = self.queue.inbox.stat().st_ino
        with self.queue.exclusive():
            self.assertIsNone(self.stage())
            self.assertEqual(self.chain.tip(self.proof).next_sequence, 0)
        self.assertEqual(self.queue.inbox.stat().st_ino, before)
        self.assertEqual(list(self.queue.pending.iterdir()), [])

    def test_first_raw_rotates_and_persists_v2_not_legacy_intent(self):
        self.emit("one.example.com")
        old = self.queue.inbox.stat().st_ino
        with self.queue.exclusive():
            path = self.stage()
            self.assertTrue(path.is_file())
            self.assertEqual(path.stat().st_ino, old)
            self.assertNotEqual(self.queue.inbox.stat().st_ino, old)
            self.assertEqual(self.queue.inbox.read_bytes(), b"")
            tip = self.chain.tip(self.proof)
            self.assertEqual(tip.next_sequence, 1)
            self.assertEqual(tip.open_intent["pending_name"], path.name)
            self.assertEqual(tip.cursor.offset, 0)
            self.assertEqual(self.stage(), path)
        self.assertFalse(any(p.name.startswith("intent-") for p in
                             (self.base / "epochs" / self.generation).iterdir()))

    def test_two_full_original_raw_cycles_chain_and_target(self):
        for expected_index, host in enumerate(("one.example.com", "two.example.com")):
            self.emit(host)
            with self.queue.exclusive():
                path = self.stage()
                self.assertEqual(self.chain.tip(self.proof).next_sequence, expected_index + 1)
                self.commit_and_ack(path, host)
                tip = self.chain.tip(self.proof)
                self.assertEqual(tip.next_sequence, expected_index + 1)
                self.assertIsNone(tip.open_folder)
                self.assertGreater(tip.cursor.offset, 0)
        self.assertEqual(self.auto.read_text(),
                         "!manual.invalid\none.example.com\ntwo.example.com\n")

    def test_pending_priority_when_new_raw_waits(self):
        self.emit("one.example.com")
        with self.queue.exclusive():
            first = self.stage()
            # A later record appears after the original first intent.
            self.emit("two.example.com")
            second_live_inode = self.queue.inbox.stat().st_ino
            self.assertEqual(self.stage(), first)
            self.assertEqual(self.queue.inbox.stat().st_ino, second_live_inode)
            self.assertEqual(self.queue.inbox.read_bytes(), b"two.example.com\n")
            self.commit_and_ack(first, "one.example.com")
            second = self.stage()
            self.assertNotEqual(first, second)
            self.commit_and_ack(second, "two.example.com")

    def test_link_before_replace_recovery_keeps_same_inode(self):
        self.emit("one.example.com")
        source = self.queue.inbox.stat().st_ino
        alias = self.queue.pending / (self.generation + "-" + "c" * 32 + ".txt")
        os.link(self.queue.inbox, alias)
        self.assertEqual(alias.stat().st_nlink, 2)
        with self.queue.exclusive():
            self.assertEqual(self.stage(), alias)
            self.assertEqual(alias.stat().st_ino, source)
            self.assertEqual(alias.stat().st_nlink, 1)
            self.assertNotEqual(self.queue.inbox.stat().st_ino, source)
            self.commit_and_ack(alias, "one.example.com")

    def test_busy_writer_retains_pending_and_retry_prepares(self):
        self.emit("one.example.com")
        with self.queue.exclusive():
            with self.assertRaisesRegex(OriginalV2PrepareRefused, "original_v2_prepared_intent_unavailable"):
                self.stage(inspect=lambda *a, **kw: FDState.BUSY)
            pending = self.queue.segments()
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0].read_bytes(), b"one.example.com\n")
            self.assertEqual(self.chain.tip(self.proof).next_sequence, 0)
            self.assertEqual(self.stage(), pending[0])

    def test_unknown_writer_retains_pending_without_intent(self):
        self.emit("one.example.com")
        with self.queue.exclusive():
            with self.assertRaisesRegex(OriginalV2PrepareRefused, "original_v2_prepared_intent_unavailable"):
                self.stage(inspect=lambda *a, **kw: FDState.UNKNOWN)
            self.assertEqual(len(self.queue.segments()), 1)
            self.assertEqual(self.chain.tip(self.proof).next_sequence, 0)

    def test_old_generation_pending_blocks_original_raw_rotation(self):
        self.emit("one.example.com")
        old = self.queue.pending / ("f" * 32 + "-" + "c" * 32 + ".txt")
        old.write_bytes(b"old.example.com\n")
        old.chmod(0o600)
        inode = self.queue.inbox.stat().st_ino
        with self.queue.exclusive():
            with self.assertRaisesRegex(OriginalV2PrepareRefused, "historical_or_ambiguous_pending"):
                self.stage()
        self.assertEqual(self.queue.inbox.stat().st_ino, inode)
        self.assertEqual(self.queue.inbox.read_bytes(), b"one.example.com\n")
        self.assertTrue(old.exists())
        self.assertEqual(self.drains, 0)

    def test_open_cursor_slot_with_missing_pending_does_not_rotate(self):
        self.emit("one.example.com")
        with self.queue.exclusive():
            first = self.stage()
            # Emulate interruption after physical unlink, before v2 ack.
            cp = self.chain.commit(
                self.proof, first,
                {"auto": {"add": ["one.example.com"], "remove": []}},
                self.writer, attest=self.attest, inspect=self.drained)
            with patch("auto_detect_cursor_chain._write_once",
                       side_effect=OSError("injected after pending unlink")):
                with self.assertRaisesRegex(Exception, "original_cursor_ack_evidence"):
                    self.chain.acknowledge(
                        self.proof, first, cp, self.writer,
                        attest=self.attest, inspect=self.drained)
            self.assertFalse(first.exists())
            self.emit("two.example.com")
            live = self.queue.inbox.stat().st_ino
            with self.assertRaisesRegex(OriginalV2PrepareRefused, "unacknowledged_pending_needs_original_ack"):
                self.stage()
            self.assertEqual(self.queue.inbox.stat().st_ino, live)
            self.assertEqual(self.queue.inbox.read_bytes(), b"two.example.com\n")

    def test_wrong_original_epoch_is_refused_before_rotation(self):
        self.emit("one.example.com")
        stale = EpochReceipts(self.base / "missing-epochs", owner_uid=os.geteuid())
        live = self.queue.inbox.stat().st_ino
        with self.queue.exclusive():
            with self.assertRaisesRegex(OriginalV2PrepareRefused, "original_v2_prepared_intent_unavailable"):
                self.stage(receipts=stale)
        self.assertEqual(self.queue.inbox.stat().st_ino, live)
        self.assertEqual(self.queue.inbox.read_bytes(), b"one.example.com\n")

    def test_changed_owner_before_rotation_refuses_original_raw(self):
        self.emit("one.example.com")
        calls = [0]
        def changed():
            calls[0] += 1
            return self.proof if calls[0] == 1 else replace(self.proof, generation="f" * 32)
        original = self.queue.inbox.stat().st_ino
        with self.queue.exclusive():
            with self.assertRaisesRegex(OriginalV2PrepareRefused, "original_owner_changed_before_rotation"):
                self.stage(attest=changed)
        self.assertEqual(self.queue.inbox.stat().st_ino, original)
        self.assertEqual(len(list(self.queue.pending.iterdir())), 0)

    def test_changed_owner_after_rotation_keeps_original_pending(self):
        self.emit("one.example.com")
        calls = [0]
        def changed():
            calls[0] += 1
            return self.proof if calls[0] < 3 else replace(self.proof, generation="f" * 32)
        with self.queue.exclusive():
            with self.assertRaisesRegex(OriginalV2PrepareRefused, "original_owner_changed_after_rotation"):
                self.stage(attest=changed)
        self.assertEqual(len(list(self.queue.pending.iterdir())), 1)

    def test_unrelated_legacy_receipt_blocks_v2_preflight(self):
        self.emit("one.example.com")
        folder = self.base / "epochs" / self.generation
        existing = folder / ("intent-" + self.generation + "-" + "c" * 32 + ".txt.json")
        existing.write_text("{}\n")
        existing.chmod(0o600)
        inode = self.queue.inbox.stat().st_ino
        with self.queue.exclusive():
            with self.assertRaisesRegex(OriginalV2PrepareRefused, "original_v2_prepared_intent_unavailable"):
                self.stage()
        self.assertEqual(self.queue.inbox.stat().st_ino, inode)

    def test_superseded_v1_rotation_is_not_present_or_imported(self):
        self.assertFalse((BACKEND / "auto_detect_original_rotation.py").exists())
        self.assertFalse((Path(__file__).parent /
                          "test-auto-detect-original-rotation.py").exists())
        from auto_detect_cursor_chain import CursorChain
        from auto_detect_original_v2_source import qualified_current_source
        self.assertTrue(callable(qualified_current_source))
        self.assertTrue(callable(CursorChain.prepare))

    def test_original_queue_lock_is_mandatory(self):
        self.emit("one.example.com")
        with self.assertRaisesRegex(OriginalV2PrepareRefused, "original_queue_epoch_lock_required"):
            self.stage()


if __name__ == "__main__":
    unittest.main()
