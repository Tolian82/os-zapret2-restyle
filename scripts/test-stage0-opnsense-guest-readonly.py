#!/usr/bin/env python3
"""Pure offline negatives for fresh OPNsense 26.7 guest identity gate."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "guest", Path(__file__).with_name("stage0-opnsense-guest-readonly.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixture():
    return {
        "uid": 0, "os": "FreeBSD", "arch": "amd64",
        "product_abi": m.PRODUCT_ABI, "package_abi": m.PKG_ABI,
        "userland": "15.1-RELEASE-p6", "virtualization": "kvm",
        "old_plugin_pkg_exists": False,
    }


class GuestIdentity(unittest.TestCase):
    def test_positive_does_not_claim_installed_or_image_attestation(self):
        report = m.evaluate(fixture())
        self.assertEqual(report["status"], "PASS_ISOLATED_OPNSENSE_26_7_GUEST_IDENTITY")
        for key in ("official_image_sha256_independently_verified",
                    "third_party_vm_image_provenance_independently_verified",
                    "actual_published_predecessor_installed",
                    "real_installed_predecessor_provenance_tested",
                    "real_service_fd9_tested", "native_successor_tested",
                    "stage0_closed"):
            self.assertFalse(report[key])

    def test_wrong_root_platform_or_arch_refuses(self):
        for key, value in (("uid", 1000), ("os", "Linux"), ("arch", "arm64")):
            data = fixture()
            data[key] = value
            with self.subTest(key=key), self.assertRaises(m.Refusal):
                m.evaluate(data)

    def test_wrong_target_abis_or_userland_refuses(self):
        for key, value in (("product_abi", "27.1"),
                           ("package_abi", "FreeBSD:14:amd64"),
                           ("userland", "14.3-RELEASE-p1")):
            data = fixture()
            data[key] = value
            with self.subTest(key=key), self.assertRaises(m.Refusal):
                m.evaluate(data)

    def test_unknown_or_missing_vm_witness_refuses(self):
        for value in ("none", "unknown", ""):
            data = fixture()
            data["virtualization"] = value
            with self.subTest(value=value), self.assertRaisesRegex(m.Refusal, "VIRTUALIZED"):
                m.evaluate(data)

    def test_installed_predecessor_is_not_fresh_guest(self):
        data = fixture()
        data["old_plugin_pkg_exists"] = True
        with self.assertRaisesRegex(m.Refusal, "NOT_FRESH"):
            m.evaluate(data)

    def test_queries_are_read_only_and_missing_pkg_is_valid(self):
        calls = []
        def fake(args, allowed=(0,)):
            calls.append((tuple(args), tuple(allowed)))
            if args[:3] == ["pkg", "info", "-e"]:
                return 1, ""
            records = {
                "opnsense-version": m.PRODUCT_ABI,
                "pkg": m.PKG_ABI,
                "freebsd-version": "15.1-RELEASE-p6",
                "sysctl": "kvm",
            }
            return 0, records[args[0]]
        with patch.object(m, "query", fake), patch.object(m.os, "geteuid", return_value=0):
            with patch.object(m.os, "uname") as mocked:
                mocked.return_value.sysname = "FreeBSD"
                mocked.return_value.machine = "amd64"
                result = m.observe()
        self.assertFalse(result["old_plugin_pkg_exists"])
        self.assertEqual(calls[-1][0], ("pkg", "info", "-e", m.NAME))
        self.assertEqual(calls[-1][1], (0, 1))
        self.assertEqual(len(calls), 5)


if __name__ == "__main__":
    unittest.main()
