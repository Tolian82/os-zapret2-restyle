#!/usr/bin/env python3
"""Pure negative contracts for staged, SHA-bound pre-pkg native source proof."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'native_archive_bootstrap', HERE / 'stage3-native-prepkg-archive-bootstrap.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class NativeArchiveBootstrapContracts(unittest.TestCase):
    def fixture(self):
        modules = {name:(m.PRODUCT / name).read_bytes() for name in m.MODULES}
        manifest = {'name':m.NAME, 'version':'0.6.2_113',
                    'abi':'FreeBSD:15:amd64','arch':'freebsd:15:x86:64',
                    'files':{'/' + m.DEST + name:'1$sha' for name in m.MODULES}}
        return modules, manifest

    def tool(self, modules, manifest, changes=None):
        changes = changes or {}
        entries = [m.DEST + name for name in m.MODULES]
        if 'entries' in changes:
            entries = changes['entries']
        def run(argv,**_):
            if argv[1] == '-tf':
                return ('\n'.join(entries)+'\n').encode()
            if argv[-1] == '+MANIFEST':
                return json.dumps(changes.get('manifest',manifest)).encode()
            name = argv[-1].split('/')[-1]
            return changes.get('bytes',{}).get(name, modules[name])
        return run

    def call(self, folder, changes=None, sha='a'*64):
        modules, manifest = self.fixture()
        # Ubuntu Actions user is not root; mock only UID while retaining
        # real inode/mode/link properties. The native KVM runs without mocks.
        original_lstat=Path.lstat
        def fake_lstat(path,*args,**kwargs):
            entry=list(original_lstat(path,*args,**kwargs))
            entry[4]=0
            return os.stat_result(entry)
        with patch.object(Path,'lstat',fake_lstat),\
             patch.object(m,'qualify'),\
             patch.object(m.candidate,'identity'),\
             patch.object(m.candidate,'inspect_archive') as check,\
             patch.object(m,'read_only',side_effect=self.tool(modules,manifest,changes)):
            result = m.staged_source_from_native_archive(
                Path('/root/os-zapret2-restyle-0.6.2_113.pkg'),'0.6.2_113',
                sha,folder)
            self.assertEqual(check.call_count,2)
        return result

    def test_four_archived_exact_source_bytes_staged_with_private_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'root'
            root.mkdir(mode=0o700)
            cli = self.call(root)
            self.assertEqual(cli,root/'native_pkg_managed.py')
            self.assertEqual({p.name for p in root.iterdir()},set(m.MODULES))
            for name in m.MODULES:
                p = root / name
                self.assertEqual(stat.S_IMODE(p.stat().st_mode),0o600)
                self.assertEqual(p.read_bytes(),(m.PRODUCT / name).read_bytes())

    def test_archive_member_duplicate_or_missing_refused_before_staging(self):
        for bad in ([],[m.DEST + m.MODULES[0]]*2,
                    [m.DEST + name for name in m.MODULES if name != m.MODULES[-1]]):
            with self.subTest(bad=bad),tempfile.TemporaryDirectory() as tmp:
                with self.assertRaisesRegex(m.Refusal,'MISSING_OR_DUPLICATED'):
                    self.call(Path(tmp),{'entries':bad})
                self.assertEqual(os.listdir(tmp),[])

    def test_native_mk_repeated_relative_prefix_but_no_traversal(self):
        canonical=[m.DEST + name for name in m.MODULES]
        with tempfile.TemporaryDirectory() as tmp:
            self.call(Path(tmp),{'entries':['././' + name for name in canonical]})
            self.assertEqual({p.name for p in Path(tmp).iterdir()},set(m.MODULES))
        # This is the real official OPNsense native Mk archive naming.
        with tempfile.TemporaryDirectory() as tmp:
            self.call(Path(tmp),{'entries':['/' + name for name in canonical]})
            self.assertEqual({p.name for p in Path(tmp).iterdir()},set(m.MODULES))
        for first in ('//','/../','../','../../'):
            with self.subTest(first=first),tempfile.TemporaryDirectory() as tmp:
                aliases=[first + canonical[0],*canonical[1:]]
                with self.assertRaisesRegex(m.Refusal,'MISSING_OR_DUPLICATED'):
                    self.call(Path(tmp),{'entries':aliases})
                self.assertEqual(list(Path(tmp).iterdir()),[])

    def test_manifest_identity_and_source_bytes_must_agree(self):
        modules,manifest=self.fixture()
        wrong=dict(manifest,version='0.6.2_999')
        tampered=dict(modules)
        tampered[m.MODULES[0]]+=b'\n# unexpected byte'
        for changed, reason in (
                ({'manifest':wrong},'IDENTITY_UNQUALIFIED'),
                ({'bytes':tampered},'TRACKED_SOURCE_BYTES_DIFFER')):
            with self.subTest(reason=reason),tempfile.TemporaryDirectory() as tmp:
                with self.assertRaisesRegex(m.Refusal,reason):
                    self.call(Path(tmp),changed)
                self.assertEqual(os.listdir(tmp),[])

    def test_existing_output_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            sentinel=root / m.MODULES[0]
            sentinel.write_text('preserve')
            with self.assertRaisesRegex(m.Refusal,'OUTPUT_ALREADY_EXISTS'):
                self.call(root)
            self.assertEqual(sentinel.read_text(),'preserve')

    def test_symlink_target_refused_without_following(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            link=root / m.MODULES[0]
            other=root / 'outside'
            other.write_text('keep')
            link.symlink_to(other)
            with self.assertRaisesRegex(m.Refusal,'OUTPUT_ALREADY_EXISTS'):
                self.call(root)
            self.assertEqual(other.read_text(),'keep')

    def test_wrong_candidate_sha_never_opens_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(m,'qualify'),\
                 patch.object(m.candidate,'identity'),\
                 patch.object(m.candidate,'inspect_archive',
                              side_effect=m.candidate.CandidateRefusal('SHA_MISMATCH')),\
                 patch.object(m,'read_only') as tar:
                with self.assertRaisesRegex(m.candidate.CandidateRefusal,'SHA_MISMATCH'):
                    m.staged_source_from_native_archive(
                        Path('/root/os-zapret2-restyle-0.6.2_113.pkg'),
                        '0.6.2_113','0'*64,Path(tmp))
                tar.assert_not_called()
                self.assertEqual(os.listdir(tmp),[])

    def test_not_supported_upgrader_or_bypass(self):
        source=(HERE / 'stage3-native-prepkg-archive-bootstrap.py').read_text()
        self.assertIn("'supported_entrypoint_implemented': False",source)
        self.assertIn("'native_pkg_mutation_after_old_install': False",source)
        self.assertIn("'lh08_ac11_accepted': False",source)
        for forbidden in ("'pkg', 'add'","'pkg', 'upgrade'","'pkg', 'delete'",
                          "os.system(", "os.execv(", "os.rename("):
            self.assertNotIn(forbidden,source)
        # Exactly one intentionally bounded Popen is used to attach the
        # disposable CI-only operator test process to its pseudo-terminal.
        # It never executes pkg; all production mutations remain prohibited.
        self.assertEqual(source.count("subprocess.Popen("),1)
        self.assertIn("master_fd, slave_fd = pty.openpty()",source)
        self.assertIn("proc = subprocess.Popen(manual, stdin=slave_fd, stdout=slave_fd,",source)
        self.assertIn("manual = [sys.executable, '-I', '-B', str(approval_tool),",source)
        self.assertIn("'ci_operator_pty_receipt_record_and_inspect_verified': True",source)
        self.assertIn("'receipt_pins_bound_to_seed_and_signed_archive_claims': True",source)
        self.assertIn("'receipt_operator_issuer_authenticated': False",source)
        self.assertIn("'ci_ephemeral_detached_approval_signature_verified': True",source)
        self.assertIn("'operator_authority_approved_out_of_band': False",source)
        self.assertIn("'OPERATOR_RECEIPT_SIGNATURE_INVALID' in denied.stderr",source)
        self.assertIn("seal_receipt()",source)
        self.assertIn("'RECEIPT_NEGATIVE_NOT_REFUSED:' + reason",source)


if __name__=='__main__':
    unittest.main()
