#!/usr/bin/env python3
"""Real schema-4 native forward runtime swap, crash safety and old rollback."""
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
from voice_native_forward_runtime import (
    install_forward_runtime,_read_redo,ForwardRuntimeError,MARKER,
)
from voice_native_file_observer import observe_live_files
from voice_cutover_restore_stage import prepare_restore_stage
from voice_cutover_install_image import prepare_installable_restore
from voice_cutover_runtime_restore import restore_previous_runtime


def fixture(name,module):
    spec=importlib.util.spec_from_file_location(module,ROOT/"scripts"/name)
    assert spec and spec.loader
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


f=fixture("test-voice-cutover-runtime-bound-intent.py","forward_runtime_fixture")


class ForwardRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.fx=f.RuntimeBoundCutoverTests()
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.fx.begin()
        self.fx.whole.mark_mutating()
        self.record=self.fx.whole.read()
        self.active=self.fx.root/"runtime"
        self.config=self.fx.root/"config.xml"
        self.old=self.fx.prior["runtime"]
        self.new=self.record["candidate"]["candidate_runtime_sha256"]
        self.guard_calls=0
        self.stopped=True

    def invoke(self, *,lock=True):
        fd=os.open(self.config,os.O_RDWR)
        try:
            if lock:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return install_forward_runtime(
                active_runtime=self.active,
                staged_config=self.fx.stage_config,
                candidate_runtime=self.fx.candidate,
                previous_backup=self.fx.backup,
                journal=self.fx.whole,
                config_path=self.config,
                locked_config_fd=fd,
                config_owner=(os.geteuid(),os.getegid()),
                require_lifecycle_owner=self.owner,
                require_all_processes_stopped=lambda:self.stopped,
            )
        finally:
            os.close(fd)

    def owner(self):
        self.guard_calls+=1

    def paths(self):
        suffix=self.record["check"][:20]
        return (self.active.with_name(".voice-forward-ready-"+suffix),
                self.active.with_name(".voice-forward-previous-"+suffix))

    def hash(self,path):
        return observe_live_files(self.fx.stage_config,path)["runtime"]

    def verify(self):
        ready,retired=self.paths()
        self.assertFalse(ready.exists())
        self.assertEqual(self.hash(self.active),self.new)
        self.assertEqual(self.hash(retired),self.old)
        self.assertEqual(self.fx.whole.read(),self.record)
        self.assertIsNotNone(_read_redo(self.fx.whole.directory))
        self.assertGreater(self.guard_calls,3)

    def test_native_forward_two_atomic_renames_and_old_tree_retained(self):
        report=self.invoke()
        self.assertEqual("native-voice-forward-runtime-installed",report["state"])
        self.assertIs(report["voice_on"],False)
        self.assertIs(report["safe_to_start"],False)
        self.verify()
        self.assertEqual("native-voice-forward-runtime-installed",self.invoke()["state"])
        self.verify()

    def test_refuses_without_config_flock_or_quiescence(self):
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.invoke(lock=False)
        self.stopped=False
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.invoke()
        self.assertIsNone(_read_redo(self.fx.whole.directory))
        self.assertEqual(self.hash(self.active),self.old)

    def test_refuses_before_whole_mutating(self):
        self.fx.whole._transition("mutating","committed")
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.invoke()
        self.assertIsNone(_read_redo(self.fx.whole.directory))

    def test_wrong_candidate_or_original_runtime_refused_without_rename(self):
        (self.fx.candidate/"dvtws.args").write_text("--port=981\n")
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.invoke()
        self.assertIsNone(_read_redo(self.fx.whole.directory))

    def test_crash_after_redo_before_first_rename_retries(self):
        import voice_native_forward_runtime as mod
        real=mod.os.rename
        def crash(src,dst):
            if Path(src)==self.active:
                raise OSError("power off before first rename")
            return real(src,dst)
        with patch.object(mod.os,"rename",side_effect=crash):
            with self.assertRaises(OSError):
                self.invoke()
        self.assertIsNotNone(_read_redo(self.fx.whole.directory))
        self.assertEqual(self.hash(self.active),self.old)
        self.invoke()
        self.verify()

    def test_crash_after_first_rename_before_directory_fsync_retries(self):
        import voice_native_forward_runtime as mod
        real=mod.os.rename
        def crash(src,dst):
            real(src,dst)
            if Path(src)==self.active:
                raise OSError("power off after first rename")
        with patch.object(mod.os,"rename",side_effect=crash):
            with self.assertRaises(OSError):
                self.invoke()
        self.assertFalse(self.active.exists())
        self.invoke()
        self.verify()

    def test_crash_after_second_rename_before_directory_fsync_retries(self):
        import voice_native_forward_runtime as mod
        real=mod.os.rename
        def crash(src,dst):
            real(src,dst)
            if Path(src)==self.paths()[0]:
                raise OSError("power off after second rename")
        with patch.object(mod.os,"rename",side_effect=crash):
            with self.assertRaises(OSError):
                self.invoke()
        self.assertEqual(self.hash(self.active),self.new)
        self.invoke()
        self.verify()

    def test_orphan_ready_pre_marker_denied_not_adopted(self):
        ready,_=self.paths()
        ready.mkdir(mode=0o700)
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.invoke()
        self.assertTrue(ready.exists())
        self.assertEqual(self.hash(self.active),self.old)

    def test_corrupted_marker_and_unexpected_retired_refused(self):
        self.invoke()
        marker=self.fx.whole.directory/MARKER
        marker.write_text('{"schema":1}')
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.invoke()
        self.assertEqual(self.hash(self.active),self.new)

    def test_installed_candidate_is_compatible_with_real_previous_runtime_rollback(self):
        self.invoke()
        staged=self.fx.root/"restore-staged"
        image=self.fx.root/"restore-image"
        prepare_restore_stage(self.fx.backup,staged,self.fx.prior)
        prepare_installable_restore(staged,image,self.fx.prior)
        result=restore_previous_runtime(
            self.active,image,self.fx.backup,self.fx.whole,
            require_lifecycle_owner=self.owner,
            expected_candidate_runtime_sha256=self.new,
        )
        self.assertEqual(result,"previous-runtime-restored")
        self.assertEqual(self.hash(self.active),self.old)
        self.assertEqual(self.fx.whole.read()["phase"],"mutating")
        self.assertTrue((self.fx.whole.directory/MARKER).is_file())


if __name__=="__main__":
    unittest.main(verbosity=2)
