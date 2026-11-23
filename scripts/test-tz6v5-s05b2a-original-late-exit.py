#!/usr/bin/env python3
"""S05b2a: exact original FD9 late-exit durable receipt, no second writer."""
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
from shared_apply_operation import SharedApplyOperation, SharedOperationError, _validate_record
import status_error_original as error_reader
import status_projection as status


def detail():
    return {"id": "c" * 32, "page": "strategies", "base": "d" * 64,
            "candidate": "e" * 64, "changed_fields": []}


def original_committed(tmp):
    store = SharedApplyOperation(Path(tmp) / "journal", owner=os.geteuid())
    d = detail()
    for phase in ("prepared", "activating", "activated", "config-saved", "committed"):
        store.advance(phase, d)
    return store, d


def facts(runtime="STOPPED", manifest="valid"):
    return classify({"plugin": "installed", "engine": "valid",
                     "config": "initialized", "manifest": manifest,
                     "runtime": runtime})


class LateExitOriginalWriter(unittest.TestCase):
    def test_original_writer_only_after_committed_and_exact_id(self):
        with tempfile.TemporaryDirectory() as temp:
            store, d = original_committed(temp)
            before = store.read()
            self.assertEqual(set(before), {"schema", "phase", "detail"})
            with self.assertRaises(SharedOperationError):
                store.record_runtime_exit("a" * 32)
            self.assertEqual(before, store.read())
            event_record = store.record_runtime_exit(d["id"])
            failure = event_record["failure"]
            self.assertEqual(failure["code"], "ENGINE_EXIT_AFTER_READY")
            self.assertEqual(failure["operation_id"], d["id"])
            self.assertEqual(failure["action"], "runtime-failure")
            self.assertIsNone(failure["exit_status"])
            self.assertRegex(failure["observed_at"],
                             r"^20[0-9]{2}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
            encoded = (store.root / "operation.json").read_bytes()
            store.record_runtime_exit(d["id"])
            self.assertEqual(encoded, (store.root / "operation.json").read_bytes())
            self.assertEqual(store.read(), event_record)

    def test_original_status_read_only_causally_qualified(self):
        with tempfile.TemporaryDirectory() as temp:
            store, d = original_committed(temp)
            store.record_runtime_exit(d["id"])
            before = (store.root / "operation.json").read_bytes()
            event = error_reader.read_qualified_failure(facts(), reader=store.read)
            self.assertEqual(before, (store.root / "operation.json").read_bytes())
            self.assertEqual(event["code"], "ENGINE_EXIT_AFTER_READY")
            self.assertEqual(event["operation_id"], d["id"])
            self.assertEqual(event["action"], "runtime-failure")
            self.assertEqual(event["stage"], "engine-stop")
            self.assertEqual(event["runtime_before"], "RUNNING")
            self.assertEqual(event["runtime_after"], "STOPPED")
            self.assertIsNone(event["exit_status"])
            self.assertIsNone(event["generation"])
            self.assertIsNone(event["stderr_excerpt"])
            projected = status.project(facts(), "2026-11-23T17:00:00Z")
            self.assertEqual(projected["runtime_state"], "STOPPED")
            self.assertEqual(projected["status_exit_code"], 1)
            for runtime, manifest in (("RUNNING", "valid"),
                                      ("FOREIGN_OR_UNVERIFIED", "valid"),
                                      ("INCOMPLETE", "stale"),
                                      ("UNKNOWN", "unknown"),
                                      ("STOPPED", "missing")):
                self.assertIsNone(error_reader.read_qualified_failure(
                    facts(runtime, manifest), reader=store.read))

    def test_successful_original_new_run_clears_not_fakes_error(self):
        with tempfile.TemporaryDirectory() as temp:
            store, d = original_committed(temp)
            store.record_runtime_exit(d["id"])
            store.clear_runtime_exit(d["id"])
            after = (store.root / "operation.json").read_bytes()
            self.assertEqual(set(store.read()), {"schema", "phase", "detail"})
            self.assertIsNone(error_reader.read_qualified_failure(facts(), reader=store.read))
            store.clear_runtime_exit(d["id"])
            self.assertEqual(after, (store.root / "operation.json").read_bytes())
            with self.assertRaises(SharedOperationError):
                store.clear_runtime_exit("f" * 32)

    def test_untrusted_receipt_and_other_original_phases_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            store = SharedApplyOperation(Path(temp) / "uncommitted", owner=os.geteuid())
            d = detail()
            store.advance("prepared", d)
            with self.assertRaises(SharedOperationError):
                store.record_runtime_exit(d["id"])
            with self.assertRaises(SharedOperationError):
                store.clear_runtime_exit(d["id"])
            committed, d = original_committed(temp)
            row = committed.record_runtime_exit(d["id"])
            for bad in (
                {**row, "failure": {**row["failure"], "exit_status": 0}},
                {**row, "failure": {**row["failure"], "operation_id": "a" * 32}},
                {**row, "failure": {**row["failure"], "code": "OTHER"}},
                {**row, "failure": {**row["failure"], "observed_at": "not-a-time"}},
                {**row, "failure": {**row["failure"], "stderr": "password=secret"}},
                {**row, "phase": "prepared"},
            ):
                with self.subTest(bad=bad):
                    with self.assertRaises(SharedOperationError):
                        _validate_record(bad)
            self.assertEqual(committed.read(), row)

    def test_reader_detects_original_journal_race(self):
        with tempfile.TemporaryDirectory() as temp:
            store, d = original_committed(temp)
            row = store.record_runtime_exit(d["id"])
            count = [0]
            def read():
                count[0] += 1
                if count[0] == 2:
                    return {**row, "failure": None}
                return store.read()
            with self.assertRaisesRegex(ValueError, "RACING_ORIGINAL_EXIT"):
                error_reader.read_qualified_failure(facts(), reader=read)

    def test_no_alternate_storage_or_public_raw_stderr(self):
        path = ROOT / "src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
        text = path.read_text()
        self.assertIn('runtime-exit-record "$_exit_owner_id"', text)
        self.assertIn('runtime-exit-clear "$_shared_boot_id"', text)
        self.assertIn('shared_apply_stop_service "$_shared_owner" "$3" || return $?', text)
        # The existing legacy orchestrator path stays untouched; the
        # earlier Common branch returns before reaching that path.
        self.assertIn('shared_apply_stop_service "$_shared_owner" "$3" || return $?', text)
        src = (BACKEND / "status_error_original.py").read_text()
        for symbol in (".write_text(", ".write_bytes(", "O_CREAT", "os.kill("):
            self.assertNotIn(symbol, src)
        with tempfile.TemporaryDirectory() as temp:
            store, d = original_committed(temp)
            store.record_runtime_exit(d["id"])
            raw = json.dumps(error_reader.read_qualified_failure(facts(), reader=store.read))
            for secret in (d["base"], d["candidate"], "argv", "/conf/", "password=", "127."):
                self.assertNotIn(secret, raw)


if __name__ == "__main__":
    unittest.main(verbosity=2)
