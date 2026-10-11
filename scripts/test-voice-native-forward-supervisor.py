#!/usr/bin/env python3
"""Real _69.._74 filesystem/ledger fixture -> simulated _75 supervisor."""
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
from voice_native_forward_supervisor import start_forward_voice_supervisor
from voice_native_kernel_argv import FreeBSDKernelArgvReader, SYSTEM_PATHS
from voice_native_supervisor_launch import canonical_supervisor_argv
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS

spec=importlib.util.spec_from_file_location(
    "forward_supervisor_fixture",ROOT/"scripts/test-voice-native-forward-ipfw.py"
)
assert spec and spec.loader
fixture=importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class ForwardSupervisorTests(unittest.TestCase):
    def setUp(self):
        self.parent=fixture.ForwardIPFWTests()
        self.parent.setUp()
        self.addCleanup(self.parent.doCleanups)
        self.parent.call()
        self.fx=self.parent.fx
        self.phase=self.parent.phase
        self.probe=self.phase.probe
        self.ps=self.phase.reader
        self.plan=canonical_supervisor_argv(EXPECTED_SCRIPTS)
        self.pids={"engine":201,"daemon":None,"monitor":None}
        self.probe._read_pid=lambda path:next(
            self.pids[role] for role,name in self.probe.pidfiles.items() if name==path
        )
        self.commands={201:" ".join(self.phase.expected)}
        self.ps.commands=self.commands
        self.argv={
            201:("\0".join(self.phase.expected)+"\0").encode("ascii"),
            202:("\0".join(self.plan["daemon"])+"\0").encode("ascii"),
            203:("\0".join(self.plan["monitor"])+"\0").encode("ascii"),
        }
        self.binary={
            201:SYSTEM_PATHS["engine"],202:SYSTEM_PATHS["daemon"],
            203:SYSTEM_PATHS["monitor"],
        }
        self.kernel=FreeBSDKernelArgvReader(
            raw_argv_reader=lambda pid:self.argv[pid],
            raw_path_reader=lambda pid:(self.binary[pid]+"\0").encode("ascii"),
        )
        self.script=self.fx.root/"supervisor-actuator.sh"
        self.script.write_text("#!/bin/sh\nexit 69\n")
        self.script.chmod(0o600)
        self.calls=[]
        self.fail=False
        self.no_start=False
        self.legacy=patch("voice_native_forward_supervisor.require_no_legacy")
        self.legacy.start()
        self.addCleanup(self.legacy.stop)

    def runner(self,argv,**opts):
        self.calls.append((argv,opts))
        self.assertEqual(["/bin/sh",str(self.script),"start-candidate-supervisor"],argv)
        self.assertEqual((9,),opts["pass_fds"])
        self.assertEqual(45,opts["timeout"])
        self.assertFalse(opts["check"])
        self.assertNotIn("shell",opts)
        with (self.fx.root/"config.xml").open("rb+") as other:
            with self.assertRaises(BlockingIOError):
                fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if not self.fail and not self.no_start:
            self.pids.update(daemon=202,monitor=203)
            self.commands[202]=" ".join(self.plan["daemon"])
            self.commands[203]=" ".join(self.plan["monitor"])
        return subprocess.CompletedProcess(argv,1 if self.fail else 0,
            stdout="",stderr="failed" if self.fail else "")

    def call(self,*,locked=True):
        config=self.fx.root/"config.xml"
        fd=os.open(config,os.O_RDWR)
        try:
            if locked:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return start_forward_voice_supervisor(
                journal=self.fx.whole,ledger=self.fx.ipfw,
                previous_backup=self.fx.backup,
                active_runtime=self.fx.root/"runtime",
                staged_config=self.fx.stage_config,candidate_runtime=self.fx.candidate,
                config_path=config,desired_manifest=self.parent.desired,
                probe=self.probe,kernel_reader=self.kernel,
                readonly_adapter=self.parent.read,
                config_fd=fd,config_owner=(os.geteuid(),os.getegid()),
                require_lifecycle_owner=lambda:None,
                runner=self.runner,actuator=self.script,
            )
        finally:
            os.close(fd)

    def test_supervisor_after_real_ipfw_precommit(self):
        original,pending=self.fx.whole.read(),self.fx.ipfw.pending()
        report=self.call()
        self.assertEqual("candidate-engine-ipfw-supervisor-kernel-verified",
                         report["state"])
        self.assertTrue(report["supervisor_started"])
        self.assertIs(report["voice_on"],False)
        self.assertIs(report["can_commit"],False)
        self.assertEqual([201,202,203],
                         [report["engine_pid"],report["daemon_pid"],report["monitor_pid"]])
        self.assertEqual(original,self.fx.whole.read())
        self.assertEqual(pending,self.fx.ipfw.pending())
        self.assertEqual(1,len(self.calls))
        self.assertEqual("running",self.probe.observe_processes()["engine"]["state"])

    def test_missing_config_flock_or_pending_denies_start(self):
        with self.assertRaises((OSError,RuntimeError,ValueError)):
            self.call(locked=False)
        self.assertFalse(self.calls)
        (self.fx.ipfw.directory/"intent.json").unlink()
        with self.assertRaises((OSError,RuntimeError,ValueError)):
            self.call()
        self.assertFalse(self.calls)

    def test_modified_live_ipfw_denies_before_process_change(self):
        self.parent.kernel.rules[19005]=[
            "divert","989","udp","from","any","to","any","596",
            "out","not","diverted","not","sockarg","xmit","vtnet1",
        ]
        with self.assertRaises((OSError,RuntimeError,ValueError)):
            self.call()
        self.assertFalse(self.calls)

    def test_changed_runtime_and_kernel_argv_denies_before_start(self):
        self.argv[201]=b"/bin/foreign\0"
        with self.assertRaises((OSError,RuntimeError,ValueError)):
            self.call()
        self.argv[201]=("\0".join(self.phase.expected)+"\0").encode("ascii")
        (self.fx.root/"runtime"/"dvtws.args").write_text("--port=999\n")
        with self.assertRaises((OSError,RuntimeError,ValueError)):
            self.call()
        self.assertFalse(self.calls)

    def test_supervisor_already_present_refuses_restart(self):
        self.pids["daemon"]=202
        self.commands[202]=" ".join(self.plan["daemon"])
        with self.assertRaises((OSError,RuntimeError,ValueError)):
            self.call()
        self.assertFalse(self.calls)

    def test_shell_failure_keeps_both_pending_recovery_intents(self):
        self.fail=True
        old,pending=self.fx.whole.read(),self.fx.ipfw.pending()
        with self.assertRaises((OSError,RuntimeError,ValueError)):
            self.call()
        self.assertEqual(old,self.fx.whole.read())
        self.assertEqual(pending,self.fx.ipfw.pending())

    def test_successful_shell_without_supervisor_is_not_success(self):
        self.no_start=True
        with self.assertRaises((OSError,RuntimeError,ValueError)):
            self.call()
        self.assertEqual("mutating",self.fx.whole.read()["phase"])

    def test_foreign_kernel_monitor_argv_or_daemon_binary_poststart(self):
        self.argv[203]=b"/bin/sh\0/tmp/foreign\0"
        with self.assertRaises((OSError,RuntimeError,ValueError)):
            self.call()
        self.assertIsNotNone(self.fx.ipfw.pending())

    def test_new_shell_action_never_starts_or_stops_engine(self):
        sh=(BACKEND/"voice_native_process_lifecycle.sh").read_text()
        segment=sh.split("    start-candidate-supervisor)")[1].split("        ;;")[0]
        self.assertIn("supervisor_start",segment)
        self.assertNotIn("launcher_start_once",segment)
        self.assertNotIn("launcher_stop",segment)


if __name__=="__main__":
    unittest.main(verbosity=2)
