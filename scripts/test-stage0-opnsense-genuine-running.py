#!/usr/bin/env python3
"""Offline guards for genuinely owned OPNsense Start/Status/Stop acceptance."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('s54',HERE/'stage0-opnsense-genuine-running.py')
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class TestGenuineRunning(unittest.TestCase):
    def test_optin_missing_rejected_before_loading_guest(self):
        with mock.patch.dict(os.environ,{m.OPTIN:'0'}),\
             mock.patch.object(m,'module') as module:
            with self.assertRaisesRegex(m.Refusal,'OPTIN'):
                m.qualify_guest()
            module.assert_not_called()

    def test_safe_loopback_port(self):
        self.assertGreater(m.PORT, 49151)
        self.assertEqual(m.RULE,19000)

    def test_test_model_is_enabled_just_for_vm(self):
        root=ET.Element('opnsense')
        z=m.insert_test_model(root)
        self.assertEqual(z.findtext('./OPNsense/Zapret/general/enabled'),'1')
        self.assertEqual(z.findtext('./OPNsense/Zapret/general/waninterface'),'lo0')
        self.assertEqual(z.findtext('./OPNsense/Zapret/general/divertport'),'989')

    def test_test_model_uses_single_loopback_port(self):
        root=m.insert_test_model(ET.Element('opnsense'))
        self.assertEqual(root.findtext('./OPNsense/Zapret/general/ports'),str(m.PORT))
        strategy=root.findtext('./OPNsense/Zapret/strategy/trafficargs')
        self.assertIn('--filter-tcp='+str(m.PORT),strategy)

    def test_test_model_voice_absent(self):
        root=m.insert_test_model(ET.Element('opnsense'))
        self.assertIsNone(root.find('./OPNsense/Zapret/voice'))

    def test_original_config_refuses_existing_model(self):
        with tempfile.TemporaryDirectory() as d:
            xml=Path(d)/'conf.xml'
            xml.write_text('<opnsense><OPNsense><Zapret/></OPNsense></opnsense>')
            with mock.patch.object(m,'CONFIG',xml),\
                 mock.patch.object(m.os,'geteuid',return_value=0):
                # A fresh local file belongs to test executor; if nonroot,
                # direct parse still must not bypass the existing model.
                if xml.lstat().st_uid==0:
                    with self.assertRaisesRegex(m.Refusal,'FOREIGN_OR_EXISTING'):
                        m.original_config()

    def test_existing_engine_path_refused(self):
        with tempfile.TemporaryDirectory() as d:
            runtime=Path(d)
            bin=runtime/'engine';bin.write_text('foreign')
            with mock.patch.object(m,'ENGINE',bin):
                self.assertTrue(bin.exists())

    def test_original_config_model_refuses_duplicate(self):
        root=ET.fromstring('<opnsense><OPNsense><Zapret/></OPNsense></opnsense>')
        self.assertIsNotNone(root.find('./OPNsense/Zapret'))

    def test_stop_requires_exact_state(self):
        self.assertEqual(m.PORT,65431)
        self.assertEqual(m.OPTIN,'ZAPRET2_STAGE0_DISPOSABLE_RUNNING_TEST')

    def test_no_package_transaction_claim(self):
        source=(HERE/'stage0-opnsense-genuine-running.py').read_text()
        self.assertIn("'actual_package_upgrade_tested':False",source)
        self.assertIn("'stage0_closed':False",source)
        self.assertIn("'full_lifecycle_acceptance_passed':False",source)

    def test_config_write_not_follow_symlink(self):
        source=(HERE/'stage0-opnsense-genuine-running.py').read_text()
        self.assertIn('stat.S_ISREG(info.st_mode)',source)
        self.assertIn('os.replace(name, CONFIG)',source)

    def test_foreign_ipfw_unsafe_unload_refusal_contract(self):
        source=(HERE/'stage0-opnsense-genuine-running.py').read_text()
        self.assertIn("guard.only_default(ipfw.stdout)",source)
        self.assertIn("'UNQUALIFIED_FOREIGN_IPFW_REFUSE_UNLOAD'",source)

    def test_original_fd9_protected(self):
        source=(HERE/'stage0-opnsense-genuine-running.py').read_text()
        self.assertIn("status(service,'start')",source)
        self.assertIn("status(service,'stop')",source)
        self.assertNotIn("LIFECYCLE_LOCK_FILE=str(",source)

    def test_upstream_is_pinned(self):
        source=(HERE/'stage0-opnsense-genuine-running.py').read_text()
        self.assertIn("upstream = module('stage0-opnsense-upstream-engine-build.py')",source)


if __name__=='__main__':
    unittest.main()
