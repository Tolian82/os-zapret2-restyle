#!/usr/bin/env python3
"""Write-once native candidate release -> genuine five-resource PREPARED intent."""
from __future__ import annotations
import fcntl
import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"))
from voice_native_forward_stage_prepare import prepare_staged_forward_voice_intent
from voice_native_apply_route import sealed_prepared_handoff
from voice_cutover_guard import check_pending

def fixture(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / path)
    assert spec and spec.loader
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

source = fixture("test-voice-native-forward-prepare.py", "voice_stage_forward_fixture")


class NativeStagePrepareTests(unittest.TestCase):
    def setUp(self):
        self.parent = source.NativeForwardPrepareTests()
        self.parent.setUp()
        self.addCleanup(self.parent.doCleanups)
        self.fx = self.parent.fx

    def prepare(self, *, locked=True, config_source=None, runtime_source=None):
        fd = os.open(self.parent.live_config, os.O_RDWR)
        try:
            if locked:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return prepare_staged_forward_voice_intent(
                journal=self.fx.whole, ledger=self.fx.ipfw,
                previous_backup=self.fx.backup,
                process_evidence=self.fx.process, security_evidence=self.fx.policy,
                previous_observer=self.parent.observer,
                config_path=self.parent.live_config,
                active_runtime=self.parent.live_runtime,
                source_config=config_source or self.fx.stage_config,
                source_runtime=runtime_source or self.fx.candidate,
                proof=self.parent.proof, desired_manifest=self.parent.manifest,
                expected_scripts=source.src.fixture.SCRIPTS,
                ipfw_adapter=self.parent.adapter,
                config_fd=fd, config_owner=(os.geteuid(), os.getegid()),
                require_lifecycle_owner=lambda: self.parent.lock_hits.append("FD9"),
            )
        finally:
            os.close(fd)

    def test_real_stage_and_original_schema4_prepared_under_same_config_lock(self):
        before_config = self.parent.live_config.read_bytes()
        result = self.prepare()
        stage = self.fx.whole.directory / "forward-candidate"
        record = self.fx.whole.read()
        self.assertEqual("native-voice-stage-and-forward-prepared", result["state"])
        self.assertEqual("prepared", record["phase"])
        self.assertEqual(4, record["schema"])
        self.assertEqual(sealed_prepared_handoff(self.fx.whole, stage),
                         self.parent.manifest)
        self.assertEqual(result["whole_check"], record["check"])
        self.assertEqual(self.parent.live_config.read_bytes(), before_config)
        self.assertIsNone(self.fx.ipfw.pending())
        self.assertFalse(result["safe_to_enable_voice"])
        self.assertFalse(check_pending(self.fx.whole.directory,
                                       self.fx.ipfw.directory)["safe_to_mutate"])

    def test_no_repeat_stage_and_no_repeat_journal(self):
        self.prepare()
        previous = self.fx.whole.read()
        with self.assertRaises((OSError, RuntimeError, ValueError)):
            self.prepare()
        self.assertEqual(previous, self.fx.whole.read())

    def test_config_flock_is_required_before_any_stage_write(self):
        with self.assertRaises((OSError, RuntimeError, ValueError)):
            self.prepare(locked=False)
        self.assertFalse((self.fx.whole.directory / "forward-candidate").exists())
        self.assertIsNone(self.fx.whole.read())

    def test_wrong_candidate_proof_or_unknown_old_state_does_not_start_mutation(self):
        self.fx.stage_config.write_bytes(b"<foreign/>")
        with self.assertRaises((OSError, RuntimeError, ValueError)):
            self.prepare()
        self.assertFalse((self.fx.whole.directory / "forward-candidate").exists())
        self.assertIsNone(self.fx.whole.read())

    def test_unknown_partial_stage_blocks_future_preparation(self):
        (self.fx.whole.directory / ".forward-candidate-orphan").mkdir(mode=0o700)
        with self.assertRaises((OSError, RuntimeError, ValueError)):
            self.prepare()
        self.assertIsNone(self.fx.whole.read())


if __name__ == "__main__":
    unittest.main(verbosity=2)
