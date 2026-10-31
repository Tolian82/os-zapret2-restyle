#!/usr/bin/env python3
"""Exercise the actual Stage 0 analyzer against a real temporary Git index."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("stage0_audit", HERE / "stage0-source-audit.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def git(path, *args):
    return subprocess.check_output(["git", "-C", str(path), *args], stderr=subprocess.PIPE).decode().strip()


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "tests@example.invalid")
        git(self.root, "config", "user.name", "audit-test")
        for path, content, executable in (
            ("src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh", "#!/bin/sh\n/usr/local/bin/python3.13 worker.py\n", False),
            ("pkg/+PRE_INSTALL", "#!/bin/sh\n# FD9 and FreeBSD.conf\n", True),
            ("scripts/build-pkg.sh", "#!/bin/sh\npkg-static create --manifest +MANIFEST\n", True),
            ("src/opnsense/mvc/app/controllers/Bridge.php", "<?php\nproc_open('/usr/local/bin/python3.13', []);\n", False),
            ("docs/history/obsolete.md", "python3.13 should not be treated as active\n", False),
            ("VERSION", "0.6.2\n", False),
        ):
            destination = self.root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content)
            destination.chmod(0o755 if executable else 0o644)
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "baseline")

    def test_exact_full_tree_and_line_inventory(self):
        report = audit.inspect(self.root)
        self.assertEqual(report["head"], git(self.root, "rev-parse", "HEAD"))
        self.assertEqual(audit.describe(report)["tracked"], 6)
        self.assertEqual(audit.describe(report)["service_mode"], "100644")
        files = {r["path"]: r for r in report["files"]}
        self.assertFalse(files["docs/history/obsolete.md"]["active"])
        self.assertEqual(files["docs/history/obsolete.md"]["hits"], [])
        self.assertEqual(files["pkg/+PRE_INSTALL"]["mode"], "100755")
        self.assertEqual(files["src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"]["hits"][0]["line"], 2)
        self.assertIn("python_minor", files["src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"]["hits"][0]["types"])
        self.assertTrue(any("package_engine" in h["types"] for h in files["scripts/build-pkg.sh"]["hits"]))
        self.assertTrue(any("python_process" in h["types"] for h in files["src/opnsense/mvc/app/controllers/Bridge.php"]["hits"]))
        self.assertEqual(report, audit.inspect(self.root))
        self.assertIn("Full path/mode/blob map", audit.markdown(report))

    def test_cli_files_and_wrong_head_refusal(self):
        outputs = (self.root / "results" / "report.json", self.root / "results" / "report.md")
        args = [sys.executable, str(HERE / "stage0-source-audit.py"), "--root", str(self.root),
                "--json", str(outputs[0]), "--markdown", str(outputs[1])]
        positive = subprocess.run(args + ["--expected-head", git(self.root, "rev-parse", "HEAD")],
                                  capture_output=True, text=True)
        self.assertEqual(positive.returncode, 0, positive.stderr)
        self.assertIn("STAGE0_SOURCE_AUDIT=READ_ONLY", positive.stdout)
        self.assertEqual(len(json.loads(outputs[0].read_text())["files"]), 6)
        negative = subprocess.run(args + ["--expected-head", "wrong-head"],
                                  capture_output=True, text=True)
        self.assertNotEqual(negative.returncode, 0)
        self.assertIn("exact-head mismatch", negative.stderr)


if __name__ == "__main__":
    unittest.main()
