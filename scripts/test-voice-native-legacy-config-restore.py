#!/usr/bin/env python3
"""Old PoC Config same-inode restoration, fsynced redo and power-cut replay."""
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
import voice_native_legacy_config_restore as config
import voice_native_legacy_reverse_wal as wal
from voice_cutover_guard import check_pending
from voice_native_file_observer import observe_live_files


def fixture():
    spec=importlib.util.spec_from_file_location(
        "old_config_same_fd_runtime_fixture",
        ROOT/"scripts/test-voice-native-legacy-runtime-restore.py",
    )
    x=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(x)
    return x


class OldConfigSameInodeTests(unittest.TestCase):
    def setUp(self):
        self.old=fixture().LegacyRuntimeRestoreTests()
        self.addCleanup(self.old.doCleanups)
        original=wal.prepare_legacy_reverse_wal
        calls=[0]
        def candidate(*args,**kwargs):
            # Native candidate Config differs from sealed original BEFORE
            # the quiescent WAL is armed. Never forge a stored digest.
            calls[0]+=1
            self.assertEqual(1,calls[0])
            target=Path(kwargs["config_path"])
            target.write_bytes(target.read_bytes()+b"\n<!-- staged-candidate -->\n")
            return original(*args,**kwargs)
        with patch.object(wal,"prepare_legacy_reverse_wal",side_effect=candidate):
            self.old.setUp()
        self.assertEqual(calls,[1])
        self.old.call()  # actual two-rename runtime restore
        self.live=self.old.live
        self.root=self.old.root
        self.saved=self.root/"legacy-previous/previous/config/config.xml"
        self.config_path=self.live.config
        self.candidate_bytes=self.config_path.read_bytes()
        self.expected_bytes=self.saved.read_bytes()
        self.assertNotEqual(self.candidate_bytes,self.expected_bytes)
        self.marker=self.old.marker
        self.original_inode=self.config_path.stat().st_ino

    def call(self,*,lock=True):
        fd=os.open(self.config_path,os.O_RDWR)
        try:
            if lock:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return config.restore_legacy_config(
                root=self.root,config_path=self.config_path,config_fd=fd,
                config_owner=(os.geteuid(),os.getegid()),
                active_runtime=self.live.runtime,
                legacy_marker=self.marker,ledger_root=self.live.ledger,
                process_probe=self.live.probe,
                readonly_ipfw=self.old.old.previous.readonly,
                require_lifecycle_owner=lambda:self.live.lock_calls.append("FD9"),
            )
        finally:
            os.close(fd)

    def test_live_config_restores_exact_bytes_on_same_locked_inode(self):
        result=self.call()
        self.assertEqual("legacy-config-restored-marker-and-processes-pending",
                         result["state"])
        for flag in ("marker_restored","process_restart_verified",
                     "whole_rollback_complete","safe_to_enable_voice","public_voice_apply"):
            self.assertFalse(result[flag])
        self.assertTrue(result["config_inode_preserved"])
        self.assertEqual(self.expected_bytes,self.config_path.read_bytes())
        self.assertEqual(self.original_inode,self.config_path.stat().st_ino)
        self.assertFalse(self.marker.exists())
        self.assertEqual(result,self.call())
        self.assertTrue((self.root/config.CONFIG_NAME/"intent.sha256").exists())
        self.assertEqual("orphan-native-voice-evidence",
                         check_pending(self.root,self.live.ledger)["reason"])

    def test_power_cut_after_truncate_may_resume_empty_prefix(self):
        original=config.os.ftruncate
        def crash(fd,size):
            original(fd,size)
            raise OSError("power lost immediately after Config ftruncate")
        with patch.object(config.os,"ftruncate",side_effect=crash):
            with self.assertRaises(OSError):
                self.call()
        self.assertEqual(b"",self.config_path.read_bytes())
        self.assertTrue((self.root/config.CONFIG_NAME/"intent.sha256").exists())
        self.call()
        self.assertEqual(self.expected_bytes,self.config_path.read_bytes())
        self.assertEqual(self.original_inode,self.config_path.stat().st_ino)

    def test_power_cut_after_partial_write_is_safe_to_retry(self):
        original=config._write_all
        writes=[0]
        def partial(fd,data):
            writes[0]+=1
            os.write(fd,data[:max(1,len(data)//2)])
            raise OSError("crash after old Config prefix")
        with patch.object(config,"_write_all",side_effect=partial):
            with self.assertRaises(OSError):
                self.call()
        data=self.config_path.read_bytes()
        self.assertEqual(writes,[1])
        self.assertTrue(data)
        self.assertTrue(self.expected_bytes.startswith(data))
        self.call()
        self.assertEqual(self.expected_bytes,self.config_path.read_bytes())

    def test_foreign_partial_bytes_are_rejected_with_durable_redo(self):
        real=config.os.ftruncate
        def truncate_then_fail(fd,size):
            real(fd,size)
            raise OSError("power cut")
        with patch.object(config.os,"ftruncate",side_effect=truncate_then_fail):
            with self.assertRaises(OSError):
                self.call()
        self.config_path.write_bytes(b"FOREIGN CONTENT")
        with self.assertRaises((OSError,ValueError,RuntimeError)):
            self.call()
        self.assertEqual(b"FOREIGN CONTENT",self.config_path.read_bytes())

    def test_untrusted_config_and_missing_flock_refuse_before_intent(self):
        with self.assertRaises((OSError,ValueError,RuntimeError)):
            self.call(lock=False)
        self.assertFalse((self.root/config.CONFIG_NAME).exists())
        self.config_path.write_bytes(b"foreign content")
        with self.assertRaises((OSError,ValueError,RuntimeError)):
            self.call()
        self.assertFalse((self.root/config.CONFIG_NAME).exists())

    def test_corrupted_redo_and_native_kernel_drift_refused(self):
        self.old.old.previous.kernel.rules[19010]=["allow","ip","from","any","to","any"]
        with self.assertRaises((OSError,ValueError,RuntimeError)):
            self.call()
        self.old.old.previous.kernel.rules.pop(19010)
        original=config._write_once
        count=[0]
        def interrupt(path,data):
            count[0]+=1
            if count[0]==2: raise OSError("crash before second redo file")
            return original(path,data)
        with patch.object(config,"_write_once",side_effect=interrupt):
            with self.assertRaises(OSError):
                self.call()
        self.assertEqual(self.candidate_bytes,self.config_path.read_bytes())
        with self.assertRaises((OSError,ValueError,RuntimeError)):
            self.call()

    def test_active_marker_or_missing_runtime_blocks_config(self):
        self.marker.write_bytes(b"")
        with self.assertRaises((OSError,ValueError,RuntimeError)):
            self.call()
        self.marker.unlink()
        (self.live.runtime/"dvtws.args").write_bytes(b"foreign-args")
        with self.assertRaises((OSError,ValueError,RuntimeError)):
            self.call()
        self.assertEqual(self.candidate_bytes,self.config_path.read_bytes())

    def test_no_public_legacy_config_action(self):
        service=(ROOT/"src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
        self.assertNotIn("voice_native_legacy_config_restore.py",service)


if __name__=="__main__":
    unittest.main(verbosity=2)
