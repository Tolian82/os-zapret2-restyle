#!/usr/bin/env python3
"""Native Voice status comes only from the one shared Voice+Strategies owner."""
from __future__ import annotations

from pathlib import Path
import sys, tempfile, unittest

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

from voice_live_inspect import examine_shared
from voice_firewall_transaction import VoiceFirewallError
import importlib.util
fixture_path = ROOT / "scripts/test-voice-firewall-transaction.py"
spec = importlib.util.spec_from_file_location("voice_fixture_for_probe", fixture_path)
fixture_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture_module)
fixtures = fixture_module.fixture

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
    def test_main_refuses_historic_ledger_without_common_owner(self):
        from unittest.mock import patch
        import contextlib, io, json
        import voice_live_inspect as module
        with patch.object(module, "SharedApplyOperation") as shared:
            shared.return_value.read.return_value = None
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                rc = module.main(["voice_live_inspect.py"])
            self.assertEqual(2, rc)
            self.assertEqual("uninitialized", json.loads(output.getvalue())["state"])
            self.assertIn("common-apply-required", output.getvalue())
            self.assertNotIn("VoiceCutoverJournal", module.__dict__)
            self.assertNotIn("VoiceOwnershipStore", module.__dict__)
            shared.return_value.read.assert_called_once_with()

    def test_main_shared_owner_and_corruption_fail_closed(self):
        from unittest.mock import patch
        import contextlib, io, json
        import voice_live_inspect as module
        with patch.object(module, "SharedApplyOperation") as shared, patch.object(
            module, "examine_shared"
        ) as native:
            shared.return_value.read.return_value = {"phase": "committed"}
            native.return_value = {"state": "ready", "source": "native-common"}
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(0, module.main(["voice_live_inspect.py"]))
            self.assertEqual("ready", json.loads(output.getvalue())["state"])
            native.assert_called_once_with({"phase": "committed"})
            shared.return_value.read.side_effect = ValueError("untrusted common record")
            native.reset_mock()
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(3, module.main(["voice_live_inspect.py"]))
            self.assertEqual("inspection-error", json.loads(output.getvalue())["state"])
            native.assert_not_called()

    def test_common_owner_verified_ipfw(self):
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
            # Regression: a missing kernel IPFW module does NOT mean that
            # the stopped sealed owner has foreign rules (FreeBSD exit 71).
            absent=examine_shared(record,work_root=Path(root),
                    bundle_verify=lambda _: None,
                    manifest_reader=lambda _: manifest,
                    adapter_factory=lambda *args: FakeAdapter(manifest),
                    runtime_probe=lambda *args: {"state":"stopped","services":{}},
                    kernel_absent=lambda: True)
            self.assertEqual("stopped",absent["state"])
            self.assertEqual("common-stopped-ipfw-kernel-absent",absent["condition"])
            self.assertEqual(0,absent["rule_count"])
            self.assertFalse(absent["can_activate"])


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
