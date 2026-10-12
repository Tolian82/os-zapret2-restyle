#!/usr/bin/env python3
"""Native Voice five-resource forward: real commit and one original Config flock.

The commit tests reuse the ACTUAL _69.._78 runtime/ledger/files stage chain
with simulated kernel + process sources; the full coordinator orchestration
uses the prepared native fixture and checks stage order/one borrowed fd.
Never calls real ipfw, FreeBSD shell actuators or an OPNsense appliance.
"""
from __future__ import annotations
import fcntl
import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

import voice_native_forward_apply as forward
from voice_ipfw_adapter import FreeBSDIPFWAdapter
from voice_native_process_actions import FreeBSDVoiceProcessActions
from voice_cutover_restore_stage import prepare_restore_stage
from voice_cutover_install_image import prepare_installable_restore
from voice_cutover_journal import _digest, mutating_predecessor


def fixture(file, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / file)
    assert spec and spec.loader
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


config_fixture = fixture("test-voice-native-forward-config.py", "forward_apply_config_fixture")
stop_fixture = fixture("test-voice-native-forward-stop.py", "forward_apply_stop_fixture")


class NativeForwardCommitTests(unittest.TestCase):
    def setUp(self):
        self.parent = config_fixture.ForwardCandidateConfigTests()
        self.parent.setUp()
        self.addCleanup(self.parent.doCleanups)
        self.parent.call()
        self.fx = self.parent.fx
        self.config = self.fx.root / "config.xml"
        self.old = self.fx.whole.read()
        self.old_owner = self.fx.ipfw.owned()
        self.precommit = self.fx.ipfw.pending()
        self.bypass_legacy = patch("voice_native_forward_apply.require_no_legacy")
        self.bypass_legacy.start()
        self.addCleanup(self.bypass_legacy.stop)

    def call(self, *, lock=True):
        fd = os.open(self.config, os.O_RDWR)
        try:
            if lock:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return forward.commit_forward_voice_apply(
                journal=self.fx.whole, ledger=self.fx.ipfw,
                previous_backup=self.fx.backup,
                config_path=self.config, config_fd=fd,
                config_owner=(os.geteuid(), os.getegid()),
                staged_config=self.fx.stage_config,
                candidate_runtime=self.fx.candidate,
                active_runtime=self.fx.root / "runtime",
                desired_manifest=self.parent.stage.parent.desired,
                probe=self.parent.stage.probe,
                kernel_reader=self.parent.stage.kernel,
                read_adapter=self.parent.stage.parent.read,
                write_adapter=self.parent.stage.parent.write,
                require_lifecycle_owner=lambda: None,
            )
        finally:
            os.close(fd)

    def test_real_desired_config_runtime_kernel_and_ipfw_commit(self):
        result = self.call()
        self.assertEqual("native-forward-five-resources-committed", result["state"])
        self.assertEqual("committed", self.fx.whole.read()["phase"])
        self.assertIsNone(self.fx.ipfw.pending())
        self.assertNotEqual(self.old_owner, self.fx.ipfw.owned())
        self.assertEqual(
            self.fx.ipfw.owned(), self.parent.stage.parent.desired
        )
        self.assertEqual(self.config.read_bytes(), self.parent.candidate)
        self.assertTrue((self.fx.whole.directory / "forward-config-redo.json").exists())
        self.assertTrue(result["previous_snapshot_retained"])
        self.assertTrue(result["postcommit_cleanup_pending"])
        self.assertIs(result["public_voice_apply"], False)

    def test_commit_refuses_without_config_flock(self):
        with self.assertRaises((RuntimeError, OSError, ValueError)):
            self.call(lock=False)
        self.assertEqual("mutating", self.fx.whole.read()["phase"])
        self.assertEqual(self.precommit, self.fx.ipfw.pending())

    def test_modified_kernel_process_refuses_without_committing(self):
        self.parent.stage.binary[202] = "/bin/foreign"
        with self.assertRaises((RuntimeError, ValueError)):
            self.call()
        self.assertEqual(self.old, self.fx.whole.read())
        self.assertEqual(self.precommit, self.fx.ipfw.pending())

    def test_wrong_live_config_refuses_without_committing(self):
        self.config.write_bytes(b"<foreign/>")
        with self.assertRaises((RuntimeError, ValueError)):
            self.call()
        self.assertEqual("mutating", self.fx.whole.read()["phase"])
        self.assertEqual(self.old_owner, self.fx.ipfw.owned())

    def test_changed_ipfw_precommit_refuses_without_committing(self):
        (self.fx.ipfw.directory / "intent.json").unlink()
        with self.assertRaises((RuntimeError, ValueError)):
            self.call()
        self.assertEqual("mutating", self.fx.whole.read()["phase"])

    def test_missing_runtime_redo_refuses(self):
        (self.fx.whole.directory / "forward-runtime-redo.json").unlink()
        with self.assertRaises((RuntimeError, ValueError)):
            self.call()
        self.assertEqual("mutating", self.fx.whole.read()["phase"])


    def replay(self, *, lock=True):
        fd = os.open(self.config, os.O_RDWR)
        try:
            if lock:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return forward.resume_committed_forward_voice_apply(
                journal=self.fx.whole, ledger=self.fx.ipfw,
                previous_backup=self.fx.backup,
                config_path=self.config, config_fd=fd,
                config_owner=(os.geteuid(), os.getegid()),
                staged_config=self.fx.stage_config,
                candidate_runtime=self.fx.candidate,
                active_runtime=self.fx.root / "runtime",
                desired_manifest=self.parent.stage.parent.desired,
                probe=self.parent.stage.probe,
                kernel_reader=self.parent.stage.kernel,
                read_adapter=self.parent.stage.parent.read,
                write_adapter=self.parent.stage.parent.write,
                require_lifecycle_owner=lambda: None,
            )
        finally:
            os.close(fd)

    def resume_via_executor(self):
        return forward.execute_prepared_voice_apply(
            journal=self.fx.whole, ledger=self.fx.ipfw,
            previous_backup=self.fx.backup, process_evidence=None,
            security_evidence=None, install_image=self.fx.root / "unused-image",
            config_path=self.config, active_runtime=self.fx.root / "runtime",
            staged_config=self.fx.stage_config,
            candidate_runtime=self.fx.candidate,
            desired_manifest=self.parent.stage.parent.desired,
            probe=self.parent.stage.probe, kernel_reader=self.parent.stage.kernel,
            read_adapter=self.parent.stage.parent.read,
            write_adapter=self.parent.stage.parent.write,
            require_lifecycle_owner=lambda: None,
            config_owner=(os.geteuid(), os.getegid()),
            actions_factory=lambda _: self.fail(
                "COMMITTED replay must not construct any process actuator"
            ),
        )

    def test_committed_retry_through_original_executor(self):
        self.fx.whole.commit()
        with patch.object(
            forward, "stop_previous_and_install_forward_runtime",
            side_effect=AssertionError("COMMITTED must not enter forward stages"),
        ):
            result = self.resume_via_executor()
        self.assertEqual(result["state"], "native-forward-five-resources-committed")
        self.assertEqual(self.fx.ipfw.owned(), self.parent.stage.parent.desired)
        self.assertIsNone(self.fx.ipfw.pending())
        self.assertEqual(self.config.read_bytes(), self.parent.candidate)

    def test_postcommit_cleanup_power_cut_after_table_destroy_retries(self):
        self.fx.whole.commit()
        adapter = self.parent.stage.parent.write
        real_destroy = adapter.destroy_table
        def power_cut_after_destroy(name):
            real_destroy(name)
            raise OSError("simulated power cut after actual IPFW table removal")
        with patch.object(adapter, "destroy_table",
                          side_effect=power_cut_after_destroy):
            with self.assertRaisesRegex(OSError, "simulated power cut"):
                self.resume_via_executor()
        # COMMITTED and desired owner are durable, while IPFW pending still
        # survives and the kernel stage was actually removed.
        self.assertEqual(self.fx.whole.read()["phase"], "committed")
        self.assertIsNotNone(self.fx.ipfw.pending())
        self.assertEqual(self.fx.ipfw.owned(), self.parent.stage.parent.desired)
        self.assertIsNone(self.parent.stage.parent.read.get_table(
            "zapret2_voice_telegram_stage"
        ))
        result = self.resume_via_executor()
        self.assertEqual(result["state"], "native-forward-five-resources-committed")
        self.assertIsNone(self.fx.ipfw.pending())

    def test_postcommit_rejects_foreign_stage_after_partial_cleanup(self):
        self.fx.whole.commit()
        self.fx.ipfw.commit(self.parent.stage.parent.desired)
        kernel = self.parent.stage.parent.read.kernel
        # A stage containing values not present in the sealed old manifest
        # must never be deleted/quietly adopted on retry.
        kernel.tables["zapret2_voice_telegram_stage"] = ["203.0.113.7"]
        before = dict(kernel.tables)
        with patch.object(
            forward, "commit_verified",
            side_effect=AssertionError("foreign stage must fail preflight"),
        ):
            with self.assertRaises((RuntimeError, ValueError, OSError)):
                self.resume_via_executor()
        self.assertEqual(kernel.tables, before)
        self.assertIsNotNone(self.fx.ipfw.pending())

    def test_committed_retry_refuses_foreign_manifest_before_actuator(self):
        self.fx.whole.commit()
        foreign = dict(self.parent.stage.parent.desired)
        foreign["rules"] = {**foreign["rules"], 19010: [
            "divert", "989", "udp", "from", "any", "to", "any",
            "7000", "out", "not", "diverted", "not", "sockarg",
            "xmit", "vtnet1",
        ]}
        with patch.object(forward, "commit_verified",
                          side_effect=AssertionError("no mutation")):
            with self.assertRaises((RuntimeError, ValueError, OSError)):
                forward.execute_prepared_voice_apply(
                    journal=self.fx.whole, ledger=self.fx.ipfw,
                    previous_backup=self.fx.backup, process_evidence=None,
                    security_evidence=None, install_image=self.fx.root,
                    config_path=self.config, active_runtime=self.fx.root / "runtime",
                    staged_config=self.fx.stage_config,
                    candidate_runtime=self.fx.candidate,
                    desired_manifest=foreign,
                    probe=self.parent.stage.probe,
                    kernel_reader=self.parent.stage.kernel,
                    read_adapter=self.parent.stage.parent.read,
                    write_adapter=self.parent.stage.parent.write,
                    require_lifecycle_owner=lambda: None,
                    config_owner=(os.geteuid(), os.getegid()),
                    actions_factory=lambda _: self.fail("no actions"),
                )
        self.assertEqual(self.fx.ipfw.pending(), self.precommit)

    def test_power_cut_after_whole_commit_recovers_ipfw(self):
        self.fx.whole.commit()
        result = self.replay()
        self.assertEqual(result["state"], "native-forward-five-resources-committed")
        self.assertEqual(self.fx.ipfw.owned(), self.parent.stage.parent.desired)
        self.assertIsNone(self.fx.ipfw.pending())
        self.assertEqual(self.config.read_bytes(), self.parent.candidate)
        self.assertEqual(self.fx.whole.read()["phase"], "committed")

    def test_power_cut_after_ipfw_ownership_switch_recovers_cleanup(self):
        self.fx.whole.commit()
        self.fx.ipfw.commit(self.parent.stage.parent.desired)
        self.assertIsNotNone(self.fx.ipfw.pending())
        result = self.replay()
        self.assertEqual(result["state"], "native-forward-five-resources-committed")
        self.assertIsNone(self.fx.ipfw.pending())

    def test_postcommit_replay_after_finish_is_read_only(self):
        self.call()
        with patch.object(forward, "commit_verified",
                          side_effect=AssertionError("no IPFW mutation permitted")):
            result = self.replay()
        self.assertEqual(result["state"], "native-forward-five-resources-committed")

    def test_postcommit_replay_refuses_prepared_and_missing_flock(self):
        with self.assertRaisesRegex(forward.NativeForwardApplyError, "COMMITTED"):
            self.replay()
        self.fx.whole.commit()
        with self.assertRaises((RuntimeError, OSError, ValueError)):
            self.replay(lock=False)
        self.assertEqual(self.fx.ipfw.pending(), self.precommit)

    def test_postcommit_replay_rejects_foreign_engine_before_ipfw(self):
        self.fx.whole.commit()
        self.parent.stage.binary[202] = "/bin/foreign"
        with patch.object(forward, "commit_verified",
                          side_effect=AssertionError("IPFW mutation forbidden")):
            with self.assertRaises((RuntimeError, OSError, ValueError)):
                self.replay()
        self.assertEqual(self.fx.ipfw.pending(), self.precommit)


class NativeForwardOneLockSequenceTests(unittest.TestCase):
    def setUp(self):
        self.parent = stop_fixture.NativeForwardStopTests()
        self.parent.setUp()
        self.addCleanup(self.parent.doCleanups)
        self.fx = self.parent.fx
        self.config = self.fx.root / "config.xml"
        self.stages = []
        self.fds = []
        self.install_stage = self.fx.whole.directory / "restore-stage"
        self.install_image = self.fx.whole.directory / "restore-install-image"
        prepare_restore_stage(
            self.fx.backup, self.install_stage, self.fx.whole.read()["previous"],
        )
        prepare_installable_restore(
            self.install_stage, self.install_image,
            self.fx.whole.read()["previous"],
        )

    def run_sequence(self, fail_at=None, rollback_phase="mutating",
                     locked_config_fd=None):
        self.recovery_calls=[]
        def actions_factory(fd):
            self._assert_held(fd)
            return FreeBSDVoiceProcessActions(
                probe=self.parent.probe, journal=self.fx.whole,
                previous_backup=self.fx.backup,
                active_runtime=self.fx.root / "runtime",
                config_path=self.config,
                config_owner=(os.geteuid(), os.getegid()),
                config_fd=fd, require_lifecycle_owner=lambda: None,
                runner=self.parent.runner, actuator=self.parent.script,
            )

        def step(name, *, make_mutating=False):
            def callback(**args):
                fd = args.get("config_fd", args.get("locked_config_fd"))
                self._assert_held(fd)
                self.stages.append(name)
                if name == "stop" and fail_at == "stop_prepared":
                    raise RuntimeError("simulated stop preflight failure")
                if make_mutating:
                    self.fx.whole.mark_mutating()
                if name == "commit" and fail_at == "committed":
                    self.fx.whole.commit()
                    raise RuntimeError("simulated commit failure")
                if fail_at == name:
                    raise RuntimeError("simulated " + name + " failure")
                return {}
            return callback

        names = [
            ("stop_previous_and_install_forward_runtime", "stop"),
            ("start_forward_candidate_engine", "engine"),
            ("install_forward_voice_ipfw", "ipfw"),
            ("start_forward_voice_supervisor", "supervisor"),
            ("persist_forward_candidate_config", "config"),
            ("commit_forward_voice_apply", "commit"),
        ]
        def rollback(**kwargs):
            self._assert_held(kwargs["config_fd"])
            self.recovery_calls.append(kwargs)
            self.assertEqual(kwargs["install_image"], self.install_image)
            self.assertEqual(kwargs["actions"].config_fd, kwargs["config_fd"])
            if rollback_phase == "rolled_back":
                previous = self.fx.whole.read()
                body = {k:v for k,v in previous.items() if k != "check"}
                body["phase"] = "rolled_back"
                body["check"] = _digest(body)
                self.fx.whole._store(body)  # inject lower verified terminal boundary
            return {
                "state": "forward-failed-five-previous-domains-observed",
                "whole_phase": (
                    "rolled_back" if rollback_phase == "rolled_back-claimed"
                    else rollback_phase
                ),
                "safe_to_enable_voice": False,
            }
        from contextlib import ExitStack
        with ExitStack() as stack:
            stack.enter_context(patch.object(
                forward, "rollback_failed_precommit_voice_apply", side_effect=rollback,
            ))
            for index, (func, label) in enumerate(names):
                stack.enter_context(patch.object(
                    forward, func, side_effect=step(
                        label, make_mutating=index == 0,
                    )
                ))
            return forward.execute_prepared_voice_apply(
                journal=self.fx.whole, ledger=self.fx.ipfw,
                previous_backup=self.fx.backup,
                process_evidence=self.fx.process,
                security_evidence=self.fx.policy,
                install_image=self.install_image,
                config_path=self.config,
                active_runtime=self.fx.root / "runtime",
                staged_config=self.fx.stage_config,
                candidate_runtime=self.fx.candidate,
                desired_manifest=self.parent.parent.manifest,
                probe=self.parent.probe,
                kernel_reader=self.parent.kernel,
                read_adapter=self.parent.parent.adapter,
                write_adapter=FreeBSDIPFWAdapter(
                    19000, 19010, allow_mutations=True,
                ),
                require_lifecycle_owner=lambda: None,
                config_owner=(os.geteuid(), os.getegid()),
                actions_factory=actions_factory,
                locked_config_fd=locked_config_fd,
            )

    def _assert_held(self, fd):
        self.assertIsInstance(fd, int)
        self.assertEqual(os.fstat(fd).st_ino, self.config.stat().st_ino)
        with self.config.open("rb+") as competitor:
            with self.assertRaises(BlockingIOError):
                fcntl.flock(competitor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.fds.append(fd)

    def test_prepared_to_forward_uses_borrowed_original_fd_without_reflock_or_close(self):
        fd = os.open(self.config, os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.run_sequence(locked_config_fd=fd)
            self.assertEqual(
                ["stop", "engine", "ipfw", "supervisor", "config", "commit"],
                self.stages,
            )
            self.assertEqual({fd}, set(self.fds))
            self._assert_held(fd)  # caller still owns EXACT same flock
            self.assertEqual("mutating", self.fx.whole.read()["phase"])
        finally:
            os.close(fd)

    def test_borrowed_fd_without_original_flock_fails_before_stopping_previous(self):
        fd = os.open(self.config, os.O_RDWR)
        try:
            with self.assertRaises((RuntimeError, OSError, ValueError)):
                self.run_sequence(locked_config_fd=fd)
            self.assertEqual([], self.stages)
            self.assertEqual("prepared", self.fx.whole.read()["phase"])
            os.fstat(fd)  # on failure, caller still owns descriptor
        finally:
            os.close(fd)

    def test_prepared_six_segments_share_one_original_config_lock(self):
        self.run_sequence()
        self.assertEqual(
            ["stop", "engine", "ipfw", "supervisor", "config", "commit"],
            self.stages,
        )
        self.assertEqual(len(set(self.fds)), 1)
        self.assertEqual("mutating", self.fx.whole.read()["phase"])

    def test_failure_after_mutating_never_auto_commits_or_clears_recovery(self):
        with self.assertRaisesRegex(
            forward.NativeForwardApplyError, "all previous five domains restored",
        ):
            self.run_sequence(fail_at="ipfw")
        self.assertEqual(["stop", "engine", "ipfw"], self.stages)
        self.assertEqual(len(self.recovery_calls), 1)
        self.assertEqual(len(set(self.fds)), 1)
        self.assertEqual("mutating", self.fx.whole.read()["phase"])
        self.assertEqual(self.fx.whole.read()["schema"], 4)

    def test_failed_forward_reports_durable_rolled_back_not_mutating(self):
        # The lower recovery primitive is mocked at its already-verified
        # return boundary; production writes its real receipt and plan.
        with self.assertRaisesRegex(
            forward.NativeForwardApplyError,
            "five previous domains durably ROLLED_BACK",
        ) as denied:
            self.run_sequence(fail_at="ipfw",rollback_phase="rolled_back")
        self.assertEqual("mutating",mutating_predecessor(
            self.fx.whole.read()
        )["phase"])
        self.assertEqual("rolled_back",self.fx.whole.read()["phase"])
        self.assertEqual(len(self.recovery_calls),1)
        self.assertEqual(len(set(self.fds)),1)
        self.assertIn("simulated ipfw failure",str(denied.exception.__cause__))

    def test_failed_forward_rejects_contradictory_terminal_report(self):
        # A fake/incorrect lower-level result may not claim ROLLED_BACK
        # unless the authoritative journal really made that transition.
        with self.assertRaisesRegex(
            forward.NativeForwardApplyError,
            "terminal result disagrees with journal",
        ):
            self.run_sequence(fail_at="ipfw",rollback_phase="rolled_back-claimed")
        self.assertEqual("mutating",self.fx.whole.read()["phase"])
        self.assertEqual(len(self.recovery_calls),1)
        self.assertEqual(len(set(self.fds)),1)

    def test_prepared_failure_does_not_try_recovery_or_mutate_live_service(self):
        with self.assertRaisesRegex(RuntimeError, "simulated stop preflight failure"):
            self.run_sequence(fail_at="stop_prepared")
        self.assertEqual("prepared", self.fx.whole.read()["phase"])
        self.assertEqual(self.recovery_calls, [])

    def test_committed_failure_never_rolls_back_previous_state(self):
        with self.assertRaisesRegex(RuntimeError, "simulated commit failure"):
            self.run_sequence(fail_at="committed")
        self.assertEqual("committed", self.fx.whole.read()["phase"])
        self.assertEqual(self.recovery_calls, [])

    def test_missing_previous_install_image_blocks_before_stop(self):
        (self.install_image / "config.xml").write_bytes(b"<foreign/>")
        with self.assertRaisesRegex(forward.NativeForwardApplyError, "install image"):
            self.run_sequence()
        self.assertEqual(self.stages, [])
        self.assertEqual("prepared", self.fx.whole.read()["phase"])
        self.assertEqual(self.recovery_calls, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
