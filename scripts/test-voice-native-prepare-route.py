#!/usr/bin/env python3
"""Operator native Voice route under one real Config FD9 simulation, no GUI."""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))
import voice_native_prepare_route as route
from voice_native_recovery_quiescence import _locked_config


class OperatorPrepareRouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="voice-operator-prebuilt-")
        self.addCleanup(self.tmp.cleanup)
        base=Path(self.tmp.name)
        self.input=base/"voice-operator-input"
        self.input.mkdir(mode=0o700)
        self.config=base/"config.xml"
        self.config.write_text("<opnsense/>")
        self.config.chmod(0o600)
        self.live=base/"runtime-live"
        self.live.mkdir(mode=0o700)
        self.whole=base/"voice-cutover"
        self.ledger=base/"voice-ipfw"
        self.build=base/"voice-build-input"
        self.build.mkdir(mode=0o700)
        (self.build/"config.xml").write_text("<opnsense/>")
        (self.build/"config.xml").chmod(0o600)
        (self.build/"release").mkdir(mode=0o700)
        self.build_worker=base/"voice_native_build_release.sh"
        self.build_worker.write_text("#!/bin/sh\nexit 0\n")
        self.calls=[]
        self.patches=[
            patch.object(route,"INPUT",self.input),
            patch.object(route,"BUILD_INPUT",self.build),
            patch.object(route,"BUILD_WORKER",self.build_worker),
            patch.object(route.native,"CONFIG",self.config),
            patch.object(route.native,"LEGACY_MARKER",base/"legacy.enabled"),
            patch.object(route.native,"ACTIVE_ROOT",self.live),
            patch.object(route.native,"WHOLE",self.whole),
            patch.object(route.native,"LEDGER",self.ledger),
            patch.object(route.native,"require_native_lock",lambda:self.calls.append("FD9")),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def input_files(self):
        for name in route.FILES:
            (self.input/name).write_text("0")
            (self.input/name).chmod(0o600)
        for name in route.DIRS:
            (self.input/name).mkdir(mode=0o755 if name == "runtime" else 0o700)

    def test_real_original_config_inode_flock_reaches_operator_coordinator(self):
        self.input_files()
        observed=[]
        def prepare(**kwargs):
            fd=kwargs["config_fd"]
            self.assertEqual(self.config,Path(kwargs["config_path"]))
            _locked_config(self.config,fd,kwargs["config_owner"])
            self.assertEqual(self.input/"voice-native-candidate",kwargs["release_dir"])
            self.assertEqual(self.input/"runtime",kwargs["source_runtime"])
            self.assertEqual(self.input/"config.xml",kwargs["source_config"])
            self.assertEqual("vtnet1",kwargs["physical_wan"])
            self.assertEqual(989,kwargs["divert_port"])
            self.assertIs(kwargs["security_reader"].probe,kwargs["probe"])
            observed.append(os.fstat(fd).st_ino)
            return {"state":"native-voice-original-lock-prepared",
                    "safe_to_enable_voice":False,"public_voice_apply":False}
        with patch.object(route,"prepare_native_voice_one_lock",side_effect=prepare):
            result=route.prepare_operator_prebuilt("vtnet1",989)
        self.assertEqual("native-voice-original-lock-prepared",result["state"])
        self.assertEqual([self.config.stat().st_ino],observed)
        self.assertGreaterEqual(len(self.calls),3)
        self.assertTrue(self.whole.is_dir())
        self.assertTrue(self.ledger.is_dir())
        self.assertEqual(self.config.read_text(),"<opnsense/>")

    def test_fixed_release_and_prepared_share_original_fd9_and_config_flock(self):
        observed=[]
        def stage(**kwargs):
            _locked_config(self.config,kwargs["config_fd"],kwargs["config_owner"])
            self.assertEqual(self.build/"config.xml",kwargs["source_config"])
            self.assertEqual(self.build/"release",kwargs["staged_release"])
            self.assertEqual(self.input,kwargs["destination"])
            self.assertEqual("vtnet1",kwargs["physical_wan"])
            self.assertEqual(989,kwargs["divert_port"])
            self.assertTrue(self.input.is_dir())
            self.assertEqual([],list(self.input.iterdir()))
            observed.append(("stage",os.fstat(kwargs["config_fd"]).st_ino))
            self.input_files()
            return {"state":"native-voice-detached-operator-input-published",
                    "safe_to_enable_voice":False,"public_voice_apply":False}
        def prepared(**kwargs):
            _locked_config(self.config,kwargs["config_fd"],kwargs["config_owner"])
            observed.append(("PREPARED",os.fstat(kwargs["config_fd"]).st_ino))
            self.assertEqual(self.input/"config.xml",kwargs["source_config"])
            return {"state":"native-voice-original-lock-prepared",
                    "safe_to_enable_voice":False,"public_voice_apply":False}
        with patch.object(route,"stage_native_operator_input",side_effect=stage), \
             patch.object(route,"prepare_native_voice_one_lock",side_effect=prepared):
            result=route.prepare_operator_prebuilt("vtnet1",989,from_release=True)
        self.assertEqual("native-voice-original-lock-prepared",result["state"])
        self.assertEqual([("stage",self.config.stat().st_ino),
                          ("PREPARED",self.config.stat().st_ino)],observed)
        self.assertEqual("<opnsense/>",self.config.read_text())

    def test_original_orchestrator_runs_between_same_original_fd9_and_prepared(self):
        (self.build/"release").rmdir()
        (self.build/"zapret.conf").write_text("ZAPRET_ENABLED=1")
        (self.build/"zapret.conf").chmod(0o600)
        calls=[]
        def build(cmd, **kwargs):
            self.assertEqual(["/bin/sh",str(self.build_worker)],cmd)
            self.assertTrue(kwargs["check"])
            self.assertIn(9, kwargs["pass_fds"])
            self.assertEqual("vtnet1", resolved_wan)
            self.assertFalse(self.input.exists() and list(self.input.iterdir()))
            (self.build/"release").mkdir()
            (self.build/".voice-build-workspace").mkdir()
            calls.append("native-orchestrator")
            return None
        def stage(**kwargs):
            _locked_config(self.config,kwargs["config_fd"],kwargs["config_owner"])
            self.assertEqual(self.build/"config.xml",kwargs["source_config"])
            self.assertEqual(self.build/"release",kwargs["staged_release"])
            calls.append("sealed-candidate")
            self.input_files()
            return {"state":"native-voice-detached-operator-input-published",
                    "safe_to_enable_voice":False,"public_voice_apply":False}
        def prepared(**kwargs):
            _locked_config(self.config,kwargs["config_fd"],kwargs["config_owner"])
            calls.append("schema4-PREPARED")
            return {"state":"native-voice-original-lock-prepared",
                    "safe_to_enable_voice":False,"public_voice_apply":False}
        resolved_wan="vtnet1"
        with patch.object(route,"require_saved_pair",return_value=None), \
             patch.object(route.subprocess,"run",side_effect=build), \
             patch.object(route,"stage_native_operator_input",side_effect=stage), \
             patch.object(route,"prepare_native_voice_one_lock",side_effect=prepared):
            result=route.prepare_operator_prebuilt(
                "vtnet1",989,from_saved=True,
            )
        self.assertEqual("native-voice-original-lock-prepared",result["state"])
        self.assertEqual(["native-orchestrator","sealed-candidate","schema4-PREPARED"],calls)
        self.assertEqual("<opnsense/>",self.config.read_text())

    def test_saved_build_refuses_foreign_or_symlinked_inputs(self):
        (self.build/"release").rmdir()
        (self.build/"zapret.conf").write_text("ZAPRET_ENABLED=1")
        (self.build/"zapret.conf").chmod(0o644)
        with self.assertRaises((OSError,ValueError,RuntimeError)):
            route.prepare_operator_prebuilt("vtnet1",989,from_saved=True)
        self.assertFalse(self.whole.exists())
        (self.build/"zapret.conf").chmod(0o600)
        (self.build/"zapret.conf").unlink()
        (self.build/"zapret.conf").symlink_to(self.build/"config.xml")
        with self.assertRaises((OSError,ValueError,RuntimeError)):
            route.prepare_operator_prebuilt("vtnet1",989,from_saved=True)
        self.assertTrue(self.input.is_dir())
        self.assertEqual([], list(self.input.iterdir()))
        self.assertFalse(self.whole.exists())
        self.assertFalse(self.ledger.exists())

    def test_mismatched_saved_pair_refuses_before_orchestrator(self):
        (self.build/"release").rmdir()
        (self.build/"zapret.conf").write_text('ZAPRET_ENABLED="1"')
        (self.build/"zapret.conf").chmod(0o600)
        with patch.object(route.subprocess, "run") as runner:
            with self.assertRaises((ValueError,RuntimeError,OSError)):
                route.prepare_operator_prebuilt("vtnet1",989,from_saved=True)
            runner.assert_not_called()
        self.assertFalse(self.whole.exists())
        self.assertFalse(self.ledger.exists())

    def test_orchestrator_build_error_cannot_prepare_or_publish(self):
        import subprocess
        (self.build/"release").rmdir()
        (self.build/"zapret.conf").write_text("ZAPRET_ENABLED=1")
        (self.build/"zapret.conf").chmod(0o600)
        with patch.object(route,"require_saved_pair",return_value=None), \
             patch.object(route.subprocess, "run",
                          side_effect=subprocess.CalledProcessError(1, ["/bin/sh"])), \
             patch.object(route, "stage_native_operator_input") as stage, \
             patch.object(route, "prepare_native_voice_one_lock") as prepared:
            with self.assertRaises(route.NativePrepareRouteError):
                route.prepare_operator_prebuilt("vtnet1", 989, from_saved=True)
            stage.assert_not_called()
            prepared.assert_not_called()
        self.assertEqual([], list(self.input.iterdir()))
        self.assertFalse(self.whole.exists())
        self.assertFalse(self.ledger.exists())

    def test_build_worker_uses_exact_existing_orchestrator_without_activating(self):
        worker = (ROOT / "src/opnsense/scripts/OPNsense/Zapret/voice_native_build_release.sh").read_text()
        self.assertIn('orchestrator_build_release \\', worker)
        self.assertIn('native-detached \\', worker)
        self.assertNotIn("orchestrator_native_start", worker)
        self.assertNotIn("atomic_install_tree", worker)
        self.assertNotIn("config_reload_template", worker)
        service = (ROOT / "src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
        self.assertIn('native-voice-prepare-saved)', service)

    def test_unknown_fixed_release_member_is_refused_before_config_open(self):
        (self.build/"foreign").write_text("foreign")
        with self.assertRaises((OSError,ValueError,RuntimeError)):
            route.prepare_operator_prebuilt("vtnet1",989,from_release=True)
        self.assertFalse(self.whole.exists())
        self.assertFalse(self.ledger.exists())
        self.assertTrue(self.input.is_dir())
        self.assertEqual([], list(self.input.iterdir()))

    def test_incomplete_source_refuses_before_ledger_or_original_config_open(self):
        self.input_files()
        (self.input/"tcp-ports.txt").unlink()
        with self.assertRaises((OSError,ValueError,RuntimeError)):
            route.prepare_operator_prebuilt("vtnet1",989)
        self.assertFalse(self.whole.exists())
        self.assertFalse(self.ledger.exists())

    def test_untrusted_operator_source_symlink_and_extra_file_denied(self):
        self.input_files()
        (self.input/"runtime").rmdir()
        (self.input/"runtime").symlink_to(self.live)
        with self.assertRaises((OSError,ValueError,RuntimeError)):
            route.prepare_operator_prebuilt("vtnet1",989)
        self.assertFalse(self.ledger.exists())
        (self.input/"runtime").unlink()
        (self.input/"runtime").mkdir(mode=0o755)
        (self.input/"unknown").write_text("bad")
        with self.assertRaises((OSError,ValueError,RuntimeError)):
            route.prepare_operator_prebuilt("vtnet1",989)
        self.assertFalse(self.whole.exists())

    def test_runtime_mode_must_be_installable_inside_private_parent(self):
        self.input_files()
        for bad in (0o700, 0o777):
            (self.input/"runtime").chmod(bad)
            with self.assertRaises((OSError,ValueError,RuntimeError)):
                route.prepare_operator_prebuilt("vtnet1",989)
            self.assertFalse(self.whole.exists())

    def test_invalid_wan_and_divert_rejected_before_any_file_action(self):
        for wan,port in (("vtnet1;",989),("vtnet1",0),("vtnet1",65536)):
            with self.subTest(wan=wan,port=port):
                with self.assertRaises((OSError,ValueError,RuntimeError)):
                    route.prepare_operator_prebuilt(wan,port)
        self.assertEqual([],self.calls)
        self.assertFalse(self.whole.exists())

    def test_saved_draft_continuous_prepare_apply_keeps_one_original_fd(self):
        import shutil
        shutil.rmtree(self.build)
        renderer = self.config.parent / "render-fixed.sh"
        renderer.write_text("#!/bin/sh\nexit 0\n")
        sequence = []
        original_fd = [None]

        def attest(**kw):
            fd = kw["config_fd"]
            _locked_config(self.config, fd, kw["config_owner"])
            if original_fd[0] is None:
                original_fd[0] = fd
            self.assertEqual(original_fd[0], fd)

        def saved_draft(**kw):
            attest(**kw)
            self.assertEqual("10000", kw["mask"])
            self.assertEqual("a" * 64, kw["expected_sha"])
            self.build.mkdir(mode=0o700)
            (self.build / "config.xml").write_text("<opnsense/>")
            (self.build / "config.xml").chmod(0o600)
            sequence.append("saved-off-candidate")
            return {"state": "native-voice-private-saved-draft-xml",
                    "safe_to_enable_voice": False, "public_voice_apply": False}

        def worker(cmd, **kw):
            self.assertIn(original_fd[0], kw["pass_fds"])
            _locked_config(self.config, original_fd[0],
                           (os.geteuid(), os.getegid()))
            self.assertEqual(cmd[0], "/bin/sh")
            if cmd[1] == str(renderer):
                self.assertEqual({"config.xml"}, set(os.listdir(self.build)))
                (self.build / ".voice-template-root").mkdir(mode=0o700)
                (self.build / "zapret.conf").write_text("test")
                (self.build / "zapret.conf").chmod(0o600)
                sequence.append("real-opnsense-renderer")
            elif cmd[1] == str(self.build_worker):
                (self.build / ".voice-build-workspace").mkdir(mode=0o700)
                (self.build / "release").mkdir(mode=0o700)
                sequence.append("native-orchestrator")
            else:
                self.fail("unexpected trusted worker")

        def stage(**kw):
            attest(**kw)
            self.input_files()
            sequence.append("qualified-operator-input")
            return {"state": "native-voice-detached-operator-input-published",
                    "safe_to_enable_voice": False, "public_voice_apply": False}

        def prepared(**kw):
            attest(**kw)
            sequence.append("schema4-PREPARED")
            return {"state": "native-voice-original-lock-prepared",
                    "safe_to_enable_voice": False, "public_voice_apply": False}

        def apply(*, locked_config_fd):
            self.assertEqual(original_fd[0], locked_config_fd)
            _locked_config(self.config, locked_config_fd,
                           (os.geteuid(), os.getegid()))
            sequence.append("guarded-forward-COMMIT")
            return {"state": "native-forward-five-resources-committed",
                    "whole_phase": "committed", "public_voice_apply": False,
                    "media_pass": False}
        with patch.object(route, "RENDER_WORKER", renderer), \
             patch.object(route, "prepare_saved_draft_candidate",
                          side_effect=saved_draft), \
             patch.object(route, "require_saved_pair"), \
             patch.object(route.subprocess, "run", side_effect=worker), \
             patch.object(route, "stage_native_operator_input",
                          side_effect=stage), \
             patch.object(route, "prepare_native_voice_one_lock",
                          side_effect=prepared), \
             patch.object(route, "execute_operator_prepared",
                          side_effect=apply):
            out = route.prepare_operator_prebuilt(
                "vtnet1", 989, from_draft=True,
                draft_mask="10000", expected_config_sha="a" * 64,
                apply_continuously=True,
            )
        self.assertEqual("native-forward-five-resources-committed", out["state"])
        self.assertEqual(
            ["saved-off-candidate", "real-opnsense-renderer",
             "native-orchestrator", "qualified-operator-input",
             "schema4-PREPARED", "guarded-forward-COMMIT"],
            sequence,
        )
        self.assertEqual("<opnsense/>", self.config.read_text())

    def test_continuous_apply_requires_saved_off_draft_and_attested_commit(self):
        with self.assertRaises(route.NativePrepareRouteError):
            route.prepare_operator_prebuilt(
                "vtnet1", 989, from_release=True, apply_continuously=True,
            )
        self.assertFalse(self.whole.exists())
        self.assertFalse(self.ledger.exists())


    def test_legacy_marker_prevents_prepared_even_when_prior_runtime_is_off(self):
        self.input_files()
        marker=route.native.LEGACY_MARKER
        marker.write_text("enabled\\n")
        (self.live/"telegram-voice-poc.state").write_text("disabled\\n")
        with patch.object(route,"prepare_native_voice_one_lock") as prepared:
            with self.assertRaisesRegex(route.NativePrepareRouteError,"requires reviewed migration"):
                route.prepare_operator_prebuilt("vtnet1",989)
            prepared.assert_not_called()
        self.assertEqual("enabled\\n",marker.read_text())
        self.assertFalse(self.whole.exists())

    def test_legacy_runtime_on_without_marker_blocks_migration(self):
        self.input_files()
        (self.live/"telegram-voice-poc.state").write_text("enabled\\n")
        with patch.object(route,"prepare_native_voice_one_lock") as prepared:
            with self.assertRaisesRegex(route.NativePrepareRouteError,"requires reviewed migration"):
                route.prepare_operator_prebuilt("vtnet1",989)
            prepared.assert_not_called()

    def test_legacy_unsafe_and_unknown_state_fail_closed(self):
        self.input_files()
        state=self.live/"telegram-voice-poc.state"
        state.symlink_to(self.config)
        with self.assertRaisesRegex(route.NativePrepareRouteError,"untrusted"):
            route.prepare_operator_prebuilt("vtnet1",989)
        state.unlink()
        state.write_text("unrecognized\\n")
        with self.assertRaisesRegex(route.NativePrepareRouteError,"unknown legacy"):
            route.prepare_operator_prebuilt("vtnet1",989)
        state.unlink()
        route.native.LEGACY_MARKER.symlink_to(self.config)
        with self.assertRaisesRegex(route.NativePrepareRouteError,"untrusted"):
            route.prepare_operator_prebuilt("vtnet1",989)

    def test_disabled_state_allows_existing_operator_preparation(self):
        self.input_files()
        (self.live/"telegram-voice-poc.state").write_text("disabled\\n")
        with patch.object(route,"prepare_native_voice_one_lock",
                          return_value={"state":"native-voice-original-lock-prepared",
                                        "safe_to_enable_voice":False,
                                        "public_voice_apply":False}) as prepared:
            out=route.prepare_operator_prebuilt("vtnet1",989)
        self.assertEqual("native-voice-original-lock-prepared",out["state"])
        prepared.assert_called_once()

    def test_shell_route_is_fd9_operator_only_not_configd(self):
        service=(ROOT/"src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
        configd=(ROOT/"src/opnsense/service/conf/actions.d/actions_zapret.conf").read_text()
        self.assertIn("native_voice_prepare_prebuilt_service()",service)
        self.assertIn("native-voice-prepare-prebuilt)",service)
        self.assertIn("native-voice-prepare-release)",service)
        self.assertIn("native-voice-prepare-saved)",service)
        self.assertIn("native-voice-prepare-draft)",service)
        self.assertIn("native-voice-prepare-apply-draft)",service)
        self.assertIn("prepare-from-draft-and-apply",service)
        self.assertIn("native_voice_prepare_prebuilt_service prepare-from-saved",service)
        self.assertIn("native_voice_prepare_prebuilt_service prepare-from-release",service)
        locked=service.split("case \"${1:-}\" in",1)[-1]
        self.assertIn("native-voice-prepare-prebuilt|native-voice-apply-prepared",locked)
        self.assertNotIn("[voice_prepare_prebuilt]",configd)
        self.assertNotIn("native-voice-prepare-prebuilt",configd)
        self.assertNotIn("native-voice-prepare-release",configd)
        self.assertNotIn("native-voice-prepare-saved",configd)
        self.assertNotIn("native-voice-prepare-draft",configd)
        self.assertNotIn("native-voice-prepare-apply-draft",configd)


if __name__=="__main__":
    unittest.main(verbosity=2)
