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

sys.path.insert(0, str(BACKEND))
import auto_detect_origin_map as origin
import auto_detect_owner as owner


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
        (self.static / "ipset" / "auto-domains.txt").write_text("")
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
        self.assertEqual(len(candidates), 3)  # explicit-only auto, no implicit shared HOSTLIST
        self.assertTrue(all(r["hostlist"] is None for r in candidates))
        self.assertTrue(any(r["status"] == "excluded-ipset" for r in candidates))


    def test_p2f_observer_plan_is_trailing_but_not_authorized(self):
        mapped, args = self.build("--filter-tcp=443\n<HOSTLIST:youtube>\n--lua-desync=fake\n")
        original = args.read_bytes()
        source = self.check_nonactivating(mapped, args)
        planned, proposed = origin.plan_trailing_observer(
            source, original, owner_id=self.work.name,
            owner_candidate_sha256="c" * 64,
            raw_path="/var/db/zapret2-auto-detect/inbox.txt",
            debug_path="/var/db/zapret2-auto-detect/debug.log",
            tcp_ports="443",
        )
        self.assertEqual(args.read_bytes(), original)
        self.assertEqual(source["evidence"], origin.NONACTIVATING)
        self.assertEqual(proposed["evidence"], "P2F_OFFLINE_PLAN_ONLY")
        self.assertEqual(proposed["observer_native_number"], 2)
        self.assertEqual(proposed["profiles"][0]["status"], "known-hostlist")
        self.assertEqual(proposed["profiles"][0]["hostlist"], "youtube")
        self.assertEqual(proposed["profiles"][-1],
                         {"native_number": 2, "status": "observer", "hostlist": None})
        self.assertTrue(planned.endswith(
            b"--new\n--filter-tcp=443\n--filter-l7=http,tls\n"
            b"--hostlist-auto=/var/db/zapret2-auto-detect/inbox.txt\n"
            b"--hostlist-auto-fail-threshold=1\n"
            b"--hostlist-auto-retrans-reset=0\n"))
        self.assertEqual(planned.count(b"--hostlist-auto-debug="), 1)
        self.assertNotIn(b"--hostlist-auto=", original)
        self.assertFalse((self.release / owner.MAP_NAME).exists())
        # A structural preview must never be mistaken for running FD9 proof.
        with self.assertRaises(owner.GenerationRefused):
            owner._valid_map(json.dumps(proposed).encode("utf-8"),
                             {"id": self.work.name, "candidate": "c" * 64},
                             planned)

    def test_p2f_voice_mixed_origin_never_promoted_to_known(self):
        mapped, args = self.build(
            "--filter-tcp=443\n<HOSTLIST:user>\n<IPSET:telegram>\n--lua-desync=fake\n",
            voice_on=True,
        )
        source = self.check_nonactivating(mapped, args)
        planned, proposed = origin.plan_trailing_observer(
            source, args.read_bytes(), owner_id=self.work.name,
            owner_candidate_sha256="c" * 64,
            raw_path="/var/db/zapret2-auto-detect/inbox.txt",
            debug_path="/var/db/zapret2-auto-detect/debug.log",
            tcp_ports="443",
        )
        self.assertEqual(proposed["profiles"][0]["status"], "excluded-voice")
        self.assertTrue(all(
            p["status"] == "excluded-ipset" and p["hostlist"] is None
            for p in proposed["profiles"][1:-2]
        ))
        self.assertTrue(planned.endswith(b"--hostlist-auto-retrans-reset=0\n"))
        source["profiles"][1]["status"] = "known-hostlist"
        source["profiles"][1]["hostlist"] = "user"
        source["profiles"][1]["selector"] = "<HOSTLIST:user>"
        with self.assertRaises(origin.AttributionError):
            origin.plan_trailing_observer(
                source, args.read_bytes(), owner_id=self.work.name,
                owner_candidate_sha256="c" * 64,
                raw_path="/var/db/zapret2-auto-detect/inbox.txt",
                debug_path="/var/db/zapret2-auto-detect/debug.log",
                tcp_ports="443",
            )



    def test_p2f_original_fd9_preflight_is_read_only_and_binds_candidate(self):
        mapped, args = self.build(
            "--filter-tcp=443\n<HOSTLIST:youtube>\n--lua-desync=fake\n")
        (self.work / "plan.json").write_text(json.dumps({
            "page": "strategies", "candidate": {"general": {"enabled": "1"}},
            "changed_fields": [], "dependencies": "a" * 64,
        }))
        original = args.read_bytes()
        source = mapped.read_bytes()
        digest = "b" * 64  # Supplied by the original PHP native preflight in production.
        proof = origin.preflight_original_observer(self.work, digest)
        self.assertEqual(proof["generation"], self.work.name)
        self.assertEqual(proof["native_candidate_sha256"], digest)
        self.assertEqual(proof["observer_native_number"], 2)
        self.assertEqual(proof["evidence"],
                         "P2F_ORIGINAL_FD9_PREFLIGHT_NONACTIVATING")
        self.assertNotEqual(proof["proposed_args_sha256"],
                            proof["original_args_sha256"])
        self.assertEqual(original, args.read_bytes())
        self.assertEqual(source, mapped.read_bytes())
        self.assertFalse((self.release / owner.MAP_NAME).exists())
        self.assertFalse((self.release / "auto-detect-observer.args").exists())
        self.assertFalse((self.work / "auto-detect" / "inbox.txt").exists())
        with self.assertRaises(origin.AttributionError):
            origin.preflight_original_observer(self.work, "invalid")
        self.assertEqual(original, args.read_bytes())

    def test_p2f_preflight_refuses_stale_or_symlinked_plan_and_port_overlap(self):
        mapped, args = self.build(
            "--filter-tcp=443-445\n<HOSTLIST:user>\n--lua-desync=fake\n")
        plan = self.work / "plan.json"
        plan.write_text(json.dumps({
            "page": "strategies", "candidate": {"general": {"enabled": "1"}},
            "changed_fields": [], "dependencies": "a" * 64,
        }))
        source = json.loads(mapped.read_text())
        proposed, _ = origin.plan_trailing_observer(
            source, args.read_bytes(), owner_id=self.work.name,
            owner_candidate_sha256="b" * 64,
            raw_path="/var/db/zapret2-auto-detect/inbox.txt",
            debug_path="/var/db/zapret2-auto-detect/debug.log",
            tcp_ports="443-445",
        )
        self.assertIn(b"--filter-tcp=443-445", proposed)
        self.assertEqual(origin.preflight_original_observer(
            self.work, "b" * 64)["observer_native_number"], 2)
        for invalid in ("443-445,444", "445-443", "0-443", "443-65536",
                        "443-444,0443", "443,,444"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(origin.AttributionError):
                    origin.plan_trailing_observer(
                        source, args.read_bytes(), owner_id=self.work.name,
                        owner_candidate_sha256="b" * 64,
                        raw_path="/var/db/zapret2-auto-detect/inbox.txt",
                        debug_path="/var/db/zapret2-auto-detect/debug.log",
                        tcp_ports=invalid,
                    )
        old = args.read_bytes()
        args.write_bytes(old + b"--new\n")
        with self.assertRaises(origin.AttributionError):
            origin.preflight_original_observer(self.work, "b" * 64)
        args.write_bytes(old)
        plan.rename(self.work / "plan-original.json")
        plan.symlink_to(self.work / "plan-original.json")
        with self.assertRaises(origin.AttributionError):
            origin.preflight_original_observer(self.work, "b" * 64)
        self.assertFalse((self.release / owner.MAP_NAME).exists())

    def test_p2h_original_fd9_sealed_preview_is_inert_and_generation_bound(self):
        mapped, args = self.build(
            "--filter-tcp=443\n<HOSTLIST:youtube>\n--lua-desync=fake\n",
            voice_on=True)
        source = self.check_nonactivating(mapped, args)
        original = args.read_bytes()
        self.assertEqual(source["profiles"][0]["status"], "excluded-voice")
        (self.work / "plan.json").write_text(json.dumps({
            "page": "strategies", "candidate": {"general": {"enabled": "1"}},
            "changed_fields": [], "dependencies": "a" * 64,
        }))
        digest = "b" * 64
        preview = origin.stage_original_preview(self.work, digest)
        self.assertEqual(preview["evidence"],
                         "P2H_ORIGINAL_FD9_SEALED_PREVIEW_NONACTIVATING")
        self.assertFalse(preview["activation_authorized"])
        self.assertEqual(preview["owner_candidate_sha256"], digest)
        self.assertEqual(preview["generation"], self.work.name)
        self.assertEqual(args.read_bytes(), original)
        self.assertEqual(mapped.read_bytes(), json.dumps(source, sort_keys=True,
                         separators=(",", ":")).encode() + b"\n")
        proposed = (self.release / "auto-detect-observer-preview.args").read_bytes()
        self.assertNotEqual(proposed, original)
        self.assertIn(b"--hostlist-auto=/var/db/zapret2-auto-detect/inbox.txt", proposed)
        self.assertFalse((self.release / owner.MAP_NAME).exists())
        self.assertFalse((self.release / "dvtws.original.args").exists())
        self.assertEqual(origin.verify_original_preview(self.work, digest),
                         preview)
        preview_map = (self.release / "auto-detect-observer-preview.json")
        with self.assertRaises(owner.GenerationRefused):
            owner._valid_map(preview_map.read_bytes(),
                             {"id": self.work.name, "candidate": digest}, proposed)
        with self.assertRaises(origin.AttributionError):
            origin.stage_original_preview(self.work, digest)
        with self.assertRaises(origin.AttributionError):
            origin.verify_original_preview(self.work, "c" * 64)
        proposed_path = self.release / "auto-detect-observer-preview.args"
        proposed_path.write_bytes(proposed + b"--new\n")
        with self.assertRaises(origin.AttributionError):
            origin.verify_original_preview(self.work, digest)
        proposed_path.write_bytes(proposed)
        preview_map.write_text(preview_map.read_text().replace(
            "P2H_ORIGINAL_FD9_SEALED_PREVIEW_NONACTIVATING",
            "ORIGINAL_SHARED_GENERATOR_CAPTURE"))
        with self.assertRaises(origin.AttributionError):
            origin.verify_original_preview(self.work, digest)
        self.assertEqual(args.read_bytes(), original)

    def test_p2h_original_fd9_preview_before_seal_and_verify_before_kernel(self):
        service = (BACKEND.parent / "zapret_service.sh").read_text()
        begin = service.index("shared_apply_prepare_service()\n")
        end = service.index("extra_resources_native_previous_owner_service()\n", begin)
        body = service[begin:end]
        self.assertLess(body.index("orchestrator_build_release"),
                        body.index("shared_apply_native_config preflight"))
        self.assertLess(body.index('auto_detect_origin_map.py"'),
                        body.index("shared_apply_bundle_service seal"))
        self.assertIn('preview "$_shared_work" "$_shared_auto_digest"', body)
        begin = service.index("shared_apply_execute_service()\n")
        end = service.index("shared_apply_wan_save_service()\n", begin)
        applied = service[begin:end]
        self.assertLess(applied.index("shared_apply_native_config preflight"),
                        applied.index('auto_detect_origin_map.py" verify-preview'))
        self.assertLess(applied.index('auto_detect_origin_map.py" verify-preview'),
                        applied.index('shared_apply_record_service prepared'))
        self.assertLess(applied.index('auto_detect_origin_map.py" verify-preview'),
                        applied.index('apply_runtime_probe "$_shared_apply_root/release"'))
        self.assertIn("preflight-rejected=observer-generation", applied)
        # P2h remains physically NONACTIVATING: only the source-only preview
        # is emitted at build time. The new original-FD9 epoch completion is
        # deliberately reached only after the terminal committed owner, not
        # while compiling a candidate or before runtime preflight.
        self.assertNotIn("auto-detect-generation.json", body)
        self.assertIn('auto-detect-generation.json" ]; then', applied)
        self.assertLess(applied.index('shared_apply_record_service committed'),
                        applied.index('finish-epoch "$_shared_apply_id"'))
        self.assertLess(applied.index('apply_runtime_probe "$_shared_apply_root/release"'),
                        applied.index('finish-epoch "$_shared_apply_id"'))

    def test_p2f_fd9_hook_runs_after_php_preflight_and_before_activation(self):
        service = (BACKEND.parent / "zapret_service.sh").read_text()
        begin = service.index("shared_apply_execute_service()\n")
        end = service.index("shared_apply_wan_save_service()\n", begin)
        body = service[begin:end]
        self.assertLess(body.index('shared_apply_native_config preflight'),
                        body.index('auto_detect_origin_map.py" preflight'))
        self.assertLess(body.index('auto_detect_origin_map.py" preflight'),
                        body.index('apply_runtime_probe "$_shared_apply_root/release"'))
        self.assertLess(body.index('auto_detect_origin_map.py" preflight'),
                        body.index('shared_apply_record_service prepared'))
        self.assertIn('"$_shared_apply_mode" = 1', body)
        self.assertIn('"$_shared_apply_candidate" >/dev/null 2>&1 || :', body)



if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    if result.wasSuccessful():
        print(MARKER + "=PASS_ORIGINAL_BUILD_NONACTIVATING", flush=True)
    raise SystemExit(0 if result.wasSuccessful() else 1)
