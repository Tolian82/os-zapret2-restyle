#!/usr/bin/env python3
"""Offline negative contracts for the read-only OPNsense firmware route boundary."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).with_name('stage0-opnsense-firmware-admission.py')
spec = importlib.util.spec_from_file_location('stage0_firmware_admission', SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class AdmissionTests(unittest.TestCase):
    def test_all_firmware_routes_explicitly_classified(self):
        self.assertEqual(set(m.FIRMWARE_ROUTES) | {'auto-update', 'direct-pkg-root'},
                         set(m.CLASSIFICATIONS))

    def test_all_routes_refuse_even_with_apparent_cold_evidence(self):
        for route in m.CLASSIFICATIONS:
            with self.subTest(route=route):
                with self.assertRaisesRegex(m.Refusal,
                                            'NO_EXCLUSIVE_OWNER_AWARE_PKG_TRANSACTION'):
                    m.admit_product_update(route, {'status': 'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY'})

    def test_unknown_route_refused(self):
        with self.assertRaisesRegex(m.Refusal, 'UNKNOWN_PACKAGE_ENTRYPOINT'):
            m.admit_product_update('surprise')

    def test_root_bypass_not_mislabeled(self):
        self.assertEqual(m.CLASSIFICATIONS['direct-pkg-root'],
                         'UNCOORDINATED_ROOT_PKG_UNSUPPORTED')
        self.assertEqual(m.CLASSIFICATIONS['unlock'],
                         'PRIVILEGED_PACKAGE_UNLOCK_BYPASS')

    def test_launcher_flock_cannot_be_substituted_for_fd9(self):
        with self.assertRaisesRegex(m.Refusal, 'FIRMWARE_LAUNCHER_LOCK_SEMANTICS_CHANGED'):
            m.verify_launcher('#!/bin/sh\n/usr/bin/lockf /tmp/other')

    def test_unexpected_firmware_source_refused(self):
        with self.assertRaisesRegex(m.Refusal, 'UNEXPECTED_FIRMWARE_IMPLEMENTATION'):
            m.verify_source('install', '#!/bin/sh\nexit 0')

    def test_unknown_firmware_script_refused(self):
        with self.assertRaisesRegex(m.Refusal, 'UNRECOGNIZED_FIRMWARE_ROUTE'):
            m.verify_source('mystery', '#!/bin/sh')

    def test_action_command_mismatch_refused(self):
        sample = ''.join('[' + route + ']\ncommand:/bin/true\nparameters:%s\n'
                         for route in m.FIRMWARE_ROUTES)
        sample += '[auto-update]\ncommand:/usr/local/etc/rc.firmware -r 1500\n'
        with self.assertRaisesRegex(m.Refusal, 'UNEXPECTED_FIRMWARE_ACTION'):
            m.verify_actions(sample)

    def test_missing_actions_refused(self):
        with self.assertRaises(m.Refusal):
            m.verify_actions('[install]\ncommand:/bin/true\n')

    def test_reject_symlinked_firmware_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'actual').write_bytes(b'a' * 400)
            (root / 'pointer').symlink_to(root / 'actual')
            with self.assertRaisesRegex(m.Refusal, 'UNQUALIFIED_FIRMWARE_FILE'):
                m.verify_regular(root / 'pointer')

    def test_reject_truncated_firmware_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'install.sh'
            p.write_bytes(b'#!/bin/sh\n')
            with self.assertRaisesRegex(m.Refusal, 'INVALID_FIRMWARE_FILE_SIZE'):
                m.verify_regular(p)

    def test_no_mutating_entrypoints_in_readonly_audit(self):
        text = SOURCE.read_text()
        for forbidden in ('subprocess.run(', 'subprocess.Popen(', 'os.system(',
                          'os.execv(', "'pkg', 'add'", "'pkg', 'delete'",
                          "'configctl', 'zapret'", "'stop'", "'apply'"):
            self.assertNotIn(forbidden, text)


if __name__ == '__main__':
    unittest.main()
