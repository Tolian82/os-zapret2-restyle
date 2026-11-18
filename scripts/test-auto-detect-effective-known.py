#!/usr/bin/env python3
"""#1052: real staged YouTube/User hostlist + protected known auto-owned rows."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

BACKEND = Path(__file__).resolve().parents[1] / 'src/opnsense/scripts/OPNsense/Zapret/backend'
sys.path.insert(0, str(BACKEND))
from auto_detect_effective_known import (compose_stage, compose_stage_planned,
                                         compose_native_planned, verify_planned_preimages,
                                         verify_native_planned, prepare_native_found_intent,
                                         classify_planned_file_images,
                                         classify_native_planned, EffectiveKnownRefused)
from auto_detect_owned_sources import bootstrap_empty, OwnedSourcesRefused
from auto_detect_destination_commit import DestinationRefused


class EffectiveKnownTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='p2k8c-')
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.base.chmod(0o700)
        self.root = self.base / 'auto-detect-owned'
        self.lock = self.base / '.auto-domains.lock'
        self.uid = os.geteuid()
        self.youtube = self.base / 'hostlist-youtube.out'
        self.user = self.base / 'hostlist-user.out'
        self.youtube.write_text('!blocked.example\n^exact.example\nmanual.example\n')
        self.user.write_text('user.example\n')
        self.youtube.chmod(0o644)
        self.user.chmod(0o644)

    def seed(self):
        bootstrap_empty(self.root, original_config_sha256='a' * 64,
                        owner_uid=self.uid, authorized_clean_start=True)

    def compose(self):
        return compose_stage(self.youtube, self.user, root=self.root,
                             lock=self.lock, owner_uid=self.uid)

    def test_absent_source_preserves_manual_files(self):
        before = (self.youtube.read_bytes(), self.user.read_bytes())
        self.assertEqual(self.compose(), {'status': 'uninitialized', 'changed': []})
        self.assertEqual(before, (self.youtube.read_bytes(), self.user.read_bytes()))
        self.assertFalse(self.root.exists())
        self.assertFalse(self.lock.exists())

    def test_real_normalizer_and_owned_rows(self):
        self.seed()
        raw = self.base / 'raw.txt'
        raw.write_text('https://WWW.Example.COM/path\n!blocked.example\n')
        proc = subprocess.run([sys.executable, str(BACKEND / 'domain_policy.py'),
                               'single', 'youtube', str(raw), str(self.youtube)],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        (self.root / 'youtube.txt').write_text('video.example\nwww.example.com\n')
        (self.root / 'user.txt').write_text('login.example\nsub.blocked.example\n')
        self.assertEqual(self.compose()['changed'], ['youtube', 'user'])
        self.assertEqual(self.youtube.read_text(),
                         'www.example.com\n!blocked.example\nvideo.example\n')
        self.assertEqual(self.user.read_text(), 'user.example\nlogin.example\n')
        self.assertEqual(self.compose()['changed'], [])
        self.assertEqual((self.root / 'youtube.txt').read_text(),
                         'video.example\nwww.example.com\n')

    def test_corrupted_source_refuses_before_any_change(self):
        self.seed()
        (self.root / 'user.txt').write_text('Upper.example\n')
        before = (self.youtube.read_bytes(), self.user.read_bytes())
        with self.assertRaises(OwnedSourcesRefused):
            self.compose()
        self.assertEqual(before, (self.youtube.read_bytes(), self.user.read_bytes()))

    def test_shared_gui_lock_prevents_read_during_gui_save(self):
        self.seed()
        (self.root / 'user.txt').write_text('new.example\n')
        fd = os.open(self.lock, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(DestinationRefused):
                self.compose()
        finally:
            os.close(fd)
        self.assertEqual(self.user.read_text(), 'user.example\n')

    def test_noncanonical_and_symlink_stage_refuse(self):
        self.seed()
        self.youtube.write_text('UPPER.example\n')
        with self.assertRaisesRegex(EffectiveKnownRefused, 'noncanonical_managed'):
            self.compose()
        self.youtube.write_text('manual.example\n')
        self.user.unlink()
        self.user.symlink_to(self.youtube)
        with self.assertRaises(DestinationRefused):
            self.compose()

    def planned_rows(self):
        names = ("youtube", "user", "auto")
        after = {"youtube": "fresh.net\n",
                 "user": "login.net\n",
                 "auto": "fallback.net\n"}
        targets = {name: self.root / (name + ".txt") for name in ("youtube", "user")}
        targets["auto"] = self.base / "auto-domains.txt"
        rows = {}
        for name in names:
            target = targets[name]
            if name == "auto":
                raw = b""
                identity = [0, 0, 0, 0, 0]
                status = "missing"
                revision = hashlib.sha256(b"missing\0").hexdigest()
            else:
                raw = target.read_bytes()
                st = target.lstat()
                identity = [st.st_dev, st.st_ino, st.st_ctime_ns,
                            st.st_mtime_ns, st.st_size]
                status = "present"
                revision = hashlib.sha256(b"present\0" + raw).hexdigest()
            rows[name] = {
                "before": raw.decode(), "after": after[name],
                "before_status": status, "before_revision": revision,
                **dict(zip(("before_device", "before_inode",
                            "before_ctime_ns", "before_mtime_ns",
                            "before_size"), identity)),
            }
        return rows, targets

    def test_planned_composer_uses_sealed_after_not_live_owned(self):
        self.seed()
        rows, targets = self.planned_rows()
        before = {name: targets[name].read_bytes() for name in ("youtube", "user")}
        result = compose_stage_planned(
            self.youtube, self.user, rows, targets=targets,
            owned_root=self.root, lock=self.lock, owner_uid=self.uid)
        self.assertEqual(result["status"], "planned-detached")
        self.assertFalse(result["auto_live_committed"])
        self.assertFalse(result["config_committed"])
        self.assertEqual(result["changed"], ["youtube", "user"])
        self.assertEqual(self.youtube.read_text(),
                         "!blocked.example\n^exact.example\nmanual.example\nfresh.net\n")
        self.assertEqual(self.user.read_text(),
                         "user.example\nlogin.net\n")
        self.assertEqual(before, {
            name: targets[name].read_bytes() for name in ("youtube", "user")
        })
        self.assertFalse(targets["auto"].exists())

    def test_planned_composer_refuses_poststage_minute_find(self):
        self.seed()
        rows, targets = self.planned_rows()
        (self.root / "youtube.txt").write_text("newer.net\n")
        before = (self.youtube.read_bytes(), self.user.read_bytes())
        with self.assertRaisesRegex(EffectiveKnownRefused, "planned_preimage_drift"):
            compose_stage_planned(self.youtube, self.user, rows, targets=targets,
                                  owned_root=self.root, lock=self.lock,
                                  owner_uid=self.uid)
        self.assertEqual(before, (self.youtube.read_bytes(), self.user.read_bytes()))
        self.assertEqual((self.root / "youtube.txt").read_text(),
                         "newer.net\n")

    def test_planned_composer_rejects_replaced_auto_and_tampered_after(self):
        self.seed()
        rows, targets = self.planned_rows()
        targets["auto"].write_text("later.net\n")
        with self.assertRaises(DestinationRefused):
            compose_stage_planned(self.youtube, self.user, rows, targets=targets,
                                  owned_root=self.root, lock=self.lock,
                                  owner_uid=self.uid)
        targets["auto"].unlink()
        rows["youtube"]["after"] = "!malicious.example.com\n"
        with self.assertRaises(DestinationRefused):
            compose_stage_planned(self.youtube, self.user, rows, targets=targets,
                                  owned_root=self.root, lock=self.lock,
                                  owner_uid=self.uid)
        self.assertEqual(self.youtube.read_text(),
                         "!blocked.example\n^exact.example\nmanual.example\n")

    def test_postseal_preimage_gate_is_readonly_and_rejects_minute_race(self):
        self.seed()
        rows, targets = self.planned_rows()
        before = {name: path.read_bytes() for name, path in targets.items()
                  if path.exists()}
        receipt = verify_planned_preimages(rows, targets=targets,
                                           owned_root=self.root, lock=self.lock,
                                           owner_uid=self.uid)
        self.assertEqual(receipt, {"status": "planned-preimages-current",
                                   "commit_authorized": False})
        self.assertEqual(before, {name: path.read_bytes()
                                  for name, path in targets.items() if path.exists()})
        self.assertFalse(targets["auto"].exists())
        (self.root / "youtube.txt").write_text("minute.net\n")
        with self.assertRaisesRegex(EffectiveKnownRefused, "planned_preimage_drift"):
            verify_planned_preimages(rows, targets=targets,
                                     owned_root=self.root, lock=self.lock,
                                     owner_uid=self.uid)
        self.assertEqual((self.root / "youtube.txt").read_text(), "minute.net\n")

    def test_postseal_preimage_gate_refuses_missing_auto_create_and_inode_swap(self):
        self.seed()
        rows, targets = self.planned_rows()
        targets["auto"].write_text("")
        with self.assertRaises(DestinationRefused):
            verify_planned_preimages(rows, targets=targets,
                                     owned_root=self.root, lock=self.lock,
                                     owner_uid=self.uid)
        targets["auto"].unlink()
        target = self.root / "user.txt"
        original = target.read_bytes()
        target.unlink()
        target.write_bytes(original)
        # Known-owned provenance rejects an inode swap before the P2 byte
        # witness itself. This is stricter than the downstream drift gate.
        with self.assertRaises(OwnedSourcesRefused):
            verify_planned_preimages(rows, targets=targets,
                                     owned_root=self.root, lock=self.lock,
                                     owner_uid=self.uid)

    def test_native_postseal_gate_refuses_missing_original_fd9(self):
        with self.assertRaisesRegex(EffectiveKnownRefused, "native_original_fd9_required"):
            verify_native_planned("a" * 32)

    def cold_image(self, rows, targets, phase=None, post=None, staged=None):
        return classify_planned_file_images(
            rows, targets=targets, owned_root=self.root,
            lock=self.lock, owner_uid=self.uid, journal_phase=phase,
            post_images=post, staged_images=staged)

    def cold_pin(self, path):
        st = path.lstat()
        raw = path.read_bytes()
        return {"device": st.st_dev, "inode": st.st_ino,
                "mtime_ns": st.st_mtime_ns, "size": st.st_size,
                "sha256": hashlib.sha256(raw).hexdigest()}

    def cold_install_after(self, rows, targets, name):
        path = targets[name]
        if path.exists():
            path.unlink()
        path.write_text(rows[name]["after"])
        path.chmod(0o600)
        return self.cold_pin(path)

    def test_cold_staged_ready_before_and_ready_after_are_read_only(self):
        self.seed()
        rows, targets = self.planned_rows()
        # Fsynced temporary inode, but the destination still holds BEFORE.
        pin = {"device": 10, "inode": 11, "mtime_ns": 12,
               "size": len(rows["youtube"]["after"].encode()),
               "sha256": hashlib.sha256(rows["youtube"]["after"].encode()).hexdigest()}
        stages = {"youtube": {"state": "ready", "pin": pin}}
        first = self.cold_image(rows, targets, "found-files-writing", staged=stages)
        self.assertEqual(first["stage_evidence"]["youtube"], "ready-but-before")
        self.assertEqual(first["stage_evidence"]["user"], "not-started")
        self.assertFalse(first["restore_authorized"])
        # An identical-byte replacement that did NOT come from pinned inode
        # must not be incorrectly classified as our post-rename image.
        self.cold_install_after(rows, targets, "youtube")
        with self.assertRaisesRegex(
                EffectiveKnownRefused, "cold_found_staged_inode_changed"):
            self.cold_image(rows, targets, "found-files-writing", staged=stages)
        stages["youtube"]["pin"] = self.cold_pin(targets["youtube"])
        second = self.cold_image(rows, targets, "found-files-writing", staged=stages)
        self.assertEqual(second["stage_evidence"]["youtube"], "ready-but-after")
        self.assertFalse(second["commit_authorized"])
        self.assertFalse(second["restore_authorized"])

    def test_cold_staged_installed_requires_original_inode_and_order(self):
        self.seed()
        rows, targets = self.planned_rows()
        pin_y = self.cold_install_after(rows, targets, "youtube")
        stages = {"youtube": {"state": "installed", "pin": pin_y}}
        receipt = self.cold_image(rows, targets, "found-files-writing", staged=stages)
        self.assertEqual(receipt["stage_evidence"]["youtube"], "installed-after")
        self.assertEqual(receipt["stage_evidence"]["user"], "not-started")
        # Keep the first changed source legitimately installed so the
        # later Auto stage is rejected *specifically* for skipping User.
        forged = {"youtube": {"state": "installed", "pin": pin_y},
                  "auto": {"state": "ready", "pin": pin_y}}
        with self.assertRaisesRegex(EffectiveKnownRefused, "out_of_order"):
            self.cold_image(rows, targets, "found-files-writing", staged=forged)
        pin_u = self.cold_install_after(rows, targets, "user")
        stages["user"] = {"state": "ready", "pin": pin_u}
        receipt = self.cold_image(rows, targets, "found-files-writing", staged=stages)
        self.assertEqual(receipt["stage_evidence"]["user"], "ready-but-after")
        # Same byte content but a foreign *inode* is not owned by this WAL.
        other = self.base / "foreign-user.tmp"
        other.write_bytes(targets["user"].read_bytes())
        other.chmod(0o600)
        os.replace(other, targets["user"])
        with self.assertRaisesRegex(EffectiveKnownRefused, "staged_inode_changed"):
            self.cold_image(rows, targets, "found-files-writing", staged=stages)

    def test_cold_staged_missing_auto_and_post_config_require_every_installed(self):
        self.seed()
        rows, targets = self.planned_rows()
        pin_y = self.cold_install_after(rows, targets, "youtube")
        pin_u = self.cold_install_after(rows, targets, "user")
        stages = {"youtube": {"state": "installed", "pin": pin_y},
                  "user": {"state": "installed", "pin": pin_u}}
        pin_a = {"device": 15, "inode": 16, "mtime_ns": 17,
                 "size": len(rows["auto"]["after"].encode()),
                 "sha256": hashlib.sha256(rows["auto"]["after"].encode()).hexdigest()}
        stages["auto"] = {"state": "ready", "pin": pin_a}
        before = self.cold_image(rows, targets, "found-files-writing", staged=stages)
        self.assertEqual(before["stage_evidence"]["auto"], "ready-but-before")
        with self.assertRaisesRegex(EffectiveKnownRefused, "complete_staged_proof_required"):
            self.cold_image(rows, targets, "found-config-saving", staged=stages)
        stages["auto"] = {"state": "installed",
                           "pin": self.cold_install_after(rows, targets, "auto")}
        with self.assertRaisesRegex(EffectiveKnownRefused, "complete_staged_proof_required"):
            self.cold_image(rows, targets, "found-config-saving", staged=stages)
        post = {}
        for name, path in targets.items():
            st = path.lstat()
            post[name] = {"status": "present", "device": st.st_dev,
                          "inode": st.st_ino, "ctime_ns": st.st_ctime_ns,
                          "mtime_ns": st.st_mtime_ns, "size": st.st_size,
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        receipt = self.cold_image(rows, targets, "found-config-saving", post, stages)
        self.assertEqual(receipt["stage_evidence"]["auto"], "installed-after")
        self.assertFalse(receipt["commit_authorized"])
        self.assertFalse(receipt["restore_authorized"])

    def test_cold_staged_rejects_tampered_hash_and_unchanged_and_missing_record(self):
        self.seed()
        rows, targets = self.planned_rows()
        pin = {"device": 13, "inode": 14, "mtime_ns": 15,
               "size": len(rows["youtube"]["after"].encode()),
               "sha256": hashlib.sha256(b"foreign").hexdigest()}
        with self.assertRaisesRegex(EffectiveKnownRefused, "staged_plan_mismatch"):
            self.cold_image(rows, targets, "found-files-writing",
                            staged={"youtube": {"state": "ready", "pin": pin}})
        with self.assertRaisesRegex(EffectiveKnownRefused, "stage_outside_writing"):
            self.cold_image(rows, targets, "prepared", staged={})
        # No staged evidence means no post-rename provenance; the full native
        # caller always supplies stages, but legacy file-only fixtures can omit.
        self.cold_install_after(rows, targets, "youtube")
        with self.assertRaisesRegex(EffectiveKnownRefused, "unstaged_after_image"):
            self.cold_image(rows, targets, "found-files-writing", staged={})
        rows2, targets2 = self.planned_rows()
        rows2["auto"]["after"] = ""
        with self.assertRaisesRegex(EffectiveKnownRefused, "stage_unchanged_source"):
            self.cold_image(rows2, targets2, "found-files-writing",
                            staged={"auto": {"state": "ready", "pin": pin}})

    def test_cold_pin_rejects_identical_byte_foreign_inode(self):
        self.seed()
        rows, targets = self.planned_rows()
        for name in ("youtube", "user", "auto"):
            path = targets[name]
            if path.exists():
                path.unlink()
            path.write_text(rows[name]["after"])
            path.chmod(0o600)
        pins = {}
        for name, path in targets.items():
            st = path.lstat()
            pins[name] = {
                "status": "present", "device": st.st_dev, "inode": st.st_ino,
                "ctime_ns": st.st_ctime_ns, "mtime_ns": st.st_mtime_ns,
                "size": st.st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        receipt = self.cold_image(rows, targets, "found-files-written", pins)
        self.assertFalse(receipt["restore_authorized"])
        self.assertFalse(receipt["commit_authorized"])
        old = targets["youtube"]
        replacement = self.root / "same-byte-foreign"
        replacement.write_bytes(old.read_bytes())
        replacement.chmod(0o600)
        os.replace(replacement, old)
        with self.assertRaisesRegex(
                EffectiveKnownRefused, "cold_found_postimage_inode_changed"):
            self.cold_image(rows, targets, "found-files-written", pins)

    def test_cold_config_attempt_phases_still_require_all_file_after_images(self):
        self.seed()
        rows, targets = self.planned_rows()
        for phase in ("found-config-saving", "found-config-saved"):
            with self.assertRaisesRegex(
                    EffectiveKnownRefused, "cold_found_written_phase_diverged"):
                self.cold_image(rows, targets, phase)
        for name in ("youtube", "user"):
            target = targets[name]
            target.unlink()
            target.write_text(rows[name]["after"])
            target.chmod(0o600)
        targets["auto"].write_text(rows["auto"]["after"])
        targets["auto"].chmod(0o600)
        for phase in ("found-config-saving", "found-config-saved"):
            receipt = self.cold_image(rows, targets, phase)
            self.assertEqual(receipt["image"], "contains-unattributed-after")
            self.assertFalse(receipt["commit_authorized"])
            self.assertFalse(receipt["restore_authorized"])

    def test_cold_prepared_phase_refuses_any_after_image(self):
        self.seed()
        rows, targets = self.planned_rows()
        self.assertEqual(self.cold_image(rows, targets, "prepared")["image"],
                         "all-before")
        targets["youtube"].unlink()
        targets["youtube"].write_text(rows["youtube"]["after"])
        targets["youtube"].chmod(0o600)
        with self.assertRaisesRegex(
                EffectiveKnownRefused, "cold_found_unexpected_prepared_image"):
            self.cold_image(rows, targets, "prepared")
        receipt = self.cold_image(rows, targets, "found-files-writing")
        self.assertEqual(receipt["states"]["youtube"], "after-image")
        self.assertFalse(receipt["commit_authorized"])
        self.assertFalse(receipt["restore_authorized"])

    def test_cold_files_written_requires_every_changed_after_image(self):
        self.seed()
        rows, targets = self.planned_rows()
        with self.assertRaisesRegex(
                EffectiveKnownRefused, "cold_found_written_phase_diverged"):
            self.cold_image(rows, targets, "found-files-written")
        for name in ("youtube", "user"):
            path = targets[name]
            path.unlink()
            path.write_text(rows[name]["after"])
            path.chmod(0o600)
        with self.assertRaisesRegex(
                EffectiveKnownRefused, "cold_found_written_phase_diverged"):
            self.cold_image(rows, targets, "found-files-written")
        targets["auto"].write_text(rows["auto"]["after"])
        targets["auto"].chmod(0o600)
        receipt = self.cold_image(rows, targets, "found-files-written")
        self.assertEqual(receipt["states"], {
            "youtube": "after-image", "user": "after-image",
            "auto": "after-image"})
        self.assertFalse(receipt["commit_authorized"])
        self.assertFalse(receipt["restore_authorized"])

    def test_cold_noop_missing_auto_stays_physically_missing(self):
        self.seed()
        rows, targets = self.planned_rows()
        rows["auto"]["after"] = ""
        # A WRITTEN journal implies every changed source has the intended
        # after-image; only the unchanged Auto may retain a missing before.
        for name in ("youtube", "user"):
            target = targets[name]
            target.unlink()
            target.write_text(rows[name]["after"])
            target.chmod(0o600)
        receipt = self.cold_image(rows, targets, "found-files-written")
        self.assertEqual(receipt["states"]["auto"], "before")
        self.assertFalse(targets["auto"].exists())
        targets["auto"].write_text("")
        targets["auto"].chmod(0o600)
        with self.assertRaises(EffectiveKnownRefused):
            self.cold_image(rows, targets, "found-files-written")

    def test_cold_unrecognized_journal_phase_refused(self):
        self.seed()
        rows, targets = self.planned_rows()
        with self.assertRaisesRegex(
                EffectiveKnownRefused, "cold_found_unknown_journal_phase"):
            self.cold_image(rows, targets, "committed")
        self.assertFalse(targets["auto"].exists())

    def test_cold_classification_all_before_is_readonly(self):
        self.seed()
        rows, targets = self.planned_rows()
        before = {name: path.read_bytes() for name, path in targets.items()
                  if path.exists()}
        receipt = self.cold_image(rows, targets)
        self.assertEqual(receipt["image"], "all-before")
        self.assertEqual(receipt["states"], dict.fromkeys(
            ("youtube", "user", "auto"), "before"))
        self.assertFalse(receipt["commit_authorized"])
        self.assertFalse(receipt["restore_authorized"])
        self.assertFalse(targets["auto"].exists())
        self.assertEqual(before, {name: path.read_bytes()
                                  for name, path in targets.items() if path.exists()})

    def test_cold_classification_partial_after_is_only_unattributed_bytes(self):
        self.seed()
        rows, targets = self.planned_rows()
        targets["youtube"].unlink()
        targets["youtube"].write_text(rows["youtube"]["after"])
        targets["youtube"].chmod(0o600)
        result = self.cold_image(rows, targets)
        self.assertEqual(result["image"], "contains-unattributed-after")
        self.assertEqual(result["states"], {
            "youtube": "after-image", "user": "before", "auto": "before"})
        self.assertFalse(result["restore_authorized"])

    def test_cold_classification_missing_auto_create_is_not_authority(self):
        self.seed()
        rows, targets = self.planned_rows()
        targets["auto"].write_text(rows["auto"]["after"])
        receipt = self.cold_image(rows, targets)
        self.assertEqual(receipt["states"]["auto"], "after-image")
        self.assertFalse(receipt["commit_authorized"])
        self.assertFalse(receipt["restore_authorized"])

    def test_cold_classification_foreign_content_and_inode_swap_refused(self):
        self.seed()
        rows, targets = self.planned_rows()
        target = targets["user"]
        old = target.read_bytes()
        target.unlink()
        target.write_bytes(old)
        target.chmod(0o600)
        with self.assertRaisesRegex(EffectiveKnownRefused, "cold_found_unknown_image"):
            self.cold_image(rows, targets)
        target.unlink()
        target.write_text("foreign.net\n")
        target.chmod(0o600)
        with self.assertRaisesRegex(EffectiveKnownRefused, "cold_found_unknown_image"):
            self.cold_image(rows, targets)

    def test_native_prepared_intent_refuses_without_original_config_and_fd9(self):
        with self.assertRaisesRegex(EffectiveKnownRefused,
                                    "native_original_config_fd9_required"):
            prepare_native_found_intent("a" * 32, 4, "b" * 64)
        with self.assertRaisesRegex(EffectiveKnownRefused,
                                    "native_original_config_fd9_required"):
            prepare_native_found_intent("not-an-op-id", 4, "b" * 64)
        with self.assertRaisesRegex(EffectiveKnownRefused,
                                    "native_original_config_fd9_required"):
            prepare_native_found_intent("a" * 32, 1, "b" * 64)

    def test_found_pristine_recovery_has_no_portable_or_cli_entry(self):
        # The first true cold terminal writer must remain import-only until
        # the original PHP Config model/FD9/P2 handoff has native acceptance.
        from auto_detect_effective_known import recover_native_found_prepared_pristine
        with self.assertRaisesRegex(
                EffectiveKnownRefused, "native_found_pristine_original_owner_required"):
            recover_native_found_prepared_pristine(
                "a" * 32, config_fd=4, config_digest="b" * 64)
        with self.assertRaisesRegex(
                EffectiveKnownRefused, "native_found_pristine_original_owner_required"):
            recover_native_found_prepared_pristine(
                "foreign", config_fd=4, config_digest="b" * 64)
        source = (BACKEND / "auto_detect_effective_known.py").read_text()
        self.assertIn("store.finish_found_prepared_pristine(", source)
        self.assertIn("with exclusive_destination_lock(AUTO_LOCK, 0):", source)
        self.assertNotIn("'recover-prepared-found'", source)

    def test_original_prepared_pristine_closure_requires_both_physical_witnesses(self):
        # Exercise the real original durable journal but isolate native BSD
        # descriptors/old IPFW observation with bounded fakes. No production
        # CLI/Config saver is reached and P2 cannot be dropped before fsync.
        import auto_detect_effective_known as effective
        import auto_detect_original_lock_handoff as inherited
        import shared_apply_operation as opmodule
        import shared_apply_seal as sealing
        import voice_ipfw_adapter as ipfw
        import voice_live_inspect as voice

        self.seed()
        rows, targets = self.planned_rows()
        journal = opmodule.SharedApplyOperation(self.base / "journal")
        previous = {"id": "a" * 32, "page": "strategies",
                    "base": "b" * 64, "candidate": "c" * 64,
                    "changed_fields": []}
        for phase in ("prepared", "activating", "activated",
                      "config-saved", "committed"):
            journal.advance(phase, previous)
        current = {"id": "d" * 32, "page": "strategies",
                   "base": previous["candidate"], "candidate": "e" * 64,
                   "changed_fields": ["hostlist.youtubedomains"]}
        raw = json.dumps({
            "page": "strategies", "result": "prepared",
            "dependencies": current["base"],
            "changed_fields": current["changed_fields"],
            "found_intent": {"config_revision": current["base"],
                             "commit_authorized": False},
            "found_batch": rows,
        }).encode()
        journal.prepare_found(current, raw, lambda _: True)
        plan_path = self.base / "work" / current["id"] / "plan.json"
        plan_path.parent.mkdir(parents=True)
        plan_path.write_bytes(raw)
        original_journal = journal.read()
        seal = {"sha256": {"plan.json": hashlib.sha256(raw).hexdigest()}}
        held = [False]
        witness_calls = [0]
        refuse_second = [True]

        @contextmanager
        def original_p2(*_args, **_kwargs):
            self.assertFalse(held[0], "second P2 lock owner")
            held[0] = True
            try:
                yield
            finally:
                held[0] = False

        def physical_preimages(*_args, **_kwargs):
            self.assertTrue(held[0], "physical source read outside P2")
            witness_calls[0] += 1
            if refuse_second[0] and witness_calls[0] == 2:
                raise EffectiveKnownRefused("minute-worker-image-drift")

        def old_runtime(pending):
            self.assertTrue(held[0], "runtime IPFW read outside P2")
            self.assertEqual(pending, original_journal)
            return {"state": "ready", "id": previous["id"]}

        with patch.object(effective.sys, "platform", "freebsd-test"), \
             patch.object(effective.os, "geteuid", return_value=0), \
             patch.object(effective, "OWNED_ROOT", self.root), \
             patch.object(effective, "AUTO_HOSTLIST", targets["auto"]), \
             patch.object(effective, "AUTO_LOCK", self.lock), \
             patch.object(effective, "_target", return_value=(raw, None)), \
             patch.object(effective, "_verify_planned_preimages_locked",
                          side_effect=physical_preimages), \
             patch.object(effective, "exclusive_destination_lock",
                          side_effect=original_p2), \
             patch.object(opmodule, "SharedApplyOperation", return_value=journal), \
             patch.object(sealing, "WORK", plan_path.parent.parent), \
             patch.object(sealing, "_stat"), \
             patch.object(sealing, "verify_seal", return_value=seal), \
             patch.object(ipfw, "require_lifecycle_lock"), \
             patch.object(inherited, "assert_inherited_config_fd"), \
             patch.object(voice, "examine_pending_found_previous",
                          side_effect=old_runtime):
            from auto_detect_effective_known import recover_native_found_prepared_pristine

            with self.assertRaisesRegex(EffectiveKnownRefused,
                                        "minute-worker-image-drift"):
                recover_native_found_prepared_pristine(
                    current["id"], config_fd=4, config_digest=current["base"])
            self.assertFalse(held[0])
            self.assertEqual(journal.read(), original_journal)
            self.assertEqual(witness_calls[0], 2)

            # A foreign Config BASE or missing predecessor never reaches
            # the P2 file writer or the terminal transition.
            with self.assertRaisesRegex(
                    EffectiveKnownRefused, "phase_or_config_drift"):
                recover_native_found_prepared_pristine(
                    current["id"], config_fd=4, config_digest="f" * 64)
            self.assertEqual(journal.read(), original_journal)

            refuse_second[0] = False
            witness_calls[0] = 0
            receipt = recover_native_found_prepared_pristine(
                current["id"], config_fd=4, config_digest=current["base"])
            self.assertEqual(witness_calls[0], 2)
            self.assertEqual(receipt["phase"], "restored")
            self.assertEqual(receipt["previous_id"], previous["id"])
            self.assertEqual(receipt["runtime_state"], "ready")
            self.assertFalse(receipt["service_restarted"])
            self.assertFalse(held[0])
            self.assertEqual(journal.read()["previous"], previous)
            self.assertNotIn("found", journal.read())
            with self.assertRaisesRegex(
                    EffectiveKnownRefused, "phase_or_config_drift"):
                recover_native_found_prepared_pristine(
                    current["id"], config_fd=4, config_digest=current["base"])

    def test_private_native_pristine_dispatch_refuses_without_original_fd4_fd9(self):
        from auto_detect_effective_known import main as original_dispatch
        # There is no second browser/configd recovery owner; without native
        # FreeBSD fd4 and original FD9 this private route cannot terminalize.
        self.assertEqual(original_dispatch([
            "recover-prepared-locked", "a" * 32, "b" * 64]), 69)
        php = (BACKEND.parent / "shared_apply_config.php").read_text()
        self.assertIn("'found-recover-prepared'", php)
        self.assertIn("'recover-prepared-locked', $base", php)
        self.assertIn("$config->lock();", php)
        self.assertIn("self::recoverFoundPreparedNative(", php)
        self.assertNotIn("$config->save(", php[
            php.index("private static function recoverFoundPreparedNative("):
            php.index("public static function saved(")
        ])

    def test_native_cold_classification_requires_original_fd9(self):
        with self.assertRaisesRegex(EffectiveKnownRefused, "native_original_fd9_required"):
            classify_native_planned("a" * 32)

    def test_planned_native_entry_refuses_without_original_fd9(self):
        with self.assertRaisesRegex(EffectiveKnownRefused, "native_original_fd9_required"):
            compose_native_planned(self.youtube, self.user, "a" * 32)

    def test_original_builder_is_wired_before_staging_publication(self):
        shell = (BACKEND / 'targets.sh').read_text()
        self.assertIn('auto_detect_effective_known.py" compose', shell)
        self.assertLess(shell.index('auto_detect_effective_known.py" compose'),
                        shell.index('mv -f "' + chr(36) + '{input_root}/hostlist-youtube.out"'))
        orchestrator = (BACKEND / 'orchestrator.sh').read_text()
        service = (BACKEND.parent / 'zapret_service.sh').read_text()
        self.assertIn('compose-planned', shell)
        self.assertIn('"${_orchestrator_build_found_id}"', orchestrator)
        self.assertIn('has("found_intent") and has("found_batch")', service)
        self.assertIn('preflight-rejected=found-transaction-pending', service)
        self.assertIn('verify-planned "$_shared_apply_id"', service)
        self.assertIn('preflight-rejected=found-source-drift', service)
        self.assertLess(service.index('verify-planned "$_shared_apply_id"'),
                        service.index('if ! apply_runtime_probe "$_shared_apply_root/release"'))
        self.assertIn('if [ "$_shared_found_scope" != ordinary ]; then', service)


if __name__ == '__main__':
    unittest.main()
