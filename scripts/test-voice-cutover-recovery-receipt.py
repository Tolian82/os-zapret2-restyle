#!/usr/bin/env python3
"""Crash-persistent previous Voice receipt; original Config flock remains held."""
from __future__ import annotations

import fcntl
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import unittest

ROOT=Path(__file__).resolve().parent.parent
BACKEND=ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0,str(BACKEND))
from voice_cutover_recovery_receipt import (
    RecoveryReceiptError,read_receipt,seal_previous_receipt,NAME,
)
from voice_cutover_install_image import prepare_installable_restore
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS,PIDFILES
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_ipfw_adapter import FreeBSDIPFWAdapter


def fixture(path,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/"scripts"/path)
    assert spec and spec.loader
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


source=fixture("test-voice-cutover-runtime-bound-intent.py","receipt_schema4_fixture")
kernel_fixture=fixture("test-voice-native-ipfw-ownership.py","receipt_kernel_fixture")


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.fx=source.RuntimeBoundCutoverTests()
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.fx.begin()
        self.fx.whole.mark_mutating()
        self.image=self.fx.root/"restore-install-image"
        prepare_installable_restore(self.fx.backup,self.image,self.fx.prior)
        self.live=self.fx.root/"restored-runtime"
        shutil.copytree(self.image/"runtime",self.live)
        self.config=self.fx.root/"config.xml"
        self.instances={
            "engine":{"pid":201,"start_ns":201000000000},
            "daemon":{"pid":202,"start_ns":202000000000},
            "monitor":{"pid":203,"start_ns":203000000000},
        }
        self.state={
            "engine":{"state":"running","process":{
                **self.instances["engine"],"executable":EXPECTED_SCRIPTS["engine"]
            },"runtime_args_sha256":self.fx.prior["runtime"]},
            "supervisor":{"state":"running","daemon":{
                **self.instances["daemon"],"executable":EXPECTED_SCRIPTS["daemon"]
            },"monitor":{
                **self.instances["monitor"],"executable":EXPECTED_SCRIPTS["monitor"]
            }},
        }
        self.probe=FreeBSDVoiceProcessProbe(
            EXPECTED_SCRIPTS,PIDFILES,self.fx.backup,ps_reader=lambda _:""
        )
        self.probe.probe=lambda:self.state
        self.kernel=kernel_fixture.KernelSimulator()
        self.adapter=FreeBSDIPFWAdapter(19000,19010,runner=self.kernel)
        self.witness={
            "state":"previous-restart-integrity-observed",
            "whole_intent_phase":"mutating",
            "safe_to_finish_intent":False,"safe_to_enable_voice":False,
            "security_policy_sha256":self.fx.policy_sha,
            "instances":self.instances,
        }
        self.calls=[]

    def seal(self, *, actual_lock=True, witness=None):
        fd=os.open(self.config,os.O_RDWR)
        try:
            if actual_lock:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return seal_previous_receipt(
                journal=self.fx.whole,ledger=self.fx.ipfw,
                previous_backup=self.fx.backup,config_path=self.config,
                active_runtime=self.live,config_fd=fd,
                config_owner=(os.geteuid(),os.getegid()),
                probe=self.probe,adapter=self.adapter,
                integrity_report=witness if witness is not None else self.witness,
                require_lifecycle_owner=lambda:self.calls.append("FD9"),
            )
        finally:
            os.close(fd)

    def test_seals_exact_five_resource_receipt_before_release_and_keeps_journal(self):
        first=self.seal()
        self.assertEqual("previous-receipt-sealed",first["state"])
        receipt=read_receipt(self.fx.whole.directory)
        self.assertEqual(receipt["phase"],"observed-only")
        self.assertEqual(receipt["whole_check"],self.fx.whole.read()["check"])
        self.assertEqual(receipt["instances"],self.instances)
        self.assertEqual(receipt["previous"],self.fx.prior)
        self.assertEqual(0o600,(self.fx.whole.directory/NAME).stat().st_mode&0o777)
        self.assertEqual("mutating",self.fx.whole.read()["phase"])
        self.assertFalse(first["can_finish_intent"])
        self.assertEqual("previous-receipt-already-sealed",self.seal()["state"])
        self.assertGreaterEqual(len(self.calls),4)

    def test_missing_config_lock_or_invalid_argv_attestation_never_creates_receipt(self):
        with self.assertRaises((ValueError,RuntimeError)):
            self.seal(actual_lock=False)
        self.assertIsNone(read_receipt(self.fx.whole.directory))
        forged={**self.witness,"security_policy_sha256":"f"*64}
        with self.assertRaises(RecoveryReceiptError):
            self.seal(witness=forged)
        self.assertIsNone(read_receipt(self.fx.whole.directory))

    def test_changed_process_pid_or_kernel_refused(self):
        self.witness["instances"]={
            **self.instances,"engine":{"pid":301,"start_ns":301000000000}
        }
        with self.assertRaises(RecoveryReceiptError):
            self.seal()
        self.witness["instances"]=self.instances
        self.kernel.rules[19000]=kernel_fixture.TCP
        with self.assertRaises((ValueError,RuntimeError)):
            self.seal()
        self.assertIsNone(read_receipt(self.fx.whole.directory))

    def test_wrong_runtime_or_pending_ipfw_fails_before_receipt(self):
        (self.live/"dvtws.args").write_text("--foreign")
        with self.assertRaises((ValueError,RuntimeError)):
            self.seal()
        self.assertIsNone(read_receipt(self.fx.whole.directory))

    def test_corrupt_existing_receipt_blocks_overwrite_and_retains_intent(self):
        path=self.fx.whole.directory/NAME
        path.write_text('{"schema":1,"check":"bad"}')
        path.chmod(0o600)
        with self.assertRaises((ValueError,RuntimeError)):
            self.seal()
        self.assertEqual("mutating",self.fx.whole.read()["phase"])

    def test_schema4_committed_cannot_be_sealed(self):
        self.fx.whole.commit()
        with self.assertRaises(RecoveryReceiptError):
            self.seal()
        self.assertIsNone(read_receipt(self.fx.whole.directory))


if __name__=="__main__":
    unittest.main(verbosity=2)
