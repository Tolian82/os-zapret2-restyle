#!/usr/bin/env python3
"""Fast isolated contract tests against the exact Stage 2 stopped replacement functions."""
import ast
import copy
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch
import xml.etree.ElementTree as ET

SOURCE = Path(__file__).with_name('stage2-opnsense-real-native-stopped-upgrade.py')
TREE = ast.parse(SOURCE.read_text(encoding='utf-8'))
FUNCS = {'Refusal', 'need', 'normalized_config', 'check_old_archive',
         'replace_with_actual_pkg', 'execute'}
NODES = [node for node in TREE.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))
         and node.name in FUNCS]
NS = {'copy': copy, 'ET': ET, 'Path': Path, 'os': os,
      'OPTIN': 'ZAPRET2_STAGE2_REAL_STOPPED_UPGRADE', 'REVISION': '63',
      'OLD_VERSION': '0.6.2_1'}
exec(compile(ast.fix_missing_locations(ast.Module(body=NODES, type_ignores=[])),
             str(SOURCE), 'exec'), NS)


class StoppedNativeContracts(unittest.TestCase):
    def test_authoritative_functions_exist(self):
        self.assertEqual(set(n.name for n in NODES), FUNCS)

    def test_requires_disposable_optin_before_native_gate(self):
        NS['native'] = SimpleNamespace(gate=Mock(side_effect=AssertionError('unsafe gate')))
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(NS['Refusal'], 'OPTIN_REQUIRED'):
                NS['execute'](Path('/tmp/untrusted-old.pkg'))
        NS['native'].gate.assert_not_called()

    def test_config_revision_only_is_accepted(self):
        before = b'<opnsense><system><firmware><plugins>os-zapret2-restyle</plugins></firmware></system><revision>1</revision></opnsense>'
        after = b'<opnsense>\n <system><firmware><plugins>os-zapret2-restyle</plugins></firmware></system><revision>2</revision>\n</opnsense>'
        self.assertEqual(NS['normalized_config'](before), NS['normalized_config'](after))

    def test_config_foreign_mutation_is_refused(self):
        a = b'<opnsense><revision>1</revision><system><hostname>before</hostname></system></opnsense>'
        b = a.replace(b'before', b'changed')
        self.assertNotEqual(NS['normalized_config'](a), NS['normalized_config'](b))

    def test_config_duplicate_revision_refused(self):
        with self.assertRaisesRegex(NS['Refusal'], 'AMBIGUOUS'):
            NS['normalized_config'](b'<opnsense><revision>1</revision><revision>2</revision></opnsense>')

    def test_config_malformed_refused(self):
        with self.assertRaisesRegex(NS['Refusal'], 'XML_INVALID'):
            NS['normalized_config'](b'<opnsense>')

    def test_old_archive_checks_version(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'old.pkg'
            path.write_bytes(b'not a real archive; mocked manifest only')
            NS['old'] = SimpleNamespace(NAME='os-zapret2-restyle', ABI='FreeBSD:15:amd64',
                                        archive_data=Mock(return_value=({'name':'os-zapret2-restyle','version':'0.6.2_2','abi':'FreeBSD:15:amd64'}, b'x')))
            with self.assertRaisesRegex(NS['Refusal'], 'IDENTITY_WRONG'):
                NS['check_old_archive'](path)

    def test_actual_replacement_keeps_original_hooks(self):
        result = SimpleNamespace(returncode=0, stdout='os-zapret2-restyle was installed.\n', stderr='')
        NS['clean'] = SimpleNamespace(run=Mock(return_value=result))
        p = Path('/tmp/successor.pkg')
        self.assertTrue(NS['replace_with_actual_pkg'](p)['original_postinstall_success_observed'])
        NS['clean'].run.assert_called_once_with(
            ['pkg', '-o', 'REPO_AUTOUPDATE=false', 'add', '-f', str(p)], timeout=230)

    def test_pkg_zero_without_hook_confirmation_refused(self):
        NS['clean'] = SimpleNamespace(run=Mock(return_value=SimpleNamespace(
            returncode=0, stdout='Installation completed', stderr='post hook unavailable')))
        with self.assertRaisesRegex(NS['Refusal'], 'POSTINSTALL_NOT_PROVEN'):
            NS['replace_with_actual_pkg'](Path('/tmp/successor.pkg'))


if __name__ == '__main__':
    unittest.main()
