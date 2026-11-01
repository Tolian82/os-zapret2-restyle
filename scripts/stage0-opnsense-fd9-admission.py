#!/usr/bin/env python3
"""Stage 0 only: native FD9 contention refusal before PRIVATE synthetic pkg.

Not an updater or atomic transaction; real published predecessor read-only.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
HOLDER = ('exec 9>"$1"; /usr/bin/lockf -s -t 0 9 || exit 75; '
          ': > "$2"; /bin/sleep 25')


class Refusal(Exception):
    pass


def need(value, reason):
    if not value:
        raise Refusal(reason)


def load(name):
    spec = importlib.util.spec_from_file_location(
        name.replace('-', '_').replace('.', '_'), HERE / name)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def contender(lock):
    try:
        r = subprocess.run(['/bin/sh', '-c',
                            '(/usr/bin/lockf -s -t 0 9) 9>"$1"',
                            'sh', str(lock)], capture_output=True, text=True,
                           timeout=8, check=False)
    except (OSError, subprocess.SubprocessError):
        raise Refusal('FD9_PROBE_UNAVAILABLE') from None
    return r.returncode == 0


def admit(lock_probe, old_probe, private_action):
    """Callback test seam, NOT atomic with next pkg and NOT a root veto."""
    need(lock_probe() is True, 'FD9_BUSY_OR_UNQUALIFIED')
    old = old_probe()
    need(type(old) is dict and
         old.get('status') == 'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY' and
         old.get('old_package') == 'os-zapret2-restyle-0.6.2_1' and
         old.get('real_old_status') == 'STOPPED' and
         old.get('safe_pkg_transaction_authorized') is False,
         'OLD_OWNER_NOT_VERIFIED_COLD')
    need(lock_probe() is True, 'FD9_CHANGED_BEFORE_PRIVATE_PKG')
    return private_action()


def busy_negative(lock, marker, baseline):
    child = subprocess.Popen(['/bin/sh', '-c', HOLDER, 'sh',
                              str(lock), str(marker)],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
    called = []
    try:
        deadline = time.monotonic() + 8
        while not marker.exists() and time.monotonic() < deadline:
            need(child.poll() is None, 'OWNED_HOLDER_EARLY_EXIT')
            time.sleep(.05)
        need(marker.exists() and child.poll() is None, 'FD9_HOLDER_NOT_LIVE')
        need(contender(lock) is False, 'FD9_BUSY_NOT_OBSERVED')
        try:
            admit(lambda: contender(lock), lambda: baseline,
                  lambda: called.append('pkg'))
        except Refusal as exc:
            need(str(exc) == 'FD9_BUSY_OR_UNQUALIFIED',
                 'WRONG_FD9_REFUSAL:' + str(exc))
        else:
            raise Refusal('FD9_BUSY_INCORRECTLY_ADMITTED')
        need(not called, 'PRIVATE_PKG_CALLBACK_INVOKED_ON_BUSY_FD9')
    finally:
        if child.poll() is None:
            child.terminate()
        try:
            child.wait(timeout=6)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=6)
    need(contender(lock) is True, 'FD9_NOT_RELEASED')
    return 'REFUSED_BUSY_FD9_BEFORE_PKG'


def private_add(work, native, fixture, locks):
    db, cache, payload = (work / x for x in ('pkgdb', 'cache', 'payload'))
    for item in (db, cache, payload):
        item.mkdir(parents=True, mode=0o700)
    pkg = ['pkg', '-o', 'REPO_AUTOUPDATE=false']
    env = dict(os.environ, PKG_DBDIR=str(db), PKG_CACHEDIR=str(cache),
               ASSUME_ALWAYS_YES='yes')
    archive, marker = fixture.build_fixture(
        work, 'old', '0.6.2_1', work / 'trace', payload)
    result = native.call(pkg + ['add', str(archive)], env)
    need(result.returncode == 0, 'PRIVATE_PKG_ADD_FAILED')
    state = locks.fixture_state(native, pkg, env, marker)
    need(state == ('zapret2-stage0-sidecar-only-fixture|0.6.2_1', b'old\n'),
         'PRIVATE_PKG_STATE_MISMATCH')
    return {'package': state[0], 'native_rc': result.returncode}


def run(archive):
    need(os.geteuid() == 0 and os.uname().sysname == 'FreeBSD' and
         os.uname().machine == 'amd64', 'ONLY_DISPOSABLE_ROOT_FREEBSD_AMD64')
    guest = load('stage0-opnsense-guest-readonly.py')
    need(guest.evaluate(guest.observe()).get('status') ==
         'PASS_ISOLATED_OPNSENSE_26_7_GUEST_IDENTITY', 'UNQUALIFIED_GUEST')
    oldinstaller = load('stage0-opnsense-installed-predecessor.py')
    routes = load('stage0-opnsense-pkg-root-routes.py')
    guard = load('stage0-opnsense-prepkg-readonly.py')
    native = load('stage0-opnsense-native-pkg-lock.py')
    fixture = load('stage0-opnsense-pkg-sidecar-bypass.py')
    locks = load('stage0-opnsense-pkg-relock-failures.py')
    oldinstaller.install_and_verify(archive)
    old = oldinstaller.pre
    host = old.run('hostname', '-s').decode().strip()
    original = old.run_guest(archive, host)
    need(original.get('status') == 'PASS_READ_ONLY_PROVENANCE',
         'ORIGINAL_NOT_PROVEN')
    baseline = routes.cold(guard, archive)
    with tempfile.TemporaryDirectory(prefix='stage0-fd9-gate-') as tmp:
        work = Path(tmp)
        lock = work / 'disposable-fd9.lock'
        negative = busy_negative(lock, work / 'holder', baseline)
        actions = []
        def private_callback():
            actions.append('private-only')
            return private_add(work / 'isolated', native, fixture, locks)
        positive = admit(lambda: contender(lock),
                         lambda: routes.cold(guard, archive), private_callback)
        need(actions == ['private-only'], 'CALLBACK_COUNT_CHANGED')
    need(old.run_guest(archive, host) == original, 'OLD_PACKAGE_CHANGED')
    routes.cold(guard, archive)
    return {'schema': 1, 'status': 'PASS_BUSY_FD9_REFUSAL_PRIVATE_PKG_ONLY',
            'negative': negative, 'positive_private_pkg': positive,
            'real_original_unchanged_cold': True,
            'real_running_engine_tested': False,
            'foreign_ipfw_tested': False, 'native_successor_tested': False,
            'atomic_pkg_transaction_proved': False,
            'direct_root_pkg_excluded': False,
            'product_safety_acceptance_passed': False, 'stage0_closed': False}


def main():
    if len(sys.argv) != 2:
        print('STAGE0_FD9_GATE=REFUSED:ARCHIVE_REQUIRED', file=sys.stderr)
        return 2
    try:
        print('STAGE0_FD9_GATE=' + json.dumps(run(Path(sys.argv[1])), sort_keys=True))
        return 0
    except Exception as exc:
        print('STAGE0_FD9_GATE=REFUSED:' + type(exc).__name__ + ':' + str(exc),
              file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
