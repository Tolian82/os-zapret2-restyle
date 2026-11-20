#!/usr/bin/env python3
"""Focused P2 race/crash regression; no appliance or network dependency."""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "src/opnsense/scripts/OPNsense/Zapret/backend/auto_detect_queue.py"
# The original module is loaded by path in this standalone test; its
# established backend siblings must stay importable without copying them.
sys.path.insert(0, str(MODULE.parent))
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

    def test_original_native_rotation_retains_open_fd_and_new_append(self):
        import hashlib
        generation = "a" * 32
        native = self.root / ("learning-" + generation + "-1.txt")
        source = b"known.example.com\nstay.example.org\n"
        native.write_bytes(source)
        initial = native.stat()
        cut = len(b"known.example.com\n")
        prefix = hashlib.sha256(source[:cut]).hexdigest()
        with self.queue.exclusive():
            with native.open("ab", buffering=0) as producer:
                pending = self.queue._rotate_original_source(
                    native, replacement=b"stay.example.org\n",
                    generation=generation,
                    expected_identity=(initial.st_dev, initial.st_ino),
                    sealed_prefix=(cut, prefix))
                producer.write(b"new-after-rename.example.net\n")
                os.fsync(producer.fileno())
            self.assertIsNotNone(pending)
            self.assertEqual(native.read_bytes(), b"stay.example.org\n")
            self.assertEqual(
                pending.read_bytes(),
                source + b"new-after-rename.example.net\n")
            self.assertNotEqual(queue._identity(native),
                                queue._identity(pending))
            self.assertEqual(pending.stat().st_nlink, 1)
            self.assertEqual(pending.parent, self.queue.pending)
            self.assertRegex(
                pending.name,
                r"^native-" + generation + r"-1-[0-9a-f]{32}\.txt$")
            with self.assertRaisesRegex(
                    queue.QueueSafetyError,
                    "native_pending_requires_qualified_ack"):
                self.queue.acknowledge(
                    pending, drained=lambda *args: True,
                    committed=lambda data: True)
            # This physical primitive CANNOT authorize any native ACK;
            # the protected source inode persists until ALL late rows
            # have a separately durable original destination receipt.
            self.assertEqual(self.queue.segments(), [pending])

    def test_original_native_append_during_hardlink_preserves_inode(self):
        import hashlib
        generation = "d" * 32
        native = self.root / ("learning-" + generation + "-4.txt")
        original = b"known.example.com\nkeep.example.com\n"
        late = b"racing.example.net\n"
        native.write_bytes(original)
        st = native.stat()
        identity = (st.st_dev, st.st_ino)
        cut = len(b"known.example.com\n")
        prefix = (cut, hashlib.sha256(original[:cut]).hexdigest())
        native_link = queue.os.link

        def append_during_link(*args, **kwargs):
            native_link(*args, **kwargs)
            with native.open("ab", buffering=0) as output:
                output.write(late)
                os.fsync(output.fileno())

        with self.queue.exclusive():
            with patch.object(queue.os, "link", side_effect=append_during_link):
                with self.assertRaisesRegex(
                        queue.QueueSafetyError,
                        "raw_changed_between_link_and_replace"):
                    self.queue._rotate_original_source(
                        native, replacement=b"keep.example.com\n",
                        generation=generation, expected_identity=identity,
                        sealed_prefix=prefix)
            pending = self.queue.segments()
            self.assertEqual(len(pending), 1)
            self.assertRegex(
                pending[0].name,
                r"^native-" + generation + r"-4-[0-9a-f]{32}\.txt$")
            self.assertEqual(queue._identity(native), identity)
            self.assertEqual(queue._identity(pending[0]), identity)
            self.assertEqual(native.read_bytes(), original + late)
            self.assertEqual(pending[0].read_bytes(), original + late)
            self.assertEqual(pending[0].stat().st_nlink, 2)
            recovered = self.queue._rotate_original_source(
                native, replacement=b"keep.example.com\nracing.example.net\n",
                generation=generation, expected_identity=identity,
                sealed_prefix=prefix)
            self.assertEqual(recovered, pending[0])
            self.assertEqual(native.read_bytes(),
                             b"keep.example.com\nracing.example.net\n")
            self.assertEqual(recovered.read_bytes(), original + late)
            self.assertEqual(recovered.stat().st_nlink, 1)

    def test_original_native_refuses_bad_epoch_and_non_subset(self):
        import hashlib
        generation = "b" * 32
        native = self.root / ("learning-" + generation + "-2.txt")
        body = b"known.example.com\nother.example.com\n"
        native.write_bytes(body)
        st = native.stat()
        identity = (st.st_dev, st.st_ino)
        cut = len(b"known.example.com\n")
        prefix = (cut, hashlib.sha256(body[:cut]).hexdigest())
        with self.queue.exclusive():
            for kwargs in (
                {"expected_identity": (st.st_dev, st.st_ino + 1),
                 "sealed_prefix": prefix},
                {"expected_identity": identity,
                 "sealed_prefix": (cut, "0" * 64)},
                {"expected_identity": identity,
                 "sealed_prefix": prefix},
            ):
                replacement = (b"not-an-original-row.example.com\n"
                               if kwargs["sealed_prefix"] == prefix and
                               kwargs["expected_identity"] == identity
                               else b"other.example.com\n")
                with self.assertRaises(queue.QueueSafetyError):
                    self.queue._rotate_original_source(
                        native, replacement=replacement,
                        generation=generation, **kwargs)
            with self.assertRaisesRegex(
                    queue.QueueSafetyError,
                    "native_compaction_must_shrink_hostlist"):
                self.queue._rotate_original_source(
                    native, replacement=body, generation=generation,
                    expected_identity=identity, sealed_prefix=prefix)
            self.assertEqual(self.queue.segments(), [])
            self.assertEqual(native.read_bytes(), body)

    def test_original_native_rotate_crash_after_link_retries_without_loss(self):
        import hashlib
        generation = "c" * 32
        native = self.root / ("learning-" + generation + "-3.txt")
        initial = b"known.example.com\nkeep.example.com\n"
        native.write_bytes(initial)
        st = native.stat()
        identity = (st.st_dev, st.st_ino)
        cut = len(b"known.example.com\n")
        prefix = (cut, hashlib.sha256(initial[:cut]).hexdigest())
        original_replace = queue.os.replace

        def crash_before_replace(*args, **kwargs):
            raise OSError("injected_before_native_replace")
        with self.queue.exclusive():
            with patch.object(queue.os, "replace",
                              side_effect=crash_before_replace):
                with self.assertRaises(OSError):
                    self.queue._rotate_original_source(
                        native, replacement=b"keep.example.com\n",
                        generation=generation, expected_identity=identity,
                        sealed_prefix=prefix)
            pending = self.queue.segments()
            self.assertEqual(len(pending), 1)
            self.assertEqual(queue._identity(pending[0]), identity)
            self.assertEqual(queue._identity(native), identity)
            with native.open("ab") as producer:
                producer.write(b"late.example.com\n")
                producer.flush()
                os.fsync(producer.fileno())
            # The original prefix remains sealed, but this native source
            # changed during the old link. The next isolated original P2a
            # attempt may resume ONLY after a fresh full native snapshot:
            # no implicit ACK or lost late producer writes.
            restored = self.queue._rotate_original_source(
                native, replacement=b"keep.example.com\nlate.example.com\n",
                generation=generation, expected_identity=identity,
                sealed_prefix=prefix)
            self.assertEqual(restored, pending[0])
            self.assertEqual(native.read_bytes(),
                             b"keep.example.com\nlate.example.com\n")
            self.assertEqual(restored.read_bytes(),
                             initial + b"late.example.com\n")
            self.assertEqual(restored.stat().st_nlink, 1)

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
