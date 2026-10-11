#!/usr/bin/env python3
"""Real schema-4 PREPARED Voice forward journal with native old-five-resource witness."""
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
sys.path.insert(0,str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))
from voice_native_forward_prepare import (
    prepare_forward_voice_intent,ForwardPrepareError,
)
from voice_native_full_observer import NativePreviousObserver
from voice_native_file_observer import LiveFileObserver
from voice_native_ipfw_ownership import observe_owned_ipfw
from voice_ipfw_adapter import FreeBSDIPFWAdapter
from voice_process_recovery_evidence import inspect_process_evidence
from voice_cutover_guard import check_pending


def fixture(path,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/"scripts"/path)
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


src=fixture("test-voice-cutover-runtime-bound-intent.py","forward_schema4_source")


class EmptyIPFW:
    def __init__(self):
        self.calls=[]
        self.unexpected=False
    def __call__(self,argv,**kwargs):
        args=tuple(argv[1:])
        self.calls.append(args)
        if self.unexpected:
            return subprocess.CompletedProcess(argv,1,stdout="",stderr="Permission denied")
        if args==("-q","list"):
            return subprocess.CompletedProcess(argv,0,stdout="",stderr="")
        if len(args)==3 and args[0]=="table" and args[2]=="info":
            return subprocess.CompletedProcess(
                argv,1,stdout="",stderr=f"table {args[1]} does not exist",
            )
        raise AssertionError("unexpected IPFW command "+repr(args))


class NativeForwardPrepareTests(unittest.TestCase):
    def setUp(self):
        self.fx=src.RuntimeBoundCutoverTests()
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.raw=EmptyIPFW()
        self.adapter=FreeBSDIPFWAdapter(19000,19010,runner=self.raw)
        self.live_config=self.fx.root/"config.xml"
        self.live_runtime=self.fx.root/"runtime"
        observation=inspect_process_evidence(
            self.fx.process,self.fx.backup,src.fixture.SCRIPTS,
        )["observation"]
        # The durable on-disk report carries its schema field; the raw
        # native process probe contract returns only engine + supervisor.
        self.process_probe=src.fixture.Probe({
            role:observation[role] for role in ("engine","supervisor")
        })
        self.observer=NativePreviousObserver(
            config=self.live_config,runtime=self.live_runtime,
            previous_backup=self.fx.backup,process_evidence=self.fx.process,
            expected_executables=src.fixture.SCRIPTS,
            process_probe=self.process_probe,firewall_store=self.fx.ipfw,
            firewall_adapter=self.adapter,
            file_observer=LiveFileObserver(
                self.live_config,self.live_runtime,self.fx.backup,
            ),
        )
        self.manifest={
            "rule_base":19000,"rule_max":19010,
            "rules":{19000:["divert","989","udp","from","any","to",
                            "table(zapret2_voice_telegram)",
                            "out","not","diverted","not","sockarg","xmit","vtnet1"]},
            "tables":{"zapret2_voice_telegram":["91.108.13.10"]},
        }
        self.proof={
            **self.fx.proof,
            "schema":1,"state":"preflight-only","activation_authorized":False,
            "enabled_services":["telegram"],
            "rule_base":19000,"rule_max":19010,
            "rule_count":1,"table_count":1,
        }
        self.lock_hits=[]

    def prepare(self,*,take_lock=True):
        fd=os.open(self.live_config,os.O_RDWR)
        try:
            if take_lock:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return prepare_forward_voice_intent(
                journal=self.fx.whole,ledger=self.fx.ipfw,
                previous_backup=self.fx.backup,
                process_evidence=self.fx.process,security_evidence=self.fx.policy,
                previous_observer=self.observer,
                config_path=self.live_config,active_runtime=self.live_runtime,
                staged_config=self.fx.stage_config,candidate_runtime=self.fx.candidate,
                proof=self.proof,desired_manifest=self.manifest,
                expected_scripts=src.fixture.SCRIPTS,
                ipfw_adapter=self.adapter,config_fd=fd,
                config_owner=(os.geteuid(),os.getegid()),
                require_lifecycle_owner=lambda:self.lock_hits.append("FD9"),
            )
        finally:
            os.close(fd)

    def test_real_durable_prepared_schema4_never_mutates_runtime(self):
        prior=self.live_config.read_bytes()
        old_argv=(self.live_runtime/"dvtws.args").read_bytes()
        new_argv=self.fx.argv.read_bytes()
        result=self.prepare()
        record=self.fx.whole.read()
        self.assertEqual("native-voice-forward-prepared-not-mutating",result["state"])
        self.assertEqual(4,record["schema"])
        self.assertEqual("prepared",record["phase"])
        self.assertEqual(self.fx.prior,record["previous"])
        self.assertEqual(self.fx.policy_sha,record["candidate"]["process_security_policy_sha256"])
        self.assertEqual(record["check"],result["whole_check"])
        self.assertFalse(result["voice_on"])
        self.assertFalse(result["safe_to_mutate"])
        self.assertEqual(prior,self.live_config.read_bytes())
        self.assertEqual(old_argv,(self.live_runtime/"dvtws.args").read_bytes())
        self.assertEqual(new_argv,self.fx.argv.read_bytes())
        self.assertIsNone(self.fx.ipfw.pending())
        self.assertFalse(check_pending(self.fx.whole.directory,self.fx.ipfw.directory)["safe_to_mutate"])
        self.assertGreater(len(self.raw.calls),4)
        self.assertTrue(all(x==("-q","list") or x[0]=="table" for x in self.raw.calls))
        self.assertGreaterEqual(len(self.lock_hits),4)

    def test_refuses_existing_or_partial_previous_intent(self):
        self.prepare()
        previous=self.fx.whole.read()
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.prepare()
        self.assertEqual(previous,self.fx.whole.read())

    def test_rejects_config_lock_candidate_drift_and_wrong_voice_manifest(self):
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.prepare(take_lock=False)
        self.fx.stage_config.write_text("<other/>")
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.prepare()
        self.fx.stage_config.write_bytes(self.live_config.read_bytes())
        self.manifest["rules"].clear()
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.prepare()
        self.assertIsNone(self.fx.whole.read())

    def test_denies_old_runtime_or_sealed_process_security_mismatch(self):
        previous=self.live_runtime/"dvtws.args"
        previous.write_text("--port=980\\n")
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.prepare()
        self.assertIsNone(self.fx.whole.read())

    def test_denies_kernel_rule_or_unknown_native_owner(self):
        self.raw.unexpected=True
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.prepare()
        self.raw.unexpected=False
        self.assertIsNone(self.fx.whole.read())

    def test_power_loss_after_journal_fsync_keeps_prepared_block(self):
        real=self.fx.whole._store
        def power_cut(record):
            real(record)
            raise OSError("power cut after durable prepared intent")
        with patch.object(self.fx.whole,"_store",side_effect=power_cut):
            with self.assertRaises(OSError):
                self.prepare()
        self.assertEqual("prepared",self.fx.whole.read()["phase"])
        self.assertFalse(check_pending(self.fx.whole.directory,self.fx.ipfw.directory)["safe_to_mutate"])
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.prepare()


if __name__=="__main__":
    unittest.main(verbosity=2)
