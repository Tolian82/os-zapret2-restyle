#!/usr/bin/env python3
"""Durable Voice postrollback reclaim: write-ahead, no-unlink candidate quarantine."""
from __future__ import annotations

import fcntl
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))
from voice_cutover_reclaim import (
    ReclaimError, NAME, read_reclaim_intent, inspect_reclaim_placement,
    stage_retired_candidate,
)
from voice_cutover_runtime_restore import _arm, _record
from voice_native_boot_recovery_review import inspect_boot_recovery


def load(name,alias):
    spec=importlib.util.spec_from_file_location(alias,ROOT/"scripts"/name)
    assert spec and spec.loader
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


fixtures=load("test-voice-cutover-cleanup-prepare.py","reclaim_cleanup_fixture")


class RetiredCandidateQuarantineTests(unittest.TestCase):
    def setUp(self):
        self.helper=fixtures.CleanupPrepareTests()
        self.helper.setUp()
        self.addCleanup(self.helper.doCleanups)
        self.fx=self.helper.fx
        self.whole=self.fx.fx.whole
        self.fx.seal()
        original=self.whole.read()
        suffix=original["check"][:20]
        self.retired=self.fx.fx.root/(".voice-restore-retired-"+suffix)
        self.held=self.fx.fx.root/(".voice-reclaim-held-"+suffix)
        shutil.copytree(self.fx.fx.candidate,self.retired,copy_function=shutil.copy2)
        parent=self.fx.live.parent.stat()
        self.redo=_record({
            "schema":1,"cutover_check":original["check"],
            "parent_dev":parent.st_dev,"parent_ino":parent.st_ino,
            "active_name":self.fx.live.name,
            "candidate_sha256":original["candidate"]["candidate_runtime_sha256"],
            "previous_sha256":original["previous"]["runtime"],
            "ready_name":".voice-restore-ready-"+suffix,
            "retired_name":self.retired.name,
        })
        _arm(self.whole.directory,self.redo)
        self.helper.complete()
        self.terminal=self.whole.read()
        self.calls=[]

    def _kwargs(self,fd):
        return dict(
            journal=self.whole,ledger=self.fx.fx.ipfw,
            previous_backup=self.fx.fx.backup,
            process_evidence=self.fx.fx.process,
            security_evidence=self.fx.fx.policy,
            install_image=self.fx.image,config_path=self.fx.config,
            active_runtime=self.fx.live,probe=self.fx.probe,
            adapter=self.fx.adapter,config_fd=fd,
            config_owner=(os.geteuid(),os.getegid()),
            require_lifecycle_owner=lambda:self.calls.append("FD9"),
        )

    def stage(self,lock=True):
        fd=os.open(self.fx.config,os.O_RDWR)
        try:
            if lock:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return stage_retired_candidate(**self._kwargs(fd))
        finally:
            os.close(fd)

    def review(self):
        fd=os.open(self.fx.config,os.O_RDWR)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return inspect_boot_recovery(**self._kwargs(fd))
        finally:
            os.close(fd)

    def assert_preserved(self):
        self.assertEqual(self.terminal,self.whole.read())
        self.assertTrue(self.fx.live.is_dir())
        self.assertTrue(self.fx.image.is_dir())
        self.assertIsNotNone(self.fx.fx.ipfw.owned())
        self.assertTrue((self.whole.directory/"previous-cleanup-plan.json").is_file())
        self.assertTrue((self.whole.directory/"previous-rollback-receipt.json").is_file())
        self.assertTrue((self.whole.directory/"runtime-restore-redo.json").is_file())

    def test_move_retired_candidate_under_real_flock_and_read_only_boot(self):
        first=self.stage()
        self.assertEqual("candidate-quarantined",first["state"])
        self.assertIs(first["voice_on"],False)
        self.assertIs(first["safe_to_close_intent"],False)
        self.assertFalse(self.retired.exists())
        self.assertTrue(self.held.is_dir())
        self.assertEqual("candidate-quarantined",self.review()["candidate_reclaim"])
        self.assertEqual("candidate-already-quarantined",self.stage()["state"])
        self.assertEqual(0o600,(self.whole.directory/NAME).stat().st_mode&0o777)
        self.assert_preserved()

    def test_crash_after_write_ahead_before_rename_resumes_idempotently(self):
        with patch("voice_cutover_reclaim.os.rename",side_effect=OSError("crash")):
            with self.assertRaises(OSError):
                self.stage()
        marker=read_reclaim_intent(self.whole.directory)
        self.assertEqual("quarantine-intent",marker["phase"])
        self.assertTrue(self.retired.is_dir())
        self.assertFalse(self.held.exists())
        self.assertEqual("write-ahead-retired",self.review()["candidate_reclaim"])
        self.assertEqual("candidate-quarantined",self.stage()["state"])
        self.assertEqual(marker,read_reclaim_intent(self.whole.directory))
        self.assert_preserved()

    def test_no_flock_or_kernel_reset_rejects_without_marker(self):
        with self.assertRaises((ValueError,RuntimeError)):
            self.stage(lock=False)
        self.assertIsNone(read_reclaim_intent(self.whole.directory))
        saved=self.fx.kernel.rules.get(19000)
        self.fx.kernel.rules[19000]=fixtures.receipt_tests.kernel_fixture.TCP
        try:
            with self.assertRaises((ValueError,RuntimeError)):
                self.stage()
        finally:
            if saved is None:
                self.fx.kernel.rules.pop(19000,None)
            else:
                self.fx.kernel.rules[19000]=saved
        self.assertIsNone(read_reclaim_intent(self.whole.directory))
        self.assertTrue(self.retired.is_dir())
        self.assert_preserved()

    def test_foreign_candidate_or_target_never_overwritten(self):
        self.held.mkdir(mode=0o700)
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.stage()
        self.assertIsNone(read_reclaim_intent(self.whole.directory))
        self.assertTrue(self.retired.is_dir())
        self.assertTrue(self.held.is_dir())
        self.held.rmdir()
        (self.retired/"foreign").write_text("tampered")
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.stage()
        self.assertIsNone(read_reclaim_intent(self.whole.directory))
        self.assert_preserved()

    def test_corrupt_marker_never_replaced_or_interpreted_as_crash(self):
        path=self.whole.directory/NAME
        path.write_text('{"schema":1,"phase":"forged"}')
        path.chmod(0o600)
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.stage()
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.review()
        self.assertEqual(self.terminal,self.whole.read())
        self.assertTrue(self.retired.is_dir())

    def test_orphan_quarantine_without_write_ahead_denied(self):
        self.retired.rename(self.held)
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.review()
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.stage()
        self.assertIsNone(read_reclaim_intent(self.whole.directory))
        self.assert_preserved()


if __name__=="__main__":
    unittest.main(verbosity=2)
