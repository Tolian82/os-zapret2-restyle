#!/usr/bin/env python3
"""Offline protected package update invariants. No real pkg/service mutation."""
import importlib.util
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import os
import re
import tarfile
from io import BytesIO
import unittest
from contextlib import ExitStack, redirect_stdout
from io import StringIO
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
        self.assertIn('native-common-boot-guard=execute', SERVICE.read_text())
        self.assertIn('native-common-boot-guard=receipt', SERVICE.read_text())

        output = StringIO()
        with tempfile.TemporaryDirectory() as tmp, redirect_stderr(output):
            calls, error, staged = self.trial(tmp, finish=False)
        self.assertEqual(error, "RUNTIME_RESTORE_REQUIRES_REVIEW")
        self.assertTrue(staged)
        self.assertEqual(len(calls), 3)
        self.assertIn("pkg-update-restore-evidence=rc:70,stage:unknown,guard:unknown",
                      output.getvalue())

    def test_original_finish_phase_causes_are_exact_and_qualified(self):
        # Execute the real extracted POSIX function with inert original
        # children. No pkg, Config, FD9, IPFW, service or journal write.
        match = re.search(
            r"(?ms)^pkg_update_finish_service\(\)\n\{.*?^\}",
            SERVICE.read_text())
        self.assertIsNotNone(match)
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp) / "runtime.sh"
            runtime.write_text(
                '#!/bin/sh\n'
                'case "$2" in\n'
                ' verify|complete) exit 0 ;;\n'
                ' previous) printf "running\\n" ;;\n'
                ' *) exit 69 ;;\n'
                'esac\n')
            runtime.chmod(0o755)
            harness = match.group() + """
status_calls=0
shared_apply_status_service() {
    status_calls=$((status_calls + 1))
    if [ "$status_calls" -eq 1 ]; then return 1; fi
    return "${FINAL_RC:-0}"
}
wan_first_service() { return 0; }
extra_resources_block_pending_start_service() { return 0; }
shared_apply_has_record_service() { [ "${OWNER_MODE:-legacy}" = common ]; }
shared_apply_inspect_service() { printf 'committed original\\n'; }
shared_apply_boot_service() { return "${BOOT_RC:-0}"; }
start_service() { return "${START_RC:-0}"; }
pkg_update_finish_service pkg-update-finish sha version
"""
            environment = {**os.environ, "PYTHON_RUNTIME": str(runtime),
                "SCRIPT_DIR": temp,
                "PKG_UPDATE_RESTART_MARKER": str(Path(temp) / "restart"),
                "PKG_UPDATE_LEGACY_MARKER": str(Path(temp) / "legacy")}
            checks = (
                ({"OWNER_MODE": "common", "BOOT_RC": "1"}, 70, "boot"),
                ({"OWNER_MODE": "legacy", "START_RC": "1"}, 70, "start"),
                ({"OWNER_MODE": "legacy", "FINAL_RC": "2"}, 70, "verify"),
                ({"OWNER_MODE": "legacy"}, 0, None),
            )
            syntax = subprocess.run(["/bin/sh", "-n"], input=harness,
                capture_output=True, text=True)
            self.assertEqual(syntax.returncode, 0, syntax.stderr)
            for overrides, expected_rc, stage in checks:
                done = subprocess.run(["/bin/sh", "-c", harness],
                    env={**environment, **overrides}, capture_output=True,
                    text=True)
                self.assertEqual(done.returncode, expected_rc, overrides)
                if stage is None:
                    self.assertIn("zapret-pkg-update-committed=1", done.stdout)
                    self.assertNotIn("pkg-update-finish-failed=", done.stderr)
                else:
                    self.assertIn(
                        "pkg-update-finish-failed=" + stage + "\n",
                        done.stderr)
                evidence = m.restore_finish_evidence(result(
                    [], done.returncode, stderr=done.stderr))
                self.assertEqual(evidence,
                    f"rc:{expected_rc},stage:{stage or 'unknown'},guard:unknown")

    def test_finish_stage_cannot_be_spoofed_by_child_stderr(self):
        for rc, stderr, expected in (
            (70, "noise pkg-update-finish-failed=boot\n", "unknown"),
            (70, "pkg-update-finish-failed=boot extra\n", "unknown"),
            (69, "pkg-update-finish-failed=boot\n", "unknown"),
            (0, "pkg-update-finish-failed=boot\n", "unknown"),
            (70, "pkg-update-finish-failed=boot\npkg-update-finish-failed=start\n",
             "unknown"),
            (70, "pkg-update-finish-failed=start\n", "start"),
            (70, "pkg-update-finish-failed=verify\n", "verify"),
        ):
            with self.subTest(rc=rc, stderr=stderr):
                actual = m.restore_finish_evidence(
                    result([], rc, stderr=stderr))
                self.assertEqual(actual,
                    f"rc:{rc},stage:{expected},guard:unknown")

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

    def test_midextract_missing_service_module_is_strictly_pre_dispatch(self):
        fixture_path = ROOT / "scripts" / "stage5-native-protected-update.py"
        spec = importlib.util.spec_from_file_location(
            "protected_midextract_refusal_fixture", fixture_path)
        fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)
        with tempfile.TemporaryDirectory() as tmp:
            service = Path(tmp) / "zapret_service.sh"
            backend = Path(tmp) / "backend"
            backend.mkdir()
            module = backend / "launcher.sh"
            verified = result([], 1, stderr=(
                "ERROR: required backend module is missing: " +
                str(module) + "\n"))
            self.assertEqual(
                fixture.classify_native_interrupted_refusal(
                    verified, service),
                "missing-required-module-before-dispatch")
            self.assertEqual(
                fixture.classify_native_interrupted_refusal(result([], 69), service),
                "guard-69")
            self.assertEqual(
                fixture.classify_native_interrupted_refusal(result([], 1), service),
                "unqualified")
            self.assertEqual(
                fixture.classify_native_interrupted_refusal(
                    result([], 1, stderr="ERROR: other refusal\n"), service),
                "unqualified")
            module.write_text("#!/bin/sh\n")
            self.assertEqual(
                fixture.classify_native_interrupted_refusal(
                    verified, service), "unqualified")
            module.unlink()
            module.symlink_to("/etc/passwd")
            self.assertEqual(
                fixture.classify_native_interrupted_refusal(
                    verified, service), "unqualified")

    def test_published107_postboot_mismatch_is_reported_not_masked(self):
        fixture_path = ROOT / "scripts" / "stage5-native-published107-schema3-upgrade.py"
        spec = importlib.util.spec_from_file_location(
            "published107_postboot_fixture", fixture_path)
        fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)
        from types import SimpleNamespace
        bad = SimpleNamespace(original_auto_generation=mock.Mock(
            side_effect=RuntimeError("AUTO_NATIVE_GENERATION_OWNER_MISMATCH")))
        self.assertEqual(
            fixture.qualified_postboot_generation(bad, "a" * 32),
            (0, [], False))
        bad.original_auto_generation.assert_called_once_with("a" * 32, True)
        records = [{"native_number": 3, "role": "learning"}]
        good = SimpleNamespace(original_auto_generation=mock.Mock(
            return_value=(3, records)))
        self.assertEqual(
            fixture.qualified_postboot_generation(good, "b" * 32),
            (3, records, True))

    def test_native_interrupted_finish_missing_pid_reports_failure_not_exception(self):
        fixture_path = ROOT / "scripts" / "stage5-native-protected-update.py"
        spec = importlib.util.spec_from_file_location(
            "protected_native_missing_pid_fixture", fixture_path)
        fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)
        with tempfile.TemporaryDirectory() as temp:
            missing = Path(temp) / "dvtws2.pid"
            self.assertEqual(fixture.read_pid_if_present(missing), "missing")
            missing.write_text("10101\n")
            self.assertEqual(fixture.read_pid_if_present(missing), "10101")
            missing.write_text("bad PID\n")
            self.assertEqual(fixture.read_pid_if_present(missing), "missing")
            missing.unlink()
            missing.symlink_to("/etc/passwd")
            self.assertEqual(fixture.read_pid_if_present(missing), "missing")

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


class PostinstallContinuation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.active = self.base / "operation.json"
        self.original = {
            "schema": 1, "phase": "postinstall-attested", "was_running": True,
            "stage": str(self.base / "incoming-old.pkg"), "sha256": "a" * 64,
            "from_version": "0.6.5_107", "to_version": "0.6.5_109"}
        # Deliberately retain original formatting, not just equivalent JSON.
        self.original_raw = (json.dumps(self.original, indent=2) + "\n").encode()
        self.active.write_bytes(self.original_raw)
        self.active.chmod(0o600)
        self.original_sha = hashlib.sha256(self.original_raw).hexdigest()
        self.stage = str(self.base / "incoming-next.pkg")
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for name, value in (("BASE", self.base), ("ACTIVE", self.active)):
            self.stack.enter_context(mock.patch.object(m, name, value))
        self.stack.enter_context(mock.patch.object(m, "fd9_is_original_owner"))
        self.stack.enter_context(mock.patch.object(m, "root_and_private_base"))
        # Linux runner UID is not appliance root. Only that platform trust
        # adapter is substituted; journal bytes and every rename/fsync are real.
        self.stack.enter_context(mock.patch.object(m, "read_active", side_effect=
            lambda: json.loads(self.active.read_bytes())))
        self.stack.enter_context(mock.patch.object(m, "validated_stage"))
        self.installed = self.stack.enter_context(mock.patch.object(
            m, "installed_version", return_value="0.6.5_109"))
        self.native = self.stack.enter_context(mock.patch.object(
            m, "native_command", return_value=result([], stdout=">\n")))

    def begin(self):
        m.continue_record(self.stage, "b" * 64, "0.6.5_111", self.original_sha)

    def resume(self):
        m.continue_record(self.stage, "b" * 64, "0.6.5_111",
                          hashlib.sha256(self.active.read_bytes()).hexdigest())

    def test_real_journal_atomic_transition_preserves_exact_old_record(self):
        self.begin()
        actual = m.read_active()
        self.assertEqual(actual["phase"], "prepared")
        self.assertEqual(actual["continuation"]["record"].encode(), self.original_raw)
        self.assertEqual(actual["continuation"]["sha256"], self.original_sha)
        self.assertTrue(actual["was_running"])
        self.assertEqual(actual["from_version"], "0.6.5_109")
        self.assertEqual(actual["to_version"], "0.6.5_111")
        self.assertEqual(self.active.stat().st_mode & 0o777, 0o600)
        self.assertEqual(m.continuation_predecessor(actual),
                         (self.original, self.original_sha))
        self.assertEqual(list(self.base.iterdir()), [self.active])

    def test_missing_original_fd9_never_changes_journal(self):
        with mock.patch.object(m, "fd9_is_original_owner", side_effect=
                               m.Refused("ORIGINAL_FD9_NOT_HELD")):
            with self.assertRaisesRegex(m.Refused, "ORIGINAL_FD9_NOT_HELD"):
                self.begin()
        self.assertEqual(self.active.read_bytes(), self.original_raw)

    def test_crash_before_publish_keeps_original_and_can_restart(self):
        with mock.patch.object(m.os, "replace", side_effect=OSError("interrupted")):
            with self.assertRaises(OSError):
                self.begin()
        self.assertEqual(self.active.read_bytes(), self.original_raw)
        self.begin()
        self.assertEqual(m.read_active()["phase"], "prepared")

    def test_crash_after_publish_resumes_same_operation(self):
        real_replace = m.os.replace
        def interrupted(*args):
            real_replace(*args)
            raise OSError("lost coordinator immediately after atomic publication")
        with mock.patch.object(m.os, "replace", side_effect=interrupted):
            with self.assertRaises(OSError):
                self.begin()
        before = self.active.read_bytes()
        output = StringIO()
        with redirect_stdout(output):
            self.resume()
        self.assertIn("zapret-pkg-update-continue=prepared", output.getvalue())
        self.assertEqual(self.active.read_bytes(), before)
        self.assertEqual(json.loads(before)["continuation"]["record"].encode(),
                         self.original_raw)

    def test_real_postinstall_can_attest_extended_schema1_record(self):
        self.begin()
        m.postinstall_attest()
        self.installed.return_value = "0.6.5_111"
        before = self.active.read_bytes()
        output = StringIO()
        with redirect_stdout(output):
            self.resume()
        self.assertEqual(self.active.read_bytes(), before)
        self.assertIn("zapret-pkg-update-continue=finish", output.getvalue())
        self.assertEqual(m.read_active()["continuation"]["record"].encode(),
                         self.original_raw)

    def test_altered_original_sha_and_prepared_without_prior_proof_refused(self):
        with self.assertRaisesRegex(m.Refused, "ACTIVE_OPERATION_CHANGED"):
            m.continue_record(self.stage, "b" * 64, "0.6.5_111", "c" * 64)
        value = dict(self.original, phase="prepared")
        raw = json.dumps(value).encode()
        self.active.write_bytes(raw)
        with self.assertRaisesRegex(m.Refused, "POSTINSTALL_CONTINUATION_REQUIRED"):
            m.continue_record(self.stage, "b" * 64, "0.6.5_111",
                              hashlib.sha256(raw).hexdigest())
        self.assertEqual(self.active.read_bytes(), raw)

    def test_same_or_older_target_refused_without_mutation(self):
        for ordering in ("=", "<", "unexpected"):
            self.native.return_value = result([], stdout=ordering + "\n")
            with self.assertRaisesRegex(m.Refused, "CONTINUATION_REQUIRES_NEWER"):
                self.begin()
            self.assertEqual(self.active.read_bytes(), self.original_raw)

    def test_resume_cannot_switch_target_or_original_restore_intent(self):
        self.begin()
        sha = hashlib.sha256(self.active.read_bytes()).hexdigest()
        with self.assertRaisesRegex(m.Refused, "CONTINUATION_TARGET_CHANGED"):
            m.continue_record(self.stage, "c" * 64, "0.6.5_111", sha)
        value = m.read_active()
        value["was_running"] = False
        self.active.write_text(json.dumps(value))
        with self.assertRaisesRegex(m.Refused, "CONTINUATION_PREDECESSOR_INVALID"):
            self.resume()

    def test_source_and_package_commands_have_separate_environments(self):
        self.begin()
        # The real coordinator is exercised with real retained archive flock.
        old = self.base / "incoming-old.pkg"
        old.write_bytes(b"original held archive")
        target = self.base / "target.pkg"
        target.write_bytes(b"next immutable archive")
        calls = []
        def validate(raw, sha, version):
            return old if sha == "a" * 64 else Path(self.stage)
        def command(args, timeout=90, *, env=None):
            calls.append((args, env))
            if "pkg-update-continue-prepare" in args:
                return result(args, stdout="zapret-pkg-update-continue=prepared\n")
            if args[0] == "/usr/sbin/pkg":
                m.postinstall_attest()
                return result(args, stdout="zapret-pkg-postinstall-guarded=1\n")
            if "pkg-update-finish" in args:
                self.active.unlink()
                return result(args, stdout="zapret-pkg-update-committed=1\n")
            self.fail("unexpected native command")
        Path(self.stage).write_bytes(target.read_bytes())
        with mock.patch.object(m, "validated_stage", side_effect=validate), \
             mock.patch.object(m, "hash_file", side_effect=lambda p:
                 "b" * 64 if Path(p) == target else hashlib.sha256(Path(p).read_bytes()).hexdigest()), \
             mock.patch.object(m, "manifest_identity", return_value="0.6.5_111"), \
             mock.patch.object(m, "inspect_regular"), \
             mock.patch.object(m, "native_command", side_effect=command):
            self.installed.return_value = "0.6.5_111"
            m.continue_postinstall(target, self.original_sha)
        self.assertEqual(sum(args[0] == "/usr/sbin/pkg" for args, _ in calls), 1)
        self.assertIn("SCRIPT_DIR", calls[0][1])
        for _, environment in calls[1:]:
            self.assertEqual(set(environment), {"PATH", "LC_ALL"})
        self.assertEqual(calls[-1][0][0],
            "/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
        self.assertTrue(old.exists())
        self.assertFalse(self.active.exists())

    def test_real_shell_requires_stopped_committed_retired_before_handoff(self):
        function = re.search(
            r"(?ms)^pkg_update_continue_prepare_service\(\)\n\{.*?^\}",
            SERVICE.read_text()).group()
        interpreter = self.base / "python_runtime.sh"
        interpreter.write_text('''#!/bin/sh
case "$1" in
    */auto_detect_minute.py) printf '%s\\n' "$RETIRE_REPLY"; exit "$RETIRE_RC" ;;
    *) printf '%s\\n' "$*" > "$HANDOFF_FILE" ;;
esac
''')
        interpreter.chmod(0o755)
        marker = self.base / "handoff"
        harness = (function + '''
shared_apply_status_service() { return "$STATUS_RC"; }
shared_apply_inspect_service() { printf '%s\\n' "$OWNER_REPLY"; }
pkg_update_continue_prepare_service pkg-update-continue-prepare archive sha version recordsha
''')
        environment = {**os.environ, "PYTHON_RUNTIME": str(interpreter),
            "BACKEND_DIR": str(self.base), "SCRIPT_DIR": str(self.base),
            "HANDOFF_FILE": str(marker), "STATUS_RC": "1",
            "OWNER_REPLY": "committed original-generation",
            "RETIRE_RC": "0", "RETIRE_REPLY": "auto-detect-retire=ready"}
        for overrides in ({"STATUS_RC": "0"}, {"STATUS_RC": "2"},
                          {"OWNER_REPLY": "requires-review foreign"},
                          {"RETIRE_RC": "69"}, {"RETIRE_REPLY": "ready"}):
            done = subprocess.run(["/bin/sh", "-c", harness],
                env={**environment, **overrides}, capture_output=True, text=True)
            self.assertEqual(done.returncode, 69, overrides)
            self.assertFalse(marker.exists(), overrides)
        done = subprocess.run(["/bin/sh", "-c", harness], env=environment,
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("continue-record archive sha version recordsha", marker.read_text())


class RecoveryPackageStaging(unittest.TestCase):
    prefix = "usr/local/opnsense/scripts/OPNsense/Zapret/"

    def archive(self, root, extra=None, self_source=None):
        files = {self.prefix + "protected_pkg_update.py":
                 SCRIPT.read_bytes() if self_source is None else self_source,
                 self.prefix + "zapret_service.sh": b"#!/bin/sh\nexit 0\n",
                 self.prefix + "backend/raw.dat": b"\x00\xff\r\nexact binary bytes\n"}
        files.update(extra or {})
        payload = dict(files)
        payload["+MANIFEST"] = json.dumps({"name": "os-zapret2-restyle",
            "version": "0.6.5_114", "files": {"/" + key: "sha" for key in files}}).encode()
        archive = root / "candidate.pkg"
        with tarfile.open(archive, "w") as output:
            for name, body in payload.items():
                entry = tarfile.TarInfo(name)
                entry.size = len(body)
                output.addfile(entry, BytesIO(body))
        return archive

    def stage(self, root, archive, digest=None):
        with mock.patch.object(m, "BASE", root), \
             mock.patch.object(m, "root_and_private_base"), \
             mock.patch.object(m, "inspect_regular"), \
             mock.patch.object(m, "manifest_identity", return_value="0.6.5_114"):
            return m.stage_recovery_code(archive, digest or hashlib.sha256(archive.read_bytes()).hexdigest())

    def test_actual_tar_to_private_package_tree_preserves_binary_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = self.archive(root)
            original = archive.read_bytes()
            stage = self.stage(root, archive)
            self.assertEqual((stage / "protected_pkg_update.py").read_bytes(), SCRIPT.read_bytes())
            self.assertEqual((stage / "backend/raw.dat").read_bytes(),
                             b"\x00\xff\r\nexact binary bytes\n")
            self.assertEqual((stage / "zapret_service.sh").stat().st_mode & 0o777, 0o755)
            self.assertEqual(archive.read_bytes(), original)
            self.assertFalse((root / "operation.json").exists())

    def test_foreign_path_duplicate_alias_and_changed_coordinator_refused(self):
        for extra, own, reason in (
            ({self.prefix + "backend/../../escape.py": b"bad"}, None, "MEMBER_REFUSED"),
            ({"./" + self.prefix + "zapret_service.sh": b"duplicate"}, None, "MEMBER_REFUSED"),
            ({}, b"foreign coordinator", "SOURCE_MISMATCH")):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                archive = self.archive(root, extra, own)
                with self.assertRaisesRegex(m.Refused, reason):
                    self.stage(root, archive)
                self.assertEqual(list(root.iterdir()), [archive])

    def test_archive_sha_refused_before_any_extraction_or_journal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = self.archive(root)
            with mock.patch.object(m, "native_command") as native:
                with self.assertRaisesRegex(m.Refused, "RECOVERY_PACKAGE_CHANGED"):
                    self.stage(root, archive, "0" * 64)
                native.assert_not_called()
            self.assertEqual(list(root.iterdir()), [archive])


if __name__ == "__main__":
    unittest.main()
