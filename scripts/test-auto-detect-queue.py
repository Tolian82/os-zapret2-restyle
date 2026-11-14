#!/usr/bin/env python3
"""Focused P2 race/crash regression; no appliance or network dependency."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "src/opnsense/scripts/OPNsense/Zapret/backend/auto_detect_queue.py"
spec = importlib.util.spec_from_file_location("auto_detect_queue", MODULE)
queue = importlib.util.module_from_spec(spec)
spec.loader.exec_module(queue)


class DurableInboxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        base.chmod(0o700)
        root = base / "auto-detect"
        root.mkdir(mode=0o700)
        (root / "pending").mkdir(mode=0o700)
        (root / "inbox.txt").write_bytes(b"one.example.com\n")
        self.root = root
        self.queue = queue.DurableInbox(root, owner_uid=os.geteuid())

    def test_rotation_preserves_data_and_keeps_live_path(self):
        with self.queue.exclusive():
            p = self.queue.rotate()
            self.assertEqual(p.read_bytes(), b"one.example.com\n")
            self.assertEqual(self.queue.inbox.read_bytes(), b"")
            self.queue.inbox.write_bytes(b"new.example.com\n")
            self.assertNotEqual(queue._identity(p), queue._identity(self.queue.inbox))
            self.assertEqual(len(self.queue.segments()), 1)

    def test_old_open_writer_survives_replace(self):
        with self.queue.exclusive():
            with self.queue.inbox.open("ab", buffering=0) as writer:
                p = self.queue.rotate()
                writer.write(b"late.example.com\n")
                os.fsync(writer.fileno())
            self.assertEqual(p.read_bytes(), b"one.example.com\nlate.example.com\n")
            self.assertEqual(self.queue.inbox.read_bytes(), b"")

    def test_crash_after_link_before_replace_recovers(self):
        with self.queue.exclusive():
            old = queue._identity(self.queue.inbox)
            p = self.queue.pending / "crash.txt"
            os.link(self.queue.inbox, p)
            self.assertEqual(queue._identity(p), old)
            self.assertFalse(self.queue.acknowledge(p, drained=lambda *_: True, committed=lambda _: True))
            self.assertEqual(self.queue.rotate(), p)
            self.assertNotEqual(queue._identity(self.queue.inbox), old)
            self.assertEqual(p.read_text(), "one.example.com\n")

    def test_drain_and_commit_must_precede_unlink(self):
        with self.queue.exclusive():
            p = self.queue.rotate()
            self.assertFalse(self.queue.acknowledge(p, drained=lambda *_: False, committed=lambda _: True))
            self.assertFalse(self.queue.acknowledge(p, drained=lambda *_: True, committed=lambda _: False))
            self.assertTrue(p.exists())
            self.assertTrue(self.queue.acknowledge(p, drained=lambda *_: True,
                                                   committed=lambda data: data == b"one.example.com\n"))
            self.assertFalse(p.exists())

    def test_partial_line_remains_pending(self):
        with self.queue.exclusive():
            p = self.queue.rotate()
            p.write_bytes(b"half.example")
            self.assertFalse(self.queue.acknowledge(p, drained=lambda *_: True, committed=lambda _: True))
            self.assertTrue(p.exists())

    def test_unsafe_symlink_and_unknown_pending_fail_closed(self):
        with self.queue.exclusive():
            p = self.queue.pending / "unexpected"
            p.write_text("something")
            with self.assertRaises(queue.QueueSafetyError):
                self.queue.rotate()
        p.unlink()
        self.queue.inbox.unlink()
        self.queue.inbox.symlink_to(self.root / "other")
        with self.assertRaises(queue.QueueSafetyError):
            with self.queue.exclusive():
                pass

    def test_concurrent_exclusive_fails_without_rotating(self):
        with self.queue.exclusive():
            with self.assertRaisesRegex(queue.QueueSafetyError, "worker_busy"):
                with self.queue.exclusive():
                    pass
            self.assertEqual(self.queue.inbox.read_bytes(), b"one.example.com\n")

    def test_oversized_live_raw_refuses_before_hardlink_or_replace(self):
        # PRE-FIX reproducer: the original P2a rotate() detached >4 MiB,
        # but its exact v2 reader/ACK can never consume that inode.
        with self.queue.inbox.open("r+b") as output:
            output.truncate(queue.MAX_SEGMENT + 1)
        before = self.queue.inbox.stat()
        with self.queue.exclusive():
            with self.assertRaisesRegex(queue.QueueSafetyError, "oversized_segment"):
                self.queue.rotate(generation="a" * 32)
            after = self.queue.inbox.stat()
            self.assertEqual((after.st_dev, after.st_ino, after.st_size),
                             (before.st_dev, before.st_ino, before.st_size))
            self.assertEqual(self.queue.segments(), [])
            self.assertEqual(list(self.root.glob(".new-inbox-*")), [])

    def test_oversized_crash_link_remains_recoverable_without_replacing_live(self):
        # Crash after hardlink but before replace: no second pending name,
        # no relabel, no destructive attempt to recover an unreadable batch.
        with self.queue.inbox.open("r+b") as output:
            output.truncate(queue.MAX_SEGMENT + 1)
        before = self.queue.inbox.stat()
        generation = "b" * 32
        p = self.queue.pending / (generation + "-" + "c" * 32 + ".txt")
        os.link(self.queue.inbox, p)
        with self.queue.exclusive():
            with self.assertRaisesRegex(queue.QueueSafetyError, "oversized_segment"):
                self.queue.rotate(generation=generation)
            after = self.queue.inbox.stat()
            self.assertEqual((after.st_dev, after.st_ino, after.st_size),
                             (before.st_dev, before.st_ino, before.st_size))
            self.assertEqual(queue._identity(p), queue._identity(self.queue.inbox))
            self.assertEqual(self.queue.segments(), [p])
            self.assertEqual(p.stat().st_nlink, 2)
            self.assertEqual(list(self.root.glob(".new-inbox-*")), [])

    def test_producer_append_during_hardlink_refuses_without_replace(self):
        # RED on _52: initial size fits, link succeeds, producer appends
        # while pending directory is synced, then rotate() replaced live.
        generation = "d" * 32
        original_link = os.link
        before = self.queue.inbox.stat()
        extra = b"late.example.com\n"

        def link_then_append(source, target, **kwargs):
            original_link(source, target, **kwargs)
            with self.queue.inbox.open("ab", buffering=0) as writer:
                writer.write(extra)
                os.fsync(writer.fileno())

        with self.queue.exclusive():
            with patch.object(queue.os, "link", side_effect=link_then_append):
                with self.assertRaisesRegex(
                    queue.QueueSafetyError, "raw_changed_between_link_and_replace"
                ):
                    self.queue.rotate(generation=generation)
            pending = self.queue.segments()
            self.assertEqual(len(pending), 1)
            live = self.queue.inbox.stat()
            self.assertEqual((live.st_dev, live.st_ino),
                             (before.st_dev, before.st_ino))
            self.assertEqual(live.st_nlink, 2)
            self.assertEqual(queue._identity(pending[0]),
                             queue._identity(self.queue.inbox))
            self.assertEqual(self.queue.inbox.read_bytes(),
                             b"one.example.com\n" + extra)
            self.assertEqual(list(self.root.glob(".new-inbox-*")), [])
            # Next attempt recovers the ORIGINAL same-generation crash link;
            # it does not invent a fresh pending or lose the late record.
            self.assertEqual(self.queue.rotate(generation=generation), pending[0])
            self.assertEqual(pending[0].read_bytes(),
                             b"one.example.com\n" + extra)
            self.assertEqual(pending[0].stat().st_nlink, 1)
            self.assertEqual(self.queue.inbox.read_bytes(), b"")

    def test_producer_crosses_4mib_after_link_still_keeps_live_inode(self):
        # The _51 pre-link size check alone cannot protect this real window.
        generation = "e" * 32
        original_link = os.link
        before = self.queue.inbox.stat()

        def link_then_overflow(source, target, **kwargs):
            original_link(source, target, **kwargs)
            with self.queue.inbox.open("r+b") as writer:
                writer.truncate(queue.MAX_SEGMENT + 1)
                writer.flush()
                os.fsync(writer.fileno())

        with self.queue.exclusive():
            with patch.object(queue.os, "link", side_effect=link_then_overflow):
                with self.assertRaisesRegex(
                    queue.QueueSafetyError, "oversized_segment"
                ):
                    self.queue.rotate(generation=generation)
            pending = self.queue.segments()
            self.assertEqual(len(pending), 1)
            live = self.queue.inbox.stat()
            self.assertEqual((live.st_dev, live.st_ino),
                             (before.st_dev, before.st_ino))
            self.assertEqual(live.st_nlink, 2)
            self.assertEqual(live.st_size, queue.MAX_SEGMENT + 1)
            self.assertEqual(queue._identity(pending[0]),
                             queue._identity(self.queue.inbox))
            self.assertEqual(list(self.root.glob(".new-inbox-*")), [])
            # This live file is now genuinely oversized; do not detach it
            # on subsequent retries or pretend to have a lossless recovery.
            with self.assertRaisesRegex(queue.QueueSafetyError,
                                        "oversized_segment"):
                self.queue.rotate(generation=generation)
            self.assertEqual(queue._identity(pending[0]),
                             queue._identity(self.queue.inbox))

    def test_oversized_pending_is_not_removed(self):
        with self.queue.exclusive():
            p = self.queue.rotate()
            with p.open("r+b") as stream:
                stream.truncate(queue.MAX_SEGMENT + 1)
            with self.assertRaisesRegex(queue.QueueSafetyError, "oversized_segment"):
                self.queue.acknowledge(p, drained=lambda *_: True, committed=lambda _: True)
            self.assertTrue(p.exists())

    def test_failed_commit_replayed_idempotently(self):
        with self.queue.exclusive():
            p = self.queue.rotate()
            written = {"count": 0}
            def write(data):
                written["count"] += 1
                return written["count"] > 1
            self.assertFalse(self.queue.acknowledge(p, drained=lambda *_: True, committed=write))
            self.assertTrue(p.exists())
            self.assertTrue(self.queue.acknowledge(p, drained=lambda *_: True, committed=write))
            self.assertEqual(written["count"], 2)


if __name__ == "__main__":
    unittest.main()
