#!/usr/bin/env python3
"""Actual isolated filesystem rename/crash recovery for native Voice runtime."""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

from voice_cutover_backup import capture_previous, bound_resource_fingerprints
from voice_cutover_restore_stage import prepare_restore_stage
from voice_cutover_install_image import prepare_installable_restore
from voice_cutover_journal import VoiceCutoverJournal
from voice_native_file_observer import observe_live_files
import voice_cutover_runtime_restore as runtime

spec=importlib.util.spec_from_file_location(
    "runtime_restore_fixture", ROOT/"scripts/test-voice-firewall-transaction.py"
)
assert spec and spec.loader
fixture=importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class RuntimeRecovery(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(prefix="voice-runtime-restore-")
        self.addCleanup(t.cleanup)
        self.base=Path(t.name)
        self.base.chmod(0o700)
        self.config=self.base/"config.xml"
        self.config.write_bytes(b"<opnsense>original</opnsense>\n")
        self.config.chmod(0o640)
        self.active=self.base/"runtime-v2"
        self.active.mkdir(mode=0o750)
        (self.active/"dvtws.args").write_text("--filter-tcp=443\n")
        (self.active/"dvtws.args").chmod(0o640)
        (self.active/"managed").mkdir()
        (self.active/"managed"/"telegram.txt").write_text("91.108.0.0/16\n")
        self.journal_dir=self.base/"private"
        self.journal_dir.mkdir(mode=0o700)
        self.backup=self.journal_dir/"previous"
        capture_previous(self.config,self.active,self.backup)
        self.previous=bound_resource_fingerprints(self.backup)
        self.stage=self.journal_dir/"restore-staged"
        self.image=self.journal_dir/"install-image"
        prepare_restore_stage(self.backup,self.stage,self.previous)
        prepare_installable_restore(self.stage,self.image,self.previous)
        self.journal=VoiceCutoverJournal(self.journal_dir)
        self.all_previous={**self.previous,"engine":"d"*64,
                           "firewall":"e"*64,"supervisor":"f"*64}
        self.proof={"saved_xml_sha256":hashlib.sha256(b"<candidate/>").hexdigest(),
                    "merged_sha256":"a"*64,"native_argv_sha256":"b"*64}
        # Simulate active candidate, preserving the previous recovery image.
        self.active.chmod(0o700)
        (self.active/"dvtws.args").write_text("--filter-tcp=443 --voice=on\n")
        (self.active/"managed"/"telegram.txt").write_text("91.108.0.0/24\n")
        (self.active/"candidate.conf").write_text("candidate\n")
        self.candidate_sha=self.sha(self.active)

    def sha(self,path):
        return observe_live_files(self.image/"config.xml",path)["runtime"]

    def begin(self):
        self.journal.begin_bound(self.all_previous,self.proof,fixture.fixture())
        self.journal.mark_mutating()

    def paths(self):
        check=self.journal.read()["check"][:20]
        return (self.active.with_name(".voice-restore-ready-"+check),
                self.active.with_name(".voice-restore-retired-"+check))

    def call(self, **kwargs):
        return runtime.restore_previous_runtime(
            self.active,self.image,self.backup,
            kwargs.get("journal",self.journal),
            require_lifecycle_owner=kwargs.get("require_lifecycle_owner",lambda:None),
            expected_candidate_runtime_sha256=kwargs.get(
                "candidate_sha",self.candidate_sha),
        )

    def test_actual_two_rename_restore_keeps_retired_candidate(self):
        self.begin()
        result=self.call()
        ready,retired=self.paths()
        self.assertEqual("previous-runtime-restored",result)
        self.assertFalse(ready.exists())
        self.assertEqual(self.sha(self.active),self.previous["runtime"])
        self.assertEqual(self.sha(retired),self.candidate_sha)
        self.assertEqual(0o750,self.active.stat().st_mode & 0o777)
        self.assertEqual(0o640,(self.active/"dvtws.args").stat().st_mode & 0o777)
        self.assertTrue((self.journal_dir/runtime.REDO).is_file())
        self.assertEqual("mutating",self.journal.read()["phase"])
        self.assertEqual("previous-runtime-restored",self.call())
        self.assertEqual(self.candidate_sha,self.sha(retired))

    def test_crash_after_first_rename_resumes_from_absent_active(self):
        self.begin()
        real=os.rename
        ready,retired=self.paths()
        def crash(source,dest):
            if Path(source)==ready and Path(dest)==self.active:
                raise OSError("power loss before second rename")
            return real(source,dest)
        with patch.object(runtime.os,"rename",side_effect=crash):
            with self.assertRaisesRegex(OSError,"power loss"):
                self.call()
        self.assertFalse(self.active.exists())
        self.assertTrue(ready.is_dir())
        self.assertEqual(self.sha(retired),self.candidate_sha)
        self.assertTrue((self.journal_dir/runtime.REDO).exists())
        self.assertEqual("previous-runtime-restored", self.call(
            journal=VoiceCutoverJournal(self.journal_dir)))
        self.assertEqual(self.sha(self.active),self.previous["runtime"])
        self.assertEqual("mutating",self.journal.read()["phase"])

    def test_crash_before_first_rename_resumes_cleanly(self):
        self.begin()
        real=os.rename
        ready,retired=self.paths()
        def crash(source,dest):
            if Path(source)==self.active and Path(dest)==retired:
                raise OSError("power loss before retiring candidate")
            return real(source,dest)
        with patch.object(runtime.os,"rename",side_effect=crash):
            with self.assertRaisesRegex(OSError,"power loss"):
                self.call()
        self.assertEqual(self.sha(self.active),self.candidate_sha)
        self.assertTrue(ready.exists())
        self.assertFalse(retired.exists())
        self.assertEqual("previous-runtime-restored",self.call())
        self.assertEqual(self.sha(self.active),self.previous["runtime"])

    def test_foreign_active_is_not_overwritten_or_retired(self):
        self.begin()
        (self.active/"candidate.conf").write_text("foreign edit\n")
        with self.assertRaisesRegex(runtime.VoiceRuntimeRestoreError,"foreign"):
            self.call()
        self.assertFalse((self.journal_dir/runtime.REDO).exists())
        self.assertEqual((self.active/"candidate.conf").read_text(),"foreign edit\n")
        ready,retired=self.paths()
        self.assertFalse(ready.exists())
        self.assertFalse(retired.exists())

    def test_unowned_ready_path_is_refused(self):
        self.begin()
        ready,retired=self.paths()
        ready.mkdir(mode=0o700)
        (ready/"foreign").write_text("untouched")
        with self.assertRaisesRegex(runtime.VoiceRuntimeRestoreError,"unowned"):
            self.call()
        self.assertEqual((ready/"foreign").read_text(),"untouched")
        self.assertEqual(self.sha(self.active),self.candidate_sha)

    def test_missing_redo_after_interrupted_first_rename_refuses(self):
        self.begin()
        ready,retired=self.paths()
        real=os.rename
        def crash(source,dest):
            if Path(source)==ready and Path(dest)==self.active:
                raise OSError("failed before installing")
            return real(source,dest)
        with patch.object(runtime.os,"rename",side_effect=crash):
            with self.assertRaises(OSError):
                self.call()
        (self.journal_dir/runtime.REDO).unlink()
        with self.assertRaises(runtime.VoiceRuntimeRestoreError):
            self.call()
        self.assertFalse(self.active.exists())
        self.assertEqual(self.sha(retired),self.candidate_sha)

    def test_tampered_retired_candidate_denies_recovery(self):
        self.begin()
        ready,retired=self.paths()
        real=os.rename
        def crash(source,dest):
            if Path(source)==ready and Path(dest)==self.active:
                raise OSError("failed")
            return real(source,dest)
        with patch.object(runtime.os,"rename",side_effect=crash):
            with self.assertRaises(OSError):
                self.call()
        (retired/"candidate.conf").write_text("foreign")
        with self.assertRaises(runtime.VoiceRuntimeRestoreError):
            self.call()
        self.assertFalse(self.active.exists())
        self.assertEqual((retired/"candidate.conf").read_text(),"foreign")

    def test_non_mutating_and_tampered_image_denied(self):
        with self.assertRaisesRegex(runtime.VoiceRuntimeRestoreError,"mutating"):
            self.call()
        self.begin()
        (self.image/"runtime/dvtws.args").write_text("tampered")
        with self.assertRaises(Exception):
            self.call()
        self.assertEqual(self.sha(self.active),self.candidate_sha)
        self.assertFalse((self.journal_dir/runtime.REDO).exists())

    def test_symlink_runtime_refused(self):
        self.begin()
        foreign=self.base/"foreign"
        foreign.mkdir()
        (foreign/"sentinel").write_text("untouched")
        shutil.rmtree(self.active)
        self.active.symlink_to(foreign,target_is_directory=True)
        with self.assertRaises(runtime.VoiceRuntimeRestoreError):
            self.call()
        self.assertEqual((foreign/"sentinel").read_text(),"untouched")
        self.assertFalse((self.journal_dir/runtime.REDO).exists())


if __name__=="__main__":
    unittest.main(verbosity=2)
