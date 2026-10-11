#!/usr/bin/env python3
"""Actual schema-4 forward MUTATING / old stop / runtime install, no router."""
from __future__ import annotations

import copy
import fcntl
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))
from voice_native_forward_stop import (
    stop_previous_and_install_forward_runtime, ForwardStopError,
)
from voice_native_process_actions import FreeBSDVoiceProcessActions
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_native_kernel_argv import FreeBSDKernelArgvReader, SYSTEM_PATHS
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS, PIDFILES
from voice_native_supervisor_launch import canonical_supervisor_argv
from voice_restart_argv_attestation import expected_engine_argv
from voice_process_recovery_evidence import inspect_process_evidence
from voice_native_file_observer import observe_live_files
from voice_native_forward_runtime import _read_redo


def fixture(filename,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/"scripts"/filename)
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


forward=fixture("test-voice-native-forward-prepare.py","stop_forward_prepare_fixture")


class NativeForwardStopTests(unittest.TestCase):
    def setUp(self):
        self.parent=forward.NativeForwardPrepareTests()
        self.parent.setUp()
        self.addCleanup(self.parent.doCleanups)
        self.parent.prepare()
        self.fx=self.parent.fx
        self.backup=self.fx.backup
        self.old_config=(self.fx.root/"config.xml").read_bytes()
        self.saved=inspect_process_evidence(
            self.fx.process,self.backup,EXPECTED_SCRIPTS,
        )["observation"]
        self.state={k:copy.deepcopy(self.saved[k])
                    for k in ("engine","supervisor")}
        self.probe=FreeBSDVoiceProcessProbe(
            EXPECTED_SCRIPTS,PIDFILES,self.backup,
            ps_reader=lambda _args:"",
        )
        self.probe.probe=lambda:copy.deepcopy(self.state)
        self.pids={"engine":101,"daemon":102,"monitor":103}
        self.expected={
            "engine":expected_engine_argv(self.backup,EXPECTED_SCRIPTS["engine"]),
            **canonical_supervisor_argv(EXPECTED_SCRIPTS),
        }
        self.argbytes={role:("\0".join(self.expected[role])+"\0").encode("ascii")
                       for role in self.pids}
        self.pathbytes={role:(SYSTEM_PATHS[role]+"\0").encode("ascii")
                        for role in self.pids}
        self.kernel=FreeBSDKernelArgvReader(
            raw_argv_reader=lambda pid:self.argbytes[next(
                role for role,n in self.pids.items() if n==pid)],
            raw_path_reader=lambda pid:self.pathbytes[next(
                role for role,n in self.pids.items() if n==pid)],
        )
        self.script=self.fx.root/"mock-lifecycle.sh"
        self.script.write_text("#!/bin/sh\nexit 69\n")
        self.script.chmod(0o600)
        self.calls=[]
        self.fail_stop=False
        self.stop_after=False

    def runner(self,argv,**options):
        self.calls.append((list(argv),options))
        self.assertEqual(argv,["/bin/sh",str(self.script),"stop"])
        self.assertEqual(options["pass_fds"],(9,))
        self.assertEqual(options["check"],False)
        self.assertNotIn("shell",options)
        # Simulate the installed FreeBSD launcher stopping all managed roles.
        if self.stop_after:
            self.state["engine"]["state"]="stopped"
            self.state["supervisor"]["state"]="stopped"
            for role,row in [
                ("engine",self.state["engine"]["process"]),
                ("daemon",self.state["supervisor"]["daemon"]),
                ("monitor",self.state["supervisor"]["monitor"]),
            ]:
                row["pid"]=None
                row["start_ns"]=None
        return subprocess.CompletedProcess(
            argv,1 if self.fail_stop else 0,stdout="",stderr="failure" if self.fail_stop else "",
        )

    def call(self,*,locked=True):
        config=self.fx.root/"config.xml"
        fd=os.open(config,os.O_RDWR)
        try:
            if locked:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            owner=lambda:None
            actions=FreeBSDVoiceProcessActions(
                probe=self.probe,journal=self.fx.whole,
                previous_backup=self.backup,active_runtime=self.fx.root/"runtime",
                config_path=config,
                config_owner=(os.geteuid(),os.getegid()),
                config_fd=fd,require_lifecycle_owner=owner,
                runner=self.runner,actuator=self.script,
            )
            return stop_previous_and_install_forward_runtime(
                journal=self.fx.whole,ledger=self.fx.ipfw,
                previous_backup=self.backup,
                process_evidence=self.fx.process,security_evidence=self.fx.policy,
                active_runtime=self.fx.root/"runtime",config_path=config,
                staged_config=self.fx.stage_config,candidate_runtime=self.fx.candidate,
                probe=self.probe,actions=actions,kernel_reader=self.kernel,
                ipfw_adapter=self.parent.adapter,
                config_fd=fd,config_owner=(os.geteuid(),os.getegid()),
                require_lifecycle_owner=owner,
            )
        finally:
            os.close(fd)

    def old_is_active(self):
        return observe_live_files(
            self.fx.root/"config.xml",self.fx.root/"runtime",
            previous_backup=self.backup,
        )["runtime"]==self.fx.prior["runtime"]

    def test_full_old_stop_then_real_runtime_install_under_one_mutating_intent(self):
        self.stop_after=True
        report=self.call()
        self.assertEqual("native-forward-previous-stopped-runtime-installed",
                         report["state"])
        self.assertFalse(report["can_activate"])
        self.assertFalse(report["voice_on"])
        self.assertEqual("mutating",self.fx.whole.read()["phase"])
        self.assertEqual(1,len(self.calls))
        self.assertEqual(self.old_config,(self.fx.root/"config.xml").read_bytes())
        self.assertTrue(_read_redo(self.fx.whole.directory))
        self.assertEqual(
            self.fx.proof["native_argv_sha256"],
            self.fx.whole.read()["candidate"]["native_argv_sha256"],
        )
        self.assertEqual(
            observe_live_files(self.fx.stage_config,self.fx.candidate)["runtime"],
            observe_live_files(self.fx.stage_config,self.fx.root/"runtime")["runtime"],
        )
        self.assertEqual(
            self.fx.prior["runtime"],
            observe_live_files(
                self.fx.stage_config,
                (self.fx.root/("runtime")).with_name(
                    ".voice-forward-previous-"+self.fx.whole.read()["check"][:20]
                ),
            )["runtime"],
        )
        self.assertIsNone(self.fx.ipfw.pending())

    def test_without_original_config_flock_cannot_advance(self):
        self.stop_after=True
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call(locked=False)
        self.assertEqual("prepared",self.fx.whole.read()["phase"])
        self.assertTrue(self.old_is_active())
        self.assertFalse(self.calls)

    def test_unexpected_kernel_engine_argv_rejected_before_mutating(self):
        self.argbytes["engine"]=b"/foreign\0"
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.assertEqual("prepared",self.fx.whole.read()["phase"])
        self.assertFalse(self.calls)

    def test_foreign_kernel_monitor_binary_rejected_before_mutating(self):
        self.pathbytes["monitor"]=b"/bin/foreign\0"
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.assertEqual("prepared",self.fx.whole.read()["phase"])
        self.assertFalse(self.calls)

    def test_previous_pid_epoch_changed_since_sealed_process_evidence(self):
        self.state["supervisor"]["daemon"]["start_ns"]+=1
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.assertEqual("prepared",self.fx.whole.read()["phase"])
        self.assertFalse(self.calls)

    def test_runtime_drift_rejected_before_any_stop(self):
        (self.fx.root/"runtime"/"dvtws.args").write_text("--port=555\n")
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.assertEqual("prepared",self.fx.whole.read()["phase"])
        self.assertFalse(self.calls)

    def test_kernel_ipfw_drift_rejected_before_any_stop(self):
        self.parent.raw.unexpected=True
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.assertEqual("prepared",self.fx.whole.read()["phase"])
        self.assertFalse(self.calls)

    def test_epoch_swap_after_mutating_mark_refuses_native_stop(self):
        # Preflight verified original PID/start; a process replacement AFTER
        # mark_mutating but BEFORE actuator must not be killed by pathname.
        original=self.fx.whole.mark_mutating
        def swap():
            original()
            self.state["engine"]["process"]["start_ns"]+=1000000000
        with patch.object(self.fx.whole,"mark_mutating",side_effect=swap):
            with self.assertRaises((RuntimeError,ValueError,OSError)):
                self.call()
        self.assertEqual(self.calls,[])
        self.assertEqual("mutating",self.fx.whole.read()["phase"])
        self.assertTrue(self.old_is_active())

    def test_binary_swap_after_mutating_mark_refuses_native_stop(self):
        # Kernel image can change after upper attestation while pidfile and
        # ps snapshots still look identical; the pinned actuator re-reads it.
        original=self.fx.whole.mark_mutating
        def swap():
            original()
            self.pathbytes["daemon"]=b"/bin/foreign\0"
        with patch.object(self.fx.whole,"mark_mutating",side_effect=swap):
            with self.assertRaises((RuntimeError,ValueError,OSError)):
                self.call()
        self.assertEqual(self.calls,[])
        self.assertEqual("mutating",self.fx.whole.read()["phase"])
        self.assertTrue(self.old_is_active())

    def test_fail_stop_after_mutating_remains_blocked_for_recovery(self):
        self.fail_stop=True
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.assertEqual("mutating",self.fx.whole.read()["phase"])
        self.assertTrue(self.old_is_active())
        self.assertIsNone(_read_redo(self.fx.whole.directory))
        self.assertEqual(1,len(self.calls))

    def test_stopped_roles_must_really_be_absent_after_actuator(self):
        self.stop_after=False
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.assertEqual("mutating",self.fx.whole.read()["phase"])
        self.assertTrue(self.old_is_active())
        self.assertIsNone(_read_redo(self.fx.whole.directory))


if __name__=="__main__":
    unittest.main(verbosity=2)
