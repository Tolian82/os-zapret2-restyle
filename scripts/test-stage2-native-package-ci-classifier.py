#!/usr/bin/env python3
"""Regression for actual general CI package path-classifier (PR #827 recovery).

Independent Stage 2 native workflow is valuable, but does not make a skipped
general package job PASS. This tests the real general CI regex, not a copy.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/ci.yml"


def package_source_pattern(source=None):
    if source is None:
        source = WORKFLOW.read_text(encoding="utf-8")
    matches = [line for line in source.splitlines()
               if "elif printf" in line and "classified_changed" in line
               and "grep -Eq" in line]
    if len(matches) != 1:
        raise AssertionError("ONE_AUTHORITATIVE_PACKAGE_PATH_CLASSIFIER_REQUIRED")
    marker = "grep -Eq '"
    if marker not in matches[0]:
        raise AssertionError("NATIVE_CI_PATH_REGEX_MISSING")
    return re.compile(matches[0].split(marker, 1)[1].split("'", 1)[0])


class NativePackageClassification(unittest.TestCase):
    def test_native_builder_and_signed_curl_trigger_real_package_job(self):
        for path in ("scripts/native-opnsense-package.py",
                     "scripts/build-curl-impersonate.sh",
                     "scripts/stage2-opnsense-native-private-source.py",
                     "scripts/stage2-opnsense-native-provider-preflight.py",
                     "scripts/stage0-opnsense-official-mk-source-package.py"):
            with self.subTest(path=path):
                self.assertTrue(package_source_pattern().search(path))

    def test_central_policy_change_triggers_real_package_job(self):
        for path in ("compatibility.json", "scripts/validate-compatibility.py",
                     "scripts/compatibility-bootstrap.sh",
                     "scripts/stage1-native-policy-static.py"):
            with self.subTest(path=path):
                self.assertTrue(package_source_pattern().search(path))

    def test_old_product_delivery_paths_continue_triggering(self):
        for path in ("Makefile", "VERSION", ".github/workflows/ci.yml",
                     "pkg/+PRE_INSTALL", "src/opnsense/service/conf/actions.d/actions_zapret.conf",
                     "repository/zapret2-restyle.conf", "scripts/build-pkg.sh",
                     "scripts/test-freebsd15-package-ci.sh"):
            with self.subTest(path=path):
                self.assertTrue(package_source_pattern().search(path))

    def test_docs_only_and_unrelated_sources_do_not_trigger(self):
        for path in ("README.md", "docs/START_HERE.md",
                     "docs/verification/evidence/receipt.md",
                     "scripts/test-stage2-native-package-ci-classifier.py",
                     "scripts/other-unrelated-analysis.py"):
            with self.subTest(path=path):
                self.assertFalse(package_source_pattern().search(path))

    def test_revision_only_makefile_normalization_remains(self):
        content = WORKFLOW.read_text()
        self.assertIn("old_makefile=$(git show", content)
        self.assertIn("new_makefile=$(git show", content)
        self.assertIn("classified_changed=$(printf", content)
        self.assertIn("needs.changes.outputs.package == 'true'", content)
        self.assertIn("Build official OPNsense 26.7 native package", content)

    def test_mandatory_regression_is_actually_executed_in_validate_project(self):
        content = WORKFLOW.read_text()
        self.assertIn("python3.13 scripts/test-stage2-native-package-ci-classifier.py", content)
        self.assertIn("Test native CI changed-path classifier", content)

    def test_dedicated_native_and_clean_install_remain_independent(self):
        for path in (".github/workflows/stage2-native-production-build.yml",
                     ".github/workflows/stage2-real-native-clean-install.yml"):
            with self.subTest(path=path):
                content = (ROOT / path).read_text()
                self.assertIn('release: "26.7"', content)
                self.assertIn("vmactions/opnsense-vm@", content)

    def test_native_candidate_package_name_is_derived_from_makefile(self):
        # A native _72 build must never be checked as the previous _71 file.
        content = (ROOT / ".github/workflows/stage2-native-production-build.yml").read_text()
        self.assertIn("version=$(tr -d", content)
        self.assertIn("revision=$(sed -nE", content)
        self.assertIn('package="dist/os-zapret2-restyle-${version}_${revision}.pkg"', content)
        self.assertIn('--arg expected "${version}_${revision}"', content)
        self.assertNotRegex(content, r'os-zapret2-restyle-0\.6\.2_[0-9]+\.pkg')

    def test_introducing_old_bug_is_rejected(self):
        source = WORKFLOW.read_text()
        broken = source.replace("|scripts/native-opnsense-package\\.py$", "")
        self.assertNotEqual(broken, source)
        self.assertFalse(package_source_pattern(broken).search(
            "scripts/native-opnsense-package.py"))


if __name__ == "__main__":
    unittest.main()
