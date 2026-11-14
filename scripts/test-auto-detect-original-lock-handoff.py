#!/usr/bin/env python3
"""P2k8f: original queue lock -> actual PHP Config flock -> child Python FD.

Portable real-process test of the unchanged open-file descriptions; synthetic
model/owner evidence is NOT installed OPNsense/FD9 acceptance.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

BACKEND = Path(__file__).resolve().parents[1] / 'src/opnsense/scripts/OPNsense/Zapret/backend'
sys.path.insert(0, str(BACKEND))
from auto_detect_queue import DurableInbox, QueueSafetyError
from auto_detect_original_lock_handoff import (
    OriginalLockRefused, assert_inherited_config_fd,
    inherited_original_locks, _original_completion_locked,
)

PHP_FIXTURE = Path(__file__).with_suffix('.php')


def probe_main(argv: list[str]) -> int:
    if len(argv) != 2:
        return 64
    root, config = map(Path, argv)
    stage = 'payload'
    try:
        payload = json.loads(sys.stdin.read(3 * 1048576 + 1))
        if (not isinstance(payload, dict) or
                set(payload) != {'manual_hostlists', 'global_exclude',
                                 'config_snapshot_sha256'} or
                set(payload['manual_hostlists']) != {'youtube', 'user'} or
                len(payload['config_snapshot_sha256']) != 64):
            return 65
        stage = 'original-inherited-locks'
        queue = DurableInbox(root, owner_uid=os.geteuid())
        with inherited_original_locks(queue, 3, 4, config, owner_uid=os.geteuid()):
            stage = 'native-model-assertion'
            assert queue._held and queue.locked_fd == 3
            assert payload['manual_hostlists']['youtube'] == 'youtube.com\n'
            assert payload['global_exclude'] == '!blocked.example\n'
            # P2k8g: optional disposable-native parent-death witness.
            # The grandchild reports its PID after both real inherited kernel
            # locks have been validated and holds them until the test releases.
            stage = 'child-hold'
            ready = os.environ.get('P2K8G_HOLD_READY')
            release = os.environ.get('P2K8G_HOLD_RELEASE')
            if ready or release:
                if (not ready or not release or
                        Path(ready).parent != Path(release).parent or
                        not Path(ready).parent.is_dir()):
                    return 69
                Path(ready).write_text(str(os.getpid()))
                for _ in range(200):
                    if Path(release).is_file():
                        break
                    time.sleep(0.05)
                else:
                    return 69
            # This fixture does not write destinations or ACK.
            print(json.dumps({'kind': 'destination-and-cursor-committed',
                              'ack_authorized': False}))
        return 0
    except (OriginalLockRefused, QueueSafetyError, KeyError, ValueError,
            AssertionError, OSError, TypeError) as exc:
        # Only private disposable-test diagnostics, never raw Config,
        # pending domains, Python argv or stderr of a real service.
        diagnostic = os.environ.get('P2K8G_CHILD_DIAG')
        if diagnostic:
            reason = str(exc)
            if not re.fullmatch(r'[a-z_]{1,100}', reason):
                reason = 'refused'
            try:
                Path(diagnostic).write_text(
                    f'{stage}:{type(exc).__name__}:{reason}\n')
            except OSError:
                pass
        return 69


class OriginalLockHandoffTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='p2k8f-')
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.base.chmod(0o700)
        self.producer = self.base / 'producer'
        self.producer.mkdir(mode=0o700)
        (self.producer / 'pending').mkdir(mode=0o700)
        self.config_dir = self.base / 'conf'
        self.config_dir.mkdir(mode=0o700)
        self.config = self.config_dir / 'config.xml'
        self.config.write_text('<opnsense/>')
        self.config.chmod(0o600)
        self.queue = DurableInbox(self.producer, owner_uid=os.geteuid())
        inbox = self.producer / 'inbox.txt'
        inbox.write_text('')
        inbox.chmod(0o600)
        self.segment = self.queue.pending / ('a'*32 + '-' + 'c'*32 + '.txt')
        self.segment.write_text('video.example.co.uk\n')
        self.segment.chmod(0o600)

    def environment(self, *, unlocked_config=False):
        return {**os.environ, 'P2K8F_PYTHON': sys.executable,
                'P2K8F_TEST_SCRIPT': str(Path(__file__).resolve()),
                'P2K8F_QUEUE_PATH': str(self.queue.lock),
                'P2K8F_QUEUE_ROOT': str(self.producer),
                'P2K8F_CONFIG_PATH': str(self.config),
                'P2K8F_UNLOCKED_CONFIG': '1' if unlocked_config else '0'}

    def invoke(self, fd, *, unlocked_config=False):
        return subprocess.run(
            ['php', str(PHP_FIXTURE), 'commit-with-fds', str(fd), self.segment.name],
            pass_fds=(fd,), env=self.environment(unlocked_config=unlocked_config),
            capture_output=True, text=True, timeout=15)

    def test_actual_three_process_handoff_and_retained_pending(self):
        # The same original queue FD stays open across two exec boundaries,
        # while the Config FD remains held during the P1 child transaction.
        with self.queue.exclusive():
            fd = self.queue.locked_fd
            result = self.invoke(fd)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(json.loads(result.stdout)['ack_authorized'])
            self.assertEqual(self.queue.locked_fd, fd)
            self.assertTrue(self.segment.exists())
        self.assertTrue(self.segment.exists())
        self.assertFalse(self.queue._held)

    def test_whole_original_queue_owner_function_not_a_new_daemon(self):
        # This invokes the production outer queue owner helper; no native
        # observer and no cron/configd enrollment is implied by the fixture.
        from unittest.mock import patch
        with patch.dict(os.environ, self.environment()):
            with self.queue.exclusive():
                result = _original_completion_locked(
                    self.queue, self.segment, php_bin='php',
                    php_script=PHP_FIXTURE, timeout=15)
        self.assertFalse(result['ack_authorized'])
        self.assertTrue(self.segment.exists())

    def test_unlocked_or_foreign_queue_fd_refuses(self):
        fd = os.open(self.queue.lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            result = self.invoke(fd)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(self.segment.exists())
        finally:
            os.close(fd)
        unrelated = self.base / 'unrelated.lock'
        unrelated.write_text('')
        unrelated.chmod(0o600)
        fd = os.open(unrelated, os.O_RDWR)
        try:
            with self.queue.exclusive():
                result = self.invoke(fd)
                self.assertNotEqual(result.returncode, 0)
        finally:
            os.close(fd)
        self.assertTrue(self.segment.exists())

    def test_config_save_style_early_unlock_refuses_without_ack(self):
        with self.queue.exclusive():
            result = self.invoke(self.queue.locked_fd, unlocked_config=True)
            self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.segment.exists())

    def test_config_wrong_inode_and_unlocked_are_not_lock_proof(self):
        with self.queue.exclusive():
            with self.assertRaises(OriginalLockRefused):
                assert_inherited_config_fd(self.queue.locked_fd, self.config,
                                            owner_uid=os.geteuid())
        with open(self.config, 'rb') as unlocked:
            with self.assertRaisesRegex(OriginalLockRefused, 'unlocked'):
                assert_inherited_config_fd(unlocked.fileno(), self.config,
                                            owner_uid=os.geteuid())

    def test_dynamic_native_config_uid_restricted_to_original_path(self):
        with open(self.config, 'rb') as fake:
            with self.assertRaisesRegex(OriginalLockRefused, 'invalid_original_config_fd'):
                assert_inherited_config_fd(fake.fileno(), self.config,
                                            owner_uid=None)
        self.assertTrue(self.segment.exists())

    def test_native_writer_cli_is_restricted_and_never_accepts_fake_origin(self):
        from auto_detect_original_lock_handoff import main
        self.assertEqual(main([]), 64)
        self.assertEqual(main(['commit-fds','anything']), 64)
        self.assertTrue(self.segment.exists())

    def test_only_current_v2_native_composer_is_disabled_off_platform(self):
        from auto_detect_original_lock_handoff import run_native_original_v2_cycle_once
        with self.assertRaisesRegex(OriginalLockRefused, 'original_native_fd9_required'):
            run_native_original_v2_cycle_once()
        self.assertTrue(self.segment.exists())


if __name__ == '__main__':
    if len(sys.argv) >= 2 and sys.argv[1] == '--child-probe':
        raise SystemExit(probe_main(sys.argv[2:]))
    unittest.main()
