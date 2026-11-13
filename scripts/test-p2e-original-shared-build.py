#!/usr/bin/env python3
"""#1052 P2e: invoke the ACTUAL original shared release orchestrator, source-only.

Disposable build on the test runner; no FD9, process launch, IPFW, Config save,
cron or appliance mutation. Unlike P0's constructed pipeline witness, this
calls orchestrator_build_release() with existing canonical shell/Python modules.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
import uuid
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
MODS = ("common", "config", "parser", "registry", "storage", "targets",
        "target_mode", "profile_normalizer", "profile_pipeline", "exclude",
        "blobs", "ports", "generator", "validator", "stage", "orchestrator")
MARKER = "P2E_ORIGINAL_SHARED_GENERATOR_MAP"


def write_xml(dest: Path, *, voice_on: bool) -> None:
    root = ET.Element("opnsense")
    model = ET.SubElement(ET.SubElement(root, "OPNsense"), "Zapret")
    general = ET.SubElement(model, "general")
    ET.SubElement(general, "waninterface").text = "lo0"
    voice = ET.SubElement(model, "voice")
    ET.SubElement(voice, "waninterface").text = "lo0"
    telegram = ET.SubElement(voice, "telegram")
    ET.SubElement(telegram, "enabled").text = "1" if voice_on else "0"
    ET.SubElement(telegram, "args").text = (
        "--filter-udp=3478\n--filter-l7=stun\n--payload=stun\n"
        "--lua-desync=fake:blob=0x00000000000000000000000000000000:repeats=2"
    ) if voice_on else ""
    hostlist = ET.SubElement(model, "hostlist")
    ET.SubElement(hostlist, "telegramips").text = "91.108.13.10"
    ET.SubElement(hostlist, "discordips").text = "198.51.100.0/24"
    ET.ElementTree(root).write(dest, encoding="utf-8")


class OriginalSharedGeneration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="zapret-p2e-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.work = self.root / uuid.uuid4().hex
        self.work.mkdir(mode=0o700)
        self.release = self.work / "release"
        self.static = self.root / "static"
        # The genuine Voice compiler correctly refuses arbitrary active
        # roots. Use its canonical *reference*, not a disposable fake path;
        # this read-only build never creates or touches that live directory.
        self.active = Path("/usr/local/etc/zapret2/runtime-v2")
        for sub in ("lua", "files/fake", "ipset"):
            (self.static / sub).mkdir(parents=True, exist_ok=True)
        for lua in ("zapret-lib.lua", "zapret-antidpi.lua", "zapret-auto.lua"):
            (self.static / "lua" / lua).write_text("-- inert original builder fixture\n")
        (self.static / "ipset" / "zapret-hosts-auto.txt").write_text("legacy.test.example\n")
        # Intentionally no engine executable: this is the normal offline
        # shared release builder, not a new or installed dvtws2 instance.

    def build(self, strategy: str, *, voice_on=False, mode="auto"):
        config = self.work / "rendered-zapret.conf"
        values = {
            "ZAPRET_ENABLED": "1", "HOSTLIST_MODE": mode,
            "WAN_IF": "lo0", "DIVERT_PORT": "19899",
            "RULE_BASE": "19000", "RULE_MAX": "19010",
            "TRAFFIC_ARGS": strategy, "YOUTUBE_DOMAINS": "youtube.com",
            "USER_DOMAINS": "example.org", "TELEGRAM_IPS": "91.108.13.10",
            "DISCORD_IPS": "", "X_IPS": "", "SIP_IPS": "", "CUSTOM_IPS": "",
            "EXCLUDE_DOMAINS": "", "EXCLUDE_IPSET": "", "EXTRA_ARGS": "",
        }
        config.write_text("".join(k + "=" + shlex.quote(v) + "\n" for k, v in values.items()))
        write_xml(self.work / "candidate.xml", voice_on=voice_on)
        sources = "\n".join(". " + shlex.quote(str(BACKEND / (name + ".sh"))) for name in MODS)
        # Native configuration is source-only. The fake physical interface
        # avoids requiring any real WAN, Config daemon or packet processing.
        shell = ("""set -eu
BACKEND_DIR=""" + shlex.quote(str(BACKEND)) + """
PYTHON_RUNTIME=""" + shlex.quote(sys.executable) + """
export BACKEND_DIR PYTHON_RUNTIME
""" + sources + """
config_resolve_interface() { printf '%s\\n' lo0; }
orchestrator_build_release "$1" "$2" "$3" "$4" "$5" "$6" shared-candidate "$7"
""")
        job = subprocess.run(
            ["/bin/sh", "-c", shell, "p2e", str(config), str(self.static),
             str(self.active), str(self.work), str(self.release),
             str(self.work / "stage.status"), str(self.work / "candidate.xml")],
            cwd=ROOT, text=True, capture_output=True, timeout=45,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertEqual(job.returncode, 0, "original build failed: " + (
            job.stderr + "\n" + job.stdout)[-5000:])
        return (self.release / "auto-detect-source-map.json", self.release / "dvtws.args")

    def check_nonactivating(self, mapped: Path, args: Path):
        raw = args.read_bytes()
        self.assertNotIn(b"--hostlist-auto=", raw)
        self.assertFalse((self.release / "auto-detect-generation.json").exists())
        self.assertFalse((self.release / "inbox.txt").exists())
        self.assertTrue((self.release / "voice.conf").exists())
        refusal = self.work / "auto-detect-capture" / "refusal.log"
        why = refusal.read_text(errors="replace") if refusal.exists() else "no reason emitted"
        self.assertTrue(mapped.is_file(), "real orchestrator did not emit origin map: " + why[-1800:])
        data = json.loads(mapped.read_bytes())
        self.assertEqual(data["evidence"], "ORIGINAL_SHARED_GENERATOR_CAPTURE_NONACTIVATING")
        self.assertEqual(data["generation"], self.work.name)
        self.assertFalse(data["observer_attached"])
        self.assertFalse(data["activation_authorized"])
        self.assertEqual(data["mode"], "auto")
        self.assertEqual(
            data["final_args_sha256"],
            __import__("hashlib").sha256(raw).hexdigest(),
        )
        return data

    def test_explicit_hostlist_original_common_builder(self):
        mapped, args = self.build("--filter-tcp=443\n<HOSTLIST:youtube>\n--lua-desync=fake\n")
        data = self.check_nonactivating(mapped, args)
        self.assertEqual(
            [(r["status"], r["hostlist"]) for r in data["profiles"] if r["role"] == "strategy"],
            [("known-hostlist", "youtube")],
        )

    def test_mixed_ipset_original_common_builder_with_voice_enabled(self):
        strategy = ("--filter-tcp=443\n<HOSTLIST:user>\n<IPSET:telegram>\n"
                    "--lua-desync=fake\n")
        mapped, args = self.build(strategy, voice_on=True)
        data = self.check_nonactivating(mapped, args)
        self.assertEqual(data["profiles"][0]["status"], "excluded-voice")
        mixed = [r for r in data["profiles"] if r["role"] == "strategy"]
        self.assertEqual(len(mixed), 2)
        self.assertTrue(all(r["source_has_ipset"] and r["status"] == "excluded-ipset"
                            and r["hostlist"] is None for r in mixed))

    def test_auto_defaults_refuse_guessed_hostlist_origin(self):
        mapped, args = self.build("--filter-tcp=443\n--lua-desync=fake\n")
        data = self.check_nonactivating(mapped, args)
        candidates = [r for r in data["profiles"] if r["role"] == "strategy"]
        self.assertEqual(len(candidates), 4)
        self.assertTrue(all(r["hostlist"] is None for r in candidates))
        self.assertTrue(any(r["status"] == "excluded-ipset" for r in candidates))


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    if result.wasSuccessful():
        print(MARKER + "=PASS_ORIGINAL_BUILD_NONACTIVATING", flush=True)
    raise SystemExit(0 if result.wasSuccessful() else 1)
