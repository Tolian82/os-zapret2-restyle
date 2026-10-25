#!/usr/bin/env python3
"""Native FD9-owned saved Config to real detached render and upstream-only view.

Source fixtures simulate the mandatory original FD9 owner with a checker, but
use the REAL exclusive Config flock, saved-pair parser, detached native
renderer, Git HEAD attestation and upstream-only view. No live OPNsense
settings, service, IPFW or installed resources are touched.
"""
from __future__ import annotations

import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "src/opnsense/scripts/OPNsense/Zapret"
sys.path.insert(0, str(BASE))
from backend.shared_apply_render import TARGETS
from backend.voice_native_saved_pair_guard import SCALARS, BLOCKS, SERVICES
from extra_resources_preflight import PreflightError
from extra_resources_saved_strategies import locked_saved_strategies_view

spec = importlib.util.spec_from_file_location(
    "saved_pair_fixture", ROOT / "scripts/test-voice-native-saved-pair-guard.py"
)
fixture = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(fixture)


class NativeConfig:
    def __init__(self, filename):
        self.filename = Path(filename)

    def get(self):
        return ET.fromstring(self.filename.read_bytes())


class NativeTemplate:
    """OFFLINE facade with the same three official OPNsense +TARGETS."""
    def __init__(self, target_root_directory):
        self.root = Path(target_root_directory)

    def list_module(self, name):
        if name != "OPNsense/Zapret":
            raise RuntimeError("foreign module")
        return {"+TARGETS": TARGETS}

    def set_config(self, config):
        self.zapret = config.find("./OPNsense/Zapret")
        if self.zapret is None:
            raise RuntimeError("missing Zapret config")

    def generate(self, module):
        if module != "OPNsense/Zapret":
            raise RuntimeError("foreign module")
        lines = ["# original OPNsense template facade"]
        for name, path, _ in SCALARS:
            item = self.zapret.find(path)
            lines.append(name + '="' + (item.text or "" if item is not None else "") + '"')
        for name, path in BLOCKS:
            item = self.zapret.find(path)
            text = (item.text or "") if item is not None else ""
            mark = "__ZAPRET_" + name + "__"
            lines.extend([name + "=$(cat <<'" + mark + "'", text, mark, ")"])
        for service in SERVICES:
            item = self.zapret.find("voice/" + service + "/enabled")
            lines.append("VOICE_" + service.upper() + '_REQUESTED="' +
                         (item.text or "0" if item is not None else "0") + '"')
        rendered = "\n".join(lines) + "\n"
        files = []
        for name, rel in TARGETS.items():
            target = self.root / rel.lstrip("/")
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            target.write_text(rendered if name == "zapret.conf" else "", encoding="utf-8")
            target.chmod(0o600)
            files.append(str(target))
        return files


class DriftedTemplate(NativeTemplate):
    def generate(self, module):
        files = super().generate(module)
        target = self.root / "usr/local/etc/zapret2/zapret.conf"
        target.write_text(target.read_text().replace("--filter-tcp=443", "--filter-tcp=80"))
        target.chmod(0o600)
        return files


class SavedNativeViewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / "runtime"
        (self.root / "lua").mkdir(parents=True)
        (self.root / "files/fake").mkdir(parents=True)
        (self.root / "lua/native.lua").write_bytes(b"-- native resource\n")
        (self.root / "files/fake/native.bin").write_bytes(b"base")
        self.git("init", "-q")
        self.git("config", "user.name", "Native test")
        self.git("config", "user.email", "offline@example.invalid")
        self.git("add", "lua", "files")
        self.git("commit", "-qm", "installed HEAD")
        extra = b"extra"
        (self.root / "files/fake/extra.bin").write_bytes(extra)
        self.manifest = self.base / "installed.json"
        self.manifest.write_text(json.dumps({
            "schema": 1,
            "files": {"files/fake/extra.bin": hashlib.sha256(extra).hexdigest()},
        }))
        self.config, _ = fixture.make_pair(self.base)
        self.saved = self.config.read_bytes()
        self.fd = os.open(self.config, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
        self.addCleanup(os.close, self.fd)
        fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.owner = (os.getuid(), os.getgid())
        self.work = self.base / "private"
        self.work.mkdir(mode=0o700)
        self.lifecycle_checks = 0

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args],
                              capture_output=True, check=True).stdout

    def verify_lock(self):
        self.lifecycle_checks += 1

    def candidate(self, **kwargs):
        return locked_saved_strategies_view(
            self.root, self.manifest, config_path=self.config,
            config_fd=self.fd, config_owner=self.owner,
            workspace_root=self.work, check_lifecycle=self.verify_lock,
            template_factory=kwargs.pop("template_factory", NativeTemplate),
            config_factory=NativeConfig, **kwargs,
        )

    def test_full_native_saved_render_produces_untrusted_result(self):
        with self.candidate() as (plan, view, xml, template):
            self.assertEqual(xml.read_bytes(), self.saved)
            self.assertIn("TRAFFIC_ARGS=$(cat", template.read_text())
            self.assertEqual(plan["saved_pair"]["status"], "verified-input-only")
            self.assertEqual(plan["compatibility"], "unknown")
            self.assertFalse(plan["authorized"])
            self.assertTrue((view / "lua/native.lua").is_file())
            self.assertFalse((view / "files/fake/extra.bin").exists())
            self.assertTrue(self.config.exists())
        self.assertGreaterEqual(self.lifecycle_checks, 3)
        self.assertEqual(self.config.read_bytes(), self.saved)
        self.assertTrue((self.root / "files/fake/extra.bin").is_file())
        self.assertEqual(list(self.work.iterdir()), [])

    def test_native_rendered_wrong_strategies_refused_without_mutation(self):
        with self.assertRaises(PreflightError):
            with self.candidate(template_factory=DriftedTemplate):
                self.fail("mismatched native render was accepted")
        self.assertEqual(list(self.work.iterdir()), [])
        self.assertEqual(self.config.read_bytes(), self.saved)

    def test_no_original_config_flock_is_refused(self):
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        with self.assertRaisesRegex(RuntimeError, "flock not held"):
            with self.candidate():
                self.fail("unlocked Config entered native view")
        self.assertEqual(list(self.work.iterdir()), [])

    def test_wrong_config_owner_refused(self):
        with self.assertRaises(RuntimeError):
            with locked_saved_strategies_view(
                self.root, self.manifest, config_path=self.config,
                config_fd=self.fd, config_owner=(self.owner[0] + 1, self.owner[1]),
                workspace_root=self.work, check_lifecycle=self.verify_lock,
                template_factory=NativeTemplate, config_factory=NativeConfig,
            ):
                self.fail("foreign owner accepted")
        self.assertEqual(list(self.work.iterdir()), [])

    def test_lifecycle_check_failure_refused(self):
        def reject():
            raise RuntimeError("native FD9 not held")
        with self.assertRaisesRegex(RuntimeError, "FD9 not held"):
            with locked_saved_strategies_view(
                self.root, self.manifest, config_path=self.config,
                config_fd=self.fd, config_owner=self.owner,
                workspace_root=self.work, check_lifecycle=reject,
                template_factory=NativeTemplate, config_factory=NativeConfig,
            ):
                self.fail("foreign FD9 accepted")
        self.assertEqual(list(self.work.iterdir()), [])

    def test_config_change_while_compiling_is_refused(self):
        with self.assertRaisesRegex(PreflightError, "changed during"):
            with self.candidate() as (_, view, _xml, _template):
                self.assertTrue((view / "lua/native.lua").is_file())
                os.pwrite(self.fd, b"X", 0)
        self.assertEqual(list(self.work.iterdir()), [])

    def test_native_saved_in_place_replacement_is_refused(self):
        with self.assertRaises(RuntimeError):
            with self.candidate() as (_, _view, _xml, _template):
                self.config.unlink()
                self.config.write_bytes(self.saved)
        self.assertEqual(list(self.work.iterdir()), [])

    def test_expected_inventory_witness_mismatch_refused(self):
        with self.assertRaisesRegex(PreflightError, "stale"):
            with self.candidate(expected_witness="0" * 64):
                self.fail("stale preview accepted")
        self.assertEqual(list(self.work.iterdir()), [])

    def test_world_readable_workspace_refused(self):
        self.work.chmod(0o755)
        with self.assertRaisesRegex(PreflightError, "unsafe prospective Config workspace"):
            with self.candidate():
                self.fail("unsafe workspace accepted")
        self.assertEqual(list(self.work.iterdir()), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
