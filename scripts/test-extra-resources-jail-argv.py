#!/usr/bin/env python3
"""Strict relocation of native, already-attested one-token-per-line argv."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/opnsense/scripts/OPNsense/Zapret"))
from extra_resources_jail_argv import relocate_direct_native_argv
from extra_resources_preflight import PreflightError


class NativeJailArgvTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "standard"
        (self.root / "lua").mkdir(parents=True)
        (self.root / "files/fake").mkdir(parents=True)
        (self.root / "lua/zapret-lib.lua").write_text("function noop() end\n")
        (self.root / "files/fake/stock.bin").write_bytes(b"PAYLOAD")

    def rewrite(self, extra=""):
        argv = "--port=19000\n--lua-init=@" + str(self.root / "lua/zapret-lib.lua") + "\n" + extra
        return relocate_direct_native_argv(argv.encode("utf8"), self.root)

    def test_exact_native_new_boundaries_and_blob_preserved(self):
        source = "--filter-tcp=443\n--new\n--filter-udp=443\n--blob=stock:@" + str(self.root / "files/fake/stock.bin") + "\n--lua-desync=fake:blob=stock\n"
        mapped, proof = self.rewrite(source)
        self.assertIn(b"--lua-init=@/upstream/lua/zapret-lib.lua\n", mapped)
        self.assertIn(b"--blob=stock:@/upstream/files/fake/stock.bin\n", mapped)
        self.assertIn(b"--new\n--filter-udp=443\n", mapped)
        self.assertEqual(proof["native_profiles"], 2)
        self.assertEqual(proof["direct_blob_files"], 1)
        self.assertFalse(proof["authorized"])
        self.assertFalse(proof["runnable"])
        self.assertEqual(proof["engine_lua_proof"], "not-run")

    def test_host_runtime_argument_remains_unmapped_and_blocks_runnable(self):
        mapped, report = self.rewrite("--hostlist-exclude=/usr/local/etc/zapret2/runtime-v2/exclude.txt\n")
        self.assertIn(b"--hostlist-exclude=/usr/local/etc/zapret2/runtime-v2", mapped)
        self.assertEqual(report["unmapped_path_tokens"], 1)
        self.assertFalse(report["runnable"])

    def test_unknown_inline_lua_and_unsafe_binaries_rejected(self):
        base = "--lua-init=print(1)\n"
        with self.assertRaisesRegex(PreflightError, "inline"):
            relocate_direct_native_argv(base.encode(), self.root)
        with self.assertRaisesRegex(PreflightError, "BLOB"):
            self.rewrite("--blob=stock:unsafe\n")
        with self.assertRaisesRegex(PreflightError, "BLOB"):
            self.rewrite("--blob=../danger:@" + str(self.root / "files/fake/stock.bin") + "\n")

    def test_reject_extra_and_symlink_resources(self):
        other = Path(self.temp.name) / "extra.lua"
        other.write_bytes(b"lua")
        with self.assertRaises(PreflightError):
            self.rewrite("--lua-init=@" + str(other) + "\n")
        path = self.root / "lua/zapret-lib.lua"
        path.unlink()
        path.symlink_to(other)
        with self.assertRaises(PreflightError):
            self.rewrite()

    def test_reject_path_traversal_missing_file_and_invalid_arg_structure(self):
        with self.assertRaises(PreflightError):
            self.rewrite("--blob=x:@" + str(self.root / "files/fake/missing.bin") + "\n")
        with self.assertRaises(PreflightError):
            self.rewrite("--lua-init=@" + str(self.root / "lua/../lua/zapret-lib.lua") + "\n")
        with self.assertRaises(PreflightError):
            self.rewrite("--new\n\n")
        with self.assertRaises(PreflightError):
            self.rewrite("--new\r\n")
        with self.assertRaises(PreflightError):
            self.rewrite("--filter-tcp=443\x00\n")

    def test_no_initializers_cannot_be_positive(self):
        with self.assertRaisesRegex(PreflightError, "missing standard"):
            relocate_direct_native_argv(b"--port=19000\n--new\n", self.root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
