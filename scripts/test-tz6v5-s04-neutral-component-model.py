#!/usr/bin/env python3
"""Real S04 pure classifier tests; these are SOURCE tests, never native proof."""
from __future__ import annotations

import builtins
from itertools import product
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"))
from component_inventory import COMPONENT_ENUMS, ComponentModelError, classify  # noqa: E402


class S04NeutralModel(unittest.TestCase):
    BASE = dict(plugin="installed", engine="valid", config="initialized",
                manifest="valid", runtime="STOPPED")

    def expect(self, change, code):
        result = classify({**self.BASE, **change})
        self.assertEqual(result["schema"], 1)
        self.assertEqual(result["classification"], code)
        self.assertEqual(result["authorization"], "NONE")
        self.assertIs(result["physical_transition_allowed"], False)
        self.assertIs(result["original_fd9_attestation_required"], True)
        self.assertEqual(result["components"], {**self.BASE, **change})
        return result

    def test_required_original_component_cases(self):
        self.expect(dict(plugin="absent", engine="absent", config="absent",
                         manifest="missing"), "PLUGIN_NOT_INSTALLED")
        self.expect(dict(engine="absent", config="absent", manifest="missing"),
                    "ENGINE_NOT_INSTALLED")
        self.expect(dict(config="absent", manifest="missing"),
                    "CONFIG_UNINITIALIZED")
        self.expect(dict(runtime="RUNNING", config="invalid"),
                    "CONFIG_INVALID")
        self.expect(dict(runtime="FOREIGN_OR_UNVERIFIED"), "FOREIGN_OWNER")
        self.expect(dict(runtime="INCOMPLETE"), "RUNTIME_INCOMPLETE")

    def test_manifest_and_readiness_are_never_authority(self):
        self.expect(dict(manifest="missing"), "MANIFEST_UNAVAILABLE")
        self.expect(dict(manifest="stale"), "MANIFEST_STALE")
        self.expect(dict(manifest="invalid"), "MANIFEST_INVALID")
        self.expect(dict(runtime="RUNNING"),
                    "RUNNING_REQUIRES_ORIGINAL_OWNER_ATTESTATION")
        self.expect({}, "COMPONENTS_PRESENT_REQUIRES_PREFLIGHT")

    def test_all_unknown_and_invalid_fail_closed(self):
        for key in COMPONENT_ENUMS:
            self.expect({key: "unknown" if key != "runtime" else "UNKNOWN"},
                        {"plugin":"PLUGIN_UNVERIFIED",
                         "engine":"ENGINE_UNVERIFIED",
                         "config":"CONFIG_UNVERIFIED",
                         "manifest":"MANIFEST_UNVERIFIED",
                         "runtime":"RUNTIME_UNVERIFIED"}[key])
            for bad in (None, False, 0, "", "YES", {}, []):
                with self.subTest(key=key, bad=type(bad).__name__):
                    with self.assertRaises(ComponentModelError):
                        classify({**self.BASE, key: bad})
        with self.assertRaises(ComponentModelError):
            classify({**self.BASE, "extra": "valid"})
        with self.assertRaises(ComponentModelError):
            classify({k:v for k,v in self.BASE.items() if k != "manifest"})
        with self.assertRaises(ComponentModelError):
            classify({**self.BASE, "runtime": "FOREIGN"})
        with self.assertRaises(ComponentModelError):
            classify("RUNNING")

    def test_every_enum_combination_is_not_permission_to_start_or_stop(self):
        keys = tuple(COMPONENT_ENUMS)
        for combo in product(*(sorted(COMPONENT_ENUMS[k]) for k in keys)):
            result = classify(dict(zip(keys, combo)))
            self.assertFalse(result["physical_transition_allowed"])
            self.assertEqual(result["authorization"], "NONE")
            self.assertTrue(result["original_fd9_attestation_required"])

    def test_classification_does_not_write_or_spawn(self):
        # Patching all common external side-effect paths is a regression
        # tripwire; production module contains no IO imports/calls.
        with patch.object(builtins, "open", side_effect=AssertionError("IO")), \
             patch("subprocess.Popen", side_effect=AssertionError("spawn")), \
             patch("os.open", side_effect=AssertionError("open")):
            self.expect({}, "COMPONENTS_PRESENT_REQUIRES_PREFLIGHT")
            self.expect({"runtime":"FOREIGN_OR_UNVERIFIED"}, "FOREIGN_OWNER")

    def test_report_is_detached_and_secret_free(self):
        facts = dict(self.BASE)
        result = classify(facts)
        result["components"]["engine"] = "absent"
        self.assertEqual(facts["engine"], "valid")
        self.assertEqual(classify(facts), classify(facts))
        self.assertNotIn("command", str(result))
        self.assertNotIn("/conf/", str(result))


if __name__ == "__main__":
    unittest.main(verbosity=2)
