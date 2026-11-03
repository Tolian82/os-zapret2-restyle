#!/usr/bin/env python3
"""Fast negative contracts against real running-native upgrade entrypoint."""
import ast
import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "stage2-opnsense-real-native-running-upgrade.py"
spec = importlib.util.spec_from_file_location("real_running_native", SOURCE)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class GenuineRunningContracts(unittest.TestCase):
    def test_candidate_revision_and_old_published_identity(self):
        self.assertEqual(runner.REVISION, "80")
        self.assertEqual(runner.old.VERSION, "0.6.2_1")
        self.assertEqual(runner.old.ARCHIVE_SHA,
                         "1e21fbcac847529b94fea940241b4da7f86a42d33c129b7003ad04a72f4e5a0f")

    def test_refuse_without_disposable_optin_before_gate(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(
            runner.native, "gate", side_effect=AssertionError("unsafe")) as gate:
            with self.assertRaisesRegex(runner.Refusal, "OPTIN_REQUIRED"):
                runner.require_disposable()
            gate.assert_not_called()

    def test_refuse_source_revision_inconsistency(self):
        flags = {k:"1" for k in (runner.OPTIN,
                                 "ZAPRET2_STAGE0_DISPOSABLE_RUNNING_TEST",
                                 "ZAPRET2_NATIVE_BUILD_CI")}
        flags["GITHUB_ACTIONS"] = "true"
        with patch.dict(os.environ, flags), patch.object(runner.native, "gate"), patch.object(
            runner.genuine, "qualify_guest"), patch.object(runner.native, "REVISION", "old"):
            with self.assertRaisesRegex(runner.Refusal, "SOURCE_REVISION"):
                runner.require_disposable()

    def test_real_source_uses_no_fake_engine_or_mocked_pkg(self):
        s = SOURCE.read_text()
        self.assertIn('upstream.build(Path(temp))', s)
        self.assertIn('genuine.bounded_running(old.SERVICE, engine_sha)', s)
        self.assertIn('stopped.replace_with_actual_pkg(successor)', s)
        self.assertNotIn('pkg", "add", "-I"', s)
        self.assertNotIn('"--script-no-exec"', s)

    def test_only_test_owned_rule_removed_from_baseline(self):
        rules = ["00100 allow ip from any to any", "19000 divert 989 tcp from any to any 65431 out via lo0",
                 "65535 allow ip from any to any"]
        self.assertEqual(runner.unrelated_rules(rules), [rules[0], rules[2]])

    def test_foreign_rules_are_not_deleted_by_comparator(self):
        rules = ["19001 divert 989 tcp from any to any 65431 out via lo0",
                 "65535 allow ip from any to any"]
        self.assertEqual(runner.unrelated_rules(rules), rules)

    def test_process_owner_requires_genuine_old_pid(self):
        with self.assertRaisesRegex(runner.Refusal, "MISSING"):
            runner.assert_old_processes_replaced({}, 124)

    def test_process_reuse_is_refused(self):
        with self.assertRaisesRegex(runner.Refusal, "REUSED"):
            runner.assert_old_processes_replaced({124:"/real/dvtws2"}, 124)

    def test_persistent_old_process_is_refused(self):
        with patch.object(runner, "owned_process_ids", return_value={124:"/real/dvtws2"}), patch.object(
            runner.time, "sleep", return_value=None):
            with self.assertRaisesRegex(runner.Refusal, "SURVIVED_REPLACEMENT"):
                runner.assert_old_processes_replaced({124:"/real/dvtws2"}, 125)

    def test_old_process_drain_observed(self):
        with patch.object(runner, "owned_process_ids", side_effect=[
            {124:"/real/dvtws2",125:"/real/dvtws2"}, {125:"/real/dvtws2"}]), patch.object(
                runner.time, "sleep", return_value=None):
            proof = runner.assert_old_processes_replaced({124:"/real/dvtws2"}, 125)
            self.assertTrue(proof["old_processes_drained"])

    def test_live_false_status_refused_before_ipfw(self):
        with patch.object(runner.genuine, "status", return_value=(1,"zapret is not running","")), patch.object(
            runner, "fw_rules", side_effect=AssertionError("should not inspect")):
            with self.assertRaisesRegex(runner.Refusal, "NOT_RUNNING"):
                runner.verify_running_successor("0"*64, {123:"old"}, [])

    def test_running_pid_and_exact_hash_and_rule_required(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            engine = root / "dvtws2"
            engine.write_bytes(b"actual pinned genuine engine")
            pid = root / "dvtws2.pid"
            pid.write_text("98991\n")
            with patch.object(runner.genuine, "ENGINE", engine), patch.object(
                runner.genuine, "PID", pid), patch.object(
                runner.genuine, "status", return_value=(0,"zapret is running","")), patch.object(
                runner.genuine, "command", return_value=SimpleNamespace(returncode=0, stdout=str(engine)+" --port=989\n")), patch.object(
                runner, "fw_rules", return_value=["65535 allow ip from any to any"]), patch.object(
                runner, "assert_old_processes_replaced", return_value={"old_processes_drained":True}):
                with self.assertRaisesRegex(runner.Refusal, "RULE_NOT_OWNED"):
                    runner.verify_running_successor(
                        hashlib.sha256(engine.read_bytes()).hexdigest(),
                        {123:"old"}, ["65535 allow ip from any to any"])

    def test_external_ipfw_change_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); engine=root/"dvtws2"; engine.write_bytes(b"actual engine")
            pid=root/"pid"; pid.write_text("98991")
            rules=["01000 deny ip from any to any", "19000 divert 989 tcp from any to any 65431 out via lo0", "65535 allow ip from any to any"]
            with patch.object(runner.genuine,"ENGINE",engine), patch.object(runner.genuine,"PID",pid), patch.object(
                runner.genuine,"status",return_value=(0,"zapret is running","")), patch.object(
                runner.genuine,"command",return_value=SimpleNamespace(returncode=0,stdout=str(engine)+" --port=989")), patch.object(
                runner,"fw_rules",return_value=rules):
                with self.assertRaisesRegex(runner.Refusal,"UNRELATED_IPFW"):
                    runner.verify_running_successor(hashlib.sha256(engine.read_bytes()).hexdigest(),{123:"old"},["65535 allow ip from any to any"])


if __name__ == "__main__":
    unittest.main()
