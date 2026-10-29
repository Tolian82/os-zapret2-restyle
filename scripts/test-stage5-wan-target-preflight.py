#!/usr/bin/env python3
"""Offline regression for the read-only installed WAN target selector."""
from __future__ import annotations

import importlib.util
import ipaddress
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

FILE = Path(__file__).with_name('stage5-wan-target-preflight.py')
spec = importlib.util.spec_from_file_location('wan_target', FILE)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def ip(value):
    return ipaddress.ip_address(value)


def profiles():
    return [
        {'index': 1, 'ordinary': False, 'tls_443': False, 'hostlists': ()},
        {'index': 2, 'ordinary': True, 'tls_443': True,
         'hostlists': (str(m.MANAGED / 'hostlist-user.txt'),)},
        {'index': 3, 'ordinary': True, 'tls_443': True,
         'hostlists': (str(m.MANAGED / 'hostlist-youtube.txt'),)},
    ]


def lists():
    return {'hostlist-user.txt': 't.me\nyt3.ggpht.com\n',
            'hostlist-youtube.txt': 'googlevideo.com\nyt3.ggpht.com\n'}


def select(ips, excluded=None, voice=None, routed='vtnet1'):
    return m.classify(
        {'installed_plugin_version': '0.6.1_12', 'state': 'ready'},
        profiles(), lists(), excluded or [], voice or {},
        resolver=lambda _: [ip(x) for x in ips],
        route_lookup=lambda _: {'status': 'ROUTE_PRESENT', 'interface': routed},
        domains=('yt3.ggpht.com',),
    )


class WANPreflightTests(unittest.TestCase):
    def test_exact_hostlist_and_parent_without_suffix_false_positive(self):
        self.assertTrue(m.hostlist_hits('ggpht.com\n', 'yt3.ggpht.com'))
        self.assertTrue(m.hostlist_hits('yt3.ggpht.com\n', 'yt3.ggpht.com'))
        self.assertFalse(m.hostlist_hits('badggpht.com\n', 'yt3.ggpht.com'))
        self.assertFalse(m.hostlist_hits('#yt3.ggpht.com\n', 'yt3.ggpht.com'))

    def test_ipv4_candidate_is_potential_only_not_packet_pass(self):
        r = select(['142.251.127.198'])
        self.assertEqual('CANDIDATE_ONLY', r['selection'])
        self.assertEqual(1, len(r['candidates']))
        case = r['candidates'][0]
        self.assertEqual([2, 3], case['potential_profile_indexes'])
        self.assertEqual('142.251.127.198', case['remote_ip'])
        self.assertEqual('ipv4', case['family'])
        self.assertEqual('yt3.ggpht.com', case['tls_sni'])
        self.assertEqual('vtnet1', case['wan_interface'])
        self.assertEqual('POTENTIAL_ONLY', case['qualification'])
        self.assertIsNone(case['source_port'])
        self.assertFalse(r['baseline_modification_proven'])
        self.assertFalse(r['packet_flow_attributed'])
        self.assertFalse(r['exclude_packet_proven'])
        self.assertEqual('OPEN', r['a07_installed_acceptance'])
        self.assertEqual('OPEN', r['a08_installed_acceptance'])

    def test_ipv6_is_not_inferred_from_ipv4(self):
        r = select(['142.251.127.198', '2001:4860:4860::8888'])
        self.assertEqual(['ipv4', 'ipv6'], [x['family'] for x in r['candidates']])
        self.assertFalse(r['ipv6_packet_proven'])

    def test_many_A_records_cannot_starve_AAAA(self):
        ips = ['142.251.127.' + str(i) for i in range(1, 9)] + ['2001:4860:4860::8888']
        self.assertIn('ipv6', [x['family'] for x in select(ips)['candidates']])

    def test_profile_l3_restricts_candidate_family(self):
        flag = m.EXPECTED_EXCLUDE_TOKEN
        def seg(_):
            return [[flag, '--filter-tcp=443', '--filter-l7=tls', '--filter-l3=ipv4']]
        rows = m.profile_summary('ignored', (seg, lambda _: ({}, ['profile']),
                                             lambda x, _: x, lambda x: x))
        self.assertEqual(('ipv4',), rows[0]['families'])
        eligible = dict(rows[0], ordinary=True,
                        hostlists=(str(m.MANAGED / 'hostlist-user.txt'),))
        r = m.classify({'installed_plugin_version': '0.6.1_12', 'state': 'ready'},
                       [eligible], lists(), [], {},
                       resolver=lambda _: [ip('2001:4860:4860::8888')],
                       route_lookup=lambda _: {'status': 'ROUTE_PRESENT', 'interface': 'vtnet1'},
                       domains=('yt3.ggpht.com',))
        self.assertEqual('NO_ELIGIBLE_CONTROL_FOUND', r['selection'])

    def test_configured_voice_wan_mismatch_is_rejected(self):
        snapshot = {'installed_plugin_version': '0.6.1_12', 'state': 'ready',
                    'runtime': {'services': {
                        'telegram': {'configured': True, 'wan': 'vtnet1'}}}}
        r = m.classify(snapshot, profiles(), lists(), [], {},
                       resolver=lambda _: [ip('142.251.127.198')],
                       route_lookup=lambda _: {'status': 'ROUTE_PRESENT', 'interface': 'vtnet2'},
                       domains=('yt3.ggpht.com',))
        self.assertEqual('NO_ELIGIBLE_CONTROL_FOUND', r['selection'])

    def test_voice_overlap_forbids_candidate(self):
        voice = {'telegram': [ipaddress.ip_network('142.251.0.0/16')]}
        self.assertEqual('NO_ELIGIBLE_CONTROL_FOUND',
                         select(['142.251.127.198'], voice=voice)['selection'])

    def test_active_exclude_forbids_baseline_candidate(self):
        excluded = [ipaddress.ip_network('142.251.127.0/24')]
        self.assertEqual('NO_ELIGIBLE_CONTROL_FOUND',
                         select(['142.251.127.198'], excluded=excluded)['selection'])

    def test_unrouted_candidate_is_rejected(self):
        r = m.classify({'installed_plugin_version': '0.6.1_12', 'state': 'ready'},
                       profiles(), lists(), [], {},
                       resolver=lambda _: [ip('142.251.127.198')],
                       route_lookup=lambda _: {'status': 'ROUTE_UNAVAILABLE'},
                       domains=('yt3.ggpht.com',))
        self.assertEqual('NO_ELIGIBLE_CONTROL_FOUND', r['selection'])

    def test_unmatched_hostlist_never_resolves(self):
        r = m.classify({'installed_plugin_version': '0.6.1_12', 'state': 'ready'},
                       profiles(), lists(), [], {},
                       resolver=Mock(side_effect=AssertionError('unexpected DNS')),
                       domains=('example.net',))
        self.assertEqual([], r['candidates'])

    def test_safe_read_refuses_symlink_hardlink_oversize_and_nul(self):
        with tempfile.TemporaryDirectory() as root:
            f = Path(root, 'hostlist-user.txt')
            f.write_text('yt3.ggpht.com\n')
            self.assertIn('yt3.ggpht.com', m.safe_read(f, 100))
            with self.assertRaises(m.PreflightError):
                m.safe_read(f, 5)
            alias = Path(root, 'alias')
            alias.symlink_to(f)
            with self.assertRaises(m.PreflightError):
                m.safe_read(alias, 100)
            extra = Path(root, 'hard')
            extra.hardlink_to(f)
            with self.assertRaises(m.PreflightError):
                m.safe_read(f, 100)
            extra.unlink()
            f.write_bytes(b'bad\x00')
            with self.assertRaises(m.PreflightError):
                m.safe_read(f, 100)

    def test_ipset_rejects_full_family_mapped_zone_and_invalid_cidr(self):
        bad_values = ('0.0.0.0/0\n', '::/0\n', '::ffff:192.0.2.1\n',
                      'fe80::1%eth0\n', '192.0.2.1/24\n', '#comment\n',
                      '0.0.0.0/1\n128.0.0.0/1\n', '::/1\n8000::/1\n')
        for bad in bad_values:
            with self.subTest(value=bad), self.assertRaises(m.PreflightError):
                m.parse_networks(bad, 'exclude')
        self.assertEqual(2, len(m.parse_networks(
            '196.216.2.24/29\n2001:db8::/64\n', 'exclude')))

    def test_final_executable_profiles_require_one_exclude_each(self):
        flag = m.EXPECTED_EXCLUDE_TOKEN
        def seg(_):
            return [['--template=x'], [flag, '--filter-tcp=443', '--filter-l7=tls',
                                       '--hostlist=' + str(m.MANAGED / 'hostlist-user.txt')]]
        def kind(_):
            return ({'x': []}, ['template', 'profile'])
        def expand(tokens, _):
            return tokens
        rows = m.profile_summary('ignored', (seg, kind, expand, lambda x: x))
        self.assertEqual(1, len(rows))
        self.assertTrue(rows[0]['tls_443'])
        self.assertEqual(1, rows[0]['index'])
        with self.assertRaises(m.PreflightError):
            m.profile_summary('ignored', (lambda _: [['--filter-tcp=443']],
                          lambda _: ({}, ['profile']), expand, lambda x: x))

    def test_voice_ipset_profile_not_classified_as_ordinary(self):
        flag = m.EXPECTED_EXCLUDE_TOKEN
        def seg(_):
            return [[flag, '--filter-tcp=443', '--filter-l7=tls', '--ipset=/managed/telegram']]
        rows = m.profile_summary('ignored', (seg, lambda _: ({}, ['profile']),
                                              lambda x, _: x, lambda x: x))
        self.assertFalse(rows[0]['ordinary'])

    def test_dns_only_subprocess_bounded(self):
        complete = subprocess.CompletedProcess([], 0, json.dumps([
            '142.251.127.198', '2001:4860:4860::8888']), '')
        with patch.object(m.subprocess, 'run', return_value=complete) as command:
            got = m.resolve('yt3.ggpht.com')
        self.assertEqual(2, len(got))
        args, kw = command.call_args
        self.assertEqual(8, kw['timeout'])
        self.assertEqual('/usr/local/bin/python3.13', args[0][0])
        self.assertNotIn('curl', str(args))

    def test_dns_resolver_retains_aaaa_among_many_A_records(self):
        addresses = ['142.251.127.' + str(i) for i in range(1, 20)] + [
            '2001:4860:4860::8888']
        response = subprocess.CompletedProcess([], 0, json.dumps(addresses), '')
        with patch.object(m.subprocess, 'run', return_value=response):
            result = m.resolve('yt3.ggpht.com')
        self.assertIn('2001:4860:4860::8888', [str(a) for a in result])
        self.assertLessEqual(len(result), m.MAX_DNS_ADDRESSES)

    def test_route_ipv6_and_ipv4_get_are_readonly(self):
        complete = subprocess.CompletedProcess([], 0, 'route to: x\n interface: vtnet1\n', '')
        with patch.object(m.subprocess, 'run', return_value=complete) as command:
            self.assertEqual('vtnet1', m.route(ip('2001:4860:4860::8888'))['interface'])
            self.assertEqual(['-6', '-n', 'get'], command.call_args[0][0][1:4])
        with patch.object(m.subprocess, 'run', return_value=complete) as command:
            self.assertEqual('vtnet1', m.route(ip('142.251.127.198'))['interface'])
            self.assertEqual(['-n', 'get'], command.call_args[0][0][1:3])

    def test_non_freebsd_refuses_without_appliance_calls(self):
        with patch.object(m.platform, 'system', return_value='Linux'), \
             patch.object(m, 'native_snapshot') as snapshot, \
             patch.object(m.subprocess, 'run') as command:
            with self.assertRaises(m.PreflightError):
                m.main()
            snapshot.assert_not_called()
            command.assert_not_called()

    def test_output_is_capped_at_four_candidates(self):
        ips = ['142.251.127.' + str(i) for i in range(1, 15)] + [
            '2001:4860:4860::' + str(i) for i in range(1, 15)]
        candidates = select(ips)['candidates']
        self.assertEqual(4, len(candidates))
        self.assertTrue(all(x['qualification'] == 'POTENTIAL_ONLY' for x in candidates))


if __name__ == '__main__':
    unittest.main(verbosity=2)
