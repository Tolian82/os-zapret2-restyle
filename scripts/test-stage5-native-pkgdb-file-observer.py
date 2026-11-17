#!/usr/bin/env python3
"""S0 metadata-only pkgdb forensic observer contracts."""
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).with_name("stage5-native-pkgdb-file-observer.py")
spec = importlib.util.spec_from_file_location("file_observer", SOURCE)
observer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observer)


class PkgdbFileObserverTests(unittest.TestCase):
    def test_read_only_header_and_sidecar_presence(self):
        with tempfile.TemporaryDirectory() as work:
            base = Path(work)
            main = base / "local.sqlite"
            header = bytearray(100)
            header[:16] = b"SQLite format 3\x00"
            header[16:18] = (4096).to_bytes(2, "big")
            header[18:20] = bytes((1, 1))
            header[24:28] = (17).to_bytes(4, "big")
            main.write_bytes(header + b"PRIVATE_DATA_DO_NOT_LOG")
            journal = base / "local.sqlite-journal"
            journal.write_bytes(b"\xd9\xd5\x05\xf9\x20\xa1\x63\xd7" + b"PRIVATE")
            before_main = main.read_bytes()
            before_journal = journal.read_bytes()
            data = observer.snapshot(base)
            self.assertEqual(data["main"]["sqlite_header"], "recognized")
            self.assertTrue(data["main"]["page_size_valid"])
            self.assertEqual(data["main"]["change_counter"], 17)
            self.assertTrue(data["rollback_journal"]["rollback_header_magic"])
            self.assertEqual(data["wal"]["state"], "missing")
            self.assertEqual(data["shm"]["state"], "missing")
            self.assertEqual(main.read_bytes(), before_main)
            self.assertEqual(journal.read_bytes(), before_journal)
            self.assertNotIn("PRIVATE", str(data))
            self.assertNotIn(str(base), str(data))

    def test_symlink_and_nonregular_path_refused_without_follow(self):
        with tempfile.TemporaryDirectory() as work:
            base = Path(work)
            dest = base / "private"
            dest.write_bytes(b"do not open")
            (base / "local.sqlite").symlink_to(dest)
            (base / "local.sqlite-wal").mkdir()
            got = observer.snapshot(base)
            self.assertEqual(got["main"]["state"], "unsafe-file")
            self.assertEqual(got["wal"]["state"], "unsafe-file")
            self.assertEqual(dest.read_bytes(), b"do not open")

    def test_unrecognized_header_does_not_claim_corruption_or_recovery(self):
        with tempfile.TemporaryDirectory() as work:
            base = Path(work)
            (base / "local.sqlite").write_bytes(b"not a valid header")
            result = observer.snapshot(base)
            self.assertEqual(result["main"]["sqlite_header"], "unrecognized")
            self.assertNotIn("integrity_ok", str(result))
            self.assertNotIn("db_recovered", str(result))

    def test_report_is_bounded_and_rejects_arbitrary_phases(self):
        with self.assertRaisesRegex(ValueError, "NOT_AN_ALLOWED_FORENSIC_PHASE"):
            observer.report("rewrite-database")
        with tempfile.TemporaryDirectory() as work:
            original = observer.DEFAULT_DB_DIR
            try:
                observer.DEFAULT_DB_DIR = Path(work)
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    observer.report("post-sigkill")
                msg = output.getvalue()
            finally:
                observer.DEFAULT_DB_DIR = original
        self.assertIn("sqlite_connection_opened", msg)
        self.assertIn('"write_attempted": false', msg)
        self.assertNotIn("sqlite3.connect", SOURCE.read_text())
        self.assertNotIn("pkg add", SOURCE.read_text())


if __name__ == "__main__":
    unittest.main()
