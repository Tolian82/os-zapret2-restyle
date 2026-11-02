#!/usr/bin/env python3
"""Offline fail-closed source contracts for disposable stock configd Unlock proof."""
import ast
from pathlib import Path
import time
from types import SimpleNamespace
import unittest

SOURCE = Path(__file__).with_name("stage2-opnsense-real-firmware-unlock-bypass.py")
TEXT = SOURCE.read_text(encoding="utf-8")
TREE = ast.parse(TEXT)

def extract(*names):
    nodes = [n for n in TREE.body if isinstance(n, ast.FunctionDef)
             and n.name in names]
    if len(nodes) != len(names):
        raise AssertionError("REQUIRED_TESTED_FUNCTION_MISSING")
    scope = {"Refusal": RuntimeError, "time": time}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), "exec"),
         scope)
    return scope

class GenuineFirmwareUnlockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        scope = extract("need", "wait_until_unlocked",
                        "classify_unlock_bypass")
        cls.classify = staticmethod(scope["classify_unlock_bypass"])
        cls.wait = staticmethod(scope["wait_until_unlocked"])

    def test_exact_unsafe_replacement_is_not_product_acceptance(self):
        self.assertEqual(
            self.classify(True, True, 0, "old", "successor", "successor",
                          True, True),
            "OBSERVED_STOCK_CONFIGD_UNLOCK_THEN_UNSAFE_NATIVE_PKG_REPLACEMENT")

    def test_refuses_missing_or_ineffective_unlock(self):
        for locked, unlocked in ((False, True), (True, False)):
            with self.subTest(locked=locked, unlocked=unlocked):
                with self.assertRaisesRegex(RuntimeError,
                                            "UNLOCK_PRE_PKG_STATE_NOT_PROVEN"):
                    self.classify(locked, unlocked, 0, "old", "new",
                                  "new", True, True)

    def test_refuses_pre_pkg_state_change(self):
        with self.assertRaisesRegex(RuntimeError, "UNLOCK_PRE_PKG_STATE_NOT_PROVEN"):
            self.classify(True, True, 0, "old", "new", "new", True, False)

    def test_refuses_package_failure_or_old_identity(self):
        for rc, observed in ((1, "old"), (1, "new"), (0, "old"),
                             (0, "unknown")):
            with self.subTest(rc=rc, observed=observed):
                with self.assertRaisesRegex(RuntimeError,
                                            "NO_NATIVE_REPLACEMENT_AFTER_STOCK_UNLOCK"):
                    self.classify(True, True, rc, "old", "new",
                                  observed, True, True)

    def test_refuses_unobserved_authentic_hook_refusal(self):
        with self.assertRaisesRegex(RuntimeError,
                                    "AUTHENTIC_PREINSTALL_REFUSAL_NOT_OBSERVED"):
            self.classify(True, True, 0, "old", "new", "new", False, True)

    def test_exact_pkg_lock_metadata_zero_one_and_refusal(self):
        scope = extract("need", "package_locked")
        scope["NAME"] = "os-zapret2-restyle"
        check = scope["package_locked"]
        expected = ["query", "%k", "os-zapret2-restyle"]
        for raw, want in (("1\n", True), ("0\n", False)):
            with self.subTest(raw=raw):
                def query(args):
                    self.assertEqual(args, expected)
                    return SimpleNamespace(returncode=0, stdout=raw)
                scope["locked"] = SimpleNamespace(pkg=query)
                self.assertIs(check(), want)
        for raw, rc in (("", 0), ("2", 0), ("0\n1", 0), ("0", 1)):
            with self.subTest(raw=raw, rc=rc):
                scope["locked"] = SimpleNamespace(pkg=lambda args:
                    SimpleNamespace(returncode=rc, stdout=raw))
                with self.assertRaisesRegex(RuntimeError,
                                            "TARGET_PACKAGE_LOCK_METADATA_UNAVAILABLE"):
                    check()

    def test_bounded_asynchronous_unlock_poll(self):
        calls = []
        self.assertTrue(self.wait(lambda: len(calls) < 2,
                                  attempts=3, delay=0, sleep=lambda _: calls.append(1)))
        self.assertEqual(len(calls), 2)
        self.assertFalse(self.wait(lambda: True, attempts=2, delay=0,
                                   sleep=lambda _: None))
        with self.assertRaisesRegex(RuntimeError, "UNBOUNDED_UNLOCK_POLL"):
            self.wait(lambda: True, attempts=100)

    def test_real_native_action_order_and_guards(self):
        required = (
            "clean.plugin_absent()", "stopped.check_old_archive(archive)",
            "native.build()", "installer.install_and_verify(archive)",
            "inspector.snapshot(archive)", "firmware.read_only_audit()",
            "foreign.activate_kernel(inspector)", "unsafe.add_test_orphan()",
            'locked.pkg(["lock", "-y", NAME])',
            "pkg_before = locked.installed_record()",
            '["/usr/local/sbin/configctl", "firmware", "unlock",',
            "wait_until_unlocked(package_locked)",
            'locked.pkg(["add", "-f", str(successor)]',
            "STAGE2_CONFIGD_UNLOCK_PRE_CLEANUP=", "unsafe.remove_test_orphan()"
        )
        indices = [TEXT.index(part) for part in required]
        self.assertEqual(indices, sorted(indices))
        for marker in ("GITHUB_ACTIONS", "DISPOSABLE_STOCK_FIRMWARE_UNLOCK",
                       "browser_web_gui_click_tested", "False",
                       "lh08_ac11_safe_upgrade_accepted",
                       "owner_appliance_modified", "package_published"):
            self.assertIn(marker, TEXT)

    def test_no_direct_unlock_or_owner_hardware_entrypoint(self):
        for forbidden in ('locked.pkg(["unlock"', 'unsafe.remove_test_orphan();',
                          '"configctl", "zapret", "stop"', 'kldunload',
                          '"ipfw", "-q", "flush"'):
            self.assertNotIn(forbidden, TEXT)

if __name__ == "__main__":
    unittest.main()
