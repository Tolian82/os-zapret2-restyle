#!/usr/bin/env python3
"""Stage 2.23 disposable managed pre-pkg gate witness; NEVER a pkg updater.

One real original FD9 is held through a non-mutating native pkg query on the
qualified cold path. Rejected cases MUST exit before that native pkg query.
This test-only CLI does not enter destructive pkg, edit hooks, or protect the
stock firmware/Web paths. LH-08/AC-11 remain BLOCKED.
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
NAME = 'os-zapret2-restyle'
OPTIN = 'ZAPRET2_STAGE2_MANAGED_PREPKG_WITNESS'
LOCKED = ('set -eu; exec 9>"$1"; /usr/bin/lockf -s -t 0 9; '
          'exec /usr/local/bin/python3 "$2" --inner "$3"')
PREFIX = 'STAGE2_MANAGED_PREPKG='


class Refusal(Exception):
    pass


def need(value, reason):
    if not value:
        raise Refusal(reason)


def load(filename):
    name = filename.replace('-', '_').replace('.', '_')
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def qualify():
    need(os.geteuid() == 0 and os.uname().sysname == 'FreeBSD'
         and os.uname().machine == 'amd64'
         and os.environ.get('GITHUB_ACTIONS') == 'true'
         and os.environ.get(OPTIN) == '1'
         and os.environ.get('ZAPRET2_STAGE2_LOCKED_COLD_REVALIDATION') == '1',
         'DISPOSABLE_NATIVE_MANAGED_OPTIN_REQUIRED')


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def installed_files(old):
    """Hash every actual pkgdb-listed installed path, not only the service."""
    raw = old.run('pkg', 'info', '-lq', NAME).decode('utf-8')
    paths = [Path(line.strip()) for line in raw.splitlines() if line.strip()]
    need(paths and all(p.is_absolute() for p in paths)
         and len(paths) == len(set(paths))
         and Path(old.SERVICE) in paths, 'INSTALLED_FILE_LIST_UNQUALIFIED')
    entries = []
    for p in paths:
        st = p.lstat()
        kind = stat.S_IFMT(st.st_mode)
        mode = stat.S_IMODE(st.st_mode)
        if stat.S_ISREG(st.st_mode):
            identity = digest(p.read_bytes())
        elif stat.S_ISLNK(st.st_mode):
            identity = os.readlink(p)
        elif stat.S_ISDIR(st.st_mode):
            identity = 'directory'
        else:
            raise Refusal('INSTALLED_FILE_TYPE_UNQUALIFIED:' + str(p))
        entries.append((str(p), kind, mode, st.st_uid, st.st_gid, identity))
    return tuple(sorted(entries))


def owner_snapshot(old, guard, archive):
    host = old.run('hostname', '-s').decode().strip()
    provenance = old.run_guest(archive, host)
    need(provenance.get('status') == 'PASS_READ_ONLY_PROVENANCE',
         'PUBLISHED_PREDECESSOR_PROVENANCE_FAILED')
    processes = guard.command(['/bin/ps', '-ax', '-o', 'command='])
    need(processes.returncode == 0, 'PROCESS_CENSUS_UNAVAILABLE')
    owned = tuple(sorted(line for line in processes.stdout.splitlines()
                         if any(token in line for token in guard.PROCESS_TOKENS)))
    kernel = guard.command(['/sbin/ipfw', '-q', 'list'])
    # A cold FreeBSD kernel returns ENOPROTOOPT; a loaded kernel returns rules.
    need(kernel.returncode in (0, 71), 'IPFW_SNAPSHOT_UNQUALIFIED')
    return {
        'pkgdb': digest(old.run('pkg', 'info', '-R', '--raw-format', 'json', NAME)),
        'installed_files': installed_files(old),
        'config': digest(Path('/conf/config.xml').read_bytes()),
        'markers': tuple((str(p), p.exists(), p.is_symlink())
                         for p in (guard.JOURNAL, *guard.MARKERS,
                                   *guard.PIDFILES, guard.PENDING_EXTRA)),
        'owned_processes': owned,
        'ipfw': (kernel.returncode, kernel.stdout, kernel.stderr),
        'ipfw_modules': tuple(guard.command(['/sbin/kldstat', '-q', '-m', name]).returncode
                              for name in ('ipfw', 'ipdivert')),
        'service_sha256': provenance['service_sha256'],
        'four_original_hooks_sha256': provenance['original_hooks_sha256']
    }


def run_inner(archive):
    qualify()
    locked = load('stage2-prepkg-locked-cold-revalidation.py')
    locked.check_fd9()
    # The existing validated _81 cold predicate does NOT invoke the original
    # Status inside its inherited FD9 (the historical old Status may deadlock).
    try:
        cold = locked.inside_lock(archive)
    except locked.Refusal as exc:
        # Genuine installed-old refusal must exit deterministically as rc=2,
        # never become a traceback or accidentally continue to native pkg.
        raise Refusal(str(exc)) from None
    need(cold['status'] == 'PASS_LOCKED_COLD_READ_ONLY_DIAGNOSTIC'
         and cold['lh08_ac11_accepted'] is False
         and cold['native_pkg_mutation_invoked'] is False,
         'COLD_GATE_UNQUALIFIED')
    locked.check_fd9()
    # Only a real native *read-only* pkg query after the gate. No mutating pkg
    # operation is reachable in this script, even for the eligible cold case.
    p = subprocess.run(['/usr/sbin/pkg', '-o', 'REPO_AUTOUPDATE=false',
                        'query', '%n|%v', NAME],
                       capture_output=True, text=True, timeout=20, check=False)
    need(p.returncode == 0 and p.stdout.strip() == NAME + '|0.6.2_1',
         'NATIVE_PKG_READ_ONLY_QUERY_FAILED')
    locked.check_fd9()
    return {'schema': 1,
            'status': 'PASS_TEST_ONLY_MANAGED_COLD_QUERY_UNDER_ORIGINAL_FD9',
            'native_pkg_read_only_query_after_gate': True,
            'original_fd9_continuous_through_query': True,
            'old_status_called_under_fd9': False,
            'native_pkg_mutation_invoked': False,
            'supported_firmware_web_entrypoint_protected': False,
            'pre_pkg_admission_implemented': False,
            'lh08_ac11_accepted': False}


def locked_attempt(archive):
    locked = load('stage2-prepkg-locked-cold-revalidation.py')
    return subprocess.run(['/bin/sh', '-c', LOCKED, 'sh', str(locked.LOCK),
                           str(Path(__file__).resolve()), str(archive)],
                          capture_output=True, text=True, timeout=65, check=False)


def classify(p, case):
    if case == 'cold':
        need(p.returncode == 0, 'COLD_MANAGED_QUERY_REFUSED:' + p.stderr[:160])
        lines = [x for x in p.stdout.splitlines() if x.startswith(PREFIX)]
        need(len(lines) == 1, 'NO_SINGLE_COLD_RESULT')
        report = json.loads(lines[0][len(PREFIX):])
        need(report.get('status') == 'PASS_TEST_ONLY_MANAGED_COLD_QUERY_UNDER_ORIGINAL_FD9'
             and report.get('native_pkg_read_only_query_after_gate') is True
             and report.get('original_fd9_continuous_through_query') is True
             and report.get('native_pkg_mutation_invoked') is False
             and report.get('pre_pkg_admission_implemented') is False
             and report.get('lh08_ac11_accepted') is False,
             'FALSE_SAFE_MANAGED_WITNESS')
        return report
    if case == 'busy':
        need(p.returncode == 75 and not p.stdout.strip(),
             'BUSY_FD9_DID_NOT_REFUSE_BEFORE_MANAGED_ENTRY')
        return 'BUSY_ORIGINAL_FD9_REFUSED_BEFORE_MANAGED_ENTRY'
    if case in ('orphan', 'journal'):
        expected = ('KERNEL_IPFW_OR_IPDIVERT_LOADED_OR_UNQUALIFIED'
                    if case == 'orphan' else 'UNVERIFIED_JOURNAL_MARKER_OR_PIDFILE:')
        need(p.returncode == 2 and not p.stdout.strip()
             and PREFIX + 'REFUSED:' + expected in p.stderr,
             'UNSAFE_OWNER_NOT_REFUSED_BEFORE_NATIVE_PKG_QUERY:' + case +
             ':rc=' + str(p.returncode) + ':' + repr(p.stderr[:200]))
        return 'REFUSED_' + case.upper() + '_BEFORE_NATIVE_PKG_QUERY'
    raise Refusal('UNKNOWN_MANAGED_CASE')


def busy_test(archive, locked, prior):
    with tempfile.TemporaryDirectory(prefix='stage2-managed-busy-') as folder:
        marker = Path(folder) / 'held'
        proc = None
        try:
            proc = subprocess.Popen(
                ['/bin/sh', '-c', locked.BUSY_HOLDER, 'sh',
                 str(locked.LOCK), str(marker)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                start_new_session=True)
            prior.wait_held(marker, proc)
            return classify(locked_attempt(archive), 'busy')
        finally:
            if proc is not None:
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGKILL)
                proc.communicate(timeout=8)


def execute(archive):
    qualify()
    locked = load('stage2-prepkg-locked-cold-revalidation.py')
    prior = load('stage2-opnsense-real-old-fd9-nonrecursive.py')
    installer = load('stage0-opnsense-installed-predecessor.py')
    guard = load('stage0-opnsense-prepkg-readonly.py')
    old = load('stage0-installed-predecessor-readonly.py')
    guest = load('stage0-opnsense-guest-readonly.py')
    unknown = load('stage0-opnsense-old-unknown-owner.py')
    foreign = load('stage0-opnsense-foreign-ipfw-admission.py')
    unsafe = load('stage2-opnsense-real-unsafe-owner-replacement.py')
    need(guest.evaluate(guest.observe())['status'] ==
         'PASS_ISOLATED_OPNSENSE_26_7_GUEST_IDENTITY', 'NOT_DISPOSABLE_NATIVE_GUEST')
    need(installer.install_and_verify(archive)['status'] ==
         'PASS_OPNSENSE_26_7_REAL_PREDECESSOR_INSTALLED_PROVENANCE',
         'PUBLISHED_OLD_INSTALL_FAILED')
    need(guard.snapshot(archive)['status'] == 'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY',
         'GENUINE_ORIGINAL_COLD_STATUS_UNQUALIFIED')
    prior.check_lock_path(locked.LOCK)
    cold = classify(locked_attempt(archive), 'cold')
    before = owner_snapshot(old, guard, archive)
    busy = busy_test(archive, locked, prior)
    need(owner_snapshot(old, guard, archive) == before,
         'BUSY_REFUSAL_CHANGED_OWNER_OR_PACKAGE')
    foreign.activate_kernel(guard)
    injected = False
    try:
        unsafe.add_test_orphan()
        injected = True
        status = foreign.command(str(old.SERVICE), 'status')
        need(status.returncode == 2 and unsafe.only_orphan_loopback_divert(),
             'GENUINE_ORPHAN_DID_NOT_CAUSE_STATUS_2')
        baseline = owner_snapshot(old, guard, archive)
        orphan = classify(locked_attempt(archive), 'orphan')
        need(owner_snapshot(old, guard, archive) == baseline,
             'ORPHAN_REFUSAL_MUTATED_PKG_CONFIG_PROCESS_IPFW')
        created_parent = False
        created_journal = False
        try:
            created_parent = unknown.create_disposable_root_if_absent()
            created_journal = unknown.create_owned_corrupt_journal()
            journal_before = owner_snapshot(old, guard, archive)
            journal = classify(locked_attempt(archive), 'journal')
            unknown.verify_corrupt_journal()
            need(owner_snapshot(old, guard, archive) == journal_before,
                 'JOURNAL_REFUSAL_MUTATED_PKG_CONFIG_PROCESS_IPFW')
        finally:
            if created_journal:
                unknown.remove_only_owned_journal()
            if created_parent:
                need(guard.JOURNAL.parent.is_dir() and
                     not guard.JOURNAL.parent.is_symlink() and
                     stat.S_IMODE(guard.JOURNAL.parent.stat().st_mode) == 0o700,
                     'OWNED_JOURNAL_PARENT_CHANGED')
                guard.JOURNAL.parent.rmdir()
        need(owner_snapshot(old, guard, archive) == baseline,
             'JOURNAL_FIXTURE_NOT_RESTORED')
        need(unsafe.only_orphan_loopback_divert(),
             'ORPHAN_RULE_CHANGED_DURING_MANAGED_VETO')
        print('STAGE2_MANAGED_PRE_CLEANUP=' + json.dumps({
            'old_package_unchanged': True,
            'genuine_old_status': 2,
            'orphan_before_pkg': orphan,
            'busy_before_pkg': busy,
            'unknown_journal_before_pkg': journal,
            'native_pkg_mutation_invoked': False
        }, sort_keys=True), flush=True)
    finally:
        if injected:
            unsafe.remove_test_orphan()  # exact test-owned lo0 rule only
    # ipfw and ipdivert remain loaded; this guest is discarded.
    return {'schema': 1, 'status': 'PASS_TEST_ONLY_MANAGED_PREPKG_REFUSAL_WITNESS',
            'cold': cold['status'], 'busy': busy, 'orphan': orphan,
            'unknown_journal': journal, 'genuine_old_status': 2,
            'original_archive_sha256': old.ARCHIVE_SHA,
            'real_package_file_bytes_modes_config_markers_process_ipfw_unchanged': True,
            'test_orphan_cleanup_exact': True,
            'native_pkg_mutation_invoked': False,
            'managed_product_entrypoint_installed': False,
            'stock_firmware_web_protected': False,
            'real_pkg_hook_handshake_proven': False,
            'lh08_ac11_accepted': False,
            'owner_appliance_modified': False}


def main():
    if len(sys.argv) != 3:
        print(PREFIX + 'REFUSED:MODE_AND_ARCHIVE_REQUIRED', file=sys.stderr)
        return 2
    try:
        if sys.argv[1] == '--inner':
            result = run_inner(Path(sys.argv[2]))
        elif sys.argv[1] == '--execute':
            result = execute(Path(sys.argv[2]))
        else:
            raise Refusal('UNRECOGNIZED_MODE')
        print(PREFIX + json.dumps(result, sort_keys=True))
        return 0
    except (Refusal, OSError, KeyError, ValueError, TypeError,
            subprocess.SubprocessError) as exc:
        print(PREFIX + 'REFUSED:' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
