#!/usr/bin/env python3
"""Offline refusal, outcomes, and no accidental real-host mutation contracts."""
import importlib.util
from pathlib import Path
import unittest
from unittest import mock

path = Path(__file__).with_name("stage0-opnsense-preinstall-abort.py")
spec = importlib.util.spec_from_file_location("preinstall", path)
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)
TRACE = ["old:pre-install", "old:post-install", s.REFUSAL_LINE]


class NativeIncomingRefusal(unittest.TestCase):
    def test_hook_is_explicit_nonzero_refusal(self):
        source = s.phase_hook(Path("/tmp/test"), "new", "pre-install")
        self.assertIn("exit 73", source)
        self.assertIn(s.REFUSAL_LINE, source)
        self.assertNotIn("pkg delete", source)

    def test_unrelated_hook_remains_nonmutating(self):
        source = s.phase_hook(Path("/tmp/test"), "old", "pre-deinstall")
        self.assertIn("exit 0", source)
        self.assertNotIn("pkg delete", source)
        with self.assertRaisesRegex(s.Refusal, "UNSAFE_FIXTURE_HOOK"):
            s.phase_hook(Path("/tmp/test"), "wrong", "pre-install")

    def test_preserved_old_fixture_is_only_bounded_positive_outcome(self):
        self.assertEqual(s.classify(73, s.FIXTURE + "|" + s.OLD_VERSION,
                                    b"old\n", TRACE), "ABORT_PRESERVED_OLD_FIXTURE")

    def test_success_exit_with_new_payload_is_not_safety_pass(self):
        self.assertEqual(s.classify(0, s.FIXTURE + "|" + s.NEW_VERSION,
                                    b"new\n", TRACE),
                         "REPLACED_DESPITE_INCOMING_PRE_INSTALL_REFUSAL")

    def test_partial_mutation_is_explicit_hazard(self):
        for name, payload in [(s.FIXTURE + "|" + s.OLD_VERSION, b"new\n"),
                              ("ABSENT", None),
                              (s.FIXTURE + "|" + s.NEW_VERSION, b"old\n")]:
            with self.subTest(name=name):
                self.assertEqual(s.classify(1, name, payload, TRACE),
                                 "PARTIAL_OR_INCONSISTENT_MUTATION_AFTER_REFUSAL")

    def test_missing_or_repeated_refusal_is_rejected(self):
        for rows in [TRACE[:2], TRACE + [s.REFUSAL_LINE],
                     [TRACE[1], TRACE[0], TRACE[2]]]:
            with self.subTest(rows=rows), self.assertRaises(s.Refusal):
                s.classify(1, s.FIXTURE + "|" + s.OLD_VERSION, b"old\n", rows)

    def test_post_install_after_refusal_is_recorded_as_bad_outcome(self):
        self.assertEqual(s.classify(0, s.FIXTURE + "|" + s.NEW_VERSION,
                                    b"new\n", TRACE + ["new:post-install"]),
                         "REPLACED_DESPITE_INCOMING_PRE_INSTALL_REFUSAL")

    def test_guest_identity_command_uses_supported_product_abi_flag(self):
        with mock.patch.object(s, "invoke", return_value=type("R", (), {
                 "returncode": 0, "stdout": "26.7\\n"})()) as command:
            self.assertEqual(s.successful(["opnsense-version", "-a"]).strip(), "26.7")
            command.assert_called_once_with(["opnsense-version", "-a"], None)

    def test_native_command_failure_works_for_single_argument(self):
        with mock.patch.object(s, "invoke", return_value=type("R", (), {
                 "returncode": 1, "stdout": ""})()):
            with self.assertRaisesRegex(s.Refusal, "NATIVE_COMMAND_FAILED:opnsense-version"):
                s.successful(["opnsense-version"])

    def test_non_target_refuses_before_any_mutation(self):
        class Linux:
            sysname = "Linux"
            machine = "x86_64"
        with mock.patch.object(s.os, "geteuid", return_value=0), \
             mock.patch.object(s.os, "uname", return_value=Linux()), \
             mock.patch.object(s, "invoke") as process:
            with self.assertRaisesRegex(s.Refusal, "ONLY_ROOT_DISPOSABLE"):
                s.run_vm()
            process.assert_not_called()


if __name__ == "__main__":
    unittest.main()
