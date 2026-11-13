#!/usr/bin/env python3
"""#1052 P2k2b: physical-file commit, cursor, crash replay and GUI conflict."""
from __future__ import annotations

import fcntl
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

BACKEND = Path(__file__).resolve().parents[1] / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

from auto_detect_debug_window import empty_epoch, propose_window
from auto_detect_epoch_receipts import EpochReceipts
from auto_detect_fd import OwnerToken
from auto_detect_owner import GenerationProof
from auto_detect_queue import DurableInbox
from auto_detect_destination_commit import DestinationCommit, DestinationRefused, run_native_destination_writer


class CommitTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="p2k2b-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.base.chmod(0o700)
        self.producer = self.base / "producer"
        self.producer.mkdir(mode=0o700)
        (self.producer / "pending").mkdir(mode=0o700)
        self.queue = DurableInbox(self.producer, owner_uid=os.geteuid())
        self.raw = self.producer / "inbox.txt"
        self.debug = self.producer / "debug.log"
        self.raw.write_bytes(b"")
        self.debug.write_bytes(b"")
        self.raw.chmod(0o600)
        self.debug.chmod(0o600)
        generation = "a" * 32
        self.proof = GenerationProof(
            OwnerToken(4321, "Fri Nov 13 10:00:00 2026", "/usr/local/sbin/dvtws2"),
            generation, generation, "b" * 64,
            str(self.raw), str(self.debug), 2,
            ((0, "unknown-native-default", None),
             (1, "known-hostlist", "youtube"), (2, "observer", None)))
        cursor = empty_epoch(self.proof, owner_uid=os.geteuid())
        self.receipts = EpochReceipts(self.base / "epochs", owner_uid=os.geteuid())
        self.receipts.begin(self.proof, cursor)
        host = "blocked.p2k2.invalid"
        self.debug.write_text(
            f"2026-11-13 13:15:30 : {host} : profile 2 (tail) : "
            f"client 127.0.0.1:4321 : proto http : adding to {self.raw}\n",
            encoding="ascii")
        data = (host + "\n").encode()
        name = generation + "-" + "c" * 32 + ".txt"
        self.segment = self.queue.pending / name
        self.segment.write_bytes(data)
        self.segment.chmod(0o600)
        self.receipts.stage(self.proof, cursor,
                            propose_window(self.proof, cursor, data,
                                           owner_uid=os.geteuid()), self.segment)
        self.lists = self.base / "lists"
        self.lists.mkdir(mode=0o700)
        self.auto = self.lists / "auto-domains.txt"
        self.youtube = self.lists / "youtube.auto.txt"
        self.auto.write_text("!manual.invalid\n", encoding="utf-8")
        self.youtube.write_text("keep.example\n", encoding="utf-8")
        self.auto.chmod(0o600)
        self.youtube.chmod(0o600)
        self.lock = self.lists / ".writer.lock"
        self.writer = DestinationCommit(self.receipts, self.queue,
                                        {"auto": self.auto, "youtube": self.youtube},
                                        self.lock)
        self.effects = {"auto": {"add": ["example.com"], "remove": []},
                        "youtube": {"add": ["sample.com"], "remove": []}}

    def commit(self):
        with self.queue.exclusive():
            return self.writer.commit(self.proof, self.segment, self.effects)

    def test_physical_multi_target_checkpoint_and_replay(self):
        c = self.commit()
        self.assertEqual(c["committed_cursor_offset"],
                         self.receipts.historical(self.proof.generation).intent["debug_end_offset"])
        self.assertFalse(c["ack_authorized"])
        self.assertEqual(self.auto.read_text(), "!manual.invalid\nexample.com\n")
        self.assertEqual(self.youtube.read_text(), "keep.example\nsample.com\n")
        self.assertTrue(self.segment.exists())
        # An explicitly removed entry stays removed after commit replay.
        self.auto.write_text("!manual.invalid\n")
        self.assertEqual(self.commit(), c)
        self.assertEqual(self.auto.read_text(), "!manual.invalid\n")

    def test_interruption_after_first_file_replays_without_duplicate(self):
        import auto_detect_destination_commit as module
        original = module._replace
        calls = []
        def interruption(*args):
            if calls:
                raise OSError("injected second-file fsync failure")
            calls.append(1)
            return original(*args)
        with patch.object(module, "_replace", side_effect=interruption):
            with self.assertRaises(OSError):
                self.commit()
        self.assertTrue(self.segment.exists())
        self.assertTrue((self.base/"epochs"/self.proof.generation/"destination"/"plan.json").exists())
        self.assertFalse((self.base/"epochs"/self.proof.generation/"destination"/"checkpoint.json").exists())
        c = self.commit()
        self.assertEqual(c["kind"], "destination-and-cursor-committed")
        self.assertEqual(self.auto.read_text().count("example.com"), 1)
        self.assertEqual(self.youtube.read_text().count("sample.com"), 1)

    def test_manual_concurrent_edit_preserved_and_pending_retained(self):
        import auto_detect_destination_commit as module
        with patch.object(module, "_replace", side_effect=OSError("before apply")):
            with self.assertRaises(OSError):
                self.commit()
        self.auto.write_text("!manual.invalid\n!example.com\n")
        with self.assertRaisesRegex(DestinationRefused, "destination_conflict_with_gui"):
            self.commit()
        self.assertIn("!example.com", self.auto.read_text())
        self.assertTrue(self.segment.exists())

    def test_writer_lock_and_queue_lock_are_both_required(self):
        with self.assertRaisesRegex(DestinationRefused, "no_locked_original_pending_intent"):
            self.writer.commit(self.proof, self.segment, self.effects)
        fd = os.open(self.lock, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(DestinationRefused, "gui_writer_busy"):
                self.commit()
        finally:
            os.close(fd)
        self.assertTrue(self.segment.exists())

    def test_untrusted_source_and_destination_refuse(self):
        self.auto.unlink()
        self.auto.symlink_to(self.youtube)
        with self.assertRaisesRegex(DestinationRefused, "unsafe_destination"):
            self.commit()
        self.auto.unlink()
        self.auto.write_text("!manual.invalid\n")
        self.auto.chmod(0o600)
        self.segment.write_text("changed.invalid\n")
        with self.assertRaisesRegex(DestinationRefused, "pending_differs_from_original_intent"):
            self.commit()

    def test_public_native_entrypoint_unconditionally_disabled(self):
        with self.assertRaisesRegex(DestinationRefused, "not_integrated"):
            run_native_destination_writer()


if __name__ == "__main__":
    unittest.main()