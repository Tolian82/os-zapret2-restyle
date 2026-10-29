#!/usr/bin/env python3
"""Offline, read-only, bounded two-phase WAN TCP PCAP flow attribution.

No capture, network access, Config/IPFW writes, service calls or transmission.
Two captures and one operator-supplied manifest are local inputs, not proof of
WAN origin, TLS SNI, dvtws modification, or global Exclude policy. Fail closed.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys

MAX_PCAP = 8 * 1024 * 1024
MAX_MANIFEST = 4096
MAX_PACKETS = 2048
MAX_FLOW_PACKETS = 256
MAX_SNAPLEN = 65535
MAGICS = {b'\xd4\xc3\xb2\xa1': '<', b'\xa1\xb2\xc3\xd4': '>',
          b'\x4d\x3c\xb2\xa1': '<', b'\xa1\xb2\x3c\x4d': '>'}
EXPECTED = {'schema_version', 'domain', 'remote_ip', 'wan_interface',
            'baseline', 'excluded'}
ENDPOINT_KEYS = {'source_ip', 'source_port'}


class EvidenceError(ValueError):
    pass


def read_file(path: Path, limit: int) -> bytes:
    """No symlinks/hardlinks and no silent truncation of sensitive capture."""
    try:
        flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
        fd = os.open(str(path), flags)
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_size > limit:
                raise EvidenceError('unsafe or oversized evidence: ' + path.name)
            with os.fdopen(fd, 'rb', closefd=False) as f:
                data = f.read(limit + 1)
            if len(data) > limit or len(data) != st.st_size:
                raise EvidenceError('oversized or changing evidence: ' + path.name)
            return data
        finally:
            os.close(fd)
    except OSError as exc:
        raise EvidenceError('unreadable evidence: ' + path.name) from exc


def parse_manifest(raw: bytes) -> dict:
    try:
        doc = json.loads(raw)
    except (UnicodeError, ValueError) as exc:
        raise EvidenceError('invalid manifest JSON') from exc
    if not isinstance(doc, dict) or set(doc) != EXPECTED or doc['schema_version'] != 1:
        raise EvidenceError('unsupported manifest schema')
    domain, wan = doc['domain'], doc['wan_interface']
    if not isinstance(domain, str) or not re.fullmatch(r'[a-z0-9-]+(?:\.[a-z0-9-]+)+', domain):
        raise EvidenceError('invalid domain identity')
    if not isinstance(wan, str) or not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_.-]{0,31}', wan):
        raise EvidenceError('invalid declared interface')
    try:
        remote = ipaddress.ip_address(doc['remote_ip'])
    except ValueError as exc:
        raise EvidenceError('invalid remote IP') from exc
    if not remote.is_global or remote.version not in (4, 6):
        raise EvidenceError('unusable remote IP')
    for phase in ('baseline', 'excluded'):
        ep = doc[phase]
        if not isinstance(ep, dict) or set(ep) != ENDPOINT_KEYS:
            raise EvidenceError('invalid ' + phase + ' endpoint')
        try:
            source = ipaddress.ip_address(ep['source_ip'])
        except ValueError as exc:
            raise EvidenceError('invalid ' + phase + ' source') from exc
        port = ep['source_port']
        if source.version != remote.version or source == remote or type(port) is not int or not 1024 <= port <= 65535:
            raise EvidenceError('invalid ' + phase + ' source/port/family')
    return doc


def ipv4_tcp(frame: bytes, pos: int):
    if len(frame) < pos + 20 or frame[pos] >> 4 != 4:
        raise EvidenceError('invalid IPv4 header')
    ihl = (frame[pos] & 15) * 4
    if ihl < 20 or len(frame) < pos + ihl:
        raise EvidenceError('bad IPv4 IHL')
    total = struct.unpack_from('!H', frame, pos + 2)[0]
    if total < ihl or pos + total > len(frame):
        raise EvidenceError('truncated IPv4 datagram')
    frag = struct.unpack_from('!H', frame, pos + 6)[0]
    if frag & 0x3fff:
        raise EvidenceError('fragmented IPv4 capture: ambiguous TCP flow')
    if frame[pos + 9] != 6:
        return None
    return (ipaddress.ip_address(frame[pos + 12:pos + 16]),
            ipaddress.ip_address(frame[pos + 16:pos + 20]),
            frame[pos + ihl:pos + total])


def ipv6_tcp(frame: bytes, pos: int):
    if len(frame) < pos + 40 or frame[pos] >> 4 != 6:
        raise EvidenceError('invalid IPv6 header')
    payload = struct.unpack_from('!H', frame, pos + 4)[0]
    if payload == 0 or pos + 40 + payload > len(frame):
        raise EvidenceError('truncated or jumbo IPv6 capture')
    # Deliberately refuse extension chains: never guess flow identity through
    # fragment, routing, AH, hop/destination options or unknown headers.
    proto = frame[pos + 6]
    if proto in (0, 43, 44, 50, 51, 60, 135):
        raise EvidenceError('unverified IPv6 extension chain')
    if proto != 6:
        return None
    return (ipaddress.ip_address(frame[pos + 8:pos + 24]),
            ipaddress.ip_address(frame[pos + 24:pos + 40]),
            frame[pos + 40:pos + 40 + payload])


def decode_frame(frame: bytes):
    if len(frame) < 14:
        raise EvidenceError('truncated Ethernet header')
    kind = struct.unpack_from('!H', frame, 12)[0]
    pos = 14
    for _ in range(2):
        if kind not in (0x8100, 0x88a8, 0x9100):
            break
        if len(frame) < pos + 4:
            raise EvidenceError('truncated VLAN tag')
        kind = struct.unpack_from('!H', frame, pos + 2)[0]
        pos += 4
    if kind in (0x8100, 0x88a8, 0x9100):
        raise EvidenceError('too many VLAN tags')
    if kind == 0x0800:
        ip = ipv4_tcp(frame, pos)
    elif kind == 0x86dd:
        ip = ipv6_tcp(frame, pos)
    else:
        return None
    if ip is None:
        return None
    src, dst, tcp = ip
    if len(tcp) < 20:
        raise EvidenceError('truncated TCP header')
    srcport, dstport, seq = struct.unpack_from('!HHI', tcp)
    offset = (tcp[12] >> 4) * 4
    if offset < 20 or offset > len(tcp):
        raise EvidenceError('invalid TCP data offset')
    return (src, dst, srcport, dstport, seq, tcp[13], tcp[offset:])


def pcap_packets(raw: bytes):
    if len(raw) < 24 or raw[:4] not in MAGICS:
        raise EvidenceError('unsupported PCAP magic')
    endian = MAGICS[raw[:4]]
    major, minor, _, _, snaplen, dlt = struct.unpack_from(endian + 'HHiIII', raw, 4)
    if (major, minor) != (2, 4) or not 1 <= snaplen <= MAX_SNAPLEN or dlt != 1:
        raise EvidenceError('require Ethernet PCAP v2.4, bounded snaplen')
    pos, n = 24, 0
    while pos < len(raw):
        if len(raw) - pos < 16:
            raise EvidenceError('incomplete PCAP record')
        _, _, captured, original = struct.unpack_from(endian + 'IIII', raw, pos)
        pos += 16
        if captured > snaplen or original < captured or captured > len(raw) - pos:
            raise EvidenceError('invalid PCAP record length')
        n += 1
        if n > MAX_PACKETS:
            raise EvidenceError('excessive packets')
        if captured != original:
            raise EvidenceError('truncated capture: cannot attest payload')
        yield decode_frame(raw[pos:pos + captured])
        pos += captured
    if n == 0:
        raise EvidenceError('empty PCAP')


def summarize(raw: bytes, manifest: dict, phase: str) -> dict:
    endpoint = manifest[phase]
    source = ipaddress.ip_address(endpoint['source_ip'])
    target = ipaddress.ip_address(manifest['remote_ip'])
    localport = endpoint['source_port']
    outward = []
    reverse = 0
    unrelated = 0
    for p in pcap_packets(raw):
        if p is None:
            unrelated += 1
            continue
        src, dst, sport, dport, seq, flags, payload = p
        if (src, dst, sport, dport) == (source, target, localport, 443):
            outward.append((seq, flags, payload))
            if len(outward) > MAX_FLOW_PACKETS:
                raise EvidenceError('too many correlated packets')
        elif (src, dst, sport, dport) == (target, source, 443, localport):
            reverse += 1
        else:
            unrelated += 1
    segments = [(seq, data) for seq, _, data in outward if data]
    seen = {}
    conflicts = 0
    for seq, data in segments:
        if seq in seen and seen[seq] != data:
            conflicts += 1
        else:
            seen[seq] = data
    canonical = sorted(seen.items())
    digest = hashlib.sha256()
    for seq, data in canonical:
        digest.update(struct.pack('!II', seq, len(data)))
        digest.update(data)
    flags = {'syn': sum(bool(f & 0x02) for _, f, _ in outward),
             'rst': sum(bool(f & 0x04) for _, f, _ in outward),
             'fin': sum(bool(f & 0x01) for _, f, _ in outward)}
    return {'phase': phase, 'family': 'ipv' + str(target.version),
            'source_ip': str(source), 'source_port': localport,
            'remote_ip': str(target), 'remote_port': 443,
            'outgoing_packets': len(outward), 'incoming_packets': reverse,
            'unrelated_packets': unrelated,
            'payload_packets': len(segments), 'unique_payload_segments': len(seen),
            'duplicate_payload_packets': len(segments) - len(seen),
            'same_sequence_conflicts': conflicts,
            'payload_bytes_observed': sum(len(d) for _, d in segments),
            'unique_payload_fingerprint': digest.hexdigest() if seen else None,
            'flags': flags, 'capture_correlated': bool(outward) and bool(segments) and conflicts == 0}


def compare(manifest: dict, baseline: bytes, excluded: bytes) -> dict:
    a, b = summarize(baseline, manifest, 'baseline'), summarize(excluded, manifest, 'excluded')
    correlation = a['capture_correlated'] and b['capture_correlated']
    if not correlation:
        observation = 'INCONCLUSIVE_NO_UNAMBIGUOUS_PAYLOAD'
    elif a['unique_payload_fingerprint'] == b['unique_payload_fingerprint'] and a['source_port'] == b['source_port']:
        observation = 'SAME_OBSERVED_TCP_PAYLOAD_FINGERPRINT'
    else:
        observation = 'DIFFERENT_OR_NONCOMPARABLE_TCP_PAYLOAD_FINGERPRINT'
    return {'status': 'OFFLINE_CAPTURE_ATTRIBUTION_ONLY',
            'declared_interface': manifest['wan_interface'],
            'declared_sni_unverified': manifest['domain'],
            'same_remote_endpoint': True,
            'same_source_port': a['source_port'] == b['source_port'],
            'phase_observations': {'baseline': a, 'excluded': b},
            'payload_comparison': observation,
            'five_tuple_capture_correlated': bool(correlation),
            'wan_capture_proven': False,
            'tls_sni_proven': False,
            'dpi_modification_proven': False,
            'exclude_effect_proven': False,
            'a07_installed_acceptance': 'OPEN', 'a08_installed_acceptance': 'OPEN',
            'note': 'Only attributable TCP packets within two caller-provided Ethernet PCAPs were observed. Capture interface, original TLS/Host/SNI, DPI modifications and restoration remain independently unverified. PCAP payload bytes were never exported.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--baseline', required=True, type=Path)
    parser.add_argument('--excluded', required=True, type=Path)
    args = parser.parse_args(argv)
    doc = parse_manifest(read_file(args.manifest, MAX_MANIFEST))
    if len({str(x.resolve()) for x in (args.manifest, args.baseline, args.excluded)}) != 3:
        raise EvidenceError('manifest and captures must be distinct files')
    print(json.dumps(compare(doc, read_file(args.baseline, MAX_PCAP),
                             read_file(args.excluded, MAX_PCAP)), sort_keys=True))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (EvidenceError, OSError) as exc:
        print('WAN_PCAP_ATTRIBUTION=UNVERIFIED: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
