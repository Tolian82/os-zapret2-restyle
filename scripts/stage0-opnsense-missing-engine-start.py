#!/usr/bin/env python3
"""Stage 0: actual archived predecessor refuses Start without separate engine.

Disposable OPNsense 26.7 KVM ONLY. This invokes installed original Start
only after authentic cold owner snapshot and engine-path absence; no setup,
firewall mutation, pkg replacement or real engine RUNNING is authorized.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ENGINE = Path('/usr/local/etc/zapret2/binaries/my/dvtws2')
ERROR = 'ERROR: zapret2 runtime is not installed or installation is incomplete'


class Refusal(Exception):
    pass


def need(condition, reason):
    if not condition:
        raise Refusal(reason)


def load(name):
    spec = importlib.util.spec_from_file_location(
        name.replace('-', '_').replace('.', '_'), HERE / name)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def require_missing_engine(path=ENGINE):
    # A dangling or present foreign symlink is never an absent runtime.
    need(not path.exists() and not path.is_symlink(),
         'RUNTIME_NOT_ABSENT_OR_FOREIGN_PATH')
    return True


def classify_start(result, before, after):
    need(before.get('status') == 'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY' and
         after.get('status') == 'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY',
         'COLD_OWNER_NOT_PRESERVED')
    need(before.get('safe_pkg_transaction_authorized') is False and
         after.get('safe_pkg_transaction_authorized') is False,
         'UNSAFE_PREPKG_AUTHORIZATION_OBSERVED')
    need(result.returncode == 1,
         'REAL_START_NOT_REFUSED_AS_EXPECTED:rc=' + str(result.returncode) +
         ':stderr=' + repr(result.stderr.strip()[:240]) +
         ':stdout=' + repr(result.stdout.strip()[:100]))
    need(ERROR in result.stderr and 'reinstall the plugin' in result.stderr,
         'REAL_START_DIAGNOSTIC_CHANGED')
    need(not result.stdout.strip(), 'UNEXPECTED_START_STDOUT')
    return 'REAL_OLD_START_REFUSED_MISSING_RUNTIME_BEFORE_FIREWALL'


def call_start(service, lock):
    env = os.environ.copy()
    env.update(LIFECYCLE_LOCK_FILE=str(lock), LOCKF_BIN='/usr/bin/lockf')
    try:
        return subprocess.run([service, 'start'], env=env, capture_output=True,
                              text=True, timeout=40, check=False)
    except (OSError, subprocess.SubprocessError):
        raise Refusal('REAL_START_UNAVAILABLE_OR_TIMEOUT') from None


def prove(archive):
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
    identity = old.run_guest(archive, hostname)
    need(identity.get('status') == 'PASS_READ_ONLY_PROVENANCE',
         'OLD_INSTALLED_PREDECESSOR_NOT_AUTHENTICATED')
    before = guard.snapshot(archive)
    need(before.get('status') == 'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY',
         'REAL_OLD_NOT_VERIFIED_COLD')
    require_missing_engine()
    with tempfile.TemporaryDirectory(prefix='stage0-absent-runtime-') as folder:
        result = call_start(old.SERVICE, Path(folder) / 'fd9.lock')
    require_missing_engine()
    after = guard.snapshot(archive)
    refused = classify_start(result, before, after)
    need(old.run_guest(archive, hostname) == identity,
         'REAL_PREDECESSOR_CHANGED_AFTER_START_REFUSAL')
    return {'schema': 1,
            'status': 'PASS_REAL_PREDECESSOR_MISSING_RUNTIME_START_REFUSAL',
            'refusal': refused, 'real_original_installed_start_invoked': True,
            'original_package_unchanged_cold': True,
            'runtime_engine_absent_before_and_after': True,
            'ipfw_unchanged_unloaded': True,
            'package_callback_invoked': False, 'old_stop_invoked': False,
            'configd_or_gui_mutation_invoked': False,
            'real_running_engine_tested': False,
            'actual_product_package_replaced': False,
            'coordinated_pkg_transaction_proved': False,
            'stage0_closed': False}


def main():
    if len(sys.argv) != 2:
        print('STAGE0_NO_ENGINE=REFUSED:ARCHIVE_REQUIRED', file=sys.stderr)
        return 2
    try:
        print('STAGE0_NO_ENGINE=' + json.dumps(prove(Path(sys.argv[1])), sort_keys=True))
        return 0
    except (Refusal, OSError, ValueError, KeyError, TypeError) as exc:
        print('STAGE0_NO_ENGINE=REFUSED:' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
