#!/usr/bin/env python3
"""Genuine five-domain late-forward failure rollback: real files/IPFW-ledger.

Uses the real _69.._78 forward-chain candidate, real Config inode/flock,
actual durable runtime/Config rollback algorithms and in-memory IPFW. Only
the FreeBSD kernel and fixed shell native process actuator are simulated.
"""
from __future__ import annotations

import fcntl
import importlib.util
import os
import shutil
import stat
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
BACKEND=ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0,str(BACKEND))
from voice_cutover_journal import _digest
from voice_native_forward_runtime import _read_redo as read_forward_runtime_redo
from voice_ipfw_runtime import rollback_precommit_verified
from voice_cutover_restore_stage import prepare_restore_stage
from voice_cutover_install_image import prepare_installable_restore
from voice_native_process_actions import FreeBSDVoiceProcessActions
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS
from voice_restart_argv_attestation import expected_engine_argv
from voice_native_supervisor_launch import canonical_supervisor_argv
from voice_native_file_observer import observe_live_files
from voice_process_recovery_evidence import inspect_process_evidence
from voice_native_forward_apply import (
    rollback_failed_precommit_voice_apply, execute_prepared_voice_apply,
    NativeForwardApplyError,
)

def fixture(path,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/"scripts"/path)
    assert spec and spec.loader
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

prior=fixture("test-voice-native-forward-config.py","forward_failure_config_fixture")


class FailedNativeForwardRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.previous=prior.ForwardCandidateConfigTests()
        self.previous.setUp()
        self.addCleanup(self.previous.doCleanups)
        self.previous.call()  # Full candidate engine+supervisor, IPFW pending, Config new
        self.fx=self.previous.fx
        self.stage=self.previous.stage
        # Earlier forward fixtures intentionally left a previous-STOP probe()
        # stub in place. The live candidate fixtures use observe_processes()
        # for accurate kernel/ps topology, but the five-resource restorer
        # calls probe(). Restore its REAL implementation so a running
        # three-role candidate is actually STOPPED before the old restart.
        self.stage.probe.probe=FreeBSDVoiceProcessProbe.probe.__get__(
            self.stage.probe,FreeBSDVoiceProcessProbe,
        )
        self.assertEqual("running",self.stage.probe.probe()["engine"]["state"])
        self.config=self.fx.root/"config.xml"
        self.prepared=self.fx.whole.read()
        self.original_inode=self.config.stat().st_ino
        self.previous_config=(self.fx.backup/"config"/"config.xml").read_bytes()
        self.restore_stage=self.fx.whole.directory/"restore-stage"
        self.install_image=self.fx.whole.directory/"restore-install-image"
        prepare_restore_stage(
            self.fx.backup,self.restore_stage,self.prepared["previous"],
        )
        prepare_installable_restore(
            self.restore_stage,self.install_image,self.prepared["previous"],
        )
        self.operations=[]
        self.old_engine=expected_engine_argv(
            self.fx.backup,EXPECTED_SCRIPTS["engine"],
        )
        self.supervisor=canonical_supervisor_argv(EXPECTED_SCRIPTS)
        self.stop_refused=False
        self.simulate_native_seal=False
        self.legacy=patch("voice_native_forward_apply.require_no_legacy")
        self.legacy.start()
        self.addCleanup(self.legacy.stop)

    def runner(self,argv,**kwargs):
        self.assertEqual(argv[0],"/bin/sh")
        self.assertEqual(str(self.stage.script),argv[1])
        self.assertEqual((9,),kwargs["pass_fds"])
        with self.config.open("rb+") as other:
            with self.assertRaises(BlockingIOError):
                fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)
        action=argv[-1]
        self.operations.append(action)
        if self.stop_refused:
            return subprocess.CompletedProcess(argv,1,stdout="",stderr="stopped denied")
        if action in ("stop","stop-candidate-engine"):
            if action=="stop-candidate-engine":
                self.assertIsNone(self.stage.pids["daemon"])
                self.assertIsNone(self.stage.pids["monitor"])
            self.stage.pids.update(engine=None,daemon=None,monitor=None)
            self.stage.ps.commands={}
        elif action=="start":
            self.stage.pids.update(engine=301,daemon=302,monitor=303)
            self.stage.ps.commands={
                301:" ".join(self.old_engine),
                302:" ".join(self.supervisor["daemon"]),
                303:" ".join(self.supervisor["monitor"]),
            }
        else:
            raise AssertionError("unexpected private native lifecycle action")
        return subprocess.CompletedProcess(argv,0,stdout="",stderr="")

    def recover(self):
        fd=os.open(self.config,os.O_RDWR)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            actions=FreeBSDVoiceProcessActions(
                probe=self.stage.probe,journal=self.fx.whole,
                previous_backup=self.fx.backup,
                active_runtime=self.fx.root/"runtime",
                config_path=self.config,
                config_owner=(os.geteuid(),os.getegid()),config_fd=fd,
                require_lifecycle_owner=lambda:None,
                runner=self.runner,actuator=self.stage.script,
            )
            if self.simulate_native_seal:
                actions.process_evidence=self.fx.process
                actions.security_evidence=self.fx.policy
                actions.security_reader=object()
                actions.argv_reader=object()
            result=rollback_failed_precommit_voice_apply(
                journal=self.fx.whole,ledger=self.fx.ipfw,
                previous_backup=self.fx.backup,
                process_evidence=self.fx.process,
                security_evidence=self.fx.policy,
                install_image=self.install_image,
                config_path=self.config,active_runtime=self.fx.root/"runtime",
                staged_config=self.fx.stage_config,
                config_fd=fd,config_owner=(os.geteuid(),os.getegid()),
                probe=self.stage.probe,kernel_reader=self.stage.kernel,
                read_adapter=self.stage.parent.read,
                write_adapter=self.stage.parent.write,
                require_lifecycle_owner=lambda:None,actions=actions,
            )
            with self.config.open("rb+") as other:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return result
        finally:
            os.close(fd)

    def resume_mutating_via_executor(self, *, desired=None):
        def native_actions(fd):
            actions=FreeBSDVoiceProcessActions(
                probe=self.stage.probe, journal=self.fx.whole,
                previous_backup=self.fx.backup,
                active_runtime=self.fx.root/"runtime",
                config_path=self.config,
                config_owner=(os.geteuid(),os.getegid()),
                config_fd=fd, require_lifecycle_owner=lambda:None,
                runner=self.runner, actuator=self.stage.script,
            )
            if self.simulate_native_seal:
                actions.process_evidence=self.fx.process
                actions.security_evidence=self.fx.policy
                actions.security_reader=object()
                actions.argv_reader=object()
            return actions
        return execute_prepared_voice_apply(
            journal=self.fx.whole,ledger=self.fx.ipfw,
            previous_backup=self.fx.backup,
            process_evidence=self.fx.process,
            security_evidence=self.fx.policy,
            install_image=self.install_image,
            config_path=self.config, active_runtime=self.fx.root/"runtime",
            staged_config=self.fx.stage_config,
            candidate_runtime=self.fx.candidate,
            desired_manifest=(self.stage.parent.desired
                              if desired is None else desired),
            probe=self.stage.probe,kernel_reader=self.stage.kernel,
            read_adapter=self.stage.parent.read,
            write_adapter=self.stage.parent.write,
            require_lifecycle_owner=lambda:None,
            config_owner=(os.geteuid(),os.getegid()),
            actions_factory=native_actions,
        )

    def test_interrupted_mutating_retries_previous_under_original_executor(self):
        with patch(
            "voice_native_forward_apply.stop_previous_and_install_forward_runtime",
            side_effect=AssertionError("MUTATING must never run forward again"),
        ):
            with self.assertRaisesRegex(
                NativeForwardApplyError,
                "interrupted MUTATING Voice forward recovered previous domains",
            ):
                self.resume_mutating_via_executor()
        self.assertEqual(self.operations,["stop","start"])
        self.assertEqual(self.config.read_bytes(),self.previous_config)
        self.assertEqual(self.config.stat().st_ino,self.original_inode)
        self.assertEqual(self.fx.ipfw.owned(),self.stage.parent.old)
        self.assertIsNone(self.fx.ipfw.pending())
        self.assertEqual(self.fx.whole.read(),self.prepared)
        self.assertEqual(
            observe_live_files(self.config,self.fx.root/"runtime",
                               previous_backup=self.fx.backup),
            {k:self.prepared["previous"][k] for k in ("config","runtime")},
        )

    def test_interrupted_mutating_foreign_kernel_refuses_before_stop(self):
        self.stage.binary[202]="/bin/foreign"
        with self.assertRaisesRegex(
            NativeForwardApplyError,"interrupted MUTATING Voice recovery refused",
        ):
            self.resume_mutating_via_executor()
        self.assertEqual(self.operations,[])
        self.assertEqual(self.fx.whole.read(),self.prepared)
        self.assertEqual(self.config.read_bytes(),self.previous.candidate)
        self.assertIsNotNone(self.fx.ipfw.pending())

    def simulate_power_cut_after_old_stop_before_forward_runtime(self):
        # Rewind the simulated kernel/files from the fully exercised
        # candidate fixture to the exact earliest MUTATING power-loss
        # boundary: all THREE old process roles stopped, previous Config
        # and active runtime intact, old IPFW still owned, and NO forward
        # runtime redo or stage directory. Keep real sealed backup/journal
        # and original Config inode; never touch actual host services.
        self.stage.pids.update(engine=None,daemon=None,monitor=None)
        self.stage.ps.commands={}
        proof={"native_argv_sha256":
               self.prepared["candidate"]["native_argv_sha256"]}
        rollback_precommit_verified(
            self.fx.ipfw,self.stage.parent.write,self.fx.whole,proof,
        )
        runtime=self.fx.root/"runtime"
        redo=read_forward_runtime_redo(self.fx.whole.directory)
        self.assertIsNotNone(redo)
        retired=runtime.with_name(redo["retained_name"])
        self.assertTrue(retired.is_dir())
        discarded=runtime.with_name(".test-removed-candidate")
        os.rename(runtime,discarded)
        os.rename(retired,runtime)
        shutil.rmtree(discarded)
        (self.fx.whole.directory/"forward-runtime-redo.json").unlink()
        self.config.write_bytes(self.previous_config)
        self.config.chmod(stat.S_IMODE((self.install_image/"config.xml").stat().st_mode))
        self.assertEqual(self.config.stat().st_ino,self.original_inode)
        self.assertIsNone(self.fx.ipfw.pending())
        self.assertEqual(self.stage.parent.old,self.fx.ipfw.owned())
        self.assertEqual("stopped",self.stage.probe.probe()["engine"]["state"])
        self.assertEqual(
            observe_live_files(self.config,runtime,previous_backup=self.fx.backup),
            {k:self.prepared["previous"][k] for k in ("config","runtime")},
        )
        return runtime

    def test_power_cut_after_old_stop_before_forward_runtime_restarts_old(self):
        self.simulate_power_cut_after_old_stop_before_forward_runtime()
        with patch(
            "voice_native_forward_apply.stop_previous_and_install_forward_runtime",
            side_effect=AssertionError("interrupted MUTATING may not replay forward"),
        ):
            with self.assertRaisesRegex(
                NativeForwardApplyError,
                "interrupted MUTATING Voice forward recovered previous domains",
            ):
                self.resume_mutating_via_executor()
        self.assertEqual(self.operations,["start"])
        self.assertIsNone(self.fx.ipfw.pending())
        self.assertEqual(self.fx.whole.read()["phase"],"mutating")
        self.assertEqual(self.config.read_bytes(),self.previous_config)
        self.assertFalse((self.fx.whole.directory/"forward-runtime-redo.json").exists())

    def test_early_forward_unarmed_ready_path_refuses_process_restart(self):
        runtime=self.simulate_power_cut_after_old_stop_before_forward_runtime()
        orphan=runtime.with_name(
            ".voice-forward-ready-"+self.prepared["check"][:20]
        )
        shutil.copytree(self.fx.candidate,orphan)
        with self.assertRaisesRegex(
            NativeForwardApplyError,"interrupted MUTATING Voice recovery refused",
        ):
            self.resume_mutating_via_executor()
        self.assertEqual(self.operations,[])
        self.assertTrue(orphan.is_dir())
        self.assertEqual(self.config.read_bytes(),self.previous_config)
        self.assertEqual(self.fx.whole.read()["phase"],"mutating")

    def test_early_forward_candidate_active_without_redo_refuses_adoption(self):
        runtime=self.simulate_power_cut_after_old_stop_before_forward_runtime()
        unowned=runtime.with_name(".test-unmarked-previous")
        os.rename(runtime,unowned)
        shutil.copytree(self.fx.candidate,runtime)
        with self.assertRaisesRegex(
            NativeForwardApplyError,"interrupted MUTATING Voice recovery refused",
        ):
            self.resume_mutating_via_executor()
        self.assertEqual(self.operations,[])
        self.assertTrue(unowned.is_dir())
        self.assertIsNone(self.fx.ipfw.pending())
        self.assertEqual(self.fx.whole.read()["phase"],"mutating")

    def test_interrupted_previous_restart_without_native_readers_refuses_stop(self):
        self.recover()  # Real previous Config/runtime/IPFW and new old-process PIDs.
        self.assertEqual(self.operations,["stop","start"])
        before=self.fx.whole.read()
        with self.assertRaisesRegex(
            NativeForwardApplyError,
            "interrupted MUTATING Voice recovery refused",
        ) as raised:
            self.resume_mutating_via_executor()
        self.assertIn(
            "restarted previous Voice requires native kernel security/argv",
            str(raised.exception.__cause__),
        )
        self.assertEqual(self.operations,["stop","start"])
        self.assertEqual(self.fx.whole.read(),before)
        self.assertEqual(self.config.read_bytes(),self.previous_config)

    def test_interrupted_previous_restart_can_seal_without_second_process_stop(self):
        import voice_native_forward_apply as forward
        self.recover()
        self.assertEqual(self.operations,["stop","start"])
        self.simulate_native_seal=True
        visits=[]
        def check_locked():
            with self.config.open("rb+") as other:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)
            self.assertEqual(self.fx.whole.read()["phase"],"mutating")
            visits.append("locked")
        def integrity(**kw):
            check_locked()
            return {"state":"previous-restart-integrity-observed",
                    "safe_to_enable_voice":False,"safe_to_finish_intent":False}
        def receipt(**kw):
            check_locked()
            return {"state":"previous-receipt-sealed","can_finish_intent":False}
        def completion(**kw):
            check_locked()
            original=self.fx.whole.read()
            body={k:v for k,v in original.items() if k!="check"}
            body["phase"]="rolled_back"
            body["check"]=_digest(body)
            self.fx.whole._store(body)
            return {"state":"previous-rollback-sealed",
                    "whole_intent_phase":"rolled_back",
                    "safe_to_finish_intent":False}
        with patch.object(forward,"attest_previous_restart",side_effect=integrity), \
             patch.object(forward,"seal_previous_receipt",side_effect=receipt), \
             patch.object(forward,"seal_previous_completion",side_effect=completion), \
             patch.object(forward,"stop_previous_and_install_forward_runtime",
                          side_effect=AssertionError("must never repeat forward stages")):
            with self.assertRaisesRegex(
                NativeForwardApplyError,
                "interrupted MUTATING Voice forward recovered previous domains",
            ):
                self.resume_mutating_via_executor()
        self.assertGreaterEqual(len(visits),3)
        self.assertEqual(self.operations,["stop","start"])
        self.assertEqual(self.fx.whole.read()["phase"],"rolled_back")
        self.assertIsNone(self.fx.ipfw.pending())

    def test_original_process_epochs_not_misclassified_as_rollback(self):
        # After a durable MUTATING mark but before stop, original old PIDs
        # are still running. No receipt, no stop or forged rollback closure.
        import voice_native_forward_apply as forward
        self.simulate_power_cut_after_old_stop_before_forward_runtime()
        old=inspect_process_evidence(
            self.fx.process,self.fx.backup,EXPECTED_SCRIPTS,
            self.prepared["previous"],
        )["observation"]
        original_observation={
            "engine":{
                "state":old["engine"]["state"],
                "process":dict(old["engine"]["process"]),
            },
            "supervisor":old["supervisor"],
        }
        # The early-STOP guard compares BOTH PID and start_ns. FakePs gives
        # arbitrary synthetic lstart timestamps unrelated to the original
        # stored capture. Return the EXACT archived native observation at
        # this isolated seam instead of fabricating matching kernel times.
        self.simulate_native_seal=True
        with patch.object(
            self.stage.probe,"observe_processes",
            return_value=original_observation,
        ), patch.object(
            forward,"seal_previous_completion",
            side_effect=AssertionError("original epochs cannot seal rollback"),
        ):
            with self.assertRaisesRegex(
                NativeForwardApplyError,
                "interrupted MUTATING Voice recovery refused",
            ) as raised:
                self.resume_mutating_via_executor()
        self.assertIn(
            "original pre-STOP process epochs",
            str(raised.exception.__cause__),
        )
        self.assertEqual(self.operations,[])
        self.assertEqual(self.fx.whole.read()["phase"],"mutating")

    def test_real_late_failure_restores_old_five_domains_and_retains_intent(self):
        result=self.recover()
        self.assertEqual(result["state"],"forward-failed-five-previous-domains-observed")
        self.assertEqual(self.operations,["stop","start"])
        self.assertEqual(self.config.read_bytes(),self.previous_config)
        self.assertEqual(self.config.stat().st_ino,self.original_inode)
        self.assertEqual(
            observe_live_files(self.config,self.fx.root/"runtime",
                               previous_backup=self.fx.backup),
            {k:self.prepared["previous"][k] for k in ("config","runtime")},
        )
        self.assertIsNone(self.fx.ipfw.pending())
        self.assertEqual(
            self.fx.ipfw.owned(),self.stage.parent.old,
        )
        self.assertEqual(self.fx.whole.read(),self.prepared)
        self.assertTrue((self.fx.whole.directory/"runtime-restore-redo.json").exists())
        self.assertTrue((self.fx.whole.directory/"config-restore-redo.json").exists())
        self.assertIs(result["safe_to_enable_voice"],False)

    def test_untrusted_previous_image_refused_without_any_stop(self):
        (self.install_image/"config.xml").write_bytes(b"<foreign/>")
        with self.assertRaises((RuntimeError,ValueError)):
            self.recover()
        self.assertEqual(self.operations,[])
        self.assertEqual(self.config.read_bytes(),self.previous.candidate)
        self.assertEqual(self.fx.whole.read(),self.prepared)

    def test_actuator_failure_preserves_candidate_and_recovery_journals(self):
        self.stop_refused=True
        with self.assertRaises((RuntimeError,ValueError)):
            self.recover()
        self.assertEqual(self.operations,["stop"])
        self.assertEqual(self.fx.whole.read(),self.prepared)
        self.assertIsNotNone(self.fx.ipfw.pending())
        self.assertEqual(self.config.read_bytes(),self.previous.candidate)

    def test_foreign_kernel_engine_denies_before_any_stop(self):
        original=self.stage.binary[201]
        self.stage.binary[201]="/bin/foreign"
        with self.assertRaisesRegex(
            NativeForwardApplyError, "kernel argv/image",
        ):
            self.recover()
        self.assertEqual(self.operations,[])
        self.assertEqual(self.config.read_bytes(),self.previous.candidate)
        self.assertEqual(self.fx.whole.read(),self.prepared)
        self.stage.binary[201]=original

    def make_engine_only(self):
        # The same real candidate dvtws2 and IPFW PRECOMMIT survive, but
        # both supervisor roles are absent, as after a supervisor failure.
        self.stage.pids.update(daemon=None,monitor=None)
        self.stage.ps.commands={
            201: " ".join(self.stage.phase.expected),
        }
        self.assertEqual(
            "engine-only", self.stage.probe.observe_candidate_engine_only()["state"],
        )
        with self.assertRaises(Exception):
            self.stage.probe.observe_processes()

    def test_engine_only_candidate_real_five_domain_recovery(self):
        self.make_engine_only()
        result=self.recover()
        self.assertEqual(
            result["state"],"forward-failed-five-previous-domains-observed",
        )
        self.assertEqual(self.operations,["stop-candidate-engine","start"])
        self.assertEqual(self.config.read_bytes(),self.previous_config)
        self.assertEqual(self.config.stat().st_ino,self.original_inode)
        self.assertIsNone(self.fx.ipfw.pending())
        self.assertEqual(self.fx.ipfw.owned(),self.stage.parent.old)
        self.assertEqual("mutating",self.fx.whole.read()["phase"])
        self.assertIs(result["safe_to_enable_voice"],False)

    def test_engine_only_foreign_binary_blocks_before_stop(self):
        self.make_engine_only()
        self.stage.binary[201]="/bin/foreign"
        with self.assertRaisesRegex(
            NativeForwardApplyError, "foreign engine-only kernel",
        ):
            self.recover()
        self.assertEqual(self.operations,[])
        self.assertEqual(self.config.read_bytes(),self.previous.candidate)
        self.assertIsNotNone(self.fx.ipfw.pending())

    def test_engine_only_actuator_failure_keeps_mutating_journals(self):
        self.make_engine_only()
        self.stop_refused=True
        with self.assertRaises((RuntimeError,ValueError)):
            self.recover()
        self.assertEqual(self.operations,["stop-candidate-engine"])
        self.assertEqual("mutating",self.fx.whole.read()["phase"])
        self.assertIsNotNone(self.fx.ipfw.pending())
        self.assertEqual(self.config.read_bytes(),self.previous.candidate)

    def test_candidate_full_process_swap_before_actuator_refuses_stop(self):
        # Upper coordinator observed sealed candidate 201/202/203, then
        # daemon restarts exactly at handoff into the lower rollback stage.
        # It must not call the no-PID stop helper against a NEW process.
        import voice_native_forward_apply as forward
        original=forward.restore_previous_five_resources
        def raced(**kwargs):
            self.stage.pids["daemon"]=222
            self.stage.ps.commands.pop(202,None)
            self.stage.ps.commands[222]=" ".join(self.supervisor["daemon"])
            return original(**kwargs)
        with patch.object(
            forward,"restore_previous_five_resources",side_effect=raced,
        ):
            with self.assertRaisesRegex(
                NativeForwardApplyError,
                "interrupted MUTATING Voice recovery refused",
            ) as denied:
                self.resume_mutating_via_executor()
        self.assertIn(
            "candidate process PID/start changed before native stop",
            str(denied.exception.__cause__),
        )
        self.assertEqual(self.operations,[])
        self.assertEqual(self.fx.whole.read(),self.prepared)
        self.assertIsNotNone(self.fx.ipfw.pending())
        self.assertEqual(self.config.read_bytes(),self.previous.candidate)

    def test_partial_supervisor_topology_matrix_blocks_all_actions(self):
        # A supervisor can fail between daemon and monitor launch, lose a
        # pidfile, or leave an orphan. Never "adopt" any partial topology
        # as engine-only, and never mutate Config/IPFW/processes.
        cases={
            "engine-plus-daemon": ({"monitor":None},(203,)),
            "engine-plus-monitor": ({"daemon":None},(202,)),
            "daemon-and-monitor-no-engine": ({"engine":None},(201,)),
            "orphan-daemon": ({"daemon":None},()),
            "orphan-monitor": ({"monitor":None},()),
            "duplicate-supervisor-pid": ({"monitor":202},(203,)),
        }
        original_pids=dict(self.stage.pids)
        original_ps=dict(self.stage.ps.commands)
        for name,(updates,removes) in cases.items():
            with self.subTest(name=name):
                self.stage.pids.update(original_pids)
                self.stage.pids.update(updates)
                self.stage.ps.commands=dict(original_ps)
                for pid in removes:
                    self.stage.ps.commands.pop(pid,None)
                with self.assertRaisesRegex(
                    NativeForwardApplyError,
                    "interrupted MUTATING Voice recovery refused",
                ):
                    self.resume_mutating_via_executor()
                self.assertEqual(self.operations,[])
                self.assertEqual(self.fx.whole.read(),self.prepared)
                self.assertIsNotNone(self.fx.ipfw.pending())
                self.assertEqual(self.config.read_bytes(),self.previous.candidate)
        self.stage.pids.update(original_pids)
        self.stage.ps.commands=dict(original_ps)

    def test_partial_supervisor_remains_blocked_not_killed(self):
        self.stage.pids.update(monitor=None)
        self.stage.ps.commands.pop(203,None)
        with self.assertRaises((RuntimeError,ValueError)):
            self.recover()
        self.assertEqual(self.operations,[])
        self.assertEqual("mutating",self.fx.whole.read()["phase"])
        self.assertEqual(self.config.read_bytes(),self.previous.candidate)

    def test_native_attested_rollback_seals_terminal_under_original_fd(self):
        from unittest.mock import patch as mock_patch
        import voice_native_process_actions as lifecycle
        import voice_native_forward_apply as forward
        self.simulate_native_seal=True
        calls=[]
        def check_locked():
            with self.config.open("rb+") as other:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)
            self.assertEqual("mutating",self.fx.whole.read()["phase"])
            calls.append("locked")
        def integrity(**kwargs):
            check_locked()
            return {"state":"previous-restart-integrity-observed",
                    "safe_to_enable_voice":False,"safe_to_finish_intent":False}
        def receipt(**kwargs):
            check_locked()
            self.assertEqual(kwargs["config_path"],self.config)
            return {"state":"previous-receipt-sealed","can_finish_intent":False}
        def completion(**kwargs):
            check_locked()
            self.assertEqual(kwargs["install_image"],self.install_image)
            old=self.fx.whole.read()
            body={k:v for k,v in old.items() if k!="check"}
            body["phase"]="rolled_back"
            body["check"]=_digest(body)
            self.fx.whole._store(body)
            return {"state":"previous-rollback-sealed",
                    "whole_intent_phase":"rolled_back",
                    "safe_to_finish_intent":False}
        with mock_patch.object(lifecycle,"attest_previous_restart",side_effect=integrity), \
             mock_patch.object(forward,"attest_previous_restart",side_effect=integrity), \
             mock_patch.object(forward,"seal_previous_receipt",side_effect=receipt), \
             mock_patch.object(forward,"seal_previous_completion",side_effect=completion):
            result=self.recover()
        self.assertEqual(self.operations,["stop","start"])
        self.assertEqual(result["whole_phase"],"rolled_back")
        self.assertEqual(self.fx.whole.read()["phase"],"rolled_back")
        self.assertEqual(self.config.read_bytes(),self.previous_config)
        self.assertFalse(result["requires_durable_previous_finalization"])
        self.assertTrue(result["requires_owner_acceptance"])
        self.assertGreaterEqual(len(calls),3)

    def test_native_seal_failure_keeps_old_state_and_mutating_journal(self):
        from unittest.mock import patch as mock_patch
        import voice_native_process_actions as lifecycle
        import voice_native_forward_apply as forward
        self.simulate_native_seal=True
        integrity_report={"state":"previous-restart-integrity-observed",
                          "safe_to_enable_voice":False,
                          "safe_to_finish_intent":False}
        with mock_patch.object(lifecycle,"attest_previous_restart",
                               return_value=integrity_report), \
             mock_patch.object(forward,"attest_previous_restart",
                               return_value=integrity_report), \
             mock_patch.object(forward,"seal_previous_receipt",
                               side_effect=RuntimeError("receipt fsync refused")):
            with self.assertRaisesRegex(RuntimeError,"receipt fsync refused"):
                self.recover()
        self.assertEqual(self.operations,["stop","start"])
        self.assertEqual("mutating",self.fx.whole.read()["phase"])
        self.assertEqual(self.config.read_bytes(),self.previous_config)
        self.assertIsNone(self.fx.ipfw.pending())

    def simulate_power_cut_between_forward_renames(self):
        # Earlier _72.._75 forward chain completed both renames. Recreate
        # the exact crash point after active(previous)->retained but BEFORE
        # ready(candidate)->active; preserve the fsync'd forward redo.
        runtime=self.fx.root/"runtime"
        redo=read_forward_runtime_redo(self.fx.whole.directory)
        self.assertIsNotNone(redo)
        ready=runtime.with_name(redo["ready_name"])
        retained=runtime.with_name(redo["retained_name"])
        self.assertTrue(retained.is_dir())
        self.assertFalse(ready.exists())
        os.rename(runtime,ready)
        self.assertFalse(runtime.exists())
        self.assertTrue(ready.is_dir())
        self.stage.pids.update(engine=None,daemon=None,monitor=None)
        self.stage.ps.commands={}
        self.assertEqual("stopped",self.stage.probe.probe()["engine"]["state"])
        return ready

    def test_power_cut_between_forward_renames_can_restore_all_five_domains(self):
        ready=self.simulate_power_cut_between_forward_renames()
        result=self.recover()
        self.assertEqual("forward-failed-five-previous-domains-observed",result["state"])
        self.assertEqual(self.operations,["start"])
        self.assertEqual(self.config.read_bytes(),self.previous_config)
        self.assertEqual(self.fx.ipfw.owned(),self.stage.parent.old)
        self.assertIsNone(self.fx.ipfw.pending())
        self.assertEqual(self.fx.whole.read(),self.prepared)
        self.assertFalse(ready.exists())
        self.assertEqual(
            observe_live_files(
                self.config,self.fx.root/"runtime",previous_backup=self.fx.backup,
            ),
            {key:self.prepared["previous"][key] for key in ("config","runtime")},
        )

    def test_power_cut_missing_forward_redo_never_guesses_missing_runtime(self):
        ready=self.simulate_power_cut_between_forward_renames()
        (self.fx.whole.directory/"forward-runtime-redo.json").unlink()
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.recover()
        self.assertEqual(self.operations,[])
        self.assertFalse((self.fx.root/"runtime").exists())
        self.assertTrue(ready.exists())
        self.assertEqual(self.config.read_bytes(),self.previous.candidate)
        self.assertEqual(self.fx.whole.read(),self.prepared)

    def test_power_cut_changed_candidate_tree_denies_restore_and_restart(self):
        ready=self.simulate_power_cut_between_forward_renames()
        (ready/"dvtws.args").write_text("--port=12345\\n")
        with self.assertRaises((RuntimeError,ValueError,OSError)):
            self.recover()
        self.assertEqual(self.operations,[])
        self.assertFalse((self.fx.root/"runtime").exists())
        self.assertEqual(self.config.read_bytes(),self.previous.candidate)
        self.assertEqual(self.fx.whole.read(),self.prepared)

    def test_power_cut_in_previous_rollback_rename_can_retry_same_five_domains(self):
        import voice_cutover_runtime_restore as old_restore
        runtime=self.fx.root/"runtime"
        suffix=self.fx.whole.read()["check"][:20]
        stopped=self.stage.pids
        stopped.update(engine=None,daemon=None,monitor=None)
        self.stage.ps.commands={}
        original_rename=os.rename
        interruptions=[]
        def interrupted_rename(source,destination):
            if Path(source).name==".voice-restore-ready-"+suffix:
                interruptions.append((str(source),str(destination)))
                raise OSError("simulated second power cut inside previous runtime restore")
            return original_rename(source,destination)
        with patch.object(old_restore.os,"rename",side_effect=interrupted_rename):
            with self.assertRaisesRegex(
                OSError,"simulated second power cut",
            ):
                self.recover()
        self.assertEqual(len(interruptions),1)
        self.assertFalse(runtime.exists())
        self.assertTrue((runtime.with_name(".voice-restore-ready-"+suffix)).is_dir())
        self.assertTrue((runtime.with_name(".voice-restore-retired-"+suffix)).is_dir())
        self.assertEqual(self.operations,[])
        self.assertEqual("mutating",self.fx.whole.read()["phase"])
        self.assertIsNone(self.fx.ipfw.pending())
        self.assertEqual(self.config.read_bytes(),self.previous.candidate)
        # On second invocation the newly present previous restore redo owns
        # the missing-active state. The forward crash bridge MUST not try to
        # replay forward ready->active; existing old-restore resumes instead.
        result=self.recover()
        self.assertEqual(
            result["state"],"forward-failed-five-previous-domains-observed",
        )
        self.assertEqual(self.operations,["start"])
        self.assertEqual(self.config.read_bytes(),self.previous_config)
        self.assertEqual(self.fx.ipfw.owned(),self.stage.parent.old)
        self.assertIsNone(self.fx.ipfw.pending())
        self.assertEqual(self.fx.whole.read()["phase"],"mutating")
        self.assertEqual(
            observe_live_files(
                self.config,runtime,previous_backup=self.fx.backup,
            ),
            {key:self.prepared["previous"][key] for key in ("config","runtime")},
        )

    def test_corrupted_kernel_blocks_failure_rollback(self):
        # Candidate IPFW ledger is still pending, but a foreign in-range
        # kernel rule must never be silently adopted as ours.
        kernel=self.stage.parent.kernel
        kernel.rules[19005]=[
            "divert","989","udp","from","any","to","any","596",
            "out","not","diverted","not","sockarg","xmit","vtnet1",
        ]
        with self.assertRaises((RuntimeError,ValueError)):
            self.recover()
        self.assertEqual(self.fx.whole.read(),self.prepared)
        self.assertEqual(self.config.read_bytes(),self.previous.candidate)


if __name__=="__main__":
    unittest.main(verbosity=2)
