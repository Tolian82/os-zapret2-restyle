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

from auto_detect_cursor_chain import CursorChain, CursorChainRefused
from auto_detect_debug_window import MAX_DEBUG, MAX_WINDOW
from auto_detect_destination_commit import DestinationCommit
from auto_detect_epoch_fixture import sealed_original_epoch
from auto_detect_epoch_receipts import EpochReceipts
from auto_detect_fd import FDState, OwnerToken
from auto_detect_original_v2_prepare import (OriginalV2PrepareRefused,
                                             prepare_original_v2_locked)
from auto_detect_owner import GenerationProof
from auto_detect_queue import DurableInbox, MAX_SEGMENT


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

    def test_midcut_later_debug_positive_before_first_original_prepare(self):
        # Original P2a hardlink/replace, P2k8o v2 preparation and v2 ACK.
        # Two separate raw inodes share ONE native debug inode; no stop.
        self.emit("one.example.com")
        with self.queue.exclusive():
            first = self.queue.rotate(generation=self.generation)
            first_debug_end = self.debug.stat().st_size
            first_inode = first.stat().st_ino
            second_live_inode = self.queue.inbox.stat().st_ino
            self.assertNotEqual(first_inode, second_live_inode)
            self.emit("two.example.com")
            self.assertEqual(first.read_bytes(), b"one.example.com\n")
            self.assertEqual(self.queue.inbox.read_bytes(), b"two.example.com\n")
            # Before the fix the second positive blocked the FIRST raw.
            self.assertEqual(self.stage(), first)
            first_intent = self.chain.tip(self.proof).open_intent
            self.assertEqual(first_intent["debug_end_offset"], first_debug_end)
            self.assertEqual(first_intent["candidate_count"], 1)
            self.commit_and_ack(first, "one.example.com")
            self.assertEqual(self.chain.tip(self.proof).cursor.offset,
                             first_debug_end)
            self.assertEqual(self.queue.inbox.stat().st_ino, second_live_inode)
            second = self.stage()
            self.assertEqual(second.stat().st_ino, second_live_inode)
            self.assertEqual(self.chain.tip(self.proof).open_intent["candidate_count"], 1)
            self.commit_and_ack(second, "two.example.com")
            self.assertEqual(self.chain.tip(self.proof).cursor.offset,
                             self.debug.stat().st_size)
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

    def test_oversized_original_raw_refuses_before_detaching_or_claiming_v2(self):
        # Actual original v2 caller: no created pending or durable intent
        # when the live producer has already exceeded its downstream bound.
        self.emit("one.example.com")
        with self.queue.inbox.open("r+b") as output:
            output.truncate(MAX_SEGMENT + 1)
        before = self.queue.inbox.stat()
        with self.queue.exclusive():
            with self.assertRaisesRegex(OriginalV2PrepareRefused,
                                        "original_v2_prepared_intent_unavailable"):
                self.stage()
            after = self.queue.inbox.stat()
            self.assertEqual((after.st_dev, after.st_ino, after.st_size),
                             (before.st_dev, before.st_ino, before.st_size))
            self.assertEqual(self.queue.segments(), [])
            self.assertEqual(self.chain.tip(self.proof).next_sequence, 0)
            self.assertEqual(self.drains, 0)

    def test_debug_window_over_limit_refuses_before_raw_detachment(self):
        self.emit("one.example.com")
        original = self.debug.read_bytes()
        with self.debug.open("ab") as output:
            output.write(b"x" * (MAX_WINDOW + 1))
        live = self.queue.inbox.stat()
        bad_debug = self.debug.read_bytes()
        with self.queue.exclusive():
            with self.assertRaisesRegex(OriginalV2PrepareRefused,
                                        "debug_window_invalid_before_raw_cut"):
                self.stage()
            now = self.queue.inbox.stat()
            self.assertEqual((now.st_dev, now.st_ino, now.st_size),
                             (live.st_dev, live.st_ino, live.st_size))
            self.assertEqual(self.queue.segments(), [])
            self.assertEqual(self.chain.tip(self.proof).next_sequence, 0)
        self.assertEqual(self.drains, 0)
        self.assertEqual(self.debug.read_bytes(), bad_debug)
        self.debug.write_bytes(original)
        with self.queue.exclusive():
            self.assertEqual(self.stage().read_bytes(), b"one.example.com\n")

    def test_debug_over_four_mib_refuses_before_raw_detachment(self):
        self.emit("one.example.com")
        original = self.debug.read_bytes()
        with self.debug.open("r+b") as output:
            output.truncate(MAX_DEBUG + 1)
        live = self.queue.inbox.stat()
        with self.queue.exclusive():
            with self.assertRaisesRegex(OriginalV2PrepareRefused,
                                        "original_v2_prepared_intent_unavailable"):
                self.stage()
            now = self.queue.inbox.stat()
            self.assertEqual((now.st_dev, now.st_ino),
                             (live.st_dev, live.st_ino))
            self.assertEqual(self.queue.segments(), [])
        self.assertEqual(self.debug.stat().st_size, MAX_DEBUG + 1)
        self.assertEqual(self.drains, 0)
        self.debug.write_bytes(original)
        with self.queue.exclusive():
            self.assertEqual(self.stage().read_bytes(), b"one.example.com\n")

    def test_original_highwater_debug_one_cut_keeps_raw_and_commits_unknown(self):
        import auto_detect_original_v2_prepare as mod
        from auto_detect_fd import FDState
        self.emit("one.example.com")
        original_debug = self.debug.read_bytes()
        old_ino = self.debug.stat().st_ino
        raw_ino = self.queue.inbox.stat().st_ino
        inspected = []
        def drained_debug(path, dev, ino, *, owner, writer_gid):
            inspected.append((path, dev, ino))
            self.assertEqual(owner, self.proof.owner)
            self.assertIsNone(writer_gid)
            self.assertEqual((path.stat().st_dev, path.stat().st_ino),
                             (dev, ino))
            return FDState.DRAINED
        # The original production watermark remains 2 MiB. Only the
        # portable source test lowers it for ONE genuine original cut.
        with patch.object(mod, "DEBUG_HIGH_WATERMARK", 64):
            with self.queue.exclusive():
                pending = self.stage(inspect_debug=drained_debug)
                retired = self.root / mod.DEBUG_OLD
                self.assertEqual(retired.read_bytes(), original_debug)
                self.assertEqual(retired.stat().st_ino, old_ino)
                self.assertEqual(retired.stat().st_nlink, 1)
                self.assertNotEqual(self.debug.stat().st_ino, old_ino)
                self.assertEqual(self.debug.read_bytes(), b"")
                self.assertNotEqual(self.queue.inbox.stat().st_ino, raw_ino)
                self.assertEqual(pending.stat().st_ino, raw_ino)
                self.assertEqual(self.chain.tip(self.proof).open_intent["evidence"],
                                 "raw-first")
                self.commit_and_ack(pending, "one.example.com")
                self.assertEqual(self.chain.tip(self.proof).cursor.offset, 0)
                self.assertEqual(self.queue.segments(), [])
                self.assertGreaterEqual(len(inspected), 2)
        self.emit("two.example.com")
        with self.queue.exclusive():
            next_pending = self.stage(inspect_debug=drained_debug)
            self.assertEqual(self.chain.tip(self.proof).open_intent["evidence"],
                             "raw-first")
            self.commit_and_ack(next_pending, "two.example.com")
            self.assertTrue(self.chain.tip(self.proof).raw_first)
        self.assertEqual(retired.read_bytes(), original_debug)
        self.assertEqual(self.auto.read_text(),
                         "!manual.invalid\none.example.com\ntwo.example.com\n")

    def test_original_highwater_busy_historical_debug_fd_refuses_before_raw_cut(self):
        import auto_detect_original_v2_prepare as mod
        self.emit("one.example.com")
        old_raw, old_debug = self.queue.inbox.stat(), self.debug.stat()
        with patch.object(mod, "DEBUG_HIGH_WATERMARK", 64):
            with self.queue.exclusive():
                with self.assertRaisesRegex(OriginalV2PrepareRefused,
                                            "original_debug_old_fd_not_drained"):
                    self.stage(inspect_debug=lambda *a, **kw: FDState.BUSY)
                self.assertEqual(self.queue.inbox.stat().st_ino, old_raw.st_ino)
                self.assertEqual(self.debug.stat().st_ino, old_debug.st_ino)
                self.assertEqual(self.queue.segments(), [])
                self.assertFalse((self.root / mod.DEBUG_OLD).exists())
                self.assertFalse((self.root / mod.DEBUG_NEXT).exists())

    def test_original_highwater_crash_after_link_recovers_same_live_inode(self):
        import auto_detect_original_v2_prepare as mod
        self.emit("one.example.com")
        old_inode = self.debug.stat().st_ino
        source = self.queue.inbox.read_bytes()
        live_raw_inode = self.queue.inbox.stat().st_ino
        real_replace = os.replace
        def break_before_debug_cut(src, dst):
            if dst == self.debug:
                raise OSError("crash-before-atomic-debug-replace")
            return real_replace(src, dst)
        with patch.object(mod, "DEBUG_HIGH_WATERMARK", 64):
            with self.queue.exclusive():
                with patch.object(mod.os, "replace", side_effect=break_before_debug_cut):
                    with self.assertRaises(OriginalV2PrepareRefused):
                        self.stage(inspect_debug=lambda *a, **kw: FDState.DRAINED)
                alias = self.root / mod.DEBUG_OLD
                prepared = self.root / mod.DEBUG_NEXT
                self.assertEqual(alias.stat().st_ino, old_inode)
                self.assertEqual(self.debug.stat().st_ino, old_inode)
                self.assertEqual(self.debug.stat().st_nlink, 2)
                self.assertTrue(prepared.is_file())
                self.assertEqual(self.queue.inbox.stat().st_ino, live_raw_inode)
                self.assertEqual(self.queue.inbox.read_bytes(), source)
                pending = self.stage(inspect_debug=lambda *a, **kw: FDState.DRAINED)
                self.assertEqual(alias.stat().st_ino, old_inode)
                self.assertEqual(alias.stat().st_nlink, 1)
                self.assertNotEqual(self.debug.stat().st_ino, old_inode)
                self.assertFalse(prepared.exists())
                self.assertEqual(self.chain.tip(self.proof).open_intent["evidence"],
                                 "raw-first")
                self.commit_and_ack(pending, "one.example.com")
        self.assertEqual(self.auto.read_text(),
                         "!manual.invalid\none.example.com\n")

    def test_original_highwater_crash_after_replace_recovers_retained_debug(self):
        import auto_detect_original_v2_prepare as mod
        self.emit("one.example.com")
        old_inode = self.debug.stat().st_ino
        original_debug = self.debug.read_bytes()
        real_sync = mod._sync_directory
        called = [0]
        def break_third_sync(path):
            called[0] += 1
            if called[0] == 3:
                raise OSError("crash-after-atomic-debug-replace")
            return real_sync(path)
        with patch.object(mod, "DEBUG_HIGH_WATERMARK", 64):
            with self.queue.exclusive():
                with patch.object(mod, "_sync_directory", side_effect=break_third_sync):
                    with self.assertRaises(OriginalV2PrepareRefused):
                        self.stage(inspect_debug=lambda *a, **kw: FDState.DRAINED)
                retired = self.root / mod.DEBUG_OLD
                self.assertEqual(retired.stat().st_ino, old_inode)
                self.assertEqual(retired.read_bytes(), original_debug)
                self.assertNotEqual(self.debug.stat().st_ino, old_inode)
                self.assertEqual(self.debug.stat().st_nlink, 1)
                self.assertFalse((self.root / mod.DEBUG_NEXT).exists())
                self.assertEqual(self.queue.segments(), [])
                pending = self.stage(inspect_debug=lambda *a, **kw: FDState.DRAINED)
                self.assertEqual(self.chain.tip(self.proof).open_intent["evidence"],
                                 "raw-first")
                self.commit_and_ack(pending, "one.example.com")
        self.assertEqual(retired.read_bytes(), original_debug)

    def test_original_highwater_retained_busy_or_second_cut_refuses_without_loss(self):
        import auto_detect_original_v2_prepare as mod
        self.emit("one.example.com")
        with patch.object(mod, "DEBUG_HIGH_WATERMARK", 64):
            with self.queue.exclusive():
                pending = self.stage(inspect_debug=lambda *a, **kw: FDState.DRAINED)
                self.commit_and_ack(pending, "one.example.com")
                retired = self.root / mod.DEBUG_OLD
                retired_inode = retired.stat().st_ino
                self.emit("two.example.com")
                # A BUSY archive may never be unlinked, but pending raw
                # intake does not have to wait for old-debug retirement.
                second = self.stage(inspect_debug=lambda *a, **kw: FDState.BUSY)
                self.assertIsNotNone(second)
                self.assertEqual(retired.stat().st_ino, retired_inode)
                self.commit_and_ack(second, "two.example.com")
                self.assertEqual(self.queue.segments(), [])
                with self.assertRaisesRegex(OriginalV2PrepareRefused,
                                            "retained_debug_writer_fd_not_drained"):
                    self.stage(inspect_debug=lambda *a, **kw: FDState.BUSY)
                self.assertEqual(retired.stat().st_ino, retired_inode)
        # The original FD check is required for cleanup, not for
        # independently ACK-proven current-generation raw intake.
        self.assertTrue(retired.exists())
    def test_original_second_highwater_requires_acked_raw_then_retires_once(self):
        import auto_detect_original_v2_prepare as mod
        native_drained = lambda *a, **kw: FDState.DRAINED
        self.emit("one.example.com")
        with patch.object(mod, "DEBUG_HIGH_WATERMARK", 64):
            with self.queue.exclusive():
                first = self.stage(inspect_debug=native_drained)
                retained = self.root / mod.DEBUG_OLD
                first_ino = retained.stat().st_ino
                self.commit_and_ack(first, "one.example.com")
        self.emit("two.example.com")
        with patch.object(mod, "DEBUG_HIGH_WATERMARK", 64):
            with self.queue.exclusive():
                # A large second diagnostic file must not block the next
                # genuine raw batch merely because the first archive exists.
                second = self.stage(inspect_debug=native_drained)
                self.assertEqual(retained.stat().st_ino, first_ino)
                self.commit_and_ack(second, "two.example.com")
            with self.queue.exclusive():
                now_old = self.debug.stat().st_ino
                before_second = self.debug.read_bytes()
                self.assertIsNone(self.stage(inspect_debug=native_drained))
                self.assertEqual(retained.stat().st_ino, now_old)
                self.assertNotEqual(retained.stat().st_ino, first_ino)
                self.assertEqual(retained.read_bytes(), before_second)
                self.assertNotEqual(self.debug.stat().st_ino, now_old)
                self.assertEqual(self.debug.read_bytes(), b"")
                self.assertEqual(self.queue.segments(), [])
        self.emit("three.example.com")
        with patch.object(mod, "DEBUG_HIGH_WATERMARK", 64):
            with self.queue.exclusive():
                # Repeated raw-first intake is not forced to wait for
                # archive deletion, and does not signal the native engine.
                third = self.stage(inspect_debug=native_drained)
                self.assertEqual(retained.stat().st_ino, now_old)
                self.commit_and_ack(third, "three.example.com")
            with self.queue.exclusive():
                # The next idle tick may retire the second archive and
                # cut the third original debug inode.
                newest = self.debug.stat().st_ino
                self.assertIsNone(self.stage(inspect_debug=native_drained))
                self.assertEqual(retained.stat().st_ino, newest)
                self.assertEqual(self.debug.read_bytes(), b"")
        self.assertEqual(
            self.auto.read_text(),
            "!manual.invalid\none.example.com\ntwo.example.com\nthree.example.com\n")
    def test_original_debug_retirement_refuses_unacked_and_live_raw(self):
        import auto_detect_original_v2_prepare as mod
        native_drained = lambda *a, **kw: FDState.DRAINED
        self.emit("one.example.com")
        with patch.object(mod, "DEBUG_HIGH_WATERMARK", 64):
            with self.queue.exclusive():
                first = self.stage(inspect_debug=native_drained)
                retained = self.root / mod.DEBUG_OLD
                self.debug.write_bytes(b"x" * 80 + b"\n")
                self.assertEqual(self.stage(inspect_debug=native_drained), first)
                self.assertTrue(retained.exists())
                self.commit_and_ack(first, "one.example.com")
                self.queue.inbox.write_bytes(b"two.example.com\n")
                old_id = retained.stat().st_ino
                # Previously this rejected the whole minute when active
                # raw had uncommitted events. It now processes raw first
                # while preserving the still-unretired archived inode.
                second = self.stage(inspect_debug=native_drained)
                self.assertEqual(retained.stat().st_ino, old_id)
                self.commit_and_ack(second, "two.example.com")
                self.assertEqual(self.queue.inbox.read_bytes(), b"")
                self.assertTrue(retained.exists())
            with self.queue.exclusive():
                with self.assertRaisesRegex(OriginalV2PrepareRefused,
                                            "retained_debug_writer_fd_not_drained"):
                    self.stage(inspect_debug=lambda *a, **kw: FDState.BUSY)
                self.assertEqual(retained.stat().st_ino, old_id)
                self.assertEqual(self.queue.segments(), [])
    def test_original_512_slot_chain_rolls_over_twice_without_engine_action(self):
        import auto_detect_cursor_chain as chain_mod
        import auto_detect_original_v2_prepare as prep_mod
        with patch.object(chain_mod, "MAX_STEPS", 2), \
             patch.object(prep_mod, "MAX_STEPS", 2):
            for step in range(1, 6):
                host = f"durable-{step}.example.com"
                self.emit(host)
                with self.queue.exclusive():
                    pending = self.stage()
                    self.assertIsNotNone(pending)
                    self.commit_and_ack(pending, host)
                if step in (2, 4):
                    with self.queue.exclusive():
                        # The next raw-free minute seals the fully ACKed
                        # original cursor and reclaims the prior root.
                        self.assertIsNone(self.stage())
                        tip = self.chain.tip(self.proof)
                        self.assertEqual(tip.cycle, step // 2)
                        self.assertEqual(tip.next_sequence, 0)
                        epoch = self.receipts.root / self.proof.generation
                        self.assertTrue((epoch / "cursor-chain-v2" /
                                         "anchor.json").exists())
                        self.assertFalse((epoch / "cursor-chain-v2.old").exists())
                        self.assertFalse((epoch / "cursor-chain-v2.next").exists())
            with self.queue.exclusive():
                tip = self.chain.tip(self.proof)
                self.assertEqual((tip.cycle, tip.next_sequence), (2, 1))
            for step in range(1, 6):
                self.assertIn(f"durable-{step}.example.com\n", self.auto.read_text())

    def test_original_cursor_rollover_crash_recovers_ack_without_replay(self):
        import auto_detect_cursor_chain as chain_mod
        import auto_detect_original_v2_prepare as prep_mod
        with patch.object(chain_mod, "MAX_STEPS", 2), \
             patch.object(prep_mod, "MAX_STEPS", 2):
            for step in range(2):
                host = f"ack-{step}.example.com"
                self.emit(host)
                with self.queue.exclusive():
                    pending = self.stage()
                    self.commit_and_ack(pending, host)
            with self.queue.exclusive():
                with patch.object(CursorChain, "_erase_old_tree",
                                  side_effect=OSError("injected-after-durable-anchor")):
                    with self.assertRaises(OriginalV2PrepareRefused):
                        self.stage()
                epoch = self.receipts.root / self.proof.generation
                self.assertTrue((epoch / "cursor-chain-v2.old").exists())
                self.assertEqual(self.chain.tip(self.proof).cycle, 1)
            with self.queue.exclusive():
                self.assertIsNone(self.stage())
                self.assertFalse((epoch / "cursor-chain-v2.old").exists())
                self.assertEqual(self.chain.tip(self.proof).cycle, 1)
            self.emit("after-crash.example.com")
            with self.queue.exclusive():
                pending = self.stage()
                self.commit_and_ack(pending, "after-crash.example.com")
            self.assertEqual(self.auto.read_text().count("after-crash.example.com"), 1)

    def test_original_cursor_rollover_recovers_staged_receipt_hardlinks(self):
        import auto_detect_cursor_chain as chain_mod
        import auto_detect_original_v2_prepare as prep_mod
        from auto_detect_epoch_receipts import _canonical
        with patch.object(chain_mod, "MAX_STEPS", 2), \
             patch.object(prep_mod, "MAX_STEPS", 2):
            for cycle in (1, 2):
                for ordinal in (0, 1):
                    host = f"stage-{cycle}-{ordinal}.example.com"
                    self.emit(host)
                    with self.queue.exclusive():
                        pending = self.stage()
                        self.commit_and_ack(pending, host)
                with self.queue.exclusive():
                    root, _, epoch_bytes = self.chain._root(
                        self.proof, create=False)
                    anchor = self.chain._next_anchor(
                        self.proof, epoch_bytes, self.chain.tip(self.proof))
                    staged = root.parent / "cursor-chain-v2.next"
                    staged.mkdir(mode=0o700)
                    temp = staged / ("." + "f" * 32 + ".part")
                    temp.write_bytes(_canonical(anchor))
                    temp.chmod(0o600)
                    if cycle == 1:
                        # Crash after hardlink before unlink leaves two
                        # names for the same protected staged receipt.
                        os.link(temp, staged / "anchor.json")
                        self.assertEqual(temp.stat().st_nlink, 2)
                    # Cycle 2 simulates crash before durable hardlink.
                    self.assertIsNone(self.stage())
                    self.assertEqual(self.chain.tip(self.proof).cycle, cycle)
                    self.assertFalse(staged.exists())
                    self.assertFalse((root.parent /
                                      "cursor-chain-v2.old").exists())
            with self.queue.exclusive():
                self.assertEqual(self.chain.tip(self.proof).cycle, 2)

    def test_four_continuous_highwater_cycles_without_debug_stall(self):
        import auto_detect_original_v2_prepare as mod
        drained = lambda *a, **kw: FDState.DRAINED
        prior_archive = None
        with patch.object(mod, "DEBUG_HIGH_WATERMARK", 64):
            for number in range(1, 5):
                host = f"repeated-{number}.example.com"
                self.emit(host)
                with self.queue.exclusive():
                    pending = self.stage(inspect_debug=drained)
                    self.assertIsNotNone(pending)
                    self.commit_and_ack(pending, host)
                    archived = self.root / mod.DEBUG_OLD
                    if prior_archive is not None:
                        self.assertEqual(archived.stat().st_ino, prior_archive)
                with self.queue.exclusive():
                    before_cut = self.debug.stat().st_ino
                    self.assertIsNone(self.stage(inspect_debug=drained))
                    self.assertEqual(archived.stat().st_ino, before_cut)
                    self.assertEqual(self.debug.read_bytes(), b"")
                    self.assertEqual(self.queue.segments(), [])
                    prior_archive = archived.stat().st_ino
        self.assertEqual(self.chain.tip(self.proof).next_sequence, 4)
        for number in range(1, 5):
            self.assertIn(f"repeated-{number}.example.com\n", self.auto.read_text())

    def test_original_debug_retirement_refuses_corrupted_old_archive(self):
        import auto_detect_original_v2_prepare as mod
        self.emit("one.example.com")
        with patch.object(mod, "DEBUG_HIGH_WATERMARK", 64):
            with self.queue.exclusive():
                first = self.stage(inspect_debug=lambda *a, **kw: FDState.DRAINED)
                self.commit_and_ack(first, "one.example.com")
                retained = self.root / mod.DEBUG_OLD
                with retained.open("ab") as out:
                    out.write(b"\x00")
                self.debug.write_bytes(b"x" * 80 + b"\n")
                with self.assertRaisesRegex(OriginalV2PrepareRefused,
                                            "retained_debug_cursor_or_content_changed"):
                    self.stage(inspect_debug=lambda *a, **kw: FDState.DRAINED)
                self.assertTrue(retained.exists())
                self.assertEqual(self.queue.segments(), [])

    def test_original_debug_retirement_crash_after_unlink_retries_second_cut(self):
        import auto_detect_original_v2_prepare as mod
        self.emit("one.example.com")
        with patch.object(mod, "DEBUG_HIGH_WATERMARK", 64):
            with self.queue.exclusive():
                first = self.stage(inspect_debug=lambda *a, **kw: FDState.DRAINED)
                self.commit_and_ack(first, "one.example.com")
                retained = self.root / mod.DEBUG_OLD
                self.debug.write_bytes(b"x" * 80 + b"\n")
                old_active = self.debug.stat().st_ino
                actual_sync = mod._sync_directory
                failed = [False]
                def fault_after_safe_unlink(path):
                    if not retained.exists() and not failed[0]:
                        failed[0] = True
                        raise OSError("crash-after-acked-retained-unlink")
                    return actual_sync(path)
                with patch.object(mod, "_sync_directory",
                                  side_effect=fault_after_safe_unlink):
                    with self.assertRaises(OriginalV2PrepareRefused):
                        self.stage(inspect_debug=lambda *a, **kw: FDState.DRAINED)
                self.assertTrue(failed[0])
                self.assertFalse(retained.exists())
                self.assertEqual(self.debug.stat().st_ino, old_active)
                self.assertIsNone(self.stage(
                    inspect_debug=lambda *a, **kw: FDState.DRAINED))
                self.assertEqual(retained.stat().st_ino, old_active)
                self.assertEqual(self.debug.read_bytes(), b"")
                self.assertEqual(self.queue.segments(), [])

    def test_debug_replacement_selects_generation_sticky_raw_first(self):
        self.emit("one.example.com")
        original = self.debug.read_bytes()
        archived = self.root / "original-debug"
        os.replace(self.debug, archived)
        self.debug.write_bytes(original)
        self.debug.chmod(0o600)
        with self.queue.exclusive():
            first = self.stage()
            intent = self.chain.tip(self.proof).open_intent
            self.assertEqual(intent["evidence"], "raw-first")
            self.assertEqual(intent["candidate_count"], 1)
            self.assertEqual(intent["debug_start_offset"], intent["debug_end_offset"])
            self.commit_and_ack(first, "one.example.com")
            self.assertTrue(self.chain.tip(self.proof).raw_first)
        # A restored matching historical debug inode may NOT revert an
        # authenticated generation to earlier debug/native classification.
        os.replace(archived, self.debug)
        self.emit("two.example.com")
        with self.queue.exclusive():
            second = self.stage()
            self.assertEqual(self.chain.tip(self.proof).open_intent["evidence"],
                             "raw-first")
            self.commit_and_ack(second, "two.example.com")
            self.assertTrue(self.chain.tip(self.proof).raw_first)
        self.assertEqual(self.auto.read_text(),
                         "!manual.invalid\none.example.com\ntwo.example.com\n")

    def test_live_cross_inode_raw_first_commits_original_pending_once(self):
        # True P2a: raw is cut FIRST. The second raw positive is written
        # to the NEW raw but OLD debug. Then the debug name is atomically
        # replaced while the old debug inode stays hardlink-reachable.
        self.emit("one.example.com")
        with self.queue.exclusive():
            first = self.queue.rotate(generation=self.generation)
            first_ino = first.stat().st_ino
            second_ino = self.queue.inbox.stat().st_ino
            self.assertNotEqual(first_ino, second_ino)
            self.emit("midcut.example.com")
            old_debug_bytes = self.debug.read_bytes()
            archived = self.root / "previous-native-debug"
            replacement = self.root / ".prepared-native-debug"
            replacement.write_bytes(b"")
            replacement.chmod(0o600)
            os.link(self.debug, archived)
            self.assertEqual(archived.stat().st_nlink, 2)
            os.replace(replacement, self.debug)
            self.assertEqual(archived.stat().st_nlink, 1)
            self.assertEqual(self.debug.stat().st_nlink, 1)
            self.assertNotEqual(archived.stat().st_ino, self.debug.stat().st_ino)
            self.assertEqual(archived.read_bytes(), old_debug_bytes)
            self.assertEqual(self.debug.read_bytes(), b"")
            self.assertEqual(first.read_bytes(), b"one.example.com\n")
            self.assertEqual(self.queue.inbox.read_bytes(),
                             b"midcut.example.com\n")

            self.assertEqual(self.stage(), first)
            self.assertEqual(self.chain.tip(self.proof).open_intent["evidence"],
                             "raw-first")
            self.commit_and_ack(first, "one.example.com")
            self.assertEqual(self.chain.tip(self.proof).cursor.offset, 0)
            self.assertEqual(self.queue.inbox.stat().st_ino, second_ino)
            second = self.stage()
            self.assertEqual(second.stat().st_ino, second_ino)
            self.assertEqual(self.chain.tip(self.proof).open_intent["evidence"],
                             "raw-first")
            self.commit_and_ack(second, "midcut.example.com")
            self.emit("aftercut.example.com")
            third = self.stage()
            self.assertEqual(self.chain.tip(self.proof).open_intent["evidence"],
                             "raw-first")
            self.commit_and_ack(third, "aftercut.example.com")
            self.assertEqual(self.chain.tip(self.proof).next_sequence, 3)
            self.assertTrue(self.chain.tip(self.proof).raw_first)
            self.assertEqual(self.queue.segments(), [])
        self.assertEqual(archived.read_bytes(), old_debug_bytes)
        self.assertEqual(self.auto.read_text(),
                         "!manual.invalid\none.example.com\nmidcut.example.com\n"
                         "aftercut.example.com\n")

    def test_raw_first_rejects_malformed_detached_raw_without_ack(self):
        self.emit("one.example.com")
        archive = self.root / "old-debug"
        os.replace(self.debug, archive)
        self.debug.write_bytes(b"")
        self.debug.chmod(0o600)
        self.queue.inbox.write_bytes(b"invalid..example.com\n")
        with self.queue.exclusive():
            with self.assertRaisesRegex(OriginalV2PrepareRefused,
                                        "original_v2_prepared_intent_unavailable"):
                self.stage()
            pending = self.queue.segments()
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0].read_bytes(),
                             b"invalid..example.com\n")
            self.assertEqual(self.chain.tip(self.proof).next_sequence, 0)
        self.assertEqual(self.auto.read_text(), "!manual.invalid\n")

    def test_raw_first_refuses_unprotected_new_debug_path_before_cut(self):
        self.emit("one.example.com")
        archived = self.root / "old-debug"
        os.replace(self.debug, archived)
        self.debug.symlink_to(archived)
        live_ino = self.queue.inbox.stat().st_ino
        with self.queue.exclusive():
            with self.assertRaisesRegex(OriginalV2PrepareRefused,
                                        "original_v2_prepared_intent_unavailable"):
                self.stage()
            self.assertEqual(self.queue.inbox.stat().st_ino, live_ino)
            self.assertEqual(self.queue.segments(), [])
        self.assertEqual(self.auto.read_text(), "!manual.invalid\n")

    def test_original_p2k8o_recovers_existing_native_debug_intent(self):
        self.emit("one.example.com")
        with self.queue.exclusive():
            pending = self.stage()
            folder = self.chain.tip(self.proof).open_folder
            original = (folder / "intent.json").read_bytes()
            previous = self.debug.with_name("original-debug-retained")
            new = self.debug.with_name(".new-debug-retained")
            new.write_bytes(b"")
            new.chmod(0o600)
            os.link(self.debug, previous)
            os.replace(new, self.debug)
            self.assertEqual(self.stage(), pending)
            self.assertEqual((folder / "intent.json").read_bytes(), original)
            self.assertTrue((folder / "recovery.json").exists())
            self.assertEqual(self.chain.tip(self.proof).open_intent["evidence"],
                             "raw-first")
            self.commit_and_ack(pending, "one.example.com")
            self.assertTrue(self.chain.tip(self.proof).raw_first)
            self.assertEqual(self.chain.tip(self.proof).cursor.offset, 0)
        self.assertEqual(previous.read_bytes().count(b"adding to "), 1)

    def test_original_prepared_checkpoint_after_debug_cut_replays_only_ack(self):
        self.emit("one.example.com")
        with self.queue.exclusive():
            pending = self.stage()
            folder = self.chain.tip(self.proof).open_folder
            intent = (folder / "intent.json").read_bytes()
            cp = self.chain.commit(
                self.proof, pending,
                {"auto": {"add": ["one.example.com"], "remove": []}},
                self.writer, attest=self.attest, inspect=self.drained)
            archive = self.debug.with_name("prior-checkpoint-native-debug")
            prepared = self.debug.with_name(".prepared-next-native-debug")
            prepared.write_bytes(b"")
            prepared.chmod(0o600)
            os.link(self.debug, archive)
            os.replace(prepared, self.debug)
            self.auto.write_text("!manual.invalid\n")
            self.assertEqual(self.stage(), pending)
            self.assertFalse((folder / "recovery.json").exists())
            self.assertEqual((folder / "intent.json").read_bytes(), intent)
            self.assertEqual(self.chain.commit(
                self.proof, pending,
                {"auto": {"add": ["one.example.com"], "remove": []}},
                self.writer, attest=self.attest, inspect=self.drained), cp)
            self.assertTrue(self.chain.acknowledge(
                self.proof, pending, cp, self.writer,
                attest=self.attest, inspect=self.drained))
            self.assertFalse(pending.exists())
            self.assertFalse(self.chain.tip(self.proof).raw_first)
            self.assertGreater(self.chain.tip(self.proof).cursor.offset, 0)
        self.assertEqual(self.auto.read_text(), "!manual.invalid\n")
        self.assertEqual(archive.read_bytes().count(b"adding to "), 1)

    def test_original_partial_plan_after_debug_cut_stages_readonly(self):
        self.emit("one.example.com")
        with self.queue.exclusive():
            pending = self.stage()
            folder = self.chain.tip(self.proof).open_folder
            import auto_detect_destination_commit as mod
            with patch.object(mod, "_replace", side_effect=OSError("target interrupted")):
                with self.assertRaises(CursorChainRefused):
                    self.chain.commit(
                        self.proof, pending,
                        {"auto": {"add": ["one.example.com"], "remove": []}},
                        self.writer, attest=self.attest, inspect=self.drained)
            old = self.debug.with_name("old-partial-v2-debug")
            new = self.debug.with_name(".new-partial-v2-debug")
            new.write_bytes(b"")
            new.chmod(0o600)
            os.link(self.debug, old)
            os.replace(new, self.debug)
            self.assertEqual(self.stage(), pending)
            self.assertFalse((folder / "destination" / "checkpoint.json").exists())
            self.assertFalse((folder / "recovery.json").exists())
            self.assertTrue(pending.exists())

    def test_prior_ack_debug_tamper_refuses_second_original_raw_cut(self):
        self.emit("one.example.com")
        with self.queue.exclusive():
            first = self.stage()
            self.commit_and_ack(first, "one.example.com")
        original_prefix = self.debug.read_bytes()
        self.emit("two.example.com")
        complete = self.debug.read_bytes()
        self.debug.write_bytes(b"X" + complete[1:])
        live = self.queue.inbox.stat()
        with self.queue.exclusive():
            with self.assertRaisesRegex(OriginalV2PrepareRefused,
                                        "debug_cursor_invalid_before_raw_cut"):
                self.stage()
            self.assertEqual(self.queue.inbox.stat().st_ino, live.st_ino)
            self.assertEqual(self.queue.segments(), [])
            self.assertEqual(self.chain.tip(self.proof).next_sequence, 1)
        self.assertEqual(self.queue.inbox.read_bytes(), b"two.example.com\n")
        self.debug.write_bytes(original_prefix + complete[len(original_prefix):])
        with self.queue.exclusive():
            second = self.stage()
            self.assertEqual(second.read_bytes(), b"two.example.com\n")
            self.commit_and_ack(second, "two.example.com")

    def test_incomplete_native_debug_line_refuses_before_raw_cut(self):
        self.emit("one.example.com")
        original = self.debug.read_bytes()
        with self.debug.open("ab") as output:
            output.write(b"incomplete")
        live = self.queue.inbox.stat()
        with self.queue.exclusive():
            with self.assertRaisesRegex(OriginalV2PrepareRefused,
                                        "debug_window_invalid_before_raw_cut"):
                self.stage()
            self.assertEqual(self.queue.inbox.stat().st_ino, live.st_ino)
            self.assertEqual(self.queue.segments(), [])
        self.assertEqual(self.drains, 0)
        self.debug.write_bytes(original)
        with self.queue.exclusive():
            self.assertEqual(self.stage().read_bytes(), b"one.example.com\n")

    def test_original_v2_late_hardlink_append_refuses_and_recovers_same_raw(self):
        # Same real P2k8o/v2 preparation, not a synthetic alternate queue:
        # native writer appends a second event *after* the first link, before
        # replace. The original source must not stage an incomplete intent.
        self.emit("one.example.com")
        old_inode = self.queue.inbox.stat().st_ino
        original_link = os.link

        def link_then_producer_append(source, target, **kwargs):
            original_link(source, target, **kwargs)
            with self.queue.inbox.open("ab", buffering=0) as output:
                output.write(b"two.example.com\n")
                os.fsync(output.fileno())
            with self.debug.open("a", encoding="ascii") as out:
                out.write(
                    f"2026-11-14 11:10:01 : two.example.com : profile 2 (tail) : "
                    f"client 127.0.0.1:1234 : proto http : adding to "
                    f"{self.queue.inbox}\n"
                )

        with self.queue.exclusive():
            with patch("auto_detect_queue.os.link",
                       side_effect=link_then_producer_append):
                with self.assertRaisesRegex(
                    OriginalV2PrepareRefused, "original_v2_prepared_intent_unavailable"
                ):
                    self.stage()
            pending = self.queue.segments()
            self.assertEqual(len(pending), 1)
            self.assertEqual(self.queue.inbox.stat().st_ino, old_inode)
            self.assertEqual(pending[0].stat().st_ino, old_inode)
            self.assertEqual(pending[0].stat().st_nlink, 2)
            self.assertEqual(self.chain.tip(self.proof).next_sequence, 0)
            self.assertEqual(self.drains, 0)
            self.assertEqual(self.queue.inbox.read_bytes(),
                             b"one.example.com\ntwo.example.com\n")
            # Recovery uses one original generation, same inode, both actual
            # correlated native-format events; no new queue or parser.
            self.assertEqual(self.stage(), pending[0])
            intent = self.chain.tip(self.proof).open_intent
            self.assertEqual(intent["candidate_count"], 2)
            self.assertEqual(pending[0].stat().st_nlink, 1)

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
