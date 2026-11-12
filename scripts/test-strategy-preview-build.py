#!/usr/bin/env python3
"""P5b2a source-only tests for disposable full-build orchestration ownership."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import stat
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

import strategy_preview_build as buildmod  # noqa: E402


XML = (b"<opnsense><system><hostname>private-preview</hostname></system>"
       b"<OPNsense><Zapret><general><enabled>1</enabled></general>"
       b"</Zapret></OPNsense></opnsense>")
PASS = {
    "schema": "p5b1-private-native-validator-v1",
    "mapped_validation": "native_mapped_valid",
    "engine_native_dry_run": "passed",
    "safe_to_apply": False,
    "public_preview_action": False,
}


class PrivateBuildSourceTests(unittest.TestCase):
    def setUp(self):
        self.paths: list[Path] = []
        self.calls = []
        self.before = {"config": "same", "ipfw": "same", "process": "same"}
        self.after = dict(self.before)
        self.checks = 0
        self.snapshot_calls = 0

    def tearDown(self):
        for path in self.paths:
            self.assertFalse(path.exists(), f"private preview workspace leaked: {path}")

    def lock_check(self):
        self.checks += 1

    def snapshot(self):
        self.snapshot_calls += 1
        return dict(self.before if self.snapshot_calls == 1 else self.after)

    def render(self, work: Path):
        self.paths.append(work)
        self.calls.append("render")
        self.assertEqual(work.parent, Path("/tmp"))
        self.assertRegex(work.name, "^zapret-p5b-[a-f0-9]{16}$")
        self.assertEqual(stat.S_IMODE(work.lstat().st_mode), 0o700)
        self.assertEqual((work / "candidate.xml").read_bytes(), XML)
        self.assertEqual(stat.S_IMODE((work / "candidate.xml").stat().st_mode),
                         0o600)
        target = work / "templates/usr/local/etc/zapret2"
        target.mkdir(parents=True)
        (target / "zapret.conf").write_text("native template")

    def stage(self, work: Path):
        self.calls.append("builder")
        self.assertEqual((work / "templates/usr/local/etc/zapret2/zapret.conf")
                         .read_text(), "native template")
        self.assertTrue((work / "candidate.xml").is_file())
        release = work / "release"
        release.mkdir(mode=0o755)
        (release / "managed").mkdir(mode=0o755)
        for name, content in {
            "dvtws.args": "--filter-tcp=443\n",
            "traffic-user.conf": "--filter-tcp=443\n",
            "tcp-ports.txt": "443\n",
            "udp-ports.txt": "",
        }.items():
            (release / name).write_text(content)
        (work / "build-stage.status").write_text("completed")

    def validate(self, work: Path):
        self.calls.append("validator")
        self.assertTrue((work / "release/dvtws.args").is_file())
        return dict(PASS)

    def run_preview(self, **changes):
        defaults = dict(native=False, lock_check=self.lock_check,
                        snapshot=self.snapshot, render=self.render,
                        build=self.stage, validator=self.validate)
        defaults.update(changes)
        return buildmod.preview_prepared_xml(XML, **defaults)

    def test_success_exact_sequence_no_apply_and_cleanup(self):
        report = self.run_preview()
        self.assertEqual(self.calls, ["render", "builder", "validator"])
        self.assertEqual(self.checks, 5)
        self.assertEqual(self.snapshot_calls, 2)
        self.assertEqual(report["schema"], "p5b2a-disposable-original-build-v1")
        self.assertEqual(report["native_validation"]["engine_native_dry_run"], "passed")
        self.assertTrue(report["workspace_cleaned"])
        self.assertTrue(report["pre_post_narrow_snapshot_equal"])
        self.assertEqual(report["full_p5_semantic_witness"], "not_run")
        self.assertIs(report["safe_to_apply"], False)
        self.assertIs(report["public_preview_action"], False)

    def test_builder_refusal_cleans_candidate(self):
        def refuse(work):
            self.calls.append("builder")
            raise RuntimeError("secret user domain text must not leak")
        with self.assertRaisesRegex(buildmod.PrivateBuildRefused,
                                    "^PRIVATE_BUILD_OR_VALIDATION_REFUSED$") as ctx:
            self.run_preview(build=refuse)
        self.assertIsNone(ctx.exception.__cause__)
        self.assertEqual(self.calls, ["render", "builder"])
        self.assertEqual(self.snapshot_calls, 2)

    def test_native_validator_refusal_cleans_workspace(self):
        def bad(work):
            self.calls.append("validator")
            raise OSError("private path /tmp and secret XML")
        with self.assertRaisesRegex(buildmod.PrivateBuildRefused,
                                    "PRIVATE_BUILD_OR_VALIDATION_REFUSED"):
            self.run_preview(validator=bad)
        self.assertEqual(self.calls, ["render", "builder", "validator"])

    def test_read_only_baseline_change_overrides_success(self):
        self.after["config"] = "changed"
        with self.assertRaisesRegex(buildmod.PrivateBuildRefused,
                                    "^LIVE_STATE_CHANGED_DURING_PREVIEW$"):
            self.run_preview()
        self.assertEqual(self.calls, ["render", "builder", "validator"])

    def test_refuse_lifecycle_changed_after_first_phase_and_cleanup(self):
        def reject_after_creation():
            self.checks += 1
            if self.checks == 2:
                raise RuntimeError("original FD9 lost")
        with self.assertRaisesRegex(buildmod.PrivateBuildRefused,
                                    "PRIVATE_BUILD_OR_VALIDATION_REFUSED"):
            self.run_preview(lock_check=reject_after_creation)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.snapshot_calls, 2)

    def test_keyboard_interrupt_still_removes_private_candidate(self):
        def cancel(work):
            raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.run_preview(build=cancel)
        self.assertEqual(self.snapshot_calls, 2)

    def test_validator_must_never_offer_apply(self):
        def lies(work):
            return {"safe_to_apply": True, "engine_native_dry_run": "passed"}
        with self.assertRaisesRegex(buildmod.PrivateBuildRefused,
                                    "VALIDATOR_REPORT_UNTRUSTED"):
            self.run_preview(validator=lies)

    def test_invalid_xml_is_rejected_before_lock_or_directory(self):
        for candidate, reason in [
            (b"", "CANDIDATE_XML_SIZE_INVALID"),
            (b"bad", "CANDIDATE_XML_INVALID"),
            (b'<!DOCTYPE x><opnsense/>', "CANDIDATE_XML_ENTITY_REFUSED"),
            (b"<opnsense/>", "CANDIDATE_XML_MODEL_INVALID"),
        ]:
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(buildmod.PrivateBuildRefused, reason):
                    buildmod.preview_prepared_xml(candidate, native=False)
        self.assertEqual(self.paths, [])
        self.assertEqual(self.checks, 0)

    def test_no_test_override_in_production_native_path(self):
        with self.assertRaisesRegex(buildmod.PrivateBuildRefused,
                                    "NATIVE_OWNER_OR_OVERRIDE_REFUSED"):
            buildmod.preview_prepared_xml(XML, render=self.render)

    def test_missing_injected_safety_guards_refuses(self):
        with self.assertRaisesRegex(buildmod.PrivateBuildRefused,
                                    "TEST_DEPENDENCIES_REQUIRED"):
            buildmod.preview_prepared_xml(XML, native=False)

    def test_preserves_original_renderer_and_full_orchestrator(self):
        code = (BACKEND / "strategy_preview_build.py").read_text(encoding="utf-8")
        self.assertIn("shared_apply_render.render_detached(", code)
        self.assertIn("orchestrator_build_release", code)
        self.assertIn('shared-candidate "$WORK/candidate.xml"', code)
        self.assertIn("validate_private_release(work, native=True)", code)
        self.assertIn("require_lifecycle_lock", code)
        self.assertIn("os.killpg", code)
        for forbidden in ("shared_apply_execute_service",
                          "shared_apply_run_service", "Config::save",
                          "ipfw add", "service_dispatch start",
                          "orchestrator_native_start"):
            self.assertNotIn(forbidden, code)

    def test_snapshots_are_read_only_not_claimed_as_full_p5(self):
        code = (BACKEND / "strategy_preview_build.py").read_text(encoding="utf-8")
        self.assertIn('"/sbin/ipfw", "-q", "list"', code)
        self.assertIn('"/sbin/ipfw", "table", "all", "list"', code)
        self.assertIn('"full_p5_semantic_witness": "not_run"', code)
        self.assertNotIn("os.chmod(0o755)", code)


if __name__ == "__main__":
    unittest.main(verbosity=2)
