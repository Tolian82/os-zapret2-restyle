#!/usr/bin/env python3
"""Stage-3 production PREPARED route: real sealed inputs, no live mutations."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"))
from voice_native_apply_route import main
from voice_native_forward_stage_prepare import (
    sealed_prepared_handoff, NativeVoiceStagePrepareError,
)
from voice_firewall_ledger import canonical_manifest
from voice_cutover_journal import VoiceCutoverJournal

spec = importlib.util.spec_from_file_location(
    "voice_schema4_apply_fixture",
    ROOT / "scripts/test-voice-cutover-runtime-bound-intent.py",
)
assert spec and spec.loader
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)

DESIRED = {
    "rule_base": 19000, "rule_max": 19010,
    "rules": {
        19000: ["divert", "989", "udp", "from", "any", "to",
                "table(zapret2_voice_telegram)", "out", "not",
                "diverted", "not", "sockarg", "xmit", "vtnet1"],
    },
    "tables": {"zapret2_voice_telegram": ["91.108.13.10"]},
}


class NativePreparedApplyRouteTests(unittest.TestCase):
    def setUp(self):
        self.fx = source.RuntimeBoundCutoverTests()
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.stage = self.fx.whole.directory / "forward-candidate"
        self.stage.mkdir(mode=0o700)
        shutil.copy2(self.fx.stage_config, self.stage / "config.xml")
        shutil.copytree(self.fx.candidate, self.stage / "runtime")
        (self.stage / "desired-ipfw.json").write_text(
            json.dumps(canonical_manifest(DESIRED), sort_keys=True),
        )
        (self.stage / "desired-ipfw.json").chmod(0o600)

    def seal(self):
        self.fx.whole.begin_runtime_bound(
            self.fx.prior, self.fx.proof, DESIRED,
            self.fx.policy, self.fx.backup, self.fx.process,
            source.fixture.SCRIPTS,
            staged_config=self.fx.stage_config, candidate_runtime=self.fx.candidate,
        )

    def test_real_schema4_prepared_inputs_are_bound_without_mutation(self):
        self.seal()
        before = self.fx.whole.read()
        self.assertEqual(sealed_prepared_handoff(self.fx.whole, self.stage), DESIRED)
        self.assertEqual(self.fx.whole.read(), before)
        self.assertIsNone(self.fx.ipfw.pending())

    def test_unprepared_or_mutating_record_cannot_cross_operator_route(self):
        with self.assertRaises((RuntimeError, OSError, ValueError)):
            sealed_prepared_handoff(self.fx.whole, self.stage)
        self.seal()
        self.fx.whole.mark_mutating()
        with self.assertRaises((RuntimeError, OSError, ValueError)):
            sealed_prepared_handoff(self.fx.whole, self.stage)

    def test_tampered_manifest_xml_argv_and_unknown_files_refused(self):
        self.seal()
        paths = [
            self.stage / "desired-ipfw.json",
            self.stage / "config.xml",
            self.stage / "runtime" / "dvtws.args",
        ]
        for path in paths:
            with self.subTest(path=path.name):
                old = path.read_bytes()
                path.write_bytes(b"foreign")
                with self.assertRaises((RuntimeError, OSError, ValueError)):
                    sealed_prepared_handoff(self.fx.whole, self.stage)
                path.write_bytes(old)
        (self.stage / "extra").touch()
        with self.assertRaises((RuntimeError, OSError, ValueError)):
            sealed_prepared_handoff(self.fx.whole, self.stage)

    def test_native_entrypoint_is_nonpublic_and_refuses_unattested_result(self):
        # Even the direct module CLI must not activate the old private owner.
        with patch("voice_native_apply_route.execute_operator_prepared") as executor:
            self.assertEqual(main(["execute-prepared"]), 69)
            self.assertEqual(main([]), 64)
            executor.assert_not_called()

    def test_retired_private_forward_apply_has_no_service_or_configd_route(self):
        sh = (ROOT / "src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
        cfg = (ROOT / "src/opnsense/service/conf/actions.d/actions_zapret.conf").read_text()
        self.assertNotIn("native-voice-apply-prepared)", sh)
        self.assertNotIn("native_voice_apply_prepared_service()", sh)
        self.assertNotIn("native-voice-prepare-apply-draft)", sh)
        self.assertNotIn("prepare-from-draft-and-apply", sh)
        self.assertNotIn("native-voice-apply-prepared", cfg)
        self.assertNotIn("native-voice-prepare-apply-draft", cfg)
        self.assertIn("shared_apply_run_service voice", sh)
        self.assertIn("[shared_apply]", cfg)
        self.assertNotIn("[voice_apply]", cfg)
        pkg = (ROOT / "scripts/build-pkg.sh").read_text()
        stage = (ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend/voice_native_forward_stage_prepare.py").read_text()
        self.assertIn('rm "${APPLY_ROUTE}"', pkg)
        self.assertIn('rm "${PREPARE_ROUTE}"', pkg)
        self.assertIn("def sealed_prepared_handoff(", stage)
        self.assertNotIn("from voice_native_apply_route import", stage)

if __name__ == "__main__":
    unittest.main(verbosity=2)
