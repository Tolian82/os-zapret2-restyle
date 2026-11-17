#!/usr/bin/env python3
"""Portable S0 regression for the disposable QEMU hard-reset acceptance."""
import importlib.util
import xml.etree.ElementTree as ET
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

    def test_saved_xml_fingerprint_distinguishes_plugin_and_system(self):
        import xml.etree.ElementTree as ET
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "config.xml"
            path.write_bytes(b'''<opnsense>
  <system><hostname>old</hostname></system>
  <interfaces><wan><if>vtnet0</if></wan></interfaces>
  <OPNsense><Zapret><strategy><trafficargs>--filter-tcp=443
--new</trafficargs></strategy></Zapret></OPNsense>
</opnsense>''')
            with mock.patch.object(fixture, "CONFIG", path):
                before = fixture.config_snapshot()
                path.write_bytes(path.read_bytes().replace(b"<hostname>old</hostname>",
                                                         b"<hostname>new</hostname>"))
                after_system = fixture.config_snapshot()
                self.assertNotEqual(before["full"], after_system["full"])
                self.assertEqual(before["plugin"], after_system["plugin"])
                self.assertEqual(before["interfaces"], after_system["interfaces"])
                path.write_bytes(path.read_bytes().replace(b"--filter-tcp=443",
                                                         b"--filter-tcp=80"))
                self.assertNotEqual(before["plugin"], fixture.config_snapshot()["plugin"])
                path.write_bytes(path.read_bytes().replace(b"vtnet0", b"vtnet1"))
                self.assertNotEqual(before["interfaces"],
                                    fixture.config_snapshot()["interfaces"])

    def test_xml_indentation_not_user_profile_content_is_ignored(self):
        base = ET.fromstring("<strategy><a>x</a><b>y</b></strategy>")
        formatted = ET.fromstring(
            "<strategy>\n    <a>x</a>\n  <b>y</b>\n</strategy>")
        self.assertEqual(fixture.stable_xml_value(base),
                         fixture.stable_xml_value(formatted))
        a = ET.fromstring("<strategy><trafficargs>  --filter-tcp=443</trafficargs></strategy>")
        b = ET.fromstring("<strategy><trafficargs>--filter-tcp=443</trafficargs></strategy>")
        self.assertNotEqual(fixture.stable_xml_value(a),
                            fixture.stable_xml_value(b))

        c = ET.fromstring("<strategy><value>x</value>suffix</strategy>")
        d = ET.fromstring("<strategy><value>x</value>changed</strategy>")
        self.assertNotEqual(fixture.stable_xml_value(c),
                            fixture.stable_xml_value(d))

    def test_native_xml_structure_is_read_only_and_identifies_missing_plugin(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "config.xml"
            path.write_bytes(b"<opnsense><interfaces/><OPNsense><Zapret/></OPNsense></opnsense>")
            with mock.patch.object(fixture, "CONFIG", path):
                got = fixture.config_structure()
                self.assertTrue(got["valid_xml"])
                self.assertTrue(got["zapret_section_present"])
                self.assertTrue(got["interfaces_section_present"])
                path.write_bytes(b"<opnsense><interfaces/></opnsense>")
                missing = fixture.config_structure()
                self.assertFalse(missing["zapret_section_present"])
                self.assertTrue(missing["interfaces_section_present"])
                path.write_bytes(b"<opnsense><OPNsense><Zapret/></OPNsense></opnsense>")
                other = fixture.config_structure()
                self.assertTrue(other["zapret_section_present"])
                self.assertFalse(other["interfaces_section_present"])
                path.write_bytes(b"<opnsense")
                invalid = fixture.config_structure()
                self.assertFalse(invalid["valid_xml"])

    def test_postboot_avoids_lifecycle_calls_if_saved_section_missing(self):
        content = SOURCE.read_text()
        verify = content.split("def guest_verify():", 1)[1]
        before_mutations = verify.split('denied = {', 1)[0]
        self.assertIn('postboot_readonly_classification(receipt)', before_mutations)
        self.assertIn('"POSTBOOT_SAVED_PLUGIN_OR_INTERFACES_MISSING"', before_mutations)
        self.assertNotIn('[str(SERVICE), "start"]', before_mutations)
        self.assertIn('"postboot_mutation_attempted": False', content)

    def test_value_free_plugin_path_diagnostics_find_only_modified_names(self):
        import xml.etree.ElementTree as ET
        before = ET.fromstring(
            "<Zapret><hostlist><mode>auto</mode></hostlist>"
            "<strategy><trafficargs>--filter-tcp=443</trafficargs>"
            "</strategy></Zapret>")
        after = ET.fromstring(
            "<Zapret><hostlist><mode>list</mode></hostlist>"
            "<strategy><trafficargs>--filter-tcp=443</trafficargs>"
            "</strategy></Zapret>")
        saved = fixture.plugin_diagnostic_paths(before)
        modified = fixture.plugin_diagnostic_paths(after)
        changed = fixture.diagnostic_changed_paths(saved, modified)
        self.assertEqual(changed, ["Zapret/hostlist[0]/mode[0]"])
        self.assertTrue(all("--filter-tcp" not in item and "auto" not in item
                            for item in changed))

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

    def test_pre_reset_diagnostic_only_observes_original_native_calls(self):
        contents = SOURCE.read_text()
        observer = contents.split("def observing_run(argv, **kwargs):", 1)[1]
        observer = observer.split("native.run = observing_run", 1)[0]
        self.assertIn("original_native_run(argv, **kwargs)", observer)
        self.assertIn("return result", observer)
        self.assertIn('call_rc[argv[1]] = result.returncode', observer)
        self.assertIn('"config_unchanged": digest(CONFIG) == config_before_partial',
                      contents)
        self.assertIn("native.run = original_native_run", contents)

    def test_disposable_native_config_fsync_is_read_only_and_no_symlink(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "config.xml"
            path.write_bytes(b"<opnsense><interfaces/></opnsense>")
            before = path.read_bytes()
            with mock.patch.object(fixture, "CONFIG", path):
                fixture.flush_native_saved_config_in_disposable_setup()
            self.assertEqual(path.read_bytes(), before)
            link = Path(root) / "config-link"
            link.symlink_to(path)
            with mock.patch.object(fixture, "CONFIG", link):
                with self.assertRaisesRegex(RuntimeError, "NATIVE_SAVED_CONFIG_UNTRUSTED"):
                    fixture.flush_native_saved_config_in_disposable_setup()

    def test_untrusted_installed_service_does_not_execute_lifecycle(self):
        code = SOURCE.read_text()
        verify = code.split("def guest_verify():", 1)[1]
        refusal_branch = verify.split('if not postboot["installed_service_source_trusted"]:', 1)[1]
        refusal_branch = refusal_branch.split('return', 1)[0]
        self.assertIn('"mutation_attempted": False', refusal_branch)
        self.assertIn('"recovery_tested": False', refusal_branch)
        self.assertNotIn("run([str(SERVICE)", refusal_branch)
        self.assertIn('postboot["guard_private_staged_package_unchanged"]', verify)

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
