#!/usr/bin/env python3
"""Five-domain rollback with REAL Config/runtime/ledger operations and fake kernel/process."""
from __future__ import annotations

import fcntl
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

import voice_cutover_five_resource_rollback as whole
import voice_native_recovery_quiescence as gate
import voice_firewall_ledger as ledger
import voice_process_recovery_evidence as evidence
from voice_ipfw_adapter import FreeBSDIPFWAdapter
from voice_native_process_probe import FreeBSDVoiceProcessProbe


def fixture(filename, name):
    spec=importlib.util.spec_from_file_location(name,ROOT/"scripts"/filename)
    assert spec and spec.loader
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

runtime_fixture=fixture("test-voice-cutover-runtime-restore.py","five_runtime_fixture")
process_fixture=fixture("test-voice-native-process-probe.py","five_process_fixture")
ipfw_fixture=fixture("test-voice-native-ipfw-ownership.py","five_ipfw_fixture")
firewall_fixture=fixture("test-voice-firewall-transaction.py","five_firewall_fixture")


class FiveDomainRecovery(unittest.TestCase):
    setUp=runtime_fixture.RuntimeRecovery.setUp
    sha=runtime_fixture.RuntimeRecovery.sha
    paths=runtime_fixture.RuntimeRecovery.paths

    def initialize(self, *, pending=False):
        self.config.write_bytes(b"<candidate/>")
        self.config.chmod(0o600)
        self.probe=FreeBSDVoiceProcessProbe(
            gate.EXPECTED_SCRIPTS,gate.PIDFILES,self.backup,
            ps_reader=process_fixture.FakePs(process_fixture.COMMANDS.copy()),
        )
        self.pidfiles={role:str(self.base/(role+".pid"))
                       for role in gate.EXPECTED_SCRIPTS}
        self.probe.pidfiles=dict(self.pidfiles)
        for index,role in enumerate(gate.EXPECTED_SCRIPTS,101):
            Path(self.pidfiles[role]).write_text(str(index)+"\n")
            Path(self.pidfiles[role]).chmod(0o600)
        self.process_evidence=self.journal_dir/"process-evidence"
        from voice_process_recovery_evidence import capture_process_evidence
        hashes=capture_process_evidence(
            self.probe,self.backup,self.process_evidence,gate.EXPECTED_SCRIPTS,
        )
        self.ledger_dir=self.base/"ipfw-ledger"
        self.ledger_dir.mkdir(mode=0o700)
        self.store=ledger.VoiceOwnershipStore(self.ledger_dir)
        self.store.seed(ipfw_fixture.OLD)
        self.previous={
            **self.previous,**hashes,
            "firewall":ledger.fingerprint(
                ledger.canonical_manifest(ipfw_fixture.OLD)
            ),
        }
        self.desired=firewall_fixture.fixture(("telegram","91.108.0.0/16"))
        self.journal.begin_bound(self.previous,self.proof,self.desired)
        self.journal.mark_mutating()
        self.kernel=ipfw_fixture.KernelSimulator()
        self.writer=firewall_fixture.FakeIPFW()
        self.kernel.rules=self.writer.rules
        self.kernel.tables=self.writer.tables
        self.reader=FreeBSDIPFWAdapter(19000,19010,runner=self.kernel)
        if pending:
            self.store.begin(ipfw_fixture.OLD,self.desired)
            self.store.mark_mutating()
        self.history=[]

    def stop(self):
        self.history.append("stop")
        self.probe.reader.commands={}
        for pidfile in self.pidfiles.values():
            Path(pidfile).unlink(missing_ok=True)

    def restart(self):
        self.history.append("restart")
        self.probe.reader.commands={
            index:process_fixture.COMMANDS[index-100]
            for index in (201,202,203)
        }
        for index,role in enumerate(gate.EXPECTED_SCRIPTS,201):
            Path(self.pidfiles[role]).write_text(str(index)+"\n")
            Path(self.pidfiles[role]).chmod(0o600)

    def recover(self, *, restart=None, stopped=None, lifecycle=None,
                locked_config_fd=None):
        with patch.object(gate,"PIDFILES",self.pidfiles):
            return whole.restore_previous_five_resources(
                journal=self.journal,ledger=self.store,
                previous_backup=self.backup,install_image=self.image,
                process_evidence=self.process_evidence,
                expected_scripts=gate.EXPECTED_SCRIPTS,
                config_path=self.config,active_runtime=self.active,
                expected_owner=(os.geteuid(),os.getegid()),
                expected_candidate_runtime_sha256=self.candidate_sha,
                candidate_proof=self.proof,process_probe=self.probe,
                read_ipfw_adapter=self.reader,write_ipfw_adapter=self.writer,
                stop_candidate=stopped or self.stop,
                start_previous=restart or self.restart,
                require_lifecycle_owner=lifecycle or (lambda:None),
                locked_config_fd=locked_config_fd,
            )

    def test_all_five_domains_restore_real_files_and_prior_kernel(self):
        self.initialize(pending=True)
        old_inode=self.config.stat().st_ino
        result=self.recover()
        self.assertEqual(result["state"],"five-previous-domains-observed")
        self.assertEqual(self.history,["stop","restart"])
        self.assertEqual(result["engine"],"running")
        self.assertEqual(result["supervisor"],"running")
        self.assertEqual(result["ipfw"],"previous")
        self.assertEqual(self.config.stat().st_ino,old_inode)
        self.assertEqual(self.config.read_bytes(),
                         (self.image/"config.xml").read_bytes())
        self.assertEqual(self.sha(self.active),self.previous["runtime"])
        self.assertIsNone(self.store.pending())
        self.assertEqual(self.store.owned(),ipfw_fixture.OLD)
        self.assertTrue((self.journal_dir/"config-restore-redo.json").exists())
        self.assertTrue((self.journal_dir/"runtime-restore-redo.json").exists())
        self.assertEqual("mutating",self.journal.read()["phase"])
        self.assertIs(result["safe_to_enable_voice"],False)
        self.assertIs(result["safe_to_clear_intent"],False)

    def test_ipfw_already_rolled_back_is_resumeable(self):
        self.initialize(pending=False)
        result=self.recover()
        self.assertEqual(result["state"],"five-previous-domains-observed")
        self.assertEqual(self.history,["stop","restart"])

    def test_config_flock_spans_stop_kernel_files_and_restart(self):
        self.initialize(pending=True)
        checks=[]
        def assert_lock():
            with self.config.open("r+b") as competing:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(competing,fcntl.LOCK_EX|fcntl.LOCK_NB)
            checks.append(1)
        def stop():
            assert_lock()
            self.stop()
        def restart():
            assert_lock()
            self.restart()
        out=self.recover(stopped=stop,restart=restart)
        self.assertEqual(out["state"],"five-previous-domains-observed")
        self.assertEqual(checks,[1,1])

    def test_refuses_running_orphan_process_before_file_mutation(self):
        self.initialize(pending=True)
        def stop_but_orphan():
            self.history.append("incomplete-stop")
        with self.assertRaises(whole.FiveResourceRollbackError):
            self.recover(stopped=stop_but_orphan)
        self.assertEqual(self.config.read_bytes(),b"<candidate/>")
        self.assertEqual(self.sha(self.active),self.candidate_sha)
        self.assertIsNotNone(self.store.pending())

    def test_refuses_restart_that_never_starts_three_roles(self):
        self.initialize(pending=True)
        with self.assertRaises(whole.FiveResourceRollbackError):
            self.recover(restart=lambda:self.history.append("no-restart"))
        self.assertEqual(self.config.read_bytes(),
                         (self.image/"config.xml").read_bytes())
        self.assertEqual(self.sha(self.active),self.previous["runtime"])
        self.assertEqual(self.journal.read()["phase"],"mutating")
        self.assertTrue((self.journal_dir/"runtime-restore-redo.json").exists())

    def test_foreign_kernel_blocks_before_process_stop(self):
        self.initialize(pending=False)
        self.kernel.rules[19000]=ipfw_fixture.TCP
        with self.assertRaises(Exception):
            self.recover()
        self.assertEqual(self.history,[])
        self.assertEqual(self.config.read_bytes(),b"<candidate/>")
        self.assertEqual(self.sha(self.active),self.candidate_sha)

    def test_lost_lifecycle_before_candidate_stop_denies_mutation(self):
        self.initialize(pending=True)
        calls=[0]
        def lose_lease():
            calls[0]+=1
            if calls[0]>=2:
                raise whole.FiveResourceRollbackError("native lease lost")
        with self.assertRaisesRegex(whole.FiveResourceRollbackError,"lease lost"):
            self.recover(lifecycle=lose_lease)
        self.assertEqual(self.history,[])
        self.assertEqual(self.config.read_bytes(),b"<candidate/>")
        self.assertIsNotNone(self.store.pending())

    def test_no_mutating_intent_does_not_stop(self):
        self.initialize(pending=True)
        self.journal.commit()
        with self.assertRaisesRegex(whole.FiveResourceRollbackError,"mutating"):
            self.recover()
        self.assertEqual(self.history,[])


    def test_borrowed_config_fd_preserves_one_lock_through_full_restore(self):
        self.initialize(pending=True)
        fd=os.open(self.config,os.O_RDWR)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            inode=os.fstat(fd).st_ino
            seen=[]
            def assert_owned():
                self.assertEqual(os.fstat(fd).st_ino,inode)
                with self.config.open("r+b") as another:
                    with self.assertRaises(BlockingIOError):
                        fcntl.flock(another,fcntl.LOCK_EX|fcntl.LOCK_NB)
                seen.append(True)
            def stop():
                assert_owned()
                self.stop()
            def restart():
                assert_owned()
                self.restart()
            result=self.recover(
                stopped=stop,restart=restart,locked_config_fd=fd,
            )
            self.assertEqual(result["state"],"five-previous-domains-observed")
            self.assertEqual(seen,[True,True])
            # The borrowed descriptor is still valid and LOCKED on return.
            assert_owned()
            self.assertEqual(self.config.stat().st_ino,inode)
            self.assertEqual(self.journal.read()["phase"],"mutating")
        finally:
            os.close(fd)

    def test_unlocked_borrowed_fd_refuses_before_process_stop(self):
        self.initialize(pending=True)
        fd=os.open(self.config,os.O_RDWR)
        try:
            with self.assertRaises((RuntimeError,OSError,ValueError)):
                self.recover(locked_config_fd=fd)
        finally:
            os.close(fd)
        self.assertEqual(self.history,[])
        self.assertEqual(self.config.read_bytes(),b"<candidate/>")
        self.assertIsNotNone(self.store.pending())

    def test_foreign_borrowed_fd_is_not_closed_or_used(self):
        self.initialize(pending=True)
        foreign=self.base/"foreign.xml"
        foreign.write_bytes(b"<foreign/>")
        fd=os.open(foreign,os.O_RDWR)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises((RuntimeError,OSError,ValueError)):
                self.recover(locked_config_fd=fd)
            self.assertEqual(os.fstat(fd).st_ino,foreign.stat().st_ino)
        finally:
            os.close(fd)
        self.assertEqual(self.history,[])
        self.assertEqual(foreign.read_bytes(),b"<foreign/>")

if __name__=="__main__":
    unittest.main(verbosity=2)
