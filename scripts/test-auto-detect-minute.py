#!/usr/bin/env python3
"""P2k8j real source-only configd ingress and fail-closed idle classification.

Only the disposable original OPNsense VM can prove configctl dispatch later;
this test never enables cron, changes config.xml or acknowledges a producer.
"""
from __future__ import annotations

import configparser
import io
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]
BACKEND = BASE / 'src/opnsense/scripts/OPNsense/Zapret/backend'
sys.path.insert(0, str(BACKEND))
import auto_detect_minute as minute
from auto_detect_minute import (inspect_inert_release, native_minute_once,
                                MinuteRefused)
from auto_detect_owner import GenerationProof, GenerationRefused
from auto_detect_fd import OwnerToken
from auto_detect_storage import RAW_PATH, DEBUG_PATH


class MinuteIngressContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='p2k8j-')
        self.addCleanup(self.temp.cleanup)
        self.active = Path(self.temp.name) / 'runtime-v2'
        self.active.mkdir(mode=0o700)
        self.uid = os.getuid()
        self.args = self.active / 'dvtws.args'
        self.generation = self.active / 'auto-detect-generation.json'

    def put_args(self, *items: str) -> None:
        self.args.write_text('\n'.join(items) + '\n', encoding='utf-8')
        self.args.chmod(0o600)

    def inspect(self) -> str:
        return inspect_inert_release(self.active, owner_uid=self.uid)

    def test_initial_missing_and_ordinary_shared_runtime_inert(self):
        self.assertEqual(self.inspect(), 'inactive')
        self.active.rmdir()
        self.assertEqual(self.inspect(), 'inactive')
        self.active.mkdir(mode=0o700)
        self.put_args('--port=989', '--filter-tcp=443', '--hostlist=/usr/local/etc/zapret2/ipset/auto-domains.txt')
        saved = self.args.read_bytes(), self.args.stat().st_mtime_ns
        self.assertEqual(self.inspect(), 'inactive')
        self.assertEqual(self.inspect(), 'inactive')
        self.assertEqual(saved, (self.args.read_bytes(), self.args.stat().st_mtime_ns))

    def test_real_native_auto_knobs_never_authorize_or_consume(self):
        for knob in ('--hostlist-auto=/var/db/zapret2-auto-detect/inbox.txt',
                     '--hostlist-auto-debug=/var/db/zapret2-auto-detect/debug.log',
                     '--hostlist-auto-fail-threshold=1', '--hostlist-auto'):
            with self.subTest(knob=knob):
                self.put_args('--port=989', knob)
                with self.assertRaisesRegex(MinuteRefused, 'worker_ack_not_authorized'):
                    self.inspect()
                self.assertEqual(self.args.read_text().strip().splitlines()[-1], knob)

    def test_forged_or_dangling_generation_cannot_authorize(self):
        self.put_args('--port=989', '--hostlist=/tmp/test')
        self.generation.write_text('{"schema":2}\n')
        with self.assertRaisesRegex(MinuteRefused, 'unexpected_native_generation'):
            self.inspect()
        self.generation.unlink()
        self.generation.symlink_to(self.active / 'not-present')
        with self.assertRaisesRegex(MinuteRefused, 'unexpected_native_generation'):
            self.inspect()
        self.args.unlink()
        with self.assertRaisesRegex(MinuteRefused, 'orphan_native_generation'):
            self.inspect()

    def test_unsafe_native_argv_and_release_refuse(self):
        self.put_args('--port=989')
        self.args.chmod(0o666)
        with self.assertRaises(MinuteRefused):
            self.inspect()
        self.args.chmod(0o600)
        self.args.unlink()
        self.args.symlink_to('/etc/passwd')
        with self.assertRaises(MinuteRefused):
            self.inspect()
        self.args.unlink()
        self.put_args('--port=989', '--filter-tcp=443')
        self.active.chmod(0o777)
        with self.assertRaisesRegex(MinuteRefused, 'unsafe_original_release_directory'):
            self.inspect()
        self.active.chmod(0o700)
        self.args.write_bytes(b'--port=989\x00--hostlist-auto=/var/db/x\n')
        with self.assertRaises(MinuteRefused):
            self.inspect()
        self.put_args('--port=989')
        target = Path(self.temp.name) / 'elsewhere'
        self.active.rename(target)
        self.active.symlink_to(target)
        with self.assertRaisesRegex(MinuteRefused, 'unsafe_original_release_directory'):
            self.inspect()

    def test_no_user_data_queue_or_config_mutations(self):
        self.put_args('--port=989')
        pending = Path(self.temp.name) / 'pending.txt'
        pending.write_bytes(b'old native event\n')
        pending.chmod(0o600)
        before = pending.stat().st_ino, pending.read_bytes(), pending.stat().st_mtime_ns
        self.assertEqual(self.inspect(), 'inactive')
        self.assertEqual(before, (pending.stat().st_ino, pending.read_bytes(), pending.stat().st_mtime_ns))
        self.assertFalse((Path(self.temp.name) / 'worker.lock').exists())

    def test_configd_route_is_registered_via_original_fd9_and_cron(self):
        config = configparser.RawConfigParser()
        path = BASE / 'src/opnsense/service/conf/actions.d/actions_zapret.conf'
        self.assertTrue(config.read(path))
        self.assertTrue(config.has_section('auto_detect_minute'))
        action = config['auto_detect_minute']
        self.assertEqual(action['parameters'], '')
        self.assertEqual(action['type'], 'script_output')
        self.assertEqual(action['timeout'], '60')
        self.assertEqual(action['command'], '/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh auto-detect-minute')
        service = (BASE / 'src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh').read_text()
        self.assertIn('auto-detect-minute)', service)
        self.assertIn('"$PYTHON_RUNTIME" "$BACKEND_DIR/auto_detect_minute.py"', service)
        self.assertIn('start|stop|restart|reconfigure|auto-detect-minute|auto-restart-tick|', service)
        self.assertIn('require_lifecycle_lock()', (BACKEND / 'auto_detect_original_lock_handoff.py').read_text())
        cron = BASE / 'src/etc/cron.d/zapret2-restyle'
        self.assertTrue(cron.is_file())
        lines = [x for x in cron.read_text().splitlines()
                 if 'zapret auto_detect_minute' in x and not x.startswith('#')]
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith('* * * * * root '))
        self.assertNotIn('auto_detect_minute.py', lines[0])

    def test_original_native_minute_runs_only_after_real_owner_attestation(self):
        # The caller is the original configd-only entry; production owner
        # attestation and P2a/Config child remain their one existing modules.
        proof = GenerationProof(
            OwnerToken(4242, 'Sun Nov 15 08:00:00 2026', '/tmp/dvtws2'),
            'a' * 32, 'a' * 32, 'b' * 64,
            str(RAW_PATH), str(DEBUG_PATH), 1,
            ((0, 'unknown-native-default', None), (1, 'observer', None)),
        )
        def run_once(result, owner):
            output, errors = io.StringIO(), io.StringIO()
            with patch.object(minute.sys, 'platform', 'freebsd15'), \
                 patch.object(minute.os, 'geteuid', return_value=0), \
                 patch.object(minute, 'require_lifecycle_lock'), \
                 patch.object(minute, 'inspect_inert_release',
                              side_effect=MinuteRefused(
                                  'native_observer_worker_ack_not_authorized')), \
                 patch.object(minute, '_secure_bytes', return_value=b'{"schema":2}'), \
                 patch.object(minute, 'attest_running_generation',
                              side_effect=owner if isinstance(owner, Exception) else None,
                              return_value=None if isinstance(owner, Exception) else owner), \
                 patch.object(minute, 'run_native_original_v2_cycle_once',
                              return_value=result) as composer, \
                 redirect_stdout(output), redirect_stderr(errors):
                rc = minute.native_minute_once([])
            return rc, output.getvalue(), errors.getvalue(), composer.call_count

        self.assertEqual(run_once(True, proof), (0, 'auto-detect-minute=processed\n', '', 1))
        self.assertEqual(run_once(False, proof), (0, 'auto-detect-minute=idle\n', '', 1))
        rc, out, err, called = run_once(True, GenerationRefused('stale'))
        self.assertEqual((rc, out, called), (69, '', 0))
        self.assertIn('auto-detect-minute-refused=GenerationRefused', err)
        bad = GenerationProof(
            proof.owner, proof.operation_id, proof.generation, proof.final_args_sha256,
            '/tmp/foreign-inbox', proof.debug_path, proof.observer_native_number, proof.profiles,
        )
        rc, out, err, called = run_once(True, bad)
        self.assertEqual((rc, out, called), (69, '', 0))
        self.assertIn('auto-detect-minute-refused=MinuteRefused', err)

    def test_learning_minute_reuses_original_config_owner_with_fd9(self):
        from auto_detect_owner import LearningGenerationProof
        generation = 'a' * 32
        proof = LearningGenerationProof(
            OwnerToken(4242, 'Sun Nov 15 08:00:00 2026', '/tmp/dvtws2'),
            generation, generation, 'b' * 64, 'c' * 64, 'd' * 64,
            ((3, 'youtube', str(minute.QUEUE_ROOT / ('learning-' + generation + '-3.txt'))),))
        with patch.object(minute.sys, 'platform', 'freebsd15'), \
             patch.object(minute.os, 'geteuid', return_value=0), \
             patch.object(minute, 'require_lifecycle_lock'), \
             patch.object(minute, 'inspect_inert_release', side_effect=MinuteRefused(
                 'native_observer_worker_ack_not_authorized')), \
             patch.object(minute, '_secure_bytes', return_value=b'{"schema":3}'), \
             patch.object(minute, 'attest_running_generation') as legacy, \
             patch.object(minute, 'attest_learning_running_generation', return_value=proof), \
             patch.object(minute, 'run_native_original_v2_cycle_once', return_value=True) as original, \
             redirect_stdout(io.StringIO()) as output:
            self.assertEqual(minute.native_minute_once([]), 0)
        original.assert_called_once_with(learning=True)
        legacy.assert_not_called()
        self.assertEqual(output.getvalue(), 'auto-detect-minute=processed\n')

    def test_learning_pre_stop_uses_only_original_fd9_epoch_and_cannot_authorize_old_retirement(self):
        from types import SimpleNamespace
        from auto_detect_owner import LearningGenerationProof
        from shared_apply_seal import WORK
        generation = 'a' * 32
        proof = LearningGenerationProof(
            OwnerToken(4242, 'Sun Nov 15 08:00:00 2026', '/tmp/dvtws2'),
            generation, generation, 'b' * 64, 'c' * 64, 'd' * 64,
            ((3, 'youtube', str(minute.QUEUE_ROOT /
                                ('learning-' + generation + '-3.txt'))),))
        from auto_detect_cursor_chain import CursorChain
        with patch.object(minute.sys, 'platform', 'freebsd15'), \
             patch.object(minute.os, 'geteuid', return_value=0), \
             patch.object(minute, 'require_lifecycle_lock') as fd9, \
             patch.object(minute, '_secure_bytes', return_value=b'{"schema":3}'), \
             patch('pwd.getpwnam', return_value=SimpleNamespace(pw_gid=65534)), \
             patch.object(minute, 'attest_running_generation') as legacy, \
             patch.object(minute, 'attest_learning_running_generation',
                          return_value=proof) as running, \
             patch.object(minute, 'DurableInbox') as queue_type, \
             patch.object(minute, 'EpochReceipts') as receipts_type, \
             patch('auto_detect_cursor_chain.CursorChain') as chain_type:
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                self.assertEqual(minute.native_retire_preflight(), 0)
            self.assertEqual(out.getvalue(),
                             'auto-detect-retire=original-learning-running-attested\n')
            self.assertEqual(err.getvalue(), '')
            fd9.assert_called_once_with()
            legacy.assert_not_called()
            self.assertEqual(running.call_count, 2)
            queue_type.assert_called_once_with(minute.QUEUE_ROOT,
                                               owner_uid=0, writer_gid=65534)
            receipts_type.assert_called_once_with(owner_uid=0, writer_gid=65534)
            chain_type.assert_called_once_with(receipts_type.return_value,
                                               queue_type.return_value)
            chain_type.return_value.learning_epoch.assert_called_once_with(
                proof, WORK / generation)
            queue_type.return_value.rotate.assert_not_called()
            queue_type.return_value.acknowledge.assert_not_called()

            # A missing/mismatched original epoch must refuse before any
            # schema2 P1/physical retirement, not downgrade to old raw.
            chain_type.return_value.learning_epoch.side_effect = RuntimeError('bad epoch')
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                self.assertEqual(minute.native_retire_preflight(), 69)
            self.assertEqual(out.getvalue(), '')
            self.assertIn('auto-detect-retire-refused=RuntimeError', err.getvalue())
            legacy.assert_not_called()

    def test_original_schema2_pre_stop_keeps_existing_owner_and_drift_path(self):
        from types import SimpleNamespace
        proof = GenerationProof(
            OwnerToken(4242, 'Sun Nov 15 08:00:00 2026', '/tmp/dvtws2'),
            'a' * 32, 'a' * 32, 'b' * 64,
            str(RAW_PATH), str(DEBUG_PATH), 1,
            ((0, 'unknown-native-default', None), (1, 'observer', None)),
        )
        with patch.object(minute.sys, 'platform', 'freebsd15'), \
             patch.object(minute.os, 'geteuid', return_value=0), \
             patch.object(minute, 'require_lifecycle_lock'), \
             patch.object(minute, '_secure_bytes', return_value=b'{"schema":2}'), \
             patch('pwd.getpwnam', return_value=SimpleNamespace(pw_gid=65534)), \
             patch.object(minute, 'attest_running_generation', return_value=proof) as legacy, \
             patch.object(minute, 'attest_learning_running_generation') as learning, \
             patch.object(minute, 'qualified_current_source'), \
             patch.object(minute, 'DurableInbox') as queue_type, \
             patch.object(minute, 'EpochReceipts') as receipts_type:
            receipts_type.return_value.verify_stop_only_epoch.return_value = False
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(minute.native_retire_preflight(), 0)
            self.assertEqual(out.getvalue(),
                             'auto-detect-retire=original-running-attested\n')
            self.assertEqual(legacy.call_count, 2)
            learning.assert_not_called()
            receipts_type.return_value.verify_stop_only_epoch.assert_called_once()
            queue_type.return_value.acknowledge.assert_not_called()

    def test_native_tick_denied_without_inherited_fd9_before_source_read(self):
        with patch.object(minute.sys, 'platform', 'freebsd15'), \
             patch.object(minute.os, 'geteuid', return_value=0), \
             patch.object(minute, 'require_lifecycle_lock',
                          side_effect=RuntimeError('fd9 missing')), \
             patch.object(minute, 'inspect_inert_release') as inspect, \
             patch.object(minute, 'attest_running_generation') as attest, \
             patch.object(minute, 'run_native_original_v2_cycle_once') as compose, \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(minute.native_minute_once([]), 69)
        inspect.assert_not_called()
        attest.assert_not_called()
        compose.assert_not_called()

    def test_original_stopped_config_bridge_refusal_uses_static_marker_only(self):
        from auto_detect_original_lock_handoff import OriginalLockRefused
        known = OriginalLockRefused('original_config_child_deadline')
        self.assertEqual(minute.original_lock_guard(known),
                         'original_config_child_deadline')
        secret = 'youtube.example.test /conf/config.xml 9:foo'
        self.assertEqual(minute.original_lock_guard(OriginalLockRefused(secret)),
                         'unknown')
        self.assertIsNone(minute.original_lock_guard(RuntimeError(secret)))

        from types import SimpleNamespace
        from auto_detect_owner import LearningGenerationProof
        generation = 'a' * 32
        proof = LearningGenerationProof(
            OwnerToken(4242, 'Sun Nov 15 08:00:00 2026', '/tmp/dvtws2'),
            generation, generation, 'b' * 64, 'c' * 64, 'd' * 64,
            ((3, 'youtube', str(minute.QUEUE_ROOT /
                    ('learning-' + generation + '-3.txt'))),))
        with patch.object(minute.sys, 'platform', 'freebsd15'), \
             patch.object(minute.os, 'geteuid', return_value=0), \
             patch.object(minute, 'require_lifecycle_lock'), \
             patch.object(minute, '_entry_present', return_value=True), \
             patch.object(minute, '_secure_bytes', return_value=b'{"schema":3}'), \
             patch('pwd.getpwnam', return_value=SimpleNamespace(pw_gid=65534)), \
             patch('auto_detect_owner.attest_learning_stopped_generation',
                   return_value=proof), \
             patch.object(minute, 'DurableInbox') as queue, \
             patch.object(minute, 'EpochReceipts') as receipts, \
             patch.object(minute, 'run_native_original_v2_cycle_once',
                          side_effect=known), \
             redirect_stderr(io.StringIO()) as output:
            receipts.return_value._generation.return_value = Path('/tmp')
            self.assertEqual(minute.native_retire_once(), 69)
        self.assertIn('auto-detect-retire-original-guard=original_config_child_deadline',
                      output.getvalue())
        self.assertNotIn(secret, output.getvalue())

    def test_schema3_retirement_reports_only_qualified_static_guard(self):
        from auto_detect_learning_retirement import LearningRetirementRefused
        qualified = LearningRetirementRefused("stopped_learning_source_fd_busy")
        self.assertEqual(
            minute.learning_retirement_guard(qualified),
            "stopped_learning_source_fd_busy")
        private = "private config.example.org /conf/config.xml"
        self.assertEqual(
            minute.learning_retirement_guard(LearningRetirementRefused(private)),
            "unknown")
        self.assertIsNone(minute.learning_retirement_guard(RuntimeError(private)))
        with patch.object(minute.sys, 'platform', 'freebsd15'), \
             patch.object(minute.os, 'geteuid', return_value=0), \
             patch.object(minute, 'require_lifecycle_lock'), \
             patch.object(minute, '_entry_present', return_value=True), \
             patch.object(minute, '_secure_bytes', return_value=b'{"schema":3}'), \
             patch('auto_detect_owner.attest_learning_stopped_generation',
                   side_effect=qualified), \
             redirect_stderr(io.StringIO()) as output:
            self.assertEqual(minute.native_retire_once(), 69)
        self.assertIn(
            'auto-detect-retire-guard=stopped_learning_source_fd_busy',
            output.getvalue())
        self.assertIn(
            'auto-detect-retire-refused=LearningRetirementRefused',
            output.getvalue())
        self.assertNotIn(private, output.getvalue())

    def test_native_entry_refuses_foreign_platform_and_cli_args(self):
        self.assertEqual(native_minute_once(['arbitrary']), 64)
        if sys.platform.startswith('freebsd') and os.geteuid() == 0:
            self.skipTest('native stock OPNsense test required for real path')
        self.assertEqual(native_minute_once([]), 69)


if __name__ == '__main__':
    unittest.main(verbosity=2)
