#!/usr/bin/env python3
"""Legacy IPFW actual replay, durable per-command redo, FreeBSD adapter fake."""
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
sys.path.insert(0,str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))
import voice_native_legacy_ipfw_replay as replay
from voice_ipfw_adapter import FreeBSDIPFWAdapter
from voice_cutover_guard import check_pending


def fixture():
    spec=importlib.util.spec_from_file_location(
        "legacy_replay_wal_fixture",
        ROOT/"scripts/test-voice-native-legacy-reverse-wal.py",
    )
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


class FakeKernel:
    """Strict command emulator: catches attempts to mutate beyond old IPFW."""
    def __init__(self):
        self.table=None
        self.rules={}
        self.native=set()
        self.writes=[]
        self.crash_after=None
        self.crash_before=None

    def __call__(self,argv,**kwargs):
        assert kwargs["capture_output"] is True and kwargs["check"] is False
        assert kwargs["timeout"]==15 and argv[0]=="/sbin/ipfw"
        cmd=list(argv[1:])
        if cmd==["-q","list"]:
            body="00001 allow ip from any to any\n"
            for num,row in sorted(self.rules.items()):
                body+=f"{num:05d} "+" ".join(row)+"\n"
            body+="65535 allow ip from any to any\n"
            return subprocess.CompletedProcess(argv,0,stdout=body,stderr="")
        if len(cmd)==3 and cmd[0]=="table" and cmd[2]=="info":
            exists=(cmd[1]=="zapret2_tgvoice" and self.table is not None) or (
                cmd[1] in self.native
            )
            if exists:
                return subprocess.CompletedProcess(argv,0,stdout="table type: addr\n",stderr="")
            return subprocess.CompletedProcess(
                argv,69,stdout="",stderr=f"Table {cmd[1]} does not exist",
            )
        if len(cmd)==3 and cmd[0]=="table" and cmd[2]=="list":
            if cmd[1]=="zapret2_tgvoice" and self.table is not None:
                return subprocess.CompletedProcess(
                    argv,0,stdout="".join(f"{a if '/' in a else a+'/32'} 0\n"
                                          for a in sorted(self.table)),stderr=""
                )
            return subprocess.CompletedProcess(argv,0,stdout="",stderr="")
        self.writes.append(cmd)
        count=len(self.writes)
        if count==self.crash_before:
            raise OSError("simulated process crash before ipfw syscall")
        if cmd==["-q","table","zapret2_tgvoice","create","type","addr"]:
            if self.table is not None:
                raise AssertionError("duplicate table creation")
            self.table=set()
        elif cmd[:4]==["-q","table","zapret2_tgvoice","add"] and len(cmd)==5:
            if self.table is None or cmd[4] in self.table:
                raise AssertionError("unexpected/replayed duplicate IPFW address")
            self.table.add(cmd[4])
        elif cmd[:2]==["-qf","add"] and len(cmd) in (17,18):
            number=int(cmd[2])
            if number in self.rules or not 19000<=number<=19010:
                raise AssertionError("duplicate/foreign rule modification")
            self.rules[number]=cmd[3:]
        else:
            raise AssertionError("foreign IPFW mutation "+repr(cmd))
        if count==self.crash_after:
            raise OSError("simulated power cut after kernel accepted command")
        return subprocess.CompletedProcess(argv,0,stdout="",stderr="")


class LegacyReplayTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture().CleanKernelRecoveryWALTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.call()
        self.kernel=FakeKernel()
        self.readonly=FreeBSDIPFWAdapter(19000,19010,runner=self.kernel)
        self.writer=FreeBSDIPFWAdapter(19000,19010,allow_mutations=True,
                                      runner=self.kernel)
        self.root=self.fixture.root
        self.live=self.fixture.live

    def call(self,*,lock=True):
        fd=os.open(self.live.config,os.O_RDWR)
        try:
            if lock:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return replay.replay_legacy_ipfw(
                root=self.root,config_path=self.live.config,config_fd=fd,
                config_owner=(os.geteuid(),os.getegid()),
                ledger_root=self.live.ledger,legacy_marker=self.fixture.marker,
                active_runtime=self.live.runtime,process_probe=self.live.probe,
                readonly_ipfw=self.readonly,mutating_ipfw=self.writer,
                require_lifecycle_owner=lambda:self.live.lock_calls.append("FD9"),
            )
        finally:
            os.close(fd)

    def test_every_old_ipfw_write_has_durable_start_done(self):
        result=self.call()
        self.assertEqual("legacy-ipfw-replayed-other-four-domains-not-restored",
                         result["state"])
        self.assertEqual(3,result["rules"])
        self.assertEqual(2,result["entries"])
        self.assertFalse(result["safe_to_enable_voice"])
        self.assertFalse(result["whole_rollback_complete"])
        self.assertEqual([19000,19001,19002],sorted(self.kernel.rules))
        self.assertEqual({"91.108.13.10","91.108.0.0/16"},self.kernel.table)
        journal=self.root/replay.REPLAY_NAME
        for n in range(len(self.kernel.writes)):
            self.assertTrue((journal/f"start-{n:04d}.txt").is_file())
            self.assertTrue((journal/f"done-{n:04d}.txt").is_file())
        before=list(self.kernel.writes)
        self.assertEqual(result,self.call())
        self.assertEqual(before,self.kernel.writes)
        self.assertEqual("orphan-native-voice-evidence",
                         check_pending(self.root,self.live.ledger)["reason"])

    def test_power_cut_after_kernel_mutation_recovers_without_duplicate(self):
        self.kernel.crash_after=4  # ipfw rule created, done marker not written
        with self.assertRaises(OSError):
            self.call()
        self.assertTrue((self.root/replay.REPLAY_NAME/"start-0003.txt").exists())
        self.assertFalse((self.root/replay.REPLAY_NAME/"done-0003.txt").exists())
        writes=len(self.kernel.writes)
        self.kernel.crash_after=None
        result=self.call()
        self.assertEqual("legacy-ipfw-replayed-other-four-domains-not-restored",
                         result["state"])
        self.assertEqual(6,len(self.kernel.writes))
        self.assertEqual(writes+2,len(self.kernel.writes))  # no replay of #4

    def test_power_cut_before_kernel_mutation_runs_same_step_once(self):
        self.kernel.crash_before=2
        with self.assertRaises(OSError):
            self.call()
        self.assertEqual(set(),self.kernel.table)
        self.assertFalse((self.root/replay.REPLAY_NAME/"done-0001.txt").exists())
        self.kernel.crash_before=None
        self.call()
        self.assertEqual(7,len(self.kernel.writes)) # failed step attempt + 6 successes

    def test_foreign_rule_or_native_table_blocks_restart(self):
        self.kernel.crash_after=2
        with self.assertRaises(OSError):
            self.call()
        self.kernel.crash_after=None
        self.kernel.rules[19007]=["allow","ip","from","any","to","any"]
        count=len(self.kernel.writes)
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.assertEqual(count,len(self.kernel.writes))
        self.kernel.rules.pop(19007)
        self.kernel.native.add("zapret2_voice_telegram_stage")
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()

    def test_flock_marker_and_pending_owner_failure(self):
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call(lock=False)
        self.assertFalse((self.root/replay.REPLAY_NAME).exists())
        self.fixture.marker.write_bytes(b"")
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.fixture.marker.unlink()
        self.live.ledger.mkdir(mode=0o700)
        (self.live.ledger/"alien").write_text("untrusted")
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.assertFalse((self.root/replay.REPLAY_NAME).exists())

    def test_crashed_replay_intent_is_never_silently_recreated(self):
        old=replay._write_once
        count=[0]
        def crash(path,data):
            count[0]+=1
            if count[0]==2:
                raise OSError("crash before replay intent seal")
            return old(path,data)
        with patch.object(replay,"_write_once",side_effect=crash):
            with self.assertRaises(OSError):
                self.call()
        self.assertFalse((self.root/replay.REPLAY_NAME).exists())
        self.assertTrue(list(self.root.glob(".legacy-ipfw-replay-*")))
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.assertEqual([],self.kernel.writes)

    def test_tampered_step_evidence_blocks_without_kernel_change(self):
        self.kernel.crash_after=1
        with self.assertRaises(OSError):
            self.call()
        checkpoint=self.root/replay.REPLAY_NAME/"start-0000.txt"
        checkpoint.write_text("forged\n")
        self.kernel.crash_after=None
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.call()
        self.assertEqual(1,len(self.kernel.writes))

    def test_never_exposed_to_service_gui_or_boot(self):
        service=(ROOT/"src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
        self.assertNotIn("legacy-ipfw-replay",service)
        self.assertNotIn("voice_native_legacy_ipfw_replay.py",service)


if __name__=="__main__":
    unittest.main(verbosity=2)
