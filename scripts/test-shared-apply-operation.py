#!/usr/bin/env python3
"""Common Apply durable phases and existing lifecycle guard, without kernel changes."""
import sys
import subprocess
from unittest.mock import patch
import tempfile
from pathlib import Path
import unittest

BACKEND=Path(__file__).resolve().parents[1]/"src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0,str(BACKEND))
from shared_apply_operation import SharedApplyOperation,SharedOperationError,committed_owner
from voice_cutover_guard import check_pending

def detail(ident="1"*32):
    return {"id":ident,"page":"voice","base":"a"*64,
            "candidate":"b"*64,"changed_fields":[
                "voice.telegram.enabled","hostlist.telegramips"]}

class TestJournal(unittest.TestCase):
    def test_legacy_prepared_is_one_durable_blocking_common_journal(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            store=SharedApplyOperation(root/"shared-apply")
            record=store.prepare_legacy_predecessor(detail(), lambda: "f"*64)
            self.assertEqual("prepared",record["phase"])
            self.assertEqual("f"*64,record["legacy_predecessor"])
            self.assertEqual("shared-apply-pending",check_pending(
                root/"voice-cutover",root/"voice-ipfw")["reason"])
            reloaded=SharedApplyOperation(store.root)
            self.assertEqual(record,reloaded.read())
            with self.assertRaisesRegex(SharedOperationError,"reviewed executor"):
                reloaded.advance("activating",detail())
            with self.assertRaisesRegex(SharedOperationError,"reviewed executor"):
                reloaded.advance("restored",detail())
            with self.assertRaisesRegex(SharedOperationError,"prepared-only"):
                reloaded.recover_prepared(detail()["id"], lambda: True)
            with self.assertRaises(SharedOperationError):
                reloaded.prepare_legacy_predecessor(detail("2"*32),lambda: "b"*64)
            self.assertEqual(record,reloaded.read())

    def test_legacy_arm_attestation_failure_never_writes_journal(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            store=SharedApplyOperation(root/"shared-apply")
            with self.assertRaisesRegex(SharedOperationError,"fingerprint"):
                store.prepare_legacy_predecessor(detail(),lambda: "unsafe")
            self.assertFalse(store.root.exists())
            with self.assertRaises(SharedOperationError):
                store.prepare_legacy_predecessor(detail(),lambda: "")
            self.assertFalse(store.root.exists())
            with self.assertRaises(SharedOperationError):
                store.prepare_legacy_predecessor(detail("2"*32),lambda: None)
            self.assertFalse(store.root.exists())
            with self.assertRaises(SharedOperationError):
                store.prepare_legacy_predecessor(
                    {**detail(),"page":"strategies"},lambda: "f"*64)
            self.assertFalse(store.root.exists())

    def test_legacy_arm_cli_refuses_missing_root_fd9(self):
        result=subprocess.run([sys.executable,
            str(BACKEND/"shared_apply_operation.py"),"arm-legacy",
            "1"*32,"a"*64,"b"*64,"-"],capture_output=True,text=True)
        self.assertEqual(69,result.returncode)
        self.assertNotIn("Traceback",result.stderr)

    def test_operator_can_only_cancel_completely_unchanged_live_predecessor(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            store=SharedApplyOperation(root/"shared-apply")
            armed=store.prepare_legacy_predecessor(detail(),lambda:"f"*64)
            for observed in ("a"*64, "", None, True):
                with self.subTest(observed=observed):
                    with self.assertRaises(SharedOperationError):
                        store.cancel_pristine_legacy(detail()["id"],lambda:observed)
                    self.assertEqual(armed,store.read())
            with self.assertRaises(SharedOperationError):
                store.cancel_pristine_legacy("2"*32,lambda:"f"*64)
            self.assertEqual("shared-apply-pending",check_pending(
                root/"voice-cutover",root/"voice-ipfw")["reason"])
            restored=store.cancel_pristine_legacy(detail()["id"],lambda:"f"*64)
            self.assertEqual("restored",restored["phase"])
            self.assertNotIn("legacy_predecessor",restored)
            self.assertIsNone(committed_owner(restored))
            self.assertTrue(check_pending(
                root/"voice-cutover",root/"voice-ipfw")["safe_to_mutate"])
            self.assertEqual(restored,SharedApplyOperation(store.root).read())
            with self.assertRaises(SharedOperationError):
                store.cancel_pristine_legacy(detail()["id"],lambda:"f"*64)
            with self.assertRaises(SharedOperationError):
                store.advance("activating",detail())

    def test_cancellation_rejects_changed_journal_after_attestation(self):
        with tempfile.TemporaryDirectory() as folder:
            store=SharedApplyOperation(Path(folder)/"shared-apply")
            armed=store.prepare_legacy_predecessor(detail(),lambda:"f"*64)
            def bad_witness():
                # Simulate a foreign/nonterminal journal swap during observer.
                target=store.root/"operation.json"
                # Replace a single valid field in-place, preserving schema
                # and the persistent armed phase so the observer can detect
                # a different but still parseable journal record.
                content=target.read_text().replace('"id":"'+"1"*32+'"','"id":"'+"2"*32+'"')
                target.write_text(content)
                return "f"*64
            with self.assertRaises(SharedOperationError):
                store.cancel_pristine_legacy(detail()["id"],bad_witness)
            self.assertEqual("2"*32,store.read()["detail"]["id"])
            self.assertEqual("prepared",store.read()["phase"])
            # Never accepted a changed durable identity as cancel authority.

    def test_legacy_cancel_cli_is_not_generic_freebsd_bypass(self):
        result=subprocess.run([sys.executable,
            str(BACKEND/"voice_native_legacy_predecessor_route.py"),"cancel-common",
            "1"*32],capture_output=True,text=True)
        self.assertEqual(69,result.returncode)
        self.assertNotIn("Traceback",result.stderr)

    def test_durable_legacy_quiescing_boundary_preserves_old_proof_and_can_cancel(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            store=SharedApplyOperation(root/"shared-apply")
            initial=store.prepare_legacy_predecessor(detail(),lambda:"f"*64)
            with self.assertRaises(SharedOperationError):
                store.begin_legacy_quiesce(detail()["id"],lambda:"a"*64)
            self.assertEqual(initial,store.read())
            record=store.begin_legacy_quiesce(detail()["id"],lambda:"f"*64)
            self.assertEqual("legacy-quiescing",record["phase"])
            self.assertEqual(initial["legacy_predecessor"],record["legacy_predecessor"])
            self.assertEqual(record,SharedApplyOperation(store.root).read())
            self.assertEqual("shared-apply-pending",check_pending(
                root/"voice-cutover",root/"voice-ipfw")["reason"])
            with self.assertRaises(SharedOperationError):
                store.begin_legacy_quiesce(detail()["id"],lambda:"f"*64)
            with self.assertRaises(SharedOperationError):
                store.advance("activating",detail())
            with self.assertRaises(SharedOperationError):
                store.recover_prepared(detail()["id"],lambda:True)
            with self.assertRaises(SharedOperationError):
                store.cancel_pristine_legacy(detail()["id"],lambda:"a"*64)
            self.assertEqual(record,store.read())
            done=store.cancel_pristine_legacy(detail()["id"],lambda:"f"*64)
            self.assertEqual("restored",done["phase"])
            self.assertNotIn("legacy_predecessor",done)
            self.assertTrue(store.advisory()["safe_to_mutate"])

    def test_old_legacy_quiescing_cannot_close_after_identity_swap(self):
        with tempfile.TemporaryDirectory() as folder:
            store=SharedApplyOperation(Path(folder)/"shared-apply")
            store.prepare_legacy_predecessor(detail(),lambda:"f"*64)
            saved=store.begin_legacy_quiesce(detail()["id"],lambda:"f"*64)
            reloaded=SharedApplyOperation(store.root)
            with self.assertRaises(SharedOperationError):
                reloaded.cancel_pristine_legacy("2"*32,lambda:"f"*64)
            with self.assertRaises(SharedOperationError):
                reloaded.cancel_pristine_legacy(detail()["id"],lambda:None)
            self.assertEqual(saved,reloaded.read())

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
                guard=check_pending(root/"voice-cutover",root/"voice-ipfw")
                self.assertEqual(("blocked","shared-apply-pending",phase),
                                 (guard["state"],guard["reason"],guard["phase"]))
                self.assertEqual(snapshot,(j.root/"operation.json").read_bytes())
                self.assertEqual(0o700,j.root.stat().st_mode & 0o777)
                self.assertEqual(0o600,(j.root/"operation.json").stat().st_mode & 0o777)
            j.advance("committed",detail())
            self.assertTrue(j.advisory()["safe_to_mutate"])
            self.assertEqual("shared-runtime-owned",
                             check_pending(root/"voice-cutover",root/"voice-ipfw")["reason"])
            self.assertTrue(check_pending(root/"voice-cutover",root/"voice-ipfw",
                                          native_scope=True)["safe_to_mutate"])
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
                             check_pending(root/"voice-cutover",root/"voice-ipfw")["reason"])
            restored=store.recover_prepared(next_owner["id"],lambda: True)
            self.assertEqual(initial,restored["previous"])
            self.assertEqual(initial,committed_owner(store.read()))
            old=check_pending(root/"voice-cutover",root/"voice-ipfw")
            self.assertEqual("shared-runtime-owned",old["reason"])
            self.assertFalse(old["safe_to_mutate"])
            self.assertTrue(check_pending(root/"voice-cutover",root/"voice-ipfw",
                                          native_scope=True)["safe_to_mutate"])
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
            self.assertEqual("invalid-or-untrusted-journal",
                check_pending(root/"voice-cutover",root/"voice-ipfw")["reason"])

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
            self.assertFalse(check_pending(root/"voice-cutover",root/"voice-ipfw")["safe_to_mutate"])
            self.assertFalse(check_pending(root/"voice-cutover",root/"voice-ipfw",
                                           native_scope=True)["safe_to_mutate"])
            self.assertTrue(check_pending(root/"voice-cutover",root/"voice-ipfw",
                                         native_scope=True,recover_saved=True)["safe_to_mutate"])
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
                status=check_pending(root/"voice-cutover",root/"voice-ipfw")
                self.assertEqual("invalid-or-untrusted-journal",status["reason"])
                self.assertFalse(status["safe_to_mutate"])

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
