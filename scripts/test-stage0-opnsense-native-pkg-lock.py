#!/usr/bin/env python3
"""Offline semantics of OPNsense-native pkg lock and firmware path probe."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SRC = Path(__file__).with_name("stage0-opnsense-native-pkg-lock.py")
spec = importlib.util.spec_from_file_location("native_lock", SRC)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
OLD = (m.NAME + "|0.6.2_1", b"old\n")
NEW = (m.NAME + "|0.6.2_39", b"new\n")


class NativePkgLock(unittest.TestCase):
    def test_locked_and_unlocked_measured_as_safe_bounded_behavior(self):
        self.assertEqual(m.verdict(OLD, OLD, NEW),
                         "PKG_LOCK_BLOCKED_DELETE_AND_FORCED_ADD_UNTIL_UNLOCK")

    def test_lock_did_not_prevent_delete_is_hazard(self):
        self.assertEqual(m.verdict(("ABSENT", None), ("ABSENT", None), ("ABSENT", None)),
                         "PKG_LOCK_BYPASS_OR_PARTIAL_MUTATION_OBSERVED")

    def test_lock_did_not_prevent_force_add_is_hazard(self):
        self.assertEqual(m.verdict(OLD, NEW, NEW),
                         "PKG_LOCK_BYPASS_OR_PARTIAL_MUTATION_OBSERVED")

    def test_partial_payload_is_hazard(self):
        self.assertEqual(m.verdict(OLD, (OLD[0], b"new\n"), NEW),
                         "PKG_LOCK_BYPASS_OR_PARTIAL_MUTATION_OBSERVED")

    def test_wrong_final_version_not_treated_as_full_pass(self):
        self.assertEqual(m.verdict(OLD, OLD, OLD), "NATIVE_PKG_LOCK_INCONCLUSIVE")

    def test_firmware_chain_accepts_supported_exact_phrases(self):
        expected = {
            "FirmwareController.php": 'configdpRun("firmware install" configdpRun("firmware remove" configdpRun("firmware reinstall"',
            "actions_firmware.conf": "[install] [remove] [reinstall] /usr/local/opnsense/scripts/firmware/launcher.sh install /usr/local/opnsense/scripts/firmware/launcher.sh remove",
            "launcher.sh": "config.sh LOCKFILE FLOCK COMMAND BASEDIR",
            "config.sh": 'LOCKFILE= FLOCK= PKG="/usr/local/sbin/pkg"',
            "install.sh": "install -y PACKAGE", "remove.sh": "remove -y PACKAGE",
            "reinstall.sh": "opnsense-revert",
        }
        snapshot = {k: (v, "sha256-"+k) for k, v in expected.items()}
        self.assertEqual(set(m.validate_firmware(snapshot)), set(expected))

    def test_firmware_missing_real_pkg_entrypoint_refused(self):
        expected = {
            "FirmwareController.php": 'configdpRun("firmware install" configdpRun("firmware remove" configdpRun("firmware reinstall"',
            "actions_firmware.conf": "[install] [remove] [reinstall] /usr/local/opnsense/scripts/firmware/launcher.sh install /usr/local/opnsense/scripts/firmware/launcher.sh remove",
            "launcher.sh": "config.sh LOCKFILE FLOCK COMMAND BASEDIR",
            "config.sh": 'LOCKFILE= FLOCK= PKG="/usr/local/sbin/pkg"',
            "install.sh": "install -y PACKAGE", "remove.sh": "remove -y PACKAGE",
            "reinstall.sh": "opnsense-revert",
        }
        expected["install.sh"] = "no package operation here"
        with self.assertRaisesRegex(m.Refusal, "INSTALLED_FIRMWARE_ROUTE_CHANGED"):
            m.validate_firmware({k:(v,"test") for k,v in expected.items()})

    def test_missing_product_refused_before_touching_pkg(self):
        class Linux:
            sysname = "Linux"
            machine = "x86_64"
        with mock.patch.object(m.os, "geteuid", return_value=0), \
             mock.patch.object(m.os, "uname", return_value=Linux()), \
             mock.patch.object(m, "inspect_firmware") as inspect:
            with self.assertRaisesRegex(m.Refusal, "ONLY_ROOT_FREEBSD"):
                m.run(mock.Mock(), mock.Mock())
            inspect.assert_not_called()

    def test_missing_native_pkgdb_is_refused(self):
        with mock.patch.object(m, "call", return_value=mock.Mock(returncode=4)):
            with self.assertRaisesRegex(m.Refusal, "PKGDB_QUERY_UNKNOWN"):
                m.status(["pkg"], {}, Path("/nonexistent-stage0-file"))

    def test_pkgdb_partial_owner_no_auto_success(self):
        self.assertEqual(m.verdict(OLD, (m.NAME + "|0.6.2_39", b"old\n"), NEW),
                         "PKG_LOCK_BYPASS_OR_PARTIAL_MUTATION_OBSERVED")

    def test_fixture_only_and_no_firmware_mutation_commands(self):
        content = SRC.read_text()
        self.assertIn("PKG_DBDIR", content)
        self.assertIn("OBSERVED_NATIVE_PKG_LOCK_AND_FIRMWARE_ROUTES", content)
        self.assertNotIn('call(["/usr/local/opnsense/scripts/firmware/launcher.sh"', content)
        self.assertNotIn('call(["configctl"', content)
        self.assertNotIn("pkg delete -f", content)

    def test_negative_product_acceptance_always_explicit(self):
        content = SRC.read_text()
        for marker in ('"product_safety_acceptance_passed": False',
                       '"stage0_closed": False',
                       '"all_firmware_update_routes_covered": False',
                       '"real_plugin_package_tested": False'):
            self.assertIn(marker, content)


if __name__=="__main__":
    unittest.main()
