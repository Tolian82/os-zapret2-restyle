#!/usr/bin/env python3
"""Fail-closed changed-path routing: user journey first, full matrix by risk.

Only exact UI/list-policy sources are exempt from unrelated legacy matrices.
Original FD9, Config, shared argv and OPNsense Model code remain critical.
Unexpected sources default to full qualification rather than silent skipping.
"""
from __future__ import annotations

import argparse
import sys

PREFIX = 'src/opnsense/'
FORM = PREFIX + 'mvc/app/'
API = FORM + 'controllers/OPNsense/Zapret/Api/'
VIEWS = FORM + 'views/OPNsense/Zapret/'
BACKEND = PREFIX + 'scripts/OPNsense/Zapret/backend/'

FLOW_ONLY = frozenset({
    VIEWS + 'general.volt', VIEWS + 'voice.volt',
    VIEWS + 'diagnostics.volt',
    FORM + 'controllers/OPNsense/Zapret/forms/general.xml',
    FORM + 'controllers/OPNsense/Zapret/forms/voice.xml',
    API + 'DomainSetPolicyBridge.php',
    API + 'IPSetPolicyBridge.php',
    BACKEND + 'domain_policy.py', BACKEND + 'ipset_policy.py',
})

CRITICAL_FLOW = frozenset({
    FORM + 'models/OPNsense/Zapret/Zapret.xml',
    API + 'SettingsController.php',
    API + 'SharedApplyEnvelope.php',
    PREFIX + 'scripts/OPNsense/Zapret/shared_apply_request.php',
    PREFIX + 'scripts/OPNsense/Zapret/apply_settings.php',
    PREFIX + 'scripts/OPNsense/Zapret/zapret_service.sh',
})

META_PATHS = frozenset({
    'README.md', 'AGENTS.md',
    'scripts/ci_owner_journey_scope.py',
    'scripts/test-github-workflow-budget.py',
})


def metadata(path: str) -> bool:
    return (path in META_PATHS or path.startswith('docs/')
            or path.startswith('.github/workflows/'))


def classify(paths: list[str], force_full: bool = False) -> dict[str, bool]:
    if force_full:
        return {'owner_flow': True, 'full_matrix': True, 'voice_scope': True}
    owner_flow = False
    full_matrix = False
    voice_scope = False
    for path in paths:
        if metadata(path):
            continue
        if path in FLOW_ONLY:
            owner_flow = True
            continue
        if path in CRITICAL_FLOW:
            owner_flow = True
            full_matrix = True
            voice_scope = True
            continue
        # New or unknown source is NOT implicitly approved as UI-only.
        full_matrix = True
        if path.startswith('src/'):
            voice_scope = True
        if path.startswith('src/') or path.startswith('scripts/'):
            owner_flow = True
    return {'owner_flow': owner_flow, 'full_matrix': full_matrix,
            'voice_scope': voice_scope}


def self_test() -> None:
    for path in ('docs/verification/owner-p6-readonly-probe.py',
                 '.github/workflows/ci.yml',
                 'scripts/ci_owner_journey_scope.py'):
        assert classify([path]) == dict(owner_flow=False, full_matrix=False,
                                        voice_scope=False), path
    for path in FLOW_ONLY:
        assert classify([path]) == dict(owner_flow=True, full_matrix=False,
                                        voice_scope=False), path
    for path in CRITICAL_FLOW:
        assert classify([path]) == dict(owner_flow=True, full_matrix=True,
                                        voice_scope=True), path
    assert classify(['src/opnsense/scripts/OPNsense/Zapret/unknown.so']) == dict(
        owner_flow=True, full_matrix=True, voice_scope=True)
    assert classify(['scripts/unknown-contract.py']) == dict(
        owner_flow=True, full_matrix=True, voice_scope=False)
    assert classify(['docs/readme.md', VIEWS + 'general.volt']) == dict(
        owner_flow=True, full_matrix=False, voice_scope=False)
    assert classify([], force_full=True) == dict(owner_flow=True,
                                                 full_matrix=True, voice_scope=True)
    print('CI_OWNER_JOURNEY_SCOPE_SELF_TEST=PASS')


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--full', action='store_true')
    args = parser.parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    paths = [line for line in sys.stdin.read().splitlines() if line]
    for name, enabled in classify(paths, args.full).items():
        print(f'{name}={str(enabled).lower()}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
