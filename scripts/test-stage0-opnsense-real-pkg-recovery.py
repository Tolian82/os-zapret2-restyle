#!/usr/bin/env python3
"""Offline contracts for isolated real published pkg fault and compensation."""
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "stage0_real_pkg_recovery", HERE / "stage0-opnsense-real-pkg-recovery.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def completed(rc, out="", err=""):
    return subprocess.CompletedProcess(["pkg"], rc, out, err)


class TestRealPkgRecovery(unittest.TestCase):
    def test_explicit_ci_optin_before_guest_or_mutation(self):
        with mock.patch.dict(os.environ, {mod.OPTIN: "0", "GITHUB_ACTIONS": "true"}):
            with mock.patch.object(mod, "module") as lookup:
                with self.assertRaisesRegex(mod.Refusal, "OPTIN"):
                    mod.qualify_disposable()
                lookup.assert_not_called()

    def test_requires_exact_old_cold_snapshot(self):
        class Guard:
            def snapshot(self, _):
                return {"status": "PASS_COLD_READ_ONLY_SNAPSHOT_ONLY",
                        "old_package": mod.PACKAGE,
                        "real_old_status": "STOPPED",
                        "safe_pkg_transaction_authorized": False}
        self.assertEqual(mod.snapshot(Path("old.pkg"), Guard())["old_package"], mod.PACKAGE)

    def test_refuses_false_atomic_authorization(self):
        class Guard:
            def snapshot(self, _):
                return {"status": "PASS_COLD_READ_ONLY_SNAPSHOT_ONLY",
                        "old_package": mod.PACKAGE,
                        "real_old_status": "STOPPED",
                        "safe_pkg_transaction_authorized": True}
        with self.assertRaisesRegex(mod.Refusal, "COLD_GATE_FAILED"):
            mod.snapshot(Path("old.pkg"), Guard())

    def test_refuses_running_or_unknown_owner(self):
        for state in ("RUNNING", "UNKNOWN", ""):
            with self.subTest(state=state):
                g = mock.Mock()
                g.snapshot.return_value = {"status": "PASS_COLD_READ_ONLY_SNAPSHOT_ONLY",
                    "old_package": mod.PACKAGE, "real_old_status": state,
                    "safe_pkg_transaction_authorized": False}
                with self.assertRaises(mod.Refusal):
                    mod.snapshot(Path("old.pkg"), g)

    def test_cannot_accept_pkg_exit_zero_after_failed_hook_as_success(self):
        self.assertTrue(mod.classify_fault(completed(
            0, "", "ERROR: os-zapret2-restyle " + mod.FAULT_SIGNATURE
        ))["pkg_exit_cannot_prove_transaction_success"])

    def test_missing_fault_observation_is_refusal(self):
        with self.assertRaisesRegex(mod.Refusal, "NOT_OBSERVED"):
            mod.classify_fault(completed(0, "installed", ""))

    def test_compensation_requires_success_and_hook_signature(self):
        for result in (completed(1, "os-zapret2-restyle was installed."),
                       completed(0, "silent")):
            with self.assertRaises(mod.Refusal):
                mod.check_success(result)
        mod.check_success(completed(0, "os-zapret2-restyle was installed."))

    def test_pkg_uses_real_pkgdb_no_foreign_environment(self):
        with tempfile.TemporaryDirectory() as d:
            archive = Path(d) / "old.pkg"
            archive.write_bytes(b"fixture")
            with mock.patch.dict(os.environ, {"PKG_DBDIR": "/tmp/foreign",
                    "PKG_CACHEDIR": "/tmp/foreign", "FIRMWARE_REGISTER": "/tmp/x"}):
                with mock.patch.object(mod.subprocess, "run",
                        return_value=completed(0)) as run:
                    mod.real_pkg_add(archive)
                    a, kw = run.call_args
                    self.assertEqual(a[0], ["pkg", "-o", "REPO_AUTOUPDATE=false",
                                             "add", "-f", str(archive)])
                    self.assertNotIn("FIRMWARE_REGISTER", kw["env"])
                    self.assertNotIn("PKG_DBDIR", kw["env"])
                    self.assertNotIn("PKG_CACHEDIR", kw["env"])
                    self.assertFalse(kw["check"])
                    self.assertEqual(kw["timeout"], 180)

    def test_success_path_does_not_inherit_fault_override(self):
        with tempfile.TemporaryDirectory() as d:
            archive = Path(d) / "old.pkg"
            archive.write_bytes(b"fixture")
            with mock.patch.dict(os.environ, {"FIRMWARE_REGISTER": "/bin/false"}):
                with mock.patch.object(mod.subprocess, "run",
                        return_value=completed(0)) as run:
                    mod.real_pkg_add(archive)
                    self.assertNotIn("FIRMWARE_REGISTER", run.call_args.kwargs["env"])

    def test_symlink_archive_rejected_before_pkg(self):
        with tempfile.TemporaryDirectory() as d:
            real = Path(d) / "real"
            real.write_bytes(b"fixture")
            link = Path(d) / "link"
            link.symlink_to(real)
            with mock.patch.object(mod.subprocess, "run") as run:
                with self.assertRaisesRegex(mod.Refusal, "UNQUALIFIED"):
                    mod.real_pkg_add(link)
                run.assert_not_called()

    def test_fault_refuses_unowned_register_helper_before_pkg(self):
        with tempfile.TemporaryDirectory() as d:
            helper = Path(d) / "helper"
            helper.write_bytes(b"fixture")
            helper.chmod(0o755)
            with mock.patch.object(mod, "REGISTER_HELPER", helper), \
                 mock.patch.object(mod, "real_pkg_add") as pkg:
                with self.assertRaisesRegex(mod.Refusal, "ROOT_OWNED"):
                    mod.faulted_real_pkg_add(Path(d) / "old.pkg")
                pkg.assert_not_called()

    def test_archived_injection_requires_original_hook(self):
        obj = mock.Mock()
        obj.archive_data.return_value = (
            {"scripts": {"post-install":
                'FIRMWARE_REGISTER="${FIRMWARE_REGISTER:-/bin/true}"\n'
                'echo "OPNsense plugin registration helper is unavailable"'}}, b"")
        mod.hook_allows_fault(Path("fixture"), obj)
        obj.archive_data.return_value = ({"scripts": {"post-install": "exit 0"}}, b"")
        with self.assertRaisesRegex(mod.Refusal, "NOT_FAULT_INJECTABLE"):
            mod.hook_allows_fault(Path("fixture"), obj)

    def test_injected_failure_never_skips_compensation(self):
        with tempfile.TemporaryDirectory() as d:
            archive = Path(d) / "old.pkg"
            archive.write_bytes(b"fixture")
            sha = hashlib.sha256(b"fixture").hexdigest()
            inst = mock.Mock()
            orig = mock.Mock(ARCHIVE_SHA=sha)
            g = mock.Mock()
            events = []
            with mock.patch.object(mod, "qualify_disposable"), \
                 mock.patch.object(mod, "module", side_effect=[inst, g, orig]), \
                 mock.patch.object(mod, "hook_allows_fault"), \
                 mock.patch.object(mod, "identity", return_value={"status": "pass"}), \
                 mock.patch.object(mod, "immutable_config", return_value=("sha", 0o640, 1, 2)), \
                 mock.patch.object(mod, "same_config"), \
                 mock.patch.object(mod, "snapshot"), \
                 mock.patch.object(mod, "faulted_real_pkg_add", side_effect=lambda a: (
                     events.append("fault") or
                     completed(0, "", "ERROR: " + mod.FAULT_SIGNATURE))), \
                 mock.patch.object(mod, "real_pkg_add", side_effect=lambda a: (
                     events.append("restore") or
                     completed(0, "os-zapret2-restyle was installed."))):
                report = mod.run(archive)
            self.assertEqual(events, ["fault", "restore"])
            self.assertFalse(report["real_new_version_successor_tested"])
            self.assertFalse(report["atomic_pkg_rollback_proved"])
            self.assertFalse(report["stage0_closed"])

    def test_bad_postfault_pkgdb_fails_before_compensation(self):
        with tempfile.TemporaryDirectory() as d:
            archive = Path(d) / "old.pkg"
            archive.write_bytes(b"fixture")
            inst = mock.Mock()
            orig = mock.Mock()
            with mock.patch.object(mod, "qualify_disposable"), \
                 mock.patch.object(mod, "module", side_effect=[inst, mock.Mock(), orig]), \
                 mock.patch.object(mod, "hook_allows_fault"), \
                 mock.patch.object(mod, "identity", side_effect=[
                     {"initial": True}, {"changed": True}]), \
                 mock.patch.object(mod, "immutable_config", return_value=("sha", 0, 0, 0)), \
                 mock.patch.object(mod, "snapshot"), \
                 mock.patch.object(mod, "faulted_real_pkg_add",
                     return_value=completed(0, "", mod.FAULT_SIGNATURE)) as pkg, \
                 mock.patch.object(mod, "real_pkg_add") as recovery:
                with self.assertRaisesRegex(mod.Refusal, "PROVENANCE"):
                    mod.run(archive)
                self.assertEqual(pkg.call_count, 1)
                recovery.assert_not_called()


if __name__ == "__main__":
    unittest.main()
