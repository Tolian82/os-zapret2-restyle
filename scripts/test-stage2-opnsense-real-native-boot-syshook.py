#!/usr/bin/env python3
"""Off-guest refusal contracts for real native shutdown and start syshooks."""
import importlib.util
import os
from pathlib import Path
from unittest.mock import patch
import unittest

SOURCE = Path(__file__).with_name('stage2-opnsense-real-native-boot-syshook.py')
spec = importlib.util.spec_from_file_location('real_native_boot', SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fixture():
    old = 'foo 2026-11-05 before'
    new = 'bar 2026-11-05 after'
    stop = {'bootid': old, 'status': 'zapret is not running',
            'pid': 'ABSENT', 'ipfw': '65535 allow ip from any to any'}
    start = {'bootid': new, 'status': 'zapret is running as pid 200',
             'pid': '200',
             'ipfw': '19000 divert 989 tcp from any to any 65431 out via lo0\n'
                     '65535 allow ip from any to any'}
    record = {'prepared_boot_id': old, 'old_pid': 100}
    live = {'pid': 200, 'rules': [
        '19000 divert 989 tcp from any to any 65431 out via lo0']}
    return record, stop, start, live, new


class ActualBootContracts(unittest.TestCase):
    def test_exact_valid_observed_shutdown_and_new_boot(self):
        self.assertTrue(mod.prove_transition(*fixture()))

    def test_reject_same_kernel_boot(self):
        record, stop, start, live, new = fixture()
        with self.assertRaisesRegex(mod.Refusal, 'DISTINCT_KERNEL'):
            mod.prove_transition(record, stop, start, live, record['prepared_boot_id'])

    def test_reject_shutdown_observer_from_new_boot(self):
        record, stop, start, live, new = fixture()
        stop['bootid'] = new
        with self.assertRaisesRegex(mod.Refusal, 'DISTINCT_KERNEL'):
            mod.prove_transition(record, stop, start, live, new)

    def test_reject_missing_boot_syshook_observation(self):
        record, stop, start, live, new = fixture()
        start['bootid'] = ''
        with self.assertRaisesRegex(mod.Refusal, 'DISTINCT_KERNEL'):
            mod.prove_transition(record, stop, start, live, new)

    def test_reject_shutdown_left_owned_engine(self):
        record, stop, start, live, new = fixture()
        stop['pid'] = '100'
        with self.assertRaisesRegex(mod.Refusal, 'STOP_HOOK_LEFT_OWNED'):
            mod.prove_transition(record, stop, start, live, new)

    def test_reject_shutdown_left_plugin_ipfw_rule(self):
        record, stop, start, live, new = fixture()
        stop['ipfw'] = live['rules'][0]
        with self.assertRaisesRegex(mod.Refusal, 'STOP_HOOK_LEFT_OWNED'):
            mod.prove_transition(record, stop, start, live, new)

    def test_reject_old_pid_reused_after_reboot(self):
        record, stop, start, live, new = fixture()
        record['old_pid'] = 200
        with self.assertRaisesRegex(mod.Refusal, 'BOOT_START_DID_NOT_RESTORE'):
            mod.prove_transition(record, stop, start, live, new)

    def test_reject_foreign_start_pid(self):
        record, stop, start, live, new = fixture()
        start['status'] = 'zapret is running as pid 201'
        with self.assertRaisesRegex(mod.Refusal, 'BOOT_START_DID_NOT_RESTORE'):
            mod.prove_transition(record, stop, start, live, new)

    def test_reject_start_missing_ipfw(self):
        record, stop, start, live, new = fixture()
        start['ipfw'] = ''
        with self.assertRaisesRegex(mod.Refusal, 'DID_NOT_RESTORE_LOOPBACK_IPFW'):
            mod.prove_transition(record, stop, start, live, new)

    def test_reject_wan_intercept_rule(self):
        record, stop, start, live, new = fixture()
        start['ipfw'] = '19000 divert 989 tcp from any to any 65431 out via vtnet1'
        with self.assertRaisesRegex(mod.Refusal, 'DID_NOT_RESTORE_LOOPBACK_IPFW'):
            mod.prove_transition(record, stop, start, live, new)

    def test_reject_second_plugin_rule(self):
        record, stop, start, live, new = fixture()
        start['ipfw'] += '\n19001 divert 989 udp from any to any'
        with self.assertRaisesRegex(mod.Refusal, 'DID_NOT_RESTORE_LOOPBACK_IPFW'):
            mod.prove_transition(record, stop, start, live, new)

    def test_reject_observed_rule_mismatch_with_live_rule(self):
        record, stop, start, live, new = fixture()
        live['rules'] = ['19000 divert 989 tcp from any to any 65431 via lo0']
        with self.assertRaisesRegex(mod.Refusal, 'POSTBOOT_LIVE_RULE_DIFFERS'):
            mod.prove_transition(record, stop, start, live, new)

    def test_witness_scripts_are_passive_and_order_after_product(self):
        for phase in ('start', 'stop'):
            script = mod.observe_bytes(phase).decode()
            self.assertTrue(script.startswith('#!/bin/sh\n'))
            self.assertIn('configctl zapret status', script)
            self.assertIn('.done', script)
            self.assertNotIn('configctl zapret start', script)
            self.assertNotIn('configctl zapret stop', script)
            self.assertEqual(mod.PRODUCT[phase].name, '20-zapret')
            self.assertTrue(mod.HOOKS[phase].name.startswith('21-'))

    def test_existing_native_config_policy_allows_revision_and_spacing_only(self):
        source = SOURCE.with_name('stage2-opnsense-real-native-stopped-upgrade.py')
        policy_spec = importlib.util.spec_from_file_location('native_boot_xml_policy', source)
        policy = importlib.util.module_from_spec(policy_spec)
        policy_spec.loader.exec_module(policy)
        before = (b'<opnsense><revision><time>1</time></revision>'
                  b'<system><hostname>guest</hostname></system>'
                  b'<OPNsense><Zapret><enabled>1</enabled></Zapret></OPNsense></opnsense>')
        after = (b'<opnsense>\n  <revision><time>2</time></revision>\n'
                 b'<system>\n  <hostname>guest</hostname>\n</system>\n'
                 b'<OPNsense><Zapret><enabled>1</enabled></Zapret></OPNsense></opnsense>')
        self.assertEqual(policy.normalized_config(before),
                         policy.normalized_config(after))
        for changed in (after.replace(b'<enabled>1</enabled>',
                                      b'<enabled>0</enabled>'),
                        after.replace(b'<hostname>guest</hostname>',
                                      b'<hostname>foreign</hostname>')):
            self.assertNotEqual(policy.normalized_config(before),
                                policy.normalized_config(changed))

    def test_redacted_semantic_diagnostic_reveals_only_structure(self):
        before = (b'<opnsense><OPNsense><Zapret><enabled>1</enabled></Zapret>'
                  b'<PrivateService><password>SECRET_ORIGINAL</password></PrivateService>'
                  b'</OPNsense></opnsense>')
        after = (b'<opnsense><OPNsense><Zapret><enabled>1</enabled></Zapret>'
                 b'<PrivateService><password>SECRET_CHANGED</password></PrivateService>'
                 b'</OPNsense></opnsense>')
        summary = mod.redacted_semantic_leaf_delta(before, after)
        self.assertTrue(summary['zapret_tree_identical'])
        self.assertTrue(summary['changed_paths'])
        self.assertIn('text', [item['kind'] for item in summary['changed_paths']])
        self.assertNotIn('PrivateService', str(summary))
        self.assertNotIn('password', str(summary))
        self.assertNotIn('SECRET_', str(summary))

    def test_redacted_semantic_diagnostic_identifies_zapret_drift(self):
        before = b'<opnsense><OPNsense><Zapret><enabled>1</enabled></Zapret></OPNsense></opnsense>'
        after = b'<opnsense><OPNsense><Zapret><enabled>0</enabled></Zapret></OPNsense></opnsense>'
        summary = mod.redacted_semantic_leaf_delta(before, after)
        self.assertFalse(summary['zapret_tree_identical'])
        self.assertTrue(any('Zapret' in item['path'] for item in summary['changed_paths']))

    @staticmethod
    def native_fixture(*, ports='65431', traffic='--filter-tcp=65431',
                       foreign='keep', version='', enabled='1'):
        v = ' version="2.0.0"' if version else ''
        return (f'<opnsense><revision><time>1</time></revision>'
                f'<OPNsense><Zapret{v}><general><enabled>{enabled}</enabled>'
                f'<waninterface>lo0</waninterface><ports>{ports}</ports>'
                f'<divertport>989</divertport></general>'
                f'<strategy><trafficargs>{traffic}</trafficargs>'
                f'<extraargs></extraargs></strategy>'
                f'<hostlist><mode>all</mode></hostlist></Zapret></OPNsense>'
                f'<system><hostname>{foreign}</hostname></system></opnsense>'
                ).encode()

    def test_model_fixture_canonicalization_preserves_foreign_scope(self):
        before = self.native_fixture()
        after = self.native_fixture(foreign='keep', version='yes',
                                    traffic='--filter-tcp=65431')
        self.assertEqual(mod.config_except_model(before),
                         mod.config_except_model(after))
        self.assertEqual(mod.protected_model_values(before),
                         mod.protected_model_values(after))

    def test_model_fixture_refuses_foreign_config_drift(self):
        self.assertNotEqual(
            mod.config_except_model(self.native_fixture()),
            mod.config_except_model(self.native_fixture(foreign='changed')))

    def test_model_fixture_rejects_modified_strategies(self):
        for data in (self.native_fixture(ports='443'),
                     self.native_fixture(traffic='--filter-tcp=443'),
                     self.native_fixture(enabled='0')):
            with self.assertRaisesRegex(mod.Refusal, 'STRATEGIES_NOT_APPROVED'):
                mod.protected_model_values(data)

    def test_model_fixture_rejects_missing_or_duplicated_scope(self):
        source = self.native_fixture()
        with self.assertRaisesRegex(mod.Refusal, 'MODEL_SCOPE_AMBIGUOUS'):
            mod.config_except_model(source.replace(b'</Zapret>',
                                                  b'</Zapret><Zapret/>'))
        with self.assertRaisesRegex(mod.Refusal, 'REQUIRED_FIELD_MISSING'):
            mod.protected_model_values(source.replace(b'<extraargs></extraargs>', b''))

    def test_requires_optin_before_guest_access(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(
                mod.active, 'guest_preflight',
                side_effect=AssertionError('must not touch device')):
            with self.assertRaisesRegex(mod.Refusal, 'EXPLICIT_DISPOSABLE'):
                mod.gate()


if __name__ == '__main__':
    unittest.main()
