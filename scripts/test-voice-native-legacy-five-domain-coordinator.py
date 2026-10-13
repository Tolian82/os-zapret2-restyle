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
from voice_native_legacy_boot_review import inspect_legacy_boot_disk, inspect_legacy_boot_live
from voice_native_legacy_rollback_route import execute_manual_legacy_rollback, main as operator_main
from voice_native_legacy_whole_receipt import (
    receipt_directory, inspect_legacy_whole_receipt, LegacyWholeReceiptError,
)


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
        self.assertEqual("legacy-five-domains-whole-receipt-sealed-boot-pending",
                         result["state"])
        self.assertEqual(list(whole.STAGES),result["phases_completed"])
        for label in ("safe_to_enable_voice",
                      "safe_to_close_intent","public_voice_apply",
                      "boot_recovery_validated","media_pass"):
            self.assertFalse(result[label])
        self.assertEqual(6,whole._prefix(self.root))
        self.assertTrue(result["whole_rollback_complete"])
        self.assertEqual("legacy-whole-receipt-disk-valid-live-recheck-required",
                         inspect_legacy_whole_receipt(self.root)["state"])
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

    def test_whole_receipt_fails_closed_on_corrupted_bytes(self):
        self.call()
        root=receipt_directory(self.root)
        record=root/"receipt.json"
        record.write_bytes(record.read_bytes()+b"foreign")
        with self.assertRaises((OSError,RuntimeError,ValueError)):
            inspect_legacy_whole_receipt(self.root)
        with self.assertRaises((OSError,RuntimeError,ValueError)):
            self.call()

    def test_whole_receipt_missing_seal_does_not_auto_repair(self):
        self.call()
        root=receipt_directory(self.root)
        (root/"receipt.sha256").unlink()
        with self.assertRaises((OSError,RuntimeError,ValueError)):
            self.call()
        self.assertFalse((root/"receipt.sha256").exists())
        self.assertEqual(1,self.t.calls)

    def test_whole_receipt_checks_sealed_source_stage_integrity(self):
        self.call()
        source=self.root/"legacy-reverse-wal"/"wal.sha256"
        source.write_bytes(source.read_bytes().replace(b"a",b"f",1))
        with self.assertRaises((OSError,RuntimeError,ValueError)):
            inspect_legacy_whole_receipt(self.root)

    def inspect_disk(self, *, locked=True):
        fd=os.open(self.live.config,os.O_RDWR)
        try:
            if locked:
                fcntl.flock(fd,fcntl.LOCK_EX | fcntl.LOCK_NB)
            return inspect_legacy_boot_disk(
                root=self.root, config_path=self.live.config,
                config_fd=fd, config_owner=(os.geteuid(),os.getegid()),
                require_lifecycle_owner=lambda:self.live.lock_calls.append("FD9"),
            )
        finally:
            os.close(fd)

    def test_legacy_boot_disk_prefix_receipt_and_no_live_claim(self):
        pre=self.inspect_disk()
        self.assertEqual("legacy-five-domain-incomplete-manual-review",pre["state"])
        self.assertEqual(0,pre["stage_directories_present"])
        self.assertFalse(pre["safe_to_start"])
        with self.assertRaises((OSError,RuntimeError,ValueError)):
            self.inspect_disk(locked=False)
        self.call()
        post=self.inspect_disk()
        self.assertEqual("legacy-whole-disk-valid-live-boot-recheck-required",post["state"])
        for key in ("safe_to_mutate","safe_to_start","safe_to_enable_voice",
                    "public_voice_apply","boot_recovery_validated","media_pass"):
            self.assertFalse(post[key])
        self.assertEqual(1,self.t.calls)

    def test_old_boot_disk_refuses_missing_stage_root_and_corrupted_receipt(self):
        self.call()
        receipt=receipt_directory(self.root)
        with patch("voice_native_legacy_boot_review.inspect_legacy_whole_receipt",
                   side_effect=RuntimeError("foreign receipt")):
            with self.assertRaises(RuntimeError):
                self.inspect_disk()
        # No implicit recovery or a process re-launch after review errors.
        self.assertTrue(receipt.is_dir())
        self.assertEqual(1,self.t.calls)

    def test_legacy_boot_review_service_stays_read_only_under_fd9(self):
        service=(ROOT/"src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
        self.assertIn("native-voice-legacy-boot-review)", service)
        self.assertIn("native-voice-legacy-boot-live-review)", service)
        self.assertIn("native_voice_legacy_boot_live_review_service", service)
        self.assertIn("native_voice_legacy_boot_review_service", service)
        self.assertIn("voice_native_legacy_boot_review.py", service)
        top=service.split('case "${1:-}" in')[-1]
        self.assertIn("|native-voice-legacy-boot-review|", top)
        self.assertIn("|native-voice-legacy-boot-live-review|", top)
        self.assertNotIn("native-voice-legacy-boot-review|runtime-failure",top)

    def test_sealed_old_receipt_live_recheck_does_not_restart_or_touch_ipfw(self):
        self.call()
        before=list(self.kernel.writes)
        fd=os.open(self.live.config,os.O_RDWR)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX | fcntl.LOCK_NB)
            args=dict(
                root=self.root, config_path=self.live.config,
                config_fd=fd, config_owner=(os.geteuid(),os.getegid()),
                active_runtime=self.live.runtime, marker_path=self.marker,
                ledger_root=self.live.ledger, process_probe=self.t.probe,
                readonly_ipfw=self.ipfw.readonly, security_reader=self.t.security,
                argv_reader=self.t.argv,
                require_lifecycle_owner=lambda:self.live.lock_calls.append("FD9"),
            )
            state=inspect_legacy_boot_live(**args)
            self.assertEqual("legacy-five-domains-live-observed-no-boot-acceptance",
                             state["state"])
            for name in ("safe_to_mutate","safe_to_start","safe_to_enable_voice",
                         "public_voice_apply","boot_recovery_validated","media_pass"):
                self.assertFalse(state[name])
            self.assertEqual(1,self.t.calls)
            self.assertEqual(before,self.kernel.writes)
            self.kernel.rules[19010]=["allow","ip","from","any","to","any"]
            with self.assertRaises((OSError,RuntimeError,ValueError)):
                inspect_legacy_boot_live(**args)
        finally:
            os.close(fd)
        self.assertEqual(1,self.t.calls)

    def test_old_live_review_does_not_start_when_receipt_absent(self):
        fd=os.open(self.live.config,os.O_RDWR)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises((OSError,RuntimeError,ValueError)):
                inspect_legacy_boot_live(
                    root=self.root,config_path=self.live.config,config_fd=fd,
                    config_owner=(os.geteuid(),os.getegid()),
                    active_runtime=self.live.runtime,marker_path=self.marker,
                    ledger_root=self.live.ledger,process_probe=self.t.probe,
                    readonly_ipfw=self.ipfw.readonly,security_reader=self.t.security,
                    argv_reader=self.t.argv,require_lifecycle_owner=lambda:None,
                )
            self.assertEqual(0,self.t.calls)
            self.assertEqual([],self.kernel.writes)
        finally:
            os.close(fd)

    def operator_call(self, *, locked=True, runner=None):
        fd=os.open(self.live.config,os.O_RDWR)
        try:
            if locked:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return execute_manual_legacy_rollback(
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

    def test_production_style_old_rollback_route_seals_while_retaining_boot_barrier(self):
        actual=self.operator_call()
        self.assertEqual("legacy-five-domains-whole-receipt-sealed-boot-pending",
                         actual["state"])
        for key in ("safe_to_enable_voice","safe_to_close_intent",
                    "boot_recovery_validated","public_voice_apply","media_pass"):
            self.assertFalse(actual[key])
        self.assertEqual(1,self.t.calls)
        self.assertTrue(receipt_directory(self.root).is_dir())
        self.assertEqual("orphan-native-voice-evidence",
                         check_pending(self.root,self.live.ledger)["reason"])
        self.assertEqual(actual,self.operator_call())
        self.assertEqual(1,self.t.calls)

    def test_operator_route_rejects_unlocked_or_foreign_wal_without_mutation(self):
        with self.assertRaises((OSError,RuntimeError,ValueError)):
            self.operator_call(locked=False)
        self.assertEqual([],self.kernel.writes)
        self.assertEqual(0,self.t.calls)
        (self.root/"foreign-intent").mkdir(mode=0o700)
        with self.assertRaises((OSError,RuntimeError,ValueError)):
            self.operator_call()
        self.assertEqual([],self.kernel.writes)
        self.assertEqual(0,self.t.calls)

    def test_operator_route_resumes_after_kernel_power_cut_without_double_start(self):
        self.kernel.crash_after=4
        with self.assertRaises((OSError,RuntimeError,ValueError)):
            self.operator_call()
        self.assertEqual(1,whole._prefix(self.root))
        self.kernel.crash_after=None
        self.operator_call()
        self.assertEqual(1,self.t.calls)
        self.assertEqual(6,whole._prefix(self.root))

    def test_operator_route_has_no_configd_gui_or_boot_entrypoint(self):
        service=(ROOT/"src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
        configd=(ROOT/"src/opnsense/service/conf/actions.d/actions_zapret.conf").read_text()
        gui=(ROOT/"src/opnsense/mvc/app/views/OPNsense/Zapret/voice.volt").read_text()
        self.assertIn("native-voice-legacy-rollback-five)",service)
        self.assertIn("native_voice_legacy_rollback_five_service",service)
        top=service.split('case "${1:-}" in')[-1]
        self.assertIn("|native-voice-legacy-rollback-five|",top)
        self.assertNotIn("native-voice-legacy-rollback-five",configd)
        self.assertNotIn("native-voice-legacy-rollback-five",gui)
        self.assertEqual(64,operator_main([]))
        self.assertEqual(64,operator_main(["rollback","/tmp/foreign"]))
        self.assertEqual(0,self.t.calls)

    def test_no_public_entrypoint_or_false_media_pass(self):
        service=(ROOT/"src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
        self.assertNotIn("voice_native_legacy_five_domain_coordinator.py",service)


if __name__=="__main__":
    unittest.main(verbosity=2)
