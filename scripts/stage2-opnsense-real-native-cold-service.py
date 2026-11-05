#!/usr/bin/env python3
"""Genuine installed cold service refusal on disposable OPNsense 26.7.

Runs after the official Mk/pkg clean-install and packaged configctl status gates.
The upstream dvtws2 engine is deliberately absent.  This is NOT a running
Strategies/Voice lifecycle, Web GUI Apply, or reboot acceptance.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'os-zapret2-restyle'
SERVICE = Path('/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh')
PYTHON = SERVICE.with_name('python_runtime.sh')
ENGINE = Path('/usr/local/etc/zapret2/binaries/my/dvtws2')
CONFIG = Path('/conf/config.xml')
MARKERS = [Path(p) for p in (
    '/var/run/dvtws2.pid', '/var/run/zapret2-supervisor-daemon.pid',
    '/var/run/zapret2-supervisor-monitor.pid',
    '/var/run/zapret2-restyle/pkg-upgrade.restart',
    '/var/run/zapret2-restyle/pkg-replacement.restart')]
OPTIN = 'ZAPRET2_STAGE2_REAL_COLD_SERVICE'
ACTIONS = ('start', 'restart', 'reconfigure')


class Refusal(Exception):
    pass


def need(condition, reason):
    if not condition:
        raise Refusal(reason)


def run(argv, timeout=45):
    try:
        return subprocess.run(argv, check=False, capture_output=True,
                              text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        raise Refusal('COMMAND_UNAVAILABLE_OR_TIMEOUT:' + str(argv[0])) from None


def stdout(argv, reason):
    result = run(argv)
    need(result.returncode == 0, reason + ':rc=' + str(result.returncode))
    return result.stdout.strip()


def installed_revision():
    version = (ROOT / 'VERSION').read_text().strip()
    match = re.search(r'(?m)^PLUGIN_REVISION=\s*(\d+)\s*$',
                      (ROOT / 'Makefile').read_text())
    need(match is not None, 'SOURCE_REVISION_MISSING')
    return version + '_' + match.group(1)


def preflight():
    need(os.environ.get('GITHUB_ACTIONS') == 'true' and
         os.environ.get('ZAPRET2_NATIVE_BUILD_CI') == '1' and
         os.environ.get(OPTIN) == '1', 'DISPOSABLE_CI_OPTIN_REQUIRED')
    need(os.geteuid() == 0 and os.uname().sysname == 'FreeBSD' and
         os.uname().machine == 'amd64', 'NOT_FREEBSD_AMD64_ROOT')
    need(stdout(['opnsense-version', '-a'], 'OPNSENSE_VERSION_UNAVAILABLE') ==
         '26.7', 'OPNSENSE_PRODUCT_UNQUALIFIED')
    need(stdout(['pkg', 'config', 'ABI'], 'PKG_ABI_UNAVAILABLE') ==
         'FreeBSD:15:amd64', 'PKG_ABI_UNQUALIFIED')
    need(stdout(['sysctl', '-n', 'kern.vm_guest'], 'VM_IDENTITY_UNAVAILABLE').lower()
         not in ('', 'none', 'unknown'), 'NOT_DISPOSABLE_GUEST')
    source_sha = os.environ.get('ZAPRET2_NATIVE_PROJECT_SHA', '')
    need(bool(re.fullmatch(r'[0-9a-f]{40}', source_sha)) and
         stdout(['git', 'rev-parse', 'HEAD'], 'SOURCE_SHA_UNAVAILABLE') == source_sha,
         'EXACT_PROJECT_SOURCE_SHA_MISMATCH')
    need(stdout(['pkg', 'query', '%v', PACKAGE], 'INSTALLED_PKG_UNAVAILABLE') ==
         installed_revision(), 'INSTALLED_PKG_REVISION_MISMATCH')
    expected = ROOT / 'src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh'
    need(SERVICE.is_file() and not SERVICE.is_symlink() and
         SERVICE.read_bytes() == expected.read_bytes(),
         'INSTALLED_SERVICE_BYTES_NOT_SOURCE')
    need(PYTHON.is_file() and not PYTHON.is_symlink(),
         'INSTALLED_PYTHON_LAUNCHER_MISSING')
    need(run([str(PYTHON), '--check']).returncode == 0,
         'QUALIFIED_INSTALLED_PYTHON_NOT_READY')
    need(CONFIG.is_file() and not CONFIG.is_symlink(), 'CONFIG_NOT_REGULAR')
    need(not ENGINE.exists() and not ENGINE.is_symlink(),
         'UPSTREAM_ENGINE_PRESENT_NOT_COLD_FIXTURE')
    for path in MARKERS:
        need(not path.exists() and not path.is_symlink(),
             'COLD_OWNER_MARKER_PRESENT:' + str(path))


def owned_ipfw_rules():
    """Read only the fixed plugin range; do not load or initialize IPFW."""
    result = run(['/sbin/ipfw', 'list'], timeout=15)
    if result.returncode != 0:
        need(not result.stdout.strip(), 'AMBIGUOUS_IPFW_READ_FAILURE')
        return {'available': False, 'rules': []}
    numbers = []
    for line in result.stdout.splitlines():
        match = re.match(r'^\s*(\d{5})\s', line)
        if match and 19000 <= int(match.group(1)) <= 19010:
            numbers.append(line)
    return {'available': True, 'rules': numbers}


def snapshot():
    need(CONFIG.is_file() and not CONFIG.is_symlink(), 'CONFIG_DISAPPEARED')
    return {'config_sha256': hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
            'runtime_present': ENGINE.exists() or ENGINE.is_symlink(),
            'markers_present': [str(p) for p in MARKERS
                                if p.exists() or p.is_symlink()],
            'ipfw': owned_ipfw_rules()}


def exercise(invoke=run, observe=snapshot):
    baseline = observe()
    need(not baseline['runtime_present'] and not baseline['markers_present']
         and not baseline['ipfw']['rules'], 'COLD_BASELINE_NOT_EMPTY')
    checked = []
    for action in ACTIONS:
        result = invoke([str(SERVICE), action])
        need(result.returncode == 1 and not result.stdout.strip() and
             'runtime is not installed' in result.stderr.lower(),
             'COLD_' + action.upper() + '_DID_NOT_REFUSE_MISSING_ENGINE')
        need(observe() == baseline,
             'COLD_' + action.upper() + '_MUTATED_CONFIG_OWNER_OR_IPFW')
        status = invoke([str(SERVICE), 'status'])
        need(status.returncode == 1 and
             status.stdout.strip() == 'zapret is not running',
             'COLD_' + action.upper() + '_STATUS_CHANGED')
        need(observe() == baseline,
             'COLD_' + action.upper() + '_STATUS_MUTATED_STATE')
        checked.append(action)
    return {'schema': 1, 'status': 'PASS_REAL_INSTALLED_COLD_LIFECYCLE_REFUSAL',
            'actions': checked, 'qualified_python_available': True,
            'runtime_missing': True, 'config_unchanged': True,
            'plugin_ipfw_unchanged': True, 'no_owner_started': True,
            'common_running_owner_tested': False, 'boot_tested': False,
            'web_apply_tested': False, 'owner_device_modified': False}


def main():
    try:
        preflight()
        report = exercise()
    except (Refusal, OSError, ValueError, UnicodeError) as exc:
        print('STAGE2_REAL_COLD_SERVICE=REFUSED:' + str(exc), file=sys.stderr)
        return 2
    print('STAGE2_REAL_COLD_SERVICE=' + json.dumps(report, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
