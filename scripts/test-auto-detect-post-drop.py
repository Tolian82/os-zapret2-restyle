#!/usr/bin/env python3
"""P2k8h: original protected inode pre/post-drop refusal before IPFW.

No native service, Model, dvtws2, IPFW or scheduler changes. The existing
single disposable P2i VM covers actual dropped-credential fchown.
"""
from __future__ import annotations
from dataclasses import replace
import fcntl
import hashlib
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

BACKEND = Path(__file__).resolve().parents[1] / 'src/opnsense/scripts/OPNsense/Zapret/backend'
sys.path.insert(0, str(BACKEND))
from auto_detect_post_drop import _capture, _reattest, _witness_line, _witness_read, original_fd9_command, PostDropRefused, native_capture_before_launch, native_restore_before_ipfw
from auto_detect_post_drop import (_witness_line_learning, _witness_decode_learning,
    _witness_read_learning, _qualified_learning_sources)
from auto_detect_queue import DurableInbox
from auto_detect_original_v2_source import (LearningCursor, OriginalSourceRefused,
    preview_original_learning_windows_locked, preview_learning_pretraffic_cursors_locked)


class PostDropContract(unittest.TestCase):
    def setUp(self):
        if os.getegid() <= 0:
            self.skipTest("portable fixture requires a non-root group; native FreeBSD root is covered separately")
        self.temp = tempfile.TemporaryDirectory(prefix='p2k8h-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'producer'
        # Match the real /var/db root traversal policy required by P2a.
        self.root.parent.chmod(0o711)
        self.root.mkdir(mode=0o700)
        self.root.chmod(0o710)
        (self.root / 'pending').mkdir(mode=0o700)
        for name in ('inbox.txt', 'debug.log'):
            p = self.root / name
            p.write_bytes(b'')
            p.chmod(0o660)
        self.owner = os.geteuid()
        self.gid = os.getegid()
        self.engine = self.owner + 1 if self.owner > 0 else 65534
        self.assertNotEqual(self.owner, self.engine)

    def capture(self):
        return _capture(self.root, root_uid=self.owner,
                        root_gid=self.gid, engine_uid=self.engine,
                        engine_gid=self.gid)

    def test_first_learning_base_zero_cut_preserves_original_queue(self):
        import json
        from auto_detect_post_drop import match_zero_cut, PROVENANCE_FIELDS
        generation = "a" * 32
        names = tuple(f"learning-{generation}-{n}.txt" for n in (3, 4))
        sources = tuple((n, "youtube", str(self.root / name))
                        for n, name in zip((3, 4), names))
        paths = tuple(self.root / name for name in ("inbox.txt", "debug.log", *names))
        for path in paths[2:]:
            path.touch()
            path.chmod(0o660)
        queue = DurableInbox(self.root, owner_uid=self.owner, writer_gid=self.gid)
        with queue.exclusive():
            def capture():
                return _capture(self.root, root_uid=self.owner, root_gid=self.gid,
                    engine_uid=self.engine, engine_gid=self.gid, learning_names=names,
                    queue_fd=queue.locked_fd)
            original = capture()
            provenance = {key: hashlib.sha256(key.encode()).hexdigest()
                          for key in PROVENANCE_FIELDS}
            seed = dict(schema=3, kind="original-fd9-learning-pretraffic-zero",
                generation=generation, owner_candidate_sha256="b" * 64,
                ack_authorized=False, **provenance,
                files=[dict(name=p.name, device=d, inode=i, nlink=l)
                       for p, (d, i, l) in zip(paths, original.identities)],
                learning=[dict(native_number=n, hostlist=h, path=p, device=d, inode=i,
                               offset=0, prefix_sha256=hashlib.sha256(b"").hexdigest())
                          for (n, h, p), (d, i, _) in zip(sources, original.identities[2:])])
            raw = (json.dumps(seed, sort_keys=True, separators=(",", ":")) + "\n").encode()
            record = dict(phase="activated", manifest={"schema": 2},
                detail={"id": generation, "base": "c" * 64, "candidate": "b" * 64},
                first_running_sha256="d" * 64,
                first_pretraffic_sha256=hashlib.sha256(raw).hexdigest())
            def check():
                return match_zero_cut(record, sources, capture(), raw, provenance)
            self.assertEqual(check(), raw)
            self.assertEqual(check(), raw)
            for path in paths:
                with self.subTest(nonempty=path.name):
                    path.write_bytes(b"fixture\n")
                    with self.assertRaises(PostDropRefused):
                        check()
                    self.assertEqual(path.read_bytes(), b"fixture\n")
                    path.write_bytes(b"")
            for key in PROVENANCE_FIELDS:
                with self.subTest(provenance=key), self.assertRaises(ValueError):
                    match_zero_cut(record, sources, capture(), raw,
                                   {**provenance, key: "f" * 64})
            paths[-1].rename(self.root.parent / "old-original")
            paths[-1].touch()
            paths[-1].chmod(0o660)
            with self.assertRaises(ValueError):
                check()
            self.assertTrue((self.root.parent / "old-original").is_file())

    def test_learning_inboxes_preserve_prelaunch_and_postdrop_inodes(self):
        names = ("learning-" + "a" * 32 + "-3.txt",
                 "learning-" + "a" * 32 + "-4.txt")
        for name in names:
            p = self.root / name
            p.write_bytes(b"")
            p.chmod(0o660)
        witness = _capture(
            self.root, root_uid=self.owner, root_gid=self.gid,
            engine_uid=self.engine, engine_gid=self.gid,
            learning_names=names)
        self.assertEqual(witness.learning_names, names)
        self.assertEqual(len(witness.identities), 4)
        (self.root / names[0]).write_bytes(b"video.example.com\n")
        self.assertEqual(_reattest(witness, lambda: True), ())
        self.assertEqual((self.root / names[0]).read_bytes(),
                         b"video.example.com\n")
        # The old six-u64 witness must refuse, never silently drop N inodes.
        with self.assertRaisesRegex(
                PostDropRefused, "legacy_fd9_witness_cannot_encode_learning_inboxes"):
            _witness_line(witness)
        temp = self.root / "replacement"
        temp.write_bytes(b"")
        temp.chmod(0o660)
        temp.replace(self.root / names[1])
        with patch("auto_detect_post_drop.os.fchown") as chown:
            with self.assertRaisesRegex(
                    PostDropRefused, "original_producer_inode_drift"):
                _reattest(witness, lambda: True)
            chown.assert_not_called()

    def test_learning_inboxes_refuse_unexpected_generation_before_changes(self):
        names = ("learning-" + "a" * 32 + "-3.txt",)
        p = self.root / names[0]
        p.write_bytes(b"")
        p.chmod(0o660)
        def capture(names_to_check):
            return _capture(
                self.root, root_uid=self.owner, root_gid=self.gid,
                engine_uid=self.engine, engine_gid=self.gid,
                learning_names=names_to_check)
        for invalid in (
            (), ("../escape",), (names[0], names[0]),
            ("learning-" + "b" * 32 + "-3.txt",),
        ):
            with self.subTest(invalid=invalid), self.assertRaises(PostDropRefused):
                capture(invalid)
        self.assertEqual(capture(names).learning_names, names)
        self.assertEqual(p.read_bytes(), b"")


    def test_tz6v4_versioned_full_fd9_witness_roundtrip_and_original_unchanged(self):
        generation = "a" * 32
        names = (
            f"learning-{generation}-3.txt",
            f"learning-{generation}-4.txt",
        )
        sources = ((3, "youtube", str(self.root / names[0])),
                   (4, "user", str(self.root / names[1])))
        for name in names:
            p = self.root / name
            p.write_bytes(b"")
            p.chmod(0o660)
        captured = _capture(
            self.root, root_uid=self.owner, root_gid=self.gid,
            engine_uid=self.engine, engine_gid=self.gid, learning_names=names)
        wire = _witness_line_learning(captured, sources)
        self.assertTrue(wire.startswith("p2k8i3:" + generation + ":2:"))
        self.assertEqual(len(wire.split(":")), 4 + 4 * 3)
        restored = _witness_decode_learning(
            wire, sources, root=self.root, root_uid=self.owner,
            root_gid=self.gid, engine_uid=self.engine, engine_gid=self.gid)
        self.assertEqual(restored, captured)
        self.assertEqual(_reattest(restored, lambda: True), ())
        with self.assertRaises(PostDropRefused):
            _witness_read(wire)
        with self.assertRaises(PostDropRefused):
            _witness_line(captured)
        # The root production helper additionally takes only ROOT + known
        # nobody identity; no alternate path accepted by the public CLI.
        with patch("auto_detect_post_drop.ROOT", self.root), \
             patch("auto_detect_post_drop._parent"), \
             patch("auto_detect_post_drop.pwd.getpwnam") as nobody:
            nobody.return_value.pw_uid = self.engine
            nobody.return_value.pw_gid = self.gid
            native = _witness_read_learning(wire, sources)
            self.assertEqual(native.identities, captured.identities)
            self.assertEqual(native.learning_names, names)

    def test_tz6v4_fd9_witness_refuses_cross_profile_or_partial_evidence(self):
        generation = "a" * 32
        names = (f"learning-{generation}-3.txt",
                 f"learning-{generation}-4.txt")
        sources = ((3, "youtube", str(self.root / names[0])),
                   (4, "user", str(self.root / names[1])))
        for name in names:
            p = self.root / name
            p.write_bytes(b"")
            p.chmod(0o660)
        captured = _capture(
            self.root, root_uid=self.owner, root_gid=self.gid,
            engine_uid=self.engine, engine_gid=self.gid, learning_names=names)
        wire = _witness_line_learning(captured, sources)
        wrong_sources = (
            ("same-path-other-hostlist", ((3, "user", str(self.root / names[0])),
                                          (4, "user", str(self.root / names[1])))),
            ("wrong-owner", ((3, "youtube", str(self.root / names[0])),
                             (5, "user", str(self.root / names[1])))),
            ("wrong-path", ((3, "youtube", str(self.root / names[0])),
                            (4, "user", str(self.root / "inbox.txt")))),
            ("wrong-generation", ((3, "youtube",
                                   str(self.root / ("learning-" + "b"*32 + "-3.txt"))),
                                  (4, "user",
                                   str(self.root / ("learning-" + "b"*32 + "-4.txt"))))),
            ("reordered", tuple(reversed(sources))),
            ("one-missing", sources[:1]),
        )
        for kind, invalid in wrong_sources:
            with self.subTest(kind=kind), self.assertRaises(PostDropRefused):
                _witness_decode_learning(
                    wire, invalid, root=self.root, root_uid=self.owner,
                    root_gid=self.gid, engine_uid=self.engine,
                    engine_gid=self.gid)
        for kind, corrupted in (
            ("extra inode", wire + ":1:1:1"),
            ("shortened", wire.rsplit(":", 1)[0]),
            ("bad generation", wire.replace(generation, "b"*32, 1)),
            ("bad count", wire.replace(":2:", ":1:", 1)),
            ("no count", wire.replace(":2:", ":0:", 1)),
            ("leading zero", wire.replace(":2:", ":02:", 1)),
            ("negative", wire.replace(":2:", ":2:-", 1)),
            ("too long", wire + "0" * 17000),
            ("foreign old format", "p2k8i:" + ":".join(
                str(v) for identity in captured.identities[:2] for v in identity)),
        ):
            with self.subTest(kind=kind), self.assertRaises(PostDropRefused):
                _witness_decode_learning(
                    corrupted, sources, root=self.root, root_uid=self.owner,
                    root_gid=self.gid, engine_uid=self.engine,
                    engine_gid=self.gid)
        # The exact pre-drop bytes have no side effect: corrupted wire
        # cannot mutate or remove any of the four native files.
        self.assertTrue(all((self.root / n).exists()
                            for n in ("inbox.txt", "debug.log", *names)))
        self.assertTrue(all((self.root / n).read_bytes() == b""
                            for n in ("inbox.txt", "debug.log", *names)))
        # A valid envelope cannot pass its protected inode to a new file.
        restored = _witness_decode_learning(
            wire, sources, root=self.root, root_uid=self.owner,
            root_gid=self.gid, engine_uid=self.engine, engine_gid=self.gid)
        replacement = self.root / "replacement"
        replacement.write_bytes(b"")
        replacement.chmod(0o660)
        replacement.replace(self.root / names[1])
        with self.assertRaisesRegex(PostDropRefused, "original_producer_inode_drift"):
            _reattest(restored, lambda: True)

    def learning_files(self):
        names = ("learning-" + "a" * 32 + "-3.txt",
                 "learning-" + "a" * 32 + "-4.txt")
        sources = (
            (3, "youtube", str(self.root / names[0])),
            (4, "user", str(self.root / names[1])),
        )
        cursors = {}
        for number, hostlist, filename in sources:
            p = Path(filename)
            p.write_bytes(b"")
            p.chmod(0o660)
            physical = p.stat()
            cursors[filename] = LearningCursor(
                "a" * 32, number, hostlist, filename,
                physical.st_dev, physical.st_ino, 0,
                hashlib.sha256(b"").hexdigest())
        return DurableInbox(self.root, owner_uid=self.owner,
                            writer_gid=self.gid), sources, cursors


    def test_learning_pretraffic_fd9_seed_to_physical_append(self):
        queue, sources, _ = self.learning_files()
        names = tuple(Path(path).name for _, _, path in sources)
        captured = _capture(
            self.root, root_uid=self.owner, root_gid=self.gid,
            engine_uid=self.engine, engine_gid=self.gid,
            learning_names=names)
        wire = _witness_line_learning(captured, sources)
        def seeded(*, source_rows=sources, wire_data=wire, attest=lambda: True):
            return preview_learning_pretraffic_cursors_locked(
                queue, wire_data, source_rows, root_gid=self.gid,
                engine_uid=self.engine, attest=attest)
        with self.assertRaisesRegex(
                OriginalSourceRefused, "learning_pretraffic_original_fd9_queue_required"):
            seeded()
        with queue.exclusive():
            start = seeded()
            self.assertEqual(set(start), {path for _, _, path in sources})
            self.assertEqual([v.native_number for v in start.values()], [3, 4])
            self.assertEqual([v.hostlist for v in start.values()],
                             ["youtube", "user"])
            self.assertEqual([v.offset for v in start.values()], [0, 0])
            self.assertTrue(all(v.prefix_sha256 ==
                                hashlib.sha256(b"").hexdigest()
                                for v in start.values()))
            first, second = (Path(row[2]) for row in sources)
            first.write_bytes(b"video.example.co.uk\n")
            second.write_bytes(b"cdn.example.com\n")
            captured_window = preview_original_learning_windows_locked(
                queue, sources, start, attest=lambda: True)
            self.assertEqual(captured_window[str(first)].rows,
                             b"video.example.co.uk\n")
            self.assertEqual(captured_window[str(second)].rows,
                             b"cdn.example.com\n")
            # A second attempt to mint new zero cursors AFTER launch
            # cannot forget already-appended bytes.
            with self.assertRaises(OriginalSourceRefused):
                seeded()
            self.assertEqual(first.read_bytes(), b"video.example.co.uk\n")

    def test_learning_pretraffic_rejects_foreign_map_inode_and_raw(self):
        queue, sources, _ = self.learning_files()
        names = tuple(Path(path).name for _, _, path in sources)
        captured = _capture(
            self.root, root_uid=self.owner, root_gid=self.gid,
            engine_uid=self.engine, engine_gid=self.gid,
            learning_names=names)
        wire = _witness_line_learning(captured, sources)
        def seeded(source_rows=sources, wire_data=wire, attest=lambda: True):
            return preview_learning_pretraffic_cursors_locked(
                queue, wire_data, source_rows, root_gid=self.gid,
                engine_uid=self.engine, attest=attest)
        with queue.exclusive():
            swapped = ((3, "user", sources[0][2]),
                       (4, "youtube", sources[1][2]))
            with self.assertRaises(OriginalSourceRefused):
                seeded(swapped)
            with self.assertRaises(OriginalSourceRefused):
                seeded(wire_data=wire.rsplit(":", 1)[0])
            with self.assertRaises(OriginalSourceRefused):
                seeded(attest=lambda: False)
            # Stale native file swap must refuse without resetting it.
            source = Path(sources[1][2])
            replacement = self.root / "replacement"
            replacement.write_bytes(b"")
            replacement.chmod(0o660)
            replacement.replace(source)
            with self.assertRaisesRegex(
                    OriginalSourceRefused, "learning_pretraffic_inode_not_empty_or_same"):
                seeded()
            self.assertTrue(source.exists())
            self.assertEqual(source.read_bytes(), b"")

    def test_learning_pretraffic_refuses_concurrent_native_append(self):
        queue, sources, _ = self.learning_files()
        names = tuple(Path(path).name for _, _, path in sources)
        captured = _capture(
            self.root, root_uid=self.owner, root_gid=self.gid,
            engine_uid=self.engine, engine_gid=self.gid,
            learning_names=names)
        wire = _witness_line_learning(captured, sources)
        from auto_detect_debug_window import _read_exact
        calls = [0]
        first = Path(sources[0][2])
        def raced(path, **kw):
            item = _read_exact(path, **kw)
            calls[0] += 1
            if path == first and calls[0] == 3:
                with first.open("ab") as out:
                    out.write(b"appended.example.com\n")
            return item
        with queue.exclusive():
            with patch("auto_detect_debug_window._read_exact",
                       side_effect=raced):
                with self.assertRaises(OriginalSourceRefused):
                    preview_learning_pretraffic_cursors_locked(
                        queue, wire, sources, root_gid=self.gid,
                        engine_uid=self.engine, attest=lambda: True)
            self.assertEqual(first.read_bytes(), b"appended.example.com\n")
            self.assertTrue(all(Path(path).exists()
                                for _, _, path in sources))

    def test_learning_physical_native_inboxes_are_read_under_original_queue(self):
        queue, sources, cursors = self.learning_files()
        with self.assertRaisesRegex(
                OriginalSourceRefused, "original_learning_queue_and_epoch_required"):
            preview_original_learning_windows_locked(
                queue, sources, cursors, attest=lambda: True)
        with queue.exclusive():
            empty = preview_original_learning_windows_locked(
                queue, sources, cursors, attest=lambda: True)
            self.assertTrue(all(v.rows == b"" for v in empty.values()))
            self.assertEqual({p: v.after for p, v in empty.items()}, cursors)

            first, second = (Path(s[2]) for s in sources)
            first.write_bytes(b"video.example.com\n")
            second.write_bytes(b"cdn.example.net\n")
            changed = preview_original_learning_windows_locked(
                queue, sources, cursors, attest=lambda: True)
            self.assertEqual(changed[str(first)].rows, b"video.example.com\n")
            self.assertEqual(changed[str(second)].rows, b"cdn.example.net\n")
            next_cursor = {p: w.after for p, w in changed.items()}
            self.assertEqual(changed[str(first)].after.offset, first.stat().st_size)
            self.assertEqual(
                changed[str(first)].after.prefix_sha256,
                hashlib.sha256(first.read_bytes()).hexdigest())
            again = preview_original_learning_windows_locked(
                queue, sources, next_cursor, attest=lambda: True)
            self.assertEqual([w.rows for w in again.values()], [b"", b""])

            with first.open("ab") as out:
                out.write(b"later.example.com\n")
            fresh = preview_original_learning_windows_locked(
                queue, sources, next_cursor, attest=lambda: True)
            self.assertEqual(fresh[str(first)].rows, b"later.example.com\n")
            self.assertEqual(fresh[str(second)].rows, b"")
            self.assertEqual(first.read_bytes(),
                             b"video.example.com\nlater.example.com\n")
            # A same-inode overwrite after the persisted cursor is fatal.
            first.write_bytes(b"forged.example.com\nlater.example.com\n")
            with self.assertRaisesRegex(
                    OriginalSourceRefused, "native_learning_content_or_prefix_changed"):
                preview_original_learning_windows_locked(
                    queue, sources, next_cursor, attest=lambda: True)
            self.assertTrue(first.exists())  # No implicit source cleanup.

    def test_learning_physical_partial_and_forged_cursor_rejected(self):
        queue, sources, cursors = self.learning_files()
        first, second = (Path(s[2]) for s in sources)
        first.write_bytes(b"video.example.com\n")
        second.write_bytes(b"cdn.example.net")  # Native writer not finished.
        with queue.exclusive():
            with self.assertRaises(OriginalSourceRefused):
                preview_original_learning_windows_locked(
                    queue, sources, cursors, attest=lambda: True)
            self.assertEqual(second.read_bytes(), b"cdn.example.net")
            second.write_bytes(b"cdn.example.net\n")
            damaged = dict(cursors)
            damaged[str(first)] = replace(
                cursors[str(first)], generation="b" * 32)
            with self.assertRaisesRegex(
                    OriginalSourceRefused, "unqualified_learning_sealed_cursor"):
                preview_original_learning_windows_locked(
                    queue, sources, damaged, attest=lambda: True)
            mismatched = (
                (3, "user", str(first)), (4, "youtube", str(second)))
            with self.assertRaisesRegex(
                    OriginalSourceRefused, "unqualified_learning_sealed_cursor"):
                preview_original_learning_windows_locked(
                    queue, mismatched, cursors, attest=lambda: True)
            with self.assertRaisesRegex(
                    OriginalSourceRefused, "unqualified_learning_current_owner"):
                preview_original_learning_windows_locked(
                    queue, sources, cursors, attest=lambda: False)

    def test_learning_physical_inode_swap_and_foreign_generation_refused(self):
        queue, sources, cursors = self.learning_files()
        first, second = (Path(s[2]) for s in sources)
        with queue.exclusive():
            outsider = self.root / ("learning-" + "b" * 32 + "-5.txt")
            outsider.write_bytes(b"")
            outsider.chmod(0o660)
            with self.assertRaisesRegex(
                    OriginalSourceRefused, "foreign_learning_producer_entry"):
                preview_original_learning_windows_locked(
                    queue, sources, cursors, attest=lambda: True)
            outsider.unlink()
            replacement = self.root / "replacement"
            replacement.write_bytes(b"")
            replacement.chmod(0o660)
            replacement.replace(second)
            with self.assertRaisesRegex(
                    OriginalSourceRefused, "native_learning_inode_or_cursor_drift"):
                preview_original_learning_windows_locked(
                    queue, sources, cursors, attest=lambda: True)
            self.assertEqual(first.read_bytes(), b"")
            self.assertEqual(second.read_bytes(), b"")

    def test_learning_physical_racing_native_append_is_retained(self):
        queue, sources, cursors = self.learning_files()
        first = Path(sources[0][2])
        first.write_bytes(b"video.example.com\n")
        original_read = os.read
        raced = [False]
        def concurrent_append(fd, length):
            data = original_read(fd, length)
            if not raced[0]:
                raced[0] = True
                with first.open("ab") as out:
                    out.write(b"later.example.com\n")
            return data
        with queue.exclusive():
            with patch("auto_detect_original_v2_source.os.read",
                       side_effect=concurrent_append):
                with self.assertRaisesRegex(
                        OriginalSourceRefused, "native_learning_content_or_prefix_changed"):
                    preview_original_learning_windows_locked(
                        queue, sources, cursors, attest=lambda: True)
            # No cleanup and no fabricated cursor: both lines remain.
            self.assertEqual(first.read_bytes(),
                             b"video.example.com\nlater.example.com\n")
            accepted = preview_original_learning_windows_locked(
                queue, sources, cursors, attest=lambda: True)
            self.assertEqual(accepted[str(first)].rows, first.read_bytes())

    def test_existing_protected_files_before_and_after_same_owner(self):
        stamp = self.capture()
        raw = (self.root / 'inbox.txt').lstat()
        done = _reattest(stamp, lambda: True)
        self.assertEqual(done, ())
        self.assertEqual(((self.root / 'inbox.txt').stat().st_dev,
                          (self.root / 'inbox.txt').stat().st_ino),
                         (raw.st_dev, raw.st_ino))
        self.assertEqual((self.root / 'inbox.txt').stat().st_size, 0)

    def test_changed_debug_inode_refuses_before_first_chown(self):
        stamp = self.capture()
        old = self.root / 'debug.log'
        replacement = self.root / 'replacement'
        replacement.write_bytes(b'')
        replacement.chmod(0o660)
        # The ORIGINAL inode still exists while the foreign inode is created:
        # atomically swap afterwards so inode reuse cannot fake no change.
        replacement.replace(old)
        with patch('auto_detect_post_drop.os.fchown') as change:
            with self.assertRaisesRegex(PostDropRefused, "original_producer_inode_drift"):
                _reattest(stamp, lambda: True)
            change.assert_not_called()
        self.assertEqual((self.root / 'inbox.txt').read_bytes(), b'')

    def test_symlink_and_foreign_inode_refuse(self):
        stamp = self.capture()
        path = self.root / 'inbox.txt'
        path.unlink()
        path.symlink_to(self.root / 'debug.log')
        with self.assertRaises(PostDropRefused):
            _reattest(stamp, lambda: True)

    def test_bad_group_or_mode_refuses_not_repaired(self):
        stamp = self.capture()
        p = self.root / 'debug.log'
        p.chmod(0o666)
        with patch('auto_detect_post_drop.os.fchown') as change:
            with self.assertRaisesRegex(PostDropRefused, "original_producer_inode_drift"):
                _reattest(stamp, lambda: True)
            change.assert_not_called()
        self.assertEqual(stat.S_IMODE(p.stat().st_mode), 0o666)

    def test_changed_process_denied_before_any_chown(self):
        stamp = self.capture()
        with patch('auto_detect_post_drop.os.fchown') as change:
            with self.assertRaisesRegex(PostDropRefused, "original_engine_owner_changed"):
                _reattest(stamp, lambda: False)
            change.assert_not_called()

    def test_process_changed_during_final_attestation_refuses(self):
        stamp = self.capture()
        calls = [True, True, True, False]
        with self.assertRaisesRegex(PostDropRefused, "original_engine_owner_changed"):
            _reattest(stamp, lambda: calls.pop(0))

    def test_untrusted_lock_and_foreign_extra_entry_refuse(self):
        lock = self.root / 'worker.lock'
        lock.write_bytes(b'')
        lock.chmod(0o666)
        with self.assertRaisesRegex(PostDropRefused, "unsafe_original_producer_lock"):
            self.capture()
        lock.unlink()
        (self.root / 'foreign').write_bytes(b'')
        with self.assertRaisesRegex(PostDropRefused, "unsafe_original_producer_layout"):
            self.capture()

    def test_pretraffic_rejects_existing_raw_without_truncation(self):
        raw = self.root / 'inbox.txt'
        raw.write_bytes(b'video.example.com\n')
        with self.assertRaisesRegex(PostDropRefused, 'nonempty_or_changed_original_pretraffic_inode'):
            self.capture()
        self.assertEqual(raw.read_bytes(), b'video.example.com\n')

    def test_pretraffic_rejects_existing_debug_without_truncation(self):
        debug = self.root / 'debug.log'
        debug.write_bytes(b'old-generation event\n')
        with self.assertRaisesRegex(PostDropRefused, 'nonempty_or_changed_original_pretraffic_inode'):
            self.capture()
        self.assertEqual(debug.read_bytes(), b'old-generation event\n')

    def test_pretraffic_rejects_unacknowledged_original_pending(self):
        old = self.root / 'pending' / ('f' * 32 + '-' + 'e' * 32 + '.txt')
        old.write_bytes(b'blocked.example.com\n')
        old.chmod(0o660)
        with self.assertRaisesRegex(PostDropRefused, 'unprocessed_original_pending_prelaunch'):
            self.capture()
        self.assertEqual(old.read_bytes(), b'blocked.example.com\n')

    def test_pretraffic_rejects_foreign_pending_without_deletion(self):
        bad = self.root / 'pending' / 'untrusted.tmp'
        bad.write_bytes(b'unknown\n')
        with self.assertRaisesRegex(PostDropRefused, 'original_pretraffic_queue_or_inode_unavailable'):
            self.capture()
        self.assertEqual(bad.read_bytes(), b'unknown\n')

    def test_original_queue_new_lock_is_private_and_group_exact(self):
        stamp = self.capture()
        path = self.root / 'worker.lock'
        lock = path.lstat()
        self.assertEqual(lock.st_uid, self.owner)
        self.assertEqual(lock.st_gid, (self.root / 'pending').lstat().st_gid)
        self.assertEqual(stat.S_IMODE(lock.st_mode), 0o600)
        self.assertEqual(self.capture().identities, stamp.identities)
        self.assertEqual(path.lstat().st_ino, lock.st_ino)

    def test_pretraffic_respects_original_queue_busy_without_second_owner(self):
        witness = self.capture()
        original_lock = self.root / 'worker.lock'
        self.assertTrue(original_lock.is_file())
        fd = os.open(original_lock, os.O_RDWR | os.O_NOFOLLOW)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(PostDropRefused, 'original_pretraffic_queue_or_inode_unavailable'):
                self.capture()
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
        self.assertEqual(self.capture().identities, witness.identities)

    def test_bound_learning_capture_borrows_exact_original_queue(self):
        name = "learning-" + "a" * 32 + "-3.txt"
        path = self.root / name
        path.write_bytes(b"")
        path.chmod(0o660)
        def capture(fd=None):
            return _capture(self.root, root_uid=self.owner, root_gid=self.gid,
                engine_uid=self.engine, engine_gid=self.gid,
                learning_names=(name,), queue_fd=fd)
        queue = DurableInbox(self.root, owner_uid=self.owner, writer_gid=self.gid)
        baseline = capture()
        with queue.exclusive(existing_only=True):
            fd = queue.locked_fd
            self.assertEqual(capture(fd), baseline)
            duplicate = os.dup(fd)
            try:
                self.assertEqual(capture(duplicate), baseline)
            finally:
                os.close(duplicate)
            foreign = os.open(queue.lock, os.O_RDWR | os.O_NOFOLLOW)
            try:
                with self.assertRaises(PostDropRefused):
                    capture(foreign)
                # Neither rejected descriptor nor borrowed-child exit releases
                # the original owner's actual flock.
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(foreign, fcntl.LOCK_EX | fcntl.LOCK_NB)
            finally:
                os.close(foreign)
            with self.assertRaises(PostDropRefused):
                capture()  # a second acquisition is forbidden
            path.write_bytes(b"unexpected.example\n")
            with self.assertRaises(PostDropRefused):
                capture(fd)
            self.assertEqual(path.read_bytes(), b"unexpected.example\n")
            path.write_bytes(b"")
            self.assertEqual(capture(fd), baseline)
        unlocked = os.open(queue.lock, os.O_RDWR | os.O_NOFOLLOW)
        try:
            with self.assertRaises(PostDropRefused):
                capture(unlocked)
        finally:
            os.close(unlocked)
        self.assertEqual(capture(), baseline)

    def test_first_bound_learning_owner_scope_requires_original_queue(self):
        from auto_detect_post_drop import _learning_pretraffic_owner
        from shared_apply_seal import WORK
        generation, candidate = "a" * 32, "b" * 64
        record = {"phase": "activating", "detail": {"id": generation,
                    "candidate": candidate}, "manifest": {"schema": 2}}
        workspace = WORK / generation
        # Only native identity and the original root/WAL reads are isolated.
        # Real OFD acceptance/refusal is exercised by the preceding test.
        with (patch("auto_detect_post_drop.sys.platform", "freebsd"),
              patch("auto_detect_post_drop.os.geteuid", return_value=0),
              patch("voice_ipfw_adapter.require_lifecycle_lock"),
              patch("shared_apply_operation.SharedApplyOperation") as factory,
              patch("neutral_root_stage.verify_original_operation_pins") as verify):
            store = factory.return_value
            store.read.return_value = record
            self.assertEqual(_learning_pretraffic_owner(workspace, candidate, 3), record)
            verify.assert_called_once_with(record=record, parent=WORK, owner_uid=0)
            for fd in (None, 4, 9, -1, True):
                with self.subTest(fd=fd), self.assertRaises(PostDropRefused):
                    _learning_pretraffic_owner(workspace, candidate, fd)
            with self.assertRaises(PostDropRefused):
                _learning_pretraffic_owner(workspace, "c" * 64, 3)
            with self.assertRaises(PostDropRefused):
                _learning_pretraffic_owner(WORK / ("c" * 32), candidate, 3)
            for wrong in ({**record, "phase": "prepared"},
                          {**record, "previous": {}},
                          {**record, "found": {}},
                          {**record, "manifest": {"schema": 1}}):
                store.read.return_value = wrong
                with self.assertRaises(PostDropRefused):
                    _learning_pretraffic_owner(workspace, candidate, 3)
            store.read.return_value = None
            self.assertIsNone(_learning_pretraffic_owner(workspace, candidate, None))
            with self.assertRaises(PostDropRefused):
                _learning_pretraffic_owner(workspace, candidate, 3)
            store.read.side_effect = [record, {**record, "phase": "activated"}]
            with self.assertRaises(PostDropRefused):
                _learning_pretraffic_owner(workspace, candidate, 3)

    def test_pretraffic_does_not_reject_native_append_after_start(self):
        # The original prelaunch witness stays valid after raw/debug append.
        # It is NOT permission to seed an epoch after traffic started.
        witness = self.capture()
        (self.root / 'inbox.txt').write_bytes(b'discovery.example.com\n')
        (self.root / 'debug.log').write_bytes(b'native adding event\n')
        self.assertEqual(_reattest(witness, lambda: True), ())
        with self.assertRaises(PostDropRefused):
            self.capture()

    def test_original_fd9_witness_token_and_malformed_refusal(self):
        # Pure envelope serialization; actual original root/FD9 identity is
        # covered by the exact real FreeBSD-native P2i packet scenario.
        line = _witness_line(self.capture())
        self.assertRegex(line, r"^p2k8i:(?:[0-9]+:){5}[0-9]+$")
        for bad in ("", "p2k8i:", "p2k8i:0:0:0:0:0:0",
                    "p2k8i:0:0:1:0:0:2", "p2k8i:0:0:1:0:0:1;touch /tmp/x",
                    "p2k8i:" + "9" * 90):
            with self.subTest(bad=bad[:30]):
                with self.assertRaisesRegex(PostDropRefused,
                                            "invalid_original_fd9_prelaunch_witness"):
                    _witness_read(bad)

    def test_original_fd9_cli_rejects_off_target(self):
        if sys.platform.startswith("freebsd"):
            self.skipTest("real original held FD9 is in disposable native P2i")
        self.assertEqual(original_fd9_command(["capture"]), 64)
        self.assertEqual(original_fd9_command(["restore", "x", "2", "/tmp/dvtws2"]), 64)
        self.assertEqual(original_fd9_command(["authorize", "/tmp/test"]), 64)

    def test_native_real_fd9_entry_refuses_on_non_freebsd(self):
        if sys.platform.startswith('freebsd'):
            self.skipTest("real native coverage is in the single P2i disposable VM")
        with self.assertRaisesRegex(PostDropRefused, "native_root_fd9_only"):
            native_capture_before_launch()


if __name__ == '__main__':
    unittest.main(verbosity=2)
