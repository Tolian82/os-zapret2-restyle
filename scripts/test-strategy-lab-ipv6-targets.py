#!/usr/bin/env python3
"""IPv6 literal, AAAA-only and dual-family exact-pinning Stage 6 contracts."""
from __future__ import annotations
from pathlib import Path
import json
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "src/opnsense/scripts/OPNsense/Zapret"
sys.path.insert(0, str(PKG))
from strategy_lab_py import endpoint_epoch, candidate, probe, request, ip_target_support, extended

class Result:
    stdout = "exit=0 remote_ip=2001:db8::10 http=1.1 code=200 bytes=42 ssl_verify=0 appconnect=0.1"
    stderr = ""
    returncode = 0
    duration_ms = 1
    timed_out = False
    ok = True
    def evidence(self):
        return {"duration_ms": 1, "command": ["curl"]}

class DualStack(unittest.TestCase):
    def test_exact_address_family_and_bracketed_ipv6_url(self):
        with patch.object(request, "binary", return_value="/curl"):
            cmd = request._curl_command("example.org", scheme="https", family="ipv6", bound_ip="2001:db8::10")
            self.assertIn("example.org:443:[2001:db8::10]", cmd)
            self.assertIn("https://example.org/", cmd)
            self.assertIn("--ipv6", cmd)
            direct = request._curl_command("2001:db8::10", scheme="https", family="ipv6", bound_ip="2001:db8::10")
            self.assertIn("https://[2001:db8::10]/", direct)
            self.assertNotIn("--resolve", direct)
            for bad in ("192.0.2.1", "::ffff:192.0.2.1%bad", "fe80::1%em0"):
                with self.assertRaises(request.UsageError):
                    request._curl_command("example.org", scheme="https", family="ipv6", bound_ip=bad)
            with self.assertRaises(request.UsageError):
                request._curl_command("2001:db8::20", scheme="https", family="ipv6", bound_ip="2001:db8::10")

    def test_canonical_ipv6_operation(self):
        from contextlib import redirect_stdout
        from io import StringIO
        with redirect_stdout(StringIO()) as buf:
            self.assertEqual(request.main(["canonical-ipv6", "2001:0DB8:0000::000a"]), 0)
        self.assertEqual(buf.getvalue().strip(), "2001:db8::a")
        for bad in ("https://[2001:db8::a]/", "2001:db8::1%em0", "2001:db8::g", "203.0.113.10"):
            with self.assertRaises(request.UsageError):
                request.main(["canonical-ipv6", bad])

    def test_search_epoch_mixed_and_aaaa_only(self):
        for has_a in (False, True):
            with self.subTest(has_a=has_a), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp) / "job.ABCDEF"
                folder.mkdir()
                evidence = [{
                    "endpoint": "example.org",
                    "dns_a": {"classification": "pass", "answers": ["192.0.2.14"]} if has_a
                             else {"classification": "parser_rejected", "answers": []},
                    "dns_aaaa": {"classification": "pass", "answers": ["2001:0DB8:0::0010"]},
                }]
                epoch = endpoint_epoch.create(folder, "example.org", "domain", ["example.org"], evidence)
                loaded = endpoint_epoch.load(folder, ["example.org"])
                self.assertEqual(epoch.epoch_id, loaded.epoch_id)
                binding = loaded.bindings[0]
                self.assertIn("2001:db8::10", binding["addresses"])
                if has_a:
                    self.assertEqual(binding["selected_ip"], "192.0.2.14")
                    self.assertEqual(binding["selected_ipv6"], "2001:db8::10")
                else:
                    self.assertEqual(binding["selected_ip"], "2001:db8::10")
                    self.assertNotIn("selected_ipv6", binding)
                with patch.dict("os.environ", {"STRATEGY_LAB_JOBS_DIR": tmp}):
                    pins, _ = candidate._pinned_endpoints("job.ABCDEF", ["example.org"])
                self.assertEqual(len(pins), 2 if has_a else 1)
                self.assertEqual({p["family"] for p in pins}, {"ipv4", "ipv6"} if has_a else {"ipv6"})
                self.assertEqual(len({p["rule"] for p in pins}), len(pins))

    def test_bad_secondary_ipv6_cannot_change_epoch(self):
        with self.assertRaises(endpoint_epoch.EndpointEpochError):
            endpoint_epoch._validated_bindings([{
                "endpoint": "example.org", "addresses": ["192.0.2.14", "2001:db8::10"],
                "selected_ip": "192.0.2.14", "selected_ipv6": "2001:db8::11",
            }])

    def test_aaaa_only_dns_not_misreported_as_ipv4_failure(self):
        def dns(_host, record):
            return request.DnsResult(
                "pass" if record == "AAAA" else "parser_rejected",
                ["2001:db8::10"] if record == "AAAA" else [], Result())
        with tempfile.TemporaryDirectory() as tmp:
            with (patch.object(request, "dns_request", side_effect=dns),
                  patch.object(request, "curl_request", return_value=Result()) as curl,
                  patch.object(request, "chrome_https_evidence", return_value={"accessible": True}),
                  patch.object(request, "chrome_certificate_error", return_value=False),
                  patch.object(request, "combined_log", return_value="tls")):
                public, evidence, failed, _ = probe._domain_endpoint("example.org", 1, Path(tmp), True)
            self.assertFalse(failed)
            self.assertEqual(public["status"], "PASS")
            self.assertEqual(public["ipv4"]["status"], "SKIPPED")
            self.assertEqual(public["ipv6"]["status"], "PASS")
            self.assertEqual(len(curl.call_args_list), 1)
            self.assertEqual(curl.call_args.kwargs["family"], "ipv6")
            self.assertEqual(curl.call_args.kwargs["bound_ip"], "2001:db8::10")
            self.assertEqual(evidence["dns_a"]["answers"], [])

    def test_mixed_family_baseline_stays_searchable_when_one_family_blocked(self):
        with (patch.object(request, "chrome_https_evidence",
                           side_effect=[{"accessible": False}, {"accessible": True}]),
              patch.object(request, "combined_log", return_value="tls"),
              patch.object(request, "chrome_certificate_error", return_value=False)):
            public = probe._domain_public("example.org", Result(), Result(),
                                          "192.0.2.14", "2001:db8::10")
        self.assertEqual(public["status"], "FAIL")
        self.assertEqual(public["ipv4"]["status"], "FAIL")
        self.assertEqual(public["ipv6"]["status"], "PASS")

    def test_ipv6_candidate_requires_pinned_remote_and_ipfw_growth(self):
        binding = {"endpoint": "example.org", "selected_ip": "2001:db8::10", "rule": 19100}
        with (patch.object(candidate, "_counter", side_effect=[(0, 0), (1, 48)]),
              patch.object(request, "curl_request", return_value=Result()) as run,
              patch.object(request, "chrome_https_evidence", return_value={"accessible": True})):
            result = ip_target_support._candidate_probe(binding)
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["endpoint_match"])
        self.assertTrue(result["firewall"]["intercepted"])
        self.assertEqual(run.call_args.kwargs["family"], "ipv6")
        self.assertEqual(run.call_args.kwargs["bound_ip"], "2001:db8::10")
        with (patch.object(candidate, "_counter", side_effect=[(0, 0), (0, 0)]),
              patch.object(request, "curl_request", return_value=Result()),
              patch.object(request, "chrome_https_evidence", return_value={"accessible": True})):
            denied = ip_target_support._candidate_probe(binding)
        self.assertEqual(denied["status"], "FAIL")
        self.assertFalse(denied["firewall"]["intercepted"])

    def test_ipv6_quic_does_not_use_ipv4_only_proof(self):
        binding = {"endpoint": "example.org", "selected_ip": "2001:db8::10", "rule": 19100}
        spec = candidate.ProtocolSpec("quic", "udp", 443, "quic")
        with (patch.object(candidate, "_counter", side_effect=[(0, 0), (0, 0)]),
              patch.object(request, "chrome_quic_evidence") as proof):
            result = ip_target_support._candidate_probe(binding, spec)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["transport"], "quic-ipv6")
        self.assertEqual(result["reachability"]["reason"], "ipv6_quic_unavailable")
        proof.assert_not_called()

    def test_extended_stage80_skips_aaaa_only_and_ipv6_literal_quic(self):
        # This is the real Stage-80 entrypoint, not the candidate-only guard.
        # In particular it must never call request.quic_target_request,
        # whose address grammar and proof accept IPv4 only.
        for endpoint in ("example.org", "2001:db8::10"):
            with self.subTest(endpoint=endpoint), tempfile.TemporaryDirectory() as tmp:
                endpoints = Path(tmp) / "endpoints.txt"
                endpoints.write_text(endpoint + "\n", encoding="utf-8")
                output = Path(tmp) / "quic.json"
                epoch = SimpleNamespace(
                    epoch_id="se1-test",
                    bindings=({"endpoint": endpoint, "selected_ip": "2001:db8::10"},),
                )
                with (patch.object(extended, "_search_epoch", return_value=epoch),
                      patch.object(extended.search, "_cancel_requested", return_value=False),
                      patch.object(request, "quic_target_request") as request_quic,
                      patch.object(request, "chrome_quic_evidence") as proof_quic):
                    self.assertEqual(
                        extended.quic("job.ABCDEF", str(endpoints), str(Path(tmp) / "network"), str(output)),
                        extended.EX_OK,
                    )
                result = json.loads(output.read_text(encoding="utf-8"))
                self.assertEqual(result["status"], "skipped")
                self.assertEqual(result["reason"], "ipv6_quic_unavailable")
                self.assertEqual(result["direct"], [])
                self.assertEqual(result["tested"], [])
                request_quic.assert_not_called()
                proof_quic.assert_not_called()

    def test_extended_stage80_mixed_aaaa_keeps_supported_ipv4_quic(self):
        with tempfile.TemporaryDirectory() as tmp:
            endpoints = Path(tmp) / "endpoints.txt"
            endpoints.write_text("example.org\n", encoding="utf-8")
            output = Path(tmp) / "quic.json"
            epoch = SimpleNamespace(
                epoch_id="se1-test",
                bindings=({
                    "endpoint": "example.org",
                    "selected_ip": "192.0.2.14",
                    "selected_ipv6": "2001:db8::10",
                },),
            )
            with (patch.object(extended, "_search_epoch", return_value=epoch),
                  patch.object(extended.search, "_cancel_requested", return_value=False),
                  patch.object(request, "quic_target_request", return_value=Result()) as request_quic,
                  patch.object(request, "chrome_quic_evidence", return_value={"accessible": True}) as proof_quic):
                self.assertEqual(
                    extended.quic("job.ABCDEF", str(endpoints), str(Path(tmp) / "network"), str(output)),
                    extended.EX_OK,
                )
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "direct_accessible")
            self.assertEqual(result["direct"][0]["selected_ip"], "192.0.2.14")
            request_quic.assert_called_once_with("example.org", "192.0.2.14")
            proof_quic.assert_called_once()

    def test_fixed_ipv6_ip_baseline_preserves_host(self):
        with tempfile.TemporaryDirectory() as tmp:
            with (patch.object(request, "curl_request", return_value=Result()) as curl,
                  patch.object(request, "chrome_https_evidence", return_value={"accessible": True}),
                  patch.object(request, "combined_log", return_value="tls")):
                before = ip_target_support._IP_BASELINE_TARGET
                try:
                    ip_target_support._IP_BASELINE_TARGET = "2001:db8::10"
                    public, evidence = ip_target_support._ip_endpoint("service.example", 1, Path(tmp))
                finally:
                    ip_target_support._IP_BASELINE_TARGET = before
            self.assertEqual(public["status"], "PASS")
            self.assertEqual(public["transport"], "https-ipv6")
            self.assertEqual(evidence["destination_ip"], "2001:db8::10")
            self.assertEqual(curl.call_args.kwargs["family"], "ipv6")
            self.assertEqual(curl.call_args.kwargs["bound_ip"], "2001:db8::10")

    def test_gui_and_native_ipv6_optin_guard(self):
        controller = (ROOT / "src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/StrategyLabController.php").read_text()
        launch = (PKG / "strategy_lab/launch.sh").read_text()
        target = (PKG / "strategy_lab/target.sh").read_text()
        self.assertIn("FILTER_VALIDATE_IP, FILTER_FLAG_IPV6", controller)
        self.assertIn("Для проверки IPv6-адреса включите галочку IPv6.", controller)
        self.assertIn("Enable IPv6 to test an IPv6 address.", controller)
        self.assertIn('request canonical-ipv6 "$1"', target)
        self.assertIn('usage_error "enable IPv6 for an IPv6 literal target"', launch)

if __name__ == "__main__":
    unittest.main(verbosity=2)
