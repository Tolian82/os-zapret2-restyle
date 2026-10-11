#!/usr/bin/env python3
"""Real files/journals + fake FreeBSD native process/IPFW: candidate Config."""
from __future__ import annotations
import fcntl
import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))
import voice_native_forward_config as forward
from voice_native_forward_config import NAME, read_forward_config_redo
from voice_native_file_observer import observe_live_files

spec = importlib.util.spec_from_file_location(
    "forward_config_supervisor_fixture",
    ROOT / "scripts/test-voice-native-forward-supervisor.py",
)
assert spec and spec.loader
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class ForwardCandidateConfigTests(unittest.TestCase):
    def setUp(self):
        self.stage = fixture.ForwardSupervisorTests()
        self.stage.setUp()
        self.addCleanup(self.stage.doCleanups)
        self.stage.call()  # _69 PREPARED through _75 native supervisor
        self.fx = self.stage.fx
        self.config = self.fx.root / "config.xml"
        self.before = self.config.read_bytes()
        self.previous_inode = self.config.stat().st_ino
        self.candidate = self.fx.stage_config.read_bytes()
        self.journal = self.fx.whole.read()
        self.pending = self.fx.ipfw.pending()
        self.stub = patch("voice_native_forward_config.require_no_legacy")
        self.stub.start()
        self.addCleanup(self.stub.stop)

    def call(self, locked=True, **overrides):
        fd = os.open(self.config, os.O_RDWR)
        try:
            if locked:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            args = dict(
                journal=self.fx.whole,
                ledger=self.fx.ipfw,
                previous_backup=self.fx.backup,
                config_path=self.config,
                locked_config_fd=fd,
                config_owner=(os.geteuid(), os.getegid()),
                staged_config=self.fx.stage_config,
                candidate_runtime=self.fx.candidate,
                active_runtime=self.fx.root / "runtime",
                desired_manifest=self.stage.parent.desired,
                probe=self.stage.probe,
                kernel_reader=self.stage.kernel,
                readonly_adapter=self.stage.parent.read,
                require_lifecycle_owner=lambda: None,
            )
            args.update(overrides)
            return forward.persist_forward_candidate_config(**args)
        finally:
            os.close(fd)

    def test_real_candidate_write_keeps_config_inode_and_all_rollback_evidence(self):
        self.assertEqual(
            self.call(), "candidate-config-persisted-pending-whole-commit"
        )
        self.assertEqual(self.config.read_bytes(), self.candidate)
        self.assertEqual(self.config.stat().st_ino, self.previous_inode)
        self.assertEqual(self.fx.whole.read(), self.journal)
        self.assertEqual(self.fx.ipfw.pending(), self.pending)
        marker = read_forward_config_redo(self.fx.whole.directory)
        self.assertIsNotNone(marker)
        self.assertEqual(marker["whole_check"], self.journal["check"])
        self.assertEqual(marker["config_inode"], self.previous_inode)
        self.assertEqual(
            marker["candidate_sha256"], self.journal["candidate"]["saved_xml_sha256"]
        )
        self.assertEqual("candidate-config-already-persisted", self.call())
        self.assertEqual(
            observe_live_files(self.config, self.fx.root / "runtime"),
            {
                "config": self.journal["candidate"]["saved_xml_sha256"],
                "runtime": self.journal["candidate"]["candidate_runtime_sha256"],
            },
        )

    def test_requires_original_config_flock_and_fd9_owner(self):
        with self.assertRaises((OSError, RuntimeError)):
            self.call(locked=False)
        def invalid_owner():
            raise RuntimeError("FD9 native owner missing")
        with self.assertRaisesRegex(RuntimeError, "FD9"):
            self.call(require_lifecycle_owner=invalid_owner)
        self.assertEqual(self.config.read_bytes(), self.before)
        self.assertFalse((self.fx.whole.directory / NAME).exists())

    def test_missing_ipfw_precommit_or_kernel_supervisor_denies(self):
        self.stage.pids["monitor"] = None
        with self.assertRaises((RuntimeError, ValueError)):
            self.call()
        self.assertEqual(self.config.read_bytes(), self.before)
        self.assertFalse((self.fx.whole.directory / NAME).exists())
        self.stage.pids["monitor"] = 203
        (self.fx.ipfw.directory / "intent.json").unlink()
        with self.assertRaises((RuntimeError, ValueError)):
            self.call()
        self.assertEqual(self.config.read_bytes(), self.before)

    def test_staged_config_or_foreign_live_config_denies(self):
        self.fx.stage_config.write_bytes(b"<tampered/>")
        with self.assertRaises((RuntimeError, ValueError)):
            self.call()
        self.assertEqual(self.config.read_bytes(), self.before)
        self.fx.stage_config.write_bytes(self.candidate)
        self.config.write_bytes(b"<foreign/>")
        with self.assertRaisesRegex(forward.ForwardConfigError, "foreign"):
            self.call()
        self.assertEqual(self.config.read_bytes(), b"<foreign/>")

    def test_power_loss_retries_only_candidate_prefix(self):
        def interrupted(fd, data):
            os.write(fd, data[:9])
            raise OSError("simulated power cut")
        with patch.object(forward, "_write_all", side_effect=interrupted):
            with self.assertRaisesRegex(OSError, "power cut"):
                self.call()
        self.assertEqual(self.config.read_bytes(), self.candidate[:9])
        marker = read_forward_config_redo(self.fx.whole.directory)
        self.assertIsNotNone(marker)
        self.assertEqual(self.journal, self.fx.whole.read())
        self.assertEqual(self.pending, self.fx.ipfw.pending())
        self.assertEqual(
            "candidate-config-persisted-pending-whole-commit", self.call()
        )
        self.assertEqual(self.config.read_bytes(), self.candidate)
        self.assertEqual(marker, read_forward_config_redo(self.fx.whole.directory))
        self.assertEqual(self.config.stat().st_ino, self.previous_inode)

    def test_marker_never_licenses_foreign_partial(self):
        def interrupted(fd, data):
            os.write(fd, data[:7])
            raise OSError("cut")
        with patch.object(forward, "_write_all", side_effect=interrupted):
            with self.assertRaises(OSError):
                self.call()
        self.config.write_bytes(b"<foreign/>")
        with self.assertRaisesRegex(forward.ForwardConfigError, "foreign"):
            self.call()
        self.assertEqual(self.config.read_bytes(), b"<foreign/>")

    def test_partial_without_marker_is_not_adopted(self):
        self.config.write_bytes(self.candidate[:8])
        with self.assertRaisesRegex(forward.ForwardConfigError, "foreign"):
            self.call()
        self.assertFalse((self.fx.whole.directory / NAME).exists())

    def test_corrupted_redo_and_replaced_inode_refused(self):
        def interrupted(fd, data):
            os.write(fd, data[:9])
            raise OSError("cut")
        with patch.object(forward, "_write_all", side_effect=interrupted):
            with self.assertRaises(OSError):
                self.call()
        redo = self.fx.whole.directory / NAME
        saved = redo.read_bytes()
        redo.write_bytes(b'{"invalid":true}\n')
        with self.assertRaises((RuntimeError, ValueError)):
            self.call()
        self.assertEqual(self.config.read_bytes(), self.candidate[:9])
        redo.write_bytes(saved)
        replacement = self.fx.root / "replacement-config.xml"
        replacement.write_bytes(self.candidate[:9])
        replacement.chmod(0o640)
        os.replace(replacement, self.config)
        with self.assertRaises((RuntimeError, ValueError)):
            self.call()
        self.assertEqual(self.config.read_bytes(), self.candidate[:9])


    def _previous_restore(self):
        from voice_cutover_restore_stage import prepare_restore_stage
        from voice_cutover_install_image import prepare_installable_restore
        from voice_cutover_config_restore import restore_previous_config_in_place
        restore_stage = self.fx.root / "restore-stage"
        install_image = self.fx.root / "restore-image"
        prepare_restore_stage(self.fx.backup, restore_stage, self.journal["previous"])
        prepare_installable_restore(restore_stage, install_image, self.journal["previous"])
        fd = os.open(self.config, os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return restore_previous_config_in_place(
                self.config, install_image, self.fx.backup, self.fx.whole,
                require_lifecycle_owner=lambda: None,
                expected_owner=(os.geteuid(), os.getegid()),
                locked_config_fd=fd,
            )
        finally:
            os.close(fd)

    def test_torn_forward_config_can_rollback_old_without_running_forward_again(self):
        def interrupted(fd, data):
            os.write(fd, data[:9])
            raise OSError("power lost")
        with patch.object(forward, "_write_all", side_effect=interrupted):
            with self.assertRaises(OSError):
                self.call()
        self.assertEqual(self.config.read_bytes(), self.candidate[:9])
        # A five-resource coordinator stops candidate engine/IPFW before
        # invoking this existing file restorer; no new-engine restart needed.
        self.assertEqual("previous-config-restored", self._previous_restore())
        self.assertEqual(self.config.read_bytes(), self.before)
        self.assertEqual(self.config.stat().st_ino, self.previous_inode)
        self.assertEqual("mutating", self.fx.whole.read()["phase"])
        self.assertTrue((self.fx.whole.directory / NAME).exists())

    def test_torn_forward_config_source_replacement_denies_old_restore(self):
        def interrupted(fd, data):
            os.write(fd, data[:9])
            raise OSError("power lost")
        with patch.object(forward, "_write_all", side_effect=interrupted):
            with self.assertRaises(OSError):
                self.call()
        original = self.config.read_bytes()
        self.fx.stage_config.unlink()
        self.fx.stage_config.write_bytes(self.candidate)
        with self.assertRaises((RuntimeError, ValueError)):
            self._previous_restore()
        self.assertEqual(self.config.read_bytes(), original)

if __name__ == "__main__":
    unittest.main(verbosity=2)
