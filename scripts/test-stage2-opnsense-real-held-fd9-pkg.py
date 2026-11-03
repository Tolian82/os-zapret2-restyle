#!/usr/bin/env python3
"""Offline fail-closed contracts: genuine outer FD9 + native pkg hazard probe."""
import ast
from pathlib import Path
import stat
import subprocess
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

SOURCE = Path(__file__).with_name("stage2-opnsense-real-held-fd9-pkg.py")
TEXT = SOURCE.read_text(encoding="utf-8")
TREE = ast.parse(TEXT)

def extract(*names):
    nodes = [n for n in TREE.body if isinstance(n, ast.FunctionDef)
             and n.name in names]
    if len(nodes) != len(names):
        raise AssertionError("MISSING_REQUIRED_NATIVE_PROBE_FUNCTION")
    scope = {"Refusal": RuntimeError, "time": time,
             "subprocess": subprocess, "stat": stat}
    exec(compile(ast.Module(body=nodes, type_ignores=[]),
                 str(SOURCE), "exec"), scope)
    return scope

class RealHeldFd9Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scope = extract("need", "classify", "wait_marker",
                            "independent_fd9_challenge")
        cls.classify = staticmethod(cls.scope["classify"])
        cls.wait = staticmethod(cls.scope["wait_marker"])

    def test_hazard_when_native_pkg_replaces_despite_real_hook_refusal(self):
        self.assertEqual(self.classify("old", "new", 0, "old", "new", True),
                         "OBSERVED_HELD_FD9_NOT_A_NATIVE_PKG_VETO")

    def test_unchanged_pkgdb_is_not_safety_acceptance(self):
        self.assertEqual(self.classify("old", "old", 1, "old", "new", True),
                         "OBSERVED_OLD_PKGDB_RETAINED_WITH_OUTER_FD9")

    def test_foreign_missing_or_incoherent_state_refused(self):
        for before, after, code, refuse, diagnostic in (
                ("wrong", "new", 0, True, "OLD_IDENTITY_NOT_PROVEN"),
                ("old", "other", 1, True, "UNKNOWN_INSTALLED_PACKAGE_IDENTITY"),
                ("old", "new", 1, True, "NEW_PKGDB_WITH_UNSUCCESSFUL_NATIVE_PKG"),
                ("old", "new", 0, False, "GENUINE_PREINSTALL_REFUSAL_NOT_OBSERVED")):
            with self.subTest(diagnostic=diagnostic):
                with self.assertRaisesRegex(RuntimeError, diagnostic):
                    self.classify(before, after, code, "old", "new", refuse)

    def test_marker_and_parent_process_required(self):
        with tempfile.TemporaryDirectory() as root:
            marker = Path(root) / "held"
            alive = SimpleNamespace(poll=lambda: None)
            with self.assertRaisesRegex(RuntimeError, "UNBOUNDED_MARKER_WAIT"):
                self.wait(marker, alive, seconds=9)
            with self.assertRaisesRegex(RuntimeError, "HELD_FD9_SHELL_EARLY_EXIT"):
                self.wait(marker, SimpleNamespace(poll=lambda: 2),
                          seconds=0.5, sleep=lambda _: None)
            marker.touch()
            self.assertTrue(self.wait(marker, alive, seconds=0.5))
            with self.assertRaisesRegex(RuntimeError, "HELD_FD9_MARKER_OR_PROCESS_MISSING"):
                self.wait(marker, SimpleNamespace(poll=lambda: 0), seconds=0.5)

    def test_separate_lock_contender_must_fail_with_exact_75(self):
        scope=self.scope
        scope["CHALLENGER_SHELL"] = 'exec 9>"$1"; /usr/bin/lockf -s -t 0 9'
        holder = Path("/var/run/zapret2-lifecycle.lock")
        recorded = []
        def fake(args, **kwargs):
            recorded.append((args, kwargs))
            return SimpleNamespace(returncode=75)
        scope["subprocess"] = SimpleNamespace(run=fake)
        self.assertTrue(scope["independent_fd9_challenge"](holder))
        self.assertEqual(recorded[0][0][0:3],
                         ["/bin/sh", "-c", scope["CHALLENGER_SHELL"]])
        self.assertEqual(recorded[0][0][-1], str(holder))
        scope["subprocess"] = SimpleNamespace(
            run=lambda *args, **kwargs: SimpleNamespace(returncode=0))
        with self.assertRaisesRegex(RuntimeError, "FD9_HOLD_NOT_EXCLUSIVE"):
            scope["independent_fd9_challenge"](holder)

    def test_actual_original_fd9_and_real_pkg_codepath_in_one_shell(self):
        required = (
            'LIFECYCLE_LOCK = Path("/var/run/zapret2-lifecycle.lock")',
            'exec 9>"$1"',
            '/usr/bin/lockf -s -t 1 9',
            'pkg -o REPO_AUTOUPDATE=false add -f "$4"',
            '"/usr/bin/lockf"',
            'CHALLENGER_SHELL',
            '"/bin/sh", "-c", HELD_PKG_SHELL',
            'start_new_session=True',
            'independent_fd9_challenge(lockfile)',
            'proc.communicate(timeout=220)',
            'os.killpg(proc.pid, signal.SIGKILL)',
            '"STAGE2_HELD_FD9_PKG_PRE_DISPOSAL="')
        for snippet in required:
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, TEXT)
        self.assertLess(TEXT.index('wait_marker(marker, proc)'),
                        TEXT.index('wait_marker(entered, proc)'))
        self.assertLess(TEXT.index('wait_marker(entered, proc)'),
                        TEXT.index('proc.communicate(timeout=220)'))

    def test_real_native_predecessor_optin_and_safety_limits(self):
        for token in (
                "GITHUB_ACTIONS", "DISPOSABLE_HELD_FD9_OPTIN_REQUIRED",
                "clean.plugin_absent()", "stopped.check_old_archive(archive)",
                "native.build()", "installer.install_and_verify(archive)",
                "inspector.snapshot(archive)", "locked.installed_record()",
                "service_before = clean.digest", "config_before =",
                "prior.package_locked()", "incoming_hook_refusal_observed",
                "lh08_ac11_accepted", "False",
                "supported_owner_pre_pkg_admission_implemented",
                "published_package_changed", "owner_appliance_modified"):
            with self.subTest(token=token):
                self.assertIn(token, TEXT)
        for forbidden in ("pkg lock -y", "pkg unlock -y",
                          '"/sbin/ipfw", "-q", "flush"',
                          '"configctl", "zapret", "stop"',
                          "kldunload"):
            self.assertNotIn(forbidden, TEXT)

if __name__ == "__main__":
    unittest.main()
