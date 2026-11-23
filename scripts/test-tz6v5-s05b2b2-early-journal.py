#!/usr/bin/env python3
"""S05b2b2: original early-start receipt, no fabricated native wait status."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

from component_inventory import classify
from shared_apply_operation import SharedApplyOperation, SharedOperationError
from status_error_original import read_qualified_failure


def detail(ident="a" * 32):
    return {"id": ident, "page": "strategies", "base": "b" * 64,
            "candidate": "c" * 64, "changed_fields": ["general.enabled"]}


def facts(runtime="INCOMPLETE", manifest="stale"):
    return classify({"plugin": "installed", "engine": "valid",
                     "config": "initialized", "manifest": manifest,
                     "runtime": runtime})


class EarlyOriginal(unittest.TestCase):
    def setup_owner(self, root, phase="requires-review"):
        store = SharedApplyOperation(root, owner=os.geteuid())
        owner = detail()
        store.advance("prepared", owner)
        store.advance("activating", owner)
        if phase != "activating":
            store.advance(phase, owner)
        return store, owner

    def test_authentic_original_operation_only_and_no_child_rc(self):
        for cause in ("no-live-pid", "stability-unverified"):
            with self.subTest(cause=cause), tempfile.TemporaryDirectory() as tmp:
                store, owner = self.setup_owner(Path(tmp) / "journal")
                before = store.read()
                got = store.record_early_start_failure(owner["id"], cause)
                self.assertEqual(got["phase"], "requires-review")
                self.assertIs(got["failure"]["exit_status"], None)
                self.assertEqual(got["failure"]["cause"], cause)
                self.assertEqual(got["failure"]["code"], "ENGINE_START_UNVERIFIED")
                self.assertEqual(store.record_early_start_failure(owner["id"], cause), got)
                written = (store.root / "operation.json").read_bytes()
                event = read_qualified_failure(facts(), reader=store.read)
                self.assertEqual((store.root / "operation.json").read_bytes(), written)
                self.assertEqual(event["stage"], "engine-start")
                self.assertEqual(event["code"], "ENGINE_START_UNVERIFIED")
                self.assertEqual(event["timestamp"], got["failure"]["observed_at"])
                self.assertEqual(event["operation_id"], owner["id"])
                for field in ("generation", "exit_status", "runtime_before",
                              "stderr_excerpt", "log_ref"):
                    self.assertIsNone(event[field])
                public = json.dumps(event)
                for secret in (owner["base"], owner["candidate"], "general.enabled"):
                    self.assertNotIn(secret, public)
                self.assertNotEqual(before, got)
                # Existing S05b2a MUST inspect the committed journal for
                # STOPPED/valid; the early requires-review record must still
                # produce no late-exit event (without modifying the file).
                for runtime, manifest in (("RUNNING", "stale"),
                                          ("FOREIGN_OR_UNVERIFIED", "stale"),
                                          ("INCOMPLETE", "valid")):
                    self.assertIsNone(read_qualified_failure(
                        facts(runtime, manifest), reader=lambda: self.fail("unsafe journal read")))
                self.assertIsNone(read_qualified_failure(
                    facts("STOPPED", "valid"), reader=store.read))
                self.assertEqual((store.root / "operation.json").read_bytes(), written)

    def test_stale_owner_wrong_phase_cause_and_conflict_are_no_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, owner = self.setup_owner(Path(tmp) / "journal", "activating")
            snapshot = (store.root / "operation.json").read_bytes()
            for ident, cause in ((owner["id"], "injected-secret"),
                                 ("f" * 32, "no-live-pid"),
                                 (owner["id"], "no-live-pid")):
                with self.assertRaises(SharedOperationError):
                    store.record_early_start_failure(ident, cause)
                self.assertEqual((store.root / "operation.json").read_bytes(), snapshot)
            store.advance("requires-review", owner)
            store.record_early_start_failure(owner["id"], "no-live-pid")
            first = (store.root / "operation.json").read_bytes()
            with self.assertRaises(SharedOperationError):
                store.record_early_start_failure(owner["id"], "stability-unverified")
            self.assertEqual((store.root / "operation.json").read_bytes(), first)
            # Tamper attempts must not be silently projected or persisted.
            for bad in ({"cause": "unknown"}, {"exit_status": 42},
                        {"code": "ENGINE_EXIT_EARLY"},
                        {"private_ip": "1.2.3.4"}):
                forged = store.read()
                forged["failure"].update(bad)
                with self.assertRaises(SharedOperationError):
                    read_qualified_failure(facts(), reader=lambda: forged)

    def test_prior_unextended_error_and_late_exit_unaffected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, owner = self.setup_owner(Path(tmp) / "journal")
            self.assertEqual(read_qualified_failure(facts(), reader=store.read)["code"],
                             "APPLY_REQUIRES_REVIEW")
        with tempfile.TemporaryDirectory() as tmp:
            store = SharedApplyOperation(Path(tmp) / "journal", owner=os.geteuid())
            owner = detail()
            for phase in ("prepared", "activating", "activated", "config-saved", "committed"):
                store.advance(phase, owner)
            old = store.record_runtime_exit(owner["id"])
            self.assertEqual(old["failure"]["code"], "ENGINE_EXIT_AFTER_READY")
            self.assertIs(old["failure"]["exit_status"], None)
            with self.assertRaises(SharedOperationError):
                store.record_early_start_failure(owner["id"], "no-live-pid")


if __name__ == "__main__":
    unittest.main(verbosity=2)
