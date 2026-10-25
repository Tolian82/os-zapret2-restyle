#!/usr/bin/env python3
"""Fail-closed source-shape inspection of native Lua calls (not execution)."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/opnsense/scripts/OPNsense/Zapret"
sys.path.insert(0, str(SRC))
from extra_resources_lua_source_shape import inspect_lua_source_shape
from extra_resources_preflight import PreflightError

spec = importlib.util.spec_from_file_location(
    "common_fixture", ROOT / "scripts/test-voice-common-runtime.py"
)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class LuaSourceShapeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.upstream = self.root / "future"
        (self.upstream / "lua").mkdir(parents=True)
        (self.upstream / "files/fake").mkdir(parents=True)
        self.lib = self.upstream / "lua/zapret-lib.lua"
        self.antidpi = self.upstream / "lua/zapret-antidpi.lua"
        self.lib.write_text("function fake(ctx, d) return 0 end\n")
        self.antidpi.write_text("function multisplit(ctx, d) return fake(ctx,d) end\n")
        self.argv = self.root / "dvtws.args"

    def run_shape(self, extra="", init_inline=""):
        self.argv.write_text(
            "--lua-init=@" + str(self.lib) + "\n"
            "--lua-init=@" + str(self.antidpi) + "\n" +
            init_inline + "\n--filter-tcp=443\n" + extra
        )
        return inspect_lua_source_shape(self.argv, self.upstream)

    def test_global_declared_function_only_source_evidence(self):
        r = self.run_shape("--lua-desync=fake:blob=foo\n--new\n"
                           "--lua-desync=multisplit:pos=1\n")
        self.assertEqual(r["requested_calls"], 2)
        self.assertEqual(r["declaration_matches"], 2)
        self.assertEqual(r["unaccounted_decl_syntax"], 0)
        self.assertFalse(r["dynamic_source_indicators"])
        self.assertEqual(r["exports"], "unknown")
        self.assertEqual(r["transitive_dependencies"], "unknown")
        self.assertEqual(r["engine_lua_proof"], "not-run")
        self.assertEqual(r["compatibility"], "unknown")
        self.assertIs(r["authorized"], False)

    def test_missing_removed_export_cannot_be_promoted(self):
        r = self.run_shape("--lua-desync=extra_function\n")
        self.assertEqual(r["unaccounted_decl_syntax"], 1)
        self.assertEqual(r["declaration_matches"], 0)
        self.assertIs(r["authorized"], False)
        self.assertEqual(r["exports"], "unknown")

    def test_comments_and_strings_must_not_invent_exports(self):
        self.lib.write_text(
            "-- function vanished(x) end\n"
            "--[=[ function ghost(x) end ]=]\n"
            'note = "function fake_from_string(x) end"\n'
            "long = [==[ function longghost(x) end ]==]\n"
            "function genuine(x) end\n"
        )
        r = self.run_shape(
            "--lua-desync=vanished\n--lua-desync=ghost\n"
            "--lua-desync=fake_from_string\n--lua-desync=longghost\n"
            "--lua-desync=genuine\n"
        )
        self.assertEqual(r["declaration_matches"], 1)
        self.assertEqual(r["unaccounted_decl_syntax"], 4)

    def test_local_declaration_not_misreported_as_global(self):
        self.lib.write_text(
            "local function only_local(x) return x end\n"
            "local shadow = function (x) return x end\n"
            "function public(x) return x end\n"
        )
        r = self.run_shape(
            "--lua-desync=only_local\n--lua-desync=shadow\n"
            "--lua-desync=public\n"
        )
        self.assertEqual(r["declaration_matches"], 1)
        self.assertEqual(r["unaccounted_decl_syntax"], 2)

    def test_dynamic_lua_cannot_authorize_transitive_graph(self):
        self.lib.write_text(
            "function fake(x) return require('unknown_dynamic_extra') end\n"
            "rawset(_G, 'extra_export', function() end)\n"
        )
        r = self.run_shape("--lua-desync=fake\n")
        self.assertTrue(r["dynamic_source_indicators"])
        self.assertEqual(r["transitive_dependencies"], "unknown")
        self.assertFalse(r["authorized"])

    def test_inline_lua_remains_dynamic(self):
        r = self.run_shape("--lua-desync=fake\n", "--lua-init=extra=function()end")
        self.assertTrue(r["dynamic_source_indicators"])
        self.assertFalse(r["authorized"])

    def test_sources_changes_invalidate_shape_sha(self):
        first = self.run_shape("--lua-desync=fake\n")
        self.antidpi.write_text("function new_function(x) end\n")
        second = self.run_shape("--lua-desync=fake\n")
        self.assertNotEqual(first["source_shape_sha256"], second["source_shape_sha256"])
        self.assertFalse(second["authorized"])

    def test_bad_unterminated_source_fails_closed(self):
        self.lib.write_text("--[=[ unclosed\n")
        with self.assertRaises(PreflightError):
            self.run_shape("--lua-desync=fake\n")

    def test_native_compiler_original_argv_is_source_inspected(self):
        native_root = self.root / "native"
        native_root.mkdir()
        (self.upstream / "lua/zapret-auto.lua").write_text("function circular(ctx, d) end\n")
        out, release = fixture.build(
            native_root, (), upstream_root=self.upstream,
            traffic_args="--filter-tcp=443\n--filter-l7=tls",
            extra_args="",
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        report = inspect_lua_source_shape(release / "dvtws.args", self.upstream)
        self.assertEqual(report["engine_lua_proof"], "not-run")
        self.assertEqual(report["compatibility"], "unknown")
        self.assertFalse(report["authorized"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
