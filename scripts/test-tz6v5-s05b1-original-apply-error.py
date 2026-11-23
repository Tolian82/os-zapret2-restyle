#!/usr/bin/env python3
"""S05b1 source RED/GREEN for original durable Apply failure projection."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

from component_inventory import classify
from shared_apply_operation import SharedApplyOperation, SharedOperationError
import status_error_original as reader
import status_readonly as cli


def qualified():
    return classify({"plugin": "installed", "engine": "valid",
                     "config": "initialized", "manifest": "stale",
                     "runtime": "INCOMPLETE"})


def detail(page="strategies"):
    return {"id": "a" * 32, "page": page, "base": "b" * 64,
            "candidate": "c" * 64, "changed_fields": ["general.enabled"]}


class NativeOriginalJournalSource(unittest.TestCase):
    def test_real_original_journal_writer_failure_phases(self):
        for phase in ("restore-failed", "requires-review"):
            for page in ("strategies", "voice"):
                with self.subTest(phase=phase, page=page), tempfile.TemporaryDirectory() as tmp:
                    owner = SharedApplyOperation(Path(tmp) / "shared", owner=os.geteuid())
                    values = detail(page)
                    owner.advance("prepared", values)
                    owner.advance("activating", values)
                    owner.advance(phase, values)
                    before = (owner.root / "operation.json").read_bytes()
                    event = reader.read_qualified_failure(qualified(), reader=owner.read)
                    after = (owner.root / "operation.json").read_bytes()
                    self.assertEqual(before, after)
                    self.assertEqual(event["source"], "original-shared-apply-journal")
                    self.assertEqual(event["operation_id"], values["id"])
                    self.assertEqual(event["action"], "voice-apply" if page == "voice" else "apply")
                    self.assertEqual(event["code"], "APPLY_ROLLBACK_FAILED" if phase == "restore-failed" else "APPLY_REQUIRES_REVIEW")
                    self.assertIsNone(event["timestamp"])
                    for name in ("generation", "exit_status", "runtime_before",
                                 "stderr_excerpt", "log_ref"):
                        self.assertIsNone(event[name])
                    raw = json.dumps(event)
                    self.assertNotIn(values["candidate"], raw)
                    self.assertNotIn(values["base"], raw)
                    self.assertNotIn("general.enabled", raw)

    def test_prepared_or_restored_never_fabricates_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            owner = SharedApplyOperation(Path(tmp) / "shared", owner=os.geteuid())
            values = detail()
            owner.advance("prepared", values)
            self.assertIsNone(reader.read_qualified_failure(qualified(), reader=owner.read))
            owner.advance("restored", values)
            self.assertIsNone(reader.read_qualified_failure(qualified(), reader=owner.read))

    def test_runtime_mismatch_refuses_to_attribute_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            owner = SharedApplyOperation(Path(tmp) / "shared", owner=os.geteuid())
            values = detail()
            for p in ("prepared", "activating", "requires-review"):
                owner.advance(p, values)
            for runtime, manifest in (("RUNNING", "stale"), ("STOPPED", "stale"),
                                      ("FOREIGN_OR_UNVERIFIED", "valid"),
                                      ("INCOMPLETE", "valid"),
                                      ("UNKNOWN", "stale")):
                fact = qualified()
                components = dict(fact["components"], runtime=runtime, manifest=manifest)
                self.assertIsNone(reader.read_qualified_failure(classify(components),
                                                              reader=lambda: self.fail("unexpected journal I/O")))
            with self.assertRaises(ValueError):
                reader.read_qualified_failure({"components": qualified()["components"]}, reader=owner.read)

    def test_original_validation_refuses_forged_and_untrusted_record(self):
        bad = {"schema": 1, "phase": "requires-review",
               "detail": {**detail(), "id": "../../secret"}}
        with self.assertRaises((ValueError, SharedOperationError)):
            reader.read_qualified_failure(qualified(), reader=lambda: bad)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "shared"
            real = SharedApplyOperation(root, owner=os.geteuid())
            values = detail()
            real.advance("prepared", values)
            real.advance("activating", values)
            real.advance("requires-review", values)
            with tempfile.TemporaryDirectory() as second:
                link = Path(second) / "shared"
                link.symlink_to(root, target_is_directory=True)
                forged = SharedApplyOperation(link, owner=os.geteuid())
                with self.assertRaises(SharedOperationError):
                    reader.read_qualified_failure(qualified(), reader=forged.read)

    def test_racing_original_journal_is_not_an_error_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            owner = SharedApplyOperation(Path(tmp) / "shared", owner=os.geteuid())
            values = detail()
            for p in ("prepared", "activating", "requires-review"):
                owner.advance(p, values)
            counter = [0]
            def racing():
                counter[0] += 1
                result = owner.read()
                if counter[0] == 2:
                    return {**result, "phase": "restored"}
                return result
            with self.assertRaisesRegex(ValueError, "RACING_ORIGINAL"):
                reader.read_qualified_failure(qualified(), reader=racing)

    def test_json_cli_attaches_only_qualified_receipt_and_never_exposes_native_error(self):
        fact = qualified()
        event = {
            "source": "original-shared-apply-journal", "action": "apply", "stage": "apply",
            "code": "APPLY_REQUIRES_REVIEW", "message": "Original Apply requires operator review",
            "operation_id": "a" * 32, "timestamp": None, "generation": None,
            "exit_status": None, "runtime_before": None, "runtime_after": "INCOMPLETE",
            "verification": "uncertain", "stderr_excerpt": None, "log_ref": None,
        }
        with patch.object(cli, "collect", return_value=fact), patch.object(cli, "read_qualified_failure", return_value=event), patch("builtins.print") as printer:
            rc = cli.main(["status_readonly.py"])
        row = json.loads(printer.call_args.args[0])
        self.assertEqual(rc, 2)
        self.assertEqual(row["code"], fact["classification"])  # S04 compatibility
        self.assertEqual(row["last_error"], event)
        self.assertEqual(row["stage"], "apply")
        self.assertEqual(row["operation_id"], "a" * 32)
        self.assertEqual(row["diagnostic_state"], "qualified")
        with patch.object(cli, "collect", return_value=fact), patch.object(cli, "read_qualified_failure", side_effect=RuntimeError("token=secret domain.example 1.2.3.4")), patch("builtins.print") as printer:
            rc = cli.main(["status_readonly.py"])
        raw = printer.call_args.args[0]
        self.assertEqual(rc, 2)
        self.assertIsNone(json.loads(raw)["last_error"])
        self.assertEqual(json.loads(raw)["diagnostic_state"], "unavailable")
        self.assertNotIn("secret", raw)
        self.assertNotIn("1.2.3.4", raw)
        self.assertNotIn("domain.example", raw)

    def test_no_independent_reader_writer_in_product(self):
        for path in (reader.__file__, cli.__file__):
            body = Path(path).read_text()
            for token in ("O_CREAT", "os.kill(", "lockf(", "flock(", "subprocess.run(",
                          "os.replace(", ".write_bytes(", "os.rename(", "Config::save",
                          "ipfw add", "unlink("):
                self.assertNotIn(token, body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
