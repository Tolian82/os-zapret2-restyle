#!/usr/bin/env python3
"""Fail-closed offline contracts for original nested FD9 diagnostic."""
import ast
from pathlib import Path
import stat
import subprocess
import time
from types import SimpleNamespace
from tempfile import TemporaryDirectory
import unittest

SOURCE_FILE = Path(__file__).with_name('stage2-opnsense-real-old-fd9-nonrecursive.py')
SOURCE = SOURCE_FILE.read_text(encoding='utf-8')
TREE = ast.parse(SOURCE)

def functions(*names):
    nodes = [n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name in names]
    if len(nodes) != len(names):
        raise AssertionError('MISSING_NATIVE_DIAGNOSTIC_FUNCTION')
    env = {'Refusal': ValueError, 'time': time, 'stat': stat,
           'subprocess': subprocess}
    exec(compile(ast.Module(body=nodes, type_ignores=[]),
                 str(SOURCE_FILE), 'exec'), env)
    return env

class HistoricalFd9Contracts(unittest.TestCase):
    def test_bounded_diagnostic_classification_not_admission(self):
        f = functions('classify')['classify']
        self.assertEqual(f(None, True, ''),
                         'ORIGINAL_STATUS_NOT_COMPLETED_WITHIN_BOUNDED_FD9_HOLD')
        self.assertEqual(f(1, False, 'zapret is not running'),
                         'ORIGINAL_COLD_STATUS_COMPLETED_UNDER_INHERITED_FD9')
        self.assertEqual(f(0, False, ''),
                         'ORIGINAL_STATUS_OTHER_RESULT_UNDER_INHERITED_FD9')

    def test_wait_refuses_missing_or_early_exited_holder(self):
        f = functions('need', 'wait_held')['wait_held']
        with TemporaryDirectory() as folder:
            marker = Path(folder) / 'held'
            with self.assertRaisesRegex(ValueError, 'UNBOUNDED_LOCK_WAIT'):
                f(marker, SimpleNamespace(poll=lambda: None), 12)
            with self.assertRaisesRegex(ValueError, 'FD9_HOLDER_EARLY_EXIT'):
                f(marker, SimpleNamespace(poll=lambda: 1), .1)
            marker.touch()
            f(marker, SimpleNamespace(poll=lambda: None), .1)

    def test_real_lock_exclusivity_result_75_required(self):
        env = functions('need', 'challenger')
        env['CHALLENGER'] = 'exec 9>"$1"; /usr/bin/lockf -s -t 0 9'
        calls = []
        def fake_run(args, **kwargs):
            calls.append(args)
            return SimpleNamespace(returncode=75)
        env['subprocess'] = SimpleNamespace(run=fake_run)
        env['challenger'](Path('/var/run/zapret2-lifecycle.lock'))
        self.assertEqual(calls[0][-1], '/var/run/zapret2-lifecycle.lock')
        env['subprocess'] = SimpleNamespace(
            run=lambda *args, **kwargs: SimpleNamespace(returncode=0))
        with self.assertRaisesRegex(ValueError, 'INDEPENDENT_FD9_NOT_BUSY'):
            env['challenger'](Path('/var/run/zapret2-lifecycle.lock'))

    def test_no_silent_safe_upgrade_claim(self):
        for required in (
            "LOCK = Path('/var/run/zapret2-lifecycle.lock')",
            '/usr/bin/lockf -s -t 1 9',
            "old.installed_manifest_from_json(record)",
            "inspector.snapshot(archive)",
            "os.killpg(proc.pid, signal.SIGKILL)",
            "'native_pkg_replacement_attempted': False",
            "'supported_admission_proven': False",
            "'lh08_ac11_accepted': False",
            "'owner_appliance_modified': False",
        ):
            with self.subTest(required=required):
                self.assertIn(required, SOURCE)
        for forbidden in ('pkg add -f', 'pkg unlock -y', 'ipfw flush'):
            self.assertNotIn(forbidden, SOURCE)

if __name__ == '__main__':
    unittest.main()
