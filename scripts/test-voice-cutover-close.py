#!/usr/bin/env python3
"""Atomic whole-rollback archival tests: no Voice ON, legacy remains blocked."""
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
from voice_cutover_close import (
    NAME,ARCHIVE,CloseError,read_close_intent,inspect_close_placement,
    archive_verified_whole_intent,
)
from voice_cutover_guard import check_pending
from voice_native_boot_recovery_review import inspect_boot_recovery


def fixture(name,mod):
    spec=importlib.util.spec_from_file_location(mod,ROOT/"scripts"/name)
    assert spec and spec.loader
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


f=fixture("test-voice-cutover-finalization.py","archive_finalization_fixture")


class ArchiveWholeRollbackTests(unittest.TestCase):
    def setUp(self):
        self.fx=f.FinalizationProofTests()
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.fx.seal()
        self.journal=self.fx.fx.journal
        self.root=self.journal.directory
        self.before=self.journal.read()

    def archive(self,lock=True):
        return self.fx._do(archive_verified_whole_intent,lock)

    def boot(self):
        return self.fx._do(inspect_boot_recovery)

    def guard(self):
        return check_pending(self.root,self.fx.fx.fx.fx.fx.ipfw.directory)

    def assert_preserved(self):
        report=self.boot()
        self.assertEqual("previous-journal-archived-awaits-native-acceptance",
                         report["state"])
        self.assertIs(report["voice_on"],False)
        self.assertIs(report["safe_to_close_intent"],False)
        for name in (
            NAME,ARCHIVE,"previous-finalization-proof.json",
            "previous-root-release-intent.json","previous-prune-intent.json",
            "previous-reclaim-intent.json","previous-cleanup-plan.json",
            "previous-rollback-receipt.json","runtime-restore-redo.json",
        ):
            self.assertTrue((self.root/name).is_file(),name)
        self.assertTrue(self.fx.fx.fx.fx.image.is_dir())
        self.assertTrue(self.fx.fx.fx.fx.live.is_dir())

    def test_archive_atomic_no_unprotected_start_and_idempotent(self):
        result=self.archive()
        self.assertEqual("whole-rollback-archived-awaiting-native-acceptance",
                         result["state"])
        self.assertIs(result["voice_on"],False)
        self.assertIs(result["safe_to_start"],False)
        self.assertIs(result["safe_to_close_intent"],False)
        self.assertIsNone(self.journal.read())
        self.assertTrue((self.root/ARCHIVE).is_file())
        self.assertEqual(self.before["check"],
                         inspect_close_placement(
                             journal=self.journal,config_path=self.fx.fx.fx.fx.config,
                             active_runtime=self.fx.fx.fx.fx.live,
                         )["record"]["check"])
        report=self.boot()
        self.assertEqual("previous-journal-archived-awaits-native-acceptance",
                         report["state"])
        self.assertEqual("archived-awaiting-native-acceptance",
                         report["whole_closure"])
        self.assertIs(report["safe_to_start"],False)
        self.assertIs(report["safe_to_close_intent"],False)
        self.assertIs(self.guard()["safe_to_mutate"],False)
        self.assertEqual("whole-rollback-archived-awaiting-native-acceptance",
                         self.archive()["state"])
        self.assert_preserved()

    def test_crash_before_rename_restarts_without_duplicate_archive(self):
        with patch("voice_cutover_close._rename",side_effect=OSError("power cut")):
            with self.assertRaises(OSError):
                self.archive()
        self.assertEqual("archive-armed",self.boot()["whole_closure"])
        self.assertIsNotNone(read_close_intent(self.root))
        self.assertEqual(self.before,self.journal.read())
        self.assertFalse((self.root/ARCHIVE).exists())
        self.assertIs(self.guard()["safe_to_mutate"],False)
        self.archive()
        self.assert_preserved()

    def test_crash_after_rename_before_parent_fsync_restarts(self):
        def interrupted(directory):
            os.rename(Path(directory)/"intent.json",Path(directory)/ARCHIVE)
            raise OSError("power cut after directory rename")
        with patch("voice_cutover_close._rename",side_effect=interrupted):
            with self.assertRaises(OSError):
                self.archive()
        self.assertIsNone(self.journal.read())
        self.assertEqual("archived-awaiting-native-acceptance",
                         self.boot()["whole_closure"])
        self.assertIs(self.guard()["safe_to_mutate"],False)
        self.archive()
        self.assert_preserved()

    def test_missing_marker_archive_fails_closed(self):
        self.archive()
        (self.root/NAME).unlink()
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.boot()
        self.assertIs(self.guard()["safe_to_mutate"],False)
        self.assertTrue((self.root/ARCHIVE).exists())

    def test_duplicate_live_journal_and_archive_denied(self):
        self.archive()
        raw=(self.root/ARCHIVE).read_bytes()
        (self.root/"intent.json").write_bytes(raw)
        (self.root/"intent.json").chmod(0o600)
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.boot()
        self.assertIs(self.guard()["safe_to_mutate"],False)

    def test_corrupt_closure_never_grants_start_or_retry(self):
        self.archive()
        (self.root/NAME).write_text('{"schema":1,"phase":"foreign"}')
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.boot()
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.archive()
        self.assertIs(self.guard()["safe_to_mutate"],False)

    def test_prior_epoch_or_original_config_flock_required(self):
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.archive(lock=False)
        self.assertIsNone(read_close_intent(self.root))
        self.assertEqual(self.before,self.journal.read())
        receipt_fixture=self.fx.fx.fx.fx
        receipt_fixture.state["supervisor"]["daemon"]["start_ns"]+=4000
        # A new (or unexpectedly changed) native process epoch does not
        # revalidate the previously sealed original rollback receipt.
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.archive()


if __name__=="__main__":
    unittest.main(verbosity=2)
