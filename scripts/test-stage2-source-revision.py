#!/usr/bin/env python3
"""Positive and negative tests of native CI source revision parsing."""
from pathlib import Path
import tempfile
import unittest

from stage2_source_revision import revision_from_makefile, version_from_file


class NativeSourceRevisionTests(unittest.TestCase):
    def test_exact_current_makefile(self):
        current = Path(__file__).resolve().parent.parent / "Makefile"
        self.assertEqual(revision_from_makefile(), revision_from_makefile(current))

    def test_product_version_comes_from_single_root_file(self):
        self.assertEqual(version_from_file(), (Path(__file__).resolve().parent.parent / "VERSION").read_text().strip())
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "VERSION"
            for version in ("0.6.2", "0.6.3", "1.7.23"):
                source.write_text(version + "\n")
                self.assertEqual(version_from_file(source), version)
            for invalid in ("", "v0.6.2", "0.6", "0.6.2-dev", "0.6.2\n0.6.3", " 0.6.2", "0.6.2 "):
                with self.subTest(invalid=invalid):
                    source.write_text(invalid)
                    with self.assertRaisesRegex(ValueError, "VERSION_INVALID"):
                        version_from_file(source)

    def test_valid_revisions(self):
        for rev in ("1", "83", "999"):
            with self.subTest(rev=rev), tempfile.TemporaryDirectory() as td:
                path = Path(td) / "Makefile"
                path.write_text("PLUGIN_REVISION=    " + rev + "\n")
                self.assertEqual(revision_from_makefile(path), rev)

    def test_refuses_invalid_missing_ambiguous(self):
        cases = ("", "PLUGIN_REVISION=0\n", "PLUGIN_REVISION=082\n",
                 "PLUGIN_REVISION=invalid\n",
                 "PLUGIN_REVISION=83\nPLUGIN_REVISION=84\n",
                 " PLUGIN_REVISION=83\n", "PLUGIN_REVISION=1000000\n",
                 "PLUGIN_REVISION=83\n PLUGIN_REVISION=84\n")
        for value in cases:
            with self.subTest(value=value), tempfile.TemporaryDirectory() as td:
                path = Path(td) / "Makefile"
                path.write_text(value)
                with self.assertRaisesRegex(ValueError, "MISSING_OR_AMBIGUOUS"):
                    revision_from_makefile(path)


if __name__ == "__main__":
    unittest.main()
