#!/usr/bin/env python3
"""Kernel ownership witness: fake IPFW executable, real private ledger."""
from __future__ import annotations
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"))
import voice_firewall_ledger as ledger
from voice_ipfw_adapter import FreeBSDIPFWAdapter
from voice_native_ipfw_ownership import KernelOwnershipError, observe_owned_ipfw

OLD = {"rule_base": 19000, "rule_max": 19010, "rules": {}, "tables": {}}
TCP = ["divert", "989", "tcp", "from", "any", "to", "any", "443",
       "out", "not", "diverted", "not", "sockarg", "xmit", "vtnet1"]


class KernelSimulator:
    def __init__(self):
        self.rules = {}
        self.tables = {}
        self.calls = []
        self.fail = False

    def __call__(self, argv, **kwargs):
        self.calls.append(tuple(argv))
        if self.fail:
            return subprocess.CompletedProcess(argv, 1, stdout="",
                                               stderr="Permission denied")
        command = tuple(argv[1:])
        if command == ("-q", "list"):
            rows = ["00001 allow ip from any to any"]
            rows += [str(n) + " " + " ".join(args)
                     for n, args in sorted(self.rules.items())]
            rows += ["65535 deny ip from any to any"]
            return subprocess.CompletedProcess(argv, 0,
                                               stdout="\n".join(rows) + "\n", stderr="")
        if len(command) == 3 and command[0] == "table":
            name, action = command[1:]
            if name not in self.tables:
                return subprocess.CompletedProcess(
                    argv, 69, stdout="",
                    stderr="Table " + name + " does not exist",
                )
            if action == "info":
                return subprocess.CompletedProcess(argv, 0,
                                                   stdout="table type: addr\n", stderr="")
            if action == "list":
                return subprocess.CompletedProcess(
                    argv, 0,
                    stdout="".join(x + " 0\n" for x in self.tables[name]), stderr="")
        raise AssertionError("unexpected or mutating IPFW operation: " + str(argv))


class WitnessTests(unittest.TestCase):
    def setup(self, root, state=OLD):
        directory = Path(root) / "voice-ipfw"
        directory.mkdir(mode=0o700)
        store = ledger.VoiceOwnershipStore(directory)
        if state is not None:
            store.seed(state)
        simulator = KernelSimulator()
        adapter = FreeBSDIPFWAdapter(19000, 19010, runner=simulator)
        return store, adapter, simulator

    def test_verified_empty_owner_and_read_only_command_allowlist(self):
        with tempfile.TemporaryDirectory() as d:
            store, adapter, fake = self.setup(d)
            expected = ledger.fingerprint(ledger.canonical_manifest(OLD))
            self.assertEqual(expected, observe_owned_ipfw(store, adapter))
            self.assertEqual(expected, observe_owned_ipfw(store, adapter))
            self.assertTrue(all(call[0] == "/sbin/ipfw" for call in fake.calls))
            self.assertTrue(all(call[1:] == ("-q","list") or
                                (len(call) == 4 and call[1] == "table" and
                                 call[-1] in ("info","list"))
                                for call in fake.calls))
            self.assertEqual(22, len(fake.calls))  # 1 rules + 10 tables, twice
            self.assertEqual(OLD, store.owned())

    def test_address_entry_order_is_semantically_a_set(self):
        entries = ["91.108.0.0/16", "91.108.13.10"]
        manifest = {**OLD, "tables": {"zapret2_voice_telegram": entries}}
        with tempfile.TemporaryDirectory() as d:
            store, adapter, fake = self.setup(d, manifest)
            fake.tables["zapret2_voice_telegram"] = list(reversed(entries))
            observed = observe_owned_ipfw(store, adapter)
            self.assertEqual(ledger.fingerprint(ledger.canonical_manifest(manifest)),
                             observed)

    def test_foreign_rule_table_or_stage_blocks_without_mutating(self):
        for case in ("foreign-rule","foreign-table","orphan-stage","missing-table",
                     "changed-address","bad-ipfw-output","ipfw-error"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as d:
                state = {**OLD, "tables": {"zapret2_voice_telegram": ["91.108.0.0/16"]}}
                store, adapter, fake = self.setup(d, state)
                fake.tables["zapret2_voice_telegram"] = ["91.108.0.0/16"]
                if case == "foreign-rule":
                    fake.rules[19000] = TCP
                elif case == "foreign-table":
                    fake.tables["zapret2_voice_discord"] = ["192.0.2.0/24"]
                elif case == "orphan-stage":
                    fake.tables["zapret2_voice_telegram_stage"] = ["91.108.13.10"]
                elif case == "missing-table":
                    del fake.tables["zapret2_voice_telegram"]
                elif case == "changed-address":
                    fake.tables["zapret2_voice_telegram"] = ["91.108.9.0/24"]
                elif case == "bad-ipfw-output":
                    fake.rules[19000] = ["allow", "ip", "from", "any", "to", "any"]
                elif case == "ipfw-error":
                    fake.fail = True
                with self.assertRaises(KernelOwnershipError):
                    observe_owned_ipfw(store, adapter)
                self.assertTrue(all(call[0] == "/sbin/ipfw" for call in fake.calls))
                self.assertEqual(state, store.owned())

    def test_no_owner_or_mutation_capability_or_wrong_range_refused(self):
        with tempfile.TemporaryDirectory() as d:
            store, adapter, fake = self.setup(d, None)
            with self.assertRaises(KernelOwnershipError):
                observe_owned_ipfw(store, adapter)
            self.assertFalse(fake.calls)
        with tempfile.TemporaryDirectory() as d:
            store, adapter, fake = self.setup(d)
            adapter.allow_mutations = True
            with self.assertRaises(KernelOwnershipError):
                observe_owned_ipfw(store, adapter)
            self.assertFalse(fake.calls)
            adapter.allow_mutations = False
            adapter.rule_max = 19009
            with self.assertRaises(KernelOwnershipError):
                observe_owned_ipfw(store, adapter)
            self.assertFalse(fake.calls)

    def test_ledger_change_injected_between_reads_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            store, adapter, fake = self.setup(d)
            original = fake.__call__
            class Changing:
                def __init__(self): self.count=0
                def __call__(self,argv,**kwargs):
                    self.count+=1
                    if self.count == 3:
                        store.begin(OLD, OLD)
                    return original(argv,**kwargs)
            adapter.runner = Changing()
            with self.assertRaises(KernelOwnershipError):
                observe_owned_ipfw(store, adapter)


if __name__ == "__main__":
    unittest.main(verbosity=2)
