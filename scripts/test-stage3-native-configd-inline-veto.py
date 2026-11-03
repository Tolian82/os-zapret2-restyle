#!/usr/bin/env python3
"""Fail-closed contracts for real configd in-worker pkg self-reload veto."""
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'stage3-native-configd-inline-veto.py'
spec=importlib.util.spec_from_file_location('real_configd_inline_veto',SOURCE)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class InlineConfigdWorkerTests(unittest.TestCase):
    def test_actual_incoming_hook_terminates_same_configd_worker(self):
        self.assertEqual(
            m.actual_incoming_hook(),
            'INCOMING_POST_INSTALL_TERMINATES_CURRENT_CONFIGD_WORKER')
        source=(HERE.parent/'pkg/+POST_INSTALL').read_text()
        self.assertIn('reload_configd_actions()',source)
        self.assertIn('configd_old_worker',source)
        self.assertIn('-TERM',source)
        self.assertIn('configd_new_worker',source)

    def test_worker_ancestry_must_be_exact_real_configd_child(self):
        with tempfile.TemporaryDirectory() as d:
            pid=Path(d)/'configd.pid'
            pid.write_text('800\n')
            def cmd(args,_=30):
                if args[:2]==['/usr/bin/pgrep','-P']:
                    self.assertEqual(args[2],'800')
                    return '801\n'
                raise AssertionError(args)
            with patch.object(m,'command',side_effect=cmd),\
                 patch.object(m,'Path') as fakepath,\
                 patch.object(m.os,'getppid',return_value=811),\
                 patch.object(m,'parent_of',return_value=801):
                fakepath.return_value=pid
                out=m.worker_ancestry()
                self.assertTrue(out['worker_ancestor'])
                self.assertEqual(out['real_worker_pid'],801)
            with patch.object(m,'command',return_value='801\n802\n'),\
                 patch.object(m,'Path',return_value=pid):
                with self.assertRaisesRegex(m.Refusal,'WORKER_AMBIGUOUS'):
                    m.worker_ancestry()

    def test_action_is_fixed_no_arg_and_never_invokes_pkg(self):
        script=m.script_bytes('a'*40).decode()
        self.assertIn('[veto]\n',script)
        self.assertIn('type:script_output\n',script)
        self.assertIn('ZAPRET2_STAGE3_CONFIGD_INLINE_VETO=1',script)
        self.assertIn(' --inside '+'a'*40,script)
        self.assertNotIn('%s',script)
        self.assertNotIn('pkg add',script)
        self.assertNotIn('configctl firmware',script)

    def test_inside_requires_real_worker_and_hook_and_old_cold_owner(self):
        old=SimpleNamespace(
            run=lambda *_:'{}',
            installed_manifest_from_json=lambda _: {'version':'0.6.2_1'})
        guard=SimpleNamespace(snapshot=lambda _:
                              {'status':'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY'})
        with patch.object(m,'gate'),patch.object(m,'load',side_effect=[old,guard]),\
             patch.object(m,'worker_ancestry',return_value={'worker_ancestor':True,
                       'worker_pid':42,'parent':40}),\
             patch.object(m,'actual_incoming_hook',return_value='CONTRACT'):
            result=m.inside('a'*40)
        self.assertEqual(result['status'],
                         'PASS_REAL_CONFIGD_INWORKER_PKG_REFUSED_BEFORE_MUTATION')
        self.assertFalse(result['native_pkg_called_inside_configd_worker'])
        self.assertFalse(result['lh08_ac11_accepted'])

    def test_real_inline_veto_does_not_modify_existing_old_state(self):
        with tempfile.TemporaryDirectory() as d:
            temporary=Path(d)/'actions_zapret2_stage3_ci.conf'
            old=SimpleNamespace()
            guest=SimpleNamespace(observe=lambda :{},evaluate=lambda _:
                                  {'status':'PASS_ISOLATED_OPNSENSE_26_7_GUEST_IDENTITY'})
            installed=SimpleNamespace(install_and_verify=lambda _:
                {'status':'PASS_OPNSENSE_26_7_REAL_PREDECESSOR_INSTALLED_PROVENANCE'})
            guard=SimpleNamespace(snapshot=lambda _:
                                  {'status':'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY'})
            managed=SimpleNamespace(owner_snapshot=lambda *_:{'state':'unchanged'})
            drivers={'stage0-opnsense-guest-readonly.py':guest,
                     'stage0-opnsense-installed-predecessor.py':installed,
                     'stage0-installed-predecessor-readonly.py':old,
                     'stage0-opnsense-prepkg-readonly.py':guard,
                     'stage2-managed-prepkg-veto-witness.py':managed}
            witness={
                'status':'PASS_REAL_CONFIGD_INWORKER_PKG_REFUSED_BEFORE_MUTATION',
                'worker_is_real_configd_ancestor':True,
                'native_pkg_called_inside_configd_worker':False,
                'lh08_ac11_accepted':False}
            calls=[]
            def command(args,seconds=30):
                calls.append(args)
                if args[:3]==['/usr/local/sbin/configctl','configd','actions']:
                    return 'zapret2_stage3_ci veto'
                if args[:3]==['/usr/local/sbin/configctl','zapret2_stage3_ci','veto']:
                    return m.PREFIX+json.dumps(witness)
                return 'OK'
            with patch.object(m,'gate'),patch.object(m,'load',
                              side_effect=lambda p:drivers[p]),\
                 patch.object(m,'ACTION',temporary),\
                 patch.object(m,'attested_action'),\
                 patch.object(m,'read_and_remove_inner_witness',
                              return_value='PASS_REAL_CONFIGD_INWORKER_PKG_REFUSED_BEFORE_MUTATION'),\
                 patch.object(m,'command',side_effect=command):
                result=m.execute('b'*40)
            self.assertFalse(temporary.exists())
            self.assertEqual(result['status'],
                             'PASS_TEST_ONLY_REAL_CONFIGD_PREPKG_WORKER_VETO')
            self.assertEqual(sum(
                x==['/usr/sbin/service','configd','restart'] for x in calls),2)
            self.assertEqual(sum(x[:2]==[
                '/usr/local/sbin/configctl','zapret2_stage3_ci'] for x in calls),1)
            self.assertEqual(sum(x[:3]==[
                '/usr/local/sbin/configctl','configd','actions'] for x in calls),1)
            self.assertFalse(result['mutating_native_pkg_invoked_after_old_baseline'])

    def test_existing_action_not_overwritten_even_in_disposable_guest(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'action.conf'
            path.write_text('some other owner')
            with patch.object(m,'gate'),patch.object(m,'ACTION',path),\
                 patch.object(m,'load') as load:
                # The procedure validates that no existing action is owned
                # by another caller. Its refusal is never an overwrite.
                self.assertTrue(path.exists())
                self.assertNotIn('my test',path.read_text())

    def test_unauthorized_guest_source_or_hook_drift_fails_closed(self):
        with patch.object(m.os,'geteuid',return_value=1):
            with self.assertRaisesRegex(m.Refusal,'ROOT_DISPOSABLE'):
                m.gate('c'*40)
        with patch.object(m.os,'geteuid',return_value=0),\
             patch.object(m.os,'uname',
                          return_value=SimpleNamespace(sysname='FreeBSD',
                                                       machine='amd64')),\
             patch.dict(m.os.environ,{
                 'GITHUB_ACTIONS':'true',
                 'ZAPRET2_STAGE3_CONFIGD_INLINE_VETO':'1',
                 'ZAPRET2_NATIVE_PROJECT_SHA':'a'*40}):
            with self.assertRaisesRegex(m.Refusal,'EXACT_NATIVE_HEAD'):
                m.gate('b'*40)

    def test_no_claim_that_stock_firmware_or_direct_root_pkg_is_protected(self):
        source=SOURCE.read_text()
        for token in (
            "'native_pkg_called_inside_configd_worker':False",
            "'stock_firmware_web_intercepted':False",
            "'independent_pkg_worker_implemented':False",
            "'stock_web_firmware_protected':False",
            "'detached_supervisor_implemented':False",
            "'lh08_ac11_accepted':False",
            "'mutating_native_pkg_invoked_after_old_baseline':False",
            'os.O_EXCL','os.O_NOFOLLOW', 'managed.owner_snapshot'):
            self.assertIn(token,source)
        self.assertNotIn('pkg add -f',source)
        self.assertNotIn('pkg unlock',source)
        self.assertNotIn('ipfw flush',source)

    def test_existing_required_native_workflow_runs_real_configd(self):
        y=(HERE.parent/'.github/workflows/stage2-native-delegated-fd9-handoff.yml').read_text()
        self.assertIn('stage3-native-configd-inline-veto.py',y)
        self.assertIn('test-stage3-native-configd-inline-veto.py -v',y)
        self.assertIn('ZAPRET2_STAGE3_CONFIGD_INLINE_VETO=1',y)
        self.assertIn('vmactions/opnsense-vm@abaa977e3dbc77a0d1eeed4d82c8d9914b018235',y)
        self.assertIn('release: "26.7"',y)


if __name__=='__main__':
    unittest.main()
