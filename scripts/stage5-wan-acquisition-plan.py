#!/usr/bin/env python3
"""Generate a bounded two-phase WAN TCP capture plan; never execute it.

No imports or commands here start a capture, network connection, or alter the
OPNsense service, Config, IPFW or routes. Actual execution needs a separate
owner-approved controller with deadline, provenance and restoration guards.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import re
import sys

MIN_PORT = 50000
MAX_PORT = 60999
CAPTURE_PACKETS = 128
CAPTURE_SNAPLEN = 4096
CAPTURE_DEADLINE_SECONDS = 18
CURL_DEADLINE_SECONDS = 12


class PlanError(ValueError):
    pass


def parse_address(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    try:
        return ipaddress.ip_address(value)
    except ValueError as exc:
        raise PlanError('invalid IP address') from exc


def validate(domain: str, target: str, source: str, port: int, wan: str) -> tuple:
    if not isinstance(domain, str) or len(domain) > 253 or not re.fullmatch(
        r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+', domain
    ):
        raise PlanError('invalid ASCII DNS name')
    if not isinstance(wan, str) or not re.fullmatch(r'[a-z][a-z0-9_.-]{0,31}', wan):
        raise PlanError('invalid WAN interface name')
    remote, local = parse_address(target), parse_address(source)
    if not remote.is_global or remote.is_multicast or remote.is_loopback:
        raise PlanError('remote endpoint must be globally routable')
    if remote.version != local.version or local.is_unspecified or local.is_multicast or local.is_loopback:
        raise PlanError('source must be a valid same-family unicast address')
    if type(port) is not int or not MIN_PORT <= port <= MAX_PORT:
        raise PlanError('source port is outside reserved trial range')
    if remote == local:
        raise PlanError('source and destination must differ')
    return remote, local


def plan(domain: str, remote_ip: str, source_ip: str, source_port: int, wan: str) -> dict:
    remote, source = validate(domain, remote_ip, source_ip, source_port, wan)
    # The BPF must keep the direction and 5-tuple. This captures inbound
    # replies too, but not a different source port to the same destination.
    outbound = (f'(src host {source} and src port {source_port} and '
                f'dst host {remote} and dst port 443)')
    inbound = (f'(src host {remote} and src port 443 and '
               f'dst host {source} and dst port {source_port})')
    bpf = f'tcp and ({outbound} or {inbound})'
    resolve = f'{domain}:443:{"[" + str(remote) + "]" if remote.version == 6 else remote}'
    manifest = {
        'schema_version': 1, 'domain': domain, 'remote_ip': str(remote),
        'wan_interface': wan,
        'baseline': {'source_ip': str(source), 'source_port': source_port},
        'excluded': {'source_ip': str(source), 'source_port': source_port},
    }
    phases = {}
    for phase in ('baseline', 'excluded'):
        phases[phase] = {
            'capture_argv': [
                '/usr/sbin/tcpdump', '-i', wan, '-nn', '-s', str(CAPTURE_SNAPLEN),
                '-c', str(CAPTURE_PACKETS), '-w', f'{phase}.pcap', bpf,
            ],
            'probe_argv': [
                '/usr/local/bin/curl', '-4' if remote.version == 4 else '-6',
                '--noproxy', '*', '--interface', f'host!{source}',
                '--local-port', str(source_port), '--resolve', resolve,
                '--http1.1', '--head', '--silent', '--show-error',
                '--retry', '0', '--connect-timeout', '5', '--max-time', str(CURL_DEADLINE_SECONDS),
                '--output', '/dev/null', f'https://{domain}/',
            ],
            'capture_deadline_seconds': CAPTURE_DEADLINE_SECONDS,
            'max_packets': CAPTURE_PACKETS,
            'max_snaplen_bytes': CAPTURE_SNAPLEN,
            'capture_format_requirement': 'classic-ethernet-pcap-DLT_EN10MB',
            'capture_source_proven': False,
            'probe_executed': False,
        }
    return {
        'status': 'PLAN_ONLY_UNEXECUTED',
        'analysis_manifest': manifest,
        'phases': phases,
        'strict_sequence': [
            'owner-approved preflight and interface/linktype/source-address validation',
            'start bounded baseline capture; execute exactly one baseline request; stop capture',
            'independently attest actual strategy baseline modification before GUI edit',
            'owner-approved normal GUI Apply of one Exclude IPSET destination',
            'start bounded excluded capture; execute one identical request; stop capture',
            'owner-approved normal GUI restoration and Config/owner/IPFW health attestation',
            'offline five-tuple PCAP attribution, classify A07/A08 as OPEN until independent proof',
        ],
        'owner_live_authorization': False,
        'executed': False,
        'route_verified': False,
        'source_ip_owned_by_wan_verified': False,
        'source_port_free_verified': False,
        'engine_profile_selected_verified': False,
        'baseline_dpi_modification_verified': False,
        'exclude_effect_verified': False,
        'wan_pcap_proven': False,
        'gui_apply_and_restore_executed': False,
        'installed_a07': 'OPEN',
        'installed_a08': 'OPEN',
        'caution': 'COMMAND ARGUMENTS ARE A REVIEW PLAN, NOT INSTRUCTIONS TO EXECUTE. '
                   'Never run these commands on OPNsense without explicit owner approval, '
                   'a bounded lifecycle controller and independent rollback/flow provenance.',
    }


def main(argv=None) -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--domain', required=True)
    cli.add_argument('--remote-ip', required=True)
    cli.add_argument('--source-ip', required=True)
    cli.add_argument('--source-port', required=True, type=int)
    cli.add_argument('--wan', required=True)
    args = cli.parse_args(argv)
    print(json.dumps(plan(args.domain, args.remote_ip, args.source_ip, args.source_port, args.wan),
                     sort_keys=True))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except PlanError as exc:
        print('WAN_ACQUISITION_PLAN=UNVERIFIED: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
