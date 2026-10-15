#!/usr/bin/env python3
"""Read-only live Voice IPFW inspection with fake kernel and durable journal."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

from voice_live_inspect import examine, examine_shared
from voice_firewall_ledger import VoiceOwnershipStore
from voice_cutover_journal import VoiceCutoverJournal, CutoverJournalError
from voice_firewall_transaction import VoiceFirewallError
import importlib.util
fixture_path=ROOT / "scripts/test-voice-firewall-transaction.py"
spec=importlib.util.spec_from_file_location("voice_fixture_for_probe", fixture_path)
fixture_module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture_module)
fixtures=fixture_module.fixture

class FakeAdapter:
    def __init__(self, manifest):
        self.rule_base = manifest["rule_base"]
        self.rule_max = manifest["rule_max"]
        self.rules = dict(manifest["rules"])
        self.tables = {name: list(entries) for name, entries in manifest["tables"].items()}
        self.operations = []
    def list_rules(self, first, last):
        self.operations.append("read-rules")
        return self.rules.copy()
    def get_table(self, name):
        self.operations.append("read-table")
        return self.tables.get(name)
    def rule_counters(self, number, expected):
        self.operations.append("read-counters")
        if number not in self.rules or self.rules[number] != expected:
            raise VoiceFirewallError("counter rule drift")
        return 7, 280

class InspectionTests(unittest.TestCase):
    def states(self, tmp):
        folder = Path(tmp) / "ledger"
        folder.mkdir(mode=0o700)
        store = VoiceOwnershipStore(folder)
        previous = fixtures()
        desired = fixtures(("telegram", "91.108.0.0/16"))
        return store,previous,desired
    def test_uninitialized_never_adopts_existing_rules(self):
        with tempfile.TemporaryDirectory() as d:
            store,old,new=self.states(d)
            kernel=FakeAdapter(old)
            self.assertEqual("uninitialized",examine(store,kernel)["state"])
            self.assertEqual([],kernel.operations)
    def test_verified_clean_owned_is_ready(self):
        with tempfile.TemporaryDirectory() as d:
            store,old,new=self.states(d)
            store.seed(old)
            kernel=FakeAdapter(old)
            self.assertEqual("ready",examine(store,kernel)["state"])
            self.assertTrue(examine(store,kernel)["can_activate"])
            self.assertTrue(all(op.startswith("read-") for op in kernel.operations))
    def test_unsorted_native_address_table_does_not_trigger_false_collision(self):
        with tempfile.TemporaryDirectory() as d:
            store, old, new = self.states(d)
            two = fixtures(("telegram", "91.108.0.0/16\n91.108.13.10"))
            store.seed(two)
            kernel = FakeAdapter(two)
            kernel.tables["zapret2_voice_telegram"].reverse()
            self.assertEqual("ready", examine(store, kernel)["state"])

    def test_whole_system_intent_dominates_even_healthy_ipfw_and_is_read_only(self):
        previous = {name: str(i) * 64 for i, name in
                    enumerate(("config","runtime","engine","firewall","supervisor"))}
        proof = {"saved_xml_sha256":"a"*64, "merged_sha256":"b"*64,
                 "native_argv_sha256":"c"*64}
        for phase,condition in (
            ("prepared","prepared-needs-previous-verification"),
            ("mutating","interrupted-needs-kernel-runtime-review"),
            ("committed","committed-needs-cleanup-review"),
        ):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as d:
                store,old,new=self.states(d)
                store.seed(old)
                parent=Path(d)/"cutover"
                parent.mkdir(mode=0o700)
                cutover=VoiceCutoverJournal(parent)
                cutover.begin(previous, proof)
                if phase in ("mutating","committed"):
                    cutover.mark_mutating()
                if phase=="committed":
                    cutover.commit()
                kernel=FakeAdapter(old)
                report=examine(store,kernel,cutover)
                self.assertEqual("interrupted",report["state"])
                self.assertEqual(condition,report["condition"])
                self.assertFalse(report["can_activate"])
                self.assertEqual([],kernel.operations,
                                 "whole-journal pending must block before IPFW read")
                self.assertEqual(phase,cutover.read()["phase"])

    def test_schema_two_whole_journal_blocks_even_healthy_owned_ipfw(self):
        previous = {name: str(i)*64 for i,name in enumerate(
            ("config","runtime","engine","firewall","supervisor")
        )}
        proof = {"saved_xml_sha256":"a"*64, "merged_sha256":"b"*64,
                 "native_argv_sha256":"c"*64}
        with tempfile.TemporaryDirectory() as d:
            store,old,new=self.states(d)
            store.seed(old)
            folder=Path(d)/"cutover"
            folder.mkdir(mode=0o700)
            whole=VoiceCutoverJournal(folder)
            whole.begin_bound(previous, proof, new)
            whole.mark_mutating()
            whole.commit()
            kernel=FakeAdapter(old)
            result=examine(store,kernel,whole)
            self.assertEqual("interrupted",result["state"])
            self.assertEqual("committed-needs-cleanup-review",result["condition"])
            self.assertFalse(result["can_activate"])
            self.assertEqual([],kernel.operations,
                             "pending v2 whole journal must preempt any kernel access")

    def test_whole_system_cutover_journal_absent_falls_back_to_owned_ipfw(self):
        with tempfile.TemporaryDirectory() as d:
            store,old,new=self.states(d)
            store.seed(old)
            folder=Path(d)/"cutover"
            folder.mkdir(mode=0o700)
            cutover=VoiceCutoverJournal(folder)
            kernel=FakeAdapter(old)
            self.assertEqual("ready",examine(store,kernel,cutover)["state"])
            self.assertEqual("no-intent",cutover.inspect())

    def test_foreign_rule_and_table_block(self):
        with tempfile.TemporaryDirectory() as d:
            store,old,new=self.states(d)
            store.seed(old)
            kernel=FakeAdapter(old)
            kernel.rules[19005]=["allow","ip","from","any","to","any"]
            self.assertEqual("foreign-or-modified-rules",examine(store,kernel)["state"])
            kernel.rules.pop(19005)
            kernel.tables["zapret2_voice_telegram"]=["8.8.8.8"]
            self.assertEqual("foreign-or-modified-table",examine(store,kernel)["state"])
            kernel.tables.pop("zapret2_voice_telegram")
            kernel.tables["zapret2_voice_telegram_stage"]=[]
            self.assertEqual("orphan-stage-table",examine(store,kernel)["state"])
    def test_interrupted_previous_or_partial_is_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            store,old,new=self.states(d)
            store.seed(old);store.begin(old,new);store.mark_mutating()
            kernel=FakeAdapter(old)
            report=examine(store,kernel)
            self.assertEqual("interrupted",report["state"])
            self.assertEqual("previous-intact",report["condition"])
            self.assertFalse(report["can_activate"])
            kernel.rules[19000]=new["rules"][19000]
            self.assertEqual("manual-review",examine(store,kernel)["condition"])
            self.assertTrue(all(op.startswith("read-") for op in kernel.operations))
    def test_different_rule_range_denied(self):
        with tempfile.TemporaryDirectory() as d:
            store,old,new=self.states(d)
            store.seed(old)
            kernel=FakeAdapter(old)
            kernel.rule_base=19200
            self.assertEqual("mismatched-range",examine(store,kernel)["state"])


    def test_common_owner_verified_ipfw_takes_precedence_over_old_ledger(self):
        with tempfile.TemporaryDirectory() as root:
            old = fixtures(("telegram", "91.108.0.0/16"))
            work = Path(root) / ("a"*32)
            work.mkdir(mode=0o700)
            identity = {"id":"a"*32, "page":"voice", "base":"b"*64,
                        "candidate":"c"*64, "changed_fields":["voice.telegram.enabled"]}
            (work / "plan.json").write_text(__import__("json").dumps({
                "page":"voice", "dependencies":identity["base"],
                "changed_fields":identity["changed_fields"]
            }))
            created = []
            def factory(first, last):
                self.assertEqual((first,last),(old["rule_base"],old["rule_max"]))
                fake=FakeAdapter(old)
                created.append(fake)
                return fake
            record={"schema":1,"phase":"committed","detail":identity}
            result=examine_shared(record, work_root=Path(root),
                                 bundle_verify=lambda path: self.assertEqual(path,work),
                                 manifest_reader=lambda release: old,
                                 adapter_factory=factory,
                                 runtime_probe=lambda *args: {
                                     "state":"running",
                                     "services":{"telegram":{"configured":True,"rule":19000}}
                                 })
            self.assertEqual("ready",result["state"])
            self.assertEqual(7,result["runtime"]["services"]["telegram"]["rule_packets"])
            self.assertEqual(280,result["runtime"]["services"]["telegram"]["rule_bytes"])
            self.assertEqual("native-common",result["source"])
            self.assertEqual(identity["candidate"], result["config_digest"])
            self.assertFalse(result["can_activate"],"IPFW read-only is not permission for Apply")
            self.assertTrue(created[0].operations)
            self.assertTrue(all(op.startswith("read-") for op in created[0].operations))
            fake=created[0]
            self.assertEqual(old["rules"],fake.rules)

    def test_committed_common_stop_is_normal_when_kernel_and_processes_are_empty(self):
        import json
        manifest=fixtures(("telegram", "91.108.0.0/16"))
        with tempfile.TemporaryDirectory() as root:
            identity={"id":"a"*32,"page":"voice","base":"b"*64,
                      "candidate":"c"*64,"changed_fields":[]}
            work=Path(root)/identity["id"]; work.mkdir()
            (work/"plan.json").write_text(json.dumps({
                "page":"voice","dependencies":identity["base"],
                "changed_fields":[],
            }))
            record={"schema":1,"phase":"committed","detail":identity}
            empty={"rule_base":manifest["rule_base"],
                   "rule_max":manifest["rule_max"],"rules":{},"tables":{}}
            captured=[]
            def factory(first,last):
                kernel=FakeAdapter(empty)
                captured.append(kernel)
                return kernel
            report=examine_shared(record,work_root=Path(root),
                    bundle_verify=lambda _: None,
                    manifest_reader=lambda _: manifest,
                    adapter_factory=factory,
                    runtime_probe=lambda *args: {"state":"stopped","services":{}})
            self.assertEqual("stopped",report["state"])
            self.assertEqual("common-runtime-stopped",report["condition"])
            self.assertEqual(identity["candidate"], report["config_digest"])
            self.assertEqual(0,report["rule_count"])
            self.assertEqual(0,report["table_count"])
            self.assertFalse(report["can_activate"])
            self.assertTrue(all(op.startswith("read-")
                                for op in captured[0].operations))

            # Stopped process with live IPFW is NOT an ordinary stopped owner.
            dirty=examine_shared(record,work_root=Path(root),
                    bundle_verify=lambda _: None,
                    manifest_reader=lambda _: manifest,
                    adapter_factory=lambda *args: FakeAdapter(manifest),
                    runtime_probe=lambda *args: {"state":"stopped","services":{}})
            self.assertEqual("foreign-or-modified-rules",dirty["state"])

            # A healthy kernel cannot hide a partial engine/monitor or
            # an installed runtime different from the sealed candidate.
            for state in ("partial","unverified-release"):
                with self.subTest(state=state):
                    mismatch=examine_shared(record,work_root=Path(root),
                            bundle_verify=lambda _: None,
                            manifest_reader=lambda _: manifest,
                            adapter_factory=lambda *args: FakeAdapter(manifest),
                            runtime_probe=lambda *args, current=state: {
                                "state":current,"services":{},
                            })
                    self.assertEqual("interrupted",mismatch["state"])
                    self.assertFalse(mismatch["can_activate"])

    def test_common_pending_phase_blocks_before_kernel_read(self):
        identity={"id":"a"*32,"page":"voice","base":"b"*64,
                  "candidate":"c"*64,"changed_fields":[]}
        for phase in ("prepared","activating","activated","config-saved",
                      "requires-review","restore-failed"):
            with self.subTest(phase=phase):
                record={"schema":1,"phase":phase,"detail":identity}
                result=examine_shared(record,
                        bundle_verify=lambda _: self.fail("pending read touched release"),
                        manifest_reader=lambda _: self.fail("pending read touched kernel"),
                        adapter_factory=lambda *args: self.fail("pending read touched IPFW"))
                self.assertEqual("interrupted",result["state"])
                self.assertFalse(result["can_activate"])

    def test_restored_common_predecessor_and_sealed_plan_owner_binding(self):
        import json
        with tempfile.TemporaryDirectory() as root:
            previous={"id":"b"*32,"page":"strategies","base":"c"*64,
                      "candidate":"d"*64,"changed_fields":[]}
            record={"schema":1,"phase":"restored",
                    "detail":{"id":"a"*32,"page":"voice","base":"e"*64,
                              "candidate":"f"*64,"changed_fields":[]},
                    "previous":previous}
            work=Path(root)/previous["id"]
            work.mkdir()
            (work/"plan.json").write_text(json.dumps({
                "page":previous["page"],"dependencies":previous["base"],
                "changed_fields":[]
            }))
            manifest=fixtures()
            result=examine_shared(record,work_root=Path(root),
                     bundle_verify=lambda _: None,
                     manifest_reader=lambda _: manifest,
                     adapter_factory=lambda first,last: FakeAdapter(manifest),
                     runtime_probe=lambda *args: {"state":"running","services":{}})
            self.assertEqual("ready",result["state"])
            (work/"plan.json").write_text(json.dumps({
                "page":"voice","dependencies":previous["base"],"changed_fields":[]
            }))
            with self.assertRaises(Exception):
                examine_shared(record,work_root=Path(root),
                     bundle_verify=lambda _: None,
                     manifest_reader=lambda _: manifest,
                     adapter_factory=lambda first,last: FakeAdapter(manifest),
                     runtime_probe=lambda *args: {"state":"running","services":{}})
            self.assertIsNone(examine_shared(
                {"schema":1,"phase":"restored","detail":record["detail"]}))

    def test_common_live_foreign_ipfw_never_reports_ready(self):
        import json
        manifest=fixtures(("telegram", "91.108.0.0/16"))
        with tempfile.TemporaryDirectory() as root:
            identity={"id":"a"*32,"page":"voice","base":"b"*64,
                      "candidate":"c"*64,"changed_fields":[]}
            work=Path(root)/identity["id"];work.mkdir()
            (work/"plan.json").write_text(json.dumps({
                "page":"voice","dependencies":"b"*64,"changed_fields":[]
            }))
            def wrong(first,last):
                fake=FakeAdapter(manifest)
                fake.rules[19005]=["allow","ip","from","any","to","any"]
                return fake
            result=examine_shared(
                {"schema":1,"phase":"committed","detail":identity},
                work_root=Path(root),bundle_verify=lambda _: None,
                manifest_reader=lambda _:manifest,adapter_factory=wrong,
                runtime_probe=lambda *args: {"state":"running","services":{}})
            self.assertNotEqual("ready",result["state"])
            self.assertFalse(result["can_activate"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
