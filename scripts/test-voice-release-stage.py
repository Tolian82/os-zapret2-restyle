#!/usr/bin/env python3
"""Stage-only Voice release regression. No router/kernel side effects."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

spec = importlib.util.spec_from_file_location("voice_release_stage", BACKEND / "voice_release_stage.py")
assert spec and spec.loader
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)

ACTIVE_ROOT = Path("/usr/local/etc/zapret2/runtime-v2")
STUN = "\n".join((
    "--filter-udp=*",
    "--filter-l7=stun",
    "--payload=stun",
    "--lua-desync=fake:blob=0x00000000000000000000000000000000:repeats=2",
))


def fixture(voice_enabled=True) -> ET.Element:
    root = ET.Element("opnsense")
    model = ET.SubElement(ET.SubElement(root, "OPNsense"), "Zapret")
    general = ET.SubElement(model, "general")
    ET.SubElement(general, "waninterface").text = "WAN"
    voice = ET.SubElement(model, "voice")
    ET.SubElement(voice, "waninterface").text = "WAN"
    telegram = ET.SubElement(voice, "telegram")
    ET.SubElement(telegram, "enabled").text = "1" if voice_enabled else "0"
    ET.SubElement(telegram, "args").text = STUN
    hostlist = ET.SubElement(model, "hostlist")
    ET.SubElement(hostlist, "telegramips").text = "91.108.0.0/16\n91.108.13.10"
    ET.SubElement(hostlist, "discordips").text = "198.51.100.0/24"
    other = ET.SubElement(root, "squid")
    ET.SubElement(other, "password").text = "SECRET_DO_NOT_LEAK"
    return root


def write_fixture(tmp: Path, root: ET.Element | None = None):
    source = tmp / "config.xml"
    ET.ElementTree(root if root is not None else fixture()).write(source, encoding="utf-8")
    managed = tmp / "managed"
    managed.mkdir()
    (managed / "ipset-telegram.txt").write_text("91.108.0.0/16\n91.108.13.10\n", encoding="utf-8")
    return source, managed


class VoiceReleaseStageTests(unittest.TestCase):
    def test_native_source_with_physical_wan_and_exact_managed_ipset(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            source, managed = write_fixture(tmp)
            bundle = stage.compile_bundle(source, managed, ACTIVE_ROOT, "vtnet1", 19000, 19010, 989)
            self.assertIn("--name=voice-telegram", bundle["voice.conf"])
            capture = json.loads(bundle["capture-plan.json"])
            meta = json.loads(bundle["metadata.json"])
            self.assertEqual("WAN", capture["logical_wan"])
            self.assertEqual("vtnet1", capture["wan"])
            self.assertEqual("vtnet1", capture["voice"][0]["argv"][-1])
            self.assertIn("table(zapret2_voice_telegram)", capture["voice"][0]["argv"])
            self.assertEqual(19001, capture["ordinary_rule_base"])
            self.assertFalse(meta["activation_authorized"])
            self.assertEqual("staged-only", meta["mode"])
            self.assertEqual(1, meta["profile_count"])
            self.assertEqual(64, len(meta["ipset_sha256"]["telegram"]))
            self.assertNotIn("SECRET_DO_NOT_LEAK", json.dumps(bundle))

    def test_all_disabled_keeps_no_voice_capture(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            source, managed = write_fixture(tmp, fixture(False))
            (managed / "ipset-telegram.txt").unlink()
            result = stage.compile_bundle(source, managed, ACTIVE_ROOT, "vtnet1", 19000, 19010, 989)
            self.assertEqual("", result["voice.conf"])
            self.assertEqual([], json.loads(result["capture-plan.json"])["voice"])

    def test_reject_stale_or_changed_managed_ipset_without_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            source, managed = write_fixture(tmp)
            target = managed / "ipset-telegram.txt"
            for text in [
                "", "91.108.0.0/16\n", "91.108.13.10\n91.108.0.0/16\n",
                "91.108.0.0/16\n91.108.13.10\n91.108.13.10\n",
                "91.108.0.0/16\n91.108.13.10",
            ]:
                with self.subTest(text=text):
                    target.write_text(text)
                    with self.assertRaisesRegex(stage.VoiceStageError, "does not match saved Voice targets"):
                        stage.compile_bundle(source, managed, ACTIVE_ROOT, "vtnet1", 19000, 19010, 989)
            target.unlink()
            with self.assertRaisesRegex(stage.VoiceStageError, "IPSET is missing"):
                stage.compile_bundle(source, managed, ACTIVE_ROOT, "vtnet1", 19000, 19010, 989)

    def test_reject_invalid_wan_and_invalid_port_and_out_of_bounds(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            source, managed = write_fixture(tmp)
            for wan in ("", "; rm -rf /", "vtnet1 $(false)"):
                with self.subTest(wan=wan):
                    with self.assertRaises(ValueError):
                        stage.compile_bundle(source, managed, ACTIVE_ROOT, wan, 19000, 19010, 989)
            with self.assertRaises(ValueError):
                stage.compile_bundle(source, managed, ACTIVE_ROOT, "vtnet1", 19000, 19000, 989)
            with self.assertRaises(ValueError):
                stage.compile_bundle(source, managed, ACTIVE_ROOT, "vtnet1", 19000, 19010, 0)

    def test_different_voice_wan_does_not_get_accepted_due_to_physical_resolution(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            root = fixture()
            root.find("./OPNsense/Zapret/voice/waninterface").text = "WAN2"
            source, managed = write_fixture(tmp, root)
            with self.assertRaisesRegex(ValueError, "independent WAN"):
                stage.compile_bundle(source, managed, ACTIVE_ROOT, "vtnet1", 19000, 19010, 989)

    def test_staging_directory_is_private_atomic_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            source, managed = write_fixture(tmp)
            candidate = stage.compile_bundle(source, managed, ACTIVE_ROOT, "vtnet1", 19000, 19010, 989)
            out = tmp / "release-voice"
            stage.stage_bundle(out, candidate)
            self.assertEqual(0o700, out.stat().st_mode & 0o777)
            self.assertEqual(set(candidate), set(p.name for p in out.iterdir()))
            for file in out.iterdir():
                self.assertEqual(0o600, file.stat().st_mode & 0o777)
            with self.assertRaisesRegex(stage.VoiceStageError, "refusing to overwrite"):
                stage.stage_bundle(out, {"voice.conf": "changed"})
            self.assertEqual(candidate["voice.conf"], (out / "voice.conf").read_text())

    def test_cli_success_and_invalid_candidate_preserve_prior_stage(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            source, managed = write_fixture(tmp)
            out = tmp / "voice-stage"
            args = [
                sys.executable, str(BACKEND / "voice_release_stage.py"),
                str(source), str(managed), str(ACTIVE_ROOT), "vtnet1",
                "19000", "19010", "989", str(out)
            ]
            ok = subprocess.run(args, capture_output=True, text=True, check=False)
            self.assertEqual(0, ok.returncode, ok.stderr)
            meta = json.loads((out / "metadata.json").read_text())
            self.assertFalse(meta["activation_authorized"])
            before = (out / "voice.conf").read_bytes()
            (managed / "ipset-telegram.txt").write_text("8.8.8.8\n", encoding="utf-8")
            failed = subprocess.run(args, capture_output=True, text=True, check=False)
            self.assertNotEqual(0, failed.returncode)
            self.assertEqual(before, (out / "voice.conf").read_bytes())
            self.assertNotIn("SECRET_DO_NOT_LEAK", failed.stderr)

    def test_staged_combined_traffic_keeps_ordinary_A2_and_voice_precedence(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            source, managed = write_fixture(tmp)
            ordinary = tmp / "traffic-user.conf"
            original = (
                "--filter-tcp=443\n--filter-l7=tls\n--new\n"
                "--filter-udp=596-599\n--filter-l7=unknown\n--payload=unknown\n"
            )
            ordinary.write_text(original, encoding="utf-8")
            artifacts = stage.compile_bundle(
                source, managed, ACTIVE_ROOT, "vtnet1", 19000, 19010, 989, ordinary
            )
            merged = artifacts["traffic.conf"]
            self.assertTrue(merged.startswith("--name=voice-telegram"))
            self.assertIn("--lua-desync=fake:blob=0x00000000000000000000000000000000:repeats=2\n--new\n--filter-tcp=443", merged)
            self.assertTrue(merged.endswith(original))
            self.assertEqual(2, merged.count("\n--new\n"))
            meta = json.loads(artifacts["metadata.json"])
            self.assertEqual(64, len(meta["merged_sha256"]))
            self.assertEqual(64, len(meta["ordinary_sha256"]))
            self.assertFalse(meta["activation_authorized"])

    def test_staged_all_off_keeps_ordinary_bytes_and_rejects_poc_collision(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            source, managed = write_fixture(tmp, fixture(False))
            ordinary = tmp / "traffic-user.conf"
            original = "--filter-tcp=443\n--filter-l7=tls\n\n"
            ordinary.write_text(original, encoding="utf-8")
            artifacts = stage.compile_bundle(
                source, managed, ACTIVE_ROOT, "vtnet1", 19000, 19010, 989, ordinary
            )
            self.assertEqual(original, artifacts["traffic.conf"])
            ordinary.write_text("--name=telegram-voice-poc\n" + original, encoding="utf-8")
            with self.assertRaises(ValueError):
                stage.compile_bundle(
                    source, managed, ACTIVE_ROOT, "vtnet1", 19000, 19010, 989, ordinary
                )

    def test_reject_nonexistent_source_with_no_artifacts(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            output = tmp / "never-created"
            proc = subprocess.run(
                [sys.executable, str(BACKEND / "voice_release_stage.py"), str(tmp / "missing"),
                 str(tmp), str(ACTIVE_ROOT), "vtnet1", "19000", "19010", "989", str(output)],
                capture_output=True, text=True
            )
            self.assertNotEqual(0, proc.returncode)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
