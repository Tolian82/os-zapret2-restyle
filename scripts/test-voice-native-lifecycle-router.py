#!/usr/bin/env python3
"""Stage-3 saved XML + native journal routing, with NO service/kernel writes."""
from __future__ import annotations

import fcntl
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))
from voice_native_lifecycle_router import (
    inspect_lifecycle, inspect_candidate, VoiceLifecycleRouteError,
    native_config_owner, _pinned_regular,
)
from shared_apply_operation import SharedApplyOperation

SERVICE = ROOT / "src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
ACTIONS = ROOT / "src/opnsense/service/conf/actions.d/actions_zapret.conf"


def config_xml(*, profiles=None, global_enabled="1", voice_wan="",
               general_wan="vtnet1", root="opnsense") -> bytes:
    profiles = profiles or {}
    voice = "".join(
        "<%s><enabled>%s</enabled></%s>" % (k, value, k)
        for k, value in profiles.items()
    )
    return (
        "<%s><OPNsense><Zapret><general><enabled>%s</enabled>"
        "<waninterface>%s</waninterface></general>"
        "<voice><waninterface>%s</waninterface>%s</voice>"
        "</Zapret></OPNsense></%s>"
        % (root, global_enabled, general_wan, voice_wan, voice, root)
    ).encode("ascii")


class LifecycleRouterTests(unittest.TestCase):
    def test_failed_inspector_emits_bounded_reason_without_success(self):
        import contextlib
        import io
        from unittest.mock import patch
        from voice_native_lifecycle_router import main as cli_main
        stderr = io.StringIO()
        with patch("voice_native_lifecycle_router.require_lifecycle_lock",
                   side_effect=VoiceLifecycleRouteError("existing lifecycle FD9 is required")):
            with contextlib.redirect_stderr(stderr):
                code = cli_main(["inspect"])
        self.assertEqual(code, 69)
        self.assertIn("existing lifecycle FD9 is required", stderr.getvalue())
        self.assertNotIn("<opnsense>", stderr.getvalue())


    def test_production_owner_is_opnsense_wwwonly_wheel_not_root(self):
        # Actual OPNsense 26.7: Mk/version.mk CORE_USER=wwwonly UID=789,
        # config.php owner=wwwonly:wheel; rc.subr.d/php chowns config.xml.
        with patch("voice_native_lifecycle_router.pwd.getpwnam",
                   return_value=SimpleNamespace(pw_uid=789)) as user, \
             patch("voice_native_lifecycle_router.grp.getgrnam",
                   return_value=SimpleNamespace(gr_gid=0)) as group:
            self.assertEqual(native_config_owner(), (789, 0))
            user.assert_called_once_with("wwwonly")
            group.assert_called_once_with("wheel")

    def test_real_style_wwwonly_inode_is_accepted_without_loosening_checks(self):
        # No ownership mutation in CI: simulate the production inode
        # while preserving the real opened file dev/ino/mode/link structure.
        fd = os.open(self.config, os.O_RDONLY)
        try:
            current = os.fstat(fd)
            fake = SimpleNamespace(
                st_mode=current.st_mode, st_nlink=current.st_nlink,
                st_dev=current.st_dev, st_ino=current.st_ino,
                st_uid=789, st_gid=0,
            )
            with patch("voice_native_lifecycle_router.os.lstat", return_value=fake), \
                 patch("voice_native_lifecycle_router.os.fstat", return_value=fake):
                self.assertIs(_pinned_regular(self.config, fd, owner=(789, 0)), fake)
                with self.assertRaisesRegex(
                    VoiceLifecycleRouteError, "unsafe or replaced native Config inode"
                ):
                    _pinned_regular(self.config, fd, owner=(0, 0))
            foreign = SimpleNamespace(
                st_mode=current.st_mode, st_nlink=current.st_nlink,
                st_dev=current.st_dev, st_ino=current.st_ino + 1,
                st_uid=789, st_gid=0,
            )
            with patch("voice_native_lifecycle_router.os.lstat", return_value=foreign), \
                 patch("voice_native_lifecycle_router.os.fstat", return_value=fake):
                with self.assertRaises(VoiceLifecycleRouteError):
                    _pinned_regular(self.config, fd, owner=(789, 0))
        finally:
            os.close(fd)

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.config = self.root / "config.xml"
        self.whole = self.root / "whole"
        self.ledger = self.root / "ipfw"
        self.config.write_bytes(config_xml())
        self.owner = (os.geteuid(), os.getegid())

    def inspect(self, *, locked=True):
        fd = os.open(self.config, os.O_RDWR)
        try:
            if locked:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return inspect_lifecycle(
                self.config, self.whole, self.ledger,
                config_fd=fd, config_owner=self.owner,
                require_lifecycle_owner=lambda: None,
            )
        finally:
            os.close(fd)

    def candidate(self):
        fd = os.open(self.config, os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return inspect_candidate(
                self.config, self.whole, self.ledger,
                config_fd=fd, config_owner=self.owner,
                require_lifecycle_owner=lambda: None,
            )
        finally:
            os.close(fd)

    def test_locked_saved_on_compiles_real_profile_without_creating_staging(self):
        xml = config_xml(profiles={"telegram": "1"})
        native = ("--filter-udp=596-599\n--filter-l7=stun\n"
                  "--payload=stun\n--lua-desync=fake:blob=0x00000000:repeats=2")
        xml = xml.replace(b"<telegram><enabled>1</enabled></telegram>",
                          ("<telegram><enabled>1</enabled><args>" + native +
                           "</args></telegram>").encode("ascii"))
        xml = xml.replace(b"</Zapret>",
                          b"<hostlist><telegramips>91.108.13.10</telegramips></hostlist></Zapret>")
        self.config.write_bytes(xml)
        result = self.candidate()
        self.assertEqual(result["state"], "native-voice-candidate-syntax-qualified")
        self.assertEqual(result["services"], ["telegram"])
        self.assertEqual(result["profile_count"], 1)
        self.assertEqual(len(result["profile_sha256"]), 64)
        self.assertEqual(len(result["plan_sha256"]), 64)
        self.assertIs(result["public_voice_apply"], False)
        self.assertIs(result["safe_to_enable_voice"], False)
        self.assertFalse(self.whole.exists())
        self.assertFalse(self.ledger.exists())
        self.assertEqual(self.config.read_bytes(), xml)

    def test_compiler_rejects_malicious_native_option_from_locked_saved_config(self):
        xml = config_xml(profiles={"telegram": "1"}).replace(
            b"</telegram>", b"<args>--exec=/bin/sh</args></telegram>"
        )
        self.config.write_bytes(xml)
        with self.assertRaises(ValueError):
            self.candidate()
        self.assertEqual(self.config.read_bytes(), xml)
        self.assertFalse(self.whole.exists())

    def test_preflight_rejects_voice_off_without_compiling_draft_args(self):
        self.config.write_bytes(config_xml())
        result = self.candidate()
        self.assertEqual(result["state"], "native-voice-candidate-not-eligible")
        self.assertEqual(result["reason"], "voice-saved-off-common-apply-available")
        self.assertIs(result["public_voice_apply"], False)

    def test_five_off_profiles_remain_read_only_under_shared_apply(self):
        report = self.inspect()
        self.assertEqual(report["state"], "voice-saved-off-common-apply-available")
        self.assertEqual(report["saved_voice_profiles"], dict.fromkeys(
            ("telegram", "discord", "x", "sip", "custom"), False,
        ))
        self.assertIs(report["safe_to_mutate"], False)
        self.assertIs(report["public_voice_apply"], False)

    def test_saved_voice_on_is_not_an_activation_authority(self):
        self.config.write_bytes(config_xml(profiles={"telegram": "1"}))
        report = self.inspect()
        self.assertEqual(report["state"], "voice-saved-on-common-apply-configured")
        self.assertIs(report["saved_voice_on"], True)
        self.assertIs(report["safe_to_enable_voice"], False)

    def test_global_off_and_different_wan_remain_blocked(self):
        self.config.write_bytes(config_xml(profiles={"discord":"1"}, global_enabled="0"))
        self.assertEqual(self.inspect()["state"], "voice-saved-on-global-service-off")
        self.config.write_bytes(config_xml(profiles={"discord":"1"}, voice_wan="vtnet2"))
        self.assertEqual(self.inspect()["state"], "voice-saved-on-wan-mismatch")

    def test_shared_pending_preempts_corrupt_saved_xml_without_poc_reads(self):
        common = SharedApplyOperation(self.root / "shared-apply")
        item = {"id":"a"*32, "page":"voice", "base":"b"*64,
                "candidate":"c"*64, "changed_fields":[]}
        common.advance("prepared",item)
        # No private old root exists; only shared Apply may block inspection.
        self.config.write_bytes(b"<incomplete")
        status = self.inspect()
        self.assertEqual("native-transaction-review-required", status["state"])
        self.assertEqual("shared-apply-pending", status["reason"])
        self.assertIsNone(status["saved_voice_on"])
        self.assertFalse(self.whole.exists())
        self.assertFalse(self.ledger.exists())

    def test_retired_cutover_evidence_cannot_block_common_saved_config(self):
        self.whole.write_text("stale old PoC marker, not common authority")
        self.ledger.write_text("retired private IPFW ledger")
        status = self.inspect()
        self.assertEqual("voice-saved-off-common-apply-available", status["state"])
        self.assertFalse((self.root / "shared-apply").exists())

    def test_invalid_xml_and_invalid_boolean_never_assume_voice_off(self):
        for body in (
            b"<incomplete",
            config_xml(profiles={"sip":"yes"}),
            config_xml(global_enabled="on"),
            config_xml(root="foreign"),
            config_xml() + b"<!DOCTYPE a>",
            config_xml(profiles={"telegram":"1", "discord":"1"}).replace(
                b"</voice>", b"<telegram><enabled>1</enabled></telegram></voice>"
            ),
        ):
            with self.subTest(body=body[:50]):
                self.config.write_bytes(body)
                with self.assertRaises(VoiceLifecycleRouteError):
                    self.inspect()

    def test_missing_actual_config_flock_is_refused(self):
        with self.assertRaises((ValueError,RuntimeError,OSError)):
            self.inspect(locked=False)

    def test_existing_fd9_dispatch_and_configd_are_read_only(self):
        shell = SERVICE.read_text()
        action = ACTIONS.read_text()
        self.assertIn("native_voice_lifecycle_inspect_service()", shell)
        self.assertIn("native-voice-lifecycle-inspect)", shell)
        self.assertIn('service_with_lifecycle_lock "${LIFECYCLE_LOCK_TIMEOUT}" "$@"', shell)
        self.assertIn("[voice_lifecycle_inspect]", action)
        self.assertIn("zapret_service.sh native-voice-lifecycle-inspect", action)
        self.assertIn("[voice_candidate_preflight]", action)
        self.assertIn("zapret_service.sh native-voice-candidate-preflight", action)
        self.assertIn("native_voice_candidate_preflight_service()", shell)
        self.assertIn("native-voice-candidate-preflight)", shell)
        self.assertNotIn("native_voice_legacy_poc_preflight_service()", shell)
        self.assertNotIn("legacy-poc-preflight", shell)
        self.assertIn("telegram_voice_compat_apply_service()", shell)
        self.assertIn(
            "telegram-voice-enable)\n            telegram_voice_compat_apply_service enable",
            shell,
        )
        self.assertIn(
            "telegram-voice-disable)\n            telegram_voice_compat_apply_service disable",
            shell,
        )
        self.assertIn(
            "telegram-voice-status)\n            telegram_voice_compat_status_service",
            shell,
        )
        self.assertIn('shared_apply_run_service voice "$_compat_encoded"', shell)
        self.assertNotIn(
            "telegram-voice-enable)\n            native_voice_legacy_poc_preflight_service",
            shell,
        )
        self.assertNotIn("voice-native-apply", action)
        self.assertNotIn("native-voice-apply)", shell)
        self.assertNotIn("native-voice-apply-prepared)", shell)
        self.assertNotIn("native-voice-prepare-apply-draft)", shell)


if __name__ == "__main__":
    unittest.main(verbosity=2)
