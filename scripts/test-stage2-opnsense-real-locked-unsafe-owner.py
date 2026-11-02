#!/usr/bin/env python3
"""Fast contract tests; no native package or appliance mutations."""
import ast
from pathlib import Path
import unittest

SOURCE = Path(__file__).with_name("stage2-opnsense-real-locked-unsafe-owner.py")
TEXT = SOURCE.read_text()
TREE = ast.parse(TEXT)

class LockedPackageContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = {"Refusal": RuntimeError}
        nodes = [x for x in TREE.body if isinstance(x, ast.FunctionDef)
                 and x.name in ("need", "classify_locked_refusal")]
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), "exec"), env)
        cls.classify = staticmethod(env["classify_locked_refusal"])

    def test_genuine_denial_with_unchanged_state(self):
        self.assertEqual(self.classify(1, "old", "old", True, True),
                         "LOCKED_REAL_PACKAGE_FORCE_ADD_REFUSED_AND_UNCHANGED")

    def test_successful_pkg_operation_does_not_pass(self):
        with self.assertRaisesRegex(RuntimeError, "NATIVE_PKG_SUCCESS_DESPITE_LOCK"):
            self.classify(0, "old", "old", True, True)

    def test_changed_pkgdb_does_not_pass(self):
        with self.assertRaisesRegex(RuntimeError, "PKGDB_CHANGED_DESPITE_LOCK"):
            self.classify(7, "old", "new", True, True)

    def test_any_file_or_config_or_ipfw_delta_fails(self):
        with self.assertRaisesRegex(RuntimeError, "FILES_OR_CONFIG_OR_IPFW_CHANGED"):
            self.classify(7, "old", "old", True, False)

    def test_unlocked_state_does_not_pass(self):
        with self.assertRaisesRegex(RuntimeError, "NATIVE_LOCK_NOT_PRESERVED"):
            self.classify(7, "old", "old", False, True)

    def test_order_and_gate(self):
        needles = ["installer.install_and_verify(archive)", "inspector.snapshot(archive)",
                   "unsafe.add_test_orphan()", "status.returncode == 2",
                   'pkg(["lock", "-y", NAME])', "before = installed_record()",
                   'pkg(["add", "-f", str(successor)]', "after = installed_record()",
                   "verdict = classify_locked_refusal("]
        indices = [TEXT.index(n) for n in needles]
        self.assertEqual(indices, sorted(indices))
        for needle in ("GITHUB_ACTIONS", "native.gate()", "firmware.read_only_audit()",
                       "root_can_unlock_and_bypass", "fd9_atomic_admission_proven",
                       "safe_product_upgrade_accepted", "package_published"):
            self.assertIn(needle, TEXT)

    def test_no_unrelated_destructive_entrypoint(self):
        for forbidden in ("configctl", "kldunload", 'pkg(["unlock"', "zapret start",
                          "zapret stop", '"/sbin/ipfw", "-q", "flush"'):
            self.assertNotIn(forbidden, TEXT)

if __name__ == "__main__":
    unittest.main()
