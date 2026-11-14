#!/usr/bin/env python3
"""P2k8h: original protected inode pre/post-drop refusal before IPFW.

No native service, Model, dvtws2, IPFW or scheduler changes. The existing
single disposable P2i VM covers actual dropped-credential fchown.
"""
from __future__ import annotations
import fcntl
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
