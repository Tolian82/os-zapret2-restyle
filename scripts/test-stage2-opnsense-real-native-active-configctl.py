#!/usr/bin/env python3
"""Off-target negatives for installed OPNsense configctl-to-service lifecycle."""
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest

SOURCE = Path(__file__).with_name('stage2-opnsense-real-native-active-configctl.py')
spec = importlib.util.spec_from_file_location('real_native_configctl', SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def outcome(rc=0, stdout='', stderr=''):
    return SimpleNamespace(returncode=rc, stdout=stdout, stderr=stderr)


def action_config(command_change=None):
    lines = []
    for name in (*mod.ACTIONS, 'status'):
        command = mod.expected_action(name)
        if name == command_change:
            command += ' ; untrusted'
        action_type = 'script_output' if name == 'status' else 'script'
        lines += [f'[{name}]', 'command:' + command, 'parameters:',
                  'type:' + action_type, 'message:fixture', '']
    return '\n'.join(lines).encode()


class InstalledConfigctlContracts(unittest.TestCase):
    def run_cycle(self, *, fail=None, pid_reused=False, config_drift=False):
        pids = iter([101, 101 if pid_reused else 102, 103])
        calls = []
        statuses = []
        saves = 0

        def invoke(name):
            calls.append(name)
            return outcome(1 if fail == name else 0, stderr='failed' if fail == name else '')

        def live(sha):
            self.assertEqual(sha, 'a' * 64)
            return {'pid': next(pids), 'rules': ['19000 divert 989 out via lo0']}

        def stopped():
            statuses.append('stopped')
            if fail == 'stopped':
                raise mod.Refusal('STOP_LEFT_OWNED_RULES')

        def check(state, pid):
            self.assertEqual(pid is not None, state)
            statuses.append('running' if state else 'status-stopped')
            if fail == 'status':
                raise mod.Refusal('CONFIGCTL_STATUS_WRONG_SERVICE_STATE')

        def saved():
            nonlocal saves
            saves += 1
            if config_drift and saves == 2:
                return b'changed'
            return b'original'

        report = mod.cycle(invoke, live, stopped, saved, check, 'a' * 64)
        return report, calls, statuses

    def test_valid_native_script_and_output_bindings(self):
        self.assertTrue(mod.inspect_bindings(action_config()))
        self.assertEqual(mod.expected_action('status'), mod.SERVICE + ' status; exit 0')

    def test_tampered_action_command_rejected(self):
        with self.assertRaisesRegex(mod.Refusal, 'COMMAND_CHANGED:restart'):
            mod.inspect_bindings(action_config('restart'))

    def test_non_script_start_rejected(self):
        raw = action_config().replace(b'[start]\ncommand:', b'[start]\ncommand:')
        raw = raw.replace(b'type:script\n', b'type:script_output\n', 1)
        with self.assertRaisesRegex(mod.Refusal, 'TYPE_CHANGED:start'):
            mod.inspect_bindings(raw)

    def test_duplicate_status_section_rejected(self):
        with self.assertRaisesRegex(mod.Refusal, 'ACTION_PARSE_INVALID'):
            mod.inspect_bindings(action_config() + b'\n[status]\ncommand:duplicate\n')

    def test_missing_lifecycle_section_rejected(self):
        raw = action_config().replace(b'[stop]\n', b'[other]\n')
        with self.assertRaisesRegex(mod.Refusal, 'ACTION_MISSING:stop'):
            mod.inspect_bindings(raw)

    def test_genuine_configctl_lifecycle_sequence(self):
        report, calls, states = self.run_cycle()
        self.assertEqual(calls, ['start', 'restart', 'reconfigure', 'stop'])
        self.assertEqual(states, ['stopped', 'status-stopped', 'running',
                                  'running', 'running', 'stopped', 'status-stopped'])
        self.assertTrue(report['real_dvtws2_pids_replaced'])
        self.assertFalse(report['web_gui_click_tested'])

    def test_refuse_failed_real_restart(self):
        with self.assertRaisesRegex(mod.Refusal, 'CONFIGCTL_RESTART_FAILED'):
            self.run_cycle(fail='restart')

    def test_refuse_reused_engine_pid(self):
        with self.assertRaisesRegex(mod.Refusal, 'RESTART_PID_NOT_REPLACED'):
            self.run_cycle(pid_reused=True)

    def test_refuse_config_mutation(self):
        with self.assertRaisesRegex(mod.Refusal, 'START_CHANGED_CONFIG'):
            self.run_cycle(config_drift=True)

    def test_refuse_unverified_stopped_state(self):
        with self.assertRaisesRegex(mod.Refusal, 'STOP_LEFT_OWNED_RULES'):
            self.run_cycle(fail='stopped')

    def test_refuse_inaccurate_configctl_status(self):
        with self.assertRaisesRegex(mod.Refusal, 'STATUS_WRONG_SERVICE_STATE'):
            self.run_cycle(fail='status')

    def test_status_requires_real_service_match(self):
        with patch.object(mod, 'invoke', return_value=outcome(0, 'zapret is running\n')), \
             patch.object(mod.active, 'action', return_value=outcome(1, 'zapret is not running\n')):
            with self.assertRaisesRegex(mod.Refusal, 'STATUS_DIFFERENT'):
                mod.check_status(True)

    def test_status_running_reports_exact_verified_engine_pid(self):
        with patch.object(mod, 'invoke',
                          return_value=outcome(0, 'zapret is running as pid 4321\n')), \
             patch.object(mod.active, 'action',
                          return_value=outcome(0, 'zapret is running as pid 4321\n')):
            self.assertEqual(mod.check_status(True, 4321),
                             'zapret is running as pid 4321')

    def test_status_running_rejects_mismatched_engine_pid(self):
        with patch.object(mod, 'invoke',
                          return_value=outcome(0, 'zapret is running as pid 4321\n')), \
             patch.object(mod.active, 'action',
                          return_value=outcome(0, 'zapret is running as pid 4321\n')):
            with self.assertRaisesRegex(mod.Refusal, 'RUNNING_PID_OR_STATUS_MISMATCH'):
                mod.check_status(True, 9999)

    def test_refuse_without_explicit_optin_before_guest_probe(self):
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(mod.active, 'guest_preflight',
                          side_effect=AssertionError('unsafe guest probe')):
            with self.assertRaisesRegex(mod.Refusal, 'CONFIGCTL_CI_OPTIN_REQUIRED'):
                mod.preflight()


if __name__ == '__main__':
    unittest.main()
