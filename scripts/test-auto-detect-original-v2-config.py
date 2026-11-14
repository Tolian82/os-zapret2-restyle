#!/usr/bin/env python3
"""#1052 P2k8p: physical original v2 Config-held P1/destination/ACK contract.

The exact original PHP Config/inherited-FD lock boundary is separately
verified by the existing real PHP/queue-process fixture. Here only the P2c
running-engine witness and P2b FreeBSD writer-FD result are test-injected;
P2a physical queue, P2k1 native debug, P2k2a epoch, P2k8n v2 files,
P1 PublicSuffixList policy, GUI destination lock and P2k2b CAS are REAL.
"""
from __future__ import annotations

from dataclasses import replace
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

from auto_detect_cursor_chain import CursorChain
from auto_detect_destination_commit import DestinationCommit
from auto_detect_epoch_fixture import sealed_original_epoch
from auto_detect_epoch_receipts import EpochReceipts
from auto_detect_fd import FDState, OwnerToken
from auto_detect_original_lock_handoff import (
    _original_v2_cycle_locked, OriginalLockRefused, run_native_original_v2_cycle_once)
from auto_detect_original_v2_model import (
    V2OriginalConfigRefused, commit_with_original_v2_model)
from auto_detect_original_v2_prepare import prepare_original_v2_locked
from auto_detect_owner import GenerationProof
from auto_detect_owned_sources import bootstrap_empty
from auto_detect_queue import DurableInbox
from domain_policy import PublicSuffixList

PSL_SOURCE = (b"// ===BEGIN ICANN DOMAINS===\ncom\nuk\nco.uk\n"
              b"// ===END ICANN DOMAINS===\n"
              b"// ===BEGIN PRIVATE DOMAINS===\nblogspot.com\n"
              b"// ===END PRIVATE DOMAINS===\n")


class OriginalConfigV2Tests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="p2k8p-")
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.base.chmod(0o700)
        root = self.base / "producer"
        root.mkdir(mode=0o700)
        (root / "pending").mkdir(mode=0o700)
        self.queue = DurableInbox(root, owner_uid=os.geteuid())
        self.queue.inbox.write_bytes(b"")
        self.queue.inbox.chmod(0o600)
        self.debug = root / "debug.log"
        self.debug.write_bytes(b"")
        self.debug.chmod(0o600)
        gen = "a" * 32
        self.proof = GenerationProof(
            OwnerToken(4321, "Fri Nov 13 10:00:00 2026", "/usr/local/sbin/dvtws2"),
            gen, gen, "b" * 64,
            str(self.queue.inbox), str(self.debug), 2,
            ((0, "unknown-native-default", None),
             (1, "known-hostlist", "youtube"), (2, "observer", None)))
        self.receipts = EpochReceipts(self.base / "epochs", owner_uid=os.geteuid())
        self.proof = sealed_original_epoch(self.base, self.proof, self.queue, self.receipts)
        self.chain = CursorChain(self.receipts, self.queue)
        self.lists = self.base / "lists"
        self.lists.mkdir(mode=0o700)
        self.auto = self.lists / "auto-domains.txt"
        self.auto.write_text("!untouched.example\n")
        self.auto.chmod(0o600)
        self.owned = self.base / "owned"
        bootstrap_empty(self.owned, original_config_sha256="b" * 64,
                        authorized_clean_start=True, owner_uid=os.geteuid())
        self.youtube = self.owned / "youtube.txt"
        self.user = self.owned / "user.txt"
        self.writer = DestinationCommit(
            self.receipts, self.queue,
            {"auto": self.auto, "youtube": self.youtube, "user": self.user},
            self.lists / ".gui.lock")
        self.psl = PublicSuffixList(PSL_SOURCE, hashlib.sha256(PSL_SOURCE).hexdigest())
        self.manual = {"youtube": "youtube.com\n", "user": ""}
        self.excluded = ""
        self.fd_state = FDState.DRAINED
        self.drains = 0

    def attest(self):
        return self.proof

    def inspect(self, pending, dev, inode, *, owner, writer_gid):
        self.drains += 1
        self.assertEqual((pending.stat().st_dev, pending.stat().st_ino),
                         (dev, inode))
        self.assertEqual(owner, self.proof.owner)
        return self.fd_state

    def emit(self, hostname):
        self.queue.inbox.write_text(hostname + "\n")
        with self.debug.open("a", encoding="ascii") as out:
            out.write(f"2026-11-14 11:10:00 : {hostname} : profile 2 (tail) : "
                      f"client 127.0.0.1:1234 : proto http : adding to {self.queue.inbox}\n")

    def prepare(self):
        return prepare_original_v2_locked(
            self.queue, self.receipts, attest=self.attest, inspect=self.inspect)

    def commit(self, pending, *, manual=None, excluded=None, attest=None):
        return commit_with_original_v2_model(
            self.writer, pending, owned_root=self.owned,
            manual_hostlists=self.manual if manual is None else manual,
            global_exclude=self.excluded if excluded is None else excluded,
            attest=self.attest if attest is None else attest,
            inspect=self.inspect, psl=self.psl)

    def ack(self, pending, result):
        return self.chain.acknowledge(
            self.proof, pending, result, self.writer,
            attest=self.attest, inspect=self.inspect)

    def test_two_real_v2_minutes_with_original_p1_and_ack(self):
        for host in ("video.example.co.uk", "cdn.second.com"):
            self.emit(host)
            with self.queue.exclusive():
                pending = self.prepare()
                result = self.commit(pending)
                self.assertFalse(result["ack_authorized"])
                self.assertTrue(self.ack(pending, result))
        self.assertEqual(self.chain_count(), 2)
        self.assertEqual(self.auto.read_text(),
                         "!untouched.example\nexample.co.uk\nsecond.com\n")
        self.assertEqual(self.youtube.read_text(), "")

    def chain_count(self):
        with self.queue.exclusive():
            return self.chain.tip(self.proof).next_sequence

    def test_replay_does_not_restore_manual_gui_deletion(self):
        self.emit("video.example.co.uk")
        with self.queue.exclusive():
            pending = self.prepare()
            checkpoint = self.commit(pending)
            self.auto.write_text("!untouched.example\n")
            self.assertEqual(self.commit(pending), checkpoint)
            self.assertEqual(self.auto.read_text(), "!untouched.example\n")
            self.assertTrue(self.ack(pending, checkpoint))

    def test_sealed_owned_known_is_relocated_not_manual(self):
        self.youtube.write_text("example.co.uk\n")
        self.emit("video.example.co.uk")
        with self.queue.exclusive():
            pending = self.prepare()
            self.commit(pending)
            self.assertEqual(self.youtube.read_text(), "")
            self.assertEqual(self.auto.read_text(),
                             "!untouched.example\nexample.co.uk\n")
        self.assertEqual(self.manual["youtube"], "youtube.com\n")

    def test_global_exclusion_prevents_any_positive(self):
        self.excluded = "example.co.uk\n"
        self.emit("video.example.co.uk")
        with self.queue.exclusive():
            pending = self.prepare()
            checkpoint = self.commit(pending)
            self.assertEqual(self.auto.read_text(), "!untouched.example\n")
            self.assertEqual(checkpoint["kind"], "destination-and-cursor-committed")
            self.assertTrue(self.ack(pending, checkpoint))

    def test_excluded_domain_in_other_manual_hostlist_blocks(self):
        self.manual["youtube"] = "!example.co.uk\n"
        self.emit("video.example.co.uk")
        with self.queue.exclusive():
            pending = self.prepare()
            self.commit(pending)
        self.assertEqual(self.auto.read_text(), "!untouched.example\n")

    def test_busy_original_fd_refuses_without_checkpoint(self):
        self.emit("video.example.co.uk")
        with self.queue.exclusive():
            pending = self.prepare()
            self.fd_state = FDState.BUSY
            with self.assertRaisesRegex(V2OriginalConfigRefused, "writer_not_drained"):
                self.commit(pending)
            self.assertTrue(pending.exists())
            self.assertFalse((self.chain.tip(self.proof).open_folder /
                              "destination" / "checkpoint.json").exists())

    def test_changed_owner_before_p1_refuses(self):
        self.emit("video.example.co.uk")
        with self.queue.exclusive():
            pending = self.prepare()
            forged = replace(self.proof, generation="f" * 32)
            with self.assertRaises(V2OriginalConfigRefused):
                self.commit(pending, attest=lambda: forged)
            self.assertTrue(pending.exists())

    def test_wrong_original_model_and_owned_sources_refuse(self):
        self.emit("video.example.co.uk")
        with self.queue.exclusive():
            pending = self.prepare()
            with self.assertRaisesRegex(V2OriginalConfigRefused, "original_config_model"):
                self.commit(pending, manual={"youtube": "youtube.com\n"})
            self.owned.joinpath("manifest.json").unlink()
            with self.assertRaises(V2OriginalConfigRefused):
                self.commit(pending)
            self.assertTrue(pending.exists())

    def test_later_native_debug_tail_is_not_reclassified(self):
        self.emit("video.example.co.uk")
        with self.queue.exclusive():
            first = self.prepare()
            # New engine events are written into newly rotated live inbox.
            self.emit("cdn.second.com")
            self.commit(first)
            self.assertEqual(self.auto.read_text(),
                             "!untouched.example\nexample.co.uk\n")
            self.assertTrue(self.ack(first, self.chain_checkpoint(0)))
            second = self.prepare()
            self.assertTrue(self.ack(second, self.commit(second)))

    def chain_checkpoint(self, step):
        import json
        path = (self.base / "epochs" / self.proof.generation / "cursor-chain-v2" /
                f"{step:08d}" / "destination" / "checkpoint.json")
        return json.loads(path.read_text())

    def test_modified_debug_prefix_keeps_original_pending(self):
        self.emit("video.example.co.uk")
        with self.queue.exclusive():
            pending = self.prepare()
            self.debug.write_text("changed event bytes\n")
            with self.assertRaises(V2OriginalConfigRefused):
                self.commit(pending)
            self.assertTrue(pending.exists())

    def test_partial_destination_recovery_after_first_replace(self):
        self.youtube.write_text("example.co.uk\n")
        self.emit("video.example.co.uk")
        import auto_detect_destination_commit as mod
        normal = mod._replace
        def failing(path, *args):
            if path == self.youtube:
                raise OSError("inject second target failure")
            return normal(path, *args)
        with self.queue.exclusive():
            pending = self.prepare()
            with patch.object(mod, "_replace", side_effect=failing):
                with self.assertRaises(V2OriginalConfigRefused):
                    self.commit(pending)
            self.assertEqual(self.auto.read_text(), "!untouched.example\nexample.co.uk\n")
            self.assertEqual(self.youtube.read_text(), "example.co.uk\n")
            cp = self.commit(pending)
            self.assertTrue(self.ack(pending, cp))
        self.assertEqual(self.youtube.read_text(), "")

    def test_gui_destination_lock_contention_denied(self):
        self.emit("video.example.co.uk")
        with self.queue.exclusive():
            pending = self.prepare()
            fd = os.open(self.writer.gui_lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaises(V2OriginalConfigRefused):
                    self.commit(pending)
                self.assertTrue(pending.exists())
            finally:
                os.close(fd)

    def test_original_parent_holds_one_queue_lock_through_child(self):
        self.emit("video.example.co.uk")
        import auto_detect_original_lock_handoff as lock
        def child(queue, pending, **kwargs):
            self.assertTrue(queue._held)
            return self.commit(pending)
        with self.queue.exclusive():
            with patch.object(lock, "_original_completion_locked", side_effect=child):
                self.assertTrue(_original_v2_cycle_locked(
                    self.queue, self.writer, php_bin="php",
                    php_script=Path("/fake/native.php"), timeout=5,
                    attest=self.attest, inspect=self.inspect))
        self.assertEqual(self.chain_count(), 1)

    def test_native_cli_and_no_unlocked_config_writer(self):
        with self.assertRaisesRegex(V2OriginalConfigRefused, "original_config_model"):
            self.commit(self.queue.pending / "missing.txt")
        with self.assertRaises(OriginalLockRefused):
            run_native_original_v2_cycle_once()


if __name__ == "__main__":
    unittest.main()
