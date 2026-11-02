#!/usr/bin/env python3
"""Fast, fail-closed Stage 2.24 configuration worker provenance tests."""
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).with_name('stage2-configd-worker-readonly.py')
spec = importlib.util.spec_from_file_location('stage2_configd_readonly', SOURCE)
witness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(witness)


def row(pid, ppid, command, birth='Mon Nov  2 20:21:00 2026'):
    return f'{pid} {ppid} {birth} {command}\n'


def result(data='', code=0):
    return SimpleNamespace(stdout=data, stderr='', returncode=code)


class WorkerIdentityTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.pidfile = Path(self.root.name) / 'configd.pid'
        self.pidfile.write_text('4142\n')
        self.watcher = row(4142, 1, 'python3 /usr/local/opnsense/service/configd.py')
        self.worker = row(4242, 4142, 'python3 /usr/local/opnsense/service/configd.py console')

    def fake(self, *args):
        if args[0] == '/bin/ps':
            return result(self.watcher if args[3] == '4142' else self.worker)
        if args[0] == '/usr/bin/pgrep':
            return result('4242\n')
        if args[0] == '/usr/local/sbin/configctl':
            return result('OK\n')
        raise AssertionError('unexpected probe: ' + str(args))

    def test_success_is_explicitly_readonly_not_signal_authorization(self):
        with patch.dict(os.environ, {'GITHUB_ACTIONS':'true',
                     'ZAPRET2_STAGE2_READONLY_CONFIGD_CI':'1'}), patch.object(
                         witness, 'run', side_effect=self.fake) as calls:
            output = witness.verify(self.pidfile)
        self.assertTrue(output['direct_child'])
        for field in ('signals_sent', 'actions_reloaded', 'restart_authorized',
                      'pid_reuse_excluded_after_observation'):
            self.assertFalse(output[field])
        self.assertEqual(calls.call_count, 7)

    def test_no_disposable_optin_refuses_before_probe(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(
                witness, 'snapshot', side_effect=AssertionError('unsafe')):
            with self.assertRaisesRegex(witness.Refusal, 'OPTIN_REQUIRED'):
                witness.verify(self.pidfile)

    def test_untrusted_pidfile_and_bad_pid_refuse(self):
        self.pidfile.unlink()
        self.pidfile.symlink_to(Path(self.root.name) / 'elsewhere')
        with self.assertRaisesRegex(witness.Refusal, 'UNTRUSTED'):
            witness.read_pid(self.pidfile)
        self.pidfile.unlink()
        self.pidfile.write_text('abc\n')
        with self.assertRaisesRegex(witness.Refusal, 'INVALID'):
            witness.read_pid(self.pidfile)

    def test_worker_direct_parent_required(self):
        self.worker = row(4242, 99, 'python3 /usr/local/opnsense/service/configd.py console')
        with patch.object(witness, 'run', side_effect=self.fake):
            with self.assertRaisesRegex(witness.Refusal, 'PARENT_MISMATCH'):
                witness.snapshot(self.pidfile)

    def test_worker_command_path_and_suffix_refuse_separately(self):
        for command, reason in (
            ('python3 /tmp/foreign/configd.py console', 'COMMAND_PATH_MISMATCH'),
            ('python3 /usr/local/opnsense/service/configd.py other',
             'CONSOLE_ROLE_MISMATCH')):
            self.worker = row(4242, 4142, command)
            with self.subTest(reason=reason), patch.object(witness, 'run', side_effect=self.fake):
                with self.assertRaisesRegex(witness.Refusal, reason):
                    witness.snapshot(self.pidfile)

    def test_real_worker_extra_arguments_do_not_hide_verified_console_role(self):
        self.worker = row(4242, 4142,
                          'python3 /usr/local/opnsense/service/configd.py console --worker-info')
        with patch.object(witness, 'run', side_effect=self.fake):
            self.assertEqual(witness.snapshot(self.pidfile)['worker']['ppid'], 4142)

    def test_watcher_not_a_console_worker(self):
        self.watcher = row(4142, 1, 'python3 /usr/local/opnsense/service/configd.py console')
        with patch.object(witness, 'run', side_effect=self.fake):
            with self.assertRaisesRegex(witness.Refusal, 'WATCHER_NOT_OWNED'):
                witness.snapshot(self.pidfile)

    def test_missing_or_multiple_workers_refuse(self):
        for data, code in (('', 1), ('4242\n5252\n', 0)):
            def fake(*args):
                if args[0] == '/usr/bin/pgrep':
                    return result(data, code)
                return self.fake(*args)
            with self.subTest(data=data), patch.object(witness, 'run', side_effect=fake):
                with self.assertRaises(witness.Refusal):
                    witness.snapshot(self.pidfile)

    def test_recycled_pid_or_worker_turnover_refused(self):
        first = {'watcher': {'pid':4142, 'birth':'a'}, 'worker':{'pid':4242,'birth':'b'}}
        second = {'watcher': {'pid':4142, 'birth':'a'}, 'worker':{'pid':4242,'birth':'c'}}
        with patch.dict(os.environ, {'GITHUB_ACTIONS':'true',
                    'ZAPRET2_STAGE2_READONLY_CONFIGD_CI':'1'}), patch.object(
                        witness, 'snapshot', side_effect=[first,second]), patch.object(
                            witness, 'run', return_value=result('OK')):
            with self.assertRaisesRegex(witness.Refusal, 'PID_REUSE_OR_WORKER_ROTATION'):
                witness.verify(self.pidfile)

    def test_configctl_failure_refuses(self):
        with patch.dict(os.environ, {'GITHUB_ACTIONS':'true',
                   'ZAPRET2_STAGE2_READONLY_CONFIGD_CI':'1'}), patch.object(
                       witness, 'snapshot', return_value={'same':True}), patch.object(
                           witness, 'run', return_value=result('', 1)):
            with self.assertRaisesRegex(witness.Refusal, 'NOT_READY'):
                witness.verify(self.pidfile)

    def test_no_mutating_calls_in_witness(self):
        text = SOURCE.read_text()
        for forbidden in ("'/bin/kill'", "'pkill'", "'service'", 'os.kill(',
                          'os.system(', 'subprocess.Popen(', 'rm -f', 'pkg add',
                          "'restart'", "'reload'"):
            self.assertNotIn(forbidden, text)


if __name__ == '__main__':
    unittest.main()
