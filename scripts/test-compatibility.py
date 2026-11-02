#!/usr/bin/env python3
"""Stage 1 positive/negative matrix tests, including hypothetical FreeBSD 16."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("compatibility_validation",
                                           HERE / "validate-compatibility.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class CompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = m.load(m.DEFAULT)

    def edited(self):
        return copy.deepcopy(self.base)

    def invalid(self, policy, code, root=m.ROOT):
        with self.assertRaisesRegex(m.Refusal, code):
            m.validate(policy, root)

    def test_qualified_original_native_tuple(self):
        self.assertEqual(len(m.validate(self.base)), 1)
        report = m.check_target(self.base, "26.7", "FreeBSD:15:amd64",
                                "amd64", "3.13.16")
        self.assertEqual(report["status"], "PASS_QUALIFIED_POLICY_TUPLE_ONLY")
        self.assertFalse(report["native_lifecycle_acceptance"])
        self.assertEqual(m.main([]), 0)

    def test_python_patch_update_same_branch(self):
        self.assertEqual(m.check_target(
            self.base, "26.7", "FreeBSD:15:amd64", "amd64", "3.13.99"
        )["python_branch"], "3.13")

    def test_freebsd_16_refused_without_qualification(self):
        with self.assertRaisesRegex(m.Refusal, "UNSUPPORTED_FREEBSD_ABI"):
            m.check_target(self.base, "26.7", "FreeBSD:16:amd64",
                           "amd64", "3.13.16")

    def test_opnsense_abi_and_architecture_must_match(self):
        for args, message in [
            (("27.1", "FreeBSD:15:amd64", "amd64", "3.13.16"),
             "UNSUPPORTED_OPNSENSE_PRODUCT_ABI"),
            (("26.7", "FreeBSD:15:amd64", "arm64", "3.13.16"),
             "UNSUPPORTED_ARCHITECTURE"),
            (("26.7", "FreeBSD:15:amd64", "amd64", "3.14.0"),
             "UNSUPPORTED_PYTHON_BRANCH"),
        ]:
            with self.subTest(message=message):
                with self.assertRaisesRegex(m.Refusal, message):
                    m.check_target(self.base, *args)

    def test_malformed_and_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "matrix.json"
            p.write_text('{"schema_version":1,"schema_version":2}')
            with self.assertRaisesRegex(m.Refusal, "DUPLICATE_JSON_KEY"):
                m.load(p)
            p.write_text('{"a":')
            with self.assertRaisesRegex(m.Refusal, "INVALID_JSON"):
                m.load(p)

    def test_bad_schema_unknown_fields_and_empty_platforms(self):
        x = self.edited()
        x["schema_version"] = 2
        self.invalid(x, "UNSUPPORTED_SCHEMA")
        x = self.edited()
        x["unknown"] = True
        self.invalid(x, "INVALID_TOP_LEVEL_FIELDS")
        x = self.edited()
        x["supported_platforms"] = []
        self.invalid(x, "EMPTY_PLATFORM_MATRIX")

    def test_no_duplicate_tuple_or_unqualified_exception(self):
        x = self.edited()
        x["supported_platforms"].append(copy.deepcopy(x["supported_platforms"][0]))
        self.invalid(x, "DUPLICATE_PLATFORM_TUPLE")
        x = self.edited()
        x["exceptions"] = [{"allow_all": True}]
        self.invalid(x, "UNQUALIFIED_EXCEPTION_POLICY")

    def test_python_policy_and_arch_conflicts(self):
        x = self.edited()
        x["supported_platforms"][0]["python"]["entrypoint"] = "/usr/local/bin/python3.13"
        self.invalid(x, "UNQUALIFIED_PYTHON_ENTRYPOINT")
        x = self.edited()
        x["supported_platforms"][0]["architecture"] = "arm64"
        self.invalid(x, "ABI_ARCHITECTURE_MISMATCH")
        x = self.edited()
        x["supported_platforms"][0]["python"]["supported"] = ["3.13", "3.13"]
        self.invalid(x, "INVALID_PYTHON_BRANCHES")

    def test_future_16_requires_own_matching_real_evidence(self):
        x = self.edited()
        platform = copy.deepcopy(x["supported_platforms"][0])
        platform["freebsd_pkg_abi"] = "FreeBSD:16:amd64"
        x["supported_platforms"].append(platform)
        self.invalid(x, "QUALIFICATION_EVIDENCE_PLATFORM_MISMATCH")

    def test_future_16_admittable_with_explicit_separate_evidence_fixture(self):
        # This is a synthetic policy/unit fixture, NOT proof of FreeBSD 16 support.
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            rel = Path("docs/verification/evidence/freebsd16-fixture.md")
            (root / rel).parent.mkdir(parents=True)
            (root / rel).write_text("OPNsense 27.1 / FreeBSD 16 test fixture\n")
            x = self.edited()
            x["supported_platforms"] = [
                {**copy.deepcopy(x["supported_platforms"][0]),
                 "opnsense_product_abi": "27.1",
                 "freebsd_pkg_abi": "FreeBSD:16:amd64",
                 "qualification": {"scope": "isolated-native-build-and-pkg-install-only",
                                   "evidence": rel.as_posix()}}
            ]
            self.assertEqual(len(m.validate(x, root)), 1)
            self.assertEqual(m.check_target(
                x, "27.1", "FreeBSD:16:amd64", "amd64", "3.13.16"
            )["status"], "PASS_QUALIFIED_POLICY_TUPLE_ONLY")

    def test_missing_capability_refused(self):
        x = self.edited()
        x["required_capabilities"] = ["owned-ipfw"]
        m.validate(x)
        with self.assertRaisesRegex(m.Refusal, "MISSING_REQUIRED_CAPABILITY:owned-ipfw"):
            m.check_target(x, "26.7", "FreeBSD:15:amd64",
                           "amd64", "3.13.16", [])

    def test_no_implicit_platform_probing_or_mutation(self):
        source = (HERE / "validate-compatibility.py").read_text()
        for forbidden in ("subprocess.", "os.system(", "pkg add", "pkg delete",
                          "chmod(", "unlink(", "socket.", "urllib."):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
