#!/usr/bin/env python3
"""Real old PoC marker installation, fsynced hardlink no-replace crash replay."""
from __future__ import annotations

import fcntl
import importlib.util
import os
from pathlib import Path
import stat
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))
import voice_native_legacy_marker_restore as marker
from voice_cutover_guard import check_pending


def fixture():
    spec=importlib.util.spec_from_file_location(
        "old_marker_config_redo_fixture",
        ROOT/"scripts/test-voice-native-legacy-config-restore.py",
    )
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


class LegacyMarkerInstallTests(unittest.TestCase):
    def setUp(self):
        self.before=fixture().OldConfigSameInodeTests()
        self.before.setUp()
        self.addCleanup(self.before.doCleanups)
        self.before.call() # actual previous Config restoration
        self.root=self.before.root
        self.live=self.before.live
        self.target=self.before.marker
        self.original=self.root/"legacy-previous/marker.bin"
        self.kernel=self.before.old.old.previous.kernel
        self.mode=stat.S_IMODE(self.original.stat().st_mode)
        self.expected=self.original.read_bytes()

    def call(self,*,locked=True):
        fd=os.open(self.live.config,os.O_RDWR)
        try:
            if locked:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return marker.restore_legacy_marker(
                root=self.root,config_path=self.live.config,config_fd=fd,
                config_owner=(os.geteuid(),os.getegid()),
                active_runtime=self.live.runtime,marker_path=self.target,
                ledger_root=self.live.ledger,
                process_probe=self.live.probe,
                readonly_ipfw=self.before.old.old.previous.readonly,
                require_lifecycle_owner=lambda:self.live.lock_calls.append("FD9"),
            )
        finally:
            os.close(fd)

    def test_exact_old_marker_restore_does_not_start_or_clear_intent(self):
        self.assertFalse(self.target.exists())
        result=self.call()
        self.assertEqual("legacy-marker-restored-old-processes-not-restarted",
                         result["state"])
        self.assertEqual(self.expected,self.target.read_bytes())
        self.assertFalse(result["safe_to_enable_voice"])
        self.assertFalse(result["safe_to_start"])
        self.assertFalse(result["whole_rollback_complete"])
        self.assertEqual("orphan-native-voice-evidence",
                         check_pending(self.root,self.live.ledger)["reason"])
        self.assertEqual(result,self.call())
        self.assertTrue((self.root/marker.MARKER_NAME/"intent.sha256").exists())

    def test_crash_after_hardlink_before_stage_unlink_is_recoverable(self):
        original=marker.os.link
        calls=[0]
        def stop_after_link(*args,**kwargs):
            original(*args,**kwargs)
            calls[0]+=1
            raise OSError("power cut after atomic no-replace link")
        with patch.object(marker.os,"link",side_effect=stop_after_link):
            with self.assertRaises(OSError):
                self.call()
        self.assertEqual(calls,[1])
        self.assertTrue(self.target.exists())
        self.assertEqual(2,self.target.stat().st_nlink)
        self.assertEqual("orphan-native-voice-evidence",
                         check_pending(self.root,self.live.ledger)["reason"])
        self.assertEqual("legacy-marker-restored-old-processes-not-restarted",
                         self.call()["state"])
        self.assertEqual(1,self.target.stat().st_nlink)
        self.assertEqual(self.expected,self.target.read_bytes())

    def test_crash_before_hardlink_replays_single_target(self):
        with patch.object(marker.os,"link",side_effect=OSError("crash before hardlink")):
            with self.assertRaises(OSError):
                self.call()
        self.assertFalse(self.target.exists())
        self.assertEqual("legacy-marker-restored-old-processes-not-restarted",
                         self.call()["state"])
        self.assertEqual(self.expected,self.target.read_bytes())

    def test_foreign_existing_marker_is_not_overwritten_or_adopted(self):
        self.target.write_bytes(b"not-ours")
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.assertEqual(b"not-ours",self.target.read_bytes())
        self.assertFalse((self.root/marker.MARKER_NAME).exists())

    def test_original_config_flock_is_required_before_marker_intent(self):
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call(locked=False)
        self.assertFalse((self.root/marker.MARKER_NAME).exists())
        self.assertFalse(self.target.exists())

    def test_modified_prior_runtime_or_ipfw_blocks_marker(self):
        self.kernel.rules[19009]=["allow","ip","from","any","to","any"]
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.kernel.rules.pop(19009)
        args=self.live.runtime/"dvtws.args"
        args.write_bytes(args.read_bytes()+b"\nforeign")
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.assertFalse(self.target.exists())

    def test_partial_intent_remains_blocked_for_manual_review(self):
        old=marker._write_once
        calls=[0]
        def crash(path,data):
            calls[0]+=1
            if calls[0]==2:
                raise OSError("power cut before intent digest")
            return old(path,data)
        with patch.object(marker,"_write_once",side_effect=crash):
            with self.assertRaises(OSError):
                self.call()
        self.assertTrue((self.root/marker.MARKER_NAME).exists())
        self.assertFalse(self.target.exists())
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()

    def test_tampered_final_marker_is_rejected_without_replacement(self):
        self.call()
        self.target.write_bytes(b"forged")
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.assertEqual(b"forged",self.target.read_bytes())

    def test_no_production_dispatch_or_automatic_restart(self):
        service=(ROOT/"src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
        self.assertNotIn("voice_native_legacy_marker_restore.py",service)


if __name__=="__main__":
    unittest.main(verbosity=2)
