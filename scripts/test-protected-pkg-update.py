#!/usr/bin/env python3
"""Offline protected package update invariants. No real pkg/service mutation."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src/opnsense/scripts/OPNsense/Zapret/protected_pkg_update.py"
SERVICE = ROOT / "src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
POST = ROOT / "pkg/+POST_INSTALL"
spec = importlib.util.spec_from_file_location("protected_pkg_update", SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def result(args, rc=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args, rc, stdout=stdout, stderr=stderr)


class ProtectedPkgUpdate(unittest.TestCase):
    def test_nonroot_refused_before_mutation(self):
        with mock.patch.object(m.os, "geteuid", return_value=1001), \
             mock.patch.object(m, "native_command") as native:
            self.assertEqual(m.main(["cmd", "replace", "/root/test.pkg"]), 69)
            native.assert_not_called()

    def test_incomplete_record_blocks_staging(self):
        with tempfile.TemporaryDirectory() as temp:
            active = Path(temp) / "operation.json"
            active.write_text("{}")
            with mock.patch.object(m, "ACTIVE", active), \
                 mock.patch.object(m, "root_and_private_base"), \
                 mock.patch.object(m, "native_command") as native:
                with self.assertRaisesRegex(m.Refused, "PREVIOUS_UPDATE_REQUIRES_REVIEW"):
                    m.stage_archive(Path(temp) / "missing.pkg")
                native.assert_not_called()

    def test_candidate_cannot_escape_private_staging(self):
        with mock.patch.object(m, "BASE", Path("/private/zapret")), \
             mock.patch.object(m, "inspect_regular") as inspect:
            with self.assertRaisesRegex(m.Refused, "STAGE_PATH_REFUSED"):
                m.validated_stage("/etc/foreign.pkg", "a" * 64, "0.6.5_84")
            inspect.assert_not_called()

    def test_manifest_foreign_package_refused(self):
        with mock.patch.object(m, "native_command", return_value=result(
                [], stdout='{"name":"foreign","version":"0.6.5_84"}')):
            with self.assertRaisesRegex(m.Refused, "PACKAGE_IDENTITY_REFUSED"):
                m.manifest_identity(Path("/fake.pkg"))

    def trial(self, temp, prepare=True, pkg_rc=0, hook_failure=False,
              finish=True, version_match=True):
        stage = Path(temp) / "incoming.pkg"
        stage.write_bytes(b"immutable staged bytes")
        digest, version = "a" * 64, "0.6.5_84"
        invoked = []
        def command(args, timeout=90):
            invoked.append(args)
            if args[0] == str(m.SERVICE):
                if args[1] == "pkg-update-prepare":
                    return result(args, 0 if prepare else 69,
                                  "zapret-pkg-update-prepared=1" if prepare else "")
                if args[1] == "pkg-update-finish":
                    return result(args, 0 if finish else 70,
                                  "zapret-pkg-update-committed=1" if finish else "")
            if args[0] == "/usr/sbin/pkg":
                return result(args, pkg_rc, "zapret-pkg-postinstall-guarded=1",
                              "pkg: PRE-INSTALL script failed" if hook_failure else "")
            raise AssertionError("unexpected native call")
        def installed():
            return version if version_match else "0.6.5_83"
        with mock.patch.object(m, "stage_archive", return_value=(stage, digest, version)), \
             mock.patch.object(m, "native_command", side_effect=command), \
             mock.patch.object(m, "installed_version", side_effect=installed), \
             mock.patch.object(m, "ACTIVE", Path(temp) / "operation.json"), \
             mock.patch.object(m, "durable_directory"):
            error = None
            try:
                m.replace(Path("/root/unread.pkg"))
            except m.Refused as exc:
                error = str(exc)
        return invoked, error, stage.exists()

    def test_rejected_prepare_never_calls_pkg(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls, error, exists = self.trial(tmp, prepare=False)
            self.assertEqual(error, "NATIVE_PREPARE_REFUSED")
            self.assertFalse(exists)
            self.assertEqual(len(calls), 1)

    def test_pkg_rc_zero_with_failed_hook_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls, error, exists = self.trial(tmp, hook_failure=True)
            self.assertEqual(error, "PACKAGE_OPERATION_NOT_CONFIRMED")
            self.assertTrue(exists)
            self.assertEqual(len(calls), 2)

    def test_pkg_nonzero_retains_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls, error, exists = self.trial(tmp, pkg_rc=3)
            self.assertEqual(error, "PACKAGE_OPERATION_NOT_CONFIRMED")
            self.assertTrue(exists)

    def test_successor_mismatch_never_restores(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls, error, exists = self.trial(tmp, version_match=False)
            self.assertEqual(error, "WRONG_INSTALLED_SUCCESSOR")
            self.assertTrue(exists)
            self.assertFalse(any(len(x)>1 and x[1]=="pkg-update-finish" for x in calls))

    def test_restore_failure_retains_staged_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls, error, exists = self.trial(tmp, finish=False)
            self.assertEqual(error, "RUNTIME_RESTORE_REQUIRES_REVIEW")
            self.assertTrue(exists)

    def test_restore_failure_marker_redacted_and_not_authorizing(self):
        from contextlib import redirect_stderr
        from io import StringIO

        private = "private /conf/config.xml <HOSTLIST:user> secret.example"
        self.assertEqual(
            m.restore_finish_evidence(result([], 70, stderr=
                "pkg-update-finish-failed=boot\n" + private)),
            "rc:70,stage:boot,guard:unknown")
        self.assertEqual(
            m.restore_finish_evidence(result([], 99, stderr=private)),
            "rc:other,stage:unknown,guard:unknown")
        self.assertEqual(
            m.restore_finish_evidence(result([], 70, stderr=
                "pkg-update-finish-failed=boot\n"
                "shared-apply-guard=epoch-attest\n" + private)),
            "rc:70,stage:boot,guard:epoch-attest")
        self.assertNotIn(private, m.restore_finish_evidence(
            result([], 70, stderr="pkg-update-finish-failed=boot\n" + private)))
        self.assertIn('pkg-update-finish-failed=boot', SERVICE.read_text())

        output = StringIO()
        with tempfile.TemporaryDirectory() as tmp, redirect_stderr(output):
            calls, error, staged = self.trial(tmp, finish=False)
        self.assertEqual(error, "RUNTIME_RESTORE_REQUIRES_REVIEW")
        self.assertTrue(staged)
        self.assertEqual(len(calls), 3)
        self.assertIn("pkg-update-restore-evidence=rc:70,stage:unknown,guard:unknown",
                      output.getvalue())

    def test_exact_success_dispatches_one_native_pkg(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls, error, exists = self.trial(tmp)
            self.assertIsNone(error)
            self.assertFalse(exists)
            self.assertEqual(sum(x[0] == "/usr/sbin/pkg" for x in calls), 1)
            self.assertEqual([x[1] for x in calls if x[0] == str(m.SERVICE)],
                             ["pkg-update-prepare", "pkg-update-finish"])

    def test_same_version_finish_without_real_postinstall_is_refused(self):
        # Matching pkgdb version does not establish that native pkg ran.
        with mock.patch.object(m, "fd9_is_original_owner"), \
             mock.patch.object(m, "root_and_private_base"), \
             mock.patch.object(m, "validate_record",
                 return_value={"phase":"prepared","was_running":True}), \
             mock.patch.object(m, "installed_version") as installed:
            with self.assertRaisesRegex(m.Refused, "NATIVE_POSTINSTALL_NOT_ATTESTED"):
                m.inspect("a" * 64, "0.6.5_84")
            installed.assert_not_called()

    def test_single_private_record_postinstall_transition(self):
        with tempfile.TemporaryDirectory() as tmp:
            import json
            base = Path(tmp)
            record = base / "operation.json"
            prior = {"schema": 1, "phase": "prepared",
                     "stage": str(base / "incoming-1.pkg"), "sha256": "a" * 64,
                     "to_version": "0.6.5_84", "from_version": "0.6.5_84",
                     "was_running": True}
            record.write_text(json.dumps(prior))
            record.chmod(0o600)
            with mock.patch.object(m, "BASE", base), \
                 mock.patch.object(m, "ACTIVE", record), \
                 mock.patch.object(m, "fd9_is_original_owner"), \
                 mock.patch.object(m, "root_and_private_base"), \
                 mock.patch.object(m, "read_active",
                     side_effect=lambda: json.loads(record.read_text())), \
                 mock.patch.object(m, "validated_stage"):
                m.postinstall_attest()
                done = json.loads(record.read_text())
                self.assertEqual(done["phase"], "postinstall-attested")
                self.assertEqual(
                    {k:v for k,v in done.items() if k != "phase"},
                    {k:v for k,v in prior.items() if k != "phase"})
                self.assertEqual(record.stat().st_mode & 0o777, 0o600)
                with self.assertRaisesRegex(m.Refused, "POSTINSTALL_PHASE_REFUSED"):
                    m.postinstall_attest()

    def test_native_runtime_release_cache_is_disposable_only(self):
        fixture_path = ROOT / "scripts" / "stage5-native-protected-update.py"
        spec = importlib.util.spec_from_file_location(
            "protected_native_cache_fixture", fixture_path)
        fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)

        class OfficialUpstream:
            RELEASE = "v1.0.7"

        with mock.patch.dict(fixture.os.environ,
                             {"GITHUB_ACTIONS": "false",
                              "ZAPRET2_PROTECTED_PKG_NATIVE_TEST": "1"},
                             clear=True):
            with self.assertRaisesRegex(
                    RuntimeError, "NATIVE_STABLE_RELEASE_CACHE_NOT_QUALIFIED"):
                fixture.seed_qualified_stable_tag_for_disposable_guest(OfficialUpstream())

    def test_single_fd9_owner_and_deferred_postinstall(self):
        service = SERVICE.read_text()
        post = POST.read_text()
        self.assertIn("pkg_update_prepare_service()", service)
        self.assertIn("pkg_update_finish_service()", service)
        self.assertIn('if [ -e "${PKG_UPDATE_RECORD}" ]', service)
        self.assertIn("status|stop|pkg-update-finish", service)
        self.assertIn("zapret-pkg-postinstall-guarded=1", post)
        self.assertIn("pkg-update-postinstall", post)
        self.assertIn("pkg_update_postinstall_service()", service)
        self.assertIn("NATIVE_POSTINSTALL_NOT_ATTESTED", SCRIPT.read_text())
        self.assertIn('elif [ "${restore_running_state}" -eq 1 ]; then', post)
        self.assertNotIn("SIGSTOP", SCRIPT.read_text())


if __name__ == "__main__":
    unittest.main()
