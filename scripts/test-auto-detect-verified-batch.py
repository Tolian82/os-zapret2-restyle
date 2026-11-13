#!/usr/bin/env python3
"""#1052 P2k3: original pending, native FD/debug, canonical P1 preview."""
from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
import sys
import tempfile
import unittest

BACKEND = Path(__file__).resolve().parents[1] / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

from auto_detect_debug_window import empty_epoch, propose_window
from auto_detect_epoch_receipts import EpochReceipts
from auto_detect_fd import FDState, OwnerToken
from auto_detect_owner import GenerationProof
from auto_detect_queue import DurableInbox
from auto_detect_verified_batch import BatchRefused, prepare_verified_batch, run_native_verified_batch_worker


class VerifiedBatchTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="p2k3-")
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
        host = "video.example.co.uk"
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
        self.hostlists = {"auto": "", "youtube": "youtube.com\n", "user": ""}
        self.automatic = {"auto": "", "youtube": "", "user": ""}
        self.inspections = []

    def inspect(self, path, device, inode, *, owner, writer_gid):
        self.inspections.append((path, device, inode, owner, writer_gid))
        return FDState.DRAINED

    def preview(self, *, attest=None, inspect=None, hostlists=None, automatic=None,
                global_exclude=""):
        with self.queue.exclusive():
            return prepare_verified_batch(
                self.queue, self.receipts, self.segment,
                hostlists if hostlists is not None else self.hostlists,
                automatic if automatic is not None else self.automatic,
                global_exclude, attest=attest or (lambda: self.proof),
                inspect=inspect or self.inspect)

    def test_real_p1_psl_unknown_observer_falls_back_without_writes(self):
        result = self.preview()
        self.assertEqual(result.generation, self.proof.generation)
        self.assertEqual(result.policy["additions"], {"auto": ["example.co.uk"]})
        self.assertEqual(result.policy["routes"][0]["destination"], "auto")
        self.assertFalse(result.ack_authorized)
        self.assertEqual(len(self.inspections), 1)
        self.assertEqual(self.inspections[0][0], self.segment)
        self.assertEqual(self.inspections[0][3], self.proof.owner)
        self.assertTrue(self.segment.exists())
        self.assertEqual(self.receipts.historical(self.proof.generation).epoch["committed_cursor_offset"], 0)
        self.assertFalse((self.base/"epochs"/self.proof.generation/"destination").exists())

    def test_other_hostlist_negative_and_global_exclusion_block_auto_add(self):
        h = {**self.hostlists, "youtube": "!example.co.uk\n"}
        a = self.preview(hostlists=h)
        self.assertEqual(a.policy["additions"], {})
        self.assertEqual(a.policy["excluded"][0]["code"], "hostlist_exclusion")
        b = self.preview(global_exclude="example.co.uk\n")
        self.assertEqual(b.policy["additions"], {})
        self.assertEqual(b.policy["excluded"][0]["code"], "global_exclusion")

    def test_busy_unknown_fd_and_changed_owner_preserve_pending(self):
        for status in (FDState.BUSY, FDState.UNKNOWN):
            with self.assertRaisesRegex(BatchRefused, "original_native_writer_fd_not_drained"):
                self.preview(inspect=lambda *a, **k: status)
        count = 0
        def changed_owner():
            nonlocal count
            count += 1
            return self.proof if count == 1 else replace(self.proof, final_args_sha256="c" * 64)
        with self.assertRaisesRegex(BatchRefused, "original_common_generation_changed"):
            self.preview(attest=changed_owner)
        self.assertTrue(self.segment.exists())

    def test_other_generation_missing_lock_and_corrupt_source_refuse(self):
        with self.assertRaisesRegex(BatchRefused, "original_queue_lock"):
            prepare_verified_batch(self.queue, self.receipts, self.segment,
                                   self.hostlists, self.automatic,
                                   attest=lambda: self.proof, inspect=self.inspect)
        with self.assertRaises(BatchRefused):
            self.preview(attest=lambda: replace(self.proof, final_args_sha256="c" * 64))
        self.segment.write_text("modified.example.com\n")
        with self.assertRaisesRegex(BatchRefused, "original_pending_inode_or_hash_changed"):
            self.preview()
        self.assertTrue(self.segment.exists())

    def test_native_debug_changed_or_unprocessed_policy_refuses(self):
        self.debug.write_bytes(self.debug.read_bytes() + b"X")
        with self.assertRaisesRegex(BatchRefused, "original_pending_policy_evidence_unavailable"):
            self.preview()
        self.assertTrue(self.segment.exists())

    def test_auto_owned_relocation_is_not_silently_committed(self):
        owned = {**self.automatic, "youtube": "example.co.uk\n"}
        with self.assertRaisesRegex(BatchRefused, "unimplemented_owned_relocation"):
            self.preview(automatic=owned)
        self.assertTrue(self.segment.exists())

    def test_public_native_entrypoint_remains_disabled(self):
        with self.assertRaisesRegex(BatchRefused, "not_connected"):
            run_native_verified_batch_worker()


if __name__ == "__main__":
    unittest.main()