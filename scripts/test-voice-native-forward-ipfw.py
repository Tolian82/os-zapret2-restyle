#!/usr/bin/env python3
"""Real schema-4 forward engine-only -> native IPFW PRECOMMIT transition.

Uses actual on-disk whole journal, IPFW ownership ledger and forward-runtime
redo, with in-memory kernel adapter and simulated candidate FreeBSD process.
All real filesystem and two durable IPFW intents are exercised without
running ipfw, stopping services, or changing the host's networking.
"""
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

from voice_native_forward_ipfw import install_forward_voice_ipfw
from voice_ipfw_adapter import FreeBSDIPFWAdapter
from voice_ipfw_runtime import rollback_precommit_verified
from voice_firewall_transaction import plan_postcommit_cleanup
from voice_firewall_ledger import fingerprint, canonical_manifest


def source(name,mod):
    spec=importlib.util.spec_from_file_location(mod,ROOT/"scripts"/name)
    assert spec and spec.loader
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

previous=source("test-voice-native-candidate-engine-start.py","forward_ipfw_engine_fixture")
transaction=source("test-voice-firewall-transaction.py","forward_ipfw_kernel_fixture")


class SimulatedNativeIPFW(FreeBSDIPFWAdapter):
    """Actual adapter contract, with an in-memory scoped kernel backend."""
    def __init__(self,kernel,*,mutable=False):
        super().__init__(19000,19010,allow_mutations=mutable)
        self.kernel=kernel

    def list_rules(self,first,last):
        return self.kernel.list_rules(first,last)

    def get_table(self,name):
        return self.kernel.get_table(name)

    def create_table(self,name):
        assert self.allow_mutations
        return self.kernel.create_table(name)

    def destroy_table(self,name):
        assert self.allow_mutations
        return self.kernel.destroy_table(name)

    def add_table_entry(self,name,entry):
        assert self.allow_mutations
        return self.kernel.add_table_entry(name,entry)

    def swap_tables(self,active,stage):
        assert self.allow_mutations
        return self.kernel.swap_tables(active,stage)

    def delete_rule(self,number):
        assert self.allow_mutations
        return self.kernel.delete_rule(number)

    def add_rule(self,number,argv):
        assert self.allow_mutations
        return self.kernel.add_rule(number,argv)


class ForwardIPFWTests(unittest.TestCase):
    def setUp(self):
        self.phase=previous.CandidateEngineStartTests()
        self.phase.setUp()
        self.addCleanup(self.phase.doCleanups)
        self.phase.call()
        self.fx=self.phase.fx
        self.old=self.fx.ipfw.owned()
        self.desired=self.phase.previous.parent.manifest
        self.kernel=transaction.FakeIPFW(self.old["rules"],self.old["tables"])
        self.read=SimulatedNativeIPFW(self.kernel)
        self.write=SimulatedNativeIPFW(self.kernel,mutable=True)
        self.check_legacy=patch("voice_native_forward_ipfw.require_no_legacy")
        self.check_legacy.start()
        self.addCleanup(self.check_legacy.stop)

    def call(self,*,lock=True,desired=None):
        config=self.fx.root/"config.xml"
        fd=os.open(config,os.O_RDWR)
        try:
            if lock:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return install_forward_voice_ipfw(
                journal=self.fx.whole,ledger=self.fx.ipfw,
                previous_backup=self.fx.backup,
                active_runtime=self.fx.root/"runtime",
                staged_config=self.fx.stage_config,
                candidate_runtime=self.fx.candidate,
                config_path=config,desired_manifest=self.desired if desired is None else desired,
                probe=self.phase.probe,kernel_reader=self.phase.kernel,
                readonly_adapter=self.read,mutating_adapter=self.write,
                config_fd=fd,config_owner=(os.geteuid(),os.getegid()),
                require_lifecycle_owner=lambda:None,
            )
        finally:
            os.close(fd)

    def test_real_forward_ipfw_desired_is_pending_old_owner_preserved(self):
        report=self.call()
        self.assertEqual("candidate-ipfw-installed-pending-whole-commit",report["state"])
        self.assertFalse(report["voice_on"])
        self.assertFalse(report["can_commit"])
        self.assertFalse(report["supervisor_started"])
        self.assertEqual("mutating",self.fx.whole.read()["phase"])
        self.assertEqual(self.old,self.fx.ipfw.owned())
        pending=self.fx.ipfw.pending()
        self.assertEqual("mutating",pending["phase"])
        self.assertEqual(fingerprint(canonical_manifest(self.desired)),
                         pending["desired_sha256"])
        self.assertEqual(self.desired["rules"],self.kernel.list_rules(19000,19010))
        self.assertEqual(self.desired["tables"]["zapret2_voice_telegram"],
                         self.kernel.get_table("zapret2_voice_telegram"))
        self.assertIsNotNone(self.kernel.get_table("zapret2_voice_telegram_stage"))
        plan_postcommit_cleanup(self.write,self.old,self.desired)
        self.assertEqual("engine-only",
                         self.phase.probe.observe_candidate_engine_only()["state"])

    def test_explicit_candidate_stop_then_real_ipfw_rollback(self):
        self.call()
        # Simulate qualified native launcher_stop: NO managed engine/supervisor.
        self.phase.engine_pid=None
        self.phase.reader.commands={}
        self.assertEqual("stopped",
                         self.phase.probe.observe_candidate_engine_only()["state"])
        proof={"native_argv_sha256":self.fx.whole.read()["candidate"]["native_argv_sha256"]}
        result=rollback_precommit_verified(
            self.fx.ipfw,self.write,self.fx.whole,proof
        )
        self.assertEqual("restored-previous",result)
        self.assertEqual(self.old["rules"],self.kernel.list_rules(19000,19010))
        self.assertIsNone(self.kernel.get_table("zapret2_voice_telegram"))
        self.assertIsNone(self.kernel.get_table("zapret2_voice_telegram_stage"))
        self.assertIsNone(self.fx.ipfw.pending())
        self.assertEqual("mutating",self.fx.whole.read()["phase"])

    def test_native_ipfw_failure_rolls_back_previous_with_whole_intent(self):
        self.kernel.failure="add_rule"
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.call()
        self.assertEqual(self.old,self.fx.ipfw.owned())
        self.assertEqual(self.old["rules"],self.kernel.list_rules(19000,19010))
        self.assertFalse(self.kernel.tables)
        self.assertIsNone(self.fx.ipfw.pending())
        self.assertEqual("mutating",self.fx.whole.read()["phase"])

    def test_denies_missing_config_flock_and_wrong_owned_interval(self):
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.call(lock=False)
        self.assertEqual([],self.kernel.ops)
        self.write.rule_base=18999
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.call()
        self.assertEqual([],self.kernel.ops)

    def test_denies_changed_candidate_pid_argv_or_binary(self):
        self.phase.kernel_argv=b"/usr/bin/foreign\0"
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.call()
        self.phase.kernel_argv=("\0".join(self.phase.expected)+"\0").encode("ascii")
        self.phase.kernel_path=b"/bin/foreign\0"
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.call()
        self.assertEqual([],self.kernel.ops)

    def test_denies_supervisor_and_runtime_drift(self):
        self.phase.reader.commands[202]=previous.processes.COMMANDS[102]
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.call()
        del self.phase.reader.commands[202]
        (self.fx.root/"runtime"/"dvtws.args").write_text("--foreign\n")
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.call()
        self.assertFalse(self.kernel.ops)

    def test_denies_wrong_destination_manifest_and_divert_port(self):
        wrong={**self.desired,"rules":{19000:[
            *self.desired["rules"][19000][:1],"990",
            *self.desired["rules"][19000][2:],
        ]}}
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.call(desired=wrong)
        self.assertFalse(self.kernel.ops)

    def test_denies_foreign_live_ipfw_prior_to_ledger_write(self):
        self.kernel.rules[19005]=[
            "divert","989","udp","from","any","to","any","596",
            "out","not","diverted","not","sockarg","xmit","vtnet1"
        ]
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.call()
        self.assertIsNone(self.fx.ipfw.pending())
        self.assertFalse(self.kernel.ops)

    def test_crash_after_kernel_activation_keeps_full_pending_intent(self):
        self.call()
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.call()
        self.assertEqual("mutating",self.fx.whole.read()["phase"])
        self.assertEqual("mutating",self.fx.ipfw.pending()["phase"])
        self.assertEqual(self.desired["rules"],self.kernel.list_rules(19000,19010))


if __name__=="__main__":
    unittest.main(verbosity=2)
