#!/usr/bin/env python3
"""Build pinned genuine upstream BSD dvtws2 only inside disposable OPNsense.

No deployed runtime install, Start, Stop, IPFW, kernel, or native pkg replacement.
VM-local build toolchain is pre-provisioned by CI from its configured repository.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
UPSTREAM = 'https://github.com/bol-van/zapret2.git'
PIN = '221d7dff24bfec0cd5ac0a5070b8acef2008af3d'
OLD_ENGINE = Path('/usr/local/etc/zapret2/binaries/my/dvtws2')


class Refusal(Exception):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def load(name):
    spec = importlib.util.spec_from_file_location(
        name.replace('-', '_').replace('.', '_'), HERE / name)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def call(args, *, cwd=None, timeout=180):
    try:
        return subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                              timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError):
        raise Refusal('COMMAND_UNAVAILABLE_OR_TIMEOUT:' + str(args[0])) from None


def checked(args, *, cwd=None, timeout=180):
    result = call(args, cwd=cwd, timeout=timeout)
    need(result.returncode == 0,
         'NATIVE_COMMAND_FAILED:' + str(args[0]) + ':' +
         (result.stderr + result.stdout)[-350:].replace('\n', ' '))
    return result.stdout.strip()


def require_uninstalled():
    need(not OLD_ENGINE.exists() and not OLD_ENGINE.is_symlink(),
         'INSTALLED_ENGINE_ALREADY_PRESENT_OR_FOREIGN')


def qualify_build(sha, exe, file_output, deps, help_output):
    need(sha == PIN, 'UPSTREAM_REVISION_NOT_EXACT_PIN')
    need(exe.is_file() and not exe.is_symlink() and os.access(exe, os.X_OK),
         'UPSTREAM_BUILD_MISSING_REAL_EXECUTABLE')
    need('ELF 64-bit' in file_output and
         ('FreeBSD' in file_output or 'FreeBSD' in deps) and
         ('x86-64' in file_output or 'x86_64' in file_output),
         'UPSTREAM_ELF_NOT_FREEBSD_AMD64')
    need('not found' not in deps.lower() and
         ('liblua' in deps.lower() or 'libluajit' in deps.lower()),
         'UNRESOLVED_OR_MISSING_LUA_PROVIDER')
    need('dvtws' in help_output.lower() or 'usage' in help_output.lower() or
         '--filter-' in help_output, 'REAL_ENGINE_HELP_UNRECOGNIZED')
    return True


def build(root):
    source = root / 'upstream'
    checked(['/usr/local/bin/git', 'init', '-q', str(source)])
    checked(['/usr/local/bin/git', '-C', str(source), 'remote', 'add', 'origin', UPSTREAM])
    checked(['/usr/local/bin/git', '-C', str(source), 'fetch', '--quiet', '--depth', '1',
             'origin', PIN], timeout=240)
    checked(['/usr/local/bin/git', '-C', str(source), 'checkout', '--quiet', '--detach', 'FETCH_HEAD'])
    sha = checked(['/usr/local/bin/git', '-C', str(source), 'rev-parse', 'HEAD'])
    need(sha == PIN, 'FETCHED_SOURCE_PIN_MISMATCH')
    checked(['/usr/local/bin/gmake', '-C', str(source), 'bsd', 'LUA_JIT=0', 'LUA_VER=5.4'],
            timeout=240)
    engine = source / 'binaries/my/dvtws2'
    need(engine.exists(), 'UPSTREAM_BUILD_DID_NOT_PRODUCE_DVTWS2')
    info = engine.lstat()
    need(stat.S_ISREG(info.st_mode) and not engine.is_symlink(),
         'UPSTREAM_ENGINE_NOT_REGULAR')
    file_output = checked(['/usr/bin/file', '-b', str(engine)])
    deps = checked(['/usr/bin/ldd', str(engine)])
    help_run = call([str(engine), '--help'], cwd=source, timeout=20)
    need(help_run.returncode in (0, 1, 2, 64), 'UPSTREAM_HELP_CRASHED_OR_UNKNOWN_EXIT')
    help_output = (help_run.stdout + '\n' + help_run.stderr)[:10000]
    qualify_build(sha, engine, file_output, deps, help_output)
    digest = hashlib.sha256(engine.read_bytes()).hexdigest()
    return {'upstream_sha': sha, 'binary_sha256': digest,
            'binary_size': info.st_size, 'file': file_output,
            'ldd': deps[:600], 'help_exit_code': help_run.returncode,
            'help_identified': True}


def run(archive):
    need(os.geteuid() == 0 and os.uname().sysname == 'FreeBSD' and
         os.uname().machine == 'amd64', 'ONLY_FREEBSD_AMD64_ROOT')
    guest = load('stage0-opnsense-guest-readonly.py')
    need(guest.evaluate(guest.observe()).get('status') ==
         'PASS_ISOLATED_OPNSENSE_26_7_GUEST_IDENTITY', 'NOT_ISOLATED_OPNSENSE_26_7')
    install = load('stage0-opnsense-installed-predecessor.py')
    guard = load('stage0-opnsense-prepkg-readonly.py')
    install.install_and_verify(archive)
    old = install.pre
    host = old.run('hostname', '-s').decode().strip()
    original = old.run_guest(archive, host)
    need(guard.snapshot(archive).get('status') == 'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY',
         'ORIGINAL_NOT_VERIFIED_COLD')
    require_uninstalled()
    with tempfile.TemporaryDirectory(prefix='stage0-real-dvtws-build-') as work:
        result = build(Path(work))
        require_uninstalled()
        need(old.run_guest(archive, host) == original, 'INSTALLED_PREDECESSOR_CHANGED')
        need(guard.snapshot(archive).get('status') == 'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY',
             'BUILD_CHANGED_ORIGINAL_COLD_OWNER')
    require_uninstalled()
    return {'schema': 1, 'status': 'PASS_PINNED_NATIVE_OPNSENSE_DVTWS2_BUILD',
            **result, 'real_old_package_unchanged_cold': True,
            'no_global_engine_install': True, 'no_firewall_or_start': True,
            'genuine_running_engine_tested': False,
            'native_pkg_successor_tested': False,
            'stage0_closed': False}


def main():
    if len(sys.argv) != 2:
        print('STAGE0_DVTWS_BUILD=REFUSED:ARCHIVE_REQUIRED', file=sys.stderr)
        return 2
    try:
        print('STAGE0_DVTWS_BUILD=' + json.dumps(run(Path(sys.argv[1])), sort_keys=True))
        return 0
    except (Refusal, OSError, ValueError, KeyError, TypeError) as exc:
        print('STAGE0_DVTWS_BUILD=REFUSED:' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
