#!/usr/bin/env python3
"""One original FD9+Config flock across REAL five legacy reverse executors."""
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
import voice_native_legacy_five_domain_coordinator as whole
from voice_native_legacy_reverse_wal import inspect_legacy_reverse_wal
from voice_cutover_guard import check_pending


def fixture():
    spec=importlib.util.spec_from_file_location(
        "old_five_domain_locked_process_fixture",
        ROOT/"scripts/test-voice-native-legacy-process-restart.py",
    )
    x=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(x)
    return x


class LegacySingleLockWholeRollbackTests(unittest.TestCase):
    def setUp(self):
        self.t=fixture().LegacyThreeRoleRestartTests()
        self.t.setUp()
        self.addCleanup(self.t.doCleanups)
        # Use the existing test's REAL old Config/runtime/marker fixtures,
        # but rewind only simulated live resources and stage artifacts.
        # Keep the original three fsync-sealed previous/plan/WAL records;
        # those source digests must not be regenerated or mocked.
        self.root=self.t.root
        self.live=self.t.live
        self.marker=self.t.marker
        self.ipfw=self.t.before.before.old.old.previous
        self.kernel=self.ipfw.kernel
        self.before_inode=self.live.config.stat().st_ino
        self.candidate_bytes=self.t.before.before.candidate_bytes
        wal=inspect_legacy_reverse_wal(
            self.root,allow_ipfw_replay=True,
            allow_files_stage="legacy-files-ready",
            allow_runtime_restore=True,
            allow_config_restore=True,
            allow_marker_restore=True,
        )
        retired=self.live.runtime.with_name(
            ".voice-legacy-retired-"+wal["restore_plan_sha256"][:20]
        )
        self.assertTrue(retired.is_dir())
        shutil.rmtree(self.live.runtime)
        os.rename(retired,self.live.runtime)
        self.live.config.write_bytes(self.candidate_bytes)
        self.marker.unlink()
        self.kernel.table=None
        self.kernel.rules.clear()
        self.kernel.writes.clear()
        for name in reversed(whole.STAGES[:-1]):
            shutil.rmtree(self.root/name)
        self.assertEqual(0,whole._prefix(self.root))
        self.assertFalse(self.t.running)

    def call(self, *, locked=True, runner=None):
        fd=os.open(self.live.config,os.O_RDWR)
        try:
            if locked:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return whole.recover_legacy_five_domains(
                root=self.root,config_path=self.live.config,config_fd=fd,
                config_owner=(os.geteuid(),os.getegid()),
                active_runtime=self.live.runtime,marker_path=self.marker,
                ledger_root=self.live.ledger,process_probe=self.t.probe,
                readonly_ipfw=self.ipfw.readonly,mutating_ipfw=self.ipfw.writer,
                security_reader=self.t.security,argv_reader=self.t.argv,
                require_lifecycle_owner=lambda:self.live.lock_calls.append("FD9"),
                runner=self.t.runner if runner is None else runner,
                actuator=self.t.actuator,
            )
        finally:
            os.close(fd)

    def test_real_five_domain_chain_one_locked_fd_then_idempotent_attest(self):
        result=self.call()
        self.assertEqual("legacy-five-domains-observed-receipt-and-boot-pending",
                         result["state"])
        self.assertEqual(list(whole.STAGES),result["phases_completed"])
        for label in ("safe_to_enable_voice","whole_rollback_complete",
                      "safe_to_close_intent","public_voice_apply",
                      "boot_recovery_validated","media_pass"):
            self.assertFalse(result[label])
        self.assertEqual(6,whole._prefix(self.root))
        self.assertEqual(1,self.t.calls)
        self.assertEqual([19000,19001,19002],sorted(self.kernel.rules))
        self.assertEqual(self.root.joinpath("legacy-previous/previous/config/config.xml").read_bytes(),
                         self.live.config.read_bytes())
        self.assertEqual(self.before_inode,self.live.config.stat().st_ino)
        self.assertEqual(self.root.joinpath("legacy-previous/marker.bin").read_bytes(),
                         self.marker.read_bytes())
        self.assertEqual(result,self.call())
        self.assertEqual(1,self.t.calls)
        self.assertEqual("orphan-native-voice-evidence",
                         check_pending(self.root,self.live.ledger)["reason"])

    def test_crash_during_old_kernel_then_resume_full_chain_without_duplicates(self):
        self.kernel.crash_after=4
        with self.assertRaises(OSError):
            self.call()
        self.assertEqual(1,whole._prefix(self.root))
        count=len(self.kernel.writes)
        self.kernel.crash_after=None
        self.call()
        self.assertEqual(count+2,len(self.kernel.writes))
        self.assertEqual(1,self.t.calls)
        self.assertEqual(6,whole._prefix(self.root))

    def test_crash_between_runtime_and_config_then_resume_without_second_ipfw(self):
        real=whole.restore_legacy_config
        with patch.object(whole,"restore_legacy_config",
                          side_effect=OSError("power cut before Config restore")):
            with self.assertRaises(OSError):
                self.call()
        self.assertEqual(3,whole._prefix(self.root))
        writes=len(self.kernel.writes)
        self.assertFalse(self.marker.exists())
        self.assertEqual(self.candidate_bytes,self.live.config.read_bytes())
        self.call()
        self.assertEqual(writes,len(self.kernel.writes))
        self.assertEqual(1,self.t.calls)
        self.assertEqual(6,whole._prefix(self.root))

    def test_marker_complete_before_process_start_can_resume_without_file_rewrite(self):
        with patch.object(whole,"restart_legacy_processes",
                          side_effect=OSError("power cut before process intent")):
            with self.assertRaises(OSError):
                self.call()
        self.assertEqual(5,whole._prefix(self.root))
        before=self.live.config.read_bytes()
        marker_ino=self.marker.stat().st_ino
        self.call()
        self.assertEqual(marker_ino,self.marker.stat().st_ino)
        self.assertEqual(before,self.live.config.read_bytes())
        self.assertEqual(1,self.t.calls)

    def test_partial_processes_after_durable_start_never_relaunch(self):
        def partial(argv,**kwargs):
            self.t.runner(argv,**kwargs)
            self.t.partial=True
            raise OSError("simulated power cut with partial three-role start")
        with self.assertRaises(OSError):
            self.call(runner=partial)
        self.assertEqual(6,whole._prefix(self.root))
        with self.assertRaises((OSError,RuntimeError,ValueError)):
            self.call()
        self.assertEqual(1,self.t.calls)

    def test_unknown_artifact_and_missing_config_flock_fail_closed(self):
        with self.assertRaises((OSError,RuntimeError,ValueError)):
            self.call(locked=False)
        self.assertEqual(0,whole._prefix(self.root))
        (self.root/"foreign-unbound").mkdir(mode=0o700)
        with self.assertRaises((OSError,RuntimeError,ValueError)):
            self.call()
        self.assertEqual(0,self.t.calls)
        self.assertEqual([],self.kernel.writes)

    def test_existing_final_process_receipt_rechecks_kernel_and_does_not_repeat(self):
        self.call()
        self.kernel.rules[19010]=["allow","ip","from","any","to","any"]
        with self.assertRaises((OSError,RuntimeError,ValueError)):
            self.call()
        self.assertEqual(1,self.t.calls)

    def test_no_public_entrypoint_or_false_media_pass(self):
        service=(ROOT/"src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
        self.assertNotIn("voice_native_legacy_five_domain_coordinator.py",service)


if __name__=="__main__":
    unittest.main(verbosity=2)
