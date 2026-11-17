#!/usr/bin/env python3
"""Portable S0 contracts for post-reset read-only host diagnostics."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SRC = Path(__file__).with_name('stage5-native-reset-observer.py')
spec = importlib.util.spec_from_file_location('native_boot_observer', SRC)
obs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(obs)


class BootObservationContracts(unittest.TestCase):
    def test_exact_snapshot_qemu_only_and_action_serial_log(self):
        with tempfile.TemporaryDirectory() as root:
            proc = Path(root)
            (proc / '7').mkdir()
            path = (obs.ANYVM_ACTION_ROOT / 'abc123' / 'output' /
                    'opnsense-26.7-amd64.serial.log')
            args = [b'/usr/bin/qemu-system-x86_64', b'-snapshot',
                    b'-drive', b'file=/tmp/opnsense.qcow2',
                    b'-serial', b'chardev:serial0', b'-chardev',
                    ('socket,id=serial0,host=127.0.0.1,port=7000,server=on,'
                     'wait=off,logfile=' + str(path)).encode()]
            (proc / '7' / 'cmdline').write_bytes(b'\x00'.join(args) + b'\x00')
            argv = obs.qemu_argv(7, proc)
            self.assertEqual(obs.serial_log_path(argv), path)
            self.assertEqual(obs.serial_log_path(argv[:-2]), None)
            (proc / '7' / 'cmdline').write_bytes(
                (proc / '7' / 'cmdline').read_bytes().replace(b'-snapshot', b'-no-snapshot'))
            self.assertEqual(obs.qemu_argv(7, proc), [])
            self.assertIsNone(obs.serial_log_path([
                '-serial', 'chardev:serial0', '-chardev',
                'socket,id=serial0,logfile=/tmp/secret.serial.log']))

    def test_bounded_console_observation_never_prints_bytes(self):
        with tempfile.TemporaryDirectory() as root:
            log = Path(root) / 'console.serial.log'
            log.write_bytes(b'first boot with secret\n')
            baseline = obs.safe_serial_size(log)
            log.write_bytes(log.read_bytes() + b'FreeBSD/amd64 booting\nlogin: ')
            got = obs.serial_delta(log, baseline)
            self.assertEqual(got['new_bytes'], len(b'FreeBSD/amd64 booting\nlogin: '))
            self.assertTrue(got['freebsd_kernel_signal'])
            self.assertTrue(got['login_prompt_signal'])
            self.assertNotIn('secret', str(got))
            self.assertFalse(obs.serial_delta(log, log.stat().st_size)
                             ['freebsd_kernel_signal'])
            link = Path(root) / 'link'
            link.symlink_to(log)
            self.assertIsNone(obs.safe_serial_size(link))
            self.assertFalse(obs.serial_delta(link, 0)['readable'])

    def test_ssh_config_only_loopback_forward(self):
        class P:
            returncode = 0
            stdout = 'hostname example.com\nport 10022\n'
        with mock.patch.object(obs.subprocess, 'run', return_value=P()):
            self.assertFalse(obs.ssh_forward_probe()['alias_loopback'])
        P.stdout = 'hostname 127.0.0.1\nport 10022\n'
        class Conn:
            def __enter__(self): return self
            def __exit__(self, *exc): pass
            def settimeout(self, n): pass
            def recv(self, n): return b'SSH-2.0-OpenSSH_9\r\n'
        with mock.patch.object(obs.subprocess, 'run', return_value=P()), \
             mock.patch.object(obs.socket, 'create_connection', return_value=Conn()):
            self.assertEqual(obs.ssh_forward_probe(), {
                'alias_loopback': True, 'tcp_accepts': True,
                'ssh_banner_seen': True})

    def test_hmp_serial_ssh_observations_never_claim_kernel_boottime(self):
        with mock.patch.object(obs, 'qemu_argv', return_value=['qemu']), \
             mock.patch.object(obs, 'ssh_forward_probe', return_value={}), \
             mock.patch.object(obs, 'serial_delta', return_value={}):
            got = obs.observe(123, 4444,
                              lambda p, command: 'VM status: running\n(qemu)',
                              None, None)
        self.assertTrue(got['hmp_running'])
        self.assertNotIn('boot_confirmed', got)
        self.assertNotIn('new_kernel_boot', got)


if __name__ == '__main__':
    unittest.main()
