#!/usr/bin/env python3
"""Offline positive, negative, concurrency and notification contracts for PR watchdog."""
from datetime import datetime, timezone
import contextlib
import io
import json
import os
import urllib.error
from unittest.mock import patch
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


class GitHubPaginationRegressionTests(unittest.TestCase):
    """Reproduce trusted-main scheduled watchdog crash from #41856709938."""

    def api(self, callback):
        api = w.Api('synthetic-unit-token', 'Owner/repo')
        api.call = callback
        return api

    def test_jobs_dict_envelope_for_real_run_id(self):
        requested = []
        def call(path):
            requested.append(path)
            return {'total_count': 2, 'jobs': [
                {'id': 126680021235, 'status': 'completed', 'conclusion': 'success'},
                {'id': 126680021503, 'status': 'in_progress', 'conclusion': None}]}
        result = self.api(call).pages('actions/runs/41860323142/jobs')
        self.assertEqual(len(result), 2)
        self.assertEqual(requested, [
            'actions/runs/41860323142/jobs?per_page=100&page=1'])

    def test_workflow_runs_dict_and_direct_lists_still_accepted(self):
        api = self.api(lambda path: (
            {'total_count': 1, 'workflow_runs': [{'id': 13}]}
            if path.startswith('actions/runs?') else [{'number': 42}]))
        self.assertEqual(api.pages('actions/runs?event=pull_request&head_sha=' + SHA),
                         [{'id': 13}])
        self.assertEqual(api.pages('pulls?state=open&base=main'), [{'number': 42}])
        self.assertEqual(api.pages('pulls/42/files'), [{'number': 42}])
        self.assertEqual(api.pages('issues/42/comments'), [{'number': 42}])

    def test_jobs_two_pages_and_total_limit(self):
        calls = []
        def multi(path):
            calls.append(path)
            return {'total_count': 101, 'jobs': [
                {'id': i} for i in (range(100) if path.endswith('&page=1') else [100])]}
        self.assertEqual(len(self.api(multi).pages('actions/runs/13/jobs')), 101)
        self.assertEqual(len(calls), 2)
        with self.assertRaisesRegex(RuntimeError, 'GITHUB_PAGINATION_LIMIT_REACHED'):
            self.api(lambda _: {'jobs': [{'id': 1}] * 100}).pages(
                'actions/runs/13/jobs')

    def test_jobs_malformed_responses_refused_before_any_ready(self):
        for response in (
                {'workflow_runs': [{'id': 1}]}, {'message': 'denied'},
                [], {'jobs': 'not-an-array'}, {'jobs': [False]},
                {'jobs': [{'id': 1}, 'not-a-job']}):
            with self.subTest(response=response):
                with self.assertRaisesRegex(ValueError,
                                            'PAGINATED_GITHUB_RESULT_UNEXPECTED'):
                    self.api(lambda _: response).pages('actions/runs/13/jobs')

    def test_unsupported_endpoint_never_reaches_network(self):
        def forbidden(_):
            raise AssertionError('Unexpected API request')
        for path in ('actions/runs/0/jobs', 'issues/42', 'actions/runs/13/logs'):
            with self.subTest(path=path), self.assertRaisesRegex(
                    ValueError, 'UNSUPPORTED_PAGINATED_GITHUB_ENDPOINT'):
                self.api(forbidden).pages(path)

    def test_all_steps_success_but_job_and_run_in_progress_not_ready(self):
        api = self.api(lambda _: {'total_count': 1, 'jobs': [{
            'id': 126681291809, 'status': 'in_progress', 'conclusion': None,
            'started_at': '2026-11-03T10:55:00Z',
            'steps': [{'name': 'Complete job', 'status': 'completed',
                       'conclusion': 'success',
                       'completed_at': '2026-11-03T11:01:00Z'}]}]})
        old = make_run(status='in_progress', conclusion=None,
                       rid=13, at='2026-11-03T10:55:00Z')
        last = w.newest_job_progress(api, old)
        self.assertEqual(last, '2026-11-03T11:01:00Z')
        state, _ = w.classify(make_pr(), ['CI'], [old], NOW, {13: last})
        self.assertEqual(state, 'CHECK_STALLED')
        self.assertNotEqual(state, 'READY_FOR_OWNER_REVIEW')

    def test_failed_job_envelope_adds_details_and_posts_open_pr_comment(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            yml = root / '.github/workflows'
            yml.mkdir(parents=True)
            (yml / 'ci.yml').write_text('name: CI\non:\n  pull_request:\n')
            pr = make_pr()
            alerts = []
            paths = []
            fail = make_run(conclusion='failure', rid=13)
            def fake(path, payload=None, method=None):
                paths.append(path)
                if path.startswith('pulls?'):
                    return [pr]
                if path == 'pulls/42':
                    return pr
                if path.startswith('pulls/42/files?'):
                    return [{'filename': 'Makefile'}]
                if path.startswith('actions/runs?'):
                    return {'total_count': 1, 'workflow_runs': [fail]}
                if path.startswith('actions/runs/13/jobs?'):
                    return {'total_count': 1, 'jobs': [{
                        'conclusion': 'failure',
                        'html_url': 'https://github.com/Owner/repo/actions/jobs/13',
                        'steps': [{'name': 'exact CI failure', 'conclusion': 'failure'}]}]}
                if path.startswith('issues/42/comments?'):
                    return []
                if path == 'issues/42/comments' and method == 'POST':
                    alerts.append(payload['body'])
                    return {'id': 1}
                raise AssertionError(path)
            api = self.api(fake)
            w.run_once(api, root)
            self.assertEqual(len(alerts), 1)
            self.assertIn('CHECK_FAILED', alerts[0])
            self.assertIn('exact CI failure', alerts[0])
            self.assertNotIn('READY_FOR_OWNER_REVIEW', alerts[0])
            self.assertTrue(any('/jobs?' in path for path in paths))


class SecurityTests(unittest.TestCase):
    def test_no_pr_code_execution_or_merge(self):
        text = Path(w.__file__).read_text()
        for forbidden in ('subprocess.', 'os.system(', 'eval(', 'exec(', 'actions/checkout@', '/merge'):
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



class DeliveryFallbackTests(unittest.TestCase):
    def test_github_403_permission_denial_is_classified_without_echoing_secrets(self):
        error = urllib.error.HTTPError(
            'https://api.github.com/hidden', 403, 'Forbidden',
            {'X-Accepted-GitHub-Permissions':
             'issues=write; pull_requests=write',
             'X-GitHub-Request-Id': '1C8:AB:421:88'},
            io.BytesIO(json.dumps({
                'message': 'Resource not accessible by integration',
                'sensitive': 'NEVER_PRINT_ME'
            }).encode()))
        message = w.classify_http_error(error)
        self.assertIn('GITHUB_API_REFUSAL_403_INTEGRATION_ACCESS_DENIED', message)
        self.assertIn('accepted_issues_write_pull_requests_write', message)
        self.assertIn('request_id_1C8:AB:421:88', message)
        self.assertNotIn('NEVER_PRINT_ME', message)
        self.assertEqual(
            w.delivery_error_label(RuntimeError(message)),
            'GITHUB_API_REFUSAL_403_INTEGRATION_ACCESS_DENIED')

    def test_secondary_and_primary_rate_limits_are_distinguished(self):
        for body, headers, expected in (
            ({'message': 'You have exceeded a secondary rate limit'},
             {'Retry-After': '40'}, 'SECONDARY_RATE_LIMIT'),
            ({'message': 'API rate limit exceeded'},
             {'X-RateLimit-Remaining': '0'}, 'PRIMARY_RATE_LIMIT'),
            ({'message': 'Other refusal, private SECRET'}, {},
             'AUTHORIZATION_OR_POLICY'),
        ):
            with self.subTest(expected=expected):
                err = urllib.error.HTTPError(
                    'https://api.github.com/hidden', 403, 'Forbidden',
                    headers, io.BytesIO(json.dumps(body).encode()))
                status = w.classify_http_error(err)
                self.assertIn(expected, status)
                self.assertNotIn('SECRET', status)

    def test_action_summary_is_bounded_and_no_pr_content_can_be_injected(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'summary.md'
            with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': str(output)}):
                w.step_summary('Owner/repo', 42, SHA, 'READY_FOR_OWNER_REVIEW',
                               'GITHUB_API_REFUSAL_403_INTEGRATION_ACCESS_DENIED')
                content = output.read_text()
                self.assertIn('https://github.com/Owner/repo/pull/42', content)
                self.assertIn('READY_FOR_OWNER_REVIEW', content)
                self.assertIn('GITHUB_API_REFUSAL_403', content)
                with self.assertRaisesRegex(ValueError,
                                            'UNTRUSTED_WATCHDOG_SUMMARY_FIELDS'):
                    w.step_summary('Owner/repo', 42, SHA,
                                   'READY_FOR_OWNER_REVIEW',
                                   'PRIVATE\nTRICK')
                self.assertEqual(content, output.read_text())

    def test_post_403_keeps_green_pr_visible_and_fails_the_job(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            policies = path / '.github/workflows'
            policies.mkdir(parents=True)
            (policies / 'ci.yml').write_text(
                'name: CI\non:\n  pull_request:\n')
            summary = path / 'summary.md'
            pr = make_pr()
            pr['title'] = 'ATTACKER\nINJECTED_TOKEN_SECRET'
            class Stub:
                repo = 'Owner/repo'
                def pages(self, location):
                    if location.startswith('pulls?'):
                        return [pr]
                    if location.endswith('/files'):
                        return [{'filename': 'Makefile'}]
                    if location.startswith('actions/runs?'):
                        return [make_run()]
                    if location.endswith('/comments'):
                        return []
                    raise AssertionError(location)
                def call(self, location, payload=None, method=None):
                    if location == 'pulls/42':
                        return pr
                    if location == 'issues/42/comments' and method == 'POST':
                        raise RuntimeError(
                            'GITHUB_API_REFUSAL_403_INTEGRATION_ACCESS_DENIED')
                    raise AssertionError(location)
            with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': str(summary)}):
                # A simulated 403 must not create a real Actions ::error.
                with contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaisesRegex(
                            RuntimeError, 'GITHUB_API_REFUSAL_403_INTEGRATION_ACCESS_DENIED'):
                        w.run_once(Stub(), path)
            data = summary.read_text()
            self.assertIn('READY_FOR_OWNER_REVIEW', data)
            self.assertIn('GITHUB_API_REFUSAL_403', data)
            self.assertIn('https://github.com/Owner/repo/pull/42', data)
            self.assertNotIn('ATTACKER', data)
            self.assertNotIn('INJECTED_TOKEN_SECRET', data)

    def test_one_time_original_merged_pr_smoke_posts_exactly_once(self):
        with tempfile.TemporaryDirectory() as folder:
            summary = Path(folder) / 'summary.md'
            comments = []
            calls = []
            class Stub:
                repo = 'Owner/repo'
                def pages(self, location):
                    self_assert.assertEqual(location, 'issues/857/comments')
                    return [{'body': body} for body in comments]
                def call(self, location, payload=None, method=None):
                    calls.append((location, method))
                    if location == 'pulls/857':
                        return {'state': 'closed', 'merged': True,
                                'head': {'sha': SHA}}
                    if location == 'issues/857/comments' and method == 'POST':
                        comments.append(payload['body'])
                        return {'id': 975}
                    raise AssertionError(location)
            self_assert = self
            with patch.dict(os.environ, {
                    'GITHUB_EVENT_NAME': 'push',
                    'GITHUB_REF': 'refs/heads/main',
                    'GITHUB_STEP_SUMMARY': str(summary)}):
                w.smoke_original_pr_delivery(Stub())
                w.smoke_original_pr_delivery(Stub())
            self.assertEqual(len(comments), 1)
            self.assertIn(w.DELIVERY_SMOKE_MARKER, comments[0])
            self.assertEqual(
                sum(path == 'issues/857/comments' and method == 'POST'
                    for path, method in calls), 1)
            self.assertIn('COMMENT_POSTED', summary.read_text())
            self.assertIn('ALREADY_NOTIFIED', summary.read_text())

    def test_smoke_write_denied_reports_403_without_untrusted_content(self):
        with tempfile.TemporaryDirectory() as folder:
            summary = Path(folder) / 'summary.md'
            class Stub:
                repo = 'Owner/repo'
                def pages(self, location):
                    return []
                def call(self, location, payload=None, method=None):
                    if location == 'pulls/857':
                        return {'state': 'closed', 'merged': True,
                                'head': {'sha': SHA}}
                    if location == 'issues/857/comments' and method == 'POST':
                        raise RuntimeError(
                            'GITHUB_API_REFUSAL_403_INTEGRATION_ACCESS_DENIED')
                    raise AssertionError(location)
            with patch.dict(os.environ, {
                    'GITHUB_EVENT_NAME': 'push',
                    'GITHUB_REF': 'refs/heads/main',
                    'GITHUB_STEP_SUMMARY': str(summary)}):
                # The mocked denial is an expected negative, not a CI error.
                with contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaisesRegex(
                            RuntimeError, 'GITHUB_API_REFUSAL_403_INTEGRATION_ACCESS_DENIED'):
                        w.smoke_original_pr_delivery(Stub())
            self.assertIn('DELIVERY_SMOKE', summary.read_text())
            self.assertIn('GITHUB_API_REFUSAL_403', summary.read_text())

    def test_smoke_never_writes_on_pull_request_or_schedule(self):
        class NoApi:
            repo = 'Owner/repo'
            def pages(self, location):
                raise AssertionError(location)
            def call(self, location, payload=None, method=None):
                raise AssertionError(location)
        for event in ('pull_request', 'workflow_run', 'schedule'):
            with self.subTest(event=event),patch.dict(
                    os.environ, {'GITHUB_EVENT_NAME': event,
                                 'GITHUB_REF': 'refs/heads/main'}):
                w.smoke_original_pr_delivery(NoApi())

    def test_debounced_workflow_still_has_reliable_periodic_fallback(self):
        text = (Path(w.__file__).resolve().parents[1] /
                '.github/workflows/pr-completion-watchdog.yml').read_text()
        self.assertEqual(text.count("      - 'CI'"), 1)
        self.assertEqual(text.count('    workflows:'), 1)
        self.assertIn("cron: '7,17,27,37,47,57 * * * *'", text)
        self.assertIn('  pull-requests: write', text)
        self.assertIn('  issues: write', text)
        self.assertIn('ref: ${{ github.event.repository.default_branch }}', text)
        self.assertNotIn('ref: ${{ github.event.pull_request.head.sha }}', text)


if __name__ == '__main__':
    unittest.main()
