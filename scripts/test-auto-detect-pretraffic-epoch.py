#!/usr/bin/env python3
"""#1052 P2k8q2: physical original release seal, prelaunch zero and live epoch.

The original shared bundle seal, P2a pending and inode reads, fsynced
root-private receipts and v2 cursor readiness use real files. Only the
postlaunch running native P2c proof is injected in portable fixtures.
No native observer, cron, Config write, consumer or package activation.
"""
from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

BACKEND = Path(__file__).resolve().parents[1] / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

from auto_detect_epoch_fixture import CANDIDATE, sealed_shared_release
from auto_detect_epoch_receipts import EpochReceipts, ReceiptRefused
from auto_detect_fd import OwnerToken
from auto_detect_owner import GenerationProof
from auto_detect_queue import DurableInbox
from shared_apply_seal import create_seal


class PretrafficEpochTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="p2k8q2-")
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
        generation = "a" * 32
        proof = GenerationProof(
            OwnerToken(4432, "Sat Nov 14 09:00:00 2026", "/usr/local/sbin/dvtws2"),
            generation, generation, "b" * 64,
            str(self.queue.inbox), str(self.debug), 2,
            ((0, "unknown-native-default", None),
             (1, "known-hostlist", "youtube"), (2, "observer", None)))
        self.work, self.proof = sealed_shared_release(self.base, proof)
        self.receipts = EpochReceipts(self.base / "epochs", owner_uid=os.geteuid())
        self.folder = self.receipts.root / generation

    def seal(self, *, digest=CANDIDATE):
        with self.queue.exclusive():
            self.receipts.seal_pretraffic(self.queue, workspace=self.work,
                                          candidate_sha256=digest)

    def finish(self, *, proof=None, attest=None):
        if proof is None:
            proof = self.proof
        if attest is None:
            attest = lambda: proof
        with self.queue.exclusive():
            self.receipts.finish_running(proof, self.queue, attest=attest)

    def test_first_native_events_after_prelaunch_are_preserved_from_offset_zero(self):
        self.seal()
        self.assertTrue((self.folder / "pretraffic.json").exists())
        self.assertFalse((self.folder / "epoch.json").exists())
        with self.assertRaises(ReceiptRefused):
            self.receipts._epoch(self.proof)
        first = b"2026-11-14 : first.example.com : profile 2 : adding to native raw\n"
        self.debug.write_bytes(first)
        self.queue.inbox.write_bytes(b"first.example.com\n")
        self.finish()
        _, final = self.receipts._epoch(self.proof)
        self.assertEqual(final["committed_cursor_offset"], 0)
        self.assertEqual(final["debug_inode"], self.debug.stat().st_ino)
        self.assertEqual(final["raw_inode"], self.queue.inbox.stat().st_ino)
        self.assertEqual(final["owner_pid"], self.proof.owner.pid)
        self.assertFalse(final["ack_authorized"])
        self.assertEqual(self.debug.read_bytes(), first)
        self.assertEqual(self.queue.inbox.read_bytes(), b"first.example.com\n")

    def test_exact_repeated_seed_and_completion_are_idempotent(self):
        self.seal()
        before = (self.folder / "pretraffic.json").read_bytes()
        self.seal()
        self.assertEqual((self.folder / "pretraffic.json").read_bytes(), before)
        self.finish()
        finalized = (self.folder / "epoch.json").read_bytes()
        self.finish()
        self.assertEqual((self.folder / "epoch.json").read_bytes(), finalized)

    def test_nonempty_original_raw_never_seeds_or_truncates(self):
        self.queue.inbox.write_bytes(b"old.example.com\n")
        with self.assertRaisesRegex(ReceiptRefused, "pretraffic_original_inodes_not_empty_and_distinct"):
            self.seal()
        self.assertEqual(self.queue.inbox.read_bytes(), b"old.example.com\n")
        self.assertFalse(self.folder.exists())

    def test_nonempty_original_debug_never_seeds_or_truncates(self):
        self.debug.write_bytes(b"older-generation native positive\n")
        with self.assertRaises(ReceiptRefused):
            self.seal()
        self.assertEqual(self.debug.read_bytes(), b"older-generation native positive\n")
        self.assertFalse(self.folder.exists())

    def test_original_pending_refused_without_unlink(self):
        pending = self.root / "pending" / ("e" * 32 + "-" + "f" * 32 + ".txt")
        pending.write_bytes(b"history.example\n")
        pending.chmod(0o600)
        with self.assertRaisesRegex(ReceiptRefused, "unacknowledged_original_pending"):
            self.seal()
        self.assertEqual(pending.read_bytes(), b"history.example\n")
        self.assertFalse(self.folder.exists())

    def test_wrong_native_candidate_digest_refused(self):
        with self.assertRaises(ReceiptRefused):
            self.seal(digest="d" * 64)
        self.assertFalse(self.folder.exists())

    def test_forged_map_after_seal_fails_before_seed(self):
        path = self.work / "release" / "auto-detect-generation.json"
        mapping = json.loads(path.read_text())
        mapping["evidence"] = "P2F_OFFLINE_PLAN_ONLY"
        path.write_text(json.dumps(mapping))
        with self.assertRaises(ReceiptRefused):
            self.seal()
        self.assertFalse(self.folder.exists())

    def test_p2h_preview_cannot_replace_authorized_map(self):
        active = self.work / "release" / "auto-detect-generation.json"
        active.rename(self.work / "release" / "auto-detect-observer-preview.json")
        (self.work / "bundle-seal.json").unlink()
        create_seal(self.work, owner=os.geteuid())
        with self.assertRaises(ReceiptRefused):
            self.seal()
        self.assertFalse(self.folder.exists())

    def test_changed_sealed_native_argv_refuses(self):
        with (self.work / "release" / "dvtws.args").open("ab") as f:
            f.write(b"\n--new\n")
        with self.assertRaises(ReceiptRefused):
            self.seal()
        self.assertFalse(self.folder.exists())

    def test_changed_debug_inode_postlaunch_refuses_without_completed_epoch(self):
        self.seal()
        new = self.root / "replacement"
        new.write_bytes(b"interrupted first native packet\n")
        new.chmod(0o600)
        new.replace(self.debug)
        with self.assertRaisesRegex(ReceiptRefused, "pretraffic_inode_replaced_after_launch"):
            self.finish()
        self.assertFalse((self.folder / "epoch.json").exists())

    def test_changed_raw_inode_postlaunch_refuses(self):
        self.seal()
        replacement = self.root / "replacement"
        replacement.write_bytes(b"one native raw host\n")
        replacement.chmod(0o600)
        replacement.replace(self.queue.inbox)
        with self.assertRaisesRegex(ReceiptRefused, "pretraffic_inode_replaced_after_launch"):
            self.finish()
        self.assertFalse((self.folder / "epoch.json").exists())

    def test_changed_process_birth_refuses_before_completion(self):
        self.seal()
        other = replace(self.proof, owner=replace(
            self.proof.owner, started="Sat Nov 14 09:01:00 2026"))
        with self.assertRaisesRegex(ReceiptRefused, "original_running_queue_and_owner_required"):
            self.finish(attest=lambda: other)
        self.assertFalse((self.folder / "epoch.json").exists())

    def test_different_second_running_owner_cannot_rewrite_epoch(self):
        self.seal()
        self.finish()
        other = replace(self.proof, owner=replace(
            self.proof.owner, pid=self.proof.owner.pid + 1))
        with self.assertRaisesRegex(ReceiptRefused, "conflicting_existing_receipt"):
            self.finish(proof=other, attest=lambda: other)
        self.assertEqual(self.receipts._epoch(self.proof)[1]["owner_pid"],
                         self.proof.owner.pid)

    def test_changed_immutable_seed_blocks_finish_and_cursor(self):
        self.seal()
        path = self.folder / "pretraffic.json"
        row = json.loads(path.read_text())
        row["raw_inode"] += 1000000
        path.write_text(json.dumps(row))
        with self.assertRaisesRegex(ReceiptRefused, "pretraffic_inode_replaced_after_launch"):
            self.finish()
        self.assertFalse((self.folder / "epoch.json").exists())

    def test_no_original_queue_lock_is_never_a_pretraffic_or_epoch_permit(self):
        with self.assertRaisesRegex(ReceiptRefused, "original_fd9_pretraffic_queue"):
            self.receipts.seal_pretraffic(self.queue, workspace=self.work,
                                          candidate_sha256=CANDIDATE)
        with self.assertRaisesRegex(ReceiptRefused, "original_running_queue"):
            self.receipts.finish_running(self.proof, self.queue, attest=lambda: self.proof)
        self.assertFalse(self.folder.exists())

    def test_old_postlaunch_begin_interface_is_removed(self):
        self.assertFalse(hasattr(EpochReceipts, "begin"))
        self.assertFalse(hasattr(EpochReceipts, "stage"))
        self.assertFalse(hasattr(EpochReceipts, "historical"))

    def test_corrupt_pretraffic_receipt_blocks_completion(self):
        self.seal()
        (self.folder / "pretraffic.json").write_bytes(b"{malformed\n")
        with self.assertRaises(ReceiptRefused):
            self.finish()
        self.assertFalse((self.folder / "epoch.json").exists())

    def test_native_seed_refuses_without_real_freebsd_root_fd9(self):
        if sys.platform.startswith("freebsd"):
            self.skipTest("real FD9 lifecycle requires original OPNsense fixture")
        with self.queue.exclusive():
            with patch("auto_detect_epoch_receipts.sys.platform", "freebsd"):
                with self.assertRaisesRegex(ReceiptRefused, "original_root_fd9_required"):
                    self.receipts.seal_pretraffic(
                        self.queue, workspace=self.work, candidate_sha256=CANDIDATE)
        self.assertFalse(self.folder.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
