#!/usr/bin/env python3
"""FD9/Config-flock boot crash review: genuine disk, fake process and kernel.

Each case is read-only once its fixture has simulated the crash. A pending
schema-4 whole journal MUST remain in place, even when all prior bytes look
healthy. No test authorizes automatic Voice ON, rollback or journal cleanup.
"""
from __future__ import annotations

import copy
import fcntl
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import unittest

ROOT=Path(__file__).resolve().parent.parent
BACKEND=ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0,str(BACKEND))
from voice_native_boot_recovery_review import inspect_boot_recovery, BootReviewError
from voice_native_forward_apply import execute_prepared_voice_apply, NativeForwardApplyError
from voice_native_kernel_argv import FreeBSDKernelArgvReader
from voice_ipfw_adapter import FreeBSDIPFWAdapter
from voice_firewall_ledger import decode_manifest
from voice_cutover_recovery_receipt import read_receipt
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS,PIDFILES
from voice_ipfw_adapter import FreeBSDIPFWAdapter
from voice_cutover_install_image import prepare_installable_restore
from voice_cutover_config_redo import ConfigRestoreRedo
from voice_cutover_runtime_restore import _arm,_record
from voice_native_file_observer import observe_live_files
from voice_cutover_backup import _sync_dir


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/"scripts"/path)
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


f=load("test-voice-cutover-runtime-bound-intent.py","boot_review_schema4_fixture")
k=load("test-voice-native-ipfw-ownership.py","boot_review_kernel_fixture")
cleanup_fixture=load("test-voice-cutover-cleanup-prepare.py","boot_review_terminal_fixture")


class BootReviewTests(unittest.TestCase):
    def setUp(self):
        self.fx=f.RuntimeBoundCutoverTests()
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.fx.begin()
        self.fx.whole.mark_mutating()
        self.image=self.fx.root/"restore-install-image"
        prepare_installable_restore(self.fx.backup,self.image,self.fx.prior)
        self.process=FreeBSDVoiceProcessProbe(
            EXPECTED_SCRIPTS,PIDFILES,self.fx.backup,ps_reader=lambda _: ""
        )
        self.process.probe=lambda:{
            "engine":{
                "state":"stopped","process":{
                    "pid":None,"start_ns":None,"executable":EXPECTED_SCRIPTS["engine"]
                },"runtime_args_sha256":self.fx.prior["runtime"],
            },
            "supervisor":{
                "state":"stopped",
                "daemon":{"pid":None,"start_ns":None,"executable":EXPECTED_SCRIPTS["daemon"]},
                "monitor":{"pid":None,"start_ns":None,"executable":EXPECTED_SCRIPTS["monitor"]},
            },
        }
        self.kernel=k.KernelSimulator()
        self.adapter=FreeBSDIPFWAdapter(19000,19010,runner=self.kernel)
        self.locks=[]

    def inspect(self):
        fd=os.open(self.fx.root/"config.xml",os.O_RDWR)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return inspect_boot_recovery(
                journal=self.fx.whole,ledger=self.fx.ipfw,
                previous_backup=self.fx.backup,process_evidence=self.fx.process,
                security_evidence=self.fx.policy,install_image=self.image,
                config_path=self.fx.root/"config.xml",
                active_runtime=self.fx.candidate,
                probe=self.process,adapter=self.adapter,config_fd=fd,
                config_owner=(os.geteuid(),os.getegid()),
                require_lifecycle_owner=lambda:self.locks.append("FD9"),
            )
        finally:
            os.close(fd)

    def assert_denied(self,report):
        for key in ("safe_to_start","safe_to_rollback_automatically",
                    "safe_to_close_intent","voice_on"):
            self.assertIs(report[key],False)
        self.assertEqual("mutating",self.fx.whole.read()["phase"])

    def test_cold_boot_stopped_previous_kernel_candidate_runtime(self):
        original=self.fx.whole.read()
        report=self.inspect()
        self.assert_denied(report)
        self.assertEqual("manual-recovery-required",report["state"])
        self.assertEqual("candidate",report["runtime"])
        self.assertEqual("previous",report["config"])
        self.assertEqual("stopped",report["processes"])
        self.assertEqual("previous",report["kernel"])
        self.assertEqual("absent",report["runtime_redo"])
        self.assertEqual(original,self.fx.whole.read())
        self.assertGreaterEqual(len(self.locks),2)

    def test_crash_after_active_runtime_rename_is_distinguished(self):
        journal=self.fx.whole.read()
        info=self.fx.candidate.parent.stat()
        key=journal["check"][:20]
        data=_record({
            "schema":1,"cutover_check":journal["check"],
            "parent_dev":info.st_dev,"parent_ino":info.st_ino,
            "active_name":self.fx.candidate.name,
            "candidate_sha256":journal["candidate"]["candidate_runtime_sha256"],
            "previous_sha256":journal["previous"]["runtime"],
            "ready_name":".voice-restore-ready-"+key,
            "retired_name":".voice-restore-retired-"+key,
        })
        _arm(self.fx.whole.directory,data)
        self.fx.candidate.rename(self.fx.root/data["retired_name"])
        result=self.inspect()
        self.assert_denied(result)
        self.assertEqual("missing-after-rename",result["runtime"])
        self.assertEqual("present",result["runtime_redo"])
        self.assertEqual("manual-recovery-required",result["state"])

    def test_partial_config_truncate_with_durable_redo_is_distinguished(self):
        config=self.fx.root/"config.xml"
        fd=os.open(config,os.O_RDWR)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            ConfigRestoreRedo(self.fx.whole.directory).arm(
                journal_record=self.fx.whole.read(),info=os.fstat(fd),
                previous_bytes=config.stat().st_size,
            )
            os.ftruncate(fd,0)
            os.write(fd,b"<op")
            os.fsync(fd)
        finally:
            os.close(fd)
        result=self.inspect()
        self.assert_denied(result)
        self.assertEqual("armed-previous-prefix",result["config"])
        self.assertEqual("present",result["config_redo"])
        self.assertEqual("manual-recovery-required",result["state"])

    def test_reset_unknown_kernel_requires_manual_recovery(self):
        self.kernel.rules[19000]=k.TCP
        report=self.inspect()
        self.assert_denied(report)
        self.assertEqual("unknown-or-reset",report["kernel"])

    def test_foreign_redo_or_corrupt_policy_is_not_readable(self):
        self.fx.whole.directory.joinpath("runtime-restore-redo.json").write_text("foreign")
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.inspect()
        self.fx.whole.directory.joinpath("runtime-restore-redo.json").unlink()
        (self.fx.policy/"policy.json").write_text("foreign")
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.inspect()

    def test_foreign_runtime_or_missing_config_lock_fails_closed(self):
        (self.fx.candidate/"foreign.sh").write_text("untrusted")
        report=self.inspect()
        self.assert_denied(report)
        self.assertEqual("foreign",report["runtime"])
        fd=os.open(self.fx.root/"config.xml",os.O_RDWR)
        try:
            with self.assertRaises((BootReviewError,ValueError,RuntimeError)):
                inspect_boot_recovery(
                    journal=self.fx.whole,ledger=self.fx.ipfw,
                    previous_backup=self.fx.backup,process_evidence=self.fx.process,
                    security_evidence=self.fx.policy,install_image=self.image,
                    config_path=self.fx.root/"config.xml",active_runtime=self.fx.candidate,
                    probe=self.process,adapter=self.adapter,config_fd=fd,
                    config_owner=(os.geteuid(),os.getegid()),
                    require_lifecycle_owner=lambda:None,
                )
        finally:
            os.close(fd)

    def test_boot_review_service_not_gui_and_fd9_bound(self):
        script=(ROOT/"src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
        self.assertIn("native-voice-boot-review)",script)
        self.assertIn("native_voice_boot_review_service",script)
        self.assertIn("voice_native_boot_recovery_review.py",script)
        self.assertIn("native-voice-rollback-five|native-voice-boot-review|",script)
        self.assertIn("service_with_lifecycle_lock",script)



class TerminalBootReviewTests(unittest.TestCase):
    """Read-only post-crash review of a REAL sealed terminal journal.

    The fixture seals the receipt/plan under a genuine Linux/FreeBSD flock
    BEFORE boot inspection. The inspection never runs cleanup or restarts.
    """
    def setUp(self):
        self.helper=cleanup_fixture.CleanupPrepareTests()
        self.helper.setUp()
        self.addCleanup(self.helper.doCleanups)
        self.fx=self.helper.fx
        self.fx.seal()
        self.helper.complete()
        self.before=self.fx.fx.whole.read()
        self.calls=[]

    def inspect(self):
        fd=os.open(self.fx.config,os.O_RDWR)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return inspect_boot_recovery(
                journal=self.fx.fx.whole,ledger=self.fx.fx.ipfw,
                previous_backup=self.fx.fx.backup,
                process_evidence=self.fx.fx.process,
                security_evidence=self.fx.fx.policy,
                install_image=self.fx.image,
                config_path=self.fx.config,
                active_runtime=self.fx.live,
                probe=self.fx.probe,adapter=self.fx.adapter,
                config_fd=fd,config_owner=(os.geteuid(),os.getegid()),
                require_lifecycle_owner=lambda:self.calls.append("FD9"),
            )
        finally:
            os.close(fd)

    def replay_in_original_executor(self, *, desired=None):
        # Exact already-sealed rollback in a real filesystem fixture;
        # both kernel and process ACTUATORS are deliberately poison-pill
        # objects: no terminal retry may call or construct mutation paths.
        original=self.fx.fx.whole.read()
        native=FreeBSDKernelArgvReader(
            raw_argv_reader=lambda pid: (_ for _ in ()).throw(
                AssertionError("rolled-back retry must not query forward argv")
            ),
            raw_path_reader=lambda pid: (_ for _ in ()).throw(
                AssertionError("rolled-back retry must not query forward binary")
            ),
        )
        read=self.fx.adapter
        def deny_mutation(*args,**kwargs):
            raise AssertionError("rolled-back retry must not call IPFW writer")
        write=FreeBSDIPFWAdapter(
            19000,19010,allow_mutations=True,runner=deny_mutation,
        )
        expected_manifest=cleanup_fixture.receipt_tests.source.fixture.IPFW
        return execute_prepared_voice_apply(
            journal=self.fx.fx.whole, ledger=self.fx.fx.ipfw,
            previous_backup=self.fx.fx.backup,
            process_evidence=self.fx.fx.process,
            security_evidence=self.fx.fx.policy,
            install_image=self.fx.image,
            config_path=self.fx.config, active_runtime=self.fx.live,
            staged_config=self.fx.fx.stage_config,
            candidate_runtime=self.fx.fx.candidate,
            desired_manifest=expected_manifest if desired is None else desired,
            probe=self.fx.probe,kernel_reader=native,
            read_adapter=read,write_adapter=write,
            require_lifecycle_owner=lambda:self.calls.append("FD9"),
            config_owner=(os.geteuid(),os.getegid()),
            actions_factory=lambda fd:deny_mutation(fd),
        )

    def test_original_executor_retries_rolled_back_read_only(self):
        before=self.fx.fx.whole.read()
        files=(self.fx.config.read_bytes(),
               (self.fx.live/"dvtws.args").read_bytes())
        result=self.replay_in_original_executor()
        self.assertEqual("native-voice-rolled-back-read-only-verified",
                         result["state"])
        self.assertEqual(result["whole_phase"],"rolled_back")
        self.assertIs(result["safe_to_enable_voice"],False)
        self.assertIs(result["safe_to_close_intent"],False)
        self.assertFalse(result["process_action_performed"])
        self.assertFalse(result["ipfw_mutation_performed"])
        self.assertEqual(self.fx.fx.whole.read(),before)
        self.assertEqual(
            (self.fx.config.read_bytes(),
             (self.fx.live/"dvtws.args").read_bytes()),files
        )
        self.assertTrue(self.fx.image.exists())
        self.assertIsNotNone(read_receipt(self.fx.fx.whole.directory))
        self.assertGreaterEqual(len(self.calls),2)

    def test_original_executor_rejects_stale_epoch_or_reset_ipfw(self):
        prior=self.fx.fx.whole.read()
        self.fx.state=copy.deepcopy(self.fx.state)
        self.fx.state["supervisor"]["daemon"]["start_ns"]+=1234
        with self.assertRaisesRegex(
            NativeForwardApplyError,"terminal Voice rollback cannot be re-attested",
        ):
            self.replay_in_original_executor()
        self.assertEqual(self.fx.fx.whole.read(),prior)
        self.fx.state["supervisor"]["daemon"]["start_ns"]-=1234
        self.fx.kernel.rules[19000]=k.TCP
        with self.assertRaisesRegex(
            NativeForwardApplyError,"terminal Voice rollback cannot be re-attested",
        ):
            self.replay_in_original_executor()
        self.assertEqual(self.fx.fx.whole.read(),prior)

    def test_original_executor_rejects_foreign_or_missing_terminal_proof(self):
        record=self.fx.fx.whole.read()
        foreign={"services":{"telegram":{"rules":[]}}}
        with self.assertRaises((NativeForwardApplyError,ValueError,RuntimeError)):
            self.replay_in_original_executor(desired=foreign)
        receipt=self.fx.fx.whole.directory/"previous-rollback-receipt.json"
        saved=receipt.read_bytes()
        receipt.unlink()
        try:
            with self.assertRaises((ValueError,RuntimeError)):
                self.replay_in_original_executor()
            self.assertEqual(self.fx.fx.whole.read(),record)
        finally:
            receipt.write_bytes(saved)
            receipt.chmod(0o600)

    def test_terminal_boot_read_only_never_promotes_to_voice_on(self):
        report=self.inspect()
        self.assertEqual("previous-rollback-sealed-needs-manual-finalization",
                         report["state"])
        self.assertEqual("rolled_back",report["phase"])
        self.assertEqual("previous",report["runtime"])
        self.assertEqual("previous",report["config"])
        self.assertEqual("previous",report["kernel"])
        self.assertEqual("prepared-only",report["cleanup_plan"])
        for field in ("safe_to_start","safe_to_rollback_automatically",
                      "safe_to_close_intent","voice_on"):
            self.assertIs(report[field],False)
        self.assertEqual(self.before,self.fx.fx.whole.read())
        self.assertTrue(self.fx.image.exists())
        self.assertGreaterEqual(len(self.calls),2)

    def test_terminal_boot_reset_kernel_and_new_epoch_not_readiness(self):
        self.fx.kernel.rules[19000]=k.TCP
        self.fx.state=copy.deepcopy(self.fx.state)
        self.fx.state["supervisor"]["daemon"]["start_ns"]+=1234
        report=self.inspect()
        self.assertEqual("unknown-or-reset",report["kernel"])
        self.assertEqual("stale-process-epoch",report["previous_receipt"])
        self.assertEqual("previous-rollback-sealed-needs-manual-finalization",
                         report["state"])
        self.assertIs(report["safe_to_close_intent"],False)
        self.assertEqual(self.before,self.fx.fx.whole.read())

    def test_terminal_missing_or_corrupt_receipt_plan_fail_closed(self):
        for name in ("previous-cleanup-plan.json","previous-rollback-receipt.json"):
            with self.subTest(name=name):
                path=self.fx.fx.whole.directory/name
                saved=path.read_bytes()
                path.unlink()
                try:
                    with self.assertRaises((ValueError,OSError,RuntimeError)):
                        self.inspect()
                    self.assertEqual(self.before,self.fx.fx.whole.read())
                finally:
                    path.write_bytes(saved)
                    path.chmod(0o600)
        path=self.fx.fx.whole.directory/"previous-cleanup-plan.json"
        path.write_bytes(b'{"schema":1,"phase":"forged"}')
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.inspect()
        self.assertEqual(self.before,self.fx.fx.whole.read())

    def test_terminal_previous_bytes_or_inode_tampering_denied(self):
        with self.fx.config.open("ab") as writer:
            writer.write(b"changed")
        with self.assertRaises((ValueError,OSError,RuntimeError)):
            self.inspect()
        self.assertEqual(self.before,self.fx.fx.whole.read())


if __name__=="__main__":
    unittest.main(verbosity=2)
