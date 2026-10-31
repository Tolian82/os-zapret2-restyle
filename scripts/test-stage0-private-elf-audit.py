#!/usr/bin/env python3
"""Negative and successful static-only ELF analysis without external network."""
from hashlib import sha256
import importlib.util
import io
from pathlib import Path
import shutil
import sys
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('elf_audit', str(Path(__file__).with_name('stage0-private-elf-audit.py')))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class StaticElfAudit(unittest.TestCase):
    def test_parse_dynamic_and_interpreter(self):
        sample = b'''  Class:                             ELF64
  Data:                              2's complement, little endian
  OS/ABI:                            UNIX - FreeBSD
  Machine:                           Advanced Micro Devices X86-64
      [Requesting program interpreter: /libexec/ld-elf.so.1]
 0x0000000000000001 (NEEDED) Shared library: [libssl.so.30]
 0x0000000000000001 (NEEDED) Shared library: [libc.so.7]
 0x000000000000001d (RUNPATH) Library runpath: [/usr/local/lib]
'''
        result = audit.parse_readelf(sample)
        self.assertEqual(result['interpreter'], '/libexec/ld-elf.so.1')
        self.assertEqual(result['needed'], ['libc.so.7', 'libssl.so.30'])
        self.assertEqual(result['dynamic_paths'], {'runpath': '/usr/local/lib'})
        self.assertEqual(result['machine'], 'Advanced Micro Devices X86-64')

    @unittest.skipUnless(shutil.which('readelf') and shutil.which('tar'), 'readelf and tar needed')
    def test_exact_archive_real_elf_and_fail_closed_digests(self):
        candidate = Path(sys.executable).resolve()
        elf = candidate.read_bytes()
        if not elf.startswith(b'\x7fELF'):
            self.skipTest('host Python is not ELF')
        with tempfile.TemporaryDirectory() as temp:
            tar_path = Path(temp) / 'package.tar.gz'
            with tarfile.open(tar_path, 'w:gz') as archive:
                entry = tarfile.TarInfo(audit.PRIVATE_PATH)
                entry.size = len(elf)
                archive.addfile(entry, io.BytesIO(elf))
            pkgsha = audit.hash_file(tar_path)
            elfsha = sha256(elf).hexdigest()
            report = audit.inspect(tar_path, pkgsha, elfsha)
            self.assertEqual(report['elf_class'], 'ELF64')
            self.assertEqual(report['private_elf_sha256'], elfsha)
            self.assertFalse(report['target_opnsense_library_providers_verified'])
            with self.assertRaisesRegex(ValueError, 'package digest mismatch'):
                audit.inspect(tar_path, '0' * 64, elfsha)
            with self.assertRaisesRegex(ValueError, 'private ELF digest mismatch'):
                audit.inspect(tar_path, pkgsha, '0' * 64)


if __name__ == '__main__':
    unittest.main()
