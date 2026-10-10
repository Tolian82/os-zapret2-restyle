#!/usr/bin/env python3
"""Read-only native Voice recovery inspection with real Config flock/IPFW fixtures."""
from __future__ import annotations

import fcntl
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
BACKEND=ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0,str(BACKEND))

import voice_native_recovery_quiescence as gate
import voice_cutover_backup as backup
import voice_cutover_journal as journal
import voice_firewall_ledger as ledger
from voice_ipfw_adapter import FreeBSDIPFWAdapter
from voice_native_process_probe import FreeBSDVoiceProcessProbe

def load_test(filename, module):
    spec=importlib.util.spec_from_file_location(module,ROOT/"scripts"/filename)
    if spec is None or spec.loader is None:
        raise RuntimeError("missing native fixture")
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

process_fixture=load_test("test-voice-native-process-probe.py","native_voice_process_fixture")
ipfw_fixture=load_test("test-voice-native-ipfw-ownership.py","native_voice_ipfw_fixture")
EMPTY=ipfw_fixture.OLD


class RecoveryQuiescenceTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix="voice-quiescent-")
        self.addCleanup(tmp.cleanup)
        root=Path(tmp.name)
        self.config=root/"config.xml"
        self.config.write_bytes(b"<opnsense>previous</opnsense>\n")
        self.config.chmod(0o640)
        self.runtime=root/"runtime-v2"
        self.runtime.mkdir()
        (self.runtime/"dvtws.args").write_bytes(b"--port=989\n")
        home=root/"private"
        home.mkdir(mode=0o700)
        self.backup=home/"previous"
        backup.capture_previous(self.config,self.runtime,self.backup)
        self.old_file=backup.bound_resource_fingerprints(self.backup)
        self.whole_dir=home/"whole"
        self.whole_dir.mkdir(mode=0o700)
        self.journal=journal.VoiceCutoverJournal(self.whole_dir)
        self.ledger_dir=home/"ipfw"
        self.ledger_dir.mkdir(mode=0o700)
        self.store=ledger.VoiceOwnershipStore(self.ledger_dir)
        self.store.seed(EMPTY)
        self.previous={**self.old_file,
                       "firewall":ledger.fingerprint(ledger.canonical_manifest(EMPTY)),
                       "engine":"d"*64,"supervisor":"e"*64}
        self.proof={"saved_xml_sha256":hashlib.sha256(b"<candidate/>").hexdigest(),
                    "merged_sha256":"a"*64,"native_argv_sha256":"b"*64}
        self.journal.begin_bound(self.previous,self.proof,EMPTY)
        self.journal.mark_mutating()
        self.fake=ipfw_fixture.KernelSimulator()
        self.adapter=FreeBSDIPFWAdapter(19000,19010,runner=self.fake)
        self.ps=process_fixture.FakePs({})
        self.real_pidfiles={role:str(root/f"{role}.pid")
                            for role in gate.EXPECTED_SCRIPTS}
        self.probe=FreeBSDVoiceProcessProbe(
            gate.EXPECTED_SCRIPTS,gate.PIDFILES,self.backup,ps_reader=self.ps)
        # Only Linux test fixtures use local pidfiles. The production gate
        # requires the precise /var/run paths hardcoded in zapret_service.sh.
        self.probe.pidfiles=self.real_pidfiles

    def check(self, *, lifecycle=None):
        with patch.object(gate,"PIDFILES",self.real_pidfiles):
            fd=os.open(self.config,os.O_RDWR)
            try:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                return gate.inspect_quiescence(
                    self.journal,self.store,self.backup,self.probe,self.adapter,
                    config_path=self.config,locked_config_fd=fd,
                    config_owner=(os.geteuid(),os.getegid()),
                    require_lifecycle_owner=lifecycle or (lambda:None),
                )
            finally:
                os.close(fd)

    def test_stopped_previous_ipfw_is_verified_twice_without_mutation(self):
        result=self.check()
        self.assertEqual("stopped-and-previous-ipfw",result["state"])
        self.assertEqual("mutating",result["whole_phase"])
        self.assertEqual("previous",result["owned_ipfw"])
        self.assertIs(result["can_enable_voice"],False)
        self.assertIs(result["can_complete_rollback"],False)
        self.assertEqual(self.config.read_bytes(),b"<opnsense>previous</opnsense>\n")
        self.assertEqual(self.journal.read()["phase"],"mutating")
        self.assertTrue(all(call[0]=="/sbin/ipfw" for call in self.fake.calls))
        self.assertTrue(all(call[1:] == ("-q","list") or
                            (len(call)==4 and call[1]=="table" and
                             call[-1] in ("info","list"))
                            for call in self.fake.calls))
        self.assertEqual(22,len(self.fake.calls))
        self.assertEqual(self.store.owned(),EMPTY)

    def test_live_engine_without_pidfile_is_not_quiescent(self):
        self.ps.commands={101:process_fixture.COMMANDS[101]}
        with self.assertRaises(Exception):
            self.check()
        self.assertEqual(self.journal.read()["phase"],"mutating")

    def test_partial_supervisor_with_pidfile_rejected(self):
        daemon_pid=Path(self.probe.pidfiles["daemon"])
        daemon_pid.write_text("102\n")
        daemon_pid.chmod(0o600)
        self.ps.commands={102:process_fixture.COMMANDS[102]}
        with self.assertRaises(Exception):
            self.check()

    def test_busy_or_unlocked_config_cannot_pass_gate(self):
        with patch.object(gate,"PIDFILES",self.real_pidfiles):
            fd=os.open(self.config,os.O_RDWR)
            try:
                with self.assertRaisesRegex(gate.NativeQuiescenceError,"flock"):
                    gate.inspect_quiescence(
                        self.journal,self.store,self.backup,self.probe,self.adapter,
                        config_path=self.config,locked_config_fd=fd,
                        config_owner=(os.geteuid(),os.getegid()),
                        require_lifecycle_owner=lambda:None,
                    )
            finally:
                os.close(fd)

    def test_foreign_ipfw_rule_and_staging_table_refused(self):
        for case in ("rule","stage","address"):
            with self.subTest(case=case):
                self.fake.rules={}
                self.fake.tables={}
                if case=="rule":
                    self.fake.rules[19000]=ipfw_fixture.TCP
                elif case=="stage":
                    self.fake.tables["zapret2_voice_telegram_stage"]=["91.108.13.10"]
                else:
                    self.fake.tables["zapret2_voice_telegram"]=["91.108.13.10"]
                with self.assertRaises(Exception):
                    self.check()

    def test_unbound_pending_ipfw_intent_is_refused(self):
        desired={**EMPTY,"tables":{"zapret2_voice_telegram":["91.108.0.0/16"]}}
        self.store.begin(EMPTY,desired)
        self.store.mark_mutating()
        with self.assertRaisesRegex(
            gate.NativeQuiescenceError,"IPFW pending transition"
        ):
            self.check()

    def test_committed_or_missing_whole_cutover_denied(self):
        self.journal.commit()
        with self.assertRaisesRegex(gate.NativeQuiescenceError,"mutating"):
            self.check()

    def test_lost_lifecycle_lease_on_second_read_fails_closed(self):
        ticks=[0]
        def lease():
            ticks[0]+=1
            if ticks[0]>=2:
                raise gate.NativeQuiescenceError("lifecycle ownership lost")
        with self.assertRaisesRegex(gate.NativeQuiescenceError,"ownership lost"):
            self.check(lifecycle=lease)
        self.assertEqual(self.journal.read()["phase"],"mutating")

    def test_process_appears_between_two_checks_refused(self):
        normal=self.ps
        def variable_ps(argv):
            if "-A" in argv:
                variable_ps.calls+=1
                if variable_ps.calls>=2:
                    normal.commands={101:process_fixture.COMMANDS[101]}
            return normal(argv)
        variable_ps.calls=0
        self.probe.reader=variable_ps
        with self.assertRaises(Exception):
            self.check()
        self.assertEqual(self.journal.read()["phase"],"mutating")

    def test_config_owner_and_changed_snapshot_refused(self):
        with patch.object(gate,"PIDFILES",self.real_pidfiles):
            fd=os.open(self.config,os.O_RDWR)
            try:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with self.assertRaises(Exception):
                    gate.inspect_quiescence(
                        self.journal,self.store,self.backup,self.probe,self.adapter,
                        config_path=self.config,locked_config_fd=fd,
                        config_owner=(os.geteuid()+10000,os.getegid()),
                        require_lifecycle_owner=lambda:None,
                    )
            finally:
                os.close(fd)
        (self.backup/"runtime/dvtws.args").write_text("tampered")
        with self.assertRaises(Exception):
            self.check()


if __name__=="__main__":
    unittest.main(verbosity=2)
