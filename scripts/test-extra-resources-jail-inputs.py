#!/usr/bin/env python3
"""Stage 2 non-executable engine/argv/upstream Lua/BIN jail input snapshots."""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/opnsense/scripts/OPNsense/Zapret"
sys.path.insert(0, str(SRC))
from extra_resources_jail_inputs import JailInputError, staged_inert_jail_inputs
from extra_resources_preflight import PreflightError

spec = importlib.util.spec_from_file_location(
    "installed_engine_elf_test_fixture", ROOT / "scripts/test-extra-resources-engine-abi.py"
)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class InertJailSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.view = base / "upstream-only"
        (self.view / "lua").mkdir(parents=True)
        (self.view / "files/fake").mkdir(parents=True)
        (self.view / "lua/zapret-lib.lua").write_bytes(b"function desync(ctx) return 0 end\n")
        (self.view / "lua/zapret-auto.lua").write_bytes(b"function noop(ctx) return 0 end\n")
        (self.view / "files/fake/stock.bin").write_bytes(b"STOCK")
        self.engine = base / "dvtws2"
        self.engine.write_bytes(fixture.native_elf("libc.so.7", "libluajit-5.1.so.2"))
        self.engine.chmod(0o755)
        self.argv = base / "dvtws.args"
        self.argv.write_text(
            "--lua-init=@" + str(self.view / "lua/zapret-lib.lua") + "\n"
            "--lua-init=@" + str(self.view / "lua/zapret-auto.lua") + "\n"
            "--new\n--blob=stock:@" + str(self.view / "files/fake/stock.bin") + "\n"
            "--lua-desync=desync\n"
        )
        self.workspace = base / "private"
        self.workspace.mkdir(mode=0o700)
        self.checked = 0

    def check_lock(self):
        self.checked += 1

    def stage(self, **kwargs):
        opts = {
            "expected_engine_sha256": hashlib.sha256(self.engine.read_bytes()).hexdigest(),
            "expected_argv_sha256": hashlib.sha256(self.argv.read_bytes()).hexdigest(),
            "check_lifecycle": self.check_lock,
        }
        opts.update(kwargs)
        return staged_inert_jail_inputs(
            self.engine, self.argv, self.view, self.workspace, **opts
        )

    def test_stage_native_input_bytes_non_executable_digest_and_cleanup(self):
        with self.stage() as (report, bundle):
            self.assertEqual(report["state"], "inert-jail-input-snapshot-only")
            self.assertEqual(report["staged_resources"], 3)
            self.assertEqual(len(report["snapshot_sha256"]), 64)
            self.assertEqual(report["argv_relocation"], "not-done")
            self.assertEqual(report["dynamic_library_closure"], "unknown")
            self.assertEqual(report["engine_lua_proof"], "not-run")
            self.assertEqual(report["compatibility"], "unknown")
            self.assertIs(report["authorized"], False)
            self.assertEqual((bundle / "engine/dvtws2").read_bytes(),
                             self.engine.read_bytes())
            self.assertEqual((bundle / "native/original-dvtws.args").read_bytes(),
                             self.argv.read_bytes())
            self.assertEqual((bundle / "upstream/files/fake/stock.bin").read_bytes(),
                             b"STOCK")
            self.assertFalse((bundle / "engine/dvtws2").stat().st_mode & 0o111)
            self.assertFalse((bundle / "native/original-dvtws.args").stat().st_mode & 0o111)
            self.assertFalse((bundle / "libexec/ld-elf.so.1").exists())
            destination = bundle
        self.assertFalse(destination.exists())
        self.assertGreaterEqual(self.checked, 3)

    def test_known_digest_is_mandatory_and_bad_expected_fails_before_copy(self):
        for wrong in ("", "0" * 64):
            with self.subTest(wrong=wrong):
                with self.assertRaises(JailInputError):
                    with self.stage(expected_engine_sha256=wrong):
                        pass
        self.assertEqual(list(self.workspace.iterdir()), [])

    def test_unsafe_or_missing_resource_does_not_stage(self):
        target = self.view / "lua/zapret-auto.lua"
        target.unlink()
        target.symlink_to(self.view / "lua/zapret-lib.lua")
        with self.assertRaises(PreflightError):
            with self.stage():
                pass
        self.assertEqual(list(self.workspace.iterdir()), [])

    def test_external_additional_lua_is_rejected_by_existing_native_attestor(self):
        extra = Path(self.tmp.name) / "external.lua"
        extra.write_text("function external() end")
        with self.argv.open("a") as output:
            output.write("--lua-init=@" + str(extra) + "\n")
        with self.assertRaises(PreflightError):
            with self.stage():
                pass

    def test_source_mutation_inside_consumer_invalidates_on_exit_and_cleans(self):
        with self.assertRaisesRegex(JailInputError, "changed before workspace teardown"):
            with self.stage() as (_, bundle):
                (self.view / "lua/zapret-auto.lua").write_text("function changed() end")
                staged_path = bundle
        self.assertFalse(staged_path.exists())

    def test_untrusted_workspace_permissions_or_symlink_fail(self):
        self.workspace.chmod(0o755)
        with self.assertRaises(JailInputError):
            with self.stage():
                pass
        self.workspace.chmod(0o700)
        replacement = Path(self.tmp.name) / "alias"
        replacement.symlink_to(self.workspace, target_is_directory=True)
        with self.assertRaises(JailInputError):
            with staged_inert_jail_inputs(
                self.engine, self.argv, self.view, replacement,
                expected_engine_sha256=hashlib.sha256(self.engine.read_bytes()).hexdigest(),
                expected_argv_sha256=hashlib.sha256(self.argv.read_bytes()).hexdigest(),
                check_lifecycle=self.check_lock,
            ):
                pass

    def test_no_external_execution_from_staging_helper(self):
        with mock.patch("subprocess.run", side_effect=AssertionError("subprocess forbidden")):
            with self.stage() as (report, _):
                self.assertIs(report["authorized"], False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
