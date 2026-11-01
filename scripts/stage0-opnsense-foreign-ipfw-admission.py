#!/usr/bin/env python3
"""Stage 0 real foreign IPFW count-only rule on disposable OPNsense KVM.

One test-owned COUNT rule, no divert, Stop, Start, pkg replacement, or
production updater. Refusal-before-callback is NOT root/pkg transaction veto.
"""
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
RULE = 63037
RULE_TEXT = f'{RULE} count ip from any to any'
DEFAULT = '65535 allow ip from any to any'
ORPHAN = '65535 count ip from any to any not // orphaned dynamic states counter'


class Refusal(Exception):
    pass


def need(condition, code):
    if not condition:
        raise Refusal(code)


def load(filename):
    spec = importlib.util.spec_from_file_location(
        filename.replace('-', '_').replace('.', '_'), HERE / filename)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def command(*args):
    try:
        return subprocess.run(args, capture_output=True, text=True,
                              timeout=25, check=False)
    except (OSError, subprocess.SubprocessError):
        raise Refusal('NATIVE_COMMAND_UNAVAILABLE_OR_TIMEOUT:' + args[0]) from None


def kernel_rules(text):
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    # Native FreeBSD 15.1 emits an additional built-in orphaned-dynamic-states
    # counter at 65535, already recognized in the project's native IPFW tests.
    # Accept ONLY this exact built-in line, not arbitrary count/allow rules.
    if lines.count(ORPHAN) > 1:
        return lines
    return [line for line in lines if line != ORPHAN]


def only_default(text):
    return kernel_rules(text) == [DEFAULT]


def only_injected_foreign(text):
    lines = kernel_rules(text)
    return lines == [RULE_TEXT, DEFAULT] or lines == [DEFAULT, RULE_TEXT]


def refuse_before_private_callback(guard, snapshot):
    calls = []
    try:
        guard.require_snapshot_before(lambda: calls.append('pkg'), snapshot)
    except guard.Refusal as exc:
        reason = str(exc)
        need(reason.startswith(('REAL_OLD_SERVICE_NOT_PROVEN_STOPPED:',
                                'KERNEL_IPFW_OR_IPDIVERT_LOADED_OR_UNQUALIFIED',
                                'IPFW_NOT_PROVEN_UNLOADED_COLD',
                                'UNVERIFIED_JOURNAL_MARKER_OR_PIDFILE:',
                                'POSSIBLE_ZAPRET_PROCESS_PRESENT')),
             'UNEXPECTED_OWNER_REFUSAL:' + reason)
        need(not calls, 'PKG_CALLBACK_EXECUTED_WITH_FOREIGN_IPFW')
        return reason
    raise Refusal('FOREIGN_KERNEL_UNSAFE_SNAPSHOT_ACCEPTED')


def unloaded(guard):
    module = command('/sbin/kldstat', '-q', '-m', 'ipfw')
    divert = command('/sbin/kldstat', '-q', '-m', 'ipdivert')
    rule = command('/sbin/ipfw', '-q', 'list')
    need(guard.check_kernel_cold(module.returncode, divert.returncode,
                                 rule.returncode, rule.stdout + rule.stderr) ==
         'UNLOADED_COLD_ENOPROTOOPT', 'BASELINE_IPFW_NOT_COLD')


def activate_kernel(guard):
    unloaded(guard)
    # Exactly the existing FreeBSD native safe-cold-load contract: default
    # accept must be confirmed before kldload. Fresh disposable guest only.
    need(command('/bin/kenv', 'net.inet.ip.fw.default_to_accept=1').returncode == 0,
         'CANNOT_SET_VM_DEFAULT_ACCEPT')
    kenv = command('/bin/kenv', '-qv', 'net.inet.ip.fw.default_to_accept')
    need(kenv.returncode == 0 and kenv.stdout.strip() in (
         'net.inet.ip.fw.default_to_accept="1"',
         'net.inet.ip.fw.default_to_accept=1'), 'DEFAULT_ACCEPT_KENV_UNVERIFIED')
    need(command('/sbin/kldload', 'ipfw').returncode == 0,
         'DISPOSABLE_VM_IPFW_KLDLOAD_FAILED')
    sysctl = command('/sbin/sysctl', '-n', 'net.inet.ip.fw.default_to_accept')
    listing = command('/sbin/ipfw', '-q', 'list')
    need(sysctl.returncode == 0 and sysctl.stdout.strip() == '1' and
         listing.returncode == 0 and only_default(listing.stdout),
         'KERNEL_NOT_EXCLUSIVELY_DEFAULT_ALLOW:sysctl=' +
         str(sysctl.returncode) + ':' + repr(sysctl.stdout.strip()) +
         ':ipfw=' + str(listing.returncode) + ':' +
         repr(listing.stdout.strip()[:360]) + ':' +
         repr(listing.stderr.strip()[:140]))


def foreign_rule_add():
    before = command('/sbin/ipfw', '-q', 'list')
    need(before.returncode == 0 and only_default(before.stdout),
         'FOREIGN_BASELINE_NOT_DEFAULT_ONLY')
    add = command('/sbin/ipfw', '-q', 'add', str(RULE),
                  'count', 'ip', 'from', 'any', 'to', 'any')
    need(add.returncode == 0, 'FOREIGN_TEST_COUNT_RULE_ADD_FAILED')
    after = command('/sbin/ipfw', '-q', 'list')
    need(after.returncode == 0 and only_injected_foreign(after.stdout),
         'FOREIGN_RULE_INSTALL_NOT_PROVEN')


def remove_owned_rule():
    current = command('/sbin/ipfw', '-q', 'list')
    need(current.returncode == 0 and only_injected_foreign(current.stdout),
         'FOREIGN_RULE_IDENTITY_CHANGED_REFUSE_DELETE')
    need(command('/sbin/ipfw', '-q', 'delete', str(RULE)).returncode == 0,
         'TEST_OWNED_RULE_DELETE_FAILED')
    after = command('/sbin/ipfw', '-q', 'list')
    need(after.returncode == 0 and only_default(after.stdout),
         'TEST_OWNED_RULE_CLEANUP_INCOMPLETE')


def run(archive):
    need(os.geteuid() == 0 and os.uname().sysname == 'FreeBSD' and
         os.uname().machine == 'amd64', 'ONLY_DISPOSABLE_FREEBSD_ROOT')
    guest = load('stage0-opnsense-guest-readonly.py')
    need(guest.evaluate(guest.observe()).get('status') ==
         'PASS_ISOLATED_OPNSENSE_26_7_GUEST_IDENTITY', 'NOT_FRESH_OPNSENSE_KVM')
    installer = load('stage0-opnsense-installed-predecessor.py')
    guard = load('stage0-opnsense-prepkg-readonly.py')
    installer.install_and_verify(archive)
    old = installer.pre
    hostname = old.run('hostname', '-s').decode().strip()
    original = old.run_guest(archive, hostname)
    need(original.get('status') == 'PASS_READ_ONLY_PROVENANCE',
         'REAL_OLD_PACKAGE_NOT_AUTHENTICATED')
    need(guard.snapshot(archive)['status'] ==
         'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY', 'GENUINE_COLD_BASELINE_MISSING')
    activate_kernel(guard)
    injected = False
    try:
        foreign_rule_add()
        injected = True
        reason = refuse_before_private_callback(guard, lambda: guard.snapshot(archive))
        live = command('/sbin/ipfw', '-q', 'list')
        need(live.returncode == 0 and only_injected_foreign(live.stdout),
             'REFUSED_PROBE_MUTATED_FOREIGN_KERNEL_RULE')
        need(old.run_guest(archive, hostname) == original,
             'REFUSED_PROBE_MUTATED_REAL_ORIGINAL_PACKAGE')
    finally:
        if injected:
            remove_owned_rule()
        # Only after exact default-only rule state; restore cold kernel in
        # throwaway guest. Never unload an unqualified modified rule table.
        current = command('/sbin/ipfw', '-q', 'list')
        need(current.returncode == 0 and only_default(current.stdout),
             'CANNOT_SAFELY_UNLOAD_MODIFIED_IPFW')
        need(command('/sbin/kldunload', 'ipfw').returncode == 0,
             'DISPOSABLE_IPFW_KLDUNLOAD_FAILED')
    unloaded(guard)
    need(guard.snapshot(archive)['status'] ==
         'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY', 'OLD_COLD_NOT_RESTORED')
    need(old.run_guest(archive, hostname) == original, 'ORIGINAL_PKGDB_CHANGED')
    return {'schema': 1, 'status': 'PASS_NATIVE_FOREIGN_IPFW_REFUSED_BEFORE_CALLBACK',
            'live_kernel_rule': RULE_TEXT, 'refusal': reason,
            'test_owned_count_rule_cleaned': True, 'original_kernel_cold_restored': True,
            'genuine_original_unchanged_cold': True, 'package_callback_invoked': False,
            'native_pkg_operation_executed': False, 'real_running_engine_tested': False,
            'real_foreign_ipfw_kernel_tested': True, 'safe_pkg_transaction_proved': False,
            'uncoordinated_root_pkg_excluded': False, 'stage0_closed': False}


def main():
    if len(sys.argv) != 2:
        print('STAGE0_FOREIGN_IPFW=REFUSED:ARCHIVE_REQUIRED', file=sys.stderr)
        return 2
    try:
        print('STAGE0_FOREIGN_IPFW=' + json.dumps(run(Path(sys.argv[1])), sort_keys=True))
        return 0
    except (Refusal, OSError, ValueError, KeyError, TypeError) as exc:
        print('STAGE0_FOREIGN_IPFW=REFUSED:' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
