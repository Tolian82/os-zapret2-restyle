#!/usr/bin/env python3
"""Installed real dvtws2 lifecycle on the existing disposable lo0 upgrade VM.

Run only after stage2-opnsense-real-native-running-upgrade.py has returned PASS.
No WAN interception, new IPFW ownership subsystem, boot or shared Voice Apply.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'os-zapret2-restyle'
SERVICE = Path('/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh')
ENGINE = Path('/usr/local/etc/zapret2/binaries/my/dvtws2')
CONFIG = Path('/conf/config.xml')
PID = Path('/var/run/dvtws2.pid')
SUPERVISOR_PIDS = (Path('/var/run/zapret2-supervisor-daemon.pid'),
                   Path('/var/run/zapret2-supervisor-monitor.pid'))
OWNER_MARKERS = (Path('/var/run/zapret2-restyle/pkg-upgrade.restart'),
                 Path('/var/run/zapret2-restyle/pkg-replacement.restart'))
LOOPBACK_PORT = 65431
OPTIN = 'ZAPRET2_STAGE2_REAL_ACTIVE_SERVICE'


class Refusal(RuntimeError):
    pass


def need(ok, message):
    if not ok:
        raise Refusal(message)


def cmd(argv, env=None, timeout=150):
    try:
        return subprocess.run(argv, capture_output=True, text=True,
                              check=False, timeout=timeout, env=env)
    except (OSError, subprocess.SubprocessError):
        raise Refusal('COMMAND_UNAVAILABLE_OR_TIMEOUT:' + str(argv[0])) from None


def required(argv, reason):
    p = cmd(argv, timeout=30)
    need(p.returncode == 0, reason + ':rc=' + str(p.returncode))
    return p.stdout.strip()


def installed_guest_identity():
    # This runs AFTER the real native pkg upgrade; the fresh-guest predicate
    # correctly rejects this state and must never be reused post-install.
    need(required(['opnsense-version', '-a'], 'OPNSENSE_VERSION_UNAVAILABLE') ==
         '26.7', 'INSTALLED_GUEST_OPNSENSE_ABI_UNQUALIFIED')
    need(required(['pkg', 'config', 'ABI'], 'PKG_ABI_UNAVAILABLE') ==
         'FreeBSD:15:amd64', 'INSTALLED_GUEST_PKG_ABI_UNQUALIFIED')
    need(required(['sysctl', '-n', 'kern.vm_guest'], 'VM_IDENTITY_UNAVAILABLE').lower()
         not in ('', 'none', 'unknown'), 'INSTALLED_TARGET_NOT_VIRTUAL_GUEST')


def qualified_revision():
    version = (ROOT / 'VERSION').read_text().strip()
    match = re.search(r'(?m)^PLUGIN_REVISION=\s*(\d+)\s*$',
                      (ROOT / 'Makefile').read_text())
    need(match is not None, 'CANDIDATE_REVISION_MISSING')
    return version + '_' + match.group(1)


def guest_preflight():
    need(os.environ.get('GITHUB_ACTIONS') == 'true' and
         os.environ.get('ZAPRET2_NATIVE_BUILD_CI') == '1' and
         os.environ.get('ZAPRET2_STAGE0_DISPOSABLE_RUNNING_TEST') == '1' and
         os.environ.get('ZAPRET2_STAGE2_REAL_RUNNING_UPGRADE') == '1' and
         os.environ.get(OPTIN) == '1', 'DISPOSABLE_RUNNING_CI_OPTIN_REQUIRED')
    need(os.geteuid() == 0 and os.uname().sysname == 'FreeBSD' and
         os.uname().machine == 'amd64', 'NOT_FREEBSD_AMD64_ROOT')
    installed_guest_identity()
    expect = os.environ.get('ZAPRET2_NATIVE_PROJECT_SHA', '')
    need(re.fullmatch(r'[a-f0-9]{40}', expect) is not None and
         expect == os.environ.get('ZAPRET2_STAGE0_PROJECT_SHA') and
         required(['git', '-c', 'safe.directory=' + str(ROOT), '-C', str(ROOT),
                   'rev-parse', 'HEAD'], 'EXACT_GIT_SOURCE_UNAVAILABLE') == expect,
         'EXACT_SOURCE_SHA_MISMATCH')
    need(required(['pkg', 'query', '%v', PACKAGE], 'INSTALLED_PKG_UNAVAILABLE') ==
         qualified_revision(), 'INSTALLED_NATIVE_PKG_REVISION_MISMATCH')
    source = ROOT / 'src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh'
    need(SERVICE.is_file() and not SERVICE.is_symlink() and
         SERVICE.read_bytes() == source.read_bytes(),
         'INSTALLED_SERVICE_NOT_CURRENT_SOURCE')
    python = SERVICE.with_name('python_runtime.sh')
    need(python.is_file() and not python.is_symlink() and
         cmd([str(python), '--check']).returncode == 0,
         'QUALIFIED_INSTALLED_PYTHON_UNAVAILABLE')
    need(ENGINE.is_file() and not ENGINE.is_symlink() and os.access(ENGINE, os.X_OK),
         'REAL_UPSTREAM_ENGINE_NOT_PRESENT')
    need(CONFIG.is_file() and not CONFIG.is_symlink(), 'SAVED_CONFIG_UNTRUSTED')
    root = ET.fromstring(CONFIG.read_bytes())
    general = root.find('./OPNsense/Zapret/general')
    strategy = root.find('./OPNsense/Zapret/strategy')
    need(general is not None and strategy is not None and
         general.findtext('enabled') == '1' and
         general.findtext('waninterface') == 'lo0' and
         general.findtext('ports') == str(LOOPBACK_PORT) and
         general.findtext('divertport') == '989' and
         '--filter-tcp=' + str(LOOPBACK_PORT) in
         (strategy.findtext('trafficargs') or ''),
         'NOT_THE_EXACT_LOOPBACK_ONLY_TEST_PROFILE')
    for marker in OWNER_MARKERS:
        need(not marker.exists() and not marker.is_symlink(),
             'STALE_PACKAGE_RESTART_MARKER:' + str(marker))
    return hashlib.sha256(ENGINE.read_bytes()).hexdigest()


def action(name, python_down=False):
    env = None
    if python_down:
        env = dict(os.environ)
        env['PYTHON_RUNTIME'] = '/nonexistent/zapret2-qualified-python-test'
    return cmd([str(SERVICE), name], env=env)


def plugin_rules():
    p = cmd(['/sbin/ipfw', '-q', 'list'], timeout=20)
    need(p.returncode == 0, 'IPFW_NOT_AVAILABLE_DURING_REAL_RUNNING_TEST')
    return [line for line in p.stdout.splitlines()
            if re.match(r'^190(?:0\d|10)\s', line)]


def live_state(expected_engine_sha):
    status = action('status')
    need(status.returncode == 0 and 'zapret is running' in status.stdout,
         'INSTALLED_SERVICE_NOT_RUNNING:' + str(status.returncode))
    need(PID.is_file() and not PID.is_symlink(), 'ENGINE_PID_NOT_REGULAR')
    value = PID.read_text().strip()
    need(value.isdecimal() and int(value) > 1, 'RUNNING_ENGINE_PID_INVALID')
    pid = int(value)
    proc = cmd(['/bin/ps', '-p', str(pid), '-o', 'command='], timeout=20)
    need(proc.returncode == 0 and proc.stdout.strip().split(' ')[0] == str(ENGINE),
         'ENGINE_PID_NOT_BOUND_TO_REAL_EXECUTABLE')
    need(hashlib.sha256(ENGINE.read_bytes()).hexdigest() == expected_engine_sha,
         'REAL_UPSTREAM_ENGINE_BYTES_CHANGED')
    rules = plugin_rules()
    need(len(rules) == 1 and rules[0].startswith('19000 ') and
         'divert 989' in rules[0] and str(LOOPBACK_PORT) in rules[0] and
         'lo0' in rules[0], 'NOT_EXACT_SINGLE_LOOPBACK_DIVERT_OWNER')
    need(all(not p.exists() and not p.is_symlink() for p in OWNER_MARKERS),
         'PACKAGE_RESTART_MARKER_REAPPEARED')
    return {'pid': pid, 'rules': rules}


def stopped_state():
    status = action('status')
    need(status.returncode == 1 and status.stdout.strip() == 'zapret is not running',
         'INSTALLED_SERVICE_STOP_STATUS_FALSE')
    need(not plugin_rules(), 'STOP_LEFT_PLUGIN_RULES')
    for p in (PID, *SUPERVISOR_PIDS):
        need(not p.exists() and not p.is_symlink(),
             'STOP_LEFT_OWNED_PIDFILE:' + str(p))
    return True


def cycle(invoke, live, stopped, saved, expected_engine_sha):
    before = saved()
    old = live(expected_engine_sha)
    transitions = []
    for operation in ('reconfigure', 'restart'):
        p = invoke(operation)
        need(p.returncode == 0, 'REAL_' + operation.upper() + '_FAILED:rc=' +
             str(p.returncode) + ':' + (p.stdout + p.stderr)[-240:])
        new = live(expected_engine_sha)
        need(new['pid'] != old['pid'], 'REAL_' + operation.upper() + '_DID_NOT_REPLACE_PID')
        need(saved() == before, 'REAL_' + operation.upper() + '_CHANGED_SAVED_CONFIG')
        transitions.append(operation)
        old = new
    p = invoke('stop')
    need(p.returncode == 0, 'REAL_STOP_FAILED:rc=' + str(p.returncode))
    stopped()
    need(saved() == before, 'REAL_STOP_CHANGED_SAVED_CONFIG')
    transitions.append('stop')
    p = invoke('start')
    need(p.returncode == 0, 'REAL_START_AFTER_STOP_FAILED:rc=' + str(p.returncode))
    old = live(expected_engine_sha)
    need(saved() == before, 'REAL_START_CHANGED_SAVED_CONFIG')
    transitions.append('start')
    for operation in ('restart', 'reconfigure'):
        p = invoke(operation, python_down=True)
        need(p.returncode == 69 and not p.stdout.strip() and
             'python' in p.stderr.lower(),
             'PYTHON_DOWN_' + operation.upper() + '_NOT_REFUSED_BEFORE_MUTATION')
        need(live(expected_engine_sha) == old and saved() == before,
             'PYTHON_DOWN_' + operation.upper() + '_CHANGED_RUNNING_OWNER')
    p = invoke('stop', python_down=True)
    need(p.returncode == 0, 'VERIFIED_PYTHON_DOWN_STOP_FAILED:rc=' +
         str(p.returncode) + ':' + (p.stdout + p.stderr)[-240:])
    stopped()
    need(saved() == before, 'PYTHON_DOWN_STOP_CHANGED_SAVED_CONFIG')
    return {'schema': 1, 'status': 'PASS_REAL_INSTALLED_ACTIVE_ORDINARY_SERVICE',
            'actions': transitions, 'python_down_restart_reconfigure_refused': True,
            'python_down_verified_ordinary_stop': True,
            'config_retained': True, 'loopback_only': True,
            'shared_voice_owner_tested': False, 'web_gui_apply_tested': False,
            'actual_reboot_tested': False, 'owner_appliance_modified': False}


def main():
    try:
        engine_sha = guest_preflight()
        report = cycle(action, live_state, stopped_state,
                       lambda: CONFIG.read_bytes(), engine_sha)
    except (Refusal, OSError, ValueError, KeyError, ET.ParseError) as exc:
        print('STAGE2_REAL_ACTIVE_SERVICE=REFUSED:' + str(exc), file=sys.stderr)
        return 2
    print('STAGE2_REAL_ACTIVE_SERVICE=' + json.dumps(report, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
