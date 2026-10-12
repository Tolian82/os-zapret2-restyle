#!/usr/bin/env python3
"""Actual legacy Telegram runtime directory restoration with exact redo/resume."""
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
import voice_native_legacy_runtime_restore as runtime
from voice_cutover_guard import check_pending
from voice_native_file_observer import observe_live_files


def fixture():
    spec=importlib.util.spec_from_file_location(
        "legacy_runtime_restore_files_ready_fixture",
        ROOT/"scripts/test-voice-native-legacy-files-ready.py",
    )
    x=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(x)
    return x


class LegacyRuntimeRestoreTests(unittest.TestCase):
    def setUp(self):
        self.old=fixture().PreviousFilesReadyTests()
        self.old.setUp()
        self.addCleanup(self.old.doCleanups)
        self.old.previous.call()  # true mock-kernel IPFW replay with redo
        self.old.call()           # old Config/runtime/marker private image
        self.root=self.old.root
        self.live=self.old.live
        self.active=self.live.runtime
        self.marker=self.old.previous.fixture.marker
        self.original_config=self.live.config.read_bytes()
        self.original_state=(self.active/"telegram-voice-poc.state").read_bytes()
        self.candidate_hash=observe_live_files(self.live.config,self.active)["runtime"]

    def call(self,*,locked=True):
        fd=os.open(self.live.config,os.O_RDWR)
        try:
            if locked:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return runtime.restore_legacy_runtime(
                root=self.root,config_path=self.live.config,config_fd=fd,
                config_owner=(os.geteuid(),os.getegid()),
                active_runtime=self.active,legacy_marker=self.marker,
                ledger_root=self.live.ledger,process_probe=self.live.probe,
                readonly_ipfw=self.old.previous.readonly,
                require_lifecycle_owner=lambda:self.live.lock_calls.append("FD9"),
            )
        finally:
            os.close(fd)

    def test_real_two_rename_restore_preserves_candidate_and_config_inode(self):
        old_inode=self.live.config.stat().st_ino
        result=self.call()
        self.assertEqual("legacy-runtime-restored-config-marker-and-processes-pending",
                         result["state"])
        self.assertFalse(result["whole_rollback_complete"])
        self.assertFalse(result["safe_to_enable_voice"])
        self.assertFalse(result["marker_restored"])
        self.assertFalse(result["process_restart_verified"])
        self.assertEqual(self.original_config,self.live.config.read_bytes())
        self.assertEqual(old_inode,self.live.config.stat().st_ino)
        self.assertFalse(self.marker.exists())
        self.assertEqual(b"enabled\n",
                         (self.active/"telegram-voice-poc.state").read_bytes())
        retired=self.active.with_name(result["candidate_retained"])
        self.assertTrue(retired.is_dir())
        self.assertEqual(self.candidate_hash,
                         observe_live_files(self.live.config,retired)["runtime"])
        self.assertEqual(result,self.call())
        self.assertEqual("orphan-native-voice-evidence",
                         check_pending(self.root,self.live.ledger)["reason"])

    def test_missing_config_lock_blocks_without_intent(self):
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call(locked=False)
        self.assertFalse((self.root/runtime.NAME_RESTORE).exists())
        self.assertEqual(self.original_state,
                         (self.active/"telegram-voice-poc.state").read_bytes())

    def test_unknown_candidate_runtime_hash_blocks_before_intent(self):
        args=self.active/"dvtws.args"
        args.write_bytes(args.read_bytes()+b"\n--foreign")
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.assertFalse((self.root/runtime.NAME_RESTORE).exists())
        self.assertFalse(self.marker.exists())

    def test_power_cut_after_first_rename_recovers_and_preserves_retired(self):
        real=runtime.os.rename
        times=[0]
        def crash(src,dst):
            result=real(src,dst)
            if Path(src)==self.active:
                times[0]+=1
                raise OSError("power cut after candidate -> retired rename")
            return result
        with patch.object(runtime.os,"rename",side_effect=crash):
            with self.assertRaises(OSError):
                self.call()
        self.assertEqual(times[0],1)
        self.assertFalse(self.active.exists())
        self.assertTrue((self.root/runtime.NAME_RESTORE/"intent.sha256").exists())
        self.assertEqual("orphan-native-voice-evidence",
                         check_pending(self.root,self.live.ledger)["reason"])
        result=self.call()
        self.assertEqual("legacy-runtime-restored-config-marker-and-processes-pending",
                         result["state"])
        self.assertEqual(b"enabled\n",
                         (self.active/"telegram-voice-poc.state").read_bytes())

    def test_power_cut_after_second_rename_is_idempotent(self):
        real=runtime.os.rename
        counter=[0]
        def crash(src,dst):
            ret=real(src,dst)
            if Path(dst)==self.active:
                counter[0]+=1
                raise OSError("power cut after ready -> active rename")
            return ret
        with patch.object(runtime.os,"rename",side_effect=crash):
            with self.assertRaises(OSError):
                self.call()
        self.assertEqual(counter,[1])
        before=observe_live_files(self.live.config,self.active)["runtime"]
        self.assertEqual(before,self.call()["active_runtime_sha256"])

    def test_foreign_ready_or_retired_path_prevents_restore(self):
        suffix=self.old.previous.fixture.root.name
        # Source does not trust an existing stage from a different recovery.
        path=self.active.with_name(".voice-legacy-ready-"+("f"*20))
        path.mkdir(mode=0o700)
        # Real deterministic names are derived from WAL, not caller input.
        from voice_native_legacy_reverse_wal import inspect_legacy_reverse_wal
        from voice_native_legacy_restore_plan import inspect_legacy_restore_plan
        plan=inspect_legacy_restore_plan(self.root)
        wal=inspect_legacy_reverse_wal(
            self.root,allow_ipfw_replay=True,allow_files_stage="legacy-files-ready")
        proper=self.active.with_name(".voice-legacy-ready-"+wal["restore_plan_sha256"][:20])
        proper.mkdir(mode=0o700)
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.assertFalse((self.root/runtime.NAME_RESTORE).exists())

    def test_partial_or_tampered_runtime_intent_refuses_foreign_recovery(self):
        original=runtime._write_once
        seen=[0]
        def cut(path,body):
            seen[0]+=1
            if seen[0]==2: raise OSError("power cut before intent sha")
            return original(path,body)
        with patch.object(runtime,"_write_once",side_effect=cut):
            with self.assertRaises(OSError):
                self.call()
        self.assertTrue((self.root/runtime.NAME_RESTORE).exists())
        self.assertEqual(self.original_state,
                         (self.active/"telegram-voice-poc.state").read_bytes())
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()

    def test_foreign_kernel_or_live_config_blocks_without_mutation(self):
        self.old.previous.kernel.rules[19009]=["allow","ip","from","any","to","any"]
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.old.previous.kernel.rules.pop(19009)
        self.live.config.write_bytes(b"foreign altered Config")
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.assertFalse((self.root/runtime.NAME_RESTORE).exists())

    def test_no_public_dispatch(self):
        service=(ROOT/"src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
        self.assertNotIn("voice_native_legacy_runtime_restore.py",service)


if __name__=="__main__":
    unittest.main(verbosity=2)
