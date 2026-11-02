#!/usr/bin/env python3
"""Stage 2.24 read-only installed configctl status acceptance in disposable OPNsense.

Never send a signal, reload configd, start/stop a service, change Config/IPFW,
or authorize a future signal. This is not Stage 3 race-safe reload acceptance.
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

ROOT = Path(__file__).resolve().parents[1]
ACTION_REL = 'opnsense/service/conf/actions.d/actions_zapret.conf'
SERVICE_REL = 'opnsense/scripts/OPNsense/Zapret/zapret_service.sh'
PACKAGE = 'os-zapret2-restyle'
VERSION = '0.6.2_77'
MARKERS = ('/var/run/zapret2-restyle/pkg-upgrade.restart',
           '/var/run/zapret2-restyle/pkg-replacement.restart')


class Refusal(RuntimeError):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def run(args, timeout=25):
    try:
        return subprocess.run(args, check=False, capture_output=True,
                              text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        raise Refusal('READONLY_COMMAND_UNAVAILABLE_OR_TIMEOUT:' + args[0]) from None


def stdout(args, reason):
    result = run(args)
    need(result.returncode == 0, reason + ':rc=' + str(result.returncode))
    return result.stdout.strip()


def safe_bytes(path):
    need(path.is_file() and not path.is_symlink(), 'ACTION_FILE_UNTRUSTED')
    meta = path.stat()
    need(stat.S_ISREG(meta.st_mode) and meta.st_size <= 65536,
         'ACTION_FILE_TYPE_OR_SIZE_INVALID')
    return path.read_bytes()


def exact_status_action(raw):
    try:
        text = raw.decode('utf-8')
    except UnicodeError:
        raise Refusal('ACTION_ENCODING_INVALID') from None
    names = re.findall(r'(?m)^\[([^]\r\n]+)\]\s*$', text)
    need(names.count('status') == 1, 'STATUS_SECTION_AMBIGUOUS')
    section = re.search(r'(?ms)^\[status\]\s*\n(.*?)(?=^\[|\Z)', text)
    need(section is not None, 'STATUS_SECTION_MISSING')
    fields = {}
    for line in section.group(1).splitlines():
        if not line.strip():
            continue
        name, sep, value = line.partition(':')
        need(sep and name not in fields, 'STATUS_ACTION_DUPLICATE_FIELD')
        fields[name] = value.strip()
    need(fields.get('command') == '/usr/local/' + SERVICE_REL + ' status; exit 0'
         and fields.get('type') == 'script_output'
         and fields.get('parameters') == '', 'STATUS_ACTION_NOT_READONLY')
    return True


def package_identity(root=Path('/usr/local')):
    need(stdout(['pkg', 'query', '%v', PACKAGE], 'PKG_VERSION_UNAVAILABLE') ==
         VERSION, 'PKG_VERSION_MISMATCH')
    owner = stdout(['pkg', 'which', '-q', str(root / ACTION_REL)],
                   'PKG_ACTION_OWNER_UNAVAILABLE')
    need(owner in (PACKAGE, PACKAGE + '-' + VERSION), 'ACTION_NOT_PKG_OWNED')


def load_watcher():
    path = Path(__file__).with_name('stage2-configd-worker-readonly.py')
    spec = importlib.util.spec_from_file_location('configd_readonly', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify(config=Path('/conf/config.xml'), installed_root=Path('/usr/local'), markers=MARKERS):
    need(os.environ.get('GITHUB_ACTIONS') == 'true'
         and os.environ.get('ZAPRET2_NATIVE_BUILD_CI') == '1'
         and os.environ.get('ZAPRET2_STAGE2_PACKAGED_CONFIGCTL_READONLY') == '1',
         'DISPOSABLE_CI_OPTIN_REQUIRED')
    need(os.geteuid() == 0 and os.uname().sysname == 'FreeBSD'
         and os.uname().machine == 'amd64', 'NOT_FREEBSD_AMD64_ROOT')
    need(stdout(['opnsense-version', '-a'], 'OPNSENSE_VERSION_UNAVAILABLE') ==
         '26.7', 'OPNSENSE_PRODUCT_ABI_UNQUALIFIED')
    need(stdout(['pkg', 'config', 'ABI'], 'PKG_ABI_UNAVAILABLE') ==
         'FreeBSD:15:amd64', 'PKG_ABI_UNQUALIFIED')
    need(stdout(['sysctl', '-n', 'kern.vm_guest'], 'VM_IDENTITY_UNAVAILABLE').lower()
         not in ('', 'none', 'unknown'), 'NOT_VIRTUAL_GUEST')
    package_identity(installed_root)
    source = safe_bytes(ROOT / 'src' / ACTION_REL)
    installed = safe_bytes(installed_root / ACTION_REL)
    need(source == installed, 'INSTALLED_ACTION_BYTES_DIFFER')
    exact_status_action(installed)
    watcher = load_watcher()
    before = watcher.snapshot()
    need(config.is_file() and not config.is_symlink(), 'CONFIG_UNTRUSTED')
    config_before = hashlib.sha256(config.read_bytes()).digest()
    need(all(not Path(p).exists() and not Path(p).is_symlink() for p in markers),
         'PREEXISTING_RESTART_MARKER')
    direct = run([str(installed_root / SERVICE_REL), 'status'])
    need(direct.returncode == 1 and direct.stdout.strip() ==
         'zapret is not running', 'DIRECT_SERVICE_NOT_STOPPED')
    stdout(['/usr/local/sbin/configctl', 'system', 'status'], 'CONFIGD_NOT_READY')
    action = stdout(['/usr/local/sbin/configctl', 'zapret', 'status'],
                    'PACKAGED_CONFIGCTL_STATUS_FAILED')
    need(action == direct.stdout.strip(), 'CONFIGCTL_STATUS_OUTPUT_DIFFERENT')
    after = run([str(installed_root / SERVICE_REL), 'status'])
    need(after.returncode == direct.returncode and after.stdout == direct.stdout,
         'DIRECT_STATUS_CHANGED')
    need(watcher.snapshot() == before, 'CONFIGD_WORKER_ROTATED')
    need(hashlib.sha256(config.read_bytes()).digest() == config_before,
         'CONFIG_CHANGED')
    need(all(not Path(p).exists() and not Path(p).is_symlink() for p in markers),
         'RESTART_MARKER_CREATED')
    return {'schema': 1, 'status': 'PASS_REAL_INSTALLED_CONFIGCTL_STATUS_READONLY',
            'package': PACKAGE + '-' + VERSION,
            'action_sha256': hashlib.sha256(installed).hexdigest(),
            'pkg_owned_action_bytes_match_source': True,
            'configd_process_identity_stable': True,
            'configctl_status': action, 'direct_status_exit': 1,
            'config_unchanged': True, 'restart_markers_absent': True,
            'start_stop_restart_executed': False, 'worker_signals_sent': False,
            'worker_reload_verified': False, 'race_safe_signal_proven': False,
            'pkg_hook_order_verified': False, 'owner_appliance_modified': False}


def main():
    try:
        result = verify()
    except (Refusal, OSError, ValueError, UnicodeError) as exc:
        print('STAGE2_PACKAGED_CONFIGCTL=REFUSED:' + str(exc), file=sys.stderr)
        return 2
    print('STAGE2_PACKAGED_CONFIGCTL=' + json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
