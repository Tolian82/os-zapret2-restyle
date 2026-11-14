#!/usr/bin/env python3
"""#1052 P2k8l original held-queue lifetime through Config completion and ACK.

Physical P2k2b files and the actual queue flock are exercised. Only the
original PHP child return and current P2c/FD observations are injected; real
three-process Config FD qualification remains in the P2k8f/P2k8g tests.
"""
from __future__ import annotations

import fcntl
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

BACKEND = Path(__file__).resolve().parents[1] / 'src/opnsense/scripts/OPNsense/Zapret/backend'
sys.path.insert(0, str(BACKEND))
import auto_detect_original_lock_handoff as original
from auto_detect_fd import FDState
from auto_detect_queue import DurableInbox
from auto_detect_destination_commit import DestinationCommit
from auto_detect_original_lock_handoff import OriginalLockRefused

SOURCE = Path(__file__).with_name('test-auto-detect-destination-commit.py')
spec = importlib.util.spec_from_file_location('destination_physical_fixture_p2k8l', SOURCE)
assert spec and spec.loader
physical = importlib.util.module_from_spec(spec)
spec.loader.exec_module(physical)


class OriginalQueueAckTests(unittest.TestCase):
    def setUp(self):
        self.fixture = physical.CommitTests('test_physical_multi_target_checkpoint_and_replay')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.f = self.fixture
        self.invocations = 0
        self.fd_observations = 0

    def attest(self):
        return self.f.proof

    def inspect(self, path, dev, ino, *, owner, writer_gid):
        self.fd_observations += 1
        self.assertEqual(path, self.f.segment)
        self.assertEqual(owner, self.f.proof.owner)
        self.assertEqual((dev, ino),
                         (self.f.segment.stat().st_dev, self.f.segment.stat().st_ino))
        return FDState.DRAINED

    def original_child(self, cmd, **kwargs):
        self.invocations += 1
        self.assertTrue(self.f.queue._held)
        self.assertEqual(kwargs['pass_fds'], (self.f.queue.locked_fd,))
        self.assertEqual(cmd[-1], self.f.segment.name)
        self.assertEqual(cmd[-2], str(self.f.queue.locked_fd))
        self.assertEqual(cmd[2], 'commit-with-fds')
        self.assertTrue(kwargs['close_fds'])
        self.assertEqual(kwargs['timeout'], 15)
        # An independent original queue-file open description cannot compete,
        # including while destination files are actually being committed.
        other = os.open(self.f.queue.lock, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            with self.assertRaises(BlockingIOError):
                fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(other)
        checkpoint = self.f.writer.commit(self.f.proof, self.f.segment, self.f.effects)
        return subprocess.CompletedProcess(cmd, 0, json.dumps(checkpoint).encode())

    def run_locked(self, *, child=None, attest=None, inspect=None,
                   pending=None, writer=None):
        with self.f.queue.exclusive():
            with patch.object(original.subprocess, 'run',
                              side_effect=child or self.original_child):
                return original._original_commit_then_ack_locked(
                    self.f.queue, pending or self.f.segment, writer or self.f.writer,
                    php_bin='/usr/local/bin/php',
                    php_script=Path('/test/original-config.php'), timeout=15,
                    attest=attest or self.attest, inspect=inspect or self.inspect)

    def test_real_file_commit_and_ack_in_one_original_queue_lock(self):
        self.assertTrue(self.run_locked())
        self.assertEqual(self.invocations, 1)
        self.assertEqual(self.fd_observations, 1)
        self.assertFalse(self.f.segment.exists())
        self.assertIn('example.com\n', self.f.auto.read_text())
        self.assertIn('sample.com\n', self.f.youtube.read_text())
        self.assertFalse(self.f.queue._held)

    def test_busy_fd_keeps_pending_and_retry_does_not_restore_gui_deletion(self):
        self.assertFalse(self.run_locked(inspect=lambda *args, **kwargs: FDState.BUSY))
        self.assertTrue(self.f.segment.exists())
        self.assertEqual(self.f.auto.read_text().count('example.com'), 1)
        self.f.auto.write_text('!manual.invalid\n')
        self.assertTrue(self.run_locked())
        self.assertFalse(self.f.segment.exists())
        self.assertEqual(self.f.auto.read_text(), '!manual.invalid\n')
        self.assertEqual(self.invocations, 2)

    def test_unknown_fd_is_not_a_durable_ack(self):
        self.assertFalse(self.run_locked(inspect=lambda *args, **kwargs: FDState.UNKNOWN))
        self.assertTrue(self.f.segment.exists())

    def test_changed_original_generation_after_php_child_keeps_pending(self):
        from dataclasses import replace
        calls = [0]
        def changed():
            calls[0] += 1
            return self.f.proof if calls[0] == 1 else replace(self.f.proof, generation='e'*32)
        with self.assertRaisesRegex(OriginalLockRefused, 'owner_changed'):
            self.run_locked(attest=changed)
        self.assertTrue(self.f.segment.exists())
        self.assertEqual(self.invocations, 1)

    def test_wrong_generation_pending_is_rejected_before_php(self):
        foreign = self.f.queue.pending / ('e'*32 + '-' + 'b'*32 + '.txt')
        foreign.write_text('foreign.invalid\n')
        foreign.chmod(0o600)
        with self.assertRaisesRegex(OriginalLockRefused, 'current_original_generation'):
            self.run_locked(pending=foreign)
        self.assertEqual(self.invocations, 0)
        self.assertTrue(foreign.exists())
        self.assertTrue(self.f.segment.exists())

    def test_false_php_completion_cannot_delete_committed_pending(self):
        def fake(cmd, **kwargs):
            actual = self.original_child(cmd, **kwargs)
            return subprocess.CompletedProcess(cmd, 0, b'{"kind":"destination-and-cursor-committed","ack_authorized":false}')
        from auto_detect_post_commit_ack import PostCommitRefused
        with self.assertRaisesRegex(PostCommitRefused, 'mismatch'):
            self.run_locked(child=fake)
        self.assertTrue(self.f.segment.exists())

    def test_child_refusal_preserves_pending_without_ack(self):
        def refused(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 69, b'')
        with self.assertRaisesRegex(OriginalLockRefused, 'child_refused'):
            self.run_locked(child=refused)
        self.assertTrue(self.f.segment.exists())

    def test_child_timeout_preserves_pending(self):
        def expired(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd, 15)
        with self.assertRaisesRegex(OriginalLockRefused, 'owner_unavailable'):
            self.run_locked(child=expired)
        self.assertTrue(self.f.segment.exists())

    def test_no_second_queue_owner_and_wrong_writer_refused(self):
        with self.assertRaisesRegex(OriginalLockRefused, 'original_locked_queue'):
            original._original_commit_then_ack_locked(
                self.f.queue, self.f.segment, self.f.writer,
                php_bin='/usr/local/bin/php',
                php_script=Path('/test/original-config.php'), timeout=15,
                attest=self.attest, inspect=self.inspect)
        other = DurableInbox(self.f.producer, owner_uid=os.geteuid())
        incompatible = DestinationCommit(self.f.receipts, other,
                                         self.f.writer.targets, self.f.lock)
        with self.assertRaisesRegex(OriginalLockRefused, 'original_locked_queue'):
            self.run_locked(writer=incompatible)
        self.assertTrue(self.f.segment.exists())

    def test_off_native_public_worker_cannot_be_invoked(self):
        with self.assertRaisesRegex(OriginalLockRefused, 'original_native_generation'):
            original.run_native_original_pending_ack_once(self.f.segment.name)
        self.assertTrue(self.f.segment.exists())


if __name__ == '__main__':
    unittest.main()
