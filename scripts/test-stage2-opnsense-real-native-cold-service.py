#!/usr/bin/env python3
"""Offline negative controls for installed cold native service lifecycle."""
import importlib.util
from pathlib import Path
import os
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'native_cold_service', HERE / 'stage2-opnsense-real-native-cold-service.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def outcome(action, case='ok'):
    if action == 'status':
        return SimpleNamespace(returncode=1, stdout='zapret is not running\n', stderr='')
    if case == 'false_success':
        return SimpleNamespace(returncode=0, stdout='', stderr='')
    if case == 'foreign_failure':
        return SimpleNamespace(returncode=69, stdout='', stderr='other failure')
    return SimpleNamespace(returncode=1, stdout='',
                           stderr='ERROR: zapret2 runtime is not installed or installation is incomplete')


class ColdServiceContracts(unittest.TestCase):
    def setUp(self):
        self.baseline = {'config_sha256': 'a' * 64, 'runtime_present': False,
                         'markers_present': [],
                         'ipfw': {'available': False, 'rules': []}}

    def simulate(self, broken=None, snapshots=None):
        actions = []
        def invoke(argv):
            action = argv[1]
            actions.append(action)
            return outcome(action, broken if action == 'restart' else 'ok')
        images = iter(snapshots) if snapshots else None
        def observe():
            return next(images) if images else self.baseline
        return mod.exercise(invoke=invoke, observe=observe), actions

    def test_exact_start_restart_reconfigure_and_status(self):
        result, actions = self.simulate()
        self.assertEqual(actions, ['start', 'status', 'restart', 'status',
                                   'reconfigure', 'status'])
        self.assertEqual(result['actions'], list(mod.ACTIONS))
        self.assertFalse(result['boot_tested'])
        self.assertFalse(result['common_running_owner_tested'])

    def test_false_restart_success_refused(self):
        with self.assertRaisesRegex(mod.Refusal, 'RESTART_DID_NOT_REFUSE'):
            self.simulate(broken='false_success')

    def test_unexpected_error_not_laundered_as_engine_absent(self):
        with self.assertRaisesRegex(mod.Refusal, 'RESTART_DID_NOT_REFUSE'):
            self.simulate(broken='foreign_failure')

    def test_config_mutation_refused(self):
        changed = dict(self.baseline, config_sha256='b' * 64)
        with self.assertRaisesRegex(mod.Refusal, 'START_MUTATED_CONFIG'):
            self.simulate(snapshots=[self.baseline, changed])

    def test_new_owner_marker_refused(self):
        changed = dict(self.baseline, markers_present=['/var/run/dvtws2.pid'])
        with self.assertRaisesRegex(mod.Refusal, 'START_MUTATED_CONFIG'):
            self.simulate(snapshots=[self.baseline, changed])

    def test_ipfw_mutation_refused(self):
        changed = dict(self.baseline,
                       ipfw={'available': True,
                             'rules': ['19000 divert 989 tcp from any to any 443']})
        with self.assertRaisesRegex(mod.Refusal, 'START_MUTATED_CONFIG'):
            self.simulate(snapshots=[self.baseline, changed])

    def test_preexisting_plugin_rule_refused(self):
        self.baseline['ipfw']['rules'] = ['19000 divert 989 tcp from any to any 443']
        with self.assertRaisesRegex(mod.Refusal, 'BASELINE_NOT_EMPTY'):
            self.simulate()

    def test_missing_explicit_guest_optin(self):
        with patch.dict(os.environ, {'GITHUB_ACTIONS': 'true',
                                      'ZAPRET2_NATIVE_BUILD_CI': '1',
                                      mod.OPTIN: ''}):
            with self.assertRaisesRegex(mod.Refusal, 'OPTIN_REQUIRED'):
                mod.preflight()

    def test_exact_source_sha_uses_existing_explicit_git_safe_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            installed = root / 'installed/zapret_service.sh'
            installed.parent.mkdir(parents=True)
            installed.write_bytes(b'#!/bin/sh\nexit 0\n')
            source = root / 'src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh'
            source.parent.mkdir(parents=True)
            source.write_bytes(installed.read_bytes())
            python = root / 'installed/python_runtime.sh'
            python.write_bytes(b'#!/bin/sh\nexit 0\n')
            config = root / 'config.xml'
            config.write_bytes(b'<opnsense/>')
            (root / 'VERSION').write_text('0.6.2\n')
            (root / 'Makefile').write_text('PLUGIN_REVISION=    142\n')
            sha = 'a' * 40
            def fake_stdout(argv, reason):
                if argv[0] == 'opnsense-version':
                    return '26.7'
                if argv[0] == 'pkg':
                    return 'FreeBSD:15:amd64' if 'config' in argv else '0.6.2_142'
                if argv[0] == 'sysctl':
                    return 'kvm'
                if argv[0] == 'git':
                    self.assertEqual(argv, ['git', '-c', 'safe.directory=' + str(root),
                                            '-C', str(root), 'rev-parse', 'HEAD'])
                    return sha
                self.fail('unexpected preflight command ' + repr(argv))
            with patch.multiple(mod, ROOT=root, SERVICE=installed, PYTHON=python,
                                CONFIG=config, ENGINE=root / 'missing-engine',
                                MARKERS=[root / 'missing-marker']), \
                 patch.dict(os.environ, {'GITHUB_ACTIONS': 'true',
                                         'ZAPRET2_NATIVE_BUILD_CI': '1',
                                         mod.OPTIN: '1',
                                         'ZAPRET2_NATIVE_PROJECT_SHA': sha}), \
                 patch.object(mod.os, 'geteuid', return_value=0), \
                 patch.object(mod.os, 'uname',
                              return_value=SimpleNamespace(sysname='FreeBSD', machine='amd64')), \
                 patch.object(mod, 'stdout', side_effect=fake_stdout), \
                 patch.object(mod, 'run', return_value=SimpleNamespace(returncode=0)):
                mod.preflight()

    def test_package_source_revision_comes_from_makefile(self):
        with tempfile.TemporaryDirectory() as root, patch.object(mod, 'ROOT', Path(root)):
            (Path(root) / 'VERSION').write_text('0.6.2\n')
            (Path(root) / 'Makefile').write_text('PLUGIN_REVISION=    142\n')
            self.assertEqual(mod.installed_revision(), '0.6.2_142')


if __name__ == '__main__':
    unittest.main()
