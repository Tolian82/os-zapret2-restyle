#!/usr/bin/env python3
"""Read-only OPNsense Zapret2 P6 integration probe. No user Config is read.

No Config/IPFW/service/runtime writes, no daemon restarts, no packet traffic,
no user domains/IP addresses or secrets reported. Only synthetic test domains.
"""
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET

MODEL = Path('/usr/local/opnsense/mvc/app/models/OPNsense/Zapret/Zapret.xml')
POLICY = Path('/usr/local/opnsense/scripts/OPNsense/Zapret/backend/domain_policy.py')
RUNNER = Path('/usr/local/opnsense/scripts/OPNsense/Zapret/python_runtime.sh')
WORKER = Path('/usr/local/opnsense/scripts/OPNsense/Zapret/apply_settings.php')
FIELDS = ('youtubedomains', 'userdomains', 'excludedomains',
          'telegramips', 'discordips', 'xips', 'sipips', 'customips', 'excludeipset')


def check(kind, value):
    data = json.dumps({'kind': kind, 'text': value}, ensure_ascii=False)
    res = subprocess.run([str(RUNNER), str(POLICY), 'inspect'], input=data,
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                         text=True, timeout=15, check=False,
                         env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    try:
        out = json.loads(res.stdout)
    except (ValueError, TypeError):
        return False
    return res.returncode == 0 and out.get('normalized') == value


def main():
    if platform.system() != 'FreeBSD':
        print('REFUSED: run on OPNsense/FreeBSD only')
        return 2
    report = {'probe': 'p6-owner-readonly', 'config_read': False,
              'config_written': False, 'service_touched': False,
              'ipfw_touched': False, 'live_domain_data_collected': False}
    try:
        pkg = subprocess.run(['pkg', 'info', '-x', 'os-zapret2-restyle'],
                             capture_output=True, text=True, timeout=10, check=False)
        report['package_identity'] = pkg.stdout.strip() if pkg.returncode == 0 else 'unknown'
        root = ET.parse(MODEL).getroot()
        report['python_governed_masks_absent'] = all(
            (node := root.find('./items/hostlist/' + f)) is not None and
            node.find('Mask') is None for f in FIELDS)
        report['native_ports_retained'] = (
            root.find('./items/general/divertport').attrib.get('type') == 'PortField'
            and root.find('./items/general/ports/Mask') is not None)
        code = WORKER.read_text(encoding='utf-8')
        report['root_python_bridge_present'] = all(
            x in code for x in ('DomainSetPolicyBridge::inspect(',
                                'IPSetPolicyBridge::inspect(',
                                'serializeToConfig(false, true)'))
        report['synthetic_local_modifiers'] = all(check(k, v) for k, v in (
            ('youtube', '!youtube.com'), ('youtube', '^youtube.com'),
            ('youtube', '!^youtube.com'), ('user', '^t.me')))
        report['synthetic_global_exclude_rejects_modifiers'] = not check('exclude', '!example.com')
        report['status'] = ('PASS_READONLY_PRECONDITIONS' if
                            all(report.get(k) is True for k in (
                                'python_governed_masks_absent',
                                'native_ports_retained',
                                'root_python_bridge_present',
                                'synthetic_local_modifiers',
                                'synthetic_global_exclude_rejects_modifiers'))
                            else 'INTEGRATION_PRECONDITION_NOT_MET')
    except (OSError, ET.ParseError, ValueError, subprocess.TimeoutExpired) as error:
        report['status'] = 'PROBE_UNAVAILABLE'
        report['error_type'] = type(error).__name__
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get('status') == 'PASS_READONLY_PRECONDITIONS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
