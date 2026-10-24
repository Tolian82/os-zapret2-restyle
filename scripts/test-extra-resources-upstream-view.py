#!/usr/bin/env python3
"""Stage 2 foundation: real HEAD resource view and native blobs.sh resolver."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
BACKEND = REPO / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND.parent))
from extra_resources_preflight import PreflightError
from extra_resources_upstream_view import upstream_only_view

LUA = b"function native_desync(ctx) return ctx end\n"
BIN = b"native binary payload"
EXTRA_LUA = b"function extra_desync(ctx) return ctx end\n"
EXTRA_BIN = b"manually added payload"


class Stage2ViewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.root = base / "runtime"
        (self.root / "lua").mkdir(parents=True)
        (self.root / "files/fake").mkdir(parents=True)
        self.state = base / "state" / "installed.json"
        self.state.parent.mkdir()
        self.config = base / "conf.xml"
        self.config.write_text("<opnsense><saved/></opnsense>\n")
        self.work = base / "work"
        self.work.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Native View")
        self.git("config", "user.email", "fixture@example.invalid")
        (self.root / "lua/native.lua").write_bytes(LUA)
        (self.root / "files/fake/native.bin").write_bytes(BIN)
        self.git("add", "lua", "files")
        self.git("commit", "-qm", "installed upstream")
        (self.root / "lua/extra.lua").write_bytes(EXTRA_LUA)
        (self.root / "files/fake/manual.bin").write_bytes(EXTRA_BIN)
        self.state.write_text(json.dumps({
            "schema": 1, "files": {"lua/extra.lua": hashlib.sha256(EXTRA_LUA).hexdigest()}
        }))

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args],
                              capture_output=True, check=True).stdout.decode().strip()

    def view(self, expected_witness=None):
        return upstream_only_view(
            self.root, self.state, self.config, workspace_root=self.work,
            expected_witness=expected_witness,
        )

    def native_resolve(self, root: Path, name: str, work: Path):
        strategy = work / "strategy.txt"
        strategy.write_text(f"--filter-tcp=443\n--blob={name}\n")
        args = work / "args.txt"
        loaded = work / "loaded.txt"
        output = work / "resolved.txt"
        script = '. "$1"; . "$2"; blobs_resolve_file "$3" "$4" "$5" "$6" "$7"'
        return subprocess.run(
            ["sh", "-c", script, "sh", str(BACKEND / "common.sh"),
             str(BACKEND / "blobs.sh"), str(strategy), str(output),
             str(args), str(loaded), str(root / "files/fake")],
            capture_output=True, text=True,
        )

    def test_native_blob_resolver_uses_only_future_upstream_files(self):
        source_files = [self.root / "lua/native.lua", self.root / "files/fake/native.bin",
                        self.root / "lua/extra.lua", self.root / "files/fake/manual.bin"]
        before = {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in source_files}
        with self.view() as (plan, view):
            self.assertEqual(plan["counts"]["total"], 2)
            self.assertFalse(plan["authorized"])
            self.assertEqual(sorted(p.name for p in (view / "lua").iterdir()), ["native.lua"])
            self.assertEqual(sorted(p.name for p in (view / "files/fake").iterdir()), ["native.bin"])
            self.assertNotEqual((view / "lua/native.lua").stat().st_ino,
                                (self.root / "lua/native.lua").stat().st_ino)
            self.assertEqual((view / "lua/native.lua").read_bytes(), LUA)
            good = self.native_resolve(view, "native", self.work)
            self.assertEqual(good.returncode, 0, good.stderr)
            self.assertIn("--blob=native:@"+str(view / "files/fake/native.bin"),
                          (self.work / "args.txt").read_text())
            removed = self.native_resolve(view, "manual", self.work)
            self.assertNotEqual(removed.returncode, 0,
                                "native Blob resolver wrongly accepted removed BIN")
            self.assertTrue((self.root / "files/fake/manual.bin").is_file())
        self.assertEqual(list(self.work.glob("zapret-upstream-only-*")), [])
        self.assertEqual(before, {str(p): (p.read_bytes(), p.stat().st_mtime_ns)
                                  for p in source_files})

    def test_changed_upstream_head_dynamically_changes_future_view(self):
        with self.view() as (_, view):
            self.assertFalse((view / "lua/extra.lua").exists())
        self.git("add", "lua/extra.lua")
        self.git("commit", "-qm", "upstream adopts extra")
        # Stale ownership is unsafe. In production an upstream-switch
        # transaction retires/reconciles the old managed manifest first.
        with self.assertRaisesRegex(PreflightError, "managed resource ownership differs from disk"):
            with self.view():
                pass
        self.state.unlink()
        with self.view() as (plan, view):
            self.assertEqual(plan["counts"]["lua"], 0)
            self.assertTrue((view / "lua/extra.lua").is_file())
            self.assertFalse((view / "files/fake/manual.bin").exists())

    def test_stale_plan_binding_blocks_before_staging(self):
        with self.view() as (plan, _):
            old = plan["witness"]["inventory_sha256"]
        self.config.write_text("<opnsense><changed/></opnsense>\n")
        with self.assertRaisesRegex(PreflightError, "stale"):
            with self.view(expected_witness=old):
                pass
        self.assertEqual(list(self.work.iterdir()), [])

    def test_upstream_modified_and_symlink_resources_fail_closed(self):
        (self.root / "lua/native.lua").write_bytes(b"tampered")
        with self.assertRaisesRegex(PreflightError, "Git-tracked resource changed"):
            with self.view():
                pass
        (self.root / "lua/native.lua").write_bytes(LUA)
        (self.root / "lua/extra.lua").unlink()
        (self.root / "lua/extra.lua").symlink_to(self.config)
        with self.assertRaisesRegex(PreflightError, "unsafe current runtime resource"):
            with self.view():
                pass
        self.assertEqual(list(self.work.iterdir()), [])

    def test_no_op_stages_only_upstream_and_never_authorizes(self):
        (self.root / "lua/extra.lua").unlink()
        (self.root / "files/fake/manual.bin").unlink()
        self.state.unlink()
        with self.view() as (plan, view):
            self.assertEqual(plan["counts"]["total"], 0)
            self.assertFalse(plan["authorized"])
            self.assertTrue((view / "lua/native.lua").is_file())

    def test_saved_config_drift_during_native_candidate_is_refused(self):
        with self.assertRaisesRegex(PreflightError, "changed during compilation"):
            with self.view() as (_, view):
                self.assertTrue((view / "lua/native.lua").is_file())
                self.config.write_text("<opnsense><changed-while-compiling/></opnsense>\n")
        self.assertEqual(list(self.work.iterdir()), [])

    def test_staged_upstream_byte_drift_during_candidate_is_refused(self):
        with self.assertRaisesRegex(PreflightError, "changed during compilation"):
            with self.view() as (_, view):
                (view / "lua/native.lua").unlink()
                (view / "lua/native.lua").write_bytes(b"tampered staged copy")
        self.assertEqual((self.root / "lua/native.lua").read_bytes(), LUA)
        self.assertEqual(list(self.work.iterdir()), [])

    def test_untrusted_workspace_refused_without_production_change(self):
        with self.assertRaisesRegex(PreflightError, "unsafe prospective"):
            with upstream_only_view(self.root, self.state, self.config,
                                    workspace_root=self.root):
                pass
        self.assertTrue((self.root / "lua/native.lua").is_file())


if __name__ == "__main__":
    unittest.main()
