#!/usr/bin/env python3
"""Production Voice rollback byte staging under the same FD9 service entry.

Tests create real sealed snapshots and both real durable journals in a
private filesystem. They never touch live OPNsense Config, engine or IPFW.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))
from voice_cutover_backup import capture_previous, bound_resource_fingerprints
from voice_cutover_journal import VoiceCutoverJournal
from voice_firewall_ledger import VoiceOwnershipStore
import voice_cutover_restore_prepare as restore

spec = importlib.util.spec_from_file_location(
    "native_restore_fixtures", ROOT / "scripts/test-voice-firewall-transaction.py"
)
assert spec and spec.loader
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)


class RealNativePreviousRestoreStage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="voice-native-restore-")
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.base = base
        self.config = base / "config.xml"
        self.config.write_text("<opnsense><service>before</service></opnsense>")
        self.runtime = base / "active"
        self.runtime.mkdir()
        self.runtime.chmod(0o750)
        (self.runtime / "dvtws.args").write_text("--port=989\n--filter-tcp=443\n")
        (self.runtime / "dvtws.args").chmod(0o640)
        (self.runtime / "traffic.conf").write_text("--filter-tcp=443\n")
        self.whole_root = base / "whole"
        self.whole_root.mkdir(mode=0o700)
        self.ledger_root = base / "ledger"
        self.ledger_root.mkdir(mode=0o700)
        self.backup = self.whole_root / "previous"
        capture_previous(self.config, self.runtime, self.backup)
        self.evidence = bound_resource_fingerprints(self.backup)
        self.firewall = VoiceOwnershipStore(self.ledger_root)
        self.old = f.fixture()
        self.firewall.seed(self.old)
        self.journal = VoiceCutoverJournal(self.whole_root)
        self.proof = {
            "saved_xml_sha256": "a" * 64,
            "merged_sha256": "b" * 64,
            "native_argv_sha256": "c" * 64,
        }
        self.previous = {
            **self.evidence,
            "engine": "d" * 64,
            "firewall": "e" * 64,
            "supervisor": "f" * 64,
        }
        self.out = self.whole_root / "restore-staged"

    def begin(self):
        self.journal.begin_bound(self.previous, self.proof, self.old)
        self.journal.mark_mutating()

    def test_mutating_rollback_prepares_exact_real_config_and_runtime(self):
        self.begin()
        before = self.config.read_bytes()
        result = restore.prepare_recovery(
            self.backup, self.out, self.journal, self.firewall
        )
        self.assertFalse(result["activation_authorized"])
        self.assertEqual("staged-only", result["state"])
        self.assertEqual(self.evidence, result["previous"])
        self.assertEqual("prepared-only", result["install_image"])
        image = self.whole_root / "restore-install-image"
        self.assertEqual(0o700, image.stat().st_mode & 0o777)
        self.assertEqual(0o750, (image / "runtime").stat().st_mode & 0o777)
        self.assertEqual(0o640, (image / "runtime/dvtws.args").stat().st_mode & 0o777)
        self.assertEqual(before, (image / "config.xml").read_bytes())
        self.assertEqual(before, (self.out / "config/config.xml").read_bytes())
        self.assertEqual((self.runtime / "dvtws.args").read_bytes(),
                         (self.out / "runtime/dvtws.args").read_bytes())
        self.assertEqual("mutating", self.journal.read()["phase"])
        self.assertEqual(self.old, self.firewall.owned())
        self.assertEqual(before, self.config.read_bytes())
        self.assertEqual(0o700, self.out.stat().st_mode & 0o777)
        with self.assertRaisesRegex(Exception, "already exists"):
            restore.prepare_recovery(
                self.backup, self.out, self.journal, self.firewall
            )

    def test_missing_intent_or_prepared_only_cannot_stage(self):
        with self.assertRaisesRegex(restore.NativeRestorePreparationError, "mutating"):
            restore.prepare_recovery(
                self.backup, self.out, self.journal, self.firewall
            )
        self.journal.begin_bound(self.previous, self.proof, self.old)
        with self.assertRaisesRegex(restore.NativeRestorePreparationError, "mutating"):
            restore.prepare_recovery(
                self.backup, self.out, self.journal, self.firewall
            )
        self.assertFalse(self.out.exists())
        self.assertFalse((self.whole_root / "restore-install-image").exists())

    def test_committed_intent_cannot_stage_old_config(self):
        self.begin()
        self.journal.commit()
        with self.assertRaisesRegex(restore.NativeRestorePreparationError, "mutating"):
            restore.prepare_recovery(
                self.backup, self.out, self.journal, self.firewall
            )
        self.assertFalse(self.out.exists())

    def test_tampered_previous_backup_denies_restore_before_stage(self):
        self.begin()
        (self.backup / "config/config.xml").write_text("<malicious/>")
        with self.assertRaises(Exception):
            restore.prepare_recovery(
                self.backup, self.out, self.journal, self.firewall
            )
        self.assertFalse(self.out.exists())
        self.assertEqual("mutating", self.journal.read()["phase"])

    def test_unowned_ipfw_denies_restore_stage(self):
        self.begin()
        empty_root = self.base / "not-owned"
        empty_root.mkdir(mode=0o700)
        with self.assertRaisesRegex(restore.NativeRestorePreparationError, "previous ownership"):
            restore.prepare_recovery(
                self.backup, self.out, self.journal,
                VoiceOwnershipStore(empty_root)
            )
        self.assertFalse(self.out.exists())

    def test_installed_service_calls_native_action_under_fd9_without_legacy_guard(self):
        source = (BACKEND.parent / "zapret_service.sh").read_text()
        self.assertIn("native_voice_restore_stage_service()", source)
        self.assertIn("voice_cutover_restore_prepare.py", source)
        self.assertIn("native-voice-restore-stage)", source)
        self.assertIn("native-voice-checkpoint|native-voice-restore-stage", source)
        self.assertIn("service_with_lifecycle_lock", source)
        # Existing old service remains blocked on a pending cutover; only
        # this explicitly scoped recovery preparation may run under FD9.
        guard = source[source.index("service_with_lifecycle_lock()"):
                       source.index("case \"${1:-}\" in", source.index("service_with_lifecycle_lock()"))]
        self.assertNotIn("native-voice-restore-stage|", guard)


if __name__ == "__main__":
    unittest.main(verbosity=2)
