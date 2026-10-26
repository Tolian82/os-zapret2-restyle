#!/usr/bin/env python3
"""Common Apply durable phases and existing lifecycle guard, without kernel changes."""
import sys
import json
from contextlib import ExitStack
import subprocess
from unittest.mock import patch
import tempfile
from pathlib import Path
import unittest

BACKEND=Path(__file__).resolve().parents[1]/"src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0,str(BACKEND))
from shared_apply_operation import SharedApplyOperation,SharedOperationError,committed_owner,native_lifecycle_gate,native_committed_owner_witness,native_remove_rollback_pair,native_remove_trial_context,native_remove_prepared_trial

def detail(ident="1"*32):
    return {"id":ident,"page":"voice","base":"a"*64,
            "candidate":"b"*64,"changed_fields":[
                "voice.telegram.enabled","hostlist.telegramips"]}

class TestJournal(unittest.TestCase):
    # Retired private Telegram PoC migration/rollback test matrix was removed
    # by owner decision. Only active shared Apply durability is exercised here.

    def test_retired_telegram_predecessor_api_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            j=SharedApplyOperation(Path(tmp)/"shared-apply")
            for phase in ("legacy-quiescing", "legacy-marker-retired",
                          "legacy-common-committing", "legacy-rollback-marker"):
                with self.assertRaises(SharedOperationError):
                    j.advance(phase, detail())
            self.assertFalse(hasattr(j, "prepare_legacy_predecessor"))
            self.assertFalse(hasattr(j, "begin_legacy_quiesce"))
            self.assertFalse(j.root.exists())
            cli=BACKEND/"shared_apply_operation.py"
            result=subprocess.run([sys.executable,str(cli),"arm-legacy",
                                   "1"*32,"a"*64,"b"*64,"-"],
                                  capture_output=True,text=True,check=False)
            self.assertEqual(64,result.returncode)
            j.advance("prepared",detail())
            target=j.root/"operation.json"
            record=json.loads(target.read_text())
            record["legacy_predecessor"]="c"*64
            target.write_text(json.dumps(record))
            with self.assertRaisesRegex(SharedOperationError,"invalid common Apply record"):
                j.read()

    def test_remove_prepared_cold_recovery_has_exact_old_journal_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = SharedApplyOperation(root/"shared-apply")
            old = detail("a"*32)
            for phase in ("prepared","activating","activated","config-saved","committed"):
                store.advance(phase, old)
            state = root/"extra-resources"
            (state/"transaction").mkdir(parents=True)
            journal = state/"transaction/journal.json"
            resource = {"schema":1,"mode":"remove","phase":"restarting",
                        "previous":{"lua/extra.lua":"e"*64},"incoming":{},
                        "source_commit":"f"*40,
                        "native_owner":{"id":old["id"],"page":old["page"],
                                        "candidate":old["candidate"]}}
            journal.write_text(json.dumps(resource))
            self.assertIsNone(native_remove_prepared_trial(store.root,state))
            new = {"id":"b"*32,"page":"strategies",
                   "base":old["candidate"],"candidate":old["candidate"],
                   "changed_fields":[]}
            store.advance("prepared",new)
            self.assertEqual(native_remove_prepared_trial(store.root,state),
                             {"id":new["id"],"old":resource["native_owner"]})
            before = (store.root/"operation.json").read_bytes()
            for bad in ("stopping","publishing","completed"):
                resource["phase"] = bad
                journal.write_text(json.dumps(resource))
                with self.assertRaisesRegex(SharedOperationError,"no quarantined"):
                    native_remove_prepared_trial(store.root,state)
            resource["phase"]="restarting"
            resource["native_owner"]["id"]="c"*32
            journal.write_text(json.dumps(resource))
            with self.assertRaisesRegex(SharedOperationError,"foreign or changed"):
                native_remove_prepared_trial(store.root,state)
            resource["native_owner"]["id"]=old["id"]
            journal.write_text(json.dumps(resource))
            self.assertEqual((store.root/"operation.json").read_bytes(),before)
            store.recover_prepared(new["id"],lambda:True)
            self.assertIsNone(native_remove_prepared_trial(store.root,state))

    def test_native_trial_requires_existing_pinned_old_owner_and_restart_phase(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = SharedApplyOperation(root/"shared-apply")
            old = detail("a"*32)
            for phase in ("prepared","activating","activated","config-saved","committed"):
                store.advance(phase, old)
            state = root/"extra-resources"
            (state/"transaction").mkdir(parents=True)
            trial_journal = state/"transaction/journal.json"
            transaction = {"schema":1,"mode":"remove","phase":"restarting",
                "previous":{"lua/custom.lua":"e"*64},"incoming":{},
                "source_commit":"f"*40,
                "native_owner":{"id":old["id"],"page":old["page"],
                                "candidate":old["candidate"]}}
            trial_journal.write_text(json.dumps(transaction))
            self.assertEqual(native_remove_trial_context(store.root,state),
                             transaction["native_owner"])
            for phase in ("stopping","publishing","completed"):
                transaction["phase"] = phase
                trial_journal.write_text(json.dumps(transaction))
                with self.assertRaisesRegex(SharedOperationError,"no prepared"):
                    native_remove_trial_context(store.root,state)
            transaction["phase"] = "restarting"
            transaction["native_owner"]["id"] = "f"*32
            trial_journal.write_text(json.dumps(transaction))
            with self.assertRaisesRegex(SharedOperationError,"previous common owner"):
                native_remove_trial_context(store.root,state)
            transaction["native_owner"]["id"] = old["id"]
            trial_journal.write_text(json.dumps(transaction))
            next_detail = {"id":"c"*32,"page":"strategies",
                           "base":old["candidate"],"candidate":old["candidate"],
                           "changed_fields":[]}
            store.advance("prepared",next_detail)
            with self.assertRaisesRegex(SharedOperationError,"previous common owner"):
                native_remove_trial_context(store.root,state)

    def test_exact_committed_remove_rollback_reinstates_predecessor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = SharedApplyOperation(root/"shared-apply")
            old = detail("a"*32)
            for phase in ("prepared", "activating", "activated", "config-saved", "committed"):
                store.advance(phase, old)
            new = {"id": "c"*32, "page": "strategies",
                   "base": old["candidate"], "candidate": old["candidate"],
                   "changed_fields": []}
            for phase in ("prepared", "activating", "activated", "config-saved", "committed"):
                store.advance(phase, new)
            txwork = root/"extra-resources"/"transaction"
            txwork.mkdir(parents=True)
            (txwork/"journal.json").write_text(json.dumps({
                "schema": 1, "mode": "remove", "phase": "restarting",
                "previous": {"lua/orphan.lua": "f"*64}, "incoming": {}, "source_commit": "d"*40,
                "native_owner": {"id":old["id"], "page":old["page"],
                                 "candidate":old["candidate"]},
            }))
            evidence = native_remove_rollback_pair(store.root, root/"extra-resources")
            self.assertEqual(evidence["state"], "trial")
            self.assertEqual(evidence["trial"], new["id"])
            before = (store.root/"operation.json").read_bytes()
            for new_id, old_id, attested in (
                ("e"*32, old["id"], True),
                (new["id"], "f"*32, True),
                (new["id"], old["id"], False),
            ):
                with self.assertRaises(SharedOperationError):
                    store.revert_committed_remove(new_id, old_id, lambda:attested)
                self.assertEqual(before, (store.root/"operation.json").read_bytes())
            store.revert_committed_remove(new["id"], old["id"], lambda:True)
            self.assertEqual(store.read()["phase"], "restored")
            self.assertEqual(committed_owner(store.read()), old)
            self.assertTrue(native_lifecycle_gate("strategy-lab-native", root=store.root)["safe_to_mutate"])
            self.assertEqual(native_remove_rollback_pair(
                store.root, root/"extra-resources")["state"], "old")
            with self.assertRaises(SharedOperationError):
                store.revert_committed_remove(new["id"], old["id"], lambda:True)

    def test_remove_rollback_refuses_foreign_owner_and_modified_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = SharedApplyOperation(root/"shared-apply")
            old = detail("a"*32)
            for phase in ("prepared", "activating", "activated", "config-saved", "committed"):
                store.advance(phase, old)
            txwork = root/"extra-resources"/"transaction"
            txwork.mkdir(parents=True)
            item = {"schema":1, "mode":"remove", "phase":"restarting",
                    "previous":{"lua/orphan.lua":"f"*64}, "incoming":{}, "source_commit":"d"*40,
                    "native_owner":{"id":"e"*32,"page":old["page"],
                                    "candidate":old["candidate"]}}
            journal = txwork/"journal.json"
            journal.write_text(json.dumps(item))
            with self.assertRaises(SharedOperationError):
                native_remove_rollback_pair(store.root, root/"extra-resources")
            item["native_owner"]["id"] = old["id"]
            journal.write_text(json.dumps(item))
            self.assertEqual(native_remove_rollback_pair(
                store.root, root/"extra-resources")["state"], "old")
            trial = {"id":"c"*32, "page":"strategies", "base":old["candidate"],
                     "candidate":"f"*64, "changed_fields":[]}
            for phase in ("prepared","activating","activated","config-saved","committed"):
                store.advance(phase, trial)
            with self.assertRaisesRegex(SharedOperationError, "unchanged Config mismatch"):
                native_remove_rollback_pair(store.root, root/"extra-resources")
            with self.assertRaises(SharedOperationError):
                store.revert_committed_remove(trial["id"],old["id"],lambda:True)
            item["mode"] = "install"
            journal.write_text(json.dumps(item))
            with self.assertRaisesRegex(SharedOperationError, "pending Remove"):
                native_remove_rollback_pair(store.root, root/"extra-resources")

    def test_owner_witness_uses_only_terminal_journal(self):
        with tempfile.TemporaryDirectory() as folder:
            j = SharedApplyOperation(Path(folder)/"shared-apply")
            first = detail()
            with self.assertRaises(SharedOperationError):
                native_committed_owner_witness(j.root)
            j.advance("prepared", first)
            with self.assertRaises(SharedOperationError):
                native_committed_owner_witness(j.root)
            for phase in ("activating", "activated", "config-saved", "committed"):
                j.advance(phase, first)
            self.assertEqual(native_committed_owner_witness(j.root),
                             {"id": first["id"], "page": first["page"],
                              "candidate": first["candidate"]})
            second = detail("2"*32)
            j.advance("prepared", second)
            with self.assertRaises(SharedOperationError):
                native_committed_owner_witness(j.root)
            j.advance("restored", second)
            self.assertEqual(native_committed_owner_witness(j.root)["id"],
                             first["id"])
            (j.root/"operation.json").write_text("broken")
            with self.assertRaises(SharedOperationError):
                native_committed_owner_witness(j.root)

    def test_native_gate_uses_only_trusted_shared_apply_owner(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            shared=root/"shared-apply"
            j=SharedApplyOperation(shared)
            for abandoned in ("voice-cutover", "voice-ipfw",
                              "voice-cutover-legacy-whole-receipt"):
                (root/abandoned).write_text("retired-old-evidence")
            self.assertTrue(native_lifecycle_gate(root=shared)["safe_to_mutate"])
            self.assertFalse(shared.exists())
            d1=detail()
            self.assertTrue(native_lifecycle_gate(root=shared)["safe_to_mutate"])
            j.advance("prepared",d1)
            self.assertFalse(native_lifecycle_gate("strategy-lab-native",root=shared)["safe_to_mutate"])
            self.assertFalse(native_lifecycle_gate(root=shared)["safe_to_mutate"])
            j.advance("activating",d1)
            self.assertFalse(native_lifecycle_gate(root=shared)["safe_to_mutate"])
            self.assertTrue(native_lifecycle_gate("common-recover-activating",root=shared)["safe_to_mutate"])
            self.assertFalse(native_lifecycle_gate("common-recover-saved",root=shared)["safe_to_mutate"])
            j.advance("activated",d1)
            self.assertTrue(native_lifecycle_gate("common-recover-activated",root=shared)["safe_to_mutate"])
            j.advance("config-saved",d1)
            self.assertTrue(native_lifecycle_gate("common-recover-saved",root=shared)["safe_to_mutate"])
            self.assertFalse(native_lifecycle_gate("common-apply",root=shared)["safe_to_mutate"])
            j.advance("committed",d1)
            self.assertFalse(native_lifecycle_gate(root=shared)["safe_to_mutate"])
            self.assertTrue(native_lifecycle_gate("common-apply",root=shared)["safe_to_mutate"])
            self.assertTrue(native_lifecycle_gate("strategy-lab-native",root=shared)["safe_to_mutate"])
            self.assertFalse(native_lifecycle_gate(root=shared)["safe_to_mutate"])
            with self.assertRaises(SharedOperationError):
                native_lifecycle_gate("legacy-skip",root=shared)
            (shared/"operation.json").write_text("untrusted")
            with self.assertRaises(SharedOperationError):
                native_lifecycle_gate("common-apply",root=shared)

    def test_production_service_uses_shared_gate_without_old_cutover(self):
        service=(BACKEND.parent/"zapret_service.sh").read_text()
        gate=service.split("preflight_shared_apply_journal()\n{",1)[1].split("\n}\n",1)[0]
        self.assertIn("shared_apply_operation.py",gate)
        self.assertIn('native-gate "$@"',gate)
        self.assertNotIn("voice_cutover_guard.py",gate)
        self.assertNotIn("voice-cutover",gate)
        cli=BACKEND/"shared_apply_operation.py"
        for arguments,expected in ((["native-gate"],69),
                                   (["native-gate","common-apply"],69),
                                   (["native-gate","bogus"],64)):
            result=subprocess.run([sys.executable,str(cli),*arguments],
                                  capture_output=True,text=True,check=False)
            self.assertEqual(expected,result.returncode, result.stderr)
            self.assertNotIn("Traceback",result.stderr)

    def test_reviewed_legacy_only_exact_first_voice_with_witness(self):
        with tempfile.TemporaryDirectory() as d:
            j=SharedApplyOperation(Path(d)/"shared-apply")
            item=detail()
            with self.assertRaises(SharedOperationError):
                j.reviewed_legacy_detail()
            for phase in ("prepared","activating","requires-review"):
                j.advance(phase,item)
            self.assertEqual(item,j.reviewed_legacy_detail())
            self.assertTrue(native_lifecycle_gate(
                "common-recover-reviewed-legacy",root=j.root)["safe_to_mutate"])
            self.assertFalse(native_lifecycle_gate("common-apply",root=j.root)["safe_to_mutate"])
            evidence=(j.root/"operation.json").read_bytes()
            for ident,proof in (("2"*32,lambda:True),(item["id"],lambda:False)):
                with self.assertRaises(SharedOperationError):
                    j.finish_reviewed_legacy(ident,proof)
                self.assertEqual(evidence,(j.root/"operation.json").read_bytes())
            self.assertEqual("restored",
                             j.finish_reviewed_legacy(item["id"],lambda:True)["phase"])
            self.assertTrue(native_lifecycle_gate("common-apply",root=j.root)["safe_to_mutate"])
            with self.assertRaises(SharedOperationError):
                j.finish_reviewed_legacy(item["id"],lambda:True)
        with tempfile.TemporaryDirectory() as d:
            j=SharedApplyOperation(Path(d)/"shared-apply")
            original=detail("a"*32)
            for phase in ("prepared","activating","activated","config-saved","committed"):
                j.advance(phase,original)
            second=detail("b"*32)
            for phase in ("prepared","activating","requires-review"):
                j.advance(phase,second)
            with self.assertRaises(SharedOperationError):
                j.reviewed_legacy_detail()
            self.assertEqual("requires-review",j.read()["phase"])

    def test_missing_state_stays_readonly(self):
        with tempfile.TemporaryDirectory() as d:
            j=SharedApplyOperation(Path(d)/"shared-apply")
            self.assertTrue(j.advisory()["safe_to_mutate"])
            self.assertFalse(j.root.exists())

    def test_phase_chain_durable_guard_terminal_new_operation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            j=SharedApplyOperation(root/"shared-apply")
            for phase in ("prepared","activating","activated","config-saved"):
                j.advance(phase,detail())
                snapshot=(j.root/"operation.json").read_bytes()
                guard=native_lifecycle_gate(root=root/"shared-apply")
                self.assertEqual(("blocked","shared-apply-pending",phase),
                                 (guard["state"],guard["reason"],guard["phase"]))
                self.assertEqual(snapshot,(j.root/"operation.json").read_bytes())
                self.assertEqual(0o700,j.root.stat().st_mode & 0o777)
                self.assertEqual(0o600,(j.root/"operation.json").stat().st_mode & 0o777)
            j.advance("committed",detail())
            self.assertTrue(j.advisory()["safe_to_mutate"])
            self.assertEqual("shared-runtime-owned",
                             native_lifecycle_gate(root=root/"shared-apply")["reason"])
            self.assertTrue(native_lifecycle_gate("common-apply", root=root/"shared-apply")["safe_to_mutate"])
            with self.assertRaises(SharedOperationError):
                j.advance("prepared",detail())
            j.advance("prepared",detail("2"*32))
            self.assertFalse(j.advisory()["safe_to_mutate"])

    def test_rollback_uncertainty_and_replay_refusal(self):
        samples=(
            ("prepared","activating","activated","restored"),
            ("prepared","activating","requires-review"),
            ("prepared","activating","activated","restore-failed"),
            ("prepared","activating","activated","config-saved","requires-review"),
        )
        for phases in samples:
            with self.subTest(phases=phases),tempfile.TemporaryDirectory() as d:
                j=SharedApplyOperation(Path(d)/"shared-apply")
                for p in phases:j.advance(p,detail())
                self.assertEqual(phases[-1]=="restored",j.advisory()["safe_to_mutate"])
                with self.assertRaises(SharedOperationError):
                    j.advance("activated",detail())

    def test_inspect_cli_has_no_root_override_and_requires_freebsd_fd9(self):
        cli=BACKEND/"shared_apply_operation.py"
        result=subprocess.run([sys.executable,str(cli),"inspect"],
                              text=True,capture_output=True,check=False)
        self.assertEqual(69,result.returncode)
        invalid=subprocess.run([sys.executable,str(cli),"inspect","/tmp/other"],
                               capture_output=True,check=False)
        self.assertEqual(64,invalid.returncode)
        safe_recovery=subprocess.run(
            [sys.executable,str(cli),"recover-prepared","1"*32],
            capture_output=True,text=True,check=False,
        )
        self.assertEqual(69,safe_recovery.returncode,
                         "recovery must refuse missing FreeBSD FD9 instead of crashing")
        self.assertNotIn("Traceback",safe_recovery.stderr)

    def test_prepared_only_recovery_attests_before_terminal_record(self):
        with tempfile.TemporaryDirectory() as folder:
            journal=SharedApplyOperation(Path(folder)/"shared-apply")
            d=detail()
            journal.advance("prepared",d)
            attempts=[]
            def witness():
                attempts.append("verified")
                return True
            journal.recover_prepared(d["id"],witness)
            self.assertEqual(["verified"],attempts)
            self.assertEqual("restored",journal.read()["phase"])
            with self.assertRaisesRegex(SharedOperationError,"prepared-only"):
                journal.recover_prepared(d["id"],witness)
        with tempfile.TemporaryDirectory() as folder:
            journal=SharedApplyOperation(Path(folder)/"shared-apply")
            d=detail()
            journal.advance("prepared",d)
            with self.assertRaisesRegex(SharedOperationError,"attestation"):
                journal.recover_prepared(d["id"],lambda: False)
            self.assertEqual("prepared",journal.read()["phase"])
            journal.advance("activating",d)
            with self.assertRaisesRegex(SharedOperationError,"prepared-only"):
                journal.recover_prepared(d["id"],lambda: True)
            self.assertEqual("activating",journal.read()["phase"])

    def test_previous_committed_owner_survives_prepared_power_cut_and_rollback(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            store=SharedApplyOperation(root/"shared-apply")
            initial=detail("a"*32)
            next_owner=detail("b"*32)
            for phase in ("prepared","activating","activated","config-saved","committed"):
                store.advance(phase,initial)
            self.assertEqual(initial,committed_owner(store.read()))
            prepared=store.advance("prepared",next_owner)
            self.assertEqual(initial,prepared["previous"])
            self.assertEqual("shared-apply-pending",
                             native_lifecycle_gate(root=root/"shared-apply")["reason"])
            restored=store.recover_prepared(next_owner["id"],lambda: True)
            self.assertEqual(initial,restored["previous"])
            self.assertEqual(initial,committed_owner(store.read()))
            old=native_lifecycle_gate(root=root/"shared-apply")
            self.assertEqual("shared-runtime-owned",old["reason"])
            self.assertFalse(old["safe_to_mutate"])
            self.assertTrue(native_lifecycle_gate("common-apply", root=root/"shared-apply")["safe_to_mutate"])
            with self.assertRaisesRegex(SharedOperationError,"predecessor ID"):
                store.advance("prepared",initial)
            third=detail("c"*32)
            carry=store.advance("prepared",third)
            self.assertEqual(initial,carry["previous"])

    def test_previous_common_owner_remains_during_safe_pre_save_rollback(self):
        with tempfile.TemporaryDirectory() as temp:
            store=SharedApplyOperation(Path(temp)/"shared-apply")
            first=detail("a"*32)
            second=detail("b"*32)
            for phase in ("prepared","activating","activated","config-saved","committed"):
                store.advance(phase,first)
            for phase in ("prepared","activating","activated","restored"):
                store.advance(phase,second)
            self.assertEqual(first,committed_owner(store.read()))
            self.assertEqual(first,store.read()["previous"])
            self.assertTrue(store.advisory()["safe_to_mutate"])

    def test_untrusted_predecessor_proof_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            store=SharedApplyOperation(root/"shared-apply")
            store.advance("prepared",detail("b"*32))
            import json
            path=store.root/"operation.json"
            record=json.loads(path.read_text())
            record["previous"]=detail("b"*32)
            path.write_text(json.dumps(record))
            with self.assertRaises(SharedOperationError):
                native_lifecycle_gate(root=root/"shared-apply")

    def test_pristine_activating_recovery_requires_previous_owner_and_attestation(self):
        with tempfile.TemporaryDirectory() as folder:
            j=SharedApplyOperation(Path(folder)/"shared-apply")
            previous=detail("a"*32)
            candidate=detail("b"*32)
            for phase in ("prepared","activating","activated","config-saved","committed"):
                j.advance(phase,previous)
            j.advance("prepared",candidate)
            j.advance("activating",candidate)
            with self.assertRaisesRegex(SharedOperationError,"pristine"):
                j.recover_activating_pristine(candidate["id"],"c"*32,lambda: True)
            with self.assertRaisesRegex(SharedOperationError,"attestation"):
                j.recover_activating_pristine(candidate["id"],previous["id"],lambda: False)
            self.assertEqual("activating",j.read()["phase"])
            restored=j.recover_activating_pristine(
                candidate["id"],previous["id"],lambda: True)
            self.assertEqual(previous,restored["previous"])
            self.assertEqual(previous,committed_owner(restored))
            with self.assertRaisesRegex(SharedOperationError,"pristine"):
                j.recover_activating_pristine(candidate["id"],previous["id"],lambda: True)
        with tempfile.TemporaryDirectory() as folder:
            j=SharedApplyOperation(Path(folder)/"shared-apply")
            d=detail("c"*32)
            j.advance("prepared",d)
            j.advance("activating",d)
            with self.assertRaisesRegex(SharedOperationError,"pristine"):
                j.recover_activating_pristine(d["id"],"a"*32,lambda: True)
            self.assertEqual("activating",j.read()["phase"])

    def test_cold_activated_completion_requires_predecessor_and_attestation(self):
        with tempfile.TemporaryDirectory() as folder:
            store=SharedApplyOperation(Path(folder)/"shared-apply")
            old=detail("a"*32); new=detail("b"*32)
            for phase in ("prepared","activating","activated","config-saved","committed"):
                store.advance(phase,old)
            for phase in ("prepared","activating","activated"):
                store.advance(phase,new)
            with self.assertRaisesRegex(SharedOperationError,"activated rollback"):
                store.finish_activated_restore(new["id"],"c"*32,lambda: True)
            with self.assertRaisesRegex(SharedOperationError,"attestation"):
                store.finish_activated_restore(new["id"],old["id"],lambda: False)
            self.assertEqual("activated",store.read()["phase"])
            restored=store.finish_activated_restore(new["id"],old["id"],lambda: True)
            self.assertEqual("restored",restored["phase"])
            self.assertEqual(old,committed_owner(restored))
            with self.assertRaisesRegex(SharedOperationError,"activated rollback"):
                store.finish_activated_restore(new["id"],old["id"],lambda: True)
        with tempfile.TemporaryDirectory() as folder:
            store=SharedApplyOperation(Path(folder)/"shared-apply")
            d=detail()
            for phase in ("prepared","activating","activated"):
                store.advance(phase,d)
            with self.assertRaisesRegex(SharedOperationError,"activated rollback"):
                store.finish_activated_restore(d["id"],"a"*32,lambda: True)

    def test_installed_activating_completion_requires_exact_previous(self):
        with tempfile.TemporaryDirectory() as folder:
            store=SharedApplyOperation(Path(folder)/"shared-apply")
            previous=detail("a"*32)
            new=detail("b"*32)
            for phase in ("prepared","activating","activated","config-saved","committed"):
                store.advance(phase,previous)
            store.advance("prepared",new)
            store.advance("activating",new)
            with self.assertRaisesRegex(SharedOperationError,"activating rollback"):
                store.finish_activating_installed_restore(new["id"],"c"*32,lambda: True)
            with self.assertRaisesRegex(SharedOperationError,"attestation"):
                store.finish_activating_installed_restore(new["id"],previous["id"],lambda: False)
            self.assertEqual("activating",store.read()["phase"])
            restored=store.finish_activating_installed_restore(new["id"],previous["id"],lambda: True)
            self.assertEqual(previous,committed_owner(restored))
            self.assertEqual("restored",restored["phase"])
            with self.assertRaisesRegex(SharedOperationError,"activating rollback"):
                store.finish_activating_installed_restore(new["id"],previous["id"],lambda: True)

    def test_installed_activating_cli_refuses_missing_freebsd_fd9(self):
        result=subprocess.run(
            [sys.executable,str(BACKEND/"shared_apply_operation.py"),
             "finish-activating","a"*32,"b"*32],
            capture_output=True,text=True,check=False)
        self.assertEqual(69,result.returncode)
        self.assertNotIn("Traceback",result.stderr)

    def test_activated_cli_refuses_missing_freebsd_fd9(self):
        result=subprocess.run([sys.executable,str(BACKEND/"shared_apply_operation.py"),
                               "finish-activated","a"*32,"b"*32],
                              capture_output=True,text=True,check=False)
        self.assertEqual(69,result.returncode)
        self.assertNotIn("Traceback",result.stderr)

    def test_post_save_recovery_only_after_attested_runtime_commit(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            j=SharedApplyOperation(root/"shared-apply")
            d=detail("4"*32)
            for phase in ("prepared","activating","activated","config-saved"):
                j.advance(phase,d)
            self.assertFalse(native_lifecycle_gate(root=root/"shared-apply")["safe_to_mutate"])
            self.assertFalse(native_lifecycle_gate("common-apply", root=root/"shared-apply")["safe_to_mutate"])
            self.assertTrue(native_lifecycle_gate("common-recover-saved", root=root/"shared-apply")["safe_to_mutate"])
            with self.assertRaisesRegex(SharedOperationError,"attestation"):
                j.finish_saved(d["id"],lambda: False)
            self.assertEqual("config-saved",j.read()["phase"])
            completed=j.finish_saved(d["id"],lambda: True)
            self.assertEqual("committed",completed["phase"])
            with self.assertRaisesRegex(SharedOperationError,"saved-only"):
                j.finish_saved(d["id"],lambda: True)
        with tempfile.TemporaryDirectory() as folder:
            j=SharedApplyOperation(Path(folder)/"shared-apply")
            d=detail()
            for phase in ("prepared","activating","activated"):
                j.advance(phase,d)
            with self.assertRaisesRegex(SharedOperationError,"saved-only"):
                j.finish_saved(d["id"],lambda: True)
            self.assertEqual("activated",j.read()["phase"])

    def test_activating_cli_refuses_unprivileged_or_missing_fd9(self):
        cli=BACKEND/"shared_apply_operation.py"
        result=subprocess.run([sys.executable,str(cli),"recover-activating",
                               "a"*32,"b"*32],
                              capture_output=True,text=True,check=False)
        self.assertEqual(69,result.returncode)
        self.assertNotIn("Traceback",result.stderr)

    def test_saved_finish_cli_refuses_unprivileged_or_missing_fd9(self):
        cli=BACKEND/"shared_apply_operation.py"
        result=subprocess.run([sys.executable,str(cli),"finish-saved","4"*32],
                              capture_output=True,text=True,check=False)
        self.assertEqual(69,result.returncode)
        self.assertNotIn("Traceback",result.stderr)

    def test_invalid_identity_fields_and_reordered_phase(self):
        with tempfile.TemporaryDirectory() as d:
            j=SharedApplyOperation(Path(d)/"shared-apply")
            good=detail()
            for bad in (
                {**good,"id":"wrong"},
                {**good,"page":"unknown"},
                {**good,"base":"bad"},
                {**good,"changed_fields":["hostlist.telegramips"]*2},
                {**good,"changed_fields":["../../etc/passwd"]},
            ):
                with self.assertRaises(SharedOperationError):
                    j.advance("prepared",bad)
            self.assertFalse(j.root.exists())
            j.advance("prepared",good)
            for phase,values in (("committed",good),
                                 ("activated",good),
                                 ("activating",detail("3"*32))):
                with self.assertRaises(SharedOperationError):
                    j.advance(phase,values)
            self.assertEqual("prepared",j.read()["phase"])

    def test_symlink_orphan_corruption_and_foreign_file_block(self):
        for issue in ("orphan","root-link","file-link","bad-json","extra","bad-mode"):
            with self.subTest(issue=issue),tempfile.TemporaryDirectory() as d:
                root=Path(d); j=SharedApplyOperation(root/"shared-apply")
                if issue=="root-link":
                    target=root/"other"; target.mkdir()
                    j.root.symlink_to(target)
                else:
                    # The writer itself creates the trusted root. Creating
                    # an empty root first intentionally represents a crash.
                    if issue in ("file-link","extra","bad-mode"):
                        j.advance("prepared",detail())
                    else:
                        j.root.mkdir(mode=0o700)
                    if issue=="file-link":
                        (j.root/"operation.json").unlink()
                        (j.root/"operation.json").symlink_to(root/"unknown")
                    elif issue=="bad-json":
                        (j.root/"operation.json").write_text("{bad")
                    elif issue=="extra":
                        (j.root/"tmp").write_text("unexpected")
                    elif issue=="bad-mode":
                        j.root.chmod(0o755)
                with self.assertRaises(SharedOperationError):
                    native_lifecycle_gate(root=root/"shared-apply")

    def test_cli_refuses_nonfreebsd_or_missing_fd9(self):
        cli=BACKEND/"shared_apply_operation.py"
        p=subprocess.run([sys.executable,str(cli),"record","prepared",
                          "1"*32,"voice","a"*64,"b"*64,"hostlist.telegramips"],
                         text=True,capture_output=True,check=False)
        self.assertEqual(69,p.returncode)

    def test_existing_service_routes_record_under_fd9(self):
        service=(BACKEND.parent/"zapret_service.sh").read_text()
        self.assertIn("shared_apply_record_service()",service)
        self.assertIn("shared-apply-record)",service)
        self.assertIn("service_with_lifecycle_lock",service)
        guard=service.split("if ! ",1)[0] if False else service.split(
            "# Do not permit ANY legacy lifecycle action",1)[1].split(
            'service_dispatch "$@"',1)[0]
        self.assertNotIn("shared-apply-record",guard)

if __name__=="__main__":
    unittest.main(verbosity=2)
