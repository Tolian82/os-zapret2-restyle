#!/usr/bin/env python3
"""Voice IPFW capture-plan regression without root/kernel access."""
import importlib.util
from pathlib import Path
import tempfile
import json
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"

def load(name):
    spec = importlib.util.spec_from_file_location(name, BACKEND / (name + ".py"))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

compiler = load("voice_profile_compiler")
planner = load("voice_capture_plan")
MANAGED = Path("/usr/local/etc/zapret2/runtime-v2/managed")
BASE_ARGS = "--filter-udp=*\n--filter-l7=stun\n--payload=stun"


def make_candidate(*services):
    state = {
        "strategy_wan": "wan0",
        "voice_wan": "",
        "services": {name: {"enabled": False, "args": "", "ips": ""}
                     for name in compiler.SERVICES},
    }
    for name, args, ips in services:
        state["services"][name] = {"enabled": True, "args": args, "ips": ips}
    return compiler.compile_candidate(state, MANAGED)[1]


def plan(candidate, base=19000, maximum=19010):
    return planner.compile_capture_plan(candidate, base, maximum, 989)


class IpFwCapturePlanTests(unittest.TestCase):
    def test_off_leaves_two_slots_for_existing_strategies(self):
        result = plan(make_candidate())
        self.assertEqual([], result["voice"])
        self.assertEqual(19000, result["ordinary_rule_base"])

    def test_wildcard_is_scoped_to_named_table_not_any(self):
        candidate = make_candidate(("telegram", BASE_ARGS, "91.108.0.0/16"))
        result = plan(candidate)
        rule = result["voice"][0]
        self.assertEqual("zapret2_voice_telegram", rule["table"])
        self.assertEqual("zapret2_voice_telegram_stage", rule["table_stage"])
        self.assertEqual(19000, rule["rule"])
        self.assertEqual(
            ["divert", "989", "udp", "from", "any", "to",
             "table(zapret2_voice_telegram)", "out", "not", "diverted",
             "not", "sockarg", "xmit", "wan0"], rule["argv"])
        self.assertEqual(19001, result["ordinary_rule_base"])
        self.assertNotIn("to any", " ".join(rule["argv"]))

    def test_disjoint_services_and_numeric_scope(self):
        c = make_candidate(
            ("telegram", "--filter-udp=596-599\n--filter-l7=stun\n--payload=stun", "91.108.0.0/16"),
            ("discord", "--filter-udp=1400,5000-5002\n--filter-l7=stun\n--payload=stun", "91.108.0.0/16"),
        )
        result = plan(c)
        self.assertEqual([19000, 19001], [p["rule"] for p in result["voice"]])
        self.assertIn("596-599", result["voice"][0]["argv"])
        self.assertIn("1400,5000-5002", result["voice"][1]["argv"])
        self.assertEqual(19002, result["ordinary_rule_base"])

    def test_many_services_do_not_overrun_owned_rule_range(self):
        c = make_candidate(
            ("telegram", BASE_ARGS, "91.108.0.0/16"),
            ("discord", BASE_ARGS, "203.0.113.0/24"),
            ("x", BASE_ARGS, "198.51.100.0/24"),
            ("sip", BASE_ARGS, "192.0.2.0/25"),
            ("custom", BASE_ARGS, "192.0.2.128/25"),
        )
        result = plan(c)
        self.assertEqual(19005, result["ordinary_rule_base"])
        self.assertEqual([19000,19001,19002,19003,19004],
                         [r["rule"] for r in result["voice"]])
        with self.assertRaisesRegex(planner.CapturePlanError, "not enough plugin-owned"):
            plan(c, 19000, 19005)

    def test_rejects_changed_or_malformed_candidate(self):
        c = make_candidate(("telegram", BASE_ARGS, "91.108.0.0/16"))
        for key,value in [
            ("wan", "-malicious"),
            ("wan", "wan0;rm -rf /"),
        ]:
            broken = json.loads(json.dumps(c))
            broken[key] = value
            with self.subTest(key=key,value=value):
                with self.assertRaises(planner.CapturePlanError):
                    plan(broken)
        for key,value in [
            ("ipset_path", "/tmp/evil.txt"),
            ("ipset_path", "/usr/local/etc/zapret2/runtime-v2/managed/../x"),
            ("ports", [[0,65535]]),
            ("ports", [[596,595]]),
            ("ports", [[True,1234]]),
            ("targets", []),
            ("targets", ["203.0.113.42/24"]),
            ("targets", ["2001:db8::1"]),
            ("target_count", 2),
            ("profile_sha256", "evil"),
        ]:
            broken = json.loads(json.dumps(c))
            broken["profiles"][0][key] = value
            with self.subTest(key=key,value=value):
                with self.assertRaises(planner.CapturePlanError):
                    plan(broken)
        for values in [(0,19010,989),(19001,19000,989),(19000,65535,989),(19000,19010,0)]:
            with self.subTest(values=values):
                with self.assertRaises(planner.CapturePlanError):
                    planner.compile_capture_plan(c,*values)

    def test_rejects_reordered_and_overlapping_profile_scopes(self):
        c = make_candidate(("telegram", BASE_ARGS,"91.108.0.0/16"),
                           ("discord", BASE_ARGS,"203.0.113.0/24"))
        bad = json.loads(json.dumps(c))
        bad["profiles"] = bad["profiles"][::-1]
        with self.assertRaisesRegex(planner.CapturePlanError, "native profile order"):
            plan(bad)
        bad = json.loads(json.dumps(c))
        bad["profiles"][1]["targets"] = ["91.108.4.0/22"]
        bad["profiles"][1]["target_count"] = 1
        with self.assertRaisesRegex(planner.CapturePlanError, "overlapping UDP"):
            plan(bad)

    def test_cli_json_is_declarative_and_never_installs_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src, out = root/"candidate.json", root/"capture.json"
            src.write_text(json.dumps(make_candidate(
                ("telegram", BASE_ARGS, "91.108.0.0/16"))))
            r = subprocess.run([sys.executable, str(BACKEND/"voice_capture_plan.py"),
                                str(src), "19000","19010","989",str(out)],
                               capture_output=True,text=True)
            self.assertEqual(0,r.returncode,r.stderr)
            self.assertEqual(19000,json.loads(out.read_text())["voice"][0]["rule"])
            self.assertNotIn("subprocess", (BACKEND/"voice_capture_plan.py").read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
