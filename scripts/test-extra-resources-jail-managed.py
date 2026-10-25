#!/usr/bin/env python3
"""Exact compiler-managed HOSTLIST/IPSET/Exclude jail input staging tests."""
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/opnsense/scripts/OPNsense/Zapret"))
from extra_resources_jail_managed import stage_native_managed_targets
from extra_resources_jail_inputs import _read_pinned, staged_inert_jail_inputs, JailInputError
from extra_resources_preflight import PreflightError

import importlib.util
spec = importlib.util.spec_from_file_location(
    "fixture", ROOT / "scripts/test-extra-resources-engine-abi.py"
)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)

PREFIX = "/usr/local/etc/zapret2/runtime-v2/managed/"


class NativeManagedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.managed = self.base / "managed"
        self.managed.mkdir()
        (self.managed / "hostlist-user.txt").write_bytes(b"example.net\n")
        (self.managed / "ipset-telegram.txt").write_bytes(b"91.108.0.0/16\n")
        (self.managed / "hostlist-exclude.txt").write_bytes(b"exclude.net\n")

    def relocate(self, *tokens):
        return stage_native_managed_targets(
            ("\n".join(tokens) + "\n").encode("utf-8"),
            self.managed, _read_pinned,
        )

    def test_two_profiles_dedup_native_targets_and_hostlist_exclude(self):
        new, proof, contents = self.relocate(
            "--lua-init=@/upstream/lua/zapret-lib.lua",
            "--hostlist=" + PREFIX + "hostlist-user.txt",
            "--ipset=" + PREFIX + "ipset-telegram.txt",
            "--new",
            "--hostlist=" + PREFIX + "hostlist-user.txt",
            "--hostlist-exclude=" + PREFIX + "hostlist-exclude.txt",
        )
        self.assertEqual(proof["managed_file_references"], 4)
        self.assertEqual(proof["managed_files"], 3)
        self.assertEqual(len(proof["managed_witness_sha256"]), 64)
        self.assertIn(b"--new\n", new)
        self.assertIn(b"--hostlist=/native-managed/hostlist-user.txt", new)
        self.assertIn(b"--ipset=/native-managed/ipset-telegram.txt", new)
        self.assertEqual(contents["hostlist-exclude.txt"], b"exclude.net\n")
        self.assertFalse(proof["runnable"])
        self.assertEqual(proof["engine_lua_proof"], "not-run")
        self.assertIs(proof["authorized"], False)

    def test_runtime_targets_not_copied_and_never_marked_runnable(self):
        other = "/usr/local/etc/zapret2/ipset/zapret-hosts-auto.txt"
        new, proof, contents = self.relocate("--hostlist=" + other)
        self.assertEqual(contents, {})
        self.assertIn(other.encode(), new)
        self.assertEqual(proof["unresolved_path_tokens"], 1)
        self.assertFalse(proof["runnable"])

    def test_symlink_traversal_absent_or_mismatched_type_rejected(self):
        for value in (PREFIX + "../hostlist-user.txt",
                      PREFIX + "nested/hostlist-user.txt",
                      PREFIX + "missing.txt"):
            with self.subTest(value=value), self.assertRaises(PreflightError):
                self.relocate("--hostlist=" + value)
        with self.assertRaises(PreflightError):
            self.relocate("--ipset=" + PREFIX + "hostlist-user.txt")
        with self.assertRaises(PreflightError):
            self.relocate("--hostlist-exclude=" + PREFIX + "hostlist-user.txt")
        link = self.managed / "hostlist-link.txt"
        link.symlink_to(self.managed / "hostlist-user.txt")
        with self.assertRaises(PreflightError):
            self.relocate("--hostlist=" + PREFIX + link.name)

    def test_integration_inert_jail_snapshot_and_source_race(self):
        view = self.base / "upstream"
        (view / "lua").mkdir(parents=True)
        (view / "files/fake").mkdir(parents=True)
        (view / "lua/zapret-lib.lua").write_text("function fake() end\n")
        engine = self.base / "dvtws2"
        engine.write_bytes(fixture.native_elf("libc.so.7", "libluajit-5.1.so.2"))
        engine.chmod(0o755)
        argv = self.base / "dvtws.args"
        argv.write_text("--lua-init=@" + str(view / "lua/zapret-lib.lua") + "\n"
                        "--hostlist=" + PREFIX + "hostlist-user.txt\n"
                        "--ipset=" + PREFIX + "ipset-telegram.txt\n")
        workspace = self.base / "private"
        workspace.mkdir(mode=0o700)
        args = dict(expected_engine_sha256=hashlib.sha256(engine.read_bytes()).hexdigest(),
                    expected_argv_sha256=hashlib.sha256(argv.read_bytes()).hexdigest(),
                    check_lifecycle=lambda: None)
        with staged_inert_jail_inputs(engine, argv, view, workspace, **args) as (proof, root):
            self.assertEqual(proof["managed_target_files"], 2)
            self.assertIn("--hostlist=/native-managed/hostlist-user.txt",
                          (root / "native/jailed-managed-targets.args").read_text())
            self.assertEqual((root / "native-managed/ipset-telegram.txt").read_bytes(),
                             b"91.108.0.0/16\n")
            self.assertEqual((root / "native-managed/hostlist-user.txt").stat().st_mode & 0o111, 0)
            finished = root
        self.assertFalse(finished.exists())
        with self.assertRaisesRegex(JailInputError, "native managed source changed"):
            with staged_inert_jail_inputs(engine, argv, view, workspace, **args):
                (self.managed / "hostlist-user.txt").write_bytes(b"changed\n")
        self.assertEqual(list(workspace.iterdir()), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
