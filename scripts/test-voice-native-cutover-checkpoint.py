#!/usr/bin/env python3
"""Exercise the production previous-state Voice snapshot under FD9 service path.

Only private filesystem and injected IPFW. No OPNsense Config, kernel changes,
real PID operations or host /var/db directories.
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
from voice_cutover_backup import inspect_previous, bound_resource_fingerprints
from voice_cutover_guard import check_pending
import voice_cutover_checkpoint as checkpoint
from voice_firewall_transaction import VoiceFirewallError

spec = importlib.util.spec_from_file_location(
    "firewall_fixtures", ROOT / "scripts/test-voice-firewall-transaction.py"
)
assert spec and spec.loader
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)


class NativeCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="voice-native-previous-")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.config = self.base / "config.xml"
        self.config.write_text("<opnsense><OPNsense><Zapret/></OPNsense></opnsense>")
        self.runtime = self.base / "runtime"
        self.runtime.mkdir()
        (self.runtime / "dvtws.args").write_text("--port=989\n--filter-tcp=443\n")
        (self.runtime / "traffic.conf").write_text("--filter-tcp=443\n")
        self.private = self.base / "voice-state"
        self.ledger = self.base / "voice-ipfw"
        self.desired = fixtures.fixture()
        self.adapter = fixtures.FakeIPFW(self.desired["rules"], self.desired["tables"])
        self.samples = []

    def take(self, *, engine=None, source=None, adapter=None):
        def engine_ok():
            self.samples.append("engine")
            if engine:
                engine()

        def source_ok():
            self.samples.append("source")
            if source:
                source()

        return checkpoint.checkpoint(
            self.config, self.runtime, self.private, self.ledger,
            adapter or self.adapter, self.desired, engine_ok, source_ok
        )

    def test_sealed_real_previous_config_and_runtime_without_ipfw_changes(self):
        evidence = self.take()
        saved = self.private / "previous"
        manifest = inspect_previous(saved)
        self.assertEqual(manifest["config"]["sha256"], evidence["config"])
        self.assertEqual(bound_resource_fingerprints(saved), evidence)
        self.assertIn("dvtws.args", manifest["runtime"])
        self.assertEqual(["engine", "source", "source", "engine"], self.samples)
        self.assertEqual([], self.adapter.ops)
        self.assertFalse(self.ledger.exists(), "snapshot does not adopt IPFW")
        self.assertEqual("clear", check_pending(self.private, self.ledger)["state"],
                         "a snapshot alone must NOT lock the normal OFF lifecycle")

    def test_existing_snapshot_must_not_be_replaced(self):
        first = self.take()
        self.config.write_text("<opnsense>different generation</opnsense>")
        with self.assertRaisesRegex(checkpoint.VoiceCheckpointError, "existing"):
            self.take()
        self.assertEqual(first, bound_resource_fingerprints(self.private / "previous"))
        self.assertEqual([], self.adapter.ops)

    def test_foreign_ipfw_denies_snapshot_before_any_file_created(self):
        foreign = dict(self.desired["rules"])
        foreign[19005] = ["allow", "ip", "from", "any", "to", "any"]
        kernel = fixtures.FakeIPFW(foreign, self.desired["tables"])
        with self.assertRaises(VoiceFirewallError):
            self.take(adapter=kernel)
        self.assertFalse(self.private.exists())
        self.assertEqual([], kernel.ops)

    def test_process_failure_denies_before_snapshot(self):
        def fail():
            raise checkpoint.VoiceCheckpointError("engine identity not trusted")

        with self.assertRaisesRegex(checkpoint.VoiceCheckpointError, "engine identity"):
            self.take(engine=fail)
        self.assertFalse(self.private.exists())

    def test_runtime_modification_during_checkpoint_denies_final_proof(self):
        def tamper_at_final_verification():
            if self.samples.count("source") == 2:
                (self.runtime / "dvtws.args").write_text("--port=990\n")

        with self.assertRaisesRegex(Exception, "changed|snapshot|runtime"):
            self.take(source=tamper_at_final_verification)
        # Copy is retained as immutable recovery evidence: never silently
        # delete fsync'd bytes after an ambiguous generation/race.
        self.assertTrue((self.private / "previous").exists())
        self.assertEqual([], self.adapter.ops)

    def test_service_is_wired_under_real_fd9_and_seed_requires_whole_journal(self):
        service = (BACKEND.parent / "zapret_service.sh").read_text()
        runtime = (BACKEND / "voice_ipfw_runtime.py").read_text()
        self.assertIn("native_voice_checkpoint_service()", service)
        self.assertIn('"${BACKEND_DIR}/voice_cutover_checkpoint.py"', service)
        self.assertIn("native-voice-checkpoint)", service)
        self.assertIn("native-voice-checkpoint|native-voice-ipfw-seed", service)
        self.assertIn("orchestrator_runtime_is_complete", service)
        self.assertIn("native IPFW seed requires a prepared whole-service cutover", runtime)
        self.assertIn('bound_resource_fingerprints(WHOLE / "previous"', runtime)


if __name__ == "__main__":
    unittest.main(verbosity=2)
