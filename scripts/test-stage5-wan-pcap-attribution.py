#!/usr/bin/env python3
"""No-network unit test for bounded, fail-closed two-phase TCP PCAP evidence."""
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

SRC = Path(__file__).with_name('stage5-wan-pcap-attribution.py')
spec = importlib.util.spec_from_file_location('stage5_pcap', SRC)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def manifest(family=4):
    remote = '142.251.127.198' if family == 4 else '2001:4860:4860::8888'
    source = '192.0.2.10' if family == 4 else '2001:db8::10'
    return {'schema_version': 1, 'domain': 'yt3.ggpht.com',
            'wan_interface': 'vtnet1', 'remote_ip': remote,
            'baseline': {'source_ip': source, 'source_port': 54111},
            'excluded': {'source_ip': source, 'source_port': 54111}}


def packet(src, dst, srcport, dstport, seq=100, payload=b'hello', flags=0x18, vlan=False):
    src, dst = ipaddress.ip_address(src), ipaddress.ip_address(dst)
    assert src.version == dst.version
    tcp = struct.pack('!HHIIHHHH', srcport, dstport, seq, 1, (5 << 12) | flags, 4096, 0, 0) + payload
    if src.version == 4:
        ip = struct.pack('!BBHHHBBH', 0x45, 0, len(tcp) + 20, 0, 0, 64, 6, 0) + src.packed + dst.packed
        ethertype = 0x0800
    else:
        ip = struct.pack('!IHBB', 0x60000000, len(tcp), 6, 64) + src.packed + dst.packed
        ethertype = 0x86dd
    eth = (b'\x11' * 6) + (b'\x22' * 6)
    if vlan:
        eth += struct.pack('!HHH', 0x8100, 1, ethertype)
    else:
        eth += struct.pack('!H', ethertype)
    return eth + ip + tcp


def pcap(*frames, endian='<'):
    magic = b'\xd4\xc3\xb2\xa1' if endian == '<' else b'\xa1\xb2\xc3\xd4'
    out = magic + struct.pack(endian + 'HHiIII', 2, 4, 0, 0, 65535, 1)
    for frame in frames:
        out += struct.pack(endian + 'IIII', 0, 0, len(frame), len(frame)) + frame
    return out


class ReadOnlyFlowTests(unittest.TestCase):
    def good(self, family=4):
        d = manifest(family)
        ep = d['baseline']
        return d, packet(ep['source_ip'], d['remote_ip'], ep['source_port'], 443)

    def test_ipv4_exact_flow_and_separate_unrelated(self):
        d, f = self.good()
        extra = packet(d['baseline']['source_ip'], d['remote_ip'], 54112, 443)
        reverse = packet(d['remote_ip'], d['baseline']['source_ip'], 443, 54111)
        r = m.summarize(pcap(extra, f, reverse), d, 'baseline')
        self.assertEqual((1, 1, 1), (r['outgoing_packets'], r['incoming_packets'], r['unrelated_packets']))
        self.assertTrue(r['capture_correlated'])
        self.assertEqual(5, r['payload_bytes_observed'])
        self.assertNotIn('hello', json.dumps(r))

    def test_ipv6_vlan_and_big_endian(self):
        d = manifest(6)
        f = packet(d['baseline']['source_ip'], d['remote_ip'], 54111, 443, vlan=True)
        a = m.summarize(pcap(f, endian='>'), d, 'baseline')
        self.assertTrue(a['capture_correlated'])
        self.assertEqual('ipv6', a['family'])

    def test_bytes_different_is_not_exclusion_proof(self):
        d, f = self.good()
        g = packet(d['baseline']['source_ip'], d['remote_ip'], 54111, 443, payload=b'jello')
        r = m.compare(d, pcap(f), pcap(g))
        self.assertEqual('DIFFERENT_OR_NONCOMPARABLE_TCP_PAYLOAD_FINGERPRINT', r['payload_comparison'])
        self.assertTrue(r['five_tuple_capture_correlated'])
        self.assertFalse(r['exclude_effect_proven'])
        self.assertFalse(r['dpi_modification_proven'])
        self.assertFalse(r['wan_capture_proven'])
        self.assertEqual('OPEN', r['a07_installed_acceptance'])

    def test_identical_bytes_not_exclusion_proof(self):
        d, f = self.good()
        r = m.compare(d, pcap(f), pcap(f))
        self.assertEqual('SAME_OBSERVED_TCP_PAYLOAD_FINGERPRINT', r['payload_comparison'])
        self.assertFalse(r['exclude_effect_proven'])
        self.assertFalse(r['tls_sni_proven'])

    def test_different_initial_sequence_numbers_do_not_change_content_fingerprint(self):
        d, f = self.good()
        g = packet(d['baseline']['source_ip'], d['remote_ip'], 54111, 443,
                   seq=983311, payload=b'hello')
        r = m.compare(d, pcap(f), pcap(g))
        self.assertEqual('SAME_OBSERVED_TCP_PAYLOAD_FINGERPRINT', r['payload_comparison'])
        self.assertFalse(r['dpi_modification_proven'])

    def test_unmatched_flow_inconclusive(self):
        d, f = self.good()
        other = packet(d['baseline']['source_ip'], d['remote_ip'], 54112, 443)
        r = m.compare(d, pcap(f), pcap(other))
        self.assertFalse(r['five_tuple_capture_correlated'])
        self.assertEqual('INCONCLUSIVE_NO_UNAMBIGUOUS_PAYLOAD', r['payload_comparison'])

    def test_retransmit_deduplication_and_conflict(self):
        d, f = self.good()
        s = m.summarize(pcap(f, f), d, 'baseline')
        self.assertEqual((1, 1), (s['duplicate_payload_packets'], s['unique_payload_segments']))
        diff = packet(d['baseline']['source_ip'], d['remote_ip'], 54111, 443, payload=b'jello')
        s = m.summarize(pcap(f, diff), d, 'baseline')
        self.assertEqual(1, s['same_sequence_conflicts'])
        self.assertFalse(s['capture_correlated'])

    def test_manifest_rejects_bad_schema_remote_family_bool_port(self):
        d = manifest()
        for mutation in ({'schema_version': 2}, {'remote_ip': '127.0.0.1'}, {'unexpected': 3},
                         {'wan_interface': 'vtnet1; evil'}, {'domain': 'bad:port'}):
            candidate = dict(d, **mutation)
            with self.subTest(mutation=mutation), self.assertRaises(m.EvidenceError):
                m.parse_manifest(json.dumps(candidate).encode())
        for port in (True, 0, 999, 65536):
            candidate = dict(d, baseline=dict(d['baseline'], source_port=port))
            with self.assertRaises(m.EvidenceError):
                m.parse_manifest(json.dumps(candidate).encode())
        candidate = dict(d, excluded={'source_ip': '2001:db8::1', 'source_port': 54111})
        with self.assertRaises(m.EvidenceError):
            m.parse_manifest(json.dumps(candidate).encode())

    def test_broken_pcap_and_truncation_rejected(self):
        d, f = self.good()
        for raw in (b'', b'nope', pcap(f)[:-3], pcap(f) + b'bad'):
            with self.subTest(size=len(raw)), self.assertRaises(m.EvidenceError):
                m.summarize(raw, d, 'baseline')
        truncated = bytearray(pcap(f)); struct.pack_into('<I', truncated, 24 + 12, len(f) + 1)
        with self.assertRaises(m.EvidenceError):
            m.summarize(bytes(truncated), d, 'baseline')

    def test_ipv4_fragments_and_ipv6_extensions_fail_closed(self):
        d, f = self.good()
        frag = bytearray(f); struct.pack_into('!H', frag, 14 + 6, 0x2000)
        with self.assertRaises(m.EvidenceError):
            m.summarize(pcap(bytes(frag)), d, 'baseline')
        d = manifest(6)
        f = bytearray(packet(d['baseline']['source_ip'], d['remote_ip'], 54111, 443))
        f[14 + 6] = 44
        with self.assertRaises(m.EvidenceError):
            m.summarize(pcap(bytes(f)), d, 'baseline')

    def test_reader_disallows_symlink_hardlink_large(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp, 'file'); f.write_bytes(b'example')
            self.assertEqual(b'example', m.read_file(f, 7))
            with self.assertRaises(m.EvidenceError):
                m.read_file(f, 6)
            link = Path(tmp, 'link'); link.symlink_to(f)
            with self.assertRaises(m.EvidenceError):
                m.read_file(link, 12)
            hard = Path(tmp, 'hard'); os.link(f, hard)
            with self.assertRaises(m.EvidenceError):
                m.read_file(f, 12)

    def test_empty_payload_never_a07_pass(self):
        d = manifest()
        f = packet(d['baseline']['source_ip'], d['remote_ip'], 54111, 443, payload=b'', flags=0x02)
        r = m.compare(d, pcap(f), pcap(f))
        self.assertFalse(r['five_tuple_capture_correlated'])
        self.assertEqual('INCONCLUSIVE_NO_UNAMBIGUOUS_PAYLOAD', r['payload_comparison'])

    def test_offline_has_no_traffic_or_firewall_modules(self):
        import ast
        src = SRC.read_text()
        names = {node.module for node in ast.walk(ast.parse(src)) if isinstance(node, ast.ImportFrom)}
        self.assertNotIn('socket', names)
        self.assertNotIn('subprocess', names)
        self.assertNotIn('requests', src)
        self.assertNotIn('ipfw add', src)


if __name__ == '__main__':
    unittest.main(verbosity=2)
