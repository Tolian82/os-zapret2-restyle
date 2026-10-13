#!/usr/bin/env python3
"""Bundle-level tests: full release must match the pinned Config and plan."""
import tempfile
from pathlib import Path
import sys
import unittest

BACKEND = Path(__file__).resolve().parents[1] / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))
from shared_apply_seal import (SharedBundleError, create_seal, verify_seal,
                               fingerprint)


class TestBundleSeal(unittest.TestCase):
    def fixture(self, root):
        base = root / "shared-work"
        base.mkdir(mode=0o700)
        job = base / ("b" * 32)
        job.mkdir(mode=0o700)
        for name, data in (("candidate.xml", "<opnsense/>"),
                           ("plan.json", '{"candidate":"test"}')):
            path = job / name
            path.write_text(data)
            path.chmod(0o600)
        release = job / "release"
        release.mkdir(mode=0o700)
        managed = release / "managed"
        managed.mkdir(mode=0o700)
        (managed / "ipset-telegram.txt").write_text("91.108.0.0/16\n")
        (managed / "ipset-telegram.txt").chmod(0o600)
        (release / "voice-plan.json").write_text('{"telegram":1}\n')
        (release / "voice-plan.json").chmod(0o600)
        return job

    def test_sealed_shared_candidate_round_trip_and_no_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            job = self.fixture(Path(tmp))
            initial = fingerprint(job)
            created = create_seal(job)
            self.assertEqual(initial, created)
            self.assertEqual(initial, verify_seal(job))
            self.assertEqual(0o600, (job / "bundle-seal.json").stat().st_mode & 0o777)
            with self.assertRaisesRegex(SharedBundleError, "already sealed"):
                create_seal(job)

    def test_candidates_and_release_are_all_bound(self):
        for name in ("candidate.xml", "plan.json", "release/voice-plan.json",
                     "release/managed/ipset-telegram.txt"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                job = self.fixture(Path(tmp))
                create_seal(job)
                (job / name).write_text("changed contents")
                with self.assertRaisesRegex(SharedBundleError, "changed after seal"):
                    verify_seal(job)

    def test_symlinks_and_missing_entries_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            job = self.fixture(Path(tmp))
            create_seal(job)
            f = job / "release/voice-plan.json"
            f.unlink()
            f.symlink_to(job / "candidate.xml")
            with self.assertRaises(SharedBundleError):
                verify_seal(job)
        with tempfile.TemporaryDirectory() as tmp:
            job = self.fixture(Path(tmp))
            (job / "candidate.xml").unlink()
            (job / "candidate.xml").symlink_to(job / "plan.json")
            with self.assertRaises(SharedBundleError):
                create_seal(job)
        with tempfile.TemporaryDirectory() as tmp:
            job = self.fixture(Path(tmp))
            (job / ".bundle-seal.pending").write_text("partial write")
            with self.assertRaisesRegex(SharedBundleError, "interrupted"):
                create_seal(job)

    def test_renamed_deleted_and_added_release_files(self):
        for action in ("rename", "delete", "add"):
            with self.subTest(action=action), tempfile.TemporaryDirectory() as tmp:
                job = self.fixture(Path(tmp))
                create_seal(job)
                file = job / "release/voice-plan.json"
                if action == "rename":
                    file.rename(job / "release/other.json")
                elif action == "delete":
                    file.unlink()
                else:
                    (job / "release/foreign.txt").write_text("extra")
                with self.assertRaisesRegex(SharedBundleError, "changed after seal"):
                    verify_seal(job)

    def test_invalid_id_and_world_writable_tree_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            job = self.fixture(Path(tmp))
            (job / "release").chmod(0o777)
            with self.assertRaisesRegex(SharedBundleError, "untrusted"):
                create_seal(job)
            (job / "release").chmod(0o700)
            fake = job.parent / "non-canonical"
            fake.mkdir()
            with self.assertRaisesRegex(SharedBundleError, "invalid shared"):
                fingerprint(fake)


if __name__ == "__main__":
    unittest.main(verbosity=2)
