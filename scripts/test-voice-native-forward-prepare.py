#!/usr/bin/env python3
"""Source-only schema-4 journal fixture for historical forward/rollback tests.

The retired native five-resource PREPARED executor is not a product entrypoint.
Downstream tests for stop, IPFW, supervisor and Config still need a genuine,
durable PREPARED record. Build it with the existing VoiceCutoverJournal API
rather than importing a second obsolete production coordinator.
"""
from __future__ import annotations

import fcntl
import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

from voice_native_recovery_quiescence import _locked_config


def fixture(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


src = fixture("test-voice-cutover-runtime-bound-intent.py", "forward_schema4_source")


class NativeForwardPrepareTests(unittest.TestCase):
    """Fixture-only: intentionally has no test_* methods.

    Keep its original class name for existing transitive test-fixture imports.
    This does not register a CLI or ship a new service-side coordinator.
    """

    def setUp(self):
        self.fx = src.RuntimeBoundCutoverTests()
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.live_config = self.fx.root / "config.xml"
        self.live_runtime = self.fx.root / "runtime"
        self.manifest = {
            "rule_base": 19000, "rule_max": 19010,
            "rules": {
                19000: [
                    "divert", "989", "udp", "from", "any", "to",
                    "table(zapret2_voice_telegram)", "out", "not",
                    "diverted", "not", "sockarg", "xmit", "vtnet1",
                ],
            },
            "tables": {"zapret2_voice_telegram": ["91.108.13.10"]},
        }
        self.proof = {
            **self.fx.proof,
            "schema": 1, "state": "preflight-only",
            "activation_authorized": False,
            "enabled_services": ["telegram"],
            "rule_base": 19000, "rule_max": 19010,
            "rule_count": 1, "table_count": 1,
        }

    def prepare(self, *, take_lock=True):
        fd = os.open(self.live_config, os.O_RDWR)
        try:
            if take_lock:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            _locked_config(
                self.live_config, fd, (os.geteuid(), os.getegid())
            )
            self.fx.whole.begin_runtime_bound(
                self.fx.prior, self.proof, self.manifest,
                self.fx.policy, self.fx.backup, self.fx.process,
                src.fixture.SCRIPTS,
                staged_config=self.fx.stage_config,
                candidate_runtime=self.fx.candidate,
            )
            return self.fx.whole.read()
        finally:
            os.close(fd)


if __name__ == "__main__":
    unittest.main(verbosity=2)
