#!/usr/bin/env python3
"""Stage-3 saved XML + native journal routing, with NO service/kernel writes."""
from __future__ import annotations

import fcntl
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))
from voice_native_lifecycle_router import (
    inspect_lifecycle, inspect_candidate, check_legacy_poc_compatibility, VoiceLifecycleRouteError,
)
from voice_cutover_journal import VoiceCutoverJournal

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
        self.assertEqual(result["reason"], "voice-saved-off-legacy-guard-still-authoritative")
        self.assertIs(result["public_voice_apply"], False)

    def legacy_guard(self):
        fd = os.open(self.config, os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return check_legacy_poc_compatibility(
                self.config, self.whole, self.ledger,
                config_fd=fd, config_owner=self.owner,
                require_lifecycle_owner=lambda: None,
            )
        finally:
            os.close(fd)

    def test_legacy_poc_allows_saved_five_off(self):
        self.assertIsNone(self.legacy_guard())
        self.assertFalse(self.whole.exists())

    def test_legacy_poc_refuses_any_saved_native_on_even_with_global_off(self):
        for settings in (
            config_xml(profiles={"telegram": "1"}),
            config_xml(profiles={"custom": "1"}, global_enabled="0"),
            config_xml(profiles={"discord": "1"}, voice_wan="vtnet2"),
        ):
            with self.subTest(xml=settings[:80]):
                self.config.write_bytes(settings)
                with self.assertRaises(VoiceLifecycleRouteError):
                    self.legacy_guard()
        self.assertFalse(self.whole.exists())
        self.assertFalse(self.ledger.exists())

    def test_legacy_poc_refuses_pending_journal_and_corrupt_config(self):
        self.config.write_bytes(b"<incomplete")
        with self.assertRaises(VoiceLifecycleRouteError):
            self.legacy_guard()
        self.config.write_bytes(config_xml())
        self.whole.mkdir(mode=0o700)
        journal = VoiceCutoverJournal(self.whole)
        old = {key: str(i) * 64 for i, key in enumerate(
            ("config", "runtime", "engine", "firewall", "supervisor"),
        )}
        proof = {key: ("a" if i == 0 else "b" if i == 1 else "c") * 64
                 for i, key in enumerate(
                     ("saved_xml_sha256", "merged_sha256", "native_argv_sha256"))}
        journal.begin(old, proof)
        with self.assertRaises(VoiceLifecycleRouteError):
            self.legacy_guard()
        self.assertIsNotNone(journal.read())

    def test_five_off_profiles_preserve_existing_legacy_guard(self):
        report = self.inspect()
        self.assertEqual(report["state"], "voice-saved-off-legacy-guard-still-authoritative")
        self.assertEqual(report["saved_voice_profiles"], dict.fromkeys(
            ("telegram", "discord", "x", "sip", "custom"), False,
        ))
        self.assertIs(report["safe_to_mutate"], False)
        self.assertIs(report["public_voice_apply"], False)

    def test_saved_voice_on_is_not_an_activation_authority(self):
        self.config.write_bytes(config_xml(profiles={"telegram": "1"}))
        report = self.inspect()
        self.assertEqual(report["state"], "voice-saved-on-native-apply-not-wired")
        self.assertIs(report["saved_voice_on"], True)
        self.assertIs(report["safe_to_enable_voice"], False)

    def test_global_off_and_different_wan_remain_blocked(self):
        self.config.write_bytes(config_xml(profiles={"discord":"1"}, global_enabled="0"))
        self.assertEqual(self.inspect()["state"], "voice-saved-on-global-service-off")
        self.config.write_bytes(config_xml(profiles={"discord":"1"}, voice_wan="vtnet2"))
        self.assertEqual(self.inspect()["state"], "voice-saved-on-wan-mismatch")

    def test_native_pending_preempts_even_corrupt_saved_xml(self):
        self.whole.mkdir(mode=0o700)
        journal = VoiceCutoverJournal(self.whole)
        old = {key: str(i) * 64 for i, key in enumerate(
            ("config", "runtime", "engine", "firewall", "supervisor"),
        )}
        proof = {key: ("a" if i == 0 else "b" if i == 1 else "c") * 64
                 for i, key in enumerate(
                     ("saved_xml_sha256","merged_sha256","native_argv_sha256"))}
        journal.begin(old, proof)
        self.config.write_bytes(b"<incomplete")
        status = self.inspect()
        self.assertEqual(status["state"], "native-transaction-review-required")
        self.assertEqual(status["reason"], "whole-runtime-intent")
        self.assertIsNone(status["saved_voice_on"])

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
