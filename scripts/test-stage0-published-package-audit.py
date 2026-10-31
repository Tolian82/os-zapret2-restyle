#!/usr/bin/env python3
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from hashlib import sha256

spec = importlib.util.spec_from_file_location('audit', str(Path(__file__).with_name('stage0-published-package-audit.py')))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

class PackageAudit(unittest.TestCase):
    def setUp(self):
        self.ctx = tempfile.TemporaryDirectory()
        self.addCleanup(self.ctx.cleanup)
        self.path = Path(self.ctx.name) / 'old.pkg'
        self.manifest = {'name': 'os-zapret2-restyle', 'version': '0.6.1_30', 'abi': 'FreeBSD:15:amd64',
                         'scripts': {h: '#!/bin/sh\necho ok\n' for h in audit.HOOKS},
                         'deps': {'python313': {'version': '0', 'origin': 'lang/python313'}}}
        self.write()

    def write(self, service_mode=0o755):
        with tarfile.open(self.path, 'w:gz') as ar:
            content = json.dumps(self.manifest).encode()
            f = tarfile.TarInfo('+MANIFEST'); f.size = len(content); f.mode = 0o644
            ar.addfile(f, io.BytesIO(content))
            service = b'#!/bin/sh\necho pass\n'
            f = tarfile.TarInfo(audit.WATCH[0]); f.size = len(service); f.mode = service_mode
            ar.addfile(f, io.BytesIO(service))
            elf = b'\x7fELF' + bytes([2,1,1]) + bytes(11) + (62).to_bytes(2, 'little') + bytes(44)
            f = tarfile.TarInfo(audit.WATCH[6]); f.size = len(elf); f.mode = 0o755
            ar.addfile(f, io.BytesIO(elf))

    def scan(self, sha=None):
        return audit.scan(self.path, 'tar', 'os-zapret2-restyle', '0.6.1_30', sha or sha256(self.path.read_bytes()).hexdigest())

    def test_valid_modes_hooks_and_elf(self):
        v = self.scan()
        self.assertEqual(v['archive_entries'], 3)
        self.assertEqual(v['watch'][audit.WATCH[0]]['mode'], '-rwxr-xr-x')
        self.assertEqual(v['private_elf']['machine'], 62)
        self.assertEqual(len(v['hooks']), 4)
        self.assertEqual(v['dependencies']['python313']['version'], '0')
        self.assertEqual(self.scan(), v)

    def test_reject_corrupt_hash_missing_hook_and_identity(self):
        with self.assertRaisesRegex(ValueError, 'wrong package SHA256'):
            self.scan('0'*64)
        del self.manifest['scripts']['post-install']
        self.write()
        with self.assertRaisesRegex(ValueError, 'lifecycle hooks'):
            self.scan()
        self.manifest['scripts']['post-install'] = '#!/bin/sh\n'
        self.manifest['version'] = 'wrong'
        self.write()
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            self.scan()

if __name__ == '__main__':
    unittest.main()
