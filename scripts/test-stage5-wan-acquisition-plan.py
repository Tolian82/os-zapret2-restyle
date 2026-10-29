#!/usr/bin/env python3
"""Offline tests for the bounded, unexecuted WAN capture/probe argv plan."""
import ast
import importlib.util
import ipaddress
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).with_name('stage5-wan-acquisition-plan.py')
_spec = importlib.util.spec_from_file_location('stage5_wan_acquisition_plan', SOURCE)
assert _spec and _spec.loader
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)


def produce(ip='142.251.127.198', source='192.168.80.251', port=54111):
    return m.plan('yt3.ggpht.com', ip, source, port, 'vtnet1')


class AcquisitionPlanTests(unittest.TestCase):
    def test_ipv4_emits_two_identical_bpf_filters_and_manifest(self):
        p = produce()
        self.assertEqual('PLAN_ONLY_UNEXECUTED', p['status'])
        self.assertEqual(p['phases']['baseline']['capture_argv'][-1],
                         p['phases']['excluded']['capture_argv'][-1])
        self.assertEqual('142.251.127.198', p['analysis_manifest']['remote_ip'])
        self.assertEqual(p['analysis_manifest']['baseline'], p['analysis_manifest']['excluded'])
        self.assertIn('src port 54111', p['phases']['baseline']['capture_argv'][-1])
        self.assertEqual('baseline.pcap', p['phases']['baseline']['capture_argv'][-2])
        self.assertEqual('excluded.pcap', p['phases']['excluded']['capture_argv'][-2])

    def test_ipv6_sni_and_resolve_are_pinned(self):
        p = produce('2001:4860:4860::8888', '2001:db8::10')
        a = p['phases']['baseline']['probe_argv']
        self.assertIn('-6', a)
        self.assertIn('yt3.ggpht.com:443:[2001:4860:4860::8888]', a)
        self.assertIn('host!2001:db8::10', a)
        self.assertEqual('2001:4860:4860::8888', p['analysis_manifest']['remote_ip'])

    def test_no_protocol_inference_from_capture_plan(self):
        p = produce()
        for key in ('owner_live_authorization', 'executed', 'route_verified',
                    'source_ip_owned_by_wan_verified', 'source_port_free_verified',
                    'engine_profile_selected_verified', 'baseline_dpi_modification_verified',
                    'exclude_effect_verified', 'wan_pcap_proven',
                    'gui_apply_and_restore_executed'):
            self.assertIs(p[key], False, key)
        self.assertEqual('OPEN', p['installed_a07'])
        self.assertEqual('OPEN', p['installed_a08'])
        self.assertFalse(p['phases']['excluded']['probe_executed'])

    def test_bounded_capture_and_probe_once(self):
        p = produce()
        for ph in p['phases'].values():
            self.assertEqual(m.CAPTURE_DEADLINE_SECONDS, ph['capture_deadline_seconds'])
            self.assertEqual(m.CAPTURE_PACKETS, ph['max_packets'])
            self.assertEqual(m.CAPTURE_SNAPLEN, ph['max_snaplen_bytes'])
            self.assertEqual(1, ph['probe_argv'].count('https://yt3.ggpht.com/'))
            self.assertEqual('0', ph['probe_argv'][ph['probe_argv'].index('--retry')+1])
            self.assertEqual('/dev/null', ph['probe_argv'][ph['probe_argv'].index('--output')+1])

    def test_config_changes_only_manual_after_baseline_attestation(self):
        s = produce()['strict_sequence']
        self.assertLess(next(i for i, x in enumerate(s) if 'baseline modification' in x),
                        next(i for i, x in enumerate(s) if 'GUI Apply' in x))
        self.assertIn('restoration', ' '.join(s))

    def test_remote_never_private_loopback_multicast(self):
        for remote in ('127.0.0.1','10.0.0.1','::1','fd00::1','224.0.0.1','ff02::1', 'garbage'):
            with self.subTest(remote=remote), self.assertRaises(m.PlanError):
                produce(remote)

    def test_invalid_domain_and_wan_fail_closed(self):
        for domain in ('a.com;reboot', '-a.com', 'a..com', 't.me/evil', 'xn--.com','A.COM'):
            with self.subTest(domain=domain), self.assertRaises(m.PlanError):
                m.plan(domain,'142.251.127.198','192.168.80.251',54111,'vtnet1')
        for iface in ('vtnet1;reboot', 'vtnet1 bad', '/dev/vtnet1','Vtnet1'):
            with self.subTest(iface=iface), self.assertRaises(m.PlanError):
                m.plan('yt3.ggpht.com','142.251.127.198','192.168.80.251',54111,iface)

    def test_source_family_mismatch_bad_source(self):
        for source in ('::1', '127.0.0.1', '0.0.0.0', '224.0.0.1', '2001:db8::1'):
            with self.subTest(source=source), self.assertRaises(m.PlanError):
                produce(source=source)

    def test_port_range_and_bool(self):
        for port in (True, -1, 0, 49999, 61000, 65535):
            with self.subTest(port=port), self.assertRaises(m.PlanError):
                produce(port=port)

    def test_urls_are_https_and_only_one_endpoint(self):
        p = produce()
        for ph in p['phases'].values():
            argv = ph['probe_argv']
            self.assertIn('--noproxy',argv)
            self.assertIn('--http1.1',argv)
            self.assertEqual('https://yt3.ggpht.com/',argv[-1])
            self.assertIn('yt3.ggpht.com:443:142.251.127.198',argv)

    def test_program_does_not_import_mutating_or_network_modules(self):
        tree = ast.parse(SOURCE.read_text())
        imports = {n.names[0].name.split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.Import)}
        imports |= {n.module.split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.ImportFrom) and n.module}
        for prohibited in ('subprocess','socket','requests','urllib','os'):
            self.assertNotIn(prohibited,imports)
        self.assertNotIn('os.system',SOURCE.read_text())

    def test_json_roundtrip_to_existing_attribution_manifest_shape(self):
        expected={'schema_version','domain','remote_ip','wan_interface','baseline','excluded'}
        d=json.loads(json.dumps(produce()))['analysis_manifest']
        self.assertEqual(expected,set(d))
        self.assertEqual({'source_ip','source_port'},set(d['baseline']))
        self.assertEqual(d['baseline']['source_port'],d['excluded']['source_port'])

    def test_main_is_only_plan_output_and_no_subprocess(self):
        with patch.object(sys, 'argv', ['p','--domain','yt3.ggpht.com','--remote-ip','142.251.127.198',
                                         '--source-ip','192.168.80.251','--source-port','54111','--wan','vtnet1']):
            from io import StringIO
            with patch('sys.stdout', new_callable=StringIO) as out:
                self.assertEqual(0,m.main())
                self.assertEqual('PLAN_ONLY_UNEXECUTED',json.loads(out.getvalue())['status'])


if __name__=='__main__':
    unittest.main(verbosity=2)
