#!/usr/bin/env python3
"""Retired private Voice PREPARED entrypoints stay absent from shipped sources.

The shared Voice/Strategies Apply and read-only draft preview are still active.
This small contract replaces tests of the deleted private PREPARED protocol.
"""
from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
SCRIPTS = ROOT / "src/opnsense/scripts/OPNsense/Zapret"


class RetiredVoiceEntrypointsTests(unittest.TestCase):
    def test_obsolete_mutating_routes_and_private_prepared_helpers_are_absent(self):
        retired = (
            "voice_native_apply_route.py",
            "voice_native_forward_apply.py",
            "voice_native_prepare_route.py",
            "voice_native_prepare_one_lock.py",
            "voice_native_operator_input_stage.py",
            "voice_native_saved_release_prepare.py",
            "voice_native_forward_stage_prepare.py",
            "voice_native_previous_evidence_prepare.py",
            "voice_native_initial_ipfw_seed.py",
            "voice_native_forward_prepare.py",
            "voice_native_forward_ipfw.py",
            "voice_native_forward_supervisor.py",
            "voice_native_candidate_engine_start.py",
            "voice_native_forward_stop.py",
        )
        for name in retired:
            with self.subTest(name=name):
                self.assertFalse((BACKEND / name).exists())
        for name in ("voice_native_render_saved.sh", "voice_native_build_release.sh"):
            with self.subTest(name=name):
                self.assertFalse((SCRIPTS / name).exists())

    def test_retired_private_cutover_executors_are_absent(self):
        for path in BACKEND.glob("voice_cutover_*.py"):
            self.fail("old cutover executor still shipped: " + path.name)
        for module in (
            "voice_ipfw_runtime.py",
            "voice_native_recovery_quiescence.py",
            "voice_native_five_resource_recovery.py",
            "voice_native_boot_recovery_review.py",
            "voice_firewall_ledger.py",
        ):
            with self.subTest(module=module):
                self.assertFalse((BACKEND / module).exists())

    def test_retired_telegram_poc_recovery_not_shipped(self):
        for path in BACKEND.glob('voice_native_legacy_*.py'):
            with self.subTest(path=path.name):
                self.fail('retired Telegram PoC legacy backend must not ship: ' + path.name)
        self.assertFalse((BACKEND / 'voice_migration_plan.py').exists())
        actions = (ROOT / 'src/opnsense/service/conf/actions.d/actions_zapret.conf').read_text()
        self.assertNotIn('[voice_recovery_status]', actions)
        shell = (SCRIPTS / 'zapret_service.sh').read_text()
        self.assertNotIn('voice_native_legacy_', shell)
        self.assertNotIn('shared-apply-legacy-', shell)

    def test_shared_apply_and_readonly_preview_remain_live_entrypoints(self):
        service = (SCRIPTS / "zapret_service.sh").read_text()
        configd = (
            ROOT / "src/opnsense/service/conf/actions.d/actions_zapret.conf"
        ).read_text()
        self.assertIn("shared_apply_run_service voice", service)
        self.assertIn("[shared_apply]", configd)
        self.assertIn("native-voice-preview-draft)", service)
        self.assertTrue((BACKEND / "voice_native_draft_preview_route.py").is_file())
        self.assertNotIn("[voice_apply]", configd)
        for command in (
            "native-voice-apply-prepared",
            "native-voice-prepare-apply-draft",
            "native-voice-prepare-prebuilt",
            "native-voice-prepare-release",
            "native-voice-prepare-saved",
            "native-voice-prepare-xml",
            "native-voice-prepare-draft",
        ):
            with self.subTest(command=command):
                self.assertNotIn(command, service)
                self.assertNotIn(command, configd)
        # The previous Python cutover coordinator is gone: do not leave its
        # standalone process actuator packaged or callable under inherited FD9.
        self.assertFalse((BACKEND / "voice_native_process_lifecycle.sh").exists())
        self.assertIn("shared_apply_stop_service", service)
        self.assertIn("shared_apply_boot_service", service)
        self.assertIn("shared_apply_execute_service", service)
        self.assertIn("start|stop|restart|reconfigure", service)
        pkg = (ROOT / "scripts/build-pkg.sh").read_text()
        self.assertNotIn('PREPARE_ROUTE=', pkg)
        self.assertNotIn('APPLY_ROUTE=', pkg)
        self.assertNotIn('FORWARD_EXECUTOR=', pkg)


if __name__ == "__main__":
    unittest.main(verbosity=2)
