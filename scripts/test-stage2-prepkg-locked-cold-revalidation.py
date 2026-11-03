#!/usr/bin/env python3
"""Offline fail-closed tests for native original FD9 locked cold revalidation."""
import importlib.util
import json
from pathlib import Path
import stat
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'stage2-prepkg-locked-cold-revalidation.py'
spec = importlib.util.spec_from_file_location('locked_cold', SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def result(rc, stdout='', stderr=''):
    return subprocess.CompletedProcess([], rc, stdout, stderr)

class LockedColdReadOnlyContracts(unittest.TestCase):
    def test_pinned_real_fd9_inode_not_arbitrary_descriptor(self):
        inode = SimpleNamespace(st_mode=stat.S_IFREG | 0o600,
                                st_uid=0, st_nlink=1, st_dev=42, st_ino=77)
        self.assertTrue(mod.check_lock_identity(mod.LOCK, inode, inode))
        for changes, reason in (
                ({'st_uid': 1000}, 'UNTRUSTED'),
                ({'st_nlink': 2}, 'UNTRUSTED'),
                ({'st_ino': 78}, 'NOT_HISTORICAL'),
                ({'st_dev': 99}, 'NOT_HISTORICAL')):
            other = SimpleNamespace(**(vars(inode) | changes))
            if 'st_ino' in changes or 'st_dev' in changes:
                args = (inode, other)
            else:
                args = (other, inode)
            with self.subTest(changes=changes), self.assertRaisesRegex(
                    mod.Refusal, reason):
                mod.check_lock_identity(mod.LOCK, *args)
        with self.assertRaisesRegex(mod.Refusal, 'PATH_UNTRUSTED'):
            mod.check_lock_identity(Path('/tmp/foreign.lock'), inode, inode)

    def test_cold_witness_cannot_be_promoted_to_update_authorization(self):
        witness={'status': 'PASS_LOCKED_COLD_READ_ONLY_DIAGNOSTIC',
                 'old_pkgdb_service_config_unchanged': True,
                 'independent_original_fd9_exclusive': True,
                 'old_status_called_under_fd9': False,
                 'native_pkg_mutation_invoked': False,
                 'pre_pkg_admission_implemented': False,
                 'lh08_ac11_accepted': False}
        report='STAGE2_LOCKED_COLD='+json.dumps(witness)+'\n'
        self.assertEqual(mod.classify(result(0, report), 'cold'), witness)
        for changed in (
                {'pre_pkg_admission_implemented': True},
                {'native_pkg_mutation_invoked': True},
                {'lh08_ac11_accepted': True},
                {'old_status_called_under_fd9': True},
                {'independent_original_fd9_exclusive': False}):
            with self.subTest(changed=changed), self.assertRaisesRegex(
                    mod.Refusal, 'UNSAFE_COLD_REPORT'):
                bad = witness | changed
                mod.classify(result(0,'STAGE2_LOCKED_COLD='+json.dumps(bad)), 'cold')

    def test_busy_original_fd9_refused_without_entering_helper(self):
        self.assertEqual(mod.classify(result(75), 'busy'),
                         'BUSY_ORIGINAL_FD9_DENIED_BEFORE_HELPER')
        for p in (result(0), result(75,'entered'), result(1)):
            with self.subTest(rc=p.returncode), self.assertRaisesRegex(
                    mod.Refusal, 'BUSY_FD9_ENTERED'):
                mod.classify(p, 'busy')

    def test_unknown_journal_refused_inside_held_fd9(self):
        self.assertEqual(mod.classify(result(
            2, '', 'STAGE2_LOCKED_COLD=REFUSED:UNVERIFIED_JOURNAL_MARKER_OR_PIDFILE:/var/db/zapret2/shared-apply'),
            'journal'), 'UNKNOWN_JOURNAL_DENIED_UNDER_ORIGINAL_FD9')
        for p in (result(0), result(2), result(2,'unexpected',
                                              'STAGE2_LOCKED_COLD=REFUSED:UNVERIFIED_JOURNAL_MARKER_OR_PIDFILE:')):
            with self.subTest(rc=p.returncode), self.assertRaisesRegex(
                    mod.Refusal, 'UNKNOWN_OWNER_NOT_REFUSED'):
                mod.classify(p, 'journal')

    def test_cold_preconditions_fail_closed(self):
        prov={'status':'PASS_READ_ONLY_PROVENANCE',
              'package':'os-zapret2-restyle-0.6.2_1'}
        g=SimpleNamespace(JOURNAL=Path('/dummy/journal'),
                          MARKERS=(Path('/dummy/marker'),),
                          PIDFILES=(Path('/dummy/pid'),),
                          PENDING_EXTRA=Path('/dummy/extra'),
                          check_no_owners=Mock(),
                          check_process_census=Mock(),
                          check_kernel_cold=Mock(return_value='UNLOADED_COLD_ENOPROTOOPT'))
        a=(result(0,''), result(1), result(1), result(71,'','Protocol not available'))
        self.assertEqual(mod.qualified_cold(prov,g,*a),
                         'COLD_READ_ONLY_REVALIDATED_UNDER_ORIGINAL_FD9')
        g.check_no_owners.assert_called_once()
        with self.assertRaisesRegex(mod.Refusal,'PREDECESSOR_UNVERIFIED'):
            mod.qualified_cold({'status':'WRONG'},g,*a)
        with self.assertRaisesRegex(mod.Refusal,'PROCESS_CENSUS_FAILED'):
            mod.qualified_cold(prov,g,result(1),*a[1:])
        g.check_kernel_cold.return_value='UNKNOWN'
        with self.assertRaisesRegex(mod.Refusal,'NATIVE_KERNEL_NOT_COLD'):
            mod.qualified_cold(prov,g,*a)

    def test_original_module_refusals_become_bounded_local_refusals(self):
        class OldFailure(Exception):
            pass
        class GuardFailure(Exception):
            pass
        old=SimpleNamespace(Refusal=OldFailure, SERVICE='/unused/service',
                            run=Mock(return_value=b'guest'),
                            run_guest=Mock(return_value={
                                'status':'PASS_READ_ONLY_PROVENANCE',
                                'package':'os-zapret2-restyle-0.6.2_1'}))
        guard=SimpleNamespace(Refusal=GuardFailure,
                              command=Mock(return_value=result(0)))
        with patch.object(mod,'qualify'), patch.object(mod,'check_fd9'), \
             patch.object(mod,'load',side_effect=[old,guard]), \
             patch.object(mod,'digest',return_value='same'):
            old.run_guest.side_effect=OldFailure('REAL_OLD_UNQUALIFIED')
            with self.assertRaisesRegex(mod.Refusal, 'REAL_OLD_UNQUALIFIED'):
                mod.inside_lock(Path('/unused.pkg'))
        old.run_guest.side_effect=None
        with patch.object(mod,'qualify'), patch.object(mod,'check_fd9'), \
             patch.object(mod,'load',side_effect=[old,guard]), \
             patch.object(mod,'digest',return_value='same'), \
             patch.object(mod,'qualified_cold',
                          side_effect=GuardFailure('UNVERIFIED_JOURNAL_MARKER_OR_PIDFILE:foreign')):
            with self.assertRaisesRegex(mod.Refusal,
                                        'UNVERIFIED_JOURNAL_MARKER_OR_PIDFILE'):
                mod.inside_lock(Path('/unused.pkg'))

    def test_source_enforces_nonrecursive_no_pkg_boundary(self):
        source=SOURCE.read_text(encoding='utf-8')
        for token in (
                "LOCK = Path('/var/run/zapret2-lifecycle.lock')",
                "/usr/bin/lockf -s -t 0 9",
                "exec /usr/local/bin/python3",
                "os.fstat(9)", "guard.check_no_owners", "guard.check_kernel_cold",
                "old.run_guest(archive, host)", "assert_unchanged",
                "'stock_firmware_route_protected': False",
                "'lh08_ac11_accepted': False",
                "unknown.verify_corrupt_journal()", "os.killpg(proc.pid, signal.SIGKILL)"):
            with self.subTest(token=token):
                self.assertIn(token,source)
        for unsafe in ("pkg add -f", "pkg upgrade", "pkg unlock", "ipfw flush",
                       "service_with_lifecycle_lock", "configctl zapret stop"):
            with self.subTest(unsafe=unsafe):
                self.assertNotIn(unsafe,source)
        self.assertNotIn('call_status(',source)
        self.assertNotIn('service_dispatch(',source)

if __name__ == '__main__':
    unittest.main()
