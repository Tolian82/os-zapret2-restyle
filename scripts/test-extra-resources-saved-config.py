#!/usr/bin/env python3
"""Stage 2: real-Git prospective resource view + original saved XML/template guard.

All fixtures are disposable. No browser input, real Config change, FD9,
service Stop/Start, engine process or IPFW action. The saved-pair witness
never authorizes removal, even if all checks pass.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/opnsense/scripts/OPNsense/Zapret"))
from extra_resources_preflight import PreflightError
from extra_resources_upstream_view import upstream_only_view

spec = importlib.util.spec_from_file_location(
    "saved_pair_fixture", ROOT / "scripts/test-voice-native-saved-pair-guard.py"
)
assert spec and spec.loader
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class SavedStrategiesPairTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="prospective-saved-")
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.runtime = self.base / "runtime"
        (self.runtime / "lua").mkdir(parents=True)
        (self.runtime / "files/fake").mkdir(parents=True)
        (self.runtime / "lua/native.lua").write_bytes(b"function native(ctx) return ctx end\n")
        (self.runtime / "files/fake/native.bin").write_bytes(b"fixture bin")
        self.git("init", "-q")
        self.git("config", "user.name", "Saved Pair")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("add", "lua", "files")
        self.git("commit", "-qm", "installed Git HEAD")
        extra = b"extra only"
        (self.runtime / "files/fake/extra.bin").write_bytes(extra)
        self.manifest = self.base / "installed.json"
        self.manifest.write_text(json.dumps({
            "schema": 1,
            "files": {"files/fake/extra.bin": hashlib.sha256(extra).hexdigest()},
        }))
        self.saved_xml, self.template = fixture.make_pair(self.base)
        self.initial_xml = self.saved_xml.read_bytes()
        self.initial_template = self.template.read_bytes()
        self.work = self.base / "work"
        self.work.mkdir()

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.runtime), *args],
            capture_output=True, check=True,
        ).stdout.decode().strip()

    def view(self):
        return upstream_only_view(
            self.runtime, self.manifest, self.saved_xml,
            workspace_root=self.work, saved_template=self.template,
        )

    def test_persisted_pair_is_attested_but_cannot_authorize_removal(self):
        with self.view() as (plan, prospective):
            self.assertEqual(plan["saved_pair"]["status"], "verified-input-only")
            self.assertEqual(plan["saved_pair"]["config_sha256"],
                             hashlib.sha256(self.initial_xml).hexdigest())
            self.assertEqual(plan["saved_pair"]["template_sha256"],
                             hashlib.sha256(self.initial_template).hexdigest())
            self.assertEqual(plan["compatibility"], "unknown")
            self.assertFalse(plan["authorized"])
            self.assertEqual(plan["counts"]["total"], 1)
            self.assertTrue((prospective / "lua/native.lua").is_file())
            self.assertFalse((prospective / "files/fake/extra.bin").exists())
        self.assertEqual(self.saved_xml.read_bytes(), self.initial_xml)
        self.assertEqual(self.template.read_bytes(), self.initial_template)
        self.assertTrue((self.runtime / "files/fake/extra.bin").is_file())
        self.assertEqual(list(self.work.iterdir()), [])

    def test_mismatch_in_saved_strategy_rejected_before_staging(self):
        self.saved_xml.write_bytes(self.initial_xml.replace(
            b"--filter-tcp=443", b"--filter-tcp=80"
        ))
        with self.assertRaisesRegex(PreflightError, "saved XML/rendered Strategies pair"):
            with self.view():
                pass
        self.assertEqual(list(self.work.iterdir()), [])
        self.assertEqual(self.template.read_bytes(), self.initial_template)

    def test_rendered_extra_arguments_changed_rejected_before_staging(self):
        self.template.write_bytes(self.initial_template.replace(
            b"--dpi-desync=fake", b"--dpi-desync=split"
        ))
        with self.assertRaisesRegex(PreflightError, "saved XML/rendered Strategies pair"):
            with self.view():
                pass
        self.assertEqual(list(self.work.iterdir()), [])

    def test_saved_xml_generation_changed_during_compilation(self):
        with self.assertRaisesRegex(PreflightError, "changed during compilation"):
            with self.view() as (_, prospective):
                self.assertTrue((prospective / "lua/native.lua").exists())
                self.saved_xml.write_bytes(self.initial_xml + b"\n")
        self.assertEqual(list(self.work.iterdir()), [])

    def test_template_generation_changed_during_compilation(self):
        with self.assertRaisesRegex(PreflightError, "template changed during compilation"):
            with self.view() as (_, prospective):
                self.assertTrue((prospective / "lua/native.lua").exists())
                self.template.write_bytes(self.initial_template + b"\n")
        self.assertEqual(self.saved_xml.read_bytes(), self.initial_xml)
        self.assertEqual(list(self.work.iterdir()), [])

    def test_template_symlink_is_rejected_before_staging(self):
        self.template.unlink()
        self.template.symlink_to(self.saved_xml)
        with self.assertRaises(PreflightError):
            with self.view():
                pass
        self.assertEqual(list(self.work.iterdir()), [])

    def test_voice_field_mismatch_also_blocks_false_strategies_verdict(self):
        self.template.write_bytes(self.initial_template.replace(
            b'VOICE_TELEGRAM_REQUESTED="1"', b'VOICE_TELEGRAM_REQUESTED="0"'
        ))
        with self.assertRaisesRegex(PreflightError, "saved XML/rendered Strategies pair"):
            with self.view():
                pass
        self.assertEqual(list(self.work.iterdir()), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
