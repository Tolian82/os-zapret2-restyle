#!/usr/bin/env python3
"""Read-only live OPNsense FreeBSD Voice process baseline before any cutover."""
from __future__ import annotations

import fcntl
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))
from voice_native_live_preflight import (
    LivePreflightError,inspect_live_preflight,_current_engine_args,
)
from voice_native_kernel_argv import FreeBSDKernelArgvReader,SYSTEM_PATHS
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS,PIDFILES
from voice_native_supervisor_launch import canonical_supervisor_argv
from voice_restart_argv_attestation import FIXED_TRAILER
from voice_ipfw_adapter import FreeBSDIPFWAdapter


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/"scripts"/path)
    assert spec and spec.loader
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


fixtures=load("test-voice-native-process-probe.py","precutover_freebsd_probe_fixture")


class FakeReadOnlyIPFW:
    def __init__(self):
        self.rules=(
            "00001 allow ip from any to any\n"
            "19005 divert 989 tcp from any to any 443 out not diverted not sockarg xmit vtnet1\n"
            "19006 divert 989 udp from any to any 596 out not diverted not sockarg xmit vtnet1\n"
            "65535 allow ip from any to any\n"
        )
        self.active=set()
        self.calls=[]
        self.list_count=0
        self.fail=False

    def __call__(self,argv,**kwargs):
        self.calls.append(tuple(argv))
        assert kwargs["check"] is False
        assert kwargs["capture_output"] is True
        assert kwargs["timeout"]==15
        if self.fail:
            return subprocess.CompletedProcess(argv,1,stdout="",stderr="Permission denied")
        args=tuple(argv[1:])
        if args==("-q","list"):
            self.list_count+=1
            return subprocess.CompletedProcess(argv,0,stdout=self.rules,stderr="")
        if len(args)==3 and args[0]=="table" and args[-1]=="info":
            if args[1] in self.active:
                return subprocess.CompletedProcess(argv,0,stdout="table type: addr\n",stderr="")
            return subprocess.CompletedProcess(
                argv,69,stdout="",stderr=f"Table {args[1]} does not exist",
            )
        if len(args)==3 and args[0]=="table" and args[-1]=="list":
            return subprocess.CompletedProcess(argv,0,stdout="",stderr="")
        raise AssertionError("unexpected, possibly mutating IPFW command: "+repr(args))


class LivePreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="voice-live-first-")
        self.addCleanup(self.temp.cleanup)
        base=Path(self.temp.name)
        t=fixtures.NativeProcessProbeTests()
        self.probe,_,self.runtime,self.config=t.fixture(base)
        # There is deliberately no original Voice rollback/backup.
        shutil.rmtree(self.probe.previous_backup)
        self.whole=base/"cutover-absent"
        self.ledger=base/"ipfw-absent"
        self.probe.pidfiles=dict(PIDFILES)
        self.pid={"engine":101,"daemon":102,"monitor":103}
        self.probe._read_pid=lambda path:next(
            self.pid[key] for key,v in PIDFILES.items() if v==path
        )
        self.expected={
            "engine":[EXPECTED_SCRIPTS["engine"],"--port=989",*FIXED_TRAILER],
            **canonical_supervisor_argv(EXPECTED_SCRIPTS),
        }
        self.commands={
            self.pid[role]:" ".join(self.expected[role])
            for role in self.pid
        }
        self.probe.reader=fixtures.FakePs(self.commands)
        self.argv={
            role:("\x00".join(self.expected[role])+"\x00").encode("ascii")
            for role in self.pid
        }
        self.image={
            role:(SYSTEM_PATHS[role]+"\x00").encode("ascii")
            for role in self.pid
        }
        self.kernel=FreeBSDKernelArgvReader(
            raw_argv_reader=lambda pid:next(self.argv[role] for role,val
                                            in self.pid.items() if val==pid),
            raw_path_reader=lambda pid:next(self.image[role] for role,val
                                            in self.pid.items() if val==pid),
        )
        self.lock_calls=[]
        self.fake_ipfw=FakeReadOnlyIPFW()
        self.adapter=FreeBSDIPFWAdapter(19000,19010,runner=self.fake_ipfw)

    def audit(self,lock=True):
        fd=os.open(self.config,os.O_RDWR)
        try:
            if lock:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return inspect_live_preflight(
                config_path=self.config,active_runtime=self.runtime,
                whole_root=self.whole,ledger_root=self.ledger,
                probe=self.probe,kernel_reader=self.kernel,
                ipfw_adapter=self.adapter,config_fd=fd,config_owner=(os.geteuid(),os.getegid()),
                require_lifecycle_owner=lambda:self.lock_calls.append("FD9"),
            )
        finally:
            os.close(fd)

    def test_live_pre_cutover_observation_needs_no_previous_backup(self):
        before=self.runtime.joinpath("dvtws.args").read_bytes()
        report=self.audit()
        self.assertEqual("live-legacy-process-argv-observed-not-readiness",
                         report["state"])
        self.assertEqual("matching-current-runtime",report["argv"])
        self.assertEqual("matching-fixed-launcher-images",
                         report["kernel_executable"])
        self.assertEqual("ordinary-structure-only-not-owned",report["kernel_ipfw"])
        self.assertEqual(2,report["kernel_ipfw_rule_count"])
        self.assertEqual("absent",report["kernel_ipfw_voice_tables"])
        self.assertEqual("absent",report["kernel_ipfw_legacy_table"])
        self.assertEqual(2,self.fake_ipfw.list_count)
        self.assertTrue(all(call[1] in ("-q","table") for call in self.fake_ipfw.calls))
        self.assertIs(report["safe_to_enable_voice"],False)
        self.assertIs(report["safe_to_mutate"],False)
        self.assertIs(report["safe_to_start"],False)
        self.assertIs(report["media_pass"],False)
        self.assertFalse(self.whole.exists())
        self.assertFalse(self.ledger.exists())
        self.assertEqual(before,self.runtime.joinpath("dvtws.args").read_bytes())
        self.assertEqual(3,len(report["instances"]))
        self.assertGreaterEqual(len(self.lock_calls),4)

    def test_ipfw_foreign_rule_number_or_port_and_voice_table_refused(self):
        original=self.fake_ipfw.rules
        for mutated in (
            original.replace("19005 divert","19005 allow"),
            original.replace("19005 divert 989","19005 divert 988"),
            original.replace("19005 divert 989 tcp","19005 divert 989 udp"),
            original.replace("19005 ","19999 ").replace("19006 ","19998 "),
            original.replace("vtnet1", "igc0",1),
        ):
            with self.subTest(mutated=mutated[-90:]):
                self.fake_ipfw.rules=mutated
                with self.assertRaises((OSError,ValueError,RuntimeError)):
                    self.audit()
        self.fake_ipfw.rules=original
        for table in ("zapret2_voice_telegram","zapret2_voice_custom_stage",
                      "zapret2_tgvoice","zapret2_tgvoice_stage"):
            with self.subTest(table=table):
                self.fake_ipfw.active.add(table)
                with self.assertRaises((OSError,ValueError,RuntimeError)):
                    self.audit()
                self.fake_ipfw.active.clear()
        self.fake_ipfw.fail=True
        with self.assertRaises((OSError,ValueError,RuntimeError)):
            self.audit()

    def test_ipfw_drift_between_scans_refused(self):
        original=self.fake_ipfw.__call__
        def changing(argv,**kwargs):
            if tuple(argv[1:])==("-q","list") and self.fake_ipfw.list_count>=1:
                self.fake_ipfw.rules=self.fake_ipfw.rules.replace(
                    "19006 divert 989 udp", "19006 divert 989 tcp",
                )
            return original(argv,**kwargs)
        self.adapter.runner=changing
        with self.assertRaises((OSError,ValueError,RuntimeError)):
            self.audit()

    def test_requires_original_config_flock(self):
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.audit(lock=False)
        self.assertFalse(self.whole.exists())

    def test_kernel_argv_and_executable_mismatch_are_refused(self):
        for role in self.pid:
            with self.subTest(role=role):
                original=self.argv[role]
                self.argv[role]=original[:-1]+b"--foreign\x00"
                with self.assertRaises((ValueError,OSError,RuntimeError)):
                    self.audit()
                self.argv[role]=original
                image=self.image[role]
                self.image[role]=b"/bin/untrusted\x00"
                with self.assertRaises((ValueError,OSError,RuntimeError)):
                    self.audit()
                self.image[role]=image

    def test_incomplete_kernel_argv_and_binary_output_are_refused(self):
        value=self.argv["engine"]
        self.argv["engine"]=value[:-1]
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.audit()
        self.argv["engine"]=value
        value=self.image["daemon"]
        self.image["daemon"]=b"/usr/sbin/daemon"
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.audit()
        self.image["daemon"]=value

    def test_original_runtime_args_changed_or_symlink_is_denied(self):
        file=self.runtime/"dvtws.args"
        file.write_text("--port=989 --user=nobody\n")
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.audit()
        file.unlink()
        file.symlink_to(self.config)
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.audit()

    def test_orphan_stale_journal_blocks_without_mutation(self):
        self.whole.mkdir(mode=0o700)
        (self.whole/"previous-close-intent.json").write_text("stale")
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.audit()
        self.assertTrue((self.whole/"previous-close-intent.json").exists())

    def test_partial_or_extra_processes_refused(self):
        self.probe._read_pid=lambda p:None
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.audit()
        self.probe._read_pid=lambda p:next(
            self.pid[k] for k,v in PIDFILES.items() if v==p
        )
        self.probe.reader=fixtures.FakePs({
            **self.commands,104:self.commands[101],
        })
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.audit()

    def test_process_epoch_race_refused(self):
        original=self.probe.reader
        count={"n":0}
        def update(argv):
            count["n"]+=1
            text=original(argv)
            # PID unchanged but FreeBSD lstart changes on the second ps pass:
            # the kernel argv check must not accept a recycled PID.
            if count["n"]>5 and "-p" in argv and argv[argv.index("-p")+1]=="101":
                return text.replace("20:25:17","20:25:18")
            return text
        self.probe.reader=update
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.audit()

    def test_safely_denies_foreign_writeable_root_and_changed_inode(self):
        self.runtime.chmod(0o777)
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.audit()
        self.runtime.chmod(0o755)
        old=_current_engine_args(self.runtime)
        self.assertEqual("--port=989",old[0][1])
        self.assertEqual(4,len(old))

    def test_production_entrypoint_uses_same_existing_lifecycle_lock(self):
        script=(ROOT/"src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
        self.assertIn("native_voice_live_preflight_service()",script)
        self.assertIn('native-voice-live-preflight)',script)
        self.assertIn(
            "native-voice-boot-review|native-voice-live-preflight|native-voice-lifecycle-inspect|native-voice-candidate-preflight|native-voice-ipfw-seed",
            script,
        )
        self.assertIn('service_with_lifecycle_lock "${LIFECYCLE_LOCK_TIMEOUT}"',script)


if __name__=="__main__":
    unittest.main(verbosity=2)
