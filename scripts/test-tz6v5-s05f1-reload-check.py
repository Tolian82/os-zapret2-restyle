#!/usr/bin/env python3
"""S05f1 source RED→GREEN: unsupported reload --check to read-only refusal."""
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
import reload_check_readonly as cli


class OriginalReloadCheck(unittest.TestCase):
    @staticmethod
    def facts(runtime, **updates):
        d = {"plugin": "installed", "engine": "valid", "config": "initialized",
             "manifest": "valid", "runtime": runtime}
        d.update(updates)
        return classify(d)

    def output(self, fact, *, json_mode=True):
        with patch.object(cli, "collect", return_value=fact):
            with patch("builtins.print") as emit:
                rc = cli.main(["reload_check_readonly.py"] +
                              (["--json"] if json_mode else []))
        return rc, emit.call_args.args[0]

    def test_stopped_always_not_running_without_start(self):
        for edits in ({}, {"plugin": "absent", "engine": "absent",
                           "config": "absent", "manifest": "missing"},
                      {"engine": "absent", "manifest": "missing"},
                      {"config": "absent", "manifest": "missing"}):
            with self.subTest(edits=edits):
                rc, raw = self.output(self.facts("STOPPED", **edits))
                row = json.loads(raw)
                self.assertEqual((rc, row["decision"], row["code"]),
                                 (1, "NOT_RUNNING", "NOT_RUNNING"))
                self.assertEqual(row["runtime_state"], "STOPPED")
                self.assertEqual(row["authorization"], "NONE")
                self.assertFalse(row["physical_transition_allowed"])
                self.assertFalse(row["semantic_diff_verified"])

    def test_running_and_unverified_never_infer_safe_or_restart(self):
        for runtime, changes in (("RUNNING", {}), ("RUNNING", {"config": "invalid"}),
                                 ("INCOMPLETE", {}), ("FOREIGN_OR_UNVERIFIED", {}),
                                 ("UNKNOWN", {})):
            with self.subTest(runtime=runtime):
                rc, raw = self.output(self.facts(runtime, **changes))
                data = json.loads(raw)
                self.assertEqual((rc, data["decision"]), (2, "REFUSE"))
                self.assertEqual(data["runtime_state"], runtime)
                self.assertEqual(data["verification"], "refused")
                self.assertFalse(data["semantic_diff_verified"])
                for forbidden in ("RELOAD_SAFE", "RESTART_REQUIRED", "--filter-"):
                    self.assertNotIn(forbidden, raw)

    def test_unknown_errors_redacted(self):
        for error in (RuntimeError("IPFW 192.0.2.11"),
                      ValueError("token=private /conf/config.xml"),
                      OSError("--filter-tcp=443")):
            with self.subTest(error=type(error).__name__):
                with patch.object(cli, "collect", side_effect=error):
                    with patch("builtins.print") as emit:
                        rc = cli.main(["reload_check_readonly.py", "--json"])
                raw = emit.call_args.args[0]
                self.assertEqual(rc, 2)
                self.assertEqual(json.loads(raw)["runtime_state"], "UNKNOWN")
                for leak in ("192.0.2.11", "token=", "/conf/", "--filter-"):
                    self.assertNotIn(leak, raw)
        with self.assertRaises(ValueError):
            cli.project_preflight({"components": {"runtime": "RUNNING"}})

    def test_plain_output_and_invalid_options_before_probe(self):
        rc, raw = self.output(self.facts("STOPPED"), json_mode=False)
        self.assertEqual((rc, raw), (1, "reload-check=NOT_RUNNING"))
        rc, raw = self.output(self.facts("RUNNING"), json_mode=False)
        self.assertEqual((rc, raw), (2, "reload-check=REFUSE"))
        with patch.object(cli, "collect", side_effect=AssertionError("no read")):
            self.assertEqual(cli.main(["reload_check_readonly.py", "--force"]), 64)
        shell = ROOT / "src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
        with tempfile.TemporaryDirectory() as tmp:
            lock = Path(tmp) / "no-new-FD9"
            env = {**os.environ, "SCRIPT_DIR": str(shell.parent),
                   "BACKEND_DIR": str(BACKEND),
                   "PYTHONDONTWRITEBYTECODE": "1",
                   "LIFECYCLE_LOCK_FILE": str(lock)}
            for argv, expected in (
                (["reload"], 69), (["reload", "--json"], 64),
                (["reload", "--force"], 64),
                (["reload", "--check", "--force"], 64),
                (["reload", "--check", "--json", "--force"], 64),
                (["reload", "--check", "--json", "--json"], 64),
                (["reload", "--check", "/conf/config.xml"], 64),
            ):
                with self.subTest(argv=argv):
                    p = subprocess.run(["/bin/sh", str(shell), *argv],
                                       capture_output=True, text=True,
                                       env=env, timeout=15)
                    self.assertEqual(p.returncode, expected, (argv, p.stderr))
                    self.assertEqual(p.stdout, "")
                    self.assertFalse(lock.exists())

    def test_original_python_entrypoint_never_writes_import_bytecode(self):
        entry = (ROOT / "src/opnsense/scripts/OPNsense/Zapret/python_runtime.sh").read_text()
        self.assertIn("PYTHONDONTWRITEBYTECODE=1", entry)
        self.assertIn("export PYTHONDONTWRITEBYTECODE", entry)
        # Preserve the exact interpreter argv; no additional -B CLI flag.
        self.assertIn('exec "${PYTHON_BIN}" "$@"', entry)

    def test_no_independent_writer_in_reader(self):
        src = Path(cli.__file__).read_text()
        for forbidden in ("subprocess", "os.kill(", "flock(", "lockf ",
                          "O_CREAT", "os.open(", "os.rename(", "SIGHUP",
                          ".write_bytes(", ".write_text(", "Config::save",
                          "RELOAD_SAFE", "RESTART_REQUIRED"):
            self.assertNotIn(forbidden, src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
