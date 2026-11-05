#!/usr/bin/env python3
"""Off-target negative controls for the genuine installed lo0 lifecycle."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import os
import tempfile
import unittest

SOURCE = Path(__file__).with_name('stage2-opnsense-real-native-active-service.py')
spec = importlib.util.spec_from_file_location('native_active_service', SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def result(code=0, stdout='', stderr=''):
    return SimpleNamespace(returncode=code, stdout=stdout, stderr=stderr)


class RealNativeActiveContracts(unittest.TestCase):
    def simulate(self, fail=None, change_config=None):
        calls = []
        live_pids = iter((100, 101, 102, 103, 103, 103))
        def act(name, python_down=False):
            calls.append((name, python_down))
            if fail == (name, python_down):
                return result(1, stderr='unverified service failure')
            if python_down and name != 'stop':
                return result(69, stderr='ERROR: required python runtime unavailable')
            return result()
        def live(sha):
            self.assertEqual(sha, 'e' * 64)
            return {'pid': next(live_pids), 'rules': ['19000 divert 989 to lo0:65431']}
        stopped_count = []
        def stopped():
            stopped_count.append(True)
            if fail == 'stopped':
                raise mod.Refusal('STOP_LEFT_PLUGIN_RULES')
        saved_count = []
        def saved():
            saved_count.append(True)
            return b'<config>mutated</config>' if (change_config and len(saved_count) == change_config) else b'<config/>'
        return (mod.cycle(act, live, stopped, saved, 'e' * 64),
                calls, stopped_count)

    def test_real_complete_service_sequence_and_python_down(self):
        report, calls, stopped = self.simulate()
        self.assertEqual(calls, [('reconfigure', False), ('restart', False),
                                 ('stop', False), ('start', False),
                                 ('restart', True), ('reconfigure', True), ('stop', True)])
        self.assertEqual(len(stopped), 2)
        self.assertEqual(report['actions'], ['reconfigure', 'restart', 'stop', 'start'])
        self.assertFalse(report['shared_voice_owner_tested'])

    def test_real_restart_failure_does_not_pass(self):
        with self.assertRaisesRegex(mod.Refusal, 'REAL_RESTART_FAILED'):
            self.simulate(fail=('restart', False))

    def test_real_start_failure_does_not_pass(self):
        with self.assertRaisesRegex(mod.Refusal, 'START_AFTER_STOP_FAILED'):
            self.simulate(fail=('start', False))

    def test_real_stop_failure_does_not_pass(self):
        with self.assertRaisesRegex(mod.Refusal, 'REAL_STOP_FAILED'):
            self.simulate(fail=('stop', False))

    def test_python_down_restart_requires_specific_refusal(self):
        with self.assertRaisesRegex(mod.Refusal, 'PYTHON_DOWN_RESTART_NOT_REFUSED'):
            self.simulate(fail=('restart', True))

    def test_python_down_verified_stop_cannot_lie(self):
        with self.assertRaisesRegex(mod.Refusal, 'VERIFIED_PYTHON_DOWN_STOP_FAILED'):
            self.simulate(fail=('stop', True))

    def test_config_change_detected_before_next_action(self):
        with self.assertRaisesRegex(mod.Refusal, 'RECONFIGURE_CHANGED_SAVED_CONFIG'):
            self.simulate(change_config=2)

    def test_unverified_stop_owner_refused(self):
        with self.assertRaisesRegex(mod.Refusal, 'STOP_LEFT_PLUGIN_RULES'):
            self.simulate(fail='stopped')

    def test_requires_explicit_optin_before_accessing_guest(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(
                mod, 'installed_guest_identity', side_effect=AssertionError('must not probe guest')):
            with self.assertRaisesRegex(mod.Refusal, 'DISPOSABLE_RUNNING_CI_OPTIN_REQUIRED'):
                mod.guest_preflight()

    def test_installed_guest_accepts_known_vm_with_package_present(self):
        observed = []
        def read(argv, reason):
            observed.append(argv)
            return {('opnsense-version','-a'): '26.7',
                    ('pkg','config','ABI'): 'FreeBSD:15:amd64',
                    ('sysctl','-n','kern.vm_guest'): 'kvm'}[tuple(argv)]
        with patch.object(mod, 'required', side_effect=read), patch.object(
                mod, 'load', create=True,
                side_effect=AssertionError('fresh guest check invalid')):
            mod.installed_guest_identity()
        self.assertEqual(len(observed), 3)

    def test_installed_guest_rejects_foreign_platform(self):
        with patch.object(mod, 'required', side_effect=['26.7', 'FreeBSD:14:amd64']):
            with self.assertRaisesRegex(mod.Refusal, 'PKG_ABI_UNQUALIFIED'):
                mod.installed_guest_identity()

    def test_revision_sourced_only_from_makefile(self):
        with tempfile.TemporaryDirectory() as td, patch.object(mod, 'ROOT', Path(td)):
            (Path(td) / 'VERSION').write_text('0.6.2\n')
            (Path(td) / 'Makefile').write_text('PLUGIN_REVISION=    143\n')
            self.assertEqual(mod.qualified_revision(), '0.6.2_143')


if __name__ == '__main__':
    unittest.main()
