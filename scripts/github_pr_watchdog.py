#!/usr/bin/env python3
"""Trusted-main notification-only PR watchdog; no PR checkout or merge endpoints."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import re
import urllib.error
import urllib.request

MARKER = '<!-- zapret2-pr-completion-watchdog-v1 -->'
ACTIONABLE = frozenset({'CHECK_FAILED', 'CHECK_STALLED', 'STALE_BASE', 'READY_FOR_OWNER_REVIEW'})
BASE = Path(__file__).resolve().parents[1]
TIMEOUT_SECONDS = 30 * 60


def dt(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')) if value else None


def match_path(pattern, filename):
    """Restricted GitHub glob: * stays inside directories, ** crosses them."""
    if any(x in pattern for x in ('{', '}', '[', ']', '\\')):
        raise ValueError('UNSUPPORTED_GITHUB_PATH_GLOB')
    out, i = '', 0
    while i < len(pattern):
        if pattern[i:i+3] == '**/':
            out += '(?:.*/)?'
            i += 3
        elif pattern[i:i+2] == '**':
            out += '.*'
            i += 2
        elif pattern[i] == '*':
            out += '[^/]*'
            i += 1
        elif pattern[i] == '?':
            out += '[^/]'
            i += 1
        else:
            out += re.escape(pattern[i])
            i += 1
    return re.fullmatch(out, filename) is not None


def yaml_items(lines, key):
    """Read supported workflow trigger lists; ambiguous syntax fails closed."""
    selected = [i for i, line in enumerate(lines)
                if re.fullmatch(r'    ' + re.escape(key) + r':\s*(.*)', line)]
    if not selected:
        return None
    if len(selected) != 1:
        raise ValueError('DUPLICATE_WORKFLOW_POLICY_FIELD:' + key)
    index = selected[0]
    raw = lines[index].split(':', 1)[1].strip()
    def clean(x):
        return x.strip().strip('"').strip("'")
    if raw.startswith('[') and raw.endswith(']'):
        return [clean(x) for x in raw[1:-1].split(',') if x.strip()]
    if raw:
        raise ValueError('UNSUPPORTED_WORKFLOW_POLICY_FIELD:' + key)
    result = []
    for line in lines[index+1:]:
        if line and not line.startswith(' ' * 6):
            break
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if not line.startswith('      - '):
            raise ValueError('UNSUPPORTED_WORKFLOW_POLICY_LIST:' + key)
        result.append(clean(line[8:].split(' #', 1)[0]))
    return result


def workflow_policy(source):
    lines = source.splitlines()
    names = [x[6:].strip() for x in lines if x.startswith('name: ')]
    if len(names) != 1 or not names[0]:
        raise ValueError('WORKFLOW_NAME_INVALID')
    ons = [i for i, x in enumerate(lines) if x == 'on:']
    if len(ons) != 1:
        raise ValueError('UNSUPPORTED_WORKFLOW_ON_SYNTAX:' + names[0])
    start = ons[0] + 1
    end = next((i for i in range(start, len(lines))
                if lines[i] and not lines[i].startswith(' ')), len(lines))
    events = lines[start:end]
    pr = [i for i, x in enumerate(events) if x.startswith('  pull_request:')]
    if not pr:
        return None
    if len(pr) != 1 or not re.fullmatch(r'  pull_request:\s*', events[pr[0]]):
        raise ValueError('UNSUPPORTED_PR_TRIGGER:' + names[0])
    start = pr[0] + 1
    end = next((i for i in range(start, len(events))
                if events[i].startswith('  ') and not events[i].startswith('    ')
                and events[i].strip()), len(events))
    fields = events[start:end]
    types = yaml_items(fields, 'types')
    if types is not None and not set(types).intersection(
            {'opened', 'synchronize', 'reopened', 'ready_for_review', 'edited'}):
        return None
    branches = yaml_items(fields, 'branches')
    ignored_branches = yaml_items(fields, 'branches-ignore')
    if branches is not None and 'main' not in branches:
        raise ValueError('UNQUALIFIED_PR_BASE_BRANCH_GLOB:' + names[0])
    if ignored_branches is not None and 'main' in ignored_branches:
        return None
    paths = yaml_items(fields, 'paths')
    ignored = yaml_items(fields, 'paths-ignore')
    if paths is not None and ignored is not None:
        raise ValueError('CONFLICTING_PATH_FILTERS:' + names[0])
    return {'name': names[0], 'paths': paths, 'ignore': ignored}


def applies(policy, files):
    if policy['paths'] is not None:
        for filename in files:
            match = False
            for pattern in policy['paths']:
                negative = pattern.startswith('!')
                if match_path(pattern[1:] if negative else pattern, filename):
                    match = not negative
            if match:
                return True
        return False
    if policy['ignore'] is not None:
        return any(not any(match_path(x, f) for x in policy['ignore']) for f in files)
    return True


def expected_workflows(root, files):
    names = []
    for path in sorted((root / '.github/workflows').glob('*.yml')):
        policy = workflow_policy(path.read_text(encoding='utf-8'))
        if policy and applies(policy, files):
            names.append(policy['name'])
    if not names or len(names) != len(set(names)) or 'CI' not in names:
        raise ValueError('REQUIRED_CI_SET_MISSING_OR_AMBIGUOUS')
    return sorted(names)


def choose_runs(expected, runs, sha):
    current = {}
    for run in runs:
        if run.get('event') != 'pull_request' or run.get('head_sha') != sha:
            continue
        name = run.get('name')
        if name not in expected:
            continue
        prev = current.get(name)
        key = (run.get('run_started_at') or run.get('created_at') or '',
               run.get('run_attempt', 1), run.get('id', 0))
        if not prev or key > prev[0]:
            current[name] = (key, run)
    return {name: x[1] for name, x in current.items()}


def classify(pr, expected, runs, now=None, job_progress=None):
    now = now or datetime.now(timezone.utc)
    if pr.get('mergeable') is False or pr.get('mergeable_state') in ('dirty', 'behind'):
        return 'STALE_BASE', ['GitHub reports a merge conflict or stale base']
    latest = choose_runs(expected, runs, pr['head']['sha'])
    missing = sorted(set(expected) - set(latest))
    failed = [(name, run) for name, run in latest.items()
              if run.get('status') == 'completed' and run.get('conclusion') != 'success']
    if failed:
        return 'CHECK_FAILED', [name + ': ' + str(run.get('conclusion') or 'unknown') +
                                ' (' + run.get('html_url', 'run URL missing') + ')'
                                for name, run in sorted(failed)]
    if missing:
        start = dt(pr.get('updated_at') or pr.get('created_at')) or now
        state = 'CHECK_STALLED' if (now - start).total_seconds() > TIMEOUT_SECONDS else 'CI_IN_PROGRESS'
        return state, ['Missing current-head checks: ' + ', '.join(missing)]
    active = [(name, run) for name, run in latest.items() if run.get('status') != 'completed']
    if active:
        stalled = []
        for name, run in active:
            progress = (job_progress or {}).get(run['id'])
            start = dt(progress or run.get('run_started_at') or run.get('created_at'))
            if start and (now - start).total_seconds() > TIMEOUT_SECONDS:
                stalled.append(name)
        if stalled:
            return 'CHECK_STALLED', ['No recent job/step progress: ' + ', '.join(sorted(stalled))]
        return 'CI_IN_PROGRESS', ['Current-head CI running: ' + ', '.join(sorted(x[0] for x in active))]
    if pr.get('draft'):
        return 'CI_IN_PROGRESS', ['All checks passed but PR remains Draft']
    if pr.get('mergeable') is not True:
        return 'CI_IN_PROGRESS', ['All checks passed; GitHub mergeability not yet confirmed']
    return 'READY_FOR_OWNER_REVIEW', ['All ' + str(len(expected)) + ' applicable current-head workflows passed']


def alert_body(pr, state, details):
    sha = pr['head']['sha']
    tick = chr(96)
    safe = '\n'.join('- ' + re.sub(r'[\r\n<>]', ' ', s)[:250] for s in details[:6])
    return (MARKER + '\n**PR watchdog** — ' + tick + state + tick +
            ' on exact head ' + tick + sha + tick + '.\n\n' + safe +
            '\n\nAlert only. No PR was repaired or merged. Owner review, '
            'current main revision, approvals and safety gates remain required.')


def already_notified(comments, sha, state):
    needle = '**PR watchdog** — ' + chr(96) + state + chr(96) + ' on exact head ' + chr(96) + sha + chr(96) + '.'
    return any(MARKER in (x.get('body') or '') and needle in (x.get('body') or '')
               for x in comments)


class Api:
    def __init__(self, token, repo):
        if not token or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
            raise ValueError('GITHUB_WATCHDOG_AUTHORITY_UNAVAILABLE')
        self.token, self.repo = token, repo

    def call(self, path, payload=None, method=None):
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            'https://api.github.com/repos/' + self.repo + '/' + path,
            data=data, method=method, headers={
                'Authorization': 'Bearer ' + self.token,
                'Accept': 'application/vnd.github+json',
                'Content-Type': 'application/json',
                'X-GitHub-Api-Version': '2022-11-28',
                'User-Agent': 'zapret2-pr-completion-watchdog'})
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            raise RuntimeError('GITHUB_API_REFUSAL_' + str(exc.code)) from None

    def pages(self, path):
        output = []
        for page in range(1, 11):
            delim = '&' if '?' in path else '?'
            result = self.call(path + delim + 'per_page=100&page=' + str(page))
            if isinstance(result, dict) and 'workflow_runs' in result:
                result = result['workflow_runs']
            if not isinstance(result, list):
                raise ValueError('PAGINATED_GITHUB_RESULT_UNEXPECTED')
            output.extend(result)
            if len(result) < 100:
                return output
        raise RuntimeError('GITHUB_PAGINATION_LIMIT_REACHED')


def newest_job_progress(api, run):
    try:
        jobs = api.pages('actions/runs/' + str(run['id']) + '/jobs')
    except RuntimeError:
        return run.get('run_started_at') or run.get('created_at')
    timestamps = []
    for job in jobs:
        for item in [job] + list(job.get('steps') or []):
            for attr in ('started_at', 'completed_at'):
                if item.get(attr):
                    timestamps.append(item[attr])
    return max(timestamps, default=run.get('run_started_at') or run.get('created_at'))


def run_once(api, root=BASE):
    scanned = alerts = 0
    for pr in api.pages('pulls?state=open&base=main'):
        if pr.get('base', {}).get('ref') != 'main' or pr.get('head', {}).get('repo', {}).get('full_name') != api.repo:
            continue
        number = pr['number']
        pr = api.call('pulls/' + str(number))
        if pr.get('state') != 'open' or pr.get('head', {}).get('repo', {}).get('full_name') != api.repo:
            continue
        scanned += 1
        files = [f['filename'] for f in api.pages('pulls/' + str(number) + '/files')]
        selected = {}
        try:
            expected = expected_workflows(root, files)
        except ValueError as exc:
            state, details = 'CHECK_FAILED', ['Workflow policy could not be verified: ' + str(exc)]
        else:
            sha = pr['head']['sha']
            runs = api.pages('actions/runs?event=pull_request&head_sha=' + sha)
            selected = choose_runs(expected, runs, sha)
            progress = {}
            for entry in selected.values():
                start = dt(entry.get('run_started_at') or entry.get('created_at'))
                if entry.get('status') != 'completed' and start and (
                        datetime.now(timezone.utc) - start).total_seconds() > TIMEOUT_SECONDS:
                    progress[entry['id']] = newest_job_progress(api, entry)
            state, details = classify(pr, expected, runs, job_progress=progress)
        print('PR #' + str(number) + ': ' + state, flush=True)
        if state not in ACTIONABLE:
            continue
        if state == 'CHECK_FAILED' and selected:
            job_details = []
            for name, run in sorted(selected.items()):
                if run.get('status') != 'completed' or run.get('conclusion') == 'success':
                    continue
                try:
                    jobs = [j for j in api.pages('actions/runs/' + str(run['id']) + '/jobs')
                            if j.get('conclusion') not in (None, 'success', 'skipped')]
                except RuntimeError:
                    jobs = []
                for job in jobs[:2]:
                    step = next((x.get('name') for x in job.get('steps') or []
                                 if x.get('conclusion') == 'failure'), 'failed or cancelled job')
                    job_details.append(name + ': ' + str(step) + ' (' + str(job.get('html_url', 'job URL missing')) + ')')
            details = job_details + details
        comments = api.pages('issues/' + str(number) + '/comments')
        if already_notified(comments, pr['head']['sha'], state):
            continue
        refreshed = api.call('pulls/' + str(number))
        if refreshed.get('state') != 'open' or refreshed.get('head', {}).get('sha') != pr['head']['sha']:
            continue
        api.call('issues/' + str(number) + '/comments',
                 {'body': alert_body(pr, state, details)}, method='POST')
        alerts += 1
    print(json.dumps({'schema': 1, 'open_managed_prs': scanned,
                      'alerts_posted': alerts, 'mode': 'notifications-only'}, sort_keys=True))


if __name__ == '__main__':
    run_once(Api(os.environ.get('GH_TOKEN'), os.environ.get('GH_REPOSITORY', '')))
