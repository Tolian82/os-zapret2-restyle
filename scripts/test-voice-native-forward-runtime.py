#!/usr/bin/env python3
"""Read-only historical forward-runtime redo evidence and fail-closed handling.

A private runtime installer is no longer part of Voice Apply. The record it
could have left on a previous appliance must remain readable by verified
previous-file recovery, without silently recreating a mutation route.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"))

import voice_native_forward_runtime as redo
from voice_cutover_file_rollback import read_forward_redo


class HistoricalForwardRuntimeRedoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.marker = self.directory / redo.MARKER
        self.fields = {
            "schema": 1,
            "whole_check": "a" * 64,
            "config_dev": 11,
            "config_inode": 12,
            "parent_dev": 21,
            "parent_inode": 22,
            "active_name": "runtime-v2",
            "candidate_sha256": "b" * 64,
            "previous_sha256": "c" * 64,
            "ready_name": ".voice-forward-ready-" + "a" * 20,
            "retained_name": ".voice-forward-previous-" + "a" * 20,
        }

    def seal(self, fields=None):
        fields = dict(self.fields if fields is None else fields)
        payload = json.dumps(fields, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True).encode("ascii")
        return {**fields, "check": hashlib.sha256(payload).hexdigest()}

    def write(self, data):
        self.marker.write_text(json.dumps(
            data, sort_keys=True, separators=(",", ":"),
        ) + "\n", encoding="ascii")
        self.marker.chmod(0o600)

    def test_exact_historical_schema_accepted_by_live_recovery_reader(self):
        expected = self.seal()
        self.write(expected)
        self.assertEqual(expected, redo._read_redo(self.directory))
        self.assertIs(read_forward_redo, redo._read_redo)
        self.assertEqual(expected, read_forward_redo(self.directory))
        # No filesystem mutation is permitted by a read-only inspector.
        self.assertEqual(expected, json.loads(self.marker.read_text()))

    def test_absent_historical_marker_is_not_a_new_install_intent(self):
        self.assertIsNone(redo._read_redo(self.directory))
        self.assertFalse(self.marker.exists())

    def test_retired_writer_api_must_not_be_reintroduced(self):
        for name in ("install_forward_runtime", "_arm", "_copy_candidate",
                     "_marked"):
            with self.subTest(name=name):
                self.assertFalse(hasattr(redo, name))

    def test_checksum_or_saved_field_tampering_is_rejected(self):
        payload = self.seal()
        payload["candidate_sha256"] = "d" * 64
        self.write(payload)
        with self.assertRaises(redo.ForwardRuntimeError):
            redo._read_redo(self.directory)
        payload = self.seal()
        payload["check"] = "0" * 64
        self.write(payload)
        with self.assertRaises(redo.ForwardRuntimeError):
            redo._read_redo(self.directory)

    def test_foreign_name_and_path_escape_rejected_even_if_resealed(self):
        for key, value in (
            ("active_name", "../runtime"),
            ("active_name", "."),
            ("active_name", ""),
            ("ready_name", ".voice-forward-ready-" + "f" * 20),
            ("retained_name", ".voice-forward-previous-" + "f" * 20),
        ):
            with self.subTest(key=key, value=value):
                self.write(self.seal({**self.fields, key: value}))
                with self.assertRaises(redo.ForwardRuntimeError):
                    redo._read_redo(self.directory)

    def test_untrusted_schema_types_and_unknown_fields_rejected(self):
        for payload in (
            {**self.fields, "schema": True},
            {**self.fields, "config_inode": -1},
            {**self.fields, "candidate_sha256": "B" * 64},
            {**self.fields, "extra": "foreign"},
            {key: value for key, value in self.fields.items()
             if key != "whole_check"},
        ):
            with self.subTest(payload=payload):
                self.write(self.seal(payload))
                with self.assertRaises(redo.ForwardRuntimeError):
                    redo._read_redo(self.directory)

    def test_malformed_and_oversized_marker_rejected(self):
        self.marker.write_text("{", encoding="ascii")
        self.marker.chmod(0o600)
        with self.assertRaises(redo.ForwardRuntimeError):
            redo._read_redo(self.directory)
        self.marker.write_bytes(b"x" * (redo.LIMIT + 1))
        self.marker.chmod(0o600)
        with self.assertRaises(redo.ForwardRuntimeError):
            redo._read_redo(self.directory)

    def test_group_readable_or_hardlinked_marker_refused(self):
        self.write(self.seal())
        self.marker.chmod(0o640)
        with self.assertRaises(redo.ForwardRuntimeError):
            redo._read_redo(self.directory)
        self.marker.chmod(0o600)
        sibling = self.directory / "sibling"
        os.link(self.marker, sibling)
        with self.assertRaises(redo.ForwardRuntimeError):
            redo._read_redo(self.directory)

    def test_directory_and_symlink_markers_cannot_be_adopted(self):
        self.marker.mkdir()
        with self.assertRaises((OSError, redo.ForwardRuntimeError)):
            redo._read_redo(self.directory)
        self.marker.rmdir()
        target = self.directory / "foreign.json"
        target.write_text(json.dumps(self.seal()), encoding="ascii")
        self.marker.symlink_to(target)
        with self.assertRaises((OSError, redo.ForwardRuntimeError)):
            redo._read_redo(self.directory)


if __name__ == "__main__":
    unittest.main(verbosity=2)
