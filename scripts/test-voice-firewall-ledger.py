#!/usr/bin/env python3
"""Persistent Voice IPFW ledger regressions, with a fake read-only kernel view."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from copy import deepcopy
from unittest.mock import patch

BACKEND = Path(__file__).resolve().parent.parent / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

def load(name):
    spec = importlib.util.spec_from_file_location(name, BACKEND / f"{name}.py")
    assert spec and spec.loader
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

ledger = load("voice_firewall_ledger")
tx = load("voice_firewall_transaction")
compiler = load("voice_profile_compiler")
planner = load("voice_capture_plan")
MANAGED = Path("/usr/local/etc/zapret2/runtime-v2/managed")
BASE = "--filter-udp=*\n--filter-l7=stun\n--payload=stun"

def manifest(*services):
    data = {"strategy_wan": "WAN", "voice_wan": "",
            "services": {n: {"enabled": False, "args": "", "ips": ""} for n in compiler.SERVICES}}
    for name, ips in services:
        data["services"][name] = {"enabled": True, "args": BASE, "ips": ips}
    _, profile = compiler.compile_candidate(data, MANAGED)
    plan = planner.compile_capture_plan(profile, 19000, 19010, 989, physical_wan="vtnet1")
    return tx.prepare_desired(plan, "443", "596-599")

class MockKernel:
    def __init__(self, state):
        self.rules = deepcopy(state["rules"])
        self.tables = deepcopy(state["tables"])
    def list_rules(self, first, last):
        return {n: deepcopy(v) for n, v in self.rules.items() if first <= n <= last}
    def get_table(self, name):
        return deepcopy(self.tables.get(name))


class VoiceLedgerTests(unittest.TestCase):
    def setup_store(self, d):
        path = Path(d) / "journal"
        path.mkdir(mode=0o700)
        return ledger.VoiceOwnershipStore(path)

    def test_canonical_codec_and_integer_rule_keys(self):
        old = manifest(("telegram", "91.108.0.0/16"))
        doc = ledger.canonical_manifest(old)
        self.assertEqual([19000, 19001, 19002],
                         [r["number"] for r in doc["rules"]])
        self.assertEqual(old, ledger.decode_manifest(json.loads(json.dumps(doc))))
        self.assertEqual(doc, ledger.canonical_manifest(ledger.decode_manifest(doc)))

    def test_seed_begin_restart_inspect_commit_finalize(self):
        old = manifest()
        desired = manifest(("telegram","91.108.0.0/16"))
        with tempfile.TemporaryDirectory() as d:
            store = self.setup_store(d)
            self.assertIsNone(store.owned())
            store.seed(old)
            store.begin(old, desired)
            self.assertEqual("previous-intact", store.inspect(MockKernel(old)))
            with self.assertRaisesRegex(ledger.LedgerError,"unfinished"):
                store.begin(old, desired)
            self.assertEqual("prepared", store.pending()["phase"])
            store.mark_mutating()
            reopened = ledger.VoiceOwnershipStore(store.directory)
            self.assertEqual("mutating", reopened.pending()["phase"])
            self.assertEqual("manual-review", reopened.inspect(MockKernel({
                "rule_base": 19000, "rule_max": 19010,
                "rules": desired["rules"], "tables": old["tables"]
            })))
            self.assertEqual("desired-intact", reopened.inspect(MockKernel(desired)))
            reopened.commit(desired)
            self.assertEqual(desired, reopened.owned())
            self.assertIsNotNone(reopened.pending())
            reopened.finish(MockKernel(desired))
            self.assertIsNone(reopened.pending())
            self.assertEqual(desired, reopened.owned())
            for entry in store.directory.iterdir():
                self.assertEqual(0o600, stat.S_IMODE(entry.stat().st_mode))

    def test_reject_foreign_or_orphan_staging_and_do_not_erase_pending(self):
        old = manifest()
        desired = manifest(("telegram","91.108.0.0/16"))
        with tempfile.TemporaryDirectory() as d:
            store = self.setup_store(d)
            store.seed(old)
            store.begin(old,desired)
            store.mark_mutating()
            store.commit(desired)
            kernel = MockKernel(desired)
            kernel.tables["zapret2_voice_telegram_stage"] = []
            self.assertEqual("manual-review", store.inspect(kernel))
            with self.assertRaisesRegex(ledger.LedgerError,"verified desired"):
                store.finish(kernel)
            self.assertIsNotNone(store.pending())
            kernel.tables.pop("zapret2_voice_telegram_stage")
            kernel.rules[19000] = ["allow","ip","from","any","to","any"]
            self.assertEqual("manual-review", store.inspect(kernel))
            with self.assertRaises(ledger.LedgerError):
                store.finish(kernel)

    def test_reject_missing_or_mismatched_ownership_and_illegal_transitions(self):
        old = manifest()
        want = manifest(("telegram","91.108.0.0/16"))
        with tempfile.TemporaryDirectory() as d:
            store = self.setup_store(d)
            with self.assertRaisesRegex(ledger.LedgerError,"untrusted or missing"):
                store.begin(old,want)
            store.seed(old)
            with self.assertRaisesRegex(ledger.LedgerError,"already initialized"):
                store.seed(old)
            with self.assertRaisesRegex(ledger.LedgerError,"not prepared"):
                store.mark_mutating()
            other = manifest(("discord","203.0.113.0/24"))
            with self.assertRaisesRegex(ledger.LedgerError,"untrusted"):
                store.begin(other,want)
            store.begin(old,want)
            with self.assertRaisesRegex(ledger.LedgerError,"cannot commit"):
                store.commit(want)
            store.mark_mutating()
            with self.assertRaisesRegex(ledger.LedgerError,"cannot commit"):
                store.commit(other)
            self.assertEqual(old,store.owned())

    def test_corruption_checksums_permissions_symlinks_and_private_directory(self):
        previous = manifest()
        with tempfile.TemporaryDirectory() as d:
            store = self.setup_store(d)
            store.seed(previous)
            file = store.directory / "ownership.json"
            raw = json.loads(file.read_text())
            raw["payload"]["rule_base"] = 19999
            file.write_text(json.dumps(raw))
            with self.assertRaisesRegex(ledger.LedgerError,"checksum"):
                store.owned()
            file.unlink()
            other = store.directory / "outside"
            other.write_text("not a valid ownership record")
            file.symlink_to(other)
            with self.assertRaises(ledger.LedgerError):
                store.owned()
            file.unlink()
            file.write_text("{}", encoding="utf-8")
            os.chmod(file, 0o644)
            with self.assertRaisesRegex(ledger.LedgerError,"private or regular"):
                store.owned()
            file.unlink()
            os.chmod(store.directory, 0o755)
            with self.assertRaisesRegex(ledger.LedgerError,"owner-private"):
                store.owned()

    def test_invalid_manifest_excluded_before_disk(self):
        valid = manifest(("telegram","91.108.0.0/16"))
        variants = []
        x = deepcopy(valid); x["rules"][19000][6] = "table(bad)"; variants.append(x)
        x = deepcopy(valid); x["rules"][19000] += ["$(rm)"]; variants.append(x)
        x = deepcopy(valid); x["tables"]["zapret2_voice_telegram"] = ["1.2.3.4;evil"]; variants.append(x)
        x = deepcopy(valid); x["tables"]["zapret2_voice_telegram"] = []; variants.append(x)
        x = deepcopy(valid); x["rules"]["19000"] = x["rules"].pop(19000); variants.append(x)
        x = deepcopy(valid); x["rules"][19000][-1] = "vtnet1;rm"; variants.append(x)
        x = deepcopy(valid); x["tables"] = {}; variants.append(x)
        x = deepcopy(valid); x["rules"][19000][7] = "--new"; variants.append(x)
        x = deepcopy(valid); x["rule_base"] = 0; variants.append(x)
        for bad in variants:
            with self.subTest(bad=bad):
                with self.assertRaises(ledger.LedgerError):
                    ledger.canonical_manifest(bad)
        good = ledger.canonical_manifest(valid)
        corrupt = deepcopy(good)
        corrupt["rules"] = list(reversed(corrupt["rules"]))
        with self.assertRaises(ledger.LedgerError):
            ledger.decode_manifest(corrupt)

    def test_atomic_write_failure_does_not_destroy_old_owner_record(self):
        old = manifest()
        with tempfile.TemporaryDirectory() as d:
            store = self.setup_store(d)
            store.seed(old)
            before = (store.directory / "ownership.json").read_bytes()
            with patch.object(ledger.os, "replace", side_effect=OSError("fault injected")):
                with self.assertRaises(OSError):
                    store._write("ownership.json", ledger.canonical_manifest(old))
            self.assertEqual(before, (store.directory / "ownership.json").read_bytes())
            self.assertEqual(["ownership.json"], [p.name for p in store.directory.iterdir()])

    def test_journal_detects_failure_between_ownership_commit_and_intent_removal(self):
        old, desired = manifest(), manifest(("telegram","91.108.0.0/16"))
        with tempfile.TemporaryDirectory() as d:
            store = self.setup_store(d)
            store.seed(old); store.begin(old, desired); store.mark_mutating()
            store.commit(desired)  # crash here before final cleanup
            reopened = ledger.VoiceOwnershipStore(store.directory)
            self.assertEqual(desired, reopened.owned())
            self.assertIsNotNone(reopened.pending())
            self.assertEqual("desired-intact", reopened.inspect(MockKernel(desired)))
            with self.assertRaisesRegex(ledger.LedgerError,"verified desired"):
                reopened.finish(MockKernel(old))
            reopened.finish(MockKernel(desired))
            self.assertIsNone(reopened.pending())

if __name__ == "__main__":
    unittest.main(verbosity=2)
