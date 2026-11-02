#!/usr/bin/env python3
"""Source-only positive and fail-closed contracts; no root pkg required."""
import ast
from pathlib import Path
import unittest

SOURCE = Path(__file__).with_name("stage2-opnsense-real-unsafe-owner-replacement.py")
TEXT = SOURCE.read_text(encoding="utf-8")
TREE = ast.parse(TEXT)


class UnsafePkgContract(unittest.TestCase):
    def test_classifier_distinguishes_pkgdb_from_hook_exit(self):
        env = {"Refusal": RuntimeError}
        nodes = [n for n in TREE.body if isinstance(n, ast.FunctionDef)
                 and n.name in ("need", "classify")]
        exec(compile(ast.Module(body=nodes, type_ignores=[]),
                     str(SOURCE), "exec"), env)
        classifier = env["classify"]
        self.assertEqual(classifier("pkg|old", "pkg|new", "pkg|old", True),
                         "OBSERVED_PKG_PRESERVED_OLD_AFTER_HOOK_REFUSAL")
        self.assertEqual(classifier("pkg|old", "pkg|new", "pkg|new", True),
                         "OBSERVED_PKG_REPLACED_DESPITE_HOOK_REFUSAL")
        with self.assertRaisesRegex(RuntimeError, "PREINSTALL_REFUSAL_NOT_OBSERVED"):
            classifier("pkg|old", "pkg|new", "pkg|new", False)
        with self.assertRaisesRegex(RuntimeError, "UNKNOWN_PACKAGE_STATE"):
            classifier("pkg|old", "pkg|new", "foreign|other", True)

    def test_guest_gate_and_contained_foreign_kernel(self):
        for marker in ("ZAPRET2_STAGE2_REAL_UNSAFE_OWNER_PKG",
                       "ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK",
                       "ZAPRET2_NATIVE_BUILD_CI", "GITHUB_ACTIONS",
                       "native.gate()", "add_test_orphan()",
                       "only_orphan_loopback_divert()",
                       "remove_test_orphan()",
                       "only_orphan_loopback_divert()",
                       "ORPHAN_RULE = 19000",
                       "ORPHAN_PORT = 65431",
                       "ipfw_ipdivert_modules_left_loaded_in_disposable_guest",
                       "foreign.only_default(current.stdout)"):
            self.assertIn(marker, TEXT)
        for forbidden in ("configctl", "zapret start", "zapret stop",
                          "foreign.foreign_rule_add()", "kldunload"):
            self.assertNotIn(forbidden, TEXT)

    def test_real_original_status_and_pkgdb_observed(self):
        self.assertLess(TEXT.index("observed_status == 2"),
                        TEXT.index('"add", "-f", str(successor)'))
        self.assertLess(TEXT.index("after_id = installed_identity()"),
                        TEXT.index("verdict = classify"))
        self.assertIn('"root_pkg_atomic_refusal_proved": False', TEXT)
        self.assertIn('"owner_appliance_modified": False', TEXT)
        self.assertIn('"new_package_published": False', TEXT)


if __name__ == "__main__":
    unittest.main()
