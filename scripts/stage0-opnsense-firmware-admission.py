#!/usr/bin/env python3
"""Stage 0 only: read-only proof of OPNsense firmware/pkg admission limits.

Not an updater, package preflight or transaction lock. Never runs pkg,
configctl, Stop, Apply or firmware actions and never authorizes replacement.
"""
import configparser
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys

HERE = Path(__file__).resolve().parent
FIRMWARE = Path('/usr/local/opnsense/scripts/firmware')
ACTIONS = Path('/usr/local/opnsense/service/conf/actions.d/actions_firmware.conf')
# Actual official 26.7 command paths, not a whitelist of safe transitions.
FIRMWARE_ROUTES = {
    'install': ('install.sh', ('output_cmd ${PKG} install -y',)),
    'remove': ('remove.sh', ('output_cmd ${PKG} remove -y',)),
    'reinstall': ('reinstall.sh', ('output_cmd opnsense-revert -l',)),
    'lock': ('lock.sh', ('${PKG} lock -y',)),
    'unlock': ('unlock.sh', ('${PKG} unlock -y',)),
    'update': ('update.sh', ('opnsense-update',)),
    'upgrade': ('upgrade.sh', ('opnsense-update -u',)),
}
# Explicitly INELIGIBLE until a separate, installed, owner-aware gate exists.
CLASSIFICATIONS = {
    'install': 'UNGUARDED_FIRMWARE_INSTALL',
    'remove': 'UNGUARDED_FIRMWARE_REMOVE',
    'reinstall': 'UNGUARDED_FIRMWARE_REINSTALL',
    'lock': 'PACKAGE_METADATA_LOCK_NOT_OWNER_GATE',
    'unlock': 'PRIVILEGED_PACKAGE_UNLOCK_BYPASS',
    'update': 'BROAD_FIRMWARE_UPDATE_NOT_OWNER_GATE',
    'upgrade': 'BROAD_FIRMWARE_UPGRADE_NOT_OWNER_GATE',
    'auto-update': 'SCHEDULED_FIRMWARE_UPDATE_NOT_OWNER_GATE',
    'direct-pkg-root': 'UNCOORDINATED_ROOT_PKG_UNSUPPORTED',
}


class Refusal(Exception):
    pass


def need(condition, reason):
    if not condition:
        raise Refusal(reason)


def load(file):
    spec = importlib.util.spec_from_file_location(
        file.replace('-', '_').replace('.', '_'), HERE / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_regular(path):
    st = path.lstat()
    need(stat.S_ISREG(st.st_mode) and not path.is_symlink(),
         'UNQUALIFIED_FIRMWARE_FILE:' + path.name)
    data = path.read_bytes()
    need(100 <= len(data) <= 45000, 'INVALID_FIRMWARE_FILE_SIZE:' + path.name)
    return data


def verify_source(route, text):
    need(route in FIRMWARE_ROUTES, 'UNRECOGNIZED_FIRMWARE_ROUTE')
    name, signatures = FIRMWARE_ROUTES[route]
    need(text.startswith('#!/bin/sh') and
         all(signature in text for signature in signatures),
         'UNEXPECTED_FIRMWARE_IMPLEMENTATION:' + name)


def verify_actions(text):
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    parser.read_string(text)
    for route in FIRMWARE_ROUTES:
        need(parser.has_section(route), 'FIRMWARE_ACTION_MISSING:' + route)
        command = parser.get(route, 'command', fallback='')
        need(command == '/usr/sbin/daemon -f '
             '/usr/local/opnsense/scripts/firmware/launcher.sh ' + route,
             'UNEXPECTED_FIRMWARE_ACTION:' + route)
        need(parser.get(route, 'parameters', fallback='') == '%s' if route in
             ('install', 'remove', 'reinstall', 'lock', 'unlock', 'update') else
             parser.get(route, 'parameters', fallback='') == '',
             'UNEXPECTED_FIRMWARE_ACTION_PARAMETERS:' + route)
    need(parser.has_section('auto-update') and
         parser.get('auto-update', 'command', fallback='') ==
         '/usr/local/etc/rc.firmware -r 1500',
         'UNEXPECTED_AUTO_UPDATE_ACTION')


def verify_launcher(text):
    need(text.startswith('#!/bin/sh') and
         '${FLOCK} -n -o ${LOCKFILE} ${COMMAND}' in text and
         'env LOCKFILE=/dev/null ${COMMAND}' in text,
         'FIRMWARE_LAUNCHER_LOCK_SEMANTICS_CHANGED')


def admit_product_update(route, *args, **kwargs):
    """Never authorize from firmware routing or a cold snapshot alone."""
    need(route in CLASSIFICATIONS, 'UNKNOWN_PACKAGE_ENTRYPOINT')
    raise Refusal('NO_EXCLUSIVE_OWNER_AWARE_PKG_TRANSACTION:' + route)


def read_only_audit(firmware=FIRMWARE, actions=ACTIONS):
    hashes = {}
    for route, (filename, _) in FIRMWARE_ROUTES.items():
        data = verify_regular(firmware / filename)
        verify_source(route, data.decode('utf-8'))
        hashes[filename] = hashlib.sha256(data).hexdigest()
    launcher = verify_regular(firmware / 'launcher.sh')
    verify_launcher(launcher.decode('utf-8'))
    hashes['launcher.sh'] = hashlib.sha256(launcher).hexdigest()
    action_bytes = verify_regular(actions)
    verify_actions(action_bytes.decode('utf-8'))
    hashes['actions_firmware.conf'] = hashlib.sha256(action_bytes).hexdigest()
    for route in CLASSIFICATIONS:
        try:
            admit_product_update(route, {'status': 'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY'})
        except Refusal as exc:
            need(str(exc) == 'NO_EXCLUSIVE_OWNER_AWARE_PKG_TRANSACTION:' + route,
                 'UNEXPECTED_ROUTE_ADMISSION_RESULT:' + route)
        else:
            raise Refusal('UNSAFE_FIRMWARE_ROUTE_AUTHORIZED:' + route)
    return {
        'schema': 1,
        'status': 'PASS_READ_ONLY_FIRMWARE_ROUTE_CLASSIFICATION',
        'native_firmware_sha256': hashes,
        'route_classification': CLASSIFICATIONS,
        'official_firmware_progress_flock_is_not_fd9': True,
        'native_pkg_lock_is_not_root_exclusion': True,
        'uncoordinated_root_pkg_unsupported': True,
        'stock_firmware_paths_accepted_as_safe_updates': False,
        'genuine_running_engine_tested': False,
        'foreign_ipfw_kernel_tested': False,
        'real_owner_aware_pkg_transaction_tested': False,
        'product_safety_acceptance_passed': False,
        'stage0_closed': False,
    }


def main():
    if len(sys.argv) != 1:
        print('STAGE0_FIRMWARE_ADMISSION=REFUSED:NO_ARGUMENTS_ALLOWED', file=sys.stderr)
        return 2
    try:
        guest = load('stage0-opnsense-guest-readonly.py')
        need(os.geteuid() == 0 and os.uname().sysname == 'FreeBSD' and
             os.uname().machine == 'amd64', 'ONLY_DISPOSABLE_OPNSENSE_FREEBSD_AMD64')
        need(guest.evaluate(guest.observe()).get('status') ==
             'PASS_ISOLATED_OPNSENSE_26_7_GUEST_IDENTITY', 'GUEST_NOT_QUALIFIED')
        report = read_only_audit()
    except (Refusal, OSError, ValueError, UnicodeDecodeError, configparser.Error) as exc:
        print('STAGE0_FIRMWARE_ADMISSION=REFUSED:' + str(exc), file=sys.stderr)
        return 2
    print('STAGE0_FIRMWARE_ADMISSION=' + json.dumps(report, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
