#!/usr/bin/env python3
"""No-exec source and staged DT_NEEDED graph regression tests."""
import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "src/opnsense/scripts/OPNsense/Zapret"))
from extra_resources_jail_libraries import collect_static_needed_libraries
from extra_resources_jail_inputs import _read_pinned, staged_inert_jail_inputs, JailInputError
from extra_resources_preflight import PreflightError

spec = importlib.util.spec_from_file_location(
    "fixture", BASE / "scripts/test-extra-resources-engine-abi.py"
)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class StaticNeededGraphTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.libroot = self.base / "sysroot"
        for p in ("lib", "usr/lib", "usr/local/lib"):
            (self.libroot / p).mkdir(parents=True, exist_ok=True)
        self.engine_data = fixture.native_elf("libfirst.so.1")
        self.first = self.libroot / "lib/libfirst.so.1"
        self.second = self.libroot / "usr/local/lib/libsecond.so.2"
        self.first.write_bytes(fixture.native_elf("libsecond.so.2"))
        self.second.write_bytes(fixture.native_elf(no_dynamic=True))

    def witness(self):
        return collect_static_needed_libraries(
            self.engine_data, self.libroot, _read_pinned
        )

    def test_recursive_graph_and_non_authorizing_flags(self):
        proof, files = self.witness()
        self.assertEqual(proof["static_needed_libraries"], 2)
        self.assertEqual(set(files), {"lib/libfirst.so.1", "usr/local/lib/libsecond.so.2"})
        self.assertEqual(proof["dynamic_library_closure"], "unknown")
        self.assertEqual(proof["dlopen_dependencies"], "unknown")
        self.assertEqual(proof["loader_path_resolution"], "unproven")
        self.assertEqual(proof["engine_lua_proof"], "not-run")
        self.assertIs(proof["authorized"], False)
        self.assertFalse(proof["runnable"])

    def test_missing_duplicate_link_or_world_writable_library_fail_closed(self):
        self.second.unlink()
        with self.assertRaisesRegex(PreflightError, "missing or ambiguous"):
            self.witness()
        self.second.write_bytes(fixture.native_elf(no_dynamic=True))
        duplicate = self.libroot / "usr/lib/libfirst.so.1"
        duplicate.write_bytes(fixture.native_elf(no_dynamic=True))
        with self.assertRaisesRegex(PreflightError, "missing or ambiguous"):
            self.witness()
        duplicate.unlink()
        self.first.chmod(0o666)
        with self.assertRaisesRegex(PreflightError, "unsafe DT_NEEDED library inode"):
            self.witness()
        self.first.chmod(0o644)
        self.first.unlink()
        self.first.symlink_to(self.second)
        with self.assertRaisesRegex(PreflightError, "linked DT_NEEDED"):
            self.witness()

    def test_malformed_elf_hostile_name_and_root_symlink_refused(self):
        self.second.write_bytes(b"malformed" + b"\x00" * 4096)
        with self.assertRaisesRegex(PreflightError, "ELF invalid"):
            self.witness()
        self.engine_data = fixture.native_elf("../evil.so")
        with self.assertRaisesRegex(PreflightError, "installed engine ELF graph invalid"):
            self.witness()
        alias = self.base / "alias"
        alias.symlink_to(self.libroot, target_is_directory=True)
        with self.assertRaises(PreflightError):
            collect_static_needed_libraries(self.engine_data, alias, _read_pinned)

    def test_no_dt_needed_never_proves_real_loader_or_lua(self):
        proof, files = collect_static_needed_libraries(
            fixture.native_elf(no_dynamic=True), self.libroot, _read_pinned
        )
        self.assertEqual(proof["static_needed_libraries"], 0)
        self.assertEqual(files, {})
        self.assertIs(proof["authorized"], False)

    def test_staged_library_copy_and_source_race_rejected(self):
        upstream = self.base / "upstream"
        (upstream / "lua").mkdir(parents=True)
        (upstream / "files/fake").mkdir(parents=True)
        (upstream / "lua/zapret-lib.lua").write_text("function noop() end\n")
        engine = self.base / "dvtws2"
        engine.write_bytes(self.engine_data)
        engine.chmod(0o755)
        argv = self.base / "dvtws.args"
        argv.write_text("--lua-init=@" + str(upstream / "lua/zapret-lib.lua") + "\n")
        workspace = self.base / "private"
        workspace.mkdir(mode=0o700)
        args = dict(
            expected_engine_sha256=hashlib.sha256(engine.read_bytes()).hexdigest(),
            expected_argv_sha256=hashlib.sha256(argv.read_bytes()).hexdigest(),
            check_lifecycle=lambda: None,
            library_source_root=self.libroot,
        )
        with staged_inert_jail_inputs(engine, argv, upstream, workspace, **args) as (proof, bundle):
            self.assertEqual(proof["static_needed_libraries"], 2)
            self.assertFalse(proof["runnable"])
            file = bundle / "elf-needed/lib/libfirst.so.1"
            self.assertEqual(file.read_bytes(), self.first.read_bytes())
            self.assertEqual(file.stat().st_mode & 0o111, 0)
            temporary = bundle
        self.assertFalse(temporary.exists())
        with self.assertRaisesRegex(PreflightError, "missing or ambiguous"):
            with staged_inert_jail_inputs(engine, argv, upstream, workspace, **args):
                self.second.write_bytes(fixture.native_elf("libother.so.3"))
        self.assertEqual(list(workspace.iterdir()), [])

    def test_no_loader_or_process_execution(self):
        with mock.patch("subprocess.run", side_effect=AssertionError("unconfined execution")):
            self.assertFalse(self.witness()[0]["runnable"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
