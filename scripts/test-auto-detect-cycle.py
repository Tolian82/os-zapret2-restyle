#!/usr/bin/env python3
"""P2j actual DurableInbox plus synthetic owner/FD/debug/commit adapter tests.

Portable safety regression, NOT live FreeBSD dvtws2 or authorized schema2.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"))

from auto_detect_cycle import CycleRefused, _cycle_once, run_native_cycle
from auto_detect_queue import DurableInbox, _identity, QueueSafetyError
from auto_detect_fd import FDState, OwnerToken
from auto_detect_owner import GenerationProof


class CycleTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="p2j-cycle-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.base.chmod(0o700)
        root = self.base / "state"
        root.mkdir(mode=0o700)
        (root / "pending").mkdir(mode=0o700)
        (root / "inbox.txt").write_bytes(b"hello.example.org\n")
        self.queue = DurableInbox(root, owner_uid=os.geteuid())
        self.proof = GenerationProof(
            owner=OwnerToken(4321, "Fri Nov 13 10:00:00 2026",
                             "/usr/local/sbin/dvtws2"),
            operation_id="a" * 32, generation="a" * 32,
            final_args_sha256="b" * 64,
            raw_path=str(self.queue.inbox),
            debug_path=str(root / "debug.log"),
            observer_native_number=2,
            profiles=((1, "known-hostlist", "youtube"),
                      (2, "observer", None),
                      (0, "unknown-native-default", None)),
        )
        self.owner = self.proof
        self.fd = FDState.DRAINED
        self.commit_ok = True
        self.debug_ok = True
        self.calls = []
        self.persisted = set()

    def attest(self):
        self.calls.append("owner")
        return self.owner

    def inspect(self, path, dev, ino, *, owner, writer_gid):
        self.assertEqual(owner, self.proof.owner)
        self.assertIsNone(writer_gid)  # Portable private-root queue only.
        self.assertEqual(_identity(path), (dev, ino))
        self.calls.append("fd")
        return self.fd

    def correlate(self, raw, proof):
        self.calls.append("debug")
        self.assertEqual(proof, self.proof)
        return self.debug_ok

    def commit(self, raw, proof):
        self.calls.append("commit")
        self.assertEqual(proof, self.proof)
        if self.commit_ok:
            self.persisted.add(raw)
        return self.commit_ok

    def cycle(self, *, debug=True, commit=True):
        return _cycle_once(self.queue, attest=self.attest,
                           inspect=self.inspect,
                           correlate=self.correlate if debug else None,
                           persist=self.commit if commit else None)

    def test_missing_adapters_refuse_before_rotation(self):
        old = _identity(self.queue.inbox)
        for kwargs in ({"debug": False}, {"commit": False}):
            with self.assertRaisesRegex(CycleRefused,
                                        "missing_fd_debug_or_durable_commit_adapter"):
                self.cycle(**kwargs)
        self.assertEqual(_identity(self.queue.inbox), old)
        self.assertFalse(list(self.queue.pending.iterdir()))

    def test_fd_busy_unknown_and_debug_unknown_preserve_pending(self):
        for state in (FDState.BUSY, FDState.UNKNOWN):
            with self.subTest(state=state):
                self.fd = state
                result = self.cycle()
                self.assertTrue(result.blocked)
                self.assertEqual(result.retained, 1)
                self.assertFalse(self.persisted)
                self.assertNotIn("commit", self.calls)
                self.calls.clear()
        self.fd = FDState.DRAINED
        self.debug_ok = False
        result = self.cycle()
        self.assertTrue(result.blocked)
        self.assertNotIn("commit", self.calls)
        self.assertTrue(list(self.queue.pending.iterdir()))

    def test_failed_persist_then_retry_acks_idempotently(self):
        self.commit_ok = False
        r = self.cycle()
        self.assertTrue(r.blocked)
        self.assertEqual(len(list(self.queue.pending.iterdir())), 1)
        self.commit_ok = True
        r = self.cycle()
        self.assertFalse(r.blocked)
        self.assertEqual(r.acknowledged, 1)
        self.assertEqual(self.persisted, {b"hello.example.org\n"})
        self.assertFalse(list(self.queue.pending.iterdir()))
        self.assertEqual(self.queue.inbox.read_bytes(), b"")

    def test_owner_changed_after_commit_never_unlinks(self):
        def changed(raw, proof):
            self.persisted.add(raw)
            self.owner = GenerationProof(
                proof.owner, "c" * 32, "c" * 32, proof.final_args_sha256,
                proof.raw_path, proof.debug_path, proof.observer_native_number,
                proof.profiles)
            return True
        with self.assertRaisesRegex(CycleRefused,
                                    "common_generation_changed_during_cycle"):
            _cycle_once(self.queue, attest=self.attest, inspect=self.inspect,
                        correlate=self.correlate, persist=changed)
        self.assertTrue(list(self.queue.pending.iterdir()))
        self.assertEqual(self.persisted, {b"hello.example.org\n"})
        self.owner = self.proof
        r = self.cycle()
        self.assertEqual(r.acknowledged, 1)
        self.assertEqual(len(self.persisted), 1)

    def test_forged_generation_refused_before_rotation(self):
        old = _identity(self.queue.inbox)
        self.owner = GenerationProof(
            self.proof.owner, self.proof.operation_id, "x" * 32,
            self.proof.final_args_sha256, self.proof.raw_path,
            self.proof.debug_path, self.proof.observer_native_number,
            self.proof.profiles)
        with self.assertRaisesRegex(CycleRefused,
                                    "wrong_queue_or_observer_generation"):
            self.cycle()
        self.assertEqual(old, _identity(self.queue.inbox))
        self.assertFalse(list(self.queue.pending.iterdir()))

    def test_recovers_same_generation_link_before_replace(self):
        previous = _identity(self.queue.inbox)
        pending = self.queue.pending / (self.proof.generation + "-" +
                                        "d" * 32 + ".txt")
        os.link(self.queue.inbox, pending)
        self.assertEqual(_identity(pending), previous)
        r = self.cycle()
        self.assertTrue(r.rotated)
        self.assertEqual(r.acknowledged, 1)
        self.assertFalse(pending.exists())
        self.assertNotEqual(_identity(self.queue.inbox), previous)
        self.assertEqual(self.persisted, {b"hello.example.org\n"})

    def test_previous_generation_pending_kept_without_new_rotation(self):
        with self.queue.exclusive():
            old = self.queue.rotate(generation="c" * 32)
        self.assertTrue(old.exists())
        existing = _identity(self.queue.inbox)
        self.queue.inbox.write_bytes(b"new.example.org\n")
        with self.assertRaisesRegex(CycleRefused,
                                    "pending_segment_has_no_current_generation_proof"):
            self.cycle()
        self.assertEqual(_identity(self.queue.inbox), existing)
        self.assertTrue(old.exists())
        self.assertFalse(self.persisted)
        self.assertNotIn("fd", self.calls)

    def test_old_generation_link_crash_refuses_replacement(self):
        old = _identity(self.queue.inbox)
        pending = self.queue.pending / ("c" * 32 + "-" + "f" * 32 + ".txt")
        os.link(self.queue.inbox, pending)
        with self.assertRaisesRegex(CycleRefused,
                                    "pending_segment_has_no_current_generation_proof"):
            self.cycle()
        self.assertEqual(_identity(self.queue.inbox), old)
        self.assertEqual(_identity(pending), old)
        self.assertFalse(self.persisted)

    def test_partial_line_never_reaches_commit(self):
        self.queue.inbox.write_bytes(b"incomplete.example")
        r = self.cycle()
        self.assertTrue(r.blocked)
        self.assertFalse(self.persisted)
        self.assertNotIn("commit", self.calls)
        self.assertTrue(list(self.queue.pending.iterdir()))

    def test_order_fd_then_debug_then_commit(self):
        r = self.cycle()
        self.assertFalse(r.blocked)
        self.assertTrue(self.calls.index("fd") <
                        self.calls.index("debug") < self.calls.index("commit"))
        self.assertEqual(r.acknowledged, 1)

    def test_invalid_generation_refused_by_queue(self):
        before = _identity(self.queue.inbox)
        with self.queue.exclusive():
            with self.assertRaisesRegex(QueueSafetyError,
                                        "invalid_producer_generation"):
                self.queue.rotate(generation="bad")
        self.assertEqual(_identity(self.queue.inbox), before)
        self.assertFalse(list(self.queue.pending.iterdir()))

    def test_public_native_entry_is_unconditionally_disabled(self):
        with self.assertRaisesRegex(CycleRefused,
                                    "native_cycle_not_active_without_debug_and_destination"):
            run_native_cycle()


if __name__ == "__main__":
    unittest.main()
