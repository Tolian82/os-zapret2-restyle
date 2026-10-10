#!/usr/bin/env python3
"""Isolated real-fd Config restore; never run against a live OPNsense router."""
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

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

from voice_cutover_backup import (
    capture_previous, bound_resource_fingerprints,
)
from voice_cutover_journal import VoiceCutoverJournal
from voice_cutover_restore_stage import prepare_restore_stage
from voice_cutover_install_image import prepare_installable_restore
import voice_cutover_config_restore as config_restorer

spec = importlib.util.spec_from_file_location(
    "config_restore_firewall_fixture",
    ROOT / "scripts/test-voice-firewall-transaction.py",
)
assert spec and spec.loader
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)

OLD = b"<opnsense><zapret>previous</zapret></opnsense>\n"
NEW = b"<opnsense><zapret>candidate</zapret></opnsense>\n"


class RealConfigInPlaceRestore(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="voice-config-restore-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.config = self.base / "config.xml"
        self.config.write_bytes(OLD)
        self.config.chmod(0o640)
        self.runtime = self.base / "runtime-v2"
        self.runtime.mkdir()
        (self.runtime / "dvtws.args").write_text("--port=989\n")
        self.journal_dir = self.base / "journal"
        self.journal_dir.mkdir(mode=0o700)
        self.backup = self.journal_dir / "previous"
        capture_previous(self.config, self.runtime, self.backup)
        evidence = bound_resource_fingerprints(self.backup)
        self.previous = {**evidence, "engine": "d" * 64,
                         "firewall": "e" * 64, "supervisor": "f" * 64}
        self.stage = self.journal_dir / "stage"
        self.image = self.journal_dir / "image"
        prepare_restore_stage(self.backup, self.stage, self.previous)
        prepare_installable_restore(self.stage, self.image, self.previous)
        self.journal = VoiceCutoverJournal(self.journal_dir)
        self.proof = {"saved_xml_sha256": hashlib.sha256(NEW).hexdigest(),
                      "merged_sha256": "a" * 64,
                      "native_argv_sha256": "b" * 64}
        self.original_inode = self.config.stat().st_ino
        self.original_dev = self.config.stat().st_dev
        self.owner = (os.geteuid(), os.getegid())

    def begin(self):
        self.journal.begin_bound(self.previous, self.proof, fixture.fixture())
        self.journal.mark_mutating()

    def call(self, **kwargs):
        return config_restorer.restore_previous_config_in_place(
            self.config, self.image, self.backup, self.journal,
            require_lifecycle_owner=kwargs.get("require_lifecycle_owner", lambda: None),
            expected_owner=kwargs.get("expected_owner", self.owner),
        )

    def test_restores_original_bytes_mode_and_same_locked_inode(self):
        self.begin()
        self.config.write_bytes(NEW)
        self.config.chmod(0o600)
        result = self.call()
        self.assertEqual(result, "previous-config-restored")
        self.assertEqual(self.config.read_bytes(), OLD)
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o640)
        self.assertEqual((self.config.stat().st_dev, self.config.stat().st_ino),
                         (self.original_dev, self.original_inode))
        self.assertEqual(self.journal.read()["phase"], "mutating")
        self.assertEqual(self.call(), "already-previous")
        self.assertEqual((self.stage / "config/config.xml").read_bytes(), OLD)
        self.assertEqual((self.image / "config.xml").read_bytes(), OLD)
        self.assertEqual((self.backup / "config/config.xml").read_bytes(), OLD)

    def test_foreign_config_not_overwritten(self):
        self.begin()
        changed = b"<opnsense><foreign>independent edit</foreign></opnsense>"
        self.config.write_bytes(changed)
        with self.assertRaisesRegex(
            config_restorer.VoiceConfigRestoreError, "foreign Config"
        ):
            self.call()
        self.assertEqual(self.config.read_bytes(), changed)
        self.assertEqual(self.journal.read()["phase"], "mutating")

    def test_no_mutating_intent_no_restore(self):
        self.config.write_bytes(NEW)
        with self.assertRaisesRegex(
            config_restorer.VoiceConfigRestoreError, "mutating"
        ):
            self.call()
        self.journal.begin_bound(self.previous, self.proof, fixture.fixture())
        with self.assertRaisesRegex(
            config_restorer.VoiceConfigRestoreError, "mutating"
        ):
            self.call()
        self.journal.mark_mutating()
        self.journal.commit()
        with self.assertRaisesRegex(
            config_restorer.VoiceConfigRestoreError, "mutating"
        ):
            self.call()
        self.assertEqual(self.config.read_bytes(), NEW)

    def test_busy_real_config_flock_refuses_without_mutation(self):
        self.begin()
        self.config.write_bytes(NEW)
        with self.config.open("r+b") as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(
                config_restorer.VoiceConfigRestoreError, "locked by another"
            ):
                self.call()
            self.assertEqual(self.config.read_bytes(), NEW)
        self.assertEqual(self.call(), "previous-config-restored")

    def test_linked_config_and_owner_drift_are_rejected(self):
        self.begin()
        self.config.write_bytes(NEW)
        with self.assertRaisesRegex(
            config_restorer.VoiceConfigRestoreError, "owner"
        ):
            self.call(expected_owner=(self.owner[0]+10000, self.owner[1]))
        self.assertEqual(self.config.read_bytes(), NEW)
        foreign = self.base / "foreign.xml"
        foreign.write_bytes(b"do not follow")
        self.config.unlink()
        self.config.symlink_to(foreign)
        with self.assertRaises(OSError):
            self.call()
        self.assertEqual(foreign.read_bytes(), b"do not follow")

    def test_tampered_image_refuses_before_live_truncate(self):
        self.begin()
        self.config.write_bytes(NEW)
        (self.image / "config.xml").write_bytes(b"untrusted image")
        with self.assertRaises(Exception):
            self.call()
        self.assertEqual(self.config.read_bytes(), NEW)

    def test_write_failure_keeps_journal_and_sealed_backup(self):
        self.begin()
        self.config.write_bytes(NEW)
        def interrupted(fd, block):
            os.write(fd, block[:7])
            raise OSError("injected interrupted Config write")
        with patch.object(config_restorer, "_write_all", side_effect=interrupted):
            with self.assertRaisesRegex(OSError, "interrupted Config write"):
                self.call()
        self.assertEqual(self.journal.read()["phase"], "mutating")
        self.assertNotEqual(self.config.read_bytes(), OLD)
        self.assertEqual((self.backup / "config/config.xml").read_bytes(), OLD)
        self.assertEqual((self.image / "config.xml").read_bytes(), OLD)


if __name__ == "__main__":
    unittest.main(verbosity=2)
