#!/usr/bin/env python3
"""Runnable offline, fail-closed tests of original FD9 pre-pkg final veto."""
import importlib.util
import pathlib
import unittest

HERE=pathlib.Path(__file__).parent
S=HERE/'stage3-native-configd-final-gate.py'
spec=importlib.util.spec_from_file_location('stage3_final_gate',S)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class Refusal(Exception):
    pass


class FinalGateContracts(unittest.TestCase):
    def test_exact_real_late_journal_refused(self):
        called=[]
        def check():
            called.append(True)
            raise Refusal(m.JOURNAL_REFUSAL+'/var/db/zapret2/shared-apply')
        r=m.deny_late_journal_before_pkg(check,481,481)
        self.assertEqual(called,[True])
        self.assertEqual(r['status'],'REFUSED_LATE_JOURNAL_BEFORE_MUTATING_PKG')
        self.assertIs(r['native_mutating_pkg_dispatch_reached'],False)

    def test_unexpected_pass_is_not_authorized(self):
        with self.assertRaisesRegex(m.FinalGateRefusal,'TRIPWIRE'):
            m.deny_late_journal_before_pkg(lambda:None,481,481)

    def test_foreign_error_not_trusted_as_expected_refusal(self):
        for exception in [Refusal('UNKNOWN_OTHER_OWNER'), ValueError(m.JOURNAL_REFUSAL+'x'), OSError('e')]:
            with self.subTest(exception=type(exception).__name__):
                def check():
                    raise exception
                with self.assertRaisesRegex(m.FinalGateRefusal,'UNQUALIFIED_FINAL_GATE_REFUSAL'):
                    m.deny_late_journal_before_pkg(check,481,481)

    def test_fd9_inode_mismatch_prevents_any_check(self):
        invoked=[]
        def check():invoked.append(True)
        for expected,actual in [(481,482),(481,0),(0,0),('481',481)]:
            with self.subTest(expected=expected,actual=actual):
                with self.assertRaisesRegex(m.FinalGateRefusal,'INODE_CHANGED'):
                    m.deny_late_journal_before_pkg(check,expected,actual)
        self.assertEqual(invoked,[])

    def test_pretend_refusal_with_wrong_exception_name_rejected(self):
        class FakeRefusal(Exception):pass
        def check():raise FakeRefusal(m.JOURNAL_REFUSAL+'x')
        with self.assertRaisesRegex(m.FinalGateRefusal,'UNQUALIFIED'):
            m.deny_late_journal_before_pkg(check,481,481)

    def test_no_mutating_pkg_symbol_or_command(self):
        src=S.read_text()
        for forbidden in ('pkg add -f','pkg upgrade','pkg delete','subprocess.Popen','os.system('):
            self.assertNotIn(forbidden,src)
        self.assertIn('TRIPWIRE',src)

    def test_native_workflow_and_core_chain_wired(self):
        script=HERE/'stage3-native-configd-fd9-handoff.py'
        workflow=HERE.parent/'.github/workflows/stage2-native-delegated-fd9-handoff.yml'
        if not script.exists() or not workflow.exists():
            self.skipTest('complete GitHub checkout required')
        s=script.read_text()
        w=workflow.read_text()
        for phrase in ('deny_late_journal_before_pkg(', 'journal.create_owned_corrupt_journal()',
                       'journal.remove_only_owned_journal()', 'ZAPRET2_STAGE3_LATE_JOURNAL_CI',
                       'PASS_TEST_ONLY_CONFIGD_FD9_LATE_JOURNAL_VETO_BEFORE_PKG',
                       'PASS_TEST_ONLY_CONFIGD_FD9_NATIVE_PKG_READ_ONLY_QUERY'):
            self.assertIn(phrase,s)
        for phrase in ('  configd-atomic-handoff-faults:',
                       '  configd-readonly-pkg:',
                       '  configd-late-owner-veto:',
                       'test-stage3-native-configd-final-gate.py -v',
                       'ZAPRET2_STAGE3_LATE_JOURNAL=1'):
            self.assertIn(phrase,w)


if __name__=='__main__':
    unittest.main()
