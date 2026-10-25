#!/usr/bin/env python3
"""FreeBSD PT_INTERP / dynamic path directives: no-exec boundary evidence."""
import hashlib
import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "src/opnsense/scripts/OPNsense/Zapret"))
from extra_resources_jail_loader import (
    STANDARD_INTERPRETER, attest_static_loader_input,
)
from extra_resources_jail_inputs import (
    _read_pinned, staged_inert_jail_inputs, JailInputError,
)
from extra_resources_preflight import PreflightError

spec = importlib.util.spec_from_file_location(
    "fixture", BASE / "scripts/test-extra-resources-engine-abi.py"
)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


def with_interp(data: bytes, path: str = STANDARD_INTERPRETER) -> bytes:
    """Extend the existing bounded REAL-layout ELF fixture with PT_INTERP."""
    result = bytearray(data)
    n = struct.unpack_from("<H", result, 56)[0]
    assert n <= 2
    interp = path.encode("ascii") + b"\x00"
    struct.pack_into("<H", result, 56, n + 1)
    struct.pack_into("<IIQQQQQQ", result, 64 + n * 56,
                     3, 4, 0x700, 0x400700, 0, len(interp), len(interp), 1)
    result[0x700:0x700 + len(interp)] = interp
    return bytes(result)


def with_dynamic_tag(data: bytes, tag: int) -> bytes:
    result = bytearray(data)
    # Exactly one DT_NEEDED: [NEEDED, STRTAB, STRSZ, NULL] -> add tag before NULL.
    struct.pack_into("<QQ", result, 0x230, tag, 0)
    struct.pack_into("<QQ", result, 0x240, 0, 0)
    struct.pack_into("<Q", result, 120 + 32, 5 * 16)
    struct.pack_into("<Q", result, 120 + 40, 5 * 16)
    return bytes(result)


class LoaderInputTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / "sysroot"
        (self.root / "libexec").mkdir(parents=True)
        self.interp = self.root / "libexec/ld-elf.so.1"
        self.interp.write_bytes(fixture.native_elf(no_dynamic=True))
        self.engine = with_interp(fixture.native_elf("libfirst.so.1"))
        self.library = fixture.native_elf(no_dynamic=True)

    def audit(self, engine=None, libraries=None):
        return attest_static_loader_input(
            self.engine if engine is None else engine,
            {"lib/libfirst.so.1": self.library} if libraries is None else libraries,
            self.root, _read_pinned,
        )

    def test_standard_interpreter_pinned_not_loader_execution(self):
        evidence, data = self.audit()
        self.assertEqual(evidence["elf_interpreter"], STANDARD_INTERPRETER)
        self.assertEqual(evidence["dynamic_library_closure"], "unknown")
        self.assertEqual(evidence["loader_path_resolution"], "unproven")
        self.assertEqual(evidence["engine_lua_proof"], "not-run")
        self.assertEqual(data["libexec/ld-elf.so.1"], self.interp.read_bytes())
        self.assertEqual(len(evidence["elf_loader_witness_sha256"]), 64)
        self.assertFalse(evidence["runnable"])
        self.assertIs(evidence["authorized"], False)

    def test_missing_interpreter_is_not_a_positive_loader_proof(self):
        report, data = self.audit(engine=fixture.native_elf("libfirst.so.1"))
        self.assertEqual(report["elf_interpreter"], "absent-unproven")
        self.assertEqual(data, {})
        self.assertFalse(report["authorized"])

    def test_missing_symlinked_world_writable_loader_rejected(self):
        self.interp.unlink()
        with self.assertRaisesRegex(PreflightError, "interpreter unavailable"):
            self.audit()
        self.interp.write_bytes(self.library)
        self.interp.chmod(0o666)
        with self.assertRaisesRegex(PreflightError, "unsafe FreeBSD interpreter inode"):
            self.audit()
        self.interp.chmod(0o644)
        self.interp.unlink()
        outside = self.base / "outside"
        outside.write_bytes(self.library)
        self.interp.symlink_to(outside)
        with self.assertRaisesRegex(PreflightError, "unsafe FreeBSD interpreter inode"):
            self.audit()

    def test_nonstandard_duplicate_and_malformed_interpreter_fail(self):
        with self.assertRaisesRegex(PreflightError, "loader metadata incompatible"):
            self.audit(engine=with_interp(fixture.native_elf("libfirst.so.1"),
                                          "/tmp/evil-loader"))
        twice = bytearray(self.engine)
        # Fourth PHDR: add a second PT_INTERP.
        struct.pack_into("<H", twice, 56, 4)
        struct.pack_into("<IIQQQQQQ", twice, 64 + 3 * 56, 3, 4,
                         0x700, 0x400700, 0, 8, 8, 1)
        with self.assertRaisesRegex(PreflightError, "loader metadata incompatible"):
            self.audit(engine=bytes(twice))
        missing_nul = bytearray(self.engine)
        missing_nul[0x700 + len(STANDARD_INTERPRETER)] = ord("X")
        with self.assertRaises(PreflightError):
            self.audit(engine=bytes(missing_nul))

    def test_rpath_runpath_engine_and_nested_lib_fail_closed(self):
        for tag in (15, 29, 0x7fffffff, 0x6ffffefc):
            with self.subTest(tag=tag), self.assertRaisesRegex(
                PreflightError, "loader metadata incompatible"
            ):
                self.audit(engine=with_interp(
                    with_dynamic_tag(fixture.native_elf("libfirst.so.1"), tag)))
        nested = with_dynamic_tag(fixture.native_elf("libc.so.7"), 29)
        with self.assertRaisesRegex(PreflightError, "loader metadata incompatible"):
            self.audit(libraries={"lib/libfirst.so.1": nested})
        with self.assertRaises(PreflightError):
            self.audit(libraries={"lib/libfirst.so.1": self.engine})

    def test_snapshot_rechecks_pinned_loader_and_staged_bytes(self):
        upstream = self.base / "upstream"
        (upstream / "lua").mkdir(parents=True)
        (upstream / "files/fake").mkdir(parents=True)
        (upstream / "lua/zapret-lib.lua").write_bytes(b"function noop() end\n")
        installed = self.base / "dvtws2"
        installed.write_bytes(self.engine)
        installed.chmod(0o755)
        argv = self.base / "dvtws.args"
        argv.write_text("--lua-init=@" + str(upstream / "lua/zapret-lib.lua") + "\n")
        (self.root / "lib").mkdir()
        (self.root / "lib/libfirst.so.1").write_bytes(self.library)
        workspace = self.base / "private"
        workspace.mkdir(mode=0o700)
        opts = dict(
            expected_engine_sha256=hashlib.sha256(installed.read_bytes()).hexdigest(),
            expected_argv_sha256=hashlib.sha256(argv.read_bytes()).hexdigest(),
            check_lifecycle=lambda: None,
            library_source_root=self.root,
        )
        with staged_inert_jail_inputs(installed, argv, upstream, workspace, **opts) as (report, bundle):
            self.assertEqual(report["elf_interpreter"], STANDARD_INTERPRETER)
            self.assertEqual((bundle / "elf-interpreter/libexec/ld-elf.so.1").read_bytes(),
                             self.interp.read_bytes())
            self.assertEqual(
                (bundle / "elf-interpreter/libexec/ld-elf.so.1").stat().st_mode & 0o111, 0
            )
            staged = bundle
        self.assertFalse(staged.exists())
        with self.assertRaisesRegex(JailInputError, "ELF interpreter source changed"):
            with staged_inert_jail_inputs(installed, argv, upstream, workspace, **opts):
                self.interp.write_bytes(with_interp(self.library))
        self.assertEqual(list(workspace.iterdir()), [])

    def test_no_subprocess_or_loader_exec(self):
        with mock.patch("subprocess.run", side_effect=AssertionError("execution forbidden")):
            self.assertIs(self.audit()[0]["authorized"], False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
