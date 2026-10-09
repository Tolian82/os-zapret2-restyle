#!/usr/bin/env python3
"""Offline cross-journal safety: no router, CLI or runtime mutations."""
from __future__ import annotations
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))
import voice_cutover_backup as backup
import voice_cutover_journal as journal
import voice_cutover_recovery_preflight as triage
import voice_firewall_ledger as ledger
PROOF={name: str(i+5)*64 for i,name in enumerate(journal.PROOF_NAMES)}
OLD={"rule_base":19000,"rule_max":19010,"rules":{},"tables":{}}


class CrossJournalTests(unittest.TestCase):
    def setup(self,root):
        base=Path(root)
        config=base/"config.xml"
        config.write_text("<opnsense/>\n")
        config.chmod(0o600)
        runtime=base/"runtime-v2"
        runtime.mkdir()
        (runtime/"ordinary.args").write_text("--port=989\n")
        for name in ("backup","whole","ipfw"):
            (base/name).mkdir(mode=0o700)
        saved=base/"backup"/"previous"
        backup.capture_previous(config,runtime,saved)
        whole=journal.VoiceCutoverJournal(base/"whole")
        fw=ledger.VoiceOwnershipStore(base/"ipfw")
        fw.seed(OLD)
        previous={**backup.bound_resource_fingerprints(saved),
                  "firewall":ledger.fingerprint(ledger.canonical_manifest(OLD)),
                  "engine":"a"*64,"supervisor":"b"*64}
        return saved,whole,fw,previous

    def check(self,saved,whole,fw,state,reason):
        paths=(whole._target(),fw._location("ownership.json"),
               fw._location("intent.json"),saved/"manifest.json")
        before=[p.read_bytes() if p.exists() else None for p in paths]
        result=triage.inspect_recovery(whole,fw,saved)
        self.assertEqual((state,reason),(result["state"],result["reason"]))
        for key in ("can_activate","can_recover_automatically","safe_to_mutate"):
            self.assertIs(result[key],False)
        self.assertEqual(before,[p.read_bytes() if p.exists() else None for p in paths])
        return result

    def test_prepared_mutating_and_full_dual_intent(self):
        with tempfile.TemporaryDirectory() as d:
            saved,whole,fw,old=self.setup(d)
            self.check(saved,whole,fw,"blocked","native-ipfw-owner-without-cutover")
            whole.begin(old,PROOF)
            self.check(saved,whole,fw,"review-required","previous-snapshot-bound")
            whole.mark_mutating()
            self.check(saved,whole,fw,"review-required","previous-snapshot-bound")
            fw.begin(OLD,OLD)
            self.check(saved,whole,fw,"review-required","dual-journals-bound")
            fw.mark_mutating()
            fw.commit(OLD)
            whole.commit()
            result=self.check(saved,whole,fw,"review-required","dual-journals-bound")
            self.assertEqual(result["phase"],"committed")

    def test_distinct_desired_ipfw_requires_matching_committed_owner(self):
        desired={**OLD,"tables":{"zapret2_voice_telegram":["91.108.0.0/16"]}}
        with tempfile.TemporaryDirectory() as d:
            saved,whole,fw,old=self.setup(d)
            whole.begin(old,PROOF)
            whole.mark_mutating()
            fw.begin(OLD,desired)
            fw.mark_mutating()
            # The full cutover must not claim an IPFW commit while ownership
            # still points at the previous manifest.
            whole.commit()
            self.check(saved,whole,fw,"blocked","uncommitted-ipfw-ownership")
            fw.commit(desired)
            self.check(saved,whole,fw,"review-required","dual-journals-bound")

    def test_phase_conflict_and_orphan_intent(self):
        with tempfile.TemporaryDirectory() as d:
            saved,whole,fw,old=self.setup(d)
            whole.begin(old,PROOF)
            fw.begin(OLD,OLD)
            self.check(saved,whole,fw,"blocked","inconsistent-journal-phase")
            whole.mark_mutating()
            whole.commit()
            self.check(saved,whole,fw,"blocked","inconsistent-journal-phase")
        with tempfile.TemporaryDirectory() as d:
            saved,whole,fw,old=self.setup(d)
            fw.begin(OLD,OLD)
            self.check(saved,whole,fw,"blocked","orphan-ipfw-intent")

    def test_bad_backup_or_cross_link_never_replays(self):
        for case in ("corrupt","missing","symlink","ipfw-mismatch"):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as d:
                saved,whole,fw,old=self.setup(d)
                if case=="ipfw-mismatch":
                    old["firewall"]="f"*64
                whole.begin(old,PROOF)
                if case=="corrupt":
                    (saved/"config/config.xml").write_text("tampered")
                elif case=="missing":
                    (saved/"manifest.sha256").unlink()
                elif case=="symlink":
                    p=saved/"runtime/ordinary.args"
                    p.unlink()
                    p.symlink_to("/etc/passwd")
                else:
                    whole.mark_mutating()
                    fw.begin(OLD,OLD)
                reason=("cross-journal-previous-ipfw-mismatch" if case=="ipfw-mismatch"
                        else "invalid-or-untrusted-recovery-evidence")
                self.check(saved,whole,fw,"blocked",reason)

    def test_unknown_owner_and_missing_ledger_block(self):
        with tempfile.TemporaryDirectory() as d:
            saved,whole,fw,old=self.setup(d)
            whole.begin(old,PROOF)
            self.assertEqual("missing-ipfw-ledger",
                triage.inspect_recovery(whole,None,saved)["reason"])
            whole.abort_verified_previous(previous_verified=True)
            old["firewall"]="f"*64
            whole.begin(old,PROOF)
            self.check(saved,whole,fw,"blocked","unbound-ipfw-ownership")


if __name__=="__main__":
    unittest.main(verbosity=2)
