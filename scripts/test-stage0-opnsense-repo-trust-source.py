#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('repo_trust', str(Path(__file__).with_name('stage0-opnsense-repo-trust-source.py')))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

MAIN = '''OPNsense: {
  fingerprints: "/usr/local/etc/pkg/fingerprints/OPNsense",
  url: "%%CORE_PACKAGESITE%%/${ABI}/%%CORE_ABI%%/latest",
  signature_type: "fingerprints",
  priority: 11,
  enabled: yes
}
'''
AUX = MAIN.replace('OPNsense: {', 'OPNsense-aux: {').replace('/latest', '/aux').replace('enabled: yes', 'enabled: no')


class OfficialRepositoryTrustSource(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.main = Path(temp.name) / 'main.conf'
        self.aux = Path(temp.name) / 'aux.conf'
        self.main.write_text(MAIN, encoding='utf-8')
        self.aux.write_text(AUX, encoding='utf-8')

    def test_exact_official_source_and_no_false_host_claim(self):
        report = audit.audit(self.main, self.aux)
        self.assertTrue(report['main_official_source_contract_valid'])
        self.assertTrue(report['aux_official_source_contract_valid'])
        self.assertFalse(report['installed_repository_configuration_qualified'])
        self.assertFalse(report['installed_trusted_fingerprint_qualified'])
        self.assertFalse(report['signed_pkg_catalog_cryptographically_verified'])
        self.assertFalse(report['stage0_closed'])

    def test_main_missing_signature_must_refuse(self):
        self.main.write_text(MAIN.replace('signature_type: "fingerprints"', 'signature_type: "none"'))
        with self.assertRaisesRegex(ValueError, 'source mismatch'):
            audit.audit(self.main, self.aux)

    def test_wrong_fingerprint_directory_refused(self):
        self.main.write_text(MAIN.replace('/fingerprints/OPNsense', '/fingerprints/FreeBSD'))
        with self.assertRaisesRegex(ValueError, 'source mismatch'):
            audit.audit(self.main, self.aux)

    def test_wrong_abi_path_refused(self):
        self.main.write_text(MAIN.replace('${ABI}/%%CORE_ABI%%', 'FreeBSD:15:amd64/26.7'))
        with self.assertRaisesRegex(ValueError, 'source mismatch'):
            audit.audit(self.main, self.aux)

    def test_aux_must_stay_disabled(self):
        self.aux.write_text(AUX.replace('enabled: no', 'enabled: yes'))
        with self.assertRaisesRegex(ValueError, 'source mismatch'):
            audit.audit(self.main, self.aux)

    def test_duplicate_or_injected_directive_refused(self):
        self.main.write_text(MAIN.replace('  priority: 11,', '  priority: 11,\n  signature_type: "none",'))
        with self.assertRaisesRegex(ValueError, 'block shape'):
            audit.audit(self.main, self.aux)
        self.main.write_text(MAIN.replace('  priority: 11,', '  priority: 11,\n  enabled: yes,'))
        with self.assertRaisesRegex(ValueError, 'block shape'):
            audit.audit(self.main, self.aux)

    def test_wrong_name_or_extra_block_refused(self):
        self.main.write_text(MAIN.replace('OPNsense: {', 'FreeBSD: {'))
        with self.assertRaisesRegex(ValueError, 'block shape'):
            audit.audit(self.main, self.aux)
        self.main.write_text(MAIN + AUX)
        with self.assertRaisesRegex(ValueError, 'block shape'):
            audit.audit(self.main, self.aux)

    def test_oversized_and_non_utf8_refused(self):
        self.main.write_bytes(b'x' * 16_385)
        with self.assertRaisesRegex(ValueError, 'oversized'):
            audit.audit(self.main, self.aux)
        self.main.write_bytes(b'\xff\xfe')
        with self.assertRaises(UnicodeDecodeError):
            audit.audit(self.main, self.aux)


if __name__ == '__main__':
    unittest.main()
