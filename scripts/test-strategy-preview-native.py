#!/usr/bin/env python3
"""P5b1 private native mapped validator: source/negative and fake binary tests."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import secrets
import shutil
import stat
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))
from strategy_preview_native import (  # noqa: E402
    NativePreviewRefused, validate_private_release,
)


class NativeValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="p5b-internal-", dir="/tmp")
        self.addCleanup(self.temp.cleanup)
        parent = Path(self.temp.name)
        self.work = Path("/tmp/zapret-p5b-" + secrets.token_hex(8))
        self.work.mkdir(mode=0o700)
        self.addCleanup(lambda: shutil.rmtree(self.work, ignore_errors=True))
        self.release = self.work / "release"
        self.release.mkdir(mode=0o755)
        (self.release / "managed").mkdir(mode=0o755)
        self.static = parent / "upstream"
        self.static.mkdir(mode=0o755)
        self.bin = self.static / "binaries/my/dvtws2"
        self.bin.parent.mkdir(parents=True, mode=0o755)
        self._file("dvtws.args", "--port=989\n--filter-tcp=443\n"
                   "--filter-l7=tls\n--payload=tls_client_hello\n"
                   "--lua-desync=fake\n")
        self._file("traffic-user.conf",
                   "--filter-tcp=443\n--filter-l7=tls\n"
                   "--payload=tls_client_hello\n--lua-desync=fake\n")
        self._file("tcp-ports.txt", "443\n")
        self._file("udp-ports.txt", "")
        self.checked = 0

    def _file(self, relative: str, contents: str):
        p = self.release / relative
        p.write_text(contents, encoding="utf-8")
        p.chmod(0o644)
        return p

    def _engine(self, exitcode: int):
        self.bin.write_text(
            "#!/bin/sh\n"
            "for a in \"$@\"; do\n"
            "  [ \"$a\" != \"--dry-run\" ] || exit " + str(exitcode) + "\n"
            "done\nexit 61\n",
            encoding="ascii")
        self.bin.chmod(0o755)

    def check(self):
        self.checked += 1

    def run_candidate(self, **changes):
        kwargs = {
            "native": False, "static_root": self.static,
            "module_root": BACKEND, "check_lock": self.check,
        }
        kwargs.update(changes)
        return validate_private_release(self.work, **kwargs)

    def test_existing_shell_validator_and_native_dry_run_called(self):
        self._engine(0)
        before = {p.relative_to(self.work).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.work.rglob("*") if p.is_file()}
        result = self.run_candidate()
        self.assertEqual(result["mapped_validation"], "native_mapped_valid")
        self.assertEqual(result["engine_native_dry_run"], "passed")
        self.assertFalse(result["safe_to_apply"])
        self.assertFalse(result["public_preview_action"])
        self.assertEqual(result["real_network_bypass"], "not_tested")
        self.assertEqual(result["effective_lifecycle_state"], "not_attested")
        self.assertGreaterEqual(self.checked, 4)
        after = {p.relative_to(self.work).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in self.work.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_native_unavailable_not_declared_pass(self):
        result = self.run_candidate()
        self.assertEqual(result["mapped_validation"], "native_mapped_valid")
        self.assertEqual(result["engine_native_dry_run"], "unavailable")

    def test_native_return_failure_is_different_from_bad_build(self):
        self._engine(42)
        self.assertEqual(self.run_candidate()["engine_native_dry_run"], "failed")
        self._file("tcp-ports.txt", "1234\n")
        report = self.run_candidate()
        self.assertEqual(report["mapped_validation"], "native_mapped_validation_failed")
        self.assertEqual(report["engine_native_dry_run"], "not_run")

    def test_mapped_reference_rejects_outside_roots(self):
        self._file("dvtws.args",
                   "--port=989\n--filter-tcp=443\n--hostlist=/etc/passwd\n")
        result = self.run_candidate()
        self.assertEqual(result["mapped_validation"], "native_mapped_validation_failed")
        self.assertEqual(result["engine_native_dry_run"], "not_run")

    def test_refuses_foreign_candidate_directory(self):
        foreign = Path(self.temp.name) / "zapret-p5b-0123456789abcdef"
        foreign.mkdir(mode=0o700)
        with self.assertRaisesRegex(NativePreviewRefused, "PRIVATE_PREVIEW_ROOT_INVALID"):
            validate_private_release(foreign, native=False, static_root=self.static,
                                     module_root=BACKEND, check_lock=self.check)

    def test_refuses_insecure_private_permissions(self):
        self.work.chmod(0o755)
        with self.assertRaisesRegex(NativePreviewRefused, "PRIVATE_PREVIEW_NOT_PRIVATE"):
            self.run_candidate()

    def test_refuses_symlink_release(self):
        shutil.rmtree(self.release)
        self.release.symlink_to(self.static, target_is_directory=True)
        with self.assertRaisesRegex(NativePreviewRefused, "PRIVATE_CANDIDATE_TYPE_UNSAFE"):
            self.run_candidate()

    def test_refuses_hardlinked_argument_file(self):
        link = self.release / "other.args"
        os.link(self.release / "dvtws.args", link)
        with self.assertRaisesRegex(NativePreviewRefused, "PRIVATE_CANDIDATE_TYPE_UNSAFE"):
            self.run_candidate()

    def test_refuses_unverified_original_lock(self):
        with self.assertRaisesRegex(NativePreviewRefused, "NATIVE_LIFECYCLE_GUARD_MISSING"):
            validate_private_release(self.work, native=False,
                                     static_root=self.static, module_root=BACKEND)

    def test_production_branch_never_uses_linux_fake_native(self):
        if sys.platform == "freebsd":
            self.skipTest("FreeBSD native owner needs actual original FD9")
        with self.assertRaisesRegex(NativePreviewRefused, "NATIVE_OWNER_OR_ROOT_REFUSED"):
            validate_private_release(self.work)

    def test_no_bypass_of_existing_validator(self):
        source = (BACKEND / "strategy_preview_native.py").read_text()
        self.assertIn("validator_validate_build_mapped", source)
        self.assertIn("validator_validate_engine_mapped", source)
        self.assertNotIn("shared_apply_execute_service", source)
        self.assertNotIn("Config::save", source)
        self.assertNotIn("ipfw add", source)
        self.assertNotIn("orchestrator_native_start", source)
        self.assertNotIn("service_dispatch start", source)
        self.assertNotIn("subprocess.run([binary", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
