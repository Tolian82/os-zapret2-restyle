#!/usr/local/bin/python3
"""One-use genuine OPNsense late-owner-fault veto on _89's *actual* pkg dispatch gate.

This runs only a DISPOSABLE native old package and a non-mutating dispatch
tripwire. It proves that a first cold admission is NOT cached and no native
pkg mutation is reached if original FD9 owner changes before dispatch.
Stock firmware, direct privileged root pkg and every post-gate race remain
UNPROTECTED. It is not a product updater or LH-08/AC-11 acceptance.
"""
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
PREFIX = 'STAGE3_LATE_OWNER_VETO='
OPTIN = 'ZAPRET2_STAGE3_LATE_OWNER_VETO'
LOCKED = ('set -eu; exec 9>"$1"; /usr/bin/lockf -s -t 0 9; '
          'exec /usr/local/bin/python3 "$2" --inner "$3" "$4"')


class Refusal(Exception):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


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
         and os.environ.get('ZAPRET2_STAGE2_LOCKED_COLD_REVALIDATION') == '1'
         and os.environ.get('ZAPRET2_STAGE2_DELEGATED_FD9_HANDOFF') == '1'
         and os.environ.get(OPTIN) == '1',
         'DISPOSABLE_NATIVE_LATE_OWNER_OPTIN_REQUIRED')


def tripwire(*_args):
    """No real pkg is reachable from the negative test-owned dispatcher."""
    raise Refusal('NATIVE_MUTATING_PKG_DISPATCH_REACHED')


def latest_gate_verdict(delegate, archive, expected_reason):
    """One identical production-candidate dispatch gate used by _89 positive.

    Passing a fake dispatcher is only a test safety tripwire. The real _89
    normal path passes no dispatcher and actually invokes native pkg.
    """
    try:
        delegate.admitted_pkg_dispatch(archive, Path('/dev/null'), {},
                                       dispatch=tripwire)
    except delegate.Refusal as exc:
        need(expected_reason in str(exc), 'WRONG_FINAL_ADMISSION_REFUSAL:' +
             str(exc)[:160])
        return 'DENIED_BEFORE_DISPATCH'
    # A successful return is not success: the mutated owner reached a call.
    raise Refusal('UNSAFE_OWNER_PASSED_FINAL_NATIVE_PKG_GATE')


def clean_tripwire(delegate, archive):
    marker = {'reached': False}
    def accepted(*_args):
        marker['reached'] = True
        return 'COLD_GATE_DISPATCH_TRIPWIRE_ONLY'
    need(delegate.verify_old_cold_admission(archive) ==
         'AUTHENTIC_OLD_COLD_OWNER_UNDER_ORIGINAL_FD9',
         'FIRST_COLD_ADMISSION_NOT_PROVEN')
    value = delegate.admitted_pkg_dispatch(
        archive, Path('/dev/null'), {}, dispatch=accepted)
    need(value == 'COLD_GATE_DISPATCH_TRIPWIRE_ONLY' and marker['reached'],
         'QUALIFIED_COLD_DISPATCH_PATH_NOT_REACHABLE')
    return 'QUALIFIED_COLD_REACHED_NONMUTATING_DISPATCH_TRIPWIRE'


def inner(case, archive):
    qualify()
    delegate = load('stage2-native-delegated-fd9-handoff.py')
    locked = load('stage2-prepkg-locked-cold-revalidation.py')
    old = load('stage0-installed-predecessor-readonly.py')
    guard = load('stage0-opnsense-prepkg-readonly.py')
    managed = load('stage2-managed-prepkg-veto-witness.py')
    unknown = load('stage0-opnsense-old-unknown-owner.py')
    foreign = load('stage0-opnsense-foreign-ipfw-admission.py')
    unsafe = load('stage2-opnsense-real-unsafe-owner-replacement.py')
    need(archive.is_file() and not archive.is_symlink(),
         'PUBLISHED_OLD_ARCHIVE_UNQUALIFIED')
    locked.check_fd9()
    old_identity = old.run('pkg', 'info', '-R', '--raw-format', 'json', NAME)
    need(old.installed_manifest_from_json(old_identity)['version'] == '0.6.2_1',
         'REAL_OLD_NOT_INSTALLED')
    if case == 'cold':
        before = managed.owner_snapshot(old, guard, archive)
        verdict = clean_tripwire(delegate, archive)
        need(managed.owner_snapshot(old, guard, archive) == before,
             'QUALIFIED_COLD_NONMUTATING_DISPATCH_CHANGED_STATE')
        return {'schema': 1, 'status': 'PASS_TEST_ONLY_COLD_GATE_REACHED_TRIPWIRE',
                'witness': verdict, 'real_pkg_mutation_invoked': False,
                'lh08_ac11_accepted': False}
    need(case in ('late_journal', 'late_orphan'),
         'UNKNOWN_LATE_OWNER_FIXTURE')
    need(delegate.verify_old_cold_admission(archive) ==
         'AUTHENTIC_OLD_COLD_OWNER_UNDER_ORIGINAL_FD9',
         'FIRST_COLD_ADMISSION_NOT_PROVEN')
    initial = managed.owner_snapshot(old, guard, archive)
    created_root = False
    created_journal = False
    added_orphan = False
    try:
        if case == 'late_journal':
            created_root = unknown.create_disposable_root_if_absent()
            created_journal = unknown.create_owned_corrupt_journal()
            unknown.verify_corrupt_journal()
            expected = 'UNVERIFIED_JOURNAL_MARKER_OR_PIDFILE:'
        else:
            foreign.activate_kernel(guard)
            unsafe.add_test_orphan()
            added_orphan = True
            need(unsafe.only_orphan_loopback_divert(),
                 'NOT_EXACT_TEST_OWNED_LOOPBACK_ORPHAN')
            expected = 'KERNEL_IPFW_OR_IPDIVERT_LOADED_OR_UNQUALIFIED'
        injected = managed.owner_snapshot(old, guard, archive)
        verdict = latest_gate_verdict(delegate, archive, expected)
        need(managed.owner_snapshot(old, guard, archive) == injected,
             'REJECTED_LATE_FAULT_CHANGED_PKGDB_FILES_CONFIG_PROCESS_IPFW')
        locked.check_fd9()
        need(old.run('pkg', 'info', '-R', '--raw-format', 'json', NAME) ==
             old_identity, 'REJECTED_LATE_FAULT_REPLACED_PUBLISHED_PACKAGE')
        if case == 'late_journal':
            unknown.verify_corrupt_journal()
        else:
            need(unsafe.only_orphan_loopback_divert(),
                 'TEST_ORPHAN_CHANGED_DURING_REFUSAL')
        print('STAGE3_LATE_OWNER_PRE_CLEANUP=' + json.dumps({
            'case': case, 'first_cold_admission_passed': True,
            'late_fault_denied': verdict, 'reason': expected,
            'real_native_pkg_mutation_invoked': False,
            'old_pkgdb_all_files_modes_config_markers_process_ipfw_unchanged': True,
        }, sort_keys=True), flush=True)
    finally:
        if created_journal:
            unknown.remove_only_owned_journal()
        if created_root:
            need(guard.JOURNAL.parent.is_dir() and
                 not guard.JOURNAL.parent.is_symlink() and
                 stat.S_IMODE(guard.JOURNAL.parent.stat().st_mode) == 0o700,
                 'OWNED_RUNTIME_JOURNAL_DIRECTORY_UNTRUSTED')
            guard.JOURNAL.parent.rmdir()
        if added_orphan:
            unsafe.remove_test_orphan()
    if case == 'late_journal':
        need(managed.owner_snapshot(old, guard, archive) == initial,
             'JOURNAL_FIXTURE_NOT_FULLY_RESTORED')
        need(delegate.verify_old_cold_admission(archive) ==
             'AUTHENTIC_OLD_COLD_OWNER_UNDER_ORIGINAL_FD9',
             'COLD_OWNER_NOT_RECOVERED_AFTER_JOURNAL_FIXTURE')
    else:
        # ipfw/ipdivert modules deliberately remain loaded in throwaway KVM;
        # no owner network appliance, production service, or repo state touched.
        need(unsafe.foreign.only_default(
             unsafe.foreign.command('/sbin/ipfw', '-q', 'list').stdout),
             'EXACT_ORPHAN_NOT_CLEANED')
    locked.check_fd9()
    return {'schema': 1,
            'status': 'PASS_TEST_ONLY_LATE_' + case.upper() + '_DENIED_BEFORE_PKG',
            'first_cold_owner_admitted': True,
            'late_owner_changed_after_first_gate': True,
            'same_final_gate_as_real_89_pkg': True,
            'observed_refusal': verdict,
            'old_pkgdb_files_modes_config_ipfw_preserved_on_refusal': True,
            'real_pkg_mutation_invoked': False,
            'stock_firmware_web_protected': False,
            'root_bypass_blocked': False,
            'post_final_gate_toc_tou_proven_absent': False,
            'product_updater_implemented': False,
            'lh08_ac11_accepted': False,
            'owner_appliance_modified': False}


def call_locked(case, archive):
    delegate = load('stage2-native-delegated-fd9-handoff.py')
    return subprocess.run(
        ['/bin/sh', '-c', LOCKED, 'sh', str(delegate.LOCK),
         str(Path(__file__).resolve()), case, str(archive)],
        capture_output=True, text=True, timeout=75, check=False)


def classify(p, case):
    need(p.returncode == 0, 'LATE_OWNER_NATIVE_WITNESS_REFUSED:' +
         str(p.returncode) + ':' + p.stderr[-320:])
    lines = [l[len(PREFIX):] for l in p.stdout.splitlines()
             if l.startswith(PREFIX)]
    need(len(lines) == 1, 'NOT_ONE_NATIVE_LATE_OWNER_WITNESS')
    report = json.loads(lines[0])
    expected = ('PASS_TEST_ONLY_COLD_GATE_REACHED_TRIPWIRE'
                if case == 'cold' else
                'PASS_TEST_ONLY_LATE_' + case.upper() + '_DENIED_BEFORE_PKG')
    need(report.get('status') == expected
         and report.get('real_pkg_mutation_invoked') is False
         and report.get('lh08_ac11_accepted') is False,
         'FALSE_LATE_NATIVE_PKG_SAFETY_REPORT')
    return report


def busy_negative(archive):
    locked = load('stage2-prepkg-locked-cold-revalidation.py')
    prior = load('stage2-opnsense-real-old-fd9-nonrecursive.py')
    with tempfile.TemporaryDirectory(prefix='stage3-busy-original-fd9-') as d:
        mark = Path(d) / 'held'
        proc = None
        try:
            proc = subprocess.Popen(
                ['/bin/sh', '-c', locked.BUSY_HOLDER, 'sh',
                 str(locked.LOCK), str(mark)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, start_new_session=True)
            prior.wait_held(mark, proc)
            p = call_locked('cold', archive)
            need(p.returncode == 75 and not p.stdout.strip(),
                 'BUSY_FD9_REACHED_MANAGED_NATIVE_DISPATCH')
            return 'BUSY_ORIGINAL_FD9_REFUSED_BEFORE_SAME_GATE'
        finally:
            if proc:
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGKILL)
                proc.communicate(timeout=8)


def execute(archive):
    qualify()
    guest = load('stage0-opnsense-guest-readonly.py')
    installer = load('stage0-opnsense-installed-predecessor.py')
    guard = load('stage0-opnsense-prepkg-readonly.py')
    old = load('stage0-installed-predecessor-readonly.py')
    managed = load('stage2-managed-prepkg-veto-witness.py')
    prior = load('stage2-opnsense-real-old-fd9-nonrecursive.py')
    locked = load('stage2-prepkg-locked-cold-revalidation.py')
    need(guest.evaluate(guest.observe())['status'] ==
         'PASS_ISOLATED_OPNSENSE_26_7_GUEST_IDENTITY',
         'NOT_ONE_USE_OPNSENSE_26_7')
    need(installer.install_and_verify(archive)['status'] ==
         'PASS_OPNSENSE_26_7_REAL_PREDECESSOR_INSTALLED_PROVENANCE',
         'REAL_PUBLISHED_OLD_NOT_INSTALLED')
    need(guard.snapshot(archive)['status'] ==
         'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY',
         'AUTHENTIC_OLD_STOPPED_PRECONDITION_FAILED')
    prior.check_lock_path(locked.LOCK)
    cold = classify(call_locked('cold', archive), 'cold')
    before = managed.owner_snapshot(old, guard, archive)
    busy = busy_negative(archive)
    need(managed.owner_snapshot(old, guard, archive) == before,
         'BUSY_REFUSAL_MUTATED_PUBLISHED_PACKAGE_OR_CONFIG')
    journal = classify(call_locked('late_journal', archive), 'late_journal')
    need(managed.owner_snapshot(old, guard, archive) == before,
         'LATE_JOURNAL_REFUSAL_MUTATED_PUBLISHED_PACKAGE')
    orphan = classify(call_locked('late_orphan', archive), 'late_orphan')
    old_after = managed.owner_snapshot(old, guard, archive)
    need(old_after['pkgdb'] == before['pkgdb']
         and old_after['installed_files'] == before['installed_files']
         and old_after['config'] == before['config']
         and old_after['markers'] == before['markers']
         and old_after['owned_processes'] == before['owned_processes']
         and old_after['four_original_hooks_sha256'] ==
             before['four_original_hooks_sha256'],
         'ORPHAN_REFUSAL_MUTATED_PRODUCT_FILES_CONFIG_OR_PROCESSES')
    return {'schema': 1,
            'status': 'PASS_TEST_ONLY_LATE_OWNER_NEGATIVES_SHARED_PKG_GATE',
            'real_predecessor_sha256': old.ARCHIVE_SHA,
            'cold_tripwire': cold['status'],
            'busy': busy, 'late_journal': journal['status'],
            'late_orphan': orphan['status'],
            'same_gate_real_positive_native_pkg_89': True,
            'genuine_published_old_pkgdb_files_config_process_preserved': True,
            'test_orphan_cleaned_exact': True,
            'ipfw_modules_left_loaded_in_disposable_guest': True,
            'native_mutating_pkg_invoked': False,
            'stock_firmware_web_route_protected': False,
            'root_pkg_bypass_protected': False,
            'post_final_check_race_prevented': False,
            'old_hooks_changed': False,
            'lh08_ac11_accepted': False,
            'owner_appliance_modified': False}


def main():
    if len(sys.argv) != 2 and not (
            len(sys.argv) == 4 and sys.argv[1] == '--inner'):
        print(PREFIX + 'REFUSED:EXACT_GUEST_ARGS_REQUIRED', file=sys.stderr)
        return 2
    try:
        if len(sys.argv) == 2:
            result = execute(Path(sys.argv[1]))
        else:
            result = inner(sys.argv[2], Path(sys.argv[3]))
        print(PREFIX + json.dumps(result, sort_keys=True), flush=True)
        return 0
    except (Refusal, OSError, KeyError, ValueError, TypeError,
            subprocess.SubprocessError) as exc:
        print(PREFIX + 'REFUSED:' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
