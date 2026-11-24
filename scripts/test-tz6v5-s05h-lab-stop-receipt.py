#!/usr/bin/env python3
"""Portable S05h user-path regression: native Lab Stage20 original stop wrapper -> result.

The source code under test is extracted from the actual lifecycle function and
actual Stage20 adapter case. This is NOT native OPNsense installed acceptance.
"""
from __future__ import annotations
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LIFECYCLE = ROOT / 'src/opnsense/scripts/OPNsense/Zapret/strategy_lab/lifecycle.sh'
ADAPTER = ROOT / 'src/opnsense/scripts/OPNsense/Zapret/strategy_lab_stage_adapter.sh'


def scenario(initial: str, stop: int, status: int, language: str) -> str:
    lifecycle = LIFECYCLE.read_text()
    adapter = ADAPTER.read_text()
    # Execute exactly the extracted *original* functions and dispatch branch.
    functions = []
    for name in ('strategy_lab_verify_stopped', 'strategy_lab_stop_normal_service'):
        match = re.search(r'(?ms)^' + name + r'\(\)\n\{.*?^\}', lifecycle)
        assert match, name + ' absent'
        functions.append(match.group())
    branch = re.search(r'(?ms)^    20\)\n.*?^        ;;', adapter)
    assert branch, 'actual Stage20 adapter branch absent'
    harness = '''set -eu
STRATEGY_LAB_STOP_TIMEOUT=10
STRATEGY_LAB_STOP_FAILURE=''
strategy_lab_timed_service_action() { return "$MOCK_STOP_RC"; }
strategy_lab_service_status_code() { return "$MOCK_STATUS_RC"; }
load_lifecycle_context() { STRATEGY_LAB_INITIAL_SERVICE_STATE="$MOCK_INITIAL"; }
error() { printf 'ERROR:%s\\n' "$1"; exit 0; }
pass() { printf 'PASS:%s\\n' "$1"; exit 0; }
''' + '\n'.join(functions) + '''
case 20 in
''' + branch.group() + '''
esac
'''
    done = subprocess.run(['/bin/sh', '-c', harness], env={**os.environ,
        'MOCK_INITIAL': initial, 'MOCK_STOP_RC': str(stop),
        'MOCK_STATUS_RC': str(status), 'LANGUAGE': language},
        capture_output=True, text=True, timeout=10)
    assert done.returncode == 0, ('shell failure', done.returncode, done.stderr)
    assert not done.stderr, 'unsafe stderr emitted: ' + done.stderr
    return done.stdout.strip()


def main() -> None:
    cases = (
        ('RUNNING', 69, 0, 'en', 'stop-wrapper-rc=69'),
        ('RUNNING', 124, 0, 'en', 'stop-wrapper-rc=124'),
        ('RUNNING', 0, 0, 'en', 'status-check-rc=0'),
        ('RUNNING', 0, 2, 'en', 'status-check-rc=2'),
        ('RUNNING', 70, 0, 'ru', 'stop-wrapper-rc=70'),
        ('STOPPED', 0, 0, 'en', 'status-check-rc=0'),
        ('INCOMPLETE', 0, 1, 'en', 'could not be stopped'),
    )
    for initial, stop, status, lang, expected in cases:
        actual = scenario(initial, stop, status, lang)
        assert actual.startswith('ERROR:'), (initial, stop, status, actual)
        assert expected in actual, (initial, stop, status, expected, actual)
        assert len(actual) < 220
        assert 'timeout exceeded' not in actual.lower(), 'rc124 is not proof of timeout'
    for initial, lang in [('RUNNING', 'en'), ('STOPPED', 'ru')]:
        ok = scenario(initial, 0, 1, lang)
        assert ok.startswith('PASS:'), (initial, ok)
        assert 'stop-wrapper-rc=' not in ok and 'status-check-rc=' not in ok
    print('S05H_ORIGINAL_STAGE20_STOP_RESULT=PASS')


if __name__ == '__main__':
    main()
