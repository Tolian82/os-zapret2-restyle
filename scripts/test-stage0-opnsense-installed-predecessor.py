#!/usr/bin/env python3
"""Offline safety-contract tests for installed predecessor on isolated OPNsense."""
import importlib.util
from pathlib import Path
from unittest.mock import patch
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "installed", Path(__file__).with_name("stage0-opnsense-installed-predecessor.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def system():
    return {
        "uid": 0, "os": "FreeBSD", "arch": "amd64",
        "product_abi": "26.7", "package_abi": "FreeBSD:15:amd64",
        "userland": "15.1-RELEASE-p1", "virtualization": "kvm",
        "old_plugin_pkg_exists": False,
    }


def archive():
    return {
        "name": m.pre.NAME, "version": m.pre.VERSION,
        "abi": m.pre.ABI, "arch": "freebsd:15:x86:64",
        "origin": "opnsense/os-zapret2-restyle",
        "deps": {"python313": {"origin": "lang/python313", "version": "3.13"}},
    }


class InstalledTarget(unittest.TestCase):
    def test_only_original_pkg_hook_execution_on_disposable_guest(self):
        self.assertEqual(m.ADD_COMMAND[-1], "add")
        for unsafe in ("--script-no-exec", "-I", "--no-scripts", "-M", "--accept-missing", "--force", "-f"):
            self.assertNotIn(unsafe, m.ADD_COMMAND)

    def test_clean_guest_and_exact_archive_allow_preflight(self):
        with tempfile.TemporaryDirectory() as d, patch.object(
                m, "query_installed", side_effect=lambda name: name != m.pre.NAME):
            path = Path(d) / "old.pkg"
            path.write_bytes(b"fixture preflight only")
            m.preflight(path, system(), archive())

    def test_existing_package_and_missing_dependencies_refuse(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "old.pkg"
            path.write_bytes(b"fixture preflight only")
            with patch.object(m, "query_installed", side_effect=[True, True]):
                with self.assertRaisesRegex(m.pre.Refusal, "ALREADY_INSTALLED"):
                    m.preflight(path, system(), archive())
            with patch.object(m, "query_installed", return_value=False):
                manifest = archive()
                manifest["deps"]["git"] = {}
                # missing means fresh independent package isn't silently installed
                with self.assertRaisesRegex(m.pre.Refusal, "MISSING_PREINSTALLED"):
                    m.preflight(path, system(), manifest)

    def test_wrong_abi_arch_or_version_refuses_before_pkg_add(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "old.pkg"
            p.write_bytes(b"fixture")
            for key, wrong in (("abi", "FreeBSD:14:amd64"),
                               ("arch", "freebsd:14:x86:64"),
                               ("version", "0.6.2_2")):
                data = archive()
                data[key] = wrong
                with self.subTest(key=key), self.assertRaises(m.pre.Refusal), patch.object(
                        m, "query_installed", side_effect=AssertionError("no pkg query")):
                    m.preflight(p, system(), data)

    def test_unqualified_vm_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "old.pkg"
            path.write_bytes(b"fixture")
            data = system()
            data["virtualization"] = "none"
            with self.assertRaises(m.guest.Refusal):
                m.preflight(path, data, archive())

    def test_postinstall_signature_required_for_real_hook_success(self):
        from unittest.mock import Mock
        with patch.object(m.subprocess, "run", return_value=Mock(
                returncode=0, stdout="Package registered", stderr="")):
            with self.assertRaisesRegex(m.pre.Refusal, "POST_INSTALL_SUCCESS_SIGNATURE_ABSENT"):
                m.execute_add(Path("/tmp/only-a-test.pkg"))
        with patch.object(m.subprocess, "run", return_value=Mock(
                returncode=0, stdout="os-zapret2-restyle was installed.", stderr="")):
            self.assertTrue(m.execute_add(Path("/tmp/only-a-test.pkg")))

    def test_bad_archive_refuses_before_add(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "wrong.pkg"
            p.write_bytes(b"wrong digest")
            with patch.object(m, "execute_add", side_effect=AssertionError("must not install")), \
                 self.assertRaisesRegex(m.pre.Refusal, "SHA256_MISMATCH"):
                m.install_and_verify(p)


if __name__ == "__main__":
    unittest.main()
