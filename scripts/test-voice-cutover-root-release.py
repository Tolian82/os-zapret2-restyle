#!/usr/bin/env python3
"""Write-ahead release of the empty Voice quarantine root; crash replay."""
from __future__ import annotations

import fcntl
import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))
from voice_cutover_root_release import (
    NAME, RootReleaseError, read_root_release_intent, release_quarantined_root,
)
from voice_native_boot_recovery_review import inspect_boot_recovery


def fixture(name,alias):
    spec=importlib.util.spec_from_file_location(alias,ROOT/"scripts"/name)
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prune_fixture=fixture("test-voice-cutover-prune.py","root_release_prune_fixture")


class RootReleaseTests(unittest.TestCase):
    def setUp(self):
        self.fx=prune_fixture.CandidatePruneTests()
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.fx.prune()
        self.held=self.fx.held
        self.terminal=self.fx.terminal
        self.journal=self.fx.whole
        self.private=self.journal.directory

    def call(self,fn,lock=True):
        fd=os.open(self.fx.fx.config,os.O_RDWR)
        try:
            if lock:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return fn(**self.fx.fixture._kwargs(fd))
        finally:
            os.close(fd)

    def release(self,lock=True):
        return self.call(release_quarantined_root,lock)

    def review(self):
        return self.call(inspect_boot_recovery)

    def assert_old_evidence_retained(self):
        self.assertEqual(self.terminal,self.journal.read())
        self.assertTrue(self.fx.fx.live.is_dir())
        self.assertTrue(self.fx.fx.image.is_dir())
        self.assertTrue(self.fx.fx.fx.backup.is_dir())
        self.assertIsNotNone(self.fx.fx.fx.ipfw.owned())
        for file in (
            "previous-rollback-receipt.json","previous-cleanup-plan.json",
            "runtime-restore-redo.json","previous-reclaim-intent.json",
            "previous-prune-intent.json","previous-root-release-intent.json",
        ):
            self.assertTrue((self.private/file).is_file(),file)

    def test_release_empty_quarantine_durably_and_idempotently(self):
        self.assertEqual([],list(self.held.iterdir()))
        report=self.release()
        self.assertEqual("candidate-root-released-awaiting-finalization",report["state"])
        self.assertIs(report["safe_to_close_intent"],False)
        self.assertIs(report["voice_on"],False)
        self.assertFalse(self.held.exists())
        self.assertEqual(report["state"],self.review()["candidate_reclaim"])
        self.assertEqual(report["state"],self.release()["state"])
        self.assertEqual(0o600,(self.private/NAME).stat().st_mode&0o777)
        self.assert_old_evidence_retained()

    def test_crash_after_fsync_write_ahead_before_rmdir(self):
        with patch("voice_cutover_root_release._durable_rmdir",
                   side_effect=OSError("simulated power loss before rmdir")):
            with self.assertRaises(OSError):
                self.release()
        marker=read_root_release_intent(self.private)
        self.assertIsNotNone(marker)
        self.assertTrue(self.held.is_dir())
        self.assertEqual("candidate-root-release-armed",self.review()["candidate_reclaim"])
        self.assertEqual("candidate-root-released-awaiting-finalization",
                         self.release()["state"])
        self.assertEqual(marker,read_root_release_intent(self.private))
        self.assert_old_evidence_retained()

    def test_crash_after_rmdir_before_parent_fsync(self):
        from voice_cutover_root_release import _durable_rmdir
        def interrupted(fd,name):
            os.rmdir(name,dir_fd=fd)
            raise OSError("simulated crash after rmdir")
        with patch("voice_cutover_root_release._durable_rmdir",side_effect=interrupted):
            with self.assertRaises(OSError):
                self.release()
        self.assertFalse(self.held.exists())
        self.assertEqual("candidate-root-released-awaiting-finalization",
                         self.review()["candidate_reclaim"])
        self.assertEqual("candidate-root-released-awaiting-finalization",
                         self.release()["state"])
        self.assert_old_evidence_retained()

    def test_unknown_entry_never_rmdir_or_write_release_marker(self):
        foreign=self.held/"unexpected"
        foreign.write_text("do not remove")
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.release()
        self.assertIsNone(read_root_release_intent(self.private))
        self.assertEqual("do not remove",foreign.read_text())
        self.assertEqual(self.terminal,self.journal.read())

    def test_root_replacement_refused_even_when_empty(self):
        prior=self.held.with_name(self.held.name+"-saved")
        self.held.rename(prior)
        self.held.mkdir(mode=0o700)
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.release()
        self.assertIsNone(read_root_release_intent(self.private))
        self.assertTrue(self.held.is_dir())
        self.assertTrue(prior.is_dir())
        self.assertEqual(self.terminal,self.journal.read())

    def test_missing_lock_or_reset_kernel_refuses(self):
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.release(lock=False)
        self.assertIsNone(read_root_release_intent(self.private))
        kernel=self.fx.fx.kernel
        kernel.rules[19000]=prune_fixture.reclaim_fixture.fixtures.receipt_tests.kernel_fixture.TCP
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.release()
        self.assertIsNone(read_root_release_intent(self.private))
        self.assertTrue(self.held.is_dir())

    def test_corrupted_release_marker_blocks_recovery(self):
        marker=self.private/NAME
        marker.write_text('{"phase":"foreign"}')
        marker.chmod(0o600)
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.release()
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.review()
        self.assertTrue(self.held.is_dir())


if __name__=="__main__":
    unittest.main(verbosity=2)
