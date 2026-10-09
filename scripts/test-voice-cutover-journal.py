#!/usr/bin/env python3
"""Durable, private whole-system Voice intent fault/restart tests (no OPNsense)."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0,str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))
import voice_cutover_journal as journal

PREVIOUS = {name: str(i) * 64 for i, name in enumerate(journal.RESOURCE_NAMES)}
PROOF = {name: str(i + 5) * 64 for i, name in enumerate(journal.PROOF_NAMES)}

class JournalTests(unittest.TestCase):
    def setup_store(self, parent):
        directory=Path(parent)/"voice-cutover"
        directory.mkdir(mode=0o700)
        return journal.VoiceCutoverJournal(directory)

    def test_begin_mark_commit_finish_is_durable_and_restartable(self):
        with tempfile.TemporaryDirectory() as d:
            store=self.setup_store(d)
            self.assertEqual("no-intent",store.inspect())
            store.begin(PREVIOUS,PROOF)
            other=journal.VoiceCutoverJournal(store.directory)
            self.assertEqual("prepared-needs-previous-verification",other.inspect())
            self.assertEqual("prepared",other.read()["phase"])
            self.assertEqual(PREVIOUS,other.read()["previous"])
            self.assertEqual({key:PROOF[key] for key in journal.PROOF_NAMES},
                             other.read()["candidate"])
            self.assertEqual(0o600,store._target().stat().st_mode & 0o777)
            other.mark_mutating()
            self.assertEqual("interrupted-needs-kernel-runtime-review",store.inspect())
            store.commit()
            self.assertEqual("committed-needs-cleanup-review",other.inspect())
            with self.assertRaises(journal.CutoverJournalError):
                store.abort_verified_previous(previous_verified=True)
            with self.assertRaises(journal.CutoverJournalError):
                store.finish_verified_desired(desired_verified=True,cleanup_verified=False)
            store.finish_verified_desired(desired_verified=True,cleanup_verified=True)
            self.assertEqual("no-intent",other.inspect())

    def test_abort_requires_fully_verified_previous_and_no_commit(self):
        with tempfile.TemporaryDirectory() as d:
            store=self.setup_store(d)
            store.begin(PREVIOUS,PROOF)
            with self.assertRaises(journal.CutoverJournalError):
                store.abort_verified_previous(previous_verified=False)
            store.mark_mutating()
            with self.assertRaises(journal.CutoverJournalError):
                store.abort_verified_previous(previous_verified=False)
            self.assertIsNotNone(store.read())
            store.abort_verified_previous(previous_verified=True)
            self.assertIsNone(store.read())

    def test_repeated_begin_or_out_of_order_transitions_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            store=self.setup_store(d)
            store.begin(PREVIOUS,PROOF)
            with self.assertRaises(journal.CutoverJournalError):
                store.begin(PREVIOUS,PROOF)
            with self.assertRaises(journal.CutoverJournalError):
                store.commit()
            store.mark_mutating()
            with self.assertRaises(journal.CutoverJournalError):
                store.mark_mutating()
            store.commit()
            with self.assertRaises(journal.CutoverJournalError):
                store.mark_mutating()

    def test_corrupt_and_unsafe_journal_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            store=self.setup_store(d)
            store.begin(PREVIOUS,PROOF)
            original=store._target().read_bytes()
            record=json.loads(original)
            record["candidate"]["merged_sha256"]="f"*64
            store._target().write_text(json.dumps(record))
            with self.assertRaisesRegex(journal.CutoverJournalError,"checksum"):
                store.read()
            with self.assertRaises(journal.CutoverJournalError):
                store.begin(PREVIOUS,PROOF)
            store._target().write_bytes(original)
            store._target().chmod(0o644)
            with self.assertRaisesRegex(journal.CutoverJournalError,"private"):
                store.inspect()
            store._target().chmod(0o600)
            store._target().unlink()
            dest=Path(d)/"outside.json"
            dest.write_bytes(original)
            store._target().symlink_to(dest)
            with self.assertRaises(journal.CutoverJournalError):
                store.read()
            self.assertEqual(original,dest.read_bytes())

    def test_reject_untrusted_directory_and_invalid_source_fingerprints(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"secure"
            path.mkdir(mode=0o700)
            path.chmod(0o755)
            with self.assertRaises(journal.CutoverJournalError):
                journal.VoiceCutoverJournal(path)
            path.chmod(0o700)
            store=journal.VoiceCutoverJournal(path)
            for prior,proof in (
                ({**PREVIOUS,"config":"broken"},PROOF),
                (PREVIOUS,{**PROOF,"saved_xml_sha256":"bad"}),
                ({**PREVIOUS,"arbitrary":"a"*64},PROOF),
            ):
                with self.subTest(prior=prior,proof=proof):
                    with self.assertRaises(journal.CutoverJournalError):
                        store.begin(prior,proof)
                    self.assertIsNone(store.read())
            with self.assertRaises(journal.CutoverJournalError):
                store.mark_mutating()

    def test_bound_desired_firewall_schema_2_survives_restart_and_phase_change(self):
        from voice_firewall_ledger import canonical_manifest, fingerprint
        desired = {"rule_base":19000,"rule_max":19010,"rules":{},
                   "tables":{"zapret2_voice_telegram":["91.108.0.0/16"]}}
        with tempfile.TemporaryDirectory() as d:
            store=self.setup_store(d)
            store.begin_bound(PREVIOUS,PROOF,desired)
            restarted=journal.VoiceCutoverJournal(store.directory)
            record=restarted.read()
            self.assertEqual(journal.BOUND_SCHEMA,record["schema"])
            self.assertEqual(fingerprint(canonical_manifest(desired)),
                             record["candidate"][journal.BOUND_FIELD])
            with self.assertRaises(journal.CutoverJournalError):
                restarted.begin(PREVIOUS,PROOF)
            restarted.mark_mutating()
            self.assertEqual("mutating",store.read()["phase"])
            self.assertEqual(record["candidate"],store.read()["candidate"])
            restarted.commit()
            self.assertEqual("committed",store.read()["phase"])
            self.assertEqual(record["candidate"],store.read()["candidate"])
            self.assertEqual("committed-needs-cleanup-review",restarted.inspect())

    def test_bound_schema_rejects_malformed_desired_and_resealed_tampering(self):
        import copy
        from voice_firewall_ledger import LedgerError
        valid={"rule_base":19000,"rule_max":19010,"rules":{},"tables":{}}
        with tempfile.TemporaryDirectory() as d:
            store=self.setup_store(d)
            with self.assertRaises(LedgerError):
                store.begin_bound(PREVIOUS,PROOF,{**valid,"rule_base":0})
            self.assertIsNone(store.read())
            store.begin_bound(PREVIOUS,PROOF,valid)
            original=store.read()
            for change in ("missing", "extra", "malformed", "downgrade"):
                record=copy.deepcopy(original)
                if change=="missing":
                    del record["candidate"][journal.BOUND_FIELD]
                elif change=="extra":
                    record["candidate"]["unknown"]="e"*64
                elif change=="malformed":
                    record["candidate"][journal.BOUND_FIELD]=True
                else:
                    record["schema"]=1
                record["check"]=journal._digest({
                    k:v for k,v in record.items() if k!="check"
                })
                store._target().write_text(json.dumps(record))
                with self.subTest(change=change):
                    with self.assertRaises(journal.CutoverJournalError):
                        store.read()
            store._target().write_text(json.dumps(original))
            self.assertEqual(original,store.read())

    def test_interrupted_phase_always_requires_review_not_automatic_replay(self):
        with tempfile.TemporaryDirectory() as d:
            store=self.setup_store(d)
            store.begin(PREVIOUS,PROOF)
            store.mark_mutating()
            reopened=journal.VoiceCutoverJournal(store.directory)
            self.assertEqual("interrupted-needs-kernel-runtime-review",reopened.inspect())
            with self.assertRaises(journal.CutoverJournalError):
                reopened.finish_verified_desired(desired_verified=True,cleanup_verified=True)
            self.assertIsNotNone(reopened.read())

if __name__=="__main__":
    unittest.main(verbosity=2)
