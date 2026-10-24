#!/usr/bin/env python3
"""Stage 2: native end-to-end Strategies compile against *future* HEAD resources.

This is evidence for the native candidate pipeline, NOT a removal clearance.
No live Config, native FD9, firewall, service or user strategy is modified.
The absence of installed dvtws2/Lua function evaluation is explicitly UNKNOWN.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ZAPRET = ROOT / "src/opnsense/scripts/OPNsense/Zapret"
sys.path.insert(0, str(ZAPRET))
from extra_resources_upstream_view import upstream_only_view

spec = importlib.util.spec_from_file_location(
    "native_common_fixture", ROOT / "scripts/test-voice-common-runtime.py"
)
assert spec and spec.loader
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)

UPSTREAM_LUA = ("zapret-lib.lua", "zapret-antidpi.lua", "zapret-auto.lua")
GOOD_STRATEGY = (
    "--filter-tcp=443\n--filter-l7=tls\n--blob=stock\n"
    "--new\n--filter-udp=596-599\n--filter-l7=stun\n--payload=stun"
)


class NativeProspectiveStrategiesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / "installed-upstream"
        (self.root / "lua").mkdir(parents=True)
        (self.root / "files/fake").mkdir(parents=True)
        for name in UPSTREAM_LUA:
            (self.root / "lua" / name).write_bytes(b"-- native Lua fixture\n")
        (self.root / "files/fake/stock.bin").write_bytes(b"upstream binary")
        self.git("init", "-q")
        self.git("config", "user.name", "Prospective Compiler")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("add", "lua", "files")
        self.git("commit", "-qm", "pinned installed upstream")
        (self.root / "lua/extra.lua").write_bytes(
            b"function extra_export(ctx) return ctx end\n"
        )
        extra = b"new external binary"
        (self.root / "files/fake/extra.bin").write_bytes(extra)
        self.manifest = self.base / "installed.json"
        self.manifest.write_text(json.dumps({
            "schema": 1,
            "files": {
                "lua/extra.lua": hashlib.sha256(
                    (self.root / "lua/extra.lua").read_bytes()
                ).hexdigest(),
                "files/fake/extra.bin": hashlib.sha256(extra).hexdigest(),
            },
        }))
        self.sample = self.base / "sample"
        self.sample.mkdir()
        initial, _ = fixture.build(self.sample, ())
        self.assertEqual(initial.returncode, 0, initial.stderr)
        self.saved_xml = self.sample / "config.xml"
        self.xml_bytes = self.saved_xml.read_bytes()
        self.workspaces = self.base / "temporary"
        self.workspaces.mkdir()
        self.compiles = 0

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.root), *args], check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).stdout.decode().strip()

    def compile(self, view, *, strategy=GOOD_STRATEGY, extra_args=""):
        self.compiles += 1
        target = self.base / f"compile-{self.compiles}"
        target.mkdir()
        result, release = fixture.build(
            target, (), upstream_root=view,
            traffic_args=strategy, extra_args=extra_args,
        )
        self.assertEqual(self.saved_xml.read_bytes(), (target / "config.xml").read_bytes())
        return result, release

    def test_native_two_profiles_and_extra_args_stock_bin_succeed_inertly(self):
        before = {(self.root / "lua" / name): (self.root / "lua" / name).read_bytes()
                  for name in UPSTREAM_LUA}
        with upstream_only_view(self.root, self.manifest, self.saved_xml,
                                workspace_root=self.workspaces) as (plan, view):
            self.assertFalse(plan["authorized"])
            self.assertEqual(plan["compatibility"], "unknown")
            self.assertEqual(plan["counts"], {"lua": 1, "bin": 1, "total": 2})
            result, release = self.compile(view, extra_args="--blob=stock")
            self.assertEqual(result.returncode, 0, result.stderr)
            args = (release / "dvtws.args").read_text()
            self.assertIn(f"--blob=stock:@{view}/files/fake/stock.bin", args)
            self.assertEqual(args.count("--blob=stock:@"), 1,
                             "native Blob registry must deduplicate across Strategies/Extra")
            self.assertIn("--filter-tcp=443", args)
            self.assertIn("--filter-udp=596-599", args)
            self.assertIn("--new", (release / "traffic-user.conf").read_text())
            self.assertNotIn("extra.bin", args)
            self.assertFalse((view / "lua/extra.lua").exists())
            self.assertFalse((view / "files/fake/extra.bin").exists())
            self.assertFalse((view / "binaries/my/dvtws2").exists(),
                             "inert candidate was never engine-Lua verified")
        self.assertEqual(self.saved_xml.read_bytes(), self.xml_bytes)
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        self.assertEqual(list(self.workspaces.iterdir()), [])

    def test_removed_bin_in_second_native_profile_refused(self):
        strategy = GOOD_STRATEGY.replace("--payload=stun", "--payload=stun\n--blob=extra")
        with upstream_only_view(self.root, self.manifest, self.saved_xml,
                                workspace_root=self.workspaces) as (_, view):
            result, release = self.compile(view, strategy=strategy)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("blob 'extra'", result.stderr)
            self.assertFalse((release / "dvtws.args").exists())
        self.assertTrue((self.root / "files/fake/extra.bin").exists())

    def test_removed_bin_in_native_extra_args_refused(self):
        with upstream_only_view(self.root, self.manifest, self.saved_xml,
                                workspace_root=self.workspaces) as (_, view):
            result, release = self.compile(view, extra_args="--blob=extra")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("blob 'extra'", result.stderr)
            self.assertFalse((release / "dvtws.args").exists())

    def test_direct_extra_lua_initializer_cannot_pass_native_validator(self):
        with upstream_only_view(self.root, self.manifest, self.saved_xml,
                                workspace_root=self.workspaces) as (_, view):
            result, release = self.compile(
                view, extra_args=f"--lua-init=@{self.root}/lua/extra.lua",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("outside allowed roots", result.stderr)
            self.assertTrue((self.root / "lua/extra.lua").is_file())

    def test_unresolved_lua_function_must_remain_unknown_without_engine(self):
        # No engine installed in this CI fixture. The native pipeline might
        # successfully create argv for a missing Lua function: this must
        # NEVER become a "compatible" or authorized preflight verdict.
        strategy = GOOD_STRATEGY + "\n--lua-desync=unavailable_export"
        with upstream_only_view(self.root, self.manifest, self.saved_xml,
                                workspace_root=self.workspaces) as (plan, view):
            result, release = self.compile(view, strategy=strategy)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("--lua-desync=unavailable_export",
                          (release / "dvtws.args").read_text())
            self.assertEqual(plan["compatibility"], "unknown")
            self.assertFalse(plan["authorized"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
