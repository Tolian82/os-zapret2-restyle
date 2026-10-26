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
from extra_resources_jail_path_gate import attest_staged_native_file_paths
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

    def test_native_staged_path_closure_over_original_multi_profile_argv(self):
        def digest(value):
            return hashlib.sha256(value).hexdigest()
        staged = {
            "upstream/lua/zapret-lib.lua": digest(b"lua"),
            "upstream/files/fake/stock.bin": digest(b"bin"),
            "native-managed/hostlist-user.txt": digest(b"host"),
            "native-managed/ipset-telegram.txt": digest(b"ipset"),
            "native-managed/hostlist-exclude.txt": digest(b"excluded"),
        }
        argv = ("--lua-init=@/upstream/lua/zapret-lib.lua\n"
                "--hostlist=/native-managed/hostlist-user.txt\n"
                "--blob=stock:@/upstream/files/fake/stock.bin\n"
                "--new\n"
                "--ipset=/native-managed/ipset-telegram.txt\n"
                "--hostlist-exclude=/native-managed/hostlist-exclude.txt\n").encode()
        proof = attest_staged_native_file_paths(argv, staged)
        self.assertEqual(proof["state"], "known-native-file-paths-staged-only")
        self.assertEqual(proof["known_file_references"], 5)
        self.assertEqual(proof["unique_staged_files"], 5)
        self.assertEqual(proof["unresolved_path_tokens"], 0)
        self.assertEqual(proof["engine_lua_proof"], "not-run")
        self.assertFalse(proof["runnable"])
        self.assertFalse(proof["authorized"])

    def test_native_staged_path_gate_rejects_fake_missing_or_wrong_kind(self):
        digest = hashlib.sha256(b"data").hexdigest()
        staged = {"upstream/lua/zapret-lib.lua": digest}
        safe = b"--lua-init=@/upstream/lua/zapret-lib.lua\n"
        for bad in (
            b"--blob=stock:@/upstream/files/fake/missing.bin\n",
            b"--hostlist=/native-managed/hostlist-missing.txt\n",
            b"--lua-init=@/upstream/lua/../secret.lua\n",
            b"--blob=stock:@/upstream/files/fake/../secret.bin\n",
            b"--hostlist=/native-managed/../secret.txt\n",
            b"--lua-init=print(1)\n",
            b"--blob=stock:@/host/stock.bin\n",
        ):
            with self.subTest(bad=bad), self.assertRaises(PreflightError):
                attest_staged_native_file_paths(safe + bad, staged)
        with self.assertRaisesRegex(PreflightError, "kind mismatch"):
            attest_staged_native_file_paths(
                safe + b"--hostlist=/native-managed/ipset-telegram.txt\n",
                {**staged, "native-managed/ipset-telegram.txt": digest},
            )

    def test_native_unresolved_host_files_are_not_considered_closed(self):
        digest = hashlib.sha256(b"lua").hexdigest()
        proof = attest_staged_native_file_paths(
            b"--lua-init=@/upstream/lua/zapret-lib.lua\n"
            b"--hostlist=/usr/local/etc/zapret2/hostlist.txt\n"
            b"--hostlist-auto=plain-name.txt\n"
            b"--new\n",
            {"upstream/lua/zapret-lib.lua": digest},
        )
        self.assertEqual(proof["state"], "unresolved-native-file-paths")
        self.assertEqual(proof["unresolved_path_tokens"], 2)
        self.assertFalse(proof["runnable"])
        self.assertFalse(proof["authorized"])

    def test_relative_native_file_options_and_runtime_controls_are_unresolved(self):
        digest = hashlib.sha256(b"lua").hexdigest()
        staged = {"upstream/lua/zapret-lib.lua": digest}
        base = b"--lua-init=@/upstream/lua/zapret-lib.lua\n"
        for option in (
            "--ipset-exclude=local.txt", "--hostlist-auto=auto.txt",
            "--hostlist-auto-debug=audit.log", "--pidfile=pid.txt",
            "--chdir=working", "--wf-save=filter.rules", "--ipset-auto=plain",
        ):
            with self.subTest(option=option):
                proof = attest_staged_native_file_paths(
                    base + (option + "\n").encode(), staged
                )
                self.assertEqual(proof["state"], "unresolved-native-file-paths")
                self.assertEqual(proof["unresolved_path_tokens"], 1)
                self.assertEqual(proof["known_file_references"], 1)
                self.assertIs(proof["authorized"], False)
        for option in ("--writable", "--daemon", "--uid=1000", "--user=nobody"):
            with self.subTest(option=option):
                proof = attest_staged_native_file_paths(
                    base + (option + "\n").encode(), staged
                )
                self.assertEqual(proof["state"], "unreviewed-native-runtime-controls")
                self.assertEqual(proof["unresolved_path_tokens"], 0)
                self.assertEqual(proof["runtime_side_effect_option_tokens"], 1)
                self.assertGreater(proof["unreviewed_native_option_tokens"], 0)
                self.assertFalse(proof["runnable"])
        for option in ("--future-flag=relative.txt", "--lua-desync=pass"):
            with self.subTest(option=option):
                proof = attest_staged_native_file_paths(
                    base + (option + "\n").encode(), staged
                )
                self.assertEqual(proof["state"], "unreviewed-native-option-semantics")
                self.assertGreater(proof["unreviewed_native_option_tokens"], 0)
                self.assertFalse(proof["runnable"])

    def test_inert_snapshot_exposes_process_side_effects(self):
        view = self.base / "native-view"
        (view / "lua").mkdir(parents=True)
        (view / "files/fake").mkdir(parents=True)
        (view / "lua/zapret-lib.lua").write_bytes(b"function pass() end\n")
        engine = self.base / "native-engine"
        engine.write_bytes(fixture.native_elf("libc.so.7", "libluajit-5.1.so.2"))
        engine.chmod(0o755)
        argv = self.base / "native.args"
        argv.write_text("--lua-init=@" + str(view / "lua/zapret-lib.lua")
                        + "\n--writable\n")
        workspace = self.base / "native-private"
        workspace.mkdir(mode=0o700)
        with staged_inert_jail_inputs(
            engine, argv, view, workspace,
            expected_engine_sha256=hashlib.sha256(engine.read_bytes()).hexdigest(),
            expected_argv_sha256=hashlib.sha256(argv.read_bytes()).hexdigest(),
            check_lifecycle=lambda: None,
        ) as (proof, _):
            self.assertEqual(proof["native_path_state"],
                             "unreviewed-native-runtime-controls")
            self.assertEqual(proof["native_runtime_side_effect_option_tokens"], 1)
            self.assertFalse(proof["runnable"])
            self.assertIs(proof["authorized"], False)

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
            self.assertEqual(proof["native_path_state"], "known-native-file-paths-staged-only")
            self.assertEqual(proof["native_unresolved_path_tokens"], 0)
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
