#!/usr/bin/env python3
"""TZ6v2 original P2 destination owner: reversible 3-source file write tests.

No new CLI, no Config writer, no service, no FD9 fake. These unit tests call
only the private already-locked helper with disposable root-owned files. The
public original-FD9 entry refuses on non-native hosts.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

BACKEND = (Path(__file__).resolve().parents[1] / "src/opnsense/scripts"
           / "OPNsense/Zapret/backend")
sys.path.insert(0, str(BACKEND))

from auto_detect_gui_hostlist import _create
import auto_detect_destination_commit as destination
from shared_apply_operation import SharedApplyOperation, SharedOperationError
from shared_apply_found_stage import FoundStageRefused, qualify_readonly
from auto_detect_destination_commit import (
    DestinationRefused, SHARED_FOUND_NAMES, _locked_shared_found_replace,
    _locked_shared_found_apply_journal,
    _replace, _plan_shared_found_under_original_locks,
    _shared_found_assert_missing,
    shared_apply_found_files_original_fd9,
)


def sha(data: bytes) -> str:
    return hashlib.sha256(b"present\0" + data).hexdigest()


class OriginalFoundFileBatchTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="original-fd9-found-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.root.chmod(0o700)
        self.uid = os.geteuid()
        self.targets = {
            name: self.root / (name + ".txt") for name in SHARED_FOUND_NAMES
        }
        self.old = {"youtube": "example.com\n", "user": "example.org\n",
                    "auto": ""}
        self.new = {"youtube": "example.com\nfresh.com\n", "user": "",
                    "auto": "shared.org\n"}
        for name, path in self.targets.items():
            path.write_text(self.old[name])
            path.chmod(0o600)

    def plan(self, new=None):
        new = self.new if new is None else new
        rows = {}
        for name, path in self.targets.items():
            before = self.old[name].encode()
            st = path.lstat()
            rows[name] = {
                "before": before.decode(), "after": new[name],
                "before_status": "present",
                "before_revision": sha(before),
                "before_device": st.st_dev, "before_inode": st.st_ino,
                "before_ctime_ns": st.st_ctime_ns,
                "before_mtime_ns": st.st_mtime_ns, "before_size": st.st_size,
            }
        return rows

    def test_lossless_php_uint64_native_identity_preserves_preimage_pin(self):
        # Python native st_dev/st_ino can exceed PHP_INT_MAX on FreeBSD.
        # The root PHP response must preserve exact decimal digits, not
        # float-round and thereby weaken the original P2 preimage check.
        qualified = destination._qualified_shared_found_batch
        oversized = (1 << 63) + 12345
        identity_keys = ("before_device", "before_inode",
                         "before_ctime_ns", "before_mtime_ns")
        for key in identity_keys:
            with self.subTest(field=key):
                rows = self.plan()
                rows["youtube"][key] = oversized
                original = qualified(rows)
                rows["youtube"][key] = str(oversized)
                transported = qualified(json.loads(json.dumps(rows)))
                self.assertEqual(transported, original)
                self.assertEqual(transported["youtube"][2][
                    ("before_device", "before_inode", "before_ctime_ns",
                     "before_mtime_ns", "before_size").index(key)], oversized)
                for malformed in (float(oversized), str(1 << 64),
                                  "0" + str(oversized), "123", -1, True):
                    rows["youtube"][key] = malformed
                    with self.assertRaisesRegex(
                            DestinationRefused, "shared_found_candidate_shape"):
                        qualified(rows)
        # The real file's physical stat must still match the decoded pin:
        # accepted JSON shape is not permission to adopt foreign inode data.
        rows = self.plan()
        rows["youtube"]["before_device"] = str(oversized)
        with self.assertRaisesRegex(
                DestinationRefused, "shared_found_preimage_changed"):
            self.apply(rows)
        self.assert_old()

    def apply(self, plan=None, **kwargs):
        return _locked_shared_found_replace(
            self.plan() if plan is None else plan, self.targets,
            uid=self.uid, **kwargs)

    def assert_old(self):
        self.assertEqual(
            {name: path.read_text() for name, path in self.targets.items()},
            self.old)


    def journaled(self, *, rows=None, witness=None, runtime_mode=None, **kwargs):
        rows = self.plan() if rows is None else rows
        d = {"id": "b" * 32, "page": "strategies",
             "base": "a" * 64, "candidate": "c" * 64,
             "changed_fields": []}
        body = json.dumps({
            "page": "strategies", "result": "prepared",
            "dependencies": d["base"], "changed_fields": [],
            "found_intent": {"config_revision": d["base"],
                             "commit_authorized": False},
            "found_batch": rows,
        }, separators=(",", ":")).encode()
        journal = SharedApplyOperation(self.root / "shared-apply",
                                       owner=self.uid)
        journal.prepare_found(d, body, lambda _: True, runtime_mode=runtime_mode)
        callback = (lambda phase, raw: raw == body) if witness is None else witness
        return journal, d, body, lambda: _locked_shared_found_apply_journal(
            rows, self.targets, store=journal, detail=d,
            plan_bytes=body, uid=self.uid, attest=callback, **kwargs)


    def test_each_changed_file_is_durable_ready_before_rename(self):
        journal, _, _, apply = self.journaled()
        import auto_detect_destination_commit as destination
        from unittest.mock import patch
        rename = destination.os.replace
        seen = []

        def guarded_rename(source, target):
            if Path(target) in self.targets.values():
                name = next(n for n, p in self.targets.items() if p == Path(target))
                staged = journal.read()["found"]["stages"].get(name)
                self.assertIsNotNone(staged)
                self.assertEqual(staged["state"], "ready")
                tmp_stat = Path(source).lstat()
                self.assertEqual((staged["pin"]["device"], staged["pin"]["inode"]),
                                 (tmp_stat.st_dev, tmp_stat.st_ino))
                seen.append(name)
            return rename(source, target)

        with patch.object(destination.os, "replace", side_effect=guarded_rename):
            receipt = apply()
        self.assertEqual(receipt["journal_phase"], "found-files-written")
        self.assertEqual(seen, ["youtube", "user", "auto"])
        staged = journal.read()["found"]["stages"]
        self.assertEqual(set(staged), set(seen))
        self.assertTrue(all(row["state"] == "installed" for row in staged.values()))

    def test_stage_ready_durable_failure_protects_first_destination(self):
        journal, _, _, apply = self.journaled()
        original_advance = journal.advance_found_stage
        seen = []

        def fail_after_file_stage(detail, raw, name, phase, pin, attest):
            seen.append((name, phase))
            if phase == "ready":
                raise OSError("simulated stage WAL fsync")
            return original_advance(detail, raw, name, phase, pin, attest)

        journal.advance_found_stage = fail_after_file_stage
        with self.assertRaisesRegex(OSError, "simulated stage WAL fsync"):
            apply()
        self.assertEqual(seen, [("youtube", "ready")])
        self.assert_old()
        self.assertEqual(journal.read()["phase"], "found-files-writing")

    def test_stage_identity_drift_after_ready_leaves_original_destination(self):
        journal, _, _, apply = self.journaled()
        original_advance = journal.advance_found_stage
        target = self.targets["youtube"]
        original_identity = destination._file_identity(target.lstat())
        replacement = self.root / "replacement.tmp"
        replacement.write_text(self.new["youtube"])
        replacement.chmod(0o600)
        observed = {}

        def advance_then_drift(detail, raw, name, phase, pin, attest):
            original_advance(detail, raw, name, phase, pin, attest)
            if name == "youtube" and phase == "ready":
                temp = target.with_name(pin["temp"])
                replacement.replace(temp)
                observed["path"] = temp
                observed["identity"] = destination._file_identity(temp.lstat())

        journal.advance_found_stage = advance_then_drift
        with self.assertRaises(DestinationRefused):
            apply()
        self.assert_old()
        self.assertEqual(destination._file_identity(target.lstat()), original_identity)
        self.assertEqual(destination._file_identity(observed["path"].lstat()),
                         observed["identity"])
        current = journal.read()
        self.assertEqual(current["phase"], "found-files-writing")
        stage = current["found"]["stages"]["youtube"]
        self.assertEqual(stage["state"], "ready")
        self.assertNotEqual(stage["pin"]["inode"], observed["identity"][1])

    def test_stage_installed_fsync_failure_keeps_ambiguous_wal(self):
        journal, _, _, apply = self.journaled()
        original_advance = journal.advance_found_stage

        def fail_post_rename(detail, raw, name, phase, pin, attest):
            if name == "youtube" and phase == "installed":
                raise OSError("simulated postrename WAL fsync")
            return original_advance(detail, raw, name, phase, pin, attest)

        journal.advance_found_stage = fail_post_rename
        with self.assertRaisesRegex(OSError, "simulated postrename WAL fsync"):
            apply()
        # Physical rename has happened, but WRITTEN is never asserted.
        self.assertEqual(journal.read()["phase"], "found-files-writing")
        self.assertEqual(journal.read()["found"]["stages"]["youtube"]["state"], "ready")
        self.assertEqual(self.targets["youtube"].read_text(), self.new["youtube"])

    def test_journal_original_wal_before_first_three_file_write(self):
        journal, detail, raw, apply = self.journaled()
        receipt = apply()
        self.assertEqual(receipt["journal_phase"], "found-files-written")
        self.assertFalse(receipt["config_committed"])
        self.assertFalse(receipt["commit_authorized"])
        self.assertEqual(journal.read()["phase"], "found-files-written")
        pins = journal.read()["found"]["post"]
        # The original FD9 journal canonicalizes JSON dict keys alphabetically.
        self.assertEqual(set(pins), set(SHARED_FOUND_NAMES))
        for name, path in self.targets.items():
            st = path.lstat()
            self.assertEqual((pins[name]["device"], pins[name]["inode"],
                              pins[name]["ctime_ns"], pins[name]["mtime_ns"]),
                             (st.st_dev, st.st_ino, st.st_ctime_ns, st.st_mtime_ns))
        self.assertEqual({name: path.read_text()
                          for name, path in self.targets.items()}, self.new)
        with self.assertRaises(SharedOperationError):
            journal.advance("committed", detail)
        with self.assertRaises(SharedOperationError):
            journal.advance("restored", detail)
        with self.assertRaises(DestinationRefused):
            apply()

    def test_original_journal_refuses_same_bytes_different_inode_after_write(self):
        # After writer-captured pins but before its durable WRITTEN record,
        # replacing a name with identical bytes is NOT valid provenance.
        journal, _, _, apply = self.journaled()
        native_target = self.targets["youtube"]
        original_target = __import__("auto_detect_destination_commit")
        original_qualified = original_target._qualified_shared_found_batch
        call = [0]
        def after_cas(rows):
            call[0] += 1
            if call[0] > 2:
                temp = native_target.with_name("foreign-same-bytes.tmp")
                temp.write_bytes(native_target.read_bytes())
                temp.chmod(0o600)
                os.replace(temp, native_target)
            return original_qualified(rows)
        from unittest.mock import patch
        with patch.object(original_target, "_qualified_shared_found_batch",
                          side_effect=after_cas):
            with self.assertRaisesRegex(
                    DestinationRefused, "shared_found_writer_postimage_changed"):
                apply()
        self.assertEqual(journal.read()["phase"], "found-files-writing")
        self.assertFalse(journal.advisory()["safe_to_mutate"])

    def test_journal_fsync_failure_before_first_write_preserves_files(self):
        journal, _, _, apply = self.journaled()
        journal._persist_record = lambda _: (_ for _ in ()).throw(
            OSError("simulated original journal fsync refusal"))
        with self.assertRaises(OSError):
            apply()
        self.assert_old()

    def recover(self, journal, body, attest=lambda: True):
        return destination._recover_found_preimages_locked(
            json.loads(body)["found_batch"], self.targets, store=journal,
            record=journal.read(), plan_bytes=body, uid=self.uid, attest=attest)

    def test_journal_rollback_resumes_after_partial_write_and_rollback_crash(self):
        journal, _, body, apply = self.journaled()
        rename = os.replace

        def second_fails(temp, target):
            if target == self.targets["user"]:
                raise OSError("file 2 pre-rename")
            rename(temp, target)

        with patch.object(destination.os, "replace", side_effect=second_fails):
            with self.assertRaisesRegex(OSError, "file 2 pre-rename"):
                apply()
        self.assertEqual(journal.read()["phase"], "found-files-writing")
        self.assertFalse(journal.advisory()["safe_to_mutate"])
        self.assertEqual(self.targets["youtube"].read_text(), self.new["youtube"])
        self.assertEqual(self.targets["user"].read_text(), self.old["user"])

        def crash_after_rollback_rename(temp, target):
            rename(temp, target)
            if target == self.targets["youtube"]:
                raise OSError("rollback interrupted after rename")

        with patch.object(destination.os, "replace", side_effect=crash_after_rollback_rename):
            with self.assertRaisesRegex(OSError, "rollback interrupted"):
                self.recover(journal, body)
        self.assertEqual(journal.read()["phase"], "found-restoring")
        self.assertEqual(self.recover(journal, body)["phase"], "restored")
        self.assert_old()

    def test_recovery_refuses_all_writes_on_same_byte_source_substitution(self):
        journal, _, body, apply = self.journaled()
        apply()
        foreign = self.root / "foreign"
        foreign.write_text(self.new["user"])
        foreign.replace(self.targets["user"])
        with self.assertRaisesRegex(DestinationRefused, "foreign_found_source"):
            self.recover(journal, body)
        self.assertEqual(journal.read()["phase"], "found-files-written")
        self.assertEqual(self.targets["youtube"].read_text(), self.new["youtube"])

    def test_uncertain_config_save_follows_proven_base_or_candidate(self):
        import auto_detect_effective_known as effective
        import voice_live_inspect as runtime

        for unchanged in (True, False):
            with self.subTest(config_unchanged=unchanged):
                for name, path in self.targets.items():
                    path.write_text(self.old[name])
                journal, detail, body, apply = self.journaled(runtime_mode="1")
                apply()
                journal.advance_found_config("found-config-saving", detail, body,
                                             lambda *_: True)
                record = journal.read()
                context = (journal, record, body, json.loads(body)["found_batch"],
                           self.targets, lambda: True)
                fd = os.open(self.root / "native-config", os.O_RDWR | os.O_CREAT, 0o600)
                try:
                    with (patch.object(destination, "_native_found_wal_context", return_value=context),
                          patch.object(effective, "AUTO_LOCK", self.root / "p2.lock"),
                          patch.object(effective, "read_owned", return_value={}),
                          patch.object(runtime, "examine_pending_found_previous",
                                       return_value={"state": "stopped", "id": "d" * 32})):
                        with self.assertRaisesRegex(effective.EffectiveKnownRefused,
                                                    "found_candidate_config_not_saved"):
                            effective.advance_native_found_locked(
                                "recover-found-locked", detail["id"], "e" * 64, config_fd=fd)
                        self.assertEqual(journal.read(), record)
                        digest = detail["base"] if unchanged else detail["candidate"]
                        if unchanged:
                            receipt = effective.advance_native_found_locked(
                                "recover-found-locked", detail["id"], digest, config_fd=fd)
                        else:
                            # Cold candidate bytes alone MUST NOT promote an
                            # uncertain save to a confirmed WAL checkpoint.
                            with self.assertRaisesRegex(
                                    effective.EffectiveKnownRefused,
                                    "found_config_save_candidate_uncertain_requires_review"):
                                effective.advance_native_found_locked(
                                    "recover-found-locked", detail["id"], digest,
                                    config_fd=fd)
                            self.assertEqual(journal.read(), record)
                            self.assertFalse(journal.advisory()["safe_to_mutate"])
                            # Only the *original returning* PHP save/readback
                            # path is allowed to issue this separate confirm.
                            receipt = effective.advance_native_found_locked(
                                "confirm-found-save-locked", detail["id"],
                                digest, config_fd=fd)
                finally:
                    os.close(fd)
                if unchanged:
                    self.assertEqual(receipt, {"result": "restored"})
                    self.assert_old()
                else:
                    self.assertEqual(receipt, {"result": "found-config-saved", "mode": "1"})
                    self.assertFalse(journal.advisory()["safe_to_mutate"])
                    self.assertEqual({name: path.read_text()
                                      for name, path in self.targets.items()}, self.new)
                (journal.root / "operation.json").unlink()
                journal.root.rmdir()

    def test_recovery_removes_only_its_interrupted_link_once_create(self):
        self.targets["auto"].unlink()
        rows, _ = self.proposed(draft={"youtube": self.new["youtube"], "user": self.new["user"],
                                        "auto": self.new["auto"]}, baseline=self.missing_base())
        journal, _, body, apply = self.journaled(rows=rows)
        link = os.link
        ready_link = []

        def interrupted_link(temp, target, **kwargs):
            result = link(temp, target, **kwargs)
            if target == self.targets["auto"]:
                ready_link.append(temp)
            return result

        # Emulate process death after link, before the original temp unlink.
        unlink = Path.unlink

        def skip_temp_unlink(path, *args, **kwargs):
            if path in ready_link:
                raise OSError("crashed before temp unlink")
            return unlink(path, *args, **kwargs)

        with patch.object(destination.os, "link", side_effect=interrupted_link):
            with patch.object(Path, "unlink", skip_temp_unlink):
                with self.assertRaisesRegex(OSError, "crashed before temp unlink"):
                    apply()
        self.assertEqual(self.targets["auto"].lstat().st_nlink, 2)
        self.assertEqual(self.recover(journal, body)["phase"], "restored")
        self.assertFalse(self.targets["auto"].exists())
        self.assertFalse(ready_link[0].exists())

    def test_journal_postwrite_witness_refusal_leaves_nonterminal_physical_after(self):
        journal, _, _, apply = self.journaled(
            witness=lambda phase, raw:
                phase == "found-files-writing" or phase.startswith("found-stage-"))
        with self.assertRaisesRegex(SharedOperationError, "witness refused"):
            apply()
        self.assertEqual(journal.read()["phase"], "found-files-writing")
        self.assertEqual({name: path.read_text()
                          for name, path in self.targets.items()}, self.new)

    def test_journal_missing_shared_auto_create_and_crash_boundary(self):
        self.targets["auto"].unlink()
        self.old["auto"] = ""
        baseline = self.missing_base()
        rows, _ = self.proposed(
            baseline=baseline, draft=dict(self.old, auto="shared.org\n"))
        journal, _, _, apply = self.journaled(rows=rows)
        receipt = apply()
        self.assertEqual(receipt["files"]["auto"]["before_status"], "missing")
        self.assertTrue(receipt["files"]["auto"]["changed"])
        self.assertEqual(self.targets["auto"].read_text(), "shared.org\n")
        self.assertEqual(journal.read()["phase"], "found-files-written")

    def test_complete_three_source_apply_has_only_files_receipt(self):
        applied = self.apply()
        self.assertEqual(applied["result"], "files-applied-under-original-transaction")
        self.assertEqual(
            {name: path.read_text() for name, path in self.targets.items()},
            self.new)
        self.assertFalse(applied["config_committed"])
        self.assertFalse(applied["commit_authorized"])
        self.assertEqual(list(applied["files"]), list(SHARED_FOUND_NAMES))

    def test_preflight_checks_all_sources_before_first_replace(self):
        rows = self.plan()
        self.targets["user"].write_text("background.org\n")
        with self.assertRaisesRegex(DestinationRefused,
                                    "shared_found_preimage_changed"):
            self.apply(rows)
        self.assertEqual(self.targets["youtube"].read_text(), self.old["youtube"])
        self.assertEqual(self.targets["auto"].read_text(), self.old["auto"])
        self.assertEqual(self.targets["user"].read_text(), "background.org\n")

    def test_inode_swap_even_identical_bytes_refuses(self):
        rows = self.plan()
        path = self.targets["user"]
        path.rename(self.root / "old-user.txt")
        path.write_text(self.old["user"])
        path.chmod(0o600)
        with self.assertRaisesRegex(DestinationRefused,
                                    "shared_found_preimage_changed"):
            self.apply(rows)
        self.assertEqual(self.targets["youtube"].read_text(), self.old["youtube"])

    def test_symlink_target_refuses_before_any_write(self):
        rows = self.plan()
        path = self.targets["auto"]
        path.unlink()
        path.symlink_to(self.root / "missing-foreign")
        with self.assertRaises(DestinationRefused):
            self.apply(rows)
        self.assert_old_others()

    def assert_old_others(self):
        self.assertEqual(self.targets["youtube"].read_text(), self.old["youtube"])
        self.assertEqual(self.targets["user"].read_text(), self.old["user"])

    def test_canonical_positive_only_and_revision_required(self):
        for change in (
            lambda r: r["youtube"].update(after="!example.com\n"),
            lambda r: r["youtube"].update(after="^example.com\n"),
            lambda r: r["youtube"].update(after="two.example.com\nexample.org\n"),
            lambda r: r["user"].update(before_revision="0" * 64),
            lambda r: r["auto"].update(before_inode=0),
            lambda r: r["auto"].update(after="example.unknownsuffix\n"),
        ):
            with self.subTest(change=repr(change)):
                rows = self.plan()
                change(rows)
                with self.assertRaises((DestinationRefused, ValueError)):
                    self.apply(rows)
                self.assert_old()

    def test_after_first_write_fault_compensates_old_bytes(self):
        counter = [0]
        def abort_on_second(path, before, after, uid):
            counter[0] += 1
            if counter[0] == 2:
                raise OSError("test-only before rename")
            return _replace(path, before, after, uid)

        with self.assertRaisesRegex(DestinationRefused,
                                    "shared_found_restored_after_failure"):
            self.apply(replace_fn=abort_on_second)
        self.assert_old()
        self.assertEqual(counter[0], 3)

    def test_after_second_physical_write_without_pin_requires_review(self):
        counter = [0]
        def abort_after_second(path, before, after, uid):
            counter[0] += 1
            _replace(path, before, after, uid)
            if counter[0] == 2:
                raise OSError("test-only after durable replace")

        # The second writer returned no inode witness after its rename.
        # Even though bytes match AFTER, compensation must not overwrite
        # a potentially foreign inode or claim safely restored.
        with self.assertRaisesRegex(DestinationRefused,
                                    "shared_found_requires_review"):
            self.apply(replace_fn=abort_after_second)
        self.assertEqual(self.targets["youtube"].read_text(), self.new["youtube"])
        self.assertEqual(self.targets["user"].read_text(), self.new["user"])
        self.assertEqual(self.targets["auto"].read_text(), self.old["auto"])

    def test_atomic_replace_refuses_same_inode_same_bytes_change_during_temp_fsync(self):
        # Reproduce a foreign in-place write after initial _target() but
        # BEFORE os.replace(temp, target). A device/inode-only CAS misses it.
        from unittest.mock import patch
        import auto_detect_destination_commit as destination
        target = self.targets["youtube"]
        old = target.read_bytes()
        native_fsync = destination.os.fsync
        touched = [False]
        def change_during_temp(fd):
            result = native_fsync(fd)
            if not touched[0]:
                st = target.lstat()
                os.utime(target, ns=(st.st_atime_ns,
                                     st.st_mtime_ns + 2_000_000_000))
                touched[0] = True
            return result
        with patch.object(destination.os, "fsync",
                          side_effect=change_during_temp):
            with self.assertRaisesRegex(
                    DestinationRefused, "destination_conflict_with_gui"):
                _replace(target, old, self.new["youtube"].encode(), self.uid)
        self.assertTrue(touched[0])
        self.assertEqual(target.read_bytes(), old)
        self.assertFalse(any(
            child.name.startswith(".auto-detect-") for child in self.root.iterdir()))

    def test_later_source_same_bytes_foreign_touch_before_rename_refused(self):
        # Replacing YouTube takes time. An out-of-lock in-place writer
        # touches User but leaves its bytes/ino unchanged before User's CAS.
        user = self.targets["user"]
        original = user.read_bytes()
        changed = [False]
        def touch_user_after_youtube(path, before, after, uid):
            _replace(path, before, after, uid)
            if path == self.targets["youtube"]:
                st = user.lstat()
                os.utime(user, ns=(st.st_atime_ns,
                                   st.st_mtime_ns + 2_000_000_000))
                changed[0] = True
        with self.assertRaisesRegex(
                DestinationRefused, "shared_found_requires_review"):
            self.apply(replace_fn=touch_user_after_youtube)
        self.assertTrue(changed[0])
        self.assertEqual(user.read_bytes(), original)
        self.assertEqual(self.targets["youtube"].read_text(),
                         self.old["youtube"])
        self.assertEqual(self.targets["auto"].read_text(),
                         self.old["auto"])

    def test_rollback_rejects_same_inode_same_bytes_timestamp_change(self):
        # A foreign in-place writer may leave EXACTLY the same bytes and inode
        # but change ctime/mtime. A dev+inode-only rollback would overwrite it.
        youtube = self.targets["youtube"]
        def modify_first_after_write(path, before, after, uid):
            if path == self.targets["user"]:
                st = youtube.lstat()
                os.utime(youtube, ns=(st.st_atime_ns,
                                      st.st_mtime_ns + 2_000_000_000))
                raise OSError("foreign in-place touch before second rename")
            return _replace(path, before, after, uid)
        with self.assertRaisesRegex(DestinationRefused,
                                    "shared_found_requires_review"):
            self.apply(replace_fn=modify_first_after_write)
        self.assertEqual(youtube.read_text(), self.new["youtube"])
        self.assertEqual(self.targets["user"].read_text(), self.old["user"])
        self.assertEqual(self.targets["auto"].read_text(), self.old["auto"])

    def test_untouched_same_byte_inode_swap_never_reports_compensated(self):
        # Three-source CAS must attest an untouched source's ORIGINAL inode,
        # not record a foreign inode as a qualified post-image. Even if prior
        # changed files were compensated, a foreign unchanged file remains.
        new = dict(self.new, auto=self.old["auto"])
        rows = self.plan(new)
        unchanged = self.targets["auto"]
        foreign_pin = [None]
        def replace_and_swap(path, before, after, uid):
            result = _replace(path, before, after, uid)
            if path == self.targets["youtube"]:
                candidate = self.root / "foreign-equal-auto.tmp"
                candidate.write_bytes(unchanged.read_bytes())
                candidate.chmod(0o600)
                os.replace(candidate, unchanged)
                st = unchanged.lstat()
                foreign_pin[0] = (st.st_dev, st.st_ino)
            return result
        with self.assertRaisesRegex(DestinationRefused,
                                    "shared_found_requires_review"):
            self.apply(plan=rows, replace_fn=replace_and_swap)
        self.assertIsNotNone(foreign_pin[0])
        st = unchanged.lstat()
        self.assertEqual(foreign_pin[0], (st.st_dev, st.st_ino))
        self.assertEqual(unchanged.read_text(), self.old["auto"])
        self.assertEqual(self.targets["youtube"].read_text(), self.old["youtube"])
        self.assertEqual(self.targets["user"].read_text(), self.old["user"])

    def test_rollback_refuses_same_byte_foreign_inode(self):
        calls = [0]
        youtube = self.targets["youtube"]
        def swap_then_fail(path, before, after, uid):
            calls[0] += 1
            if calls[0] == 2:
                temp = self.root / "foreign-twin.tmp"
                temp.write_bytes(youtube.read_bytes())
                temp.chmod(0o600)
                os.replace(temp, youtube)
                raise OSError("second writer not started")
            return _replace(path, before, after, uid)
        with self.assertRaisesRegex(DestinationRefused,
                                    "shared_found_requires_review"):
            self.apply(replace_fn=swap_then_fail)
        self.assertEqual(youtube.read_text(), self.new["youtube"])
        self.assertEqual(self.targets["user"].read_text(), self.old["user"])

    def test_compensation_failure_requires_review_and_never_claims_success(self):
        counter = [0]
        def fail_rollback(path, before, after, uid):
            counter[0] += 1
            if counter[0] in (2, 3):
                raise OSError("test-only write/rollback fault")
            return _replace(path, before, after, uid)

        with self.assertRaisesRegex(DestinationRefused,
                                    "shared_found_requires_review"):
            self.apply(replace_fn=fail_rollback)
        self.assertEqual(self.targets["youtube"].read_text(),
                         self.new["youtube"])
        self.assertEqual(self.targets["user"].read_text(), self.old["user"])

    def test_all_noop_keeps_exact_original_inodes(self):
        same = dict(self.old)
        inodes = {name: path.lstat().st_ino for name, path in self.targets.items()}
        result = self.apply(plan=self.plan(new=same))
        self.assertFalse(any(x["changed"] for x in result["files"].values()))
        self.assertEqual(
            {name: path.lstat().st_ino for name, path in self.targets.items()}, inodes)

    def base_records(self):
        return {
            name: {"status": "populated" if value else "empty",
                   "content": value, "revision": sha(value.encode())}
            for name, value in self.old.items()
        }

    def proposed(self, *, draft=None, baseline=None, manual=None, exclude=""):
        return _plan_shared_found_under_original_locks(
            self.base_records() if baseline is None else baseline,
            dict(self.old) if draft is None else draft,
            {"youtube": "", "user": ""} if manual is None else manual,
            exclude, self.targets, uid=self.uid)

    def test_rebased_user_deletion_keeps_concurrent_minute_addition(self):
        # User removes a seen root; the one-minute writer added another.
        self.targets["youtube"].write_text("example.com\nexample.net\n")
        drafts = dict(self.old, youtube="")
        rows, preview = self.proposed(draft=drafts)
        self.assertTrue(preview["sources"]["youtube"]["rebased"])
        self.assertEqual(rows["youtube"]["before"], "example.com\nexample.net\n")
        self.assertEqual(rows["youtube"]["after"], "example.net\n")
        self.apply(plan=rows)
        self.assertEqual(self.targets["youtube"].read_text(), "example.net\n")
        self.assertEqual(self.targets["user"].read_text(), self.old["user"])

    def test_two_tab_stale_base_rebases_against_first_tab_commit(self):
        first = dict(self.old, youtube="example.com\nfirst.net\n")
        rows, _ = self.proposed(draft=first)
        self.apply(plan=rows)
        second = dict(self.old, youtube="example.com\nsecond.net\n")
        rows, preview = self.proposed(draft=second)
        self.assertTrue(preview["sources"]["youtube"]["rebased"])
        self.assertEqual(rows["youtube"]["after"],
                         "example.com\nfirst.net\nsecond.net\n")
        self.apply(plan=rows)
        self.assertEqual(self.targets["youtube"].read_text(),
                         "example.com\nfirst.net\nsecond.net\n")

    def test_drift_after_preparation_refuses_all_writes(self):
        rows, _ = self.proposed(draft=dict(self.old, youtube="example.com\nnew.net\n"))
        self.targets["user"].write_text("example.org\nlate.net\n")
        with self.assertRaisesRegex(DestinationRefused,
                                    "shared_found_preimage_changed"):
            self.apply(plan=rows)
        self.assertEqual(self.targets["youtube"].read_text(), self.old["youtube"])
        self.assertEqual(self.targets["user"].read_text(), "example.org\nlate.net\n")

    def test_cross_known_provenance_conflict_does_not_mutate(self):
        with self.assertRaisesRegex(DestinationRefused,
                                    "ambiguous_known_source_provenance"):
            self.proposed(draft=dict(self.old,
                               youtube="example.com\nexample.org\n"))
        self.assert_old()

    def test_invalid_draft_and_uninitialized_owned_base_refuse(self):
        with self.assertRaisesRegex(DestinationRefused, "invalid_draft_line"):
            self.proposed(draft=dict(self.old, auto="!bad.example.com"))
        baseline = self.base_records()
        baseline["youtube"] = {
            "status": "uninitialized", "revision": None, "content": ""}
        with self.assertRaisesRegex(DestinationRefused,
                                    "owned_source_not_initialized"):
            self.proposed(baseline=baseline)
        self.assert_old()

    def missing_base(self):
        baseline = self.base_records()
        baseline["auto"] = {"status": "missing", "content": "",
                            "revision": hashlib.sha256(b"missing\0").hexdigest()}
        return baseline

    def test_missing_shared_auto_unmodified_stays_missing(self):
        self.targets["auto"].unlink()
        rows, preview = self.proposed(baseline=self.missing_base())
        self.assertEqual(rows["auto"]["before_status"], "missing")
        self.assertEqual(rows["auto"]["before_inode"], 0)
        self.assertFalse(preview["sources"]["auto"]["would_change_current"])
        receipt = self.apply(plan=rows)
        self.assertFalse(receipt["files"]["auto"]["changed"])
        self.assertFalse(self.targets["auto"].exists())
        self.assert_old_others()

    def test_missing_shared_auto_changed_is_durably_created_once(self):
        self.targets["auto"].unlink()
        rows, _ = self.proposed(
            baseline=self.missing_base(),
            draft=dict(self.old, auto="shared.org\n"))
        result = self.apply(plan=rows)
        self.assertEqual(result["files"]["auto"]["before_status"], "missing")
        self.assertTrue(result["files"]["auto"]["changed"])
        self.assertEqual(self.targets["auto"].read_text(), "shared.org\n")
        self.assertFalse(result["config_committed"])
        self.assertFalse(result["commit_authorized"])
        self.assert_old_others()

    def test_missing_shared_auto_rejects_occupied_and_symlink_target(self):
        for mode in ("occupied", "symlink"):
            with self.subTest(mode=mode):
                self.targets["auto"].unlink()
                rows, _ = self.proposed(
                    baseline=self.missing_base(),
                    draft=dict(self.old, auto="shared.org\n"))
                if mode == "occupied":
                    self.targets["auto"].write_text("foreign.org\n")
                else:
                    self.targets["auto"].symlink_to(self.root / "foreign-target")
                with self.assertRaisesRegex(
                        DestinationRefused, "shared_found_expected_missing"):
                    self.apply(plan=rows)
                self.assert_old_others()

    def test_missing_shared_auto_create_failure_before_link_restores_known(self):
        self.targets["auto"].unlink()
        rows, _ = self.proposed(
            baseline=self.missing_base(),
            draft=dict(self.old, youtube="example.com\nfresh.net\n",
                       auto="shared.org\n"))
        def fail_before_link(path, data, uid):
            raise OSError("injected before link")
        with self.assertRaisesRegex(
                DestinationRefused, "shared_found_restored_after_failure"):
            self.apply(plan=rows, create_fn=fail_before_link)
        self.assertFalse(self.targets["auto"].exists())
        self.assert_old_others()

    def test_missing_shared_auto_postlink_unknown_requires_review(self):
        self.targets["auto"].unlink()
        rows, _ = self.proposed(
            baseline=self.missing_base(),
            draft=dict(self.old, auto="shared.org\n"))
        def fail_after_link(path, data, uid):
            _create(path, data, uid)
            raise OSError("injected after link and fsync")
        with self.assertRaisesRegex(DestinationRefused,
                                    "shared_found_requires_review"):
            self.apply(plan=rows, create_fn=fail_after_link)
        self.assertEqual(self.targets["auto"].read_text(), "shared.org\n")
        self.assert_old_others()

    def test_missing_shared_auto_shape_must_not_forge_known_ownership(self):
        rows = self.plan()
        rows["youtube"]["before_status"] = "missing"
        rows["youtube"]["before_inode"] = 0
        with self.assertRaisesRegex(DestinationRefused,
                                    "shared_found_candidate_revision"):
            self.apply(plan=rows)
        self.assert_old()

    def root_stage_payload(self, *, drafts=None, base=None):
        known = self.old
        raw = self.base_records() if base is None else base
        # PHP's real multipart schema binds status/revision/content in this
        # exact order; the older local planner fixtures use a different
        # dict insertion order. Mirror the genuine wire contract here.
        source = {
            name: {"status": raw[name]["status"],
                   "revision": raw[name]["revision"],
                   "content": raw[name]["content"]}
            for name in SHARED_FOUND_NAMES
        }
        draft = known if drafts is None else drafts
        return {
            "schema_version": 1, "kind": "tz6v2-found-root-stage",
            "config_revision": "a" * 64,
            "found_intent": {
                "schema_version": 1, "kind": "tz6v2-found-intent",
                "sources": {
                    name: {"base": source[name], "draft": draft[name]}
                    for name in SHARED_FOUND_NAMES
                },
                "config_revision": "a" * 64,
                "cross_source_validated": False,
                "commit_authorized": False,
            },
            "manual": {"youtube": "", "user": ""},
            "global_exclude": "",
        }

    def test_original_root_stage_qualifies_sealable_batch_without_any_write(self):
        payload = self.root_stage_payload(drafts=dict(
            self.old, youtube="example.com\nfresh.net\n", user=""))
        before = {name: path.read_bytes() for name, path in self.targets.items()}
        result = qualify_readonly(payload, self.targets,
                                  {name: self.old[name] for name in ("youtube", "user")},
                                  uid=self.uid)
        self.assertEqual(result["kind"], "tz6v2-found-readonly-candidate")
        self.assertTrue(result["cross_source_validated"])
        self.assertFalse(result["commit_authorized"])
        self.assertFalse(result["config_committed"])
        self.assertEqual(list(result["found_batch"]), list(SHARED_FOUND_NAMES))
        self.assertEqual(result["found_batch"]["youtube"]["after"],
                         "example.com\nfresh.net\n")
        self.assertEqual(result["found_batch"]["user"]["after"], "")
        self.assertEqual(before, {
            name: path.read_bytes() for name, path in self.targets.items()
        })
        self.assertFalse((self.root / "operation.json").exists())

    def test_original_root_stage_three_way_keeps_independent_minute_find(self):
        payload = self.root_stage_payload(
            drafts=dict(self.old, youtube=""))
        self.targets["youtube"].write_text("example.com\nlater.net\n")
        result = qualify_readonly(payload, self.targets,
                                  {"youtube": "example.com\nlater.net\n",
                                   "user": self.old["user"]}, uid=self.uid)
        self.assertEqual(result["found_batch"]["youtube"]["before"],
                         "example.com\nlater.net\n")
        self.assertEqual(result["found_batch"]["youtube"]["after"],
                         "later.net\n")
        # Preview cannot mutate the owner; actual CAS will recheck identity.
        self.assertEqual(self.targets["youtube"].read_text(),
                         "example.com\nlater.net\n")

    def test_original_root_stage_rejects_forged_or_incomplete_intent(self):
        owner = {"youtube": self.old["youtube"], "user": self.old["user"]}
        for tamper in (
            lambda p: p["found_intent"].update(commit_authorized=True),
            lambda p: p["found_intent"].update(cross_source_validated=True),
            lambda p: p.update(config_revision="b" * 64),
            lambda p: p["found_intent"]["sources"]["youtube"].update(draft="!invalid.org"),
            lambda p: p["found_intent"]["sources"]["youtube"]["base"].update(revision="0" * 64),
            lambda p: p["manual"].update(evil="foreign"),
            lambda p: p["found_intent"]["sources"].update(evil={}),
        ):
            payload = self.root_stage_payload()
            tamper(payload)
            with self.subTest(tamper=repr(tamper)):
                with self.assertRaises((FoundStageRefused, DestinationRefused)):
                    qualify_readonly(payload, self.targets, owner, uid=self.uid)
        with self.assertRaisesRegex(FoundStageRefused, "original_known_owner_changed"):
            qualify_readonly(self.root_stage_payload(), self.targets,
                             {"youtube": "foreign.net\n",
                              "user": self.old["user"]}, uid=self.uid)
        self.assert_old()

    @unittest.skipIf(sys.platform.startswith("freebsd") and os.geteuid() == 0,
                     "A native root requires a real FD9 parent, not a fixture")
    def test_retired_bound_recovery_hands_same_existing_queue_to_original_php(self):
        from types import SimpleNamespace
        from auto_detect_effective_known import native_found_recover_original_fd9
        from auto_detect_queue import DurableInbox, QueueSafetyError
        import fcntl

        producer = self.root / "producer"
        producer.mkdir(mode=0o700)
        (producer / "pending").mkdir(mode=0o700)
        queue = DurableInbox(producer, owner_uid=self.uid)
        queue.inbox.write_bytes(b"")
        queue.inbox.chmod(0o600)
        operation = "a" * 32
        record = {"detail": {"id": operation, "page": "strategies"},
                  "found": {}, "manifest": {"schema": 1}, "previous_manifest": {"schema": 2},
                  "phase": "found-config-saving"}
        store = SimpleNamespace(read=lambda: record)
        calls = []

        def run(args, **kwargs):
            calls.append(args)
            expected = "found-bound-recover" if "previous_manifest" in record else "found-recover"
            self.assertEqual(args[2:5], [expected, operation, "strategies"])
            if "previous_manifest" in record:
                self.assertEqual(kwargs["pass_fds"], (queue.locked_fd, 9))
                self.assertEqual(args[5], "--queue-fd=" + str(queue.locked_fd))
                self.assertEqual(os.fstat(queue.locked_fd).st_ino, pin)
                foreign = os.open(queue.lock, os.O_RDONLY)
                try:
                    with self.assertRaises(BlockingIOError):
                        fcntl.flock(foreign, fcntl.LOCK_EX | fcntl.LOCK_NB)
                finally:
                    os.close(foreign)
            else:
                self.assertFalse(queue._held)
                self.assertEqual(kwargs["pass_fds"], (9,))
                self.assertEqual(len(args), 5)
            return SimpleNamespace(returncode=70)

        with patch("sys.platform", "freebsd15"), patch("os.geteuid", return_value=0), \
                patch("pwd.getpwnam", return_value=SimpleNamespace(pw_gid=65534)), \
                patch("voice_ipfw_adapter.require_lifecycle_lock"), \
                patch("shared_apply_operation.SharedApplyOperation", return_value=store), \
                patch("auto_detect_queue.DurableInbox", return_value=queue), \
                patch("subprocess.run", side_effect=run):
            with self.assertRaises(FileNotFoundError):
                native_found_recover_original_fd9(operation)
            self.assertFalse(queue.lock.exists())
            with queue.exclusive():
                pin = queue.lock.stat().st_ino
                with self.assertRaises(QueueSafetyError):
                    native_found_recover_original_fd9(operation)
            self.assertEqual(calls, [])
            self.assertEqual(native_found_recover_original_fd9(operation), 70)
            self.assertFalse(queue._held)
            record["phase"] = "found-config-saved"
            self.assertEqual(native_found_recover_original_fd9(operation), 70)
            self.assertFalse(queue._held)
            record["phase"] = "prepared"
            with self.assertRaises(RuntimeError):
                native_found_recover_original_fd9(operation)
            record["phase"] = "found-config-saving"
            record.pop("previous_manifest")
            self.assertEqual(native_found_recover_original_fd9(operation), 70)
            self.assertEqual(len(calls), 3)
            with self.assertRaises(RuntimeError):
                native_found_recover_original_fd9("b" * 32)
            self.assertEqual(len(calls), 3)

    def test_bound_found_recovery_chooses_locked_image_without_fallback(self):
        from types import SimpleNamespace
        from auto_detect_effective_known import recover_native_bound_found_locked
        op, base, candidate = "a" * 32, "b" * 64, "c" * 64
        rec = {"detail": {"id": op, "base": base, "candidate": candidate},
               "manifest": {"schema": 1}, "previous_manifest": {"schema": 2},
               "found": {"runtime_mode": "0"}, "phase": "found-config-saving"}
        store = SimpleNamespace(read=lambda: rec)
        with patch("auto_detect_destination_commit._native_found_wal_context",
                   return_value=(store, rec, None, None, None, lambda: True)), \
             patch("auto_detect_effective_known.finish_native_bound_stopped_found_locked",
                   return_value={"result": "committed", "mode": "0"}) as finish, \
             patch("auto_detect_effective_known.advance_native_found_locked",
                   return_value={"result": "restored"}) as rollback:
            def run(digest, queue_fd=3):
                return recover_native_bound_found_locked(op, digest, config_fd=4, queue_fd=queue_fd)
            self.assertEqual(run(candidate)["result"], "committed")
            finish.assert_called_once_with(op, candidate, config_fd=4, queue_fd=3)
            rollback.assert_not_called()
            self.assertEqual(run(base)["result"], "restored")
            rollback.assert_called_once_with("recover-found-locked", op, base, config_fd=4, queue_fd=3)
            for digest, fd in (("d"*64, 3), (candidate, None), (base, None)):
                with self.assertRaises(RuntimeError):
                    run(digest, fd)
            rec["phase"] = "found-config-saved"
            with self.assertRaises(RuntimeError):
                run(base)
            self.assertEqual(run(candidate)["result"], "committed")
            finish.side_effect = RuntimeError("physical proof refused")
            with self.assertRaises(RuntimeError):
                run(candidate)
            self.assertEqual(rollback.call_count, 1)

    def test_public_original_fd9_entry_refuses_non_native(self):
        with self.assertRaisesRegex(DestinationRefused,
                                    "original_native_fd9_required"):
            shared_apply_found_files_original_fd9("a" * 32, -1)


if __name__ == "__main__":
    unittest.main()
