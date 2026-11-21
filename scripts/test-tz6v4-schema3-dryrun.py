#!/usr/bin/env python3
"""Original validator native dry-run must mirror exact schema3 N paths only.

Portable offline path/ownership authorization using real shell + Python,
real temporary inodes and a deliberately fake dry-run *parser*. The installed
FreeBSD workflow separately uses real dvtws2 and original Apply/Stop.
No user Config, producer root, IPFW, FD9 or engine is touched here.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend/validator.sh"
NATIVE = Path("/var/db/zapret2-auto-detect")
GEN = "b" * 32


class NativeDryRunPaths(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="tz6v4-native-validator-")
        self.addCleanup(self.tmp.cleanup)
        self.workspace = Path(self.tmp.name) / GEN
        self.release = self.workspace / "release"
        self.release.mkdir(parents=True)
        self.args = self.workspace / "dvtws.args"
        self.binary = self.workspace / "test-dvtws-dryrun.sh"
        self.binary.write_text(
            "#!/bin/sh\n"
            "test \"$\" != \"never\" || exit 22\n"
            "count=0\n"
            "debug=0\n"
            "for arg in \"$@\"; do\n"
            " case \"$arg\" in\n"
            " --hostlist-auto=*) path=${arg#*=}; [ -f \"$path\" ] || exit 25; "
            "count=$((count + 1)) ;;\n"
            " --hostlist-auto-debug=*) path=${arg#*=}; [ -f \"$path\" ] || exit 26; "
            "debug=$((debug + 1)) ;;\n"
            " esac\n"
            "done\n"
            "[ \"$count\" -gt 0 ] && [ \"$debug\" -eq 1 ] || exit 27\n"
            "exit 0\n",
            encoding="utf-8")
        self.binary.chmod(0o755)
        self.inputs = {
            n: str(NATIVE / f"learning-{GEN}-{n}.txt") for n in (3, 4)}
        self.debug = str(NATIVE / "debug.log")
        self.doc = {
            "schema": 3, "generation": GEN,
            "profiles": [
                {"role": "learning", "native_number": n,
                 "auto_inbox": self.inputs[n], "debug_identity": self.debug}
                for n in (3, 4)
            ],
        }
        self.map = self.release / "auto-detect-generation.json"
        self.write_map(self.doc)

    def write_map(self, document):
        self.map.write_text(json.dumps(document), encoding="utf-8")

    def tokens(self, *sources):
        return [
            "--port=989", f"--hostlist-auto-debug={self.debug}",
            "--new", "--filter-tcp=443", *(
                f"--hostlist-auto={source}" for source in sources),
        ]

    def validate(self, tokens):
        self.args.write_text("\n".join(tokens) + "\n", encoding="utf-8")
        code = '. "' + str(VALIDATOR) + '"; validator_validate_engine_mapped "$1" "$2" "$3" "$4" "$5"'
        return subprocess.run(
            ["/bin/sh", "-c", code, "validator",
             str(self.binary), str(self.args),
             "/usr/local/etc/zapret2/runtime-v2", str(self.release),
             sys.executable],
            capture_output=True, text=True, timeout=20)

    def test_exact_two_learning_inboxes_dry_run(self):
        p = self.validate(self.tokens(self.inputs[3], self.inputs[4]))
        self.assertEqual(p.returncode, 0, p.stderr[-600:])

    def test_schema3_rejects_foreign_profile_path(self):
        for forged in (
            str(NATIVE / f"learning-{'a'*32}-3.txt"),
            str(NATIVE / f"learning-{GEN}-5.txt"),
            str(NATIVE / f"learning-{GEN}-03.txt"),
            "/tmp/learning-" + GEN + "-3.txt",
            str(NATIVE / "../other/learning-" + GEN + "-3.txt"),
        ):
            with self.subTest(forged=forged):
                p = self.validate(self.tokens(forged, self.inputs[4]))
                self.assertNotEqual(p.returncode, 0, "forged native source accepted")

    def test_schema3_rejects_duplicate_or_missing_N(self):
        for paths in ((self.inputs[3],), (self.inputs[3], self.inputs[3]),
                      (self.inputs[4],)):
            p = self.validate(self.tokens(*paths))
            self.assertNotEqual(p.returncode, 0, "missing/duplicate native N accepted")

    def test_schema3_debug_is_exact_and_single(self):
        p = self.validate([
            "--port=989", "--hostlist-auto-debug=/tmp/fake-debug.log",
            f"--hostlist-auto={self.inputs[3]}",
            f"--hostlist-auto={self.inputs[4]}",
        ])
        self.assertNotEqual(p.returncode, 0)
        p = self.validate(self.tokens(self.inputs[3], self.inputs[4]) +
                          [f"--hostlist-auto-debug={self.debug}"])
        self.assertNotEqual(p.returncode, 0)

    def test_schema3_rejects_unbound_map_or_workspace(self):
        saved = dict(self.doc)
        for mutated in (
            {**saved, "generation": "a" * 32},
            {**saved, "profiles": [
                {**saved["profiles"][0], "native_number": 4},
                saved["profiles"][1]]},
            {**saved, "profiles": []},
            {**saved, "profiles": [
                {**saved["profiles"][0], "debug_identity": "/tmp/debug"},
                saved["profiles"][1]]},
        ):
            with self.subTest(mutated=mutated):
                self.write_map(mutated)
                p = self.validate(self.tokens(self.inputs[3], self.inputs[4]))
                self.assertNotEqual(p.returncode, 0)
        self.write_map(self.doc)
        self.map.unlink()
        self.map.symlink_to(self.args)
        p = self.validate(self.tokens(self.inputs[3], self.inputs[4]))
        self.assertNotEqual(p.returncode, 0)

    def test_schema2_legacy_fixed_inbox_unchanged(self):
        self.map.unlink()
        p = self.validate(self.tokens(str(NATIVE / "inbox.txt")))
        self.assertEqual(p.returncode, 0, p.stderr[-600:])
        p = self.validate(self.tokens(self.inputs[3]))
        self.assertNotEqual(p.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
