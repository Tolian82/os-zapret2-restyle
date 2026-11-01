#!/usr/bin/env python3
"""Offline fail-closed fixtures for independently authenticated OPNsense trust."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location(
    "trust", Path(__file__).with_name("stage0-verify-opnsense-official-key.py"))
trust = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trust)


def fingerprint(value=None):
    return ('function: "sha256"\n'
            'fingerprint: "' + (value or trust.OFFICIAL_26_7_PKG_SHA256) + '"\n')


class Official26_7KeyTests(unittest.TestCase):
    def fixture(self, tmp):
        root = Path(tmp) / "OPNsense"
        (root / "trusted").mkdir(parents=True)
        (root / "revoked").mkdir()
        (root / "trusted" / trust.OFFICIAL_26_7_TRUSTED_FILENAME).write_text(
            fingerprint(), encoding="ascii")
        return root

    def test_official_pem_matches_pinned_core_sha256(self):
        self.assertEqual(trust.official_pem_fingerprint(),
                         "9f3b76ffef38fb6405595038b324b61043c9a2c375ae5c151d628508e9a845ce")

    def test_independent_release_pem_tampering_refused(self):
        with mock.patch.object(trust, "OFFICIAL_26_7_PEM",
                               trust.OFFICIAL_26_7_PEM.replace("MIICIj", "MIICIk")):
            with self.assertRaisesRegex(trust.Refusal, "OFFICIAL_PEM_AND_CORE"):
                trust.official_pem_fingerprint()

    def test_exact_trust_and_prior_revocations_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.fixture(tmp)
            (root / "revoked" / "old-key").write_text(fingerprint("a" * 64))
            observed = trust.verify_trust(root, root_owner=False)
            self.assertTrue(observed["installed_key_matches_independent_official_reference"])
            self.assertFalse(observed["official_key_found_in_revoked"])

    def test_installed_key_mismatch_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.fixture(tmp)
            (root / "trusted" / trust.OFFICIAL_26_7_TRUSTED_FILENAME).write_text(
                fingerprint("0" * 64))
            with self.assertRaisesRegex(trust.Refusal, "INSTALLED_KEY_DIFFERS"):
                trust.verify_trust(root, root_owner=False)

    def test_unexpected_extra_or_missing_key_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.fixture(tmp)
            key = root / "trusted" / trust.OFFICIAL_26_7_TRUSTED_FILENAME
            (root / "trusted" / "extra").write_text(fingerprint())
            with self.assertRaisesRegex(trust.Refusal, "EXTRA_MISSING"):
                trust.verify_trust(root, root_owner=False)
            (root / "trusted" / "extra").unlink()
            key.unlink()
            with self.assertRaisesRegex(trust.Refusal, "EXTRA_MISSING"):
                trust.verify_trust(root, root_owner=False)

    def test_symlinked_key_and_keystore_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.fixture(tmp)
            key = root / "trusted" / trust.OFFICIAL_26_7_TRUSTED_FILENAME
            original = root / "key"
            key.rename(original)
            key.symlink_to(original)
            with self.assertRaisesRegex(trust.Refusal, "SYMLINK"):
                trust.verify_trust(root, root_owner=False)
            key.unlink()
            key.write_text(fingerprint())
            trusted = root / "trusted"
            trusted.rename(root / "real-trusted")
            trusted.symlink_to(root / "real-trusted", target_is_directory=True)
            with self.assertRaisesRegex(trust.Refusal, "KEYSTORE_SYMLINK"):
                trust.verify_trust(root, root_owner=False)

    def test_writable_key_and_directory_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.fixture(tmp)
            key = root / "trusted" / trust.OFFICIAL_26_7_TRUSTED_FILENAME
            key.chmod(0o666)
            with self.assertRaisesRegex(trust.Refusal, "UNSAFE_FINGERPRINT_FILE"):
                trust.verify_trust(root, root_owner=False)
            key.chmod(0o644)
            (root / "trusted").chmod(0o777)
            with self.assertRaisesRegex(trust.Refusal, "UNSAFE_KEYSTORE_DIRECTORY"):
                trust.verify_trust(root, root_owner=False)

    def test_official_key_in_revoked_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.fixture(tmp)
            (root / "revoked" / "wrong").write_text(fingerprint())
            with self.assertRaisesRegex(trust.Refusal, "IS_REVOKED"):
                trust.verify_trust(root, root_owner=False)

    def test_missing_or_ambiguous_fingerprint_fields_refused(self):
        for raw in [fingerprint() + 'function: "sha256"\n',
                    fingerprint().replace("sha256", "md5"),
                    "fingerprint: " + trust.OFFICIAL_26_7_PKG_SHA256 + "\n",
                    fingerprint().replace("fingerprint:", "other:")]:
            with self.subTest(raw=raw[:75]):
                with self.assertRaises(trust.Refusal):
                    trust.parse_fingerprint(raw)

    def test_empty_or_invalid_revoked_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.fixture(tmp)
            bad = root / "revoked" / "bad"
            bad.write_text("unsupported-content")
            with self.assertRaisesRegex(trust.Refusal, "FINGERPRINT_FORMAT_AMBIGUOUS"):
                trust.verify_trust(root, root_owner=False)
            bad.unlink()
            bad.symlink_to(root / "trusted" / trust.OFFICIAL_26_7_TRUSTED_FILENAME)
            with self.assertRaisesRegex(trust.Refusal, "SYMLINK"):
                trust.verify_trust(root, root_owner=False)


if __name__ == "__main__":
    unittest.main()
