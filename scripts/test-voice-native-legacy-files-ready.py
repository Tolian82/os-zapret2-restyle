#!/usr/bin/env python3
"""After durable IPFW replay, stage exact old Config/runtime/marker without activation."""
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
import voice_native_legacy_files_ready as files
from voice_cutover_guard import check_pending
from voice_native_live_ipfw import OLD_TABLE


def load_fixture():
    spec=importlib.util.spec_from_file_location(
        "legacy_previous_files_replay_fixture",
        ROOT/"scripts/test-voice-native-legacy-ipfw-replay.py",
    )
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PreviousFilesReadyTests(unittest.TestCase):
    def setUp(self):
        self.previous=load_fixture().LegacyReplayTests()
        self.previous.setUp()
        self.addCleanup(self.previous.doCleanups)
        self.live=self.previous.live
        self.root=self.previous.root
        self.old_marker=self.root/"legacy-previous/marker.bin"
        self.config_before=self.live.config.read_bytes()
        self.runtime_before=(self.live.runtime/"telegram-voice-poc.state").read_bytes()

    def call(self,*,lock=True):
        fd=os.open(self.live.config,os.O_RDWR)
        try:
            if lock:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return files.stage_legacy_previous_files(
                root=self.root,config_path=self.live.config,config_fd=fd,
                config_owner=(os.geteuid(),os.getegid()),
                active_runtime=self.live.runtime,
                legacy_marker=self.previous.fixture.marker,
                ledger_root=self.live.ledger,
                process_probe=self.live.probe,
                readonly_ipfw=self.previous.readonly,
                require_lifecycle_owner=lambda:self.live.lock_calls.append("FD9"),
            )
        finally:
            os.close(fd)

    def test_end_to_end_real_legacy_ipfw_then_old_file_image_sealed(self):
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call() # IPFW replay not yet completed
        self.previous.call()
        result=self.call()
        self.assertEqual("legacy-previous-files-staged-not-installed",result["state"])
        for name in ("safe_to_install","safe_to_start","safe_to_enable_voice",
                     "whole_rollback_complete","public_voice_apply"):
            self.assertFalse(result[name])
        path=self.root/files.FILES_NAME
        self.assertTrue((path/"restore-stage/config/config.xml").is_file())
        self.assertTrue((path/"install-image/config.xml").is_file())
        self.assertTrue((path/"install-image/runtime/dvtws.args").is_file())
        self.assertEqual(self.old_marker.read_bytes(),(path/"marker.bin").read_bytes())
        self.assertEqual(self.config_before,self.live.config.read_bytes())
        self.assertEqual(self.runtime_before,
                         (self.live.runtime/"telegram-voice-poc.state").read_bytes())
        self.assertFalse(self.previous.fixture.marker.exists())
        self.assertEqual(result,files.inspect_legacy_files_ready(self.root))
        self.assertEqual("orphan-native-voice-evidence",
                         check_pending(self.root,self.live.ledger)["reason"])
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()

    def test_conflicting_kernel_or_native_table_blocks_file_stage(self):
        self.previous.call()
        self.previous.kernel.rules[19007]=["allow","ip","from","any","to","any"]
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.previous.kernel.rules.pop(19007)
        self.previous.kernel.native.add("zapret2_voice_telegram")
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.assertFalse((self.root/files.FILES_NAME).exists())

    def test_marker_or_process_resurrection_is_not_accepted(self):
        self.previous.call()
        self.previous.fixture.marker.write_bytes(b"")
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.previous.fixture.marker.unlink()
        self.previous.fixture.process_patcher.stop()
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.assertFalse((self.root/files.FILES_NAME).exists())

    def test_original_config_lock_is_mandatory(self):
        self.previous.call()
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call(lock=False)
        self.assertFalse((self.root/files.FILES_NAME).exists())

    def test_power_cut_mid_image_leaves_blocking_stage_and_no_installs(self):
        self.previous.call()
        with patch.object(files,"prepare_installable_restore",
                          side_effect=OSError("power cut after file-stage")):
            with self.assertRaises(OSError):
                self.call()
        self.assertTrue(list(self.root.glob(".legacy-files-ready-*")))
        self.assertFalse((self.root/files.FILES_NAME).exists())
        self.assertEqual(self.config_before,self.live.config.read_bytes())
        self.assertEqual("orphan-native-voice-evidence",
                         check_pending(self.root,self.live.ledger)["reason"])
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()

    def test_tampered_saved_file_or_marker_detected_on_inspection(self):
        self.previous.call()
        self.call()
        marker=self.root/files.FILES_NAME/"marker.bin"
        marker.write_bytes(b"forgery")
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            files.inspect_legacy_files_ready(self.root)

    def test_absent_production_entrypoint(self):
        service=(ROOT/"src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
        self.assertNotIn("legacy-files-ready",service)
        self.assertNotIn("voice_native_legacy_files_ready.py",service)


if __name__=="__main__":
    unittest.main(verbosity=2)
