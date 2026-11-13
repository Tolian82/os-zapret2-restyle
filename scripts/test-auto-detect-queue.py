#!/usr/bin/env python3
"""Focused P2 race/crash regression; no appliance or network dependency."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

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
