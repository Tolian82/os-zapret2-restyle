#!/usr/bin/env python3
"""Local tests of the read-only Stage-5 one-shot tool; no appliance needed."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch, Mock

SOURCE = Path(__file__).with_name('stage5-installed-one-shot.py')
SPEC = importlib.util.spec_from_file_location('stage5_one_shot', SOURCE)
assert SPEC is not None and SPEC.loader is not None
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def snapshot():
    entries = {n: {'configured': False} for n in m.SERVICES}
    entries['telegram'] = {'configured': True, 'wan': 'vtnet1'}
    return {
        'installed_plugin_version': '0.6.1_12', 'state': 'ready',
        'rule_count': 3, 'table_count': 1,
        'runtime': {'state': 'running', 'engine_verified': True, 'services': entries},
    }


class Stage5OneShotTests(unittest.TestCase):
    def test_ipv4_only_honestly_reports_unavailable_without_route(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root, 'ipset-telegram.txt').write_text('149.154.160.0/20\n')
            with patch.object(m, 'route_interface') as route:
                r = m.summarize(snapshot(), Path(root))
                route.assert_not_called()
            self.assertEqual('READ_ONLY_PREFLIGHT', r['status'])
            self.assertEqual('OPEN', r['stage5_installed_acceptance'])
            self.assertFalse(r['ipv6_packet_proven'])
            self.assertFalse(r['exclude_packet_proven'])
            self.assertEqual('NO_GLOBAL_IPV6_TARGET', r['services']['telegram']['ipv6_route'])
            self.assertEqual(1, r['services']['telegram']['ipv4_entries'])
            self.assertEqual(0, r['services']['telegram']['ipv6_entries'])

    def test_ipv6_candidate_with_wan_route_is_eligibility_not_wire_pass(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root, 'ipset-telegram.txt').write_text('149.154.160.0/20\n2001:4860:4860::/48\n')
            with patch.object(m, 'route_interface', return_value=('ROUTE_PRESENT', 'vtnet1')) as route:
                r = m.summarize(snapshot(), Path(root))
            route.assert_called_once_with('2001:4860:4860::1')
            self.assertEqual('ROUTE_PRESENT', r['services']['telegram']['ipv6_route'])
            self.assertTrue(r['services']['telegram']['wan_match'])
            self.assertEqual(1, r['services']['telegram']['ipv6_entries'])
            self.assertFalse(r['ipv6_packet_proven'])

    def test_non_wan_route_fails_eligibility(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root, 'ipset-telegram.txt').write_text('2001:4860:4860::1\n')
            with patch.object(m, 'route_interface', return_value=('ROUTE_PRESENT', 'vtnet0')):
                r = m.summarize(snapshot(), Path(root))
            self.assertEqual('OTHER_INTERFACE', r['services']['telegram']['ipv6_route'])
            self.assertFalse(r['services']['telegram']['wan_match'])

    def test_non_global_ipv6_never_triggers_probe(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root, 'ipset-telegram.txt').write_text('fd00::/8\nfe80::/64\n')
            with patch.object(m, 'route_interface') as route:
                r = m.summarize(snapshot(), Path(root))
                route.assert_not_called()
            self.assertEqual('NO_GLOBAL_IPV6_TARGET', r['services']['telegram']['ipv6_route'])
            self.assertEqual(2, r['services']['telegram']['ipv6_entries'])

    def test_symlink_and_full_family_and_bad_input_fail_closed(self):
        for content in ('::/0\n', 'this-is-not-an-ip\n', '2001:db8::1%vtnet1\n'):
            with self.subTest(content=content), tempfile.TemporaryDirectory() as root:
                f = Path(root, 'ipset-telegram.txt')
                f.write_text(content)
                with self.assertRaises(m.PreflightError):
                    m.summarize(snapshot(), Path(root))
        with tempfile.TemporaryDirectory() as root:
            real = Path(root, 'real.txt')
            real.write_text('149.154.160.0/20\n')
            Path(root, 'ipset-telegram.txt').symlink_to(real)
            with self.assertRaises(m.PreflightError):
                m.summarize(snapshot(), Path(root))

    def test_route_lookup_is_strict_readonly_and_bounded(self):
        with patch.object(m.subprocess, 'run', return_value=subprocess.CompletedProcess(
            [], 0, 'route to: 2001:4860:4860::1\n interface: vtnet1\n', '')) as command:
            state, iface = m.route_interface('2001:4860:4860::1')
        self.assertEqual(('ROUTE_PRESENT', 'vtnet1'), (state, iface))
        args, kwargs = command.call_args
        self.assertEqual(['/sbin/route', '-6', '-n', 'get', '2001:4860:4860::1'], args[0])
        self.assertEqual(8, kwargs['timeout'])

    def test_no_non_freebsd_shell_or_appliance_calls(self):
        with patch.object(m.platform, 'system', return_value='Linux'), \
             patch.object(m.subprocess, 'run') as commands, \
             patch.object(m, 'load_bridge') as bridge:
            with self.assertRaises(m.PreflightError):
                m.main()
            bridge.assert_not_called()
            commands.assert_not_called()

    def test_native_bridge_collect_is_the_only_snapshot_authority(self):
        s = snapshot()
        bridge = Mock()
        bridge.collect = Mock(side_effect=lambda: print(json.dumps(s)) or 0)
        bridge._parse_snapshot = Mock(side_effect=lambda raw, _: json.loads(raw))
        self.assertEqual(s, m.collect_native(bridge))
        bridge.collect.assert_called_once_with()
        bridge._parse_snapshot.assert_called_once()


if __name__ == '__main__':
    unittest.main(verbosity=2)
