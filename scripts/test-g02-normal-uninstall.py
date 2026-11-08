#!/usr/bin/env python3
"""Fast, offline G02 contract tests for normal (NOT full-purge) pkg uninstall."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "pkg/+POST_DEINSTALL"


class PostDeinstallTests(unittest.TestCase):
    def test_shell_syntax(self):
        r = subprocess.run(["/bin/sh", "-n", str(HOOK)], capture_output=True, text=True)
        self.assertEqual(0, r.returncode, r.stderr)

    def _execute(self, register_exit=0, php_exit=0, remove_php=False):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            reg = base / "register"
            php = base / "php"
            log = base / "calls.txt"
            user = base / "my-custom-lua"
            user.write_text("PRESERVE\n")
            reg.write_text("#!/bin/sh\nprintf 'register %s\\n' \"$*\" >> \"$G02_CALLS\"\n"
                           f"exit {register_exit}\n")
            php.write_text("#!/bin/sh\n[ \"$1\" = '-r' ] || exit 11\n"
                           "case \"$2\" in *MenuSystem*invalidateCache*) ;; *) exit 12 ;; esac\n"
                           "printf 'php MenuSystem invalidateCache script/load_phalcon.php\\n' >> \"$G02_CALLS\"\n"
                           f"exit {php_exit}\n")
            for p in (reg, php):
                p.chmod(0o755)
            if remove_php:
                php.unlink()
            env = {**os.environ, "FIRMWARE_REGISTER": str(reg),
                   "PHP_BIN": str(php), "G02_CALLS": str(log)}
            result = subprocess.run(["/bin/sh", str(HOOK)],
                                    env=env, capture_output=True, text=True)
            lines = log.read_text().splitlines() if log.exists() else []
            self.assertEqual("PRESERVE\n", user.read_text())
            return result, lines

    def test_stock_unregister_and_native_menu_invalidation_sequence(self):
        result, calls = self._execute()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(2, len(calls))
        self.assertEqual("register remove os-zapret2-restyle", calls[0])
        self.assertIn("MenuSystem", calls[1])
        self.assertIn("invalidateCache", calls[1])
        self.assertIn("script/load_phalcon.php", calls[1])

    def test_failure_of_registrar_stops_without_cache_mutation(self):
        result, calls = self._execute(register_exit=1)
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(["register remove os-zapret2-restyle"], calls)

    def test_failure_of_native_php_is_reported(self):
        result, calls = self._execute(php_exit=1)
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(2, len(calls))

    def test_missing_native_helper_refuses(self):
        result, calls = self._execute(remove_php=True)
        self.assertNotEqual(0, result.returncode)
        self.assertEqual([], calls)

    def test_never_implements_destructive_purge_or_global_gui_restart(self):
        source = HOOK.read_text()
        for forbidden in ("rm -rf ", "pkg autoremove", "pfctl -d", "configctl webgui",
                          "setup.sh uninstall", "system config restore", "os.kill"):
            self.assertNotIn(forbidden, source)
        self.assertIn('invalidateCache()', source)
        self.assertIn('remove os-zapret2-restyle', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
