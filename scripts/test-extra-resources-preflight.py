#!/usr/bin/env python3
"""Bounded, offline tests of extra-resource catalog preflight (no appliance writes)."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "src/opnsense/scripts/OPNsense/Zapret/extra_resources_preflight.py"
spec = importlib.util.spec_from_file_location("extra_resources_preflight", PATH)
assert spec and spec.loader
extra = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extra)

REV = "a" * 40
LUA = b"function my_dynamic_action(ctx, desync)\n  return nil\nend\n"
BIN = b"\x16\x03\x03\x00\x08\x01\x00\x00\x04aaaa"
PAYLOADS = {"lua/dynamic-helper.lua": LUA, "files/fake/opaque-payload.bin": BIN}


def archive_for(payloads=None, *, corrupted=False, duplicate=False, escape=False):
    payloads = dict(PAYLOADS if payloads is None else payloads)
    records = [{"target": name, "size": len(data),
                "sha": extra.git_blob_sha(data)} for name, data in payloads.items()]
    if corrupted:
        records[0]["sha"] = "0" * 40
    if duplicate:
        records.append(dict(records[0]))
    metadata = {
        "schema": 1, "total": len(records),
        "counts": {"lua": sum(n.startswith("lua/") for n in payloads),
                   "bin": sum(n.startswith("files/fake/") for n in payloads)},
        "resources": records,
    }
    capabilities = {
        "schema": 1, "resources": [
            {"target": "lua/dynamic-helper.lua", "kind": "lua",
             "export": "my_dynamic_action", "role": "desync",
             "protocol": "tls13", "transport": "tcp"},
            {"target": "files/fake/opaque-payload.bin", "kind": "blob",
             "format": "tls-clienthello", "protocol": "tls13",
             "transport": "tcp"},
        ]
    }
    files = dict(payloads)
    files.update({"inventory/sources.json": json.dumps(metadata).encode(),
                  "inventory/capabilities.json": json.dumps(capabilities).encode()})
    if escape:
        files["../escape.lua"] = b"unsafe"
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w:gz") as stream:
        for name, data in files.items():
            member = tarfile.TarInfo(f"zapret2-extra-resources-{REV}/{name}")
            member.size = len(data)
            stream.addfile(member, io.BytesIO(data))
    return raw.getvalue()


class TestCatalogPreflight(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "zapret2"
        self.root.mkdir()
        (self.root / "lua").mkdir()
        (self.root / "files").mkdir()
        (self.root / "files/fake").mkdir()
        self.managed = Path(self.tmp.name) / "managed.json"

    def preflight(self, data=None):
        return extra.preflight(archive_for() if data is None else data,
                               REV, self.root, self.managed)

    def test_no_install_side_effects(self):
        outcome = self.preflight()
        self.assertEqual(outcome["status"], "preflight_only")
        self.assertEqual((outcome["lua"], outcome["bin"]), (1, 1))
        self.assertEqual(outcome["described_capabilities"], 2)
        self.assertEqual(outcome["new"], 2)
        self.assertFalse(outcome["installed"])
        self.assertFalse(outcome["restarted"])
        self.assertFalse((self.root / "lua/dynamic-helper.lua").exists())
        self.assertFalse(self.managed.exists())

    def test_existing_unmanaged_name_is_a_conflict_even_if_identical(self):
        (self.root / "lua/dynamic-helper.lua").write_bytes(LUA)
        with self.assertRaisesRegex(extra.PreflightError, "upstream/user"):
            self.preflight()

    def test_managed_files_can_be_reverified_and_updated(self):
        (self.root / "lua/dynamic-helper.lua").write_bytes(LUA)
        (self.root / "files/fake/opaque-payload.bin").write_bytes(b"old")
        self.managed.write_text(json.dumps({
            "schema": 1,
            "files": {"lua/dynamic-helper.lua": extra.sha256(LUA),
                      "files/fake/opaque-payload.bin": extra.sha256(b"old")},
        }))
        result = self.preflight()
        self.assertEqual((result["new"], result["updated"], result["unchanged"]), (0, 1, 1))

    def test_modification_of_owned_file_blocks_update(self):
        (self.root / "lua/dynamic-helper.lua").write_bytes(b"tampered")
        self.managed.write_text(json.dumps({
            "schema": 1, "files": {"lua/dynamic-helper.lua": extra.sha256(LUA)},
        }))
        with self.assertRaisesRegex(extra.PreflightError, "changed or missing"):
            self.preflight()

    def test_symlink_escape_is_refused(self):
        (self.root / "lua/dynamic-helper.lua").symlink_to(self.managed)
        with self.assertRaisesRegex(extra.PreflightError, "symlink"):
            self.preflight()

    def test_bad_checksum_is_refused(self):
        with self.assertRaisesRegex(extra.PreflightError, "checksum"):
            self.preflight(archive_for(corrupted=True))

    def test_duplicate_file_identity_is_refused(self):
        with self.assertRaisesRegex(extra.PreflightError, "duplicate"):
            self.preflight(archive_for(duplicate=True))

    def test_tar_path_escape_is_refused(self):
        with self.assertRaisesRegex(extra.PreflightError, "invalid path"):
            self.preflight(archive_for(escape=True))

    def test_unsupported_bin_path_and_missing_description(self):
        self.assertFalse(extra.resource_path("lua/../../bad.lua"))
        self.assertFalse(extra.resource_path("files/fake/x.sh"))
        self.assertTrue(extra.resource_path("files/fake/new-dynamic.bin"))
        self.assertTrue(extra.resource_path("lua/new-dynamic.lua"))

    def test_changed_catalog_requires_no_python_name_update(self):
        payloads = dict(PAYLOADS)
        payloads["files/fake/new-payload.bin"] = b"some-new-payload"
        result = self.preflight(archive_for(payloads))
        self.assertEqual(result["bin"], 2)
        self.assertEqual(result["new"], 3)
        del payloads["files/fake/new-payload.bin"]
        self.assertEqual(self.preflight(archive_for(payloads))["new"], 2)


if __name__ == "__main__":
    unittest.main()
