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

BACKEND = (Path(__file__).resolve().parents[1] / "src/opnsense/scripts"
           / "OPNsense/Zapret/backend")
sys.path.insert(0, str(BACKEND))

from auto_detect_gui_hostlist import _create
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

    def apply(self, plan=None, **kwargs):
        return _locked_shared_found_replace(
            self.plan() if plan is None else plan, self.targets,
            uid=self.uid, **kwargs)

    def assert_old(self):
        self.assertEqual(
            {name: path.read_text() for name, path in self.targets.items()},
            self.old)


    def journaled(self, *, rows=None, witness=None, **kwargs):
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
        journal.prepare_found(d, body, lambda _: True)
        callback = (lambda phase, raw: raw == body) if witness is None else witness
        return journal, d, body, lambda: _locked_shared_found_apply_journal(
            rows, self.targets, store=journal, detail=d,
            plan_bytes=body, uid=self.uid, attest=callback, **kwargs)

    def test_journal_original_wal_before_first_three_file_write(self):
        journal, detail, raw, apply = self.journaled()
        receipt = apply()
        self.assertEqual(receipt["journal_phase"], "found-files-written")
        self.assertFalse(receipt["config_committed"])
        self.assertFalse(receipt["commit_authorized"])
        self.assertEqual(journal.read()["phase"], "found-files-written")
        pins = journal.read()["found"]["post"]
        self.assertEqual(list(pins), list(SHARED_FOUND_NAMES))
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
            if call[0] > 1:
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

    def test_journal_partial_file_error_retains_writing_phase_even_after_compensation(self):
        call = [0]
        def second_fails(path, before, after, uid):
            call[0] += 1
            if call[0] == 2:
                raise OSError("file 2 pre-rename")
            return _replace(path, before, after, uid)
        journal, _, _, apply = self.journaled(replace_fn=second_fails)
        with self.assertRaisesRegex(
                DestinationRefused, "shared_found_restored_after_failure"):
            apply()
        self.assert_old()
        self.assertEqual(journal.read()["phase"], "found-files-writing")
        self.assertFalse(journal.advisory()["safe_to_mutate"])

    def test_journal_postwrite_witness_refusal_leaves_nonterminal_physical_after(self):
        journal, _, _, apply = self.journaled(
            witness=lambda phase, raw: phase == "found-files-writing")
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

    def test_after_second_physical_write_failure_is_compensated(self):
        counter = [0]
        def abort_after_second(path, before, after, uid):
            counter[0] += 1
            _replace(path, before, after, uid)
            if counter[0] == 2:
                raise OSError("test-only after durable replace")

        with self.assertRaisesRegex(DestinationRefused,
                                    "shared_found_restored_after_failure"):
            self.apply(replace_fn=abort_after_second)
        self.assert_old()

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
    def test_public_original_fd9_entry_refuses_non_native(self):
        with self.assertRaisesRegex(DestinationRefused,
                                    "original_native_fd9_required"):
            shared_apply_found_files_original_fd9("a" * 32, -1)


if __name__ == "__main__":
    unittest.main()
