#!/usr/bin/env python3
"""Offline preflight for disposable FreeBSD pkgdb format roundtrip."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

src = Path(__file__).with_name("stage0-installed-pkgdb-native.py")
spec = importlib.util.spec_from_file_location("pkgdb_fixture", src)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class NativePkgDBContract(unittest.TestCase):
    def test_unattested_or_wrong_platform_refuses(self):
        for args in ((False, "FreeBSD", "amd64", 0, "15.1-RELEASE"),
                     (True, "Linux", "x86_64", 0, "15.1-RELEASE"),
                     (True, "FreeBSD", "amd64", 1000, "15.1-RELEASE"),
                     (True, "FreeBSD", "amd64", 0, "14.3-RELEASE")):
            with self.subTest(args=args), self.assertRaises(mod.pre.Refusal):
                mod.check_platform(*args)
        mod.check_platform(True, "FreeBSD", "amd64", 0, "15.1-RELEASE-p1")

    def test_synthetic_package_scripts_are_inert(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "installed" / "mock-service.sh"
            meta = mod.fixture_manifest(path, b"#!/bin/sh\nexit 0\n")
            self.assertEqual(meta["name"], mod.pre.NAME)
            self.assertEqual(meta["abi"], mod.pre.ABI)
            self.assertEqual(set(meta["scripts"]), set(mod.pre.PHASES))
            self.assertEqual(set(meta["scripts"].values()), {"#!/bin/sh\nexit 0\n"})
            self.assertEqual(list(meta["files"]), [str(path)])
            self.assertNotIn("/usr/local/opnsense", str(path))

    def test_digest_fails_before_any_pkg_operation(self):
        with tempfile.TemporaryDirectory() as d:
            archive = Path(d) / "incorrect.pkg"
            archive.write_bytes(b"not the immutable published archive")
            with self.assertRaisesRegex(mod.pre.Refusal, "SHA256_MISMATCH"):
                mod.native_roundtrip(archive)


if __name__ == "__main__":
    unittest.main()
