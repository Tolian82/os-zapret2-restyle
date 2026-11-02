#!/usr/bin/env python3
"""Read-only provenance witness for the current OPNsense configd watcher/worker.

Never sends signals, reloads services, changes hooks or authorizes a future
signal: PID and start time can still race after this observation. Intended for
an explicitly disposable, independently attested OPNsense CI guest only.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

PID_FILE = Path('/var/run/configd.pid')
SERVICE = '/usr/local/opnsense/service/configd.py'
WORKER_PATTERN = 'configd.py console'
STAMP = re.compile(r'^\s*(\d+)\s+(\d+)\s+([A-Za-z]{3}\s+[A-Za-z]{3}\s+\d{1,2}\s+\d\d:\d\d:\d\d\s+\d{4})\s+(\S.*)$')


class Refusal(RuntimeError):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def run(*args):
    try:
        return subprocess.run(args, capture_output=True, text=True,
                              timeout=12, check=False)
    except (OSError, subprocess.SubprocessError):
        raise Refusal('READONLY_PROCESS_PROBE_UNAVAILABLE') from None


def read_pid(path=PID_FILE):
    need(path.is_file() and not path.is_symlink(), 'CONFIGD_PID_FILE_UNTRUSTED')
    need(path.stat().st_size <= 16, 'CONFIGD_PID_FILE_OVERSIZED')
    data = path.read_text(encoding='ascii').strip()
    need(data.isascii() and data.isdecimal() and 1 < int(data) < 100000000,
         'CONFIGD_WATCHER_PID_INVALID')
    return int(data)


def process(pid):
    res = run('/bin/ps', '-ww', '-p', str(pid), '-o', 'pid=', '-o',
              'ppid=', '-o', 'lstart=', '-o', 'command=')
    need(res.returncode == 0, 'CONFIGD_PS_PROBE_FAILED')
    rows = [line for line in res.stdout.splitlines() if line.strip()]
    need(len(rows) == 1, 'CONFIGD_PROCESS_AMBIGUOUS')
    m = STAMP.fullmatch(rows[0])
    need(m is not None and int(m.group(1)) == pid,
         'CONFIGD_PROCESS_IDENTITY_INVALID')
    return {'pid': pid, 'ppid': int(m.group(2)), 'birth': m.group(3),
            'command': m.group(4)}


def workers(parent):
    res = run('/usr/bin/pgrep', '-P', str(parent), '-f', WORKER_PATTERN)
    need(res.returncode == 0, 'CONFIGD_WORKER_NOT_FOUND')
    lines = [x.strip() for x in res.stdout.splitlines() if x.strip()]
    need(len(lines) == 1 and lines[0].isascii() and
         lines[0].isdecimal() and int(lines[0]) > 1,
         'CONFIGD_WORKER_AMBIGUOUS')
    return int(lines[0])


def snapshot(path=PID_FILE):
    parent = read_pid(path)
    watcher = process(parent)
    need(watcher['ppid'] != parent and SERVICE in watcher['command'] and
         not watcher['command'].rstrip().endswith(' console'),
         'CONFIGD_WATCHER_NOT_OWNED')
    worker_pid = workers(parent)
    need(worker_pid != parent, 'CONFIGD_WORKER_IS_WATCHER')
    worker = process(worker_pid)
    need(worker['ppid'] == parent, 'CONFIGD_WORKER_PARENT_MISMATCH')
    need(SERVICE in worker['command'], 'CONFIGD_WORKER_COMMAND_PATH_MISMATCH')
    need(re.search(r'(?<!\S)' + re.escape(SERVICE) +
                   r'\s+console(?=\s|$)', worker['command']) is not None,
         'CONFIGD_WORKER_CONSOLE_ROLE_MISMATCH')
    return {'watcher': watcher, 'worker': worker}


def verify(path=PID_FILE):
    need(os.environ.get('GITHUB_ACTIONS') == 'true' and
         os.environ.get('ZAPRET2_STAGE2_READONLY_CONFIGD_CI') == '1',
         'DISPOSABLE_CI_OPTIN_REQUIRED')
    before = snapshot(path)
    status = run('/usr/local/sbin/configctl', 'system', 'status')
    need(status.returncode == 0, 'CONFIGD_SYSTEM_STATUS_NOT_READY')
    after = snapshot(path)
    need(before == after, 'CONFIGD_PID_REUSE_OR_WORKER_ROTATION_OBSERVED')
    return {'schema': 1, 'status': 'PASS_READONLY_CONFIGD_WORKER_IDENTITY',
            'watcher_pid': before['watcher']['pid'],
            'worker_pid': before['worker']['pid'],
            'watcher_birth': before['watcher']['birth'],
            'worker_birth': before['worker']['birth'],
            'direct_child': True, 'system_status_ready': True,
            'signals_sent': False, 'actions_reloaded': False,
            'restart_authorized': False, 'pid_reuse_excluded_after_observation': False,
            'owner_appliance_modified': False, 'package_hooks_executed': False}


def main():
    try:
        report = verify()
    except (Refusal, OSError, UnicodeError, ValueError) as exc:
        print('STAGE2_CONFIGD_IDENTITY=REFUSED:' + str(exc), file=sys.stderr)
        return 2
    print('STAGE2_CONFIGD_IDENTITY=' + json.dumps(report, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
