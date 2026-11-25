#!/usr/bin/env python3
"""TZ6v5 S10b2b2b3b1: genuine current P2e and original Config/WAN seam.

The exact source root, FD9 journal and schema3 generated old/final refs are
real. Previous live process/IPFW responses and Config/WAN subprocess outputs
are injected; this is NOT evidence of installed router state or WAN address.
"""
import importlib.util
from pathlib import Path
import os
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(B))
import neutral_schema3_saved_wan_preimage as gate
import neutral_schema3_previous_preimage as previous
from shared_apply_operation import SharedOperationError

spec = importlib.util.spec_from_file_location(
    "genuine_original_b3a_fixture",
    ROOT / "scripts/test-tz6v5-s10b2b2b3a-original-previous-readonly.py")
if spec is None or spec.loader is None:
    raise RuntimeError("GENUINE_ORIGINAL_S10B2B2B3A_MISSING")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class SavedWanOriginalFd9(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p.OriginalSchema3PreviousReadOnly.setUpClass()

    @classmethod
    def tearDownClass(cls):
        p.OriginalSchema3PreviousReadOnly.tearDownClass()

    def setUp(self):
        self.f = p.OriginalSchema3PreviousReadOnly("runTest")
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.f.prepare_with_previous()
        self.candidate = self.f.stage_and_bind()
        self.pinned = self.f.f.original.read()
        self.config_calls = []
        self.wan_calls = []

    def config(self, generation, page):
        self.config_calls.append((generation, page))
        detail = self.pinned["detail"]
        return {
            "result": "prepared",
            "snapshot": detail["candidate"],
            "enabled": "1", "changes": len(detail["changed_fields"]),
            "base": detail["base"],
            "candidate": detail["candidate"],
            "fields": detail["changed_fields"],
        }

    def wan(self):
        self.wan_calls.append(True)
        return "vtnet0"

    def attest(self, **changes):
        f = self.f.f
        args = dict(generation=f.generation, effective=f.effective,
                    native=f.native, enabled=True, parent=f.parent,
                    journal_root=f.journal_root, owner_uid=os.geteuid())
        args.update(changes)
        return gate._attest_saved_wan(**args)

    def guard(self, config=None, wan=None, old=None):
        config = config if config is not None else self.config
        wan = wan if wan is not None else self.wan
        old = old if old is not None else self.f.observed()
        return (
            patch.object(gate, "_native_preflight", side_effect=config),
            patch.object(gate, "_native_wan", side_effect=wan),
            patch.object(previous, "examine_shared", return_value=old),
        )

    def test_real_new_schema3_original_root_old_runtime_and_saved_wan(self):
        a, b, c = self.guard()
        with a as native, b as wan, c as runtime:
            receipt = self.attest()
        self.assertEqual(receipt.generation, self.f.f.generation)
        self.assertEqual(receipt.root_sha256, self.candidate.sha256)
        self.assertEqual(receipt.previous_generation, self.f.old["id"])
        self.assertEqual(receipt.previous_state, "ready")
        self.assertEqual(receipt.config_base_sha256, self.pinned["detail"]["base"])
        self.assertEqual(receipt.config_candidate_sha256,
                         self.pinned["detail"]["candidate"])
        self.assertEqual(receipt.verified_wan_device, "vtnet0")
        self.assertEqual(native.call_count, 2)
        self.assertEqual(wan.call_count, 2)
        self.assertEqual(runtime.call_count, 4)
        self.assertEqual(self.f.f.original.read(), self.pinned)
        self.assertEqual(receipt.authorization, "NONE")
        self.assertFalse(receipt.physical_transition_allowed)
        self.assertFalse(receipt.promotion_allowed)
        self.assertTrue(receipt.complete_active_root_required)
        self.assertTrue(receipt.original_pid_birth_epoch_required)
        self.assertTrue(receipt.first_install_stopped_kernel_required)
        with self.assertRaisesRegex(SharedOperationError, "preactivation gate"):
            self.f.f.original.advance("activating", self.f.f.detail)

    def test_original_stopped_prior_and_physical_wan_still_read_only(self):
        a, b, c = self.guard(old=self.f.observed("stopped"))
        with a, b, c:
            proof = self.attest()
        self.assertEqual(proof.previous_state, "stopped")
        self.assertFalse(proof.physical_transition_allowed)

    def test_native_config_drift_and_field_forgery_all_refused(self):
        good = self.config(self.f.f.generation, self.f.f.detail["page"])
        bads = (
            {"base": "0" * 64},
            {"candidate": "1" * 64},
            {"snapshot": "2" * 64},
            {"fields": ["general.enabled"]},
            {"changes": len(good["fields"]) + 1},
            {"enabled": "0"},
            {"result": "committed"},
            {"unknown": True},
            {"changes": True},
        )
        for changes in bads:
            with self.subTest(changes=changes):
                def wrong(*args):
                    return {**good, **changes}
                a, b, c = self.guard(config=wrong)
                with a, b, c, self.assertRaises(gate.SavedWanPreimageRefused):
                    self.attest()

    def test_original_wan_errors_or_mixed_physical_devices_refused(self):
        for state in ("", "wan-not-required", "wan-invalid", None, 1):
            with self.subTest(state=state):
                a, b, c = self.guard(wan=lambda: state)
                with a, b, c, self.assertRaises(gate.SavedWanPreimageRefused):
                    self.attest()
        iterator = iter(("vtnet0", "tun1"))
        a, b, c = self.guard(wan=lambda: next(iterator))
        with a, b, c, self.assertRaises(gate.SavedWanPreimageRefused):
            self.attest()

    def test_original_preflight_model_race_between_two_locks_refuses(self):
        actual = self.config(self.f.f.generation, self.f.f.detail["page"])
        wrong = {**actual, "snapshot": "3" * 64}
        values = iter((actual, wrong))
        a, b, c = self.guard(config=lambda *args: next(values))
        with a, b, c, self.assertRaises(gate.SavedWanPreimageRefused):
            self.attest()

    def test_original_previous_running_ipfw_changed_refused_before_save(self):
        a, b, c = self.guard(old=self.f.observed(source="foreign"))
        with a as nc, b as nw, c, self.assertRaises(gate.SavedWanPreimageRefused):
            self.attest()
        nc.assert_not_called()
        nw.assert_not_called()

    def test_original_bound_manifest_tamper_refused_before_php(self):
        candidate = self.f.f.release / "dvtws.args"
        contents = candidate.read_bytes()
        try:
            candidate.write_bytes(contents + b" ")
            a, b, c = self.guard()
            with a as nc, b as nw, c, self.assertRaises(gate.SavedWanPreimageRefused):
                self.attest()
            nc.assert_not_called()
            nw.assert_not_called()
        finally:
            candidate.write_bytes(contents)

    def test_original_prepared_journal_race_refuses_even_if_php_ready(self):
        def racing_config(*args):
            # Simulated external writer/race, not an original recovery.
            self.f.f.original._persist_record({**self.f.f.original.read(), "phase": "restored"})
            return self.config(*args)
        a, b, c = self.guard(config=racing_config)
        with a, b, c, self.assertRaises(gate.SavedWanPreimageRefused):
            self.attest()
        self.assertEqual(self.f.f.original.read()["phase"], "restored")

    def test_public_original_fd9_required_no_native_reader_called(self):
        with patch.object(gate, "require_lifecycle_lock",
                          side_effect=RuntimeError("not original FD9")), \
             patch.object(gate, "_native_preflight") as config, \
             patch.object(gate, "_native_wan") as wan:
            with self.assertRaisesRegex(gate.SavedWanPreimageRefused, "FD9"):
                gate.attest_saved_wan_under_fd9(
                    generation=self.f.f.generation, native=self.f.f.native,
                    effective=self.f.f.effective, enabled=True)
            config.assert_not_called()
            wan.assert_not_called()

    def test_inherited_only_fd9_and_fixed_original_php_and_wan_shell(self):
        issued = []
        def proc(argv, **kwargs):
            issued.append((argv, kwargs))
            if len(issued) == 1:
                return Mock(returncode=0, stdout=b'{"result":"prepared"}\n')
            if len(issued) == 2:
                return Mock(returncode=0, stdout=b"wan-ready\n")
            return Mock(returncode=0, stdout=b"tun3\n")
        with patch.object(gate.subprocess, "run", side_effect=proc):
            self.assertEqual(
                gate._native_preflight(self.f.f.generation, "strategies"),
                {"result": "prepared"})
            self.assertEqual(gate._native_wan(), "tun3")
        self.assertEqual([a[0] for a in issued], [
            ("/usr/local/bin/php",
             "/usr/local/opnsense/scripts/OPNsense/Zapret/shared_apply_config.php",
             "preflight", self.f.f.generation, "strategies"),
            ("/usr/local/opnsense/scripts/OPNsense/Zapret/wan_preflight.sh",
             "require"),
            ("/usr/local/opnsense/scripts/OPNsense/Zapret/wan_preflight.sh",
             "device"),
        ])
        self.assertTrue(all(k["pass_fds"] == (9,) and
                            k["timeout"] == 12 and
                            k["check"] is False for _, k in issued))

    def test_native_subprocess_failure_and_noncanonical_output(self):
        with patch.object(gate.subprocess, "run") as run:
            for status, raw in ((69, b""), (0, b""), (0, b"bad\n"),
                                (0, b"{}\n{}\n"), (0, b"x" * 5000)):
                with self.subTest(status=status, raw=raw[:12]):
                    run.return_value = Mock(returncode=status, stdout=raw)
                    with self.assertRaises(gate.SavedWanPreimageRefused):
                        gate._native_preflight(self.f.f.generation, "voice")
            run.side_effect = subprocess.TimeoutExpired("native", 12)
            with self.assertRaises(gate.SavedWanPreimageRefused):
                gate._native_wan()

    def test_existing_php_config_and_wan_are_original_read_only(self):
        php = (ROOT / "src/opnsense/scripts/OPNsense/Zapret/shared_apply_config.php"
               ).read_text()
        apply = (ROOT / "src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SettingsApply.php"
                 ).read_text()
        wan = (ROOT / "src/opnsense/scripts/OPNsense/Zapret/wan_preflight.sh"
               ).read_text()
        self.assertIn("$config->lock();", php)
        self.assertIn("self::preflight($plan, $fresh, $argv[3], $model)", php)
        self.assertIn("self::requireUnchanged($plan, $live);", apply)
        self.assertIn("config_resolve_interface", wan)
        self.assertIn("require|if-start|device", wan)
        self.assertEqual(self.f.f.original.read(), self.pinned)


    def test_disabled_native_config_seam_preserves_original_old_owner_double_read(self):
        # Schema1/Enabled OFF root qualification belongs to the REAL
        # _attest_prepared_previous. Here only that prerequisite is injected
        # because this particular genuine fixture is schema2/Enabled ON.
        from neutral_schema3_previous_preimage import PreviousRuntimeReceipt
        old = self.pinned["previous"]
        def receipt(state):
            return PreviousRuntimeReceipt(
                self.f.f.generation, self.pinned["manifest"]["root_sha256"],
                old["id"], old["candidate"], state, 0, 0)
        original = self.f.f.original.read()
        for state in ("stopped", "ready"):
            with self.subTest(old_state=state):
                off = {**self.config(self.f.f.generation, self.f.f.detail["page"]),
                       "enabled": "0"}
                with patch.object(gate, "_attest_prepared_previous",
                                  return_value=receipt(state)) as previous_read, \
                     patch.object(gate, "_native_preflight",
                                  return_value=off) as config_read, \
                     patch.object(gate, "_native_wan",
                                  side_effect=AssertionError("OFF must not probe active WAN")) as wan:
                    result = self.attest(enabled=False)
                self.assertEqual(result.previous_state, state)
                self.assertIsNone(result.verified_wan_device)
                self.assertEqual(config_read.call_count, 2)
                self.assertEqual(previous_read.call_count, 2)
                wan.assert_not_called()
                self.assertEqual(result.authorization, "NONE")
                self.assertFalse(result.physical_transition_allowed)
                self.assertFalse(result.promotion_allowed)
                self.assertEqual(self.f.f.original.read(), original)

    def test_disabled_config_and_predecessor_race_still_refuse(self):
        from dataclasses import replace
        from neutral_schema3_previous_preimage import PreviousRuntimeReceipt
        old = self.pinned["previous"]
        base = PreviousRuntimeReceipt(
            self.f.f.generation, self.pinned["manifest"]["root_sha256"],
            old["id"], old["candidate"], "stopped", 0, 0)
        off = {**self.config(self.f.f.generation, self.f.f.detail["page"]),
               "enabled": "0"}
        for source in ("config", "previous"):
            with self.subTest(source=source):
                native_config = ([off, {**off, "enabled": "1"}] if source == "config"
                                 else [off, off])
                natives = ([base, base] if source == "config"
                           else [base, replace(base, observed_previous_state="ready")])
                with patch.object(gate, "_attest_prepared_previous",
                                  side_effect=natives), \
                     patch.object(gate, "_native_preflight",
                                  side_effect=native_config), \
                     patch.object(gate, "_native_wan") as wan, \
                     self.assertRaises(gate.SavedWanPreimageRefused):
                    self.attest(enabled=False)
                wan.assert_not_called()

    def test_nonboolean_enabled_refuses_before_native_read(self):
        with patch.object(gate, "_native_preflight") as config, \
             patch.object(gate, "_native_wan") as wan:
            for enabled in (0, 1, None, "0", "1"):
                with self.subTest(enabled=enabled), \
                     self.assertRaises(gate.SavedWanPreimageRefused):
                    self.attest(enabled=enabled)
        config.assert_not_called()
        wan.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
