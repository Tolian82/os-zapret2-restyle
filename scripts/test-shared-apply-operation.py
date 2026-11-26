#!/usr/bin/env python3
"""Common Apply durable phases and existing lifecycle guard, without kernel changes."""
import sys
import json
import hashlib
from contextlib import ExitStack
import subprocess
from unittest.mock import patch
import tempfile
from pathlib import Path
import unittest

BACKEND=Path(__file__).resolve().parents[1]/"src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0,str(BACKEND))
from shared_apply_operation import SharedApplyOperation,SharedOperationError,committed_owner,native_lifecycle_gate,native_committed_owner_witness,native_remove_rollback_pair,native_remove_trial_context,native_remove_prepared_trial

def detail(ident="1"*32):
    return {"id":ident,"page":"voice","base":"a"*64,
            "candidate":"b"*64,"changed_fields":[
                "voice.telegram.enabled","hostlist.telegramips"]}

def trivial_post():
    import hashlib
    return {
        name: {"status": "present", "device": 1, "inode": index + 1,
               "ctime_ns": 1, "mtime_ns": 1, "size": 0,
               "sha256": hashlib.sha256(b"").hexdigest()}
        for index, name in enumerate(("youtube", "user", "auto"))
    }

class TestJournal(unittest.TestCase):




    def test_found_staged_temp_inode_requires_two_durable_owner_steps(self):
        with tempfile.TemporaryDirectory() as root:
            store = SharedApplyOperation(Path(root) / "journal")
            d = {"id": "a" * 32, "page": "strategies", "base": "b" * 64,
                 "candidate": "c" * 64, "changed_fields": []}
            changes = {"youtube": ("example.com\\n", "new.example.com\\n"),
                       "user": ("example.org\\n", "new.example.org\\n"),
                       "auto": ("", "")}
            rows = {k: {"before": before, "after": after, "before_status": "present"}
                    for k, (before, after) in changes.items()}
            plan = json.dumps({"page": "strategies", "result": "prepared",
                               "dependencies": d["base"], "found_batch": rows,
                               "found_intent": {"config_revision": d["base"],
                                                "commit_authorized": False}}).encode()
            store.prepare_found(d, plan, lambda _: True)
            store.advance_found_files("found-files-writing", d, plan,
                                      lambda *_: True)
            self.assertEqual(store.read()["found"]["stages"], {})
            make_pin = lambda name, inode: {
                "device": 13, "inode": inode, "mtime_ns": 900,
                "size": len(rows[name]["after"].encode()),
                "sha256": hashlib.sha256(rows[name]["after"].encode()).hexdigest()}
            yp, up = make_pin("youtube", 20), make_pin("user", 21)
            with self.assertRaisesRegex(SharedOperationError, "source reordered"):
                store.advance_found_stage(d, plan, "user", "ready", up,
                                          lambda *_: True)
            with self.assertRaisesRegex(SharedOperationError, "not ready"):
                store.advance_found_stage(d, plan, "youtube", "installed", yp,
                                          lambda *_: True)
            before = (store.root / "operation.json").read_bytes()
            with self.assertRaisesRegex(SharedOperationError, "witness refused"):
                store.advance_found_stage(d, plan, "youtube", "ready", yp,
                                          lambda *_: False)
            self.assertEqual((store.root / "operation.json").read_bytes(), before)
            for name, pin in (("youtube", yp), ("user", up)):
                store.advance_found_stage(d, plan, name, "ready", pin,
                                          lambda phase, raw, n, p:
                                              phase == "ready" and n == name and p == pin)
                self.assertEqual(store.read()["found"]["stages"][name]["state"], "ready")
                with self.assertRaisesRegex(SharedOperationError, "not ready"):
                    other_pin = {**pin, "inode": pin["inode"] + 90}
                    store.advance_found_stage(d, plan, name, "installed", other_pin,
                                              lambda *_: True)
                store.advance_found_stage(d, plan, name, "installed", pin,
                                          lambda *_: True)
            self.assertEqual(set(store.read()["found"]["stages"]), {"youtube", "user"})
            with self.assertRaisesRegex(SharedOperationError, "original staged found"):
                store.advance_found_stage(d, plan, "auto", "ready", yp,
                                          lambda *_: True)
            self.assertFalse(native_lifecycle_gate("common-apply", root=store.root)["safe_to_mutate"])
            post = trivial_post()
            post["youtube"].update(device=yp["device"], inode=yp["inode"],
                                   mtime_ns=yp["mtime_ns"], size=yp["size"],
                                   sha256=yp["sha256"])
            post["user"].update(device=up["device"], inode=up["inode"],
                                mtime_ns=up["mtime_ns"], size=up["size"],
                                sha256=up["sha256"])
            store.advance_found_files("found-files-written", d, plan,
                                      lambda *_: True, post_images=post)
            self.assertEqual(store.read()["phase"], "found-files-written")
            self.assertEqual(store.read()["found"]["stages"]["youtube"]["state"], "installed")

    def test_found_prepared_pristine_recovery_reuses_one_journal_and_old_owner(self):
        import hashlib
        with tempfile.TemporaryDirectory() as root:
            journal = SharedApplyOperation(Path(root) / "journal")
            previous = detail("a" * 32)
            for phase in ("prepared", "activating", "activated",
                          "config-saved", "committed"):
                journal.advance(phase, previous)
            d = {"id": "b" * 32, "page": "strategies",
                 "base": previous["candidate"], "candidate": "c" * 64,
                 "changed_fields": ["hostlist.youtubedomains"]}
            plan = json.dumps({
                "result": "prepared", "page": "strategies",
                "dependencies": d["base"],
                "changed_fields": d["changed_fields"],
                "found_intent": {"config_revision": d["base"],
                                 "commit_authorized": False},
                "found_batch": {"youtube": {}, "user": {}, "auto": {}}
            }).encode()
            journal.prepare_found(d, plan, lambda _: True)
            before = (journal.root / "operation.json").read_bytes()
            calls = []
            with self.assertRaisesRegex(SharedOperationError, "runtime refused"):
                journal.finish_found_prepared_pristine(
                    d["id"], plan,
                    lambda raw, old: calls.append((raw, old)) or False)
            self.assertEqual(calls, [(plan, previous)])
            self.assertEqual(before, (journal.root / "operation.json").read_bytes())
            with self.assertRaisesRegex(SharedOperationError, "phase/plan mismatch"):
                journal.finish_found_prepared_pristine(
                    d["id"], plan + b" ", lambda *_: True)
            with self.assertRaisesRegex(SharedOperationError, "phase/plan mismatch"):
                journal.finish_found_prepared_pristine(
                    "f" * 32, plan, lambda *_: True)
            self.assertFalse(native_lifecycle_gate("common-apply", root=journal.root)["safe_to_mutate"])
            result = journal.finish_found_prepared_pristine(
                d["id"], plan, lambda raw, old: raw == plan and old == previous)
            self.assertEqual(result["phase"], "restored")
            self.assertEqual(result["previous"], previous)
            self.assertNotIn("found", result)
            self.assertEqual(journal.read(), result)
            self.assertEqual(committed_owner(result), previous)
            self.assertTrue(native_lifecycle_gate("common-apply", root=journal.root)["safe_to_mutate"])
            self.assertEqual((journal.root / "operation.json").stat().st_mode & 0o777, 0o600)
            with self.assertRaisesRegex(SharedOperationError, "phase/plan mismatch"):
                journal.finish_found_prepared_pristine(
                    d["id"], plan, lambda *_: True)
            self.assertEqual(journal.read(), result)

    def test_found_prepared_pristine_refuses_later_phases_and_modified_plan(self):
        with tempfile.TemporaryDirectory() as root:
            journal = SharedApplyOperation(Path(root) / "journal")
            d = {"id": "b" * 32, "page": "strategies",
                 "base": "a" * 64, "candidate": "c" * 64, "changed_fields": []}
            original = {
                "result": "prepared", "page": "strategies",
                "dependencies": d["base"], "changed_fields": [],
                "found_intent": {"config_revision": d["base"],
                                 "commit_authorized": False},
                "found_batch": {"youtube": {}, "user": {}, "auto": {}}
            }
            plan = json.dumps(original).encode()
            journal.prepare_found(d, plan, lambda _: True)
            invalid = dict(original, changed_fields=["hostlist.userdomains"])
            # Changing the plan also changes its SHA; reject before trusting
            # any source fields or running the attestation callback.
            with self.assertRaisesRegex(SharedOperationError, "phase/plan mismatch"):
                journal.finish_found_prepared_pristine(
                    d["id"], json.dumps(invalid).encode(),
                    lambda *_: True)
            # Source remains untouched in the journal after refusal.
            self.assertEqual(journal.read()["phase"], "prepared")
            journal.advance_found_files(
                "found-files-writing", d, plan, lambda *_: True)
            before = (journal.root / "operation.json").read_bytes()
            with self.assertRaisesRegex(SharedOperationError, "phase/plan mismatch"):
                journal.finish_found_prepared_pristine(
                    d["id"], plan, lambda *_: True)
            self.assertEqual((journal.root / "operation.json").read_bytes(), before)
            self.assertFalse(native_lifecycle_gate("common-apply", root=journal.root)["safe_to_mutate"])

    def test_found_prepared_pristine_first_install_retains_no_previous_owner(self):
        with tempfile.TemporaryDirectory() as root:
            journal = SharedApplyOperation(Path(root) / "journal")
            d = {"id": "b" * 32, "page": "strategies",
                 "base": "a" * 64, "candidate": "c" * 64, "changed_fields": []}
            plan = json.dumps({
                "result": "prepared", "page": "strategies",
                "dependencies": d["base"], "changed_fields": [],
                "found_intent": {"config_revision": d["base"],
                                 "commit_authorized": False},
                "found_batch": {"youtube": {}, "user": {}, "auto": {}}
            }).encode()
            journal.prepare_found(d, plan, lambda _: True)
            witnessed = []
            completed = journal.finish_found_prepared_pristine(
                d["id"], plan, lambda raw, previous:
                    witnessed.append(previous) is None and previous is None)
            self.assertEqual(witnessed, [None])
            self.assertEqual(completed["phase"], "restored")
            self.assertNotIn("previous", completed)
            self.assertIsNone(committed_owner(completed))

    def test_found_config_wal_pre_save_and_post_save_is_strictly_nonterminal(self):
        import hashlib
        with tempfile.TemporaryDirectory() as temporary:
            store = SharedApplyOperation(Path(temporary) / "shared-apply")
            detail_found = {"id": "e" * 32, "page": "strategies",
                            "base": "a" * 64, "candidate": "b" * 64,
                            "changed_fields": []}
            plan = json.dumps({
                "page": "strategies", "result": "prepared",
                "dependencies": detail_found["base"],
                "found_intent": {"config_revision": detail_found["base"],
                                 "commit_authorized": False},
                "found_batch": {name: {"before": "", "after": "", "before_status": "present"}
                                for name in ("youtube", "user", "auto")}
            }, separators=(",", ":")).encode()
            store.prepare_found(detail_found, plan, lambda _: True)
            store.advance_found_files("found-files-writing", detail_found,
                                      plan, lambda *_: True)
            store.advance_found_files("found-files-written", detail_found,
                                      plan, lambda *_: True, post_images=trivial_post())
            sequence = []
            for phase in ("found-config-saving", "found-config-saved"):
                record_before = (store.root / "operation.json").read_bytes()
                with self.assertRaisesRegex(SharedOperationError, "witness refused"):
                    store.advance_found_config(phase, detail_found, plan,
                                               lambda *_: False)
                self.assertEqual((store.root / "operation.json").read_bytes(),
                                 record_before)
                with self.assertRaisesRegex(SharedOperationError, "state/plan mismatch"):
                    store.advance_found_config(phase, detail_found, plan + b" ",
                                               lambda *_: True)
                persisted = store.advance_found_config(
                    phase, detail_found, plan,
                    lambda p, raw: (sequence.append(p) or raw == plan))
                self.assertEqual(store.read(), persisted)
                self.assertEqual(persisted["phase"], phase)
                self.assertEqual(persisted["found"]["plan_sha256"],
                                 hashlib.sha256(plan).hexdigest())
                self.assertEqual((store.root / "operation.json").stat().st_mode & 0o777, 0o600)
                self.assertFalse(native_lifecycle_gate("common-apply", root=store.root)["safe_to_mutate"])
                for illegal in ("committed", "restored", "requires-review",
                                "config-saved", "activated"):
                    with self.assertRaisesRegex(
                            SharedOperationError, "found files require original durable"):
                        store.advance(illegal, detail_found)
            self.assertEqual(sequence, ["found-config-saving", "found-config-saved"])
            with self.assertRaisesRegex(SharedOperationError, "state/plan mismatch"):
                store.advance_found_config(
                    "found-config-saving", detail_found, plan, lambda *_: True)
            with self.assertRaisesRegex(SharedOperationError, "prepared-only"):
                store.recover_prepared(detail_found["id"], lambda: True)
            self.assertEqual(store.read()["phase"], "found-config-saved")

    def test_found_config_attempt_refused_before_files_written(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = SharedApplyOperation(Path(temporary) / "shared-apply")
            d = {"id": "d" * 32, "page": "strategies",
                 "base": "a" * 64, "candidate": "b" * 64,
                 "changed_fields": []}
            plan = json.dumps({
                "page": "strategies", "result": "prepared",
                "dependencies": d["base"],
                "found_intent": {"config_revision": d["base"],
                                 "commit_authorized": False},
                "found_batch": {"youtube": {}, "user": {}, "auto": {}}
            }).encode()
            store.prepare_found(d, plan, lambda _: True)
            before = (store.root / "operation.json").read_bytes()
            with self.assertRaisesRegex(SharedOperationError, "state/plan mismatch"):
                store.advance_found_config("found-config-saving", d, plan,
                                           lambda *_: True)
            self.assertEqual((store.root / "operation.json").read_bytes(), before)
            with self.assertRaisesRegex(SharedOperationError, "missing original intent"):
                store._persist_record(
                    {"schema": 1, "phase": "found-config-saving", "detail": d})
            self.assertEqual((store.root / "operation.json").read_bytes(), before)
            with self.assertRaisesRegex(SharedOperationError, "invalid original found Config"):
                store.advance_found_config("committed", d, plan, lambda *_: True)

    def test_found_physical_write_intent_is_fsynced_before_any_file_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = SharedApplyOperation(Path(tmp) / "shared-apply")
            d = {"id": "c" * 32, "page": "strategies", "base": "a" * 64,
                 "candidate": "b" * 64, "changed_fields": []}
            plan = json.dumps({
                "page": "strategies", "result": "prepared",
                "dependencies": d["base"],
                "found_intent": {"config_revision": d["base"],
                                 "commit_authorized": False},
                "found_batch": {name: {"before": "", "after": "", "before_status": "present"}
                                for name in ("youtube", "user", "auto")},
            }).encode()
            journal.prepare_found(d, plan, lambda b: b == plan)
            steps = []
            for phase in ("found-files-writing", "found-files-written"):
                with self.assertRaisesRegex(SharedOperationError, "witness refused"):
                    journal.advance_found_files(
                        phase, d, plan, lambda *_: False,
                        post_images=trivial_post() if phase == "found-files-written" else None)
                with self.assertRaisesRegex(SharedOperationError, "state/plan mismatch"):
                    journal.advance_found_files(phase, d, plan + b"\n",
                                                lambda *_: True)
                record = journal.advance_found_files(
                    phase, d, plan,
                    lambda p, raw: (steps.append(p) or raw == plan),
                    post_images=trivial_post() if phase == "found-files-written" else None)
                self.assertEqual(record["phase"], phase)
                self.assertEqual(journal.read(), record)
                self.assertEqual(
                    (journal.root / "operation.json").stat().st_mode & 0o777,
                    0o600)
                self.assertFalse(native_lifecycle_gate(
                    "common-apply", root=journal.root)["safe_to_mutate"])
                for legacy in ("activated", "restored", "config-saved", "committed"):
                    with self.assertRaises(SharedOperationError):
                        journal.advance(legacy, d)
            self.assertEqual(steps, ["found-files-writing", "found-files-written"])
            with self.assertRaisesRegex(SharedOperationError, "state/plan mismatch"):
                journal.advance_found_files(
                    "found-files-writing", d, plan, lambda *_: True)
            with self.assertRaisesRegex(SharedOperationError, "prepared-only"):
                journal.recover_prepared(d["id"], lambda: True)

    def test_found_file_phase_cannot_be_forged_from_ordinary_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = SharedApplyOperation(Path(tmp) / "shared-apply")
            old = detail("f" * 32)
            journal.advance("prepared", old)
            before = (journal.root / "operation.json").read_bytes()
            with self.assertRaises(SharedOperationError):
                journal.advance_found_files(
                    "found-files-writing", old, b'{"plan":1}', lambda *_: True)
            self.assertEqual((journal.root / "operation.json").read_bytes(), before)
            forged = json.loads(before)
            forged["phase"] = "found-files-writing"
            with self.assertRaisesRegex(SharedOperationError, "missing original intent"):
                journal._persist_record(forged)
            self.assertEqual((journal.root / "operation.json").read_bytes(), before)

    def test_found_intent_is_one_durable_original_record_not_ordinary_apply(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            store = SharedApplyOperation(Path(tmp) / "shared-apply")
            old = detail("a" * 32)
            for phase in ("prepared", "activating", "activated", "config-saved", "committed"):
                store.advance(phase, old)
            found = {"id": "b" * 32, "page": "strategies",
                     "base": old["candidate"], "candidate": "c" * 64,
                     "changed_fields": []}
            body = json.dumps({"page": "strategies", "result": "prepared",
                "dependencies": found["base"],
                "found_intent": {"config_revision": found["base"],
                                 "commit_authorized": False},
                "found_batch": {"youtube": {}, "user": {}, "auto": {}}
            }, separators=(",", ":")).encode()
            called = []
            prepared = store.prepare_found(
                found, body, lambda content: (called.append(content) or True))
            self.assertEqual(called, [body])
            self.assertEqual(prepared["phase"], "prepared")
            self.assertEqual(prepared["previous"], old)
            self.assertEqual(prepared["found"], {
                "schema": 1, "kind": "sealed-five-editor-three-file-intent",
                "plan_sha256": hashlib.sha256(body).hexdigest(),
                "sources": ["youtube", "user", "auto"]})
            physical = (store.root / "operation.json").read_bytes()
            self.assertEqual(store.read(), prepared)
            self.assertEqual((store.root / "operation.json").stat().st_mode & 0o777, 0o600)
            self.assertFalse(native_lifecycle_gate("common-apply", root=store.root)["safe_to_mutate"])
            for phase in ("activating", "restored", "config-saved", "committed"):
                with self.assertRaises(SharedOperationError):
                    store.advance(phase, found)
                self.assertEqual((store.root / "operation.json").read_bytes(), physical)
            with self.assertRaisesRegex(SharedOperationError, "prepared-only"):
                store.recover_prepared(found["id"], lambda: True)
            self.assertEqual(store.read(), prepared)

    def test_found_prepared_refuses_unsealed_or_nonterminal_reuse_without_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SharedApplyOperation(Path(tmp) / "shared-apply")
            found = {"id": "c" * 32, "page": "strategies",
                     "base": "a" * 64, "candidate": "b" * 64,
                     "changed_fields": []}
            base_plan = {"page": "strategies", "result": "prepared",
                         "dependencies": found["base"],
                         "found_intent": {"config_revision": found["base"],
                                          "commit_authorized": False},
                         "found_batch": {"youtube": {}, "user": {}, "auto": {}}}
            def raw(x):
                return json.dumps(x).encode()
            for changed in (
                {"page": "voice"},
                {"found_batch": {"youtube": {}, "auto": {}, "user": {}}},
                {"found_intent": {"config_revision": found["base"],
                                  "commit_authorized": True}},
                {"dependencies": "f" * 64},
                {"found_batch": {}},
            ):
                with self.subTest(changed=changed):
                    with self.assertRaisesRegex(SharedOperationError, "unqualified"):
                        store.prepare_found(found, raw({**base_plan, **changed}),
                                            lambda _: True)
            with self.assertRaisesRegex(SharedOperationError, "unverified"):
                store.prepare_found(found, raw(base_plan), lambda _: False)
            self.assertFalse(store.root.exists())
            good = store.prepare_found(found, raw(base_plan), lambda _: True)
            before = (store.root / "operation.json").read_bytes()
            with self.assertRaisesRegex(SharedOperationError, "unfinished"):
                store.prepare_found({**found, "id": "d" * 32},
                                    raw(base_plan), lambda _: True)
            self.assertEqual((store.root / "operation.json").read_bytes(), before)
            record = json.loads(before)
            record["found"]["plan_sha256"] = "bad"
            (store.root / "operation.json").write_text(json.dumps(record))
            with self.assertRaisesRegex(SharedOperationError, "invalid sealed found"):
                store.read()

    # Retired private Telegram PoC migration/rollback test matrix was removed
    # by owner decision. Only active shared Apply durability is exercised here.

    def test_reviewed_native_only_proved_auto_transition_may_close(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SharedApplyOperation(Path(tmp) / "shared-apply")
            old = {"id": "a" * 32, "page": "strategies", "base": "e" * 64,
                   "candidate": "c" * 64, "changed_fields": []}
            fresh = {"id": "b" * 32, "page": "strategies",
                     "base": old["candidate"], "candidate": "d" * 64,
                     "changed_fields": ["hostlist.mode"]}
            for phase in ("prepared", "activating", "activated", "config-saved", "committed"):
                store.advance(phase, old)
            for phase in ("prepared", "activating", "activated", "requires-review"):
                store.advance(phase, fresh)
            before = store.read()
            self.assertEqual(store.reviewed_native_detail(), fresh)
            with self.assertRaises(SharedOperationError):
                store.advance("committed", fresh)  # generic bypass remains banned
            for ident, proof in (("f" * 32, lambda: True),
                                 (fresh["id"], lambda: False),
                                 (fresh["id"], None)):
                with self.assertRaises(SharedOperationError):
                    store.finish_reviewed_native(ident, proof)
                self.assertEqual(store.read(), before)
            proof = store.finish_reviewed_native(fresh["id"], lambda: True)
            self.assertEqual(proof["phase"], "committed")
            self.assertEqual(committed_owner(proof), fresh)
            self.assertEqual(proof["previous"], old)
            with self.assertRaises(SharedOperationError):
                store.reviewed_native_detail()
        for kind in ("unrelated-field", "wrong-base", "unchanged",
                     "wrong-page", "first-install"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                store = SharedApplyOperation(Path(tmp) / "shared-apply")
                old = {"id": "a" * 32, "page": "strategies", "base": "e" * 64,
                       "candidate": "c" * 64, "changed_fields": []}
                fresh = {"id": "b" * 32, "page": "strategies",
                         "base": old["candidate"], "candidate": "d" * 64,
                         "changed_fields": ["hostlist.mode"]}
                if kind != "first-install":
                    for phase in ("prepared", "activating", "activated", "config-saved", "committed"):
                        store.advance(phase, old)
                if kind == "unrelated-field":
                    fresh["changed_fields"] = ["hostlist.userdomains"]
                elif kind == "wrong-base":
                    fresh["base"] = "f" * 64
                elif kind == "unchanged":
                    fresh["candidate"] = fresh["base"]
                elif kind == "wrong-page":
                    fresh["page"] = "voice"
                for phase in ("prepared", "activating", "requires-review"):
                    store.advance(phase, fresh)
                before = store.read()
                with self.assertRaises(SharedOperationError):
                    store.finish_reviewed_native(fresh["id"], lambda: True)
                self.assertEqual(store.read(), before)

    def test_original_epoch_must_complete_before_terminal_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SharedApplyOperation(Path(tmp) / "shared-apply")
            current = detail("e" * 32)
            for phase in ("prepared", "activating", "activated"):
                store.advance(phase, current)
            with self.assertRaises(SharedOperationError):
                store.advance("epoch-finalizing", detail("f" * 32))
            store.advance("epoch-finalizing", current)
            self.assertIsNone(committed_owner(store.read()))
            with self.assertRaises(SharedOperationError):
                store.advance("prepared", detail("f" * 32))
            with self.assertRaises(SharedOperationError):
                store.advance("activated", current)
            store.advance("requires-review", current)
            self.assertIsNone(committed_owner(store.read()))
            with self.assertRaises(SharedOperationError):
                store.advance("committed", current)
        with tempfile.TemporaryDirectory() as tmp:
            store = SharedApplyOperation(Path(tmp) / "shared-apply")
            current = detail("c" * 32)
            for phase in ("prepared", "activating", "activated",
                          "epoch-finalizing", "committed"):
                store.advance(phase, current)
            self.assertEqual(committed_owner(store.read()), current)
        with tempfile.TemporaryDirectory() as tmp:
            store = SharedApplyOperation(Path(tmp) / "shared-apply")
            current = detail("a" * 32)
            for phase in ("prepared", "activating", "activated", "config-saved"):
                store.advance(phase, current)
            with self.assertRaises(SharedOperationError):
                store.advance("epoch-finalizing", current)

    def test_retired_telegram_predecessor_api_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            j=SharedApplyOperation(Path(tmp)/"shared-apply")
            for phase in ("legacy-quiescing", "legacy-marker-retired",
                          "legacy-common-committing", "legacy-rollback-marker"):
                with self.assertRaises(SharedOperationError):
                    j.advance(phase, detail())
            self.assertFalse(hasattr(j, "prepare_legacy_predecessor"))
            self.assertFalse(hasattr(j, "begin_legacy_quiesce"))
            self.assertFalse(j.root.exists())
            cli=BACKEND/"shared_apply_operation.py"
            result=subprocess.run([sys.executable,str(cli),"arm-legacy",
                                   "1"*32,"a"*64,"b"*64,"-"],
                                  capture_output=True,text=True,check=False)
            self.assertEqual(64,result.returncode)
            j.advance("prepared",detail())
            target=j.root/"operation.json"
            record=json.loads(target.read_text())
            record["legacy_predecessor"]="c"*64
            target.write_text(json.dumps(record))
            with self.assertRaisesRegex(SharedOperationError,"invalid common Apply record"):
                j.read()

    def test_remove_prepared_cold_recovery_has_exact_old_journal_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = SharedApplyOperation(root/"shared-apply")
            old = detail("a"*32)
            for phase in ("prepared","activating","activated","config-saved","committed"):
                store.advance(phase, old)
            state = root/"extra-resources"
            (state/"transaction").mkdir(parents=True)
            journal = state/"transaction/journal.json"
            resource = {"schema":1,"mode":"remove","phase":"restarting",
                        "previous":{"lua/extra.lua":"e"*64},"incoming":{},
                        "source_commit":"f"*40,
                        "native_owner":{"id":old["id"],"page":old["page"],
                                        "candidate":old["candidate"]}}
            journal.write_text(json.dumps(resource))
            self.assertIsNone(native_remove_prepared_trial(store.root,state))
            new = {"id":"b"*32,"page":"strategies",
                   "base":old["candidate"],"candidate":old["candidate"],
                   "changed_fields":[]}
            store.advance("prepared",new)
            self.assertEqual(native_remove_prepared_trial(store.root,state),
                             {"id":new["id"],"phase":"prepared","old":resource["native_owner"]})
            store.advance("activating",new)
            self.assertEqual(native_remove_prepared_trial(store.root,state),
                             {"id":new["id"],"phase":"activating",
                              "old":resource["native_owner"]})
            store.advance("activated",new)
            self.assertEqual(native_remove_prepared_trial(store.root,state),
                             {"id":new["id"],"phase":"activated",
                              "old":resource["native_owner"]})
            before = (store.root/"operation.json").read_bytes()
            for bad in ("stopping","publishing","completed"):
                resource["phase"] = bad
                journal.write_text(json.dumps(resource))
                with self.assertRaisesRegex(SharedOperationError,"no quarantined"):
                    native_remove_prepared_trial(store.root,state)
            resource["phase"]="restarting"
            resource["native_owner"]["id"]="c"*32
            journal.write_text(json.dumps(resource))
            with self.assertRaisesRegex(SharedOperationError,"foreign or changed"):
                native_remove_prepared_trial(store.root,state)
            resource["native_owner"]["id"]=old["id"]
            journal.write_text(json.dumps(resource))
            self.assertEqual((store.root/"operation.json").read_bytes(),before)
            store.finish_activated_restore(new["id"],old["id"],lambda:True)
            self.assertIsNone(native_remove_prepared_trial(store.root,state))

    def test_remove_config_saved_can_restore_only_unchanged_old_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = SharedApplyOperation(root/"shared-apply")
            old = detail("a"*32)
            for phase in ("prepared","activating","activated","config-saved","committed"):
                store.advance(phase,old)
            state = root/"extra-resources"
            (state/"transaction").mkdir(parents=True)
            resource = {
                "schema":1,"mode":"remove","phase":"restarting",
                "previous":{"lua/custom.lua":"e"*64},"incoming":{},
                "source_commit":"f"*40,
                "native_owner":{"id":old["id"],"page":old["page"],
                                "candidate":old["candidate"]},
            }
            path = state/"transaction/journal.json"
            path.write_text(json.dumps(resource))
            trial = {"id":"b"*32,"page":"strategies",
                     "base":old["candidate"],"candidate":old["candidate"],
                     "changed_fields":[]}
            for phase in ("prepared","activating","activated","config-saved"):
                store.advance(phase,trial)
            self.assertEqual(native_remove_prepared_trial(store.root,state)["phase"],
                             "config-saved")
            self.assertTrue(native_lifecycle_gate(
                "common-recover-saved",root=store.root)["safe_to_mutate"])
            self.assertFalse(native_lifecycle_gate(
                "common-recover-activated",root=store.root)["safe_to_mutate"])
            # Generic journal writer remains forbidden to roll back a saved
            # ordinary Apply; only the Remove-specific verified method works.
            with self.assertRaisesRegex(SharedOperationError,"illegal"):
                store.advance("restored",trial)
            with self.assertRaisesRegex(SharedOperationError,"predecessor"):
                store.finish_saved_remove_restore(trial["id"],"c"*32,lambda:True,state)
            with self.assertRaisesRegex(SharedOperationError,"attested"):
                store.finish_saved_remove_restore(trial["id"],old["id"],lambda:False,state)
            self.assertEqual(store.read()["phase"],"config-saved")
            for bad_phase in ("stopping","publishing","completed"):
                resource["phase"]=bad_phase
                path.write_text(json.dumps(resource))
                with self.assertRaisesRegex(SharedOperationError,"no quarantined"):
                    store.finish_saved_remove_restore(trial["id"],old["id"],lambda:True,state)
            resource["phase"]="restarting"
            resource["native_owner"]["id"]="c"*32
            path.write_text(json.dumps(resource))
            with self.assertRaisesRegex(SharedOperationError,"foreign"):
                store.finish_saved_remove_restore(trial["id"],old["id"],lambda:True,state)
            resource["native_owner"]["id"]=old["id"]
            path.write_text(json.dumps(resource))
            attests=[]
            restored=store.finish_saved_remove_restore(
                trial["id"],old["id"],lambda: (attests.append("old-live") or True),state)
            self.assertEqual(["old-live"],attests)
            self.assertEqual(restored["phase"],"restored")
            self.assertEqual(old,committed_owner(restored))
            with self.assertRaisesRegex(SharedOperationError,"config-saved"):
                store.finish_saved_remove_restore(trial["id"],old["id"],lambda:True,state)
            with self.assertRaisesRegex(SharedOperationError,"saved-only"):
                store.finish_saved(trial["id"],lambda:True)

    def test_remove_config_saved_refuses_modified_strategies_or_voice(self):
        for changed in (["strategy.tcp"],[],):
            with self.subTest(changed=changed):
                with tempfile.TemporaryDirectory() as tmp:
                    root=Path(tmp)
                    j=SharedApplyOperation(root/"shared-apply")
                    old=detail("a"*32)
                    for phase in ("prepared","activating","activated","config-saved","committed"):
                        j.advance(phase,old)
                    state=root/"extra-resources"
                    (state/"transaction").mkdir(parents=True)
                    resource={"schema":1,"mode":"remove","phase":"restarting",
                         "previous":{"lua/extra.lua":"e"*64},"incoming":{},
                         "source_commit":"f"*40,
                         "native_owner":{"id":old["id"],"page":old["page"],
                                         "candidate":old["candidate"]}}
                    (state/"transaction/journal.json").write_text(json.dumps(resource))
                    new={"id":"b"*32,"page":"strategies",
                         "base":old["candidate"],
                         "candidate":("d"*64 if not changed else old["candidate"]),
                         "changed_fields":changed}
                    for phase in ("prepared","activating","activated","config-saved"):
                        j.advance(phase,new)
                    with self.assertRaisesRegex(SharedOperationError,"foreign or changed"):
                        j.finish_saved_remove_restore(new["id"],old["id"],lambda:True,state)
                    self.assertEqual(j.read()["phase"],"config-saved")

    def test_remove_saved_finish_cli_refuses_non_fd9_authority(self):
        result=subprocess.run(
            [sys.executable,str(BACKEND/"shared_apply_operation.py"),
             "finish-remove-saved","a"*32,"b"*32],
            capture_output=True,text=True,check=False)
        self.assertEqual(result.returncode,69)
        self.assertNotIn("Traceback",result.stderr)

    def test_native_trial_requires_existing_pinned_old_owner_and_restart_phase(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = SharedApplyOperation(root/"shared-apply")
            old = detail("a"*32)
            for phase in ("prepared","activating","activated","config-saved","committed"):
                store.advance(phase, old)
            state = root/"extra-resources"
            (state/"transaction").mkdir(parents=True)
            trial_journal = state/"transaction/journal.json"
            transaction = {"schema":1,"mode":"remove","phase":"restarting",
                "previous":{"lua/custom.lua":"e"*64},"incoming":{},
                "source_commit":"f"*40,
                "native_owner":{"id":old["id"],"page":old["page"],
                                "candidate":old["candidate"]}}
            trial_journal.write_text(json.dumps(transaction))
            self.assertEqual(native_remove_trial_context(store.root,state),
                             transaction["native_owner"])
            for phase in ("stopping","publishing","completed"):
                transaction["phase"] = phase
                trial_journal.write_text(json.dumps(transaction))
                with self.assertRaisesRegex(SharedOperationError,"no prepared"):
                    native_remove_trial_context(store.root,state)
            transaction["phase"] = "restarting"
            transaction["native_owner"]["id"] = "f"*32
            trial_journal.write_text(json.dumps(transaction))
            with self.assertRaisesRegex(SharedOperationError,"previous common owner"):
                native_remove_trial_context(store.root,state)
            transaction["native_owner"]["id"] = old["id"]
            trial_journal.write_text(json.dumps(transaction))
            next_detail = {"id":"c"*32,"page":"strategies",
                           "base":old["candidate"],"candidate":old["candidate"],
                           "changed_fields":[]}
            store.advance("prepared",next_detail)
            with self.assertRaisesRegex(SharedOperationError,"previous common owner"):
                native_remove_trial_context(store.root,state)

    def test_exact_committed_remove_rollback_reinstates_predecessor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = SharedApplyOperation(root/"shared-apply")
            old = detail("a"*32)
            for phase in ("prepared", "activating", "activated", "config-saved", "committed"):
                store.advance(phase, old)
            new = {"id": "c"*32, "page": "strategies",
                   "base": old["candidate"], "candidate": old["candidate"],
                   "changed_fields": []}
            for phase in ("prepared", "activating", "activated", "config-saved", "committed"):
                store.advance(phase, new)
            txwork = root/"extra-resources"/"transaction"
            txwork.mkdir(parents=True)
            (txwork/"journal.json").write_text(json.dumps({
                "schema": 1, "mode": "remove", "phase": "restarting",
                "previous": {"lua/orphan.lua": "f"*64}, "incoming": {}, "source_commit": "d"*40,
                "native_owner": {"id":old["id"], "page":old["page"],
                                 "candidate":old["candidate"]},
            }))
            evidence = native_remove_rollback_pair(store.root, root/"extra-resources")
            self.assertEqual(evidence["state"], "trial")
            self.assertEqual(evidence["trial"], new["id"])
            before = (store.root/"operation.json").read_bytes()
            for new_id, old_id, attested in (
                ("e"*32, old["id"], True),
                (new["id"], "f"*32, True),
                (new["id"], old["id"], False),
            ):
                with self.assertRaises(SharedOperationError):
                    store.revert_committed_remove(new_id, old_id, lambda:attested)
                self.assertEqual(before, (store.root/"operation.json").read_bytes())
            store.revert_committed_remove(new["id"], old["id"], lambda:True)
            self.assertEqual(store.read()["phase"], "restored")
            self.assertEqual(committed_owner(store.read()), old)
            self.assertTrue(native_lifecycle_gate("strategy-lab-native", root=store.root)["safe_to_mutate"])
            self.assertEqual(native_remove_rollback_pair(
                store.root, root/"extra-resources")["state"], "old")
            with self.assertRaises(SharedOperationError):
                store.revert_committed_remove(new["id"], old["id"], lambda:True)

    def test_remove_rollback_refuses_foreign_owner_and_modified_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = SharedApplyOperation(root/"shared-apply")
            old = detail("a"*32)
            for phase in ("prepared", "activating", "activated", "config-saved", "committed"):
                store.advance(phase, old)
            txwork = root/"extra-resources"/"transaction"
            txwork.mkdir(parents=True)
            item = {"schema":1, "mode":"remove", "phase":"restarting",
                    "previous":{"lua/orphan.lua":"f"*64}, "incoming":{}, "source_commit":"d"*40,
                    "native_owner":{"id":"e"*32,"page":old["page"],
                                    "candidate":old["candidate"]}}
            journal = txwork/"journal.json"
            journal.write_text(json.dumps(item))
            with self.assertRaises(SharedOperationError):
                native_remove_rollback_pair(store.root, root/"extra-resources")
            item["native_owner"]["id"] = old["id"]
            journal.write_text(json.dumps(item))
            self.assertEqual(native_remove_rollback_pair(
                store.root, root/"extra-resources")["state"], "old")
            trial = {"id":"c"*32, "page":"strategies", "base":old["candidate"],
                     "candidate":"f"*64, "changed_fields":[]}
            for phase in ("prepared","activating","activated","config-saved","committed"):
                store.advance(phase, trial)
            with self.assertRaisesRegex(SharedOperationError, "unchanged Config mismatch"):
                native_remove_rollback_pair(store.root, root/"extra-resources")
            with self.assertRaises(SharedOperationError):
                store.revert_committed_remove(trial["id"],old["id"],lambda:True)
            item["mode"] = "install"
            journal.write_text(json.dumps(item))
            with self.assertRaisesRegex(SharedOperationError, "pending Remove"):
                native_remove_rollback_pair(store.root, root/"extra-resources")

    def test_owner_witness_uses_only_terminal_journal(self):
        with tempfile.TemporaryDirectory() as folder:
            j = SharedApplyOperation(Path(folder)/"shared-apply")
            first = detail()
            with self.assertRaises(SharedOperationError):
                native_committed_owner_witness(j.root)
            j.advance("prepared", first)
            with self.assertRaises(SharedOperationError):
                native_committed_owner_witness(j.root)
            for phase in ("activating", "activated", "config-saved", "committed"):
                j.advance(phase, first)
            self.assertEqual(native_committed_owner_witness(j.root),
                             {"id": first["id"], "page": first["page"],
                              "candidate": first["candidate"]})
            second = detail("2"*32)
            j.advance("prepared", second)
            with self.assertRaises(SharedOperationError):
                native_committed_owner_witness(j.root)
            j.advance("restored", second)
            self.assertEqual(native_committed_owner_witness(j.root)["id"],
                             first["id"])
            (j.root/"operation.json").write_text("broken")
            with self.assertRaises(SharedOperationError):
                native_committed_owner_witness(j.root)

    def test_bound_successor_prepare_is_detached_only(self):
        import os
        from shared_apply_operation import native_bound_prepare_gate
        from shared_apply_render import regular

        old = detail("1" * 32)
        op = "2" * 32
        pin = {"schema": 1, "generation": old["id"], "root_sha256": "c" * 64,
               "seal_sha256": "d" * 64, "candidate_sha256": old["candidate"]}
        record = {"schema": 1, "phase": "committed", "detail": old, "manifest": pin}
        plan = {"result": "prepared", "page": "strategies", "dependencies": old["candidate"],
                "candidate": {"general": {"enabled": "1"}, "hostlist": {"mode": "list"}}}
        uid = os.geteuid()
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            root = Path(tmp)
            work = root / "work"
            work.mkdir(mode=0o700)
            candidate = work / op
            candidate.mkdir(mode=0o700)
            xml = candidate / "candidate.xml"
            xml.write_bytes(b"detached XML")
            xml.chmod(0o600)
            plan_file = candidate / "plan.json"
            plan_file.write_text(json.dumps(plan))
            plan_file.chmod(0o600)
            store = SharedApplyOperation(root / "journal", owner=uid)
            store._persist_record(record)
            original = (store.root / "operation.json").read_bytes()
            stack.enter_context(patch("shared_apply_operation.SharedApplyOperation", return_value=store))
            stack.enter_context(patch("shared_apply_operation.sys.platform", "freebsd15"))
            stack.enter_context(patch("shared_apply_operation.os.geteuid", return_value=0))
            stack.enter_context(patch("voice_ipfw_adapter.require_lifecycle_lock"))
            stack.enter_context(patch("shared_apply_seal.WORK", work))
            stack.enter_context(patch("shared_apply_render.regular", side_effect=
                lambda path, owner, **kw: regular(path, uid, **kw)))
            pins = stack.enter_context(patch("neutral_root_stage.verify_original_operation_pins"))
            native_bound_prepare_gate(op)
            self.assertEqual(pins.call_count, 2)
            self.assertFalse(native_lifecycle_gate("common-apply", root=store.root)["safe_to_mutate"])
            for patch_plan in ({"dependencies": "0" * 64}, {"found_intent": {}},
                               {"candidate": {"general": {"enabled": "1"}, "hostlist": {"mode": "auto"}}},
                               {"candidate": []}, {"page": "voice"}):
                with self.subTest(plan=patch_plan):
                    plan_file.write_text(json.dumps({**plan, **patch_plan}))
                    with self.assertRaises(SharedOperationError):
                        native_bound_prepare_gate(op)
            plan_file.write_text(json.dumps(plan))
            for bad in (old["id"], "invalid"):
                with self.assertRaises(SharedOperationError):
                    native_bound_prepare_gate(bad)
            residue = candidate / "release"
            residue.mkdir()
            with self.assertRaises(SharedOperationError):
                native_bound_prepare_gate(op)
            residue.rmdir()
            xml.unlink()
            xml.symlink_to(plan_file)
            with self.assertRaises(RuntimeError):
                native_bound_prepare_gate(op)
            xml.unlink()
            xml.write_bytes(b"detached XML")
            xml.chmod(0o600)
            pins.side_effect = RuntimeError("foreign original pin")
            with self.assertRaises(RuntimeError):
                native_bound_prepare_gate(op)
            pins.side_effect = None
            for phase in ("activated", "restored"):
                store._persist_record({**record, "phase": phase})
                with self.assertRaises(SharedOperationError):
                    native_bound_prepare_gate(op)
            store._persist_record(record)
            self.assertEqual((store.root / "operation.json").read_bytes(), original)
            self.assertEqual(set(candidate.iterdir()), {xml, plan_file})
            self.assertEqual(xml.read_bytes(), b"detached XML")
            self.assertEqual(json.loads(plan_file.read_bytes()), plan)

    def test_native_gate_uses_only_trusted_shared_apply_owner(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            shared=root/"shared-apply"
            j=SharedApplyOperation(shared)
            for abandoned in ("voice-cutover", "voice-ipfw",
                              "voice-cutover-legacy-whole-receipt"):
                (root/abandoned).write_text("retired-old-evidence")
            self.assertTrue(native_lifecycle_gate(root=shared)["safe_to_mutate"])
            self.assertFalse(shared.exists())
            d1=detail()
            self.assertTrue(native_lifecycle_gate(root=shared)["safe_to_mutate"])
            j.advance("prepared",d1)
            self.assertFalse(native_lifecycle_gate("strategy-lab-native",root=shared)["safe_to_mutate"])
            self.assertFalse(native_lifecycle_gate(root=shared)["safe_to_mutate"])
            j.advance("activating",d1)
            self.assertFalse(native_lifecycle_gate(root=shared)["safe_to_mutate"])
            self.assertTrue(native_lifecycle_gate("common-recover-activating",root=shared)["safe_to_mutate"])
            self.assertFalse(native_lifecycle_gate("common-recover-saved",root=shared)["safe_to_mutate"])
            j.advance("activated",d1)
            self.assertTrue(native_lifecycle_gate("common-recover-activated",root=shared)["safe_to_mutate"])
            j.advance("config-saved",d1)
            self.assertTrue(native_lifecycle_gate("common-recover-saved",root=shared)["safe_to_mutate"])
            self.assertFalse(native_lifecycle_gate("common-apply",root=shared)["safe_to_mutate"])
            j.advance("committed",d1)
            self.assertFalse(native_lifecycle_gate(root=shared)["safe_to_mutate"])
            self.assertTrue(native_lifecycle_gate("common-apply",root=shared)["safe_to_mutate"])
            self.assertTrue(native_lifecycle_gate("strategy-lab-native",root=shared)["safe_to_mutate"])
            self.assertFalse(native_lifecycle_gate(root=shared)["safe_to_mutate"])
            with self.assertRaises(SharedOperationError):
                native_lifecycle_gate("legacy-skip",root=shared)
            (shared/"operation.json").write_text("untrusted")
            with self.assertRaises(SharedOperationError):
                native_lifecycle_gate("common-apply",root=shared)

    def test_production_service_uses_shared_gate_without_old_cutover(self):
        service=(BACKEND.parent/"zapret_service.sh").read_text()
        gate=service.split("preflight_shared_apply_journal()\n{",1)[1].split("\n}\n",1)[0]
        self.assertIn("shared_apply_operation.py",gate)
        self.assertIn('native-gate "$@"',gate)
        self.assertNotIn("voice_cutover_guard.py",gate)
        self.assertNotIn("voice-cutover",gate)
        cli=BACKEND/"shared_apply_operation.py"
        for arguments,expected in ((["native-gate"],69),
                                   (["native-gate","common-apply"],69),
                                   (["native-gate","bogus"],64)):
            result=subprocess.run([sys.executable,str(cli),*arguments],
                                  capture_output=True,text=True,check=False)
            self.assertEqual(expected,result.returncode, result.stderr)
            self.assertNotIn("Traceback",result.stderr)

    def test_reviewed_legacy_only_exact_first_voice_with_witness(self):
        with tempfile.TemporaryDirectory() as d:
            j=SharedApplyOperation(Path(d)/"shared-apply")
            item=detail()
            with self.assertRaises(SharedOperationError):
                j.reviewed_legacy_detail()
            for phase in ("prepared","activating","requires-review"):
                j.advance(phase,item)
            self.assertEqual(item,j.reviewed_legacy_detail())
            self.assertTrue(native_lifecycle_gate(
                "common-recover-reviewed-legacy",root=j.root)["safe_to_mutate"])
            self.assertFalse(native_lifecycle_gate("common-apply",root=j.root)["safe_to_mutate"])
            evidence=(j.root/"operation.json").read_bytes()
            for ident,proof in (("2"*32,lambda:True),(item["id"],lambda:False)):
                with self.assertRaises(SharedOperationError):
                    j.finish_reviewed_legacy(ident,proof)
                self.assertEqual(evidence,(j.root/"operation.json").read_bytes())
            self.assertEqual("restored",
                             j.finish_reviewed_legacy(item["id"],lambda:True)["phase"])
            self.assertTrue(native_lifecycle_gate("common-apply",root=j.root)["safe_to_mutate"])
            with self.assertRaises(SharedOperationError):
                j.finish_reviewed_legacy(item["id"],lambda:True)
        with tempfile.TemporaryDirectory() as d:
            j=SharedApplyOperation(Path(d)/"shared-apply")
            original=detail("a"*32)
            for phase in ("prepared","activating","activated","config-saved","committed"):
                j.advance(phase,original)
            second=detail("b"*32)
            for phase in ("prepared","activating","requires-review"):
                j.advance(phase,second)
            with self.assertRaises(SharedOperationError):
                j.reviewed_legacy_detail()
            self.assertEqual("requires-review",j.read()["phase"])

    def test_missing_state_stays_readonly(self):
        with tempfile.TemporaryDirectory() as d:
            j=SharedApplyOperation(Path(d)/"shared-apply")
            self.assertTrue(j.advisory()["safe_to_mutate"])
            self.assertFalse(j.root.exists())

    def test_phase_chain_durable_guard_terminal_new_operation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            j=SharedApplyOperation(root/"shared-apply")
            for phase in ("prepared","activating","activated","config-saved"):
                j.advance(phase,detail())
                snapshot=(j.root/"operation.json").read_bytes()
                guard=native_lifecycle_gate(root=root/"shared-apply")
                self.assertEqual(("blocked","shared-apply-pending",phase),
                                 (guard["state"],guard["reason"],guard["phase"]))
                self.assertEqual(snapshot,(j.root/"operation.json").read_bytes())
                self.assertEqual(0o700,j.root.stat().st_mode & 0o777)
                self.assertEqual(0o600,(j.root/"operation.json").stat().st_mode & 0o777)
            j.advance("committed",detail())
            self.assertTrue(j.advisory()["safe_to_mutate"])
            self.assertEqual("shared-runtime-owned",
                             native_lifecycle_gate(root=root/"shared-apply")["reason"])
            self.assertTrue(native_lifecycle_gate("common-apply", root=root/"shared-apply")["safe_to_mutate"])
            with self.assertRaises(SharedOperationError):
                j.advance("prepared",detail())
            j.advance("prepared",detail("2"*32))
            self.assertFalse(j.advisory()["safe_to_mutate"])

    def test_rollback_uncertainty_and_replay_refusal(self):
        samples=(
            ("prepared","activating","activated","restored"),
            ("prepared","activating","requires-review"),
            ("prepared","activating","activated","restore-failed"),
            ("prepared","activating","activated","config-saved","requires-review"),
        )
        for phases in samples:
            with self.subTest(phases=phases),tempfile.TemporaryDirectory() as d:
                j=SharedApplyOperation(Path(d)/"shared-apply")
                for p in phases:j.advance(p,detail())
                self.assertEqual(phases[-1]=="restored",j.advisory()["safe_to_mutate"])
                with self.assertRaises(SharedOperationError):
                    j.advance("activated",detail())

    def test_inspect_cli_has_no_root_override_and_requires_freebsd_fd9(self):
        cli=BACKEND/"shared_apply_operation.py"
        result=subprocess.run([sys.executable,str(cli),"inspect"],
                              text=True,capture_output=True,check=False)
        self.assertEqual(69,result.returncode)
        invalid=subprocess.run([sys.executable,str(cli),"inspect","/tmp/other"],
                               capture_output=True,check=False)
        self.assertEqual(64,invalid.returncode)
        safe_recovery=subprocess.run(
            [sys.executable,str(cli),"recover-prepared","1"*32],
            capture_output=True,text=True,check=False,
        )
        self.assertEqual(69,safe_recovery.returncode,
                         "recovery must refuse missing FreeBSD FD9 instead of crashing")
        self.assertNotIn("Traceback",safe_recovery.stderr)

    def test_prepared_only_recovery_attests_before_terminal_record(self):
        with tempfile.TemporaryDirectory() as folder:
            journal=SharedApplyOperation(Path(folder)/"shared-apply")
            d=detail()
            journal.advance("prepared",d)
            attempts=[]
            def witness():
                attempts.append("verified")
                return True
            journal.recover_prepared(d["id"],witness)
            self.assertEqual(["verified"],attempts)
            self.assertEqual("restored",journal.read()["phase"])
            with self.assertRaisesRegex(SharedOperationError,"prepared-only"):
                journal.recover_prepared(d["id"],witness)
        with tempfile.TemporaryDirectory() as folder:
            journal=SharedApplyOperation(Path(folder)/"shared-apply")
            d=detail()
            journal.advance("prepared",d)
            with self.assertRaisesRegex(SharedOperationError,"attestation"):
                journal.recover_prepared(d["id"],lambda: False)
            self.assertEqual("prepared",journal.read()["phase"])
            journal.advance("activating",d)
            with self.assertRaisesRegex(SharedOperationError,"prepared-only"):
                journal.recover_prepared(d["id"],lambda: True)
            self.assertEqual("activating",journal.read()["phase"])

    def test_previous_committed_owner_survives_prepared_power_cut_and_rollback(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            store=SharedApplyOperation(root/"shared-apply")
            initial=detail("a"*32)
            next_owner=detail("b"*32)
            for phase in ("prepared","activating","activated","config-saved","committed"):
                store.advance(phase,initial)
            self.assertEqual(initial,committed_owner(store.read()))
            prepared=store.advance("prepared",next_owner)
            self.assertEqual(initial,prepared["previous"])
            self.assertEqual("shared-apply-pending",
                             native_lifecycle_gate(root=root/"shared-apply")["reason"])
            restored=store.recover_prepared(next_owner["id"],lambda: True)
            self.assertEqual(initial,restored["previous"])
            self.assertEqual(initial,committed_owner(store.read()))
            old=native_lifecycle_gate(root=root/"shared-apply")
            self.assertEqual("shared-runtime-owned",old["reason"])
            self.assertFalse(old["safe_to_mutate"])
            self.assertTrue(native_lifecycle_gate("common-apply", root=root/"shared-apply")["safe_to_mutate"])
            with self.assertRaisesRegex(SharedOperationError,"predecessor ID"):
                store.advance("prepared",initial)
            third=detail("c"*32)
            carry=store.advance("prepared",third)
            self.assertEqual(initial,carry["previous"])

    def test_previous_common_owner_remains_during_safe_pre_save_rollback(self):
        with tempfile.TemporaryDirectory() as temp:
            store=SharedApplyOperation(Path(temp)/"shared-apply")
            first=detail("a"*32)
            second=detail("b"*32)
            for phase in ("prepared","activating","activated","config-saved","committed"):
                store.advance(phase,first)
            for phase in ("prepared","activating","activated","restored"):
                store.advance(phase,second)
            self.assertEqual(first,committed_owner(store.read()))
            self.assertEqual(first,store.read()["previous"])
            self.assertTrue(store.advisory()["safe_to_mutate"])

    def test_untrusted_predecessor_proof_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            store=SharedApplyOperation(root/"shared-apply")
            store.advance("prepared",detail("b"*32))
            import json
            path=store.root/"operation.json"
            record=json.loads(path.read_text())
            record["previous"]=detail("b"*32)
            path.write_text(json.dumps(record))
            with self.assertRaises(SharedOperationError):
                native_lifecycle_gate(root=root/"shared-apply")

    def test_pristine_activating_recovery_requires_previous_owner_and_attestation(self):
        with tempfile.TemporaryDirectory() as folder:
            j=SharedApplyOperation(Path(folder)/"shared-apply")
            previous=detail("a"*32)
            candidate=detail("b"*32)
            for phase in ("prepared","activating","activated","config-saved","committed"):
                j.advance(phase,previous)
            j.advance("prepared",candidate)
            j.advance("activating",candidate)
            with self.assertRaisesRegex(SharedOperationError,"pristine"):
                j.recover_activating_pristine(candidate["id"],"c"*32,lambda: True)
            with self.assertRaisesRegex(SharedOperationError,"attestation"):
                j.recover_activating_pristine(candidate["id"],previous["id"],lambda: False)
            self.assertEqual("activating",j.read()["phase"])
            restored=j.recover_activating_pristine(
                candidate["id"],previous["id"],lambda: True)
            self.assertEqual(previous,restored["previous"])
            self.assertEqual(previous,committed_owner(restored))
            with self.assertRaisesRegex(SharedOperationError,"pristine"):
                j.recover_activating_pristine(candidate["id"],previous["id"],lambda: True)
        with tempfile.TemporaryDirectory() as folder:
            j=SharedApplyOperation(Path(folder)/"shared-apply")
            d=detail("c"*32)
            j.advance("prepared",d)
            j.advance("activating",d)
            with self.assertRaisesRegex(SharedOperationError,"pristine"):
                j.recover_activating_pristine(d["id"],"a"*32,lambda: True)
            self.assertEqual("activating",j.read()["phase"])

    def test_cold_activated_completion_requires_predecessor_and_attestation(self):
        with tempfile.TemporaryDirectory() as folder:
            store=SharedApplyOperation(Path(folder)/"shared-apply")
            old=detail("a"*32); new=detail("b"*32)
            for phase in ("prepared","activating","activated","config-saved","committed"):
                store.advance(phase,old)
            for phase in ("prepared","activating","activated"):
                store.advance(phase,new)
            with self.assertRaisesRegex(SharedOperationError,"activated rollback"):
                store.finish_activated_restore(new["id"],"c"*32,lambda: True)
            with self.assertRaisesRegex(SharedOperationError,"attestation"):
                store.finish_activated_restore(new["id"],old["id"],lambda: False)
            self.assertEqual("activated",store.read()["phase"])
            restored=store.finish_activated_restore(new["id"],old["id"],lambda: True)
            self.assertEqual("restored",restored["phase"])
            self.assertEqual(old,committed_owner(restored))
            with self.assertRaisesRegex(SharedOperationError,"activated rollback"):
                store.finish_activated_restore(new["id"],old["id"],lambda: True)
        with tempfile.TemporaryDirectory() as folder:
            store=SharedApplyOperation(Path(folder)/"shared-apply")
            d=detail()
            for phase in ("prepared","activating","activated"):
                store.advance(phase,d)
            with self.assertRaisesRegex(SharedOperationError,"activated rollback"):
                store.finish_activated_restore(d["id"],"a"*32,lambda: True)

    def test_installed_activating_completion_requires_exact_previous(self):
        with tempfile.TemporaryDirectory() as folder:
            store=SharedApplyOperation(Path(folder)/"shared-apply")
            previous=detail("a"*32)
            new=detail("b"*32)
            for phase in ("prepared","activating","activated","config-saved","committed"):
                store.advance(phase,previous)
            store.advance("prepared",new)
            store.advance("activating",new)
            with self.assertRaisesRegex(SharedOperationError,"activating rollback"):
                store.finish_activating_installed_restore(new["id"],"c"*32,lambda: True)
            with self.assertRaisesRegex(SharedOperationError,"attestation"):
                store.finish_activating_installed_restore(new["id"],previous["id"],lambda: False)
            self.assertEqual("activating",store.read()["phase"])
            restored=store.finish_activating_installed_restore(new["id"],previous["id"],lambda: True)
            self.assertEqual(previous,committed_owner(restored))
            self.assertEqual("restored",restored["phase"])
            with self.assertRaisesRegex(SharedOperationError,"activating rollback"):
                store.finish_activating_installed_restore(new["id"],previous["id"],lambda: True)

    def test_installed_activating_cli_refuses_missing_freebsd_fd9(self):
        result=subprocess.run(
            [sys.executable,str(BACKEND/"shared_apply_operation.py"),
             "finish-activating","a"*32,"b"*32],
            capture_output=True,text=True,check=False)
        self.assertEqual(69,result.returncode)
        self.assertNotIn("Traceback",result.stderr)

    def test_activated_cli_refuses_missing_freebsd_fd9(self):
        result=subprocess.run([sys.executable,str(BACKEND/"shared_apply_operation.py"),
                               "finish-activated","a"*32,"b"*32],
                              capture_output=True,text=True,check=False)
        self.assertEqual(69,result.returncode)
        self.assertNotIn("Traceback",result.stderr)

    def test_post_save_recovery_only_after_attested_runtime_commit(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            j=SharedApplyOperation(root/"shared-apply")
            d=detail("4"*32)
            for phase in ("prepared","activating","activated","config-saved"):
                j.advance(phase,d)
            self.assertFalse(native_lifecycle_gate(root=root/"shared-apply")["safe_to_mutate"])
            self.assertFalse(native_lifecycle_gate("common-apply", root=root/"shared-apply")["safe_to_mutate"])
            self.assertTrue(native_lifecycle_gate("common-recover-saved", root=root/"shared-apply")["safe_to_mutate"])
            with self.assertRaisesRegex(SharedOperationError,"attestation"):
                j.finish_saved(d["id"],lambda: False)
            self.assertEqual("config-saved",j.read()["phase"])
            completed=j.finish_saved(d["id"],lambda: True)
            self.assertEqual("committed",completed["phase"])
            with self.assertRaisesRegex(SharedOperationError,"saved-only"):
                j.finish_saved(d["id"],lambda: True)
        with tempfile.TemporaryDirectory() as folder:
            j=SharedApplyOperation(Path(folder)/"shared-apply")
            d=detail()
            for phase in ("prepared","activating","activated"):
                j.advance(phase,d)
            with self.assertRaisesRegex(SharedOperationError,"saved-only"):
                j.finish_saved(d["id"],lambda: True)
            self.assertEqual("activated",j.read()["phase"])

    def test_activating_cli_refuses_unprivileged_or_missing_fd9(self):
        cli=BACKEND/"shared_apply_operation.py"
        result=subprocess.run([sys.executable,str(cli),"recover-activating",
                               "a"*32,"b"*32],
                              capture_output=True,text=True,check=False)
        self.assertEqual(69,result.returncode)
        self.assertNotIn("Traceback",result.stderr)

    def test_saved_finish_cli_refuses_unprivileged_or_missing_fd9(self):
        cli=BACKEND/"shared_apply_operation.py"
        result=subprocess.run([sys.executable,str(cli),"finish-saved","4"*32],
                              capture_output=True,text=True,check=False)
        self.assertEqual(69,result.returncode)
        self.assertNotIn("Traceback",result.stderr)

    def test_invalid_identity_fields_and_reordered_phase(self):
        with tempfile.TemporaryDirectory() as d:
            j=SharedApplyOperation(Path(d)/"shared-apply")
            good=detail()
            for bad in (
                {**good,"id":"wrong"},
                {**good,"page":"unknown"},
                {**good,"base":"bad"},
                {**good,"changed_fields":["hostlist.telegramips"]*2},
                {**good,"changed_fields":["../../etc/passwd"]},
            ):
                with self.assertRaises(SharedOperationError):
                    j.advance("prepared",bad)
            self.assertFalse(j.root.exists())
            j.advance("prepared",good)
            for phase,values in (("committed",good),
                                 ("activated",good),
                                 ("activating",detail("3"*32))):
                with self.assertRaises(SharedOperationError):
                    j.advance(phase,values)
            self.assertEqual("prepared",j.read()["phase"])

    def test_symlink_orphan_corruption_and_foreign_file_block(self):
        for issue in ("orphan","root-link","file-link","bad-json","extra","bad-mode"):
            with self.subTest(issue=issue),tempfile.TemporaryDirectory() as d:
                root=Path(d); j=SharedApplyOperation(root/"shared-apply")
                if issue=="root-link":
                    target=root/"other"; target.mkdir()
                    j.root.symlink_to(target)
                else:
                    # The writer itself creates the trusted root. Creating
                    # an empty root first intentionally represents a crash.
                    if issue in ("file-link","extra","bad-mode"):
                        j.advance("prepared",detail())
                    else:
                        j.root.mkdir(mode=0o700)
                    if issue=="file-link":
                        (j.root/"operation.json").unlink()
                        (j.root/"operation.json").symlink_to(root/"unknown")
                    elif issue=="bad-json":
                        (j.root/"operation.json").write_text("{bad")
                    elif issue=="extra":
                        (j.root/"tmp").write_text("unexpected")
                    elif issue=="bad-mode":
                        j.root.chmod(0o755)
                with self.assertRaises(SharedOperationError):
                    native_lifecycle_gate(root=root/"shared-apply")

    def test_cli_refuses_nonfreebsd_or_missing_fd9(self):
        cli=BACKEND/"shared_apply_operation.py"
        p=subprocess.run([sys.executable,str(cli),"record","prepared",
                          "1"*32,"voice","a"*64,"b"*64,"hostlist.telegramips"],
                         text=True,capture_output=True,check=False)
        self.assertEqual(69,p.returncode)

    def test_existing_service_routes_record_under_fd9(self):
        service=(BACKEND.parent/"zapret_service.sh").read_text()
        self.assertIn("shared_apply_record_service()",service)
        self.assertIn("shared-apply-record)",service)
        self.assertIn("service_with_lifecycle_lock",service)
        guard=service.split("if ! ",1)[0] if False else service.split(
            "# Do not permit ANY legacy lifecycle action",1)[1].split(
            'service_dispatch "$@"',1)[0]
        self.assertNotIn("shared-apply-record",guard)

if __name__=="__main__":
    unittest.main(verbosity=2)
