#!/usr/bin/env python3
"""Real GUI XML + managed IPSET + generator argv -> native schema-4 PREPARED."""
from __future__ import annotations

import fcntl
import importlib.util
import os
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"))
from voice_native_saved_release_prepare import (
    prepare_saved_release_forward_intent, SavedReleasePrepareError,
)
from voice_cutover_guard import check_pending
from voice_handoff_preflight import build_runtime_handoff, _publish_runtime_handoff

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / path)
    assert spec and spec.loader
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

old = load("test-voice-native-forward-prepare.py", "saved_stage_previous_fixture")
bridge = load("test-voice-generator-interop.py", "saved_stage_generator_fixture")


class SavedReleaseBridgeTests(unittest.TestCase):
    def setUp(self):
        self.previous = old.NativeForwardPrepareTests()
        self.previous.setUp()
        self.addCleanup(self.previous.doCleanups)
        self.fx = self.previous.fx
        self.source = self.fx.root / "saved-source"
        self.source.mkdir()
        self.xml, self.managed = bridge.fixtures.write_fixture(self.source)
        tree = ET.parse(self.xml)
        general = tree.getroot().find("./OPNsense/Zapret/general")
        ET.SubElement(general, "enabled").text = "1"
        tree.write(self.xml, encoding="utf-8")
        self.ordinary = self.source / "ordinary.conf"
        self.ordinary.write_text(bridge.ORDINARY)
        self.bundle = bridge.stage.compile_bundle(
            self.xml, self.managed, bridge.ACTIVE_ROOT,
            "vtnet1", 19000, 19010, 989, self.ordinary,
        )
        self.release = self.source / "release"
        bridge.stage.stage_bundle(self.release, self.bundle)
        args = bridge.generate_native_argv(
            self.source / "generator", self.bundle["traffic.conf"],
        )
        self.fx.argv.write_text(args, encoding="utf-8")
        self.ports = self.source / "ports"
        self.tcp, self.udp = bridge.extract_real_ordinary_ports(
            self.ports, bridge.ORDINARY,
        )
        self.tcp_file, self.udp_file = self.ports / "ordinary.tcp", self.ports / "ordinary.udp"
        # Emulate the exact final orchestrator.sh output, including its
        # generator argv and two independently verified handoff seals.
        (self.release / "dvtws.args").write_text(args, encoding="utf-8")
        manifest, proof = build_runtime_handoff(
            self.release, self.release / "dvtws.args", self.ordinary,
            self.tcp_file, self.udp_file, self.xml,
        )
        _publish_runtime_handoff(self.release, manifest, proof)

    def prepare(self, locked=True):
        fd = os.open(self.previous.live_config, os.O_RDWR)
        try:
            if locked:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return prepare_saved_release_forward_intent(
                release_dir=self.release, managed_source=self.managed,
                ordinary_source=self.ordinary, tcp_ports=self.tcp_file,
                udp_ports=self.udp_file, physical_wan="vtnet1",
                divert_port=989, source_config=self.xml,
                source_runtime=self.fx.candidate,
                journal=self.fx.whole, ledger=self.fx.ipfw,
                previous_backup=self.fx.backup,
                process_evidence=self.fx.process,
                security_evidence=self.fx.policy,
                previous_observer=self.previous.observer,
                config_path=self.previous.live_config,
                active_runtime=self.previous.live_runtime,
                expected_scripts=old.src.fixture.SCRIPTS,
                ipfw_adapter=self.previous.adapter,
                config_fd=fd, config_owner=(os.geteuid(), os.getegid()),
                require_lifecycle_owner=lambda: self.previous.lock_hits.append("FD9"),
            )
        finally:
            os.close(fd)

    def test_real_gui_and_generator_release_prepares_five_resource_intent(self):
        old_config = self.previous.live_config.read_bytes()
        result = self.prepare()
        record = self.fx.whole.read()
        self.assertEqual("native-voice-stage-and-forward-prepared", result["state"])
        self.assertEqual("prepared", record["phase"])
        self.assertEqual(4, record["schema"])
        self.assertEqual(self.xml.read_bytes(),
                         (self.fx.whole.directory / "forward-candidate" / "config.xml").read_bytes())
        self.assertEqual(old_config, self.previous.live_config.read_bytes())
        self.assertIsNone(self.fx.ipfw.pending())
        self.assertFalse(result["safe_to_enable_voice"])
        self.assertFalse(check_pending(self.fx.whole.directory,
                                       self.fx.ipfw.directory)["safe_to_mutate"])

    def test_no_config_flock_prevents_any_candidate_publication(self):
        with self.assertRaises((RuntimeError, ValueError, OSError)):
            self.prepare(locked=False)
        self.assertIsNone(self.fx.whole.read())
        self.assertFalse((self.fx.whole.directory / "forward-candidate").exists())

    def test_invalid_global_disabled_xml_refused_before_journal(self):
        tree = ET.parse(self.xml)
        tree.getroot().find("./OPNsense/Zapret/general/enabled").text = "0"
        tree.write(self.xml, encoding="utf-8")
        with self.assertRaises((RuntimeError, ValueError, OSError)):
            self.prepare()
        self.assertIsNone(self.fx.whole.read())

    def test_stale_release_and_managed_ipset_refused_before_journal(self):
        (self.release / "voice.conf").write_text("foreign")
        with self.assertRaises((RuntimeError, ValueError, OSError)):
            self.prepare()
        self.assertIsNone(self.fx.whole.read())

    def test_foreign_native_generator_argv_refused_before_journal(self):
        self.fx.argv.write_text("--port=989\n--name=foreign\n", encoding="utf-8")
        with self.assertRaises((RuntimeError, ValueError, OSError)):
            self.prepare()
        self.assertIsNone(self.fx.whole.read())

    def test_wrong_ordinary_port_extractor_refused_before_journal(self):
        self.tcp_file.write_text("80")
        with self.assertRaises((RuntimeError, ValueError, OSError)):
            self.prepare()
        self.assertIsNone(self.fx.whole.read())

    def test_partial_five_file_release_is_not_a_production_generator_result(self):
        (self.release / "handoff-proof.json").unlink()
        with self.assertRaises((RuntimeError, ValueError, OSError)):
            self.prepare()
        self.assertIsNone(self.fx.whole.read())
        self.assertFalse((self.fx.whole.directory / "forward-candidate").exists())

    def test_foreign_generator_manifest_refused_before_seed_or_journal(self):
        import json
        file = self.release / "desired-ipfw.json"
        value = json.loads(file.read_text())
        value["rule_base"] = 19001
        file.write_text(json.dumps(value))
        with self.assertRaises((RuntimeError, ValueError, OSError)):
            self.prepare()
        self.assertIsNone(self.fx.whole.read())

    def test_different_runtime_argv_refused_before_stage(self):
        (self.release / "dvtws.args").write_text("--port=989\\n--name=unrelated\\n")
        with self.assertRaises((RuntimeError, ValueError, OSError)):
            self.prepare()
        self.assertIsNone(self.fx.whole.read())

    def test_extra_foreign_generator_artifact_refused(self):
        (self.release / "unknown.conf").write_text("malicious")
        with self.assertRaises((RuntimeError, ValueError, OSError)):
            self.prepare()
        self.assertIsNone(self.fx.whole.read())


if __name__ == "__main__":
    unittest.main(verbosity=2)
