#!/usr/bin/env python3
"""Offline negative contracts for real historical old Status syscall trace."""
import importlib.util
import hashlib
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'stage2-original-fd9-syscall-trace.py'
spec = importlib.util.spec_from_file_location('stage2_original_trace', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def witness(*, held, timeout, rc, lockf=True, original_stopped=False,
            exclusive=False):
    return {
        'held': held,
        'bounded_timeout': timeout,
        'exit': rc,
        'independent_fd9_exclusive': exclusive,
        'reported_original_cold_status': original_stopped,
        'syscalls': {
            'historical_lockf_exec_observed': lockf,
            'old_lock_path_observed': True,
            'flock_syscall_recorded': False,
            'fcntl_syscall_recorded': False},
        'wait': {'lockf_processes_observed': 1,
                 'sleeping_lockf_wchan_visible': False}
    }


class OriginalOldFd9TraceContracts(unittest.TestCase):
    def test_real_control_and_held_bounded_timeout_classification(self):
        old = witness(held=False, timeout=False, rc=1,
                      original_stopped=True)
        held = witness(held=True, timeout=True, rc=None, exclusive=True)
        self.assertEqual(module.classify(old, held),
                         'OBSERVED_ORIGINAL_STATUS_NESTED_LOCKF_NOT_FINISHED_WITH_HELD_FD9')
        # FreeBSD truss itself may return zero for the traced child even
        # though the authenticated original Status is STOPPED (exit 1).
        self.assertEqual(module.classify(old | {'exit': 0}, held),
                         'OBSERVED_ORIGINAL_STATUS_NESTED_LOCKF_NOT_FINISHED_WITH_HELD_FD9')

    def test_held_stopped_is_not_a_safe_pkg_claim(self):
        old = witness(held=False, timeout=False, rc=1,
                      original_stopped=True)
        held = witness(held=True, timeout=False, rc=1,
                       exclusive=True, original_stopped=True)
        self.assertEqual(module.classify(old, held),
                         'OBSERVED_ORIGINAL_STATUS_COMPLETED_WITH_HELD_FD9_NOT_AUTHORIZED')

    def test_ambiguous_original_status_or_fd9_or_trace_fails_closed(self):
        old = witness(held=False, timeout=False, rc=1,
                      original_stopped=True)
        held = witness(held=True, timeout=True, rc=None, exclusive=True)
        cases = [
            (old | {'exit': 2}, held, 'CONTROL_STATUS'),
            (old | {'bounded_timeout': True}, held, 'CONTROL_STATUS'),
            (old | {'reported_original_cold_status': False}, held, 'CONTROL_STATUS'),
            (old, held | {'independent_fd9_exclusive': False}, 'NOT_INDEPENDENTLY'),
            (old | {'syscalls': {**old['syscalls'],
                                'historical_lockf_exec_observed': False}},
             held, 'CONTROL_LOCKF_EXEC'),
            (old, held | {'syscalls': {**held['syscalls'],
                                      'historical_lockf_exec_observed': False}},
             'HELD_LOCKF_EXEC'),
            (old, held | {'bounded_timeout': False, 'exit': None}, 'HELD_STATUS_MISSING')
        ]
        for wrong_old, wrong_held, reason in cases:
            with self.subTest(reason=reason), self.assertRaisesRegex(
                    module.Refusal, reason):
                module.classify(wrong_old, wrong_held)

    def test_actual_truss_trace_is_redacted_to_fixed_boolean_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'truss.log'
            raw = ('123: openat(AT_FDCWD,"/var/run/zapret2-lifecycle.lock",'
                   'O_WRONLY|O_CREAT) = 9\n'
                   '123: execve("/usr/bin/lockf",...) = 0\n'
                   '123: flock(9,LOCK_EX) = 0\n'
                   '123: fcntl(9,F_GETFD) = 0\n').encode()
            p.write_bytes(raw)
            report = module.summarize_trace(p)
            self.assertEqual(report['trace_sha256'],
                             hashlib.sha256(raw).hexdigest())
            self.assertEqual(report['trace_bytes'], len(raw))
            self.assertTrue(report['historical_lockf_exec_observed'])
            self.assertTrue(report['old_lock_path_observed'])
            self.assertTrue(report['flock_syscall_recorded'])
            self.assertTrue(report['fcntl_syscall_recorded'])
            self.assertNotIn('raw_trace', report)
            self.assertNotIn('arguments', report)

    def test_missing_or_oversized_trace_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'trace'
            for raw in (b'', b'x' * (module.MAX_TRACE_BYTES + 1)):
                p.write_bytes(raw)
                with self.assertRaisesRegex(
                        module.Refusal, 'NATIVE_TRACE_EMPTY_OR_OVERSIZED'):
                    module.summarize_trace(p)
            p.unlink()
            with self.assertRaisesRegex(module.Refusal, 'NATIVE_TRACE_FILE_MISSING'):
                module.summarize_trace(p)

    def test_independent_fd9_challenger_must_return_75(self):
        for rc in (75, 0, 1):
            with self.subTest(rc=rc), patch.object(
                    module.subprocess, 'run',
                    return_value=SimpleNamespace(returncode=rc)) as fake:
                if rc == 75:
                    module.challenge(module.LOCK)
                else:
                    with self.assertRaisesRegex(
                            module.Refusal, 'INDEPENDENT_FD9_CHALLENGER_NOT_BUSY'):
                        module.challenge(module.LOCK)
                args = fake.call_args.args[0]
                self.assertEqual(args[:3],
                                 ['/bin/sh', '-c', module.CHALLENGER])
                self.assertEqual(args[-1], str(module.LOCK))

    def test_native_truss_path_and_original_fd9_are_not_simulated(self):
        source = SOURCE.read_text()
        required = (
            'exec 9>"$1"', '/usr/bin/lockf -s -t 0 9',
            'exec /usr/bin/truss -f -o "$3" "$4" status',
            "TRACE_EXEC = Path('/usr/bin/truss')",
            'proc.communicate(timeout=7)',
            'os.killpg(proc.pid, signal.SIGKILL)',
            'prior.wait_held(marker, proc)',
            'challenge(LOCK)',
            'installer.install_and_verify(archive)',
            "guard.snapshot(archive)",
            "managed.owner_snapshot(old, guard, archive)",
            "after == before",
            "'real_mutating_pkg_attempted': False",
            "'safe_managed_pkg_handshake_proven': False",
            "'lh08_ac11_accepted': False"
        )
        for token in required:
            with self.subTest(token=token):
                self.assertIn(token, source)
        self.assertLess(source.index("control = trace_case("),
                        source.index("historical = trace_case("))
        self.assertNotIn("pkg add -f", source)
        for unsafe in ('pkg upgrade', 'pkg delete', 'ipfw flush',
                       'configctl zapret stop', 'service_dispatch('):
            with self.subTest(unsafe=unsafe):
                self.assertNotIn(unsafe, source)

    def test_native_workflow_is_scoped_to_genuine_opnsense_not_owner(self):
        workflow = (HERE.parent / '.github/workflows/'
                    'stage2-original-fd9-syscall-trace.yml').read_text()
        self.assertIn('vmactions/opnsense-vm@abaa977e3dbc77a0d1eeed4d82c8d9914b018235',
                      workflow)
        self.assertIn('release: "26.7"', workflow)
        self.assertIn('ZAPRET2_STAGE2_ORIGINAL_FD9_SYSCALL_TRACE=1', workflow)
        self.assertIn('scripts/test-stage2-original-fd9-syscall-trace.py -v',
                      workflow)
        self.assertNotIn('ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK=1', workflow)


if __name__ == '__main__':
    unittest.main()
