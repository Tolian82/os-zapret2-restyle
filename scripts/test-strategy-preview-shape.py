#!/usr/bin/env python3
"""P5a focused source-only regression: canonical structural preview is not Apply."""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend/strategy_preview.py"
POLICY = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend/profile_policy.py"


def run_preview(request: object, *, raw: bytes | None = None, cwd: str | None = None):
    data = (json.dumps(request, ensure_ascii=False).encode("utf-8")
            if raw is None else raw)
    return subprocess.run(
        [sys.executable, str(HELPER), "inspect-stdin"],
        input=data, capture_output=True, cwd=cwd, check=False, timeout=8,
    )


class P5AStructural(unittest.TestCase):
    def valid(self, strategy: str, mode: str = "all", **other):
        result = run_preview({"strategy": strategy, "target_mode": mode, **other})
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        self.assertFalse(result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["state"], "advisory_not_native_validated")
        self.assertEqual(report["schema"], "p5a-structural-advisory-v1")
        self.assertEqual(report["engine_native_dry_run"], "not_run")
        self.assertEqual(report["actual_resources"], "not_checked")
        self.assertEqual(report["actual_voice_merge"], "not_checked")
        self.assertEqual(report["effective_ipfw_port_coverage"], "not_computed")
        self.assertEqual(report["real_network_bypass"], "not_tested")
        self.assertEqual(report["config_process_fd9_ipfw_mutation"], "not_performed")
        return report

    def refused(self, request, reason: str, raw: bytes | None = None):
        result = run_preview(request, raw=raw)
        self.assertEqual(result.returncode, 65, result.stdout.decode(errors="replace"))
        self.assertFalse(result.stdout)
        self.assertIn("P5A_STRUCTURAL_PREVIEW_REFUSED=" + reason,
                      result.stderr.decode("utf-8"))
        self.assertNotIn("Traceback", result.stderr.decode("utf-8"))

    def test_empty_strategy_is_allowed(self):
        r = self.valid("", "all")
        self.assertEqual(r["canonical_source_profile_count"], 0)
        self.assertEqual(r["canonical_expanded_profile_count"], 0)
        self.assertEqual(r["profiles"], [])
        self.assertIn("EMPTY_TRAFFIC_STRATEGY_ALLOWED", r["warnings"])

    def test_tcp_tls_and_udp_quic_native_profile_order(self):
        sample = (
            "--filter-tcp=443\n--filter-l7=tls\n<HOSTLIST:youtube>\n"
            "--payload=tls_client_hello\n--out-range=-d10\n"
            "--lua-desync=multisplit:pos=midsld:seqovl=1\n--new\n"
            "--filter-udp=443\n--filter-l7=quic\n<HOSTLIST:youtube>\n"
            "--payload=quic_initial\n"
            "--lua-desync=fake:blob=fake_default_quic:repeats=5\n"
        )
        r = self.valid(sample, "list", extra_arguments="--debug=1",
                       exclude_domains_configured=True)
        self.assertEqual(r["canonical_source_profile_count"], 2)
        self.assertEqual(r["canonical_expanded_profile_count"], 2)
        first, second = r["profiles"]
        self.assertEqual([x["number"] for x in r["profiles"]], [1, 2])
        self.assertEqual(first["requested_ports"], {"tcp": ["443"], "udp": []})
        self.assertEqual(second["requested_ports"], {"tcp": [], "udp": ["443"]})
        self.assertEqual(first["requested_l7"], ["tls"])
        self.assertEqual(second["requested_l7"], ["quic"])
        self.assertEqual(first["explicit_selectors"], ["<HOSTLIST:youtube>"])
        self.assertEqual(first["lua_actions"][0]["payload"], "tls_client_hello")
        self.assertEqual(first["lua_actions"][0]["out_range"], "-d10")
        self.assertEqual(second["lua_actions"][0]["payload"], "quic_initial")
        self.assertEqual(second["lua_actions"][0]["lua"],
                         "fake:blob=fake_default_quic:repeats=5")
        self.assertIn("EXTRA_ARGUMENTS_SCOPE_NOT_RESOLVED", r["warnings"])
        self.assertTrue(r["global_exclusions_configured"]["domains"])
        self.assertFalse(r["global_exclusions_configured"]["ipset"])

    def test_one_profile_expands_two_native_selectors(self):
        raw = ("--filter-tcp=80,443\n--filter-l7=http,tls\n"
               "<HOSTLIST:user>\n<IPSET:telegram>\n"
               "--payload=http_req\n--lua-desync=multisplit:pos=method+2\n")
        r = self.valid(raw, "auto")
        self.assertEqual(r["canonical_source_profile_count"], 1)
        self.assertEqual(r["canonical_expanded_profile_count"], 2)
        self.assertEqual([x["explicit_selectors"] for x in r["profiles"]],
                         [["<HOSTLIST:user>"], ["<IPSET:telegram>"]])
        self.assertTrue(all(p["requested_default_mode"] == "auto"
                            for p in r["profiles"]))
        self.assertTrue(all(p["target_source"] == "explicit_placeholders"
                            for p in r["profiles"]))
        self.assertIn("MULTI_TARGET_PROFILE_EXPANSION", r["warnings"])

    def test_first_match_warning_is_possibility_not_assertion(self):
        p = ("--filter-tcp=443\n--filter-l7=tls\n<HOSTLIST:user>\n"
             "--payload=tls_client_hello\n--lua-desync=fake\n")
        r = self.valid(p + "--new\n" + p)
        self.assertNotIn("POSSIBLE_FIRST_MATCH_OVERLAP", r["profiles"][0]["warnings"])
        self.assertIn("POSSIBLE_FIRST_MATCH_OVERLAP", r["profiles"][1]["warnings"])
        self.assertEqual(r["engine_native_dry_run"], "not_run")

    def test_duplicate_reference_warning_not_misrepresented_as_resolved_file(self):
        p = ("--filter-tcp=80\n<HOSTLIST:user>\n<HOSTLIST:user>\n"
             "--payload=http_req\n--lua-desync=multisplit\n")
        r = self.valid(p)
        self.assertIn("REPEATED_TEXTUAL_TARGET_REFERENCE", r["profiles"][0]["warnings"])

    def test_default_mode_and_direct_native_targets_remain_unresolved(self):
        p = ("--filter-tcp=443\n--hostlist-domains=example.org\n"
             "--lua-desync=fake\n")
        r = self.valid(p, "list")
        self.assertEqual(r["profiles"][0]["target_source"],
                         "native_direct_target_unresolved")
        self.assertEqual(r["effective_ipfw_port_coverage"], "not_computed")

    def test_refuse_empty_and_malformed_new_boundary(self):
        self.refused({"strategy": "--new\n--filter-tcp=443", "target_mode": "all"},
                     "CANONICAL_PROFILE_POLICY_REFUSED")
        self.refused({"strategy": "--filter-tcp=443\n--new\n",
                      "target_mode": "all"}, "CANONICAL_PROFILE_POLICY_REFUSED")

    def test_refuse_incomplete_placeholder(self):
        self.refused({"strategy": "--filter-tcp=443\n<HOSTLIST:>\n",
                      "target_mode": "all"}, "CANONICAL_PROFILE_POLICY_REFUSED")

    def test_refuse_unknown_target_mode_and_fields(self):
        self.refused({"strategy": "", "target_mode": "other"}, "TARGET_MODE_INVALID")
        self.refused({"strategy": "", "target_mode": "all", "run": True},
                     "REQUEST_FIELDS_INVALID")
        self.refused({"strategy": "", "target_mode": "all",
                      "exclude_ipset_configured": "true"}, "REQUEST_FIELD_TYPES_INVALID")

    def test_refuse_duplicate_json_keys_and_binary(self):
        self.refused({}, "DUPLICATE_REQUEST_KEY",
                     raw=b'{"strategy":"","strategy":"--new","target_mode":"all"}')
        self.refused({}, "REQUEST_JSON_INVALID", raw=b"\xff")
        self.refused({}, "REQUEST_SIZE_INVALID", raw=b"A" * 65537)
        self.refused({"strategy": "--filter-tcp=443\x00",
                      "target_mode": "all"}, "CONTROL_CHARACTER_REFUSED")

    def test_no_tmp_or_config_write_by_cli_even_for_invalid_request(self):
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder) / "sentinel"
            marker.write_bytes(b"unchanged")
            before = {p.name: p.read_bytes() for p in Path(folder).iterdir()}
            valid = run_preview({"strategy": "--filter-tcp=443\n--lua-desync=fake\n",
                                 "target_mode": "all"}, cwd=folder)
            invalid = run_preview({"strategy": "--new", "target_mode": "all"},
                                  cwd=folder)
            self.assertEqual(valid.returncode, 0)
            self.assertEqual(invalid.returncode, 65)
            self.assertEqual(before, {p.name: p.read_bytes()
                                      for p in Path(folder).iterdir()})

    def test_static_pure_boundary_reuses_canonical_parser(self):
        source = HELPER.read_text(encoding="utf-8")
        tree = ast.parse(source)
        self.assertIn("profile_policy.split_profiles(", source)
        self.assertIn("profile_policy.expand_profiles(", source)
        forbidden = {"os", "subprocess", "tempfile", "fcntl", "socket", "shutil",
                     "pathlib", "ctypes"}
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(item.name.split(".")[0] for item in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        self.assertFalse(forbidden & imports, forbidden & imports)
        self.assertIn("split_profiles(", POLICY.read_text(encoding="utf-8"))
        self.assertIn("def expand_profiles(", POLICY.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
