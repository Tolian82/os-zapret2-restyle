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


from auto_detect_five_editor_plan import FiveEditorPlanRefused, preview_five_sources


class FiveEditorPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.psl = PublicSuffixList.load()

    def plan(self, *, manual=None, baseline=None, draft=None, current=None,
             exclude=''):
        base = {'youtube': record(''), 'user': record(''), 'auto': record('', 'missing')}
        current_base = dict(base)
        drafts_base = {'youtube': '', 'user': '', 'auto': ''}
        return preview_five_sources(base | (baseline or {}),
                                    drafts_base | (draft or {}),
                                    current_base | (current or {}),
                                    {'youtube': '', 'user': ''} | (manual or {}),
                                    exclude, psl=self.psl)

    def test_manual_known_and_shared_fallback_coverage(self):
        value = self.plan(manual={'youtube': 'example.com'},
            draft={'youtube': 'example.com\nexample.org',
                   'user': 'another.net', 'auto': 'example.com\nexample.org\nanother.net'},
            current={'auto': record('', 'missing')})
        self.assertEqual(value['sources']['youtube']['content'], 'example.org\n')
        self.assertEqual(value['sources']['user']['content'], 'another.net\n')
        self.assertEqual(value['sources']['auto']['content'], '')
        self.assertEqual(value['sources']['youtube']['coverage_removals']['manual_covered'], 1)
        self.assertEqual(value['sources']['auto']['coverage_removals']['known_covered'], 3)
        self.assertFalse(value['commit_authorized'])
        self.assertTrue(value['cross_source_validated'])
        self.assertTrue(value['manual_untouched'])

    def test_owner_variant_a_deleted_domain_background_discovery_survives(self):
        result = self.plan(baseline={'youtube': record('example.com\n')},
                           current={'youtube': record('example.com\nexample.org\n')},
                           draft={'youtube': ''})
        self.assertEqual(result['sources']['youtube']['content'], 'example.org\n')
        self.assertEqual(result['sources']['youtube']['user_removed'], 1)
        self.assertTrue(result['sources']['youtube']['rebased'])

    def test_manual_negative_from_other_profile_vetoes_auto(self):
        result = self.plan(manual={'user': '!example.com\n!^video.exact.net'},
            draft={'youtube': 'example.com\nother.org\nexact.net',
                   'auto': 'example.com\nexact.net'},
            current={'auto': record('', 'missing')})
        self.assertEqual(result['sources']['youtube']['content'], 'exact.net\nother.org\n')
        self.assertEqual(result['sources']['auto']['content'], '')

    def test_exact_positive_only_covers_matching_root(self):
        result = self.plan(manual={'youtube': '^video.example.com\n^exact.net'},
            draft={'youtube': 'example.com\nexact.net'})
        self.assertEqual(result['sources']['youtube']['content'], 'example.com\n')

    def test_global_exclude_and_private_suffix(self):
        result = self.plan(exclude='user.github.io\nexample.org',
            draft={'youtube': 'video.user.github.io\nvideo.example.org\nextra.net'})
        self.assertEqual(result['sources']['youtube']['content'], 'extra.net\n')

    def test_conflicting_known_provenance_requires_original_p1_attribution(self):
        with self.assertRaisesRegex(FiveEditorPlanRefused,
                                    'ambiguous_known_source_provenance'):
            self.plan(draft={'youtube': 'example.org', 'user': 'example.org'})

    def test_uninitialized_known_and_bad_revision_fail_closed(self):
        with self.assertRaisesRegex(FiveEditorPlanRefused,
                                    'owned_source_not_initialized'):
            self.plan(baseline={'youtube': {'status': 'uninitialized',
                                           'revision': None, 'content': ''}})
        with self.assertRaisesRegex(FiveEditorPlanRefused,
                                    'revision_content_mismatch'):
            self.plan(current={'user': dict(record('example.org\n'), revision='0'*64)})

    def test_forbidden_modifiers_and_conflicting_manual_fail_closed(self):
        with self.assertRaisesRegex(FiveEditorPlanRefused, 'invalid_draft_line'):
            self.plan(draft={'auto': '!example.com'})
        with self.assertRaisesRegex(FiveEditorPlanRefused,
                                    'invalid_manual_or_exclusion'):
            self.plan(manual={'youtube': '!example.com\n^example.com'})

    def test_no_unverified_source_or_parser_fallback(self):
        with self.assertRaisesRegex(FiveEditorPlanRefused, 'incomplete_five_source_input'):
            preview_five_sources({}, {}, {}, {}, psl=self.psl)
        with self.assertRaises(FiveEditorPlanRefused):
            self.plan(draft={'auto': 'example.unknownsuffix'})


if __name__ == '__main__':
    unittest.main()
