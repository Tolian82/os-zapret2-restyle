#!/usr/bin/env python3
"""Read-only native configctl status: local fail-closed contracts."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

FILE = Path(__file__).with_name('stage2-packaged-configctl-readonly.py')
spec = importlib.util.spec_from_file_location('configctl_proof', FILE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
ACTION = b'''[start]\ncommand:/usr/local/x start\ntype:script\n\n[status]\ncommand:/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh status; exit 0\nparameters:\ntype:script_output\nmessage:zapret2 status\n\n[stop]\ncommand:/usr/local/x stop\ntype:script\n'''


class TestConfigctlReadonly(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.inst = self.root / 'installed' / m.ACTION_REL
        self.src = self.root / 'src' / m.ACTION_REL
        for p in [self.inst, self.src]:
            p.parent.mkdir(parents=True)
            p.write_bytes(ACTION)

    def test_status_section_strict(self):
        self.assertTrue(m.exact_status_action(ACTION))
        for data in (ACTION + b'\n[status]\n', ACTION.replace(b'[status]', b'[absent]'),
                     ACTION.replace(b'status; exit 0', b'start; exit 0'),
                     ACTION.replace(b'type:script_output', b'type:script'),
                     ACTION.replace(b'parameters:\n', b'parameters:%s\n')):
            with self.subTest(data=data[-55:]), self.assertRaises(m.Refusal):
                m.exact_status_action(data)

    def test_file_symlink_and_size_refusal(self):
        self.inst.unlink()
        self.inst.symlink_to(self.src)
        with self.assertRaises(m.Refusal):
            m.safe_bytes(self.inst)
        self.inst.unlink()
        self.inst.write_bytes(b'0' * 65537)
        with self.assertRaises(m.Refusal):
            m.safe_bytes(self.inst)

    def test_pkg_version_and_owner_guard(self):
        with patch.object(m, 'stdout', side_effect=[m.VERSION, m.PACKAGE]):
            m.package_identity(self.root / 'installed')
        for data in (['0.6.2_71'], [m.VERSION, 'foreign-package']):
            with self.subTest(data=data), patch.object(m, 'stdout', side_effect=data):
                with self.assertRaises(m.Refusal):
                    m.package_identity(self.root / 'installed')

    def test_no_disposable_optin_refuses_without_commands(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(m, 'stdout',
                side_effect=AssertionError('unexpected access')):
            with self.assertRaises(m.Refusal):
                m.verify()

    def test_observation_paths_have_no_mutators(self):
        source = FILE.read_text()
        for token in ('SIGTERM', 'os.kill(', 'subprocess.Popen(',
                      "['pkg', 'add'", "['pkg', 'delete'", "['/bin/kill'",
                      "['/sbin/ipfw'"):
            with self.subTest(token=token):
                self.assertNotIn(token, source)


if __name__ == '__main__':
    unittest.main()
