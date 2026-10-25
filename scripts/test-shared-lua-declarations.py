#!/usr/bin/env python3
"""One lexical Lua policy feeds Strategy Lab and prospective resource removal.

This never executes Lua; declarations, even when present, are NOT runtime proof.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/opnsense/scripts/OPNsense/Zapret"))
from strategy_lab_py.lua_declarations import (
    inspect_lua_declarations,
    has_explicit_top_level_function,
    LuaSourceEvidenceError,
)


class SharedLuaDeclarationTests(unittest.TestCase):
    def test_plain_global_matches_both_consumers(self):
        data = b"function free_export(ctx, desync) end\n"
        detail = inspect_lua_declarations(data)
        self.assertIn("free_export", detail["global_declarations"])
        self.assertIn("free_export", detail["line_start_functions"])
        self.assertTrue(has_explicit_top_level_function(data, "free_export"))
        self.assertFalse(detail["dynamic_source"])

    def test_global_assignment_only_suggests_declaration_to_remove(self):
        data = b"inline_export = function(ctx) end\n"
        detail = inspect_lua_declarations(data)
        self.assertIn("inline_export", detail["global_declarations"])
        self.assertNotIn("inline_export", detail["line_start_functions"])
        self.assertFalse(has_explicit_top_level_function(data, "inline_export"))

    def test_string_and_comment_fakes_are_ineligible_everywhere(self):
        data = (
            b"-- function phony() end\n"
            b"--[=[ function concealed() end ]=]\n"
            b"doc = 'function fake_str() end'\n"
            b"multi = [==[ function hidden() end ]==]\n"
            b"function genuine() end\n"
        )
        detail = inspect_lua_declarations(data)
        self.assertEqual(detail["global_declarations"], frozenset(["genuine"]))
        self.assertEqual(detail["line_start_functions"], frozenset(["genuine"]))
        for name in ("phony", "concealed", "fake_str", "hidden"):
            self.assertFalse(has_explicit_top_level_function(data, name))
        self.assertTrue(has_explicit_top_level_function(data, "genuine"))

    def test_local_functions_never_categorized_as_globals(self):
        data = b"local function inner() end\nlocal shadow = function() end\nfunction outer() end\n"
        detail = inspect_lua_declarations(data)
        self.assertEqual(detail["global_declarations"], frozenset(["outer"]))
        self.assertEqual(detail["line_start_functions"], frozenset(["outer"]))
        self.assertFalse(has_explicit_top_level_function(data, "inner"))

    def test_dynamic_runtime_dependency_does_not_become_proof(self):
        data = b"function main() return require('extra') end\n"
        detail = inspect_lua_declarations(data)
        self.assertTrue(detail["dynamic_source"])
        self.assertTrue(has_explicit_top_level_function(data, "main"))
        # Positive declaration hint is NEVER proof that require('extra') works.

    def test_broken_comment_utf8_and_oversize_fail_closed(self):
        for data in (b"--[=[ never closed", b"\xfffunction maybe() end",
                     b"a" * (4 * 1024 * 1024 + 1), b""):
            with self.subTest(data=data[:20]):
                with self.assertRaises(LuaSourceEvidenceError):
                    inspect_lua_declarations(data)
                self.assertFalse(has_explicit_top_level_function(data, "maybe"))

    def test_invalid_export_name_never_eligible(self):
        self.assertFalse(has_explicit_top_level_function(b"function valid() end", "../valid"))
        self.assertFalse(has_explicit_top_level_function(b"function valid() end", "valid();"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
