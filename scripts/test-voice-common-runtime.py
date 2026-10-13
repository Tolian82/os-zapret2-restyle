#!/usr/bin/env python3
"""Full common release build on private inputs; no kernel or live Config calls."""
from pathlib import Path
import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
ACTIVE = "/usr/local/etc/zapret2/runtime-v2"
SERVICES = ("telegram", "discord", "x", "sip", "custom")
STUN = "--filter-udp=*\n--filter-l7=stun\n--payload=stun"
ORDINARY = "--filter-tcp=443\n--filter-l7=tls\n--new\n--filter-udp=596-599\n<IPSET:telegram>\n--filter-l7=unknown\n--payload=unknown"


def build(tmp, enabled, *, bad_args=False, wan="WAN", global_enabled=True, engine=None):
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
        ET.SubElement(entry, "args").text = ("--new" if bad_args and name in enabled else STUN)
        ipset = f"198.51.100.{i + 1}"
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
    (tools / "python3.13").symlink_to(sys.executable)
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
                self.assertEqual("596-599", (release / "udp-ports.txt").read_text().strip())
                self.assertEqual("443", (release / "tcp-ports.txt").read_text().strip())
                self.assertIn("--filter-l7=unknown\n--payload=unknown", traffic)
                self.assertNotIn("telegram-voice-poc", traffic)
                self.assertFalse((release / "voice-native-candidate").exists())
                for name in enabled:
                    self.assertIn("--name=voice-" + name, args)
                    row = next(r for r in plan["capture"]["voice"] if r["service"] == name)
                    self.assertEqual("table(zapret2_voice_" + name + ")", row["argv"][6])

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
