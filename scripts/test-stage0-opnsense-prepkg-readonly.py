#!/usr/bin/env python3
"""Local, executable refusals for Stage 0 historical-predecessor preflight."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('prepkg', HERE / 'stage0-opnsense-prepkg-readonly.py')
g=importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


def result(rc, stdout='', stderr=''):
    return subprocess.CompletedProcess([], rc, stdout, stderr)


class ColdReadOnlyContracts(unittest.TestCase):
    def setUp(self):
        self.prov={'status':'PASS_READ_ONLY_PROVENANCE','package':'os-zapret2-restyle-0.6.2_1'}
        self.cold=result(1,'zapret is not running\n')
        self.kmod=result(1)
        self.ipfw=result(71,'', 'ipfw: Protocol not available')

    def evaluate(self, **changes):
        a=dict(provenance=self.prov, status=self.cold, kld_ipfw=self.kmod,
               kld_divert=self.kmod, ipfw=self.ipfw, processes='')
        a.update(changes)
        with tempfile.TemporaryDirectory() as t:
            return g.observed_cold(journal=Path(t)/'journal',
               markers=(Path(t)/'marker',),pidfiles=(Path(t)/'pid',),**a)

    def test_actual_cold_witness_is_snapshot_only(self):
        a=self.evaluate()
        self.assertEqual(a['status'],'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY')
        self.assertFalse(a['safe_pkg_transaction_authorized'])

    def test_bad_provenance_refused(self):
        for bad in ({'status':'wrong','package':'os-zapret2-restyle-0.6.2_1'},
                    {'status':'PASS_READ_ONLY_PROVENANCE','package':'foreign'}):
            with self.subTest(bad=bad),self.assertRaisesRegex(g.Refusal,'PROVENANCE'):
                self.evaluate(provenance=bad)

    def test_unknown_or_running_status_refused(self):
        for rc,text in ((0,'zapret is running'),(2,'zapret is in an incomplete runtime state'),
                        (75,''),(1,'wrong')):
            with self.subTest(rc=rc),self.assertRaisesRegex(g.Refusal,'NOT_PROVEN_STOPPED'):
                self.evaluate(status=result(rc,text))

    def test_journal_and_dangling_symlink_refused(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'journal';p.mkdir()
            with self.assertRaisesRegex(g.Refusal,'UNVERIFIED_JOURNAL'):
                g.check_no_owners([p])
            p.rmdir();p.symlink_to('/nonexistent-target')
            with self.assertRaisesRegex(g.Refusal,'UNVERIFIED_JOURNAL'):
                g.check_no_owners([p])

    def test_marker_pidfile_and_extra_resource_refused(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'any';p.write_text('x')
            with self.assertRaisesRegex(g.Refusal,'UNVERIFIED_JOURNAL'):
                g.check_no_owners([p])

    def test_running_process_tokens_refused(self):
        for line in ('123 /usr/local/etc/zapret2/binaries/my/dvtws2',
                     '98 /usr/local/opnsense/scripts/OPNsense/Zapret/supervisor_loop.sh',
                     '12 /usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh'):
            with self.subTest(line=line),self.assertRaisesRegex(g.Refusal,'POSSIBLE_ZAPRET_PROCESS'):
                self.evaluate(processes=line)

    def test_loaded_kernel_or_unknown_ipfw_refused(self):
        for args in ({'kld_ipfw':result(0)}, {'kld_divert':result(0)},
                     {'ipfw':result(0, '19000 divert 989 tcp from any to any')},
                     {'ipfw':result(71,'','unrecognized error')}):
            with self.subTest(args=args),self.assertRaises(g.Refusal):
                self.evaluate(**args)

    def test_denied_gate_never_calls_operation(self):
        action=mock.Mock();probe=mock.Mock(side_effect=g.Refusal('UNKNOWN_OWNER'))
        with self.assertRaisesRegex(g.Refusal,'UNKNOWN_OWNER'):
            g.require_snapshot_before(action,probe)
        action.assert_not_called()

    def test_unknown_status_result_no_operation(self):
        action=mock.Mock()
        def probe():
            return self.evaluate(status=result(2,'zapret is in an incomplete runtime state'))
        with self.assertRaises(g.Refusal):
            g.require_snapshot_before(action,probe)
        action.assert_not_called()

    def test_invalid_schema_denies_call(self):
        action=mock.Mock()
        with self.assertRaisesRegex(g.Refusal,'EVIDENCE_NOT_ACCEPTED'):
            g.require_snapshot_before(action,lambda:{'status':'PASS_INSTALLED_SUCCESS'})
        action.assert_not_called()

    def test_non_target_refused_before_provenance_or_mutation(self):
        class Other:
            sysname='Linux';machine='x86_64'
        with mock.patch.object(g.os,'uname',return_value=Other()),\
             mock.patch.object(g.os,'geteuid',return_value=0),\
             mock.patch.object(g,'load') as loader:
            with self.assertRaisesRegex(g.Refusal,'ONLY_ROOT_DISPOSABLE'):
                g.snapshot(Path('/missing.pkg'),pre=mock.Mock(),fd9=mock.Mock())
            loader.assert_not_called()

    def test_readonly_source_never_invokes_pkg_transaction(self):
        src=(HERE/'stage0-opnsense-prepkg-readonly.py').read_text()
        self.assertNotIn('"add", "-f"',src)
        self.assertNotIn('"delete", "-y"',src)
        self.assertNotIn('subprocess.Popen',src)


if __name__=='__main__':
    unittest.main()
