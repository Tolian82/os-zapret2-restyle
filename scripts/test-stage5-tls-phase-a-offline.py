#!/usr/bin/env python3
"""No-network tests of Phase-A evidence binding and negative claims."""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import ipaddress
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).with_name('stage5-tls-phase-a-offline.py')
spec = importlib.util.spec_from_file_location('phasea', SCRIPT)
phasea = importlib.util.module_from_spec(spec)
spec.loader.exec_module(phasea)


class Native:
    @staticmethod
    def segments(text):
        return [x for x in text.split('--new') if x.strip()]
    @staticmethod
    def templates_and_imports(rows):
        return {}, ['profile'] * len(rows)
    @staticmethod
    def inherited(row, _):
        return row
    @staticmethod
    def visible(row):
        return row


class Target:
    MANAGED = Path('/usr/local/etc/zapret2/runtime-v2/managed')
    def profile_summary(self, text, parser):
        return [
            {'index': i + 1, 'ordinary': True, 'tls_443': True,
             'hostlists': (str(self.MANAGED / 'hostlist-user.txt'),),
             'families': ('ipv4', 'ipv6')}
            for i, _ in enumerate(parser[0](text))]
    @staticmethod
    def hostlist_hits(content, domain):
        return any(line == domain or domain.endswith('.' + line)
                   for line in content.splitlines() if line and not line.startswith('#'))
    @staticmethod
    def parse_networks(text, _):
        out = [ipaddress.ip_network(x, strict=True) for x in text.splitlines() if x]
        if any(x.prefixlen == 0 for x in out):
            raise ValueError('whole-family forbidden')
        return out
    @staticmethod
    def matches(ip, nets):
        return any(ip in x for x in nets if ip.version == x.version)


class Controller:
    def __init__(self, manifest):
        self.manifest = manifest
    def safe_plan(self, path):
        assert path.is_file()
        return {'analysis_manifest': self.manifest}


class Owner:
    def _parse_snapshot(self, raw, _):
        data = json.loads(raw)
        if data.get('state') != 'ready':
            raise ValueError('unready owner')
        return data


class Pcap:
    MAX_PCAP = 100
    def read_file(self, path, _):
        return path.read_bytes()
    @staticmethod
    def parse_manifest(raw):
        return json.loads(raw)
    @staticmethod
    def summarize(data, manifest, _):
        return {'capture_correlated': data == b'correlated',
                'same_sequence_conflicts': 0 if data == b'correlated' else 1,
                'payload_packets': 1}


class PhaseATests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.bundle = self.root / 'snapshot'; self.bundle.mkdir()
        self.plan = self.root / 'plan.json'; self.plan.write_text('{}')
        self.baseline = self.root / 'baseline.pcap'; self.baseline.write_bytes(b'correlated')
        self.manifest = {'domain': 'yt3.ggpht.com', 'remote_ip': '142.251.127.198',
                         'wan_interface': 'vtnet1',
                         'baseline': {'source_ip': '192.168.80.251', 'source_port': 54111}}
        self.tools = {'phase_a_controller': Controller(self.manifest),
                      'phase_a_selector': Target(), 'phase_a_owner': Owner(),
                      'phase_a_native': Native(), 'phase_a_pcap': Pcap()}
        patcher = patch.object(phasea, 'companion', side_effect=lambda name, path: self.tools[name])
        patcher.start();self.addCleanup(patcher.stop)
        for key, (name, _) in phasea.FILES.items():
            value = ('{"state":"ready","installed_plugin_version":"0.6.1_12",'
                     '"config_digest":"'+'a'*64+'"}' if key == 'owner' else
                     '--filter-tcp=443 --filter-l7=tls' if key == 'argv' else
                     'yt3.ggpht.com\n' if key == 'user' else '')
            (self.bundle / name).write_text(value)
        self.refresh_policy()

    def refresh_policy(self):
        payload = (self.bundle / 'dvtws.args').read_bytes()
        (self.bundle / 'dvtws.args.global-policy.json').write_text(json.dumps({
            'schema': 1, 'argv_sha256': hashlib.sha256(payload).hexdigest(),
            'profiles': len(Native.segments(payload.decode()))}))

    def inspect(self, captured=False):
        return phasea.inspect(self.bundle, self.plan, self.baseline if captured else None)

    def test_ipv4_eligibility_not_execution(self):
        result=self.inspect()
        self.assertEqual([1], result['eligible_profile_indexes'])
        self.assertEqual('ONE_ELIGIBLE_PROFILE',result['candidate_classification'])
        self.assertEqual('UNVERIFIED', result['runtime_profile_selected'])
        self.assertEqual('UNVERIFIED', result['baseline_strategy_mutation'])
        self.assertFalse(result['phase_b_permitted'])
        self.assertFalse(result['owner_live_authorized'])
        self.assertEqual(('OPEN','OPEN'),(result['installed_a07'],result['installed_a08']))
        self.assertNotIn('yt3.ggpht.com\n',json.dumps(result))

    def test_ipv6_same_family(self):
        self.manifest['remote_ip']='2001:4860:4860::8888'
        self.manifest['baseline']['source_ip']='2001:db8::10'
        self.assertEqual('ipv6', self.inspect()['identity']['family'])

    def test_multiple_candidates_never_select_runtime_profile(self):
        f=self.bundle/'dvtws.args'
        f.write_text(f.read_text()+' --new --filter-tcp=443 --filter-l7=tls')
        self.refresh_policy()
        result=self.inspect()
        self.assertEqual([1,2],result['eligible_profile_indexes'])
        self.assertEqual('MULTIPLE_ELIGIBLE_PROFILES',result['candidate_classification'])
        self.assertEqual('UNVERIFIED',result['runtime_profile_selected'])

    def test_domain_mismatch(self):
        (self.bundle/'hostlist-user.txt').write_text('badggpht.com\n')
        self.assertEqual([],self.inspect()['eligible_profile_indexes'])

    def test_global_exclusion_and_voice_overlap(self):
        for name in ('ipset-exclude.txt','ipset-telegram.txt'):
            file=self.bundle/name
            file.write_text('142.251.127.0/24\n')
            self.assertEqual('TARGET_EXCLUDED_OR_VOICE_OVERLAP',
                             self.inspect()['candidate_classification'])
            file.write_text('')

    def test_ipv6_exclusion_does_not_exclude_ipv4(self):
        (self.bundle/'ipset-exclude.txt').write_text('2001:db8::/64\n')
        self.assertEqual([1],self.inspect()['eligible_profile_indexes'])

    def test_tampered_native_policy_digest_blocks(self):
        (self.bundle/'dvtws.args').write_text('changed')
        with self.assertRaises(phasea.PhaseAError): self.inspect()

    def test_wrong_policy_profile_count_blocks(self):
        f=self.bundle/'dvtws.args.global-policy.json'
        data=json.loads(f.read_text()); data['profiles']=99;f.write_text(json.dumps(data))
        with self.assertRaises(phasea.PhaseAError):self.inspect()

    def test_wrong_installed_version_and_unready_blocks(self):
        f=self.bundle/'owner.json'; old=f.read_text()
        f.write_text(old.replace('0.6.1_12','0.6.1_11'))
        with self.assertRaises(phasea.PhaseAError):self.inspect()
        f.write_text(old.replace('"ready"','"stopped"'))
        with self.assertRaises(ValueError):self.inspect()

    def test_symlink_hardlink_and_oversized_refused(self):
        f=self.bundle/'hostlist-user.txt';f.unlink()
        f.symlink_to(self.bundle/'hostlist-youtube.txt')
        with self.assertRaises(phasea.PhaseAError):self.inspect()
        f.unlink();f.write_text('yt3.ggpht.com\n')
        alias=self.root/'hard';alias.hardlink_to(f)
        with self.assertRaises(phasea.PhaseAError):self.inspect()
        alias.unlink(); f.write_text('Z'* (12*1024*1024+1))
        with self.assertRaises(phasea.PhaseAError):self.inspect()

    def test_retained_capture_only_stays_unverified(self):
        result=self.inspect(captured=True)
        self.assertTrue(result['retained_baseline']['five_tuple_correlated_in_supplied_pcap'])
        self.assertEqual('UNVERIFIED',result['wan_packet_provenance'])
        self.baseline.write_bytes(b'ambiguous')
        self.assertEqual('AMBIGUOUS_BASELINE_STOP',self.inspect(captured=True)['candidate_classification'])

    def test_no_executable_network_or_permission(self):
        tree=ast.parse(SCRIPT.read_text()); imports=set()
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):imports.update(n.name.split('.')[0] for n in node.names)
            elif isinstance(node,ast.ImportFrom) and node.module:imports.add(node.module.split('.')[0])
        self.assertTrue(imports.isdisjoint({'socket','subprocess','urllib','requests'}))
        self.assertNotIn('execute_one(',SCRIPT.read_text())


if __name__=='__main__':unittest.main(verbosity=2)
