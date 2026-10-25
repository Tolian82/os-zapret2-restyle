#!/usr/bin/env python3
"""Stage 2: real native common candidate via new private source-only shell route.

No actual OPNsense runtime/Config service/IPFW actions, no real dvtws2
execution, no Lua function/export confirmation, no removal permission.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SRC = ROOT / "src/opnsense/scripts/OPNsense/Zapret"
SHELL = SRC / "extra_resources_inert_compile.sh"
spec = importlib.util.spec_from_file_location(
    "native_common_fixture", SCRIPTS / "test-voice-common-runtime.py"
)
assert spec and spec.loader
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class InertShellNativeTests(unittest.TestCase):
    def test_syntax_and_no_service_activation_or_file_deletion(self):
        run = subprocess.run(["sh", "-n", str(SHELL)],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        script = SHELL.read_text()
        self.assertIn("orchestrator_build_release", script)
        self.assertIn("shared-candidate", script)
        for call in ("service_dispatch ", "config_reload_template ",
                     "firewall_prepare ", "orchestrator_native_start ",
                     "orchestrator_native_stop ", "pkg add ", "rm -rf "):
            self.assertNotIn(call, script)

    def test_native_candidate_built_with_real_compiler_and_missing_lua_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            result, _ = fixture.build(root, ())
            self.assertEqual(result.returncode, 0, result.stderr)
            upstream = root / "upstream"
            before = {
                item.relative_to(upstream): hashlib.sha256(item.read_bytes()).hexdigest()
                for dirname in ("lua", "files/fake")
                for item in (upstream / dirname).iterdir()
            }
            # Only the test fixture supplies an OPNsense logical iface.
            tools = root / "tools"
            (tools / "ifconfig").write_text("#!/bin/sh\nexit 0\n")
            (tools / "ifconfig").chmod(0o755)
            env = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ["PATH"])

            def compile_native(name):
                work = root / name
                work.mkdir(mode=0o700)
                cmd = [
                    "/bin/sh", str(SHELL), str(root / "zapret.conf"),
                    str(upstream), str(root / "config.xml"),
                    "/usr/local/etc/zapret2/runtime-v2",
                    str(work), str(work / "release"),
                ]
                output = subprocess.run(cmd, capture_output=True, text=True,
                                        env=env, timeout=35)
                return output, work / "release"

            done, release = compile_native("native")
            self.assertEqual(done.returncode, 0, done.stderr)
            argv = (release / "dvtws.args").read_text()
            self.assertIn("--lua-init=@" + str(upstream / "lua/zapret-lib.lua"), argv)
            self.assertIn("--filter-tcp=443", argv)
            self.assertFalse((upstream / "binaries/my/dvtws2").exists())
            self.assertEqual(before, {
                item.relative_to(upstream): hashlib.sha256(item.read_bytes()).hexdigest()
                for dirname in ("lua", "files/fake")
                for item in (upstream / dirname).iterdir()
            })
            # The exact same common compiler must refuse absent upstream Lua
            # *before* any future compatibility or removal decision.
            (upstream / "lua/zapret-auto.lua").unlink()
            refused, missing_release = compile_native("missing")
            self.assertNotEqual(refused.returncode, 0)
            self.assertFalse((missing_release / "dvtws.args").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
