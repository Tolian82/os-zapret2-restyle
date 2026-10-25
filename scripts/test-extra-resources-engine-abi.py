#!/usr/bin/env python3
"""FreeBSD ELF64 ABI hints for installed dvtws2: no executable invocation."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import struct
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "src/opnsense/scripts/OPNsense/Zapret"
sys.path.insert(0, str(MOD))
from extra_resources_engine_abi import inspect_installed_engine_abi, EngineABIError


def native_elf(*libraries: str, no_dynamic: bool = False) -> bytes:
    """Minimal bounded AMD64 FreeBSD ELF whose DT_NEEDED names are real data."""
    data = bytearray(4096)
    data[:16] = b"\x7fELF\x02\x01\x01\x09" + b"\x00" * 8
    struct.pack_into("<HHIQQQIHHHHHH", data, 16,
                     2, 62, 1, 0x401000, 64, 0, 0, 64, 56,
                     1 if no_dynamic else 2, 0, 0, 0)
    struct.pack_into("<IIQQQQQQ", data, 64, 1, 5, 0, 0x400000, 0, 4096, 4096, 4096)
    if not no_dynamic:
        count = len(libraries) + 3
        struct.pack_into("<IIQQQQQQ", data, 120, 2, 4, 0x200,
                         0x400200, 0, count * 16, count * 16, 16)
        names = bytearray(b"\x00")
        offsets = []
        for lib in libraries:
            offsets.append(len(names))
            names.extend(lib.encode("ascii") + b"\x00")
        data[0x400:0x400 + len(names)] = names
        off = 0x200
        for val in offsets:
            struct.pack_into("<QQ", data, off, 1, val)
            off += 16
        struct.pack_into("<QQ", data, off, 5, 0x400400)
        struct.pack_into("<QQ", data, off + 16, 10, len(names))
        struct.pack_into("<QQ", data, off + 32, 0, 0)
    return bytes(data)


class EngineABIReadOnlyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.engine = Path(self.tmp.name) / "dvtws2"

    def save(self, data: bytes):
        self.engine.write_bytes(data)
        self.engine.chmod(0o755)

    def inspect(self):
        return inspect_installed_engine_abi(self.engine)

    def assert_not_proven(self, result):
        self.assertEqual(result["engine_lua_proof"], "not-run")
        self.assertEqual(result["compatibility"], "unknown")
        self.assertIs(result["authorized"], False)

    def test_missing_engine_is_unknown(self):
        r = self.inspect()
        self.assertEqual(r["state"], "engine-not-installed")
        self.assertEqual(r["abi"], "unknown")
        self.assertIsNone(r["engine_sha256"])
        self.assert_not_proven(r)

    def test_luajit_abi_hint_never_proves_runtime_export(self):
        binary = native_elf("libc.so.7", "libluajit-5.1.so.2")
        self.save(binary)
        r = self.inspect()
        self.assertEqual(r["state"], "engine-elf-abi-hint-only")
        self.assertEqual(r["abi"], "luajit-5.1")
        self.assertEqual(r["engine_sha256"], hashlib.sha256(binary).hexdigest())
        self.assert_not_proven(r)

    def test_dynamic_regular_lua_and_static_engine_remain_unknown(self):
        self.save(native_elf("liblua-5.4.so.0"))
        a = self.inspect()
        self.assertEqual(a["abi"], "lua-5.4")
        self.assert_not_proven(a)
        self.save(native_elf(no_dynamic=True))
        b = self.inspect()
        self.assertEqual(b["abi"], "unknown")
        self.assert_not_proven(b)
        self.assertNotEqual(a["engine_sha256"], b["engine_sha256"])

    def test_multiple_runtime_abi_no_positive(self):
        self.save(native_elf("liblua-5.4.so.0", "libluajit-5.1.so.2"))
        r = self.inspect()
        self.assertEqual(r["abi"], "unknown")
        self.assert_not_proven(r)

    def test_no_linked_lua_does_not_prove_lua_absent(self):
        self.save(native_elf("libc.so.7"))
        r = self.inspect()
        self.assertEqual(r["abi"], "unknown")
        self.assert_not_proven(r)

    def test_invalid_elf_and_truncated_phdr_fail_closed(self):
        self.save(b"bad" * 128)
        with self.assertRaises(EngineABIError):
            self.inspect()
        data = bytearray(native_elf("libluajit-5.1.so.2"))
        struct.pack_into("<Q", data, 32, len(data) - 12)
        self.save(bytes(data))
        with self.assertRaises(EngineABIError):
            self.inspect()

    def test_invalid_needed_offset_and_ambiguous_address_fail_closed(self):
        data = bytearray(native_elf("libluajit-5.1.so.2"))
        struct.pack_into("<Q", data, 0x208, 9999)
        self.save(bytes(data))
        with self.assertRaises(EngineABIError):
            self.inspect()
        data = bytearray(native_elf("libluajit-5.1.so.2"))
        struct.pack_into("<Q", data, 0x218, 0xDEADBEEF)
        self.save(bytes(data))
        with self.assertRaises(EngineABIError):
            self.inspect()

    def test_symlink_not_executable_and_oversize_refuse(self):
        real = Path(self.tmp.name) / "real"
        real.write_bytes(native_elf("libluajit-5.1.so.2"))
        real.chmod(0o755)
        self.engine.symlink_to(real)
        with self.assertRaises(EngineABIError):
            self.inspect()
        self.engine.unlink()
        self.save(native_elf("libluajit-5.1.so.2"))
        self.engine.chmod(0o644)
        with self.assertRaises(EngineABIError):
            self.inspect()
        self.engine.chmod(0o755)
        with self.engine.open("ab") as stream:
            stream.truncate(64 * 1024 * 1024 + 1)
        with self.assertRaises(EngineABIError):
            self.inspect()

    def test_installed_path_replaced_during_fd_read_fails_closed(self):
        self.save(native_elf("libluajit-5.1.so.2"))
        replacement = Path(self.tmp.name) / "replacement"
        replacement.write_bytes(native_elf("liblua-5.4.so.0"))
        replacement.chmod(0o755)
        original_read = os.read
        swapped = False

        def replace_after_first_read(fd, size):
            nonlocal swapped
            chunk = original_read(fd, size)
            if not swapped:
                swapped = True
                os.replace(replacement, self.engine)
            return chunk

        with mock.patch("extra_resources_engine_abi.os.read",
                        side_effect=replace_after_first_read):
            with self.assertRaisesRegex(EngineABIError, "changed during ABI read"):
                self.inspect()
        self.assertTrue(swapped)

    def test_installed_path_unlinked_during_fd_read_fails_closed(self):
        self.save(native_elf("libluajit-5.1.so.2"))
        original_read = os.read
        removed = False

        def unlink_after_first_read(fd, size):
            nonlocal removed
            chunk = original_read(fd, size)
            if not removed:
                removed = True
                self.engine.unlink()
            return chunk

        with mock.patch("extra_resources_engine_abi.os.read",
                        side_effect=unlink_after_first_read):
            with self.assertRaisesRegex(EngineABIError, "path changed during ABI read"):
                self.inspect()
        self.assertTrue(removed)

    def test_does_not_execute_binary_or_start_network_probe(self):
        source = (MOD / "extra_resources_engine_abi.py").read_text()
        self.assertNotIn("subprocess", source.split("\nfrom __future__", 1)[-1])
        for token in ("os.system(", "os.exec", "socket.socket(", "ldd ", "dlopen("):
            self.assertNotIn(token, source.split("\ndef inspect_installed_engine_abi(", 1)[-1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
