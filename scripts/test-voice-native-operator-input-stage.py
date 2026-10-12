#!/usr/bin/env python3
"""Detached operator input must come from actual native release and one Config FD."""
from __future__ import annotations

import fcntl
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"))
from voice_native_operator_input_stage import (
    stage_native_operator_input, PREFIX, FILE_NAMES, DIR_NAMES,
)
from voice_native_recovery_quiescence import _locked_config
from voice_native_saved_release_prepare import qualify_saved_voice_release


def load_fixture():
    file = ROOT / "scripts/test-voice-native-saved-release-prepare.py"
    spec = importlib.util.spec_from_file_location("voice_operator_fixture", file)
    assert spec is not None and spec.loader is not None
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


class OperatorInputStageTests(unittest.TestCase):
    def setUp(self):
        fixture_type = load_fixture().SavedReleaseBridgeTests
        self.fixture = fixture_type()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.live = self.fixture.previous.live_config
        shutil.copyfile(self.fixture.xml, self.live)
        self.old_bytes = self.fixture.previous.live_runtime.joinpath(
            "dvtws.args"
        ).read_bytes() if (
            self.fixture.previous.live_runtime / "dvtws.args"
        ).exists() else b""
        self.old_sha = self.live.read_bytes()
        self.stage = self.fixture.source / "ordinary-orchestrator-release"
        self.stage.mkdir()
        shutil.copytree(self.fixture.release, self.stage / "voice-native-candidate")
        shutil.copytree(self.fixture.managed, self.stage / "managed")
        shutil.copyfile(self.fixture.ordinary, self.stage / "traffic-user.conf")
        shutil.copyfile(self.fixture.tcp_file, self.stage / "tcp-ports.txt")
        shutil.copyfile(self.fixture.udp_file, self.stage / "udp-ports.txt")
        shutil.copyfile(self.fixture.ordinary, self.stage / "traffic.conf")
        (self.stage / "dvtws.args").write_text("--port=989\n--name=ordinary\n")
        self.private = self.fixture.source / "operator-private"
        self.private.mkdir(mode=0o700)
        self.output = self.private / "voice-operator-input"
        self.hits = 0

    def publish(self, *, locked=True):
        fd = os.open(self.live, os.O_RDWR)
        try:
            if locked:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            def owner():
                self.hits += 1
            return stage_native_operator_input(
                config_path=self.live, staged_release=self.stage,
                destination=self.output, physical_wan="vtnet1",
                divert_port=989, config_fd=fd,
                config_owner=(os.geteuid(), os.getegid()),
                require_lifecycle_owner=owner,
            )
        finally:
            os.close(fd)

    def test_real_eight_file_handoff_and_inert_runtime(self):
        result = self.publish()
        self.assertEqual("native-voice-detached-operator-input-published",
                         result["state"])
        self.assertFalse(result["safe_to_enable_voice"])
        self.assertFalse(result["public_voice_apply"])
        self.assertGreaterEqual(self.hits, 3)
        self.assertEqual(set(FILE_NAMES + DIR_NAMES),
                         {p.name for p in self.output.iterdir()})
        self.assertEqual(self.old_sha, self.live.read_bytes())
        self.assertEqual(self.old_bytes, (
            self.fixture.previous.live_runtime / "dvtws.args"
        ).read_bytes() if (
            self.fixture.previous.live_runtime / "dvtws.args"
        ).exists() else b"")
        self.assertEqual(
            (self.fixture.release / "dvtws.args").read_bytes(),
            (self.output / "runtime/dvtws.args").read_bytes(),
        )
        self.assertEqual(
            (self.fixture.release / "traffic.conf").read_bytes(),
            (self.output / "runtime/traffic.conf").read_bytes(),
        )
        self.assertEqual(
            self.fixture.ordinary.read_bytes(),
            (self.output / "user-traffic.conf").read_bytes(),
        )
        self.assertEqual(
            self.fixture.managed.joinpath("ipset-telegram.txt").read_bytes(),
            self.output.joinpath("managed/ipset-telegram.txt").read_bytes(),
        )
        self.assertEqual(0o700, self.output.stat().st_mode & 0o777)
        self.assertFalse((self.output / "runtime/voice-native-candidate").exists())
        self.assertEqual([], list(self.private.glob(PREFIX + "*")))
        # This is the unchanged production verifier, not a mocked seal.
        fd = os.open(self.live, os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            manifest, proof = qualify_saved_voice_release(
                release_dir=self.output / "voice-native-candidate",
                managed_source=self.output / "managed",
                ordinary_source=self.output / "user-traffic.conf",
                tcp_ports=self.output / "tcp-ports.txt",
                udp_ports=self.output / "udp-ports.txt",
                physical_wan="vtnet1", divert_port=989,
                source_config=self.output / "config.xml",
                source_runtime=self.output / "runtime",
                config_path=self.live,
                active_runtime=Path("/usr/local/etc/zapret2/runtime-v2"),
                config_fd=fd,
                config_owner=(os.geteuid(), os.getegid()),
                require_lifecycle_owner=lambda: None,
            )
            self.assertTrue(proof["enabled_services"])
            self.assertTrue(manifest["tables"])
        finally:
            os.close(fd)

    def test_missing_config_flock_refuses_before_publishing(self):
        with self.assertRaises((RuntimeError, ValueError, OSError)):
            self.publish(locked=False)
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.private.iterdir()))

    def test_stale_generated_proof_never_publishes(self):
        (self.stage / "voice-native-candidate/handoff-proof.json").write_text("{}")
        with self.assertRaises((RuntimeError, ValueError, OSError)):
            self.publish()
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.private.iterdir()))
        self.assertEqual(self.old_sha, self.live.read_bytes())

    def test_symlinked_release_child_cannot_be_adopted(self):
        (self.stage / "traffic-user.conf").unlink()
        (self.stage / "traffic-user.conf").symlink_to(self.fixture.ordinary)
        with self.assertRaises((RuntimeError, ValueError, OSError)):
            self.publish()
        self.assertFalse(self.output.exists())
        self.assertEqual(self.old_sha, self.live.read_bytes())

    def test_unknown_previous_stage_blocks_without_overwrite(self):
        self.private.joinpath(PREFIX + "orphan").mkdir()
        with self.assertRaises((RuntimeError, ValueError, OSError)):
            self.publish()
        self.assertFalse(self.output.exists())

    def test_existing_publication_cannot_be_overwritten(self):
        self.publish()
        digest = (self.output / "config.xml").read_bytes()
        with self.assertRaises((RuntimeError, ValueError, OSError)):
            self.publish()
        self.assertEqual(digest, (self.output / "config.xml").read_bytes())

    def test_power_cut_before_publish_keeps_private_partial(self):
        with patch("voice_native_operator_input_stage.qualify_saved_voice_release",
                   side_effect=RuntimeError("simulated power loss")):
            with self.assertRaises(RuntimeError):
                self.publish()
        self.assertFalse(self.output.exists())
        self.assertEqual(1, len(list(self.private.glob(PREFIX + "*"))))
        with self.assertRaises((RuntimeError, ValueError, OSError)):
            self.publish()


if __name__ == "__main__":
    unittest.main(verbosity=2)
