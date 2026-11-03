#!/usr/bin/env python3
"""Stage 2.23: bounded read-only cold revalidation under authentic old FD9.

Disposable OPNsense 26.7 KVM only. No authorized or actual package replacement.
This does NOT define or implement a protected firmware/Web/pkg entrypoint.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
LOCK = Path('/var/run/zapret2-lifecycle.lock')
OPTIN = 'ZAPRET2_STAGE2_LOCKED_COLD_REVALIDATION'
NAME = 'os-zapret2-restyle'
# Shell acquires ORIGINAL FD9 once, then execs the READ-ONLY Python witness.
# Do not invoke historical service Status while holding the original lock.
LOCKED = ('set -eu; exec 9>"$1"; /usr/bin/lockf -s -t 0 9; '
          'exec /usr/local/bin/python3 "$2" --locked "$3"')
BUSY_HOLDER = ('set -eu; exec 9>"$1"; /usr/bin/lockf -s -t 1 9; '
               'printf "HELD\n" > "$2"; /bin/sleep 8')
CHALLENGER = 'exec 9>"$1"; /usr/bin/lockf -s -t 0 9'

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

def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def qualify():
    need(os.geteuid() == 0 and os.uname().sysname == 'FreeBSD'
         and os.uname().machine == 'amd64' and
         os.environ.get('GITHUB_ACTIONS') == 'true' and
         os.environ.get(OPTIN) == '1', 'DISPOSABLE_NATIVE_CI_OPTIN_REQUIRED')

def check_lock_identity(path, actual, held):
    need(path == LOCK and not path.is_symlink(), 'HISTORICAL_FD9_PATH_UNTRUSTED')
    need(stat.S_ISREG(actual.st_mode) and actual.st_uid == 0
         and actual.st_nlink == 1, 'HISTORICAL_FD9_INODE_UNTRUSTED')
    need(stat.S_ISREG(held.st_mode) and held.st_dev == actual.st_dev
         and held.st_ino == actual.st_ino,
         'INHERITED_FD9_NOT_HISTORICAL_INODE')
    return True

def check_fd9():
    need(LOCK.is_file() and not LOCK.is_symlink(), 'ORIGINAL_FD9_MISSING')
    try:
        held = os.fstat(9)
    except OSError:
        raise Refusal('INHERITED_FD9_NOT_OPEN') from None
    check_lock_identity(LOCK, LOCK.lstat(), held)
    p = subprocess.run(['/bin/sh', '-c', CHALLENGER, 'sh', str(LOCK)],
                       capture_output=True, text=True, timeout=6, check=False)
    need(p.returncode == 75, 'INDEPENDENT_FD9_NOT_BUSY:' + str(p.returncode))

def qualified_cold(prov, guard, process_result, ipfw, ipdivert, rules):
    need(prov.get('status') == 'PASS_READ_ONLY_PROVENANCE'
         and prov.get('package') == NAME + '-0.6.2_1',
         'GENUINE_INSTALLED_PREDECESSOR_UNVERIFIED')
    guard.check_no_owners((guard.JOURNAL, *guard.MARKERS,
                           *guard.PIDFILES, guard.PENDING_EXTRA))
    need(process_result.returncode == 0, 'PROCESS_CENSUS_FAILED')
    guard.check_process_census(process_result.stdout)
    need(guard.check_kernel_cold(ipfw.returncode, ipdivert.returncode,
                                 rules.returncode, rules.stdout + rules.stderr)
         == 'UNLOADED_COLD_ENOPROTOOPT', 'NATIVE_KERNEL_NOT_COLD')
    return 'COLD_READ_ONLY_REVALIDATED_UNDER_ORIGINAL_FD9'

def inside_lock(archive):
    qualify()
    check_fd9()
    old = load('stage0-installed-predecessor-readonly.py')
    guard = load('stage0-opnsense-prepkg-readonly.py')
    host = old.run('hostname', '-s').decode().strip()
    prov = old.run_guest(archive, host)
    before = (old.run('pkg', 'info', '-R', '--raw-format', 'json', NAME),
              digest(old.SERVICE), digest('/conf/config.xml'))
    observation = qualified_cold(
        prov, guard, guard.command(['/bin/ps', '-ax', '-o', 'command=']),
        guard.command(['/sbin/kldstat', '-q', '-m', 'ipfw']),
        guard.command(['/sbin/kldstat', '-q', '-m', 'ipdivert']),
        guard.command(['/sbin/ipfw', '-q', 'list']))
    after = (old.run('pkg', 'info', '-R', '--raw-format', 'json', NAME),
             digest(old.SERVICE), digest('/conf/config.xml'))
    need(before == after, 'PKGDB_SERVICE_OR_CONFIG_CHANGED_WITHIN_LOCK')
    return {'status': 'PASS_LOCKED_COLD_READ_ONLY_DIAGNOSTIC',
            'observed': observation, 'independent_original_fd9_exclusive': True,
            'old_pkgdb_service_config_unchanged': True,
            'old_status_called_under_fd9': False,
            'native_pkg_mutation_invoked': False,
            'pre_pkg_admission_implemented': False,
            'stock_firmware_route_protected': False,
            'lh08_ac11_accepted': False}

def call_locked(archive):
    return subprocess.run(['/bin/sh', '-c', LOCKED, 'sh', str(LOCK),
                           str(Path(__file__).resolve()), str(archive)],
                          capture_output=True, text=True, timeout=40, check=False)

def classify(result, case):
    if case == 'cold':
        need(result.returncode == 0, 'COLD_LOCKED_PROBE_REFUSED:' +
             result.stderr.strip()[:200])
        lines = [x for x in result.stdout.splitlines()
                 if x.startswith('STAGE2_LOCKED_COLD=')]
        need(len(lines) == 1, 'NO_SINGLE_COLD_WITNESS')
        value = json.loads(lines[0].split('=', 1)[1])
        need(value['status'] == 'PASS_LOCKED_COLD_READ_ONLY_DIAGNOSTIC'
             and value['old_pkgdb_service_config_unchanged'] is True
             and value['independent_original_fd9_exclusive'] is True
             and value['old_status_called_under_fd9'] is False
             and value['native_pkg_mutation_invoked'] is False
             and value['pre_pkg_admission_implemented'] is False
             and value['lh08_ac11_accepted'] is False, 'UNSAFE_COLD_REPORT')
        return value
    if case == 'busy':
        need(result.returncode == 75 and not result.stdout.strip(),
             'BUSY_FD9_ENTERED_READ_ONLY_HELPER')
        return 'BUSY_ORIGINAL_FD9_DENIED_BEFORE_HELPER'
    if case == 'journal':
        need(result.returncode == 2 and
             'STAGE2_LOCKED_COLD=REFUSED:UNVERIFIED_JOURNAL_MARKER_OR_PIDFILE:'
             in result.stderr and not result.stdout.strip(),
             'UNKNOWN_OWNER_NOT_REFUSED_UNDER_FD9')
        return 'UNKNOWN_JOURNAL_DENIED_UNDER_ORIGINAL_FD9'
    raise Refusal('UNRECOGNIZED_PROBE_CASE')

def assert_unchanged(old, guard, archive, before):
    current = (old.run('pkg', 'info', '-R', '--raw-format', 'json', NAME),
               digest(old.SERVICE), digest('/conf/config.xml'),
               tuple((x.exists(), x.is_symlink()) for x in guard.MARKERS))
    need(current == before, 'ORIGINAL_PACKAGE_OR_CONFIG_CHANGED')
    host = old.run('hostname', '-s').decode().strip()
    need(old.run_guest(archive, host)['status'] == 'PASS_READ_ONLY_PROVENANCE',
         'ORIGINAL_INSTALLED_PROVENANCE_CHANGED')

def busy_negative(archive, prior):
    with tempfile.TemporaryDirectory(prefix='stage2-busy-fd9-') as folder:
        marker = Path(folder) / 'held'
        proc = None
        try:
            proc = subprocess.Popen(['/bin/sh', '-c', BUSY_HOLDER, 'sh',
                                     str(LOCK), str(marker)],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, start_new_session=True)
            prior.wait_held(marker, proc)
            observed = classify(call_locked(archive), 'busy')
        finally:
            if proc is not None and proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.communicate(timeout=8)
    return observed

def execute(archive):
    qualify()
    guest = load('stage0-opnsense-guest-readonly.py')
    guest.evaluate(guest.observe())
    old = load('stage0-installed-predecessor-readonly.py')
    installer = load('stage0-opnsense-installed-predecessor.py')
    guard = load('stage0-opnsense-prepkg-readonly.py')
    unknown = load('stage0-opnsense-old-unknown-owner.py')
    prior = load('stage2-opnsense-real-old-fd9-nonrecursive.py')
    need(installer.install_and_verify(archive)['status'] ==
         'PASS_OPNSENSE_26_7_REAL_PREDECESSOR_INSTALLED_PROVENANCE',
         'GENUINE_OLD_INSTALL_FAILED')
    need(guard.snapshot(archive)['status'] == 'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY',
         'ORIGINAL_COLD_STATUS_UNVERIFIED')
    prior.check_lock_path(LOCK)
    before = (old.run('pkg', 'info', '-R', '--raw-format', 'json', NAME),
              digest(old.SERVICE), digest('/conf/config.xml'),
              tuple((x.exists(), x.is_symlink()) for x in guard.MARKERS))
    cold = classify(call_locked(archive), 'cold')
    assert_unchanged(old, guard, archive, before)
    busy = busy_negative(archive, prior)
    assert_unchanged(old, guard, archive, before)
    created_parent = False
    created_journal = False
    try:
        created_parent = unknown.create_disposable_root_if_absent()
        created_journal = unknown.create_owned_corrupt_journal()
        negative = classify(call_locked(archive), 'journal')
        unknown.verify_corrupt_journal()
        assert_unchanged(old, guard, archive, before)
    finally:
        if created_journal:
            unknown.remove_only_owned_journal()
        if created_parent:
            need(guard.JOURNAL.parent.is_dir()
                 and not guard.JOURNAL.parent.is_symlink()
                 and stat.S_IMODE(guard.JOURNAL.parent.stat().st_mode) == 0o700,
                 'DISPOSABLE_JOURNAL_ROOT_CHANGED')
            guard.JOURNAL.parent.rmdir()
    assert_unchanged(old, guard, archive, before)
    need(guard.snapshot(archive)['status'] == 'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY',
         'ORIGINAL_COLD_STATE_NOT_RESTORED')
    return {'schema': 1, 'status': 'PASS_PREPKG_FD9_COLD_REVALIDATION_DIAGNOSTIC_ONLY',
            'cold': cold, 'busy_negative': busy, 'unknown_negative': negative,
            'original_archive_sha256': old.ARCHIVE_SHA,
            'original_package_unchanged': True, 'real_native_pkg_replacement': False,
            'service_status_under_held_fd9': False, 'admission_to_pkg_interval_proved': False,
            'supported_firmware_web_entrypoint_implemented': False,
            'lh08_ac11_accepted': False, 'owner_appliance_modified': False}

def main():
    if len(sys.argv) != 3:
        print('STAGE2_LOCKED_COLD=REFUSED:MODE_AND_ARCHIVE_REQUIRED', file=sys.stderr)
        return 2
    try:
        if sys.argv[1] == '--locked':
            result = inside_lock(Path(sys.argv[2]))
        elif sys.argv[1] == '--execute':
            result = execute(Path(sys.argv[2]))
        else:
            raise Refusal('UNKNOWN_MODE')
        print('STAGE2_LOCKED_COLD=' + json.dumps(result, sort_keys=True))
        return 0
    except (Refusal, OSError, ValueError, KeyError, TypeError,
            subprocess.SubprocessError) as exc:
        print('STAGE2_LOCKED_COLD=REFUSED:' + str(exc), file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(main())
