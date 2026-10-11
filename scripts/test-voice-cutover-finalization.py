#!/usr/bin/env python3
"""Write-once postrollback finalization proof: no whole-intent close or Voice ON."""
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

from voice_cutover_finalization import (
    NAME,FinalizationError,read_finalization_proof,
    inspect_finalization_proof,seal_finalization_proof,
)
from voice_native_boot_recovery_review import inspect_boot_recovery


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/"scripts"/path)
    assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


roots=load("test-voice-cutover-root-release.py","finalization_root_fixture")


class FinalizationProofTests(unittest.TestCase):
    def setUp(self):
        self.fx=roots.RootReleaseTests()
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.fx.release()
        self.before=self.fx.journal.read()
        self.folder=self.fx.private

    def _do(self,fn,lock=True):
        fd=os.open(self.fx.fx.fx.config,os.O_RDWR)
        try:
            if lock:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return fn(**self.fx.fx.fixture._kwargs(fd))
        finally:
            os.close(fd)

    def seal(self,lock=True):
        return self._do(seal_finalization_proof,lock)

    def review(self):
        return self._do(inspect_boot_recovery)

    def test_sealed_finalization_only_reports_acceptance_not_voice_on(self):
        self.assertEqual("absent",self.review()["previous_finalization"])
        state=self.seal()
        self.assertEqual("finalization-sealed-awaiting-owner-acceptance",state["state"])
        self.assertFalse(state["voice_on"])
        self.assertFalse(state["safe_to_close_intent"])
        self.assertEqual(
            "sealed-awaiting-owner-acceptance",
            self.review()["previous_finalization"],
        )
        self.assertEqual("finalization-sealed-awaiting-owner-acceptance",
                         self.seal()["state"])
        proof=read_finalization_proof(self.folder)
        self.assertEqual(self.before["check"],proof["terminal_check"])
        self.assertTrue((self.folder/NAME).is_file())
        self.assertEqual(0o600,(self.folder/NAME).stat().st_mode&0o777)
        self.assertEqual(self.before,self.fx.journal.read())
        self.assertFalse(self.fx.held.exists())
        self.assertTrue(self.fx.fx.fx.image.exists())
        self.assertTrue(self.fx.fx.fx.live.exists())

    def test_crash_after_exclusive_create_blocks_unsafe_replacement(self):
        with patch("voice_cutover_finalization._publish",
                   side_effect=OSError("simulated crash before marker")):
            with self.assertRaises(OSError):
                self.seal()
        self.assertIsNone(read_finalization_proof(self.folder))
        self.assertEqual("finalization-sealed-awaiting-owner-acceptance",
                         self.seal()["state"])
        self.assertEqual(self.before,self.fx.journal.read())

    def test_corrupted_record_rejected_on_boot_and_seal(self):
        self.seal()
        marker=self.folder/NAME
        marker.write_text('{"schema":1,"state":"foreign"}')
        marker.chmod(0o600)
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.review()
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.seal()
        self.assertEqual(self.before,self.fx.journal.read())

    def test_reject_missing_prior_release_without_finalization(self):
        (self.folder/"previous-root-release-intent.json").unlink()
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.seal()
        self.assertIsNone(read_finalization_proof(self.folder))
        self.assertEqual(self.before,self.fx.journal.read())

    def test_reject_missing_config_flock_and_kernel_drift(self):
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.seal(lock=False)
        self.assertIsNone(read_finalization_proof(self.folder))
        kernel=self.fx.fx.fx.kernel
        kernel.rules[19000]=roots.prune_fixture.reclaim_fixture.fixtures.receipt_tests.kernel_fixture.TCP
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.seal()
        self.assertIsNone(read_finalization_proof(self.folder))
        self.assertEqual(self.before,self.fx.journal.read())

    def test_boot_recognizes_proof_when_process_epoch_differs_not_readiness(self):
        self.seal()
        real=self.fx.fx.fx
        old=real.state["supervisor"]["daemon"]["start_ns"]
        real.state["supervisor"]["daemon"]["start_ns"]=old+4000
        report=self.review()
        self.assertEqual("sealed-awaiting-owner-acceptance",
                         report["previous_finalization"])
        self.assertEqual("stale-process-epoch",report["previous_receipt"])
        self.assertIs(report["safe_to_close_intent"],False)
        self.assertIs(report["voice_on"],False)
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.seal()
        self.assertEqual(self.before,self.fx.journal.read())


if __name__=="__main__":
    unittest.main(verbosity=2)
