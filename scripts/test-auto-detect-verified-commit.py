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
from auto_detect_verified_owned_commit import (VerifiedOwnedRefused, commit_verified_owned_relocation,
                                               commit_with_locked_original_model,
                                               run_native_verified_owned_worker)
from auto_detect_owned_sources import bootstrap_empty, read_owned
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


    def setup_owned_relocation(self):
        self.owned_root = self.base / "auto-detect-owned"
        bootstrap_empty(self.owned_root, original_config_sha256="b" * 64,
                        owner_uid=os.geteuid(), authorized_clean_start=True)
        self.owned_youtube = self.owned_root / "youtube.txt"
        self.owned_user = self.owned_root / "user.txt"
        self.owned_youtube.write_text("example.co.uk\n")
        self.writer = DestinationCommit(self.receipts, self.queue,
            {"auto": self.auto, "youtube": self.owned_youtube,
             "user": self.owned_user}, self.lock)

    def owned_snapshot(self):
        return ({"auto": self.auto.read_text(), "youtube": self.youtube, "user": ""},
                read_owned(self.owned_root, owner_uid=os.geteuid()),
                self.global_exclude)

    def run_owned(self, snapshot=None):
        with self.queue.exclusive():
            return commit_verified_owned_relocation(
                self.writer, self.segment, owned_root=self.owned_root,
                snapshot=snapshot or self.owned_snapshot,
                attest=lambda: self.proof, inspect=lambda *a, **k: self.fd_state)

    def test_owned_relocation_moves_only_private_source_and_preserves_gui_deletion(self):
        self.setup_owned_relocation()
        previous_manual = self.youtube
        done = self.run_owned()
        self.assertFalse(done["ack_authorized"])
        self.assertEqual(self.auto.read_text(), "!untouched.example\nexample.co.uk\n")
        self.assertEqual(self.owned_youtube.read_text(), "")
        self.assertEqual(self.youtube, previous_manual)
        self.assertTrue(self.segment.exists())
        self.assertEqual(self.run_owned(), done)
        self.auto.write_text("!untouched.example\n")
        self.assertEqual(self.run_owned(), done)
        self.assertEqual(self.auto.read_text(), "!untouched.example\n")

    def _owned_relocation_crash(self, checkpoint_crash):
        import auto_detect_destination_commit as module
        self.setup_owned_relocation()
        orig_replace, orig_write = module._replace, module._write_once
        def replace(path, *args):
            if not checkpoint_crash and path == self.owned_youtube:
                raise OSError("injected second-target failure")
            return orig_replace(path, *args)
        def write(folder, name, data, uid):
            if checkpoint_crash and name == "checkpoint.json":
                raise OSError("injected checkpoint failure")
            return orig_write(folder, name, data, uid)
        with patch.object(module, "_replace", side_effect=replace), \
             patch.object(module, "_write_once", side_effect=write):
            with self.assertRaisesRegex(VerifiedOwnedRefused, "original_owner_policy"):
                self.run_owned()
        self.assertEqual(self.auto.read_text(), "!untouched.example\nexample.co.uk\n")
        self.assertFalse(self.checkpoint().exists())
        self.assertTrue(self.segment.exists())
        result = self.run_owned()
        self.assertFalse(result["ack_authorized"])
        self.assertEqual(self.owned_youtube.read_text(), "")
        self.assertEqual(self.auto.read_text().count("example.co.uk"), 1)

    def test_owned_relocation_crash_after_first_write(self):
        self._owned_relocation_crash(False)

    def test_owned_relocation_crash_before_checkpoint(self):
        self._owned_relocation_crash(True)

    def test_owned_relocation_stale_owned_and_config_or_gui_lock_refuse(self):
        self.setup_owned_relocation()
        def stale():
            return (self.owned_snapshot()[0], {"youtube": "", "user": ""}, "")
        with self.assertRaisesRegex(VerifiedOwnedRefused, "stale_original_config"):
            self.run_owned(stale)
        self.owned_user.write_text("UPPER.example\n")
        with self.assertRaisesRegex(VerifiedOwnedRefused, "original_owner_policy"):
            self.run_owned()
        self.owned_user.write_text("")
        fd = os.open(self.lock, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(DestinationRefused):
                self.run_owned()
        finally:
            os.close(fd)
        self.assertEqual(self.owned_youtube.read_text(), "example.co.uk\n")

    def test_owned_relocation_exclusion_and_native_cli_remain_closed(self):
        self.setup_owned_relocation()
        with self.assertRaisesRegex(VerifiedOwnedRefused, "not_authorized"):
            run_native_verified_owned_worker()
        self.global_exclude = "example.co.uk\n"
        self.assertFalse(self.run_owned()["ack_authorized"])
        self.assertEqual(self.owned_youtube.read_text(), "example.co.uk\n")
        self.assertEqual(self.auto.read_text(), "!untouched.example\n")


    def run_locked_original_model(self, manual=None, excluded=None):
        with self.queue.exclusive():
            return commit_with_locked_original_model(
                self.writer, self.segment, owned_root=self.owned_root,
                manual_hostlists=(
                    {'youtube': self.youtube, 'user': ''}
                    if manual is None else manual
                ),
                global_exclude=(
                    self.global_exclude if excluded is None else excluded
                ),
                attest=lambda: self.proof,
                inspect=lambda *a, **k: self.fd_state)

    def test_original_model_locked_adapter_reuses_real_p2k8d_destination(self):
        self.setup_owned_relocation()
        receipt = self.run_locked_original_model()
        self.assertFalse(receipt['ack_authorized'])
        self.assertEqual(self.auto.read_text(), '!untouched.example\nexample.co.uk\n')
        self.assertEqual(self.owned_youtube.read_text(), '')
        self.assertTrue(self.segment.exists())
        self.assertEqual(self.run_locked_original_model(), receipt)
        self.assertEqual(self.auto.read_text().count('example.co.uk\n'), 1)

    def test_original_model_locked_adapter_preserves_exclusion_and_manual(self):
        self.setup_owned_relocation()
        before = self.youtube
        result = self.run_locked_original_model(
            manual={'youtube': '!example.co.uk\n', 'user': ''})
        self.assertFalse(result['ack_authorized'])
        self.assertEqual(self.auto.read_text(), '!untouched.example\n')
        self.assertEqual(self.owned_youtube.read_text(), 'example.co.uk\n')
        self.assertEqual(self.youtube, before)
        self.assertTrue(self.segment.exists())

    def test_original_model_locked_adapter_rejects_incomplete_snapshot(self):
        self.setup_owned_relocation()
        with self.queue.exclusive():
            with self.assertRaisesRegex(VerifiedOwnedRefused, 'original_locked_model_required'):
                commit_with_locked_original_model(
                    self.writer, self.segment, owned_root=self.owned_root,
                    manual_hostlists={'youtube': 'youtube.com\n'},
                    global_exclude='', attest=lambda: self.proof,
                    inspect=lambda *a, **k: self.fd_state)
        self.assertTrue(self.segment.exists())
        self.assertFalse(self.checkpoint().exists())


if __name__ == "__main__":
    unittest.main()