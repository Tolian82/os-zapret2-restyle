#!/usr/bin/env python3
"""S05a source RED/GREEN: typed JSON and no fictional diagnostic receipts."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))
from component_inventory import classify
import status_projection as m
import status_readonly as cli


class StatusSourceCases(unittest.TestCase):
    def facts(self, runtime, **kwargs):
        d = {"plugin": "installed", "engine": "valid", "config": "initialized",
             "manifest": "valid", "runtime": runtime}
        d.update(kwargs)
        return classify(d)

    def test_physical_runtime_codes_are_distinct_from_component_errors(self):
        cases = [
            ("STOPPED", {"plugin": "absent", "engine": "absent",
                         "config": "absent", "manifest": "missing"}, 1),
            ("STOPPED", {"engine": "absent", "manifest": "missing"}, 1),
            ("STOPPED", {"config": "absent", "manifest": "missing"}, 1),
            ("RUNNING", {"config": "invalid"}, 0),
            ("FOREIGN_OR_UNVERIFIED", {"config": "invalid"}, 2),
            ("INCOMPLETE", {}, 2),
            ("UNKNOWN", {}, 2),
        ]
        for runtime, values, exit_rc in cases:
            with self.subTest(runtime=runtime, values=values):
                report = m.project(self.facts(runtime, **values), "2026-11-23T16:00:00Z")
                self.assertEqual(report["runtime_state"], runtime)
                self.assertEqual(report["status_exit_code"], exit_rc)
                self.assertEqual(report["authorization"], "NONE")
                self.assertFalse(report["physical_transition_allowed"])
                self.assertIsNone(report["stage"])
                for name in ("generation", "operation_id", "exit_status",
                             "stderr_excerpt", "log_ref", "requested", "effective"):
                    self.assertIsNone(report[name])
                self.assertNotIn("pid", json.dumps(report).lower())
                self.assertNotIn("/conf/", json.dumps(report))

    def test_forged_original_receipts_and_input_shape_rejected(self):
        original = self.facts("RUNNING")
        bad = dict(original)
        for changes in ({"authorization": "STOP"}, {"physical_transition_allowed": True},
                        {"classification": "RUNNING"}, {"new": "foreign"}):
            tampered = dict(original, **changes)
            with self.assertRaises((m.StatusProjectionError, ValueError)):
                m.project(tampered, "2026-11-23T16:00:00Z")
        with self.assertRaises(m.StatusProjectionError):
            m.project(original, "not-a-timestamp")
        with self.assertRaises(ValueError):
            m.project({"components": {"runtime": "RUNNING"}}, "2026-11-23T16:00:00Z")

    def test_error_returns_unqualified_without_secret_exception(self):
        with patch.object(cli, "collect", side_effect=RuntimeError("secret IP 1.2.3.4")):
            with patch("builtins.print") as emit:
                rc = cli.main(["status_readonly.py"])
            self.assertEqual(rc, 2)
            raw = emit.call_args.args[0]
            actual = json.loads(raw)
            self.assertEqual(actual["code"], "STATUS_UNAVAILABLE")
            self.assertEqual(actual["runtime_state"], "UNKNOWN")
            self.assertNotIn("1.2.3.4", raw)
            self.assertNotIn("secret", raw)
            self.assertEqual(actual["authorization"], "NONE")
        with patch.object(cli, "collect", side_effect=AssertionError("must not touch")):
            self.assertEqual(cli.main(["status_readonly.py", "--force"]), 64)

    def test_invalid_status_option_rejected_before_any_fd9_dispatch(self):
        script = ROOT / "src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            env = {**os.environ, "SCRIPT_DIR": str(script.parent),
                   "BACKEND_DIR": str(BACKEND),
                   "LIFECYCLE_LOCK_FILE": str(target / "must-not-exist")}
            for args in (["status", "--force"], ["status", "--json", "--json"],
                         ["status", "--bogus"]):
                p = subprocess.run(["/bin/sh", str(script), *args],
                                   env=env, text=True, capture_output=True, timeout=12)
                self.assertEqual(p.returncode, 64, (args, p.stderr))
                self.assertFalse((target / "must-not-exist").exists())

    def test_source_contains_no_independent_writer(self):
        contents = Path(cli.__file__).read_text() + Path(m.__file__).read_text()
        for token in ("O_CREAT", "os.kill(", "fcntl.", "flock(", "lockf ",
                      "subprocess.run(", "ipfw add", ".write_bytes(", ".write_text(",
                      "Config::save", "os.rename(", "unlink("):
            self.assertNotIn(token, contents)


if __name__ == "__main__":
    unittest.main(verbosity=2)
