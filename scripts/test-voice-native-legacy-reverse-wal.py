#!/usr/bin/env python3
"""Original-lock clean-boundary legacy reverse WAL acceptance, no executor."""
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
import voice_native_legacy_reverse_wal as wal
from voice_native_legacy_clean_wal_route import (
    seal_old_clean_boundary, main as clean_wal_main,
)
from voice_cutover_guard import check_pending
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS


def load_fixture():
    spec=importlib.util.spec_from_file_location(
        "legacy_wal_reverse_plan_fixture",
        ROOT/"scripts/test-voice-native-legacy-restore-plan.py",
    )
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CleanKernelRecoveryWALTests(unittest.TestCase):
    def setUp(self):
        self.reverse=load_fixture().LegacyReversePlanTests()
        self.reverse.setUp()
        self.addCleanup(self.reverse.doCleanups)
        self.reverse.plan()
        self.root=self.reverse.root
        self.live=self.reverse.old.case.live
        self.marker=self.reverse.old.case.marker
        self.marker.unlink()
        (self.live.runtime/"telegram-voice-poc.state").write_text("disabled\n")
        self.fake=self.live.fake_ipfw
        self.fake.rules=("00001 allow ip from any to any\n"
                         "65535 allow ip from any to any\n")
        self.fake.active.clear()
        def row(role):
            return {"pid":None,"start_ns":None,
                    "executable":EXPECTED_SCRIPTS[role]}
        stopped={"engine":{"state":"stopped","process":row("engine")},
                 "supervisor":{"state":"stopped","daemon":row("daemon"),
                               "monitor":row("monitor")}}
        self.process_patcher=patch.object(self.live.probe,"observe_processes",
                                          return_value=stopped)
        self.process_patcher.start()
        self.addCleanup(self.process_patcher.stop)

    def call(self,*,lock=True):
        fd=os.open(self.live.config,os.O_RDWR)
        try:
            if lock:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return wal.prepare_legacy_reverse_wal(
                self.root,config_path=self.live.config,config_fd=fd,
                config_owner=(os.geteuid(),os.getegid()),
                ledger_root=self.live.ledger,
                legacy_marker=self.marker,active_runtime=self.live.runtime,
                process_probe=self.live.probe,readonly_ipfw=self.live.adapter,
                require_lifecycle_owner=lambda:self.live.lock_calls.append("FD9"),
            )
        finally:
            os.close(fd)

    def test_fsync_write_once_with_exact_empty_kernel_and_three_roles(self):
        original_config=self.live.config.read_bytes()
        report=self.call()
        self.assertEqual("reverse-wal-sealed-not-executable",report["state"])
        self.assertEqual("prepared-clean-kernel-not-executable",report["phase"])
        self.assertEqual("legacy-marker-absent-and-runtime-not-enabled",
                         report["legacy_authority"])
        self.assertEqual("exact-three-role-absence",report["quiescent_processes"])
        self.assertEqual("no-native-ledger",report["native_ledger"])
        self.assertEqual(5,len(report["previous_five"]))
        for k in ("safe_to_execute","safe_to_enable_voice",
                  "safe_to_mutate","public_voice_apply"):
            self.assertIs(report[k],False)
        self.assertEqual(original_config,self.live.config.read_bytes())
        self.assertEqual(report,wal.inspect_legacy_reverse_wal(self.root))
        self.assertTrue((self.root/wal.WAL_NAME/"wal.sha256").is_file())
        self.assertTrue(all(call[1] in ("-q","table") for call in self.fake.calls))
        self.assertEqual("orphan-native-voice-evidence",
                         check_pending(self.root,self.live.ledger)["reason"])

    def test_original_config_flock_is_required_before_wal_staging(self):
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call(lock=False)
        self.assertEqual({"legacy-previous","legacy-restore-plan"},
                         set(os.listdir(self.root)))

    def test_active_legacy_marker_state_or_process_refused(self):
        self.marker.write_bytes(b"")
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.marker.unlink()
        state=self.live.runtime/"telegram-voice-poc.state"
        state.write_text("enabled\n")
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        state.write_text("disabled\n")
        self.process_patcher.stop()
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()

    def test_foreign_ipfw_rule_or_any_native_or_old_table_refused(self):
        old=self.fake.rules
        self.fake.rules="19000 allow ip from any to any\n"+old
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.fake.rules=old
        for name in ("zapret2_voice_telegram","zapret2_voice_custom_stage",
                     "zapret2_tgvoice","zapret2_tgvoice_stage"):
            with self.subTest(table=name):
                self.fake.active.add(name)
                with self.assertRaises((RuntimeError,ValueError,OSError)):
                    self.call()
                self.fake.active.remove(name)
        self.assertFalse((self.root/wal.WAL_NAME).exists())

    def test_unknown_native_ledger_or_foreign_root_is_never_adopted(self):
        self.live.ledger.mkdir(mode=0o700)
        (self.live.ledger/"orphan").write_text("unknown")
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        (self.live.ledger/"orphan").unlink()
        (self.root/"alien").write_text("unknown")
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.assertFalse((self.root/wal.WAL_NAME).exists())

    def test_power_cut_keeps_partial_wal_and_blocks_retry(self):
        original=wal._write_once
        times=[0]
        def crash(path,data):
            times[0]+=1
            if times[0]==2: raise OSError("simulated power-cut")
            return original(path,data)
        with patch.object(wal,"_write_once",side_effect=crash):
            with self.assertRaises(OSError):
                self.call()
        self.assertFalse((self.root/wal.WAL_NAME).exists())
        self.assertTrue(list(self.root.glob(".legacy-reverse-wal-*")))
        self.assertFalse(check_pending(self.root,self.live.ledger)["safe_to_mutate"])
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()

    def test_reopen_tamper_and_repeat_seal_refused(self):
        first=self.call()
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.assertEqual(first,wal.inspect_legacy_reverse_wal(self.root))
        path=self.root/wal.WAL_NAME/"wal.json"
        path.write_bytes(path.read_bytes().replace(
            b"prepared-clean-kernel-not-executable",
            b"mutating-allowed-without-owner"))
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            wal.inspect_legacy_reverse_wal(self.root)

    def operator_seal(self, *, locked=True):
        fd=os.open(self.live.config,os.O_RDWR)
        try:
            if locked:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return seal_old_clean_boundary(
                root=self.root,config_path=self.live.config,config_fd=fd,
                config_owner=(os.geteuid(),os.getegid()),
                ledger_root=self.live.ledger,marker_path=self.marker,
                active_runtime=self.live.runtime,process_probe=self.live.probe,
                readonly_ipfw=self.live.adapter,
                require_lifecycle_owner=lambda:self.live.lock_calls.append("FD9"),
            )
        finally:
            os.close(fd)

    def test_manual_operator_seals_full_clean_boundary_without_kernel_mutation(self):
        before=self.live.config.read_bytes()
        rules=self.fake.rules
        result=self.operator_seal()
        self.assertEqual("legacy-clean-boundary-wal-sealed-reverse-owner-pending",
                         result["state"])
        for name in ("safe_to_execute","safe_to_mutate","safe_to_enable_voice",
                     "public_voice_apply","boot_recovery_validated","media_pass"):
            self.assertFalse(result[name])
        self.assertEqual({"legacy-previous","legacy-restore-plan",
                          "legacy-reverse-wal"},set(os.listdir(self.root)))
        self.assertEqual(before,self.live.config.read_bytes())
        self.assertEqual(rules,self.fake.rules)
        self.assertFalse(self.marker.exists())
        self.assertFalse(check_pending(self.root,self.live.ledger)["safe_to_mutate"])
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.operator_seal()

    def test_manual_operator_requires_original_config_flock(self):
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.operator_seal(locked=False)
        self.assertFalse((self.root/wal.WAL_NAME).exists())

    def test_manual_operator_never_accepts_active_old_marker_or_ipfw(self):
        self.marker.write_bytes(b"")
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.operator_seal()
        self.marker.unlink()
        self.fake.rules="19000 allow ip from any to any\n"+self.fake.rules
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.operator_seal()
        self.assertFalse((self.root/wal.WAL_NAME).exists())

    def test_manual_operator_retains_interrupted_wal_without_retry(self):
        with patch.object(wal,"_write_once",side_effect=OSError("power-cut")):
            with self.assertRaises(OSError):
                self.operator_seal()
        self.assertTrue(list(self.root.glob(".legacy-reverse-wal-*")))
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.operator_seal()
        self.assertFalse(check_pending(self.root,self.live.ledger)["safe_to_mutate"])

    def test_manual_clean_wal_only_under_existing_fd9_not_gui_or_boot(self):
        service=(ROOT/"src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
        configd=(ROOT/"src/opnsense/service/conf/actions.d/actions_zapret.conf").read_text()
        gui=(ROOT/"src/opnsense/mvc/app/views/OPNsense/Zapret/voice.volt").read_text()
        self.assertIn("native-voice-legacy-seal-clean-wal)",service)
        self.assertIn("native_voice_legacy_seal_clean_wal_service",service)
        self.assertIn("|native-voice-legacy-seal-clean-wal|",service)
        self.assertNotIn("native-voice-legacy-seal-clean-wal",configd)
        self.assertNotIn("native-voice-legacy-seal-clean-wal",gui)
        self.assertEqual(64,clean_wal_main([]))
        self.assertEqual(64,clean_wal_main(["seal-clean-wal","/tmp/alien"]))
        self.assertFalse((self.root/wal.WAL_NAME).exists())

    def test_no_automatic_wiring_and_no_mutating_ipfw(self):
        source=(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend/"
                "voice_native_legacy_reverse_wal.py").read_text()
        service=(ROOT/"src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
        self.assertNotIn("native-voice-legacy-reverse-wal-autostart",service)
        self.assertNotIn("subprocess.run(",source)
        self.assertNotIn("modifying=True",source)
        self.assertNotIn("allow_mutations=True",source)


if __name__=="__main__":
    unittest.main(verbosity=2)
