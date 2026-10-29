#!/usr/bin/env python3
"""One-shot read-only installed OPNsense Stage-5 IPv6 eligibility preflight.

Never changes Config, IPFW, running services, routes, or any packet bytes.
It delegates ownership attestation to the existing native Voice inspector via
stage5-installed-evidence.collect(). A route lookup alone is NOT IPv6 proof.
"""
from __future__ import annotations

from contextlib import redirect_stdout
import importlib.util
import io
import ipaddress
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys

BRIDGE = Path(__file__).with_name('stage5-installed-evidence.py')
MANAGED = Path('/usr/local/etc/zapret2/runtime-v2/managed')
SERVICES = ('telegram', 'discord', 'x', 'sip', 'custom')
MAX_FILE = 262144
MAX_LINES = 4096
ROUTE = '/sbin/route'


class PreflightError(ValueError):
    pass


def load_bridge():
    spec = importlib.util.spec_from_file_location('stage5_installed_evidence', BRIDGE)
    if spec is None or spec.loader is None:
        raise PreflightError('existing Stage-5 installed inspector bridge is missing')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def collect_native(bridge) -> dict:
    # Existing collect() checks root/FreeBSD, exact installed pkg version,
    # original production inspector and committed owner/runtime/IPFW witnesses.
    output = io.StringIO()
    try:
        with redirect_stdout(output):
            if bridge.collect() != 0:
                raise PreflightError('native Stage-5 inspector refused the installed state')
        snapshot = json.loads(output.getvalue())
        return bridge._parse_snapshot(json.dumps(snapshot).encode(), 'one-shot')
    except (ValueError, UnicodeError, OSError, subprocess.TimeoutExpired) as error:
        raise PreflightError('native Stage-5 owner evidence was not attested') from error


def networks(path: Path) -> tuple[int, list[ipaddress.IPv6Network]]:
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_FILE:
            raise PreflightError('unsafe Voice IPSET file: ' + path.name)
        raw = path.read_bytes()
        if len(raw) > MAX_FILE:
            raise PreflightError('oversized Voice IPSET: ' + path.name)
        rows = raw.decode('utf-8').splitlines()
        if len(rows) > MAX_LINES:
            raise PreflightError('too many Voice IPSET entries: ' + path.name)
        ipv4_count = 0
        ipv6 = []
        for row in rows:
            value = row.strip()
            if not value:
                continue
            if value.startswith('#') or '%' in value:
                raise PreflightError('unexpected managed Voice IPSET value: ' + path.name)
            entry = ipaddress.ip_network(value, strict=True)
            if entry.prefixlen == 0:
                raise PreflightError('unsafe full-family Voice IPSET: ' + path.name)
            if entry.version == 4:
                ipv4_count += 1
            else:
                if entry.network_address.ipv4_mapped:
                    raise PreflightError('unexpected mapped IPv6 target')
                ipv6.append(entry)
        return ipv4_count, ipv6
    except (OSError, UnicodeError, ValueError) as error:
        if isinstance(error, PreflightError):
            raise
        raise PreflightError('invalid managed Voice IPSET: ' + path.name) from error


def eligible_target(prefixes: list[ipaddress.IPv6Network]) -> str | None:
    for prefix in prefixes:
        # A ULA/LL-only IPSET is not a WAN IPv6 eligibility witness.
        host = prefix.network_address
        if prefix.num_addresses > 1:
            host += 1
        if host.is_global:
            return str(host)
    return None


def route_interface(destination: str) -> tuple[str, str | None]:
    # Read-only kernel FIB lookup; does not transmit a probe packet.
    result = subprocess.run([ROUTE, '-6', '-n', 'get', destination],
                            capture_output=True, text=True, timeout=8, check=False)
    if result.returncode:
        return 'ROUTE_UNAVAILABLE', None
    found = re.search(r'(?m)^\s*interface:\s*([^\s]+)\s*$', result.stdout)
    if found is None:
        return 'ROUTE_UNVERIFIED', None
    return 'ROUTE_PRESENT', found.group(1)


def summarize(snapshot: dict, managed: Path = MANAGED) -> dict:
    runtime = snapshot['runtime']
    details = runtime['services']
    report = {
        'status': 'READ_ONLY_PREFLIGHT',
        'installed_version': snapshot['installed_plugin_version'],
        'native_owner': snapshot['state'],
        'engine_verified': runtime['engine_verified'],
        'rule_count': snapshot['rule_count'],
        'table_count': snapshot['table_count'],
        'services': {},
        'stage5_installed_acceptance': 'OPEN',
        'ipv6_packet_proven': False,
        'exclude_packet_proven': False,
        'note': 'No packet sent or altered. Route lookup and IPSET inventory are only prerequisites; installed WAN divert, reinjection, rollback and live Voice remain unverified.',
    }
    for name in SERVICES:
        record = details[name]
        service = {'configured': record['configured'], 'ipv4_entries': 0,
                   'ipv6_entries': 0, 'ipv6_route': 'NOT_CONFIGURED',
                   'wan_match': False}
        if record['configured']:
            wan = record.get('wan')
            if not isinstance(wan, str) or not re.fullmatch(r'[a-z][a-z0-9_.-]{0,31}', wan):
                raise PreflightError('configured Voice WAN is not attested: ' + name)
            ipv4, ipv6 = networks(managed / f'ipset-{name}.txt')
            service['ipv4_entries'] = ipv4
            service['ipv6_entries'] = len(ipv6)
            target = eligible_target(ipv6)
            if target is None:
                service['ipv6_route'] = 'NO_GLOBAL_IPV6_TARGET'
            else:
                state, interface = route_interface(target)
                service['ipv6_route'] = state
                service['wan_match'] = state == 'ROUTE_PRESENT' and interface == wan
                if state == 'ROUTE_PRESENT' and interface != wan:
                    service['ipv6_route'] = 'OTHER_INTERFACE'
        report['services'][name] = service
    return report


def main() -> int:
    if platform.system() != 'FreeBSD' or os.geteuid() != 0:
        raise PreflightError('requires installed OPNsense root; no offline execution')
    snapshot = collect_native(load_bridge())
    print(json.dumps(summarize(snapshot), sort_keys=True))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (PreflightError, OSError, subprocess.TimeoutExpired) as error:
        print('STAGE5_ONESHOT=UNVERIFIED: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
