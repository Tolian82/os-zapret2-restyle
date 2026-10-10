#!/usr/bin/env python3
"""Real isolated Config+runtime rollback under ONE held Config inode flock."""
from __future__ import annotations

import fcntl
import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
BACKEND=ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0,str(BACKEND))

import voice_cutover_file_rollback as both
import voice_cutover_config_restore as config_backend
import voice_cutover_runtime_restore as runtime_backend
from voice_cutover_journal import VoiceCutoverJournal
from voice_native_file_observer import observe_live_files

spec=importlib.util.spec_from_file_location(
    "file_restore_fixture",ROOT/"scripts/test-voice-cutover-runtime-restore.py"
)
assert spec and spec.loader
fixture=importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
ORIGINAL=fixture.RuntimeRecovery
CANDIDATE_CONFIG=b"<candidate/>"


class TwoFileRollback(unittest.TestCase):
    # Reuse exact saved previous Config/runtime and modified candidate trees
    # from the already independently tested real runtime recovery fixture.
    setUp=ORIGINAL.setUp
    begin=ORIGINAL.begin
    sha=ORIGINAL.sha
    paths=ORIGINAL.paths

    def call(self, *, require_quiescent=None, require_lifecycle_owner=None):
        return both.restore_previous_files(
            self.config,self.active,self.image,self.backup,self.journal,
            expected_owner=(os.geteuid(),os.getegid()),
            expected_candidate_runtime_sha256=self.candidate_sha,
            require_lifecycle_owner=(
                require_lifecycle_owner if require_lifecycle_owner is not None
                else lambda:None
            ),
            require_quiescent=(
                require_quiescent if require_quiescent is not None
                else lambda:True
            ),
        )

    def start(self):
        self.begin()
        self.config.write_bytes(CANDIDATE_CONFIG)
        self.config.chmod(0o600)

    def test_two_real_file_domains_restore_keep_all_intents(self):
        self.start()
        inode=self.config.stat().st_ino
        before_runtime=self.candidate_sha
        output=self.call()
        self.assertEqual(output["state"],"previous-files-restored")
        self.assertIs(output["safe_to_restart_engine"],False)
        self.assertIs(output["safe_to_clear_intent"],False)
        self.assertEqual(self.config.stat().st_ino,inode)
        self.assertEqual(self.config.read_bytes(),
                         (self.image/"config.xml").read_bytes())
        self.assertEqual(self.config.stat().st_mode & 0o777,0o640)
        self.assertEqual(self.sha(self.active),self.previous["runtime"])
        ready,retired=self.paths()
        self.assertFalse(ready.exists())
        self.assertEqual(self.sha(retired),before_runtime)
        self.assertTrue((self.journal_dir/"runtime-restore-redo.json").exists())
        self.assertTrue((self.journal_dir/"config-restore-redo.json").exists())
        self.assertEqual(self.journal.read()["phase"],"mutating")
        self.assertEqual(self.call()["state"],"previous-files-restored")

    def test_single_flock_is_held_during_runtime_and_config(self):
        self.start()
        real_runtime=both.restore_previous_runtime
        real_config=both.restore_previous_config_in_place
        checkpoints=[]
        def assert_competing_fd_cannot_lock():
            with self.config.open("r+b") as contender:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(contender,fcntl.LOCK_EX|fcntl.LOCK_NB)
            checkpoints.append(True)
        def watched_runtime(*a,**kw):
            assert_competing_fd_cannot_lock()
            return real_runtime(*a,**kw)
        def watched_config(*a,**kw):
            assert_competing_fd_cannot_lock()
            self.assertIsInstance(kw["locked_config_fd"],int)
            return real_config(*a,**kw)
        with patch.object(both,"restore_previous_runtime",
                          side_effect=watched_runtime), \
             patch.object(both,"restore_previous_config_in_place",
                          side_effect=watched_config):
            self.assertEqual(self.call()["state"],"previous-files-restored")
        self.assertEqual(checkpoints,[True,True])
        # After the transaction returns, our Config lease is released.
        with self.config.open("r+b") as contender:
            fcntl.flock(contender,fcntl.LOCK_EX|fcntl.LOCK_NB)

    def test_crash_after_runtime_before_config_is_resumable(self):
        self.start()
        real_config=both.restore_previous_config_in_place
        with patch.object(both,"restore_previous_config_in_place",
                          side_effect=OSError("crash before Config writer")):
            with self.assertRaisesRegex(OSError,"crash before"):
                self.call()
        self.assertEqual(self.sha(self.active),self.previous["runtime"])
        self.assertEqual(self.config.read_bytes(),CANDIDATE_CONFIG)
        self.assertEqual(self.journal.read()["phase"],"mutating")
        self.assertTrue((self.journal_dir/"runtime-restore-redo.json").exists())
        self.assertFalse((self.journal_dir/"config-restore-redo.json").exists())
        self.assertEqual(self.call()["state"],"previous-files-restored")
        self.assertEqual(self.config.read_bytes(),
                         (self.image/"config.xml").read_bytes())

    def test_partial_config_write_resumes_with_both_redos(self):
        self.start()
        def truncated(fd,bytes_):
            os.write(fd,bytes_[:6])
            raise OSError("crash during Config content write")
        with patch.object(config_backend,"_write_all",side_effect=truncated):
            with self.assertRaisesRegex(OSError,"crash during Config"):
                self.call()
        self.assertEqual(self.config.read_bytes(),
                         (self.image/"config.xml").read_bytes()[:6])
        self.assertTrue((self.journal_dir/"runtime-restore-redo.json").exists())
        self.assertTrue((self.journal_dir/"config-restore-redo.json").exists())
        self.assertEqual(self.journal.read()["phase"],"mutating")
        result=self.call()
        self.assertEqual(result["state"],"previous-files-restored")
        self.assertEqual(self.sha(self.active),self.previous["runtime"])

    def test_quiescence_refuses_without_mutation(self):
        self.start()
        with self.assertRaisesRegex(
            both.VoiceFileRollbackError,"quiescence"
        ):
            self.call(require_quiescent=lambda:False)
        self.assertEqual(self.sha(self.active),self.candidate_sha)
        self.assertEqual(self.config.read_bytes(),CANDIDATE_CONFIG)
        self.assertFalse((self.journal_dir/"runtime-restore-redo.json").exists())

    def test_lost_quiescence_after_runtime_keeps_journal(self):
        self.start()
        calls=[0]
        def quiescence():
            calls[0]+=1
            return calls[0]!=3
        with self.assertRaisesRegex(
            both.VoiceFileRollbackError,"quiescence"
        ):
            self.call(require_quiescent=quiescence)
        self.assertEqual(self.sha(self.active),self.previous["runtime"])
        self.assertEqual(self.config.read_bytes(),CANDIDATE_CONFIG)
        self.assertEqual(self.journal.read()["phase"],"mutating")
        self.assertEqual(self.call()["state"],"previous-files-restored")

    def test_busy_config_prevents_runtime_mutation(self):
        self.start()
        with self.config.open("r+b") as lock_owner:
            fcntl.flock(lock_owner,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaisesRegex(
                both.VoiceFileRollbackError,"flock"
            ):
                self.call()
        self.assertEqual(self.sha(self.active),self.candidate_sha)
        self.assertEqual(self.config.read_bytes(),CANDIDATE_CONFIG)
        self.assertFalse((self.journal_dir/"runtime-restore-redo.json").exists())

    def test_corrupt_runtime_after_rollback_denies_transaction(self):
        self.start()
        self.assertEqual(self.call()["state"],"previous-files-restored")
        (self.active/"dvtws.args").write_text("foreign")
        with self.assertRaises(Exception):
            self.call()
        self.assertEqual(self.journal.read()["phase"],"mutating")


if __name__=="__main__":
    unittest.main(verbosity=2)
