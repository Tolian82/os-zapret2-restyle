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


class LockedWanRegression(unittest.TestCase):
    def test_original_fd4_wan_read_does_not_reopen_config_lock(self):
        import fcntl
        import tempfile
        import auto_detect_original_lock_handoff as handoff

        def xml(value):
            return ("<opnsense><OPNsense><Zapret><general><waninterface>" + value +
                    "</waninterface></general></Zapret></OPNsense></opnsense>").encode()

        real_run = subprocess.run
        original_assert = handoff.assert_inherited_config_fd
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config.xml"
            config.write_bytes(xml("lo0"))
            config.chmod(0o600)
            common = root / "common.sh"
            common.write_text('common_error() { echo "refused" >&2; }\n')
            plugin = root / "pluginctl"
            plugin.write_text('#!/bin/sh\ncase "$1" in\n'
                ' -4) printf "{}\\n" ;;\n'
                ' -g) [ "$2" = interfaces.opt0.if ] || exit 2; printf "%s\\n" "$ASSIGNED" ;;\n'
                ' *) exit 2 ;;\nesac\n')
            jq = root / "jq"
            jq.write_text('#!/bin/sh\ncat >/dev/null\nprintf "%s\\n" "$IPV4"\n')
            plugin.chmod(0o700)
            jq.chmod(0o700)
            source = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend/config.sh"
            resolver = root / "config.sh"
            resolver.write_text(source.read_text().replace("/usr/local/sbin/pluginctl", str(plugin))
                .replace("/usr/local/bin/jq", str(jq)))
            calls = []
            state = {"devices": "lo0", "ipv4": "", "assigned": "", "mutate": False}
            with config.open("r+b") as held:
                fd = held.fileno()
                fcntl.flock(fd, fcntl.LOCK_EX)
                os.lseek(fd, 2, os.SEEK_SET)

                def attest(number, path, *, owner_uid):
                    self.assertIsNone(owner_uid)
                    self.assertEqual(number, fd)
                    original_assert(number, path, owner_uid=os.geteuid())

                def run(argv, **kwargs):
                    if argv[0] == gate._WAN:
                        # Same blocking flock as the original independent PHP
                        # Config::lock, with a short disposable fixture deadline.
                        return real_run([sys.executable, "-c",
                            'import fcntl,sys; f=open(sys.argv[1],"r+b"); '
                            'fcntl.flock(f,fcntl.LOCK_EX); print("wan-ready")', str(config)],
                            timeout=0.15, capture_output=True)
                    self.assertEqual(argv[:2], ("/bin/sh", "-c"))
                    self.assertEqual(argv[3], "s10-locked-wan")
                    self.assertEqual(kwargs["pass_fds"], ())
                    self.assertTrue(kwargs["close_fds"])
                    self.assertIn("/sbin", kwargs["env"]["PATH"].split(":"))
                    self.assertNotIn("wan_preflight.php", argv[2])
                    calls.append(argv[4])
                    shell = ('ifconfig() { case " $DEVICES " in *" $1 "*) return 0 ;; esac; return 1; }; '
                        + argv[2].replace("/usr/local/opnsense/scripts/OPNsense/Zapret/backend/common.sh", str(common))
                        .replace("/usr/local/opnsense/scripts/OPNsense/Zapret/backend/config.sh", str(resolver)))
                    reply = real_run(("/bin/sh", "-c", shell, argv[3], argv[4]),
                        **{**kwargs, "env": {**kwargs["env"], "DEVICES": state["devices"],
                            "IPV4": state["ipv4"], "ASSIGNED": state["assigned"]}})
                    if state["mutate"]:
                        os.pwrite(fd, xml("tun"), 0)
                    return reply

                with patch.object(handoff, "CONFIG_PATH", config), \
                     patch.object(handoff, "assert_inherited_config_fd", side_effect=attest), \
                     patch.object(gate, "require_lifecycle_lock"), \
                     patch.object(gate.subprocess, "run", side_effect=run):
                    with self.assertRaises(gate.SavedWanPreimageRefused):
                        gate._native_wan()
                    for logical, devices, ipv4, assigned, expected in (
                        ("lo0", "lo0", "", "", "lo0"),
                        ("tun42", "tun42", "", "", "tun42"),
                        ("wan", "vtnet1", "vtnet1", "", "vtnet1"),
                        ("opt0", "tun42", "", "tun42", "tun42"),
                        ("opt0", "vtnet1", "", "tun42", None),
                        ("opt0", "tun42", "", "tun42;bad", None),
                    ):
                        with self.subTest(logical=logical, expected=expected):
                            config.write_bytes(xml(logical))
                            state.update(devices=devices, ipv4=ipv4, assigned=assigned)
                            if expected is None:
                                with self.assertRaises(gate.SavedWanPreimageRefused):
                                    gate._native_wan_locked(fd)
                            else:
                                self.assertEqual(gate._native_wan_locked(fd), expected)
                            self.assertEqual(calls[-1], logical)
                            self.assertEqual(os.lseek(fd, 0, os.SEEK_CUR), 2)
                    count = len(calls)
                    for raw in (xml(""), xml("lo0;bad"), xml("<x>lo0</x>"),
                                xml("lo0</waninterface><waninterface>tun42"),
                                b"<!DOCTYPE opnsense><opnsense/>", b"<broken"):
                        config.write_bytes(raw)
                        with self.assertRaises(gate.SavedWanPreimageRefused):
                            gate._native_wan_locked(fd)
                    self.assertEqual(len(calls), count)
                    config.write_bytes(xml("lo0"))
                    state.update(devices="lo0", ipv4="", assigned="", mutate=True)
                    with self.assertRaises(gate.SavedWanPreimageRefused):
                        gate._native_wan_locked(fd)
                    self.assertEqual(os.lseek(fd, 0, os.SEEK_CUR), 2)
                    state["mutate"] = False
                    config.write_bytes(xml("lo0"))
                    count = len(calls)
                    fcntl.flock(fd, fcntl.LOCK_UN)
                    with self.assertRaises(handoff.OriginalLockRefused):
                        gate._native_wan_locked(fd)
                    self.assertEqual(len(calls), count)

    def test_first_enabled_physical_boundaries_reuse_locked_wan(self):
        from contextlib import ExitStack
        import neutral_schema3_quiescent_preimage as quiescent
        import neutral_root_stage as roots
        import auto_detect_original_lock_handoff as handoff

        op, base, candidate, root = "a" * 32, "b" * 64, "c" * 64, "d" * 64
        record = {"phase": "activating", "detail": {"id": op, "page": "strategies",
            "base": base, "candidate": candidate, "changed_fields": ["hostlist.mode"]},
            "manifest": {"schema": 1, "root_sha256": root}}
        preimage = quiescent.QuiescentPreimage(op, root, None, None, base, candidate,
            "tun0", "first-install-empty", "native-kernel-absent", "no-prior-data")
        store = Mock(read=Mock(return_value=record))
        activated = {**record, "phase": "activated", "first_running_sha256": "e" * 64}
        receipt = Mock(running=object(), pretraffic_sha256=None,
                       kernel_state="native-managed-kernel-staged")

        def activate(*args, **kwargs):
            store.read.return_value = activated
            return activated, receipt

        store._record_native_bound_activated.side_effect = activate
        with ExitStack() as stack:
            stack.enter_context(patch.object(sys, "platform", "freebsd15"))
            stack.enter_context(patch.object(os, "geteuid", return_value=0))
            stack.enter_context(patch.object(quiescent, "require_lifecycle_lock"))
            stack.enter_context(patch.object(handoff, "assert_inherited_config_fd"))
            stack.enter_context(patch.object(quiescent, "SharedApplyOperation", return_value=store))
            stack.enter_context(patch.object(roots, "_verify_original_pinned_root",
                return_value=b'{"service":{"enabled":true,"target_mode":"list"}}'))
            stack.enter_context(patch.object(quiescent, "_first_inert_recovery_layout",
                return_value=(None, None, "native-kernel-absent")))
            legacy = stack.enter_context(patch.object(gate, "_native_wan",
                side_effect=AssertionError("independent Config reader under FD4")))
            locked = stack.enter_context(patch.object(gate, "_native_wan_locked", return_value="tun0"))
            actuator = stack.enter_context(patch.object(quiescent, "_run_bound_restore_joined",
                return_value=Mock(returncode=0, stdout=b"first-enabled-physical=activated\n")))
            quiescent.native_guard_first_enabled_shell_locked(op, candidate, "tun0", config_fd=4)
            self.assertEqual([call.args for call in locked.call_args_list], [(4,), (4,)])
            locked.reset_mock()
            locked.side_effect = ("tun0", "tun1")
            with self.assertRaises(quiescent.QuiescentPreimageRefused):
                quiescent.native_guard_first_enabled_shell_locked(op, candidate, "tun0", config_fd=4)
            locked.reset_mock()
            locked.side_effect = ("tun0", "tun1")
            with self.assertRaises(quiescent.QuiescentPreimageRefused):
                quiescent.native_install_first_enabled_bound_locked(record, preimage=preimage,
                    config_fd=4, config_digest=base)
            actuator.assert_not_called()
            locked.reset_mock()
            locked.side_effect = None
            self.assertEqual(quiescent.native_install_first_enabled_bound_locked(record,
                preimage=preimage, config_fd=4, config_digest=base), (activated, receipt))
            self.assertEqual([call.args for call in locked.call_args_list], [(4,), (4,), (4,)])
            actuator.assert_called_once()
            self.assertEqual(actuator.call_args.kwargs["pass_fds"], (9, 4))
            legacy.assert_not_called()


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

    def test_cold_config_classification_does_not_authorize_recovery(self):
        from copy import deepcopy
        from json import dumps
        record = deepcopy(self.pinned)
        record["phase"] = "activated"
        detail = record["detail"]
        base, candidate = detail["base"], detail["candidate"]
        self.assertNotEqual(base, candidate)
        row = dict(result="read-only-ordinary-config-classification",
            image="base-image", base=base, candidate=candidate, snapshot=base,
            enabled="1", commit_authorized=False, restore_authorized=False,
            save_attested=False, runtime_attested=False)
        self.assertEqual(gate._qualify_ordinary_cold_config(row, record),
                         ("base-image", base, "1"))
        candidate_row = dict(row, image="candidate-image", snapshot=candidate)
        self.assertEqual(gate._qualify_ordinary_cold_config(candidate_row, record),
                         ("candidate-image", candidate, "1"))
        for phase in ("config-saved", "epoch-finalizing"):
            with self.assertRaises(gate.SavedWanPreimageRefused):
                gate._qualify_ordinary_cold_config(row, dict(record, phase=phase))
            gate._qualify_ordinary_cold_config(candidate_row, dict(record, phase=phase))
        with self.assertRaises(gate.SavedWanPreimageRefused):
            gate._qualify_ordinary_cold_config(candidate_row, dict(record, phase="activating"))
        with self.assertRaises(gate.SavedWanPreimageRefused):
            gate._qualify_ordinary_cold_config(dict(row, save_attested=True), record)
        with patch.object(sys, "platform", "freebsd15"), \
                patch.object(os, "geteuid", return_value=0), \
                patch.object(gate, "require_lifecycle_lock"), \
                patch.object(gate, "SharedApplyOperation",
                             return_value=Mock(read=Mock(return_value=record))) as store, \
                patch("neutral_root_stage.verify_original_operation_pins") as pins, \
                patch.object(gate, "_native_call",
                             return_value=(dumps(row) + "\n").encode()) as native:
            self.assertEqual(gate.attest_ordinary_cold_config_under_fd9(record),
                             ("base-image", base, "1"))
            self.assertEqual(native.call_count, 2)
            self.assertEqual(pins.call_count, 4)
            native.side_effect = [(dumps(row) + "\n").encode(),
                                  (dumps(candidate_row) + "\n").encode()]
            with self.assertRaises(gate.SavedWanPreimageRefused):
                gate.attest_ordinary_cold_config_under_fd9(record)
            store.return_value._persist_record.assert_not_called()

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
