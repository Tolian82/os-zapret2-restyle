#!/usr/bin/env python3
"""Real bound schema3 root + stopped/cold source contracts, no native install."""
from contextlib import ExitStack
from dataclasses import replace
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"))
import neutral_schema3_quiescent_preimage as gate
from shared_apply_operation import SharedOperationError
from voice_firewall_transaction import VoiceFirewallError

spec = importlib.util.spec_from_file_location(
    "original_full_prior", ROOT / "scripts/test-tz6v5-s10b2b2b3b2a-original-prior-full-tree-pid.py")
if spec is None or spec.loader is None:
    raise RuntimeError("ORIGINAL_PRIOR_FIXTURE_REQUIRED")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class OriginalQuiescentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        m.FullPreviousOwnerReadOnly.setUpClass()

    @classmethod
    def tearDownClass(cls):
        m.FullPreviousOwnerReadOnly.tearDownClass()

    def setUp(self):
        self.fixture = m.FullPreviousOwnerReadOnly("runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.f = self.fixture.f.f.f
        self.active = self.fixture.active
        self.root = Path(self.f.tmp.name)
        self.backups = self.root / "backups"
        self.producer = self.root / "producer"
        self.epochs = self.root / "epochs"
        self.pidfiles = (self.fixture.pidfile, self.fixture.monitorfile,
                         self.root / "daemon.pid")
        self.saved = replace(self.fixture.saved, previous_state="stopped")
        self.config = self.fixture.f.config(self.f.generation, self.f.detail["page"])
        self.runner = Mock(return_value=Mock(
            returncode=0, stderr="", stdout="0 [kernel]\n1 /sbin/init\n123 /bin/sh\n"))
        self.adapter = Mock(spec=["rule_base", "rule_max", "list_rules", "get_table"])
        self.adapter.rule_base = 19000
        self.adapter.rule_max = 19099
        self.adapter.list_rules.return_value = {}
        self.adapter.get_table.return_value = None

    def call(self):
        return gate._attest_quiescent(
            generation=self.f.generation, native=self.f.native,
            effective=self.f.effective, enabled=True, parent=self.f.parent,
            journal_root=self.f.journal_root, owner_uid=os.geteuid(),
            active=self.active, backups=self.backups, producer=self.producer,
            epochs=self.epochs, pidfiles=self.pidfiles, runner=self.runner)

    def native_seams(self, stack, *, cold_kernel=False):
        stack.enter_context(patch.object(gate, "_native_preflight", return_value=self.config))
        stack.enter_context(patch.object(gate, "_native_wan", return_value="tun0"))
        stack.enter_context(patch.object(gate, "_first_learning_candidate_wan", return_value="tun0"))
        stack.enter_context(patch.object(gate, "_attest_saved_wan", return_value=self.saved))
        stack.enter_context(patch.object(gate, "_ipfw_kernel_confirmed_absent",
                                         return_value=cold_kernel))
        stack.enter_context(patch.object(gate, "FreeBSDIPFWAdapter",
                                         return_value=self.adapter))
        return stack.enter_context(patch.object(gate, "_native_call",
                                  return_value=b"auto-detect-retire=ready\n"))

    def cold(self):
        shutil.rmtree(self.active)
        shutil.rmtree(self.fixture.old_work)
        record = self.f.original.read()
        record.pop("previous")
        self.f.original._persist_record(record)

    def lock(self):
        self.producer.mkdir(mode=0o700)
        lock = self.producer / "worker.lock"
        lock.touch(mode=0o600)
        if os.geteuid() == 0:
            os.chown(lock, 0, 0)
        lock.chmod(0o600)

    def test_first_learning_wan_uses_sealed_candidate_before_config_save(self):
        import hashlib
        import subprocess

        op = "a" * 32
        record = {"phase": "prepared", "detail": {"id": op,
                    "base": "b" * 64, "candidate": "c" * 64},
                  "manifest": {"schema": 2}}
        raw = (b"<opnsense><OPNsense><Zapret><general><enabled>1</enabled>"
               b"<waninterface>opt7</waninterface></general><hostlist><mode>auto</mode>"
               b"</hostlist></Zapret></OPNsense></opnsense>")
        seal = {"sha256": {"candidate.xml": hashlib.sha256(raw).hexdigest()}}
        with ExitStack() as stack:
            stack.enter_context(patch.object(gate, "require_lifecycle_lock"))
            lock = stack.enter_context(patch("auto_detect_original_lock_handoff.assert_inherited_config_fd"))
            seal_read = stack.enter_context(patch("shared_apply_seal.verify_seal", return_value=seal))
            content = stack.enter_context(patch("auto_detect_owner._secure_bytes", return_value=raw))
            run = stack.enter_context(patch.object(gate.subprocess, "run",
                return_value=subprocess.CompletedProcess([], 0, b"tun7\n", b"")))
            def call(fd=None, owner=record):
                return gate._first_learning_candidate_wan(owner, parent=self.root,
                    owner_uid=os.geteuid(), config_fd=fd)
            self.assertEqual(call(), "tun7")
            lock.assert_not_called()
            self.assertEqual(run.call_args.args[0][-1], "opt7")
            self.assertEqual(run.call_args.kwargs["pass_fds"], ())
            self.assertEqual(content.call_args.args[0], self.root / op / "candidate.xml")
            self.assertEqual(call(4, {**record, "phase": "activating"}), "tun7")
            self.assertEqual(lock.call_count, 2)
            run.reset_mock()
            for invalid in ({**record, "previous": {}}, {**record, "found": {}},
                            {**record, "manifest": {"schema": 1}}):
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    call(owner=invalid)
            content.return_value = raw.replace(b"opt7", b"opt8")
            with self.assertRaises(gate.QuiescentPreimageRefused):
                call()
            run.assert_not_called()
            content.return_value = raw
            seal_read.side_effect = [seal, {"sha256": {"candidate.xml": "0" * 64}}]
            with self.assertRaises(gate.QuiescentPreimageRefused):
                call()
            seal_read.side_effect = None
            run.return_value = subprocess.CompletedProcess([], 0, b"wan-invalid\n", b"")
            with self.assertRaises(gate.QuiescentPreimageRefused):
                call()

    def test_first_learning_handoff_requires_inherited_queue_and_both_pins(self):
        import io
        import json
        from dataclasses import asdict
        from shared_apply_operation import _config_save_witness

        op, base, candidate, root = "a" * 32, "b" * 64, "c" * 64, "d" * 64
        detail = {"id": op, "page": "strategies", "base": base, "candidate": candidate,
                  "changed_fields": ["general.enabled"]}
        record = {"phase": "activating", "detail": detail,
                  "manifest": {"schema": 2, "root_sha256": root}}
        witness = _config_save_witness(detail, "e" * 64)
        preimage = gate.QuiescentPreimage(op, root, None, None, base, candidate,
            "tun0", "first-install-empty", "native-kernel-absent", "no-prior-data")
        wire = (json.dumps(asdict(preimage), sort_keys=True,
            separators=(",", ":")) + "\n").encode()
        store = Mock(read=Mock(return_value=record))
        running = object()
        receipt = gate.StagedBoundRuntimeReceipt(op, root, base, "f" * 64,
            None, running, "native-managed-kernel-staged", base, "2" * 64)
        activated = {**record, "phase": "activated", "first_running_sha256": "1" * 64,
                     "first_pretraffic_sha256": "2" * 64}
        observed = [activated, receipt]

        def activate(*args, **kwargs):
            self.assertEqual(args, (record,))
            self.assertEqual(kwargs, {"preimage": preimage, "config_digest": base,
                                      "config_fd": 4, "queue_fd": 3})
            store.read.return_value = observed[0]
            return tuple(observed)

        with ExitStack() as stack:
            stack.enter_context(patch.object(sys, "platform", "freebsd15"))
            stack.enter_context(patch.object(gate.os, "geteuid", return_value=0))
            stack.enter_context(patch.object(gate, "require_lifecycle_lock"))
            stack.enter_context(patch("auto_detect_original_lock_handoff.assert_inherited_config_fd"))
            stack.enter_context(patch.object(gate, "SharedApplyOperation", return_value=store))
            stack.enter_context(patch("shared_apply_seal.verify_seal",
                return_value={"sha256": {"plan.json": "e" * 64}}))
            match = stack.enter_context(patch("shared_apply_operation._first_running_pin_matches",
                side_effect=lambda rec, proc, fd, *, pretraffic_sha256:
                    rec["first_pretraffic_sha256"] == pretraffic_sha256))
            install = stack.enter_context(patch.object(
                gate, "native_install_first_enabled_bound_locked", side_effect=activate))
            def call(fd=3):
                store.read.return_value = record
                return gate.native_write_first_enabled_handoff_locked(
                    op, witness, io.BytesIO(wire), config_fd=4, queue_fd=fd)
            for fd in (None, 4, 9, True, -1):
                with self.subTest(fd=fd), self.assertRaises(gate.QuiescentPreimageRefused):
                    call(fd)
            install.assert_not_called()
            self.assertEqual(call(), {"result": "first-enabled-activated", "id": op})
            match.assert_called_once_with(activated, running, 4, pretraffic_sha256="2" * 64)
            for invalid in ({k:v for k,v in activated.items() if k != "first_pretraffic_sha256"},
                            {**activated, "first_pretraffic_sha256": "3" * 64}):
                observed[0] = invalid
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    call()
            observed[:] = [activated, replace(receipt, pretraffic_sha256=None)]
            with self.assertRaises(gate.QuiescentPreimageRefused):
                call()

    def test_first_enabled_handoff_retains_running_pin_and_rejects_replaced_owner(self):
        import io
        import json
        from dataclasses import asdict
        from shared_apply_operation import _config_save_witness

        op, base, candidate, root = "a" * 32, "b" * 64, "c" * 64, "d" * 64
        detail = {"id": op, "page": "strategies", "base": base, "candidate": candidate,
                  "changed_fields": ["general.enabled"]}
        record = {"phase": "activating", "detail": detail,
                  "manifest": {"schema": 1, "root_sha256": root}}
        witness = _config_save_witness(detail, "e" * 64)
        preimage = gate.QuiescentPreimage(op, root, None, None, base, candidate,
            "tun0", "first-install-empty", "native-kernel-absent", "no-prior-data")
        wire = (json.dumps(asdict(preimage), sort_keys=True,
            separators=(",", ":")) + "\n").encode()
        store = Mock(read=Mock(return_value=record))
        running = object()
        receipt = gate.StagedBoundRuntimeReceipt(op, root, base, "f" * 64,
            None, running, "native-managed-kernel-staged", base)

        def activate(*args, **kwargs):
            self.assertEqual(kwargs["preimage"], preimage)
            self.assertEqual(kwargs["config_digest"], base)
            result = {**record, "phase": "activated", "first_running_sha256": "1" * 64}
            store.read.return_value = result
            return result, receipt

        with ExitStack() as stack:
            stack.enter_context(patch.object(sys, "platform", "freebsd15"))
            stack.enter_context(patch.object(gate.os, "geteuid", return_value=0))
            stack.enter_context(patch.object(gate, "require_lifecycle_lock"))
            stack.enter_context(patch("auto_detect_original_lock_handoff.assert_inherited_config_fd"))
            stack.enter_context(patch.object(gate, "SharedApplyOperation", return_value=store))
            stack.enter_context(patch("shared_apply_seal.verify_seal",
                return_value={"sha256": {"plan.json": "e" * 64}}))
            match = stack.enter_context(patch("shared_apply_operation._first_running_pin_matches",
                return_value=True))
            install = stack.enter_context(patch.object(
                gate, "native_install_first_enabled_bound_locked", side_effect=activate))
            def call(payload=wire, digest=witness):
                return gate.native_write_first_enabled_handoff_locked(
                    op, digest, io.BytesIO(payload), config_fd=4)
            self.assertEqual(call(), {"result": "first-enabled-activated", "id": op})
            install.assert_called_once()
            store.read.return_value = record
            install.reset_mock()
            for bad in (b"{}\n", b" " + wire, wire + b"\n",
                        wire.replace(b":", b": ", 1)):
                with self.assertRaises((gate.QuiescentPreimageRefused, ValueError)):
                    call(payload=bad)
            with self.assertRaises(gate.QuiescentPreimageRefused):
                call(digest="0" * 64)
            install.assert_not_called()
            match.return_value = False
            with self.assertRaises(gate.QuiescentPreimageRefused):
                call()


    def test_original_first_disabled_locked_wire_refuses_foreign_and_requires_activated(self):
        import io
        import json
        from dataclasses import asdict
        from shared_apply_operation import _config_save_witness

        op, base, candidate, root = "a" * 32, "b" * 64, "c" * 64, "d" * 64
        detail = {"id": op, "page": "strategies", "base": base, "candidate": candidate,
                  "changed_fields": ["hostlist.youtubedomains"]}
        record = {"phase": "activating", "detail": detail,
                  "manifest": {"schema": 1, "root_sha256": root}}
        witness = _config_save_witness(detail, "e" * 64)
        preimage = gate.QuiescentPreimage(op, root, None, None, base, candidate,
            None, "first-install-empty", "native-kernel-absent", "no-prior-data")
        wire = (json.dumps(asdict(preimage), sort_keys=True,
            separators=(",", ":")) + "\n").encode()
        store = Mock(read=Mock(return_value=record))
        with ExitStack() as stack:
            stack.enter_context(patch("sys.platform", "freebsd15"))
            stack.enter_context(patch("os.geteuid", return_value=0))
            stack.enter_context(patch.object(gate, "require_lifecycle_lock"))
            stack.enter_context(patch("auto_detect_original_lock_handoff.assert_inherited_config_fd"))
            stack.enter_context(patch.object(gate, "SharedApplyOperation", return_value=store))
            stack.enter_context(patch("shared_apply_seal.verify_seal",
                return_value={"sha256": {"plan.json": "e" * 64}}))
            receipt = gate.StagedBoundRuntimeReceipt(op, root, base, "f" * 64,
                None, None, "native-managed-kernel-empty", base)
            def installed(*args, **kw):
                self.assertEqual((args[0], kw["preimage"], kw["config_digest"]),
                                 (record, preimage, base))
                installed_record = {**record, "phase": "activated"}
                store.read.return_value = installed_record
                return installed_record, receipt
            activate = stack.enter_context(patch.object(
                gate, "native_install_first_disabled_bound_locked", side_effect=installed))
            def finish(data=wire, digest=witness):
                return gate.native_write_first_disabled_handoff_locked(
                    op, digest, io.BytesIO(data), config_fd=4)
            self.assertEqual(finish(), {"result": "first-disabled-activated", "id": op})
            activate.assert_called_once()
            activate.reset_mock()
            store.read.return_value = record
            for invalid in (b"{}\n", b" " + wire, wire + b"\n", wire.replace(b":", b": ", 1)):
                with self.assertRaises((gate.QuiescentPreimageRefused, ValueError)):
                    finish(invalid)
            with self.assertRaises(gate.QuiescentPreimageRefused):
                finish(digest="0" * 64)
            activate.assert_not_called()


    def test_first_learning_layout_uses_the_original_pretraffic_owner_receipt(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            parent = Path(tmp)
            op, base, candidate = "a" * 32, "b" * 64, "c" * 64
            work = parent / "work" / op
            release = work / "release"
            release.mkdir(parents=True)
            active = parent / "runtime-v2"
            record = {"phase": "activating", "detail": {
                "id": op, "base": base, "candidate": candidate}, "manifest": {"schema": 2}}
            store = Mock(read=Mock(return_value=record))
            producer = object()
            for name, value in (("WORK", work.parent), ("COMMON_ACTIVE", active),
                                ("EPOCH_ROOT", parent / "epochs")):
                stack.enter_context(patch.object(gate, name, value))
            stack.enter_context(patch("sys.platform", "freebsd15"))
            stack.enter_context(patch("os.geteuid", return_value=0))
            stack.enter_context(patch.object(gate, "require_lifecycle_lock"))
            stack.enter_context(patch("voice_ipfw_adapter.require_lifecycle_lock"))
            stack.enter_context(patch("auto_detect_original_lock_handoff.assert_inherited_config_fd"))
            stack.enter_context(patch("shared_apply_operation.SharedApplyOperation", return_value=store))
            stack.enter_context(patch("shared_apply_seal._stat", side_effect=lambda path, *_a, **_k: path.lstat()))
            stack.enter_context(patch("shared_apply_seal.WORK", work.parent))
            stack.enter_context(patch("shared_apply_seal.verify_seal", return_value={"sha256": {"release": "tree"}}))
            stack.enter_context(patch("neutral_root_stage.verify_original_operation_pins"))
            stack.enter_context(patch("neutral_root_stage._original_plan_matches", return_value=True))
            stack.enter_context(patch("neutral_root_stage._verify_original_pinned_root",
                                      return_value=b'{"service":{"enabled":true,"target_mode":"auto"}}'))
            stack.enter_context(patch("auto_detect_post_drop._learning_release_sources",
                                      return_value=(work, candidate, ())))
            stack.enter_context(patch("auto_detect_post_drop._qualified_learning_sources",
                                      return_value=(op, ())))
            stack.enter_context(patch("auto_detect_post_drop._capture", return_value=producer))
            stack.enter_context(patch.object(gate, "_zero_processes"))
            stack.enter_context(patch.object(gate, "_first_inert_kernel_state", return_value="empty"))
            self.assertEqual(gate._first_inert_recovery_layout(record, config_fd=4, config_digest=base,
                queue_fd=3, store=store, first_learning_launch=True), (None, None, "empty", producer))

    def test_first_disabled_install_normalizes_only_the_exact_empty_tree(self):
        import json
        import subprocess
        import tempfile

        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryFile() as config, ExitStack() as stack:
            base = Path(tmp)
            op = "a" * 32
            work = base / "work" / op
            release = work / "release"
            release.mkdir(parents=True)
            (release / "item").write_bytes(b"sealed")
            active = base / "runtime-v2"
            active.mkdir()
            record = {"phase": "activating", "detail": {"id": op, "base": "b" * 64,
                "candidate": "c" * 64}, "manifest": {"schema": 1, "root_sha256": "d" * 64}}
            preimage = gate.QuiescentPreimage(op, "d" * 64, None, None,
                "b" * 64, "c" * 64, None, "first-install-empty",
                "native-kernel-absent", "no-prior-data")
            store = Mock(read=Mock(return_value=record))
            receipt = object()
            for key, value in (("WORK", work.parent), ("COMMON_ACTIVE", active)):
                stack.enter_context(patch.object(gate, key, value))
            stack.enter_context(patch("sys.platform", "freebsd15"))
            stack.enter_context(patch("os.geteuid", return_value=0))
            stack.enter_context(patch.object(gate, "require_lifecycle_lock"))
            stack.enter_context(patch("auto_detect_original_lock_handoff.assert_inherited_config_fd"))
            stack.enter_context(patch.object(gate, "SharedApplyOperation", return_value=store))
            stack.enter_context(patch("shared_apply_seal._stat",
                side_effect=lambda path, *args, **kw: path.lstat()))
            root = stack.enter_context(patch("neutral_root_stage._verify_original_pinned_root",
                return_value=json.dumps({"service": {"enabled": False}}).encode()))

            def layout(*args, **kw):
                live = None
                if active.exists():
                    info = active.stat()
                    live = ("candidate" if (active / "item").exists() else "empty",
                            info.st_dev, info.st_ino)
                return live, None, preimage.kernel_state

            stack.enter_context(patch.object(gate, "_first_inert_recovery_layout", side_effect=layout))

            def install(command, **kw):
                self.assertEqual(command[-4:], (str(release), str(active),
                    str(base / "runtime-v2-backups"), op))
                self.assertEqual(kw["pass_fds"], (9, config.fileno()))
                self.assertFalse(active.exists())
                shutil.copytree(release, active)
                return subprocess.CompletedProcess(command, 0, b"\n", b"")

            joined = stack.enter_context(patch.object(gate, "_run_bound_restore_joined",
                side_effect=install))

            def activate(current, **kw):
                self.assertEqual(kw["preimage"], preimage)
                result = {**current, "phase": "activated"}
                store.read.return_value = result
                return result, receipt

            store._record_native_bound_activated.side_effect = activate

            def run():
                return gate.native_install_first_disabled_bound_locked(record,
                    preimage=preimage, config_fd=config.fileno(), config_digest="b" * 64)

            root.return_value = b'{"service":{"enabled":true}}'
            with self.assertRaises(gate.QuiescentPreimageRefused):
                run()
            joined.assert_not_called()
            root.return_value = b'{"service":{"enabled":false}}'
            real_rmdir = os.rmdir

            def race(path):
                (active / "foreign").write_bytes(b"retain")
                return real_rmdir(path)

            with patch("os.rmdir", side_effect=race):
                with self.assertRaises(OSError):
                    run()
            self.assertEqual((active / "foreign").read_bytes(), b"retain")
            joined.assert_not_called()
            (active / "foreign").unlink()
            self.assertEqual(run(), ({**record, "phase": "activated"}, receipt))
            self.assertEqual((active / "item").read_bytes(), b"sealed")
            joined.assert_called_once()

    def test_first_activating_pristine_restore_requires_exact_empty_state(self):
        import subprocess
        from shared_apply_seal import verify_seal, _release_hash, _stat, SharedBundleError

        self.cold()
        original = self.f.original.read()
        record = {**original, "phase": "activating",
                  "manifest": {**original["manifest"], "schema": 1}}
        store = Mock(read=Mock(return_value=record))
        release = self.f.parent / record["detail"]["id"] / "release"
        stage = self.active.parent / f".{self.active.name}.stage.{record['detail']['id']}"
        backup = self.active.with_name("runtime-v2-backups")

        def advance(phase, expected, attest):
            self.assertEqual(expected, record)
            if not attest():
                raise gate.QuiescentPreimageRefused("drift")
            result = {**record, "phase": phase}
            store.read.return_value = result
            return result

        def remove(command, *, pass_fds, budget):
            self.assertEqual((pass_fds, budget), ((9, 4), 20))
            return subprocess.run(["/bin/sh", "-c", '. "$1"; atomic_remove_tree "$2"',
                "fixture", str(ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend/atomic.sh"),
                command[-1]], check=False)

        safe_empty = gate._safe_empty_directory
        store._advance_bound_ordinary.side_effect = advance
        with ExitStack() as stack:
            for key, value in (("WORK", self.f.parent), ("COMMON_ACTIVE", self.active),
                               ("PRODUCER_ROOT", self.producer), ("EPOCH_ROOT", self.epochs)):
                stack.enter_context(patch.object(gate, key, value))
            stack.enter_context(patch.object(gate, "require_lifecycle_lock"))
            stack.enter_context(patch("auto_detect_original_lock_handoff.assert_inherited_config_fd"))
            stack.enter_context(patch("neutral_root_stage.verify_original_operation_pins"))
            stack.enter_context(patch("neutral_root_stage._original_plan_matches", return_value=True))
            stack.enter_context(patch.object(gate, "inspect_inert_release", return_value="inactive"))
            uid = os.geteuid()
            stack.enter_context(patch("shared_apply_seal._stat", side_effect=
                lambda path, owner, **kw: _stat(path, uid, **kw)))
            stack.enter_context(patch("shared_apply_seal.verify_seal", side_effect=
                lambda path, **kw: verify_seal(path, owner=uid)))
            stack.enter_context(patch("shared_apply_seal._release_hash", side_effect=
                lambda path, owner: _release_hash(path, uid)))
            stack.enter_context(patch.object(gate, "_safe_empty_directory", side_effect=
                lambda path, owner: safe_empty(path, uid)))
            processes = stack.enter_context(patch.object(gate, "_zero_processes"))
            kernel = stack.enter_context(patch.object(gate, "_empty_kernel", return_value="empty"))
            removal = stack.enter_context(patch.object(gate, "_run_bound_restore_joined", side_effect=remove))

            def recover(**kw):
                options = dict(config_fd=4, config_digest=record["detail"]["base"], queue_fd=None)
                options.update(kw)
                return gate._finish_first_pristine_locked(store, record, **options)

            with self.assertRaises(gate.QuiescentPreimageRefused):
                recover(config_digest="0" * 64)
            self.active.mkdir()
            (self.active / "foreign").touch()
            with self.assertRaises((gate.QuiescentPreimageRefused, SharedBundleError)):
                recover()
            shutil.rmtree(self.active)
            processes.side_effect = gate.QuiescentPreimageRefused("live process")
            with self.assertRaises(gate.QuiescentPreimageRefused):
                recover()
            processes.side_effect = None
            kernel.side_effect = ("empty", "absent")
            with self.assertRaises(gate.QuiescentPreimageRefused):
                recover()
            kernel.side_effect = None
            shutil.copytree(release, self.active)
            shutil.copytree(release, stage)
            with self.assertRaises(gate.QuiescentPreimageRefused):
                recover()
            shutil.rmtree(stage)
            backup.mkdir()
            (backup / "foreign").mkdir()
            with self.assertRaises(gate.QuiescentPreimageRefused):
                recover()
            shutil.rmtree(backup)
            removal.assert_not_called()
            self.assertEqual(store.read(), record)
            self.assertEqual(recover(), {**record, "phase": "restored"})
            self.assertFalse(self.active.exists())

            store.read.return_value = record
            self.active.mkdir()
            original_inode = self.active.stat().st_ino
            shutil.copytree(release, stage)
            self.assertEqual(recover(), {**record, "phase": "restored"})
            self.assertFalse(stage.exists())
            self.assertEqual(self.active.stat().st_ino, original_inode)

            store.read.return_value = record
            self.assertEqual(recover(), {**record, "phase": "restored"})
            self.assertEqual(removal.call_count, 2)

    def test_first_inert_staged_kernel_uses_original_rollback(self):
        import json
        from copy import deepcopy
        from voice_firewall_transaction import verify_prior_state

        record = self.f.original.read()
        release = self.f.parent / record["detail"]["id"] / "release"
        live = ("candidate", 1, 2)
        staged = (live, None, "native-managed-kernel-staged")
        empty = {"rule_base": 19000, "rule_max": 19099, "rules": {}, "tables": {}}
        table = "zapret2_voice_telegram"
        desired = {**empty, "rules": {19001: ["divert", "989"]},
                   "tables": {table: ["91.108.13.10"]}}
        rules = {**deepcopy(desired["rules"]), 20000: ["unrelated"]}
        tables = {**deepcopy(desired["tables"]), table + "_stage": []}
        writes = []
        adapter = Mock()
        adapter.rule_base = 19000
        adapter.rule_max = 19099
        adapter.list_rules.side_effect = lambda a, b: {
            k: v for k, v in rules.items() if a <= k <= b}
        adapter.get_table.side_effect = tables.get

        def delete(number):
            writes.append(number)
            del rules[number]

        def destroy(name):
            writes.append(name)
            del tables[name]

        adapter.delete_rule.side_effect = delete
        adapter.destroy_table.side_effect = destroy

        def empty_kernel(_):
            verify_prior_state(adapter, empty, desired)
            return "native-managed-kernel-empty"

        with ExitStack() as stack:
            stack.enter_context(patch.object(gate, "require_lifecycle_lock"))
            stack.enter_context(patch("auto_detect_original_lock_handoff.assert_inherited_config_fd"))
            root = stack.enter_context(patch("neutral_root_stage._verify_original_pinned_root",
                return_value=json.dumps({"service": {"enabled": True}}).encode()))
            stack.enter_context(patch.object(gate, "shared_release_manifest", return_value=desired))
            stack.enter_context(patch.object(gate, "_empty_kernel", side_effect=empty_kernel))
            native = stack.enter_context(patch.object(gate, "FreeBSDIPFWAdapter", return_value=adapter))

            def observe():
                return live, None, gate._first_inert_kernel_state(record, release, installed=True)

            self.assertEqual(observe(), staged)
            with self.assertRaises(VoiceFirewallError):
                gate._first_inert_kernel_state(record, release, installed=False)
            root.return_value = json.dumps({"service": {"enabled": False}}).encode()
            with self.assertRaises(gate.QuiescentPreimageRefused):
                observe()
            root.return_value = json.dumps({"service": {"enabled": True}}).encode()
            rules[19002] = ["foreign"]
            with self.assertRaises(VoiceFirewallError):
                observe()
            del rules[19002]
            del tables[table + "_stage"]
            with self.assertRaises(VoiceFirewallError):
                observe()
            tables[table + "_stage"] = []
            tables["zapret2_voice_discord"] = ["91.108.13.10"]
            with self.assertRaises(VoiceFirewallError):
                observe()
            del tables["zapret2_voice_discord"]
            with self.assertRaises(gate.QuiescentPreimageRefused):
                gate._rollback_first_inert_kernel(record, release, config_fd=4, first=staged,
                    observe=lambda: (("candidate", 1, 3), None, staged[2]))
            self.assertEqual(writes, [])
            self.assertEqual(gate._rollback_first_inert_kernel(record, release,
                config_fd=4, first=staged, observe=observe),
                (live, None, "native-managed-kernel-empty"))
            self.assertEqual(rules, {20000: ["unrelated"]})
            self.assertEqual(tables, {})
            self.assertEqual(writes, [19001, table, table + "_stage"])
            self.assertIn(unittest.mock.call(19000, 19099, allow_mutations=True),
                          native.call_args_list)

    def test_first_saved_disabled_checkpoint_retains_exact_observation(self):
        import tempfile

        record = {**self.f.original.read(), "phase": "activated"}
        store = Mock(read=Mock(return_value=record))
        observation = (("candidate", 1, 2), None, "native-managed-kernel-empty")
        def advance(phase, current, attest):
            self.assertEqual(store.read(), current)
            if not attest():
                raise gate.QuiescentPreimageRefused("drift")
            result = {**current, "phase": phase}
            store.read.return_value = result
            return result

        store._advance_bound_ordinary.side_effect = advance
        with tempfile.TemporaryFile() as config, ExitStack() as stack:
            stack.enter_context(patch.object(gate, "require_lifecycle_lock"))
            stack.enter_context(patch("auto_detect_original_lock_handoff.assert_inherited_config_fd"))
            layout = stack.enter_context(patch.object(gate, "_first_inert_recovery_layout",
                return_value=observation))
            def recover(current):
                return gate._finish_first_saved_locked(store, current,
                    config_fd=config.fileno(), config_digest=current["detail"]["candidate"])
            layout.side_effect = [observation] * 4 + [(None, None, "changed")]
            with self.assertRaises(gate.QuiescentPreimageRefused):
                recover(record)
            self.assertEqual(store.read(), {**record, "phase": "config-saved"})
            layout.side_effect = None
            self.assertEqual(recover(store.read()), {**record, "phase": "committed"})
            self.assertTrue(all(call.kwargs["saved"] for call in layout.call_args_list))

    def test_first_saved_running_checkpoint_orders_cleanup_and_refuses_drift(self):
        import tempfile
        record = {**self.f.original.read(), "phase": "activated",
                  "first_running_sha256": "a" * 64}
        store = Mock(read=Mock(return_value=record))
        live = ("candidate", 1, 2)
        staged = ("native-managed-kernel-staged", "a" * 64, (("stage", "table_stage", ()),))
        final = ("native-managed-kernel-final", "a" * 64, ())
        state = [staged]
        calls = []

        def advance(phase, current, attest):
            self.assertEqual(store.read(), current)
            if not attest():
                raise gate.QuiescentPreimageRefused("drift")
            result = {**current, "phase": phase}
            store.read.return_value = result
            calls.append(phase)
            return result

        def cleanup(*args):
            self.assertEqual(store.read()["phase"], "config-saved")
            calls.append("cleanup")
            state[0] = final

        store._advance_bound_ordinary.side_effect = advance
        with tempfile.TemporaryFile() as config, ExitStack() as stack:
            stack.enter_context(patch.object(gate, "require_lifecycle_lock"))
            stack.enter_context(patch("auto_detect_original_lock_handoff.assert_inherited_config_fd"))
            stack.enter_context(patch.object(gate, "_first_inert_recovery_layout",
                side_effect=lambda *args, **kw: (live, None, state[0])))
            stack.enter_context(patch.object(gate, "_first_inert_staged_manifests",
                return_value=({}, {})))
            stack.enter_context(patch.object(gate, "FreeBSDIPFWAdapter"))
            native = stack.enter_context(patch("voice_firewall_transaction.cleanup_committed",
                side_effect=VoiceFirewallError("uncertain cleanup")))

            def recover():
                current = store.read()
                return gate._finish_first_saved_locked(store, current,
                    config_fd=config.fileno(), config_digest=current["detail"]["candidate"])

            with self.assertRaises(VoiceFirewallError):
                recover()
            self.assertEqual(store.read()["phase"], "config-saved")
            self.assertEqual(calls, ["config-saved"])
            native.side_effect = cleanup
            self.assertEqual(recover()["phase"], "committed")
            self.assertEqual(calls, ["config-saved", "cleanup", "committed"])

    def test_first_running_base_proof_is_read_only_and_refuses_drift(self):
        import tempfile
        import json
        from hashlib import sha256

        record = {"phase": "activated", "detail": {"id": "a" * 32,
                   "base": "b" * 64, "candidate": "c" * 64},
                  "manifest": {"schema": 1}, "first_running_sha256": "d" * 64}
        store = Mock(read=Mock(return_value=record))
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            parent = Path(temp)
            work = parent / "work"
            release = work / record["detail"]["id"] / "release"
            release.mkdir(parents=True)
            active = parent / "runtime-v2"
            active.mkdir()
            (active / "dvtws.args").write_bytes(b"candidate")
            (release / "dvtws.args").write_bytes(b"candidate")
            digest = lambda path: sha256((path / "dvtws.args").read_bytes()).hexdigest()
            for key, value in (("WORK", work), ("COMMON_ACTIVE", active),
                               ("PRODUCER_ROOT", parent / "producer"), ("EPOCH_ROOT", parent / "epochs")):
                stack.enter_context(patch.object(gate, key, value))
            stack.enter_context(patch.object(gate, "require_lifecycle_lock"))
            stack.enter_context(patch("auto_detect_original_lock_handoff.assert_inherited_config_fd"))
            stack.enter_context(patch("neutral_root_stage.verify_original_operation_pins"))
            stack.enter_context(patch("neutral_root_stage._original_plan_matches", return_value=True))
            root = stack.enter_context(patch("neutral_root_stage._verify_original_pinned_root"))
            root.return_value = json.dumps({"service": {"enabled": True, "target_mode": "list"}})
            stack.enter_context(patch.object(gate, "inspect_inert_release", return_value="inactive"))
            stack.enter_context(patch("shared_apply_seal._stat", side_effect=lambda path, *a, **kw: path.lstat()))
            stack.enter_context(patch("shared_apply_seal.verify_seal", return_value={"sha256": {"release": digest(release)}}))
            stack.enter_context(patch("shared_apply_seal._release_hash", side_effect=lambda path, owner: digest(path)))
            zero = stack.enter_context(patch.object(gate, "_zero_processes"))
            cold = stack.enter_context(patch.object(gate, "_first_inert_kernel_state"))
            kernel = stack.enter_context(patch.object(gate, "_first_saved_running_kernel"))
            proof = ("native-managed-kernel-staged", record["first_running_sha256"], (("stage", "table_stage", ()),))
            kernel.return_value = proof

            def attest(current=record, digest=record["detail"]["base"]):
                store.read.return_value = current
                return gate._attest_first_running_base_locked(store, current, config_fd=4, config_digest=digest)

            self.assertEqual(attest(), (("candidate", active.stat().st_dev, active.stat().st_ino), None, proof))
            self.assertEqual(kernel.call_count, 2)
            for current, image in ((record, record["detail"]["candidate"]),
                    ({**record, "phase": "config-saved"}, record["detail"]["base"]),
                    ({k: v for k, v in record.items() if k != "first_running_sha256"}, record["detail"]["base"])):
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    attest(current, image)
            for enabled, mode in ((False, "list"), (True, "auto")):
                root.return_value = json.dumps({"service": {"enabled": enabled, "target_mode": mode}})
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    attest()
            root.return_value = json.dumps({"service": {"enabled": True, "target_mode": "all"}})
            kernel.side_effect = VoiceFirewallError("foreign kernel")
            with self.assertRaises(VoiceFirewallError):
                attest()
            kernel.side_effect = (proof, ("native-managed-kernel-final", record["first_running_sha256"], ()))
            with self.assertRaises(gate.QuiescentPreimageRefused):
                attest()
            kernel.side_effect = None
            (active / "dvtws.args").write_bytes(b"foreign")
            with self.assertRaises(gate.QuiescentPreimageRefused):
                attest()
            (active / "dvtws.args").write_bytes(b"candidate")
            self.assertEqual(attest()[2], proof)
            zero.assert_not_called()
            cold.assert_not_called()
            store._advance_bound_ordinary.assert_not_called()
            self.assertEqual(store.read(), record)
            self.assertEqual((active / "dvtws.args").read_bytes(), b"candidate")

    def test_first_running_base_recovery_joined_through_original_restored_wal(self):
        import json
        import subprocess
        import tempfile
        from copy import deepcopy
        from hashlib import sha256
        from shared_apply_operation import SharedApplyOperation, _config_observation_witness

        detail = {"id": "a" * 32, "page": "strategies", "base": "b" * 64,
                  "candidate": "c" * 64, "changed_fields": ["general.enabled"]}
        record = {"schema": 1, "phase": "activated", "detail": detail,
                  "manifest": {"schema": 1, "generation": detail["id"],
                      "root_sha256": "d" * 64, "seal_sha256": "e" * 64,
                      "candidate_sha256": detail["candidate"]},
                  "first_running_sha256": "f" * 64}
        plan = "1" * 64
        witness = _config_observation_witness(detail, plan, detail["base"])
        empty = {"rule_base": 19000, "rule_max": 19099, "rules": {}, "tables": {}}
        table = "zapret2_voice_telegram"
        uid = os.geteuid()
        for scenario in ("running", "already-stopped", "lost-receipt", "stop-refused", "empty-kernel", "lost-tree-receipt"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
                root = Path(temp)
                work = root / "work"
                release = work / detail["id"] / "release"
                release.mkdir(parents=True)
                (release / "dvtws.args").write_bytes(b"candidate\n")
                active = root / "runtime-v2"
                shutil.copytree(release, active)
                config = root / "config.xml"
                config.write_bytes(b"original Config bytes\n")
                pidfiles = tuple(root / name for name in ("child.pid", "monitor.pid", "daemon.pid"))
                running = scenario != "already-stopped"
                if running:
                    for path, pid in zip(pidfiles, (321, 654, 987)):
                        path.write_text(str(pid) + "\n")
                desired = deepcopy(empty)
                if scenario != "empty-kernel":
                    desired["rules"] = {19001: ["divert", "989"]}
                    desired["tables"] = {table: ["91.108.13.10"]}
                rules = {**deepcopy(desired["rules"]), 20000: ["unrelated"]}
                tables = deepcopy(desired["tables"])
                if table in tables:
                    tables[table + "_stage"] = []
                store = SharedApplyOperation(root / "journal", owner=uid)
                store._persist_record(record)
                original_wal = (store.root / "operation.json").read_bytes()
                events = []
                adapter = Mock()
                adapter.rule_base, adapter.rule_max = 19000, 19099
                adapter.list_rules.side_effect = lambda a, b: {k: v for k, v in rules.items() if a <= k <= b}
                adapter.get_table.side_effect = tables.get

                def delete(number):
                    self.assertFalse(running)
                    events.append(number)
                    del rules[number]

                def destroy(name):
                    self.assertFalse(running)
                    events.append(name)
                    del tables[name]

                adapter.delete_rule.side_effect = delete
                adapter.destroy_table.side_effect = destroy
                script = ROOT / "src/opnsense/scripts/OPNsense/Zapret"

                def digest(path, owner=None):
                    return sha256((path / "dvtws.args").read_bytes()).hexdigest()

                def joined(command, *, pass_fds, budget, capture_output=False):
                    nonlocal running
                    self.assertEqual(pass_fds, (9, 4))
                    self.assertEqual(store.read(), record)
                    if command[0] == str(script / "zapret_service.sh"):
                        self.assertEqual(command[1:], ("shared-apply-first-running-base-physical",
                            detail["id"], detail["base"]))
                        self.assertTrue(running)
                        events.append("stop")
                        if scenario == "stop-refused":
                            return subprocess.CompletedProcess(command, 70, b"", b"")
                        running = False
                        for path in pidfiles:
                            path.unlink()
                        gate.native_guard_first_running_base_stopped_shell_locked(
                            detail["id"], detail["base"], config_fd=4)
                        if scenario == "lost-receipt":
                            return subprocess.CompletedProcess(command, 70, b"", b"")
                        return subprocess.CompletedProcess(command, 0,
                            b"first-running-base-physical=stopped\n", b"")
                    self.assertEqual(command[-1], str(active))
                    self.assertFalse(running)
                    self.assertEqual(rules, {20000: ["unrelated"]})
                    self.assertEqual(tables, {})
                    events.append("remove-tree")
                    reply = subprocess.run(command, capture_output=True, check=False)
                    if scenario == "lost-tree-receipt":
                        self.assertEqual(reply.returncode, 0)
                        self.assertFalse(active.exists())
                        return subprocess.CompletedProcess(command, 70, b"", b"")
                    return reply

                for key, value in (("WORK", work), ("COMMON_ACTIVE", active),
                                   ("PRODUCER_ROOT", root / "producer"), ("EPOCH_ROOT", root / "epochs"),
                                   ("CHILD_PID", pidfiles[0]), ("MONITOR_PID", pidfiles[1]),
                                   ("DAEMON_PID", pidfiles[2]), ("SCRIPT", script)):
                    stack.enter_context(patch.object(gate, key, value))
                stack.enter_context(patch.object(sys, "platform", "freebsd15"))
                stack.enter_context(patch.object(gate.os, "geteuid", return_value=0))
                stack.enter_context(patch.object(gate, "SharedApplyOperation", return_value=store))
                stack.enter_context(patch.object(gate, "require_lifecycle_lock"))
                stack.enter_context(patch("voice_ipfw_adapter.require_lifecycle_lock"))
                stack.enter_context(patch("auto_detect_original_lock_handoff.assert_inherited_config_fd"))
                stack.enter_context(patch("neutral_root_stage.verify_original_operation_pins"))
                stack.enter_context(patch("neutral_root_stage._original_plan_matches", return_value=True))
                stack.enter_context(patch("neutral_root_stage._verify_original_pinned_root", return_value=json.dumps(
                    {"service": {"enabled": True, "target_mode": "list"}})))
                stack.enter_context(patch.object(gate, "inspect_inert_release", return_value="inactive"))
                stack.enter_context(patch("shared_apply_seal._stat", side_effect=lambda path, *a, **kw: path.lstat()))
                stack.enter_context(patch("shared_apply_seal.verify_seal", return_value={"sha256": {
                    "release": digest(release), "plan.json": plan}}))
                stack.enter_context(patch("shared_apply_seal._release_hash", side_effect=digest))
                stack.enter_context(patch.object(gate, "_run", return_value="1 /sbin/init\n"))
                stack.enter_context(patch("neutral_schema3_previous_physical._running_native", return_value=object()))
                stack.enter_context(patch.object(gate, "_first_running_digest", return_value=record["first_running_sha256"]))
                stack.enter_context(patch.object(gate, "shared_release_manifest", return_value=desired))
                stack.enter_context(patch.object(gate, "_ipfw_kernel_confirmed_absent", return_value=False))
                stack.enter_context(patch.object(gate, "FreeBSDIPFWAdapter", return_value=adapter))
                stack.enter_context(patch.object(gate, "_run_bound_restore_joined", side_effect=joined))

                def recover():
                    return gate.finish_first_config_recovery_locked(detail["id"], witness, config_fd=4)

                if scenario in ("stop-refused", "lost-receipt"):
                    with self.assertRaises(gate.QuiescentPreimageRefused):
                        recover()
                    self.assertEqual(events, ["stop"])
                    self.assertEqual((store.root / "operation.json").read_bytes(), original_wal)
                    self.assertTrue(active.is_dir())
                    self.assertEqual(rules, {**desired["rules"], 20000: ["unrelated"]})
                    self.assertEqual(tables, {**desired["tables"], table + "_stage": []})
                    if scenario == "stop-refused":
                        self.assertTrue(running)
                        self.assertEqual(config.read_bytes(), b"original Config bytes\n")
                        continue

                if scenario == "lost-tree-receipt":
                    with self.assertRaises(gate.QuiescentPreimageRefused):
                        recover()
                    self.assertEqual(events, ["stop", 19001, table, table + "_stage", "remove-tree"])
                    self.assertEqual((store.root / "operation.json").read_bytes(), original_wal)
                    self.assertFalse(active.exists())
                    self.assertEqual(rules, {20000: ["unrelated"]})
                    self.assertEqual(tables, {})
                    self.assertEqual(config.read_bytes(), b"original Config bytes\n")

                self.assertEqual(recover(), {"result": "original-bound-cold-restored", "id": detail["id"]})
                expected = [] if scenario == "already-stopped" else ["stop"]
                if scenario != "empty-kernel":
                    expected += [19001, table, table + "_stage"]
                self.assertEqual(events, expected + ["remove-tree"])
                self.assertEqual(store.read(), {**record, "phase": "restored"})
                self.assertEqual(set(os.listdir(store.root)), {"operation.json"})
                self.assertFalse(active.exists())
                self.assertTrue(release.is_dir())
                self.assertEqual(rules, {20000: ["unrelated"]})
                self.assertEqual(tables, {})
                self.assertEqual(config.read_bytes(), b"original Config bytes\n")
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    recover()
                self.assertEqual(events, expected + ["remove-tree"])

    def test_first_running_base_stopped_empty_kernel_requires_empty_sealed_manifest(self):
        import subprocess

        record = {"phase": "activated", "detail": {"id": "a" * 32, "base": "b" * 64}}
        store = Mock(read=Mock(return_value=record))
        empty = {"rule_base": 19000, "rule_max": 19099, "rules": {}, "tables": {}}
        live = (("candidate", 1, 3), None,
                ("native-managed-kernel-final", "d" * 64, ()))
        with ExitStack() as stack:
            stack.enter_context(patch.object(gate, "_first_running_base_scope_locked",
                return_value=(store, record)))
            stack.enter_context(patch.object(gate, "require_lifecycle_lock"))
            stack.enter_context(patch("auto_detect_original_lock_handoff.assert_inherited_config_fd"))
            stack.enter_context(patch.object(gate, "_zero_processes"))
            layout = stack.enter_context(patch.object(gate, "_first_inert_recovery_layout",
                return_value=(live[0], None, "native-managed-kernel-empty")))
            manifests = stack.enter_context(patch.object(gate,
                "_first_inert_staged_manifests", return_value=(empty, empty)))
            stack.enter_context(patch.object(gate, "_attest_first_running_base_locked",
                return_value=live))
            joined = stack.enter_context(patch.object(gate, "_run_bound_restore_joined",
                return_value=subprocess.CompletedProcess([], 0,
                    b"first-running-base-physical=stopped\n", b"")))

            def shell_guard():
                return gate.native_guard_first_running_base_stopped_shell_locked(
                    record["detail"]["id"], record["detail"]["base"], config_fd=4)

            def joined_guard():
                return gate._stop_first_running_base_joined_locked(store, record,
                    config_fd=4, config_digest=record["detail"]["base"])

            for kernel in ("native-managed-kernel-empty", "native-kernel-absent"):
                with self.subTest(kernel=kernel):
                    layout.return_value = (live[0], None, kernel)
                    self.assertIsNone(shell_guard())
                    self.assertIsNone(joined_guard())

            # A missing kernel is not acceptable if the sealed source
            # actually requested any ordinary rule or Voice destination.
            for field, payload in (("rules", {19000: ["divert", "989"]}),
                                   ("tables", {"zapret2_voice_telegram": ["1.2.3.4"]})):
                with self.subTest(field=field):
                    manifests.return_value = (empty, {**empty, field: payload})
                    for run in (shell_guard, joined_guard):
                        with self.assertRaises(gate.QuiescentPreimageRefused):
                            run()
            manifests.side_effect = VoiceFirewallError("untrusted original manifest")
            for run in (shell_guard, joined_guard):
                with self.assertRaises(VoiceFirewallError):
                    run()
            manifests.side_effect = None
            layout.return_value = (live[0], None, "native-managed-kernel-staged")
            manifests.reset_mock()
            self.assertIsNone(shell_guard())
            self.assertIsNone(joined_guard())
            manifests.assert_not_called()
            self.assertEqual(store.read(), record)
            store._advance_bound_ordinary.assert_not_called()
            joined.assert_called()

    def test_first_running_base_stop_requires_exact_joined_receipt(self):
        import subprocess
        record = {"phase": "activated", "detail": {"id": "a" * 32, "base": "b" * 64}}
        store = Mock(read=Mock(return_value=record))
        live = (("candidate", 1, 3), None,
                ("native-managed-kernel-staged", "d" * 64, ()))
        cold = (("candidate", 1, 3), None, "native-managed-kernel-staged")
        with ExitStack() as stack:
            stack.enter_context(patch.object(gate, "require_lifecycle_lock"))
            stack.enter_context(patch("auto_detect_original_lock_handoff.assert_inherited_config_fd"))
            stack.enter_context(patch.object(gate, "_attest_first_running_base_locked",
                return_value=live))
            zero = stack.enter_context(patch.object(gate, "_zero_processes"))
            layout = stack.enter_context(patch.object(gate, "_first_inert_recovery_layout",
                return_value=cold))
            joined = stack.enter_context(patch.object(gate, "_run_bound_restore_joined",
                return_value=subprocess.CompletedProcess([], 0,
                    b"first-running-base-physical=stopped\n", b"")))

            def recover():
                return gate._stop_first_running_base_joined_locked(store, record,
                    config_fd=4, config_digest=record["detail"]["base"])

            self.assertIsNone(recover())
            joined.assert_called_with((str(gate.SCRIPT / "zapret_service.sh"),
                "shared-apply-first-running-base-physical", record["detail"]["id"],
                record["detail"]["base"]), pass_fds=(9, 4), budget=60,
                capture_output=True)
            zero.assert_called_with((gate.CHILD_PID, gate.MONITOR_PID, gate.DAEMON_PID))
            layout.assert_called_once()
            store._advance_bound_ordinary.assert_not_called()
            for result in (subprocess.CompletedProcess([], 70, b"", b""),
                           subprocess.CompletedProcess([], 0, b"foreign\n", b""),
                           subprocess.CompletedProcess([], 0,
                               b"first-running-base-physical=stopped\nother\n", b"")):
                joined.return_value = result
                layout.reset_mock()
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    recover()
                layout.assert_not_called()
            joined.return_value = subprocess.CompletedProcess([], 0,
                b"first-running-base-physical=stopped\n", b"")
            layout.return_value = (("candidate", 1, 4), None, "native-managed-kernel-staged")
            with self.assertRaises(gate.QuiescentPreimageRefused):
                recover()
            store._advance_bound_ordinary.assert_not_called()

    def test_first_running_base_observed_config_routes_stop_then_cold(self):
        import sys
        from shared_apply_operation import _config_observation_witness

        detail = {"id": "a" * 32, "page": "strategies", "base": "b" * 64,
                  "candidate": "c" * 64, "changed_fields": ["general.enabled"]}
        record = {"phase": "activated", "detail": detail, "manifest": {"schema": 1},
                  "first_running_sha256": "d" * 64}
        store = Mock(read=Mock(return_value=record))
        plan_sha = "e" * 64
        base_witness = _config_observation_witness(detail, plan_sha, detail["base"])
        with ExitStack() as stack:
            stack.enter_context(patch.object(sys, "platform", "freebsd15"))
            stack.enter_context(patch.object(gate.os, "geteuid", return_value=0))
            stack.enter_context(patch.object(gate, "require_lifecycle_lock"))
            stack.enter_context(patch("auto_detect_original_lock_handoff.assert_inherited_config_fd"))
            stack.enter_context(patch.object(gate, "SharedApplyOperation", return_value=store))
            stack.enter_context(patch("shared_apply_seal.verify_seal",
                return_value={"sha256": {"plan.json": plan_sha}}))
            zero = stack.enter_context(patch.object(gate, "_zero_processes",
                side_effect=gate.QuiescentPreimageRefused("running")))
            physical = stack.enter_context(patch.object(gate, "_stop_first_running_base_joined_locked"))
            cold = stack.enter_context(patch.object(gate, "finish_bound_cold_restore_locked",
                return_value={"result": "original-bound-cold-restored", "id": detail["id"]}))
            reply = gate.finish_first_config_recovery_locked(detail["id"], base_witness,
                config_fd=4)
            self.assertEqual(reply, {"result": "original-bound-cold-restored", "id": detail["id"]})
            physical.assert_called_once_with(store, record, config_fd=4,
                config_digest=detail["base"])
            cold.assert_called_once_with(detail["id"], detail["base"], config_fd=4)
            physical.reset_mock()
            cold.reset_mock()
            zero.side_effect = None
            self.assertEqual(gate.finish_first_config_recovery_locked(detail["id"],
                base_witness, config_fd=4), reply)
            physical.assert_not_called()
            cold.assert_called_once()
            physical.reset_mock()
            cold.reset_mock()
            with self.assertRaises(gate.QuiescentPreimageRefused):
                gate.finish_first_config_recovery_locked(detail["id"], "0" * 64,
                    config_fd=4)
            physical.assert_not_called()
            cold.assert_not_called()
    def test_first_saved_running_requires_all_rollback_stages_until_config_saved(self):
        names = ("zapret2_voice_telegram", "zapret2_voice_discord")
        pinned = "a" * 64
        empty = {"rule_base": 19000, "rule_max": 19099, "rules": {}, "tables": {}}
        with ExitStack() as stack:
            stack.enter_context(patch("neutral_schema3_previous_physical._running_native"))
            stack.enter_context(patch.object(gate, "_first_running_digest", return_value=pinned))
            manifests = stack.enter_context(patch.object(gate, "_first_inert_staged_manifests"))
            adapter = stack.enter_context(patch.object(gate, "FreeBSDIPFWAdapter")).return_value
            adapter.rule_base, adapter.rule_max = 19000, 19099
            for phase, active, stages, expected in (
                ("activated", names, (), None),
                ("activated", names, names[:1], None),
                ("activated", names, names, "native-managed-kernel-staged"),
                ("activated", (), (), "native-managed-kernel-final"),
                ("config-saved", names, (), "native-managed-kernel-final"),
                ("config-saved", names, names[:1], "native-managed-kernel-staged"),
            ):
                with self.subTest(phase=phase, active=active, stages=stages):
                    desired = {**empty, "rules": {19000: []},
                               "tables": {name: ["91.108.0.0/16"] for name in active}}
                    tables = {**desired["tables"], **{name + "_stage": [] for name in stages}}
                    manifests.return_value = (empty, desired)
                    adapter.list_rules.return_value = desired["rules"]
                    adapter.get_table.side_effect = tables.get
                    record = {"phase": phase, "first_running_sha256": pinned}
                    if expected is None:
                        with self.assertRaisesRegex(VoiceFirewallError, "missing shared IPFW rollback stage table"):
                            gate._first_saved_running_kernel(record, Path("/unused"), config_fd=4)
                    else:
                        self.assertEqual(gate._first_saved_running_kernel(
                            record, Path("/unused"), config_fd=4)[0], expected)

    def test_first_learning_saved_recovery_orders_epoch_and_keeps_failed_checkpoint(self):
        import tempfile
        from types import SimpleNamespace
        from contextlib import nullcontext
        record = {**self.f.original.read(), "phase": "activated",
                  "manifest": {"schema": 2}, "first_running_sha256": "a" * 64,
                  "first_pretraffic_sha256": "b" * 64}
        record.pop("previous", None)
        record.pop("previous_manifest", None)
        detail = record["detail"]
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryFile() as config, ExitStack() as stack:
            base = Path(tmp)
            work = base / "work" / detail["id"]
            work.mkdir(parents=True)
            active = base / "active"
            active.mkdir()
            epochs = base / "epochs"
            (epochs / detail["id"]).mkdir(parents=True)
            for key, value in (("WORK", work.parent), ("COMMON_ACTIVE", active),
                               ("EPOCH_ROOT", epochs), ("PRODUCER_ROOT", base / "producer")):
                stack.enter_context(patch.object(gate, key, value))
            store = Mock(read=Mock(return_value=record))
            sources = ((1, "learning", "/fixture/source"),)
            proof = SimpleNamespace(operation_id=detail["id"], generation=detail["id"],
                owner_candidate_sha256=detail["candidate"], learning=sources)
            data = {"pretraffic_sha256": record["first_pretraffic_sha256"]}
            queue = Mock()
            queue.inherited_exclusive.side_effect = lambda fd: nullcontext()
            receipts = Mock()
            receipts._attest_learning_running_seed.return_value = (None, data)
            staged = ("native-managed-kernel-staged", "a" * 64, (("stage", "x", ()),))
            final = ("native-managed-kernel-final", "a" * 64, ())
            calls = []
            def advance(phase, current, attest):
                if not attest():
                    raise gate.QuiescentPreimageRefused("drift")
                calls.append(phase)
                result = {**current, "phase": phase}
                store.read.return_value = result
                return result
            store._advance_bound_ordinary.side_effect = advance
            for name in ("require_lifecycle_lock", "_safe_empty_directory", "_reject_cold_recovery_residue"):
                stack.enter_context(patch.object(gate, name))
            stack.enter_context(patch("auto_detect_original_lock_handoff.assert_inherited_config_fd"))
            stack.enter_context(patch("neutral_root_stage.verify_original_operation_pins"))
            stack.enter_context(patch("shared_apply_seal._stat"))
            stack.enter_context(patch("auto_detect_post_drop._learning_release_sources",
                return_value=(work, detail["candidate"], sources)))
            stack.enter_context(patch("auto_detect_post_drop._qualified_learning_sources",
                return_value=(detail["id"], ("source",))))
            stack.enter_context(patch("auto_detect_post_drop._original_epoch_queue",
                return_value=(queue, receipts)))
            for name in ("attest_bound_learning_staged_generation",
                         "attest_learning_epoch_finalizing_generation"):
                stack.enter_context(patch("auto_detect_owner." + name, return_value=proof))
            stack.enter_context(patch.object(gate, "_full_prior_tree", return_value="tree"))
            kernel = stack.enter_context(patch.object(gate, "_first_saved_running_kernel",
                return_value=staged))
            stack.enter_context(patch.object(gate, "_first_inert_staged_manifests",
                return_value=({}, {})))
            stack.enter_context(patch.object(gate, "FreeBSDIPFWAdapter"))
            stack.enter_context(patch("voice_firewall_transaction.verify_staged_state"))
            def cleanup(*args):
                self.assertEqual(store.read()["phase"], "epoch-finalizing")
                calls.append("cleanup")
                kernel.return_value = final
            native = stack.enter_context(patch("voice_firewall_transaction.cleanup_committed",
                side_effect=VoiceFirewallError("uncertain cleanup")))
            def finish(*args, **kwargs):
                calls.append("epoch")
                return data
            stack.enter_context(patch("auto_detect_post_drop.native_finish_first_bound_learning_epoch_locked",
                side_effect=finish))
            def recover():
                return gate._finish_first_learning_saved_locked(store, store.read(),
                    config_fd=config.fileno(), config_digest=detail["candidate"], queue_fd=3)
            with self.assertRaises(VoiceFirewallError):
                recover()
            self.assertEqual(calls, ["epoch-finalizing"])
            native.side_effect = cleanup
            self.assertEqual(recover()["phase"], "committed")
            self.assertEqual(calls, ["epoch-finalizing", "cleanup", "epoch", "committed"])

    def test_real_bound_cold_root_with_actual_empty_manifest_check(self):
        self.cold()
        record = self.f.original.read()
        with ExitStack() as stack:
            retired = self.native_seams(stack)
            receipt = self.call()
            retired.assert_not_called()
        self.assertEqual(receipt.old_state, "first-install-empty")
        self.assertEqual(receipt.kernel_state, "native-managed-kernel-empty")
        self.assertEqual(receipt.retirement_state, "no-prior-data")
        self.assertEqual(receipt.root_sha256, record["manifest"]["root_sha256"])
        self.assertIsNone(receipt.previous_generation)
        self.assertFalse(receipt.physical_transition_allowed)
        self.assertEqual(receipt.authorization, "NONE")
        self.adapter.list_rules.assert_called_with(19000, 19099)
        self.assertEqual(self.f.original.read(), record)
        with self.assertRaisesRegex(SharedOperationError, "preactivation gate"):
            self.f.original.advance("activating", self.f.detail)

    def test_bound_inert_cold_restore_requires_saved_old_config_and_exact_artifacts(self):
        import json
        old = {"id": "a" * 32, "page": "strategies", "base": "b" * 64,
               "candidate": "c" * 64, "changed_fields": []}
        new = {"id": "d" * 32, "page": "strategies", "base": old["candidate"],
               "candidate": "e" * 64, "changed_fields": []}
        pin = lambda d: dict(schema=1, generation=d["id"],
                             root_sha256="f" * 64, seal_sha256="0" * 64,
                             candidate_sha256=d["candidate"])
        record = dict(schema=1, phase="activating", detail=new,
                      previous=old, manifest=pin(new), previous_manifest=pin(old))
        saved = {"result": "committed", "snapshot": old["candidate"], "enabled": "0"}
        classified = dict(result="read-only-ordinary-config-classification",
            image="base-image", base=new["base"], candidate=new["candidate"],
            snapshot=new["base"], enabled="0", commit_authorized=False,
            restore_authorized=False, save_attested=False, runtime_attested=False)
        old_hash, new_hash = "1" * 64, "2" * 64
        stage = self.active.parent / f".{self.active.name}.stage.{new['id']}"
        stage.mkdir()
        def seal(work, **_):
            return {"sha256": {"release": old_hash if work.name == old["id"] else new_hash}}
        with ExitStack() as stack:
            stack.enter_context(patch.object(gate, "require_lifecycle_lock"))
            stack.enter_context(patch.object(gate, "SharedApplyOperation",
                return_value=Mock(read=Mock(return_value=record))))
            stack.enter_context(patch.object(gate, "COMMON_ACTIVE", self.active))
            stack.enter_context(patch.object(gate, "_observe_idle_producer", return_value=None))
            stack.enter_context(patch.object(gate, "_zero_processes"))
            stack.enter_context(patch.object(gate, "inspect_inert_release",
                                             return_value="inactive"))
            pins = stack.enter_context(patch("neutral_root_stage.verify_original_operation_pins"))
            stack.enter_context(patch("neutral_root_stage._original_plan_matches", return_value=True))
            stack.enter_context(patch("shared_apply_seal.verify_seal", side_effect=seal))
            stack.enter_context(patch("shared_apply_seal._stat"))
            artifact = stack.enter_context(patch("shared_apply_seal._release_hash",
                side_effect=lambda path, uid: old_hash if path == self.active else new_hash))
            def read_config(argv):
                row = saved if argv[2] == "saved" else classified
                return (json.dumps(row) + "\n").encode()
            native = stack.enter_context(patch.object(gate, "_native_call",
                                                       side_effect=read_config))
            full = stack.enter_context(patch.object(gate, "_full_prior_tree", return_value=old_hash))
            kernel = stack.enter_context(patch.object(gate, "_empty_kernel",
                                                       return_value="native-managed-kernel-empty"))
            gate.attest_inert_bound_cold_recovery(record, restored=False)
            full.assert_not_called()
            kernel.assert_not_called()
            gate.attest_inert_bound_cold_recovery(record, restored=True)
            self.assertEqual(pins.call_count, 4)
            self.assertEqual([call.args[0][2:] for call in native.call_args_list],
                [("saved", old["id"], old["page"]),
                 ("ordinary-cold", new["id"], new["page"])] * 4)
            artifact.assert_called_with(stage, 0)
            # Terminal child inherits Config rather than invoking PHP while
            # it owns FD4, and borrows (never acquires) the original queue.
            with patch.object(sys, "platform", "freebsd15"), \
                    patch.object(os, "geteuid", return_value=0), \
                    patch("auto_detect_original_lock_handoff.assert_inherited_config_fd") as lock, \
                    patch.object(gate, "_cold_locked_producer", return_value=(None, None)) as producer:
                native.reset_mock()
                gate.attest_inert_bound_cold_recovery(
                    record, restored=True, config_fd=4, config_digest=new["base"], queue_fd=3)
                native.assert_not_called()
                self.assertEqual(producer.call_count, 2)
                self.assertGreaterEqual(lock.call_count, 5)
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    gate.attest_inert_bound_cold_recovery(
                        record, restored=True, config_fd=4, config_digest=new["candidate"], queue_fd=3)
            # An apparently saved old Config is insufficient if the original
            # successor plan reports a different image. Both recovery gates
            # must refuse it (old implementation never read this receipt).
            classified.update(image="candidate-image", snapshot=new["candidate"])
            for restored in (False, True):
                with self.assertRaises(ValueError):
                    gate.attest_inert_bound_cold_recovery(record, restored=restored)
            classified.update(image="base-image", snapshot=new["base"])
            classified["enabled"] = "1"
            with self.assertRaises(gate.QuiescentPreimageRefused):
                gate.attest_inert_bound_cold_recovery(record, restored=False)
            classified["enabled"] = "0"
            # Only ACTIVATING can use an equal model image: native save has
            # not been attempted in that phase. ACTIVATED stays ambiguous.
            equal_new = {**new, "candidate": new["base"]}
            equal = {**record, "detail": equal_new, "manifest": pin(equal_new)}
            gate.SharedApplyOperation.return_value.read.return_value = equal
            classified.update(image="base-equals-candidate", candidate=new["base"])
            gate.attest_inert_bound_cold_recovery(equal, restored=False)
            ambiguous = {**equal, "phase": "activated"}
            gate.SharedApplyOperation.return_value.read.return_value = ambiguous
            for restored in (False, True):
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    gate.attest_inert_bound_cold_recovery(ambiguous, restored=restored)
            gate.SharedApplyOperation.return_value.read.return_value = record
            classified.update(image="base-image", candidate=new["candidate"])
            # An inert candidate can roll back to an already retired Auto
            # owner, but only on its full immutable history and idle proof.
            retired = {**record, "previous_manifest": {**record["previous_manifest"], "schema": 2}}
            store = gate.SharedApplyOperation.return_value
            store.read.return_value = retired
            with patch.object(gate, "_observe_cold_retired_predecessor",
                              return_value=("a" * 64, ((1, 2, 0, "b" * 64),
                                                       (1, 3, 0, "b" * 64)))) as epoch:
                gate.attest_inert_bound_cold_recovery(retired, restored=False)
                gate.attest_inert_bound_cold_recovery(retired, restored=True)
                self.assertEqual(epoch.call_count, 4)
                epoch.side_effect = ValueError("missing retirement")
                with self.assertRaises(ValueError):
                    gate.attest_inert_bound_cold_recovery(retired, restored=False)
            store.read.return_value = record
            # A partial/corrupted stage is not terminal old-owner evidence.
            artifact.side_effect = lambda path, uid: old_hash if path == self.active else "3" * 64
            for restored in (False, True):
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    gate.attest_inert_bound_cold_recovery(record, restored=restored)
            artifact.side_effect = lambda path, uid: old_hash if path == self.active else new_hash
            saved["snapshot"] = new["candidate"]
            with self.assertRaises(gate.QuiescentPreimageRefused):
                gate.attest_inert_bound_cold_recovery(record, restored=False)
            # Bound learning, Found and post-save uncertainty cannot enter
            # the ordinary inert cold rollback route.
            for forbidden in (
                    {**record, "manifest": {**record["manifest"], "schema": 2}},
                    {**record, "found": {}}, {**record, "phase": "config-saved"}):
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    gate.attest_inert_bound_cold_recovery(forbidden, restored=False)

    def test_bound_parked_restore_preserves_original_evidence(self):
        import shutil
        import tempfile

        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            active = Path(temp) / "runtime-v2"
            record = dict(phase="activating", detail={"id": "d" * 32},
                          previous={"id": "a" * 32})
            stage = active.parent / (".runtime-v2.stage." + record["detail"]["id"])
            hold = active.parent / (".runtime-v2.old." + record["detail"]["id"])
            stage.mkdir()
            hold.mkdir()
            (stage / "new").write_text("candidate")
            (hold / "old").write_text("previous")
            stack.enter_context(patch.object(gate, "COMMON_ACTIVE", active))
            stack.enter_context(patch.object(gate, "require_lifecycle_lock"))
            stack.enter_context(patch("auto_detect_original_lock_handoff.assert_inherited_config_fd"))
            stack.enter_context(patch("shared_apply_seal.verify_seal",
                side_effect=lambda path, **kw: {"sha256": {"release":
                    "old" if path.name == record["previous"]["id"] else "new"}}))
            proof = stack.enter_context(patch.object(gate, "attest_inert_bound_cold_recovery"))
            trees = stack.enter_context(patch.object(gate, "_cold_recovery_trees",
                side_effect=lambda *a, **kw: ("old" if active.exists() else None,
                                              "new", "old", None)))
            stack.enter_context(patch.object(gate, "_empty_kernel", return_value="empty"))

            def copy_old(argv, **kwargs):
                self.assertEqual(kwargs, {"pass_fds": (9, 4, 3), "budget": 20})
                self.assertEqual(argv[-2], str(active))
                shutil.copytree(hold, active)
                return Mock(returncode=0)

            run = stack.enter_context(patch.object(gate, "_run_bound_restore_joined",
                                                  side_effect=copy_old))
            self.assertTrue(gate._restore_bound_parked_cold_locked(
                record, config_fd=4, config_digest="b"*64, queue_fd=3))
            self.assertEqual((active / "old").read_text(), "previous")
            self.assertEqual((stage / "new").read_text(), "candidate")
            self.assertEqual((hold / "old").read_text(), "previous")
            self.assertEqual(proof.call_count, 3)
            run.assert_called_once()
            shutil.rmtree(active)
            run.reset_mock()
            trees.side_effect = None
            trees.return_value = (None, "new", "old", "old")
            with self.assertRaises(gate.QuiescentPreimageRefused):
                gate._restore_bound_parked_cold_locked(
                    record, config_fd=4, config_digest="b"*64, queue_fd=3)
            run.assert_not_called()
            trees.return_value = (None, "new", "old", None)
            (active.parent / ".runtime-v2.stage.123").mkdir()
            with self.assertRaises(gate.QuiescentPreimageRefused):
                gate._restore_bound_parked_cold_locked(
                    record, config_fd=4, config_digest="b"*64, queue_fd=3)
            run.assert_not_called()
            (active.parent / ".runtime-v2.stage.123").rmdir()
            # A valid 32-hex ID may consist entirely of decimal digits.
            (active.parent / (".runtime-v2.stage." + "1" * 32)).mkdir()
            gate._reject_cold_recovery_residue(active)

    def test_installed_cold_rollback_uses_empty_prior_kernel_under_config(self):
        import json
        import tempfile
        from unittest.mock import call

        base = "b" * 64
        record = dict(phase="activated", detail={"id": "d" * 32},
                      previous={"id": "a" * 32}, manifest={"schema": 1})
        empty = {"rule_base": 19000, "rule_max": 19099, "rules": {}, "tables": {}}
        desired = {"rule_base": 19000, "rule_max": 19010, "rules": {19000: []}, "tables": {}}
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            active = Path(temp) / "runtime-v2"
            active.mkdir()
            stack.enter_context(patch.object(gate, "COMMON_ACTIVE", active))
            stack.enter_context(patch.object(gate, "require_lifecycle_lock"))
            stack.enter_context(patch("auto_detect_original_lock_handoff.assert_inherited_config_fd"))
            stack.enter_context(patch("shared_apply_seal.verify_seal",
                side_effect=lambda path, **kw: {"sha256": {"release":
                    "old" if path.name == record["previous"]["id"] else "new"}}))
            stack.enter_context(patch("shared_apply_seal._release_hash", return_value="new"))
            stack.enter_context(patch("neutral_root_stage._verify_original_pinned_root",
                return_value=json.dumps({"service": {"enabled": True}}).encode()))
            proof = stack.enter_context(patch.object(gate, "attest_inert_bound_cold_recovery"))
            tree = stack.enter_context(patch.object(gate, "_cold_recovery_trees",
                return_value=("new", None, None, "old")))
            stack.enter_context(patch.object(gate, "shared_release_manifest", return_value=desired))
            stack.enter_context(patch.object(gate, "_ipfw_kernel_confirmed_absent", return_value=False))
            adapter = stack.enter_context(patch.object(gate, "FreeBSDIPFWAdapter"))
            stack.enter_context(patch.object(gate, "verify_prior_state",
                                             side_effect=gate.VoiceFirewallError("staged")))
            staged = stack.enter_context(patch("voice_firewall_transaction.verify_staged_state"))
            rollback = stack.enter_context(patch("voice_firewall_transaction.rollback_uncommitted"))
            stack.enter_context(patch.object(gate, "_empty_kernel"))
            run = stack.enter_context(patch.object(gate, "_run_bound_restore_joined",
                                                   return_value=Mock(returncode=0)))
            self.assertTrue(gate._restore_bound_installed_cold_locked(
                record, config_fd=4, config_digest=base, queue_fd=3))
            self.assertEqual(adapter.call_args_list, [call(19000, 19099),
                                                      call(19000, 19099, allow_mutations=True)])
            staged.assert_called_once_with(adapter.return_value, empty, desired)
            rollback.assert_called_once_with(adapter.return_value, empty, desired)
            self.assertEqual(run.call_args.kwargs["pass_fds"], (9, 4, 3))
            self.assertEqual(proof.call_count, 3)
            rollback.reset_mock()
            run.reset_mock()
            tree.return_value = ("new", None, None, None)
            with self.assertRaises(gate.QuiescentPreimageRefused):
                gate._restore_bound_installed_cold_locked(
                    record, config_fd=4, config_digest=base, queue_fd=3)
            rollback.assert_not_called()
            run.assert_not_called()
            tree.return_value = ("new", None, None, "old")
            staged.side_effect = gate.VoiceFirewallError("foreign")
            with self.assertRaises(gate.VoiceFirewallError):
                gate._restore_bound_installed_cold_locked(
                    record, config_fd=4, config_digest=base, queue_fd=3)
            rollback.assert_not_called()
            run.assert_not_called()

    def test_pristine_stage_cleanup_uses_exact_original_atomic_helper(self):
        import subprocess
        import tempfile

        # Exercise actual files and production atomic_remove_tree, while
        # mocking the native FD9/FD4 and sealed bundle readers only.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            active = root / "runtime-v2"
            active.mkdir()
            generation = "d" * 32
            old = {"id": "a" * 32}
            record = {"phase": "activating", "detail": {"id": generation},
                      "previous": old}
            stage = root / f".runtime-v2.stage.{generation}"
            parked = root / f".runtime-v2.old.{generation}"
            stage.mkdir()
            (stage / "sealed").write_text("candidate")
            store = Mock(read=Mock(return_value=record))
            actual_run = subprocess.run

            def shell(argv, **kwargs):
                self.assertEqual(kwargs.pop("pass_fds"), (9, 4, 3))
                self.assertEqual(argv[-1], str(stage))
                self.assertEqual(kwargs.pop("budget"), 20)
                return actual_run(argv, **kwargs)

            with ExitStack() as stack:
                stack.enter_context(patch.object(gate, "COMMON_ACTIVE", active))
                stack.enter_context(patch.object(gate, "SCRIPT",
                    ROOT / "src/opnsense/scripts/OPNsense/Zapret"))
                stack.enter_context(patch.object(gate, "require_lifecycle_lock"))
                lock = stack.enter_context(patch(
                    "auto_detect_original_lock_handoff.assert_inherited_config_fd"))
                stack.enter_context(patch.object(gate, "SharedApplyOperation",
                                                   return_value=store))
                stack.enter_context(patch("shared_apply_seal.verify_seal", side_effect=[
                    {"sha256": {"release": "old"}}, {"sha256": {"release": "new"}},
                    {"sha256": {"release": "old"}}, {"sha256": {"release": "new"}}]))
                trees = stack.enter_context(patch.object(gate, "_cold_recovery_trees",
                    return_value=("old", "new", None, None)))
                run = stack.enter_context(patch.object(gate, "_run_bound_restore_joined", side_effect=shell))
                self.assertTrue(gate._remove_bound_pristine_stage_locked(
                    record, config_fd=4, queue_fd=3))
                self.assertFalse(stage.exists())
                self.assertTrue(active.exists())
                self.assertGreaterEqual(lock.call_count, 3)
                run.assert_called_once()
                stage.mkdir()
                parked.mkdir()
                self.assertFalse(gate._remove_bound_pristine_stage_locked(
                    record, config_fd=4, queue_fd=3))
                self.assertTrue(stage.exists())
                parked.rmdir()
                trees.return_value = ("old", "foreign", None, None)
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    gate._remove_bound_pristine_stage_locked(record, config_fd=4, queue_fd=3)
                self.assertTrue(stage.exists())
                run.assert_called_once()

    def test_bound_restore_deadline_joins_physical_child(self):
        import fcntl
        import subprocess
        import tempfile

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lockpath = root / "lock"
            marker = root / "finished"
            with lockpath.open("w") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                command = ["/bin/sh", "-c",
                           'sleep 0.15; printf done > "$1"', "fixture", str(marker)]
                with self.assertRaises(subprocess.TimeoutExpired):
                    gate._run_bound_restore_joined(command, budget=0.01,
                                                   pass_fds=(lock.fileno(),))
                self.assertEqual(marker.read_text(), "done")
                with lockpath.open("r") as other:
                    with self.assertRaises(BlockingIOError):
                        fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
                result = gate._run_bound_restore_joined(
                    ["/bin/sh", "-c", "printf receipt"], budget=5,
                    capture_output=True, pass_fds=(lock.fileno(),))
                self.assertEqual((result.returncode, result.stdout), (0, b"receipt"))

    def test_bound_cold_restore_terminal_handoff_retains_native_locks(self):
        import json
        import subprocess
        from contextlib import contextmanager

        base = "b" * 64
        new = {"id": "d" * 32, "page": "strategies", "base": base,
               "candidate": "c" * 64}
        old = {"id": "a" * 32, "candidate": base}
        record = dict(phase="activated", detail=new, previous=old,
                      manifest={"schema": 1}, previous_manifest={"schema": 2})
        terminal = {**record, "phase": "restored"}
        store = Mock()
        store.read.return_value = record
        queue = Mock(root=gate.PRODUCER_ROOT, uid=0, locked_fd=7)
        receipts = Mock(root=gate.EPOCH_ROOT)
        held = [False]

        @contextmanager
        def exclusive(*, existing_only):
            self.assertTrue(existing_only)
            held[0] = True
            try:
                yield
            finally:
                held[0] = False

        queue.exclusive.side_effect = exclusive

        def advance(phase, expected, attest):
            self.assertTrue(held[0])
            self.assertEqual((phase, expected), ("restored", record))
            self.assertTrue(attest())
            store.read.return_value = terminal
            return terminal

        def invoke(argv, **kwargs):
            self.assertTrue(held[0])
            self.assertEqual(argv[-4:], ["ordinary-restore-finish", new["id"],
                                          "strategies", "--queue-fd=7"])
            self.assertEqual(kwargs["pass_fds"], (7, 9))
            result = gate.finish_bound_cold_restore_locked(
                new["id"], base, config_fd=4, queue_fd=3)
            return Mock(returncode=0, stdout=(json.dumps(result) + "\n").encode())

        with ExitStack() as stack:
            stack.enter_context(patch.object(sys, "platform", "freebsd15"))
            stack.enter_context(patch.object(os, "geteuid", return_value=0))
            stack.enter_context(patch.object(gate, "require_lifecycle_lock"))
            stack.enter_context(patch.object(gate, "SharedApplyOperation", return_value=store))
            stack.enter_context(patch.object(gate, "_present", return_value=False))
            stack.enter_context(patch("auto_detect_post_drop._original_epoch_queue",
                                       return_value=(queue, receipts)))
            config_lock = stack.enter_context(patch(
                "auto_detect_original_lock_handoff.assert_inherited_config_fd"))
            proof = stack.enter_context(patch.object(gate, "attest_inert_bound_cold_recovery"))
            stack.enter_context(patch.object(gate, "_reject_cold_recovery_residue"))
            stack.enter_context(patch.object(gate, "_restore_bound_parked_cold_locked", return_value=False))
            stack.enter_context(patch.object(gate, "_restore_bound_installed_cold_locked", return_value=False))
            stack.enter_context(patch.object(gate, "_remove_bound_pristine_stage_locked", return_value=False))
            run = stack.enter_context(patch.object(gate, "_run_bound_restore_joined", side_effect=invoke))
            store._advance_bound_ordinary.side_effect = advance
            self.assertEqual(gate.native_finish_bound_cold_restore(record), terminal)
            proof.assert_called_once_with(record, restored=True, config_fd=4,
                                          config_digest=base, queue_fd=3)
            self.assertEqual(config_lock.call_count, 3)
            store._advance_bound_ordinary.assert_called_once()
            self.assertFalse(held[0])
            store.read.return_value = record
            store._advance_bound_ordinary.reset_mock()
            with self.assertRaises(gate.QuiescentPreimageRefused):
                gate.finish_bound_cold_restore_locked(
                    new["id"], new["candidate"], config_fd=4, queue_fd=3)
            store._advance_bound_ordinary.assert_not_called()
            run.side_effect = subprocess.TimeoutExpired("php", 90)
            with self.assertRaisesRegex(gate.QuiescentPreimageRefused, "OUTCOME_UNCERTAIN"):
                gate.native_finish_bound_cold_restore(record)
            self.assertFalse(held[0])
            store._advance_bound_ordinary.assert_not_called()

    def test_cold_retired_predecessor_requires_existing_queue_and_complete_history(self):
        from contextlib import contextmanager
        record = {"previous": {"id": "a" * 32, "candidate": "b" * 64},
                  "previous_manifest": {"schema": 2}}
        queue = Mock(root=gate.PRODUCER_ROOT, uid=0)
        receipts = Mock(root=gate.EPOCH_ROOT)
        held = [False]

        @contextmanager
        def lock(*, existing_only):
            self.assertTrue(existing_only)
            self.assertFalse(held[0])
            held[0] = True
            try:
                yield
            finally:
                held[0] = False

        queue.exclusive.side_effect = lock
        ready = "c" * 64
        idle = ((1, 2, 0, "d" * 64), (1, 3, 0, "d" * 64))
        def verify(*args):
            self.assertTrue(held[0])
            self.assertEqual(args, (record, queue, receipts, ready))
        with ExitStack() as stack:
            stack.enter_context(patch("auto_detect_post_drop._original_epoch_queue",
                                       return_value=(queue, receipts)))
            digest = stack.enter_context(patch.object(gate, "_retired_ready_digest",
                                                        return_value=ready))
            history = stack.enter_context(patch.object(gate, "_verify_retired_history",
                                                         side_effect=verify))
            producer = stack.enter_context(patch.object(gate, "_verify_idle_producer",
                                                          return_value=idle))
            self.assertEqual(gate._observe_cold_retired_predecessor(record), (ready, idle))
            history.assert_called_once()
            producer.assert_called_once_with(queue, receipts)
            self.assertEqual(digest.call_count, 2)
            digest.side_effect = (ready, "e" * 64)
            with self.assertRaises(gate.QuiescentPreimageRefused):
                gate._observe_cold_retired_predecessor(record)
            digest.side_effect = None
            history.side_effect = ValueError("missing ACK")
            with self.assertRaises(ValueError):
                gate._observe_cold_retired_predecessor(record)
            history.side_effect = verify
            producer.side_effect = ValueError("nonempty producer")
            with self.assertRaises(ValueError):
                gate._observe_cold_retired_predecessor(record)
            producer.side_effect = None
            receipts.root = Path("/foreign")
            with self.assertRaises(gate.QuiescentPreimageRefused):
                gate._observe_cold_retired_predecessor(record)
            self.assertFalse(held[0])

    def test_bound_cold_atomic_images_are_checked_before_mutation(self):
        from tempfile import TemporaryDirectory
        from shared_apply_seal import _release_hash, SharedBundleError

        with TemporaryDirectory() as tmp:
            parent = Path(tmp)
            active = parent / "runtime-v2"
            generation = "a" * 32
            stage = parent / f".runtime-v2.stage.{generation}"
            parked = parent / f".runtime-v2.old.{generation}"
            backup_root = parent / "runtime-v2-backups"
            backup = backup_root / f"runtime-v2-{generation}"
            old, new, foreign = (parent / name for name in ("old", "new", "foreign"))
            for path, content in ((old, b"old"), (new, b"new"), (foreign, b"foreign")):
                path.mkdir()
                (path / "data").write_bytes(content)
            uid = os.geteuid()
            old_hash, new_hash = _release_hash(old, uid), _release_hash(new, uid)

            def clear():
                for path in (active, stage, parked, backup_root):
                    if path.is_symlink():
                        path.unlink()
                    elif path.exists():
                        shutil.rmtree(path)

            def run(mapping, allowed, *, phase="activating", restored=False):
                clear()
                for path, source in mapping:
                    path.parent.mkdir(exist_ok=True)
                    shutil.copytree(source, path)
                before = {str(p): p.lstat().st_ino for p in parent.rglob("*")}
                def observe():
                    return gate._cold_recovery_trees(
                        active, generation, old_hash, new_hash, phase=phase,
                        restored=restored, owner_uid=uid)
                if allowed:
                    observe()
                else:
                    with self.assertRaises((gate.QuiescentPreimageRefused, SharedBundleError)):
                        observe()
                self.assertEqual(before, {str(p): p.lstat().st_ino for p in parent.rglob("*")})

            run(((active, old),), True)
            run(((active, old), (stage, new)), True)
            run(((stage, new), (parked, old)), True)
            run(((stage, new), (backup, old)), True)
            run(((active, new), (backup, old)), True, phase="activated")
            run(((active, old), (stage, new), (parked, old)), True, restored=True)
            run(((active, new),), False)
            run(((active, foreign),), False)
            run(((active, old), (stage, foreign)), False)
            run(((active, new), (backup, foreign)), False)
            run(((active, old), (parked, old), (backup, old)), False)
            run(((stage, new),), False)
            run(((stage, new), (parked, old)), False, phase="activated")
            run(((active, new), (backup, old)), False, restored=True)
            run(((active, new), (backup, old), (stage, new)), False)
            clear()
            shutil.copytree(old, active)
            backup_root.symlink_to(old, target_is_directory=True)
            with self.assertRaises(SharedBundleError):
                gate._cold_recovery_trees(
                    active, generation, old_hash, new_hash, phase="activating",
                    restored=False, owner_uid=uid)

    def test_cold_native_absent_kernel_never_loads_adapter(self):
        self.cold()
        with ExitStack() as stack:
            self.native_seams(stack, cold_kernel=True)
            receipt = self.call()
        self.assertEqual(receipt.kernel_state, "native-kernel-absent")
        self.adapter.list_rules.assert_not_called()

    def test_cold_orphan_rule_or_managed_stage_table_refused(self):
        self.cold()
        with ExitStack() as stack:
            self.native_seams(stack)
            self.adapter.list_rules.return_value = {19095: ["foreign"]}
            with self.assertRaises(gate.QuiescentPreimageRefused):
                self.call()
            self.adapter.list_rules.return_value = {}
            self.adapter.get_table.side_effect = lambda name: (
                ["192.0.2.1"] if name.endswith("_stage") else None)
            with self.assertRaises(gate.QuiescentPreimageRefused):
                self.call()

    def test_no_previous_with_active_tree_is_not_cold(self):
        record = self.f.original.read()
        record.pop("previous")
        self.f.original._persist_record(record)
        with ExitStack() as stack:
            self.native_seams(stack, cold_kernel=True)
            with self.assertRaises(gate.QuiescentPreimageRefused):
                self.call()

    def test_cold_pidfile_foreign_process_and_malformed_census(self):
        self.cold()
        with ExitStack() as stack:
            self.native_seams(stack, cold_kernel=True)
            for path in self.pidfiles:
                path.write_text("5432\n")
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    self.call()
                path.unlink()
            for line in (f"999 {gate.CHILD_EXEC}", f"999 /bin/sh {gate.MONITOR_EXEC}",
                         "999 daemon: supervisor_loop.sh[123] (daemon)",
                         "999 daemon: dvtws2[123] (daemon)",
                         f"999 daemon: {gate.CHILD_EXEC}[123] (daemon)",
                         f"999 daemon: {gate.MONITOR_EXEC}[123] (daemon)",
                         "malformed", "999"):
                self.runner.return_value.stdout = "1 /sbin/init\n" + line + "\n"
                with self.subTest(line=line), self.assertRaises(gate.QuiescentPreimageRefused):
                    self.call()

    def test_cold_residual_producer_epoch_backup_atomic_stage_and_old_work(self):
        self.cold()
        with ExitStack() as stack:
            self.native_seams(stack, cold_kernel=True)
            for path in (self.producer, self.epochs, self.backups, self.active,
                         self.f.parent / ("0" * 32)):
                path.mkdir()
                (path / "evidence").touch()
                with self.subTest(path=path.name), self.assertRaises(gate.QuiescentPreimageRefused):
                    self.call()
                shutil.rmtree(path)
            stage = self.active.parent / (f".{self.active.name}.stage." + "0" * 32)
            stage.mkdir()
            with self.assertRaises(gate.QuiescentPreimageRefused):
                self.call()

    def test_stopped_old_tree_plus_existing_retired_ready_command(self):
        self.lock()
        record = self.f.original.read()
        with ExitStack() as stack:
            cmd = self.native_seams(stack)
            receipt = self.call()
        self.assertEqual(receipt.old_state, "committed-stopped")
        self.assertEqual(receipt.previous_generation, record["previous"]["id"])
        self.assertEqual(receipt.retirement_state, "original-epoch-ack-retired")
        self.assertEqual(cmd.call_count, 2)
        cmd.assert_called_with((str(gate.SCRIPT / "python_runtime.sh"),
            str(gate.SCRIPT / "backend/auto_detect_minute.py"), "--retired-ready"))
        self.assertEqual(record, self.f.original.read())
        self.assertEqual(receipt.authorization, "NONE")

    def test_stopped_native_retirement_must_be_complete_no_lock_creation(self):
        with ExitStack() as stack:
            cmd = self.native_seams(stack)
            with self.assertRaises(gate.QuiescentPreimageRefused):
                self.call()
            cmd.assert_not_called()
            self.assertFalse(self.producer.exists())
            self.lock()
            for response in (b"auto-detect-retire=processed\n",
                             b"auto-detect-retire=idle\n", b"", b"foreign\n"):
                cmd.return_value = response
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    self.call()

    def test_stopped_old_tree_mutation_and_running_refused(self):
        self.lock()
        with ExitStack() as stack:
            self.native_seams(stack)
            (self.active / "tcp-ports.txt").write_bytes(b"tampered\n")
            with self.assertRaises(gate.QuiescentPreimageRefused):
                self.call()
        with ExitStack() as stack:
            self.saved = replace(self.saved, previous_state="ready")
            cmd = self.native_seams(stack)
            with self.assertRaises(gate.QuiescentPreimageRefused):
                self.call()
            cmd.assert_not_called()

    def test_second_observation_wan_or_kernel_changed_refused(self):
        self.cold()
        with ExitStack() as stack:
            self.native_seams(stack)
            with patch.object(gate, "_first_learning_candidate_wan", side_effect=("tun0", "tun1")):
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    self.call()
            with patch.object(gate, "_ipfw_kernel_confirmed_absent",
                              side_effect=(True, False)):
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    self.call()

    def test_retired_readonly_native_source_still_uses_repair_false(self):
        minute = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend/auto_detect_minute.py"
        text = minute.read_text().split("def native_retired_ready(", 1)[1]
        self.assertIn("repair=False", text)
        self.assertIn("verify_retired(previous, queue)", text)
        self.assertNotIn("retire_stopped(", text)

    def test_public_wrapper_refuses_absent_original_fd9(self):
        with patch.object(gate, "require_lifecycle_lock",
                          side_effect=RuntimeError("no FD9")), \
             patch.object(gate, "_attest_quiescent") as read:
            with self.assertRaisesRegex(gate.QuiescentPreimageRefused, "FD9"):
                gate.attest_quiescent_under_fd9(
                    generation=self.f.generation, native=self.f.native,
                    effective=self.f.effective, enabled=True)
            read.assert_not_called()


    def test_disabled_cold_all_list_auto_schema1_mode_dispatch_without_wan(self):
        # Genuine filesystem/process/kernel cold guards remain exercised.
        # Inject ONLY original bound-root proof + WAL schema because this
        # existing real candidate fixture is specifically schema2 Auto ON.
        from types import SimpleNamespace
        self.cold()
        real = self.f.original.read()
        schema1 = {**real, "manifest": {**real["manifest"], "schema": 1}}
        for mode in ("all", "list", "auto"):
            with self.subTest(mode=mode), ExitStack() as stack:
                self.native_seams(stack)
                stack.enter_context(patch.object(
                    gate, "SharedApplyOperation",
                    return_value=Mock(read=Mock(return_value=schema1))))
                root = stack.enter_context(patch.object(
                    gate, "_attest_bound_candidate",
                    return_value=SimpleNamespace(
                        root_sha256=schema1["manifest"]["root_sha256"])))
                stack.enter_context(patch.object(
                    gate, "_native_preflight",
                    return_value={**self.config, "enabled": "0"}))
                wan = stack.enter_context(patch.object(
                    gate, "_native_wan",
                    side_effect=AssertionError("OFF must not require WAN")))
                proof = gate._attest_quiescent(
                    generation=self.f.generation,
                    native=replace(self.f.native, mode=mode),
                    effective=self.f.effective, enabled=False,
                    parent=self.f.parent, journal_root=self.f.journal_root,
                    owner_uid=os.geteuid(), active=self.active,
                    backups=self.backups, producer=self.producer,
                    epochs=self.epochs, pidfiles=self.pidfiles,
                    runner=self.runner)
                self.assertEqual(proof.old_state, "first-install-empty")
                self.assertIsNone(proof.verified_wan_device)
                self.assertEqual(root.call_count, 3)
                self.assertEqual(root.call_args.kwargs["mode"], mode)
                self.assertFalse(root.call_args.kwargs["schema3"])
                self.assertEqual(proof.authorization, "NONE")
                self.assertFalse(proof.physical_transition_allowed)
                wan.assert_not_called()

    def test_disabled_schema_mismatch_refuses_before_bound_read(self):
        self.cold()
        with ExitStack() as stack:
            self.native_seams(stack)
            bound = stack.enter_context(patch.object(
                gate, "_attest_bound_candidate"))
            for mode, enabled in (("all", True), ("list", False),
                                  ("auto", False)):
                with self.subTest(mode=mode, enabled=enabled), \
                     self.assertRaises(gate.QuiescentPreimageRefused):
                    gate._attest_quiescent(
                        generation=self.f.generation,
                        native=replace(self.f.native, mode=mode),
                        effective=self.f.effective, enabled=enabled,
                        parent=self.f.parent, journal_root=self.f.journal_root,
                        owner_uid=os.geteuid(), active=self.active,
                        backups=self.backups, producer=self.producer,
                        epochs=self.epochs, pidfiles=self.pidfiles,
                        runner=self.runner)
            bound.assert_not_called()


class StagedQuiescentTests(unittest.TestCase):
    def test_exact_stopped_preimage_and_rollback_stage_required(self):
        import json
        import tempfile
        from types import SimpleNamespace
        from voice_firewall_transaction import TABLE_PREFIX
        from shared_apply_seal import _stat
        generation, old, base, candidate = "a" * 32, "b" * 32, "c" * 64, "d" * 64
        record = {"phase": "activating",
                  "detail": {"id": generation, "base": base, "candidate": candidate},
                  "previous": {"id": old, "candidate": base},
                  "manifest": {"schema": 1, "root_sha256": "e" * 64}}
        preimage = gate.QuiescentPreimage(generation, "e" * 64, old, "f" * 64,
            base, candidate, "tun0", "committed-stopped",
            "native-managed-kernel-empty", "inert-no-producer-data")
        root = {"schema": 1, "generation": generation,
                "service": {"enabled": True, "target_mode": "list"}}
        key = TABLE_PREFIX + "telegram"
        manifest = {"rule_base": 19000, "rule_max": 19010,
                    "rules": {19000: ["divert"]}, "tables": {key: ["192.0.2.1"]}}
        tables = {key: ["192.0.2.1"], key + "_stage": []}
        adapter = SimpleNamespace(rule_base=19000, rule_max=19099,
            list_rules=Mock(return_value=manifest["rules"]),
            get_table=Mock(side_effect=lambda name: tables.get(name)))
        token = SimpleNamespace(pid=5432, started="original")

        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            active = Path(tmp) / "runtime-v2"
            backup = active.with_name("runtime-v2-backups") / f"runtime-v2-{generation}"
            active.mkdir()
            backup.mkdir(parents=True)
            actual_uid = active.stat().st_uid
            stack.enter_context(patch("sys.platform", "freebsd15"))
            stack.enter_context(patch("os.geteuid", return_value=0))
            stack.enter_context(patch.object(gate, "require_lifecycle_lock"))
            stack.enter_context(patch("auto_detect_original_lock_handoff.assert_inherited_config_fd"))
            stack.enter_context(patch.object(gate, "SharedApplyOperation",
                return_value=SimpleNamespace(read=lambda: record)))
            stack.enter_context(patch.object(gate, "COMMON_ACTIVE", active))
            stack.enter_context(patch("neutral_root_stage.verify_original_operation_pins"))
            stack.enter_context(patch("neutral_root_stage._verify_original_pinned_root",
                side_effect=lambda **kw: json.dumps(root).encode()))
            stack.enter_context(patch("neutral_root_stage._original_plan_matches", return_value=True))
            stack.enter_context(patch("shared_apply_seal._stat",
                side_effect=lambda path, uid, **kw: _stat(path, actual_uid, **kw)))
            tree = stack.enter_context(patch.object(gate, "_full_prior_tree",
                side_effect=lambda work, target, uid: "f" * 64 if target == backup else "2" * 64))
            stack.enter_context(patch.object(gate, "inspect_inert_release", return_value="inactive"))
            stack.enter_context(patch.object(gate, "_safe_empty_directory"))
            stack.enter_context(patch.object(gate, "shared_release_manifest", return_value=manifest))
            stack.enter_context(patch.object(gate, "FreeBSDIPFWAdapter", return_value=adapter))
            process = stack.enter_context(patch(
                "neutral_schema3_previous_physical._running_native", return_value=token))

            def run(**kw):
                args = dict(preimage=preimage, config_fd=4, config_digest=base)
                return gate.attest_bound_quiescent_staged_under_fd9(record, **(args | kw))

            def refuses(**kw):
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    run(**kw)

            result = run()
            self.assertEqual((result.backup_sha256, result.running), ("f" * 64, token))
            adapter.list_rules.assert_called_with(19000, 19099)
            refuses(config_digest=candidate)
            refuses(preimage=replace(preimage, retirement_state="original-epoch-ack-retired"))
            del tables[key + "_stage"]
            refuses()
            tables[key + "_stage"] = ["192.0.2.2"]
            refuses()
            tables[key + "_stage"] = []
            stage = active.parent / f".runtime-v2.stage.{generation}"
            stage.mkdir()
            refuses()
            stage.rmdir()
            tree.side_effect = lambda work, target, uid: "3" * 64
            refuses()
            tree.side_effect = lambda work, target, uid: "f" * 64 if target == backup else "2" * 64
            parent = backup.parent
            parked = parent.with_name("other-backups")
            parent.rename(parked)
            parent.symlink_to(parked, target_is_directory=True)
            refuses()
            parent.unlink()
            parked.rename(parent)
            process.side_effect = [token, SimpleNamespace(pid=5433)]
            refuses()
            process.side_effect = None
            record["phase"] = "activated"
            self.assertEqual(run().kernel_state, "native-managed-kernel-staged")
            self.assertEqual(run(saved=True, config_digest=candidate).observed_config_sha256,
                             candidate)
            refuses(saved=True)
            refuses(queue_fd=3)
            # Same original stopped predecessor, now a pinned learning
            # generation with a genuine old retirement receipt identity.
            from contextlib import nullcontext
            idle_identity = ((1, 2, 0, "0" * 64), (1, 3, 0, "0" * 64))
            retired = replace(preimage, retirement_state="original-epoch-ack-retired",
                              retired_ready_sha256="9" * 64, idle_producer=idle_identity)
            record["previous_manifest"] = {"schema": 2}
            queue = SimpleNamespace(inherited_exclusive=Mock(return_value=nullcontext()))
            receipts = object()
            stack.enter_context(patch("auto_detect_post_drop._original_epoch_queue",
                                      return_value=(queue, receipts)))
            history = stack.enter_context(patch.object(gate, "_verify_retired_history"))
            idle = stack.enter_context(patch.object(gate, "_verify_idle_producer",
                                                    return_value=idle_identity))
            refuses(preimage=retired)
            self.assertEqual(run(preimage=retired, queue_fd=3).retired_ready_sha256,
                             "9" * 64)
            self.assertEqual(run(preimage=retired, queue_fd=3).idle_producer,
                             idle_identity)
            queue.inherited_exclusive.assert_called_with(3)
            history.assert_called_with(record, queue, receipts, "9" * 64)
            history.side_effect = ValueError("archive drift")
            refuses(preimage=retired, queue_fd=3)
            history.side_effect = None
            idle.side_effect = ValueError("retired root data")
            refuses(preimage=retired, queue_fd=3)
            idle.side_effect = None
            # Next inert Apply still sees the same canonical idle producer;
            # it must not require deleting it or inventing a second epoch.
            record.pop("previous_manifest")
            inert_idle = replace(preimage, retirement_state="inert-idle-producer",
                                 idle_producer=idle_identity)
            history.reset_mock()
            self.assertEqual(run(preimage=inert_idle, queue_fd=3).idle_producer, idle_identity)
            history.assert_not_called()
            idle.return_value = ((1, 4, 0, "0" * 64), idle_identity[1])
            refuses(preimage=inert_idle, queue_fd=3)
            record["phase"] = "config-saved"
            refuses(preimage=retired, queue_fd=3)

    def test_internal_activated_writer_cannot_accept_foreign_receipt(self):
        from types import SimpleNamespace
        from shared_apply_operation import SharedApplyOperation, DEFAULT_ROOT
        generation, base = "a" * 32, "b" * 64
        record = {"phase": "activating", "detail": {"id": generation, "base": base},
                  "manifest": {"schema": 1, "root_sha256": "c" * 64}}
        receipt = gate.StagedBoundRuntimeReceipt(generation, "c" * 64, base,
            "d" * 64, None, None, "native-managed-kernel-empty", base)
        def advance(phase, expected, attest):
            self.assertEqual((phase, expected), ("activated", record))
            if not attest():
                raise SharedOperationError("witness refused")
            return dict(record, phase=phase)
        store = SimpleNamespace(root=DEFAULT_ROOT, owner=0, read=lambda: record,
                                _advance_bound_ordinary=Mock(side_effect=advance))
        with patch.object(gate, "attest_bound_quiescent_staged_under_fd9",
                          return_value=receipt) as physical:
            def activate():
                return SharedApplyOperation._record_native_bound_activated(
                    store, record, preimage=None, config_fd=4, config_digest=base)
            activated, evidence = activate()
            self.assertEqual(activated["phase"], "activated")
            self.assertEqual(evidence, receipt)
            physical.return_value = replace(receipt, root_sha256="e" * 64)
            with self.assertRaises(SharedOperationError):
                activate()
            record["found"] = {"runtime_mode": "0"}
            physical.reset_mock()
            with self.assertRaises(SharedOperationError):
                activate()
            physical.assert_not_called()


    def test_internal_first_running_activated_pins_exact_identity_before_save(self):
        from types import SimpleNamespace
        from shared_apply_operation import SharedApplyOperation, DEFAULT_ROOT, _first_running_pin_matches
        from neutral_schema3_previous_physical import PriorRunningToken
        generation, base, root = "a" * 32, "b" * 64, "c" * 64
        record = {"phase": "activating", "detail": {"id": generation, "base": base},
                  "manifest": {"schema": 1, "root_sha256": root}}
        running = PriorRunningToken(123, "birth", 456, "supervisor-birth", "d" * 64)
        receipt = gate.StagedBoundRuntimeReceipt(generation, root, base,
            "e" * 64, None, running, "native-managed-kernel-staged", base)

        def advance(phase, expected, attest, *, first_running_sha256):
            self.assertEqual((phase, expected, first_running_sha256),
                             ("activated", record, "f" * 64))
            if not attest():
                raise SharedOperationError("witness refused")
            return dict(record, phase=phase, first_running_sha256=first_running_sha256)

        store = SimpleNamespace(root=DEFAULT_ROOT, owner=0, read=lambda: record,
                                _advance_bound_ordinary=Mock(side_effect=advance))
        with patch.object(gate, "attest_bound_quiescent_staged_under_fd9",
                          return_value=receipt), \
                patch.object(gate, "_first_running_digest", return_value="f" * 64) as digest:
            def activate():
                return SharedApplyOperation._record_native_bound_activated(
                    store, record, preimage=None, config_fd=4, config_digest=base)

            activated, evidence = activate()
            self.assertEqual(evidence, receipt)
            self.assertEqual(activated["first_running_sha256"], "f" * 64)
            self.assertTrue(_first_running_pin_matches(activated, running, 4))
            self.assertFalse(_first_running_pin_matches(record, running, 4))
            digest.side_effect = ["f" * 64, "0" * 64]
            with self.assertRaises(SharedOperationError):
                activate()

    def test_first_learning_activation_pins_original_pretraffic_and_running_together(self):
        from types import SimpleNamespace
        from shared_apply_operation import (SharedApplyOperation, DEFAULT_ROOT,
            _first_running_pin_matches, _validate_first_running_pin)
        from neutral_schema3_previous_physical import PriorRunningToken
        generation, base, root = "a" * 32, "b" * 64, "c" * 64
        record = {"phase": "activating", "detail": {"id": generation, "base": base},
                  "manifest": {"schema": 2, "root_sha256": root}}
        running = PriorRunningToken(123, "birth", 456, "supervisor-birth", "d" * 64)
        receipt = gate.StagedBoundRuntimeReceipt(generation, root, base,
            "e" * 64, None, running, "native-managed-kernel-staged", base, "1" * 64)

        def advance(phase, expected, attest, **pins):
            self.assertEqual((phase, expected), ("activated", record))
            self.assertEqual(pins, {"first_running_sha256": "f" * 64,
                                    "first_pretraffic_sha256": "1" * 64})
            if not attest():
                raise SharedOperationError("witness refused")
            result = dict(record, phase=phase, **pins)
            _validate_first_running_pin(result)
            return result

        store = SimpleNamespace(root=DEFAULT_ROOT, owner=0, read=lambda: record,
                                _advance_bound_ordinary=Mock(side_effect=advance))
        with patch.object(gate, "attest_bound_quiescent_staged_under_fd9",
                          return_value=receipt) as physical, \
                patch.object(gate, "_first_running_digest", return_value="f" * 64):
            def activate():
                return SharedApplyOperation._record_native_bound_activated(
                    store, record, preimage=None, config_fd=4, config_digest=base, queue_fd=3)

            activated, evidence = activate()
            self.assertEqual(evidence, receipt)
            for phase in ("activated", "epoch-finalizing", "committed"):
                saved = dict(activated, phase=phase)
                self.assertTrue(_first_running_pin_matches(saved, running, 4,
                    pretraffic_sha256=receipt.pretraffic_sha256))
                self.assertFalse(_first_running_pin_matches(saved, running, 4,
                    pretraffic_sha256="0" * 64))
            for key in ("first_running_sha256", "first_pretraffic_sha256"):
                partial = dict(activated)
                partial.pop(key)
                with self.assertRaises(SharedOperationError):
                    _validate_first_running_pin(partial)
            with self.assertRaises(SharedOperationError):
                _validate_first_running_pin(dict(activated, phase="config-saved"))
            physical.side_effect = [receipt, replace(receipt, pretraffic_sha256="0" * 64)]
            with self.assertRaises(SharedOperationError):
                activate()

    def test_internal_saved_writer_requires_same_activated_runtime(self):
        from types import SimpleNamespace
        from shared_apply_operation import SharedApplyOperation, DEFAULT_ROOT
        generation, base, candidate, root = "a" * 32, "b" * 64, "c" * 64, "d" * 64
        record = {"phase": "activated", "detail": {"id": generation, "base": base,
                                                   "candidate": candidate},
                  "manifest": {"schema": 1, "root_sha256": root}}
        calls = []
        receipt = gate.StagedBoundRuntimeReceipt(generation, root, base,
            "e" * 64, None, SimpleNamespace(pid=5432), "native-managed-kernel-staged", base)
        def advance(phase, expected, attest):
            self.assertEqual(expected, record)
            calls.append(phase)
            if not attest():
                raise SharedOperationError("witness refused")
            return dict(record, phase=phase)
        store = SimpleNamespace(root=DEFAULT_ROOT, owner=0, read=lambda: record,
                                _advance_bound_ordinary=Mock(side_effect=advance))
        with patch("sys.platform", "freebsd15"), patch("os.geteuid", return_value=0), \
                patch("voice_ipfw_adapter.require_lifecycle_lock"), \
                patch("auto_detect_original_lock_handoff.assert_inherited_config_fd"), \
                patch("os.fsync", side_effect=lambda fd: calls.append(("fsync", fd))), \
                patch("shared_apply_operation._first_running_pin_matches", return_value=True), \
                patch.object(gate, "attest_bound_quiescent_staged_under_fd9",
                             return_value=replace(receipt, observed_config_sha256=candidate)) as physical:
            def saved(evidence=receipt, digest=candidate, queue_fd=None):
                return SharedApplyOperation._record_native_bound_saved(
                    store, record, preimage=None, activated_receipt=evidence,
                    config_fd=4, config_digest=digest, queue_fd=queue_fd)
            self.assertEqual(saved()["phase"], "config-saved")
            self.assertEqual(calls, [("fsync", 4), "config-saved"])
            physical.assert_called_with(record, preimage=None, config_fd=4,
                                       config_digest=candidate, queue_fd=None, saved=True)
            calls.clear()
            with self.assertRaises(SharedOperationError):
                saved(digest=base)
            self.assertEqual(calls, [])
            physical.return_value = replace(receipt, observed_config_sha256=candidate,
                                            running=SimpleNamespace(pid=5433))
            with self.assertRaises(SharedOperationError):
                saved()
            record["manifest"]["schema"] = 2
            learning = replace(receipt, pretraffic_sha256="f" * 64)
            physical.return_value = replace(learning, observed_config_sha256=candidate)
            self.assertEqual(saved(learning, queue_fd=3)["phase"], "epoch-finalizing")
            physical.return_value = replace(learning, observed_config_sha256=candidate,
                                            pretraffic_sha256="0" * 64)
            with self.assertRaises(SharedOperationError):
                saved(learning, queue_fd=3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
