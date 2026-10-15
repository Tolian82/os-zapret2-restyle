#!/usr/bin/env python3
"""Forward Voice real candidate-engine-only launcher, safe native kernel witness."""
from __future__ import annotations

import fcntl
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))
from voice_native_candidate_engine_start import start_forward_candidate_engine
from voice_native_kernel_argv import FreeBSDKernelArgvReader, SYSTEM_PATHS
from voice_native_live_preflight import _current_engine_args
from voice_native_recovery_quiescence import PIDFILES
from voice_native_forward_runtime import _read_redo


def source(path,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/"scripts"/path)
    assert spec and spec.loader
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


step72=source("test-voice-native-forward-stop.py","forward_candidate_oldstop_fixture")
processes=source("test-voice-native-process-probe.py","forward_candidate_ps_fixture")


class CandidateEngineStartTests(unittest.TestCase):
    def setUp(self):
        self.previous=step72.NativeForwardStopTests()
        self.previous.setUp()
        self.addCleanup(self.previous.doCleanups)
        self.previous.stop_after=True
        self.previous.call()
        self.fx=self.previous.fx
        self.probe=self.previous.probe
        self.reader=processes.FakePs({})
        self.probe.reader=self.reader
        self.engine_pid=None
        self.probe._read_pid=lambda path:self.engine_pid if (
            path==self.probe.pidfiles["engine"]
        ) else None
        self.expected=_current_engine_args(self.fx.root/"runtime")[0]
        self.pids={201}
        self.kernel_argv=("\0".join(self.expected)+"\0").encode("ascii")
        self.kernel_path=(SYSTEM_PATHS["engine"]+"\0").encode("ascii")
        self.kernel=FreeBSDKernelArgvReader(
            raw_argv_reader=lambda pid:self.kernel_argv if pid in self.pids else b"",
            raw_path_reader=lambda pid:self.kernel_path if pid in self.pids else b"",
        )
        self.script=self.fx.root/"native-process-actuator.sh"
        self.script.write_text("#!/bin/sh\nexit 69\n")
        self.script.chmod(0o600)
        self.calls=[]
        self.runner_failed=False
        self.dont_start=False
        self.foreign_supervisor=False

    def runner(self,argv,**kwargs):
        self.calls.append((argv,kwargs))
        self.assertEqual(argv,["/bin/sh",str(self.script),"start-candidate-engine"])
        self.assertEqual(kwargs["pass_fds"],(9,))
        self.assertNotIn("shell",kwargs)
        self.assertFalse(kwargs["check"])
        self.assertEqual(kwargs["timeout"],45)
        with (self.fx.root/"config.xml").open("rb+") as other:
            with self.assertRaises(BlockingIOError):
                fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if not self.runner_failed and not self.dont_start:
            self.engine_pid=201
            self.reader.commands={
                201:" ".join(self.expected),
            }
            if self.foreign_supervisor:
                self.reader.commands[202]=processes.COMMANDS[102]
        return subprocess.CompletedProcess(
            argv,1 if self.runner_failed else 0,
            stdout="",stderr="failure" if self.runner_failed else "",
        )

    def call(self,*,lock=True):
        config=self.fx.root/"config.xml"
        fd=os.open(config,os.O_RDWR)
        try:
            if lock:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return start_forward_candidate_engine(
                journal=self.fx.whole,ledger=self.fx.ipfw,
                previous_backup=self.fx.backup,
                active_runtime=self.fx.root/"runtime",
                staged_config=self.fx.stage_config,
                candidate_runtime=self.fx.candidate,
                config_path=config,
                probe=self.probe,kernel_reader=self.kernel,
                read_ipfw_adapter=self.previous.parent.adapter,
                config_fd=fd,config_owner=(os.geteuid(),os.getegid()),
                require_lifecycle_owner=lambda:None,runner=self.runner,
                actuator=self.script,
            )
        finally:
            os.close(fd)

    def test_native_one_engine_launch_after_previous_stop_and_runtime_install(self):
        self.assertEqual("mutating",self.fx.whole.read()["phase"])
        report=self.call()
        self.assertEqual(
            "candidate-engine-kernel-verified-supervisor-not-started",report["state"],
        )
        self.assertEqual(201,report["engine_pid"])
        self.assertIs(report["voice_on"],False)
        self.assertIs(report["supervisor_started"],False)
        self.assertIs(report["can_commit"],False)
        self.assertEqual(1,len(self.calls))
        self.assertEqual("mutating",self.fx.whole.read()["phase"])
        self.assertTrue(_read_redo(self.fx.whole.directory))
        self.assertIsNone(self.fx.ipfw.pending())
        self.assertEqual("engine-only",self.probe.observe_candidate_engine_only()["state"])

    def test_original_config_flock_required_before_process_start(self):
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.call(lock=False)
        self.assertFalse(self.calls)

    def test_forward_redo_missing_or_changed_denies_start(self):
        marker=self.fx.whole.directory/"forward-runtime-redo.json"
        marker.unlink()
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.call()
        self.assertFalse(self.calls)

    def test_candidate_arguments_or_active_tree_mismatch_denies_start(self):
        (self.fx.root/"runtime"/"dvtws.args").write_text("--port=555\n")
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.call()
        self.assertFalse(self.calls)

    def test_kernel_ipfw_changes_before_start_denied(self):
        self.previous.parent.raw.unexpected=True
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.call()
        self.assertFalse(self.calls)

    def test_unowned_existing_candidate_process_denies_double_start(self):
        self.engine_pid=201
        self.reader.commands={201:" ".join(self.expected)}
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.call()
        self.assertFalse(self.calls)

    def test_supervisor_or_orphan_process_denied_before_start(self):
        self.reader.commands={202:processes.COMMANDS[102]}
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.call()
        self.assertFalse(self.calls)
        self.reader.commands={201:" ".join(self.expected)}
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.call()
        self.assertFalse(self.calls)

    def test_launcher_failure_leaves_mutating_journal_and_old_runtime(self):
        self.runner_failed=True
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.call()
        self.assertEqual("mutating",self.fx.whole.read()["phase"])
        self.assertEqual(1,len(self.calls))

    def test_successful_launcher_without_engine_refuses_completion(self):
        self.dont_start=True
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.call()
        self.assertEqual("mutating",self.fx.whole.read()["phase"])

    def test_foreign_kernel_argv_denied_after_process_start(self):
        self.kernel_argv=b"/usr/local/etc/zapret2/binaries/my/dvtws2\0--foreign\0"
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.call()
        self.assertEqual(1,len(self.calls))
        self.assertEqual("mutating",self.fx.whole.read()["phase"])

    def test_foreign_kernel_binary_denied_after_process_start(self):
        self.kernel_path=b"/usr/bin/foreign\0"
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.call()
        self.assertEqual("mutating",self.fx.whole.read()["phase"])

    def test_supervisor_cannot_start_in_engine_only_phase(self):
        self.foreign_supervisor=True
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.call()
        self.assertEqual("mutating",self.fx.whole.read()["phase"])

    def test_installed_shell_only_exposes_fixed_engine_command(self):
        shell=(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend/voice_native_process_lifecycle.sh").read_text()
        self.assertIn(
            'case "$1" in stop|stop-candidate-engine|start|'
            'start-candidate-engine) ;; *) exit 64 ;; esac',
            shell,
        )
        self.assertNotIn("start-candidate-supervisor",shell)
        solo=shell.split("    stop-candidate-engine)")[1].split("        ;;")[0]
        self.assertIn('launcher_stop "${CHILD_PIDFILE}" 5',solo)
        self.assertIn('"${SUPERVISOR_DAEMON_PIDFILE}"',solo)
        self.assertIn('"${SUPERVISOR_MONITOR_PIDFILE}"',solo)
        self.assertNotIn("supervisor_stop",solo)
        self.assertNotIn("eval ",solo)
        phase=shell.split("    start-candidate-engine)")[1].split("        ;;")[0]
        self.assertIn("launcher_start_once",phase)
        self.assertNotIn("supervisor_start",phase)
        self.assertNotIn("eval ",phase)
        self.assertNotIn("sh -c",phase)


if __name__=="__main__":
    unittest.main(verbosity=2)
