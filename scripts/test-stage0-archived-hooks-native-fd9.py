#!/usr/bin/env python3
"""Offline fail-closed contract for actual archived hook runner; VM is separate."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "archived", Path(__file__).with_name("stage0-archived-hooks-native-fd9.py"))
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


def result(text, code=0):
    return type("Result", (), {"stdout": text, "returncode": code, "stderr": ""})()


def metadata():
    return {"name": "os-zapret2-restyle", "version": "0.6.2_1",
            "abi": "FreeBSD:15:amd64",
            "scripts": {p: "#!/bin/sh\nexit 0\n" for p in h.PHASES}}


class ArchivedHookContract(unittest.TestCase):
    def test_exact_archive_hash_guarded_before_reading_hook(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.pkg"
            p.write_bytes(b"fixture only")
            with patch.object(h, "execute") as cmd:
                with self.assertRaisesRegex(h.Refusal, "ARCHIVE_DIGEST"):
                    h.load_old_hooks(p)
                cmd.assert_not_called()

    def test_exact_manifest_can_extract_four_complete_script_texts(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "fixture.pkg"
            p.write_bytes(b"controlled fixture")
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
            with patch.object(h, "SHA", digest), patch.object(h, "execute", return_value=result(json.dumps(metadata()))):
                scripts = h.load_old_hooks(p)
                self.assertEqual(set(scripts), set(h.PHASES))
                self.assertEqual(scripts["pre-deinstall"], "#!/bin/sh\nexit 0\n")

    def test_missing_each_historical_hook_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "fixture.pkg"
            p.write_bytes(b"controlled fixture")
            with patch.object(h, "SHA", hashlib.sha256(p.read_bytes()).hexdigest()):
                for phase in h.PHASES:
                    body = metadata()
                    del body["scripts"][phase]
                    with self.subTest(phase=phase), patch.object(
                        h, "execute", return_value=result(json.dumps(body))
                    ), self.assertRaisesRegex(h.Refusal, "HOOK_MISSING"):
                        h.load_old_hooks(p)

    def test_wrong_historical_name_version_and_abi_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "fixture.pkg"
            p.write_bytes(b"controlled fixture")
            with patch.object(h, "SHA", hashlib.sha256(p.read_bytes()).hexdigest()):
                for field, wrong in [("name", "not-zapret"), ("version", "0.6.2_2"),
                                     ("abi", "Linux:15:amd64")]:
                    body = metadata()
                    body[field] = wrong
                    with self.subTest(field=field), patch.object(
                        h, "execute", return_value=result(json.dumps(body))
                    ), self.assertRaisesRegex(h.Refusal, "IDENTITY_OR_ABI"):
                        h.load_old_hooks(p)

    def test_changed_shell_or_manifest_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "fixture.pkg"
            p.write_bytes(b"controlled fixture")
            with patch.object(h, "SHA", hashlib.sha256(p.read_bytes()).hexdigest()):
                for invalid in ["echo injected", "", None]:
                    body = metadata()
                    body["scripts"]["pre-install"] = invalid
                    with self.subTest(invalid=invalid), patch.object(
                        h, "execute", return_value=result(json.dumps(body))
                    ), self.assertRaisesRegex(h.Refusal, "HOOK_MISSING_OR_NOT_SHELL"):
                        h.load_old_hooks(p)

    def test_fixture_overrides_real_process_targets(self):
        with tempfile.TemporaryDirectory() as d:
            f = h.fixture(d, metadata()["scripts"])
            e = f["env"]
            for key in ("SERVICE_SCRIPT", "PGREP_BIN", "KILL_BIN",
                        "CONFIGCTL", "FIRMWARE_REGISTER", "CONFIGURE_PLUGINS",
                        "CONFIGD_PID_FILE", "SHARED_APPLY_JOURNAL", "UPGRADE_STATE_DIR",
                        "UPGRADE_RESTART_MARKER", "REPLACEMENT_RESTART_MARKER",
                        "LIFECYCLE_LOCK_FILE", "EXTRA_INVENTORY_CACHE"):
                self.assertTrue(e[key].startswith(d), key)
            self.assertEqual(e["LOCKF_BIN"], "/usr/bin/lockf")
            self.assertEqual(e["FD9_REQUIRED"], "1")

    def test_wrong_os_refused_before_archived_package_access(self):
        with tempfile.TemporaryDirectory() as d:
            class Linux:
                sysname = "Linux"
                machine = "x86_64"
            with patch.object(h.os, "uname", return_value=Linux()), \
                    patch.object(h, "load_old_hooks") as loader:
                with self.assertRaisesRegex(h.Refusal, "ONLY_DISPOSABLE"):
                    h.run(Path(d) / "absent.pkg", Path(d) / "report.json")
                loader.assert_not_called()

    def test_historical_post_deinstall_is_never_implicitly_scheduled(self):
        self.assertEqual(h.PHASES, ("pre-install", "post-install", "pre-deinstall", "post-deinstall"))
        with tempfile.TemporaryDirectory() as d:
            hooks = metadata()["scripts"]
            f = h.fixture(d, hooks)
            self.assertEqual(set(f["hooks"]), set(h.PHASES))
            self.assertFalse(f["marker"].exists())


if __name__ == "__main__":
    unittest.main()
