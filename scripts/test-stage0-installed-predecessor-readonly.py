#!/usr/bin/env python3
"""Deterministic negatives for the read-only installed predecessor witness."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "predecessor", Path(__file__).with_name("stage0-installed-predecessor-readonly.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def manifest():
    return {"name": m.NAME, "version": m.VERSION, "abi": m.ABI,
            "arch": "freebsd:15:x86:64", "origin": "opnsense/os-zapret2-restyle",
            "scripts": {p: "#!/bin/sh\necho " + p + "\n" for p in m.PHASES}}


def args():
    return [manifest(), manifest(), b"#!/bin/sh\nexit 0\n", b"#!/bin/sh\nexit 0\n",
            m.NAME + "-" + m.VERSION, 0o755, "26.7", m.ABI, "bhyve"]


class Provenance(unittest.TestCase):
    def test_positive_is_explicitly_not_lifecycle_acceptance(self):
        report = m.verify_data(*args())
        self.assertEqual(report["status"], "PASS_READ_ONLY_PROVENANCE")
        for p in ("real_fd9_tested", "actual_pkg_replacement", "native_successor_package_tested",
                  "isolated_environment_independently_attested"):
            self.assertIs(report[p], False)
        self.assertEqual(set(report["original_hooks_sha256"]), set(m.PHASES))

    def test_each_hook_mutation_fails_closed(self):
        for p in m.PHASES:
            a = args()
            a[1]["scripts"][p] = "#!/bin/sh\nexit 3\n"
            with self.subTest(phase=p), self.assertRaisesRegex(m.Refusal, "HOOK_BODY_MISMATCH"):
                m.verify_data(*a)

    def test_wrong_or_missing_installed_identity(self):
        for key, val in (("name", "other"), ("version", "0.6.2_2"), ("abi", "FreeBSD:14:amd64")):
            a = args()
            a[1][key] = val
            with self.subTest(key=key), self.assertRaisesRegex(m.Refusal, "INSTALLED_PACKAGE_IDENTITY"):
                m.verify_data(*a)

    def test_changed_native_arch_or_origin_refuses_even_when_abi_matches(self):
        for key, bad in (("arch", "freebsd:14:x86:64"),
                         ("origin", "unknown/not-the-signed-package")):
            a = args()
            self.assertEqual(a[1]["abi"], m.ABI)
            a[1][key] = bad
            with self.subTest(key=key), self.assertRaisesRegex(
                    m.Refusal, "INSTALLED_PACKAGE_IDENTITY_" + key.upper() + "_MISMATCH"):
                m.verify_data(*a)

    def test_missing_or_untrusted_native_arch_origin_refuses(self):
        for key in ("arch", "origin"):
            for which in (0, 1):
                a = args()
                del a[which][key]
                with self.subTest(key=key, which=which), self.assertRaisesRegex(
                        m.Refusal, "INSTALLED_PACKAGE_IDENTITY_" + key.upper() + "_MISMATCH"):
                    m.verify_data(*a)

    def test_extra_archived_or_installed_lifecycle_hook_refuses(self):
        for which in (0, 1):
            a = args()
            a[which]["scripts"]["pre-upgrade"] = "#!/bin/sh\nexit 0\n"
            with self.subTest(which=which), self.assertRaisesRegex(
                    m.Refusal, ("ARCHIVE" if which == 0 else "INSTALLED") +
                    "_FOUR_MANUAL_HOOKS_MISSING_OR_EXTRA"):
                m.verify_data(*a)

    def test_missing_historical_hook(self):
        a = args()
        del a[0]["scripts"]["pre-deinstall"]
        with self.assertRaisesRegex(m.Refusal, "ARCHIVE_FOUR_MANUAL_HOOKS"):
            m.verify_data(*a)

    def test_service_bytes_mode_and_owner(self):
        for index, value, code in ((3, b"modified", "SERVICE_BYTES"),
                                   (5, 0o644, "MODE_NOT_0755"),
                                   (4, "other-1", "OWNER_UNPROVEN")):
            a = args()
            a[index] = value
            with self.subTest(index=index), self.assertRaisesRegex(m.Refusal, code):
                m.verify_data(*a)

    def test_qualifiers_are_strict(self):
        for index, value, code in ((6, "26.1", "PRODUCT_ABI"),
                                   (7, "FreeBSD:14:amd64", "PACKAGE_ABI"),
                                   (8, "none", "VIRTUAL_GUEST")):
            a = args()
            a[index] = value
            with self.subTest(index=index), self.assertRaisesRegex(m.Refusal, code):
                m.verify_data(*a)

    def test_digest_of_unverified_archive_fails_before_tar(self):
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            a = Path(d) / "fake.pkg"
            a.write_bytes(b"not an archive")
            with patch.object(m, "run") as run, self.assertRaisesRegex(m.Refusal, "SHA256_MISMATCH"):
                m.archive_data(a)
                run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
