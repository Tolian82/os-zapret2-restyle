#!/usr/bin/env python3
"""Regression: official Mk product inputs MUST activate general package CI.

This gate is separate from the dedicated installed-package OPNsense test;
a skipped package job must never be reported as executed acceptance.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github/workflows/ci.yml"


def package_source_pattern():
    source = WORKFLOW.read_text()
    matches = [line for line in source.splitlines()
               if "elif printf" in line and "classified_changed" in line
               and "grep -Eq" in line]
    if len(matches) != 1:
        raise AssertionError("ONE_AUTHORITATIVE_PACKAGE_PATH_CLASSIFIER_REQUIRED")
    marker = "grep -Eq '"
    return re.compile(matches[0].split(marker, 1)[1].split("'", 1)[0])


class NativePackageClassification(unittest.TestCase):
    def test_real_native_mk_builder_change_triggers_package_job(self):
        self.assertTrue(package_source_pattern().search("scripts/native-opnsense-package.py"))

    def test_signed_private_curl_extraction_change_triggers_package_job(self):
        self.assertTrue(package_source_pattern().search("scripts/build-curl-impersonate.sh"))

    def test_old_product_delivery_paths_still_trigger(self):
        for path in ("Makefile", "VERSION", ".github/workflows/ci.yml",
                     "pkg/+PRE_INSTALL", "src/opnsense/service/conf/actions.d/actions_zapret.conf",
                     "repository/zapret2-restyle.conf", "scripts/build-pkg.sh",
                     "scripts/test-freebsd15-package-ci.sh"):
            with self.subTest(path=path):
                self.assertTrue(package_source_pattern().search(path))

    def test_pure_docs_do_not_force_native_product_package(self):
        for path in ("README.md", "docs/START_HERE.md", "docs/PROJECT_STATE.md",
                     "docs/verification/evidence/receipt.md"):
            with self.subTest(path=path):
                self.assertFalse(package_source_pattern().search(path))

    def test_revision_only_makefile_normalization_remains(self):
        text = WORKFLOW.read_text()
        self.assertIn("old_makefile=$(git show", text)
        self.assertIn("new_makefile=$(git show", text)
        self.assertIn("classified_changed=$(printf", text)

    def test_general_package_job_still_requires_classifier(self):
        text = WORKFLOW.read_text()
        self.assertIn("needs.changes.outputs.package == 'true'", text)
        self.assertIn("Build official OPNsense 26.7 native package", text)
        self.assertIn("Test official native package path classification", text)

    def test_dedicated_install_and_source_package_jobs_independent(self):
        workflows = [".github/workflows/stage2-native-production-build.yml",
                     ".github/workflows/stage2-real-native-clean-install.yml"]
        for path in workflows:
            with self.subTest(path=path):
                source = (ROOT / path).read_text()
                self.assertIn('release: "26.7"', source)
                self.assertIn("vmactions/opnsense-vm@", source)
        installed = (ROOT / workflows[1]).read_text()
        self.assertIn("stage2-opnsense-real-native-clean-install.py", installed)
        source_only = (ROOT / workflows[0]).read_text()
        self.assertIn("scripts/build-pkg.sh", source_only)


if __name__ == "__main__":
    unittest.main()
