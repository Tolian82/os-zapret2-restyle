#!/usr/bin/env python3
"""Common Apply durable phases and existing lifecycle guard, without kernel changes."""
import sys
import subprocess
import tempfile
from pathlib import Path
import unittest

BACKEND=Path(__file__).resolve().parents[1]/"src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0,str(BACKEND))
from shared_apply_operation import SharedApplyOperation,SharedOperationError
from voice_cutover_guard import check_pending

def detail(ident="1"*32):
    return {"id":ident,"page":"voice","base":"a"*64,
            "candidate":"b"*64,"changed_fields":[
                "voice.telegram.enabled","hostlist.telegramips"]}

class TestJournal(unittest.TestCase):
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
