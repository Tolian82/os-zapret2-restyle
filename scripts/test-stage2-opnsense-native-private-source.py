#!/usr/bin/env python3
"""Offline negative contracts for the signed latest private curl native package."""
import hashlib
import importlib.util
import os
from pathlib import Path
import stat
import struct
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "stage2_private", HERE / "stage2-opnsense-native-private-source.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fixture(root, elf_machine=62, profile="chrome133"):
    dest = Path(root) / "libexec/zapret2-restyle"
    private = dest / "curl-impersonate"
    binary = private / "bin/curl-impersonate"
    binary.parent.mkdir(parents=True)
    blob = bytearray(1100)
    blob[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<H", blob, 18, elf_machine)
    binary.write_bytes(blob)
    binary.chmod(0o755)
    (private / "licenses").mkdir()
    (private / "licenses/LICENSE").write_text("fixture LICENSE\n")
    (private / "BINARY_SHA256").write_text(hashlib.sha256(blob).hexdigest() + "\n")
    (private / "SOURCE_PKG_SHA256").write_text("a" * 64 + "\n")
    (private / "CHROME_PROFILE").write_text(profile + "\n")
    (private / "FREEBSD_ABI").write_text("FreeBSD:15:amd64\n")
    (private / "UPSTREAM_VERSION").write_text("1.0.0_1\n")
    for name in mod.LAUNCHERS:
        source = mod.ROOT / "scripts" / name
        f = dest / name
        f.write_bytes(source.read_bytes())
        f.chmod(0o755)
    return dest, private, binary


class PrivateNativeContracts(unittest.TestCase):
    def test_actual_source_only_revision_and_historical_base(self):
        self.assertEqual(mod.SOURCE_REVISION, "59")
        self.assertEqual(mod.PREDECESSOR_REVISION, "58")
        self.assertEqual(mod.old.REVISION, "59")

    def test_positive_private_bundle_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            dest, _, binary = fixture(td)
            record = mod.validate_bundle(dest)
            self.assertEqual(record["private_binary_sha256"],
                             hashlib.sha256(binary.read_bytes()).hexdigest())
            self.assertEqual(record["profile"], "chrome133")
            self.assertEqual(record["license_file_count"], 1)

    def test_wrong_elf_architecture_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            dest, _, _ = fixture(td, elf_machine=3)
            with self.assertRaisesRegex(mod.old.Refusal, "NOT_AMD64_ELF"):
                mod.validate_bundle(dest)

    def test_mutated_binary_digest_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            dest, private, _ = fixture(td)
            (private / "BINARY_SHA256").write_text("0" * 64 + "\n")
            with self.assertRaisesRegex(mod.old.Refusal, "BINARY_SHA_MISMATCH"):
                mod.validate_bundle(dest)

    def test_wrong_package_sha_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            dest, private, _ = fixture(td)
            (private / "SOURCE_PKG_SHA256").write_text("not-a-sha\n")
            with self.assertRaisesRegex(mod.old.Refusal, "PROVENANCE_HASH_INVALID"):
                mod.validate_bundle(dest)

    def test_actual_freebsd_latest_version_diagnostic_syntax(self):
        with tempfile.TemporaryDirectory() as td:
            dest, private, _ = fixture(td)
            (private / "UPSTREAM_VERSION").write_text("2.2.3_1~2$uenpqenr\n")
            self.assertEqual(mod.validate_bundle(dest)["latest_version_diagnostic"],
                             "2.2.3_1~2$uenpqenr")
            for value in ("../bad", "invalid/version", "a\ncontrol", "a" * 129):
                (private / "UPSTREAM_VERSION").write_text(value + "\n")
                with self.subTest(value=repr(value)), self.assertRaisesRegex(
                        mod.old.Refusal, "VERSION_UNQUALIFIED"):
                    mod.validate_bundle(dest)

    def test_unknown_browser_profile_refused(self):
        with tempfile.TemporaryDirectory() as td:
            dest, _, _ = fixture(td, profile="edge112")
            with self.assertRaisesRegex(mod.old.Refusal, "PROFILE_UNQUALIFIED"):
                mod.validate_bundle(dest)

    def test_missing_private_license_refused(self):
        with tempfile.TemporaryDirectory() as td:
            dest, private, _ = fixture(td)
            (private / "licenses/LICENSE").unlink()
            with self.assertRaisesRegex(mod.old.Refusal, "LICENSES_MISSING"):
                mod.validate_bundle(dest)

    def test_mismatched_launcher_refused(self):
        with tempfile.TemporaryDirectory() as td:
            dest, _, _ = fixture(td)
            (dest / mod.LAUNCHERS[0]).write_text("echo unsafe\n")
            with self.assertRaisesRegex(mod.old.Refusal, "LAUNCHER_SOURCE_MISMATCH"):
                mod.validate_bundle(dest)

    def test_symlinked_private_license_refused(self):
        with tempfile.TemporaryDirectory() as td:
            dest, private, _ = fixture(td)
            (private / "licenses/link").symlink_to(private / "licenses/LICENSE")
            with self.assertRaisesRegex(mod.old.Refusal, "LICENSE_SYMLINK_REFUSED"):
                mod.validate_bundle(dest)

    def test_mode_mismatch_refused(self):
        with tempfile.TemporaryDirectory() as td:
            dest, _, binary = fixture(td)
            binary.chmod(0o644)
            with self.assertRaisesRegex(mod.old.Refusal, "BINARY_NOT_0755"):
                mod.validate_bundle(dest)

    def test_missing_runtime_libs_refused(self):
        class Result:
            stdout = b"libc.so.7 => not found\n"
            stderr = b""
        with patch.object(mod, "run_binary", return_value=Result()):
            with self.assertRaisesRegex(mod.old.Refusal, "UNRESOLVED_ELF_LIBRARY"):
                mod.native_ldd(Path("/tmp/test"))

    def test_duplicate_runtime_libraries_refused(self):
        class Result:
            stdout = b"libc.so.7 => /lib/libc.so.7\nlibc.so.7 => /lib/libc.so.7\n"
            stderr = b""
        with patch.object(mod, "run_binary", return_value=Result()):
            with self.assertRaisesRegex(mod.old.Refusal, "EMPTY_OR_DUPLICATE"):
                mod.native_ldd(Path("/tmp/test"))

    def test_unqualified_library_path_refused(self):
        class Result:
            stdout = b"libc.so.7 => /opt/freebsd/lib/libc.so.7\n"
            stderr = b""
        with patch.object(mod, "run_binary", return_value=Result()):
            with self.assertRaisesRegex(mod.old.Refusal, "LIBRARY_PATH_NOT_QUALIFIED"):
                mod.native_ldd(Path("/tmp/test"))

    def test_successful_base_library_provenance(self):
        class Result:
            stdout = b"libc.so.7 => /lib/libc.so.7\n"
            stderr = b""
        with patch.object(mod, "run_binary", return_value=Result()):
            with patch.object(Path, "is_file", return_value=True):
                v = mod.native_ldd(Path("/tmp/fake"))
        self.assertEqual(v["libc.so.7"]["provenance"], "target-opnsense-base")

    def test_no_live_package_or_owner_modification_claim(self):
        source = (HERE / "stage2-opnsense-native-private-source.py").read_text()
        for needle in ('"native_package_installed": False',
                       '"production_builder_replaced": False',
                       '"official_final_package_qualified": False',
                       '"owner_gateway_modified": False',
                       '"stage0_closed": False',
                       '"stage1_admitted": False',
                       '"signed_latest_source_pkg_installed_to_system": False'):
            self.assertIn(needle, source)
        self.assertIn('"https://127.0.0.1:1/"', source)
        self.assertIn('"make", "-C", str(plugin)', source)
        self.assertIn('"build-curl-impersonate.sh"', source)

    def test_loader_and_native_provenance_strict(self):
        source = (HERE / "stage2-opnsense-native-private-source.py").read_text()
        self.assertIn('old.guest_gate()', source)
        self.assertIn('old.clone_official(Path(td))', source)
        self.assertIn('old.native_variables(plugin, project, provider)', source)
        self.assertIn('old.manifest_identity(manifest, plugin, provider)', source)
        self.assertIn('native_ldd(', source)
        self.assertIn('verify_native_private_archive(', source)


if __name__ == "__main__":
    unittest.main()
