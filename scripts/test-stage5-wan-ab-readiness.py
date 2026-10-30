#!/usr/bin/env python3
"""Offline A07 A/B restoration guards; no network or appliance calls."""
import ast
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).with_name('stage5-wan-ab-readiness.py')
spec = importlib.util.spec_from_file_location('a07_review', SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class Control:
    def __init__(self, family=4):
        remote, source = (('142.251.127.198','192.168.80.251') if family == 4 else
                          ('2001:4860:4860::8888','2001:db8::10'))
        ep = {'source_ip':source,'source_port':54111}
        self.manifest = {'schema_version':1,'domain':'yt3.ggpht.com',
                         'remote_ip':remote,'wan_interface':'vtnet1',
                         'baseline':ep,'excluded':deepcopy(ep)}
        self.correlated = True
        self.pair_ok = True
    def safe_plan(self, path):
        return {'analysis_manifest':self.manifest}
    def parse_manifest(self, raw):
        return json.loads(raw)
    def read_file(self, path, limit):
        data = path.read_bytes()
        if len(data) > limit: raise mod.ReadinessError('oversized')
        return data
    MAX_PCAP = 8*1024*1024
    def summarize(self, raw, manifest, phase):
        return {'capture_correlated':self.correlated,'same_sequence_conflicts':int(not self.correlated),
                'outgoing_packets':1,'payload_packets':1}
    def compare(self, manifest, before, after):
        return {'five_tuple_capture_correlated':self.pair_ok,
                'same_remote_endpoint':True,'same_source_port':True,
                'payload_comparison':'DIFFERENT_OR_NONCOMPARABLE_TCP_PAYLOAD_FINGERPRINT'}


class Owner:
    MAX_SNAPSHOT = 262144
    def _parse_snapshot(self, data, label):
        return json.loads(data)
    def _scope(self, snap):
        return snap['scope']


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.paths = {k:Path(self.tmp.name,k) for k in (
            'plan','baseline','excluded','original_owner','excluded_owner','restored_owner',
            'original_exclude','excluded_exclude','restored_exclude')}
        for key in ('plan','baseline','excluded'): self.paths[key].write_bytes(key.encode())
        self.control = Control()
        self.fakes = {'controller':self.control,'pcap':self.control,'owner':Owner()}
        p = patch.object(mod,'companion',side_effect=lambda name:self.fakes[name]);p.start();self.addCleanup(p.stop)
        self.witness(4)

    def witness(self, family):
        self.control = Control(family)
        self.fakes['controller'] = self.fakes['pcap'] = self.control
        for phase, digest in (('original','a'*64),('excluded','b'*64),('restored','a'*64)):
            self.paths[phase+'_owner'].write_text(json.dumps({
                'config_digest':digest,'rule_count':3,'table_count':1,'scope':'native'}))
        before = b'196.216.2.24/29\n'
        remote = (b'142.251.127.198/32\n' if family==4 else b'2001:4860:4860::8888/128\n')
        self.paths['original_exclude'].write_bytes(before)
        self.paths['excluded_exclude'].write_bytes(before+remote)
        self.paths['restored_exclude'].write_bytes(before)

    def completed(self):
        return {k:v for k,v in self.paths.items() if k not in ('plan','baseline')}

    def test_unexecuted_plan_does_not_authorize_anything(self):
        r=mod.review(self.paths['plan'])
        self.assertEqual('A07_PLAN_REVIEW_ONLY',r['status'])
        self.assertFalse(r['phase_b_permitted'])
        self.assertFalse(r['owner_live_authorized'])
        self.assertEqual(('OPEN','OPEN'),(r['installed_a07'],r['installed_a08']))

    def test_baseline_only_is_not_engine_modification(self):
        r=mod.review(self.paths['plan'],self.paths['baseline'])
        self.assertEqual('A07_BASELINE_CAPTURE_REVIEW_ONLY',r['status'])
        self.assertFalse(r['baseline_strategy_modification_proven'])
        self.assertFalse(r['phase_b_permitted'])

    def test_complete_ipv4_and_ipv6_are_still_review_only(self):
        for family in (4,6):
            with self.subTest(family=family):
                self.witness(family)
                r=mod.review(self.paths['plan'],self.paths['baseline'],self.completed())
                self.assertEqual('A07_OFFLINE_AB_RESTORATION_REVIEW_ONLY',r['status'])
                self.assertTrue(r['restoration']['managed_exclude_bytes_equal'])
                self.assertFalse(r['wan_origin_proven'])
                self.assertFalse(r['exclude_effect_proven'])
                self.assertFalse(r['process_continuity_proven'])
                self.assertEqual('OPEN',r['installed_a07'])
                self.assertNotIn('196.216.2.24/29',json.dumps(r))

    def test_unattributed_capture_blocks(self):
        self.control.correlated=False
        self.assertEqual('AMBIGUOUS_BASELINE_CAPTURE_STOP',
                         mod.review(self.paths['plan'],self.paths['baseline'])['next_gate'])
        with self.assertRaises(mod.ReadinessError):
            mod.review(self.paths['plan'],self.paths['baseline'],self.completed())
        self.control.correlated=True;self.control.pair_ok=False
        with self.assertRaises(mod.ReadinessError):
            mod.review(self.paths['plan'],self.paths['baseline'],self.completed())

    def test_native_config_digest_change_and_restore_required(self):
        original=self.paths['excluded_owner'].read_bytes()
        self.paths['excluded_owner'].write_bytes(self.paths['original_owner'].read_bytes())
        with self.assertRaises(mod.ReadinessError):
            mod.review(self.paths['plan'],self.paths['baseline'],self.completed())
        self.paths['excluded_owner'].write_bytes(original)
        for field,value in (('config_digest','c'*64),('rule_count',4),('table_count',2),('scope','other')):
            previous=self.paths['restored_owner'].read_bytes()
            doc=json.loads(previous);doc[field]=value
            self.paths['restored_owner'].write_text(json.dumps(doc))
            with self.assertRaises(mod.ReadinessError):
                mod.review(self.paths['plan'],self.paths['baseline'],self.completed())
            self.paths['restored_owner'].write_bytes(previous)

    def test_target_membership_and_byte_exact_restore(self):
        for name,wrong in (('original_exclude',b'142.251.127.198/32\n'),
                           ('excluded_exclude',b'196.216.2.24/29\n'),
                           ('restored_exclude',b'196.216.2.24/29\n# changed\n'),
                           ('excluded_exclude',b'0.0.0.0/0\n')):
            previous=self.paths[name].read_bytes();self.paths[name].write_bytes(wrong)
            with self.assertRaises(mod.ReadinessError):
                mod.review(self.paths['plan'],self.paths['baseline'],self.completed())
            self.paths[name].write_bytes(previous)

    def test_plan_identity_and_partial_cli_rejected(self):
        self.control.manifest['excluded']['source_port']=54112
        with self.assertRaises(mod.ReadinessError):mod.review(self.paths['plan'])
        with self.assertRaises(mod.ReadinessError):mod.main([
            '--plan',str(self.paths['plan']),'--excluded',str(self.paths['excluded'])])
        with self.assertRaises(mod.ReadinessError):mod.main([
            '--plan',str(self.paths['plan']),'--baseline',str(self.paths['plan'])])

    def test_module_is_offline_only(self):
        tree=ast.parse(SOURCE.read_text());imports=set()
        for node in ast.walk(tree):
            if isinstance(node,ast.Import): imports|={a.name.split('.')[0] for a in node.names}
            elif isinstance(node,ast.ImportFrom) and node.module: imports.add(node.module.split('.')[0])
        self.assertTrue(imports.isdisjoint({'socket','subprocess','requests','urllib'}))
        self.assertNotIn('execute_one(',SOURCE.read_text())


if __name__=='__main__':
    unittest.main(verbosity=2)
