#!/usr/bin/env python3
"""Stage 5 installed evidence bridge: non-mutating parsing and fail-closed tests."""
from __future__ import annotations

from copy import deepcopy
from contextlib import redirect_stdout
import io
import importlib.util
import json
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "stage5_installed_evidence", ROOT / "stage5-installed-evidence.py"
)
assert spec is not None and spec.loader is not None
evidence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evidence)


def snapshot(packets=12, bytes_=1100):
    services = {
        name: {"configured": False, "capture_verified": False,
               "runtime_state": "disabled", "media_verified": False}
        for name in evidence.SERVICES
    }
    services["telegram"] = {
        "configured": True, "capture_verified": True,
        "runtime_state": "engine-present", "media_verified": False,
        "rule": 19000, "rule_packets": packets, "rule_bytes": bytes_,
        "profile_id": "voice-telegram", "wan": "vtnet1",
        "udp_ports": "596-599", "ipset_entries": 2,
    }
    return {
        "state": "ready", "source": "native-common",
        "config_digest": "a" * 64,
        "installed_plugin_version": "0.6.1_12",
        "rule_count": 3, "table_count": 1,
        "runtime": {
            "state": "running", "engine_verified": True,
            "supervisor_verified": True, "source_verified": True,
            "call_verified": False, "services": services,
        },
    }


class InstalledEvidenceTests(unittest.TestCase):
    def test_activity_does_not_falsely_claim_ipv6_or_full_acceptance(self):
        before = snapshot()
        after = snapshot(15, 1500)
        result = evidence.compare(before, after)
        self.assertEqual("READ_ONLY_OBSERVATION", result["status"])
        self.assertEqual("OPEN", result["stage5_installed_acceptance"])
        self.assertIs(result["ipv6_packet_proven"], False)
        self.assertEqual("COUNTERS_INCREASED_FAMILY_UNKNOWN", result["voice_activity"])
        self.assertEqual({"packets": 3, "bytes": 400}, result["counter_deltas"]["telegram"])
        self.assertNotIn("PASS", result["status"])

    def test_unchanged_counter_is_truthful_inconclusive(self):
        result = evidence.compare(snapshot(), snapshot())
        self.assertEqual("NO_COUNTER_INCREASE_OBSERVED", result["voice_activity"])
        self.assertFalse(result["ipv6_packet_proven"])

    def test_unavailable_native_rule_counter_is_not_invented(self):
        before, after = snapshot(), snapshot()
        del before["runtime"]["services"]["telegram"]["rule_packets"]
        result = evidence.compare(before, after)
        self.assertEqual(["telegram"], result["counter_unavailable"])
        self.assertEqual({}, result["counter_deltas"])

    def test_foreign_changed_config_rules_or_tables_rejected(self):
        for key, value in [
            ("config_digest", "b" * 64),
            ("rule_count", 4),
            ("table_count", 2),
            ("installed_plugin_version", "0.6.1_6"),
        ]:
            with self.subTest(key=key):
                after = snapshot()
                after[key] = value
                with self.assertRaises(evidence.EvidenceError):
                    evidence.compare(snapshot(), after)
        after = snapshot()
        after["runtime"]["services"]["telegram"]["rule"] = 19001
        with self.assertRaises(evidence.EvidenceError):
            evidence.compare(snapshot(), after)
        for key, value in (("wan", "vtnet2"), ("udp_ports", "500-501")):
            with self.subTest(key=key):
                after = snapshot()
                after["runtime"]["services"]["telegram"][key] = value
                with self.assertRaises(evidence.EvidenceError):
                    evidence.compare(snapshot(), after)

    def test_counter_reset_cannot_masquerade_as_activity(self):
        with self.assertRaisesRegex(evidence.EvidenceError, "counter reset"):
            evidence.compare(snapshot(), snapshot(1, 100))

    def test_closed_or_unverified_owner_is_rejected(self):
        for field, value in [
            ("state", "stopped"),
            ("source", "legacy-ledger"),
            ("config_digest", "-"),
        ]:
            with self.subTest(field=field):
                after = snapshot()
                after[field] = value
                with self.assertRaises(evidence.EvidenceError):
                    evidence.compare(snapshot(), after)
        after = snapshot()
        after["runtime"]["engine_verified"] = False
        with self.assertRaises(evidence.EvidenceError):
            evidence.compare(snapshot(), after)

    def test_invalid_json_oversize_and_nonregular_file_fail_closed(self):
        with self.assertRaises(evidence.EvidenceError):
            evidence._parse_snapshot(b"{", "broken")
        with self.assertRaises(evidence.EvidenceError):
            evidence._parse_snapshot(b"x" * (evidence.MAX_SNAPSHOT + 1), "oversize")
        with tempfile.TemporaryDirectory() as root:
            regular = Path(root) / "before.json"
            regular.write_text(json.dumps(snapshot()), encoding="utf-8")
            self.assertEqual("ready", evidence._read_snapshot(str(regular), "a")["state"])
            alias = Path(root) / "alias"
            alias.symlink_to(regular)
            with self.assertRaises(evidence.EvidenceError):
                evidence._read_snapshot(str(alias), "symlink")

    def test_collect_uses_actual_python311_or_313_without_new_interpreter(self):
        # Owner's diagnostic host has python3.11, not python3.13.
        # Before the fix, collect() required the absent hard-coded 3.13 path.
        for executable in ("/usr/local/bin/python3.11", "/usr/local/bin/python3.13"):
            with self.subTest(executable=executable):
                responses = (
                    subprocess.CompletedProcess([], 0, b"0.6.1_12\n", b""),
                    subprocess.CompletedProcess([], 0, json.dumps(snapshot()).encode(), b""),
                )
                with patch.object(evidence.platform, "system", return_value="FreeBSD"), \
                     patch.object(evidence.os, "geteuid", return_value=0), \
                     patch.object(evidence.sys, "executable", executable), \
                     patch.object(evidence.Path, "is_file", return_value=True), \
                     patch.object(evidence.subprocess, "run", side_effect=responses) as commands, \
                     redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(0, evidence.collect())
                self.assertEqual([executable, evidence.INSTALLED_INSPECTOR],
                                 commands.call_args_list[1].args[0])
                self.assertEqual("ready", json.loads(output.getvalue())["state"])

    def test_collect_refuses_missing_running_interpreter_without_inspection(self):
        with patch.object(evidence.platform, "system", return_value="FreeBSD"), \
             patch.object(evidence.os, "geteuid", return_value=0), \
             patch.object(evidence.Path, "is_file", return_value=False), \
             patch.object(evidence.subprocess, "run") as commands:
            with self.assertRaisesRegex(evidence.EvidenceError, "Python or Voice"):
                evidence.collect()
            commands.assert_not_called()

    def test_collect_does_not_run_commands_on_non_freebsd(self):
        with patch.object(evidence.platform, "system", return_value="Linux"), \
             patch.object(evidence.subprocess, "run") as commands:
            with self.assertRaises(evidence.EvidenceError):
                evidence.collect()
            commands.assert_not_called()

    def test_comparison_does_not_call_kernel_or_shell(self):
        with patch.object(evidence.subprocess, "run") as commands:
            evidence.compare(snapshot(), snapshot(13, 1200))
            commands.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
