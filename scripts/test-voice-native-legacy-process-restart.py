#!/usr/bin/env python3
"""Re-start exact previous Telegram triad with bounded single-shot durable intent."""
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
import voice_native_legacy_process_restart as restart
from voice_cutover_backup import inspect_previous
from voice_cutover_guard import check_pending
from voice_process_recovery_evidence import _runtime_args_digest,inspect_process_evidence
from voice_freebsd_process_security import FreeBSDProcessSecurityReader
from voice_freebsd_kernel_argv import FreeBSDKernelArgvReader
from voice_native_supervisor_launch import canonical_supervisor_argv
from voice_restart_argv_attestation import expected_engine_argv
from voice_security_policy_evidence import inspect_security_policy
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS


def fixture():
    spec=importlib.util.spec_from_file_location(
        "prior_old_marker_restart_fixture",
        ROOT/"scripts/test-voice-native-legacy-marker-restore.py",
    )
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class LegacyThreeRoleRestartTests(unittest.TestCase):
    def setUp(self):
        self.before=fixture().LegacyMarkerInstallTests()
        self.before.setUp()
        self.addCleanup(self.before.doCleanups)
        self.before.call()
        self.root=self.before.root
        self.live=self.before.live
        self.probe=self.live.probe
        self.marker=self.before.target
        self.calls=0
        self.running=False
        self.partial=False
        self.original=self.root/"legacy-previous/previous"
        self.saved=inspect_previous(self.original)
        self.args_sha=_runtime_args_digest(self.saved)
        evidence=inspect_process_evidence(
            self.root/"legacy-previous/process-evidence",
            self.original,EXPECTED_SCRIPTS,
        )["observation"]
        def no_role(role):
            return {"pid":None,"start_ns":None,
                    "executable":EXPECTED_SCRIPTS[role]}
        self.stopped={
            "engine":{"state":"stopped","process":no_role("engine"),
                      "runtime_args_sha256":self.args_sha},
            "supervisor":{"state":"stopped","daemon":no_role("daemon"),
                          "monitor":no_role("monitor")},
        }
        max_old=max(
            evidence["engine"]["process"]["start_ns"],
            evidence["supervisor"]["daemon"]["start_ns"],
            evidence["supervisor"]["monitor"]["start_ns"],
        )
        def new_role(role,index):
            return {"pid":30500+index,"start_ns":max_old+1000000+index,
                    "executable":EXPECTED_SCRIPTS[role]}
        self.new={
            "engine":{"state":"running","process":new_role("engine",1),
                      "runtime_args_sha256":self.args_sha},
            "supervisor":{"state":"running","daemon":new_role("daemon",2),
                          "monitor":new_role("monitor",3)},
        }
        self.mockprobe=patch.object(
            self.probe,"probe",
            side_effect=lambda:copy.deepcopy(
                {**self.new,"supervisor":{**self.new["supervisor"],"state":"stopped"}}
                if self.partial else self.new if self.running else self.stopped
            ),
        )
        self.mockprobe.start()
        self.addCleanup(self.mockprobe.stop)
        self.policy=inspect_security_policy(
            self.root/"legacy-previous/process-security-policy",self.original,
            self.root/"legacy-previous/process-evidence",
            expected_scripts=EXPECTED_SCRIPTS,
        )
        p=self.policy["policy"]
        self.security=FreeBSDProcessSecurityReader(
            EXPECTED_SCRIPTS,p["images"],p["credentials"],self.probe,
        )
        self.argv=FreeBSDKernelArgvReader(EXPECTED_SCRIPTS,self.probe)
        args={"engine":expected_engine_argv(
            self.original,EXPECTED_SCRIPTS["engine"]
        ),**canonical_supervisor_argv(EXPECTED_SCRIPTS)}
        def security_report():
            roles={}
            for i,role in enumerate(("engine","daemon","monitor"),1):
                row=self.new["engine"]["process"] if role=="engine" else self.new["supervisor"][role]
                roles[role]={"pid":row["pid"],"start_ns":row["start_ns"],
                             "image":p["images"][role],
                             "credentials":p["credentials"][role]}
            return {"state":"review-required",
                    "reason":"matching-process-path-and-ids-only",
                    "roles":roles,"can_activate":False,
                    "can_recover_automatically":False,
                    "safe_to_mutate":False,"startup_ready":False,"media_pass":False}
        def argv_report():
            rows={}
            for role in ("engine","daemon","monitor"):
                row=self.new["engine"]["process"] if role=="engine" else self.new["supervisor"][role]
                rows[role]={**row,"argv":args[role]}
            return {"engine":rows["engine"],"supervisor":{
                "daemon":rows["daemon"],"monitor":rows["monitor"]
            }}
        self.mocksecurity=patch.object(self.security,"inspect_twice",
                                       side_effect=security_report)
        self.mockargv=patch.object(self.argv,"observe_argv",
                                   side_effect=argv_report)
        self.mocksecurity.start()
        self.mockargv.start()
        self.addCleanup(self.mocksecurity.stop)
        self.addCleanup(self.mockargv.stop)
        self.actuator=self.root.parent/"voice-lifecycle-test.sh"
        self.actuator.write_text("#!/bin/sh\nexit 69\n")
        self.actuator.chmod(0o700)

    def runner(self,argv,**kwargs):
        self.calls+=1
        self.assertEqual(["/bin/sh",str(self.actuator),"start"],argv)
        self.assertEqual((9,),kwargs["pass_fds"])
        self.assertFalse(kwargs["check"])
        self.running=True
        return subprocess.CompletedProcess(argv,0,stdout="",stderr="")

    def call(self,*,locked=True,runner=None):
        fd=os.open(self.live.config,os.O_RDWR)
        try:
            if locked:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return restart.restart_legacy_processes(
                root=self.root,config_path=self.live.config,config_fd=fd,
                config_owner=(os.geteuid(),os.getegid()),
                active_runtime=self.live.runtime,marker_path=self.marker,
                ledger_root=self.live.ledger,process_probe=self.probe,
                readonly_ipfw=self.before.before.old.old.previous.readonly,
                security_reader=self.security,argv_reader=self.argv,
                require_lifecycle_owner=lambda:self.live.lock_calls.append("FD9"),
                runner=self.runner if runner is None else runner,
                actuator=self.actuator,
            )
        finally:
            os.close(fd)

    def test_single_restart_seals_kernel_argv_and_security_without_voice_on(self):
        result=self.call()
        self.assertEqual("legacy-three-roles-restarted-needs-whole-owner-acceptance",
                         result["state"])
        self.assertEqual(1,self.calls)
        for field in ("safe_to_enable_voice","whole_rollback_complete",
                      "public_voice_apply","boot_recovery_validated","media_pass"):
            self.assertFalse(result[field])
        self.assertEqual(result,self.call())
        self.assertEqual(1,self.calls)
        self.assertTrue((self.root/restart.PROCESS_NAME/"verified.sha256").is_file())
        self.assertEqual("orphan-native-voice-evidence",
                         check_pending(self.root,self.live.ledger)["reason"])

    def test_crash_after_successful_actuator_is_not_double_started(self):
        def powercut(argv,**kwargs):
            result=self.runner(argv,**kwargs)
            raise OSError("power cut after process launcher returned")
        with self.assertRaises(OSError):
            self.call(runner=powercut)
        self.assertEqual(1,self.calls)
        self.assertTrue((self.root/restart.PROCESS_NAME/"intent.sha256").exists())
        self.assertFalse((self.root/restart.PROCESS_NAME/"verified.json").exists())
        self.assertEqual("legacy-three-roles-restarted-needs-whole-owner-acceptance",
                         self.call()["state"])
        self.assertEqual(1,self.calls)

    def test_partial_running_roles_block_retry_with_no_second_launch(self):
        def partial(argv,**kwargs):
            out=self.runner(argv,**kwargs)
            self.partial=True
            raise OSError("crash with only engine process")
        with self.assertRaises(OSError):
            self.call(runner=partial)
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.assertEqual(1,self.calls)

    def test_crash_before_actuator_does_not_automatically_retry_start(self):
        def aborted(argv,**kwargs):
            self.calls+=1
            raise OSError("launcher not reached after intent")
        with self.assertRaises(OSError):
            self.call(runner=aborted)
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.assertEqual(1,self.calls)

    def test_wrong_original_flock_refused_before_durable_intent(self):
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call(locked=False)
        self.assertFalse((self.root/restart.PROCESS_NAME).exists())
        self.assertEqual(0,self.calls)

    def test_tampered_marker_or_foreign_ipfw_refused_before_start(self):
        self.before.kernel.rules[19009]=["allow","ip","from","any","to","any"]
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.before.kernel.rules.pop(19009)
        self.marker.write_bytes(b"tampered")
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.assertEqual(0,self.calls)

    def test_tampered_security_observation_blocks_receipt_and_second_start(self):
        def forged(argv,**kwargs):
            self.runner(argv,**kwargs)
            self.security.credentials["engine"]["euid"]=99999
            return subprocess.CompletedProcess(argv,0,stdout="",stderr="")
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call(runner=forged)
        self.assertFalse((self.root/restart.PROCESS_NAME/"verified.json").exists())
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.assertEqual(1,self.calls)

    def test_unknown_partial_intent_remains_blocked(self):
        original=restart._write_once
        count=[0]
        def cut(path,raw):
            count[0]+=1
            if count[0]==2:raise OSError("power loss before intent checksum")
            return original(path,raw)
        with patch.object(restart,"_write_once",side_effect=cut):
            with self.assertRaises(OSError):
                self.call()
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.assertEqual(0,self.calls)

    def test_actuator_requires_secure_regular_script(self):
        self.actuator.chmod(0o777)
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.assertEqual(0,self.calls)

    def test_no_service_gui_or_boot_wiring(self):
        service=(ROOT/"src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
        self.assertNotIn("voice_native_legacy_process_restart.py",service)


if __name__=="__main__":
    unittest.main(verbosity=2)
