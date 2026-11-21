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


if __name__ == "__main__":
    unittest.main()
