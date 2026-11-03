#!/usr/bin/env python3
"""Finite authentic installed old Status syscall trace under original FD9.

Diagnostic on disposable OPNsense 26.7 only. NO native pkg replacement, stock
firmware alteration, production hook rewrite or supported updater. The already
measured _79 real held-FD9 pkg hazard is NOT rerun by this experiment.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
LOCK = Path('/var/run/zapret2-lifecycle.lock')
OPTIN = 'ZAPRET2_STAGE2_ORIGINAL_FD9_SYSCALL_TRACE'
TRACE_EXEC = Path('/usr/bin/truss')
HOLDER = ('set -eu; exec 9>"$1"; /usr/bin/lockf -s -t 0 9; '
          'printf "HELD\n" > "$2"; '
          'exec /usr/bin/truss -f -o "$3" "$4" status')
CHALLENGER = 'exec 9>"$1"; /usr/bin/lockf -s -t 0 9'
MAX_TRACE_BYTES = 4 * 1024 * 1024
PREFIX = 'STAGE2_OLD_FD9_TRACE='


class Refusal(Exception):
    pass


def need(ok, why):
    if not ok:
        raise Refusal(why)


def load(name):
    spec = importlib.util.spec_from_file_location(
        name.replace('-', '_').replace('.', '_'), HERE / name)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def qualify():
    need(os.geteuid() == 0 and os.uname().sysname == 'FreeBSD'
         and os.uname().machine == 'amd64'
         and os.environ.get('GITHUB_ACTIONS') == 'true'
         and os.environ.get(OPTIN) == '1',
         'DISPOSABLE_NATIVE_SYSCALL_TRACE_OPTIN_REQUIRED')
    need(TRACE_EXEC.is_file() and not TRACE_EXEC.is_symlink()
         and os.access(TRACE_EXEC, os.X_OK),
         'NATIVE_TRUSS_NOT_QUALIFIED')


def challenge(lock):
    p = subprocess.run(['/bin/sh', '-c', CHALLENGER, 'sh', str(lock)],
                       capture_output=True, text=True, timeout=6, check=False)
    need(p.returncode == 75, 'INDEPENDENT_FD9_CHALLENGER_NOT_BUSY:' +
         str(p.returncode))


def summarize_trace(path):
    need(path.is_file() and not path.is_symlink(),
         'NATIVE_TRACE_FILE_MISSING')
    data = path.read_bytes()
    need(0 < len(data) <= MAX_TRACE_BYTES, 'NATIVE_TRACE_EMPTY_OR_OVERSIZED')
    # Do not expose raw syscall trace: it can contain real filenames/arguments.
    text = data.decode('utf-8', 'replace')
    return {
        'trace_sha256': hashlib.sha256(data).hexdigest(),
        'trace_bytes': len(data),
        'old_lock_path_observed': str(LOCK) in text,
        'historical_lockf_exec_observed': bool(re.search(
            r'execve\([^)]*(?:/usr/bin/lockf|/lockf")', text)),
        'flock_syscall_recorded': bool(re.search(r'\bflock\(', text)),
        'fcntl_syscall_recorded': bool(re.search(r'\bfcntl\(', text))
    }


def observe_lock_wait():
    p = subprocess.run(['/bin/ps', '-ax', '-o',
                        'pid=,ppid=,stat=,wchan=,command='],
                       capture_output=True, text=True, timeout=6, check=False)
    need(p.returncode == 0, 'NATIVE_LOCK_PROCESS_CENSUS_FAILED')
    rows = [r.strip() for r in p.stdout.splitlines()
            if re.search(r'(?<![A-Za-z])lockf(?:\s|$)', r)
            and '/usr/bin/truss' not in r]
    # Never report full command lines, arguments or PIDs from the guest.
    return {
        'lockf_processes_observed': len(rows),
        'sleeping_lockf_wchan_visible': any(
            bool(re.search(r'\b(?:flock|lockf|lockmgr|lck|fdesc)\b', r,
                           re.IGNORECASE)) for r in rows)
    }


def trace_case(service, held, prior):
    with tempfile.TemporaryDirectory(prefix='stage2-original-fd9-trace-') as d:
        folder = Path(d)
        trace = folder / 'trace.txt'
        marker = folder / 'held'
        if held:
            argv = ['/bin/sh', '-c', HOLDER, 'sh',
                    str(LOCK), str(marker), str(trace), str(service)]
        else:
            argv = [str(TRACE_EXEC), '-f', '-o', str(trace),
                    str(service), 'status']
        proc = None
        timed_out = False
        output = ('', '')
        wait = {'lockf_processes_observed': 0,
                'sleeping_lockf_wchan_visible': False}
        contended = False
        try:
            proc = subprocess.Popen(
                argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, start_new_session=True)
            if held:
                prior.wait_held(marker, proc)
                challenge(LOCK)
                contended = True
            try:
                output = proc.communicate(timeout=7)
            except subprocess.TimeoutExpired:
                timed_out = True
                if held:
                    wait = observe_lock_wait()
        finally:
            if proc is not None and proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)
                output = proc.communicate(timeout=8)
        need(proc is not None, 'NATIVE_TRACE_PROCESS_NOT_STARTED')
        trace_info = summarize_trace(trace)
        return {
            'held': held,
            'bounded_timeout': timed_out,
            'exit': None if timed_out else proc.returncode,
            'independent_fd9_exclusive': contended,
            'reported_original_cold_status': (
                'zapret is not running' in (output[0] + output[1])),
            'syscalls': trace_info,
            'wait': wait,
        }


def classify(control, held):
    need(control['held'] is False and
         control['bounded_timeout'] is False and
         # FreeBSD truss returned 0 in real native control although the
         # authentic child printed STOPPED and standalone old Status was 1.
         # Never infer service exit solely from the tracer's exit code.
         control['exit'] in (0, 1) and
         control['reported_original_cold_status'] is True,
         'ORIGINAL_CONTROL_STATUS_WITH_TRUSS_NOT_COLD')
    need(held['held'] is True and held['independent_fd9_exclusive'] is True,
         'HELD_ORIGINAL_FD9_NOT_INDEPENDENTLY_PROVEN')
    need(control['syscalls']['historical_lockf_exec_observed'] is True,
         'CONTROL_LOCKF_EXEC_NOT_OBSERVED')
    need(held['syscalls']['historical_lockf_exec_observed'] is True,
         'HELD_LOCKF_EXEC_NOT_OBSERVED')
    if held['bounded_timeout']:
        return 'OBSERVED_ORIGINAL_STATUS_NESTED_LOCKF_NOT_FINISHED_WITH_HELD_FD9'
    need(held['exit'] is not None, 'HELD_STATUS_MISSING_EXIT')
    return 'OBSERVED_ORIGINAL_STATUS_COMPLETED_WITH_HELD_FD9_NOT_AUTHORIZED'


def execute(archive):
    qualify()
    guest = load('stage0-opnsense-guest-readonly.py')
    installer = load('stage0-opnsense-installed-predecessor.py')
    old = load('stage0-installed-predecessor-readonly.py')
    guard = load('stage0-opnsense-prepkg-readonly.py')
    managed = load('stage2-managed-prepkg-veto-witness.py')
    prior = load('stage2-opnsense-real-old-fd9-nonrecursive.py')
    need(guest.evaluate(guest.observe())['status'] ==
         'PASS_ISOLATED_OPNSENSE_26_7_GUEST_IDENTITY',
         'NOT_ONE_USE_OPNSENSE_GUEST')
    need(installer.install_and_verify(archive)['status'] ==
         'PASS_OPNSENSE_26_7_REAL_PREDECESSOR_INSTALLED_PROVENANCE',
         'GENUINE_OLD_PACKAGE_NOT_INSTALLED')
    need(guard.snapshot(archive)['status'] ==
         'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY',
         'HISTORICAL_COLD_STATUS_NOT_VERIFIED')
    prior.check_lock_path(LOCK)
    service = Path(old.SERVICE)
    before = managed.owner_snapshot(old, guard, archive)
    control = trace_case(service, False, prior)
    # On a native failure, disclose only bounded structural evidence, never
    # raw truss lines, Config contents, system filenames or process argv.
    print(PREFIX + 'CONTROL_DIAGNOSTIC=' + json.dumps({
        'exit': control['exit'],
        'bounded_timeout': control['bounded_timeout'],
        'reported_original_cold_status': control['reported_original_cold_status'],
        'historical_lockf_exec_observed': control['syscalls']['historical_lockf_exec_observed'],
        'flock_syscall_recorded': control['syscalls']['flock_syscall_recorded'],
        'trace_bytes': control['syscalls']['trace_bytes'],
    }, sort_keys=True), flush=True)
    need(managed.owner_snapshot(old, guard, archive) == before,
         'CONTROL_TRACE_CHANGED_OLD_OR_CONFIG_OR_IPFW')
    historical = trace_case(service, True, prior)
    after = managed.owner_snapshot(old, guard, archive)
    need(after == before, 'HELD_TRACE_CHANGED_OLD_OR_CONFIG_OR_IPFW')
    need(guard.snapshot(archive)['status'] ==
         'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY',
         'ORIGINAL_COLD_STATE_NOT_RESTORED')
    classification = classify(control, historical)
    return {
        'schema': 1,
        'status': 'PASS_ORIGINAL_OLD_FD9_SYSCALL_TRACE_DIAGNOSTIC_ONLY',
        'classification': classification,
        'control': control,
        'original_fd9_held': historical,
        'real_installed_old_archive_sha256': old.ARCHIVE_SHA,
        'before_after_pkgdb_all_file_modes_config_process_ipfw_identical': True,
        'real_mutating_pkg_attempted': False,
        'stock_firmware_web_route_protected': False,
        'production_hook_change': False,
        'safe_managed_pkg_handshake_proven': False,
        'lh08_ac11_accepted': False,
        'owner_appliance_modified': False,
    }


def main():
    if len(sys.argv) != 2:
        print(PREFIX + 'REFUSED:OLD_ARCHIVE_REQUIRED', file=sys.stderr)
        return 2
    try:
        print(PREFIX + json.dumps(execute(Path(sys.argv[1])),
                                  sort_keys=True), flush=True)
        return 0
    except (Refusal, OSError, subprocess.SubprocessError, KeyError,
            ValueError, TypeError) as exc:
        print(PREFIX + 'REFUSED:' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
