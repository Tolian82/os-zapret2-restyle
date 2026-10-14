#!/usr/bin/env python3
"""Full common release build on private inputs; no kernel or live Config calls."""
from pathlib import Path
import json
import hashlib
import importlib.util
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))
from voice_ipfw_adapter import shared_release_manifest, shared_firewall_action, IPFWAdapterError
from voice_traffic_merge import profile_tokens

spec = importlib.util.spec_from_file_location("firewall_test_fixture", ROOT / "scripts/test-voice-firewall-transaction.py")
firewall_fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(firewall_fixture)
FakeIPFW = firewall_fixture.FakeIPFW
ACTIVE = "/usr/local/etc/zapret2/runtime-v2"
SERVICES = ("telegram", "discord", "x", "sip", "custom")
STUN = "--filter-udp=*\n--filter-l7=stun\n--payload=stun"
ORDINARY = "--filter-tcp=443\n--filter-l7=tls\n--new\n--filter-udp=596-599\n<IPSET:telegram>\n--filter-l7=unknown\n--payload=unknown"


def build(tmp, enabled, *, bad_args=False, wan="WAN", global_enabled=True, engine=None,
          target_offset=0, stun_ports="*"):
    xml = ET.Element("opnsense")
    model = ET.SubElement(ET.SubElement(xml, "OPNsense"), "Zapret")
    general = ET.SubElement(model, "general")
    ET.SubElement(general, "waninterface").text = wan
    voice = ET.SubElement(model, "voice")
    hosts = ET.SubElement(model, "hostlist")
    settings = {"ZAPRET_ENABLED": "1" if global_enabled else "0", "WAN_IF": "WAN",
                "HOSTLIST_MODE": "all", "DIVERT_PORT": "989", "TRAFFIC_ARGS": ORDINARY,
                "YOUTUBE_DOMAINS": "", "USER_DOMAINS": "", "EXCLUDE_DOMAINS": "example.com",
                "EXTRA_ARGS": ""}
    for i, name in enumerate(SERVICES):
        entry = ET.SubElement(voice, name)
        ET.SubElement(entry, "enabled").text = "1" if name in enabled else "0"
        ET.SubElement(entry, "args").text = ("--new" if bad_args and name in enabled else
                                                STUN.replace("--filter-udp=*", "--filter-udp=" + stun_ports))
        ipset = f"198.51.100.{i + 1 + target_offset}"
        ET.SubElement(hosts, name + "ips").text = ipset
        settings[name.upper() + "_IPS"] = ipset
        settings["VOICE_" + name.upper() + "_REQUESTED"] = "1" if name in enabled else "0"
    source = tmp / "config.xml"
    ET.ElementTree(xml).write(source, encoding="utf-8")
    config = tmp / "zapret.conf"
    config.write_text("\n".join(k + "=" + shlex.quote(v) for k, v in settings.items()) + "\n")
    runtime = tmp / "upstream"
    (runtime / "files/fake").mkdir(parents=True)
    (runtime / "lua").mkdir()
    for name in ("zapret-lib.lua", "zapret-antidpi.lua", "zapret-auto.lua"):
        (runtime / "lua" / name).write_text("-- resource fixture\n")
    if engine is not None:
        binary = runtime / "binaries/my/dvtws2"
        binary.parent.mkdir(parents=True)
        binary.write_text("#!/bin/sh\nprintf '%s\\n' \"$@\" > " + shlex.quote(str(tmp / "engine-argv")) +
                          "\nexit " + ("0" if engine == "accept" else "7") + "\n")
        binary.chmod(0o755)
    work = tmp / "work"
    work.mkdir()
    # Repository builds can run under the local Python; native CI uses 3.13.
    tools = tmp / "tools"
    tools.mkdir()
    # pkg python313 does not promise a generic python3 executable on FreeBSD.
    # Existing strict IPSET normalization calls that name; expose both names
    # to the same real interpreter in this private test environment.
    for name in ("python3", "python3.13"):
        (tools / name).symlink_to(sys.executable)
    marker = tmp / "old-marker"
    marker.write_text("1\n")
    old_config = source.read_bytes()
    env = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ["PATH"])
    script = r'''
set -eu
BACKEND_DIR="$1"
for module in common config parser registry storage targets telegram_voice target_mode \
    profile_normalizer profile_pipeline exclude blobs ports generator validator stage orchestrator; do
    . "$BACKEND_DIR/$module.sh"
done
config_resolve_interface() { [ "$1" = WAN ] || return 1; printf 'vtnet1\n'; }
TELEGRAM_VOICE_MARKER_FILE="$7"
orchestrator_build_release "$2" "$3" "$4" "$5" "$6" "$5/stages" shared-candidate "$8"
'''
    result = subprocess.run(["/bin/sh", "-c", script, "common-runtime-test", str(BACKEND),
                             str(config), str(runtime), ACTIVE, str(work), str(tmp / "release"),
                             str(marker), str(source)], env=env, capture_output=True, text=True, timeout=30)
    assert source.read_bytes() == old_config
    assert marker.read_text() == "1\n"
    return result, tmp / "release"


class CommonRuntimeTests(unittest.TestCase):
    def test_shared_firewall_full_cycle_and_precommit_runtime_failure_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifests = []
            for index, (enabled, offset) in enumerate(((SERVICES, 0), (SERVICES, 10), ((), 0))):
                path = root / str(index)
                path.mkdir()
                result, release = build(path, enabled, target_offset=offset)
                self.assertEqual(0, result.returncode, result.stderr)
                manifests.append(shared_release_manifest(release))
            first, updated, off = manifests
            empty = {"rule_base": 19000, "rule_max": 19010, "rules": {}, "tables": {}}
            adapter = FakeIPFW({18500: ["allow", "ip", "from", "any", "to", "any"]})
            shared_firewall_action(adapter, "install", empty, first)
            self.assertEqual(5, len(first["tables"]))
            self.assertEqual(7, len(first["rules"]))
            shared_firewall_action(adapter, "commit", empty, first)
            shared_firewall_action(adapter, "install", first, updated)
            # Simulate launcher/Config failure after successful kernel install.
            shared_firewall_action(adapter, "rollback", first, updated)
            shared_firewall_action(adapter, "verify", empty, first)
            shared_firewall_action(adapter, "install", first, updated)
            shared_firewall_action(adapter, "commit", first, updated)
            # Repeat, all Voice OFF (ordinary retained), then ordinary Stop.
            for previous, desired in ((updated, updated), (updated, off), (off, empty)):
                shared_firewall_action(adapter, "install", previous, desired)
                shared_firewall_action(adapter, "commit", previous, desired)
                shared_firewall_action(adapter, "verify", previous, desired)
            self.assertEqual({}, adapter.tables)
            self.assertEqual({18500: ["allow", "ip", "from", "any", "to", "any"]}, adapter.rules)

    def test_shared_firewall_foreign_objects_refused_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            result, release = build(Path(directory), SERVICES)
            self.assertEqual(0, result.returncode, result.stderr)
            desired = shared_release_manifest(release)
            empty = {"rule_base": 19000, "rule_max": 19010, "rules": {}, "tables": {}}
            for adapter in (FakeIPFW({19000: ["allow", "ip", "from", "any", "to", "any"]}),
                            FakeIPFW(tables={"zapret2_voice_custom": ["8.8.8.8"]})):
                with self.assertRaises(RuntimeError):
                    shared_firewall_action(adapter, "install", empty, desired)
                self.assertEqual([], adapter.ops)

    def test_shared_manifest_rejects_drift_and_cli_requires_original_fd9(self):
        with tempfile.TemporaryDirectory() as directory:
            result, release = build(Path(directory), SERVICES)
            self.assertEqual(0, result.returncode, result.stderr)
            (release / "managed/ipset-custom.txt").write_text("8.8.8.8\n")
            with self.assertRaisesRegex(IPFWAdapterError, "IPSET"):
                shared_release_manifest(release)
            response = subprocess.run([sys.executable, str(BACKEND / "voice_ipfw_adapter.py"),
                                       "shared", "install", "-", str(release)],
                                      capture_output=True, text=True, timeout=15)
            self.assertNotEqual(0, response.returncode)
            self.assertIn("ERROR:", response.stderr)

    def test_all_five_and_each_individual_service_use_main_runtime(self):
        for enabled in (SERVICES, *((s,) for s in SERVICES)):
            with self.subTest(enabled=enabled), tempfile.TemporaryDirectory() as directory:
                result, release = build(Path(directory), enabled)
                self.assertEqual(0, result.returncode, result.stderr)
                traffic = (release / "traffic.conf").read_text()
                args = (release / "dvtws.args").read_text()
                plan = json.loads((release / "voice-plan.json").read_text())
                self.assertEqual(list(enabled), [p["service"] for p in plan["profiles"]])
                self.assertEqual(len(enabled), len(plan["capture"]["voice"]))
                self.assertEqual(1, args.count("--port=989\n"))
                self.assertEqual(len(enabled) + 1, traffic.count("\n--new\n"))
                self.assertTrue(args.endswith("--hostlist-exclude=" + ACTIVE + "/managed/hostlist-exclude.txt\n"))
                # Voice wildcard STUN must NOT broaden ordinary UDP IPFW.
                # Each Voice service instead gets a destination-table rule.
                self.assertEqual("596-599", (release / "udp-ports.txt").read_text().strip())
                self.assertEqual("443", (release / "tcp-ports.txt").read_text().strip())
                manifest = shared_release_manifest(release)
                for name in enabled:
                    rule = next(argv for argv in manifest["rules"].values()
                                if "table(zapret2_voice_" + name + ")" in argv)
                    self.assertEqual("udp", rule[2])
                    self.assertNotIn("*", rule)
                    self.assertEqual(
                        ["198.51.100." + str(SERVICES.index(name) + 1)],
                        manifest["tables"]["zapret2_voice_" + name]
                    )
                self.assertIn("--filter-l7=unknown\n--payload=unknown", traffic)
                self.assertNotIn("telegram-voice-poc", traffic)
                self.assertFalse((release / "voice-native-candidate").exists())
                for name in enabled:
                    self.assertIn("--name=voice-" + name, args)
                    row = next(r for r in plan["capture"]["voice"] if r["service"] == name)
                    self.assertEqual("table(zapret2_voice_" + name + ")", row["argv"][6])

    def test_shared_engine_argv_and_voice_capture_must_match_before_ipfw(self):
        # Exercise the real staged release, not a synthetic kernel manifest.
        # A changed Voice profile may still be syntactically valid, but
        # installing its previously sealed IPFW owner would capture the wrong
        # flow. No kernel operation is allowed in any mismatch case.
        for change in ("traffic", "args", "plan", "identity"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                result, release = build(Path(directory), ("telegram",))
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertTrue(shared_release_manifest(release)["rules"])
                if change == "traffic":
                    traffic = release / "traffic.conf"
                    traffic.write_text(
                        traffic.read_text().replace("--payload=stun",
                                                    "--payload=unknown", 1)
                    )
                elif change == "args":
                    argv = release / "dvtws.args"
                    argv.write_text(
                        argv.read_text().replace("--name=voice-telegram",
                                                  "--name=missing-telegram", 1)
                    )
                elif change == "plan":
                    path = release / "voice-plan.json"
                    plan = json.loads(path.read_text())
                    plan["profiles"][0]["profile_sha256"] = "0" * 64
                    path.write_text(json.dumps(plan))
                elif change == "identity":
                    path = release / "traffic.conf"
                    path.write_text(path.read_text().replace(
                        "--name=voice-telegram", "--name=voice-discord", 1
                    ))
                with self.assertRaisesRegex(IPFWAdapterError,
                                            "common engine|Voice kernel capture"):
                    shared_release_manifest(release)

    def test_common_voice_kernel_capture_matches_real_engine_udp_and_ipsets(self):
        with tempfile.TemporaryDirectory() as directory:
            result, release = build(Path(directory), ("telegram",), stun_ports="3478")
            self.assertEqual(0, result.returncode, result.stderr)
            manifest = shared_release_manifest(release)
            self.assertIn("3478", manifest["rules"][19000])
            self.assertIn("table(zapret2_voice_telegram)", manifest["rules"][19000])
            self.assertEqual("596-599", (release / "udp-ports.txt").read_text().strip())

        for drift in ("coherent-profile-ports", "capture-ports", "saved-targets",
                      "capture-targets"):
            with self.subTest(drift=drift), tempfile.TemporaryDirectory() as directory:
                result, release = build(Path(directory), ("telegram",))
                self.assertEqual(0, result.returncode, result.stderr)
                plan_file = release / "voice-plan.json"
                plan = json.loads(plan_file.read_text())
                if drift == "coherent-profile-ports":
                    # Both engine and declared profile are updated together.
                    # The old capture is unchanged, so _83's hash still
                    # passes; the _84 port-to-capture witness MUST refuse.
                    for name in ("traffic.conf", "dvtws.args"):
                        path = release / name
                        path.write_text(path.read_text().replace(
                            "--filter-udp=*", "--filter-udp=3478", 1
                        ))
                    profile = profile_tokens((release / "traffic.conf").read_text())[0]
                    plan["profiles"][0]["profile_sha256"] = hashlib.sha256(
                        "\n".join(profile).encode("ascii")
                    ).hexdigest()
                    plan["profiles"][0]["ports"] = [[3478, 3478]]
                elif drift == "capture-ports":
                    plan["capture"]["voice"][0]["ports"] = [[3478, 3478]]
                elif drift == "saved-targets":
                    plan["profiles"][0]["targets"] = ["192.0.2.9"]
                else:
                    plan["capture"]["voice"][0]["destinations"] = ["192.0.2.9"]
                plan_file.write_text(json.dumps(plan))
                with self.assertRaisesRegex(IPFWAdapterError,
                                             "engine/IPFW|UDP selector"):
                    shared_release_manifest(release)

    def test_all_off_preserves_resolved_ordinary_and_ignores_old_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            result, release = build(Path(directory), ())
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual((release / "traffic-user.conf").read_bytes(), (release / "traffic.conf").read_bytes())
            self.assertEqual([], json.loads((release / "voice-plan.json").read_text())["profiles"])

    def test_global_off_can_be_validated_without_starting_service(self):
        with tempfile.TemporaryDirectory() as directory:
            result, release = build(Path(directory), SERVICES, global_enabled=False)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue((release / "dvtws.args").is_file())

    def test_invalid_profile_or_mismatched_rendered_wan_is_refused(self):
        for kwargs in ({"bad_args": True}, {"wan": "OPT1"}):
            with self.subTest(kwargs=kwargs), tempfile.TemporaryDirectory() as directory:
                result, release = build(Path(directory), SERVICES, **kwargs)
                self.assertNotEqual(0, result.returncode)
                self.assertFalse((release / "dvtws.args").exists())

    def test_installed_engine_checks_candidate_paths_and_rejection_stops_build(self):
        for engine in ("accept", "reject"):
            with self.subTest(engine=engine), tempfile.TemporaryDirectory() as directory:
                tmp = Path(directory)
                result, release = build(tmp, SERVICES, engine=engine)
                self.assertEqual(engine == "accept", result.returncode == 0, result.stderr)
                argv = (tmp / "engine-argv").read_text().splitlines()
                self.assertEqual("--dry-run", argv[-1])
                self.assertIn("--ipset=" + str(release / "managed/ipset-telegram.txt"), argv)
                self.assertNotIn("--ipset=" + ACTIVE + "/managed/ipset-telegram.txt", argv)


if __name__ == "__main__":
    unittest.main(verbosity=2)
