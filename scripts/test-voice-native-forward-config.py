#!/usr/bin/env python3
"""Legacy forward Config redo: read-only proof, never candidate Config writes."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

import voice_native_forward_config as forward
from voice_cutover_journal import RUNTIME_BOUND_SCHEMA


def digest(data):
    return hashlib.sha256(data).hexdigest()


class HistoricalForwardConfigRedoTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.root.chmod(0o700)
        self.candidate = b"<opnsense><voice enabled='1'/></opnsense>"
        self.previous = b"<opnsense><voice enabled='0'/></opnsense>"
        self.source = self.root / "staged.xml"
        self.source.write_bytes(self.candidate)
        self.live = self.root / "config.xml"
        self.live.write_bytes(self.candidate[:15])
        candidate_info = self.source.stat()
        live_info = self.live.stat()
        self.record = {
            "schema": RUNTIME_BOUND_SCHEMA,
            "phase": "mutating",
            "check": digest(b"sealed whole operation"),
            "previous": {"config": digest(self.previous)},
            "candidate": {"saved_xml_sha256": digest(self.candidate)},
        }
        fields = {
            "schema": 1,
            "whole_check": self.record["check"],
            "config_dev": live_info.st_dev,
            "config_inode": live_info.st_ino,
            "config_uid": live_info.st_uid,
            "config_gid": live_info.st_gid,
            "previous_sha256": digest(self.previous),
            "candidate_sha256": digest(self.candidate),
            "candidate_bytes": len(self.candidate),
            "previous_mode": 0o600,
            "source_path": str(self.source),
            "source_dev": candidate_info.st_dev,
            "source_inode": candidate_info.st_ino,
            "source_uid": candidate_info.st_uid,
            "source_gid": candidate_info.st_gid,
        }
        self.marker = {**fields, "check": forward._digest(fields)}
        self.path = self.root / forward.NAME

    def write_marker(self, marker=None):
        self.path.write_text(json.dumps(self.marker if marker is None else marker))
        self.path.chmod(0o600)

    def proof(self, marker=None, record=None):
        fd = os.open(self.live, os.O_RDONLY)
        try:
            return forward.is_bound_forward_candidate_prefix(
                self.marker if marker is None else marker,
                self.record if record is None else record,
                fd, os.fstat(fd),
            )
        finally:
            os.close(fd)

    def test_no_legacy_forward_config_writer_is_exported(self):
        self.assertFalse(hasattr(forward, "persist_forward_candidate_config"))
        self.assertFalse(hasattr(forward, "_arm"))
        self.assertIsNone(forward.read_forward_config_redo(self.root))

    def test_existing_sealed_marker_and_prefix_remain_readable(self):
        self.write_marker()
        self.assertEqual(self.marker, forward.read_forward_config_redo(self.root))
        before = self.live.read_bytes()
        self.assertTrue(self.proof())
        self.assertEqual(before, self.live.read_bytes())

    def test_missing_or_foreign_prefix_cannot_authorize_rollback(self):
        self.assertFalse(forward.is_bound_forward_candidate_prefix(
            None, self.record, -1, None))
        self.live.write_bytes(b"<foreign>")
        self.assertFalse(self.proof())

    def test_wrong_operation_phase_or_inode_rejected(self):
        record = dict(self.record, phase="prepared")
        with self.assertRaises(forward.ForwardConfigError):
            self.proof(record=record)
        foreign = dict(self.marker, config_inode=self.marker["config_inode"] + 1)
        foreign["check"] = forward._digest(
            {k: v for k, v in foreign.items() if k != "check"}
        )
        with self.assertRaises(forward.ForwardConfigError):
            self.proof(marker=foreign)

    def test_source_replacement_or_tampering_rejected(self):
        replacement = self.root / "replacement.xml"
        replacement.write_bytes(self.candidate)
        replacement.replace(self.source)
        with self.assertRaises(forward.ForwardConfigError):
            self.proof()
        self.source.write_bytes(b"changed")
        with self.assertRaises(forward.ForwardConfigError):
            self.proof()

    def test_corrupt_or_public_marker_rejected(self):
        self.write_marker()
        altered = dict(self.marker, candidate_bytes=0)
        self.write_marker(altered)
        with self.assertRaises(forward.ForwardConfigError):
            forward.read_forward_config_redo(self.root)
        self.write_marker()
        self.path.chmod(0o644)
        with self.assertRaises(forward.ForwardConfigError):
            forward.read_forward_config_redo(self.root)


if __name__ == "__main__":
    unittest.main()
