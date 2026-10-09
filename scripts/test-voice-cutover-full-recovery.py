#!/usr/bin/env python3
"""Offline five-resource recovery decision tests: zero appliance operations."""
from __future__ import annotations

from pathlib import Path
import copy
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"))
import voice_cutover_backup as backup
import voice_cutover_journal as journal
import voice_firewall_ledger as ledger
import voice_process_recovery_evidence as process
import voice_cutover_full_recovery as complete

PATHS = {"engine": "/usr/local/etc/zapret2/binaries/my/dvtws2",
         "daemon": "/usr/sbin/daemon",
         "monitor": "/usr/local/opnsense/scripts/OPNsense/Zapret/supervisor_loop.sh"}
OLD = {"rule_base": 19000, "rule_max": 19010, "rules": {}, "tables": {}}
PROOF = {name: "f" * 64 for name in journal.PROOF_NAMES}


class Probe:
    def __init__(self, observation):
        self.observation = observation
        self.calls = 0

    def probe(self):
        self.calls += 1
        return copy.deepcopy(self.observation)


class Observer:
    def __init__(self, values):
        self.values = values
        self.calls = 0
        self.change_at = None
        self.callback = None

    def observe(self):
        self.calls += 1
        if self.callback is not None:
            self.callback(self.calls)
        result = copy.deepcopy(self.values)
        if self.change_at == self.calls:
            result["engine"] = "a" * 64
        return result


class FullRecoveryTests(unittest.TestCase):
    def fixture(self, root):
        base = Path(root)
        config = base / "config.xml"
        config.write_bytes(b"<opnsense>previous</opnsense>\n")
        config.chmod(0o600)
        runtime = base / "runtime"
        runtime.mkdir()
        (runtime / "dvtws.args").write_bytes(b"--port=989\n")
        home = base / "private"
        home.mkdir(mode=0o700)
        for name in ("whole", "ipfw"):
            (home / name).mkdir(mode=0o700)
        saved = home / "previous"
        snap = backup.capture_previous(config, runtime, saved)
        args_digest = snap["runtime"]["dvtws.args"]["sha256"]
        def proc(role, pid):
            return {"pid": pid, "start_ns": pid * 100000000,
                    "executable": PATHS[role]}
        observed = {
            "engine": {"state": "running",
                       "process": proc("engine", 101),
                       "runtime_args_sha256": args_digest},
            "supervisor": {"state": "running",
                           "daemon": proc("daemon", 102),
                           "monitor": proc("monitor", 103)},
        }
        proc_dir = home / "process"
        proc_hashes = process.capture_process_evidence(
            Probe(observed), saved, proc_dir, PATHS,
        )
        fw = ledger.VoiceOwnershipStore(home / "ipfw")
        fw.seed(OLD)
        previous = {**backup.bound_resource_fingerprints(saved), **proc_hashes,
                    "firewall": ledger.fingerprint(ledger.canonical_manifest(OLD))}
        whole = journal.VoiceCutoverJournal(home / "whole")
        return whole, fw, saved, proc_dir, previous, config, runtime

    def inspect(self, whole, fw, saved, proc_dir, observer):
        return complete.inspect_full_recovery(
            whole, fw, saved, proc_dir, PATHS, observer,
        )

    def assert_inert(self, result):
        for key in ("can_activate", "can_recover_automatically",
                    "safe_to_mutate", "safe_to_finish_intent"):
            self.assertIs(result[key], False)

    def test_prepared_and_mutating_exact_previous_still_require_manual_review(self):
        with tempfile.TemporaryDirectory() as d:
            whole, fw, saved, proc_dir, previous, config, runtime = self.fixture(d)
            whole.begin_bound(previous, PROOF, OLD)
            observer = Observer(previous)
            for phase in ("prepared", "mutating"):
                with self.subTest(phase=phase):
                    result = self.inspect(whole, fw, saved, proc_dir, observer)
                    self.assertEqual("review-required", result["state"])
                    self.assertEqual("all-previous-fingerprints-observed", result["reason"])
                    self.assertEqual(phase, result["phase"])
                    self.assertEqual({name: "previous" for name in journal.RESOURCE_NAMES},
                                     result["domains"])
                    self.assert_inert(result)
                    self.assertEqual(b"<opnsense>previous</opnsense>\n",
                                     config.read_bytes())
                    self.assertEqual(b"--port=989\n",
                                     (runtime / "dvtws.args").read_bytes())
                if phase == "prepared":
                    whole.mark_mutating()
            self.assertEqual(4, observer.calls)

    def test_each_changed_or_missing_domain_blocks(self):
        for domain in journal.RESOURCE_NAMES:
            with self.subTest(domain=domain), tempfile.TemporaryDirectory() as d:
                whole, fw, saved, proc_dir, prev, config, runtime = self.fixture(d)
                whole.begin_bound(prev, PROOF, OLD)
                seen = dict(prev)
                seen[domain] = "a" * 64
                result = self.inspect(whole, fw, saved, proc_dir, Observer(seen))
                self.assertEqual("blocked", result["state"])
                self.assertEqual("mixed-or-untrusted-previous-state", result["reason"])
                self.assertEqual("unknown-or-changed", result["domains"][domain])
                self.assert_inert(result)
        for missing in journal.RESOURCE_NAMES:
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as d:
                whole, fw, saved, proc_dir, prev, config, runtime = self.fixture(d)
                whole.begin_bound(prev, PROOF, OLD)
                seen = dict(prev)
                del seen[missing]
                result = self.inspect(whole, fw, saved, proc_dir, Observer(seen))
                self.assertEqual("blocked", result["state"])
                self.assert_inert(result)

    def test_committed_never_proves_desired_even_with_all_previous_or_ipfw(self):
        desired = {**OLD, "tables": {"zapret2_voice_telegram": ["91.108.0.0/16"]}}
        with tempfile.TemporaryDirectory() as d:
            whole, fw, saved, proc_dir, previous, config, runtime = self.fixture(d)
            whole.begin_bound(previous, PROOF, desired)
            whole.mark_mutating()
            fw.begin(OLD, desired)
            fw.mark_mutating()
            whole.commit()
            # Matching old ownership is not proof of committed target.
            old = self.inspect(whole, fw, saved, proc_dir, Observer(previous))
            self.assertEqual("blocked", old["state"])
            self.assertEqual("cross-journal-not-bound", old["reason"])
            fw.commit(desired)
            seen = dict(previous)
            seen["firewall"] = ledger.fingerprint(ledger.canonical_manifest(desired))
            result = self.inspect(whole, fw, saved, proc_dir, Observer(seen))
            self.assertEqual("blocked", result["state"])
            self.assertEqual("committed-system-not-fully-attestable", result["reason"])
            self.assert_inert(result)

    def test_missing_corrupt_or_mismatched_snapshot_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            whole, fw, saved, proc_dir, previous, config, runtime = self.fixture(d)
            self.assertEqual("missing-whole-cutover-intent",
                             self.inspect(whole, fw, saved, proc_dir,
                                          Observer(previous))["reason"])
            whole.begin_bound(previous, PROOF, OLD)
            with (saved / "config/config.xml").open("ab") as handle:
                handle.write(b"corrupted")
            result = self.inspect(whole, fw, saved, proc_dir, Observer(previous))
            self.assertEqual("blocked", result["state"])
            self.assert_inert(result)
        with tempfile.TemporaryDirectory() as d:
            whole, fw, saved, proc_dir, previous, config, runtime = self.fixture(d)
            whole.begin_bound(previous, PROOF, OLD)
            (proc_dir / "processes.json").write_bytes(b"invalid json")
            self.assertEqual("invalid-or-incomplete-whole-system-evidence",
                             self.inspect(whole, fw, saved, proc_dir,
                                          Observer(previous))["reason"])

    def test_changed_process_or_journal_during_probes_is_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            whole, fw, saved, proc_dir, previous, config, runtime = self.fixture(d)
            whole.begin_bound(previous, PROOF, OLD)
            observer = Observer(previous)
            observer.change_at = 2
            r = self.inspect(whole, fw, saved, proc_dir, observer)
            self.assertEqual("unstable-recovery-observation", r["reason"])
            self.assert_inert(r)
        with tempfile.TemporaryDirectory() as d:
            whole, fw, saved, proc_dir, previous, config, runtime = self.fixture(d)
            whole.begin_bound(previous, PROOF, OLD)
            observer = Observer(previous)
            observer.callback = lambda count: whole.mark_mutating() if count == 2 else None
            r = self.inspect(whole, fw, saved, proc_dir, observer)
            self.assertEqual("unstable-recovery-observation", r["reason"])
            self.assert_inert(r)
        with tempfile.TemporaryDirectory() as d:
            whole, fw, saved, proc_dir, previous, config, runtime = self.fixture(d)
            whole.begin_bound(previous, PROOF, OLD)
            observer = Observer(previous)
            observer.values["engine"] = False
            r = self.inspect(whole, fw, saved, proc_dir, observer)
            self.assertEqual("invalid-or-incomplete-whole-system-evidence", r["reason"])

    def test_cross_journal_phase_mismatch_stays_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            whole, fw, saved, proc_dir, previous, config, runtime = self.fixture(d)
            whole.begin_bound(previous, PROOF, OLD)
            fw.begin(OLD, OLD)
            result = self.inspect(whole, fw, saved, proc_dir, Observer(previous))
            self.assertEqual("cross-journal-not-bound", result["reason"])
            self.assert_inert(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
