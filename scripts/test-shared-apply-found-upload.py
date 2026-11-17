#!/usr/bin/env python3
"""Hostile multipart path/descriptor tests for the existing native FD9 transport."""
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest

BACKEND = Path(__file__).resolve().parents[1] / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))
from shared_apply_found_upload import read_qualified, UploadRefused, MAX_BYTES


class MultipartUploadTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="found-transport-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.root.chmod(0o700)
        self.name = self.root / "phpAaBbCc"
        self.body = b'{"kind":"tz6v2-found-form-intent"}'
        self.name.write_bytes(self.body)
        self.name.chmod(0o600)
        self.uid = os.geteuid()

    def read(self, *, digest=None, size=None):
        return read_qualified(self.name, len(self.body) if size is None else size,
            digest or hashlib.sha256(self.body).hexdigest(),
            self.uid, test_parent=self.root)

    def test_exact_content(self):
        self.assertEqual(self.read(), self.body)

    def test_wrong_digest(self):
        with self.assertRaises(UploadRefused):
            self.read(digest="0" * 64)

    def test_symlink_not_followed(self):
        self.name.unlink()
        (self.root / "target").write_bytes(self.body)
        self.name.symlink_to(self.root / "target")
        with self.assertRaises(UploadRefused):
            self.read()

    def test_fifo_does_not_block(self):
        self.name.unlink()
        os.mkfifo(self.name)
        with self.assertRaises(UploadRefused):
            self.read()

    def test_world_readable_upload_rejected(self):
        self.name.chmod(0o644)
        with self.assertRaises(UploadRefused):
            self.read()

    def test_oversize_and_missing(self):
        with self.assertRaises(UploadRefused):
            self.read(size=MAX_BYTES + 1)
        self.name.unlink()
        with self.assertRaises(UploadRefused):
            self.read()

    def test_default_tmp_upload_refused(self):
        with self.assertRaises(UploadRefused):
            read_qualified(Path('/tmp/phpAaBbCc'), len(self.body),
                hashlib.sha256(self.body).hexdigest(), self.uid)

    def test_unqualified_parent_refused(self):
        with self.assertRaises(UploadRefused):
            read_qualified(self.name, len(self.body),
                hashlib.sha256(self.body).hexdigest(), self.uid)


if __name__ == "__main__":
    unittest.main()
