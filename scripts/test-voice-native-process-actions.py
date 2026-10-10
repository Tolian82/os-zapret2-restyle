#!/usr/bin/env python3
"""Five-resource rollback with native one-engine process actuator boundaries.

Tests execute REAL Config/runtime/redo/ledger mutations and exact process
adapter argv/FD9 passing; native shell/process/kernel calls are simulated.
Production shell helper is checked with /bin/sh -n, never executed by CI.
"""
from __future__ import annotations

import fcntl
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
BACKEND=ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0,str(BACKEND))
import voice_native_process_actions as native_actions
import voice_cutover_five_resource_rollback as rollback
import voice_native_recovery_quiescence as gate
import voice_process_recovery_evidence as proc_evidence


def source(name, filename):
    spec=importlib.util.spec_from_file_location(name, ROOT/"scripts"/filename)
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

previous=source("native_process_actuator_five_fixture",
                "test-voice-cutover-five-resource-rollback.py")
shell_path=BACKEND/"voice_native_process_lifecycle.sh"


class NativeProcessActionTests(previous.FiveDomainRecovery):
    # The inherited five-resource tests also run under this subclass,
    # with their original deterministic fake stop/start callbacks.
    def fake_runner(self, args, **kwargs):
        self.executed.append((args,kwargs))
        self.assertEqual(args,["/bin/sh",str(self.script),"stop" if not
                               self.script_state else "start"])
        self.assertEqual(kwargs["pass_fds"],(9,))
        self.assertFalse(kwargs["check"])
        self.assertTrue(kwargs["capture_output"])
        self.assertEqual(kwargs["env"]["LC_ALL"],"C")
        self.assertNotIn("shell",kwargs)
        with self.config.open("r+b") as competing:
            with self.assertRaises(BlockingIOError):
                fcntl.flock(competing,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if not self.script_state:
            self.stop()
            self.script_state=True
        else:
            self.restart()
        return subprocess.CompletedProcess(args,0,stdout="",stderr="")

    def factory(self, fd):
        return native_actions.FreeBSDVoiceProcessActions(
            probe=self.probe, journal=self.journal,
            previous_backup=self.backup, active_runtime=self.active,
            config_path=self.config, config_owner=(os.geteuid(),os.getegid()),
            config_fd=fd, require_lifecycle_owner=lambda:None,
            runner=self.fake_runner, actuator=self.script,
        )

    def native_rollback(self, *, factory=None):
        with patch.object(gate,"PIDFILES",self.pidfiles), \
             patch.object(native_actions,"PIDFILES",self.pidfiles):
            return rollback.restore_previous_five_resources(
                journal=self.journal,ledger=self.store,
                previous_backup=self.backup,install_image=self.image,
                process_evidence=self.process_evidence,
                expected_scripts=gate.EXPECTED_SCRIPTS,
                config_path=self.config,active_runtime=self.active,
                expected_owner=(os.geteuid(),os.getegid()),
                expected_candidate_runtime_sha256=self.candidate_sha,
                candidate_proof=self.proof,process_probe=self.probe,
                read_ipfw_adapter=self.reader,write_ipfw_adapter=self.writer,
                process_actions_factory=factory or self.factory,
                require_lifecycle_owner=lambda:None,
            )

    def prepare(self):
        self.initialize(pending=True)
        self.script=self.base/"native-lifecycle.sh"
        self.script.write_text("#!/bin/sh\nexit 0\n")
        self.script.chmod(0o600)
        self.script_state=False
        self.executed=[]

    def test_real_file_and_ipfw_rollback_with_native_process_adapter(self):
        self.prepare()
        result=self.native_rollback()
        self.assertEqual(result["state"],"five-previous-domains-observed")
        self.assertEqual(self.history,["stop","restart"])
        self.assertEqual([cmd[0][-1] for cmd in self.executed],["stop","start"])
        self.assertEqual(self.sha(self.active),self.previous["runtime"])
        self.assertEqual(self.config.read_bytes(),
                         (self.image/"config.xml").read_bytes())
        self.assertIsNone(self.store.pending())
        self.assertEqual(self.journal.read()["phase"],"mutating")
        self.assertTrue((self.journal_dir/"runtime-restore-redo.json").exists())
        self.assertTrue((self.journal_dir/"config-restore-redo.json").exists())

    def _reject_bad_shell(self, case):
        self.prepare()
        if case=="symlink":
            self.script.unlink()
            self.script.symlink_to(self.config)
        else:
            self.script.chmod(0o666)
        with self.assertRaises(native_actions.NativeVoiceProcessActionError):
            self.native_rollback()
        self.assertEqual(self.executed,[])
        self.assertEqual(self.history,[])
        self.assertEqual(self.sha(self.active),self.candidate_sha)
        self.assertIsNotNone(self.store.pending())

    def test_linked_shell_refused_before_mutation(self):
        self._reject_bad_shell("symlink")

    def test_world_writable_shell_refused_before_mutation(self):
        self._reject_bad_shell("world-writable")

    def test_fake_success_without_stopping_is_refused(self):
        self.prepare()
        def no_stop(args,**kwargs):
            self.executed.append((args,kwargs))
            return subprocess.CompletedProcess(args,0,stdout="",stderr="")
        self.fake_runner=no_stop
        with self.assertRaises(native_actions.NativeVoiceProcessActionError):
            self.native_rollback()
        self.assertEqual(self.config.read_bytes(),b"<candidate/>")
        self.assertEqual(self.sha(self.active),self.candidate_sha)
        self.assertIsNotNone(self.store.pending())

    def test_factory_with_foreign_config_descriptor_denied(self):
        self.prepare()
        def wrong_factory(fd):
            action=self.factory(fd)
            action.config_fd=fd+1
            return action
        with self.assertRaises(rollback.FiveResourceRollbackError):
            self.native_rollback(factory=wrong_factory)
        self.assertEqual(self.executed,[])
        self.assertEqual(self.history,[])

    def test_old_runtime_must_exist_before_start(self):
        self.prepare()
        self.script_state=True
        # Give a native controller a true pinned Config lock, but do not
        # swap the live candidate runtime to previous yet.
        with self.config.open("r+b") as fd:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with patch.object(native_actions,"PIDFILES",self.pidfiles):
                action=self.factory(fd.fileno())
                self.stop()
                with self.assertRaises(native_actions.NativeVoiceProcessActionError):
                    action.start_previous()
        self.assertEqual(self.executed,[])

    def test_executable_shell_helper_syntax_and_allowlist(self):
        report=subprocess.run(["/bin/sh","-n",str(shell_path)],
                              capture_output=True,text=True,check=False)
        self.assertEqual(report.returncode,0,report.stderr)
        body=shell_path.read_text()
        for keyword in ("supervisor_stop", "launcher_stop",
                        "launcher_start_once", "supervisor_start",
                        'case "$1" in', ': <&9'):
            self.assertIn(keyword,body)
        self.assertNotIn("daemon -r",body.split("case \"$1\" in")[-1])


if __name__=="__main__":
    # Avoid subclass re-running inherited test fixtures; only local tests.
    names=[name for name in NativeProcessActionTests.__dict__ if name.startswith("test_")]
    suite=unittest.TestSuite(NativeProcessActionTests(name) for name in names)
    unittest.TextTestRunner(verbosity=2).run(suite)
