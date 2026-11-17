#!/usr/bin/env python3
"""TZ6v2 original P2 destination owner: reversible 3-source file write tests.

No new CLI, no Config writer, no service, no FD9 fake. These unit tests call
only the private already-locked helper with disposable root-owned files. The
public original-FD9 entry refuses on non-native hosts.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest

BACKEND = (Path(__file__).resolve().parents[1] / "src/opnsense/scripts"
           / "OPNsense/Zapret/backend")
sys.path.insert(0, str(BACKEND))

from auto_detect_destination_commit import (
    DestinationRefused, SHARED_FOUND_NAMES, _locked_shared_found_replace,
    _replace, shared_apply_found_files_original_fd9,
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

    @unittest.skipIf(sys.platform.startswith("freebsd") and os.geteuid() == 0,
                     "A native root requires a real FD9 parent, not a fixture")
    def test_public_original_fd9_entry_refuses_non_native(self):
        with self.assertRaisesRegex(DestinationRefused,
                                    "original_native_fd9_required"):
            shared_apply_found_files_original_fd9("a" * 32, -1)


if __name__ == "__main__":
    unittest.main()
