#!/usr/bin/env python3
"""No network/appliance required: fail-closed target qualification contracts."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location("witness", str(Path(__file__).with_name("stage0-target-trust-runtime.py")))
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)

REPO_BLOCK = """Repositories:
  OPNsense: {
    url             : "pkg+https://mirror.invalid/opnsense/FreeBSD:15:amd64/26.7/latest",
    enabled         : yes,
    priority        : 11,
    signature_type  : "FINGERPRINTS",
    fingerprints    : "/usr/local/etc/pkg/fingerprints/OPNsense"
  }
"""

def ret(stdout='', rc=0):
    return type("Result", (), {"stdout":stdout, "returncode":rc})()


class Stage0TargetWitnessTests(unittest.TestCase):
    def test_effective_signed_repo_positive(self):
        self.assertTrue(w.parse_pkg_repos(REPO_BLOCK))

    def test_unsigned_foreign_or_wrong_abi_repo_refused(self):
        for value in [
            REPO_BLOCK.replace('FINGERPRINTS', 'none'),
            REPO_BLOCK.replace('enabled         : yes', 'enabled         : no'),
            REPO_BLOCK.replace('/fingerprints/OPNsense', '/fingerprints/FreeBSD'),
            REPO_BLOCK.replace('/26.7/latest', '/27.1/latest'),
            REPO_BLOCK + REPO_BLOCK,
        ]:
            with self.subTest(value=value[-70:]):
                with self.assertRaises(w.Refusal):
                    w.parse_pkg_repos(value)

    def test_duplicate_field_or_malformed_config_refused(self):
        duplicate = REPO_BLOCK.replace('    enabled         : yes,',
                                       '    enabled         : yes,\n    enabled         : yes,')
        with self.assertRaisesRegex(w.Refusal, 'FIELDS_AMBIGUOUS'):
            w.parse_pkg_repos(duplicate)
        with self.assertRaisesRegex(w.Refusal, 'BLOCK_UNPARSEABLE'):
            w.parse_pkg_repos(REPO_BLOCK.replace('  }\n', '  MISSING\n'))

    def test_trusted_key_exists_but_is_not_independent_official_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'trusted').mkdir()
            key = Path(tmp) / 'trusted' / 'key'
            key.write_text('function: sha256\nfingerprint: test\n')
            self.assertEqual(w.trusted_key_count(tmp), 1)
            key.chmod(0o666)
            with self.assertRaisesRegex(w.Refusal, 'NO_READABLE'):
                w.trusted_key_count(tmp)
            key.chmod(0o644)
            key.unlink()
            key.symlink_to('/dev/null')
            with self.assertRaisesRegex(w.Refusal, 'SYMLINKED'):
                w.trusted_key_count(tmp)

    def test_isolated_catalog_update_only_and_provider_provenance(self):
        calls = []
        def fake_cmd(argv, env=None, timeout=30):
            calls.append((argv, dict(env or {})))
            if argv == ['opnsense-version', '-a']:
                return ret('26.7\n')
            if argv == ['pkg', 'config', 'ABI']:
                return ret('FreeBSD:15:amd64\n')
            if argv[:3] == ['pkg', 'query', '%n|%v|%o']:
                return ret('os-zapret2-restyle|0.6.2_1|opnsense/os-zapret2-restyle\n')
            if argv == ['pkg', '-vv']:
                return ret(REPO_BLOCK)
            if argv[:2] == ['pkg','update']:
                self.assertTrue(env['PKG_DBDIR'].startswith('/tmp/'))
                self.assertNotEqual(env['PKG_DBDIR'], '/var/db/pkg')
                self.assertTrue(Path(env['PKG_CACHEDIR']).is_dir())
                return ret('verified ephemeral repo')
            if 'rquery' in argv:
                name = argv[-1]
                return ret(f'{name}|1.2|category/{name}|OPNsense\n')
            raise AssertionError(argv)
        with mock.patch.object(w, 'cmd', side_effect=fake_cmd), \
             mock.patch.object(w, 'trusted_key_count', return_value=1):
            result = w.verify_catalog()
        self.assertTrue(result['catalog_update_in_isolated_database'])
        self.assertFalse(result['official_trust_anchor_independently_compared'])
        self.assertEqual(set(result['provider_candidates']),set(w.PROVIDERS))
        self.assertEqual(len([x for x in calls if x[0][:2] == ['pkg','update']]), 1)
        self.assertFalse(Path(next(e['PKG_DBDIR'] for a,e in calls if a[:2]==['pkg','update'])).exists())

    def test_invalid_signature_update_is_fail_closed(self):
        def fake_cmd(argv, env=None, timeout=30):
            if argv == ['opnsense-version', '-a']:
                return ret('26.7')
            if argv == ['pkg', 'config', 'ABI']:
                return ret(w.ABI)
            if argv[:3] == ['pkg', 'query', '%n|%v|%o']:
                return ret('os-zapret2-restyle|0.6.2_1|opnsense/os-zapret2-restyle')
            if argv == ['pkg', '-vv']:
                return ret(REPO_BLOCK)
            if argv[:2] == ['pkg', 'update']:
                return ret('', 1)
            self.fail(f'Unexpected call: {argv}')
        with mock.patch.object(w, 'cmd', side_effect=fake_cmd), \
             mock.patch.object(w, 'trusted_key_count', return_value=1):
            with self.assertRaisesRegex(w.Refusal, 'ISOLATED_SIGNED_CATALOG_UPDATE_FAILED'):
                w.verify_catalog()

    def test_ldd_sonames_are_all_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            lines=[]
            for so in w.SONAMES:
                file=Path(tmp)/so
                file.write_bytes(b'ELF')
                lines.append(f'    {so} => {file} (0x1234)')
            self.assertEqual(len(w.parse_ldd('\n'.join(lines))),6)
            with self.assertRaisesRegex(w.Refusal, 'ELF_LIBRARY_UNRESOLVED'):
                w.parse_ldd('\n'.join(lines[:-1]))
            with self.assertRaisesRegex(w.Refusal, 'ELF_LIBRARY_UNRESOLVED'):
                w.parse_ldd('\n'.join(lines).replace(' (0x1234)', ' not found (0x1234)', 1))

    def test_wrong_elf_digest_refused_before_any_process_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            elf=Path(tmp)/'curl-impersonate'
            elf.write_bytes(b'invalid')
            with mock.patch.object(w, 'ELF', elf), mock.patch.object(w, 'cmd') as c:
                with self.assertRaisesRegex(w.Refusal, 'DIGEST_MISMATCH'):
                    w.verify_elf()
                c.assert_not_called()


if __name__ == '__main__':
    unittest.main()
