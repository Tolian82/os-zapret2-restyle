#!/usr/bin/env python3
"""Fast, read-only G10A packaged purge safety and distribution contract."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent.parent
CANONICAL = ROOT / "scripts/purge-os-zapret2-restyle.sh"
RELATIVE = "src/opnsense/scripts/OPNsense/Zapret/purge-os-zapret2-restyle.sh"
PACKAGED = ROOT / RELATIVE
LOCAL = "/usr/local/opnsense/scripts/OPNsense/Zapret/purge-os-zapret2-restyle.sh"

class PackagedPurgeTest(unittest.TestCase):
    def test_packaged_script_is_exact_canonical_bytes(self):
        self.assertEqual(CANONICAL.read_bytes(), PACKAGED.read_bytes())
        self.assertTrue(PACKAGED.read_bytes().startswith(b"#!/bin/sh\n"))

    def test_installed_purge_is_executable_in_git_index(self):
        out = subprocess.run(["git", "ls-files", "--stage", "--", RELATIVE],
                             cwd=ROOT, capture_output=True, text=True, check=True).stdout
        self.assertTrue(out.startswith("100755 "), out)

    def test_shell_and_embedded_python_parse_without_execution(self):
        for path in (CANONICAL, PACKAGED):
            r = subprocess.run(["sh", "-n", str(path)], capture_output=True, text=True)
            self.assertEqual(0, r.returncode, r.stderr)
            body = path.read_text().split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
            compile(body, str(path), "exec")

    def test_interactive_purge_confirmation_reads_controlling_tty_not_stdin(self):
        """Real PTY input is accepted; absent/wrong TTY fails before any deletion."""
        import ast
        import errno
        import os
        import pty
        import stat
        from unittest import mock

        text = CANONICAL.read_text().split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
        tree = ast.parse(text)
        functions = [node for node in tree.body
                     if isinstance(node, ast.FunctionDef)
                     and node.name == "read_confirmation_from_tty"]
        self.assertEqual(len(functions), 1)
        class Refusal(Exception):
            pass
        namespace = {"os": os, "stat": stat, "Refusal": Refusal}
        exec(compile(ast.Module(body=functions, type_ignores=[]), "<tty-only>", "exec"),
             namespace)
        confirm = namespace["read_confirmation_from_tty"]
        with mock.patch.object(os, "open", side_effect=OSError(errno.ENXIO, "no tty")):
            with self.assertRaisesRegex(Refusal, "controlling terminal required"):
                confirm()
        for entry, allowed in ((b"PURGE OS-ZAPRET2-RESTYLE\\n", True),
                               (b"WRONG\\n", False)):
            master, slave = pty.openpty()
            try:
                os.write(master, entry.replace(b"\\n", b"\n"))
                with mock.patch.object(os, "open", return_value=os.dup(slave)):
                    got = confirm()
                self.assertEqual(got == "PURGE OS-ZAPRET2-RESTYLE", allowed)
            finally:
                os.close(slave)
                os.close(master)

    def test_survives_removal_of_its_own_package_file(self):
        code = PACKAGED.read_text()
        self.assertIn('exec /usr/bin/env python3 - "$@" <<', code)
        self.assertIn('run(["/usr/sbin/pkg", "delete", "-y", PACKAGE]', code)
        self.assertIn('"/usr/local/opnsense/scripts/OPNsense/Zapret",', code)
        self.assertIn('backup = backup_config()', code)
        self.assertIn('phrase != "PURGE OS-ZAPRET2-RESTYLE"', code)
        self.assertIn('phrase = read_confirmation_from_tty()', code)
        self.assertNotIn('phrase = input(', code)
        self.assertIn('os.open("/dev/tty"', code)
        self.assertIn('if processes():', code)

    def test_strategies_gui_does_not_expose_purge_links_or_commands(self):
        """Owner decision: remove the purge help UI, not the packaged CLI script."""
        ui = (ROOT / "src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt").read_text()
        for marker in ("zapretUsefulLinks", "zapretPurgeSourceLink",
                       "zapretPurgeInstructions", "zapretPurgeWarning",
                       "purgeText", "Полезные ссылки", "Full purge script source",
                       LOCAL, "PURGE OS-ZAPRET2-RESTYLE"):
            self.assertNotIn(marker, ui, "Unexpected purge UI: " + marker)
        self.assertIn('id="zapretExtraInstall"', ui)
        self.assertIn('id="zapretExtraRemove"', ui)
        self.assertIn('id="reconfigureAct"', ui)

    def test_cli_only_policy_remains_in_spec_and_plan(self):
        for path in ("docs/architecture/OPNSENSE_CLEAN_INSTALL_LIFECYCLE_RECOVERY_SPEC.md",
                     "docs/architecture/OPNSENSE_CLEAN_INSTALL_LIFECYCLE_RECOVERY_PLAN.md"):
            doc = (ROOT / path).read_text()
            self.assertIn("не отображать", doc)
            self.assertIn("Полезные ссылки", doc)
            self.assertIn(LOCAL, doc)
            self.assertIn("--dry-run", doc)
            self.assertIn("--purge", doc)

    def test_package_verify_checks_exact_bytes_and_execute_mode(self):
        code = (ROOT / "scripts/native-opnsense-package.py").read_text()
        self.assertIn('PURGE_SCRIPT = "opnsense/scripts/OPNsense/Zapret/purge-os-zapret2-restyle.sh"', code)
        self.assertIn('archived_file(pkg, PURGE_SCRIPT)', code)
        self.assertIn('for rel in (SERVICE, PURGE_SCRIPT, BINARY', code)

    def test_native_installed_g01_runs_package_executable_and_checks_self_delete(self):
        native = (ROOT / "scripts/stage2-opnsense-real-native-purge.py").read_text()
        self.assertIn('def attest_installed_purger():', native)
        self.assertIn('def attest_package_purger_removed():', native)
        self.assertIn('PACKAGED_PURGER.read_bytes() == PURGER.read_bytes()', native)
        self.assertIn('stat.S_IMODE(details.st_mode) == 0o755', native)
        self.assertIn('not os.path.lexists(PACKAGED_PURGER)', native)
        self.assertEqual(native.count('str(PACKAGED_PURGER), "--purge"'), 2)
        self.assertEqual(native.count('str(PURGER), "--purge"'), 1)
        self.assertIn('str(PACKAGED_PURGER), "--dry-run"', native)
        self.assertIn('G10A_INSTALLED_PACKAGE_PURGER_SELF_DELETE=PASS', native)
        self.assertIn('G01_REAL_CLEAN_INSTALL_DEFAULT_CONFIG_MISMATCH', native)
        self.assertIn('setup_transaction.sh', native)
        self.assertNotIn('NOT_EMPTY_FOR_G01_CONFIG_SEED', native)

    def test_readme_includes_local_safety_instructions(self):
        readme = (ROOT / "README.md").read_text()
        self.assertIn(LOCAL + " --dry-run", readme)
        self.assertIn(LOCAL + " --purge", readme)
        self.assertIn("PURGE OS-ZAPRET2-RESTYLE", readme)
        self.assertIn("Normal GUI uninstall is not purge", readme)

if __name__ == "__main__":
    unittest.main()
