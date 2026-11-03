#!/usr/bin/env python3
"""Executable fail-closed contracts for one-use original FD9 delegated hook."""
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
SOURCE = HERE / 'stage2-native-delegated-fd9-handoff.py'
spec = importlib.util.spec_from_file_location('test_native_fd9_handoff', SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class DelegatedOldFD9Tests(unittest.TestCase):
    def test_only_real_original_lockf_timeout_and_descriptor_accepted(self):
        for argv in (['-s','-t','0','9'], ['-s','-t','1','9'],
                     ['-s','-t','5','9'], ['-s','-t','30','9']):
            mod.shim_arguments(argv)
        for argv in (['-s', '-t', '30', '8'], ['-s', '-t', '999', '9'],
                     ['-s', '-t', '-1', '9'], ['-s', '-t', '30'],
                     ['-t', '-s', '30', '9'], [], ['-s', '-t', '30', '9', 'extra']):
            with self.subTest(argv=argv), self.assertRaisesRegex(
                    mod.Refusal, 'UNEXPECTED_DELEGATED_LOCK_REQUEST'):
                mod.shim_arguments(argv)

    def test_ticket_is_exact_and_holder_bound_to_real_inode(self):
        fd=SimpleNamespace(st_dev=17, st_ino=44)
        ticket={'nonce':'a'*64, 'holder_pid':999, 'dev':17, 'ino':44}
        mod.ticket_validate(ticket,fd,'a'*64,999)
        for invalid in (
            (ticket,fd,'b'*64,999),
            (ticket,fd,'a'*64,1000),
            (ticket,SimpleNamespace(st_dev=17,st_ino=45),'a'*64,999),
            (ticket | {'unknown':'x'},fd,'a'*64,999),
            (ticket | {'holder_pid':'999'},fd,'a'*64,999),
            (ticket | {'nonce':'short'},fd,'short',999),
        ):
            with self.subTest(data=invalid),self.assertRaisesRegex(
                    mod.Refusal,'DELEGATED_LOCK_TICKET_INCORRECT'):
                mod.ticket_validate(*invalid)

    def test_independent_real_fd9_contender_expects_exact_75(self):
        for rc in (75,0,1,2):
            with patch.object(mod.subprocess,'run',
                              return_value=SimpleNamespace(returncode=rc)) as command:
                if rc==75:
                    mod.independent_challenge()
                else:
                    with self.assertRaisesRegex(
                            mod.Refusal,'ORIGINAL_FD9_NOT_ACTUALLY_EXCLUSIVE'):
                        mod.independent_challenge()
                argv=command.call_args.args[0]
                self.assertIn('/usr/bin/lockf -s -t 0 9', argv[2])
                self.assertEqual(argv[-1],str(mod.LOCK))

    def test_ticket_modes_and_symlinks_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            file=folder/'ticket'
            file.write_text('{}')
            file.chmod(0o600)
            # GitHub ubuntu-latest tests are non-root; the real KVM probe
            # validates the root-owned success case, this unit test enforces
            # rejection for an unprivileged fixture without bypassing checks.
            if file.lstat().st_uid == 0:
                mod.trusted_inode(file,0o600)
            else:
                with self.assertRaisesRegex(mod.Refusal, 'MODE_OR_OWNER_UNTRUSTED'):
                    mod.trusted_inode(file,0o600)
            file.chmod(0o644)
            with self.assertRaises(mod.Refusal):
                mod.trusted_inode(file,0o600)
            file.unlink()
            file.symlink_to(folder/'nonexistent')
            with self.assertRaises(mod.Refusal):
                mod.trusted_inode(file,0o600)

    def test_count_calls_accepts_only_bounded_exact_lines(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            self.assertEqual(mod.count_calls(folder),0)
            marker=folder/'delegated.calls'
            marker.write_bytes(b'ACCEPTED\nACCEPTED\n')
            marker.chmod(0o600)
            # The runner is intentionally unprivileged; isolate the
            # marker parser while ownership/mode are exercised separately.
            # Do NOT weaken the production root-only trusted_inode gate.
            with patch.object(mod, 'trusted_inode') as checked:
                self.assertEqual(mod.count_calls(folder),2)
                marker.write_bytes(b'ACCEPTED\nFORGED\n')
                with self.assertRaisesRegex(
                        mod.Refusal,'DELEGATED_CALL_MARKER_MALFORMED'):
                    mod.count_calls(folder)
                marker.write_bytes(b'X'*4097)
                with self.assertRaisesRegex(
                        mod.Refusal,'DELEGATED_CALL_MARKER_MALFORMED'):
                    mod.count_calls(folder)
                self.assertEqual(checked.call_count,3)

    def test_real_pkg_path_passes_original_fd9_not_a_mock(self):
        fake=Mock()
        fake.return_value.communicate.return_value=('installed','')
        fake.return_value.returncode=0
        with patch.object(mod.subprocess,'Popen',fake):
            self.assertEqual(mod.run_pkg(Path('/tmp/successor.pkg'),{'LOCKF_BIN':'testshim'}),
                             (0,'installed',''))
        args=fake.call_args.args[0]
        self.assertEqual(args[:6],
                         ['/usr/sbin/pkg','-o','REPO_AUTOUPDATE=false','add','-f',
                          '/tmp/successor.pkg'])
        self.assertEqual(fake.call_args.kwargs['pass_fds'],(9,))
        self.assertTrue(fake.call_args.kwargs['start_new_session'])
        fake.return_value.communicate.assert_called_with(timeout=230)

    def test_native_pkg_timeout_kills_only_own_session_and_refuses(self):
        fake=Mock()
        fake.return_value.communicate.side_effect=[
            subprocess.TimeoutExpired(cmd='pkg',timeout=230),('','')]
        fake.return_value.poll.return_value=None
        fake.return_value.pid=18181
        with patch.object(mod.subprocess,'Popen',fake), \
             patch.object(mod.os,'killpg') as killed:
            with self.assertRaisesRegex(
                    mod.Refusal,'NATIVE_PKG_UNBOUNDED_WITH_DELEGATED_FD9'):
                mod.run_pkg(Path('/tmp/successor.pkg'),{})
        killed.assert_called_once_with(18181,mod.signal.SIGKILL)

    def test_private_shim_mode_main_dispatch_cannot_fake_pkg_success(self):
        with patch.object(mod,'shim',return_value=0) as s, \
             patch.object(mod.sys,'argv',
                          ['shim','-s','-t','30','9']):
            self.assertEqual(mod.main(),0)
            s.assert_called_once_with(['-s','-t','30','9'])
        with patch.object(mod.sys,'argv',['shim','-s','-t','30','8']),\
             patch.object(mod,'shim',side_effect=mod.Refusal(
                 'DELEGATED_CHILD_FD9_NOT_HISTORICAL_INODE')):
            self.assertEqual(mod.main(),2)

    def test_read_only_cold_precondition_before_mutating_pkg(self):
        s=SOURCE.read_text()
        self.assertLess(s.index('locked.inside_lock(archive)'),
                        s.index('rc, out, err = admitted_pkg_dispatch(archive, successor, env)'))
        self.assertLess(s.index('count_calls(folder)\n        need(before_calls'),
                        s.index('rc, out, err = admitted_pkg_dispatch(archive, successor, env)'))
        final_gate = s[s.index('def admitted_pkg_dispatch('):
                       s.index('def inside_lock(', s.index('def admitted_pkg_dispatch('))]
        self.assertLess(final_gate.index('verify_old_cold_admission(archive)'),
                        final_gate.index('run_pkg if dispatch is None'))
        self.assertIn("native_calls >= 1",s)
        self.assertIn('old.run_guest', (HERE/'stage2-prepkg-locked-cold-revalidation.py').read_text())
        self.assertIn('locked.check_fd9()',s)
        self.assertIn("'lh08_ac11_accepted': False",s)

    def test_post_pkg_status_still_uses_same_delegated_fd9(self):
        source=SOURCE.read_text()
        self.assertNotIn('service_status = clean.cold_status()', source)
        self.assertIn("'NEW_SERVICE_DID_NOT_USE_PRIVATE_DELEGATED_FD9'", source)
        self.assertIn("post = subprocess.run(", source)
        self.assertIn("env=env, pass_fds=(9,)", source)
        self.assertIn("for name in clean.PRESERVED:", source)
        self.assertIn("stopped.verify_cold_runtime()", source)

    def test_test_only_override_not_any_installed_product(self):
        code=SOURCE.read_text()
        for token in (
            "OPTIN = 'ZAPRET2_STAGE2_DELEGATED_FD9_HANDOFF'",
            "'GITHUB_ACTIONS'", "'LOCKF_BIN': str(script)",
            "script.write_bytes(Path(__file__).read_bytes())",
            "script.chmod(0o700)",
            "ticket.chmod(0o600)",
            "os.fstat(9)",
            "secrets.compare_digest",
            "os.kill(pid, 0)",
            "'shim_installed_into_product': False",
            "'test_only_lockf_env_override': True",
            "'stock_firmware_web_covered': False",
            "'direct_root_pkg_covered': False",
            "'negative_no_pkg_invocation_proven_here': False",
            "'lh08_ac11_accepted': False",
        ):
            with self.subTest(token=token):
                self.assertIn(token,code)
        self.assertNotIn('ipfw flush',code)
        self.assertNotIn('pkg unlock',code)
        self.assertNotIn('configctl zapret stop',code)


if __name__=='__main__':
    unittest.main()
