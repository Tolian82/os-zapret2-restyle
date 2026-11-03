#!/usr/bin/env python3
"""Disposable OPNsense: historical package Status under its real inherited FD9.

Diagnostic only, never a package updater or a supported admission barrier.
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
import time

HERE = Path(__file__).resolve().parent
LOCK = Path('/var/run/zapret2-lifecycle.lock')
OPTIN = 'ZAPRET2_STAGE2_ORIGINAL_FD9_NESTED_STATUS'
HOLDER = ('set -eu; exec 9>"$1"; /usr/bin/lockf -s -t 1 9; '
          'printf "HELD\n" > "$2"; /bin/sleep 1; "$3" status')
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

def sha(data):
    return hashlib.sha256(data).hexdigest()

def check_lock_path(path):
    need(path == LOCK and not path.is_symlink(), 'FOREIGN_LOCK_PATH')
    if path.exists():
        st = path.lstat()
        need(stat.S_ISREG(st.st_mode) and st.st_nlink == 1 and st.st_uid == 0,
             'FOREIGN_LOCK_INODE')

def wait_held(marker, proc, timeout=8):
    need(0 < timeout <= 8, 'UNBOUNDED_LOCK_WAIT')
    deadline = time.monotonic() + timeout
    while not marker.exists() and time.monotonic() < deadline:
        need(proc.poll() is None, 'FD9_HOLDER_EARLY_EXIT')
        time.sleep(0.05)
    need(marker.is_file() and not marker.is_symlink() and proc.poll() is None,
         'FD9_HOLDER_UNVERIFIED')

def challenger(path):
    p = subprocess.run(['/bin/sh', '-c', CHALLENGER, 'sh', str(path)],
                       capture_output=True, text=True, timeout=6, check=False)
    need(p.returncode == 75, 'INDEPENDENT_FD9_NOT_BUSY:' + str(p.returncode))

def classify(rc, timed_out, output):
    if timed_out:
        return 'ORIGINAL_STATUS_NOT_COMPLETED_WITHIN_BOUNDED_FD9_HOLD'
    if rc == 1 and 'zapret is not running' in output:
        return 'ORIGINAL_COLD_STATUS_COMPLETED_UNDER_INHERITED_FD9'
    return 'ORIGINAL_STATUS_OTHER_RESULT_UNDER_INHERITED_FD9'

def inspect_nested_status(service):
    with tempfile.TemporaryDirectory(prefix='stage2-original-fd9-') as folder:
        marker = Path(folder) / 'held'
        proc = None
        timed_out = False
        out, err = '', ''
        try:
            proc = subprocess.Popen(
                ['/bin/sh', '-c', HOLDER, 'sh', str(LOCK), str(marker), str(service)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                start_new_session=True)
            wait_held(marker, proc)
            challenger(LOCK)
            try:
                out, err = proc.communicate(timeout=7)
            except subprocess.TimeoutExpired:
                timed_out = True
        finally:
            if proc is not None and proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)
                out, err = proc.communicate(timeout=8)
        need(marker.is_file(), 'NO_AUTHENTIC_FD9_HOLD')
        return {'verdict': classify(proc.returncode, timed_out, out + '\n' + err),
                'status_exit': None if timed_out else proc.returncode,
                'bounded_timeout': timed_out,
                'independent_fd9_contender_busy': True,
                'status_output_excerpt': (out + '\n' + err).strip()[:500]}

def execute(archive):
    need(os.geteuid() == 0 and os.environ.get('GITHUB_ACTIONS') == 'true'
         and os.environ.get(OPTIN) == '1', 'DISPOSABLE_OPTIN_REQUIRED')
    old = load('stage0-installed-predecessor-readonly.py')
    installer = load('stage0-opnsense-installed-predecessor.py')
    inspector = load('stage0-opnsense-prepkg-readonly.py')
    guest = load('stage0-opnsense-guest-readonly.py')
    need(guest.observe()['product_abi'] == '26.7', 'UNQUALIFIED_GUEST')
    witness = installer.install_and_verify(archive)
    need(witness['status'] == 'PASS_OPNSENSE_26_7_REAL_PREDECESSOR_INSTALLED_PROVENANCE',
         'OLD_PACKAGE_UNQUALIFIED')
    before = inspector.snapshot(archive)
    need(before['status'] == 'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY',
         'ORIGINAL_COLD_STATE_UNQUALIFIED')
    check_lock_path(LOCK)
    service = Path(old.SERVICE)
    service_sha = sha(service.read_bytes())
    config_sha = sha(Path('/conf/config.xml').read_bytes())
    query = ('pkg', '-o', 'REPO_AUTOUPDATE=false', 'info', '-R',
             '--raw-format', 'json', old.NAME)
    record = old.run(*query)
    obj = old.installed_manifest_from_json(record)
    need(obj.get('name') == old.NAME and obj.get('version') == old.VERSION,
         'OLD_PACKAGE_IDENTITY_UNVERIFIED')
    markers = tuple((p.exists(), p.is_symlink()) for p in inspector.MARKERS)
    result = inspect_nested_status(service)
    need(sha(service.read_bytes()) == service_sha, 'SERVICE_BYTES_CHANGED')
    need(sha(Path('/conf/config.xml').read_bytes()) == config_sha,
         'CONFIG_BYTES_CHANGED')
    need(old.run(*query) == record, 'PKGDB_BYTES_CHANGED')
    need(tuple((p.exists(), p.is_symlink()) for p in inspector.MARKERS)
         == markers, 'RESTART_MARKERS_CHANGED')
    need(inspector.snapshot(archive)['status'] == before['status'],
         'ORIGINAL_COLD_STATE_CHANGED')
    return {'schema': 1, 'status': 'PASS_ORIGINAL_FD9_NESTED_STATUS_DIAGNOSTIC_ONLY',
            'old_package': 'os-zapret2-restyle-0.6.2_1',
            'old_archive_sha256': old.ARCHIVE_SHA,
            'pkgdb_service_config_markers_unchanged': True,
            'native_pkg_replacement_attempted': False,
            'supported_admission_proven': False,
            'lh08_ac11_accepted': False, 'owner_appliance_modified': False,
            **result}

def main():
    if len(sys.argv) != 2:
        print('STAGE2_ORIGINAL_FD9=REFUSED:OLD_ARCHIVE_REQUIRED', file=sys.stderr)
        return 2
    try:
        print('STAGE2_ORIGINAL_FD9=' +
              json.dumps(execute(Path(sys.argv[1])), sort_keys=True))
        return 0
    except (Refusal, OSError, ValueError, KeyError, TypeError,
            subprocess.SubprocessError) as exc:
        print('STAGE2_ORIGINAL_FD9=REFUSED:' + str(exc), file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(main())
