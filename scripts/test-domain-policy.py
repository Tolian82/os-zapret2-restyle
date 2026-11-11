#!/usr/bin/env python3
"""Unit and CLI checks for the single Python domain policy."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'src' / 'opnsense' / 'scripts' / 'OPNsense' / 'Zapret' / 'backend' / 'domain_policy.py'
SPEC = importlib.util.spec_from_file_location('domain_policy', MODULE)
assert SPEC and SPEC.loader
policy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(policy)


class DomainPolicyTests(unittest.TestCase):
    def test_ordinary_and_legacy(self):
        for src, want in {
            ' EXAMPLE.COM  ': 'example.com',
            'https://Example.com/path?q=1': 'example.com',
            'HTTP://YouTube.com/': 'youtube.com',
            '*.Example.com': 'example.com',
            'Example.COM,': 'example.com',
            '': '',
        }.items():
            with self.subTest(src=src):
                self.assertEqual(policy.normalize(src, 'youtube')['normalized'], want)

    def test_modifiers(self):
        for src, want in {
            '!Example.com': '!example.com',
            '^Example.com': '^example.com',
            '!^Example.com': '!^example.com',
            '^!Example.com': '!^example.com',
            '!https://Example.com/path': '!example.com',
        }.items():
            with self.subTest(src=src):
                self.assertEqual(policy.normalize(src, 'user')['normalized'], want)
        result = policy.normalize('!^Example.com\n^!example.com', 'user')
        self.assertEqual((result['normalized'], result['duplicates']), ('!^example.com', 1))

    def test_invalid(self):
        for src, code, line in [
            ('example.com\n!example.com', 'conflicting_modifiers', 2),
            ('^example.com\nexample.com', 'conflicting_modifiers', 2),
            ('!!example.com', 'repeated_modifier', 1),
            ('^^example.com', 'repeated_modifier', 1),
            ('!^!example.com', 'repeated_modifier', 1),
            ('!', 'missing_domain', 1),
            ('^*.example.com', 'modifier_with_wildcard', 1),
            ('127.0.0.1', 'ip_in_domain_list', 1),
            ('example..com', 'invalid_domain', 1),
            ('bad-.example.com', 'invalid_domain', 1),
            ('bad_.com', 'invalid_domain', 1),
        ]:
            with self.subTest(src=src):
                with self.assertRaises(policy.DomainPolicyError) as context:
                    policy.normalize(src, 'youtube')
                self.assertEqual((context.exception.code, context.exception.line), (code, line))

    def test_exclude_is_separate(self):
        self.assertEqual(policy.normalize('Example.COM', 'exclude')['normalized'], 'example.com')
        for src in ('!example.com', '^example.com', '^!example.com'):
            with self.subTest(src=src):
                with self.assertRaises(policy.DomainPolicyError) as context:
                    policy.normalize(src, 'exclude')
                self.assertEqual(context.exception.code, 'modifiers_not_allowed')

    def test_deduplication(self):
        got = policy.normalize('Example.com\nexample.com\nOther.com', 'user')
        self.assertEqual(got['normalized'], 'example.com\nother.com')
        self.assertEqual((got['duplicates'], got['entry_count'], got['changed']), (1, 2, 2))

    def test_inspect_and_single_are_consistent_and_atomic(self):
        with tempfile.TemporaryDirectory(prefix='domain-policy-') as tmp:
            root = Path(tmp)
            source, target = root / 'input.txt', root / 'out.txt'
            source.write_text('^!Example.com\nPlain.com\n', encoding='utf-8')
            cmd = [sys.executable, str(MODULE)]
            result = subprocess.run(cmd + ['inspect'], input=json.dumps({
                'kind': 'youtube', 'text': source.read_text()
            }), text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            expected = json.loads(result.stdout)['normalized'] + '\n'
            written = subprocess.run(cmd + ['single', 'youtube', str(source), str(target)],
                                     capture_output=True, text=True)
            self.assertEqual(written.returncode, 0, written.stderr)
            self.assertEqual(target.read_text(), expected)
            source.write_text('Plain.com\n!Plain.com\n')
            rejected = subprocess.run(cmd + ['single', 'youtube', str(source), str(target)],
                                      capture_output=True, text=True)
            self.assertEqual(rejected.returncode, 2)
            self.assertIn('line 2:', rejected.stderr)
            self.assertEqual(target.read_text(), expected)
            self.assertFalse(list(root.glob('.domain-policy-*')))
            invalid = subprocess.run(cmd + ['inspect'], input=json.dumps({
                'kind': 'youtube', 'text': source.read_text()
            }), text=True, capture_output=True)
            self.assertEqual(invalid.returncode, 2)
            self.assertEqual(json.loads(invalid.stdout)['error']['code'], 'conflicting_modifiers')


if __name__ == '__main__':
    unittest.main()
