#!/usr/bin/env python3
"""Genuine five-domain late-forward failure rollback: real files/IPFW-ledger.

Uses the real _69.._78 forward-chain candidate, real Config inode/flock,
actual durable runtime/Config rollback algorithms and in-memory IPFW. Only
the FreeBSD kernel and fixed shell native process actuator are simulated.
"""
from __future__ import annotations

import fcntl
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
BACKEND=ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0,str(BACKEND))
from voice_cutover_restore_stage import prepare_restore_stage
from voice_cutover_install_image import prepare_installable_restore
from voice_native_process_actions import FreeBSDVoiceProcessActions
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS
from voice_restart_argv_attestation import expected_engine_argv
from voice_native_supervisor_launch import canonical_supervisor_argv
from voice_native_file_observer import observe_live_files
from voice_native_forward_apply import (
    rollback_failed_precommit_voice_apply, NativeForwardApplyError,
)

def fixture(path,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/"scripts"/path)
    assert spec and spec.loader
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

prior=fixture("test-voice-native-forward-config.py","forward_failure_config_fixture")


class FailedNativeForwardRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.previous=prior.ForwardCandidateConfigTests()
        self.previous.setUp()
        self.addCleanup(self.previous.doCleanups)
        self.previous.call()  # Full candidate engine+supervisor, IPFW pending, Config new
        self.fx=self.previous.fx
        self.stage=self.previous.stage
        self.config=self.fx.root/"config.xml"
        self.prepared=self.fx.whole.read()
        self.original_inode=self.config.stat().st_ino
        self.previous_config=(self.fx.backup/"config"/"config.xml").read_bytes()
        self.restore_stage=self.fx.whole.directory/"restore-stage"
        self.install_image=self.fx.whole.directory/"restore-install-image"
        prepare_restore_stage(
            self.fx.backup,self.restore_stage,self.prepared["previous"],
        )
        prepare_installable_restore(
            self.restore_stage,self.install_image,self.prepared["previous"],
        )
        self.operations=[]
        self.old_engine=expected_engine_argv(
            self.fx.backup,EXPECTED_SCRIPTS["engine"],
        )
        self.supervisor=canonical_supervisor_argv(EXPECTED_SCRIPTS)
        self.stop_refused=False
        self.legacy=patch("voice_native_forward_apply.require_no_legacy")
        self.legacy.start()
        self.addCleanup(self.legacy.stop)

    def runner(self,argv,**kwargs):
        self.assertEqual(argv[0],"/bin/sh")
        self.assertEqual(str(self.stage.script),argv[1])
        self.assertEqual((9,),kwargs["pass_fds"])
        with self.config.open("rb+") as other:
            with self.assertRaises(BlockingIOError):
                fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)
        action=argv[-1]
        self.operations.append(action)
        if self.stop_refused:
            return subprocess.CompletedProcess(argv,1,stdout="",stderr="stopped denied")
        if action=="stop":
            self.stage.pids.update(engine=None,daemon=None,monitor=None)
            self.stage.ps.commands={}
        elif action=="start":
            self.stage.pids.update(engine=301,daemon=302,monitor=303)
            self.stage.ps.commands={
                301:" ".join(self.old_engine),
                302:" ".join(self.supervisor["daemon"]),
                303:" ".join(self.supervisor["monitor"]),
            }
        else:
            raise AssertionError("unexpected private native lifecycle action")
        return subprocess.CompletedProcess(argv,0,stdout="",stderr="")

    def recover(self):
        fd=os.open(self.config,os.O_RDWR)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            actions=FreeBSDVoiceProcessActions(
                probe=self.stage.probe,journal=self.fx.whole,
                previous_backup=self.fx.backup,
                active_runtime=self.fx.root/"runtime",
                config_path=self.config,
                config_owner=(os.geteuid(),os.getegid()),config_fd=fd,
                require_lifecycle_owner=lambda:None,
                runner=self.runner,actuator=self.stage.script,
            )
            result=rollback_failed_precommit_voice_apply(
                journal=self.fx.whole,ledger=self.fx.ipfw,
                previous_backup=self.fx.backup,
                process_evidence=self.fx.process,
                security_evidence=self.fx.policy,
                install_image=self.install_image,
                config_path=self.config,active_runtime=self.fx.root/"runtime",
                config_fd=fd,config_owner=(os.geteuid(),os.getegid()),
                probe=self.stage.probe,
                read_adapter=self.stage.parent.read,
                write_adapter=self.stage.parent.write,
                require_lifecycle_owner=lambda:None,actions=actions,
            )
            with self.config.open("rb+") as other:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return result
        finally:
            os.close(fd)

    def test_real_late_failure_restores_old_five_domains_and_retains_intent(self):
        result=self.recover()
        self.assertEqual(result["state"],"forward-failed-five-previous-domains-observed")
        self.assertEqual(self.operations,["stop","start"])
        self.assertEqual(self.config.read_bytes(),self.previous_config)
        self.assertEqual(self.config.stat().st_ino,self.original_inode)
        self.assertEqual(
            observe_live_files(self.config,self.fx.root/"runtime",
                               previous_backup=self.fx.backup),
            {k:self.prepared["previous"][k] for k in ("config","runtime")},
        )
        self.assertIsNone(self.fx.ipfw.pending())
        self.assertEqual(
            self.fx.ipfw.owned(),self.stage.parent.old,
        )
        self.assertEqual(self.fx.whole.read(),self.prepared)
        self.assertTrue((self.fx.whole.directory/"runtime-restore-redo.json").exists())
        self.assertTrue((self.fx.whole.directory/"config-restore-redo.json").exists())
        self.assertIs(result["safe_to_enable_voice"],False)

    def test_untrusted_previous_image_refused_without_any_stop(self):
        (self.install_image/"config.xml").write_bytes(b"<foreign/>")
        with self.assertRaises((RuntimeError,ValueError)):
            self.recover()
        self.assertEqual(self.operations,[])
        self.assertEqual(self.config.read_bytes(),self.previous.candidate)
        self.assertEqual(self.fx.whole.read(),self.prepared)

    def test_actuator_failure_preserves_candidate_and_recovery_journals(self):
        self.stop_refused=True
        with self.assertRaises((RuntimeError,ValueError)):
            self.recover()
        self.assertEqual(self.operations,["stop"])
        self.assertEqual(self.fx.whole.read(),self.prepared)
        self.assertIsNotNone(self.fx.ipfw.pending())
        self.assertEqual(self.config.read_bytes(),self.previous.candidate)

    def test_corrupted_kernel_blocks_failure_rollback(self):
        # Candidate IPFW ledger is still pending, but a foreign in-range
        # kernel rule must never be silently adopted as ours.
        kernel=self.stage.parent.kernel
        kernel.rules[19005]=[
            "divert","989","udp","from","any","to","any","596",
            "out","not","diverted","not","sockarg","xmit","vtnet1",
        ]
        with self.assertRaises((RuntimeError,ValueError)):
            self.recover()
        self.assertEqual(self.fx.whole.read(),self.prepared)
        self.assertEqual(self.config.read_bytes(),self.previous.candidate)


if __name__=="__main__":
    unittest.main(verbosity=2)
