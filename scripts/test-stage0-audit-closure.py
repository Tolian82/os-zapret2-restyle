#!/usr/bin/env python3
"""Negative tests for Stage 0 audit-only closure contract."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
S=Path(__file__).with_name("stage0-audit-closure.py")
spec=importlib.util.spec_from_file_location("closure",S)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Stage0ClosureTests(unittest.TestCase):
    def test_actual_repository(self):
        x=m.verify(m.ROOT)
        self.assertEqual(x["status"],"PASS_STAGE0_AUDIT_RECORD_ONLY")
        self.assertEqual(x["step_count"],16)
        self.assertFalse(x["full_product_acceptance"])
        self.assertFalse(x["foreign_repository_cleanup_permitted"])

    def test_missing_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(m.Refusal,"MISSING_RECORD"):
                m.verify(Path(td))

    def test_missing_step_rejected(self):
        original=m.read
        def fake(root,path):
            content=original(root,path)
            return content.replace("| 0.08 | AUDITED |","| 0.08 | UNKNOWN |") if path==m.RECORD else content
        with patch.object(m,"read",side_effect=fake):
            with self.assertRaisesRegex(m.Refusal,"STAGE0_MISSING_OR_REORDERED"):
                m.verify(m.ROOT)

    def test_foreign_owner_must_remain_negative(self):
        original=m.read
        def fake(root,path):
            content=original(root,path)
            return content.replace("| 0.12 | NEGATIVE_CLASSIFIED |","| 0.12 | AUDITED |") if path==m.RECORD else content
        with patch.object(m,"read",side_effect=fake):
            with self.assertRaisesRegex(m.Refusal,"FOREIGN_FILE_OWNERSHIP_MISCLASSIFIED"):
                m.verify(m.ROOT)

    def test_unqualified_future_plan_state_rejected(self):
        original=m.read
        def fake(root,path):
            content=original(root,path)
            if path==Path("docs/history/stages/native-packaging-2026-11/OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_PLAN.md"):
                return content.replace("**Stage 1 status: SOURCE/NATIVE-CI ACCEPTED**",
                                       "**Stage 1 status: UNKNOWN**")
            return content
        with patch.object(m,"read",side_effect=fake):
            with self.assertRaisesRegex(m.Refusal,"WRONG_PLAN_STATE"):
                m.verify(m.ROOT)

    def test_no_mutation_executables(self):
        s=S.read_text()
        for forbidden in ("subprocess.run(", "os.system(", "pkg delete ", "pkg add ",
                          "chmod(", "unlink(", "socket.connect("):
            self.assertNotIn(forbidden,s)

if __name__=="__main__":
    unittest.main()
