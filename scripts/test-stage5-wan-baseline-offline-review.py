#!/usr/bin/env python3
"""Offline one-capture report contracts, without network or appliance access."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).with_name('stage5-wan-baseline-offline-review.py')
spec = importlib.util.spec_from_file_location('stage5_single_review', SOURCE)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def observation(correlated=True, conflicts=0):
    return {
        'phase': 'baseline', 'family': 'ipv4', 'outgoing_packets': 18,
        'incoming_packets': 13, 'payload_packets': 6,
        'same_sequence_conflicts': conflicts, 'capture_correlated': correlated,
        'unique_payload_fingerprint': 'abcd' * 16,
    }


MANIFEST = {
    'schema_version': 1, 'domain': 'yt3.ggpht.com',
    'remote_ip': '142.251.127.198', 'wan_interface': 'vtnet1',
    'baseline': {'source_ip': '192.168.80.251', 'source_port': 54111},
    'excluded': {'source_ip': '192.168.80.251', 'source_port': 54111},
}


class OfflineBaselineReviewTests(unittest.TestCase):
    def test_correlated_still_does_not_prove_mutation_or_exclude(self):
        r = m.report(observation(), '0' * 64, MANIFEST)
        self.assertEqual('BASELINE_OFFLINE_REVIEW_ONLY', r['status'])
        self.assertEqual('CORRELATED_TCP_PAYLOAD_OBSERVED_ONLY', r['condition'])
        self.assertEqual(18, r['baseline_observation']['outgoing_packets'])
        for key in ('wan_origin_proven', 'tls_sni_proven',
                    'engine_strategy_modification_proven', 'exclude_effect_proven'):
            self.assertIs(r[key], False, key)
        self.assertEqual(('OPEN', 'OPEN'), (r['installed_a07'], r['installed_a08']))
        self.assertNotIn('raw_payload', json.dumps(r))

    def test_conflict_and_missing_payload_are_not_pass(self):
        r = m.report(observation(correlated=False, conflicts=2), '1' * 64, MANIFEST)
        self.assertEqual('AMBIGUOUS_SAME_SEQUENCE_TCP_PAYLOAD', r['condition'])
        self.assertIs(r['engine_strategy_modification_proven'], False)
        r = m.report(observation(correlated=False), '2' * 64, MANIFEST)
        self.assertEqual('INCONCLUSIVE_NO_UNAMBIGUOUS_TCP_PAYLOAD', r['condition'])
        self.assertEqual('OPEN', r['installed_a07'])

    def test_inspect_passes_exact_existing_generated_plan_to_trusted_parser(self):
        class Controller:
            def safe_plan(self, p):
                self.path = p
                return {'analysis_manifest': MANIFEST}
        class Parser:
            MAX_PCAP = 8 * 1024 * 1024
            def parse_manifest(self, raw):
                self.manifest = json.loads(raw)
                return self.manifest
            def read_file(self, path, limit):
                self.read_args = (path, limit)
                return b'local synthetic capture bytes'
            def summarize(self, raw, manifest, phase):
                self.summary_args = (raw, manifest, phase)
                return observation()
        ctl, parser = Controller(), Parser()
        with patch.object(m, 'companion', side_effect=(object(), ctl, parser)) as load:
            r = m.inspect(Path('plan.json'), Path('baseline.pcap'))
        self.assertEqual([m.PLAN_TOOL, m.CONTROLLER, m.ATTRIBUTION],
                         [call.args[1] for call in load.call_args_list])
        self.assertEqual(('baseline.pcap', parser.MAX_PCAP),
                         (str(parser.read_args[0]), parser.read_args[1]))
        self.assertEqual('baseline', parser.summary_args[2])
        self.assertEqual(MANIFEST, parser.manifest)
        self.assertEqual('BASELINE_OFFLINE_REVIEW_ONLY', r['status'])
        self.assertEqual(64, len(r['capture_sha256']))

    def test_companion_refuses_missing_symlink_and_hardlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp, 'stub.py')
            with self.assertRaises(m.ReviewError):
                m.companion('missing_companion', p)
            p.write_text('VALUE = 42\n')
            loaded = m.companion('safe_companion', p)
            self.assertEqual(42, loaded.VALUE)
            symlink = Path(tmp, 'sym.py'); symlink.symlink_to(p)
            with self.assertRaises(m.ReviewError):
                m.companion('unsafe_symlink', symlink)
            hard = Path(tmp, 'hard.py'); os.link(p, hard)
            with self.assertRaises(m.ReviewError):
                m.companion('unsafe_hardlink', p)

    def test_cli_requires_two_distinct_paths_without_loading_any_companion(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(m, 'companion') as loader:
            f = Path(tmp, 'same.json'); f.write_text('{}')
            with self.assertRaisesRegex(m.ReviewError, 'distinct'):
                m.main(['--plan', str(f), '--baseline', str(f)])
            loader.assert_not_called()

    def test_cli_prints_sanitized_summary_not_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = Path(tmp, 'plan.json'); plan.write_text('{}')
            cap = Path(tmp, 'baseline.pcap'); cap.write_bytes(b'not actually parsed')
            with patch.object(m, 'inspect', return_value=m.report(observation(), 'a' * 64, MANIFEST)):
                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(0, m.main(['--plan', str(plan), '--baseline', str(cap)]))
            decoded = json.loads(out.getvalue())
            self.assertFalse(decoded['exclude_effect_proven'])
            self.assertEqual('OPEN', decoded['installed_a07'])

    def test_wrapper_contains_no_live_network_or_firewall_imports(self):
        import ast
        tree = ast.parse(SOURCE.read_text())
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(x.name.split('.')[0] for x in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add((node.module or '').split('.')[0])
        self.assertTrue(imports.isdisjoint({'socket', 'subprocess', 'requests', 'urllib'}))


if __name__ == '__main__':
    unittest.main(verbosity=2)
