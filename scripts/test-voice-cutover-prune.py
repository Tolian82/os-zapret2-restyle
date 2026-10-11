#!/usr/bin/env python3
"""Candidate-only Voice prune: durable per-inode inventory and crash resume."""
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
from voice_cutover_prune import (
    PruneError, read_prune_intent, prune_quarantined_candidate, NAME,
)
from voice_native_boot_recovery_review import inspect_boot_recovery


def fixture(path,alias):
    spec=importlib.util.spec_from_file_location(alias,ROOT/"scripts"/path)
    assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


reclaim_fixture=fixture("test-voice-cutover-reclaim.py","prune_quarantine_fixture")


class CandidatePruneTests(unittest.TestCase):
    def setUp(self):
        self.fixture=reclaim_fixture.RetiredCandidateQuarantineTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.stage()
        self.fx=self.fixture.fx
        self.whole=self.fixture.whole
        self.held=self.fixture.held
        self.terminal=self.whole.read()
        self.original=self.held.joinpath("dvtws.args").read_bytes()

    def run_with_lock(self, func, *, lock=True):
        fd=os.open(self.fx.config,os.O_RDWR)
        try:
            if lock:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return func(**self.fixture._kwargs(fd))
        finally:
            os.close(fd)

    def prune(self,lock=True):
        return self.run_with_lock(prune_quarantined_candidate,lock=lock)

    def review(self):
        return self.run_with_lock(inspect_boot_recovery)

    def check_preserved(self):
        self.assertEqual(self.terminal,self.whole.read())
        self.assertTrue(self.held.is_dir())
        self.assertTrue(self.fx.image.is_dir())
        self.assertTrue(self.fx.live.is_dir())
        self.assertTrue(self.fx.fx.backup.is_dir())
        self.assertIsNotNone(self.fx.fx.ipfw.owned())
        for name in ("previous-rollback-receipt.json","previous-cleanup-plan.json",
                     "runtime-restore-redo.json","previous-reclaim-intent.json",
                     "previous-prune-intent.json"):
            self.assertTrue((self.whole.directory/name).is_file(),name)

    def test_actual_prune_preserves_active_previous_and_resumes_noop(self):
        report=self.prune()
        self.assertEqual("candidate-pruned-retained-root",report["state"])
        self.assertIs(report["voice_on"],False)
        self.assertIs(report["safe_to_close_intent"],False)
        self.assertEqual([],list(self.held.iterdir()))
        marker=read_prune_intent(self.whole.directory)
        self.assertEqual("prune-write-ahead",marker["phase"])
        self.assertEqual(0o600,(self.whole.directory/NAME).stat().st_mode&0o777)
        self.assertEqual("candidate-pruned-retained-root",self.review()["candidate_reclaim"])
        self.assertEqual("candidate-pruned-retained-root",self.prune()["state"])
        self.check_preserved()

    def test_crash_after_marker_before_first_unlink(self):
        with patch("voice_cutover_prune.os.unlink",side_effect=OSError("crash")):
            with self.assertRaises(OSError):
                self.prune()
        marker=read_prune_intent(self.whole.directory)
        self.assertIsNotNone(marker)
        self.assertEqual(self.original,self.held.joinpath("dvtws.args").read_bytes())
        self.assertEqual("candidate-prune-interrupted",self.review()["candidate_reclaim"])
        self.assertEqual("candidate-pruned-retained-root",self.prune()["state"])
        self.assertEqual(marker,read_prune_intent(self.whole.directory))
        self.check_preserved()

    def test_crash_after_unlink_before_completion_is_recoverable(self):
        import voice_cutover_prune as impl
        original=impl._remove_pinned_entry
        def after_remove(*args,**kwargs):
            original(*args,**kwargs)
            raise OSError("crash after unlink")
        with patch.object(impl,"_remove_pinned_entry",side_effect=after_remove):
            with self.assertRaises(OSError):
                self.prune()
        self.assertEqual([],list(self.held.iterdir()))
        self.assertEqual("candidate-pruned-retained-root",self.review()["candidate_reclaim"])
        self.assertEqual("candidate-pruned-retained-root",self.prune()["state"])
        self.check_preserved()

    def test_foreign_candidate_after_interrupted_prune_is_never_deleted(self):
        with patch("voice_cutover_prune.os.unlink",side_effect=OSError("crash")):
            with self.assertRaises(OSError):
                self.prune()
        foreign=self.held/"not-ours"
        foreign.write_text("untouched")
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.review()
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.prune()
        self.assertEqual("untouched",foreign.read_text())
        self.assertEqual(self.original,self.held.joinpath("dvtws.args").read_bytes())

    def test_corrupt_inventory_or_changed_inode_blocks_replay(self):
        with patch("voice_cutover_prune.os.unlink",side_effect=OSError("crash")):
            with self.assertRaises(OSError):
                self.prune()
        path=self.whole.directory/NAME
        path.write_text('{"phase":"tampered"}')
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.prune()
        self.assertTrue(self.held.joinpath("dvtws.args").is_file())

    def test_native_lock_and_kernel_gate_before_marker(self):
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.prune(lock=False)
        self.assertIsNone(read_prune_intent(self.whole.directory))
        from voice_native_ipfw_ownership import KernelOwnershipError
        self.fx.kernel.rules[19000]=reclaim_fixture.fixtures.receipt_tests.kernel_fixture.TCP
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.prune()
        self.assertIsNone(read_prune_intent(self.whole.directory))
        self.assertEqual(self.original,self.held.joinpath("dvtws.args").read_bytes())


if __name__=="__main__":
    unittest.main(verbosity=2)
