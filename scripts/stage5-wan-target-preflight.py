#!/usr/bin/env python3
"""Read-only, no-target-traffic installed OPNsense WAN Exclude target preflight.

This is not an A07/A08 acceptance test: no TLS probe, PCAP, Apply or IPFW
mutation. Authoritative native owner evidence and native profile parsing are
reused, not recreated. DNS-only resolution is bounded in a subprocess.
"""
from __future__ import annotations

import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import platform
import re
import socket
import stat
import subprocess
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
BRIDGE = SCRIPT_DIR / 'stage5-installed-evidence.py'
INSTALLED_BACKEND = Path('/usr/local/opnsense/scripts/OPNsense/Zapret/backend')
RUNTIME = Path('/usr/local/etc/zapret2/runtime-v2')
MANAGED = RUNTIME / 'managed'
ARGS = RUNTIME / 'dvtws.args'
EXPECTED_VERSION = '0.6.1_12'
DOMAINS = ('yt3.ggpht.com', 'play.google.ru', 'zyro.com')
HOSTLISTS = ('hostlist-user.txt', 'hostlist-youtube.txt')
VOICE_LISTS = ('telegram', 'discord', 'x', 'sip', 'custom')
MAX_HOSTLIST_BYTES = 12 * 1024 * 1024
MAX_HOSTLIST_LINES = 250000
MAX_IPSET_BYTES = 262144
MAX_PROFILE_BYTES = 262144
MAX_DNS_ADDRESSES = 8
MAX_RESULTS = 4
EXPECTED_EXCLUDE_TOKEN = '--ipset-exclude=' + str(MANAGED / 'ipset-exclude.txt')
DNS_CHILD = (
    'import json,socket,sys; '
    'rows=socket.getaddrinfo(sys.argv[1],443,socket.AF_UNSPEC,socket.SOCK_STREAM); '
    'print(json.dumps(sorted(set(r[4][0] for r in rows))))'
)


class PreflightError(ValueError):
    pass


def safe_read(path: Path, limit: int) -> str:
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or not 0 <= info.st_size <= limit:
            raise PreflightError('unsafe or oversized file: ' + path.name)
        data = path.read_bytes()
        if len(data) > limit or b'\x00' in data:
            raise PreflightError('untrusted file bytes: ' + path.name)
        return data.decode('utf-8')
    except (OSError, UnicodeError) as error:
        raise PreflightError('missing or invalid file: ' + path.name) from error


def hostlist_hits(content: str, domain: str) -> bool:
    lines = content.splitlines()
    if len(lines) > MAX_HOSTLIST_LINES:
        raise PreflightError('too many HOSTLIST entries')
    for raw in lines:
        entry = raw.strip().lower()
        if not entry or entry.startswith('#'):
            continue
        # Candidate proof deliberately accepts only exact or parent domains.
        if entry == domain or domain.endswith('.' + entry):
            return True
    return False


def parse_networks(text: str, name: str) -> list[ipaddress._BaseNetwork]:
    lines = text.splitlines()
    if len(lines) > 4096:
        raise PreflightError('too many IPSET entries: ' + name)
    result = []
    for raw in lines:
        token = raw.strip()
        if not token:
            continue
        if token.startswith('#') or '%' in token:
            raise PreflightError('invalid managed IPSET entry: ' + name)
        try:
            network = ipaddress.ip_network(token, strict=True)
        except ValueError as error:
            raise PreflightError('invalid managed IPSET entry: ' + name) from error
        if network.prefixlen == 0 or (network.version == 6 and network.network_address.ipv4_mapped):
            raise PreflightError('unsafe managed IPSET scope: ' + name)
        result.append(network)
    for family in (4, 6):
        members = [n for n in result if n.version == family]
        if any(n.prefixlen == 0 for n in ipaddress.collapse_addresses(members)):
            raise PreflightError('effective full-family IPSET: ' + name)
    return result


def matches(ip: ipaddress._BaseAddress, nets: list[ipaddress._BaseNetwork]) -> bool:
    return any(ip in network for network in nets if network.version == ip.version)


def native_parser():
    if not INSTALLED_BACKEND.is_dir():
        raise PreflightError('installed production profile parser unavailable')
    sys.path.insert(0, str(INSTALLED_BACKEND))
    try:
        from global_exclusions import segments, templates_and_imports, inherited, visible
    except ImportError as error:
        raise PreflightError('native production profile parser cannot load') from error
    return segments, templates_and_imports, inherited, visible


def profile_summary(text: str, parser) -> list[dict]:
    segments, templates_and_imports, inherited, visible = parser
    rows = segments(text)
    templates, kinds = templates_and_imports(rows)
    executable = []
    for row, kind in zip(rows, kinds):
        if kind != 'profile':
            continue
        effective = inherited(visible(row), templates)
        if row.count(EXPECTED_EXCLUDE_TOKEN) != 1:
            raise PreflightError('global Exclude is missing/duplicated in final profile')
        num = len(executable) + 1
        tcp = [x.partition('=')[2] for x in effective if x.startswith('--filter-tcp=')]
        l7 = [x.partition('=')[2].split(',') for x in effective if x.startswith('--filter-l7=')]
        host_refs = [x.partition('=')[2] for x in effective if x.startswith('--hostlist=')]
        restricted = any(x.startswith(('--ipset=', '--ipset-ip=', '--filter-l3=ipv6', '--name=voice-')) for x in effective)
        tls = '443' in tcp and any('tls' in t for t in l7)
        refs = tuple(x for x in host_refs if x in (str(MANAGED / y) for y in HOSTLISTS))
        family_flags = [x.partition('=')[2].split(',') for x in effective
                        if x.startswith('--filter-l3=')]
        families = ('ipv4', 'ipv6') if not family_flags else tuple(
            f for f in ('ipv4', 'ipv6') if all(f in flags for flags in family_flags))
        executable.append({'index': num, 'tls_443': tls, 'ordinary': not restricted,
                           'hostlists': refs, 'families': families})
    if not executable:
        raise PreflightError('no final executable profiles')
    return executable


def resolve(domain: str) -> list[ipaddress._BaseAddress]:
    """DNS traffic only; no HTTP, TLS or target packets; hard wall-clock limit."""
    p = subprocess.run(['/usr/local/bin/python3.13', '-c', DNS_CHILD, domain],
                       capture_output=True, text=True, timeout=8, check=False)
    if p.returncode != 0 or len(p.stdout) > 16384:
        return []
    try:
        values = json.loads(p.stdout)
        if not isinstance(values, list) or len(values) > 128:
            return []
        ips = sorted(set(ipaddress.ip_address(x) for x in values),
                     key=lambda x: (x.version, int(x)))
        return [ip for ip in ips if ip.is_global][:MAX_DNS_ADDRESSES]
    except (ValueError, TypeError):
        return []


def route(ip: ipaddress._BaseAddress) -> dict:
    args = ['/sbin/route'] + (['-6'] if ip.version == 6 else []) + ['-n', 'get', str(ip)]
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=8, check=False)
    except subprocess.TimeoutExpired:
        return {'status': 'ROUTE_UNAVAILABLE'}
    if p.returncode:
        return {'status': 'ROUTE_UNAVAILABLE'}
    found = re.search(r'(?m)^\s*interface:\s*([a-zA-Z][a-zA-Z0-9_.:-]{0,63})\s*$', p.stdout)
    return {'status': 'ROUTE_PRESENT', 'interface': found.group(1)} if found else {'status': 'ROUTE_UNVERIFIED'}


def native_snapshot() -> dict:
    spec = importlib.util.spec_from_file_location('stage5_installed_evidence', BRIDGE)
    if spec is None or spec.loader is None:
        raise PreflightError('installed native evidence bridge unavailable')
    bridge = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bridge)
    import io
    from contextlib import redirect_stdout
    out = io.StringIO()
    with redirect_stdout(out):
        if bridge.collect() != 0:
            raise PreflightError('production native owner is not ready')
    try:
        snap = bridge._parse_snapshot(out.getvalue().encode(), 'WAN target')
    except (ValueError, UnicodeError) as error:
        raise PreflightError('native owner snapshot unverified') from error
    if snap['installed_plugin_version'] != EXPECTED_VERSION:
        raise PreflightError('installed package version differs from tested candidate')
    return snap


def classify(snapshot: dict, profiles: list[dict], hostlists: dict[str, str],
             excludes: list[ipaddress._BaseNetwork], voice: dict[str, list[ipaddress._BaseNetwork]],
             resolver=resolve, route_lookup=route, domains=DOMAINS) -> dict:
    result = {
        'status': 'READ_ONLY_CANDIDATE_PREFLIGHT',
        'installed_version': snapshot['installed_plugin_version'],
        'native_owner_ready': snapshot['state'] == 'ready',
        'executable_profiles': len(profiles),
        'candidates': [],
        'a07_installed_acceptance': 'OPEN', 'a08_installed_acceptance': 'OPEN',
        'ipv6_packet_proven': False, 'exclude_packet_proven': False,
        'baseline_modification_proven': False, 'packet_flow_attributed': False,
        'note': 'DNS queries and FIB lookups only. No target probes, packets captured, IPFW/Config/service writes or GUI Apply. A selected candidate does not prove strategy selection/modification.',
    }
    configured_wans = {record.get('wan') for record in snapshot.get('runtime', {}).get('services', {}).values()
                       if record.get('configured') and isinstance(record.get('wan'), str)}
    for domain in tuple(domains)[:3]:
        if not re.fullmatch(r'[a-z0-9-]+(?:\.[a-z0-9-]+)+', domain):
            raise PreflightError('invalid bounded domain candidate')
        hits = [str(MANAGED / name) for name, content in hostlists.items() if hostlist_hits(content, domain)]
        relevant = [p for p in profiles if p['ordinary'] and p['tls_443']
                    and any(h in p['hostlists'] for h in hits)]
        if not relevant:
            continue
        resolved = resolver(domain)
        # Retain both eligible families when DNS supplies many A/AAAA records.
        chosen = [ip for ip in resolved if ip.version == 4][:2] + [
            ip for ip in resolved if ip.version == 6][:2]
        for ip in chosen:
            if len(result['candidates']) >= MAX_RESULTS:
                break
            if not isinstance(ip, (ipaddress.IPv4Address, ipaddress.IPv6Address)) or not ip.is_global:
                continue
            if matches(ip, excludes) or any(matches(ip, nets) for nets in voice.values()):
                continue
            ids = [p['index'] for p in relevant if f'ipv{ip.version}' in p.get('families', ('ipv4', 'ipv6'))]
            if not ids:
                continue
            fib = route_lookup(ip)
            if fib.get('status') != 'ROUTE_PRESENT':
                continue
            if configured_wans and fib.get('interface') not in configured_wans:
                continue
            result['candidates'].append({
                'domain': domain, 'remote_ip': str(ip), 'family': f'ipv{ip.version}',
                'protocol': 'tcp', 'destination_port': 443,
                'tls_sni': domain, 'host_identity': domain,
                'wan_interface': fib['interface'],
                'configured_voice_wan_match': (fib['interface'] in configured_wans if configured_wans else None),
                'potential_profile_indexes': ids,
                'voice_ipset_overlap': False, 'exclude_ipset_overlap': False,
                'source_ip': None, 'source_port': None,
                'flow_five_tuple_proven': False, 'strategy_modification_proven': False,
                'qualification': 'POTENTIAL_ONLY',
            })
        if len(result['candidates']) >= MAX_RESULTS:
            break
    result['selection'] = 'CANDIDATE_ONLY' if result['candidates'] else 'NO_ELIGIBLE_CONTROL_FOUND'
    return result


def main() -> int:
    if platform.system() != 'FreeBSD' or os.geteuid() != 0 or not INSTALLED_BACKEND.is_dir():
        raise PreflightError('only an explicitly installed OPNsense root may collect')
    snapshot = native_snapshot()
    profiles = profile_summary(safe_read(ARGS, MAX_PROFILE_BYTES), native_parser())
    hostlists = {name: safe_read(MANAGED / name, MAX_HOSTLIST_BYTES) for name in HOSTLISTS}
    excludes = parse_networks(safe_read(MANAGED / 'ipset-exclude.txt', MAX_IPSET_BYTES), 'exclude')
    voice = {name: parse_networks(safe_read(MANAGED / f'ipset-{name}.txt', MAX_IPSET_BYTES), name)
             for name in VOICE_LISTS}
    print(json.dumps(classify(snapshot, profiles, hostlists, excludes, voice), sort_keys=True))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (PreflightError, OSError, subprocess.TimeoutExpired, ValueError) as error:
        print('WAN_TARGET_PREFLIGHT=UNVERIFIED: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
