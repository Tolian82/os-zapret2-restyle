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
from auto_detect_original_v2_prepare import (OriginalV2PrepareRefused,
                                             prepare_original_v2_locked)
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

    def test_real_original_config_raw_first_cross_inode_commit_and_ack(self):
        # Native debug positive for the second raw lands in the previous
        # debug inode; P2c + all-PID P2b raw are independently sufficient
        # for UNKNOWN Auto Hostlist, not YouTube/User attribution.
        self.emit("video.example.co.uk")
        with self.queue.exclusive():
            first = self.queue.rotate(generation=self.proof.generation)
            self.emit("cdn.second.com")
            old = self.debug.with_name("old-debug-for-test")
            new = self.debug.with_name(".new-debug-for-test")
            new.write_bytes(b"")
            new.chmod(0o600)
            os.link(self.debug, old)
            os.replace(new, self.debug)
            self.assertEqual(old.stat().st_nlink, 1)
            self.assertEqual(self.prepare(), first)
            intent = self.chain.tip(self.proof).open_intent
            self.assertEqual(intent["evidence"], "raw-first")
            self.assertEqual(intent["debug_end_offset"], 0)
            cp = self.commit(first)
            self.assertEqual(cp["evidence"], "raw-first")
            # Same original Config checkpoint cannot apply one raw twice.
            self.assertEqual(self.commit(first), cp)
            self.assertTrue(self.ack(first, cp))
            self.assertTrue(self.ack(first, cp))
            self.assertEqual(self.chain.tip(self.proof).next_sequence, 1)
            self.assertTrue(self.chain.tip(self.proof).raw_first)
            second = self.prepare()
            cp2 = self.commit(second)
            self.assertTrue(self.ack(second, cp2))
            # Duplicate root after debug cut remains P1-idempotent.
            self.emit("video.example.co.uk")
            third = self.prepare()
            self.assertTrue(self.ack(third, self.commit(third)))
            self.assertEqual(self.chain.tip(self.proof).next_sequence, 3)
            self.assertEqual(self.chain.tip(self.proof).cursor.offset, 0)
        self.assertEqual(self.auto.read_text(),
                         "!untouched.example\nexample.co.uk\nsecond.com\n")
        self.assertEqual(self.youtube.read_text(), "")
        self.assertEqual(old.read_bytes().count(b"adding to "), 2)

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

    def test_original_config_recovers_preplan_native_debug_as_unknown(self):
        self.emit("video.example.co.uk")
        with self.queue.exclusive():
            pending = self.prepare()
            folder = self.chain.tip(self.proof).open_folder
            original_intent = (folder / "intent.json").read_bytes()
            old_debug = self.debug.with_name("previous-original-debug")
            new_debug = self.debug.with_name(".prepared-debug")
            new_debug.write_bytes(b"")
            new_debug.chmod(0o600)
            os.link(self.debug, old_debug)
            os.replace(new_debug, self.debug)
            # Original parent re-enters P2k8o with SAME original queue lock
            # and unchanged pending: one root-private recovery receipt.
            self.assertEqual(self.prepare(), pending)
            self.assertEqual((folder / "intent.json").read_bytes(), original_intent)
            self.assertTrue((folder / "recovery.json").is_file())
            self.assertEqual(self.chain.tip(self.proof).open_intent["evidence"],
                             "raw-first")
            self.assertEqual(self.chain.tip(self.proof).cursor.offset, 0)
            # Genuine original P1/Config policy is sampled only now.
            cp = self.commit(pending)
            self.assertEqual(cp["evidence"], "raw-first")
            self.assertEqual(self.commit(pending), cp)
            self.assertTrue(self.ack(pending, cp))
            self.assertTrue(self.ack(pending, cp))
            self.assertTrue(self.chain.tip(self.proof).raw_first)
            self.assertFalse(pending.exists())
            self.assertEqual(self.auto.read_text(),
                             "!untouched.example\nexample.co.uk\n")
            self.assertEqual(self.youtube.read_text(), "")
            self.emit("cdn.second.com")
            second = self.prepare()
            self.assertTrue(self.ack(second, self.commit(second)))
            self.assertEqual(self.chain.tip(self.proof).cursor.offset, 0)
            self.assertEqual(self.chain.tip(self.proof).next_sequence, 2)
        self.assertEqual(self.auto.read_text(),
                         "!untouched.example\nexample.co.uk\nsecond.com\n")
        self.assertEqual(old_debug.read_bytes().count(b"adding to "), 1)

    def test_original_config_postcheckpoint_debug_cut_does_not_restore_gui_delete(self):
        self.emit("video.example.co.uk")
        with self.queue.exclusive():
            pending = self.prepare()
            folder = self.chain.tip(self.proof).open_folder
            checkpoint = self.commit(pending)
            self.assertEqual(checkpoint["evidence"], "native-debug")
            intent_bytes = (folder / "intent.json").read_bytes()
            original_plan = (folder / "destination" / "plan.json").read_bytes()
            original_checkpoint = (folder / "destination" / "checkpoint.json").read_bytes()
            self.assertEqual(self.auto.read_text(),
                             "!untouched.example\nexample.co.uk\n")
            historical = self.debug.with_name("previous-committed-debug")
            fresh = self.debug.with_name(".next-committed-debug")
            fresh.write_bytes(b"")
            fresh.chmod(0o600)
            os.link(self.debug, historical)
            os.replace(fresh, self.debug)
            # A user removes the committed domain between destination fsync
            # and original raw ACK. P1 must NOT reapply that old positive.
            self.auto.write_text("!untouched.example\n")
            self.chain = CursorChain(self.receipts, self.queue)
            self.assertEqual(self.prepare(), pending)
            self.assertEqual(self.commit(pending), checkpoint)
            self.assertTrue(self.ack(pending, checkpoint))
            self.assertTrue(self.ack(pending, checkpoint))
            self.assertEqual(self.auto.read_text(), "!untouched.example\n")
            self.assertEqual(self.youtube.read_text(), "")
            self.assertFalse(pending.exists())
            self.assertFalse((folder / "recovery.json").exists())
            self.assertEqual((folder / "intent.json").read_bytes(), intent_bytes)
            self.assertEqual((folder / "destination" / "plan.json").read_bytes(),
                             original_plan)
            self.assertEqual((folder / "destination" / "checkpoint.json").read_bytes(),
                             original_checkpoint)
            self.assertEqual(self.chain.tip(self.proof).next_sequence, 1)
            self.assertGreater(self.chain.tip(self.proof).cursor.offset, 0)
            self.assertEqual(historical.read_bytes().count(b"adding to "), 1)

    def test_original_config_partial_plan_debug_cut_refuses_and_preserves_gui_edit(self):
        self.youtube.write_text("example.co.uk\n")
        self.emit("video.example.co.uk")
        import auto_detect_destination_commit as mod
        prior_replace = mod._replace
        def broken_second_target(path, *args):
            if path == self.youtube:
                raise OSError("original-second-target-io-failure")
            return prior_replace(path, *args)
        with self.queue.exclusive():
            pending = self.prepare()
            folder = self.chain.tip(self.proof).open_folder
            with patch.object(mod, "_replace", side_effect=broken_second_target):
                with self.assertRaises(V2OriginalConfigRefused):
                    self.commit(pending)
            # First target applied before second target failed: NO checkpoint.
            self.assertTrue((folder / "destination" / "plan.json").is_file())
            self.assertFalse((folder / "destination" / "checkpoint.json").exists())
            self.assertEqual(self.auto.read_text(),
                             "!untouched.example\nexample.co.uk\n")
            old = self.debug.with_name("prior-partial-debug")
            new = self.debug.with_name(".new-partial-debug")
            new.write_bytes(b"")
            new.chmod(0o600)
            os.link(self.debug, old)
            os.replace(new, self.debug)
            # User GUI deletes the first partial effect. It must not be
            # recreated from an uncommitted plan after diagnostic cut.
            self.auto.write_text("!untouched.example\n")
            with self.assertRaisesRegex(OriginalV2PrepareRefused,
                                        "original_v2_prepared_intent_unavailable"):
                self.prepare()
            with self.assertRaises(V2OriginalConfigRefused):
                self.commit(pending)
            self.assertTrue(pending.exists())
            self.assertEqual(self.auto.read_text(), "!untouched.example\n")
            self.assertEqual(self.youtube.read_text(), "example.co.uk\n")
            self.assertFalse((folder / "recovery.json").exists())

    def test_recovery_replays_current_gui_exclusion_and_not_stale_plan(self):
        self.emit("video.example.co.uk")
        with self.queue.exclusive():
            pending = self.prepare()
            old = self.debug.with_name("previous-debug")
            new = self.debug.with_name(".future-debug")
            new.write_bytes(b"")
            new.chmod(0o600)
            os.link(self.debug, old)
            os.replace(new, self.debug)
            self.assertEqual(self.prepare(), pending)
            # User edits manual exclusions AFTER original native event;
            # recovery must ask P1/Config now, not reuse earlier guesses.
            self.excluded = "example.co.uk\n"
            cp = self.commit(pending)
            self.assertTrue(self.ack(pending, cp))
            self.assertEqual(self.auto.read_text(), "!untouched.example\n")
            self.assertEqual(self.chain.tip(self.proof).next_sequence, 1)

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
