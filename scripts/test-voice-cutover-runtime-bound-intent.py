#!/usr/bin/env python3
"""Schema-4 write-once Voice cutover: seal EXACT candidate runtime, not live guesses."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))
from voice_cutover_journal import (
    CutoverJournalError, RUNTIME_BOUND_SCHEMA, RUNTIME_FIELD,
    SECURITY_FIELD, VoiceCutoverJournal, bound_candidate_runtime,
    new_runtime_bound_record,
)
from voice_native_file_observer import observe_live_files
from voice_native_supervisor_launch import canonical_supervisor_argv
from voice_security_policy_evidence import inspect_security_policy

spec=importlib.util.spec_from_file_location(
    "intent_security_fixture",ROOT/"scripts/test-voice-security-policy-evidence.py"
)
assert spec and spec.loader
fixture=importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class RuntimeBoundCutoverTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix="voice-schema4-")
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.fixture=fixture.SecurityPolicyTests()
        self.before=self.fixture.setup(
            temp.name,supervisor_argv=canonical_supervisor_argv(fixture.SCRIPTS)
        )
        self.whole,self.ipfw,self.backup,self.process,self.policy, \
            self.prior,self.policy_sha=self.before
        self.stage_config=self.root/"staged-config.xml"
        self.stage_config.write_bytes((self.root/"config.xml").read_bytes())
        self.stage_config.chmod(0o600)
        self.candidate=self.root/"candidate-runtime"
        self.candidate.mkdir(mode=0o700)
        self.argv=self.candidate/"dvtws.args"
        self.argv.write_bytes(b"--port=989\n--filter=udp\n")
        self.argv.chmod(0o600)
        self.proof={
            "saved_xml_sha256":hashlib.sha256(self.stage_config.read_bytes()).hexdigest(),
            "merged_sha256":"f"*64,
            "native_argv_sha256":hashlib.sha256(self.argv.read_bytes()).hexdigest(),
        }

    def begin(self):
        self.whole.begin_runtime_bound(
            self.prior,self.proof,fixture.IPFW,self.policy,self.backup,
            self.process,fixture.SCRIPTS,
            staged_config=self.stage_config,candidate_runtime=self.candidate,
        )

    def test_intent_reopen_has_exact_candidate_tree_and_policy_fingerprint(self):
        expected=observe_live_files(self.stage_config,self.candidate)["runtime"]
        self.begin()
        saved=self.whole.read()
        self.assertEqual(saved["schema"],RUNTIME_BOUND_SCHEMA)
        self.assertEqual(bound_candidate_runtime(saved),expected)
        self.assertEqual(saved["candidate"][RUNTIME_FIELD],expected)
        self.assertEqual(saved["candidate"][SECURITY_FIELD],self.policy_sha)
        self.whole.mark_mutating()
        reread=VoiceCutoverJournal(self.whole.directory).read()
        self.assertEqual(bound_candidate_runtime(reread),expected)
        verified=inspect_security_policy(
            self.policy,self.backup,self.process,journal_record=reread,
            expected_scripts=fixture.SCRIPTS
        )
        self.assertEqual(verified["policy_sha256"],self.policy_sha)
        self.assertEqual(2,verified["schema"])
        self.assertNotEqual(expected,reread["previous"]["runtime"])
        self.assertIsNotNone(self.ipfw.owned())
        self.assertIsNone(self.ipfw.pending())

    def test_older_cutover_schemas_never_supply_production_candidate_digest(self):
        for schema in (1,2,3):
            with self.subTest(schema=schema):
                if schema==1:
                    from voice_cutover_journal import new_record
                    record=new_record(self.prior,self.proof)
                elif schema==2:
                    from voice_cutover_journal import new_bound_record
                    record=new_bound_record(self.prior,self.proof,fixture.IPFW)
                else:
                    from voice_cutover_journal import new_security_bound_record
                    record=new_security_bound_record(
                        self.prior,self.proof,fixture.IPFW,self.policy_sha
                    )
                with self.assertRaises(CutoverJournalError):
                    bound_candidate_runtime(record)
        self.begin()
        self.whole.mark_mutating()
        self.whole.commit()
        with self.assertRaises(CutoverJournalError):
            bound_candidate_runtime(self.whole.read())

    def test_corrupt_or_foreign_staging_does_not_write_intent(self):
        for kind in ("wrong-xml","wrong-args","linked-args","public-args",
                     "missing-tree","different-policy"):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory(
                prefix="voice-schema4-foreign-"
            ) as directory:
                sub=RuntimeBoundCutoverTests()
                sub.setUp()
                try:
                    if kind=="wrong-xml":
                        sub.stage_config.write_text("<foreign/>")
                    elif kind=="wrong-args":
                        sub.argv.write_text("--invalid\n")
                    elif kind=="linked-args":
                        sub.argv.unlink()
                        sub.argv.symlink_to(sub.stage_config)
                    elif kind=="public-args":
                        sub.argv.chmod(0o644)
                    elif kind=="missing-tree":
                        sub.argv.unlink()
                    else:
                        sub.policy_sha="0"*64
                        sub.prior={**sub.prior,"engine":"0"*64}
                    with self.assertRaises((OSError,ValueError,RuntimeError)):
                        sub.begin()
                    self.assertIsNone(sub.whole.read())
                finally:
                    sub.doCleanups()

    def test_torn_record_cannot_masquerade_as_previous_runtime(self):
        self.begin()
        before=self.whole.read()
        record=copy.deepcopy(before)
        record["candidate"][RUNTIME_FIELD]="0"*64
        with self.assertRaises(CutoverJournalError):
            from voice_cutover_journal import validate_record
            validate_record(record)
        # A changed external stage does not change a durable earlier
        # fingerprint: reboot recovery takes the JOURNAL hash, not new bytes.
        self.argv.write_bytes(b"--foreign-after-intent\n")
        self.assertEqual(bound_candidate_runtime(self.whole.read()),
                         before["candidate"][RUNTIME_FIELD])
        self.assertNotEqual(
            observe_live_files(self.stage_config,self.candidate)["runtime"],
            bound_candidate_runtime(self.whole.read())
        )

    def test_no_implicit_overwrite_or_commit_without_evidence(self):
        self.begin()
        with self.assertRaises(CutoverJournalError):
            self.begin()
        self.assertIsNone(self.ipfw.pending())


if __name__=="__main__":
    unittest.main(verbosity=2)
