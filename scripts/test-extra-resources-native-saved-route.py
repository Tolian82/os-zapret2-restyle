#!/usr/bin/env python3
"""Native setup.lock -> original FD9 -> Config-flock saved input preview tests.

This runs with offline Git, a real kernel Config flock and mock native FD9/
official OPNsense template engine. CLI and shell path checks prove that only
the preexisting setup.lock and service FD9 owner expose the import-only path.
"""
from __future__ import annotations

import contextlib
import fcntl
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SRC = ROOT / "src/opnsense/scripts/OPNsense/Zapret"
sys.path.insert(0, str(SRC))

spec = importlib.util.spec_from_file_location(
    "locked_preview_fixture", SCRIPTS / "test-extra-resources-native-locked-config.py"
)
assert spec and spec.loader
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
from extra_resources_saved_route import preview_saved_input, main

CLEAR = {"state": "clear", "safe_to_mutate": True}
BLOCKED = {"state": "blocked", "reason": "shared-apply-pending", "safe_to_mutate": False}


class NativePreviewRouteTests(base.SavedNativeViewTests):
    @staticmethod
    def fake_compiler(*_args):
        return {"state": "native-common-candidate-compiled-input-only",
                "authorized": False, "engine_lua_proof": "not-run",
                "argv_sha256": "a" * 64}

    def preview(self, *, checker=None, gate=None, **kwargs):
        # The native route itself acquires the only saved Config flock. The
        # inherited base fixture holds it when testing an import-only context.
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        return preview_saved_input(
            config=self.config, runtime=self.root, manifest=self.manifest,
            workspace=self.work,
            gate_checker=gate or (lambda: dict(CLEAR)),
            lock_checker=checker or self.verify_lock,
            owner_provider=lambda: self.owner,
            template_factory=base.NativeTemplate,
            config_factory=base.NativeConfig,
            compiler=kwargs.pop("compiler", self.fake_compiler),
            **kwargs,
        )

    def test_production_route_reuses_saved_pair_and_cannot_grant_remove(self):
        report = self.preview()
        self.assertEqual(report["state"], "saved-native-input-attested")
        self.assertEqual(report["saved_pair"], "verified-input-only")
        self.assertEqual(report["engine_lua_proof"], "not-run")
        self.assertEqual(report["native_candidate"], "native-common-candidate-compiled-input-only")
        self.assertEqual(report["candidate_argv_sha256"], "a" * 64)
        self.assertEqual(report["compatibility"], "unknown")
        self.assertIs(report["authorized"], False)
        self.assertEqual((report["lua"], report["bin"], report["total"]), (0, 1, 1))
        self.assertEqual(len(report["inventory_sha256"]), 64)
        self.assertGreaterEqual(self.lifecycle_checks, 3)
        self.assertEqual(self.config.read_bytes(), self.saved)
        self.assertTrue((self.root / "files/fake/extra.bin").is_file())
        self.assertEqual(list(self.work.iterdir()), [])

    def test_refuses_shared_apply_pending_journal_before_any_snapshot(self):
        with self.assertRaisesRegex(RuntimeError, "shared Apply journal"):
            self.preview(gate=lambda: BLOCKED)
        self.assertEqual(list(self.work.iterdir()), [])

    def test_refuses_shared_apply_generation_change_after_snapshot(self):
        checks = []
        def gate():
            checks.append(1)
            return dict(CLEAR) if len(checks) < 2 else BLOCKED
        with self.assertRaisesRegex(RuntimeError, "journal changed"):
            self.preview(gate=gate)
        self.assertEqual(list(self.work.iterdir()), [])

    def test_refuses_missing_original_fd9_before_config_read(self):
        def deny():
            raise RuntimeError("native original FD9 not held")
        with self.assertRaisesRegex(RuntimeError, "FD9 not held"):
            self.preview(checker=deny)
        self.assertEqual(list(self.work.iterdir()), [])

    def test_native_compiler_cannot_override_unknown_or_authorization(self):
        def malicious(*_args):
            return {"state": "native-common-candidate-compiled-input-only",
                    "authorized": True, "engine_lua_proof": "verified",
                    "argv_sha256": "b" * 64}
        with self.assertRaisesRegex(RuntimeError, "compiler attestation"):
            self.preview(compiler=malicious)
        self.assertEqual(list(self.work.iterdir()), [])

    def test_narrow_cli_and_no_public_api_action(self):
        self.assertEqual(main([]), 64)
        self.assertEqual(main(["preview-saved", "arbitrary"]), 64)
        with patch("extra_resources_saved_route.require_lifecycle_lock",
                   side_effect=RuntimeError("no original FD9")):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(main(["preview-saved"]), 69)
            self.assertNotIn("<opnsense>", err.getvalue())
        service = (SRC / "zapret_service.sh").read_text()
        launcher = (SRC / "extra_resources_launcher.sh").read_text()
        actions = (ROOT / "src/opnsense/service/conf/actions.d/actions_zapret.conf").read_text()
        self.assertIn('extra-resources-preview-saved)', service)
        self.assertIn('extra_resources_preview_saved_service()', service)
        self.assertIn('extra-resources-preview-saved|upstream-recover-mutating', service)
        self.assertIn('EXTRA_RESOURCES_SETUP_LOCK_OWNER:-0', service)
        self.assertIn('preview-saved)', launcher)
        segment = launcher.split('    preview-saved)\n', 1)[1].split('    install|recover)', 1)[0]
        self.assertIn('"$LOCKF_BIN" -s -t 3 "$LOCK_FILE"', segment)
        self.assertLess(segment.index('"$LOCKF_BIN" -s -t 3 "$LOCK_FILE"'),
                        segment.index('"$SERVICE_SCRIPT" extra-resources-preview-saved'))
        self.assertNotIn("extra_resources_preview_saved", actions)
        self.assertNotIn("extra_resources_remove", actions)
        self.assertNotIn("stop_service", segment)
        self.assertNotIn("restart", segment)
        for path in ("extra_resources_launcher.sh", "zapret_service.sh"):
            compiled = subprocess.run(["sh", "-n", str(SRC / path)],
                                      capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
