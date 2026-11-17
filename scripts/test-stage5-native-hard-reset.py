#!/usr/bin/env python3
"""Portable S0 regression for the disposable QEMU hard-reset acceptance."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SOURCE = Path(__file__).with_name("stage5-native-hard-reset.py")
spec = importlib.util.spec_from_file_location("hardreset_fixture", SOURCE)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class HardResetContracts(unittest.TestCase):
    def test_boot_time_and_untrusted_reply(self):
        self.assertEqual(
            fixture.boot_seconds("{ sec = 1794915324, usec = 6721 }"),
            1794915324)
        with self.assertRaisesRegex(ValueError, "BOOT_TIME_NOT_PARSEABLE"):
            fixture.boot_seconds("kernel rebooted")

    def test_snapshot_qemu_monitor_is_uniquely_qualified(self):
        with tempfile.TemporaryDirectory() as root:
            proc = Path(root)
            one = proc / "101"
            one.mkdir()
            (one / "cmdline").write_bytes(
                b"/usr/bin/qemu-system-x86_64\0-snapshot\0"
                b"-drive\0file=/tmp/opnsense-26.7.qcow2\0"
                b"-monitor\0tcp:127.0.0.1:4488,server,nowait,nodelay\0")
            other = proc / "102"
            other.mkdir()
            (other / "cmdline").write_bytes(
                b"/usr/bin/qemu-system-x86_64\0"
                b"-drive\0file=/tmp/other-guest.qcow2\0"
                b"-monitor\0tcp:0.0.0.0:4489,server,nowait,nodelay\0")
            self.assertEqual(fixture.qemu_candidates(proc), [(101, 4488)])
            (one / "cmdline").write_bytes(
                b"/usr/bin/qemu-system-x86_64\0-snapshot\0"
                b"-drive\0file=/tmp/opnsense-26.7.qcow2\0"
                b"-monitor\0tcp:0.0.0.0:4488,server,nowait,nodelay\0")
            self.assertEqual(fixture.qemu_candidates(proc), [])

    def test_os_owned_config_accepts_native_file_and_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "config.xml"
            path.write_bytes(b"<opnsense/>")
            twin = Path(root) / "hardlinked"
            import os
            os.link(path, twin)
            with mock.patch.object(fixture, "CONFIG", path):
                self.assertTrue(fixture.opnsense_config_readable())
            link = Path(root) / "symlink"
            link.symlink_to(path)
            with mock.patch.object(fixture, "CONFIG", link):
                self.assertFalse(fixture.opnsense_config_readable())

    def test_guest_and_host_actions_refuse_outside_disposable_context(self):
        with mock.patch.dict(fixture.os.environ, {
                "GITHUB_ACTIONS": "false",
                "ZAPRET2_NATIVE_HARDRESET_HOST": "1",
                "ZAPRET2_NATIVE_HARDRESET_TEST": "1"}, clear=True):
            with self.assertRaisesRegex(
                    RuntimeError, "NOT_DISPOSABLE_GITHUB_VM_HOST"):
                fixture.host_hard_reset()
            with self.assertRaisesRegex(
                    RuntimeError, "NOT_DISPOSABLE_FREEBSD_GUEST"):
                fixture.guest_gate()

    def test_minimal_auto_setup_reuses_exact_native_midextract(self):
        source = SOURCE.read_text()
        self.assertIn('def guest_setup():', source)
        self.assertIn('strategies.request("auto")', source)
        self.assertIn("native.native_partial_payload_interruption(", source)
        self.assertNotIn("native.native_running_reinstall(", source)
        self.assertNotIn("native.native_interrupted_handoff(", source)

    def test_reboot_is_not_host_power_loss_or_pkgdb_repair(self):
        source = SOURCE.read_text()
        self.assertIn('monitor_command(port, "system_reset")', source)
        self.assertNotIn("system_powerdown", source)
        self.assertNotIn("qemu-img commit", source)
        self.assertNotIn("pkg add -f", source)
        self.assertIn('"power_loss_tested": False', source)
        self.assertIn('"automatic_repair_attempted": False', source)


if __name__ == "__main__":
    unittest.main()
