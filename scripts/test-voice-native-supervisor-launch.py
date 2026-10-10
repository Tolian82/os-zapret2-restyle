#!/usr/bin/env python3
"""Deterministic trusted supervisor argv template and installed-shell parity."""
from __future__ import annotations

import copy
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parent.parent
BACKEND=ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0,str(BACKEND))
from voice_native_supervisor_launch import (
    PATHS, ENGINE, DAEMON, LOOP, SERVICE, ENGINE_PID, DAEMON_PID,
    MONITOR_PID, LOG, SupervisorLaunchError,
    canonical_supervisor_argv, verified_supervisor_argv, supervisor_plan_sha256,
)


class SupervisorPlanTests(unittest.TestCase):
    def test_exact_native_one_supervisor_command(self):
        plan=canonical_supervisor_argv(PATHS)
        self.assertEqual([
            DAEMON,"-P",DAEMON_PID,"-p",MONITOR_PID,
            "-o",LOG,"-f",LOOP,ENGINE_PID,SERVICE,ENGINE
        ],plan["daemon"])
        self.assertEqual([
            "/bin/sh",LOOP,ENGINE_PID,SERVICE,ENGINE
        ],plan["monitor"])
        self.assertEqual(plan,verified_supervisor_argv(PATHS,plan))
        self.assertEqual(supervisor_plan_sha256(PATHS),
                         supervisor_plan_sha256(dict(PATHS)))
        self.assertEqual(64,len(supervisor_plan_sha256(PATHS)))

    def test_no_caller_process_path_or_command_override(self):
        good=canonical_supervisor_argv(PATHS)
        for role in PATHS:
            with self.subTest(role=role):
                foreign=dict(PATHS)
                foreign[role]="/tmp/foreign"
                with self.assertRaises(SupervisorLaunchError):
                    canonical_supervisor_argv(foreign)
        for case in ("daemon-extra","monitor-arg","foreign-shell","missing","extra"):
            with self.subTest(case=case):
                foreign=copy.deepcopy(good)
                if case=="daemon-extra":
                    foreign["daemon"].append("--trampoline")
                elif case=="monitor-arg":
                    foreign["monitor"][3]="/tmp/foreign_service"
                elif case=="foreign-shell":
                    foreign["monitor"][0]="/bin/csh"
                elif case=="missing":
                    del foreign["daemon"]
                else:
                    foreign["untrusted"]=["/bin/sh"]
                with self.assertRaises(SupervisorLaunchError):
                    verified_supervisor_argv(PATHS,foreign)

    def test_template_matches_installed_shell_and_supervisor_argv_order(self):
        wrapper=(BACKEND/"voice_native_process_lifecycle.sh").read_text()
        supervisor=(BACKEND/"supervisor.sh").read_text()
        for value in (
            PATHS["engine"],ENGINE_PID,DAEMON_PID,
            MONITOR_PID,LOG,"supervisor_loop.sh","zapret_service.sh"
        ):
            self.assertIn(value,wrapper)
        v=lambda name:'"'+chr(36)+'{'+name+'}"'
        for piece in ("-P "+v("_supervisor_daemon_pidfile"),
                      "-p "+v("_supervisor_monitor_pidfile"),
                      "-o "+v("_supervisor_log"),
                      "-f "+v("_supervisor_loop"),
                      v("_supervisor_child_pidfile"),
                      v("_supervisor_service_script"),
                      v("_supervisor_expected_child")):
            self.assertIn(piece,supervisor)
        proc=subprocess.run(["/bin/sh","-n",str(BACKEND/"voice_native_process_lifecycle.sh")],
                            capture_output=True,text=True,check=False)
        self.assertEqual(0,proc.returncode,proc.stderr)


if __name__=="__main__":
    unittest.main(verbosity=2)
