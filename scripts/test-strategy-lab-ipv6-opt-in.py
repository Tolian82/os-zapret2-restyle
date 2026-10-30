#!/usr/bin/env python3
"""Stage 6: real job IPv6 request persistence and real network-probe gating."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / 'src/opnsense/scripts/OPNsense/Zapret'
if not BACKEND.is_dir():
    raise SystemExit('RUN_REQUIRES_PROJECT_CHECKOUT: repository sources missing')
sys.path.insert(0, str(BACKEND))
from strategy_lab_py import probe, state


class ProbeStub:
    ok = True
    duration_ms = 1
    @staticmethod
    def evidence():
        return {'test': True}


def run_network(tmp: Path, selected: str | None):
    if selected is not None:
        (tmp / 'ipv6-enabled').write_text(selected + '\n', encoding='ascii')
    calls = []
    def curl(host, *, scheme, family):
        calls.append(family)
        return ProbeStub()
    with (patch.object(probe.request, 'binary', return_value='/bin/true'),
          patch.object(probe.request, 'ipv6_default_route', return_value=(True, ProbeStub())),
          patch.object(probe.request, 'curl_request', side_effect=curl),
          patch.object(probe.request, 'quic_ipv4_request', return_value=ProbeStub()),
          patch.object(probe.request, 'combined_log', return_value=''),
          patch.object(probe.telemetry, 'record')):
        rc = probe._network(tmp, tmp / 'network.json')
    assert rc == 0, rc
    return json.loads((tmp / 'network.json').read_text()), calls


class OptIn(unittest.TestCase):
    def test_persisted_off_and_on(self):
        for choice, enabled in (('0', False), ('1', True)):
            with self.subTest(choice=choice), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / 'job.ABCDEF'
                root.mkdir()
                state.initialize('job.ABCDEF', str(root / 'status.json'), str(root / 'events.ndjson'),
                                 'example.org', 'standard', 'ru', choice)
                record = json.loads((root / 'status.json').read_text())
                self.assertIs(record['ipv6_enabled'], enabled)

    def test_invalid_selection_rejected_without_saved_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'job.ABCDEF'
            root.mkdir()
            with self.assertRaises(state.UsageError):
                state.initialize('job.ABCDEF', str(root / 'status.json'), str(root / 'events.ndjson'),
                                 'example.org', 'standard', 'en', 'yes')
            self.assertFalse((root / 'status.json').exists())

    def test_off_or_unset_never_sends_ipv6_probe(self):
        for selection in (None, '0'):
            with self.subTest(selection=selection), tempfile.TemporaryDirectory() as tmp:
                network, calls = run_network(Path(tmp), selection)
                self.assertEqual(network['ipv4'], 'available')
                self.assertEqual(network['ipv6'], 'unavailable')
                self.assertEqual(calls, ['ipv4'])

    def test_selected_ipv6_probes_both_families(self):
        with tempfile.TemporaryDirectory() as tmp:
            network, calls = run_network(Path(tmp), '1')
            self.assertEqual(network['ipv6'], 'available')
            self.assertCountEqual(calls, ['ipv4', 'ipv6'])

    def test_invalid_saved_choice_fails_closed(self):
        for value in ('', 'yes', '1\n0', '2'):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / 'ipv6-enabled').write_text(value, encoding='ascii')
                with self.assertRaises(probe.UsageError):
                    run_network(root, None)

    def test_view_api_configd_launcher_binding(self):
        src = BACKEND.parents[2]
        view = (src / 'mvc/app/views/OPNsense/Zapret/diagnostics.volt').read_text()
        controller = (src / 'mvc/app/controllers/OPNsense/Zapret/Api/StrategyLabController.php').read_text()
        actions = (src / 'service/conf/actions.d/actions_zapret.conf').read_text()
        launch = (BACKEND / 'strategy_lab/launch.sh').read_text()
        self.assertIn('id="strategyLabIpv6Enabled"', view)
        self.assertIn('ipv6_enabled:ipv6Enabled', view)
        self.assertIn("getPost('ipv6_enabled'", controller)
        self.assertIn('_strategy_lab_ipv6_enabled="$9"', launch)
        self.assertIn('ipv6-enabled', launch)
        self.assertIn('parameters:%s %s %s %s %s %s %s %s', actions)


if __name__ == '__main__':
    unittest.main(verbosity=2)
