#!/usr/bin/env python3
"""Write-once legacy PoC marker/IPFW/Config/runtime evidence, no activation."""
from __future__ import annotations

import fcntl
import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))

from voice_native_legacy_previous_seal import (
    capture_legacy_previous, inspect_legacy_previous, LegacyPreviousSealError,
)
from voice_cutover_guard import check_pending


def load_fixture():
    spec = importlib.util.spec_from_file_location(
        "legacy_live_seal_fixture", ROOT/"scripts/test-voice-native-live-preflight.py"
    )
    item = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(item)
    return item


class DurableOldPoCTests(unittest.TestCase):
    def setUp(self):
        self.case = load_fixture().OldPoCFullBaselineTests()
        self.case.setUp()
        self.addCleanup(self.case.live.doCleanups)
        self.root = self.case.live.whole
        self.root.mkdir(mode=0o700)

    def capture(self, *, lock=True):
        live = self.case.live
        fd = os.open(live.config, os.O_RDWR)
        try:
            if lock:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return capture_legacy_previous(
                root=self.root, config_path=live.config,
                active_runtime=live.runtime, legacy_marker=self.case.marker,
                ledger_root=live.ledger, probe=live.probe,
                kernel_reader=live.kernel, ipfw_adapter=live.adapter,
                config_fd=fd, config_owner=(os.geteuid(), os.getegid()),
                require_lifecycle_owner=lambda:live.lock_calls.append("FD9"),
            )
        finally:
            os.close(fd)

    def test_writes_restorable_old_files_marker_and_exact_ipfw_with_no_kernel_mutation(self):
        before = self.case.live.config.read_bytes()
        marker = self.case.marker.read_bytes()
        report = self.capture()
        self.assertEqual("legacy-poc-previous-files-and-kernel-witness-sealed",
                         report["state"])
        self.assertFalse(report["rollback_implemented"])
        self.assertFalse(report["process_security_sealed"])
        self.assertFalse(report["safe_to_mutate"])
        self.assertFalse(report["public_voice_apply"])
        self.assertEqual(marker, (self.root/"legacy-previous/marker.bin").read_bytes())
        self.assertEqual(before, (self.root/"legacy-previous/previous/config/config.xml").read_bytes())
        self.assertEqual(before, self.case.live.config.read_bytes())
        self.assertTrue(self.case.marker.exists())
        self.assertEqual("orphan-native-voice-evidence",
                         check_pending(self.root,self.case.live.ledger)["reason"])
        self.assertTrue(all(x[1] in ("-q","table") for x in self.case.live.fake_ipfw.calls))
        self.assertEqual(report, inspect_legacy_previous(self.root))

    def test_existing_archive_must_not_be_replaced(self):
        first = self.capture()
        with self.assertRaises((OSError, ValueError, RuntimeError)):
            self.capture()
        self.assertEqual(first, inspect_legacy_previous(self.root))

    def test_corrupt_marker_or_manifest_refuses_inspection(self):
        self.capture()
        marker=self.root/"legacy-previous/marker.bin"
        marker.write_bytes(b"forged")
        with self.assertRaises((OSError, ValueError, RuntimeError)):
            inspect_legacy_previous(self.root)
        marker.write_bytes(b"")
        manifest=self.root/"legacy-previous/legacy.json"
        manifest.write_bytes(manifest.read_bytes().replace(
            b"previous-evidence-only-not-owned",b"native-owned-and-ready",
        ))
        with self.assertRaises((OSError, ValueError, RuntimeError)):
            inspect_legacy_previous(self.root)

    def test_marker_absent_or_unlocked_rejects_before_any_staging(self):
        with self.assertRaises((OSError, ValueError, RuntimeError)):
            self.capture(lock=False)
        self.assertEqual([],list(self.root.iterdir()))
        self.case.marker.unlink()
        with self.assertRaises((OSError, ValueError, RuntimeError)):
            self.capture()
        self.assertEqual([],list(self.root.iterdir()))

    def test_old_kernel_mismatch_rejects_before_mutation(self):
        self.case.live.fake_ipfw.rules += "19009 allow ip from any to any\n"
        with self.assertRaises((OSError, ValueError, RuntimeError)):
            self.capture()
        self.assertEqual([],list(self.root.iterdir()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
