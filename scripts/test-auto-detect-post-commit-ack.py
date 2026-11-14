#!/usr/bin/env python3
"""P2k8k: durable destination/intent/child-result plus native drain before ACK.

Uses real P2a/P2k2a/P2k2b filesystem fixtures. Only the attester/FD probe
are injected: a synthetic owner is never production authorization.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest

BACKEND = Path(__file__).resolve().parents[1] / 'src/opnsense/scripts/OPNsense/Zapret/backend'
sys.path.insert(0, str(BACKEND))
from auto_detect_fd import FDState
from auto_detect_post_commit_ack import (PostCommitRefused,
                                         acknowledge_current_checkpoint, main)

SOURCE = Path(__file__).with_name('test-auto-detect-destination-commit.py')
spec = importlib.util.spec_from_file_location('destination_real_fixture', SOURCE)
assert spec is not None and spec.loader is not None
fixture_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture_module)


class PostCommitAckTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture_module.CommitTests('test_physical_multi_target_checkpoint_and_replay')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.f = self.fixture
        self.calls = []

    def attest(self):
        return self.f.proof

    def drained(self, path, dev, ino, *, owner, writer_gid):
        self.calls.append((path, dev, ino))
        return FDState.DRAINED

    def commit_and_ack(self, *, result=None, attest=None, inspect=None):
        with self.f.queue.exclusive():
            committed = self.f.writer.commit(self.f.proof, self.f.segment, self.f.effects)
            return acknowledge_current_checkpoint(
                self.f.writer, self.f.segment, result if result is not None else committed,
                attest=attest or self.attest, inspect=inspect or self.drained)

    def test_full_real_journal_and_native_fd_gate_ack_only_one_inode(self):
        self.assertTrue(self.commit_and_ack())
        self.assertEqual(len(self.calls), 1)
        self.assertFalse(self.f.segment.exists())
        self.assertIn('example.com\n', self.f.auto.read_text())
        self.assertIn('sample.com\n', self.f.youtube.read_text())

    def test_missing_checkpoint_never_acks_even_if_child_says_success(self):
        with self.f.queue.exclusive():
            with self.assertRaises(PostCommitRefused):
                acknowledge_current_checkpoint(self.f.writer, self.f.segment,
                                               {'kind':'destination-and-cursor-committed',
                                                'ack_authorized':False},
                                               attest=self.attest, inspect=self.drained)
        self.assertTrue(self.f.segment.exists())

    def test_fd_busy_keeps_original_pending(self):
        self.assertFalse(self.commit_and_ack(inspect=lambda *a, **kw: FDState.BUSY))
        self.assertTrue(self.f.segment.exists())

    def test_unknown_fd_keeps_original_pending(self):
        self.assertFalse(self.commit_and_ack(inspect=lambda *a, **kw: FDState.UNKNOWN))
        self.assertTrue(self.f.segment.exists())

    def test_original_engine_change_after_commit_keeps_pending(self):
        from dataclasses import replace
        calls = [0]
        def swapped():
            calls[0] += 1
            return self.f.proof if calls[0] == 1 else replace(self.f.proof, generation='e'*32)
        self.assertFalse(self.commit_and_ack(attest=swapped))
        self.assertTrue(self.f.segment.exists())

    def test_wrong_child_completion_is_never_ack_authority(self):
        with self.assertRaises(PostCommitRefused):
            self.commit_and_ack(result={'kind':'destination-and-cursor-committed',
                                        'ack_authorized':False})
        self.assertTrue(self.f.segment.exists())

    def test_corrupted_checkpoint_preserves_pending(self):
        with self.f.queue.exclusive():
            response = self.f.writer.commit(self.f.proof, self.f.segment, self.f.effects)
            cp = self.f.receipts.root / self.f.proof.generation / 'destination' / 'checkpoint.json'
            doc = json.loads(cp.read_text())
            doc['committed_cursor_offset'] += 1
            cp.write_text(json.dumps(doc))
            with self.assertRaises(PostCommitRefused):
                acknowledge_current_checkpoint(self.f.writer, self.f.segment, response,
                                               attest=self.attest, inspect=self.drained)
        self.assertTrue(self.f.segment.exists())

    def test_changed_pending_inode_refuses_even_with_checkpoint(self):
        with self.f.queue.exclusive():
            response = self.f.writer.commit(self.f.proof, self.f.segment, self.f.effects)
            self.f.segment.unlink()
            self.f.segment.write_text('new.example\n')
            self.f.segment.chmod(0o600)
            with self.assertRaises(PostCommitRefused):
                acknowledge_current_checkpoint(self.f.writer, self.f.segment, response,
                                               attest=self.attest, inspect=self.drained)
        self.assertTrue(self.f.segment.exists())

    def test_manual_delete_after_durable_commit_is_not_reverted_by_ack(self):
        with self.f.queue.exclusive():
            response = self.f.writer.commit(self.f.proof, self.f.segment, self.f.effects)
            self.f.auto.write_text('!manual.invalid\n')
            self.assertTrue(acknowledge_current_checkpoint(self.f.writer, self.f.segment,
                         response, attest=self.attest, inspect=self.drained))
        self.assertEqual(self.f.auto.read_text(), '!manual.invalid\n')

    def test_original_queue_owner_required(self):
        with self.assertRaises(PostCommitRefused):
            acknowledge_current_checkpoint(self.f.writer, self.f.segment, {},
                                           attest=self.attest, inspect=self.drained)
        self.assertTrue(self.f.segment.exists())

    def test_no_direct_production_cli(self):
        with self.assertRaisesRegex(PostCommitRefused, 'not_enabled'):
            main()
        self.assertTrue(self.f.segment.exists())


if __name__ == '__main__':
    unittest.main()
