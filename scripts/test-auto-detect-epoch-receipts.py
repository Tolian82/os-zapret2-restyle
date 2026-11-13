#!/usr/bin/env python3
"""P2k2a: real-file root-private epoch and pending-intent recovery; NOT commit."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest

BACKEND = Path(__file__).resolve().parents[1] / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

from auto_detect_debug_window import Cursor, Window, Candidate, empty_epoch, propose_window
from auto_detect_epoch_receipts import (
    EpochReceipts, ReceiptRefused, ROOT, run_native_epoch_worker
)
from auto_detect_fd import OwnerToken
from auto_detect_owner import GenerationProof


class EpochTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="p2k2a-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.base.chmod(0o700)
        self.producer = self.base / "producer"
        self.producer.mkdir(mode=0o700)
        self.pending = self.producer / "pending"
        self.pending.mkdir(mode=0o700)
        self.raw = self.producer / "inbox.txt"
        self.debug = self.producer / "debug.log"
        self.raw.write_bytes(b"")
        self.debug.write_bytes(b"")
        self.raw.chmod(0o600)
        self.debug.chmod(0o600)
        self.generation = "a" * 32
        self.proof = GenerationProof(
            OwnerToken(4321, "Fri Nov 13 10:00:00 2026", "/usr/local/sbin/dvtws2"),
            self.generation, self.generation, "b" * 64,
            str(self.raw), str(self.debug), 2,
            ((0, "unknown-native-default", None),
             (1, "known-hostlist", "youtube"), (2, "observer", None)))
        self.cursor = empty_epoch(self.proof, owner_uid=os.geteuid())
        self.store = EpochReceipts(self.base / "epochs", owner_uid=os.geteuid())

    def begin(self):
        self.store.begin(self.proof, self.cursor)

    def event(self, *, hostname="blocked.p2k2.invalid"):
        self.debug.write_text(
            f"2026-11-13 13:15:30 : {hostname} : profile 2 (tail) : "
            f"client 127.0.0.1:4321 : proto http : adding to {self.raw}\n",
            encoding="ascii")
        raw = hostname.encode("ascii") + b"\n"
        name = self.generation + "-" + "c" * 32 + ".txt"
        segment = self.pending / name
        segment.write_bytes(raw)
        segment.chmod(0o600)
        return segment, propose_window(self.proof, self.cursor, raw,
                                       owner_uid=os.geteuid())

    def test_root_epoch_real_debug_inode_and_recovery(self):
        self.begin()
        receipt = self.store.historical(self.generation)
        self.assertIsNone(receipt.intent)
        self.assertFalse(receipt.epoch["ack_authorized"])
        self.assertEqual(receipt.epoch["debug_inode"], self.debug.stat().st_ino)
        self.assertEqual(receipt.epoch["committed_cursor_offset"], 0)
        epoch = self.base / "epochs" / self.generation / "epoch.json"
        self.assertEqual(epoch.stat().st_mode & 0o777, 0o600)
        self.assertEqual(epoch.stat().st_nlink, 1)

    def test_begin_rejects_fabricated_inode(self):
        with self.assertRaisesRegex(ReceiptRefused, "initial_debug_inode_does_not_match"):
            self.store.begin(self.proof, replace(self.cursor, inode=123))
        self.assertFalse((self.base / "epochs").exists())

    def test_begin_refuses_preexisting_debug_history(self):
        self.debug.write_bytes(b"earlier-event\n")
        with self.assertRaisesRegex(ReceiptRefused, "no_trusted_empty_debug_epoch"):
            self.begin()

    def test_intent_survives_restart_but_is_never_a_commit(self):
        self.begin()
        segment, window = self.event()
        self.store.stage(self.proof, self.cursor, window, segment)
        again = EpochReceipts(self.base / "epochs", owner_uid=os.geteuid())
        recovered = again.historical(self.generation)
        self.assertEqual(recovered.intent["pending_name"], segment.name)
        self.assertEqual(recovered.intent["pending_inode"], segment.stat().st_ino)
        self.assertEqual(recovered.intent["pending_sha256"],
                         hashlib.sha256(segment.read_bytes()).hexdigest())
        self.assertEqual(recovered.intent["debug_end_offset"],
                         window.proposed_cursor.offset)
        self.assertEqual(recovered.epoch["committed_cursor_offset"], 0)
        self.assertIs(recovered.intent["ack_authorized"], False)
        self.assertTrue(segment.exists())  # staging never deletes pending
        self.store.stage(self.proof, self.cursor, window, segment)  # immutable replay
        self.assertEqual(len(list((self.base/"epochs"/self.generation).iterdir())), 2)

    def test_second_pending_never_overwrites_or_advances_first(self):
        self.begin()
        segment, window = self.event()
        self.store.stage(self.proof, self.cursor, window, segment)
        sibling = self.pending / (self.generation + "-" + "d" * 32 + ".txt")
        sibling.write_bytes(segment.read_bytes())
        sibling.chmod(0o600)
        with self.assertRaisesRegex(ReceiptRefused, "older_pending_intent_not_committed"):
            self.store.stage(self.proof, self.cursor, window, sibling)
        self.assertEqual(self.store.historical(self.generation).intent["pending_name"],
                         segment.name)

    def test_forged_debug_window_is_not_staged(self):
        self.begin()
        segment, window = self.event()
        forged = replace(window, proposed_cursor=replace(
            window.proposed_cursor, offset=window.proposed_cursor.offset + 1))
        with self.assertRaisesRegex(ReceiptRefused, "caller_window_differs_from_native_debug"):
            self.store.stage(self.proof, self.cursor, forged, segment)
        self.assertIsNone(self.store.historical(self.generation).intent)

    def test_producer_debug_modified_after_proposed_window_refuses(self):
        self.begin()
        segment, window = self.event()
        self.debug.write_bytes(self.debug.read_bytes() + b"X")
        with self.assertRaisesRegex(ReceiptRefused, "native_debug_does_not_support_pending"):
            self.store.stage(self.proof, self.cursor, window, segment)

    def test_partial_segment_refused_before_intent(self):
        self.begin()
        segment, window = self.event()
        segment.write_bytes(b"incomplete.p2k2.invalid")
        with self.assertRaisesRegex(ReceiptRefused, "incomplete_pending_segment"):
            self.store.stage(self.proof, self.cursor, window, segment)

    def test_alias_live_inbox_refused_even_if_bytes_identical(self):
        self.begin()
        segment, window = self.event()
        segment.unlink()
        self.raw.write_bytes(b"blocked.p2k2.invalid\n")
        os.link(self.raw, segment)
        with self.assertRaisesRegex(ReceiptRefused, "pending_inode_not_fully_rotated"):
            self.store.stage(self.proof, self.cursor, window, segment)

    def test_wrong_generation_or_sealed_original_sha_refused(self):
        self.begin()
        segment, window = self.event()
        changed = replace(self.proof, final_args_sha256="c" * 64)
        with self.assertRaisesRegex(ReceiptRefused, "epoch_differs_from_original_owner"):
            self.store.stage(changed, self.cursor, window, segment)
        wrong = replace(self.proof, generation="d" * 32,
                        operation_id="d" * 32)
        with self.assertRaises(ReceiptRefused):
            self.store.stage(wrong, self.cursor, window, segment)

    def test_preexisting_collision_or_foreign_partial_fails_closed(self):
        self.begin()
        folder = self.base / "epochs" / self.generation
        (folder / ".leftover.part").write_bytes(b"old")
        with self.assertRaisesRegex(ReceiptRefused, "foreign_or_ambiguous_generation_receipt"):
            self.store.historical(self.generation)

    def test_epoch_mode_symlink_and_hardlink_fail_closed(self):
        self.begin()
        folder = self.base / "epochs" / self.generation
        path = folder / "epoch.json"
        path.chmod(0o666)
        with self.assertRaisesRegex(ReceiptRefused, "untrusted_receipt"):
            self.store.historical(self.generation)
        path.chmod(0o600)
        alt = self.base / "extra-epoch.json"
        os.link(path, alt)
        with self.assertRaisesRegex(ReceiptRefused, "untrusted_receipt"):
            self.store.historical(self.generation)

    def test_public_entrypoint_refuses_any_live_action(self):
        with self.assertRaisesRegex(ReceiptRefused,
                                    "no_live_fd9_or_durable_destination_commit"):
            run_native_epoch_worker()


if __name__ == "__main__":
    unittest.main()
