#!/usr/bin/env python3
"""Real packaged configctl start/stop/restart/reconfigure on disposable OPNsense.

Runs on the SAME VM, immediately after the genuine installed direct service
lifecycle has ended STOPPED. Never exercises a Web GUI click, reboot, WAN,
common Voice Apply, or any owner device.
"""
import configparser
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ACTION_REL = Path('opnsense/service/conf/actions.d/actions_zapret.conf')
ACTION = Path('/usr/local') / ACTION_REL
CONFIGCTL = '/usr/local/sbin/configctl'
OPTIN = 'ZAPRET2_STAGE2_REAL_ACTIVE_CONFIGCTL'
ACTIONS = ('start', 'restart', 'reconfigure', 'stop')
SERVICE = '/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh'


def load_active():
    path = HERE / 'stage2-opnsense-real-native-active-service.py'
    spec = importlib.util.spec_from_file_location('stage2_real_active', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


active = load_active()
Refusal = active.Refusal
need = active.need


def expected_action(name):
    return SERVICE + ' ' + name + ('; exit 0' if name == 'status' else '')


def inspect_bindings(raw):
    try:
        ini = configparser.ConfigParser(interpolation=None, delimiters=(':',),
                                        strict=True)
        ini.read_string(raw.decode('utf-8'))
    except (UnicodeError, configparser.Error) as exc:
        raise Refusal('INSTALLED_CONFIGCTL_ACTION_PARSE_INVALID:' +
                      type(exc).__name__) from None
    for name in (*ACTIONS, 'status'):
        need(name in ini, 'INSTALLED_CONFIGCTL_ACTION_MISSING:' + name)
        fields = ini[name]
        need(fields.get('command') == expected_action(name),
             'INSTALLED_CONFIGCTL_ACTION_COMMAND_CHANGED:' + name)
        need(fields.get('parameters') == '',
             'INSTALLED_CONFIGCTL_UNEXPECTED_PARAMETERS:' + name)
        need(fields.get('type') ==
             ('script_output' if name == 'status' else 'script'),
             'INSTALLED_CONFIGCTL_ACTION_TYPE_CHANGED:' + name)
    return True


def preflight():
    need(os.environ.get(OPTIN) == '1',
         'REAL_INSTALLED_CONFIGCTL_CI_OPTIN_REQUIRED')
    engine_sha = active.guest_preflight()  # Exact source SHA, VM, pkg, lo0.
    need(ACTION.is_file() and not ACTION.is_symlink() and
         ACTION.stat().st_size <= 65536,
         'INSTALLED_CONFIGCTL_ACTION_NOT_REGULAR')
    source = ROOT / 'src' / ACTION_REL
    need(source.is_file() and not source.is_symlink() and
         ACTION.read_bytes() == source.read_bytes(),
         'INSTALLED_CONFIGCTL_ACTION_NOT_SOURCE_BYTES')
    owner = active.required(['pkg', 'which', '-q', str(ACTION)],
                            'INSTALLED_CONFIGCTL_ACTION_PKG_OWNER_UNKNOWN')
    package = active.PACKAGE
    version = active.qualified_revision()
    need(owner in (package, package + '-' + version),
         'INSTALLED_CONFIGCTL_ACTION_NOT_PKG_OWNED')
    inspect_bindings(ACTION.read_bytes())
    ready = active.cmd([CONFIGCTL, 'system', 'status'], timeout=35)
    need(ready.returncode == 0, 'INSTALLED_CONFIGD_NOT_READY')
    return engine_sha


def invoke(name):
    need(name in (*ACTIONS, 'status'), 'UNKNOWN_CONFIGCTL_ACTION')
    return active.cmd([CONFIGCTL, 'zapret', name], timeout=180)


def check_status(expected_running, pid=None):
    via = invoke('status')
    direct = active.action('status')
    need(via.returncode == 0 and direct.stdout.strip() == via.stdout.strip(),
         'CONFIGCTL_STATUS_DIFFERENT_FROM_REAL_SERVICE')
    # Real launcher_status reports the exact PID, not just "running".
    # Bind configctl output to the independently verified dvtws2 process.
    if expected_running:
        need(isinstance(pid, int) and pid > 1 and
             via.stdout.strip() == 'zapret is running as pid ' + str(pid),
             'CONFIGCTL_RUNNING_PID_OR_STATUS_MISMATCH:' + repr(via.stdout.strip()))
    else:
        need(pid is None and via.stdout.strip() == 'zapret is not running',
             'CONFIGCTL_STOPPED_STATUS_MISMATCH:' + repr(via.stdout.strip()))
    return via.stdout.strip()


def cycle(invoke_action, live, stopped, saved, check, engine_sha):
    original = saved()
    stopped()
    check(False, None)
    transitions = []
    previous_pid = None
    for name in ('start', 'restart', 'reconfigure'):
        outcome = invoke_action(name)
        need(outcome.returncode == 0,
             'REAL_CONFIGCTL_' + name.upper() + '_FAILED:rc=' +
             str(outcome.returncode) + ':' +
             (outcome.stdout + outcome.stderr)[-260:])
        state = live(engine_sha)
        need(previous_pid is None or state['pid'] != previous_pid,
             'REAL_CONFIGCTL_' + name.upper() + '_PID_NOT_REPLACED')
        previous_pid = state['pid']
        check(True, state['pid'])
        need(saved() == original,
             'REAL_CONFIGCTL_' + name.upper() + '_CHANGED_CONFIG')
        transitions.append(name)
    outcome = invoke_action('stop')
    need(outcome.returncode == 0, 'REAL_CONFIGCTL_STOP_FAILED:rc=' +
         str(outcome.returncode) + ':' +
         (outcome.stdout + outcome.stderr)[-260:])
    stopped()
    check(False, None)
    need(saved() == original, 'REAL_CONFIGCTL_STOP_CHANGED_CONFIG')
    transitions.append('stop')
    return {'schema': 1, 'status': 'PASS_REAL_INSTALLED_CONFIGCTL_ACTIVE_SERVICE',
            'actions': transitions, 'configctl_status_running_and_stopped': True,
            'real_dvtws2_pids_replaced': True, 'single_loopback_ipfw_rule': True,
            'saved_config_unchanged': True, 'installed_actions_pkg_owned': True,
            'common_voice_apply_tested': False, 'web_gui_click_tested': False,
            'reboot_tested': False, 'owner_appliance_modified': False}


def main():
    try:
        digest = preflight()
        result = cycle(invoke, active.live_state, active.stopped_state,
                       lambda: active.CONFIG.read_bytes(), check_status, digest)
        need(all(not p.exists() and not p.is_symlink() for p in active.OWNER_MARKERS),
             'PACKAGE_RESTART_MARKERS_CREATED_BY_CONFIGCTL')
    except (Refusal, OSError, ValueError, UnicodeError) as exc:
        print('STAGE2_REAL_ACTIVE_CONFIGCTL=REFUSED:' + str(exc), file=sys.stderr)
        return 2
    print('STAGE2_REAL_ACTIVE_CONFIGCTL=' + json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
