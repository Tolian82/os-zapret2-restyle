#!/usr/bin/env python3
"""Check the real native engine --dry-run validator without live service/IPFW.

A fake engine simulates nobody-level path access, even if CI is non-root.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend/validator.sh"
REF = "/usr/local/etc/zapret2/runtime-v2"
PREFIX = "zapret-dvtws-validate-"


def fake_binary(path: Path) -> None:
    path.write_text("""#!/usr/bin/env python3
import json
import os
from pathlib import Path
import stat
import sys
args = sys.argv[1:]
if '--dry-run' not in args or os.environ.get('FAKE_ENGINE_FAIL') == '1':
    sys.exit(50)
checked = []
for token in args:
    name, sep, value = token.partition('=')
    if not sep or name not in ('--ipset', '--hostlist', '--hostlist-exclude'):
        continue
    p = Path(value)
    for parent in [p.parent, *p.parents]:
        if not (parent.stat().st_mode & stat.S_IXOTH):
            sys.exit(51)
    if not p.is_file() or not (p.stat().st_mode & stat.S_IROTH):
        sys.exit(52)
    checked.append([name, p.read_text(), value])
if len(checked) != 2:
    sys.exit(53)
Path(os.environ['FAKE_ENGINE_RECORD']).write_text(json.dumps(checked))
""", encoding="utf-8")
    path.chmod(0o755)


class PrivateRuntimeValidation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zapret-private-validate-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.work = self.root / "private" / ("d" * 32)
        self.release = self.work / "release"
        managed = self.release / "managed"
        managed.mkdir(parents=True)
        (self.root / "private").chmod(0o700)
        self.work.chmod(0o700)
        self.release.chmod(0o755)
        managed.chmod(0o755)
        (managed / "hostlist-exclude.txt").write_text("example.org\n")
        (managed / "ipset-telegram.txt").write_text("91.108.0.0/16\n")
        for file in managed.iterdir():
            file.chmod(0o644)
        self.args = self.work / "dvtws.args"
        self.args.write_text(
            "--hostlist-exclude=" + REF + "/managed/hostlist-exclude.txt\n"
            "--ipset=" + REF + "/managed/ipset-telegram.txt\n"
        )
        self.engine = self.root / "fake-dvtws2"
        fake_binary(self.engine)
        self.record = self.root / "engine-proof.json"
        self.sh = """set -eu
. "$1"
validator_validate_engine_mapped "$2" "$3" "$4" "$5" "$6"
"""
        self.old_dryruns = {
            name for name in os.listdir("/tmp") if name.startswith(PREFIX)
        }

    def invoke(self, extra_env=None):
        env = os.environ.copy()
        env["FAKE_ENGINE_RECORD"] = str(self.record)
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            ["/bin/sh", "-c", self.sh, "validator-test", str(VALIDATOR),
             str(self.engine), str(self.args), REF, str(self.release),
             sys.executable],
            env=env, capture_output=True, text=True, check=False, timeout=20,
        )

    def assert_cleanup(self):
        after = {name for name in os.listdir("/tmp") if name.startswith(PREFIX)}
        self.assertEqual(self.old_dryruns, after, "public dry-run mirror leaked")

    def test_public_mirror_for_nobody_preserves_private_workspace(self):
        result = self.invoke()
        self.assertEqual(0, result.returncode, result.stderr)
        proof = json.loads(self.record.read_text())
        self.assertEqual(
            ["example.org\n", "91.108.0.0/16\n"], [item[1] for item in proof]
        )
        self.assertTrue(all("/tmp/" + PREFIX in item[2] for item in proof))
        self.assertEqual(0o700, self.work.stat().st_mode & 0o777)
        self.assertEqual(0o700, (self.root / "private").stat().st_mode & 0o777)
        self.assert_cleanup()

    def test_symlink_is_not_staged_or_followed(self):
        file = self.release / "managed" / "ipset-telegram.txt"
        file.unlink()
        file.symlink_to(self.root / "private" / "secret.xml")
        result = self.invoke()
        self.assertNotEqual(0, result.returncode)
        self.assertFalse(self.record.exists())
        self.assert_cleanup()

    def test_engine_rejection_propagates_and_mirror_is_cleaned(self):
        result = self.invoke({"FAKE_ENGINE_FAIL": "1"})
        self.assertNotEqual(0, result.returncode)
        self.assertIn("installed engine rejected candidate", result.stderr)
        self.assert_cleanup()

    def test_reference_cannot_escape_managed_runtime(self):
        self.args.write_text("--ipset=" + REF + "/../candidate.xml\n")
        result = self.invoke()
        self.assertNotEqual(0, result.returncode)
        self.assertFalse(self.record.exists())
        self.assert_cleanup()


if __name__ == "__main__":
    unittest.main(verbosity=2)
