#!/usr/bin/env python3
"""Offline negative contracts for independent root pre-pkg read-only CLI."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "zapret2_pre_pkg_standalone", HERE / "native-prepkg-standalone.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def root_stat(entry):
    a = list(entry)
    a[4] = 0
    return os.stat_result(a)


def fake_root_lstat(path, *args, **kwargs):
    return root_stat(ORIGINAL_LSTAT(path, *args, **kwargs))


ORIGINAL_LSTAT = Path.lstat


class StandalonePrepkgContracts(unittest.TestCase):
    def setUp(self):
        self.version = "0.6.2_106"
        self.old_version = "0.6.2_1"
        self.sha = "a" * 64
        self.old_sha = "b" * 64

    def test_commands_other_than_readonly_reject_without_any_pkg(self):
        with patch.object(m, "inspect") as inspect:
            for argv in ([], ["upgrade"], ["reinstall"],
                         ["upgrade", "anything", "else"],
                         ["inspect-predecessor", "not", "enough"]):
                with self.subTest(argv=argv):
                    self.assertEqual(m.main(argv), 78)
            inspect.assert_not_called()
        source = (HERE / "native-prepkg-standalone.py").read_text()
        self.assertIn('"supported_mandatory_entrypoint": False', source)
        self.assertIn('"lh08_ac11_accepted": False', source)
        self.assertNotIn("pkg add", source)
        self.assertNotIn("pkg upgrade", source)
        self.assertNotIn("pkg delete", source)

    def test_archive_expected_name_digest_and_absolute_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            valid = Path(tmp) / ("os-zapret2-restyle-" + self.version + ".pkg")
            valid.write_bytes(b"native package bytes")
            m.identity(valid, self.version, self.sha)
            for v, sha in ((self.version, "x" * 64),
                           ("0.6.2_0", self.sha),
                           ("0.6.2_999", self.sha)):
                with self.subTest(v=v, sha=sha), self.assertRaises(m.Refusal):
                    m.identity(valid, v, sha)
            with self.assertRaises(m.Refusal):
                m.identity(Path(valid.name), self.version, self.sha)
            valid.unlink()
            valid.symlink_to(Path(tmp) / "missing")
            with self.assertRaises(m.Refusal):
                m.identity(valid, self.version, self.sha)

    def test_archive_digest_and_symlink_with_no_follow(self):
        real_fstat = os.fstat
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / ("os-zapret2-restyle-" + self.version + ".pkg")
            pkg.write_bytes(b"real archive bytes")
            exact = hashlib.sha256(pkg.read_bytes()).hexdigest()
            with patch.object(Path, "lstat", fake_root_lstat), \
                 patch.object(m.os, "fstat", side_effect=lambda fd:
                              root_stat(real_fstat(fd))):
                self.assertEqual(m.verified_archive(pkg, self.version, exact)[2],
                                 len(b"real archive bytes"))
                with self.assertRaisesRegex(m.Refusal, "ARCHIVE_SHA256_MISMATCH"):
                    m.verified_archive(pkg, self.version, self.sha)
            pkg.unlink()
            target = Path(tmp) / "real"
            target.write_bytes(b"real archive bytes")
            pkg.symlink_to(target)
            with self.assertRaisesRegex(m.Refusal, "ARCHIVE_EXPECTATION_UNQUALIFIED"):
                m.verified_archive(pkg, self.version, exact)

    def test_find_modules_exact_native_paths_and_aliases(self):
        expected = [m.ARCHIVE_PREFIX + name for name in m.MODULES]
        for listing in (expected, ["./" + x.lstrip("/") for x in expected]):
            with patch.object(m, "read_tar", return_value=("\n".join(listing) + "\n").encode()):
                self.assertEqual(set(m.find_modules(Path("/tmp/pkg"))), set(m.MODULES))
        for bad in (expected + [expected[0]],
                    ["//" + expected[0].lstrip("/"), *expected[1:]],
                    ["/../" + expected[0].lstrip("/"), *expected[1:]],
                    expected[1:]):
            with self.subTest(bad=bad), \
                 patch.object(m, "read_tar", return_value=("\n".join(bad)+"\n").encode()), \
                 self.assertRaisesRegex(m.Refusal, "ARCHIVE_MODULE_ABSENT_OR_DUPLICATED"):
                m.find_modules(Path("/tmp/pkg"))

    def test_source_manifest_refusal_and_mode_staging(self):
        fake = {name: b"#!/usr/bin/env python3\n# byte equal\n" for name in m.MODULES}
        manifest = {"name": m.NAME, "version": self.version,
                    "abi": "FreeBSD:15:amd64", "arch": "freebsd:15:x86:64",
                    "files": {m.ARCHIVE_PREFIX + name: "1$hash" for name in m.MODULES}}
        def query(_pkg, _operation, member=None, limit=None):
            if member == "+MANIFEST":
                return json.dumps(manifest).encode()
            return fake[Path(member).name]
        members = {name: m.ARCHIVE_PREFIX + name for name in m.MODULES}
        with patch.object(m, "find_modules", return_value=members), \
             patch.object(m, "read_tar", side_effect=query):
            self.assertEqual(m.source_bytes(Path("/tmp/pkg"), self.version), fake)
            manifest["abi"] = "FreeBSD:16:amd64"
            with self.assertRaisesRegex(m.Refusal, "ABI_UNQUALIFIED"):
                m.source_bytes(Path("/tmp/pkg"), self.version)
            manifest["abi"] = "FreeBSD:15:amd64"
            manifest["files"].pop(m.ARCHIVE_PREFIX + m.MODULES[-1])
            with self.assertRaisesRegex(m.Refusal, "NOT_DECLARED"):
                m.source_bytes(Path("/tmp/pkg"), self.version)
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(Path, "lstat", fake_root_lstat):
            root = Path(tmp)
            root.chmod(0o700)
            cli = m.stage(root, fake)
            self.assertEqual(cli, root / "native_pkg_managed.py")
            for name in m.MODULES:
                target = root / name
                self.assertEqual(target.read_bytes(), fake[name])
                self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
            with self.assertRaisesRegex(m.Refusal, "STAGING_OUTPUT_ALREADY_EXISTS"):
                m.stage(root, fake)

    def test_no_checkout_independent_positive_and_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.chmod(0o700)
            newer = Path(tmp) / ("os-zapret2-restyle-" + self.version + ".pkg")
            old = Path(tmp) / ("os-zapret2-restyle-" + self.old_version + ".pkg")
            modules = {name: b"#!/usr/bin/env python3\n# isolated\n"
                       for name in m.MODULES}
            response = {"status": "PASS_MANAGED_READ_ONLY_PREDECESSOR_SCREEN",
                        "predecessor_cold_screened": True, "archive_sha256": self.old_sha,
                        "pkg_invoked": False, "old_owner_qualified": False,
                        "lh08_ac11_accepted": False}
            def proc(argv, **kwargs):
                self.assertEqual(argv[:3], [m.sys.executable, "-E", "-B"])
                self.assertTrue(argv[3].startswith(str(root)))
                self.assertEqual(kwargs["cwd"], str(root))
                self.assertNotIn("PYTHONPATH", kwargs["env"])
                return SimpleNamespace(returncode=0, stderr="",
                                       stdout="ZAPRET2_MANAGED="+json.dumps(response)+"\n")
            with patch.object(m, "ROOT", root), \
                 patch.object(m, "require_root_source", return_value="f"*64), \
                 patch.object(m, "verified_archive") as bound, \
                 patch.object(m, "source_bytes", return_value=modules), \
                 patch.object(Path, "lstat", fake_root_lstat), \
                 patch.object(m.subprocess, "run", side_effect=proc):
                result = m.inspect(newer, self.version, self.sha,
                                   old, self.old_version, self.old_sha)
                self.assertEqual(bound.call_count, 4)
                self.assertEqual(result["status"], "PASS_STANDALONE_PREPKG_READ_ONLY_COLD")
                self.assertFalse(result["pkg_invoked"])
                self.assertFalse(result["supported_mandatory_entrypoint"])
                self.assertEqual(set(result["modules_sha256"]), set(m.MODULES))
            self.assertFalse(list(root.iterdir()), "private temporary bytes remain")

    def test_worker_false_authorization_not_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.chmod(0o700)
            data = {name: b"#!/usr/bin/env python3\n" for name in m.MODULES}
            fake = {"status": "PASS_MANAGED_READ_ONLY_PREDECESSOR_SCREEN",
                    "predecessor_cold_screened": True, "archive_sha256": self.old_sha,
                    "pkg_invoked": True, "old_owner_qualified": True,
                    "lh08_ac11_accepted": True}
            with patch.object(m, "ROOT", root), \
                 patch.object(m, "require_root_source", return_value="f"*64), \
                 patch.object(m, "verified_archive"), \
                 patch.object(m, "source_bytes", return_value=data), \
                 patch.object(Path, "lstat", fake_root_lstat), \
                 patch.object(m.subprocess, "run", return_value=SimpleNamespace(
                    returncode=0, stderr="", stdout="ZAPRET2_MANAGED="+json.dumps(fake)+"\n")):
                with self.assertRaisesRegex(m.Refusal,"FALSE_AUTHORIZATION"):
                    m.inspect(Path("/root/new"), self.version,self.sha,
                              Path("/root/old"),self.old_version,self.old_sha)
            self.assertEqual(list(root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
