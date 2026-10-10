#!/usr/bin/env python3
"""Real staged Voice release -> one dvtws2 argv -> owned IPFW manifest.

Exercises the actual compiler, generator.sh and ports.sh on private
temporary files. Never invokes live configd, dvtws2 or kernel IPFW.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

spec = importlib.util.spec_from_file_location(
    "voice_generator_bridge", ROOT / "scripts/test-voice-generator-interop.py"
)
assert spec and spec.loader
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)

from voice_firewall_ledger import decode_manifest, fingerprint


class ProductionHandoffTests(unittest.TestCase):
    def build(self, root: Path, on: bool, big_config: bool = False):
        bundle = bridge.GeneratorInteropTests().compile(root, enabled=on)
        if big_config:
            # OPNsense Config includes many unrelated subsystems and may be
            # larger than the staged dvtws2/Voice artifacts.
            xml_source = root / "config.xml"
            with xml_source.open("ab") as stream:
                stream.write(b"\n<!--" + b"x" * (4 * 1048576) + b"-->\n")
            bundle = bridge.stage.compile_bundle(
                xml_source, root / "managed", bridge.ACTIVE_ROOT,
                "vtnet1", 19000, 19010, 989, root / "ordinary.resolved.conf",
            )
        stage = root / "candidate"
        bridge.stage.stage_bundle(stage, bundle)
        args = bridge.generate_native_argv(root / "engine", bundle["traffic.conf"])
        (stage / "dvtws.args").write_text(args, encoding="utf-8")
        source = root / "ordinary.resolved.conf"
        tcp, udp = bridge.extract_real_ordinary_ports(root / "ports", source.read_text())
        tcp_file, udp_file = root / "ports-tcp", root / "ports-udp"
        tcp_file.write_text(tcp + "\n")
        udp_file.write_text(udp + "\n")
        return stage, stage / "dvtws.args", source, tcp_file, udp_file, root / "config.xml"

    def call(self, files):
        return subprocess.run(
            [sys.executable, str(BACKEND / "voice_handoff_preflight.py"),
             *map(str, files)],
            capture_output=True, text=True, timeout=30, check=False,
        )

    def test_one_engine_native_on_candidate_and_destination_scoped_ipfw(self):
        with tempfile.TemporaryDirectory() as directory:
            files = self.build(Path(directory), True)
            result = self.call(files)
            self.assertEqual(0, result.returncode, result.stderr)
            manifest = json.loads((files[0] / "desired-ipfw.json").read_text())
            proof = json.loads((files[0] / "handoff-proof.json").read_text())
            decoded = decode_manifest(manifest)
            self.assertEqual([19000, 19001, 19002], sorted(decoded["rules"]))
            self.assertEqual("table(zapret2_voice_telegram)", decoded["rules"][19000][6])
            self.assertEqual("tcp", decoded["rules"][19001][2])
            self.assertEqual("udp", decoded["rules"][19002][2])
            self.assertEqual(["91.108.0.0/16", "91.108.13.10"],
                             decoded["tables"]["zapret2_voice_telegram"])
            self.assertEqual(["telegram"], proof["enabled_services"])
            self.assertEqual(fingerprint(manifest), proof["desired_ipfw_sha256"])
            self.assertFalse(proof["activation_authorized"])
            self.assertEqual(1, files[1].read_text().count("--port=989\n"))
            self.assertEqual(0o600, (files[0] / "desired-ipfw.json").stat().st_mode & 0o777)
            self.assertNotEqual(0, self.call(files).returncode)  # refuse overwrite

    def test_all_off_produces_ordinary_rules_without_voice_tables(self):
        with tempfile.TemporaryDirectory() as directory:
            files = self.build(Path(directory), False)
            self.assertEqual(0, self.call(files).returncode)
            state = decode_manifest(json.loads(
                (files[0] / "desired-ipfw.json").read_text()
            ))
            self.assertEqual([19000, 19001], sorted(state["rules"]))
            self.assertEqual({}, state["tables"])

    def test_large_real_opnsense_config_is_accepted_and_stream_hashed(self):
        with tempfile.TemporaryDirectory() as directory:
            files = self.build(Path(directory), False, big_config=True)
            self.assertGreater(files[5].stat().st_size, 4 * 1048576)
            result = self.call(files)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue((files[0] / "desired-ipfw.json").is_file())

    def test_tampering_before_handoff_never_publishes_desired_ipfw(self):
        for kind in ("ports", "argv", "xml", "targets"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                files = self.build(Path(directory), True)
                if kind == "ports":
                    files[3].write_text("80\n")
                elif kind == "argv":
                    files[1].write_text(files[1].read_text().replace("--port=989", "--port=990"))
                elif kind == "xml":
                    with files[5].open("ab") as f:
                        f.write(b"<!-- concurrent edit -->")
                else:
                    metadata = files[0] / "metadata.json"
                    record = json.loads(metadata.read_text())
                    record["ipset_sha256"]["telegram"] = "0" * 64
                    metadata.write_text(json.dumps(record))
                result = self.call(files)
                self.assertNotEqual(0, result.returncode, kind)
                self.assertFalse((files[0] / "desired-ipfw.json").exists(), kind)
                self.assertFalse((files[0] / "handoff-proof.json").exists(), kind)

    def test_real_orchestrator_wires_both_generators_before_release_ready(self):
        text = (BACKEND / "orchestrator.sh").read_text()
        source = text[text.index("orchestrator_build_release()"):
                      text.index("orchestrator_cleanup_runtime()")]
        self.assertIn("native_args", source)
        self.assertIn("voice-native-candidate", source)
        self.assertIn("voice_handoff_preflight.py", source)
        self.assertLess(source.index("generator_build_args_mapped"),
                        source.index("voice_handoff_preflight.py"))
        self.assertIn("config_voice_staged_only_guard || {", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
