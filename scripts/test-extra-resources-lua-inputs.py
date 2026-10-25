#!/usr/bin/env python3
"""Original generated argv Lua/BIN provenance: no engine startup, no mutation."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/opnsense/scripts/OPNsense/Zapret"
sys.path.insert(0, str(SRC))
from extra_resources_lua_inputs import attest_candidate_lua_files
from extra_resources_preflight import PreflightError

spec = importlib.util.spec_from_file_location(
    "common_fixture", ROOT / "scripts/test-voice-common-runtime.py"
)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class CompiledLuaReferencesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / "future"
        (self.root / "lua").mkdir(parents=True)
        (self.root / "files/fake").mkdir(parents=True)
        for name in ("zapret-lib.lua", "zapret-antidpi.lua", "zapret-auto.lua"):
            (self.root / "lua" / name).write_text("function noop(ctx,d) return 0 end\n")
        (self.root / "files/fake/stock.bin").write_bytes(b"STOCK")
        self.argv = self.base / "dvtws.args"
        self.prefix = "\n".join(
            "--lua-init=@" + str(self.root / "lua" / name)
            for name in ("zapret-lib.lua", "zapret-antidpi.lua", "zapret-auto.lua")
        ) + "\n--filter-tcp=443\n"

    def attest(self, tail=""):
        self.argv.write_text(self.prefix + tail)
        return attest_candidate_lua_files(self.argv, self.root)

    def test_three_native_initializers_multinew_and_stock_blob(self):
        report = self.attest(
            "--lua-desync=fake:blob=stock\n--new\n--filter-udp=443\n"
            "--blob=stock:@" + str(self.root / "files/fake/stock.bin") + "\n"
            "--lua-desync=multisplit:pos=1\n"
        )
        self.assertEqual(report["lua_init_files"], 3)
        self.assertEqual(report["blob_files"], 1)
        self.assertEqual(report["desync_calls"], 2)
        self.assertEqual(report["state"], "native-lua-direct-files-attested")
        self.assertEqual(len(report["resource_witness_sha256"]), 64)
        self.assertEqual(report["engine_lua_proof"], "not-run")
        self.assertEqual(report["exports"], "unknown")
        self.assertEqual(report["transitive_dependencies"], "unknown")
        self.assertEqual(report["compatibility"], "unknown")
        self.assertIs(report["authorized"], False)

    def test_unknown_lua_desync_export_stays_unknown(self):
        report = self.attest("--lua-desync=removed_implicit_export\n")
        self.assertEqual(report["desync_calls"], 1)
        self.assertIs(report["authorized"], False)
        self.assertEqual(report["exports"], "unknown")

    def test_inline_initializer_remains_unknown_without_execution(self):
        report = self.attest("--lua-init=do_stuff()\n--lua-desync=noop\n")
        self.assertEqual(report["inline_lua_initializers"], 1)
        self.assertEqual(report["engine_lua_proof"], "not-run")

    def test_missing_future_lua_rejected(self):
        (self.root / "lua/zapret-auto.lua").unlink()
        with self.assertRaises(PreflightError):
            self.attest()

    def test_live_extra_lua_ref_rejected_even_if_present(self):
        live = self.base / "production"
        live.mkdir()
        (live / "extra.lua").write_text("function myfake() end")
        with self.assertRaisesRegex(PreflightError, "escapes upstream"):
            self.attest("--lua-init=@" + str(live / "extra.lua") + "\n")

    def test_extra_blob_outside_future_view_refused(self):
        extra = self.base / "removed.bin"
        extra.write_bytes(b"EXTRA")
        with self.assertRaisesRegex(PreflightError, "escapes upstream"):
            self.attest("--blob=extra:@" + str(extra) + "\n")

    def test_symlink_to_extra_is_not_followed(self):
        victim = self.base / "extra.lua"
        victim.write_text("function unsafe() end")
        future = self.root / "lua/zapret-auto.lua"
        future.unlink()
        future.symlink_to(victim)
        with self.assertRaises(PreflightError):
            self.attest()

    def test_traversal_and_nested_resources_rejected(self):
        (self.root / "lua/nested").mkdir()
        (self.root / "lua/nested/lib.lua").write_text("-- hidden")
        with self.assertRaises(PreflightError):
            self.attest("--lua-init=@" + str(self.root / "lua/nested/lib.lua") + "\n")
        with self.assertRaises(PreflightError):
            self.attest("--lua-init=@" + str(self.root) + "/lua/../lua/zapret-auto.lua\n")

    def test_mutating_future_lua_changes_witness_without_authorizing(self):
        first = self.attest()
        (self.root / "lua/zapret-auto.lua").write_text("function after() end\n")
        second = self.attest()
        self.assertNotEqual(first["resource_witness_sha256"], second["resource_witness_sha256"])
        self.assertFalse(second["authorized"])

    def test_no_lua_initializer_is_not_positive(self):
        self.argv.write_text("--lua-desync=fake\n")
        with self.assertRaisesRegex(PreflightError, "no verified"):
            attest_candidate_lua_files(self.argv, self.root)

    def test_actual_native_compiler_argv_has_attestable_initializers(self):
        sample = self.base / "sample"
        sample.mkdir()
        out, release = fixture.build(
            sample, (), upstream_root=self.root,
            traffic_args="--filter-tcp=443\n--filter-l7=tls\n--new\n"
                         "--filter-udp=443\n--filter-l7=quic",
            extra_args="--blob=stock",
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        evidence = attest_candidate_lua_files(release / "dvtws.args", self.root)
        self.assertEqual(evidence["lua_init_files"], 3)
        self.assertEqual(evidence["blob_files"], 1)
        self.assertEqual(evidence["compatibility"], "unknown")
        self.assertFalse(evidence["authorized"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
