#!/usr/bin/env python3
"""Disposable OPNsense Stage 0 ONLY: independent pre-pkg cold owner snapshot.

Never invokes pkg add/delete/upgrade, Stop/Start/Apply, or alters service/IPFW.
A successful *snapshot* is NOT transaction authorization: no FD9 lock is held
across a real package operation, and direct pkg commands bypass this script.
"""
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
JOURNAL = Path('/var/db/zapret2/shared-apply')
MARKERS = (Path('/var/run/zapret2-restyle/pkg-upgrade.restart'),
           Path('/var/run/zapret2-restyle/pkg-replacement.restart'))
PIDFILES = (Path('/var/run/dvtws2.pid'),
            Path('/var/run/zapret2-supervisor-daemon.pid'),
            Path('/var/run/zapret2-supervisor-monitor.pid'))
PENDING_EXTRA = Path('/var/db/zapret2-restyle/extra-resources/transaction')
STOPPED_TEXT = 'zapret is not running'
PROCESS_TOKENS = ('/dvtws2', '/supervisor_loop.sh', '/zapret_service.sh')


class Refusal(Exception):
    pass


def require(ok, reason):
    if not ok:
        raise Refusal(reason)


def load(name):
    path = HERE / name
    spec = importlib.util.spec_from_file_location(name.replace('.', '_').replace('-', '_'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_no_owners(paths):
    for path in paths:
        # lexists-like inspection; dangling symlinks are also foreign evidence.
        require(not path.exists() and not path.is_symlink(),
                'UNVERIFIED_JOURNAL_MARKER_OR_PIDFILE:' + str(path))


def check_process_census(output):
    # This deliberately errs on the side of refusing false-positive process
    # matches. It is not evidence for the RUNNING state or safe native Stop.
    require(not any(token in line for line in output.splitlines()
                    for token in PROCESS_TOKENS), 'POSSIBLE_ZAPRET_PROCESS_PRESENT')


def check_kernel_cold(kld_ipfw, kld_divert, ipfw_rc, ipfw_diagnostic):
    require(kld_ipfw == 1 and kld_divert == 1,
            'KERNEL_IPFW_OR_IPDIVERT_LOADED_OR_UNQUALIFIED')
    require(ipfw_rc == 71 and 'Protocol not available' in ipfw_diagnostic,
            'IPFW_NOT_PROVEN_UNLOADED_COLD')
    return 'UNLOADED_COLD_ENOPROTOOPT'


def command(args, timeout=25):
    try:
        return subprocess.run(args, capture_output=True, text=True,
                              check=False, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        raise Refusal('READ_ONLY_COMMAND_UNAVAILABLE_OR_TIMEOUT:' + args[0]) from None


def observed_cold(provenance, status, kld_ipfw, kld_divert, ipfw, processes,
                  journal=JOURNAL, markers=MARKERS, pidfiles=PIDFILES):
    require(provenance.get('status') == 'PASS_READ_ONLY_PROVENANCE' and
            provenance.get('package') == 'os-zapret2-restyle-0.6.2_1',
            'EXACT_PUBLISHED_PREDECESSOR_PROVENANCE_MISSING')
    check_no_owners((journal, *markers, *pidfiles, PENDING_EXTRA))
    require(status.returncode == 1 and status.stdout.strip() == STOPPED_TEXT,
            'REAL_OLD_SERVICE_NOT_PROVEN_STOPPED:' + str(status.returncode))
    check_process_census(processes)
    kernel = check_kernel_cold(kld_ipfw.returncode, kld_divert.returncode,
                               ipfw.returncode, ipfw.stdout + ipfw.stderr)
    return {'schema': 1, 'status': 'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY',
            'old_package': provenance['package'], 'real_old_status': 'STOPPED',
            'kernel': kernel, 'no_journal_or_marker_or_pidfiles': True,
            'no_matching_processes_seen': True,
            'safe_pkg_transaction_authorized': False,
            'native_successor_tested': False, 'stage0_closed': False}


def snapshot(archive, pre=None, fd9=None):
    pre = pre or load('stage0-installed-predecessor-readonly.py')
    fd9 = fd9 or load('stage0-opnsense-old-service-fd9.py')
    require(os.geteuid() == 0 and os.uname().sysname == 'FreeBSD' and
            os.uname().machine == 'amd64', 'ONLY_ROOT_DISPOSABLE_FREEBSD_AMD64')
    # Existing proven old-package verifier authenticates archive bytes,
    # four hook bodies, installed pkgdb, owner, service bytes and 0755 mode.
    hostname = pre.run('hostname', '-s').decode().strip()
    provenance = pre.run_guest(archive, hostname)
    require(provenance.get('virtual_guest_reported', '').lower() not in
            ('', 'none', 'unknown'), 'UNQUALIFIED_VIRTUAL_GUEST')
    check_no_owners((JOURNAL, *MARKERS, *PIDFILES, PENDING_EXTRA))
    # Historical service Status has its OWN lifecycle FD9 acquisition.
    # Do NOT wrap it inside a second persistent lockf or claim atomicity with
    # a later pkg command. The lock path here belongs to disposable guest.
    with tempfile.TemporaryDirectory(prefix='stage0-prepkg-cold-') as root:
        status = fd9.call_status(Path(root) / 'status-fd9.lock')
    return observed_cold(provenance, status,
                         command(['/sbin/kldstat', '-q', '-m', 'ipfw']),
                         command(['/sbin/kldstat', '-q', '-m', 'ipdivert']),
                         command(['/sbin/ipfw', '-q', 'list']),
                         checked_process_census())


def checked_process_census():
    result = command(['/bin/ps', '-ax', '-o', 'command='])
    require(result.returncode == 0, 'PROCESS_CENSUS_UNAVAILABLE')
    return result.stdout


def require_snapshot_before(operation, probe):
    """Bounded test seam: a rejected probe never invokes an operation callback.

    Do not wire a destructive pkg operation into this helper in production:
    there is no lock spanning the predicate and subsequent action.
    """
    evidence = probe()
    require(evidence.get('status') == 'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY',
            'PREPKG_COLD_EVIDENCE_NOT_ACCEPTED')
    return operation()


def prove_negative(archive):
    pre = load('stage0-installed-predecessor-readonly.py')
    fd9 = load('stage0-opnsense-old-service-fd9.py')
    unknown = load('stage0-opnsense-old-unknown-owner.py')
    baseline = snapshot(archive, pre, fd9)
    host = pre.run('hostname', '-s').decode().strip()
    old = pre.run_guest(archive, host)
    require(old['status'] == 'PASS_READ_ONLY_PROVENANCE', 'BASELINE_INVALID')
    # Same exact synthetic journal used by the separately proven _36 run.
    # It belongs exclusively to the fresh disposable OPNsense guest.
    created = False
    created_parent = False
    fake_calls = []
    try:
        created_parent = unknown.create_disposable_root_if_absent()
        created = unknown.create_owned_corrupt_journal()
        with tempfile.TemporaryDirectory(prefix='stage0-prepkg-negative-') as folder:
            unknown.prove_unknown_status(fd9.call_status(Path(folder) / 'fd9.lock'))
        try:
            require_snapshot_before(lambda: fake_calls.append('pkg'),
                                    lambda: snapshot(archive, pre, fd9))
        except Refusal as exc:
            reason = str(exc)
        else:
            raise Refusal('UNSAFE_UNKNOWN_OWNER_WAS_ACCEPTED')
        require(reason.startswith('UNVERIFIED_JOURNAL_MARKER_OR_PIDFILE:'),
                'WRONG_NEGATIVE_REFUSAL:' + reason)
        require(not fake_calls, 'PACKAGE_CALLBACK_INVOKED_AFTER_REFUSAL')
        unknown.verify_corrupt_journal()
        require(pre.run_guest(archive, host) == old,
                'REFUSED_PREFLIGHT_CHANGED_INSTALLED_PACKAGE')
    finally:
        if created:
            unknown.remove_only_owned_journal()
        if created_parent:
            require(JOURNAL.parent.is_dir() and not JOURNAL.parent.is_symlink() and
                    stat.S_IMODE(JOURNAL.parent.stat().st_mode) == 0o700,
                    'DISPOSABLE_PARENT_OWNERSHIP_CHANGED')
            JOURNAL.parent.rmdir()
    require(pre.run_guest(archive, host) == old,
            'CLEANUP_CHANGED_INSTALLED_OLD_PACKAGE')
    with tempfile.TemporaryDirectory(prefix='stage0-prepkg-restored-') as folder:
        fd9.prove_stopped(fd9.call_status(Path(folder) / 'fd9.lock'))
    return {'schema': 1, 'status': 'PASS_PREPKG_UNKNOWN_OWNER_NO_PKG_INVOKED',
            'initial_cold_snapshot': baseline['status'],
            'injected_state': 'synthetic-invalid-common-apply-journal-only',
            'genuine_installed_old_status': 2,
            'refusal': reason, 'package_callback_invoked': False,
            'original_package_preserved': True,
            'original_service_restored_cold': True,
            'disposable_fixture_removed': True,
            'real_pkg_operation_executed': False,
            'actual_foreign_ipfw_tested': False,
            'safe_pkg_transaction_authorized': False,
            'native_successor_tested': False, 'stage0_closed': False}


def main():
    if len(sys.argv) != 2:
        print('STAGE0_PREPKG=REFUSED:EXACT_ARCHIVE_REQUIRED', file=sys.stderr)
        return 2
    try:
        result = prove_negative(Path(sys.argv[1]))
    except (Refusal, OSError, ValueError, KeyError, TypeError) as exc:
        print('STAGE0_PREPKG=REFUSED:' + str(exc), file=sys.stderr)
        return 2
    print('STAGE0_PREPKG=' + json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
