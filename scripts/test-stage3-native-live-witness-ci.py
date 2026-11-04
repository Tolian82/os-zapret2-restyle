#!/usr/bin/env python3
"""Source and genuine loopback mTLS/SQLite CI witness tests, no pkg in unit tests."""
import hashlib
import importlib.util
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
HEAD = 'a' * 40
NONCE = 'f' * 32
ENV = {'GITHUB_ACTIONS': 'true',
       'ZAPRET2_STAGE3_NATIVE_LIVE_WITNESS': '1',
       'ZAPRET2_STAGE3_NATIVE_LIVE_WITNESS_CI': '1',
       'ZAPRET2_STAGE3_NATIVE_MUTATING_PKG_CI': '1',
       'ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK': '1',
       'ZAPRET2_STAGE3_NATIVE_STDIN_PKG': '1'}


def module(filename):
    spec = importlib.util.spec_from_file_location(
        filename.replace('-', '_').replace('.py', ''), HERE / filename)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


live = module('stage3-native-live-witness-ci.py')


class LiveWitnessNativeContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='ci-live-witness-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.root.chmod(0o700)
        self.env = mock.patch.dict(os.environ, ENV, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.calls = 0
        self.old = self.root / 'os-zapret2-restyle-0.6.2_1.pkg'
        self.new = self.root / 'os-zapret2-restyle-0.6.2_134.pkg'
        self.old.write_bytes(b'CI-REAL-OLD-CANDIDATE-PACKAGE-TEST')
        self.new.write_bytes(b'CI-REAL-NEW-NATIVE-PACKAGE-TEST')
        self.old.chmod(0o600)
        self.new.chmod(0o600)
        self.old_sha = hashlib.sha256(self.old.read_bytes()).hexdigest()
        self.new_sha = hashlib.sha256(self.new.read_bytes()).hexdigest()
        self.proc = None
        self.addCleanup(self.stop)

    def check_fd9(self):
        self.calls += 1

    def stop(self):
        live.stop(self.proc)
        self.proc = None

    def issue(self):
        grant = module('stage3-native-configd-operator-grant-ci.py')
        pins = live.prepare(self.root)
        ticket = grant.issue(self.root, HEAD, self.old, self.new,
                             self.old_sha, self.new_sha, '134', nonce=NONCE)
        self.assertEqual(ticket['client_sha256'], pins['client_sha256'])
        self.assertTrue((self.root / live.ROOT_NAME / 'status.key').exists())
        self.assertFalse((self.root / grant.ROOT_NAME / 'status-private.pem').exists())
        self.assertFalse((self.root / grant.ROOT_NAME / 'operator-private.pem').exists())
        return ticket

    def serve(self, ticket):
        self.proc = live.start(self.root, ticket, HEAD, self.old, self.new, NONCE)

    def assert_real_consumed(self, ticket, recovered=False):
        grant = module('stage3-native-configd-operator-grant-ci.py')
        positive = grant.verify(self.root, ticket, HEAD, self.old, self.new,
                                self.old_sha, self.new_sha, '134',
                                self.check_fd9, nonce=NONCE, live_phase='consume')
        final = grant.verify(self.root, ticket, HEAD, self.old, self.new,
                             self.old_sha, self.new_sha, '134',
                             self.check_fd9, nonce=NONCE, live_phase='status')
        self.assertEqual(positive, final)
        self.assertFalse(final['ci_remote_witness_deployed'])
        report = live.confirm(self.root, ticket, HEAD, NONCE)
        self.assertTrue(report['ci_real_sqlite_consumed'])
        self.assertEqual(report['ci_challenges_consumed'], 4 if recovered else 3)
        self.assertFalse(report['ci_owner_approval_authenticated'])
        self.assertGreaterEqual(self.calls, 12)
        return positive

    def test_live_loopback_durable_reserve_consume_status_real_signatures(self):
        ticket = self.issue()
        self.serve(ticket)
        self.assert_real_consumed(ticket)
        self.stop()
        module('stage3-native-configd-operator-grant-ci.py').cleanup(self.root)
        live.cleanup(self.root)
        self.assertFalse((self.root / live.ROOT_NAME).exists())

    def test_live_consumption_missing_service_refuses_before_pkg(self):
        ticket = self.issue()
        self.serve(ticket)
        self.stop()
        guard = module('stage3-native-configd-operator-grant-ci.py')
        with self.assertRaises(OSError):
            guard.verify(self.root, ticket, HEAD, self.old, self.new,
                         self.old_sha, self.new_sha, '134',
                         self.check_fd9, nonce=NONCE, live_phase='consume')
        with sqlite3.connect(self.root / live.ROOT_NAME / 'operations.sqlite') as con:
            self.assertEqual(con.execute('SELECT count(*) FROM operations').fetchone()[0], 0)

    def test_live_wrong_nonce_fails_before_request(self):
        ticket = self.issue()
        self.serve(ticket)
        guard = module('stage3-native-configd-operator-grant-ci.py')
        with self.assertRaisesRegex(Exception, 'FD9_GRANT_ROOT_TICKET_ROLE_OR_OPERATION_UNTRUSTED'):
            guard.verify(self.root, ticket, HEAD, self.old, self.new,
                         self.old_sha, self.new_sha, '134',
                         self.check_fd9, nonce='e'*32, live_phase='consume')
        self.assertEqual(self.calls, 0)
        with sqlite3.connect(self.root / live.ROOT_NAME / 'operations.sqlite') as con:
            self.assertEqual(con.execute('SELECT count(*) FROM challenges').fetchone()[0], 0)

    def test_live_duplicate_reservation_refused_after_consumed(self):
        ticket = self.issue()
        self.serve(ticket)
        self.assert_real_consumed(ticket)
        with self.assertRaisesRegex(Exception,'CLIENT_REFUSED_OR_BAD_ENVELOPE'):
            live.exchange(self.root, ticket, HEAD, NONCE,
                          self.check_fd9, 'consume')
        with sqlite3.connect(self.root / live.ROOT_NAME / 'operations.sqlite') as con:
            self.assertEqual(con.execute('SELECT count(*) FROM operations').fetchone()[0], 1)

    def test_live_lost_reply_recovers_only_via_fresh_signed_status(self):
        ticket = self.issue()
        self.serve(ticket)
        result = live.exchange(self.root, ticket, HEAD, NONCE, self.check_fd9,
                               'consume', drop_consume=True)
        self.assertTrue(result['ci_live_loopback_witness_consumed'])
        guard = module('stage3-native-configd-operator-grant-ci.py')
        guard.verify(self.root, ticket, HEAD, self.old, self.new,
                     self.old_sha, self.new_sha, '134', self.check_fd9,
                     nonce=NONCE, live_phase='status')
        self.assertEqual(live.confirm(self.root, ticket, HEAD, NONCE)
                         ['ci_challenges_consumed'], 4)

    def test_live_wrong_server_leaf_pin_refused_no_sqlite_mutation(self):
        ticket = self.issue()
        self.serve(ticket)
        endpoint = self.root / live.ROOT_NAME / 'endpoint.json'
        import json
        data = json.loads(endpoint.read_text())
        data['server_sha256'] = 'f'*64
        endpoint.write_text(json.dumps(data))
        endpoint.chmod(0o600)
        with self.assertRaisesRegex(Exception,'CLIENT_SERVER_CERT_PIN_MISMATCH'):
            live.exchange(self.root, ticket, HEAD, NONCE, self.check_fd9,
                          'consume')
        with sqlite3.connect(self.root / live.ROOT_NAME / 'operations.sqlite') as con:
            self.assertEqual(con.execute('SELECT count(*) FROM operations').fetchone()[0], 0)

    def test_live_not_owner_or_offhost_evidence(self):
        ticket = self.issue()
        self.serve(ticket)
        status = live.exchange(self.root, ticket, HEAD, NONCE, self.check_fd9,
                               'consume')
        self.assertFalse(status['ci_offhost_monotonic_store'])
        self.assertFalse(status['ci_external_witness_owner_approved'])
        self.assertFalse(status['ci_production_pkg_authorized'])

    def test_server_restart_keeps_committed_operation_for_fresh_signed_status(self):
        ticket = self.issue()
        self.serve(ticket)
        live.exchange(self.root, ticket, HEAD, NONCE, self.check_fd9, 'consume')
        with sqlite3.connect(self.root / live.ROOT_NAME / 'operations.sqlite') as con:
            self.assertEqual(con.execute(
                "SELECT state, witness_seq FROM operations").fetchall(),
                [('CONSUMED', ticket['checkpoint_sequence'] + 2)])
        self.proc = live.restart(self.root, ticket, HEAD, self.old, self.new,
                                 NONCE, self.proc)
        guard = module('stage3-native-configd-operator-grant-ci.py')
        guard.verify(self.root, ticket, HEAD, self.old, self.new,
                     self.old_sha, self.new_sha, '134', self.check_fd9,
                     nonce=NONCE, live_phase='status')
        report = live.confirm(self.root, ticket, HEAD, NONCE)
        self.assertTrue(report['ci_real_sqlite_consumed'])
        self.assertEqual(report['ci_challenges_consumed'], 3)
        with sqlite3.connect(self.root / live.ROOT_NAME / 'operations.sqlite') as con:
            self.assertEqual(con.execute('SELECT count(*) FROM operations').fetchone()[0], 1)

    def test_server_restart_without_existing_db_refuses_no_listener(self):
        ticket = self.issue()
        self.serve(ticket)
        live.stop(self.proc)
        (self.root / live.ROOT_NAME / 'operations.sqlite').unlink()
        with self.assertRaisesRegex(live.Refusal, 'CI_LIVE_WITNESS_RESTART_DB_UNTRUSTED'):
            live.restart(self.root, ticket, HEAD, self.old, self.new,
                         NONCE, self.proc)
        self.assertFalse((self.root / live.ROOT_NAME / 'endpoint.json').exists())

    def test_server_restart_wrong_original_nonce_does_not_stop_live_server(self):
        ticket = self.issue()
        self.serve(ticket)
        with self.assertRaisesRegex(live.Refusal, 'CI_LIVE_WITNESS_ENDPOINT_NOT_BOUND'):
            live.restart(self.root, ticket, HEAD, self.old, self.new,
                         'e' * 32, self.proc)
        self.assertIsNone(self.proc.poll())
        self.assertEqual(live.endpoint(self.root, HEAD, ticket, NONCE)['head'], HEAD)

    def test_server_restart_rejects_unsafe_db_mode_before_listener(self):
        ticket = self.issue()
        self.serve(ticket)
        live.stop(self.proc)
        (self.root / live.ROOT_NAME / 'operations.sqlite').chmod(0o644)
        with self.assertRaisesRegex(live.Refusal, 'CI_LIVE_WITNESS_RESTART_DB_UNTRUSTED'):
            live.restart(self.root, ticket, HEAD, self.old, self.new,
                         NONCE, self.proc)
        self.assertFalse((self.root / live.ROOT_NAME / 'endpoint.json').exists())

    def test_mode_refuses_without_disposable_flags(self):
        with mock.patch.dict(os.environ,
                             {'ZAPRET2_STAGE3_NATIVE_LIVE_WITNESS':'1'}, clear=True):
            with self.assertRaisesRegex(live.Refusal, 'CI_LIVE_WITNESS_DISPOSABLE_OPTIN_REQUIRED'):
                live.mode()
        with mock.patch.dict(os.environ,
                             {'ZAPRET2_STAGE3_NATIVE_LIVE_WITNESS':'bad'}, clear=True):
            with self.assertRaisesRegex(live.Refusal, 'CI_LIVE_WITNESS_MODE_INVALID'):
                live.mode()

    def test_invalid_original_transfer_nonce_refused(self):
        with self.assertRaisesRegex(live.Refusal,'CI_LIVE_WITNESS_TICKET_NONCE_INVALID'):
            live.make_request('RESERVE', {}, HEAD, 'wrong')

    def test_random_challenge_changes_even_for_same_operation(self):
        req = {'operation_id': 'a'*64, 'payload_sha256': self.new_sha,
               'checkpoint_sha256': self.old_sha, 'checkpoint_sequence': 1}
        first = live.make_request('RESERVE', req, HEAD, NONCE)
        second = live.make_request('RESERVE', req, HEAD, NONCE)
        self.assertNotEqual(first['challenge_sha256'], second['challenge_sha256'])
        self.assertEqual(first['operation_id'], second['operation_id'])

    def test_exact_owner_only_signer_and_cert_fixture(self):
        pins = live.prepare(self.root)
        self.assertEqual(len(pins['server_sha256']), 64)
        self.assertEqual(len(pins['client_sha256']), 64)
        folder = self.root / live.ROOT_NAME
        for f in folder.iterdir():
            self.assertEqual(f.stat().st_mode & 0o777, 0o600)
        with self.assertRaisesRegex(live.Refusal,'CI_LIVE_WITNESS_FOREIGN_ROOT_PRESENT'):
            live.prepare(self.root)

    def test_endpoint_nonce_and_client_pin_are_exact(self):
        ticket = self.issue()
        self.serve(ticket)
        self.assertEqual(live.endpoint(self.root, HEAD, ticket, NONCE)['head'], HEAD)
        with self.assertRaisesRegex(live.Refusal,'CI_LIVE_WITNESS_ENDPOINT_NOT_BOUND'):
            live.endpoint(self.root, HEAD, ticket, 'e'*32)

    def test_unsafe_hardlinked_private_endpoint_refused(self):
        ticket = self.issue()
        self.serve(ticket)
        source = self.root / live.ROOT_NAME / 'endpoint.json'
        os.link(source, self.root / live.ROOT_NAME / 'foreign-hardlink')
        with self.assertRaisesRegex(live.Refusal,'CI_LIVE_WITNESS_PRIVATE_FILE_INVALID'):
            live.endpoint(self.root, HEAD, ticket, NONCE)

    def test_cleanup_foreign_resource_refused(self):
        ticket = self.issue()
        self.serve(ticket)
        self.stop()
        foreign = self.root / live.ROOT_NAME / 'foreign'
        foreign.write_bytes(b'not-owned')
        with self.assertRaisesRegex(live.Refusal, 'CI_LIVE_WITNESS_FOREIGN_OR_MISSING_CLEANUP_FILE'):
            live.cleanup(self.root)
        self.assertTrue(foreign.exists())

    def test_source_proves_live_request_before_real_pkg_and_no_prod_trust(self):
        parent = HERE/'stage3-native-configd-fd9-handoff.py'
        worker = HERE/'stage3-native-configd-mutating-pkg.py'
        workflow = HERE.parent/'.github/workflows/stage2-native-delegated-fd9-handoff.yml'
        source = parent.read_text()
        run = worker.read_text()
        self.assertIn('live_process=live.start(ROOT,ci_grant,head,base.OLD,native_archive,nonce)',source)
        self.assertIn('confirmed=live.confirm(ROOT,ci_grant,head,nonce)',source)
        self.assertIn('live.stop(live_process)',source)
        self.assertIn('live.cleanup(ROOT)',source)
        self.assertIn("live_phase='consume' if live_witness else None",run)
        self.assertIn("live_phase='status' if live_witness else None",run)
        self.assertLess(run.index('approval=grant_guard.verify('),
                        run.index('second=grant_guard.verify('))
        self.assertLess(run.index('second=grant_guard.verify('),
                        run.index('delegate.admitted_pkg_dispatch(archive,candidate,env)'))
        self.assertIn('configd-native-live-mtls-sqlite-witness-stdin:',workflow.read_text())
        self.assertIn("'ci_operator_grant_is_owner_approved':False",source)
        self.assertIn("'lh08_ac11_accepted':False",source)


if __name__=='__main__':
    unittest.main()
