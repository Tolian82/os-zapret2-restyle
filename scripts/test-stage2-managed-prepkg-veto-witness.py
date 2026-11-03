#!/usr/bin/env python3
"""Offline executable contracts for Stage 2.23 test-only managed pre-pkg gate."""
import importlib.util
import json
from pathlib import Path
import stat
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'stage2-managed-prepkg-veto-witness.py'
spec = importlib.util.spec_from_file_location('stage2_managed_gate', SOURCE)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def completed(rc, out='', err=''):
    return subprocess.CompletedProcess([], rc, out, err)


class ManagedAdmissionContracts(unittest.TestCase):
    def test_actual_shell_original_fd9_and_nonrecursive_exec_argv(self):
        self.assertIn('exec 9>"$1"', gate.LOCKED)
        self.assertIn('/usr/bin/lockf -s -t 0 9', gate.LOCKED)
        self.assertIn('exec /usr/local/bin/python3 "$2" --inner "$3"', gate.LOCKED)
        self.assertNotIn('"$4"', gate.LOCKED)

    def test_valid_read_only_cold_report_and_no_false_authorization(self):
        valid = {
            'status': 'PASS_TEST_ONLY_MANAGED_COLD_QUERY_UNDER_ORIGINAL_FD9',
            'native_pkg_read_only_query_after_gate': True,
            'original_fd9_continuous_through_query': True,
            'native_pkg_mutation_invoked': False,
            'pre_pkg_admission_implemented': False,
            'lh08_ac11_accepted': False
        }
        report = completed(0, gate.PREFIX + json.dumps(valid) + '\n')
        self.assertEqual(gate.classify(report, 'cold'), valid)
        for change in ({'native_pkg_mutation_invoked': True},
                       {'pre_pkg_admission_implemented': True},
                       {'lh08_ac11_accepted': True},
                       {'native_pkg_read_only_query_after_gate': False},
                       {'original_fd9_continuous_through_query': False}):
            with self.subTest(change=change), self.assertRaisesRegex(
                    gate.Refusal, 'FALSE_SAFE_MANAGED_WITNESS'):
                gate.classify(completed(0,gate.PREFIX + json.dumps(valid | change)), 'cold')

    def test_unsafe_orphan_refuses_before_pkg_query(self):
        p = completed(2, '', gate.PREFIX +
                      'REFUSED:KERNEL_IPFW_OR_IPDIVERT_LOADED_OR_UNQUALIFIED')
        self.assertEqual(gate.classify(p, 'orphan'),
                         'REFUSED_ORPHAN_BEFORE_NATIVE_PKG_QUERY')
        for bad in (completed(0), completed(2, gate.PREFIX+'foo',p.stderr),
                    completed(2, '', gate.PREFIX+'REFUSED:wrong')):
            with self.subTest(bad=bad), self.assertRaisesRegex(
                    gate.Refusal, 'UNSAFE_OWNER_NOT_REFUSED'):
                gate.classify(bad, 'orphan')

    def test_unknown_journal_refuses_before_pkg_query(self):
        p = completed(2,'',gate.PREFIX +
                      'REFUSED:UNVERIFIED_JOURNAL_MARKER_OR_PIDFILE:/var/db/zapret2/shared-apply')
        self.assertEqual(gate.classify(p,'journal'),
                         'REFUSED_JOURNAL_BEFORE_NATIVE_PKG_QUERY')
        with self.assertRaises(gate.Refusal):
            gate.classify(completed(0), 'journal')

    def test_busy_fd9_rejected_before_python_helper(self):
        self.assertEqual(gate.classify(completed(75), 'busy'),
                         'BUSY_ORIGINAL_FD9_REFUSED_BEFORE_MANAGED_ENTRY')
        for p in (completed(0), completed(75,'unexpected'), completed(1)):
            with self.subTest(p=p), self.assertRaisesRegex(
                    gate.Refusal, 'BUSY_FD9_DID_NOT_REFUSE'):
                gate.classify(p, 'busy')

    def test_file_bytes_permissions_owner_and_symlink_target_are_snapshotted(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            f = root / 'service.sh'
            f.write_bytes(b'old bytes')
            f.chmod(0o755)
            link = root / 'service-link'
            link.symlink_to(f)
            old = SimpleNamespace(SERVICE=str(f),
                                  run=Mock(return_value=(
                                      str(f) + '\n' + str(link) + '\n' +
                                      str(root) + '\n').encode()))
            one = gate.installed_files(old)
            self.assertEqual(len(one),3)
            f.write_bytes(b'new bytes')
            self.assertNotEqual(one,gate.installed_files(old))
            f.write_bytes(b'old bytes')
            f.chmod(0o700)
            self.assertNotEqual(one,gate.installed_files(old))
            f.chmod(0o755)
            link.unlink()
            link.symlink_to(root)
            self.assertNotEqual(one,gate.installed_files(old))

    def test_reject_unqualified_file_inventory(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d) / 'service.sh'
            f.write_text('service')
            old=SimpleNamespace(SERVICE=str(f),run=Mock(return_value=b'relative.txt\n'))
            with self.assertRaisesRegex(gate.Refusal,'INSTALLED_FILE_LIST_UNQUALIFIED'):
                gate.installed_files(old)
            old.run.return_value=(str(f)+'\n'+str(f)+'\n').encode()
            with self.assertRaisesRegex(gate.Refusal,'INSTALLED_FILE_LIST_UNQUALIFIED'):
                gate.installed_files(old)

    def test_old_cold_guard_refusal_never_calls_native_pkg_query(self):
        class OldRefusal(Exception): pass
        locked=SimpleNamespace(Refusal=OldRefusal,check_fd9=Mock(),
                               inside_lock=Mock(side_effect=OldRefusal(
                                   'KERNEL_IPFW_OR_IPDIVERT_LOADED_OR_UNQUALIFIED')))
        with patch.object(gate,'qualify'),patch.object(gate,'load',return_value=locked),\
             patch.object(gate.subprocess,'run') as run:
            with self.assertRaisesRegex(gate.Refusal,'KERNEL_IPFW'):
                gate.run_inner(Path('/tmp/predecessor.pkg'))
            run.assert_not_called()
            self.assertEqual(locked.check_fd9.call_count,1)

    def test_cold_gate_can_only_execute_read_only_native_pkg(self):
        cold={'status':'PASS_LOCKED_COLD_READ_ONLY_DIAGNOSTIC',
              'lh08_ac11_accepted':False, 'native_pkg_mutation_invoked':False}
        locked=SimpleNamespace(check_fd9=Mock(),inside_lock=Mock(return_value=cold))
        with patch.object(gate,'qualify'), patch.object(gate,'load',return_value=locked),\
             patch.object(gate.subprocess,'run',
                          return_value=completed(0,'os-zapret2-restyle|0.6.2_1')) as run:
            report=gate.run_inner(Path('/tmp/predecessor.pkg'))
        self.assertFalse(report['lh08_ac11_accepted'])
        self.assertFalse(report['native_pkg_mutation_invoked'])
        self.assertEqual(locked.check_fd9.call_count,3)
        args=run.call_args.args[0]
        self.assertEqual(args[:4],
                         ['/usr/sbin/pkg','-o','REPO_AUTOUPDATE=false','query'])
        self.assertEqual(args[4:],['%n|%v','os-zapret2-restyle'])
        self.assertNotIn('add',args)
        self.assertNotIn('upgrade',args)

    def test_cold_pkg_read_only_query_failure_must_refuse(self):
        cold={'status':'PASS_LOCKED_COLD_READ_ONLY_DIAGNOSTIC',
              'lh08_ac11_accepted':False, 'native_pkg_mutation_invoked':False}
        locked=SimpleNamespace(check_fd9=Mock(),inside_lock=Mock(return_value=cold))
        for bad in (completed(1),completed(0,'wrong package')):
            with self.subTest(bad=bad),patch.object(gate,'qualify'),\
                 patch.object(gate,'load',return_value=locked),\
                 patch.object(gate.subprocess,'run',return_value=bad):
                with self.assertRaisesRegex(gate.Refusal,'NATIVE_PKG_READ_ONLY_QUERY_FAILED'):
                    gate.run_inner(Path('/tmp/predecessor.pkg'))

    def test_source_cannot_execute_native_mutating_pkg_or_replace_stock_hooks(self):
        source=SOURCE.read_text(encoding='utf-8')
        for forbidden in ('pkg add -f', 'pkg upgrade', 'pkg remove',
                          'pkg unlock', 'ipfw flush', 'configctl firmware install',
                          'service_dispatch(', 'call_status('):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden,source)
        for required in ('locked.inside_lock(archive)', 'locked.check_fd9()',
                         'unsafe.add_test_orphan()', 'status.returncode == 2',
                         'installed_files(old)', 'owner_snapshot(old, guard, archive)',
                         'unsafe.remove_test_orphan()', "'lh08_ac11_accepted': False"):
            with self.subTest(required=required):
                self.assertIn(required,source)


if __name__ == '__main__':
    unittest.main()
