#!/usr/bin/env python3
"""Crash-safe cleanup PREPARE only: no deletion of journals or candidate data."""
from __future__ import annotations

import copy
import fcntl
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import unittest

ROOT=Path(__file__).resolve().parent.parent
BACKEND=ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0,str(BACKEND))
from voice_cutover_cleanup_prepare import (
    CleanupPrepareError, NAME, read_cleanup_plan,prepare_previous_cleanup,seal_previous_completion,
)
from voice_cutover_recovery_receipt import (
    read_receipt, seal_previous_receipt,
)
from voice_cutover_config_redo import ConfigRestoreRedo
from voice_cutover_runtime_restore import _arm, _record
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS


def fixture(file,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/"scripts"/file)
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


receipt_tests=fixture("test-voice-cutover-recovery-receipt.py","cleanup_prepare_fixture")


class CleanupPrepareTests(unittest.TestCase):
    def setUp(self):
        self.fx=receipt_tests.ReceiptTests()
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.observations=[]

    def prepare(self, *, lock=True, witness=None):
        fd=os.open(self.fx.config,os.O_RDWR)
        try:
            if lock:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            proof=self.fx.witness if witness is None else witness
            return prepare_previous_cleanup(
                journal=self.fx.fx.whole,ledger=self.fx.fx.ipfw,
                previous_backup=self.fx.fx.backup,
                install_image=self.fx.image,
                config_path=self.fx.config,active_runtime=self.fx.live,
                config_fd=fd,config_owner=(os.geteuid(),os.getegid()),
                probe=self.fx.probe,adapter=self.fx.adapter,
                integrity_report=proof,
                require_lifecycle_owner=lambda:self.observations.append("FD9"),
            )
        finally:
            os.close(fd)

    def test_receipt_required_then_prepared_without_deletion(self):
        with self.assertRaises(CleanupPrepareError):
            self.prepare()
        self.assertIsNone(read_cleanup_plan(self.fx.fx.whole.directory))
        self.fx.seal()
        original=self.fx.fx.whole.read()
        result=self.prepare()
        self.assertEqual("previous-cleanup-prepared-only",result["state"])
        self.assertIs(result["safe_to_finish_intent"],False)
        self.assertIs(result["safe_to_enable_voice"],False)
        marker=read_cleanup_plan(self.fx.fx.whole.directory)
        self.assertEqual(original["check"],marker["whole_check"])
        self.assertEqual(read_receipt(self.fx.fx.whole.directory)["check"],
                         marker["receipt_check"])
        self.assertEqual(original["candidate"]["candidate_runtime_sha256"],
                         marker["candidate_runtime_sha256"])
        self.assertEqual("mutating",self.fx.fx.whole.read()["phase"])
        self.assertEqual("previous-cleanup-already-prepared",
                         self.prepare()["state"])
        self.assertEqual(
            0o600,(self.fx.fx.whole.directory/NAME).stat().st_mode&0o777
        )
        self.assertTrue(self.fx.live.is_dir())
        self.assertTrue(self.fx.image.is_dir())
        self.assertIsNotNone(read_receipt(self.fx.fx.whole.directory))


    def complete(self, *, lock=True, witness=None):
        fd=os.open(self.fx.config,os.O_RDWR)
        try:
            if lock:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return seal_previous_completion(
                journal=self.fx.fx.whole,ledger=self.fx.fx.ipfw,
                previous_backup=self.fx.fx.backup,install_image=self.fx.image,
                config_path=self.fx.config,active_runtime=self.fx.live,
                config_fd=fd,config_owner=(os.geteuid(),os.getegid()),
                probe=self.fx.probe,adapter=self.fx.adapter,
                integrity_report=self.fx.witness if witness is None else witness,
                require_lifecycle_owner=lambda:self.observations.append("FD9"),
            )
        finally:
            os.close(fd)

    def test_previous_completion_persists_terminal_phase_and_evidence(self):
        self.fx.seal()
        before=self.fx.fx.whole.read()
        receipt=read_receipt(self.fx.fx.whole.directory)
        result=self.complete()
        self.assertEqual("previous-rollback-sealed",result["state"])
        self.assertEqual("rolled_back",self.fx.fx.whole.read()["phase"])
        self.assertEqual("previous-restored-needs-final-cleanup",
                         self.fx.fx.whole.inspect())
        self.assertEqual(before["previous"],self.fx.fx.whole.read()["previous"])
        self.assertEqual(before["candidate"],self.fx.fx.whole.read()["candidate"])
        plan=read_cleanup_plan(self.fx.fx.whole.directory)
        self.assertEqual(before["check"],plan["whole_check"])
        self.assertEqual(receipt["check"],plan["receipt_check"])
        self.assertTrue(self.fx.live.exists())
        self.assertTrue(self.fx.image.exists())
        self.assertIs(result["safe_to_enable_voice"],False)
        with self.assertRaises((CleanupPrepareError,ValueError,RuntimeError)):
            self.complete()

    def test_previous_completion_requires_receipt_and_original_flock(self):
        original=self.fx.fx.whole.read()
        with self.assertRaises((CleanupPrepareError,ValueError,RuntimeError)):
            self.complete()
        self.assertEqual(original,self.fx.fx.whole.read())
        self.fx.seal()
        with self.assertRaises((CleanupPrepareError,ValueError,RuntimeError)):
            self.complete(lock=False)
        self.assertEqual("mutating",self.fx.fx.whole.read()["phase"])

    def test_previous_completion_rejects_stale_process_attestation(self):
        self.fx.seal()
        stale=copy.deepcopy(self.fx.witness)
        stale["instances"]["engine"]["pid"]+=1
        with self.assertRaises((CleanupPrepareError,ValueError,RuntimeError)):
            self.complete(witness=stale)
        self.assertEqual("mutating",self.fx.fx.whole.read()["phase"])
        self.assertIsNone(read_cleanup_plan(self.fx.fx.whole.directory))

    def test_missing_config_lock_fails_closed(self):
        self.fx.seal()
        with self.assertRaises((CleanupPrepareError,ValueError,RuntimeError)):
            self.prepare(lock=False)
        self.assertIsNone(read_cleanup_plan(self.fx.fx.whole.directory))

    def test_unknown_new_process_or_stale_report_denied(self):
        self.fx.seal()
        foreign=copy.deepcopy(self.fx.witness)
        foreign["instances"]["daemon"]["pid"]+=1000
        with self.assertRaises(CleanupPrepareError):
            self.prepare(witness=foreign)
        self.assertIsNone(read_cleanup_plan(self.fx.fx.whole.directory))
        self.fx.witness["instances"]["daemon"]["pid"]+=1000
        with self.assertRaises(CleanupPrepareError):
            self.prepare()

    def test_retired_candidate_verified_against_sealed_digest(self):
        self.fx.seal()
        record=self.fx.fx.whole.read()
        root=self.fx.fx.root
        suffix=record["check"][:20]
        retired_name=".voice-restore-retired-"+suffix
        retired=root/retired_name
        shutil.copytree(self.fx.fx.candidate,retired,copy_function=shutil.copy2)
        stat_parent=self.fx.live.parent.stat()
        data=_record({
            "schema":1,"cutover_check":record["check"],
            "parent_dev":stat_parent.st_dev,"parent_ino":stat_parent.st_ino,
            "active_name":self.fx.live.name,
            "candidate_sha256":record["candidate"]["candidate_runtime_sha256"],
            "previous_sha256":record["previous"]["runtime"],
            "ready_name":".voice-restore-ready-"+suffix,
            "retired_name":retired_name,
        })
        _arm(self.fx.fx.whole.directory,data)
        marker=self.prepare()
        self.assertEqual("previous-cleanup-prepared-only",marker["state"])
        read=read_cleanup_plan(self.fx.fx.whole.directory)
        self.assertEqual(retired_name,read["retired_name"])
        self.assertEqual(data["checksum"],read["runtime_redo_check"])
        self.assertTrue(retired.is_dir())
        self.assertEqual("mutating",self.fx.fx.whole.read()["phase"])

    def test_foreign_retired_candidate_blocks_without_cleanup(self):
        self.fx.seal()
        record=self.fx.fx.whole.read()
        suffix=record["check"][:20]
        retired=self.fx.fx.root/(".voice-restore-retired-"+suffix)
        shutil.copytree(self.fx.fx.candidate,retired)
        (retired/"foreign").write_text("tampered")
        stat_parent=self.fx.live.parent.stat()
        data=_record({
            "schema":1,"cutover_check":record["check"],
            "parent_dev":stat_parent.st_dev,"parent_ino":stat_parent.st_ino,
            "active_name":self.fx.live.name,
            "candidate_sha256":record["candidate"]["candidate_runtime_sha256"],
            "previous_sha256":record["previous"]["runtime"],
            "ready_name":".voice-restore-ready-"+suffix,
            "retired_name":retired.name,
        })
        _arm(self.fx.fx.whole.directory,data)
        with self.assertRaises((CleanupPrepareError,ValueError,RuntimeError)):
            self.prepare()
        self.assertTrue(retired.exists())
        self.assertIsNone(read_cleanup_plan(self.fx.fx.whole.directory))

    def test_config_redo_record_bound_to_same_locked_inode(self):
        fd=os.open(self.fx.config,os.O_RDWR)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            saved=ConfigRestoreRedo(self.fx.fx.whole.directory).arm(
                journal_record=self.fx.fx.whole.read(),
                info=os.fstat(fd),
                previous_bytes=os.fstat(fd).st_size,
            )
        finally:
            os.close(fd)
        self.fx.seal()
        self.prepare()
        result=read_cleanup_plan(self.fx.fx.whole.directory)
        self.assertEqual(saved["checksum"],result["config_redo_check"])

    def test_corrupt_write_once_plan_refuses_replacement(self):
        self.fx.seal()
        path=self.fx.fx.whole.directory/NAME
        path.write_text('{"schema":1,"check":"bad"}')
        path.chmod(0o600)
        with self.assertRaises((CleanupPrepareError,ValueError,RuntimeError)):
            self.prepare()
        self.assertEqual("mutating",self.fx.fx.whole.read()["phase"])
        self.assertTrue(path.exists())

    def test_new_attempt_never_closes_committed_intent(self):
        self.fx.seal()
        self.fx.fx.whole.commit()
        with self.assertRaises(CleanupPrepareError):
            self.prepare()
        self.assertIsNone(read_cleanup_plan(self.fx.fx.whole.directory))


if __name__=="__main__":
    unittest.main(verbosity=2)
