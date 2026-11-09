#!/usr/bin/env python3
"""Bounded, offline tests of extra-resource catalog preflight (no appliance writes)."""
from __future__ import annotations

import errno
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
import subprocess

ROOT = Path(__file__).resolve().parents[1]
INSTALLED_MODE = os.environ.get("ZAPRET2_STAGE5_INSTALLED_LAB_RESOURCES") == "1"
if INSTALLED_MODE and os.environ.get("GITHUB_ACTIONS") != "true":
    raise SystemExit("REFUSED: installed Extra Resources preflight requires disposable GitHub CI")
PATH = (Path("/usr/local/opnsense/scripts/OPNsense/Zapret/extra_resources_preflight.py")
        if INSTALLED_MODE else
        ROOT / "src/opnsense/scripts/OPNsense/Zapret/extra_resources_preflight.py")
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


class _ReadResponse:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        return self.value[:size]


class TestBoundedReadOnlyFetch(unittest.TestCase):
    def test_first_healthy_get_has_exactly_one_network_call(self):
        with patch.object(extra, "urlopen", return_value=_ReadResponse(
                json.dumps({"object": {"sha": REV}}).encode())) as open_mock, \
             patch.object(extra.time, "sleep") as sleep_mock:
            self.assertEqual(extra.obtain_revision(), REV)
            self.assertEqual(open_mock.call_count, 1)
            sleep_mock.assert_not_called()

    def test_transient_eacces_recovers_before_any_install(self):
        denied = URLError(PermissionError(errno.EACCES, "Permission denied"))
        payload = json.dumps({"object": {"sha": REV}}).encode()
        with patch.object(extra, "urlopen", side_effect=[
                denied, _ReadResponse(payload)]) as open_mock, \
             patch.object(extra.time, "sleep") as sleep_mock:
            self.assertEqual(extra.obtain_revision(), REV)
            self.assertEqual(open_mock.call_count, 2)
            sleep_mock.assert_called_once_with(1)

        archive_bytes = archive_for()
        with patch.object(extra, "urlopen", side_effect=[
                denied, denied, _ReadResponse(archive_bytes)]) as open_mock, \
             patch.object(extra.time, "sleep") as sleep_mock:
            self.assertEqual(extra.obtain_archive(REV), archive_bytes)
            self.assertEqual(open_mock.call_count, 3)
            self.assertEqual([c.args[0] for c in sleep_mock.call_args_list],
                             [1, 3])

    def test_permanent_eacces_still_fails_closed_after_three_read_only_gets(self):
        denied = URLError(PermissionError(errno.EACCES, "Permission denied"))
        with patch.object(extra, "urlopen", side_effect=[denied]*3) as opens, \
             patch.object(extra.time, "sleep") as sleeps:
            with self.assertRaises(URLError):
                extra.obtain_revision()
            self.assertEqual(opens.call_count, 3)
            self.assertEqual(sleeps.call_count, 2)

    def test_api_rate_limit_falls_back_to_same_github_git_main_once(self):
        # The primary API is still tried first; only an actual rate-limit
        # response enables the read-only Git transport for the same ref.
        limited = HTTPError(extra.SOURCE_REF_URL, 403, "Forbidden",
                            {"X-RateLimit-Remaining": "0"},
                            io.BytesIO(b'{"message":"API rate limit exceeded"}'))
        resolved = subprocess.CompletedProcess([], 0,
                                               REV + "\trefs/heads/main\n", "")
        with patch.object(extra, "urlopen", side_effect=limited) as api, \
             patch.object(extra.subprocess, "run", return_value=resolved) as git, \
             patch.object(extra.time, "sleep") as sleeps:
            self.assertEqual(extra.obtain_revision(), REV)
            self.assertEqual(api.call_count, 1)
            self.assertEqual(git.call_count, 1)
            self.assertEqual(git.call_args.args[0][-2:], [
                "https://github.com/" + extra.SOURCE + ".git", "refs/heads/main"
            ])
            self.assertEqual(git.call_args.kwargs["env"]["GIT_TERMINAL_PROMPT"], "0")
            self.assertEqual(git.call_args.kwargs["timeout"], 30)
            sleeps.assert_not_called()

    def test_api_403_other_than_rate_limit_must_not_fallback(self):
        forbidden = HTTPError(extra.SOURCE_REF_URL, 403, "Forbidden", {},
                              io.BytesIO(b'{"message":"permission denied"}'))
        with patch.object(extra, "urlopen", side_effect=forbidden), \
             patch.object(extra.subprocess, "run") as git:
            with self.assertRaises(HTTPError):
                extra.obtain_revision()
            git.assert_not_called()

    def test_git_rate_limit_fallback_rejects_ambiguous_or_foreign_ref(self):
        for output in ("", REV + "\tHEAD\n",
                       REV + "\trefs/heads/main\n" + REV + "\trefs/tags/x\n",
                       "not-a-commit\trefs/heads/main\n"):
            with self.subTest(output=output):
                limited = HTTPError(extra.SOURCE_REF_URL, 403, "Forbidden",
                                    {"X-RateLimit-Remaining": "0"}, io.BytesIO(b""))
                result = subprocess.CompletedProcess([], 0, output, "")
                with patch.object(extra, "urlopen", side_effect=limited), \
                     patch.object(extra.subprocess, "run", return_value=result):
                    with self.assertRaisesRegex(extra.PreflightError, "no single valid main"):
                        extra.obtain_revision()

    def test_api_rate_limit_message_without_header_uses_same_git_ref(self):
        limited = HTTPError(extra.SOURCE_REF_URL, 403, "Forbidden", {},
                            io.BytesIO(b'{"message":"API rate limit exceeded"}'))
        resolved = subprocess.CompletedProcess([], 0,
                                               REV + "\trefs/heads/main\n", "")
        with patch.object(extra, "urlopen", side_effect=limited), \
             patch.object(extra.subprocess, "run", return_value=resolved):
            self.assertEqual(extra.obtain_revision(), REV)

    def test_rate_limited_api_with_failed_git_transport_remains_refused(self):
        limited = HTTPError(extra.SOURCE_REF_URL, 403, "Forbidden",
                            {"X-RateLimit-Remaining": "0"}, None)
        result = subprocess.CompletedProcess([], 128, "", "untrusted git error")
        with patch.object(extra, "urlopen", side_effect=limited), \
             patch.object(extra.subprocess, "run", return_value=result):
            with self.assertRaisesRegex(extra.PreflightError, "no single valid main"):
                extra.obtain_revision()

    def test_git_rate_limit_fallback_timeout_is_fail_closed(self):
        limited = HTTPError(extra.SOURCE_REF_URL, 429, "Too Many Requests", {},
                            io.BytesIO(b""))
        with patch.object(extra, "urlopen", side_effect=limited), \
             patch.object(extra.subprocess, "run",
                          side_effect=subprocess.TimeoutExpired(["git"], 30)):
            with self.assertRaisesRegex(extra.PreflightError,
                                        "GitHub main revision unavailable"):
                extra.obtain_revision()

    def test_http_and_unrelated_socket_failures_are_never_retried(self):
        for reason in (URLError(PermissionError(errno.EPERM, "not allowed")),
                       URLError(ConnectionRefusedError(errno.ECONNREFUSED,
                                                       "not connected")),
                       URLError("HTTP 403 rate-limited")):
            with self.subTest(reason=repr(reason)), \
                 patch.object(extra, "urlopen", side_effect=reason) as opens, \
                 patch.object(extra.time, "sleep") as sleeps:
                with self.assertRaises(URLError):
                    extra.obtain_revision()
                self.assertEqual(opens.call_count, 1)
                sleeps.assert_not_called()


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
