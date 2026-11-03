#!/usr/bin/env python3
"""Negative-only source contracts: historical FD9 recursion vs pre-pkg gate."""
import ast
from pathlib import Path
import time
from types import SimpleNamespace
import unittest

SOURCE = Path(__file__).with_name("stage2-opnsense-old-fd9-recursion-prepkg.py")
TEXT = SOURCE.read_text(encoding="utf-8")
TREE = ast.parse(TEXT)

def extract(*names):
    nodes = [node for node in TREE.body if isinstance(node, ast.FunctionDef)
             and node.name in names]
    if len(nodes) != len(names):
        raise AssertionError("TESTED_NATIVE_GATE_FUNCTION_MISSING")
    namespace = {"Refusal": RuntimeError, "time": time}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), "exec"),
         namespace)
    return namespace

class OldFd9PrePkgNegativeContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ns = extract("need", "refuse_before_pkg", "marker")
        cls.admit = staticmethod(cls.ns["refuse_before_pkg"])
        cls.sha = "a" * 64

    def test_busy_fd9_refused_without_attempting_pkg(self):
        calls = []
        outcome = self.admit(False, 1, self.sha,
                             lambda: calls.append("destructive-pkg"))
        self.assertEqual(outcome, "REFUSED_BUSY_OR_INHERITED_FD9_BEFORE_PKG")
        self.assertEqual(calls, [])

    def test_old_status_two_or_unknown_refused_before_pkg(self):
        calls = []
        for state in (0, 2, 75, -1, 99, None):
            with self.subTest(state=state):
                self.assertEqual(
                    self.admit(True, state, self.sha,
                               lambda: calls.append("destructive-pkg")),
                    "REFUSED_UNVERIFIED_OLD_OWNER_BEFORE_PKG")
        self.assertEqual(calls, [])

    def test_healthy_owner_not_misrepresented_as_qualified_admission(self):
        calls = []
        self.assertEqual(
            self.admit(True, 1, self.sha, lambda: calls.append("pkg")),
            "REFUSED_NO_SUPPORTED_MANAGED_PKG_ADAPTER")
        self.assertEqual(calls, [])

    def test_bad_archive_digest_not_accepted_for_any_state(self):
        for digest in ("", "a" * 63, "A" * 64, "g" * 64, "0" * 65):
            with self.subTest(digest=digest):
                with self.assertRaisesRegex(RuntimeError,
                                            "CANDIDATE_ARCHIVE_SHA_UNVERIFIED"):
                    self.admit(False, 2, digest, lambda: None)

    def test_marker_requires_bound_live_owner_and_no_symlink(self):
        with unittest.mock.patch.object(time, "monotonic", side_effect=[0, 1]):
            with self.assertRaisesRegex(RuntimeError, "UNBOUNDED_MARKER_WAIT"):
                self.ns["marker"](Path("/nonexistent"), SimpleNamespace(
                    poll=lambda: None), bound=9)

    def test_native_default_fd9_and_real_old_service_call(self):
        required = (
            'FD9 = Path("/var/run/zapret2-lifecycle.lock")',
            'LIFECYCLE_LOCK',
            '"/usr/bin/lockf"',
            '/usr/bin/lockf -s -t 1 9',
            '"/usr/bin/lockf -s -t 0 9',
            'STATUS_UNDER_HELD_FD9',
            'str(service)',
            'marker(ready, proc)',
            'challenge(lockfile) == 75',
            'marker(entered, proc)',
            'proc.communicate(timeout=4.5)',
            'os.killpg(proc.pid, signal.SIGKILL)',
            'challenge(lockfile) == 0'
        )
        for text in required:
            with self.subTest(text=text):
                self.assertIn(text, TEXT)

    def test_real_negatives_and_no_destructive_pkg_in_entrypoint(self):
        for text in ("clean.plugin_absent()", "stopped.check_old_archive(archive)",
                     "native.build()", "installer.install_and_verify(archive)",
                     "inspector.snapshot(archive)", "foreign.activate_kernel(inspector)",
                     "unsafe.add_test_orphan()", "status.returncode == 2",
                     "refuse_before_pkg(False, 1",
                     "refuse_before_pkg(True, status.returncode",
                     "destructive_pkg_callbacks_invoked",
                     '"real_native_pkg_replacement_invoked": False',
                     '"lh08_ac11_accepted": False'):
            with self.subTest(text=text):
                self.assertIn(text, TEXT)
        for forbidden in ("pkg add -f", "pkg remove -y", "pkg unlock",
                          "kldunload", '"/sbin/ipfw", "-q", "flush"'):
            self.assertNotIn(forbidden, TEXT)
        fn = next(x for x in TREE.body if isinstance(x, ast.FunctionDef)
                  and x.name == "refuse_before_pkg")
        self.assertFalse(any(isinstance(x, ast.Call)
                             and isinstance(x.func, ast.Name)
                             and x.func.id == "invoke_pkg"
                             for x in ast.walk(fn)))

if __name__ == "__main__":
    unittest.main()
