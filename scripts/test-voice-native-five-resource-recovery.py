#!/usr/bin/env python3
"""Native Voice emergency rollback under FD9: disk fixtures, fake kernel, no mutations."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))
from voice_cutover_install_image import prepare_installable_restore
from voice_native_five_resource_recovery import (
    NativeFiveResourceRecoveryError, preflight_native_recovery,
    execute_native_recovery, main,
)
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS, PIDFILES
from voice_cutover_journal import RUNTIME_BOUND_SCHEMA
from voice_ipfw_adapter import FreeBSDIPFWAdapter
from voice_native_ipfw_ownership import KernelOwnershipError

def fixture(filename,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/"scripts"/filename)
    assert spec and spec.loader
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

schema4=fixture("test-voice-cutover-runtime-bound-intent.py","five_native_intent_fixture")
kernel=fixture("test-voice-native-ipfw-ownership.py","five_native_ipfw_fixture")


class NativeRollbackEntrypointTests(unittest.TestCase):
    def setUp(self):
        self.base=schema4.RuntimeBoundCutoverTests()
        self.base.setUp()
        self.addCleanup(self.base.doCleanups)
        self.base.begin()
        self.base.whole.mark_mutating()
        self.install=self.base.root/"restore-install-image"
        prepare_installable_restore(self.base.backup,self.install,self.base.prior)
        self.fake=kernel.KernelSimulator()
        self.reader=FreeBSDIPFWAdapter(19000,19010,runner=self.fake)
        self.writer=FreeBSDIPFWAdapter(19000,19010,runner=self.fake,allow_mutations=True)
        self.locks=[]

    def kw(self):
        return dict(
            journal=self.base.whole,ledger=self.base.ipfw,
            previous_backup=self.base.backup,process_evidence=self.base.process,
            security_evidence=self.base.policy,install_image=self.install,
            read_ipfw_adapter=self.reader,
            require_lifecycle_owner=lambda:self.locks.append("FD9"),
        )

    def test_strict_real_snapshot_preflight_with_durable_candidate_sha(self):
        result=preflight_native_recovery(**self.kw())
        self.assertEqual("eligible-for-five-resource-rollback-only",result["state"])
        self.assertEqual(result["record"]["schema"],RUNTIME_BOUND_SCHEMA)
        self.assertEqual(result["candidate_runtime_sha256"],
                         self.base.whole.read()["candidate"]["candidate_runtime_sha256"])
        self.assertEqual(result["native_candidate_proof"]["native_argv_sha256"],
                         self.base.proof["native_argv_sha256"])
        self.assertEqual(2,result["policy"]["schema"])
        self.assertFalse(result["voice_on"])
        self.assertEqual(["FD9","FD9"],self.locks)
        self.assertTrue(self.fake.calls)

    def test_foreign_ipfw_and_tampered_previous_image_denied(self):
        self.fake.rules[19000]=kernel.TCP
        with self.assertRaises((NativeFiveResourceRecoveryError,KernelOwnershipError)):
            preflight_native_recovery(**self.kw())
        self.fake.rules.clear()
        (self.install/"runtime/dvtws.args").write_text("tampered")
        with self.assertRaises((OSError,ValueError,RuntimeError)):
            preflight_native_recovery(**self.kw())
        self.assertEqual("mutating",self.base.whole.read()["phase"])

    def test_absent_lock_corrupt_policy_or_committed_journal_denied(self):
        def lost():
            raise NativeFiveResourceRecoveryError("FD9 lease absent")
        with self.assertRaisesRegex(NativeFiveResourceRecoveryError,"FD9 lease absent"):
            preflight_native_recovery(**{**self.kw(),"require_lifecycle_owner":lost})
        (self.base.policy/"policy.json").write_text("tampered")
        with self.assertRaises((OSError,ValueError,RuntimeError)):
            preflight_native_recovery(**self.kw())
        self.base.whole.commit()
        with self.assertRaises(NativeFiveResourceRecoveryError):
            preflight_native_recovery(**self.kw())

    def test_executor_receives_schema4_hash_and_always_leaves_intent(self):
        observed=[]
        def injected(**kwargs):
            observed.append(kwargs)
            return {"state":"five-previous-domains-observed",
                    "safe_to_clear_intent":False,"safe_to_enable_voice":False}
        probe=FreeBSDVoiceProcessProbe(
            EXPECTED_SCRIPTS,PIDFILES,self.base.backup,
            ps_reader=lambda _argv:""
        )
        receipt=execute_native_recovery(
            **self.kw(),config_path=self.base.root/"config.xml",
            active_runtime=self.base.root/"runtime",
            write_ipfw_adapter=self.writer,process_probe=probe,
            native_actions_factory=lambda fd:None,
            rollback_executor=injected,
        )
        self.assertEqual(receipt["state"],"five-previous-domains-observed")
        self.assertEqual(len(observed),1)
        context=observed[0]
        self.assertEqual(context["expected_candidate_runtime_sha256"],
                         self.base.whole.read()["candidate"]["candidate_runtime_sha256"])
        self.assertEqual(context["candidate_proof"]["native_argv_sha256"],
                         self.base.proof["native_argv_sha256"])
        self.assertIs(context["process_probe"],probe)
        self.assertTrue(callable(context["process_actions_factory"]))
        self.assertEqual("mutating",self.base.whole.read()["phase"])

    def test_private_command_inherits_existing_fd9_and_has_no_gui_hook(self):
        shell=(ROOT/"src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
        self.assertIn("native-voice-rollback-five)",shell)
        self.assertIn("voice_native_five_resource_recovery.py",shell)
        self.assertIn("native_voice_five_restore_service",shell)
        self.assertIn("service_with_lifecycle_lock",shell)
        self.assertIn("native-voice-recovery-quiescence|native-voice-rollback-five|",shell)
        self.assertEqual(64,main(["command","invalid"]))


if __name__=="__main__":
    unittest.main(verbosity=2)
