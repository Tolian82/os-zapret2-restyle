#!/usr/bin/env python3
"""#1052 P2k8b: physical protected known-HOSTLIST ownership sources."""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

BACKEND = Path(__file__).resolve().parents[1] / 'src/opnsense/scripts/OPNsense/Zapret/backend'
sys.path.insert(0, str(BACKEND))
from auto_detect_owned_sources import (bootstrap_empty, read_owned, snapshot,
                                       OwnedSourcesRefused)
from auto_detect_destination_commit import DestinationRefused

class OwnedSourceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='p2k8b-owned-')
        self.addCleanup(tmp.cleanup)
        self.parent = Path(tmp.name)
        self.parent.chmod(0o700)
        self.root = self.parent / 'auto-detect-owned'
        self.final = self.parent / 'auto-domains.txt'
        self.lock = self.parent / '.auto-domains.lock'
        self.uid = os.geteuid()
        self.final.write_text('!^excluded.example\nmanual.example\n', encoding='utf-8')
        self.final.chmod(0o600)

    def read(self):
        return snapshot(self.final, self.lock, self.root, owner_uid=self.uid)

    def init(self):
        bootstrap_empty(self.root, original_config_sha256='a'*64,
                        owner_uid=self.uid, authorized_clean_start=True)

    def test_uninitialized_is_unknown_not_empty_and_never_creates(self):
        v=self.read()
        self.assertEqual(v['result'],'ok')
        self.assertIsNone(v['auto_owned_components'])
        self.assertFalse(v['auto_owned_complete'])
        self.assertEqual(v['content'],'!^excluded.example\nmanual.example\n')
        self.assertFalse(self.root.exists())

    def test_missing_original_state_parent_is_uninitialized_not_an_error(self):
        cold = self.parent / 'not-provisioned' / 'auto-detect-owned'
        self.assertIsNone(read_owned(cold, owner_uid=self.uid))
        self.assertFalse(cold.parent.exists())
        with self.assertRaisesRegex(OwnedSourcesRefused,'ownership_directory_unavailable'):
            bootstrap_empty(cold, original_config_sha256='a'*64,
                            owner_uid=self.uid, authorized_clean_start=True)
        parent_link = self.parent / 'unsafe-parent'
        parent_link.symlink_to(self.parent, target_is_directory=True)
        with self.assertRaisesRegex(OwnedSourcesRefused, 'unsafe_ownership_directory'):
            read_owned(parent_link / 'owned', owner_uid=self.uid)

    def test_explicit_seal_of_clean_ownership_and_exact_snapshot(self):
        self.init()
        v=self.read()
        self.assertTrue(v['auto_owned_complete'])
        self.assertEqual(v['auto_owned_components'],{'youtube':'','user':''})
        self.assertEqual(set(os.listdir(self.root)),{'manifest.json','youtube.txt','user.txt'})
        self.assertEqual(self.root.stat().st_mode & 0o777,0o700)
        self.assertEqual((self.root/'manifest.json').stat().st_mode & 0o777,0o600)
        self.assertIn('"initial_config_sha256":"'+ 'a'*64 +'"',
                      (self.root/'manifest.json').read_text())
        self.assertEqual(v['revision'],__import__('hashlib').sha256(b'present\0'+self.final.read_bytes()).hexdigest())
        self.assertEqual(self.final.read_text(),'!^excluded.example\nmanual.example\n')

    def test_bootstrap_cannot_be_implicit_or_repeated(self):
        with self.assertRaisesRegex(OwnedSourcesRefused,'authority_required'):
            bootstrap_empty(self.root, original_config_sha256='a'*64,owner_uid=self.uid)
        self.assertFalse(self.root.exists())
        self.init()
        with self.assertRaisesRegex(OwnedSourcesRefused,'ownership_already'):
            self.init()

    def test_explicit_owned_rows_stay_separate_from_manual(self):
        self.init()
        (self.root/'youtube.txt').write_text('video.example\n')
        (self.root/'user.txt').write_text('login.example\n')
        r=self.read()
        self.assertEqual(r['auto_owned_components'],{'youtube':'video.example\n','user':'login.example\n'})
        self.assertNotIn('video.example',r['content'])

    def test_modifier_duplicate_and_case_tampering_refuse(self):
        for raw in ['!denied.example\n','^exact.example\n','A.example\n',
                    'a.example\na.example\n', 'example.com', '\xff']:
            with self.subTest(raw=raw):
                if not self.root.exists(): self.init()
                (self.root/'youtube.txt').write_bytes(raw.encode() if isinstance(raw,str) and raw != '\xff' else b'\xff')
                with self.assertRaises(OwnedSourcesRefused):
                    self.read()
                (self.root/'youtube.txt').write_bytes(b'')

    def test_partial_mismatched_manifest_and_unknown_names_refuse(self):
        self.root.mkdir(mode=0o700)
        with self.assertRaisesRegex(OwnedSourcesRefused,'incomplete'):
            self.read()
        self.root.rmdir()
        self.init()
        (self.root/'manifest.json').write_text('{}')
        with self.assertRaisesRegex(OwnedSourcesRefused,'invalid_owned_manifest'):
            self.read()

    def test_foreign_files_and_symlinks_refuse(self):
        self.init()
        (self.root/'foreign.txt').write_text('untrusted')
        with self.assertRaisesRegex(OwnedSourcesRefused,'incomplete_or_foreign'):
            self.read()
        (self.root/'foreign.txt').unlink()
        (self.root/'user.txt').unlink()
        (self.root/'user.txt').symlink_to(self.final)
        with self.assertRaises(OwnedSourcesRefused):
            self.read()

    def test_component_ownership_and_modes_refuse(self):
        self.init()
        f=self.root/'youtube.txt'
        f.chmod(0o666)
        with self.assertRaisesRegex(OwnedSourcesRefused,'unsafe_owned_component'):
            self.read()
        f.chmod(0o600)
        self.root.chmod(0o777)
        with self.assertRaisesRegex(OwnedSourcesRefused,'unsafe_ownership_directory'):
            self.read()

    def test_common_gui_file_lock_guards_entire_snapshot(self):
        self.init()
        fd=os.open(self.lock,os.O_CREAT|os.O_RDWR,0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaisesRegex(DestinationRefused,'gui_writer_busy'):
                self.read()
        finally:
            os.close(fd)
        self.assertTrue(self.read()['auto_owned_complete'])

    def test_missing_final_and_root_only_cli_gates(self):
        self.init()
        self.final.unlink()
        r=self.read()
        self.assertEqual(r['status'],'missing')
        self.assertEqual(r['content'],'')
        from auto_detect_owned_sources import main
        self.assertEqual(main(['bootstrap']),0)
        self.assertFalse(self.final.exists())

if __name__=='__main__':
    unittest.main()