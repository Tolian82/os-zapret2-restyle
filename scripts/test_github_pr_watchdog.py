#!/usr/bin/env python3
"""Offline positive, negative, concurrency and notification contracts for PR watchdog."""
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
import github_pr_watchdog as w

NOW = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)
SHA = 'a' * 40
OTHER = 'b' * 40


def make_pr(sha=SHA, mergeable=True, draft=False, **extra):
    p = {'number': 42, 'state': 'open', 'head': {
             'sha': sha, 'repo': {'full_name': 'Owner/repo'}},
         'base': {'ref': 'main'}, 'created_at': '2026-11-03T11:51:00Z',
         'mergeable': mergeable, 'draft': draft}
    p.update(extra)
    return p


def make_run(name='CI', conclusion='success', sha=SHA, status='completed',
             rid=1, at='2026-11-03T11:54:00Z'):
    return {'name': name, 'event': 'pull_request', 'head_sha': sha,
            'status': status, 'conclusion': conclusion, 'id': rid,
            'run_started_at': at, 'run_attempt': 1,
            'html_url': 'https://github.com/Owner/repo/actions/runs/' + str(rid)}


class PolicyTests(unittest.TestCase):
    def test_current_scope_path_filters_and_closed_only(self):
        w1 = w.workflow_policy('name: Scoped\non:\n  pull_request:\n    paths:\n      - src/**\n      - "!src/obsolete/**"\n')
        self.assertTrue(w.applies(w1, ['src/current/module.php']))
        self.assertFalse(w.applies(w1, ['src/obsolete/old.php']))
        self.assertFalse(w.applies(w1, ['docs/start.md']))
        self.assertTrue(w.match_path('docs/**/*.md', 'docs/a.md'))
        self.assertTrue(w.match_path('docs/**/*.md', 'docs/a/b.md'))
        self.assertFalse(w.match_path('docs/*.md', 'docs/a/b.md'))
        self.assertIsNone(w.workflow_policy('name: Closed\non:\n  pull_request:\n    types: [closed]\n'))

    def test_dynamic_workflow_count_and_duplicate_refusal(self):
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d) / '.github/workflows'
            directory.mkdir(parents=True)
            (directory/'ci.yml').write_text('name: CI\non:\n  pull_request:\n    branches: [main]\n')
            (directory/'one.yml').write_text('name: Native\non:\n  pull_request:\n    paths: [Makefile]\n')
            self.assertEqual(w.expected_workflows(Path(d), ['docs/a.md']), ['CI'])
            self.assertEqual(w.expected_workflows(Path(d), ['Makefile']), ['CI', 'Native'])
            (directory/'two.yml').write_text('name: Native\non:\n  pull_request:\n    paths: [Makefile]\n')
            with self.assertRaisesRegex(ValueError, 'AMBIGUOUS'):
                w.expected_workflows(Path(d), ['Makefile'])

    def test_unrecognized_policy_fails_closed(self):
        with self.assertRaisesRegex(ValueError, 'UNSUPPORTED'):
            w.workflow_policy('name: Invalid\non:\n  pull_request: [main]\n')
        with self.assertRaisesRegex(ValueError, 'CONFLICTING'):
            w.workflow_policy('name: Invalid\non:\n  pull_request:\n    paths: [src/**]\n    paths-ignore: [src/test/**]\n')


class CheckStateTests(unittest.TestCase):
    checks = ['CI', 'Pull request title']

    def all_green(self, sha=SHA):
        return [make_run(sha=sha), make_run(name='Pull request title', rid=2, sha=sha)]

    def test_exact_head_green_only(self):
        self.assertEqual(w.classify(make_pr(), self.checks, self.all_green(), NOW)[0],
                         'READY_FOR_OWNER_REVIEW')
        self.assertEqual(w.classify(make_pr(), self.checks, self.all_green(OTHER), NOW)[0],
                         'CI_IN_PROGRESS')

    def test_current_failure_replaces_old_success(self):
        old = make_run(rid=1, at='2026-11-03T11:50:00Z')
        bad = make_run(rid=2, conclusion='failure', at='2026-11-03T11:55:00Z')
        state, reasons = w.classify(make_pr(), ['CI'], [old, bad], NOW)
        self.assertEqual(state, 'CHECK_FAILED')
        self.assertIn('/runs/2', reasons[0])

    def test_rejects_cancelled_skipped_timed_out_and_neutral(self):
        for result in ['failure', 'cancelled', 'skipped', 'timed_out', 'neutral', 'action_required']:
            with self.subTest(result=result):
                self.assertEqual(w.classify(make_pr(), ['CI'], [make_run(conclusion=result)], NOW)[0],
                                 'CHECK_FAILED')

    def test_in_progress_missing_and_stalled(self):
        pending = make_run(status='in_progress', conclusion=None)
        self.assertEqual(w.classify(make_pr(), ['CI'], [pending], NOW)[0], 'CI_IN_PROGRESS')
        self.assertEqual(w.classify(make_pr(), ['CI'], [], NOW)[0], 'CI_IN_PROGRESS')
        old = make_run(status='in_progress', conclusion=None, at='2026-11-03T10:55:00Z')
        self.assertEqual(w.classify(make_pr(), ['CI'], [old], NOW)[0], 'CHECK_STALLED')
        self.assertEqual(w.classify(make_pr(), ['CI'], [old], NOW, {1: '2026-11-03T11:59:00Z'})[0],
                         'CI_IN_PROGRESS')
        self.assertEqual(w.classify(make_pr(updated_at='2026-11-03T10:00:00Z'), ['CI'], [], NOW)[0],
                         'CHECK_STALLED')

    def test_no_ready_on_merge_conflict_draft_or_undefined_mergeability(self):
        for p, expected in [(make_pr(mergeable=False), 'STALE_BASE'),
                            (make_pr(draft=True), 'CI_IN_PROGRESS'),
                            (make_pr(mergeable=None), 'CI_IN_PROGRESS'),
                            (make_pr(mergeable=True, mergeable_state='behind'), 'STALE_BASE')]:
            with self.subTest(expected=expected):
                self.assertEqual(w.classify(p, self.checks, self.all_green(), NOW)[0], expected)

    def test_deduplicated_per_exact_head_and_state(self):
        body = w.alert_body(make_pr(), 'READY_FOR_OWNER_REVIEW', ['All checks succeeded'])
        self.assertIn(w.MARKER, body)
        self.assertTrue(w.already_notified([{'body': body}], SHA, 'READY_FOR_OWNER_REVIEW'))
        self.assertFalse(w.already_notified([{'body': body}], OTHER, 'READY_FOR_OWNER_REVIEW'))
        self.assertFalse(w.already_notified([{'body': body}], SHA, 'CHECK_FAILED'))


class SecurityTests(unittest.TestCase):
    def test_no_pr_code_execution_or_merge(self):
        text = Path(w.__file__).read_text()
        for forbidden in ('subprocess.', 'os.system(', 'eval(', 'exec(', 'checkout', '/merge'):
            self.assertNotIn(forbidden, text)
        with self.assertRaises(ValueError):
            w.Api('', 'Owner/repo')
        with self.assertRaises(ValueError):
            w.Api('token', 'Owner/repo;bad')

    def test_no_open_prs_no_mutation(self):
        class Stub:
            repo = 'Owner/repo'
            def pages(self, path):
                self.assertEqual(path, 'pulls?state=open&base=main')
                return []
            def call(self, *args, **kwargs):
                raise AssertionError('No write expected')
        stub = Stub()
        stub.assertEqual = self.assertEqual
        w.run_once(stub)

    def test_only_same_repo_prs_and_no_repeated_notifications(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td) / '.github/workflows'
            folder.mkdir(parents=True)
            (folder/'ci.yml').write_text('name: CI\non:\n  pull_request:\n')
            owned = make_pr()
            foreign = make_pr()
            foreign['head']['repo']['full_name'] = 'Fork/repo'
            comments = []
            class Stub:
                repo = 'Owner/repo'
                def pages(self, path):
                    if path.startswith('pulls?'):
                        return [owned, foreign]
                    if path.endswith('/files'):
                        return [{'filename': 'Makefile'}]
                    if path.startswith('actions/runs?'):
                        return [make_run()]
                    if path.endswith('/comments'):
                        return [{'body': x} for x in comments]
                    raise AssertionError(path)
                def call(self, path, payload=None, method=None):
                    if path == 'pulls/42':
                        return owned
                    if path == 'issues/42/comments' and method == 'POST':
                        comments.append(payload['body'])
                        return {'id': 1}
                    raise AssertionError(path)
            a = Stub()
            w.run_once(a, Path(td))
            w.run_once(a, Path(td))
            self.assertEqual(len(comments), 1)


if __name__ == '__main__':
    unittest.main()
