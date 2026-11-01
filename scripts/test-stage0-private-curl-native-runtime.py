#!/usr/bin/env python3
"""Offline negative contract tests for immutable published curl native witness."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
from unittest import TestCase, main, mock

module_spec = importlib.util.spec_from_file_location(
    'native_curl', str(Path(__file__).with_name('stage0-private-curl-native-runtime.py')))
audit = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(audit)

GOOD_LDD = '\n'.join('    %s => /lib/%s (0xabc)' % (n, n) for n in audit.NEEDED)


class NativePrivateCurlContract(TestCase):
    def test_required_sonames_all_resolve(self):
        found = audit.interpret_ldd(GOOD_LDD)
        self.assertEqual(set(found), set(audit.NEEDED))
        self.assertTrue(all(v.startswith('/lib/') for v in found.values()))

    def test_missing_and_unresolved_sonames_are_refused(self):
        with self.assertRaisesRegex(ValueError, 'missing required'):
            audit.interpret_ldd(GOOD_LDD.replace('libthr.so.3 =>', 'libother.so.3 =>'))
        with self.assertRaisesRegex(ValueError, 'not resolved'):
            audit.interpret_ldd(GOOD_LDD.replace('/lib/libm.so.5', 'not found'))

    def test_http3_and_https_are_mandatory(self):
        audit.check_http3_version('curl 8.0\nProtocols: http https\nFeatures: HTTP3 SSL\n')
        with self.assertRaisesRegex(ValueError, 'HTTP3'):
            audit.check_http3_version('curl\nProtocols: http https\nFeatures: SSL\n')
        with self.assertRaisesRegex(ValueError, 'HTTPS'):
            audit.check_http3_version('curl\nProtocols: http\nFeatures: HTTP3\n')

    def test_bad_archive_digest_fails_before_extract(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / 'invalid.pkg'
            archive.write_bytes(b'not a published package')
            with mock.patch.object(audit, 'get_archive_member') as extract:
                with self.assertRaisesRegex(ValueError, 'archive SHA-256 mismatch'):
                    audit.confirm_archives(archive)
                extract.assert_not_called()

    def test_positive_fixture_and_bad_elf_or_profile_refused(self):
        raw_archive = b'controlled historical package fixture'
        raw_binary = b'\x7fELF' + b'\0' * 90
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / 'fixture.pkg'
            pkg.write_bytes(raw_archive)
            with mock.patch.object(audit, 'PACKAGE_SHA256', hashlib.sha256(raw_archive).hexdigest()), \
                    mock.patch.object(audit, 'ELF_SHA256', hashlib.sha256(raw_binary).hexdigest()):
                with mock.patch.object(audit, 'get_archive_member',
                                       side_effect=[raw_binary, b'chrome133\n']):
                    binary, profile = audit.confirm_archives(pkg)
                    self.assertEqual(binary, raw_binary)
                    self.assertEqual(profile, 'chrome133')
                with mock.patch.object(audit, 'get_archive_member',
                                       side_effect=[b'\x7fELF' + b'evil', b'chrome133\n']):
                    with self.assertRaisesRegex(ValueError, 'executable SHA-256'):
                        audit.confirm_archives(pkg)
                with mock.patch.object(audit, 'get_archive_member',
                                       side_effect=[raw_binary, b'chrome133;rm -rf /\n']):
                    with self.assertRaisesRegex(ValueError, 'profile format'):
                        audit.confirm_archives(pkg)

    def test_not_a_generic_freebsd_or_ubuntu_qualification(self):
        self.assertEqual(audit.PACKAGE_SHA256,
                         '1e21fbcac847529b94fea940241b4da7f86a42d33c129b7003ad04a72f4e5a0f')
        self.assertEqual(audit.ELF_SHA256,
                         'e4af7ba05b6ad8dd997aefeae3a9c15a08be2700534d043cd93c7987f97c451f')
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(audit.os, 'uname') as fake:
                fake.return_value = type('U', (), {'sysname': 'Linux', 'machine': 'x86_64'})()
                with self.assertRaisesRegex(ValueError, 'actual FreeBSD'):
                    audit.run_native(Path(tmp) / 'absent.pkg', Path(tmp) / 'report.json')


if __name__ == '__main__':
    main()
