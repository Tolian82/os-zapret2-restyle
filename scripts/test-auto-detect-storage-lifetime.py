#!/usr/bin/env python3
"""#1052 original FD9 storage lifetime; no native engine action."""
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

BACKEND = (Path(__file__).resolve().parents[1] /
           "src/opnsense/scripts/OPNsense/Zapret/backend")
sys.path.insert(0, str(BACKEND))
from auto_detect_cursor_chain import ChainTip
from auto_detect_debug_window import Cursor
from auto_detect_epoch_receipts import (EpochReceipts, EMPTY_HASH, _canonical,
                                         _proof_fields, ReceiptRefused)
from auto_detect_fd import FDState, OwnerToken
from auto_detect_original_v2_prepare import _debug_cut_once
import auto_detect_original_v2_prepare as prep
from auto_detect_owner import GenerationProof
from auto_detect_queue import DurableInbox


class LifetimeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="autodetect-lifetime-")
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.base.chmod(0o700)
        root = self.base / "producer"
        root.mkdir(mode=0o700)
        (root / "pending").mkdir(mode=0o700)
        self.inbox = root / "inbox.txt"
        self.inbox.write_bytes(b"")
        self.inbox.chmod(0o600)
        self.debug = root / "debug.log"
        self.debug.write_bytes(b"")
        self.debug.chmod(0o600)
        self.queue = DurableInbox(root, owner_uid=os.geteuid())
        self.receipts = EpochReceipts(self.base / "epochs",
                                      owner_uid=os.geteuid())
        self.receipts.root.mkdir(mode=0o700)

    def proof(self, number: int):
        gen = f"{number:032x}"
        return GenerationProof(
            OwnerToken(1300 + number, "Fri Nov 13 10:00:00 2026",
                       "/usr/local/sbin/dvtws2"),
            gen, gen, "b" * 64, str(self.inbox), str(self.debug), 2,
            ((2, "observer", None),))

    def test_no_restart_debug_only_fourteen_consecutive_cuts(self):
        proof = self.proof(1)
        cursor = Cursor(proof.generation, self.debug.stat().st_dev,
                        self.debug.stat().st_ino, 0, EMPTY_HASH)
        tip = ChainTip(0, cursor, "c" * 64, None, None, frozenset(), False)
        with patch.object(prep, "DEBUG_HIGH_WATERMARK", 64):
            with self.queue.exclusive():
                for i in range(14):
                    with self.debug.open("ab") as log:
                        log.write((f"{i} ".encode() + b"x" * 90 + b"\n"))
                    self.assertTrue(_debug_cut_once(
                        self.queue, self.receipts, proof, cursor, False,
                        lambda: proof,
                        lambda *args, **kw: FDState.DRAINED,
                        retirement_tip=tip))
                    archived = self.debug.parent / prep.DEBUG_OLD
                    self.assertEqual(archived.stat().st_nlink, 1)
                    self.assertEqual(self.debug.read_bytes(), b"")
                    self.assertEqual(self.inbox.read_bytes(), b"")
                    self.assertEqual(self.queue.segments(), [])
                    self.assertFalse(
                        (self.debug.parent / prep.DEBUG_NEXT).exists())

    def test_real_two_mebibyte_no_raw_debug_cut_without_restart(self):
        proof = self.proof(1)
        cursor = Cursor(proof.generation, self.debug.stat().st_dev,
                        self.debug.stat().st_ino, 0, EMPTY_HASH)
        tip = ChainTip(0, cursor, "c" * 64, None, None, frozenset(), False)
        line = b"2026-11-15 10:00:00 : failure counter 1/3\\n".replace(
            b"\\n", b"\n")
        data = line * ((2 * 1024 * 1024 // len(line)) + 2)
        self.assertGreater(len(data), 2 * 1024 * 1024)
        self.assertLess(len(data), 4 * 1024 * 1024)
        with self.queue.exclusive():
            for i in range(3):
                with self.debug.open("ab") as stream:
                    stream.write(data)
                self.assertTrue(_debug_cut_once(
                    self.queue, self.receipts, proof, cursor, False,
                    lambda: proof,
                    lambda *args, **kwargs: FDState.DRAINED,
                    retirement_tip=tip))
                self.assertEqual(self.debug.read_bytes(), b"")
                self.assertEqual(self.inbox.read_bytes(), b"")
                self.assertEqual(self.queue.segments(), [])
                self.assertEqual(
                    (self.debug.parent / prep.DEBUG_OLD).stat().st_size,
                    len(data))
        # Real diagnostic-only file above the P2k1 256-KiB window now
        # rotates safely without inventing an ACK or restarting dvtws2.

    def seed_completed(self, number: int):
        proof = self.proof(number)
        folder = self.receipts.root / proof.generation
        folder.mkdir(mode=0o700)
        n = 7500 + number
        seed = {
            "schema": 2, "kind": "original-fd9-pretraffic-zero",
            "generation": proof.generation,
            "owner_candidate_sha256": "c" * 64,
            "release_seal_sha256": "d" * 64,
            "final_args_sha256": "b" * 64,
            "raw_path": proof.raw_path, "debug_path": proof.debug_path,
            "raw_device": n, "raw_inode": n + 20,
            "debug_device": n, "debug_inode": n + 30,
            "observer_native_number": 2, "profiles": [[2, "observer", None]],
            "ack_authorized": False,
        }
        seed_raw = _canonical(seed)
        (folder / "pretraffic.json").write_bytes(seed_raw)
        (folder / "pretraffic.json").chmod(0o600)
        encoded = _canonical({
            **_proof_fields(proof),
            "owner_candidate_sha256": "c" * 64,
            "pretraffic_sha256": hashlib.sha256(seed_raw).hexdigest(),
            "raw_device": n, "raw_inode": n + 20,
            "debug_device": n, "debug_inode": n + 30,
            "committed_cursor_offset": 0,
            "committed_cursor_sha256": EMPTY_HASH,
        })
        (folder / "epoch.json").write_bytes(encoded)
        (folder / "epoch.json").chmod(0o600)
        sources = {}
        for key, name in (("inbox", "retired-inbox.txt"),
                          ("debug", "retired-debug.log")):
            target = folder / name
            target.write_bytes(b"")
            target.chmod(0o600)
            info = target.stat()
            sources[key] = [info.st_dev, info.st_ino, 0, EMPTY_HASH]
        sources["previous"] = None
        plan = {
            "schema": 1, "kind": "original-stopped-source-retirement",
            "generation": proof.generation,
            "owner_sha256": hashlib.sha256(
                _canonical(_proof_fields(proof))).hexdigest(),
            "last_ack_sha256": hashlib.sha256(encoded).hexdigest(),
            "cycle": 0, "next_sequence": 0,
            "sources": sources,
        }
        (folder / "retired.json").write_bytes(_canonical(plan))
        (folder / "retired.json").chmod(0o600)

    def test_keep_four_completed_only_and_crash_tombstone(self):
        for i in range(1, 8):
            self.seed_completed(i)
        protected = "f" * 32
        with self.queue.exclusive():
            self.assertEqual(self.receipts.prune_completed(
                self.queue, protect=protected), 3)
            self.assertEqual(self.receipts.prune_completed(
                self.queue, protect=protected), 0)
        expected = [f"{n:032x}" for n in range(4, 8)]
        self.assertEqual(sorted(p.name for p in self.receipts.root.iterdir()),
                         expected)
        self.assertEqual(self.inbox.read_bytes(), b"")
        # Interrupted tombstone deletion resumes under the next exact FD9.
        tomb = self.receipts.root / (".gc-" + f"{4:032x}")
        (self.receipts.root / f"{4:032x}").rename(tomb)
        (tomb / "pretraffic.json").unlink()
        with self.queue.exclusive():
            self.assertEqual(self.receipts.prune_completed(
                self.queue, protect=protected), 0)
        self.assertFalse(tomb.exists())

    def test_tampered_completed_ack_never_deleted(self):
        for i in range(1, 7):
            self.seed_completed(i)
        target = self.receipts.root / f"{1:032x}" / "retired.json"
        altered = target.read_bytes().replace(
            b'"last_ack_sha256":"', b'"last_ack_sha256":"0')
        target.write_bytes(altered)
        with self.queue.exclusive():
            with self.assertRaises(ReceiptRefused):
                self.receipts.prune_completed(
                    self.queue, protect="f" * 32)
        self.assertEqual(len(list(self.receipts.root.iterdir())), 6)


if __name__ == "__main__":
    unittest.main()
