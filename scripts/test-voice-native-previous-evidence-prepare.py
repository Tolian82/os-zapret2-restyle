#!/usr/bin/env python3
"""Old five-domain native evidence -> existing locked Voice PREPARED, offline."""
from __future__ import annotations
import fcntl
import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"))
from voice_native_previous_evidence_prepare import prepare_native_previous_evidence
from voice_native_forward_stage_prepare import prepare_staged_forward_voice_intent
from voice_cutover_journal import VoiceCutoverJournal
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS, PIDFILES
from voice_native_kernel_argv import SYSTEM_PATHS
from voice_freebsd_process_security import FreeBSDProcessSecurityReader
from voice_process_recovery_evidence import inspect_process_evidence


def load(path, name):
    spec=importlib.util.spec_from_file_location(name, ROOT / "scripts" / path)
    assert spec and spec.loader
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


source=load("test-voice-native-forward-prepare.py", "native_previous_source")


class PreviousNativeEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.parent=source.NativeForwardPrepareTests()
        self.parent.setUp()
        self.addCleanup(self.parent.doCleanups)
        self.fx=self.parent.fx
        self.root=self.fx.root / "fresh-native-whole"
        self.root.mkdir(mode=0o700)
        self.journal=VoiceCutoverJournal(self.root)
        self.backup=self.root / "previous"
        self.original=inspect_process_evidence(
            self.fx.process, self.fx.backup, EXPECTED_SCRIPTS,
        )["observation"]
        self.snapshot={k:self.original[k] for k in ("engine", "supervisor")}
        self.probe=FreeBSDVoiceProcessProbe(EXPECTED_SCRIPTS, PIDFILES, self.backup)
        self.process_patch=patch.object(
            self.probe, "observe_processes", return_value={
                "engine":{k:v for k,v in self.snapshot["engine"].items()
                          if k!="runtime_args_sha256"},
                "supervisor":self.snapshot["supervisor"],
            },
        )
        self.process_patch.start()
        self.addCleanup(self.process_patch.stop)
        credentials=source.src.fixture.CREDS
        by_pid={101:"engine",102:"daemon",103:"monitor"}
        self.reader=FreeBSDProcessSecurityReader(
            EXPECTED_SCRIPTS,SYSTEM_PATHS,credentials,self.probe,
            path_reader=lambda pid: SYSTEM_PATHS[by_pid[pid]].encode()+b"\x00",
            ps_reader=lambda argv: str(int(argv[2])) + " " + " ".join(
                str(credentials[by_pid[int(argv[2])]][x])
                for x in ("euid","ruid","svuid","egid","rgid","svgid")
            ) + "\n",
        )
        self.fd=None

    def call(self, *, locked=True):
        fd=os.open(self.parent.live_config,os.O_RDWR)
        try:
            if locked:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return prepare_native_previous_evidence(
                journal=self.journal,ledger=self.fx.ipfw,
                config_path=self.parent.live_config,
                active_runtime=self.parent.live_runtime,
                probe=self.probe,security_reader=self.reader,
                ipfw_adapter=self.parent.adapter,
                config_fd=fd,config_owner=(os.geteuid(),os.getegid()),
                require_lifecycle_owner=lambda:self.parent.lock_hits.append("FD9"),
            )
        finally:
            os.close(fd)

    def test_previous_evidence_and_prepared_candidate_share_one_original_lock(self):
        fd=os.open(self.parent.live_config,os.O_RDWR)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            common=dict(config_fd=fd,config_owner=(os.geteuid(),os.getegid()),
                        require_lifecycle_owner=lambda:self.parent.lock_hits.append("FD9"))
            result=prepare_native_previous_evidence(
                journal=self.journal,ledger=self.fx.ipfw,
                config_path=self.parent.live_config,
                active_runtime=self.parent.live_runtime,
                probe=self.probe,security_reader=self.reader,
                ipfw_adapter=self.parent.adapter,**common,
            )
            self.assertEqual("native-previous-five-domains-sealed",result["state"])
            self.assertEqual(self.fx.prior,result["previous"])
            cutover=prepare_staged_forward_voice_intent(
                journal=self.journal,ledger=self.fx.ipfw,
                previous_backup=result["previous_backup"],
                process_evidence=result["process_evidence"],
                security_evidence=result["security_evidence"],
                previous_observer=result["previous_observer"],
                config_path=self.parent.live_config,
                active_runtime=self.parent.live_runtime,
                source_config=self.fx.stage_config,
                source_runtime=self.fx.candidate,
                proof=self.parent.proof,desired_manifest=self.parent.manifest,
                expected_scripts=EXPECTED_SCRIPTS,
                ipfw_adapter=self.parent.adapter,**common,
            )
            self.assertEqual("native-voice-stage-and-forward-prepared",cutover["state"])
            self.assertEqual("prepared",self.journal.read()["phase"])
            self.assertEqual(4,self.journal.read()["schema"])
            self.assertTrue((self.root/"restore-install-image").is_dir())
            self.assertFalse(result["safe_to_enable_voice"])
            self.assertFalse(cutover["safe_to_enable_voice"])
        finally:
            os.close(fd)

    def test_unsealed_ipfw_is_never_adopted(self):
        with patch.object(self.fx.ipfw,"owned",return_value=None):
            with self.assertRaises((ValueError,RuntimeError,OSError)):
                self.call()
        self.assertEqual([],os.listdir(self.root))

    def test_original_config_lock_required_before_first_snapshot(self):
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.call(locked=False)
        self.assertEqual([],os.listdir(self.root))

    def test_foreign_previous_evidence_blocks_new_snapshot(self):
        (self.root/"previous").mkdir(mode=0o700)
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.call()
        self.assertIsNone(self.journal.read())

    def test_process_capture_failure_retains_previous_seal(self):
        with patch("voice_native_previous_evidence_prepare.capture_process_evidence",
                   side_effect=OSError("simulated interruption")):
            with self.assertRaises(OSError):
                self.call()
        self.assertTrue((self.root/"previous").is_dir())
        self.assertFalse((self.root/"process-evidence").exists())
        self.assertIsNone(self.journal.read())
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.call()


if __name__=="__main__":
    unittest.main(verbosity=2)
