#!/usr/bin/env python3
"""Legacy Telegram PoC reverse-plan is durable and strictly non-executable."""
from __future__ import annotations

import copy
import fcntl
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))
from voice_native_legacy_restore_plan import (
    _validate_old_kernel, build_legacy_restore_plan, inspect_legacy_restore_plan,
    prepare_legacy_restore_plan, LegacyRestorePlanError, PLAN_NAME,
)
from voice_cutover_guard import check_pending


def fixture():
    spec=importlib.util.spec_from_file_location(
        "legacy_original_seal_fixture",
        ROOT/"scripts/test-voice-native-legacy-previous-seal.py",
    )
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LegacyReversePlanTests(unittest.TestCase):
    def setUp(self):
        self.old=fixture().DurableOldPoCTests()
        self.old.setUp()
        self.addCleanup(self.old.doCleanups)
        self.old.capture()
        self.root=self.old.root

    def plan(self, locked=True):
        config=self.old.case.live.config
        fd=os.open(config,os.O_RDWR)
        try:
            if locked:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return prepare_legacy_restore_plan(
                self.root,config_path=config,config_fd=fd,
                config_owner=(os.geteuid(),os.getegid()),
                require_lifecycle_owner=lambda:
                    self.old.case.live.lock_calls.append("FD9"),
            )
        finally:
            os.close(fd)

    def test_reproducible_reverse_plan_sealed_without_live_mutations(self):
        config=self.old.case.live.config.read_bytes()
        marker=self.old.case.marker.read_bytes()
        table_before=self.old.case.live.fake_ipfw.rules
        result=self.plan()
        self.assertEqual("legacy-reverse-actions-sealed-not-authorized",result["state"])
        self.assertFalse(result["safe_to_execute"])
        self.assertFalse(result["rollback_implemented"])
        self.assertFalse(result["public_voice_apply"])
        self.assertEqual("legacy-previous/marker.bin",result["marker_saved_relative"])
        self.assertEqual(5,len(result["previous_five"]))
        commands=result["legacy_ipfw_commands"]
        self.assertEqual(
            ["/sbin/ipfw","-q","table","zapret2_tgvoice","create","type","addr"],
            commands[0],
        )
        self.assertEqual(2,len([c for c in commands if c[4:5]==["add"]]))
        self.assertEqual([19000,19001,19002],[int(c[3]) for c in commands if c[1]=="-qf"])
        self.assertEqual(result,inspect_legacy_restore_plan(self.root))
        self.assertEqual(config,self.old.case.live.config.read_bytes())
        self.assertEqual(marker,self.old.case.marker.read_bytes())
        self.assertEqual(table_before,self.old.case.live.fake_ipfw.rules)
        self.assertTrue(all(c[1] in ("-q","table") for c in self.old.case.live.fake_ipfw.calls))
        self.assertFalse(check_pending(self.root,self.old.case.live.ledger)["safe_to_mutate"])

    def test_old_kernel_contract_rejects_foreign_or_wrong_port(self):
        saved=build_legacy_restore_plan(self.root)
        valid={"rules":{str(c[3]):c[4:] for c in saved["legacy_ipfw_commands"]
                        if c[1]=="-qf"},
               "targets":[c[5] for c in saved["legacy_ipfw_commands"] if c[4:5]==["add"]],
               "wan":"vtnet1","port":"989"}
        # first rule is the exact legacy UDP table rule, with ordinary rules.
        _validate_old_kernel(valid,"989",valid["targets"])
        for which in ("port","wan","target","number","foreign"):
            bad=copy.deepcopy(valid)
            if which=="port": bad["port"]="990"
            if which=="wan": bad["wan"]="bad;iface"
            if which=="target": bad["targets"].append("10.0.0.0/8")
            if which=="number": bad["rules"]["19007"]=bad["rules"].pop("19002")
            if which=="foreign": bad["rules"]["19000"][6]="table(foreign)"
            with self.subTest(which=which),self.assertRaises((RuntimeError,ValueError)):
                _validate_old_kernel(bad,"989",valid["targets"])

    def test_unknown_existing_artifact_or_missing_config_flock_refused(self):
        with self.assertRaises((OSError,ValueError,RuntimeError)):
            self.plan(locked=False)
        self.assertFalse((self.root/PLAN_NAME).exists())
        self.plan()
        with self.assertRaises((OSError,ValueError,RuntimeError)):
            self.plan()
        (self.root/PLAN_NAME/"plan.json").write_bytes(b"forged")
        with self.assertRaises((OSError,ValueError,RuntimeError)):
            inspect_legacy_restore_plan(self.root)

    def test_original_managed_ipset_change_rejected(self):
        file=self.root/"legacy-previous/previous/runtime/managed/ipset-telegram.txt"
        file.write_text("91.108.13.11\n")
        with self.assertRaises((OSError,ValueError,RuntimeError)):
            build_legacy_restore_plan(self.root)
        self.assertFalse((self.root/PLAN_NAME).exists())

    def test_interrupted_seal_retains_fail_closed_evidence(self):
        import voice_native_legacy_restore_plan as module
        original=module._write_once
        count=[0]
        def crash(path,data):
            count[0]+=1
            if count[0]==2: raise OSError("power-cut-before-manifest-digest")
            return original(path,data)
        with patch.object(module,"_write_once",side_effect=crash):
            with self.assertRaises(OSError):
                self.plan()
        self.assertFalse((self.root/PLAN_NAME).exists())
        self.assertTrue(list(self.root.glob(".legacy-restore-plan-*")))
        self.assertFalse(check_pending(self.root,self.old.case.live.ledger)["safe_to_mutate"])
        with self.assertRaises((OSError,ValueError,RuntimeError)):
            self.plan()

    def test_no_wiring_to_public_apply_or_legacy_kernel_executor(self):
        module=(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend/"
                "voice_native_legacy_restore_plan.py").read_text()
        service=(ROOT/"src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
        self.assertNotIn("legacy-restore-plan",service)
        self.assertNotIn("subprocess.run(",module)
        self.assertNotIn("allow_mutations=True",module)


if __name__=="__main__":
    unittest.main(verbosity=2)
