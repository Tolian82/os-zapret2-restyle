#!/usr/bin/env python3
"""Stage 0 native pkg hook-failure compensation on PRIVATE synthetic fixtures.

Disposable OPNsense 26.7 only. Genuine published old Zapret2 is installed for
READ-ONLY authentication and cold Status. No genuine pkg replacement, Stop,
Start, Apply, firmware, IPFW modification or production transaction is made.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
NAME = 'zapret2-stage0-compensation-fixture'
OLD = (NAME + '|0.6.2_1', b'old\n')
NEW = (NAME + '|0.6.2_50', b'faulted\n')
PHASES = ('pre-install', 'post-install', 'pre-deinstall', 'post-deinstall')
INITIAL = ('old:pre-install', 'old:post-install')
FAULT = ('faulted:pre-install', 'faulted:post-install:INJECTED_FAULT')


class Refusal(Exception):
    pass


def need(condition, code):
    if not condition:
        raise Refusal(code)


def load(filename):
    spec = importlib.util.spec_from_file_location(
        filename.replace('.', '_').replace('-', '_'), HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build(work, role, trace, payload_root, native):
    need(role in ('old', 'faulted'), 'UNEXPECTED_SYNTHETIC_ROLE')
    version = '0.6.2_1' if role == 'old' else '0.6.2_50'
    payload = (role + '\n').encode('ascii')
    marker = payload_root / 'fixture'
    staging = work / ('staging-' + role)
    file = staging / str(marker).lstrip('/')
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(payload)
    scripts = {}
    for phase in PHASES:
        fault = role == 'faulted' and phase == 'post-install'
        event = role + ':' + phase + (':INJECTED_FAULT' if fault else '')
        scripts[phase] = ('#!/bin/sh\n/bin/echo "' + event + '" >> "' +
                          str(trace) + '"\nexit ' + ('73' if fault else '0') + '\n')
    manifest = {'name': NAME, 'origin': 'sysutils/' + NAME,
                'version': version, 'abi': 'FreeBSD:15:amd64',
                'arch': 'freebsd:15:x86:64', 'prefix': str(payload_root),
                'comment': 'Disposable OPNsense Stage0 package compensation',
                'desc': 'Synthetic private pkg hook failure only',
                'maintainer': 'test@example.invalid',
                'www': 'https://example.invalid', 'licenselogic': 'single',
                'licenses': ['MIT'], 'scripts': scripts,
                'files': {str(marker): hashlib.sha256(payload).hexdigest()}}
    source = work / ('manifest-' + role + '.json')
    source.write_text(json.dumps(manifest), encoding='utf-8')
    dest = work / ('archives-' + role)
    dest.mkdir()
    outcome = native.call(['pkg', 'create', '-M', str(source),
                           '-r', str(staging), '-o', str(dest)])
    need(outcome.returncode == 0, 'SYNTHETIC_ARCHIVE_CREATION_FAILED')
    paths = list(dest.glob(NAME + '-' + version + '.pkg'))
    need(len(paths) == 1, 'SYNTHETIC_ARCHIVE_UNQUALIFIED')
    return paths[0], marker


def pkg_state(native, pkg, env, marker):
    result = native.call(pkg + ['query', '%n|%v', NAME], env)
    need(result.returncode == 0, 'PRIVATE_PKGDB_QUERY_FAILED')
    need(marker.is_file() and not marker.is_symlink(),
         'PRIVATE_PAYLOAD_MISSING_OR_FOREIGN')
    return (result.stdout.strip(), marker.read_bytes())


def classify_mutation(exit_code, state, events):
    need(state == NEW, 'INJECTED_HOOK_PKG_MUTATION_NOT_PROVEN')
    need(tuple(events) == INITIAL + FAULT,
         'INJECTED_HOOK_PHASES_NOT_EXACT')
    need(exit_code == 0, 'NATIVE_PKG_RETURN_BEHAVIOR_DIFFERENT')
    return 'NATIVE_PKG_RETURNED_SUCCESS_AFTER_FAILED_POST_INSTALL'


def assert_compensated(state, events):
    need(state == OLD, 'PRIVATE_PKG_COMPENSATION_DID_NOT_RESTORE_OLD')
    need(tuple(events) == INITIAL + FAULT + INITIAL,
         'PRIVATE_PKG_COMPENSATION_PHASES_NOT_EXACT')
    return 'PRIVATE_FIXTURE_RESTORED_AFTER_DETECTED_HOOK_FAULT'


def isolated_compensation(work, native):
    db, cache, payload = work / 'pkgdb', work / 'cache', work / 'payload'
    for path in (db, cache, payload):
        path.mkdir(parents=True, mode=0o700)
    env = dict(os.environ, PKG_DBDIR=str(db), PKG_CACHEDIR=str(cache),
               ASSUME_ALWAYS_YES='yes')
    pkg = ['pkg', '-o', 'REPO_AUTOUPDATE=false']
    trace = work / 'hooks.trace'
    old_archive, marker = build(work, 'old', trace, payload, native)
    fault_archive, same_marker = build(work, 'faulted', trace, payload, native)
    need(marker == same_marker, 'INCONSISTENT_PRIVATE_FILE_IDENTITY')
    first = native.call(pkg + ['add', str(old_archive)], env)
    need(first.returncode == 0 and pkg_state(native, pkg, env, marker) == OLD,
         'PRIVATE_OLD_FIXTURE_NOT_INSTALLED')
    need(tuple(trace.read_text(encoding='ascii').splitlines()) == INITIAL,
         'INITIAL_HOOK_SCHEDULER_CHANGED')
    # Do NOT hold original FD9 across pkg; old/new hooks may reacquire it.
    attempt = native.call(pkg + ['add', '-f', str(fault_archive)], env)
    mutated = pkg_state(native, pkg, env, marker)
    actual = trace.read_text(encoding='ascii').splitlines()
    observed = classify_mutation(attempt.returncode, mutated, actual)
    # Compensation is ONLY on a synthetic private pkgdb; not a product
    # transaction, native rollback guarantee, or crash-safe atomic commit.
    restored = native.call(pkg + ['add', '-f', str(old_archive)], env)
    need(restored.returncode == 0, 'PRIVATE_COMPENSATION_PKG_FAILED')
    after = pkg_state(native, pkg, env, marker)
    completed = trace.read_text(encoding='ascii').splitlines()
    outcome = assert_compensated(after, completed)
    return {'observed_native_fault': observed,
            'compensation': outcome,
            'native_fault_add_rc': attempt.returncode,
            'native_compensation_rc': restored.returncode,
            'final_private_package': after[0],
            'hook_trace': completed}


def prove(archive):
    need(os.geteuid() == 0 and os.uname().sysname == 'FreeBSD' and
         os.uname().machine == 'amd64', 'ONLY_DISPOSABLE_FREEBSD_ROOT')
    guest = load('stage0-opnsense-guest-readonly.py')
    need(guest.evaluate(guest.observe()).get('status') ==
         'PASS_ISOLATED_OPNSENSE_26_7_GUEST_IDENTITY', 'NOT_FRESH_KVM_OPNSENSE')
    installed = load('stage0-opnsense-installed-predecessor.py')
    routes = load('stage0-opnsense-pkg-root-routes.py')
    guard = load('stage0-opnsense-prepkg-readonly.py')
    native = load('stage0-opnsense-native-pkg-lock.py')
    installed.install_and_verify(archive)
    old = installed.pre
    hostname = old.run('hostname', '-s').decode().strip()
    original = old.run_guest(archive, hostname)
    need(original.get('status') == 'PASS_READ_ONLY_PROVENANCE',
         'PUBLISHED_PREDECESSOR_UNVERIFIED')
    routes.cold(guard, archive)
    with tempfile.TemporaryDirectory(prefix='stage0-pkg-compensation-') as tmp:
        report = isolated_compensation(Path(tmp), native)
    need(old.run_guest(archive, hostname) == original,
         'AUTHENTIC_OLD_PACKAGE_MUTATED')
    routes.cold(guard, archive)
    return {'schema': 1,
            'status': 'PASS_PRIVATE_NATIVE_PKG_HOOK_FAULT_COMPENSATION',
            **report, 'genuine_predecessor_unchanged_and_cold': True,
            'real_plugin_replaced': False,
            'real_running_engine_tested': False,
            'foreign_ipfw_kernel_tested': False,
            'native_successor_tested': False,
            'actual_product_rollback_tested': False,
            'crash_atomicity_proved': False,
            'root_pkg_bypass_excluded': False,
            'product_safety_acceptance_passed': False,
            'stage0_closed': False}


def main():
    if len(sys.argv) != 2:
        print('STAGE0_PKG_COMPENSATION=REFUSED:ARCHIVE_REQUIRED', file=sys.stderr)
        return 2
    try:
        print('STAGE0_PKG_COMPENSATION=' +
              json.dumps(prove(Path(sys.argv[1])), sort_keys=True))
        return 0
    except (Refusal, OSError, ValueError, KeyError) as exc:
        print('STAGE0_PKG_COMPENSATION=REFUSED:' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
