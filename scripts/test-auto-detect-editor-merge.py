#!/usr/bin/env python3
"""TZ6v2 found-editor three-way user-intent and fail-closed unit contracts.

Production tests import the original pinned-PSL domain_policy; no HTTP,
Config writer, temporary source rewrite or engine activation is involved.
"""
import hashlib
from pathlib import Path
import sys
import unittest

BACKEND = (Path(__file__).resolve().parents[1] / 'src/opnsense/scripts/'
           'OPNsense/Zapret/backend')
sys.path.insert(0, str(BACKEND))
from domain_policy import PublicSuffixList
from auto_detect_editor_merge import EditorMergeRefused, preview_found_merge


def record(text, status=None):
    status = status or ('populated' if text else 'empty')
    return {'status': status, 'content': text,
            'revision': hashlib.sha256(b'missing\0' if status == 'missing'
                    else b'present\0' + text.encode('utf-8')).hexdigest()}


class ThreeWayEditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.psl = PublicSuffixList.load()

    def preview(self, source, baseline, draft, current):
        return preview_found_merge(source, baseline, draft, current,
                                   psl=self.psl)

    def test_owner_variant_a_user_delete_and_independent_background_discovery(self):
        for source in ('youtube', 'user', 'auto'):
            with self.subTest(source=source):
                result = self.preview(source, record('example.com\n'), '',
                                      record('example.com\nexample.org\n'))
                self.assertEqual(result['content'], 'example.org\n')
                self.assertEqual((result['user_removed'], result['user_added']),
                                 (1, 0))
                self.assertTrue(result['rebased'])
                self.assertTrue(result['would_change_current'])
                self.assertFalse(result['commit_authorized'])
                self.assertFalse(result['cross_source_validated'])

    def test_rebase_keeps_both_manual_addition_and_background_addition(self):
        result = self.preview('youtube', record('example.com\n'),
                              'example.com\nnew.example.net\n',
                              record('background.org\nexample.com\n'))
        self.assertEqual(result['content'],
                         'background.org\nexample.com\nexample.net\n')
        self.assertEqual(result['user_added'], 1)

    def test_shared_missing_to_background_created_and_no_write(self):
        result = self.preview('auto', record('', 'missing'), '',
                              record('background.org\n'))
        self.assertEqual(result['content'], 'background.org\n')
        self.assertEqual(result['result'], 'preview_only')
        self.assertFalse(result['would_change_current'])
        self.assertFalse(result['commit_authorized'])

    def test_uninitialized_known_and_missing_known_are_not_empty(self):
        for source in ('youtube', 'user'):
            with self.subTest(source=source):
                with self.assertRaisesRegex(EditorMergeRefused,
                                            'owned_source_not_initialized'):
                    self.preview(source,
                        {'status': 'uninitialized', 'content': '', 'revision': None},
                        '', record(''))
                with self.assertRaisesRegex(EditorMergeRefused,
                                            'invalid_snapshot_state'):
                    self.preview(source, record('', 'missing'), '', record(''))

    def test_draft_modifiers_malformed_state_and_stale_revision_fail_closed(self):
        valid = record('example.com\n')
        for bad in (dict(valid, revision='0' * 64),
                    record('zeta.org\nalpha.com\n'),
                    record('!example.com\n'),
                    dict(valid, status='empty'),
                    {'status': 'uninitialized', 'content': '', 'revision': None}):
            with self.subTest(bad=bad):
                with self.assertRaises(EditorMergeRefused):
                    self.preview('youtube', bad, '', valid)
        with self.assertRaisesRegex(EditorMergeRefused,
                                    'invalid_draft_line_1_modifiers_not_allowed'):
            self.preview('youtube', valid, '!example.org', valid)
        with self.assertRaisesRegex(EditorMergeRefused,
                                    'source_disappeared_during_edit'):
            self.preview('auto', valid, 'example.com', record('', 'missing'))

    def test_private_psl_and_idna_are_still_owned_by_canonical_policy(self):
        result = self.preview('user', record(''),
                              'video.user.github.io\nвидео.пример.рф', record(''))
        self.assertEqual(result['content'],
                         'user.github.io\nxn--e1afmkfd.xn--p1ai\n')
        with self.assertRaises(EditorMergeRefused):
            self.preview('user', record(''), 'example.unknownsuffix', record(''))

    def test_no_implicit_write_or_cross_list_authorization(self):
        p = self.preview('auto', record(''), '', record(''))
        self.assertFalse(p['commit_authorized'])
        self.assertFalse(p['cross_source_validated'])
        self.assertEqual(p['content'], '')
        self.assertFalse(p['would_change_current'])


if __name__ == '__main__':
    unittest.main()
