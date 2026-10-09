#!/usr/bin/env python3
"""Non-mutating-to-appliance fault injection for whole Voice cutover lifecycle.

The injected adapter models durable intent and old/new Config, dvtws2,
plugin-owned IPFW and supervisor state. NO router operations happen.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent.parent
BACKEND=ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0,str(BACKEND))
import voice_cutover_coordinator as cutover

VALID={
    "schema":1, "state":"preflight-only", "activation_authorized":False,
    "saved_xml_sha256":"a"*64, "merged_sha256":"b"*64,
    "native_argv_sha256":"c"*64, "enabled_services":["telegram"],
    "rule_base":19000, "rule_max":19010, "rule_count":3, "table_count":1,
}

class FakeLifecycle:
    def __init__(self, fail=None, legacy=False, locked=True):
        self.fail=fail
        self.legacy=legacy
        self.locked=locked
        self.calls=[]
        self.config="old"
        self.runtime="old"
        self.engine="old"
        self.supervisor="old"
        self.firewall="old"
        self.intent=None
        self.cleaned=False

    def _op(self,name,after=False):
        self.calls.append(name)
        if self.fail==name and not after:
            raise OSError(f"simulated {name} error")
        return self.fail==name and after

    def locks_held(self):
        self._op("locks_held")
        return self.locked

    def verify_legacy_absent(self):
        self._op("verify_legacy_absent")
        if self.legacy:
            raise cutover.CutoverRejected("legacy PoC is not adopted")

    def snapshot_previous(self):
        self._op("snapshot_previous")
        return {"config":"old","runtime":"old","engine":"old",
                "firewall":"old","supervisor":"old"}

    def reverify_sources(self,proof):
        self._op("reverify_sources")

    def begin_intent(self, previous,proof):
        self.intent="prepared"
        if self._op("begin_intent",after=True):
            raise OSError("failed fsync after begin")

    def mark_mutating(self):
        self.intent="mutating"
        if self._op("mark_mutating",after=True):
            raise OSError("failed fsync after mutating intent")

    def install_candidate_tree(self):
        self.runtime="new"
        if self._op("install_candidate_tree",after=True):
            raise OSError("runtime rename failed after mutation")

    def stop_previous_engine(self):
        self.engine="stopped"
        if self._op("stop_previous_engine",after=True):
            raise OSError("old engine stop failed after mutation")

    def start_candidate_engine(self):
        self.engine="new"
        if self._op("start_candidate_engine",after=True):
            raise OSError("new engine started but readiness probe failed")

    def install_owned_firewall(self):
        self.firewall="new"
        if self._op("install_owned_firewall",after=True):
            raise OSError("kernel changed before callback error")

    def start_candidate_supervisor(self):
        self.supervisor="new"
        if self._op("start_candidate_supervisor",after=True):
            raise OSError("supervisor came up but its health check failed")

    def verify_candidate(self):
        if self._op("verify_candidate"):
            raise OSError("unexpected state")
        if (self.runtime,self.engine,self.firewall,self.supervisor)!=("new",)*4:
            raise OSError("incomplete desired runtime")

    def persist_config(self):
        self.config="new"
        if self._op("persist_config",after=True):
            raise OSError("config.xml rename failed after writing")

    def commit_intent(self):
        self.intent="committed"
        if self._op("commit_intent",after=True):
            raise OSError("commit fsync uncertain")

    def cleanup_retired(self):
        self.cleaned=True
        if self._op("cleanup_retired",after=True):
            raise OSError("post-commit cleanup failed")

    def finish_intent(self):
        if self._op("finish_intent"):
            raise OSError("journal finalization failed")
        self.intent=None

    def stop_candidate(self):
        self.engine="stopped"
        self.supervisor="stopped"
        self._op("stop_candidate")

    def restore_config(self,previous):
        self.config=previous["config"]
        self._op("restore_config")

    def restore_tree(self,previous):
        self.runtime=previous["runtime"]
        self._op("restore_tree")

    def restore_owned_firewall(self,previous):
        self.firewall=previous["firewall"]
        self._op("restore_owned_firewall")

    def restore_previous_engine(self,previous):
        self.engine=previous["engine"]
        self.supervisor=previous["supervisor"]
        self._op("restore_previous_engine")

    def verify_previous(self,previous):
        if self._op("verify_previous"):
            raise OSError("failed previous state attestation")
        if (self.config,self.runtime,self.firewall,self.engine,self.supervisor)!=("old",)*5:
            raise OSError("previous appliance state is incomplete")

    def abort_intent(self):
        if self._op("abort_intent"):
            raise OSError("cannot durably erase previous intent")
        self.intent=None

    def state(self):
        return (self.config,self.runtime,self.firewall,self.engine,self.supervisor)


class WholeCutoverTests(unittest.TestCase):
    def test_real_staging_and_generator_proof_feeds_mock_cutover(self):
        """Carry real candidate/XML/ports/IPFW hashes through the mock lifecycle."""
        spec=importlib.util.spec_from_file_location(
            "voice_handoff_fixture",
            ROOT/"scripts/test-voice-handoff-preflight.py"
        )
        fixture=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)
        case=fixture.VoiceHandoffPreflightTests()
        with tempfile.TemporaryDirectory() as tmp:
            bundle, native_argv=case.build(Path(tmp)/"voice", True)
            proof=case.validate(bundle, native_argv)
            adapter=FakeLifecycle()
            outcome=cutover.simulate_cutover(adapter, proof, test_only_mutations=True)
            self.assertEqual("simulated-committed",outcome)
            self.assertEqual(["telegram"],proof["enabled_services"])
            self.assertEqual(("new",)*5,adapter.state())
            self.assertEqual([],proof.get("mutation_history",[]))
            self.assertIsNone(adapter.intent)

    def test_default_rejects_all_real_mutations(self):
        a=FakeLifecycle()
        with self.assertRaises(cutover.CutoverRejected):
            cutover.simulate_cutover(a,VALID)
        self.assertEqual([],a.calls)
        self.assertIsNone(a.intent)

    def test_explicitly_mocked_happy_path_orders_every_component(self):
        a=FakeLifecycle()
        self.assertEqual("simulated-committed",cutover.simulate_cutover(
            a,VALID,test_only_mutations=True))
        self.assertEqual(("new",)*5,a.state())
        self.assertIsNone(a.intent)
        self.assertTrue(a.cleaned)
        self.assertLess(a.calls.index("begin_intent"),a.calls.index("mark_mutating"))
        self.assertLess(a.calls.index("mark_mutating"),a.calls.index("install_candidate_tree"))
        self.assertLess(a.calls.index("start_candidate_engine"),
                        a.calls.index("install_owned_firewall"))
        self.assertLess(a.calls.index("start_candidate_supervisor"),
                        a.calls.index("persist_config"))
        self.assertLess(a.calls.index("persist_config"),a.calls.index("commit_intent"))
        self.assertLess(a.calls.index("commit_intent"),a.calls.index("cleanup_retired"))
        self.assertEqual(2,a.calls.count("verify_candidate")-1)  # two before commit, one after

    def test_missing_locks_legacy_or_unverified_sources_cannot_touch_runtime(self):
        for kwargs,fail in [({"locked":False},None),
                            ({"legacy":True},None),
                            ({}, "snapshot_previous"),
                            ({}, "reverify_sources")]:
            with self.subTest(kwargs=kwargs,fail=fail):
                a=FakeLifecycle(fail=fail,**kwargs)
                with self.assertRaises(Exception):
                    cutover.simulate_cutover(a,VALID,test_only_mutations=True)
                self.assertEqual(("old",)*5,a.state())
                self.assertIsNone(a.intent)
                self.assertNotIn("install_candidate_tree",a.calls)

    def test_all_partial_mutation_errors_restore_verified_previous_and_abort(self):
        for fault in (
            "install_candidate_tree", "stop_previous_engine",
            "start_candidate_engine", "install_owned_firewall",
            "start_candidate_supervisor", "verify_candidate", "persist_config"
        ):
            with self.subTest(fault=fault):
                a=FakeLifecycle(fail=fault)
                # verify_candidate raises on both attempts, including after
                # rollback? previous verification is a distinct method.
                with self.assertRaisesRegex(cutover.CutoverError,"restored"):
                    cutover.simulate_cutover(a,VALID,test_only_mutations=True)
                self.assertEqual(("old",)*5,a.state())
                self.assertIsNone(a.intent)
                self.assertIn("abort_intent",a.calls)
                self.assertLess(a.calls.index("restore_tree"),
                                a.calls.index("restore_owned_firewall"))
                self.assertLess(a.calls.index("restore_owned_firewall"),
                                a.calls.index("restore_previous_engine"))
                self.assertIn("verify_previous",a.calls)

    def test_rollback_failure_requires_operator_recovery_and_keeps_intent(self):
        for operation in ("restore_config","restore_tree","restore_owned_firewall",
                          "restore_previous_engine","verify_previous","abort_intent"):
            with self.subTest(operation=operation):
                class Broken(FakeLifecycle):
                    def __init__(self):
                        super().__init__(fail="install_owned_firewall")
                    def _op(self,name,after=False):
                        if name==operation:
                            self.calls.append(name)
                            raise OSError("rollback failure")
                        return super()._op(name,after)
                a=Broken()
                with self.assertRaises(cutover.CutoverManualReview):
                    cutover.simulate_cutover(a,VALID,test_only_mutations=True)
                self.assertIsNotNone(a.intent)
                self.assertIn("verify_previous",a.calls)

    def test_crash_or_uncertain_intent_writes_fail_closed(self):
        for fault in ("begin_intent","mark_mutating","commit_intent",
                      "cleanup_retired","finish_intent"):
            with self.subTest(fault=fault):
                a=FakeLifecycle(fail=fault)
                with self.assertRaises(cutover.CutoverManualReview):
                    cutover.simulate_cutover(a,VALID,test_only_mutations=True)
                self.assertIsNotNone(a.intent)
                if fault in ("begin_intent","mark_mutating"):
                    self.assertEqual(("old",)*5,a.state())
                    self.assertNotIn("install_candidate_tree",a.calls)
                elif fault in ("commit_intent","cleanup_retired","finish_intent"):
                    self.assertEqual(("new",)*5,a.state())
                    self.assertNotIn("restore_tree",a.calls)

    def test_invalid_proofs_rejected_without_any_adapter_action(self):
        for mutation in [
            {"activation_authorized":True},
            {"saved_xml_sha256":"broken"},
            {"rule_count":200},
            {"table_count":0},
            {"enabled_services":["telegram","telegram"]},
            {"enabled_services":["bad-service"]},
            {"state":"ready"},
            {"schema":2},
        ]:
            with self.subTest(mutation=mutation):
                a=FakeLifecycle()
                with self.assertRaises(cutover.CutoverRejected):
                    cutover.simulate_cutover(a,{**VALID,**mutation},
                                             test_only_mutations=True)
                self.assertEqual([],a.calls)
                self.assertIsNone(a.intent)


if __name__=="__main__":
    unittest.main(verbosity=2)
