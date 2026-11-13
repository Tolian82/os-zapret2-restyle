#!/usr/bin/env python3
"""#1052 P2k4: real P2k3→P2k2b file transaction, lock/CAS/replay and no-op."""
from __future__ import annotations

import fcntl
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
from auto_detect_fd import FDState, OwnerToken
from auto_detect_owner import GenerationProof
from auto_detect_queue import DurableInbox
from auto_detect_destination_commit import DestinationCommit, DestinationRefused
from auto_detect_verified_commit import (commit_verified_fallback,
                                         VerifiedCommitRefused,
                                         run_native_verified_commit_worker)


class GenuineSourceToDestinationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="p2k4-")
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
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
        gen = "a" * 32
        self.proof = GenerationProof(
            OwnerToken(4321, "Fri Nov 13 10:00:00 2026", "/usr/local/sbin/dvtws2"),
            gen, gen, "b" * 64, str(self.raw), str(self.debug), 2,
            ((0, "unknown-native-default", None),
             (1, "known-hostlist", "youtube"), (2, "observer", None)))
        cursor = empty_epoch(self.proof, owner_uid=os.geteuid())
        self.receipts = EpochReceipts(self.base / "epochs", owner_uid=os.geteuid())
        self.receipts.begin(self.proof, cursor)
        host = "video.example.co.uk"
        self.debug.write_text(
            f"2026-11-13 13:15:30 : {host} : profile 2 (tail) : "
            f"client 127.0.0.1:4321 : proto http : adding to {self.raw}\n",
            encoding="ascii")
        data = (host + "\n").encode()
        self.segment = self.queue.pending / (gen + "-" + "c" * 32 + ".txt")
        self.segment.write_bytes(data)
        self.segment.chmod(0o600)
        self.receipts.stage(self.proof, cursor,
                            propose_window(self.proof, cursor, data,
                                           owner_uid=os.geteuid()), self.segment)
        self.lists = self.base / "lists"
        self.lists.mkdir(mode=0o700)
        self.auto = self.lists / "auto-domains.txt"
        self.auto.write_text("!untouched.example\n", encoding="utf-8")
        self.auto.chmod(0o600)
        self.lock = self.lists / ".writer.lock"
        self.writer = DestinationCommit(self.receipts, self.queue,
                                        {"auto": self.auto}, self.lock)
        self.youtube = "youtube.com\n"
        self.global_exclude = ""
        self.fd_state = FDState.DRAINED

    def snapshot(self):
        return ({"auto": self.auto.read_text(), "youtube": self.youtube,
                 "user": ""}, {"auto": "", "youtube": "", "user": ""},
                self.global_exclude)

    def run_commit(self, *, snapshot=None, inspect=None):
        with self.queue.exclusive():
            return commit_verified_fallback(
                self.writer, self.segment,
                snapshot=snapshot if snapshot is not None else self.snapshot,
                attest=lambda: self.proof,
                inspect=inspect if inspect is not None else
                (lambda *a, **k: self.fd_state))

    def checkpoint(self):
        return self.base / "epochs" / self.proof.generation / "destination" / "checkpoint.json"

    def test_real_p1_policy_then_durable_list_and_cursor_no_ack(self):
        receipt = self.run_commit()
        self.assertEqual(receipt["kind"], "destination-and-cursor-committed")
        self.assertFalse(receipt["ack_authorized"])
        self.assertEqual(self.auto.read_text(), "!untouched.example\nexample.co.uk\n")
        self.assertTrue(self.checkpoint().exists())
        self.assertTrue(self.segment.exists())
        self.assertEqual(self.receipts.historical(self.proof.generation).epoch["committed_cursor_offset"], 0)
        self.assertEqual(self.run_commit(), receipt)
        self.assertEqual(self.auto.read_text().count("example.co.uk"), 1)

    def test_gui_deletion_after_checkpoint_remains_respected_on_retry(self):
        done = self.run_commit()
        self.auto.write_text("!untouched.example\n", encoding="utf-8")
        self.assertEqual(self.run_commit(), done)
        self.assertEqual(self.auto.read_text(), "!untouched.example\n")

    def test_noop_all_excluded_has_real_cursor_checkpoint_without_write(self):
        self.global_exclude = "example.co.uk\n"
        original = self.auto.read_bytes()
        recorded = self.auto.stat().st_ino
        done = self.run_commit()
        self.assertTrue(self.checkpoint().exists())
        self.assertFalse(done["ack_authorized"])
        self.assertEqual(self.auto.read_bytes(), original)
        self.assertEqual(self.auto.stat().st_ino, recorded)
        self.assertTrue(self.segment.exists())
        self.assertEqual(self.run_commit(), done)

    def test_failure_after_file_replace_replays_before_ack(self):
        import auto_detect_destination_commit as module
        real = module._write_once
        def crash(folder, name, data, uid):
            if name == "checkpoint.json":
                raise OSError("injected crash after complete file change")
            return real(folder, name, data, uid)
        with patch.object(module, "_write_once", side_effect=crash):
            with self.assertRaisesRegex(VerifiedCommitRefused, "original_owner_policy_or_destination_refused"):
                self.run_commit()
        self.assertIn("example.co.uk\n", self.auto.read_text())
        self.assertFalse(self.checkpoint().exists())
        self.assertTrue(self.segment.exists())
        recorded = self.auto.stat().st_ino
        done = self.run_commit()
        self.assertEqual(self.auto.stat().st_ino, recorded)
        self.assertTrue(self.checkpoint().exists())
        self.assertFalse(done["ack_authorized"])

    def test_gui_race_and_fd_refusal_preserve_all_pending(self):
        fd = os.open(self.lock, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(DestinationRefused, "gui_writer_busy"):
                self.run_commit()
        finally:
            os.close(fd)
        self.fd_state = FDState.UNKNOWN
        with self.assertRaisesRegex(VerifiedCommitRefused, "original_owner_policy_or_destination_refused"):
            self.run_commit()
        self.assertFalse(self.checkpoint().exists())
        self.assertTrue(self.segment.exists())

    def test_stale_gui_snapshot_and_global_negative_prevent_positive(self):
        def stale():
            return ({"auto": "", "youtube": "", "user": ""},
                    {"auto": "", "youtube": "", "user": ""}, "")
        with self.assertRaisesRegex(VerifiedCommitRefused, "shared_hostlist_snapshot_not_current"):
            self.run_commit(snapshot=stale)
        self.youtube = "!example.co.uk\n"
        self.run_commit()
        self.assertEqual(self.auto.read_text(), "!untouched.example\n")
        self.assertTrue(self.segment.exists())

    def test_source_cannot_be_acked_and_native_cli_is_disabled(self):
        with self.assertRaisesRegex(VerifiedCommitRefused, "not_authorized"):
            run_native_verified_commit_worker()
        self.run_commit()
        self.assertTrue(self.segment.exists())


if __name__ == "__main__":
    unittest.main()