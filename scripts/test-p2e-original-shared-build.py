#!/usr/bin/env python3
"""#1052 P2e: invoke the ACTUAL original shared release orchestrator, source-only.

Disposable build on the test runner; no FD9, process launch, IPFW, Config save,
cron or appliance mutation. Unlike P0's constructed pipeline witness, this
calls orchestrator_build_release() with existing canonical shell/Python modules.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
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
import auto_detect_post_drop as post_drop
import auto_detect_storage as producer_storage
from auto_detect_queue import DurableInbox
from auto_detect_fd import OwnerToken
from voice_live_inspect import CHILD_EXEC
from auto_detect_epoch_receipts import EpochReceipts, ReceiptRefused
from auto_detect_original_v2_model import (preview_learning_domains,
                                           V2OriginalConfigRefused)
from domain_policy import PublicSuffixList, plan_auto_additions
from shared_apply_seal import create_seal, SharedBundleError
from unittest.mock import patch


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


    def test_tz6v4_two_tier_preserves_ordinary_first_match(self):
        strategy = (
            "--filter-tcp=443\n--filter-l7=tls\n<HOSTLIST:youtube>\n--lua-desync=fake\n"
            "--new\n--filter-udp=443\n--filter-l7=quic\n<HOSTLIST:youtube>\n"
            "--lua-desync=fake\n--new\n--filter-tcp=443\n"
            "<HOSTLIST:user>\n--lua-desync=fake\n"
        )
        mapped, args = self.build(strategy, voice_on=True)
        source = self.check_nonactivating(mapped, args)
        original = args.read_bytes()
        projected, proposal = origin.plan_learning_tier(
            source, original, owner_id=self.work.name,
            owner_candidate_sha256="d" * 64)
        profiles = proposal["profiles"]
        regular = [p for p in profiles if p["role"] in ("working", "excluded")
                   and p["native_number"] not in (None, 0)]
        learning = [p for p in profiles if p["role"] == "learning"]
        self.assertEqual([p["hostlist"] for p in learning],
                         ["youtube", "youtube", "user"])
        self.assertEqual([p["found_source_id"] for p in learning],
                         ["youtube_found", "youtube_found", "user_found"])
        self.assertEqual([p["native_number"] for p in learning],
                         list(range(len(regular) + 1, len(regular) + 4)))
        self.assertEqual([p["source_profile"] for p in learning],
                         [p["source_profile"] for p in regular
                          if p["hostlist"] in ("youtube", "user")])
        self.assertEqual(projected.count(b"--hostlist-auto="), 3)
        self.assertEqual(projected.count(b"--hostlist-auto-debug="), 1)
        self.assertEqual(len({p["auto_inbox"] for p in learning}), 3)
        # Level-1 original argv is bit-for-bit untouched and precedes level 2.
        self.assertEqual(
            [t for t in projected.split() if not t.startswith(b"--hostlist-auto-debug=")]
            [:len(original.split())], original.split())
        self.assertEqual(args.read_bytes(), original)
        self.assertFalse((self.release / owner.MAP_NAME).exists())
        self.assertEqual(proposal["evidence"], origin.LEARNING_PROPOSAL)
        self.assertIs(proposal["activation_authorized"], False)
        with self.assertRaises(owner.GenerationRefused):
            owner._valid_map(json.dumps(proposal).encode(),
                             {"id": self.work.name, "candidate": "d" * 64},
                             projected)


    def test_tz6v4_learning_map_has_independent_native_proof(self):
        mapped, args = self.build(
            "--filter-tcp=443\n<HOSTLIST:youtube>\n--lua-desync=fake\n"
            "--new\n--filter-tcp=443\n<HOSTLIST:user>\n--lua-desync=fake\n")
        source = self.check_nonactivating(mapped, args)
        original = args.read_bytes()
        projected, proposal = origin.plan_learning_tier(
            source, original, owner_id=self.work.name,
            owner_candidate_sha256="d" * 64)
        owner_ref = {"id": self.work.name, "candidate": "d" * 64}
        encode = lambda record: json.dumps(record, sort_keys=True).encode()
        authorized = owner._valid_learning_proposal(
            encode(proposal), owner_ref, original, projected)
        self.assertEqual(
            [(n, host) for n, host, _ in authorized],
            [(3, "youtube"), (4, "user")])
        self.assertTrue(all(path.startswith("/var/db/zapret2-auto-detect/")
                            for _, _, path in authorized))
        for kind in ("role", "source", "found", "inbox", "number",
                     "args", "ordinary", "debug", "extra"):
            tampered = json.loads(json.dumps(proposal))
            changed_args = projected
            changed_original = original
            learner = next(p for p in tampered["profiles"]
                           if p["role"] == "learning")
            if kind == "role":
                learner["role"] = "working"
            elif kind == "source":
                learner["source_profile"] = self.work.name + ":2"
            elif kind == "found":
                learner["found_source_id"] = "user_found"
            elif kind == "inbox":
                learner["auto_inbox"] = "/var/db/zapret2-auto-detect/inbox.txt"
            elif kind == "number":
                learner["native_number"] = 4
            elif kind == "args":
                changed_args = projected.replace(
                    b"--lua-desync=fake", b"--lua-desync=none", 1)
                tampered["final_args_sha256"] = hashlib.sha256(changed_args).hexdigest()
            elif kind == "ordinary":
                changed_original = original.replace(
                    b"--filter-tcp=443", b"--filter-tcp=80", 1)
                tampered["original_args_sha256"] = hashlib.sha256(changed_original).hexdigest()
            elif kind == "debug":
                changed_args = projected.replace(
                    b"--hostlist-auto-debug=", b"--hostlist-auto-debug-rogue=", 1)
                tampered["final_args_sha256"] = hashlib.sha256(changed_args).hexdigest()
            else:
                tampered["profiles"].append({"role": "observer"})
            with self.subTest(kind=kind), self.assertRaises(owner.GenerationRefused):
                owner._valid_learning_proposal(
                    encode(tampered), owner_ref, changed_original, changed_args)
        # No standalone proposal is ever accepted as an active owner map.
        with self.assertRaises(owner.GenerationRefused):
            owner._valid_map(encode(proposal), owner_ref, projected)

    def test_tz6v4_native_per_profile_append_to_existing_p1(self):
        # User journey, source-only: real shared generator --> proposed
        # native profile and file -> matching debug + physically recorded
        # lines -> ORIGINAL P1 origin-before-PSL routing. NO cursor, ACK,
        # FD9, Config or active hostlist mutation is authorized here.
        mapped, args = self.build(
            "--filter-tcp=443\n<HOSTLIST:youtube>\n--lua-desync=fake\n"
            "--new\n--filter-tcp=443\n<HOSTLIST:user>\n--lua-desync=fake\n")
        source = self.check_nonactivating(mapped, args)
        original = args.read_bytes()
        proposed, proposal = origin.plan_learning_tier(
            source, original, owner_id=self.work.name,
            owner_candidate_sha256="d" * 64)
        owner_ref = {"id": self.work.name, "candidate": "d" * 64}
        payload = json.dumps(proposal, sort_keys=True).encode()
        native = owner._valid_learning_proposal(
            payload, owner_ref, original, proposed)
        self.assertEqual([(n, host) for n, host, _ in native],
                         [(3, "youtube"), (4, "user")])

        yt = "video.example.co.uk"
        user = "cdn.service-example.com"
        first, second = native[0][2], native[1][2]
        rows = {first: (yt + "\n").encode(),
                second: (user + "\n").encode()}
        def debug(number, hostname, path):
            return (
                "2026-11-20 11:00:00 : " + hostname
                + " : profile " + str(number)
                + " (learning) : client 127.0.0.1:1234 : proto tls : adding to "
                + path + "\n"
            ).encode()
        positive_a = debug(3, yt, first)
        positive_b = debug(4, user, second)
        window = (b"native diagnostic not adding\n"
                  + positive_a + positive_b)
        # The bytes supplied here model bounded physical append windows.
        # Real P2 must obtain them from exact protected FD9/P2b-owned inodes.
        observations = preview_learning_domains(
            payload, owner_ref, original, proposed, rows, window)
        self.assertEqual(observations, [
            {"hostname": yt, "hostlist": "youtube"},
            {"hostname": user, "hostlist": "user"},
        ])
        psl_source = (
            b"// ===BEGIN ICANN DOMAINS===\ncom\nuk\nco.uk\n"
            b"// ===END ICANN DOMAINS===\n"
            b"// ===BEGIN PRIVATE DOMAINS===\nblogspot.com\n"
            b"// ===END PRIVATE DOMAINS===\n"
        )
        psl = PublicSuffixList(psl_source,
                               hashlib.sha256(psl_source).hexdigest())
        policy = plan_auto_additions(
            observations,
            {"youtube": "youtube.com\n", "user": "", "auto": ""},
            {"youtube": "", "user": ""},
            global_exclude="", psl=psl)
        self.assertEqual(policy["result"], "ok")
        self.assertEqual(policy["additions"],
                         {"youtube": ["example.co.uk"],
                          "user": ["service-example.com"]})
        self.assertNotIn("auto", policy["additions"])
        self.assertEqual(args.read_bytes(), original)
        self.assertFalse((self.release / owner.MAP_NAME).exists())

        # Upstream logs before appending. A debug-only event must never be
        # enough to write Found or acknowledge an unread native record.
        wrongs = (
            ("debug-before-append", {first: b"", second: rows[second]}, window),
            ("raw-without-debug", rows, positive_a),
            ("cross-profile-number", rows,
             debug(4, yt, first) + positive_b),
            ("foreign-file", rows,
             debug(3, yt, "/tmp/foreign.txt") + positive_b),
            ("wrong-raw-host", {first: b"other.example.co.uk\n",
                                second: rows[second]}, window),
            ("partial-raw", {first: rows[first][:-1],
                             second: rows[second]}, window),
            ("incomplete-debug", rows, window[:-1]),
            ("duplicate-debug", rows, positive_a + positive_a + positive_b),
            ("raw-first-is-not-guessed-known", rows, b""),
        )
        for kind, changes, debug_bytes in wrongs:
            with self.subTest(kind=kind), self.assertRaises(
                    V2OriginalConfigRefused):
                preview_learning_domains(
                    payload, owner_ref, original, proposed,
                    changes, debug_bytes)
        # A tampered proposal still cannot become valid solely because the
        # physical lines and debug window happen to match its invented owner.
        wrong_map = json.loads(json.dumps(proposal))
        next(p for p in wrong_map["profiles"]
             if p["role"] == "learning")["found_source_id"] = "user_found"
        with self.assertRaises(V2OriginalConfigRefused):
            preview_learning_domains(
                json.dumps(wrong_map).encode(), owner_ref, original,
                proposed, rows, window)



    def test_tz6v4_real_generator_promotes_exact_learning_candidate(self):
        """One original common builder -> active schema3 release, no process.

        Unlike the epoch source fixture this test promotes the actual
        generated release using the production function, then verifies it
        independently and seals it under the shared Apply bundle contract.
        """
        mapped, args = self.build(
            "--filter-tcp=443\n--filter-l7=tls\n<HOSTLIST:youtube>\n"
            "--lua-desync=fake\n--new\n--filter-tcp=443\n"
            "<HOSTLIST:user>\n--lua-desync=fake\n", voice_on=True)
        source = self.check_nonactivating(mapped, args)
        original = args.read_bytes()
        candidate = "d" * 64
        (self.work / "plan.json").write_text(json.dumps({
            "page": "strategies", "candidate": {"general": {"enabled": "1"}},
            "changed_fields": [], "dependencies": "a" * 64,
        }))
        preflight = origin.preflight_learning_tier(self.work, candidate)
        self.assertEqual(preflight["evidence"],
                         "TZ6V4_ORIGINAL_FD9_LEARNING_PREFLIGHT_NONACTIVATING")
        self.assertEqual(len(preflight["learning_native_numbers"]), 2)
        promoted = origin.promote_learning_release(self.work, candidate)
        self.assertEqual(promoted["schema"], 3)
        self.assertTrue(promoted["activation_authorized"])
        self.assertEqual(promoted["mode"], "auto")
        self.assertEqual(
            [row["hostlist"] for row in promoted["profiles"]
             if row["role"] == "learning"], ["youtube", "user"])
        self.assertEqual(origin.verify_learning_promotion(self.work, candidate),
                         promoted)
        self.assertEqual((self.release / "dvtws.original.args").read_bytes(),
                         original)
        self.assertNotEqual(args.read_bytes(), original)
        self.assertEqual(
            promoted["final_args_sha256"],
            hashlib.sha256(args.read_bytes()).hexdigest())
        self.assertEqual(
            promoted["original_args_sha256"], hashlib.sha256(original).hexdigest())
        self.assertTrue(args.read_bytes().startswith(original.split(b"--new")[0]
                                                   .split(b"\n", 1)[0]))
        self.assertEqual(
            [row["source_profile"] for row in promoted["profiles"]
             if row["role"] == "learning"],
            [row["source_profile"] for row in promoted["profiles"]
             if row["role"] == "working" and row["found_source_id"]])
        self.assertEqual(
            [row["hostlist"] for row in promoted["profiles"]
             if row["role"] == "working" and row["found_source_id"]],
            ["youtube", "user"])
        self.assertFalse((self.release / "auto-detect-observer-preview.args").exists())
        with self.assertRaises(origin.AttributionError):
            origin.promote_learning_release(self.work, candidate)
        self.assertEqual(origin.verify_learning_promotion(self.work, candidate),
                         promoted)
        (self.work / "plan.json").write_text(json.dumps({
            "page": "strategies", "candidate": {"general": {"enabled": "1"}},
            "changed_fields": [], "dependencies": "a" * 64,
        }))
        create_seal(self.work, owner=os.geteuid())
        from shared_apply_seal import verify_seal
        self.assertIsNotNone(verify_seal(self.work, owner=os.geteuid()))
        self.assertEqual(json.loads((self.release / owner.MAP_NAME).read_bytes()),
                         promoted)
        # No native inbox/epoch/Config/IPFW writes are a promoter side effect.
        self.assertFalse((self.release / "inbox.txt").exists())
        self.assertFalse((self.root / "producer").exists())

    def test_tz6v4_promoted_generation_fails_closed_on_tamper(self):
        mapped, args = self.build(
            "--filter-tcp=443\n<HOSTLIST:youtube>\n--lua-desync=fake\n")
        self.check_nonactivating(mapped, args)
        candidate = "d" * 64
        (self.work / "plan.json").write_text(json.dumps({
            "page": "strategies", "candidate": {"general": {"enabled": "1"}},
            "changed_fields": [], "dependencies": "a" * 64,
        }))
        promoted = origin.promote_learning_release(self.work, candidate)
        self.assertEqual(origin.verify_learning_promotion(self.work, candidate),
                         promoted)
        original_bytes = (self.release / "dvtws.original.args").read_bytes()
        with args.open("ab") as file:
            file.write(b"--new\n--filter-tcp=80\n")
        with self.assertRaises(origin.AttributionError):
            origin.verify_learning_promotion(self.work, candidate)
        self.assertEqual((self.release / "dvtws.original.args").read_bytes(),
                         original_bytes)

    def test_tz6v4_reject_unlearnable_only_source_before_promotion(self):
        mapped, args = self.build(
            "--filter-udp=443\n<IPSET:telegram>\n--lua-desync=fake\n",
            voice_on=True)
        self.check_nonactivating(mapped, args)
        original = args.read_bytes()
        (self.work / "plan.json").write_text(json.dumps({
            "page": "strategies", "candidate": {"general": {"enabled": "1"}},
            "changed_fields": [], "dependencies": "a" * 64,
        }))
        with self.assertRaises(origin.AttributionError):
            origin.promote_learning_release(self.work, "d" * 64)
        self.assertEqual(args.read_bytes(), original)
        self.assertFalse((self.release / owner.MAP_NAME).exists())
        self.assertFalse((self.release / "dvtws.original.args").exists())


    def test_tz6v4_real_promotion_fd9_source_gate_matches_active_copy(self):
        """Real original generator -> sealed candidate -> FD9 source gate.

        Only the original process launcher may later enter this gate
        on a FreeBSD host with the inherited original FD9. This source
        fixture neither starts dvtws2 nor constructs a second owner.
        """
        mapped, args = self.build(
            "--filter-tcp=443\n<HOSTLIST:youtube>\n--lua-desync=fake\n"
            "--new\n--filter-tcp=443\n<HOSTLIST:user>\n--lua-desync=fake\n")
        self.check_nonactivating(mapped, args)
        candidate = "d" * 64
        (self.work / "plan.json").write_text(json.dumps({
            "page": "strategies", "candidate": {"general": {"enabled": "1"}},
            "changed_fields": [], "dependencies": "a" * 64,
        }))
        data_root = self.root / "producer"
        with patch.object(origin, "RAW_PATH", data_root / "inbox.txt"), \
             patch.object(producer_storage, "ROOT", data_root), \
             patch.object(post_drop, "ROOT", data_root), \
             patch("shared_apply_seal.WORK", self.root):
            record = origin.promote_learning_release(self.work, candidate)
            create_seal(self.work, owner=os.geteuid())
            approved = tuple(
                (row["native_number"], row["hostlist"], row["auto_inbox"])
                for row in record["profiles"] if row["role"] == "learning")
            self.assertEqual(
                [row[1] for row in approved], ["youtube", "user"])
            self.assertEqual(
                post_drop._learning_release_sources(self.release),
                (self.work, candidate, approved))
            self.assertFalse(data_root.exists())
            active = self.root / "installed-active"
            shutil.copytree(self.release, active)
            with patch("voice_live_inspect.COMMON_ACTIVE", active):
                self.assertEqual(
                    post_drop._learning_release_sources(active),
                    (self.work, candidate, approved))
                # The owner cannot adopt an edited active source or argv
                # merely because a once-valid candidate remains sealed.
                (active / "dvtws.args").write_bytes(b"--port=989\n")
                with self.assertRaises(post_drop.PostDropRefused):
                    post_drop._learning_release_sources(active)
                self.assertFalse(data_root.exists())
                # A foreign release path is never an authorization.
                with self.assertRaises(post_drop.PostDropRefused):
                    post_drop._learning_release_sources(self.root / "unknown")
                # Restore active exact bytes and verify no new candidate
                # was created behind the original release seal.
                shutil.copy2(self.release / "dvtws.args", active / "dvtws.args")
                self.assertEqual(
                    post_drop._learning_release_sources(active),
                    (self.work, candidate, approved))

    def test_tz6v4_schema3_fd9_verbs_have_exact_shapes(self):
        """Unconnected CLI cannot authorize non-FD9 caller or emit witness."""
        actions = {
            "authorize-learning": 2, "prepare-learning": 2,
            "capture-learning": 2, "seal-learning-epoch": 4,
            "restore-learning": 6, "finish-learning-epoch": 2,
        }
        for action, n in actions.items():
            with self.subTest(action=action):
                self.assertEqual(
                    post_drop.original_fd9_command([action]), 64)
                # Test the non-native guard deterministically without
                # inventing a FreeBSD inherited-FD9 context.
                with patch.object(post_drop.sys, "platform", "linux"):
                    self.assertEqual(
                        post_drop.original_fd9_command(
                            [action] + ["bogus"] * (n - 1)), 64)

    @staticmethod
    def _tz6v4_psl_for_fixtures() -> PublicSuffixList:
        """Hash-verified ICANN+PRIVATE fixture; no runner idna dependency.

        Production P1 still loads the complete pinned PSL and refuses
        if its qualified IDNA2008 provider is absent. This tiny PSL is
        intentionally test-only and covers the example.com/net/org roots.
        """
        raw = (
            b"// ===BEGIN ICANN DOMAINS===\n"
            b"com\nnet\norg\n"
            b"// ===END ICANN DOMAINS===\n"
            b"// ===BEGIN PRIVATE DOMAINS===\n"
            b"blogspot.com\n"
            b"// ===END PRIVATE DOMAINS===\n"
        )
        return PublicSuffixList(raw, hashlib.sha256(raw).hexdigest())

    def test_tz6v4_p1_routes_confirmed_native_sources_to_found(self):
        """Existing P1 PSL and composer, no invented model for known Found."""
        from auto_detect_original_v2_model import preview_learning_p1_effects
        psl = self._tz6v4_psl_for_fixtures()
        manual = {"youtube": "", "user": ""}
        owned = {"youtube": "", "user": ""}
        observations = [
            {"hostname": "video.example.com", "hostlist": "youtube"},
            {"hostname": "mail.example.org", "hostlist": "user"},
        ]
        planned = preview_learning_p1_effects(
            observations, manual, owned, "", "", psl=psl)
        self.assertEqual(planned["effects"], {
            "youtube": {"add": ["example.com"], "remove": []},
            "user": {"add": ["example.org"], "remove": []},
        })
        self.assertEqual(planned["found_after"]["youtube"], b"example.com\n")
        self.assertEqual(planned["found_after"]["user"], b"example.org\n")
        self.assertEqual(planned["managed_after"]["youtube"], b"example.com\n")
        self.assertEqual(planned["managed_after"]["user"], b"example.org\n")
        self.assertEqual(planned["found_after"]["auto"], b"")
        self.assertFalse(planned["commit_authorized"])
        self.assertFalse(planned["cleanup_authorized"])
        self.assertFalse(planned["ack_authorized"])

        # First-match attribution is from the sealed native map, never a
        # hostname guess. Two independently proven sources for the SAME
        # PSL root are ambiguous and belong in the explicit shared Found.
        ambiguity = preview_learning_p1_effects(
            [observations[0],
             {"hostname": "www.example.com", "hostlist": "user"}],
            manual, owned, "", "", psl=psl)
        self.assertEqual(ambiguity["effects"], {
            "auto": {"add": ["example.com"], "remove": []},
        })
        self.assertEqual(ambiguity["found_after"]["auto"],
                         b"example.com\n")
        self.assertEqual(ambiguity["managed_after"]["youtube"], b"")
        self.assertEqual(ambiguity["managed_after"]["user"], b"")

        # Existing auto-owned rows may move to shared, but neither the
        # original manual content nor a negative modifier may be deleted.
        moved = preview_learning_p1_effects(
            [{"hostname": "www.example.com", "hostlist": "user"}],
            manual, {"youtube": "example.com\n", "user": ""}, "", "", psl=psl)
        self.assertEqual(moved["effects"], {
            "youtube": {"add": [], "remove": ["example.com"]},
            "auto": {"add": ["example.com"], "remove": []},
        })
        self.assertEqual(moved["found_after"]["youtube"], b"")
        self.assertEqual(moved["managed_after"]["youtube"], b"")
        excluded = preview_learning_p1_effects(
            observations, {"youtube": "!example.com\n", "user": ""},
            owned, "", "", psl=psl)
        self.assertEqual(excluded["effects"], {
            "user": {"add": ["example.org"], "remove": []},
        })
        self.assertEqual(excluded["managed_after"]["youtube"],
                         b"!example.com\n")
        globally_excluded = preview_learning_p1_effects(
            observations, manual, owned, "", "example.com\n", psl=psl)
        self.assertEqual(globally_excluded["effects"], {
            "user": {"add": ["example.org"], "remove": []},
        })
        repeat = preview_learning_p1_effects(
            observations, manual,
            {"youtube": "example.com\n", "user": "example.org\n"}, "", "", psl=psl)
        self.assertEqual(repeat["effects"], {})
        for bad in (
            [{"hostname": "invalid_host", "hostlist": "youtube"}],
            [{"hostname": "example.com", "hostlist": None}],
            [{"hostname": "example.com", "hostlist": "unmapped"}],
            [{"hostname": "example.com", "hostlist": "youtube",
              "invented": True}],
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(V2OriginalConfigRefused):
                    preview_learning_p1_effects(bad, manual, owned, "", "", psl=psl)

    def test_tz6v4_remaining_new_reaches_original_destination(self):
        """Real files through original generator/P1/WAL; synthetic FD9 only."""
        self.exercise_remaining_new = True
        self.test_tz6v4_sealed_full_n_pretraffic_is_one_original_epoch()

    def test_tz6v4_independent_native_minute_cycles(self):
        """One real native file may grow while every other N stays empty."""
        if sys.platform.startswith("freebsd"):
            self.skipTest("Disposable Config FD is Linux source evidence only")
        self.exercise_independent_cycles = True
        self.test_tz6v4_sealed_full_n_pretraffic_is_one_original_epoch()

    def test_tz6v4_native_cycle_partial_found_managed(self):
        self.native_cycle_case = "partial"
        self.test_tz6v4_independent_native_minute_cycles()

    def test_tz6v4_native_cycle_post_unlink_ack_only(self):
        self.native_cycle_case = "ack"
        self.test_tz6v4_independent_native_minute_cycles()

    def test_tz6v4_native_cycle_late_old_append(self):
        self.native_cycle_case = "old-tail"
        self.test_tz6v4_independent_native_minute_cycles()

    def test_tz6v4_native_cycle_rollover_with_unread(self):
        self.native_cycle_case = "rollover"
        self.test_tz6v4_independent_native_minute_cycles()

    def test_tz6v4_diagnostic_only_highwater_advances_one_original_wal(self):
        """A >2 MiB no-positive debug suffix must not stall eight minutes."""
        self.native_cycle_case = "diagnostic-highwater"
        self.test_tz6v4_independent_native_minute_cycles()

    def test_tz6v4_debug_cut_recovers_after_atomic_replace_crash(self):
        self.native_cycle_case = "debug-cut-crash"
        self.test_tz6v4_independent_native_minute_cycles()

    def test_tz6v4_debug_cut_recovers_fsynced_intent_part(self):
        self.native_cycle_case = "debug-cut-part"
        self.test_tz6v4_independent_native_minute_cycles()

    def test_tz6v4_debug_cut_repeats_after_next_original_ack(self):
        self.native_cycle_case = "debug-cut-repeat"
        self.test_tz6v4_independent_native_minute_cycles()

    def test_tz6v4_debug_cut_never_discards_late_old_inode_append(self):
        self.native_cycle_case = "debug-cut-late-old"
        self.test_tz6v4_independent_native_minute_cycles()

    def test_tz6v4_stopped_owner_original_p1_cas(self):
        self.native_cycle_case = "stopped-cas"
        self.test_tz6v4_independent_native_minute_cycles()

    def test_tz6v4_stopped_owner_refuses_foreign_managed_preimage(self):
        self.native_cycle_case = "stopped-cas-drift"
        self.test_tz6v4_independent_native_minute_cycles()

    def test_tz6v4_debug_cut_replays_late_old_native_positive(self):
        self.native_cycle_case = "debug-cut-late-positive"
        self.test_tz6v4_independent_native_minute_cycles()

    def test_tz6v4_debug_cut_replays_after_rollback_rename_crash(self):
        self.native_cycle_case = "debug-cut-late-positive-rollback-crash"
        self.test_tz6v4_independent_native_minute_cycles()

    def test_tz6v4_debug_cut_preserves_both_inodes_when_new_is_nonempty(self):
        self.native_cycle_case = "debug-cut-late-positive-new-busy"
        self.test_tz6v4_independent_native_minute_cycles()

    def test_tz6v4_malformed_positive_is_not_skipped_as_diagnostic(self):
        self.native_cycle_case = "foreign-positive"
        self.test_tz6v4_independent_native_minute_cycles()

    def _exercise_independent_cycles(self, writer, proof, queue, owned_dir,
                                     native_debug, drained):
        import fcntl
        import auto_detect_original_v2_model as model
        from auto_detect_destination_commit import _target
        from auto_detect_owned_sources import read_owned
        active = self.root / "independent-runtime"
        managed = active / "managed"
        managed.mkdir(mode=0o700, parents=True)
        manual = {"youtube": "youtube.com\n", "user": ""}
        for name in manual:
            path = managed / ("hostlist-" + name + ".txt")
            path.write_text(manual[name])
            path.chmod(0o600)
        youtube = Path(proof.learning[0][2])
        user = Path(proof.learning[1][2])
        user.write_bytes(b"")
        debug = queue.root / "debug.log"
        debug.write_bytes(native_debug(proof.learning[0][0],
                                       "video.example.com", str(youtube)))
        config = self.root / "independent-config.xml"
        config.write_bytes(b"<opnsense/>\n")
        config.chmod(0o600)
        config_fd = os.open(config, os.O_RDWR | os.O_NOFOLLOW)
        fcntl.flock(config_fd, fcntl.LOCK_EX)

        def live_preview(canonical, effects, **kwargs):
            owned = read_owned(owned_dir, owner_uid=os.geteuid())
            shared = _target(writer.targets["auto"], os.geteuid())[0].decode()
            # This injected source-only attester replaces process/argv
            # inspection, not P1, destination CAS, filesystem or cursor ACK.
            from auto_detect_destination_commit import _edit
            from auto_detect_effective_known import compose_known
            after = dict(owned)
            for name, change in effects.items():
                if name in after:
                    after[name] = _edit(after[name].encode(),
                                        change["add"], change["remove"]).decode()
            composed = compose_known(canonical, after)
            files, changed = {}, []
            for name in manual:
                path = managed / ("hostlist-" + name + ".txt")
                before = path.read_bytes()
                image = composed[name].encode()
                files[name] = dict(path=str(path),
                    before_sha256=hashlib.sha256(before).hexdigest(),
                    after_sha256=hashlib.sha256(image).hexdigest())
                if before != image:
                    changed.append(name)
            return dict(owner_schema=3, generation=proof.generation,
                        operation=proof.operation_id, pid=proof.owner.pid,
                        started=proof.owner.started, changed=changed,
                        files=files, commit_authorized=False,
                        ack_authorized=False)

        def run(**kwargs):
            return model.process_original_learning_cycle(
                writer, proof, self.work, config_fd=config_fd,
                config_path=config, owned_root=owned_dir,
                manual_hostlists=manual, global_exclude="",
                attest=lambda: proof, inspect=drained,
                psl=self._tz6v4_psl_for_fixtures(), **kwargs)
        try:
            with patch.object(model, "COMMON_ACTIVE", active), patch.object(
                    model, "preview_live_known_after_readonly", live_preview):
                case = getattr(self, "native_cycle_case", "ordinary")
                root = writer.receipts.root / proof.generation / "cursor-chain-v2"
                if case == "partial":
                    from auto_detect_destination_commit import _replace, DestinationRefused
                    def crash_after_found(path, *args, **kwargs):
                        _replace(path, *args, **kwargs)
                        if path == writer.targets["youtube"]:
                            raise DestinationRefused("injected_after_found_before_managed")
                    with patch("auto_detect_destination_commit._replace", crash_after_found):
                        with self.assertRaises((V2OriginalConfigRefused, DestinationRefused)):
                            run()
                    self.assertEqual(writer.targets["youtube"].read_bytes(), b"example.com\n")
                    self.assertEqual((managed / "hostlist-youtube.txt").read_bytes(), b"youtube.com\n")
                    self.assertEqual(youtube.read_bytes(), b"video.example.com\n")
                    self.assertFalse((root / "00000000" / "ack.json").exists())
                    user.write_bytes(b"mail.example.org\n")
                    with debug.open("ab") as out:
                        out.write(native_debug(proof.learning[1][0], "mail.example.org", str(user)))
                    self.assertTrue(run())
                    self.assertEqual(user.read_bytes(), b"mail.example.org\n")
                    self.assertEqual(writer.targets["user"].read_bytes(), b"")
                    self.assertTrue(run())
                    self.assertEqual(writer.targets["user"].read_bytes(), b"example.org\n")
                    self.assertEqual(queue.segments(), [])
                    self.assertFalse(run())
                    return
                if case == "ack":
                    import auto_detect_epoch_receipts as receipts_module
                    original_write = receipts_module._write_once
                    def crash_after_unlink(folder, name, *args):
                        if folder.name == "progress" and name == f"{proof.learning[0][0]:03d}.json":
                            self.assertEqual(queue.segments(), [])
                            raise OSError("injected_after_unlink_before_cursor_ack")
                        return original_write(folder, name, *args)
                    with patch.object(receipts_module, "_write_once", crash_after_unlink):
                        with self.assertRaises(OSError):
                            run()
                    self.assertEqual(youtube.read_bytes(), b"")
                    self.assertFalse((root / "00000000" / "ack.json").exists())
                    writer.targets["youtube"].write_bytes(b"")
                    (managed / "hostlist-youtube.txt").write_bytes(b"youtube.com\n")
                    self.assertTrue(run())
                    self.assertEqual(writer.targets["youtube"].read_bytes(), b"")
                    self.assertEqual((managed / "hostlist-youtube.txt").read_bytes(), b"youtube.com\n")
                    self.assertTrue((root / "00000000" / "ack.json").exists())
                    self.assertFalse(run())
                    return
                if case == "old-tail":
                    old_fd = os.open(youtube, os.O_WRONLY | os.O_APPEND)
                    physical_rotate = queue._rotate_original_source
                    def append_after_cut(*args, **kwargs):
                        result = physical_rotate(*args, **kwargs)
                        os.write(old_fd, b"www.late-boundary.org\n")
                        with debug.open("ab") as out:
                            out.write(native_debug(proof.learning[0][0], "www.late-boundary.org", str(youtube)))
                        return result
                    try:
                        with patch.object(queue, "_rotate_original_source", append_after_cut):
                            self.assertTrue(run())
                        self.assertEqual(len(queue.segments()), 1)
                        self.assertIn(b"www.late-boundary.org\n", queue.segments()[0].read_bytes())
                        self.assertNotIn(b"late-boundary.org\n", writer.targets["youtube"].read_bytes())
                    finally:
                        os.close(old_fd)
                    self.assertTrue(run())
                    self.assertIn(b"late-boundary.org\n", writer.targets["youtube"].read_bytes())
                    self.assertEqual(queue.segments(), [])
                    self.assertEqual(youtube.read_bytes(), b"")
                    self.assertFalse(run())
                    return
                self.assertTrue(run())
                self.assertEqual(writer.targets["youtube"].read_bytes(),
                                 b"example.com\n")
                self.assertEqual(writer.targets["user"].read_bytes(), b"")
                self.assertEqual((managed / "hostlist-youtube.txt").read_bytes(),
                                 b"youtube.com\nexample.com\n")
                self.assertEqual(youtube.read_bytes(), b"")
                self.assertEqual(queue.segments(), [])
                self.assertFalse(run())
                if case == "foreign-positive":
                    # The first non-native "adding to" must not be treated
                    # as a diagnostic-only source ACK; preserve every byte.
                    with debug.open("ab") as out:
                        out.write(b"native : untrusted.example : adding to /tmp/foreign\n")
                    from auto_detect_cursor_chain import CursorChainRefused
                    with self.assertRaises(CursorChainRefused):
                        run()
                    self.assertEqual(
                        debug.read_bytes()[-len(b"/tmp/foreign\n"):],
                        b"/tmp/foreign\n")
                    self.assertFalse((root / "00000001" / "ack.json").exists())
                    return
                if case in ("diagnostic-highwater", "debug-cut-crash",
                            "debug-cut-repeat", "debug-cut-late-old",
                            "debug-cut-late-positive",
                            "debug-cut-late-positive-rollback-crash",
                            "debug-cut-late-positive-new-busy",
                            "debug-cut-part"):
                    # The original one-PHP/FD9 WAL still commits/ACKs the
                    # unchanged N cursors. All bytes are real on disk and
                    # no worker, engine signal or Config mutation is faked.
                    diagnostic = b"2026-11-21 : native diagnostic without discovery\n"
                    count = (2 * 1024 * 1024) // len(diagnostic) + 2
                    with debug.open("ab") as out:
                        out.write(diagnostic * count)
                    full_size = debug.stat().st_size
                    self.assertGreater(full_size, 2 * 1024 * 1024)
                    self.assertTrue(run())
                    from auto_detect_cursor_chain import CursorChain
                    # This entire source fixture ALREADY holds the
                    # original P2a flock: do not acquire a second one.
                    self.assertTrue(queue._held)
                    tip = CursorChain(writer.receipts, queue).learning_tip(
                        proof, self.work)
                    self.assertEqual(tip["debug"]["offset"], full_size)
                    self.assertEqual(
                        tip["state"][proof.learning[0][0]]["streams"][0]["offset"], 0)
                    self.assertEqual(
                        tip["state"][proof.learning[1][0]]["streams"][0]["offset"], 0)
                    self.assertEqual(writer.targets["user"].read_bytes(), b"")
                    self.assertTrue((root / "00000001" / "ack.json").exists())
                    from auto_detect_cursor_chain import CursorChainRefused
                    from auto_detect_fd import FDState
                    chain = CursorChain(writer.receipts, queue)
                    candidate = chain.learning_debug_highwater_candidate(
                        proof, self.work, attest=lambda: proof, inspect=drained)
                    self.assertIsNotNone(candidate)
                    self.assertEqual(candidate["schema"], 3)
                    self.assertEqual(candidate["debug"]["offset"], full_size)
                    self.assertEqual(candidate["next_sequence"], 2)
                    self.assertTrue(candidate["source_fully_acked"])
                    self.assertTrue(candidate["p2b_drained"])
                    self.assertFalse(candidate["cut_authorized"])
                    self.assertFalse(candidate["ack_authorized"])
                    self.assertEqual(
                        candidate["previous_ack_sha256"],
                        tip["previous_ack_sha256"])
                    with self.assertRaisesRegex(
                            CursorChainRefused, "learning_debug_cut_native_fd_busy"):
                        chain.learning_debug_highwater_candidate(
                            proof, self.work, attest=lambda: proof,
                            inspect=lambda *args, **kwargs: FDState.BUSY)
                    with self.assertRaisesRegex(
                            CursorChainRefused, "learning_debug_cut_original_owner_required"):
                        chain.learning_debug_highwater_candidate(
                            proof, self.work, attest=lambda: None, inspect=drained)
                user.write_bytes(b"mail.example.org\n")
                with debug.open("ab") as out:
                    out.write(native_debug(proof.learning[1][0],
                                           "mail.example.org", str(user)))
                if case in ("diagnostic-highwater", "debug-cut-crash",
                            "debug-cut-repeat", "debug-cut-late-old",
                            "debug-cut-late-positive",
                            "debug-cut-late-positive-rollback-crash",
                            "debug-cut-late-positive-new-busy",
                            "debug-cut-part"):
                    # A newly appended real native hostname makes the
                    # previously qualified candidate obsolete before P1.
                    self.assertIsNone(chain.learning_debug_highwater_candidate(
                        proof, self.work, attest=lambda: proof, inspect=drained))
                if case == "stopped-cas-drift":
                    # STOPPED P1 may not resurrect a GUI-edited managed
                    # image or pretend that an old engine still runs.
                    physical = managed / "hostlist-user.txt"
                    baseline = physical.read_bytes()
                    physical.write_bytes(b"foreign.example\n")
                    with self.assertRaisesRegex(
                            V2OriginalConfigRefused,
                            "learning_stopped_managed_manual_found_drift"):
                        run(stopped=True)
                    self.assertEqual(user.read_bytes(), b"mail.example.org\n")
                    self.assertEqual(writer.targets["user"].read_bytes(), b"")
                    physical.write_bytes(baseline)
                self.assertTrue(run(stopped=case in
                                    ("stopped-cas", "stopped-cas-drift")))
                self.assertEqual(writer.targets["user"].read_bytes(),
                                 b"example.org\n")
                self.assertEqual((managed / "hostlist-user.txt").read_bytes(),
                                 b"example.org\n")
                self.assertEqual(user.read_bytes(), b"")
                if case in ("diagnostic-highwater", "debug-cut-crash",
                            "debug-cut-repeat", "debug-cut-late-old",
                            "debug-cut-late-positive",
                            "debug-cut-late-positive-rollback-crash",
                            "debug-cut-late-positive-new-busy",
                            "debug-cut-part"):
                    # Native User has been committed AFTER the original
                    # highwater candidate became stale. The next original
                    # FD9/P2a cycle can now make a safe physical debug cut.
                    old_inode = debug.stat().st_ino
                    previous_slot = root / "00000002"
                    if case == "debug-cut-part":
                        import auto_detect_cursor_chain as cursors
                        original_link = os.link
                        def interrupted_cut_receipt(source, target, *args, **kwargs):
                            if Path(target).name == cursors.DEBUG_CUT_INTENT:
                                raise OSError("injected_before_debug_intent_link")
                            return original_link(source, target, *args, **kwargs)
                        with patch.object(cursors.os, "link", interrupted_cut_receipt):
                            with self.assertRaises(OSError):
                                run()
                        staged = [p for p in previous_slot.iterdir()
                                  if p.name.endswith(".part")]
                        self.assertEqual(len(staged), 1)
                        self.assertTrue((previous_slot / cursors.DEBUG_CUT_FRESH).exists())
                        self.assertFalse((previous_slot / cursors.DEBUG_CUT_INTENT).exists())
                        self.assertEqual(debug.stat().st_ino, old_inode)
                    if case in ("debug-cut-crash", "debug-cut-late-old",
                                "debug-cut-late-positive",
                                "debug-cut-late-positive-rollback-crash",
                                "debug-cut-late-positive-new-busy"):
                        import auto_detect_cursor_chain as cursors
                        original_replace = os.replace
                        def interrupted_debug_cut(source, target):
                            result = original_replace(source, target)
                            if Path(source).name == cursors.DEBUG_CUT_FRESH:
                                if case in ("debug-cut-late-old",
                                            "debug-cut-late-positive",
                                            "debug-cut-late-positive-rollback-crash",
                                            "debug-cut-late-positive-new-busy"):
                                    # Simulate a native writer whose old FD
                                    # survived os.replace after the P2b scan.
                                    with (previous_slot / cursors.DEBUG_CUT_OLD).open("ab") as fp:
                                        if case == "debug-cut-late-old":
                                            fp.write(b"late-old-native-diagnostic\n")
                                        else:
                                            fp.write(native_debug(
                                                proof.learning[0][0],
                                                "late.example.net", str(youtube)))
                                    if case != "debug-cut-late-old":
                                        youtube.write_bytes(b"late.example.net\n")
                                    if case == "debug-cut-late-positive-new-busy":
                                        with debug.open("ab") as dest:
                                            dest.write(b"new-native-diagnostic\n")
                                raise OSError("injected_after_original_debug_replace")
                            return result
                        with patch.object(cursors.os, "replace", interrupted_debug_cut):
                            with self.assertRaises(OSError):
                                run()
                        self.assertTrue((previous_slot / cursors.DEBUG_CUT_OLD).is_file())
                        self.assertNotEqual(debug.stat().st_ino, old_inode)
                        if case == "debug-cut-late-positive-new-busy":
                            from auto_detect_cursor_chain import CursorChainRefused
                            with self.assertRaisesRegex(
                                    CursorChainRefused, "learning_debug_cut_positive_new_not_empty"):
                                run()
                            self.assertTrue((previous_slot / cursors.DEBUG_CUT_OLD).is_file())
                            self.assertFalse((previous_slot / cursors.DEBUG_CUT_ROLLBACK).exists())
                            self.assertIn(b"new-native-diagnostic\n", debug.read_bytes())
                            self.assertEqual(youtube.read_bytes(), b"late.example.net\n")
                            return
                        if case in ("debug-cut-late-positive",
                                    "debug-cut-late-positive-rollback-crash"):
                            if case == "debug-cut-late-positive-rollback-crash":
                                original_rename = os.replace
                                def interrupted_rollback(source, target):
                                    result = original_rename(source, target)
                                    if Path(source).name == cursors.DEBUG_CUT_OLD:
                                        raise OSError("injected_after_positive_rollback_rename")
                                    return result
                                with patch.object(cursors.os, "replace", interrupted_rollback):
                                    with self.assertRaises(OSError):
                                        run()
                                self.assertEqual(debug.stat().st_ino, old_inode)
                                self.assertTrue(
                                    (previous_slot / cursors.DEBUG_CUT_ROLLBACK_NEW).exists())
                                self.assertFalse(
                                    (previous_slot / cursors.DEBUG_CUT_ABORT).exists())
                            self.assertTrue(run())
                            self.assertEqual(debug.stat().st_ino, old_inode)
                            self.assertEqual(youtube.read_bytes(), b"")
                            self.assertIn(b"example.net\n", writer.targets["youtube"].read_bytes())
                            self.assertEqual((managed / "hostlist-user.txt").read_bytes(),
                                             b"example.org\n")
                            self.assertTrue(
                                (previous_slot / cursors.DEBUG_CUT_ROLLBACK).is_file())
                            self.assertTrue(
                                (previous_slot / cursors.DEBUG_CUT_ABORT).is_file())
                            self.assertFalse(
                                (previous_slot / cursors.DEBUG_CUT_ROLLBACK_NEW).exists())
                            self.assertFalse(
                                (previous_slot / cursors.DEBUG_CUT_OLD).exists())
                            self.assertFalse(
                                (previous_slot / cursors.DEBUG_CUT_RETIRE).exists())
                            self.assertTrue((root / "00000003" / "ack.json").exists())
                            # Next minute now safely cuts the fully ACKed
                            # ORIGINAL debug inode; no duplicate discovery.
                            self.assertTrue(run())
                            self.assertNotEqual(debug.stat().st_ino, old_inode)
                            self.assertTrue(
                                (root / "00000003" / cursors.DEBUG_CUT_RETIRE).exists())
                            self.assertFalse(run())
                            return
                    self.assertTrue(run())
                    self.assertNotEqual(debug.stat().st_ino, old_inode)
                    self.assertEqual(debug.read_bytes(), b"")
                    for receipt in ("debug-cut-intent.json",
                                    "debug-cut-complete.json",
                                    "debug-cut-retire.json"):
                        self.assertTrue((previous_slot / receipt).is_file())
                    if case == "debug-cut-late-old":
                        retired = json.loads(
                            (previous_slot / "debug-cut-retire.json").read_bytes())
                        self.assertEqual(
                            retired["late_diagnostic_bytes"],
                            len(b"late-old-native-diagnostic\n"))
                        self.assertEqual(
                            retired["retained_size"],
                            full_size + len(native_debug(
                                proof.learning[1][0], "mail.example.org", str(user)))
                            + len(b"late-old-native-diagnostic\n"))
                    self.assertFalse(
                        (previous_slot / "debug-cut-retained.log").exists())
                    self.assertFalse(
                        (previous_slot / "debug-cut-fresh.log").exists())
                    new_tip = chain.learning_tip(proof, self.work)
                    self.assertEqual(new_tip["debug"]["offset"], 0)
                    self.assertEqual(new_tip["debug"]["inode"],
                                     debug.stat().st_ino)
                    self.assertFalse(run())
                    if case == "debug-cut-repeat":
                        first_cut_inode = debug.stat().st_ino
                        with debug.open("ab") as fp:
                            fp.write(diagnostic * count)
                        self.assertTrue(run())  # WAL/ACK the next diagnostic
                        self.assertTrue(run())  # repeat the original debug cut
                        self.assertNotEqual(debug.stat().st_ino, first_cut_inode)
                        self.assertEqual(debug.read_bytes(), b"")
                        self.assertTrue(
                            (root / "00000003" / "debug-cut-retire.json").exists())
                        self.assertFalse(
                            (root / "00000003" / "debug-cut-retained.log").exists())
                        self.assertFalse(run())
                else:
                    self.assertFalse(run())
                root = writer.receipts.root / proof.generation / "cursor-chain-v2"
                self.assertTrue((root / "00000000" / "ack.json").exists())
                self.assertTrue((root / "00000001" / "ack.json").exists())
                if case in ("diagnostic-highwater", "debug-cut-crash",
                            "debug-cut-repeat", "debug-cut-late-old",
                            "debug-cut-late-positive",
                            "debug-cut-late-positive-rollback-crash",
                            "debug-cut-late-positive-new-busy",
                            "debug-cut-part"):
                    self.assertTrue((root / "00000002" / "ack.json").exists())
                    if case == "debug-cut-repeat":
                        self.assertTrue((root / "00000003" / "ack.json").exists())
                        self.assertFalse((root / "00000004").exists())
                    else:
                        self.assertFalse((root / "00000003").exists())
                else:
                    self.assertFalse((root / "00000002").exists())
                if case == "rollover":
                    import auto_detect_cursor_chain as cursors
                    youtube.write_bytes(b"www.rollover-boundary.net\n")
                    with debug.open("ab") as out:
                        out.write(native_debug(proof.learning[0][0], "www.rollover-boundary.net", str(youtube)))
                    rename = Path.rename
                    def interrupted_swap(path, target):
                        result = rename(path, target)
                        if path == root and Path(target).name == cursors.OLD:
                            raise OSError("injected_after_predecessor_rename")
                        return result
                    with patch.object(cursors, "MAX_STEPS", 2):
                        with patch.object(Path, "rename", interrupted_swap):
                            with self.assertRaises(OSError):
                                run()
                        self.assertEqual(youtube.read_bytes(), b"www.rollover-boundary.net\n")
                        self.assertTrue(run())
                        self.assertFalse(run())
                    self.assertIn(b"rollover-boundary.net\n", writer.targets["youtube"].read_bytes())
                    anchor = json.loads((root / "anchor.json").read_bytes())
                    self.assertEqual(anchor["cycle"], 1)
                    self.assertTrue((root / "00000000" / "ack.json").exists())
        finally:
            os.close(config_fd)

    def test_tz6v4_sealed_full_n_pretraffic_is_one_original_epoch(self):
        """Real shared generator + sealed active schema3 + protected inodes.

        This source-only fixture explicitly constructs the FUTURE promoted
        release, not an original FD9 CLI invocation. No engine runs, and
        _epoch still refuses schema3 until a genuine P2c owner path exists.
        """
        mapped, args = self.build(
            "--filter-tcp=443\n<HOSTLIST:youtube>\n--lua-desync=fake\n"
            "--new\n--filter-tcp=443\n<HOSTLIST:user>\n--lua-desync=fake\n")
        source = self.check_nonactivating(mapped, args)
        original = args.read_bytes()
        producer_parent = self.root / "producer-parent"
        producer_parent.mkdir(mode=0o711)
        data_root = producer_parent / "producer"
        data_root.mkdir(mode=0o710)
        writer_gid = max(os.getegid(), 1)
        if os.geteuid() == 0:
            os.chown(data_root, 0, writer_gid)
        pending = data_root / "pending"
        pending.mkdir(mode=0o700)
        if os.geteuid() == 0:
            # FreeBSD native filesystem inherits parent producer group
            # (nobody) on mkdir; original P2a pending must be root:root.
            os.chown(pending, 0, os.getegid())
        for name in ("inbox.txt", "debug.log"):
            item = data_root / name
            item.write_bytes(b"")
            item.chmod(0o660)
            if os.geteuid() == 0:
                os.chown(item, 0, writer_gid)
        queue = DurableInbox(data_root, owner_uid=os.geteuid(),
                             writer_gid=writer_gid)
        root_gid = os.getegid()
        engine_uid = os.geteuid() + 2
        candidate = "d" * 64
        with patch.object(origin, "RAW_PATH", queue.inbox), \
             patch.object(origin, "DEBUG_PATH", data_root / "debug.log"), \
             patch.object(producer_storage, "ROOT", data_root), \
             patch.object(producer_storage, "DEBUG_PATH", data_root / "debug.log"):
            projected, proposal = origin.plan_learning_tier(
                source, original, owner_id=self.work.name,
                owner_candidate_sha256=candidate)
            self.assertEqual(
                owner._valid_learning_proposal(
                    json.dumps(proposal).encode(),
                    {"id": self.work.name, "candidate": candidate},
                    original, projected)[0][1],
                "youtube")
            active = {**proposal,
                      "evidence": owner.LEARNING_ACTIVE,
                      "activation_authorized": True}
            learning = owner._valid_learning_active(
                json.dumps(active).encode(),
                {"id": self.work.name, "candidate": candidate},
                source, original, projected)
            self.assertEqual([name for _, name, _ in learning],
                             ["youtube", "user"])
            args_original = self.release / "dvtws.original.args"
            args_original.write_bytes(original)
            args.write_bytes(projected)
            (self.release / owner.MAP_NAME).write_bytes(
                json.dumps(active, sort_keys=True).encode())
            (self.work / "plan.json").write_text(json.dumps({
                "page": "strategies",
                "candidate": {"general": {"enabled": "1"}},
                "changed_fields": [], "dependencies": "a" * 64,
            }))
            create_seal(self.work, owner=os.geteuid())
            for _, _, filename in learning:
                path = Path(filename)
                path.write_bytes(b"")
                path.chmod(0o660)
                if os.geteuid() == 0:
                    os.chown(path, 0, writer_gid)
            names = tuple(Path(path).name for _, _, path in learning)
            # Original _capture takes its own short P2a lock. It must
            # complete BEFORE the later original FD9 epoch lock is held;
            # nested flock would be a second writer and correctly refuses.
            captured = post_drop._capture(
                data_root, root_uid=os.geteuid(), root_gid=root_gid,
                engine_uid=engine_uid, engine_gid=writer_gid,
                learning_names=names)
            wire = post_drop._witness_line_learning(captured, learning)
            # Native CI has no inherited original FD9. Mock ONLY that
            # FD9 presence check in this explicitly source-only fixture;
            # the actual FreeBSD producer inodes, P2a lock and bundle seal
            # remain physically enforced by production code.
            with queue.exclusive(), patch("voice_ipfw_adapter.require_lifecycle_lock"):
                epoch = EpochReceipts(self.root / "epochs",
                                      owner_uid=os.geteuid(),
                                      writer_gid=writer_gid)
                seed = epoch.seal_learning_pretraffic(
                    queue, workspace=self.work, candidate_sha256=candidate,
                    wire=wire, root_gid=root_gid, engine_uid=engine_uid,
                    attest=lambda: True)
                self.assertEqual(seed["schema"], 3)
                self.assertFalse(seed["ack_authorized"])
                self.assertEqual(len(seed["files"]), len(learning) + 2)
                self.assertEqual([row["offset"] for row in seed["learning"]],
                                 [0, 0])
                folder = epoch.root / self.work.name
                raw = (folder / "pretraffic.json").read_bytes()
                self.assertEqual(json.loads(raw), seed)
                self.assertFalse((folder / "epoch.json").exists())
                native = Path(learning[0][2])
                native.write_bytes(b"video.example.com\n")
                (data_root / "debug.log").write_bytes(
                    b"test native postlaunch debug record\n")
                # The owner proof shape is SYNTHETIC in this source-only
                # fixture. Real original FD9/P2c PID/birth/argv attestation
                # is still unconnected; this does not qualify live runtime.
                proof = owner.LearningGenerationProof(
                    OwnerToken(3214, "Fri Nov 20 12:34:56 2026", CHILD_EXEC),
                    self.work.name, self.work.name, candidate,
                    hashlib.sha256(projected).hexdigest(),
                    hashlib.sha256((self.release / owner.MAP_NAME).read_bytes()).hexdigest(),
                    learning,
                )
                with self.assertRaises(ReceiptRefused):
                    epoch.finish_learning_running(
                        proof, queue, workspace=self.work,
                        attest=lambda: None)
                self.assertFalse((folder / "epoch.json").exists())
                completed = epoch.finish_learning_running(
                    proof, queue, workspace=self.work,
                    attest=lambda: proof)
                self.assertEqual(completed["schema"], 3)
                self.assertEqual(completed["owner_pid"], 3214)
                self.assertEqual(completed["learning"], seed["learning"])
                self.assertEqual(completed["files"], seed["files"])
                self.assertEqual(
                    completed["pretraffic_sha256"],
                    hashlib.sha256(raw).hexdigest())
                self.assertFalse(completed["ack_authorized"])
                epoch_bytes = (folder / "epoch.json").read_bytes()
                self.assertEqual(json.loads(epoch_bytes), completed)
                # Legacy P2 worker/ACK reader must NEVER accept schema3.
                with self.assertRaises(ReceiptRefused):
                    epoch._epoch(proof)
                # Idempotent same-proof replay may not mutate durable bytes.
                self.assertEqual(
                    epoch.finish_learning_running(
                        proof, queue, workspace=self.work,
                        attest=lambda: proof), completed)
                self.assertEqual((folder / "epoch.json").read_bytes(), epoch_bytes)
                with self.assertRaises(ReceiptRefused):
                    epoch.seal_learning_pretraffic(
                        queue, workspace=self.work,
                        candidate_sha256=candidate, wire=wire,
                        root_gid=root_gid, engine_uid=engine_uid,
                        attest=lambda: True)
                self.assertEqual((folder / "pretraffic.json").read_bytes(), raw)
                self.assertEqual(native.read_bytes(), b"video.example.com\n")
                self.assertEqual((folder / "epoch.json").read_bytes(), epoch_bytes)

                # Read-only original-P2a physical native → registered P1
                # proposal. The source-level process proof is synthetic,
                # never a real FD9 owner or a permission to ACK.
                from auto_detect_original_v2_source import (
                    preview_original_learning_candidates_locked,
                    OriginalSourceRefused,
                )
                user_native = Path(learning[1][2])
                user_native.write_bytes(b"mail.example.org\n")
                def native_debug(number, hostname, pathname):
                    return (f"12:00 : {hostname} : profile {number} (learn) "
                            f": client 198.51.100.1 : proto tls : adding to "
                            f"{pathname}\n").encode("ascii")
                first_debug = native_debug(
                    learning[0][0], "video.example.com", learning[0][2])
                second_debug = native_debug(
                    learning[1][0], "mail.example.org", learning[1][2])
                debug_path = data_root / "debug.log"
                debug_path.write_bytes(first_debug + second_debug)
                observed = preview_original_learning_candidates_locked(
                    queue, epoch, proof, self.work, attest=lambda: proof)
                self.assertEqual(observed["observations"], [
                    {"hostname": "video.example.com", "hostlist": "youtube"},
                    {"hostname": "mail.example.org", "hostlist": "user"},
                ])
                self.assertEqual(set(observed["native_cursors"]),
                                 {item[2] for item in learning})
                self.assertEqual(
                    [observed["native_cursors"][item[2]].offset
                     for item in learning],
                    [len(b"video.example.com\n"), len(b"mail.example.org\n")])
                self.assertFalse(observed["commit_authorized"])
                self.assertFalse(observed["ack_authorized"])
                self.assertEqual(native.read_bytes(), b"video.example.com\n")
                self.assertEqual(user_native.read_bytes(), b"mail.example.org\n")
                self.assertEqual((folder / "epoch.json").read_bytes(), epoch_bytes)
                # One original P2b all-PID per-inode scan is a prerequisite
                # for any future durable transfer. The injected inspector
                # simulates the native FreeBSD fstat result ONLY; this is
                # not an installed FD9/Config or dvtws2 acceptance test.
                from auto_detect_original_v2_source import (
                    attest_original_learning_drained_candidate_locked,
                )
                from auto_detect_fd import FDState
                scans = []
                def drained(path, device, inode, *, owner, writer_gid):
                    scans.append((path, device, inode, owner, writer_gid))
                    return FDState.DRAINED
                qualified = attest_original_learning_drained_candidate_locked(
                    queue, epoch, proof, self.work, attest=lambda: proof,
                    inspect=drained)
                self.assertEqual(qualified["observations"],
                                 observed["observations"])
                self.assertTrue(qualified["p2b_drained"])
                self.assertFalse(qualified["commit_authorized"])
                self.assertFalse(qualified["ack_authorized"])
                self.assertEqual([row[0] for row in scans],
                                 [debug_path, native, user_native])
                # Original locked P2+GUI+P1 preflight: a real physical N
                # native candidate becomes only a proposed three-Found
                # destination and two effective managed byte images.
                # No durable WAL/Config authority is granted by this fixture.
                from auto_detect_destination_commit import DestinationCommit
                from auto_detect_owned_sources import bootstrap_empty
                from auto_detect_original_v2_model import (
                    preview_original_learning_p1_locked,
                )
                owned_dir = self.root / "owned-source-test"
                bootstrap_empty(
                    owned_dir, original_config_sha256="a" * 64,
                    owner_uid=os.geteuid(),
                    authorized_clean_start=True)
                shared = self.root / "shared-source-test.txt"
                shared.write_bytes(b"")
                shared.chmod(0o600)
                targets = {
                    "auto": shared,
                    "youtube": owned_dir / "youtube.txt",
                    "user": owned_dir / "user.txt",
                }
                writer = DestinationCommit(
                    epoch, queue, targets,
                    self.root / "source-test-gui.lock")
                if getattr(self, "exercise_independent_cycles", False):
                    self._exercise_independent_cycles(
                        writer, proof, queue, owned_dir, native_debug, drained)
                    return
                protected = [debug_path, native, user_native,
                             shared, targets["youtube"], targets["user"]]
                originals = {str(path): path.read_bytes()
                             for path in protected}
                with writer.exclusive_targets():
                    p1 = preview_original_learning_p1_locked(
                        writer, proof, self.work, owned_root=owned_dir,
                        manual_hostlists={
                            "youtube": "youtube.com\n", "user": ""},
                        global_exclude="", attest=lambda: proof,
                        inspect=drained,
                        psl=self._tz6v4_psl_for_fixtures())
                self.assertEqual(p1["p1"]["effects"], {
                    "youtube": {"add": ["example.com"], "remove": []},
                    "user": {"add": ["example.org"], "remove": []},
                })
                self.assertEqual(p1["p1"]["managed_after"]["youtube"],
                                 b"youtube.com\nexample.com\n")
                self.assertEqual(p1["p1"]["managed_after"]["user"],
                                 b"example.org\n")
                self.assertFalse(p1["commit_authorized"])
                self.assertFalse(p1["cleanup_authorized"])
                self.assertFalse(p1["ack_authorized"])
                self.assertEqual(
                    {str(path): path.read_bytes() for path in protected},
                    originals)
                self.assertEqual((folder / "epoch.json").read_bytes(),
                                 epoch_bytes)
                # This API refuses a call outside the ORIGINAL existing
                # destination lock even with a valid synthetic P2b result.
                with self.assertRaises(V2OriginalConfigRefused):
                    preview_original_learning_p1_locked(
                        writer, proof, self.work, owned_root=owned_dir,
                        manual_hostlists={"youtube": "", "user": ""},
                        global_exclude="", attest=lambda: proof,
                        inspect=drained)

                # First original schema3 durable N-native cursor slot:
                # one write-once intent inside the EXISTING v2 chain root,
                # never a replacement queue or an ACK/Found permission.
                from auto_detect_cursor_chain import (
                    CursorChain, CursorChainRefused,
                )
                chain = CursorChain(epoch, queue)
                saved = chain.prepare_learning_first_slot(
                    proof, self.work, attest=lambda: proof, inspect=drained)
                slot = folder / "cursor-chain-v2" / "00000000"
                self.assertEqual(saved["slot"], slot)
                self.assertEqual(
                    set(path.name for path in slot.iterdir()), {"intent.json"})
                durable = (slot / "intent.json").read_bytes()
                persisted = json.loads(durable)
                self.assertEqual(persisted["schema"], 3)
                self.assertEqual(persisted["kind"],
                                 "original-learning-cursor-prepared")
                self.assertEqual(persisted["observations"],
                                 observed["observations"])
                self.assertEqual(
                    [row["hostlist"] for row in persisted["native"]],
                    ["youtube", "user"])
                self.assertEqual(
                    [row["end_offset"] for row in persisted["native"]],
                    [len(b"video.example.com\n"),
                     len(b"mail.example.org\n")])
                self.assertFalse(saved["commit_authorized"])
                self.assertFalse(saved["cleanup_authorized"])
                self.assertFalse(saved["ack_authorized"])
                self.assertEqual(
                    chain.prepare_learning_first_slot(
                        proof, self.work, attest=lambda: proof,
                        inspect=drained)["intent_sha256"],
                    saved["intent_sha256"])
                self.assertEqual((slot / "intent.json").read_bytes(), durable)
                self.assertFalse((slot / "ack.json").exists())
                self.assertFalse((slot / "destination").exists())

                # One original Config-FD-held P1→source-bound WAL→real
                # permanent Found and live managed CAS on disposable files.
                # Config FD + P2a and P2b here are synthetic source-only
                # witnesses; the production PHP/FD9 dispatcher is NOT wired.
                import fcntl
                from auto_detect_destination_commit import (
                    DestinationRefused, qualified_destination_plan,
                )
                from auto_detect_epoch_receipts import _canonical
                from auto_detect_original_v2_model import (
                    commit_with_original_learning_first_slot,
                )
                active_root = self.root / "synthetic-active-runtime"
                active_managed = active_root / "managed"
                active_managed.mkdir(mode=0o700, parents=True)
                working = {}
                for name, before in (
                    ("youtube", b"youtube.com\n"), ("user", b"")):
                    path = active_managed / ("hostlist-" + name + ".txt")
                    path.write_bytes(before)
                    path.chmod(0o600)
                    working[name] = {
                        "path": path,
                        "before_sha256": hashlib.sha256(before).hexdigest(),
                        "after": p1["p1"]["managed_after"][name],
                    }
                source_raw = _canonical(
                    {"observations": persisted["observations"]})
                with writer.exclusive_targets():
                    with self.assertRaisesRegex(
                            DestinationRefused,
                            "learning_wal_requires_live_and_source"):
                        writer._locked_commit(
                            slot, persisted, source_raw,
                            p1["p1"]["effects"], live=None)
                config_path = self.root / "original-test-config.xml"
                config_path.write_bytes(b"<opnsense/>\n")
                config_path.chmod(0o600)
                cfg_fd = os.open(config_path, os.O_RDWR | os.O_NOFOLLOW)
                fcntl.flock(cfg_fd, fcntl.LOCK_EX)
                def native_live_preview(*args, **kwargs):
                    self.assertEqual(kwargs["active"], active_root)
                    self.assertEqual(kwargs["attest"](), proof)
                    return {
                        "owner_schema": 3,
                        "generation": proof.generation,
                        "operation": proof.operation_id,
                        "pid": proof.owner.pid,
                        "started": proof.owner.started,
                        "changed": ["youtube", "user"],
                        "files": {
                            name: {
                                "path": str(item["path"]),
                                "before_sha256": item["before_sha256"],
                                "after_sha256": hashlib.sha256(
                                    item["after"]).hexdigest(),
                            }
                            for name, item in working.items()
                        },
                        "commit_authorized": False,
                        "ack_authorized": False,
                    }
                if sys.platform.startswith("freebsd"):
                    # Native product accepts ONLY genuine /conf Config FD.
                    # Never weaken that protection for this disposable test.
                    with self.assertRaisesRegex(
                            V2OriginalConfigRefused,
                            "learning_original_config_fd9_model_required"):
                        commit_with_original_learning_first_slot(
                            writer, proof, self.work,
                            config_fd=cfg_fd, config_path=config_path,
                            owned_root=owned_dir,
                            manual_hostlists={
                                "youtube": "youtube.com\n", "user": ""},
                            global_exclude="", attest=lambda: proof,
                            inspect=drained,
                            psl=self._tz6v4_psl_for_fixtures())

                from auto_detect_destination_commit import _replace as real_replace
                from auto_detect_original_v2_model import (
                    _recover_original_learning_partial_locked,
                )
                def commit_fixture_once(*, global_exclude=""):
                    with patch(
                            "auto_detect_original_v2_model.COMMON_ACTIVE",
                            active_root), patch(
                            "auto_detect_original_v2_model.preview_live_known_after_readonly",
                            side_effect=native_live_preview):
                        if sys.platform.startswith("freebsd"):
                            # Original private P2k2b/partial-P1 primitives
                            # only; no test may impersonate PHP Config FD4.
                            with writer.exclusive_targets():
                                if (slot / "destination" / "plan.json").exists():
                                    return _recover_original_learning_partial_locked(
                                        writer, proof, self.work, slot, persisted,
                                        owned_root=owned_dir,
                                        manual_hostlists={
                                            "youtube": "youtube.com\n", "user": ""},
                                        global_exclude=global_exclude,
                                        attest=lambda: proof, inspect=drained,
                                        psl=self._tz6v4_psl_for_fixtures())
                                return writer._locked_commit(
                                    slot, persisted, source_raw,
                                    p1["p1"]["effects"], live=working)
                        return commit_with_original_learning_first_slot(
                            writer, proof, self.work,
                            config_fd=cfg_fd, config_path=config_path,
                            owned_root=owned_dir,
                            manual_hostlists={
                                "youtube": "youtube.com\n", "user": ""},
                            global_exclude=global_exclude,
                            attest=lambda: proof,
                            inspect=drained,
                            psl=self._tz6v4_psl_for_fixtures())

                # Crash just AFTER the first permanent Found rename/fsync.
                # The original WAL plan exists, but there is NO checkpoint
                # and still NO managed update or native row cleanup/ACK.
                replacements = [0]
                def crash_after_first_cas(*args, **kwargs):
                    real_replace(*args, **kwargs)
                    replacements[0] += 1
                    if replacements[0] == 1:
                        raise DestinationRefused(
                            "synthetic_crash_after_first_original_found")
                with patch("auto_detect_destination_commit._replace",
                           side_effect=crash_after_first_cas):
                    with self.assertRaises(
                            (V2OriginalConfigRefused, DestinationRefused)):
                        commit_fixture_once()
                self.assertEqual(replacements, [1])
                self.assertTrue((slot / "destination" / "plan.json").exists())
                self.assertFalse(
                    (slot / "destination" / "checkpoint.json").exists())
                # Original writer orders destination names lexically:
                # 'user' is the first physical CAS, 'youtube' is pending.
                self.assertEqual(targets["user"].read_bytes(),
                                 b"example.org\n")
                self.assertEqual(targets["youtube"].read_bytes(), b"")
                self.assertEqual(working["youtube"]["path"].read_bytes(),
                                 b"youtube.com\n")
                self.assertFalse((slot / "ack.json").exists())

                # This native writer ignores P2a flock: a NEW append must
                # remain preserved and not be added to the old WAL slot.
                with user_native.open("ab") as out:
                    out.write(b"later.example.org\n")
                self.assertEqual(
                    chain.prepare_learning_first_slot(
                        proof, self.work, attest=lambda: proof,
                        inspect=drained)["intent_sha256"],
                    saved["intent_sha256"])
                # Reprocessing with changed current P1/exclusion is not
                # an excuse to reauthorize the previously sealed effects.
                with self.assertRaises(
                        (V2OriginalConfigRefused, DestinationRefused)):
                    commit_fixture_once(global_exclude="example.com\n")
                self.assertFalse(
                    (slot / "destination" / "checkpoint.json").exists())
                saved_checkpoint = commit_fixture_once()
                self.assertEqual(user_native.read_bytes(),
                                 b"mail.example.org\nlater.example.org\n")
                # Reset only disposable fixture tail for later source tests.
                user_native.write_bytes(b"mail.example.org\n")
                self.assertFalse(saved_checkpoint["ack_authorized"])
                expected_plan, plan_raw = qualified_destination_plan(
                    slot, persisted, epoch.uid, targets=writer.targets)
                self.assertEqual(expected_plan["schema"], 3)
                self.assertEqual(
                    expected_plan["source_intent_sha256"],
                    hashlib.sha256(durable).hexdigest())
                self.assertEqual(
                    expected_plan["pending_name"], "learning-00000000")
                self.assertEqual(targets["youtube"].read_bytes(),
                                 b"example.com\n")
                self.assertEqual(targets["user"].read_bytes(),
                                 b"example.org\n")
                self.assertEqual(working["youtube"]["path"].read_bytes(),
                                 b"youtube.com\nexample.com\n")
                self.assertEqual(working["user"]["path"].read_bytes(),
                                 b"example.org\n")
                self.assertEqual(shared.read_bytes(), b"")
                self.assertFalse((slot / "ack.json").exists())
                self.assertEqual((slot / "intent.json").read_bytes(), durable)
                self.assertEqual((folder / "epoch.json").read_bytes(),
                                 epoch_bytes)
                self.assertEqual(native.read_bytes(),
                                 b"video.example.com\n")
                self.assertEqual(user_native.read_bytes(),
                                 b"mail.example.org\n")
                # Original STEP 5: the sealed Found + SAME-PID managed
                # checkpoint qualifies precise native working rows for
                # future compaction, NEVER an import-only cleanup/ACK.
                # A new native append is preserved BYTE-FOR-BYTE: only
                # the old attributed prefix can be considered removable.
                from auto_detect_original_v2_model import (
                    preview_learning_checkpoint_native_compaction_locked,
                )
                with user_native.open("ab", buffering=0) as producer:
                    producer.write(b"late.example.org\n")
                    os.fsync(producer.fileno())
                def compaction_preview(*, exclude="", owner_witness=lambda: proof):
                    with writer.exclusive_targets(), patch(
                            "auto_detect_original_v2_model.COMMON_ACTIVE",
                            active_root):
                        return preview_learning_checkpoint_native_compaction_locked(
                            writer, proof, self.work, owned_root=owned_dir,
                            manual_hostlists={
                                "youtube": "youtube.com\n", "user": ""},
                            global_exclude=exclude, attest=owner_witness,
                            inspect=drained,
                            psl=self._tz6v4_psl_for_fixtures())
                compact = compaction_preview()
                self.assertFalse(compact["cleanup_authorized"])
                self.assertFalse(compact["ack_authorized"])
                self.assertEqual(
                    [(item["hostlist"], item["removed"],
                      item["replacement"]) for item in compact["profiles"]],
                    [("youtube", ("video.example.com",), b""),
                     ("user", ("mail.example.org",),
                      b"late.example.org\n")])
                for item in compact["profiles"]:
                    source_bytes = item["path"].read_bytes()
                    self.assertEqual(
                        item["expected_native_image"],
                        (len(source_bytes),
                         hashlib.sha256(source_bytes).hexdigest()))
                    self.assertEqual(
                        (item["path"].stat().st_dev,
                         item["path"].stat().st_ino),
                        item["expected_identity"])
                # The first-slot durable cross-N receipt is the ONLY
                # original generation journal for future native rebind.
                # First the original permanent+active checkpoint exists;
                # then per-N records, then the aggregate manifest LAST.
                from auto_detect_original_v2_model import (
                    seal_original_learning_native_rebind_locked,
                )
                def seal_native_transition(*, config_descriptor=cfg_fd):
                    with writer.exclusive_targets(), patch(
                            "auto_detect_original_v2_model.COMMON_ACTIVE",
                            active_root):
                        return seal_original_learning_native_rebind_locked(
                            writer, proof, self.work,
                            config_fd=config_descriptor,
                            config_path=config_path, owned_root=owned_dir,
                            manual_hostlists={
                                "youtube": "youtube.com\n", "user": ""},
                            global_exclude="", attest=lambda: proof,
                            inspect=drained,
                            psl=self._tz6v4_psl_for_fixtures())
                if sys.platform.startswith("freebsd"):
                    with self.assertRaisesRegex(
                            V2OriginalConfigRefused,
                            "learning_rebind_original_fd4_fd9_required"):
                        seal_native_transition()
                else:
                    with self.assertRaises(V2OriginalConfigRefused):
                        seal_native_transition(config_descriptor=-1)
                    # Crash AFTER the first original write-once profile,
                    # BEFORE the aggregate manifest. The same immutable
                    # source may resume; NO partial journal grants rotation.
                    from auto_detect_epoch_receipts import (
                        _write_once as normal_original_write_once,
                    )
                    injected = [0]
                    def fail_after_first_profile(folder, name, raw, uid):
                        normal_original_write_once(folder, name, raw, uid)
                        if (folder.name == "native-rebind" and
                                name != "manifest.json" and
                                injected[0] == 0):
                            injected[0] += 1
                            raise RuntimeError(
                                "synthetic_native_rebind_profile_crash")
                    with patch(
                            "auto_detect_epoch_receipts._write_once",
                            side_effect=fail_after_first_profile):
                        with self.assertRaisesRegex(
                                RuntimeError, "synthetic_native_rebind_profile_crash"):
                            seal_native_transition()
                    pending_journal = slot / "native-rebind"
                    self.assertEqual(
                        len(list(pending_journal.iterdir())), 1)
                    self.assertFalse(
                        (pending_journal / "manifest.json").exists())
                    self.assertEqual(queue.segments(), [])
                    self.assertEqual(
                        user_native.read_bytes(),
                        b"mail.example.org\nlate.example.org\n")
                    result = seal_native_transition()
                    self.assertEqual(result["profiles_count"], 2)
                    self.assertEqual(result["rotation_count"], 2)
                    self.assertFalse(result["physical_rotation_authorized"])
                    self.assertFalse(result["ack_authorized"])
                    journal = slot / "native-rebind"
                    names = {f"{number:03d}.json"
                             for number, _, _ in proof.learning}
                    self.assertEqual(
                        {p.name for p in journal.iterdir()},
                        names | {"manifest.json"})
                    data = json.loads((journal / "manifest.json").read_bytes())
                    self.assertEqual(data["schema"], 3)
                    self.assertEqual(data["profiles_count"], 2)
                    self.assertFalse(data["ack_authorized"])
                    perprofile = [
                        (journal / f"{number:03d}.json").read_bytes()
                        for number, _, _ in proof.learning
                    ]
                    self.assertEqual(
                        data["profiles_sha256"],
                        hashlib.sha256(b"".join(
                            hashlib.sha256(raw).digest()
                            for raw in perprofile)).hexdigest())
                    for record in map(json.loads, perprofile):
                        self.assertEqual(record["schema"], 3)
                        self.assertFalse(record["ack_authorized"])
                        self.assertEqual(
                            record["generation"], proof.generation)
                        self.assertRegex(
                            record["pending_name"],
                            r"^native-" + proof.generation +
                            r"-[0-9]+-[0-9a-f]{32}\.txt$")
                    before_records = {
                        p.name: p.read_bytes() for p in journal.iterdir()}
                    self.assertEqual(seal_native_transition(), result)
                    self.assertEqual(
                        before_records,
                        {p.name: p.read_bytes() for p in journal.iterdir()})
                    # First-slot source replay recognizes native-rebind
                    # as belonging to the SAME original cursor journal.
                    self.assertEqual(
                        chain.prepare_learning_first_slot(
                            proof, self.work, attest=lambda: proof,
                            inspect=drained)["intent_sha256"],
                        saved["intent_sha256"])
                    # If dvtws2 appends after durable plan publish, that
                    # old plan is NOT refreshed to guess a new postimage.
                    with user_native.open("ab") as producer:
                        producer.write(b"new.example.org\n")
                    with self.assertRaises(V2OriginalConfigRefused):
                        seal_native_transition()
                    user_native.write_bytes(
                        b"mail.example.org\nlate.example.org\n")
                    self.assertEqual(before_records, {
                        p.name: p.read_bytes() for p in journal.iterdir()})
                    self.assertEqual(
                        user_native.read_bytes(),
                        b"mail.example.org\nlate.example.org\n")
                    self.assertEqual(queue.segments(), [])
                    # Physical-state read is not a cursor advancement:
                    # the immutable original manifest survives a native
                    # rename, whereas first-slot zero-epoch reader would
                    # correctly reject an inode replacement.
                    from auto_detect_original_v2_model import (
                        inspect_original_learning_native_rebind_locked,
                    )
                    def physical_state(*, config_descriptor=cfg_fd):
                        with writer.exclusive_targets(), patch(
                                "auto_detect_original_v2_model.COMMON_ACTIVE",
                                active_root):
                            return inspect_original_learning_native_rebind_locked(
                                writer, proof, self.work,
                                config_fd=config_descriptor,
                                config_path=config_path, attest=lambda: proof)
                    initial_physical = physical_state()
                    self.assertEqual(
                        [row["phase"] for row in initial_physical["profiles"]],
                        ["prepared-unmodified", "prepared-unmodified"])
                    self.assertFalse(
                        initial_physical["physical_rotation_authorized"])
                    self.assertFalse(initial_physical["ack_authorized"])
                    user_num = learning[1][0]
                    native_plan = json.loads(
                        (journal / f"{user_num:03d}.json").read_bytes())
                    self.assertEqual(native_plan["hostlist"], "user")
                    retained = queue.pending / native_plan["pending_name"]
                    # A crash between original hardlink() and rename()
                    # leaves TWO names for the same old inode.
                    os.link(user_native, retained)
                    self.assertEqual(
                        physical_state()["profiles"][1]["phase"],
                        "linked-source-grew")
                    self.assertEqual(retained.stat().st_nlink, 2)
                    # Now simulate ONLY the disposable P2a file primitive,
                    # not a product call / verified live dvtws2 transaction.
                    with user_native.open("ab", buffering=0) as old_writer:
                        rotated = queue._rotate_original_source(
                            user_native,
                            replacement=b"late.example.org\n",
                            generation=proof.generation,
                            expected_identity=(
                                native_plan["old_device"],
                                native_plan["old_inode"]),
                            sealed_prefix=(
                                native_plan["sealed_end_offset"],
                                native_plan["sealed_end_sha256"]),
                            expected_native_image=(
                                native_plan["full_preimage"]["size"],
                                native_plan["full_preimage"]["sha256"]),
                            native_pending_name=native_plan["pending_name"])
                        self.assertEqual(rotated, retained)
                        self.assertEqual(
                            [r["phase"] for r in physical_state()["profiles"]],
                            ["prepared-unmodified",
                             "replaced-with-unprocessed-tails"])
                        old_writer.write(b"oldlate.example.net\n")
                        os.fsync(old_writer.fileno())
                    with user_native.open("ab", buffering=0) as new_writer:
                        new_writer.write(b"newlate.example.net\n")
                        os.fsync(new_writer.fileno())
                    observed = physical_state()
                    self.assertEqual(
                        [r["phase"] for r in observed["profiles"]],
                        ["prepared-unmodified",
                         "replaced-with-unprocessed-tails"])
                    self.assertEqual(
                        observed["profiles"][1]["old_tail_size"],
                        len(b"late.example.org\noldlate.example.net\n"))
                    self.assertEqual(
                        observed["profiles"][1]["new_tail_size"],
                        len(b"late.example.org\nnewlate.example.net\n"))
                    self.assertFalse(observed["ack_authorized"])
                    self.assertEqual(
                        retained.read_bytes(),
                        b"mail.example.org\nlate.example.org\n"
                        b"oldlate.example.net\n")
                    self.assertEqual(
                        user_native.read_bytes(),
                        b"late.example.org\nnewlate.example.net\n")
                    # Losing the retained old inode after a rename must
                    # fail closed even if the new live bytes are intact.
                    held_away = data_root / ".retained-old-inode-test"
                    retained.replace(held_away)
                    with self.assertRaises(V2OriginalConfigRefused):
                        physical_state()
                    held_away.replace(retained)
                    # Native working content mismatch is not permission to
                    # reconstruct from an unverified inode or to ACK old FD.
                    new_bytes = user_native.read_bytes()
                    user_native.write_bytes(b"forged.example.org\n")
                    with self.assertRaises(V2OriginalConfigRefused):
                        physical_state()
                    user_native.write_bytes(new_bytes)
                    self.assertEqual(
                        physical_state()["profiles"][1]["phase"],
                        "replaced-with-unprocessed-tails")
                    # An old-FD late-tail modification that damages the
                    # sealed old preimage is NOT a valid pending source.
                    saved_retained = retained.read_bytes()
                    retained.write_bytes(b"forged-retained.example.net\n")
                    with self.assertRaises(V2OriginalConfigRefused):
                        physical_state()
                    retained.write_bytes(saved_retained)
                    # A change to an EARLIER N profile during a later N
                    # read must be caught by the all-N second pass.
                    import auto_detect_original_v2_model as original_model
                    actual_native_snapshot = (
                        original_model._native_rebind_stable_snapshot)
                    injected_race = [False]
                    def race_between_profiles(path, *args, **kwargs):
                        result = actual_native_snapshot(path, *args, **kwargs)
                        if path == retained and not injected_race[0]:
                            injected_race[0] = True
                            with native.open("ab", buffering=0) as producer:
                                producer.write(b"raced.example.com\n")
                                os.fsync(producer.fileno())
                        return result
                    with patch.object(
                            original_model, "_native_rebind_stable_snapshot",
                            side_effect=race_between_profiles):
                        with self.assertRaises(V2OriginalConfigRefused):
                            physical_state()
                    self.assertTrue(injected_race[0])
                    native.write_bytes(b"video.example.com\n")
                    self.assertEqual(
                        physical_state()["profiles"][1]["phase"],
                        "replaced-with-unprocessed-tails")
                    # Restore the original OLD inode only in this disposable
                    # test fixture; production MUST retain both until its
                    # future qualified cursor+ACK lifecycle is implemented.
                    retained.replace(user_native)
                    user_native.write_bytes(
                        b"mail.example.org\nlate.example.org\n")
                    self.assertEqual(queue.segments(), [])
                    self.assertEqual(
                        physical_state()["profiles"][1]["phase"],
                        "prepared-unmodified")
                    # Qualify TWO post-rename native files in the same
                    # original all-N manifest. Per-N cursor bases must
                    # remain durable, even after a partial write crash.
                    youtube_num = learning[0][0]
                    youtube_plan = json.loads(
                        (journal / f"{youtube_num:03d}.json").read_bytes())
                    youtube_pending = queue.pending / youtube_plan["pending_name"]
                    user_pending = queue.pending / native_plan["pending_name"]
                    for live_path, record, postimage in (
                        (native, youtube_plan, b""),
                        (user_native, native_plan, b"late.example.org\n"),
                    ):
                        created = queue._rotate_original_source(
                            live_path,
                            replacement=postimage,
                            generation=proof.generation,
                            expected_identity=(
                                record["old_device"], record["old_inode"]),
                            sealed_prefix=(
                                record["sealed_end_offset"],
                                record["sealed_end_sha256"]),
                            expected_native_image=(
                                record["full_preimage"]["size"],
                                record["full_preimage"]["sha256"]),
                            native_pending_name=record["pending_name"])
                        self.assertEqual(created.name,
                                         record["pending_name"])
                    self.assertEqual(
                        [item["phase"] for item in physical_state()["profiles"]],
                        ["replaced-retained",
                         "replaced-with-unprocessed-tails"])
                    from auto_detect_original_v2_model import (
                        seal_original_learning_post_inode_seed_locked,
                    )
                    def write_inode_seed(*, config_descriptor=cfg_fd):
                        with writer.exclusive_targets(), patch(
                                "auto_detect_original_v2_model.COMMON_ACTIVE",
                                active_root):
                            return seal_original_learning_post_inode_seed_locked(
                                writer, proof, self.work,
                                config_fd=config_descriptor,
                                config_path=config_path,
                                attest=lambda: proof)
                    with self.assertRaises(V2OriginalConfigRefused):
                        write_inode_seed(config_descriptor=-1)
                    observed_root = journal / "observed"
                    observed_crashes = [0]
                    def crash_after_first_inode_seed(folder, name, raw, uid):
                        normal_original_write_once(folder, name, raw, uid)
                        if (folder.name == "observed" and
                                observed_crashes[0] == 0):
                            observed_crashes[0] += 1
                            raise RuntimeError("injected_inode_seed_crash")
                    with patch("auto_detect_epoch_receipts._write_once",
                               side_effect=crash_after_first_inode_seed):
                        with self.assertRaisesRegex(
                                RuntimeError, "injected_inode_seed_crash"):
                            write_inode_seed()
                    self.assertEqual(len(list(observed_root.iterdir())), 1)
                    self.assertEqual(
                        [row["phase"] for row in physical_state()["profiles"]],
                        ["replaced-retained",
                         "replaced-with-unprocessed-tails"])
                    sealed_seed = write_inode_seed()
                    self.assertEqual(sealed_seed["seeds"], 2)
                    self.assertFalse(sealed_seed["cursor_advanced"])
                    self.assertFalse(sealed_seed["ack_authorized"])
                    saved_seeds = {
                        p.name: p.read_bytes()
                        for p in observed_root.iterdir()}
                    self.assertEqual(set(saved_seeds), names)
                    self.assertEqual(write_inode_seed(), sealed_seed)
                    self.assertEqual({
                        p.name: p.read_bytes()
                        for p in observed_root.iterdir()}, saved_seeds)
                    for number, expected_pending in (
                            (youtube_num, youtube_pending),
                            (user_num, user_pending)):
                        record = json.loads(
                            (observed_root / f"{number:03d}.json").read_bytes())
                        self.assertEqual(
                            record["old_pending_name"],
                            expected_pending.name)
                        self.assertFalse(record["cursor_advanced"])
                        self.assertFalse(record["ack_authorized"])
                        self.assertEqual(
                            record["old_pending_inode"]["cut_offset"],
                            (youtube_plan if number == youtube_num
                             else native_plan)["sealed_end_offset"])
                        self.assertEqual(
                            record["new_live_inode"]["cut_offset"], 0)
                        self.assertEqual(
                            record["new_live_inode"]["cut_sha256"],
                            hashlib.sha256(b"").hexdigest())
                        self.assertEqual(
                            record["old_pending_proven_preimage"]["size"],
                            (youtube_plan if number == youtube_num
                             else native_plan)["full_preimage"]["size"])
                        self.assertEqual(
                            record["new_live_proven_postimage"]["size"],
                            (youtube_plan if number == youtube_num
                             else native_plan)["replacement"]["size"])
                    # The late domain was present in P1's FULL image
                    # but NOT in the original first-slot observations.
                    # It must remain unprocessed on BOTH physical paths.
                    user_before = json.loads(
                        (observed_root / f"{user_num:03d}.json").read_bytes())
                    self.assertEqual(
                        user_before["old_pending_inode"]["cut_offset"],
                        len(b"mail.example.org\n"))
                    self.assertLess(
                        user_before["old_pending_inode"]["cut_offset"],
                        user_before["old_pending_proven_preimage"]["size"])
                    self.assertGreater(
                        user_before["new_live_proven_postimage"]["size"], 0)
                    self.assertEqual(
                        physical_state()["profiles"][1]["new_tail_size"],
                        len(b"late.example.org\n"))
                    # New tails NEVER move either immutable cursor base:
                    # old-FD bytes and new-path bytes are still unprocessed.
                    with user_pending.open("ab", buffering=0) as old:
                        old.write(b"after-seal-old.example.net\n")
                        os.fsync(old.fileno())
                    with user_native.open("ab", buffering=0) as fresh:
                        fresh.write(b"after-seal-new.example.net\n")
                        os.fsync(fresh.fileno())
                    tails = physical_state()
                    self.assertGreater(
                        tails["profiles"][1]["old_tail_size"], 0)
                    self.assertGreater(
                        tails["profiles"][1]["new_tail_size"], 0)
                    self.assertEqual(write_inode_seed(), sealed_seed)
                    self.assertEqual({
                        p.name: p.read_bytes()
                        for p in observed_root.iterdir()}, saved_seeds)
                    # Forward N-native preview: source-only. The
                    # unchanged original P2a/Config/GUI FD9 + original
                    # P2b must pair every NEW domain with the same-profile
                    # native "adding to" debug emitted after first slot.
                    # Merely reading a native list never authorizes P1.
                    from auto_detect_original_v2_model import (
                        preview_original_learning_forward_windows_locked,
                    )
                    def forward_preview(*, inspect_witness=drained):
                        with writer.exclusive_targets(), patch(
                                "auto_detect_original_v2_model.COMMON_ACTIVE",
                                active_root):
                            return preview_original_learning_forward_windows_locked(
                                writer, proof, self.work,
                                config_fd=cfg_fd, config_path=config_path,
                                attest=lambda: proof,
                                inspect=inspect_witness)
                    with self.assertRaises(V2OriginalConfigRefused):
                        forward_preview()
                    second_tail = (
                        native_debug(user_num, "late.example.org", learning[1][2]) +
                        native_debug(user_num, "after-seal-old.example.net",
                                     learning[1][2]) +
                        native_debug(user_num, "after-seal-new.example.net",
                                     learning[1][2]))
                    # Two physically different file paths contain the ONE
                    # late domain, but it has exactly ONE genuine debug
                    # positive in the post-first-slot stream.
                    debug_path.write_bytes(
                        first_debug + second_debug + second_tail)
                    forward = forward_preview()
                    self.assertTrue(forward["p2b_drained"])
                    self.assertFalse(forward["commit_authorized"])
                    self.assertFalse(forward["ack_authorized"])
                    self.assertEqual(forward["deduped_cross_inode"], 1)
                    self.assertEqual(forward["observations"], [
                        {"hostname": "after-seal-new.example.net",
                         "hostlist": "user"},
                        {"hostname": "after-seal-old.example.net",
                         "hostlist": "user"},
                        {"hostname": "late.example.org", "hostlist": "user"},
                    ])
                    self.assertEqual(
                        forward["native"][1]["old_start"],
                        len(b"mail.example.org\n"))
                    self.assertEqual(forward["native"][1]["new_start"], 0)
                    self.assertEqual(
                        forward["native"][1]["new_end"],
                        len(b"late.example.org\n"
                            b"after-seal-new.example.net\n"))
                    self.assertEqual(forward_preview(), forward)
                    self.assertEqual(
                        forward["debug"]["start"],
                        len(first_debug + second_debug))
                    # A hostname may be discovered by BOTH native
                    # profiles. Same-host duplicate is removed ONLY
                    # within one exact (N, HOSTLIST) source, never by
                    # guessing that YouTube and User share a destination.
                    native.write_bytes(b"late.example.org\n")
                    debug_path.write_bytes(
                        first_debug + second_debug + second_tail +
                        native_debug(youtube_num, "late.example.org",
                                     learning[0][2]))
                    mixed = forward_preview()
                    self.assertEqual(
                        len(mixed["observations"]), 4)
                    self.assertEqual(
                        {r["hostlist"] for r in mixed["observations"]
                         if r["hostname"] == "late.example.org"},
                        {"youtube", "user"})
                    self.assertFalse(mixed["ack_authorized"])
                    native.write_bytes(b"")
                    debug_path.write_bytes(
                        first_debug + second_debug + second_tail)
                    # Even a genuinely matching append must NOT arrive
                    # while the global original P2b FD scan runs:
                    # the all-N source cut and debug cursor have changed.
                    raced = [False]
                    def p2b_append_race(path, device, inode, *, owner, writer_gid):
                        if not raced[0]:
                            raced[0] = True
                            with user_native.open("ab", buffering=0) as producer:
                                producer.write(b"racing-p2b.example.net\n")
                                os.fsync(producer.fileno())
                            with debug_path.open("ab", buffering=0) as out:
                                out.write(native_debug(
                                    user_num, "racing-p2b.example.net",
                                    learning[1][2]))
                                os.fsync(out.fileno())
                        return drained(path, device, inode, owner=owner,
                                       writer_gid=writer_gid)
                    with self.assertRaises(V2OriginalConfigRefused):
                        forward_preview(inspect_witness=p2b_append_race)
                    self.assertTrue(raced[0])
                    user_native.write_bytes(
                        b"late.example.org\nafter-seal-new.example.net\n")
                    debug_path.write_bytes(
                        first_debug + second_debug + second_tail)
                    self.assertEqual(forward_preview(), forward)
                    # A debug event alone cannot advance any source:
                    # the native row may not have been persisted yet.
                    debug_path.write_bytes(
                        first_debug + second_debug + second_tail +
                        native_debug(user_num, "absent.example.net",
                                     learning[1][2]))
                    with self.assertRaises(V2OriginalConfigRefused):
                        forward_preview()
                    # Wrong native number/path is NEVER guessed from domain.
                    debug_path.write_bytes(
                        first_debug + second_debug +
                        native_debug(youtube_num, "late.example.org",
                                     learning[1][2]) +
                        second_tail)
                    with self.assertRaises(V2OriginalConfigRefused):
                        forward_preview()
                    # Native with no matching after-slot positive must
                    # remain unread (not silently folded or auto-ACKed).
                    debug_path.write_bytes(first_debug + second_debug)
                    with self.assertRaises(V2OriginalConfigRefused):
                        forward_preview()
                    debug_path.write_bytes(
                        first_debug + second_debug + second_tail)
                    with self.assertRaises(V2OriginalConfigRefused):
                        forward_preview(
                            inspect_witness=lambda *_args, **_kwargs:
                                FDState.BUSY)
                    self.assertEqual(forward_preview(), forward)
                    self.assertFalse((slot.parent / "00000001").exists())
                    self.assertFalse((slot / "ack.json").exists())
                    # No new cursor, destination plan or native ACK exists
                    # simply because the original P2b preview passed.
                    self.assertEqual(
                        {p.name: p.read_bytes()
                         for p in observed_root.iterdir()}, saved_seeds)
                    from auto_detect_original_v2_model import (
                        prepare_original_learning_forward_second_slot_locked,
                    )
                    def seal_second_slot(*, inspect_witness=drained):
                        with writer.exclusive_targets(), patch(
                                "auto_detect_original_v2_model.COMMON_ACTIVE",
                                active_root):
                            return prepare_original_learning_forward_second_slot_locked(
                                writer, proof, self.work, config_fd=cfg_fd,
                                config_path=config_path, attest=lambda: proof,
                                inspect=inspect_witness)
                    second_slot = slot.parent / "00000001"
                    from auto_detect_original_v2_model import (
                        seal_original_learning_forward_progress_locked,
                        preview_original_learning_late_tails_locked,
                        prepare_original_learning_third_slot_locked,
                        seal_original_learning_third_progress_locked,
                        preview_original_learning_third_pending_retirement_locked,
                        prepare_original_learning_third_pending_ack_locked,
                    )
                    def advance_second_cursor(*, inspect_witness=drained):
                        with writer.exclusive_targets(), patch(
                                "auto_detect_original_v2_model.COMMON_ACTIVE",
                                active_root):
                            return seal_original_learning_forward_progress_locked(
                                writer, proof, self.work,
                                config_fd=cfg_fd, config_path=config_path,
                                attest=lambda: proof,
                                inspect=inspect_witness)
                    def preview_late_tails(*, inspect_witness=drained):
                        with writer.exclusive_targets(), patch(
                                "auto_detect_original_v2_model.COMMON_ACTIVE",
                                active_root):
                            return preview_original_learning_late_tails_locked(
                                writer, proof, self.work,
                                config_fd=cfg_fd, config_path=config_path,
                                attest=lambda: proof,
                                inspect=inspect_witness)
                    def seal_third_slot(*, inspect_witness=drained):
                        with writer.exclusive_targets(), patch(
                                "auto_detect_original_v2_model.COMMON_ACTIVE",
                                active_root):
                            return prepare_original_learning_third_slot_locked(
                                writer, proof, self.work,
                                config_fd=cfg_fd, config_path=config_path,
                                attest=lambda: proof,
                                inspect=inspect_witness)
                    third_slot = slot.parent / "00000002"
                    def advance_third_cursor(*, inspect_witness=drained):
                        with writer.exclusive_targets(), patch(
                                "auto_detect_original_v2_model.COMMON_ACTIVE",
                                active_root):
                            return seal_original_learning_third_progress_locked(
                                writer, proof, self.work, config_fd=cfg_fd,
                                config_path=config_path, attest=lambda: proof,
                                inspect=inspect_witness)
                    def pending_retirement(*, inspect_witness=drained):
                        with writer.exclusive_targets(), patch(
                                "auto_detect_original_v2_model.COMMON_ACTIVE",
                                active_root):
                            return preview_original_learning_third_pending_retirement_locked(
                                writer, proof, self.work,
                                config_fd=cfg_fd, config_path=config_path,
                                attest=lambda: proof,
                                inspect=inspect_witness)
                    def prepare_native_ack(*, inspect_witness=drained):
                        with writer.exclusive_targets(), patch(
                                "auto_detect_original_v2_model.COMMON_ACTIVE",
                                active_root):
                            return prepare_original_learning_third_pending_ack_locked(
                                writer, proof, self.work,
                                config_fd=cfg_fd, config_path=config_path,
                                attest=lambda: proof,
                                inspect=inspect_witness)
                    from auto_detect_original_native_archive import (
                        archive_original_learning_pending_locked,
                        preview_original_learning_archive_release_locked,
                    )
                    def archive_release_preview(*, inspect_witness=drained):
                        with writer.exclusive_targets(), patch(
                                "auto_detect_original_v2_model.COMMON_ACTIVE",
                                active_root):
                            return preview_original_learning_archive_release_locked(
                                writer, proof, self.work,
                                config_fd=cfg_fd, config_path=config_path,
                                attest=lambda: proof,
                                inspect=inspect_witness)
                    def archive_pending(*, inspect_witness=drained):
                        with writer.exclusive_targets(), patch(
                                "auto_detect_original_v2_model.COMMON_ACTIVE",
                                active_root):
                            return archive_original_learning_pending_locked(
                                writer, proof, self.work,
                                config_fd=cfg_fd, config_path=config_path,
                                attest=lambda: proof,
                                inspect=inspect_witness)
                    from auto_detect_original_history import (
                        seal_original_learning_independent_history_locked,
                        read_original_learning_independent_history_locked,
                    )
                    def seal_independent_history():
                        with writer.exclusive_targets(), patch(
                                "auto_detect_original_v2_model.COMMON_ACTIVE",
                                active_root):
                            return seal_original_learning_independent_history_locked(
                                writer, proof, self.work,
                                config_fd=cfg_fd, config_path=config_path,
                                attest=lambda: proof, inspect=drained)
                    def read_independent_history():
                        with writer.exclusive_targets():
                            return read_original_learning_independent_history_locked(
                                writer, proof, self.work,
                                config_fd=cfg_fd, config_path=config_path,
                                attest=lambda: proof)
                    from auto_detect_original_history_wal import (
                        preview_original_learning_independent_wal_locked,
                    )
                    def preview_independent_wal(*, inspect_witness=drained):
                        with writer.exclusive_targets(), patch(
                                "auto_detect_original_v2_model.COMMON_ACTIVE",
                                active_root):
                            return preview_original_learning_independent_wal_locked(
                                writer, proof, self.work,
                                config_fd=cfg_fd, config_path=config_path,
                                attest=lambda: proof, inspect=inspect_witness)
                    from auto_detect_original_history_postimages import (
                        seal_original_learning_independent_postimages_locked,
                        read_original_learning_independent_postimages_locked,
                    )
                    def seal_independent_postimages(*, inspect_witness=drained):
                        with writer.exclusive_targets(), patch(
                                "auto_detect_original_v2_model.COMMON_ACTIVE",
                                active_root):
                            return seal_original_learning_independent_postimages_locked(
                                writer, proof, self.work,
                                config_fd=cfg_fd, config_path=config_path,
                                attest=lambda: proof, inspect=inspect_witness)
                    def read_independent_postimages(*, inspect_witness=drained):
                        with writer.exclusive_targets(), patch(
                                "auto_detect_original_v2_model.COMMON_ACTIVE",
                                active_root):
                            return read_original_learning_independent_postimages_locked(
                                writer, proof, self.work,
                                config_fd=cfg_fd, config_path=config_path,
                                attest=lambda: proof, inspect=inspect_witness)
                    from auto_detect_original_history_positive import (
                        preview_original_learning_independent_positive_locked,
                    )
                    def preview_independent_positive(*, inspect_witness=drained):
                        with writer.exclusive_targets(), patch(
                                "auto_detect_original_v2_model.COMMON_ACTIVE",
                                active_root):
                            return preview_original_learning_independent_positive_locked(
                                writer, proof, self.work,
                                config_fd=cfg_fd, config_path=config_path,
                                attest=lambda: proof, inspect=inspect_witness)
                    from auto_detect_original_history_release_guard import (
                        seal_original_learning_release_guard_locked,
                        preview_original_learning_release_guard_locked,
                        preview_original_learning_release_owner_live_locked,
                    )
                    def seal_original_release_guard(*, inspect_witness=drained):
                        with writer.exclusive_targets(), patch(
                                "auto_detect_original_v2_model.COMMON_ACTIVE",
                                active_root):
                            return seal_original_learning_release_guard_locked(
                                writer, proof, self.work,
                                config_fd=cfg_fd, config_path=config_path,
                                attest=lambda: proof, inspect=inspect_witness)
                    def preview_original_release_guard(*, inspect_witness=drained):
                        with writer.exclusive_targets(), patch(
                                "auto_detect_original_v2_model.COMMON_ACTIVE",
                                active_root):
                            return preview_original_learning_release_guard_locked(
                                writer, proof, self.work,
                                config_fd=cfg_fd, config_path=config_path,
                                attest=lambda: proof, inspect=inspect_witness)
                    def preview_original_owner_live(*, inspect_witness=drained):
                        with writer.exclusive_targets(), patch(
                                "auto_detect_original_v2_model.COMMON_ACTIVE",
                                active_root):
                            return preview_original_learning_release_owner_live_locked(
                                writer, proof, self.work,
                                config_fd=cfg_fd, config_path=config_path,
                                attest=lambda: proof, inspect=inspect_witness)
                    from auto_detect_original_history_stopped import (
                        preview_original_learning_stopped_guard_locked,
                        preview_original_learning_stopped_destination_reconciliation_locked,
                    )
                    def preview_original_stopped_guard(*, inspect_witness=drained):
                        with writer.exclusive_targets(), patch(
                                "auto_detect_original_v2_model.COMMON_ACTIVE",
                                active_root):
                            return preview_original_learning_stopped_guard_locked(
                                writer, proof, self.work,
                                config_fd=cfg_fd, config_path=config_path,
                                attest=lambda: proof, inspect=inspect_witness)
                    def preview_original_destination_reconcile(
                            *, inspect_witness=drained):
                        with writer.exclusive_targets(), patch(
                                "auto_detect_original_v2_model.COMMON_ACTIVE",
                                active_root):
                            return (
                                preview_original_learning_stopped_destination_reconciliation_locked(
                                    writer, proof, self.work,
                                    config_fd=cfg_fd, config_path=config_path,
                                    attest=lambda: proof, inspect=inspect_witness))
                    self.assertFalse(second_slot.exists())
                    with self.assertRaises(V2OriginalConfigRefused):
                        archive_release_preview()
                    with self.assertRaises(V2OriginalConfigRefused):
                        prepare_native_ack()
                    with self.assertRaises(V2OriginalConfigRefused):
                        pending_retirement()
                    with self.assertRaises(V2OriginalConfigRefused):
                        preview_late_tails()
                    with self.assertRaises(V2OriginalConfigRefused):
                        seal_third_slot()
                    with self.assertRaises(V2OriginalConfigRefused):
                        advance_third_cursor()
                    partial_second = [False]
                    def abort_after_one_native(folder, name, data, uid):
                        normal_original_write_once(folder, name, data, uid)
                        if (folder.name == "native" and
                                not partial_second[0]):
                            partial_second[0] = True
                            raise RuntimeError(
                                "synthetic_forward_second_slot_crash")
                    with patch("auto_detect_epoch_receipts._write_once",
                               side_effect=abort_after_one_native):
                        with self.assertRaisesRegex(
                                RuntimeError,
                                "synthetic_forward_second_slot_crash"):
                            seal_second_slot()
                    self.assertTrue(partial_second[0])
                    self.assertFalse((second_slot / "intent.json").exists())
                    self.assertEqual(len(list(
                        (second_slot / "native").iterdir())), 1)
                    # An interrupted INCOMPLETE slot cannot change its
                    # already written N window just because the producer
                    # later appended additional rows or debug positives.
                    # The first source-only receipt belongs to YouTube:
                    # changing that SAME sealed N cursor before the
                    # aggregate manifest must refuse instead of silently
                    # widening the interrupted transaction.
                    with native.open("ab", buffering=0) as producer:
                        producer.write(b"partial-late.example.net\n")
                        os.fsync(producer.fileno())
                    with debug_path.open("ab", buffering=0) as debug:
                        debug.write(native_debug(
                            youtube_num, "partial-late.example.net",
                            learning[0][2]))
                        os.fsync(debug.fileno())
                    with self.assertRaises(V2OriginalConfigRefused):
                        seal_second_slot()
                    native.write_bytes(b"")
                    debug_path.write_bytes(
                        first_debug + second_debug + second_tail)
                    second_result = seal_second_slot()
                    self.assertEqual(second_result["sequence"], 1)
                    self.assertEqual(second_result["profiles_count"], 2)
                    self.assertEqual(second_result["observations_count"], 3)
                    self.assertFalse(second_result["cursor_advanced"])
                    self.assertFalse(second_result["commit_authorized"])
                    self.assertFalse(second_result["ack_authorized"])
                    self.assertEqual(
                        set(p.name for p in second_slot.iterdir()),
                        {"intent.json", "native"})
                    per_native = {
                        p.name: p.read_bytes() for p in
                        (second_slot / "native").iterdir()}
                    intent_second_raw = (
                        second_slot / "intent.json").read_bytes()
                    self.assertEqual(
                        second_result["intent_sha256"],
                        hashlib.sha256(intent_second_raw).hexdigest())
                    self.assertEqual(seal_second_slot(), second_result)
                    # STEP 7: this is STILL the same original
                    # DestinationCommit Found -> managed CAS, never a new
                    # writer. The forward second-slot source is committed
                    # from the exact bound observations, not from any
                    # later native/debug append. Source-only fixture.
                    from auto_detect_original_v2_model import (
                        preview_learning_p1_effects,
                        commit_with_original_learning_forward_second_slot,
                    )
                    from auto_detect_owned_sources import read_owned
                    second_intent = json.loads(intent_second_raw)
                    self.assertEqual(
                        second_intent["observations_count"],
                        len(second_intent["observations"]))
                    second_p1 = preview_learning_p1_effects(
                        second_intent["observations"],
                        {"youtube": "youtube.com\n", "user": ""},
                        read_owned(owned_dir, owner_uid=os.geteuid()),
                        shared.read_text(), "",
                        psl=self._tz6v4_psl_for_fixtures())
                    self.assertEqual(
                        second_p1["effects"], {
                            "user": {"add": ["example.net"], "remove": []},
                        })
                    next_active = (
                        active_managed / "hostlist-user.txt")
                    before_next = next_active.read_bytes()
                    after_next = second_p1["managed_after"]["user"]
                    self.assertNotEqual(before_next, after_next)
                    def forward_live_preview(*_args, **kwargs):
                        self.assertEqual(kwargs["active"], active_root)
                        return {
                            "owner_schema": 3,
                            "generation": proof.generation,
                            "operation": proof.operation_id,
                            "pid": proof.owner.pid,
                            "started": proof.owner.started,
                            "changed": ["user"],
                            "files": {
                                "user": {
                                    "path": str(next_active),
                                    "before_sha256": hashlib.sha256(
                                        before_next).hexdigest(),
                                    "after_sha256": hashlib.sha256(
                                        after_next).hexdigest(),
                                },
                            },
                            "commit_authorized": False,
                            "ack_authorized": False,
                        }
                    def forward_commit_fixture():
                        with patch(
                                "auto_detect_original_v2_model.COMMON_ACTIVE",
                                active_root), patch(
                                "auto_detect_original_v2_model.preview_live_known_after_readonly",
                                side_effect=forward_live_preview):
                            return commit_with_original_learning_forward_second_slot(
                                writer, proof, self.work,
                                config_fd=cfg_fd, config_path=config_path,
                                owned_root=owned_dir,
                                manual_hostlists={
                                    "youtube": "youtube.com\n", "user": ""},
                                global_exclude="", attest=lambda: proof,
                                inspect=drained,
                                psl=self._tz6v4_psl_for_fixtures())
                    if sys.platform.startswith("freebsd"):
                        # No synthetic /conf FD4, so product entrypoint
                        # MUST refuse. Linux disposable-file source
                        # fixture runs the complete P1/WAL crash path.
                        with self.assertRaises(V2OriginalConfigRefused):
                            forward_commit_fixture()
                    else:
                        from auto_detect_destination_commit import (
                            _replace as original_second_replace,
                        )
                        second_writes = [0]
                        def crash_after_forward_found(*args, **kwargs):
                            original_second_replace(*args, **kwargs)
                            second_writes[0] += 1
                            if second_writes[0] == 1:
                                raise DestinationRefused(
                                    "fixture_second_found_write_crash")
                        with patch(
                                "auto_detect_destination_commit._replace",
                                side_effect=crash_after_forward_found):
                            with self.assertRaises(
                                    (DestinationRefused,
                                     V2OriginalConfigRefused)):
                                forward_commit_fixture()
                        self.assertEqual(second_writes, [1])
                        self.assertTrue(
                            (second_slot / "destination" /
                             "plan.json").exists())
                        self.assertFalse(
                            (second_slot / "destination" /
                             "checkpoint.json").exists())
                        with self.assertRaises(V2OriginalConfigRefused):
                            advance_second_cursor()
                        self.assertFalse(
                            (second_slot / "cursor-progress.json").exists())
                        self.assertIn(
                            b"example.net\n",
                            targets["user"].read_bytes())
                        self.assertEqual(next_active.read_bytes(),
                                         before_next)
                        self.assertEqual(
                            seal_second_slot(), second_result)
                        # A recovery with changed P1 policy is unsafe.
                        with patch(
                                "auto_detect_original_v2_model.COMMON_ACTIVE",
                                active_root):
                            with writer.exclusive_targets():
                                with self.assertRaises(V2OriginalConfigRefused):
                                    _recover_original_learning_partial_locked(
                                        writer, proof, self.work,
                                        second_slot, second_intent,
                                        owned_root=owned_dir,
                                        manual_hostlists={
                                            "youtube": "youtube.com\n",
                                            "user": ""},
                                        global_exclude="example.net\n",
                                        attest=lambda: proof, inspect=drained,
                                        psl=self._tz6v4_psl_for_fixtures(),
                                        config_fd=cfg_fd,
                                        config_path=config_path)
                        recovered_second = forward_commit_fixture()
                        self.assertEqual(
                            recovered_second["pending_name"],
                            "learning-00000001")
                        self.assertFalse(recovered_second["ack_authorized"])
                        self.assertEqual(next_active.read_bytes(), after_next)
                        self.assertEqual(
                            recovered_second, forward_commit_fixture())
                        second_plan, raw_second_plan = (
                            qualified_destination_plan(
                                second_slot, second_intent,
                                os.geteuid(), targets=writer.targets))
                        self.assertEqual(
                            second_plan["source_intent_sha256"],
                            hashlib.sha256(intent_second_raw).hexdigest())
                        self.assertEqual(
                            recovered_second["plan_sha256"],
                            hashlib.sha256(raw_second_plan).hexdigest())
                        self.assertFalse(
                            (second_slot / "ack.json").exists())
                        self.assertEqual(queue.segments(),
                                         [youtube_pending, user_pending])
                        advanced = advance_second_cursor()
                        self.assertTrue(advanced["cursor_advanced"])
                        self.assertEqual(advanced["profiles_count"], 2)
                        self.assertFalse(
                            advanced["native_pending_ack_authorized"])
                        self.assertFalse(
                            advanced["native_cleanup_authorized"])
                        self.assertFalse(advanced["generation_retired"])
                        self.assertEqual(
                            advance_second_cursor(), advanced)
                        frozen_progress = (
                            second_slot / "cursor-progress.json").read_bytes()
                        self.assertEqual(
                            advanced["progress_sha256"],
                            hashlib.sha256(frozen_progress).hexdigest())
                        self.assertEqual(queue.segments(),
                                         [youtube_pending, user_pending])
                        initial_late = preview_late_tails()
                        self.assertEqual(initial_late["native_observations"], [])
                        self.assertEqual(initial_late["unread_native_bytes"], 0)
                        self.assertFalse(
                            initial_late["native_pending_ack_authorized"])
                        self.assertFalse(initial_late["cursor_advanced"])
                    # After the durable second intent, appends on BOTH
                    # native inodes and debug are permitted. Read-only
                    # replay verifies historical source prefixes and
                    # recovers EXACT old observations, not new candidates.
                    with user_pending.open("ab", buffering=0) as old:
                        old.write(b"later-old.alpha.com\n")
                        os.fsync(old.fileno())
                    with user_native.open("ab", buffering=0) as live:
                        live.write(b"later-new.beta.org\n")
                        os.fsync(live.fileno())
                    with debug_path.open("ab", buffering=0) as debug:
                        debug.write(
                            native_debug(user_num, "later-old.alpha.com",
                                         learning[1][2]) +
                            native_debug(user_num, "later-new.beta.org",
                                         learning[1][2]))
                        os.fsync(debug.fileno())
                    self.assertEqual(seal_second_slot(), second_result)
                    self.assertEqual(
                        {p.name: p.read_bytes() for p in
                         (second_slot / "native").iterdir()}, per_native)
                    self.assertEqual(
                        (second_slot / "intent.json").read_bytes(),
                        intent_second_raw)
                    self.assertGreater(
                        len(forward_preview()["observations"]),
                        second_result["observations_count"])
                    if not sys.platform.startswith("freebsd"):
                        late = preview_late_tails()
                        self.assertEqual(late["previous_sequence"], 1)
                        self.assertEqual(late["native_observations"], [
                            {"native_number": user_num, "hostlist": "user",
                             "hostname": "later-new.beta.org"},
                            {"native_number": user_num, "hostlist": "user",
                             "hostname": "later-old.alpha.com"},
                        ])
                        self.assertFalse(late["cursor_advanced"])
                        self.assertFalse(late["native_cleanup_authorized"])
                        self.assertFalse(
                            late["native_pending_ack_authorized"])
                        user_cut = json.loads(
                            per_native[f"{user_num:03d}.json"])["cursor"]
                        self.assertEqual(
                            late["native"][1]["old"]["start"],
                            user_cut["old_end"])
                        self.assertEqual(
                            late["native"][1]["new"]["start"],
                            user_cut["new_end"])
                        self.assertEqual(
                            late["native"][1]["old"]["unread_bytes"],
                            len(b"later-old.alpha.com\n"))
                        self.assertEqual(
                            late["native"][1]["new"]["unread_bytes"],
                            len(b"later-new.beta.org\n"))
                        self.assertEqual(
                            late["debug"]["start"],
                            second_intent["debug"]["end"])
                        self.assertEqual(
                            preview_late_tails(), late)
                        # SOURCE ONLY: third original slot is immutable
                        # N-per-inode provenance, NOT a third P1 or ACK.
                        third_crashed = [False]
                        def fail_first_third_N(folder, name, data, uid):
                            normal_original_write_once(
                                folder, name, data, uid)
                            if (folder.name == "native" and
                                    folder.parent.name == "00000002" and
                                    not third_crashed[0]):
                                third_crashed[0] = True
                                raise RuntimeError(
                                    "synthetic_third_original_N_crash")
                        with patch(
                                "auto_detect_learning_third_slot._write_once",
                                side_effect=fail_first_third_N):
                            with self.assertRaisesRegex(
                                    RuntimeError,
                                    "synthetic_third_original_N_crash"):
                                seal_third_slot()
                        self.assertTrue(third_crashed[0])
                        self.assertFalse(
                            (third_slot / "intent.json").exists())
                        self.assertEqual(
                            len(list((third_slot / "native").iterdir())), 1)
                        third = seal_third_slot()
                        self.assertEqual(third["sequence"], 2)
                        self.assertEqual(third["profiles_count"], 2)
                        self.assertEqual(third["observations_count"], 2)
                        self.assertFalse(third["cursor_advanced"])
                        self.assertFalse(third["commit_authorized"])
                        self.assertFalse(third["ack_authorized"])
                        self.assertEqual(seal_third_slot(), third)
                        # Source alone is NOT permission for a third
                        # logical cursor without the original P1 receipt.
                        with self.assertRaises(V2OriginalConfigRefused):
                            advance_third_cursor()
                        self.assertFalse(
                            (third_slot / "cursor-progress.json").exists())
                        # Third original destination SOURCE provenance is
                        # already qualified without starting another P1.
                        # This is the sole existing DestinationCommit
                        # source-plan codec, not a new backend writer.
                        from auto_detect_destination_commit import (
                            _original_source_plan_fields,
                            DestinationRefused,
                        )
                        third_prepared = json.loads(
                            (third_slot / "intent.json").read_bytes())
                        third_fields = _original_source_plan_fields(
                            third_slot, third_prepared, os.geteuid())
                        self.assertEqual(
                            third_fields["pending_name"],
                            "learning-00000002")
                        self.assertEqual(
                            third_fields["previous_cursor_progress_sha256"],
                            advanced["progress_sha256"])
                        self.assertEqual(
                            third_fields["source_intent_sha256"],
                            third["intent_sha256"])
                        self.assertFalse(
                            (third_slot / "destination").exists())
                        # A forged N cut or previous cursor must NEVER
                        # qualify even if its JSON is otherwise parseable.
                        child_path = (
                            third_slot / "native" /
                            f"{user_num:03d}.json")
                        original_child = child_path.read_bytes()
                        forged = json.loads(original_child)
                        forged["cursor"]["old_end"] += 1
                        child_path.write_bytes(
                            (json.dumps(forged, sort_keys=True,
                                        separators=(",", ":")) +
                             "\n").encode())
                        with self.assertRaises(DestinationRefused):
                            _original_source_plan_fields(
                                third_slot, third_prepared, os.geteuid())
                        child_path.write_bytes(original_child)
                        previous_progress = (
                            second_slot / "cursor-progress.json")
                        progress_original = previous_progress.read_bytes()
                        previous_progress.write_bytes(
                            progress_original.replace(
                                b'"cursor_advanced":true',
                                b'"cursor_advanced":false'))
                        with self.assertRaises(DestinationRefused):
                            _original_source_plan_fields(
                                third_slot, third_prepared, os.geteuid())
                        previous_progress.write_bytes(progress_original)
                        self.assertEqual(
                            _original_source_plan_fields(
                                third_slot, third_prepared, os.geteuid()),
                            third_fields)
                        # The third SOURCE now enters the EXISTING
                        # DestinationCommit P1->Found->managed WAL, not
                        # another owner or write mechanism.
                        from auto_detect_original_v2_model import (
                            commit_with_original_learning_third_slot,
                        )
                        third_effects = preview_learning_p1_effects(
                            third_prepared["observations"],
                            {"youtube": "youtube.com\n", "user": ""},
                            read_owned(
                                owned_dir, owner_uid=os.geteuid()),
                            shared.read_text(), "",
                            psl=self._tz6v4_psl_for_fixtures())
                        self.assertEqual(third_effects["effects"], {
                            "user": {
                                "add": ["alpha.com", "beta.org"],
                                "remove": [],
                            },
                        })
                        third_before_active = next_active.read_bytes()
                        third_after_active = (
                            third_effects["managed_after"]["user"])
                        self.assertNotEqual(
                            third_before_active, third_after_active)
                        def third_live_preview(*_args, **kwargs):
                            self.assertEqual(kwargs["active"], active_root)
                            return {
                                "owner_schema": 3,
                                "generation": proof.generation,
                                "operation": proof.operation_id,
                                "pid": proof.owner.pid,
                                "started": proof.owner.started,
                                "changed": ["user"],
                                "files": {"user": {
                                    "path": str(next_active),
                                    "before_sha256": hashlib.sha256(
                                        third_before_active).hexdigest(),
                                    "after_sha256": hashlib.sha256(
                                        third_after_active).hexdigest(),
                                }},
                                "commit_authorized": False,
                                "ack_authorized": False,
                            }
                        def third_commit_fixture(*, exclude=""):
                            with patch(
                                    "auto_detect_original_v2_model.COMMON_ACTIVE",
                                    active_root), patch(
                                    "auto_detect_original_v2_model.preview_live_known_after_readonly",
                                    side_effect=third_live_preview):
                                return commit_with_original_learning_third_slot(
                                    writer, proof, self.work,
                                    config_fd=cfg_fd, config_path=config_path,
                                    owned_root=owned_dir,
                                    manual_hostlists={
                                        "youtube": "youtube.com\n", "user": ""},
                                    global_exclude=exclude,
                                    attest=lambda: proof, inspect=drained,
                                    psl=self._tz6v4_psl_for_fixtures())
                        third_checkpoint = None
                        if sys.platform.startswith("freebsd"):
                            # Synthetic config cannot impersonate the
                            # actual OPNsense inherited /conf FD4.
                            with self.assertRaises(V2OriginalConfigRefused):
                                third_commit_fixture()
                        else:
                            from auto_detect_destination_commit import (
                                _replace as original_third_replace,
                            )
                            third_writes = [0]
                            def crash_third_after_found(*args, **kwargs):
                                original_third_replace(*args, **kwargs)
                                third_writes[0] += 1
                                if third_writes[0] == 1:
                                    raise DestinationRefused(
                                        "fixture_third_found_write_crash")
                            with patch(
                                    "auto_detect_destination_commit._replace",
                                    side_effect=crash_third_after_found):
                                with self.assertRaises((
                                        DestinationRefused,
                                        V2OriginalConfigRefused)):
                                    third_commit_fixture()
                            self.assertEqual(third_writes, [1])
                            self.assertTrue((
                                third_slot / "destination" /
                                "plan.json").exists())
                            self.assertFalse((
                                third_slot / "destination" /
                                "checkpoint.json").exists())
                            self.assertEqual(
                                next_active.read_bytes(),
                                third_before_active)
                            with self.assertRaises(V2OriginalConfigRefused):
                                advance_third_cursor()
                            self.assertFalse(
                                (third_slot / "cursor-progress.json").exists())
                            self.assertIn(
                                b"alpha.com\n", targets["user"].read_bytes())
                            self.assertEqual(
                                seal_third_slot(), third)
                            with self.assertRaises(V2OriginalConfigRefused):
                                third_commit_fixture(
                                    exclude="alpha.com\n")
                            third_checkpoint = third_commit_fixture()
                            self.assertEqual(
                                third_checkpoint["pending_name"],
                                "learning-00000002")
                            self.assertFalse(
                                third_checkpoint["ack_authorized"])
                            self.assertEqual(
                                next_active.read_bytes(),
                                third_after_active)
                            self.assertIn(
                                b"beta.org\n", targets["user"].read_bytes())
                            self.assertEqual(
                                third_commit_fixture(), third_checkpoint)
                            self.assertEqual(
                                seal_third_slot(), third)
                            self.assertEqual(
                                seal_second_slot(), second_result)
                            self.assertEqual(
                                advance_second_cursor(), advanced)
                            # STEP 9: after durable THIRD P1, seal ONLY
                            # the original third logical cursor, never
                            # native old-pending ACK or generation retire.
                            third_progress_crashed = [False]
                            def third_progress_crash(
                                    folder, name, data, uid):
                                normal_original_write_once(
                                    folder, name, data, uid)
                                if (folder.name == "00000002" and
                                        name == "cursor-progress.json" and
                                        not third_progress_crashed[0]):
                                    third_progress_crashed[0] = True
                                    raise RuntimeError(
                                        "synthetic_third_cursor_after_fsync")
                            with patch(
                                    "auto_detect_epoch_receipts._write_once",
                                    side_effect=third_progress_crash):
                                with self.assertRaisesRegex(
                                        RuntimeError,
                                        "synthetic_third_cursor_after_fsync"):
                                    advance_third_cursor()
                            self.assertTrue(third_progress_crashed[0])
                            self.assertTrue((
                                third_slot / "cursor-progress.json").exists())
                            third_advanced = advance_third_cursor()
                            self.assertTrue(third_advanced["cursor_advanced"])
                            self.assertEqual(third_advanced["sequence"], 2)
                            self.assertFalse(third_advanced[
                                "native_pending_ack_authorized"])
                            self.assertFalse(third_advanced[
                                "native_cleanup_authorized"])
                            self.assertFalse(third_advanced[
                                "generation_retired"])
                            self.assertEqual(
                                advance_third_cursor(), third_advanced)
                            third_progress_path = (
                                third_slot / "cursor-progress.json")
                            frozen_third_progress = (
                                third_progress_path.read_bytes())
                            recorded_third_progress = json.loads(
                                frozen_third_progress)
                            self.assertEqual(
                                recorded_third_progress["kind"],
                                "original-learning-third-cursor-progress")
                            self.assertEqual(
                                recorded_third_progress[
                                    "previous_cursor_progress_sha256"],
                                advanced["progress_sha256"])
                            self.assertEqual(
                                recorded_third_progress[
                                    "destination_checkpoint_sha256"],
                                third_advanced[
                                    "destination_checkpoint_sha256"])
                            self.assertEqual(
                                recorded_third_progress["profiles_count"], 2)
                            self.assertEqual(
                                third_advanced["progress_sha256"],
                                hashlib.sha256(
                                    frozen_third_progress).hexdigest())
                            self.assertFalse(
                                (third_slot / "ack.json").exists())
                            # STEP 10: read-only native pending disposition,
                            # no P2a/native unlink or ACK authority.
                            observed_files = {
                                p: p.read_bytes() for p in
                                (youtube_pending, user_pending, native,
                                 user_native, debug_path)}
                            pending_preview = pending_retirement()
                            self.assertEqual(
                                pending_preview["progress_sha256"],
                                third_advanced["progress_sha256"])
                            self.assertFalse(
                                pending_preview[
                                    "native_pending_ack_authorized"])
                            self.assertFalse(
                                pending_preview["native_cleanup_authorized"])
                            self.assertFalse(
                                pending_preview["generation_retired"])
                            user_row = next(
                                x for x in pending_preview["profiles"]
                                if x["native_number"] == user_num)
                            self.assertEqual(
                                user_row["status"],
                                "covered-old-pending-no-ACK")
                            self.assertEqual(
                                user_row["unprocessed_old_bytes"], 0)
                            self.assertEqual(
                                user_row["unprocessed_new_bytes"], 0)
                            self.assertEqual(
                                pending_retirement(), pending_preview)
                            self.assertEqual(
                                {p: p.read_bytes() for p in observed_files},
                                observed_files)
                            with self.assertRaises(V2OriginalConfigRefused):
                                pending_retirement(
                                    inspect_witness=lambda *_a, **_kw:
                                        FDState.BUSY)
                            with self.assertRaises(V2OriginalConfigRefused):
                                prepare_native_ack(
                                    inspect_witness=lambda *_a, **_kw:
                                        FDState.BUSY)
                            # STEP 11: original write-once N ACK-prep
                            # receipts, aggregate manifest LAST.
                            ack_folder = third_slot / "pending-ack-prepare"
                            ack_crashed = [False]
                            def crash_after_first_ack_N(
                                    folder, name, data, uid):
                                normal_original_write_once(
                                    folder, name, data, uid)
                                if (folder.name == "pending-ack-prepare"
                                        and name != "manifest.json"
                                        and not ack_crashed[0]):
                                    ack_crashed[0] = True
                                    raise RuntimeError(
                                        "synthetic_native_pending_ack_N_fsync")
                            with patch(
                                    "auto_detect_epoch_receipts._write_once",
                                    side_effect=crash_after_first_ack_N):
                                with self.assertRaisesRegex(
                                        RuntimeError,
                                        "synthetic_native_pending_ack_N_fsync"):
                                    prepare_native_ack()
                            self.assertTrue(ack_crashed[0])
                            self.assertTrue(ack_folder.is_dir())
                            self.assertFalse(
                                (ack_folder / "manifest.json").exists())
                            self.assertEqual(
                                len(list(ack_folder.iterdir())), 1)
                            manifest_crashed = [False]
                            def crash_after_ack_manifest(
                                    folder, name, data, uid):
                                normal_original_write_once(
                                    folder, name, data, uid)
                                if (folder.name == "pending-ack-prepare"
                                        and name == "manifest.json"
                                        and not manifest_crashed[0]):
                                    manifest_crashed[0] = True
                                    raise RuntimeError(
                                        "synthetic_native_pending_ack_manifest_fsync")
                            with patch(
                                    "auto_detect_epoch_receipts._write_once",
                                    side_effect=crash_after_ack_manifest):
                                with self.assertRaisesRegex(
                                        RuntimeError,
                                        "synthetic_native_pending_ack_manifest_fsync"):
                                    prepare_native_ack()
                            self.assertTrue(manifest_crashed[0])
                            self.assertTrue(
                                (ack_folder / "manifest.json").exists())
                            prepared_ack = prepare_native_ack()
                            self.assertEqual(
                                prepared_ack["profiles_count"], 2)
                            self.assertFalse(
                                prepared_ack["pending_released"])
                            self.assertFalse(
                                prepared_ack["native_pending_ack_authorized"])
                            self.assertFalse(
                                prepared_ack["native_cleanup_authorized"])
                            self.assertFalse(
                                prepared_ack["generation_retired"])
                            frozen_ack = {
                                p.name: p.read_bytes()
                                for p in ack_folder.iterdir()}
                            self.assertEqual(
                                len(frozen_ack), 3)
                            self.assertEqual(
                                prepare_native_ack(), prepared_ack)
                            self.assertEqual(
                                {p.name: p.read_bytes()
                                 for p in ack_folder.iterdir()}, frozen_ack)
                            self.assertEqual(
                                {p: p.read_bytes() for p in observed_files},
                                observed_files)
                            self.assertEqual(
                                queue.segments(),
                                [youtube_pending, user_pending])
                            self.assertEqual(
                                seal_third_slot(), third)
                            self.assertEqual(
                                advance_third_cursor(), third_advanced)
                            # STEP 12: physical P2a pending ARCHIVE, no
                            # unlink of an old source inode. One N moves,
                            # crashes after rename+fsync, another call
                            # recovers from the original immutable plan.
                            archive_folder = (
                                third_slot / "pending-ack-archive")
                            from auto_detect_original_native_archive import (
                                _move_original_pending as original_move,
                            )
                            failed_move = [False]
                            def move_then_fail(source, destination):
                                original_move(source, destination)
                                if not failed_move[0]:
                                    failed_move[0] = True
                                    raise RuntimeError(
                                        "synthetic_native_archive_after_first_rename")
                            with patch(
                                    "auto_detect_original_native_archive._move_original_pending",
                                    side_effect=move_then_fail):
                                with self.assertRaisesRegex(
                                        RuntimeError,
                                        "synthetic_native_archive_after_first_rename"):
                                    archive_pending()
                            self.assertTrue(failed_move[0])
                            self.assertEqual(len(queue.segments()), 1)
                            self.assertTrue(
                                (archive_folder / "manifest.json").exists())
                            archived_result = archive_pending()
                            self.assertEqual(
                                archived_result["profiles_archived"], 2)
                            self.assertTrue(
                                archived_result["pending_relocated"])
                            self.assertTrue(
                                archived_result["pending_bytes_preserved"])
                            self.assertFalse(
                                archived_result[
                                    "native_pending_ack_authorized"])
                            self.assertFalse(
                                archived_result["archive_unlink_authorized"])
                            self.assertFalse(
                                archived_result["generation_retired"])
                            self.assertEqual(queue.segments(), [])
                            self.assertEqual(
                                archive_pending(), archived_result)
                            self.assertEqual(seal_third_slot(), third)
                            self.assertEqual(
                                advance_third_cursor(), third_advanced)
                            self.assertEqual(
                                pending_retirement(), pending_preview)
                            self.assertEqual(
                                (archive_folder / f"{youtube_num:03d}.txt").read_bytes(),
                                observed_files[youtube_pending])
                            self.assertEqual(
                                (archive_folder / f"{user_num:03d}.txt").read_bytes(),
                                observed_files[user_pending])
                            self.assertEqual(
                                user_native.read_bytes(),
                                observed_files[user_native])
                            # STEP 14: original final release remains
                            # BLOCKED although queue.pending is empty:
                            # first/second/third history still opens the
                            # exact archived old inode for replay.
                            release_preview = archive_release_preview()
                            self.assertTrue(
                                release_preview[
                                    "archive_relocation_qualified"])
                            self.assertTrue(
                                release_preview[
                                    "archive_required_for_original_replay"])
                            self.assertFalse(
                                release_preview[
                                    "source_independent_replay_available"])
                            self.assertFalse(
                                release_preview["archive_unlink_authorized"])
                            self.assertFalse(
                                release_preview[
                                    "native_pending_ack_authorized"])
                            self.assertFalse(
                                release_preview["generation_retired"])
                            self.assertEqual(
                                release_preview["profiles_count"], 2)
                            self.assertEqual(
                                release_preview["release_blocker"],
                                "first_second_third_original_replay_requires_old_inode")
                            self.assertEqual(
                                archive_release_preview(), release_preview)
                            with self.assertRaises(V2OriginalConfigRefused):
                                archive_release_preview(
                                    inspect_witness=lambda *_a, **_kw:
                                        FDState.BUSY)
                            self.assertEqual(queue.segments(), [])
                            # The audit creates NO release marker/ACK
                            # and never changes the original source bytes.
                            self.assertFalse(
                                (third_slot /
                                 "archive-release-ready.json").exists())
                            self.assertEqual(
                                (archive_folder / f"{youtube_num:03d}.txt").read_bytes(),
                                observed_files[youtube_pending])
                            self.assertEqual(
                                (archive_folder / f"{user_num:03d}.txt").read_bytes(),
                                observed_files[user_pending])
                            # STEP 15a: create a write-once ALL-N historical
                            # source image under the SAME protected archive.
                            # A crash before its final manifest is resumable.
                            history_root = archive_folder / "history"
                            from unittest.mock import patch as patch_history
                            import auto_detect_original_history as history_module
                            saved_write_once = history_module._write_once
                            history_crashed = [False]
                            def crash_on_first_history_chunk(folder, name, raw, uid):
                                saved_write_once(folder, name, raw, uid)
                                if name == "00000.bin" and not history_crashed[0]:
                                    history_crashed[0] = True
                                    raise RuntimeError("synthetic_history_chunk_crash")
                            with patch_history(
                                    "auto_detect_original_history._write_once",
                                    side_effect=crash_on_first_history_chunk):
                                with self.assertRaisesRegex(
                                        RuntimeError, "synthetic_history_chunk_crash"):
                                    seal_independent_history()
                            self.assertTrue(history_crashed[0])
                            self.assertFalse(
                                (history_root / "manifest.json").exists())
                            history_sealed = seal_independent_history()
                            self.assertEqual(
                                history_sealed["profiles_sealed"], 2)
                            self.assertFalse(history_sealed[
                                "source_independent_transaction_replay_available"])
                            self.assertFalse(history_sealed[
                                "archive_unlink_authorized"])
                            self.assertEqual(
                                seal_independent_history(), history_sealed)
                            history_image = read_independent_history()
                            self.assertEqual(
                                history_image["old_images"][youtube_num],
                                observed_files[youtube_pending])
                            self.assertEqual(
                                history_image["old_images"][user_num],
                                observed_files[user_pending])
                            self.assertFalse(history_image[
                                "archive_unlink_authorized"])
                            chunk = history_root / f"{youtube_num:03d}" / "00000.bin"
                            chunk_original = chunk.read_bytes()
                            chunk.write_bytes(b"forged-history.example.net\n")
                            with self.assertRaises(V2OriginalConfigRefused):
                                read_independent_history()
                            # Only disposable test fixtures restore contents.
                            chunk.write_bytes(chunk_original)
                            self.assertEqual(
                                read_independent_history(), history_image)
                            self.assertEqual(
                                archive_release_preview(), release_preview)
                            committed_wal = preview_independent_wal()
                            self.assertTrue(committed_wal[
                                "all_three_original_wal_checkpoints_verified"])
                            self.assertTrue(committed_wal[
                                "third_destination_postimages_verified"])
                            self.assertFalse(committed_wal[
                                "source_independent_transaction_replay_available"])
                            self.assertFalse(committed_wal[
                                "archive_unlink_authorized"])
                            self.assertEqual(
                                preview_independent_wal(), committed_wal)
                            with self.assertRaises(V2OriginalConfigRefused):
                                preview_independent_wal(
                                    inspect_witness=lambda *_a, **_kw:
                                        FDState.BUSY)
                            # A corrupt committed checkpoint is a hard
                            # refusal, not a reason to re-run P1 or rewrite.
                            checkpoint_path = (
                                third_slot / "destination" / "checkpoint.json")
                            checkpoint_original = checkpoint_path.read_bytes()
                            checkpoint_path.write_bytes(b"{}\n")
                            try:
                                with self.assertRaises(V2OriginalConfigRefused):
                                    preview_independent_wal()
                            finally:
                                checkpoint_path.write_bytes(checkpoint_original)
                            self.assertEqual(
                                preview_independent_wal(), committed_wal)
                            # STEP 15b2a: the source-only WAL reader
                            # knows the latest SHA of EVERY destination,
                            # but older first/second last-writers lack
                            # final physical inode pins. One write-once
                            # receipt now binds all current final identities
                            # BEFORE any old source could be unlinked.
                            from unittest.mock import patch as patch_postimages
                            import auto_detect_original_history_postimages as pim
                            final_postimage_path = (
                                history_root / "postimages.json")
                            saved_postimage_write = pim._write_once
                            postimage_crashed = [False]
                            def crash_after_postimage_receipt(
                                    folder, name, data, uid):
                                saved_postimage_write(folder, name, data, uid)
                                if (name == "postimages.json" and
                                        not postimage_crashed[0]):
                                    postimage_crashed[0] = True
                                    raise RuntimeError(
                                        "synthetic_postimage_after_durable_receipt")
                            with patch_postimages(
                                    "auto_detect_original_history_postimages._write_once",
                                    side_effect=crash_after_postimage_receipt):
                                with self.assertRaisesRegex(
                                        RuntimeError,
                                        "synthetic_postimage_after_durable_receipt"):
                                    seal_independent_postimages()
                            self.assertTrue(postimage_crashed[0])
                            self.assertTrue(final_postimage_path.exists())
                            final_postimages = seal_independent_postimages()
                            self.assertTrue(final_postimages[
                                "all_final_destinations_inode_pinned"])
                            self.assertTrue(final_postimages[
                                "all_three_original_wal_checkpoints_verified"])
                            self.assertFalse(final_postimages[
                                "source_independent_transaction_replay_available"])
                            self.assertFalse(final_postimages[
                                "archive_unlink_authorized"])
                            self.assertEqual(
                                seal_independent_postimages(), final_postimages)
                            self.assertEqual(
                                read_independent_postimages(), final_postimages)
                            self.assertEqual(
                                read_independent_history(), history_image)
                            with self.assertRaises(V2OriginalConfigRefused):
                                read_independent_postimages(
                                    inspect_witness=lambda *_a, **_kw:
                                        FDState.BUSY)
                            # No inode swap is needed to prove that a
                            # foreign postimage witness is refused. Inject a
                            # same-content, changed inode observation ONLY
                            # at the read-only witness boundary, leaving
                            # real Found/managed inode metadata untouched.
                            actual_observer = pim._read_original_wal_once
                            def changed_postimage_identity(*args, **kwargs):
                                witness = actual_observer(*args, **kwargs)
                                copied = dict(witness)
                                rows = dict(witness["destination_witnesses"])
                                self.assertTrue(rows)
                                key = sorted(rows)[0]
                                path, sha, identity, sequence = rows[key]
                                identity = (
                                    identity[0], identity[1] + 1,
                                    *identity[2:])
                                rows[key] = (path, sha, identity, sequence)
                                copied["destination_witnesses"] = rows
                                return copied
                            with patch_postimages(
                                    "auto_detect_original_history_postimages._read_original_wal_once",
                                    side_effect=changed_postimage_identity):
                                with self.assertRaises(V2OriginalConfigRefused):
                                    read_independent_postimages()
                            # A corrupted postimage receipt is rejected,
                            # including after it was durably sealed.
                            postimage_original = (
                                final_postimage_path.read_bytes())
                            final_postimage_path.write_bytes(b"{}\n")
                            try:
                                with self.assertRaises(V2OriginalConfigRefused):
                                    read_independent_postimages()
                            finally:
                                final_postimage_path.write_bytes(
                                    postimage_original)
                            self.assertEqual(
                                read_independent_postimages(), final_postimages)
                            positive_baseline = preview_independent_positive()
                            self.assertTrue(positive_baseline[
                                "new_positive_debug_attribution_verified"])
                            self.assertEqual(
                                positive_baseline["positive_event_count"], 0)
                            self.assertFalse(positive_baseline[
                                "archive_unlink_authorized"])
                            self.assertFalse(positive_baseline[
                                "native_pending_ack_authorized"])
                            with self.assertRaises(V2OriginalConfigRefused):
                                preview_independent_positive(
                                    inspect_witness=lambda *_a, **_kw:
                                        FDState.BUSY)
                            # STEP 15b3h2a: genuinely append native+debug
                            # after THIRD P1, while the prior pinned
                            # Found/managed remain intact. This is a source
                            # WAL only; the STOPPED owner cannot write it.
                            # No real dvtws2/Config FD owner is claimed by
                            # this disposable native-fixture injection.
                            import auto_detect_original_history_running_late as rl
                            from unittest.mock import patch as late_patch
                            saved_live_before = user_native.read_bytes()
                            saved_debug_before = debug_path.read_bytes()
                            late_slot = third_slot.parent / "00000003"
                            self.assertFalse(late_slot.exists())
                            def run_late(*, owner_proof=proof, witness=drained):
                                with writer.exclusive_targets(), patch(
                                        "auto_detect_original_v2_model.COMMON_ACTIVE",
                                        active_root), late_patch(
                                        "auto_detect_original_history_running_late.attest_learning_running_generation",
                                        return_value=owner_proof):
                                    return rl.prepare_original_learning_running_late_source_locked(
                                        writer, proof, self.work,
                                        config_fd=cfg_fd, config_path=config_path,
                                        attest=lambda: proof, inspect=witness)
                            with self.assertRaises(V2OriginalConfigRefused):
                                run_late()
                            self.assertFalse(late_slot.exists())
                            late_name = "www.fourth-boundary.com"
                            later_name = "www.fifth-boundary.org"
                            try:
                                with user_native.open("ab") as stream:
                                    stream.write((late_name + "\n").encode())
                                with debug_path.open("ab") as stream:
                                    stream.write(native_debug(
                                        user_num, late_name, str(user_native)))
                                with self.assertRaises(V2OriginalConfigRefused):
                                    run_late(owner_proof=None)
                                with self.assertRaises(V2OriginalConfigRefused):
                                    run_late(witness=lambda *_a, **_k: FDState.BUSY)
                                self.assertFalse(late_slot.exists())
                                # A failure AFTER the durable source intent
                                # keeps it: exact owner replay must reuse
                                # that receipt, not issue another plan.
                                original_late_write = rl._write_once
                                # An interruption AFTER the durable empty
                                # directory but BEFORE intent publication
                                # must continue on that SAME empty slot.
                                with late_patch.object(
                                        rl, "_write_once",
                                        side_effect=RuntimeError(
                                            "synthetic_before_late_intent")):
                                    with self.assertRaisesRegex(
                                            RuntimeError,
                                            "synthetic_before_late_intent"):
                                        run_late()
                                self.assertTrue(late_slot.is_dir())
                                self.assertEqual(list(late_slot.iterdir()), [])
                                crashed_late = [False]
                                def durable_late_crash(folder, name, raw, uid):
                                    original_late_write(folder, name, raw, uid)
                                    if name == rl.INTENT and not crashed_late[0]:
                                        crashed_late[0] = True
                                        raise RuntimeError(
                                            "synthetic_late_after_source_fsync")
                                with late_patch.object(
                                        rl, "_write_once",
                                        side_effect=durable_late_crash):
                                    with self.assertRaisesRegex(
                                            RuntimeError,
                                            "synthetic_late_after_source_fsync"):
                                        run_late()
                                self.assertTrue(crashed_late[0])
                                late_raw = (late_slot / rl.INTENT).read_bytes()
                                sealed_late = json.loads(late_raw)
                                self.assertEqual(sealed_late["sequence"], 3)
                                self.assertEqual(
                                    sealed_late["native_positive_observations"], [
                                        {"native_number": user_num,
                                         "hostlist": "user",
                                         "hostname": late_name}])
                                self.assertFalse(sealed_late[
                                    "destination_commit_authorized"])
                                self.assertFalse(sealed_late[
                                    "native_pending_ack_authorized"])
                                sealed_result = run_late()
                                self.assertEqual(
                                    sealed_result["source_intent_sha256"],
                                    hashlib.sha256(late_raw).hexdigest())
                                self.assertEqual(
                                    sealed_result["frozen_positive_count"], 1)
                                self.assertFalse(sealed_result[
                                    "p1_destination_checkpoint_created"])
                                self.assertFalse(sealed_result[
                                    "generation_retired"])
                                # Append AFTER the frozen cut must not be
                                # incorporated into its immutable source.
                                with user_native.open("ab") as stream:
                                    stream.write((later_name + "\n").encode())
                                with debug_path.open("ab") as stream:
                                    stream.write(native_debug(
                                        user_num, later_name, str(user_native)))
                                self.assertEqual(run_late(), sealed_result)
                                self.assertEqual(
                                    (late_slot / rl.INTENT).read_bytes(), late_raw)
                                self.assertEqual(len(sealed_late[
                                    "native_positive_observations"]), 1)
                                # Corrupted durable receipt rejects, never
                                # silently overwrites it or writes Found.
                                (late_slot / rl.INTENT).write_bytes(b"{}\n")
                                try:
                                    with self.assertRaises(V2OriginalConfigRefused):
                                        run_late()
                                finally:
                                    (late_slot / rl.INTENT).write_bytes(late_raw)
                                self.assertEqual(run_late(), sealed_result)
                                if getattr(self, "exercise_remaining_new", False):
                                    from auto_detect_effective_known import compose_known
                                    from auto_detect_destination_commit import _edit
                                    def late_live_preview(manual, effects, **context):
                                        owned = {name: targets[name].read_text()
                                                 for name in ("youtube", "user")}
                                        after_owned = {
                                            name: _edit(owned[name].encode(),
                                                effects.get(name, {}).get("add", []),
                                                effects.get(name, {}).get("remove", [])).decode()
                                            for name in owned}
                                        after = compose_known(manual, after_owned)
                                        files = {}
                                        changed = []
                                        for name in owned:
                                            pathname = active_managed / f"hostlist-{name}.txt"
                                            before_bytes = pathname.read_bytes()
                                            if before_bytes != after[name].encode():
                                                changed.append(name)
                                            files[name] = {
                                                "path": str(pathname),
                                                "before_sha256": hashlib.sha256(before_bytes).hexdigest(),
                                                "after_sha256": hashlib.sha256(after[name].encode()).hexdigest()}
                                        return {
                                            "owner_schema": 3, "generation": proof.generation,
                                            "operation": proof.operation_id, "pid": proof.owner.pid,
                                            "started": proof.owner.started, "changed": changed,
                                            "files": files, "commit_authorized": False,
                                            "ack_authorized": False}
                                    def commit_late(exclude="", *, next_cycle=False):
                                        with patch(
                                                "auto_detect_original_v2_model.COMMON_ACTIVE", active_root), patch(
                                                "auto_detect_original_v2_model.preview_live_known_after_readonly",
                                                side_effect=late_live_preview), patch(
                                                "auto_detect_original_history_running_late.attest_learning_running_generation",
                                                return_value=proof):
                                            consumer = (rl.process_original_learning_running_late_once
                                                        if next_cycle else rl.commit_original_learning_running_late)
                                            return consumer(
                                                writer, proof, self.work,
                                                config_fd=cfg_fd, config_path=config_path,
                                                owned_root=owned_dir,
                                                manual_hostlists={"youtube": "youtube.com\n", "user": ""},
                                                global_exclude=exclude, attest=lambda: proof,
                                                inspect=drained, psl=self._tz6v4_psl_for_fixtures())
                                    managed_user = active_managed / "hostlist-user.txt"
                                    before_managed = managed_user.read_bytes()
                                    # The original writer can leave an empty
                                    # destination directory before plan fsync.
                                    # Re-entry must finish that SAME slot.
                                    (late_slot / "destination").mkdir(mode=0o700)
                                    crashed = [False]
                                    def interrupt_found(*args, **kwargs):
                                        real_replace(*args, **kwargs)
                                        if not crashed[0]:
                                            crashed[0] = True
                                            raise DestinationRefused("fourth_found_before_managed")
                                    with patch("auto_detect_destination_commit._replace",
                                               side_effect=interrupt_found):
                                        with self.assertRaises(V2OriginalConfigRefused):
                                            commit_late()
                                    self.assertTrue(crashed[0])
                                    self.assertIn(b"fourth-boundary.com\n", targets["user"].read_bytes())
                                    self.assertNotIn(b"fifth-boundary.org\n", targets["user"].read_bytes())
                                    self.assertEqual(managed_user.read_bytes(), before_managed)
                                    self.assertFalse((late_slot / "destination/checkpoint.json").exists())
                                    plan_bytes = (late_slot / "destination/plan.json").read_bytes()
                                    forged_plan = json.loads(plan_bytes)
                                    forged_plan["writes"]["user"]["before_inode"] += 1
                                    (late_slot / "destination/plan.json").write_bytes(_canonical(forged_plan))
                                    try:
                                        with self.assertRaises(V2OriginalConfigRefused):
                                            commit_late()
                                    finally:
                                        (late_slot / "destination/plan.json").write_bytes(plan_bytes)
                                    with self.assertRaises(V2OriginalConfigRefused):
                                        commit_late("fourth-boundary.com\n")
                                    completed_late = commit_late()
                                    self.assertEqual(completed_late["pending_name"], "learning-00000003")
                                    self.assertFalse(completed_late["ack_authorized"])
                                    self.assertIn(b"fourth-boundary.com\n", managed_user.read_bytes())
                                    self.assertNotIn(b"fifth-boundary.org\n", managed_user.read_bytes())
                                    self.assertEqual((late_slot / "destination/plan.json").read_bytes(), plan_bytes)
                                    self.assertEqual(commit_late(), completed_late)
                                    self.assertEqual((late_slot / rl.INTENT).read_bytes(), late_raw)
                                    self.assertTrue(user_native.read_bytes().endswith((later_name + "\n").encode()))
                                    self.assertTrue((late_slot / "cursor-progress.json").exists())
                                    # Old receipts stay immutable, but lawful fourth
                                    # CAS postimages must no longer poison history.
                                    continued_postimages = read_independent_postimages()
                                    self.assertEqual(continued_postimages["postimages_sha256"],
                                                     final_postimages["postimages_sha256"])
                                    self.assertTrue(continued_postimages["all_final_destinations_inode_pinned"])
                                    self.assertEqual(continued_postimages["unprocessed_new_native_bytes"],
                                                     len((later_name + "\n").encode()))
                                    self.assertEqual(final_postimage_path.read_bytes(), postimage_original)
                                    with writer.exclusive_targets(), patch(
                                            "auto_detect_original_v2_model.COMMON_ACTIVE", active_root):
                                        from auto_detect_original_history_stopped import (
                                            _current_original_final_destinations,
                                        )
                                        reconciled = _current_original_final_destinations(
                                            writer, proof, hashlib.sha256(postimage_original).hexdigest())
                                    self.assertTrue(all(state == "exact" for _, state in reconciled))
                                    fifth = commit_late(next_cycle=True)
                                    self.assertEqual(fifth["pending_name"], "learning-00000004")
                                    fifth_slot = late_slot.parent / "00000004"
                                    fifth_intent = json.loads((fifth_slot / rl.INTENT).read_bytes())
                                    self.assertEqual(fifth_intent["observations"], [
                                        {"hostname": later_name, "hostlist": "user"}])
                                    self.assertIn(b"fifth-boundary.org\n", managed_user.read_bytes())
                                    self.assertEqual(read_independent_postimages()["postimages_sha256"],
                                                     final_postimages["postimages_sha256"])
                                    self.assertIsNone(commit_late(next_cycle=True))
                                    self.assertFalse((late_slot.parent / "00000005").exists())
                                    sixth_name = "www.sixth-boundary.net"
                                    with user_native.open("ab") as stream:
                                        stream.write((sixth_name + "\n").encode())
                                    with debug_path.open("ab") as stream:
                                        stream.write(native_debug(user_num, sixth_name, str(user_native)))
                                    sixth = commit_late(next_cycle=True)
                                    self.assertEqual(sixth["pending_name"], "learning-00000005")
                                    self.assertIn(b"sixth-boundary.net\n", managed_user.read_bytes())
                                    self.assertIsNone(commit_late(next_cycle=True))
                                    self.assertEqual(read_independent_postimages()["postimages_sha256"],
                                                     final_postimages["postimages_sha256"])
                                    self.assertEqual(read_independent_postimages()["unprocessed_new_native_bytes"], 0)
                                    # Replaying a committed old source cannot
                                    # resurrect a later GUI deletion. New work
                                    # refuses the changed physical lineage.
                                    target_bytes = targets["user"].read_bytes()
                                    targets["user"].write_bytes(target_bytes.replace(
                                        b"fourth-boundary.com\n", b""))
                                    deleted_bytes = targets["user"].read_bytes()
                                    self.assertEqual(commit_late(), completed_late)
                                    self.assertEqual(targets["user"].read_bytes(), deleted_bytes)
                                    with self.assertRaises(V2OriginalConfigRefused):
                                        commit_late(next_cycle=True)
                                    return
                            finally:
                                # Test fixture only, not production rollback:
                                # restore identical live inode bytes; then
                                # remove the disposable fourth source slot.
                                user_native.write_bytes(saved_live_before)
                                debug_path.write_bytes(saved_debug_before)
                                if late_slot.exists():
                                    shutil.rmtree(late_slot)
                            self.assertFalse(late_slot.exists())
                            self.assertEqual(
                                preview_independent_positive(), positive_baseline)
                            # STEP 15b3a: without a durable all-N guard
                            # the source-independent inspector MUST refuse
                            # even though independent OLD/Found/debug proof
                            # is available. Seal one original write-once
                            # pre-unlink guard; do not perform any unlink.
                            with self.assertRaises(V2OriginalConfigRefused):
                                preview_original_release_guard()
                            import auto_detect_original_history_release_guard as rg
                            from unittest.mock import patch as guard_patch
                            # A genuine owner proof cannot override absent
                            # protected immutable archive journal evidence.
                            with guard_patch(
                                    "auto_detect_original_history_release_guard.attest_learning_running_generation",
                                    return_value=proof):
                                with self.assertRaises(V2OriginalConfigRefused):
                                    preview_original_owner_live()
                            release_path = history_root / "release-guard.json"
                            original_guard_writer = rg._write_once
                            crashed_guard = [False]
                            def crash_after_release_guard(
                                    folder, name, content, uid):
                                original_guard_writer(
                                    folder, name, content, uid)
                                if name == "release-guard.json" and not crashed_guard[0]:
                                    crashed_guard[0] = True
                                    raise RuntimeError(
                                        "synthetic_guard_durable_before_return")
                            with guard_patch(
                                    "auto_detect_original_history_release_guard._write_once",
                                    side_effect=crash_after_release_guard):
                                with self.assertRaisesRegex(
                                        RuntimeError,
                                        "synthetic_guard_durable_before_return"):
                                    seal_original_release_guard()
                            self.assertTrue(crashed_guard[0])
                            sealed_guard = seal_original_release_guard()
                            self.assertEqual(
                                sealed_guard["old_archive_state"], "all-retained")
                            self.assertEqual(
                                sealed_guard["missing_old_native_numbers"], [])
                            self.assertEqual(
                                sorted(sealed_guard["retained_old_native_numbers"]),
                                sorted([youtube_num, user_num]))
                            self.assertFalse(
                                sealed_guard["archive_unlink_authorized"])
                            self.assertFalse(
                                sealed_guard["native_pending_ack_authorized"])
                            self.assertFalse(
                                sealed_guard["physical_old_archive_cleanup_authorized"])
                            self.assertEqual(
                                seal_original_release_guard(), sealed_guard)
                            self.assertEqual(
                                preview_original_release_guard(), sealed_guard)
                            # STEP 15b3d: independently check original
                            # STOPPED schema3 + immutable WAL and guard.
                            # This does not claim physical postimage/current
                            # NEW positive evidence, so permissions stay false.
                            from auto_detect_owner import GenerationRefused
                            from unittest.mock import patch as stop_patch
                            stopped_calls = [0]
                            def genuine_stopped():
                                stopped_calls[0] += 1
                                return proof
                            with stop_patch(
                                    "auto_detect_original_history_stopped.attest_learning_stopped_generation",
                                    side_effect=genuine_stopped):
                                stopped = preview_original_stopped_guard()
                            self.assertEqual(stopped_calls[0], 2)
                            self.assertTrue(stopped[
                                "stopped_original_owner_freshly_reattested"])
                            # STEP 15b3e — all 3 checkpointed CAS are already
                            # committed, so no original post-archive
                            # transaction replay is necessary or safe.
                            from auto_detect_destination_commit import (
                                _target as strict_original_target,
                                DestinationRefused as OriginalTargetRefused,
                            )
                            from types import SimpleNamespace
                            import json as original_json
                            with stop_patch(
                                    "auto_detect_original_history_stopped.attest_learning_stopped_generation",
                                    return_value=proof):
                                original_reconciled = (
                                    preview_original_destination_reconcile())
                            self.assertTrue(original_reconciled[
                                "historical_wal_all_destination_commits_complete"])
                            self.assertFalse(original_reconciled[
                                "post_archive_destination_transaction_replay_required"])
                            self.assertTrue(original_reconciled[
                                "current_destinations_match_original_physical_postimages"])
                            self.assertEqual(original_reconciled[
                                "current_destination_conflicts"], [])
                            self.assertTrue(original_reconciled[
                                "current_final_destinations_inode_pinned"])
                            self.assertEqual(original_reconciled[
                                "current_destinations_checked_count"],
                                stopped["historical_final_destinations_count"])
                            for forbidden in (
                                    "automatic_repair_authorized",
                                    "archive_unlink_authorized",
                                    "native_pending_ack_authorized",
                                    "generation_retired"):
                                self.assertFalse(original_reconciled[forbidden])
                            # Same bytes from DIFFERENT inode is NOT
                            # original final postimage (GUI delete/recreate).
                            original_saved_rows = original_json.loads(
                                final_postimage_path.read_bytes())["destinations"]
                            chosen_row = original_saved_rows[0]
                            chosen_path = Path(chosen_row["path"])
                            def fake_target_same_bytes_new_inode(path, uid):
                                raw, st = strict_original_target(path, uid)
                                if Path(path) == chosen_path:
                                    return raw, SimpleNamespace(
                                        st_dev=st.st_dev, st_ino=st.st_ino + 99,
                                        st_ctime_ns=st.st_ctime_ns,
                                        st_mtime_ns=st.st_mtime_ns,
                                        st_size=st.st_size)
                                return raw, st
                            with stop_patch(
                                    "auto_detect_original_history_stopped.attest_learning_stopped_generation",
                                    return_value=proof), stop_patch(
                                    "auto_detect_original_history_stopped._target",
                                    side_effect=fake_target_same_bytes_new_inode):
                                displaced = preview_original_destination_reconcile()
                            self.assertFalse(displaced[
                                "current_destinations_match_original_physical_postimages"])
                            self.assertFalse(displaced[
                                "current_final_destinations_inode_pinned"])
                            self.assertEqual(displaced[
                                "current_destination_conflicts"], [{
                                    "target": chosen_row["target"], "state": "changed"}])
                            self.assertFalse(displaced["automatic_repair_authorized"])
                            self.assertFalse(displaced["native_pending_ack_authorized"])
                            def fake_target_manual_edit(path, uid):
                                raw, st = strict_original_target(path, uid)
                                if Path(path) == chosen_path:
                                    return raw + b"manually-deleted.example\n", st
                                return raw, st
                            with stop_patch(
                                    "auto_detect_original_history_stopped.attest_learning_stopped_generation",
                                    return_value=proof), stop_patch(
                                    "auto_detect_original_history_stopped._target",
                                    side_effect=fake_target_manual_edit):
                                edited = preview_original_destination_reconcile()
                            self.assertEqual(edited[
                                "current_destination_conflicts"], [{
                                    "target": chosen_row["target"], "state": "changed"}])
                            self.assertFalse(edited["automatic_repair_authorized"])
                            # Missing physical target is a conflict. Only a
                            # genuine FileNotFound error, with no new name
                            # racing into place, may be classified missing.
                            original_path_exists = Path.exists
                            def missing_path_only(path):
                                if path == chosen_path:
                                    return False
                                return original_path_exists(path)
                            def fake_target_missing(path, uid):
                                if Path(path) == chosen_path:
                                    try:
                                        raise FileNotFoundError(
                                            "simulated_stopped_gui_delete")
                                    except FileNotFoundError as exc:
                                        raise OriginalTargetRefused(
                                            "destination_read_failed") from exc
                                return strict_original_target(path, uid)
                            with stop_patch(
                                    "auto_detect_original_history_stopped.attest_learning_stopped_generation",
                                    return_value=proof), stop_patch(
                                    "auto_detect_original_history_stopped._target",
                                    side_effect=fake_target_missing), stop_patch.object(
                                    Path, "exists", new=missing_path_only):
                                missing_gui_file = (
                                    preview_original_destination_reconcile())
                            self.assertEqual(missing_gui_file[
                                "current_destination_conflicts"], [{
                                    "target": chosen_row["target"], "state": "missing"}])
                            self.assertFalse(missing_gui_file["automatic_repair_authorized"])
                            # Changed between two snapshots: refuse, not
                            # claim durable recovery of an old WAL.
                            current_reads = [0]
                            def fake_target_race(path, uid):
                                raw, st = strict_original_target(path, uid)
                                if Path(path) == chosen_path:
                                    current_reads[0] += 1
                                    if current_reads[0] == 2:
                                        return raw + b"changed\n", st
                                return raw, st
                            with stop_patch(
                                    "auto_detect_original_history_stopped.attest_learning_stopped_generation",
                                    return_value=proof), stop_patch(
                                    "auto_detect_original_history_stopped._target",
                                    side_effect=fake_target_race):
                                with self.assertRaisesRegex(
                                        V2OriginalConfigRefused,
                                        "stopped_reconciliation_current_destinations_raced"):
                                    preview_original_destination_reconcile()
                            with stop_patch(
                                    "auto_detect_original_history_stopped.attest_learning_stopped_generation",
                                    return_value=proof), stop_patch(
                                    "auto_detect_original_history_stopped._target",
                                    side_effect=OriginalTargetRefused(
                                        "foreign_or_symlink_destination")):
                                with self.assertRaises(V2OriginalConfigRefused):
                                    preview_original_destination_reconcile()


                            # STEP 15b3f: one original FD9 STOPPED OLD-only
                            # retirement, not operator Stop and NOT all N
                            # native ACK. Test the actual OS unlink helper
                            # separately, then park original OLD inodes
                            # through rename to preserve this larger fixture.
                            import auto_detect_original_history_stop_retirement as sr
                            from unittest.mock import patch as retire_patch
                            def stop_retire(*, identity=proof,
                                            witness=drained):
                                with writer.exclusive_targets(), patch(
                                        "auto_detect_original_v2_model.COMMON_ACTIVE",
                                        active_root), retire_patch(
                                        "auto_detect_original_history_stopped.attest_learning_stopped_generation",
                                        return_value=proof), retire_patch(
                                        "auto_detect_original_history_stop_retirement.attest_learning_stopped_generation",
                                        return_value=identity):
                                    return sr.retire_original_learning_stopped_OLD_locked(
                                        writer, proof, self.work,
                                        config_fd=cfg_fd, config_path=config_path,
                                        attest=lambda: proof, inspect=witness)
                            retire_dir = third_slot / "pending-old-retirement"
                            self.assertFalse(retire_dir.exists())
                            with self.assertRaises(V2OriginalConfigRefused):
                                stop_retire(witness=lambda *_a, **_kw:
                                            FDState.BUSY)
                            self.assertFalse(retire_dir.exists())
                            original_new_bytes = user_native.read_bytes()
                            original_debug_bytes = debug_path.read_bytes()
                            original_found_bytes = {
                                row["path"]: Path(row["path"]).read_bytes()
                                for row in original_saved_rows}
                            # Unlink primitive with one disposable inode:
                            # a BUSY original FD refuses, DRAINED actually
                            # removes the file and fsyncs its directory.
                            primitive_archive = self.root / "test-only-OLD-unlink"
                            primitive_archive.mkdir(mode=0o700)
                            try:
                                imported_guard_rows = original_json.loads(
                                    release_path.read_bytes())["profiles"]
                                source_old = archive_folder / f"{user_num:03d}.txt"
                                dummy_old = primitive_archive / f"{user_num:03d}.txt"
                                import shutil as stop_shutil
                                stop_shutil.copy2(source_old, dummy_old)
                                dummy_old.chmod(0o660)
                                if os.geteuid() == 0:
                                    os.chown(dummy_old, 0, writer_gid)
                                dummy_stat = dummy_old.stat()
                                dummy_row = dict(next(
                                    x for x in imported_guard_rows
                                    if x["native_number"] == user_num))
                                dummy_row.update(
                                    old_device=dummy_stat.st_dev,
                                    old_inode=dummy_stat.st_ino,
                                    old_size=dummy_stat.st_size,
                                    old_mtime_ns=dummy_stat.st_mtime_ns)
                                with retire_patch.object(
                                        sr, "_archive_paths",
                                        return_value=(
                                            third_slot,
                                            third_slot / "pending-ack-prepare",
                                            primitive_archive)):
                                    with self.assertRaises(V2OriginalConfigRefused):
                                        sr._unlink_original_OLD_only(
                                            dummy_old, dummy_row, writer, proof,
                                            lambda *_a, **_k: FDState.BUSY)
                                    self.assertTrue(dummy_old.exists())
                                    sr._unlink_original_OLD_only(
                                        dummy_old, dummy_row, writer, proof,
                                        drained)
                                    self.assertFalse(dummy_old.exists())
                            finally:
                                if dummy_old.exists():
                                    dummy_old.unlink()
                                primitive_archive.rmdir()
                            # No receipt can be published from an unproven
                            # STOPPED owner even with fully retained OLD.
                            with self.assertRaises(V2OriginalConfigRefused):
                                stop_retire(identity=None)
                            self.assertFalse(retire_dir.exists())
                            parked_old_for_restore = {}
                            interrupted = [False]
                            def disposable_OLD_drop(path, row, *_args):
                                backup = self.root / (
                                    "test-only-retired-OLD-%03d.txt" %
                                    row["native_number"])
                                os.rename(path, backup)
                                parked_old_for_restore[row["native_number"]] = (
                                    backup, path)
                                if not interrupted[0]:
                                    interrupted[0] = True
                                    raise RuntimeError(
                                        "synthetic_after_first_old_inode_disappeared")
                            try:
                                with retire_patch.object(
                                        sr, "_unlink_original_OLD_only",
                                        side_effect=disposable_OLD_drop):
                                    with self.assertRaisesRegex(
                                            RuntimeError,
                                            "synthetic_after_first_old_inode_disappeared"):
                                        stop_retire()
                                self.assertTrue(interrupted[0])
                                self.assertEqual(len(parked_old_for_restore), 1)
                                self.assertTrue((retire_dir / "intent.json").exists())
                                self.assertFalse((retire_dir / "complete.json").exists())
                                with retire_patch(
                                        "auto_detect_original_history_stopped.attest_learning_stopped_generation",
                                        return_value=proof):
                                    partial_retirement = (
                                        preview_original_stopped_guard())
                                self.assertEqual(partial_retirement[
                                    "old_archive_state"], "partially-missing")
                                # A changed or missing intent after one
                                # unlink is fatal: never guess a new plan.
                                original_intent = (
                                    retire_dir / "intent.json").read_bytes()
                                (retire_dir / "intent.json").write_bytes(
                                    b"{}\n")
                                try:
                                    with self.assertRaises(V2OriginalConfigRefused):
                                        stop_retire()
                                    self.assertEqual(
                                        len(parked_old_for_restore), 1)
                                finally:
                                    (retire_dir / "intent.json").write_bytes(
                                        original_intent)
                                # Engine/owner reappears between unlink
                                # attempts: do not touch the remaining OLD.
                                with self.assertRaises(V2OriginalConfigRefused):
                                    stop_retire(identity=None)
                                self.assertEqual(len(parked_old_for_restore), 1)
                                with retire_patch.object(
                                        sr, "_unlink_original_OLD_only",
                                        side_effect=disposable_OLD_drop):
                                    retired_old_only = stop_retire()
                                    self.assertEqual(stop_retire(),
                                                     retired_old_only)
                                self.assertTrue(retired_old_only[
                                    "original_OLD_archive_physically_retired"])
                                self.assertEqual(retired_old_only[
                                    "old_archive_state"], "all-missing")
                                self.assertEqual(len(parked_old_for_restore),
                                                 len(proof.learning))
                                self.assertTrue((retire_dir / "complete.json").exists())
                                # STEP 15b3g: still-physical NEW/debug MUST
                                # be assessed separately from OLD retirement.
                                # These are original P2e files, not a daemon
                                # or a real installed owner; only the real
                                # FreeBSD entrypoint can attest STOPPED.
                                import auto_detect_original_history_stop_new as sn
                                def preview_stopped_NEW(*, witness=drained):
                                    with writer.exclusive_targets(), patch(
                                            "auto_detect_original_v2_model.COMMON_ACTIVE",
                                            active_root), retire_patch(
                                            "auto_detect_original_history_stopped.attest_learning_stopped_generation",
                                            return_value=proof), retire_patch(
                                            "auto_detect_original_history_stop_new.attest_learning_stopped_generation",
                                            return_value=proof):
                                        return sn.preview_original_learning_stopped_NEW_tail_locked(
                                            writer, proof, self.work,
                                            config_fd=cfg_fd,
                                            config_path=config_path,
                                            attest=lambda: proof,
                                            inspect=witness)
                                remaining_empty = preview_stopped_NEW()
                                self.assertTrue(remaining_empty[
                                    "original_OLD_archive_physically_retired"])
                                self.assertTrue(remaining_empty[
                                    "all_NEW_native_and_debug_physically_pinned"])
                                self.assertEqual(remaining_empty[
                                    "remaining_new_state"], "no-unread-native-bytes")
                                self.assertEqual(remaining_empty[
                                    "remaining_new_native_bytes"], 0)
                                self.assertEqual(remaining_empty[
                                    "remaining_positive_native_observations"], [])
                                self.assertFalse(remaining_empty[
                                    "native_pending_ack_authorized"])
                                self.assertFalse(remaining_empty[
                                    "generation_retired"])
                                with self.assertRaises(V2OriginalConfigRefused):
                                    preview_stopped_NEW(
                                        witness=lambda *_a, **_kw: FDState.BUSY)
                                # A paired NEW native+debug positive after
                                # the third sealed cut is NOT consumed by
                                # physically completing the OLD archive.
                                # Inject only the protected source reader's
                                # return as a synthetic branch case; do not
                                # mutate live fixture inodes or Found.
                                observed_NEW = sn._positive_snapshot_once(
                                    writer, proof, drained)
                                invented_tail = dict(observed_NEW)
                                invented_tail["native_bytes_after_third"] = (
                                    len(b"fresh.example.net\n"))
                                invented_tail["debug_bytes_after_third"] = 74
                                invented_tail["positive"] = ((
                                    user_num, "user", "fresh.example.net"),)
                                with retire_patch.object(
                                        sn, "_positive_snapshot_once",
                                        return_value=invented_tail):
                                    pending_NEW = preview_stopped_NEW()
                                self.assertEqual(pending_NEW[
                                    "remaining_new_state"], "unconsumed-native-events")
                                self.assertEqual(pending_NEW[
                                    "remaining_positive_native_observations"], [
                                        {"native_number": user_num,
                                         "hostlist": "user",
                                         "hostname": "fresh.example.net"}])
                                self.assertFalse(pending_NEW[
                                    "remaining_new_events_committed_to_found"])
                                self.assertFalse(pending_NEW[
                                    "native_pending_ack_authorized"])
                                # STEP 15b3h1: feed the established
                                # STOPPED positive source to the ORIGINAL
                                # PSL/IDNA/exclude/Found P1 (no new parser,
                                # no WAL writer, no post-STOPPED live owner).
                                # The original fixture has already
                                # committed example.net in user Found.
                                import auto_detect_original_history_stop_p1 as sp
                                def stopped_p1(*, candidate=None, exclude=""):
                                    def preview():
                                        return sp.preview_original_learning_stopped_NEW_p1_locked(
                                            writer, proof, self.work,
                                            config_fd=cfg_fd,
                                            config_path=config_path,
                                            owned_root=owned_dir,
                                            manual_hostlists={
                                                "youtube": "youtube.com\n",
                                                "user": "",
                                            },
                                            global_exclude=exclude,
                                            attest=lambda: proof,
                                            inspect=drained,
                                            psl=self._tz6v4_psl_for_fixtures())
                                    with writer.exclusive_targets(), patch(
                                            "auto_detect_original_v2_model.COMMON_ACTIVE",
                                            active_root), retire_patch(
                                            "auto_detect_original_history_stopped.attest_learning_stopped_generation",
                                            return_value=proof), retire_patch(
                                            "auto_detect_original_history_stop_new.attest_learning_stopped_generation",
                                            return_value=proof):
                                        if candidate is None:
                                            return preview()
                                        with retire_patch.object(
                                                sp,
                                                "preview_original_learning_stopped_NEW_tail_locked",
                                                return_value=candidate):
                                            return preview()
                                no_new_p1 = stopped_p1()
                                self.assertFalse(no_new_p1[
                                    "p1_projection_available"])
                                self.assertEqual(no_new_p1["found_effects"], {})
                                self.assertFalse(no_new_p1[
                                    "native_pending_ack_authorized"])
                                already_found_p1 = stopped_p1(candidate=pending_NEW)
                                self.assertTrue(already_found_p1[
                                    "p1_projection_available"])
                                self.assertEqual(already_found_p1[
                                    "found_effects"], {})
                                self.assertFalse(already_found_p1[
                                    "stopped_p1_wal_checkpoint_created"])
                                # New positive from the already qualified
                                # N/path is distinct from old handled rows:
                                # the sole original P1 proposes correct
                                # eTLD+1 for User and its managed digest.
                                other_NEW = dict(pending_NEW)
                                other_NEW["remaining_positive_native_observations"] = [
                                    {"native_number": user_num,
                                     "hostlist": "user",
                                     "hostname": "late.newbrand.net"}]
                                proposed_new = stopped_p1(candidate=other_NEW)
                                self.assertEqual(proposed_new["found_effects"], {
                                    "user": {"add": ["newbrand.net"], "remove": []}})
                                self.assertEqual(
                                    set(proposed_new["managed_after_sha256"]),
                                    {"youtube", "user"})
                                for forbidden in (
                                        "current_generation_managed_write_authorized",
                                        "stopped_p1_wal_checkpoint_created",
                                        "native_pending_ack_authorized",
                                        "native_cleanup_authorized",
                                        "generation_retired",
                                        "operator_stop_may_be_blocked"):
                                    self.assertFalse(proposed_new[forbidden])
                                excluded_new = stopped_p1(
                                    candidate=other_NEW,
                                    exclude="newbrand.net\n")
                                self.assertEqual(excluded_new["found_effects"], {})
                                foreign_new = dict(other_NEW)
                                foreign_new["remaining_positive_native_observations"] = [
                                    {"native_number": user_num + 77,
                                     "hostlist": "user",
                                     "hostname": "late.newbrand.net"}]
                                with self.assertRaises(V2OriginalConfigRefused):
                                    stopped_p1(candidate=foreign_new)
                                # Distinguish a stable original STOPPED
                                # source from a new native write between
                                # P1 calculation and its final owner proof.
                                with writer.exclusive_targets(), retire_patch.object(
                                        sp, "preview_original_learning_stopped_NEW_tail_locked",
                                        side_effect=[other_NEW, pending_NEW]):
                                    with self.assertRaises(V2OriginalConfigRefused):
                                        sp.preview_original_learning_stopped_NEW_p1_locked(
                                            writer, proof, self.work,
                                            config_fd=cfg_fd,
                                            config_path=config_path,
                                            owned_root=owned_dir,
                                            manual_hostlists={
                                                "youtube": "youtube.com\n",
                                                "user": ""},
                                            global_exclude="",
                                            attest=lambda: proof,
                                            inspect=drained,
                                            psl=self._tz6v4_psl_for_fixtures())
                                # Two different physical snapshots are not
                                # one admissible exact cut.
                                with retire_patch.object(
                                        sn, "_positive_snapshot_once",
                                        side_effect=[observed_NEW, invented_tail]):
                                    with self.assertRaises(V2OriginalConfigRefused):
                                        preview_stopped_NEW()
                                saved_complete = (retire_dir / "complete.json").read_bytes()
                                (retire_dir / "complete.json").write_bytes(b"{}\n")
                                try:
                                    with self.assertRaises(V2OriginalConfigRefused):
                                        preview_stopped_NEW()
                                finally:
                                    (retire_dir / "complete.json").write_bytes(
                                        saved_complete)
                                # A vanished NEW inode must never be treated
                                # as an empty tail or permission to ACK.
                                moved_live = self.root / "test-only-NEW-absent.txt"
                                user_native.rename(moved_live)
                                try:
                                    with self.assertRaises(V2OriginalConfigRefused):
                                        preview_stopped_NEW()
                                finally:
                                    moved_live.rename(user_native)
                                self.assertEqual(preview_stopped_NEW()[
                                    "remaining_new_state"], "no-unread-native-bytes")
                                for field in ("native_pending_ack_authorized",
                                              "generation_retired",
                                              "operator_stop_may_be_blocked",
                                              "new_native_live_files_touched",
                                              "new_native_debug_touched"):
                                    self.assertFalse(retired_old_only[field])
                                self.assertEqual(user_native.read_bytes(),
                                                 original_new_bytes)
                                self.assertEqual(debug_path.read_bytes(),
                                                 original_debug_bytes)
                                self.assertEqual({
                                    row["path"]: Path(row["path"]).read_bytes()
                                    for row in original_saved_rows},
                                    original_found_bytes)
                            finally:
                                # Disposable fixture ONLY: restore the same
                                # original dev/inode by rename and delete
                                # synthetic test receipts. No production
                                # replay ever resurrects an archived OLD.
                                for _, (backup, oldpath) in sorted(
                                        parked_old_for_restore.items()):
                                    backup.rename(oldpath)
                                if retire_dir.exists():
                                    for filename in retire_dir.iterdir():
                                        filename.unlink()
                                    retire_dir.rmdir()
                            with retire_patch(
                                    "auto_detect_original_history_stopped.attest_learning_stopped_generation",
                                    return_value=proof):
                                self.assertEqual(
                                    preview_original_stopped_guard(), stopped)
                            self.assertFalse(retire_dir.exists())

                            self.assertTrue(stopped[
                                "all_three_original_historical_wal_checkpoints_verified"])
                            self.assertEqual(stopped["old_archive_state"],
                                             "all-retained")
                            self.assertEqual(
                                stopped["historical_final_postimages_sha256"],
                                final_postimages["postimages_sha256"])
                            for forbidden in (
                                    "current_new_native_and_debug_verified",
                                    "current_final_destinations_inode_pinned",
                                    "new_positive_debug_attribution_verified",
                                    "archive_unlink_authorized",
                                    "native_pending_ack_authorized",
                                    "generation_retired",
                                    "physical_old_archive_cleanup_authorized",
                                    "source_independent_transaction_replay_available",
                                    "owner_lifecycle_mutation_authorized"):
                                self.assertIs(stopped[forbidden], False)
                            with stop_patch(
                                    "auto_detect_original_history_stopped.attest_learning_stopped_generation",
                                    return_value=proof):
                                self.assertEqual(preview_original_stopped_guard(),
                                                 stopped)
                                with self.assertRaises(V2OriginalConfigRefused):
                                    preview_original_stopped_guard(
                                        inspect_witness=lambda *_a, **_kw:
                                            FDState.BUSY)
                            with stop_patch(
                                    "auto_detect_original_history_stopped.attest_learning_stopped_generation",
                                    side_effect=GenerationRefused(
                                        "engine_is_running")):
                                with self.assertRaises(V2OriginalConfigRefused):
                                    preview_original_stopped_guard()
                            with stop_patch(
                                    "auto_detect_original_history_stopped.attest_learning_stopped_generation",
                                    side_effect=(proof, None)):
                                with self.assertRaises(V2OriginalConfigRefused):
                                    preview_original_stopped_guard()
                            # Mock STOPPED engine file teardown in
                            # disposable fixture: move, never unlink.
                            # The source-only STOPPED join must not
                            # reopen disappearing live NEW/debug paths.
                            moved_new = self.root / "test-only-stopped-new.txt"
                            moved_debug = self.root / "test-only-stopped-debug.log"
                            user_native.rename(moved_new)
                            debug_path.rename(moved_debug)
                            try:
                                with stop_patch(
                                        "auto_detect_original_history_stopped.attest_learning_stopped_generation",
                                        return_value=proof):
                                    self.assertEqual(
                                        preview_original_stopped_guard(),
                                        stopped)
                                    self.assertEqual(
                                        preview_original_destination_reconcile(),
                                        original_reconciled)
                                with self.assertRaises(V2OriginalConfigRefused):
                                    preview_original_release_guard()
                            finally:
                                moved_debug.rename(debug_path)
                                moved_new.rename(user_native)
                            # STEP 15b3b: unlike the caller-supplied
                            # original FD9 attest(), this independent gate
                            # calls the real native schema3 process/census
                            # attester twice around the entire archive read.
                            from auto_detect_owner import GenerationRefused
                            owner_checks = [0]
                            def independent_live_owner():
                                owner_checks[0] += 1
                                return proof
                            with guard_patch(
                                    "auto_detect_original_history_release_guard.attest_learning_running_generation",
                                    side_effect=independent_live_owner):
                                fresh = preview_original_owner_live()
                            self.assertEqual(owner_checks[0], 2)
                            self.assertTrue(fresh[
                                "original_running_owner_freshly_reattested"])
                            self.assertFalse(fresh[
                                "owner_lifecycle_mutation_authorized"])
                            self.assertFalse(fresh[
                                "archive_unlink_authorized"])
                            self.assertFalse(fresh[
                                "native_pending_ack_authorized"])
                            self.assertEqual(
                                fresh["old_archive_state"], "all-retained")
                            with guard_patch(
                                    "auto_detect_original_history_release_guard.attest_learning_running_generation",
                                    side_effect=GenerationRefused(
                                        "stopped_original_generation")):
                                with self.assertRaises(V2OriginalConfigRefused):
                                    preview_original_owner_live()
                            # Cleanup preflight's stopped-owner refusal
                            # cannot break operator Stop/Restart: original
                            # read-only missing/retained state remains
                            # intact, and NO lifecycle function is called.
                            self.assertEqual(
                                preview_original_release_guard(), sealed_guard)
                            with guard_patch(
                                    "auto_detect_original_history_release_guard.attest_learning_running_generation",
                                    side_effect=(proof, None)):
                                with self.assertRaises(V2OriginalConfigRefused):
                                    preview_original_owner_live()
                            with guard_patch(
                                    "auto_detect_original_history_release_guard.attest_learning_running_generation",
                                    return_value=None):
                                with self.assertRaises(V2OriginalConfigRefused):
                                    preview_original_owner_live()
                            with guard_patch(
                                    "auto_detect_original_history_release_guard.attest_learning_running_generation",
                                    return_value=proof):
                                with self.assertRaises(V2OriginalConfigRefused):
                                    preview_original_owner_live(
                                        inspect_witness=lambda *_a, **_kw:
                                            FDState.BUSY)
                            self.assertEqual(
                                read_independent_history(), history_image)
                            with self.assertRaises(V2OriginalConfigRefused):
                                preview_original_release_guard(
                                    inspect_witness=lambda *_a, **_kw:
                                        FDState.BUSY)
                            # A damaged write-once guard cannot be replaced.
                            guard_backup = release_path.read_bytes()
                            release_path.write_bytes(b"{}\n")
                            try:
                                with stop_patch(
                                        "auto_detect_original_history_stopped.attest_learning_stopped_generation",
                                        return_value=proof):
                                    with self.assertRaises(V2OriginalConfigRefused):
                                        preview_original_stopped_guard()
                                with self.assertRaises(V2OriginalConfigRefused):
                                    preview_original_release_guard()
                                with self.assertRaises(V2OriginalConfigRefused):
                                    seal_original_release_guard()
                            finally:
                                release_path.write_bytes(guard_backup)
                            # Unknown entries in the original archive
                            # cannot silently become a missing N.
                            foreign_guard_entry = archive_folder / "foreign.txt"
                            foreign_guard_entry.write_bytes(b"foreign\n")
                            try:
                                with self.assertRaises(V2OriginalConfigRefused):
                                    preview_original_release_guard()
                            finally:
                                foreign_guard_entry.unlink()
                            self.assertEqual(
                                preview_original_release_guard(), sealed_guard)
                            # Deliberately simulate a missing archived
                            # inode ONLY inside this disposable fixture:
                            # old first/second/third source replay must
                            # refuse, not declare it safe to delete.
                            missing_old = (
                                archive_folder / f"{youtube_num:03d}.txt")
                            # Park outside ALL original journal folders:
                            # a third-slot foreign-file refusal would mask
                            # the actual missing-OLD-inode recovery defect.
                            out_of_tree = (
                                self.root / "test-only-detached-source.txt")
                            missing_old.rename(out_of_tree)
                            try:
                                with self.assertRaisesRegex(
                                        V2OriginalConfigRefused,
                                        "native_archive_old_missing_without_archived_inode"):
                                    archive_release_preview()
                                # Historical bytes remain readable WITHOUT the
                                # OLD archive inode, but original transaction
                                # replay is still safely blocked.
                                self.assertEqual(
                                    read_independent_history(), history_image)
                                # After the archive inode disappears, the
                                # ORIGINAL 3-slot immutable WAL/checkpoint
                                # and current postimages remain independently
                                # inspectable. Original old-inode replay still
                                # has to refuse; NO ACK/unlink is granted.
                                self.assertEqual(
                                    preview_independent_wal(), committed_wal)
                                self.assertEqual(
                                    read_independent_postimages(), final_postimages)
                                # The first physical OLD is absent: inspect
                                # the bounded partial archive rather than
                                # assuming old-source replay can continue.
                                partial_guard = preview_original_release_guard()
                                self.assertEqual(
                                    partial_guard["old_archive_state"],
                                    "partially-missing")
                                with guard_patch(
                                        "auto_detect_original_history_release_guard.attest_learning_running_generation",
                                        return_value=proof):
                                    self.assertEqual(
                                        preview_original_owner_live()[
                                            "old_archive_state"],
                                        "partially-missing")
                                with stop_patch(
                                        "auto_detect_original_history_stopped.attest_learning_stopped_generation",
                                        return_value=proof):
                                    stopped_partial = preview_original_stopped_guard()
                                self.assertEqual(
                                    stopped_partial["old_archive_state"],
                                    "partially-missing")
                                with stop_patch(
                                        "auto_detect_original_history_stopped.attest_learning_stopped_generation",
                                        return_value=proof):
                                    still_reconciled = (
                                        preview_original_destination_reconcile())
                                self.assertEqual(still_reconciled[
                                    "old_archive_state"], "partially-missing")
                                self.assertTrue(still_reconciled[
                                    "current_destinations_match_original_physical_postimages"])
                                self.assertFalse(still_reconciled[
                                    "native_pending_ack_authorized"])
                                self.assertEqual(
                                    stopped_partial["missing_old_native_numbers"],
                                    [youtube_num])
                                self.assertFalse(
                                    stopped_partial["native_pending_ack_authorized"])
                                self.assertEqual(
                                    partial_guard["missing_old_native_numbers"],
                                    [youtube_num])
                                self.assertFalse(
                                    partial_guard["archive_unlink_authorized"])
                                # Deliberately park the second OLD inode as
                                # well, still outside the original journals.
                                user_missing_path = (
                                    archive_folder / f"{user_num:03d}.txt")
                                parked_user_source = (
                                    self.root / "test-only-detached-user.txt")
                                user_missing_path.rename(parked_user_source)
                                try:
                                    all_missing_guard = (
                                        preview_original_release_guard())
                                    self.assertEqual(
                                        all_missing_guard["old_archive_state"],
                                        "all-missing")
                                    with guard_patch(
                                            "auto_detect_original_history_release_guard.attest_learning_running_generation",
                                            return_value=proof):
                                        self.assertEqual(
                                            preview_original_owner_live()[
                                                "old_archive_state"],
                                            "all-missing")
                                    with stop_patch(
                                            "auto_detect_original_history_stopped.attest_learning_stopped_generation",
                                            return_value=proof):
                                        gone = preview_original_stopped_guard()
                                    self.assertEqual(
                                        gone["old_archive_state"], "all-missing")
                                    with stop_patch(
                                            "auto_detect_original_history_stopped.attest_learning_stopped_generation",
                                            return_value=proof):
                                        no_old_reconcile = (
                                            preview_original_destination_reconcile())
                                    self.assertEqual(no_old_reconcile[
                                        "old_archive_state"], "all-missing")
                                    self.assertTrue(no_old_reconcile[
                                        "historical_wal_all_destination_commits_complete"])
                                    self.assertFalse(no_old_reconcile[
                                        "archive_unlink_authorized"])
                                    self.assertFalse(gone["archive_unlink_authorized"])
                                    self.assertEqual(
                                        sorted(all_missing_guard[
                                            "missing_old_native_numbers"]),
                                        sorted([youtube_num, user_num]))
                                    self.assertFalse(
                                        all_missing_guard[
                                            "native_pending_ack_authorized"])
                                finally:
                                    parked_user_source.rename(
                                        user_missing_path)
                                # An identical byte sequence at a *different*
                                # physical inode is not a verified archive.
                                # Disposable fixture only: preserve original
                                # inode by its parked path, then restore it.
                                import shutil as guard_shutil
                                guard_shutil.copy2(out_of_tree, missing_old)
                                try:
                                    with self.assertRaises(
                                            V2OriginalConfigRefused):
                                        preview_original_release_guard()
                                finally:
                                    missing_old.unlink()
                                self.assertEqual(
                                    preview_original_release_guard()[
                                        "old_archive_state"],
                                    "partially-missing")
                                with self.assertRaises(
                                        V2OriginalConfigRefused):
                                    seal_third_slot()
                            finally:
                                out_of_tree.rename(missing_old)
                            self.assertEqual(
                                archive_release_preview(),
                                release_preview)
                            # If an old archive is appended after N=1
                            # was read but while N=2 is being checked,
                            # ALL-N final physical reread must refuse.
                            import auto_detect_original_v2_model as origin_model
                            from unittest.mock import patch as patch_module
                            previous_snap = (
                                origin_model._native_rebind_stable_snapshot)
                            raced_snap = [False]
                            def late_archive_in_first_N(path, *args, **kwargs):
                                result = previous_snap(path, *args, **kwargs)
                                if (path == archive_folder /
                                        f"{user_num:03d}.txt"
                                        and not raced_snap[0]):
                                    raced_snap[0] = True
                                    with (archive_folder /
                                          f"{youtube_num:03d}.txt").open(
                                              "ab", buffering=0) as out:
                                        out.write(
                                            b"late-archive-race.example.net\n")
                                        os.fsync(out.fileno())
                                return result
                            archived_youtube = (
                                archive_folder / f"{youtube_num:03d}.txt")
                            old_stat = archived_youtube.stat()
                            with patch_module(
                                    "auto_detect_original_v2_model._native_rebind_stable_snapshot",
                                    side_effect=late_archive_in_first_N):
                                with self.assertRaises(
                                        V2OriginalConfigRefused):
                                    archive_release_preview()
                            self.assertTrue(raced_snap[0])
                            self.assertIn(
                                b"late-archive-race.example.net\n",
                                archived_youtube.read_bytes())
                            # Test-only restoration, never production
                            # truncate of an original archived source.
                            archived_youtube.write_bytes(
                                observed_files[youtube_pending])
                            os.utime(
                                archived_youtube, ns=(
                                    old_stat.st_atime_ns,
                                    old_stat.st_mtime_ns))
                            self.assertEqual(
                                archive_release_preview(),
                                release_preview)
                            # STEP 13: archived OLD remains covered
                            # while a NEW live native/positive-debug pair
                            # is still unread. Replaying an old cursor or
                            # archive MUST NOT consume, move or remove it.
                            late_live_domain = "post-archive-new.example.net"
                            with user_native.open("ab", buffering=0) as live:
                                live.write(
                                    (late_live_domain + "\n").encode())
                                os.fsync(live.fileno())
                            # Producer appends native AFTER the debug
                            # positive; this inverted/crashed fixture must
                            # REFUSE instead of claiming an unmatched N.
                            with self.assertRaises(V2OriginalConfigRefused):
                                preview_independent_positive()
                            with debug_path.open("ab", buffering=0) as debug:
                                debug.write(native_debug(
                                    user_num, late_live_domain,
                                    learning[1][2]))
                                os.fsync(debug.fileno())
                            positive_late = preview_independent_positive()
                            post_positive_guard = preview_original_release_guard()
                            self.assertEqual(post_positive_guard["positive_event_count"], 1)
                            self.assertEqual(post_positive_guard["old_archive_state"],
                                             "all-retained")
                            self.assertEqual(
                                positive_late["positive_event_count"], 1)
                            self.assertIn(
                                {"native_number": user_num,
                                 "hostlist": "user",
                                 "hostname": late_live_domain},
                                positive_late["positive_native_observations"])
                            self.assertTrue(positive_late[
                                "all_final_destinations_inode_pinned"])
                            self.assertFalse(positive_late[
                                "source_independent_transaction_replay_available"])
                            # No original OLD inode is required even for
                            # a positive NEW append after archival.
                            missing_after_late = (
                                archive_folder / f"{youtube_num:03d}.txt")
                            parked_late = (
                                self.root / "test-only-positive-absent-old.txt")
                            missing_after_late.rename(parked_late)
                            try:
                                self.assertEqual(
                                    preview_independent_positive(),
                                    positive_late)
                                with self.assertRaises(V2OriginalConfigRefused):
                                    archive_release_preview()
                            finally:
                                parked_late.rename(missing_after_late)
                            self.assertEqual(
                                preview_independent_positive(), positive_late)
                            archive_late = pending_retirement()
                            late_user = next(
                                item for item in archive_late["profiles"]
                                if item["native_number"] == user_num)
                            self.assertEqual(
                                late_user["status"],
                                "covered-old-pending-no-ACK")
                            self.assertEqual(
                                late_user["unprocessed_old_bytes"], 0)
                            self.assertGreater(
                                late_user["unprocessed_new_bytes"], 0)
                            archive_live_observations = (
                                preview_late_tails()["native_observations"])
                            self.assertIn({
                                "native_number": user_num,
                                "hostlist": "user",
                                "hostname": late_live_domain,
                            }, archive_live_observations)
                            self.assertEqual(
                                advance_third_cursor(), third_advanced)
                            self.assertEqual(seal_third_slot(), third)
                            self.assertEqual(
                                archive_pending(), archived_result)
                            self.assertEqual(queue.segments(), [])
                            late_release = archive_release_preview()
                            self.assertEqual(
                                late_release["profiles_count"], 2)
                            self.assertFalse(
                                late_release["archive_unlink_authorized"])
                            self.assertGreater(
                                next(x["unprocessed_new_bytes"]
                                     for x in late_release["profiles"]
                                     if x["native_number"] == user_num), 0)
                            with self.assertRaises(V2OriginalConfigRefused):
                                prepare_native_ack()
                            self.assertEqual(
                                (archive_folder / f"{user_num:03d}.txt").read_bytes(),
                                observed_files[user_pending])
                            self.assertIn(
                                (late_live_domain + "\n").encode(),
                                user_native.read_bytes())
                            self.assertFalse(
                                (third_slot / "ack.json").exists())
                            # Native debug writes the positive BEFORE the
                            # native append. A debug-only, crash-interrupted
                            # event must not be accepted as a durable find.
                            orphan_debug_original = debug_path.read_bytes()
                            orphan_name = "post-archive-debug-only.example.net"
                            with debug_path.open("ab", buffering=0) as debug:
                                debug.write(native_debug(
                                    user_num, orphan_name, learning[1][2]))
                                os.fsync(debug.fileno())
                            try:
                                with self.assertRaises(V2OriginalConfigRefused):
                                    preview_independent_positive()
                            finally:
                                # Only disposable test fixtures may restore
                                # a producer file for the next scenario.
                                debug_path.write_bytes(orphan_debug_original)
                            self.assertEqual(
                                preview_independent_positive(), positive_late)
                            # Mismatched N on positive debug is NOT proof
                            # of the new native User observation. Reject
                            # it instead of confirming a YouTube find.
                            new_live_copy = user_native.read_bytes()
                            debug_copy = debug_path.read_bytes()
                            wrong_domain = "post-archive-wrong-n.example.net"
                            with user_native.open("ab", buffering=0) as live:
                                live.write((wrong_domain + "\n").encode())
                                os.fsync(live.fileno())
                            with debug_path.open("ab", buffering=0) as debug:
                                debug.write(native_debug(
                                    youtube_num, wrong_domain,
                                    learning[0][2]))
                                os.fsync(debug.fileno())
                            with self.assertRaises(V2OriginalConfigRefused):
                                preview_independent_positive()
                            with self.assertRaises(V2OriginalConfigRefused):
                                pending_retirement()
                            with self.assertRaises(V2OriginalConfigRefused):
                                archive_pending()
                            self.assertEqual(queue.segments(), [])
                            self.assertEqual(
                                (archive_folder / f"{user_num:03d}.txt").read_bytes(),
                                observed_files[user_pending])
                            # Test-only restoration of the unconfirmed
                            # misattributed pair, NOT a production truncate.
                            user_native.write_bytes(new_live_copy)
                            debug_path.write_bytes(debug_copy)
                            self.assertEqual(
                                archive_pending(), archived_result)
                            self.assertEqual(
                                preview_independent_positive(), positive_late)
                            # Foreign archive entry and a hardlink alias
                            # must NEVER qualify as a root-private N.
                            archived_user = (
                                archive_folder / f"{user_num:03d}.txt")
                            foreign = archive_folder / "shadow-old.txt"
                            os.link(archived_user, foreign)
                            try:
                                with self.assertRaises(V2OriginalConfigRefused):
                                    archive_pending()
                            finally:
                                foreign.unlink()
                            self.assertEqual(
                                archive_pending(), archived_result)
                            # Genuine OLD archive append after its
                            # committed cut invalidates ACK/retirement;
                            # no silent deletion of the late source.
                            with archived_user.open("ab", buffering=0) as old:
                                old.write(b"post-archive-old.example.net\n")
                                os.fsync(old.fileno())
                            with self.assertRaises(V2OriginalConfigRefused):
                                archive_pending()
                            with self.assertRaises(V2OriginalConfigRefused):
                                pending_retirement()
                            self.assertEqual(queue.segments(), [])
                            self.assertIn(
                                b"post-archive-old.example.net\n",
                                archived_user.read_bytes())
                            # Test-only restore before the independent
                            # pre-archive late-tail fixture below; the
                            # immutable production archive is NOT edited.
                            archived_user.write_bytes(
                                observed_files[user_pending])
                            user_native.write_bytes(
                                observed_files[user_native])
                            debug_path.write_bytes(
                                observed_files[debug_path])
                            # Fixture-only reset to continue the legacy
                            # late-append test on physical pending names.
                            for number, pending in (
                                    (youtube_num, youtube_pending),
                                    (user_num, user_pending)):
                                (archive_folder / f"{number:03d}.txt").rename(
                                    pending)
                            (archive_folder / "manifest.json").unlink()
                            # The mirror is test-only; production cleanup is
                            # intentionally NOT implemented or authorized.
                            shutil.rmtree(history_root)
                            archive_folder.rmdir()
                            for receipt in ack_folder.iterdir():
                                receipt.unlink()
                            # Re-pin fixture-only old ctime (rename changed
                            # inode metadata); PRODUCTION never rewrites
                            # original immutable ACK receipts.
                            prepared_ack = prepare_native_ack()
                            frozen_ack = {
                                p.name: p.read_bytes()
                                for p in ack_folder.iterdir()}
                            self.assertEqual(queue.segments(),
                                             [youtube_pending, user_pending])
                            self.assertEqual(seal_third_slot(), third)

                        third_intent_bytes = (
                            third_slot / "intent.json").read_bytes()
                        third_intent = json.loads(third_intent_bytes)
                        self.assertEqual(
                            third_intent["previous_cursor_progress_sha256"],
                            advanced["progress_sha256"])
                        self.assertEqual(
                            third_intent["previous_source_intent_sha256"],
                            advanced["source_intent_sha256"])
                        self.assertEqual(
                            third_intent["observations"],
                            late["observations"])
                        self.assertEqual(
                            third_intent["native_observations"],
                            late["native_observations"])
                        frozen_N = {
                            p.name: p.read_bytes() for p in
                            (third_slot / "native").iterdir()}
                        previous_old = user_pending.read_bytes()
                        previous_live = user_native.read_bytes()
                        previous_debug = debug_path.read_bytes()
                        # New-only late appends are independent from
                        # old-pending cover: they stay UNPROCESSED in live.
                        with user_native.open("ab", buffering=0) as live:
                            live.write(b"post-third-new.example.net\n")
                            os.fsync(live.fileno())
                        with debug_path.open("ab", buffering=0) as debug:
                            debug.write(native_debug(
                                user_num, "post-third-new.example.net",
                                learning[1][2]))
                            os.fsync(debug.fileno())
                        new_only = pending_retirement()
                        user_only = next(
                            x for x in new_only["profiles"]
                            if x["native_number"] == user_num)
                        self.assertEqual(user_only["status"],
                                         "covered-old-pending-no-ACK")
                        self.assertGreater(
                            user_only["unprocessed_new_bytes"], 0)
                        self.assertEqual(
                            user_only["unprocessed_old_bytes"], 0)
                        # Live-only N appends do not alter immutable
                        # old-pending ACK-prep SHA; new live remains unread.
                        self.assertEqual(
                            prepare_native_ack(), prepared_ack)
                        self.assertEqual(
                            {p.name: p.read_bytes()
                             for p in ack_folder.iterdir()}, frozen_ack)
                        # A late write to OLD pending must switch the
                        # disposition to KEEP; the third P1 tip is not
                        # allowed to delete those unread bytes.
                        with user_pending.open("ab", buffering=0) as old:
                            old.write(b"post-third-old.example.net\n")
                            os.fsync(old.fileno())
                        with debug_path.open("ab", buffering=0) as debug:
                            debug.write(native_debug(
                                user_num, "post-third-old.example.net",
                                learning[1][2]))
                            os.fsync(debug.fileno())
                        late_retirement = pending_retirement()
                        late_user = next(
                            x for x in late_retirement["profiles"]
                            if x["native_number"] == user_num)
                        self.assertEqual(
                            late_user["status"], "retained-unprocessed-old")
                        self.assertGreater(
                            late_user["unprocessed_old_bytes"], 0)
                        self.assertGreater(
                            late_user["unprocessed_new_bytes"], 0)
                        with self.assertRaisesRegex(
                                V2OriginalConfigRefused,
                                "learning_pending_ack_unprocessed_old_or_unrotated"):
                            prepare_native_ack()
                        self.assertEqual(
                            {p.name: p.read_bytes()
                             for p in ack_folder.iterdir()}, frozen_ack)
                        self.assertGreaterEqual(
                            late_retirement[
                                "retained_with_unprocessed_old"], 1)
                        self.assertFalse(
                            late_retirement[
                                "native_pending_ack_authorized"])
                        self.assertEqual(
                            queue.segments(),
                            [youtube_pending, user_pending])
                        self.assertEqual(seal_third_slot(), third)
                        self.assertEqual(
                            (third_slot / "intent.json").read_bytes(),
                            third_intent_bytes)
                        self.assertEqual(
                            {p.name: p.read_bytes() for p in
                             (third_slot / "native").iterdir()},
                            frozen_N)
                        self.assertEqual(
                            advance_third_cursor(), third_advanced)
                        self.assertEqual(
                            (third_slot / "cursor-progress.json").read_bytes(),
                            frozen_third_progress)
                        self.assertEqual(
                            pending_retirement(), late_retirement)
                        self.assertGreater(
                            len(preview_late_tails()["observations"]),
                            third["observations_count"])
                        self.assertEqual(seal_second_slot(), second_result)
                        self.assertEqual(advance_second_cursor(), advanced)
                        if third_checkpoint is None:
                            self.assertFalse(
                                (third_slot / "destination").exists())
                        else:
                            self.assertEqual(
                                third_commit_fixture(), third_checkpoint)
                        self.assertFalse(
                            (third_slot / "ack.json").exists())
                        with self.assertRaises(V2OriginalConfigRefused):
                            seal_third_slot(
                                inspect_witness=lambda *_a, **_kw:
                                    FDState.BUSY)
                        with self.assertRaises(V2OriginalConfigRefused):
                            advance_third_cursor(
                                inspect_witness=lambda *_a, **_kw:
                                    FDState.BUSY)
                        # Disposable source-only fixture restoration.
                        user_pending.write_bytes(previous_old)
                        user_native.write_bytes(previous_live)
                        debug_path.write_bytes(previous_debug)
                        self.assertEqual(seal_third_slot(), third)
                        # After write_bytes rewrites the old inode,
                        # same-content ctime/mtime still forbids
                        # re-sealing a different physical ACK witness.
                        with self.assertRaisesRegex(
                                V2OriginalConfigRefused,
                                "learning_pending_ack_prior_inode_witness_changed"):
                            prepare_native_ack()
                        # Exact N is not optional when a YouTube and a
                        # User learning clone detect the same hostname.
                        raw_mix_debug = debug_path.read_bytes()
                        native.write_bytes(b"later-old.alpha.com\n")
                        with debug_path.open("ab", buffering=0) as debug:
                            debug.write(native_debug(
                                youtube_num, "later-old.alpha.com",
                                learning[0][2]))
                            os.fsync(debug.fileno())
                        cross_origin = preview_late_tails()
                        self.assertEqual(
                            {(x["native_number"], x["hostlist"])
                             for x in cross_origin["native_observations"]
                             if x["hostname"] == "later-old.alpha.com"},
                            {(youtube_num, "youtube"), (user_num, "user")})
                        native.write_bytes(b"")
                        debug_path.write_bytes(raw_mix_debug)
                        self.assertEqual(preview_late_tails(), late)
                        self.assertEqual(
                            queue.segments(),
                            [youtube_pending, user_pending])
                        with user_pending.open("ab", buffering=0) as old:
                            old.write(b"raw-without-debug.example.net\n")
                            os.fsync(old.fileno())
                        with self.assertRaises(V2OriginalConfigRefused):
                            preview_late_tails()
                        user_pending.write_bytes(
                            user_pending.read_bytes().replace(
                                b"raw-without-debug.example.net\n", b""))
                        self.assertEqual(preview_late_tails(), late)
                        with self.assertRaises(V2OriginalConfigRefused):
                            preview_late_tails(
                                inspect_witness=lambda *_a, **_k: FDState.BUSY)
                        self.assertFalse(
                            (second_slot / "ack.json").exists())
                        # Completed second P1 is immutable even if the
                        # producer grows BOTH native tails and debug.
                        # Replay cannot re-commit a later minute or
                        # rewrite the managed image.
                        self.assertEqual(
                            forward_commit_fixture(), recovered_second)
                        # Replaying the OLD second checkpoint must NEVER
                        # roll back an already committed THIRD managed
                        # postimage or reapply an older source.
                        self.assertEqual(
                            next_active.read_bytes(), third_after_active)
                        self.assertEqual(
                            third_commit_fixture(), third_checkpoint)
                        self.assertEqual(
                            advance_second_cursor(), advanced)
                        self.assertEqual(
                            (second_slot / "cursor-progress.json").read_bytes(),
                            frozen_progress)
                        self.assertEqual(queue.segments(),
                                         [youtube_pending, user_pending])
                        with self.assertRaises(V2OriginalConfigRefused):
                            advance_second_cursor(
                                inspect_witness=lambda *_a, **_k: FDState.BUSY)
                        before_managed_progress = next_active.read_bytes()
                        next_active.write_bytes(b"foreign.example.net\n")
                        with self.assertRaises(V2OriginalConfigRefused):
                            advance_second_cursor()
                        with self.assertRaises(V2OriginalConfigRefused):
                            advance_third_cursor()
                        next_active.write_bytes(before_managed_progress)
                        self.assertEqual(
                            advance_second_cursor(), advanced)
                        # Same bytes are not the original ctime/mtime.
                        # The third immutable after-inode witness MUST
                        # refuse that GUI restoration, not silently
                        # grant a new logical cursor or a pending ACK.
                        with self.assertRaisesRegex(
                                V2OriginalConfigRefused,
                                "learning_third_progress_postimage_identity_changed"):
                            advance_third_cursor()
                        self.assertEqual(
                            (third_slot / "cursor-progress.json").read_bytes(),
                            frozen_third_progress)
                    # Mutating already sealed old-source prefix MUST
                    # refuse even if the new live inode remains available.
                    former_old_data = user_pending.read_bytes()
                    user_pending.write_bytes(
                        b"forged.example.org\n" +
                        former_old_data[len(b"mail.example.org\n"):])
                    with self.assertRaises(V2OriginalConfigRefused):
                        seal_second_slot()
                    if not sys.platform.startswith("freebsd"):
                        with self.assertRaises(V2OriginalConfigRefused):
                            advance_second_cursor()
                    user_pending.write_bytes(former_old_data)
                    self.assertEqual(seal_second_slot(), second_result)
                    if not sys.platform.startswith("freebsd"):
                        # Disposable fixture cleanup ONLY. No product
                        # recovery removes completed original WAL or
                        # reverts the valid second Found/managed image.
                        targets["user"].write_bytes(b"example.org\n")
                        next_active.write_bytes(before_next)
                        for artifact in (
                                second_slot / "destination").iterdir():
                            artifact.unlink()
                        (second_slot / "destination").rmdir()
                    self.assertFalse((second_slot / "destination").exists())
                    self.assertFalse((second_slot / "ack.json").exists())
                    # Disposable test teardown only: production MUST
                    # preserve the immutable third source journal.
                    if third_slot.exists():
                        # Disposable fixtures only: never delete a
                        # production third source or original WAL.
                        ack_folder = third_slot / "pending-ack-prepare"
                        if ack_folder.exists():
                            for artifact in ack_folder.iterdir():
                                artifact.unlink()
                            ack_folder.rmdir()
                        progress_third = third_slot / "cursor-progress.json"
                        if progress_third.exists():
                            progress_third.unlink()
                        if (third_slot / "destination").exists():
                            for artifact in (
                                    third_slot / "destination").iterdir():
                                artifact.unlink()
                            (third_slot / "destination").rmdir()
                        for receipt in (third_slot / "native").iterdir():
                            receipt.unlink()
                        (third_slot / "intent.json").unlink()
                        (third_slot / "native").rmdir()
                        third_slot.rmdir()
                    # Disposable source-only fixture cleanup, never a
                    # production rollback/unlink of original cursor WAL.
                    progress_file = second_slot / "cursor-progress.json"
                    if progress_file.exists():
                        progress_file.unlink()
                    # Clear late tails without altering the pinned inodes
                    # to continue the independent first-slot test below.
                    user_pending.write_bytes(
                        b"mail.example.org\nlate.example.org\n"
                        b"after-seal-old.example.net\n")
                    user_native.write_bytes(
                        b"late.example.org\nafter-seal-new.example.net\n")
                    debug_path.write_bytes(first_debug + second_debug)
                    for disposable in (second_slot / "native").iterdir():
                        disposable.unlink()
                    (second_slot / "intent.json").unlink()
                    (second_slot / "native").rmdir()
                    second_slot.rmdir()
                    # Post-seal inode reuse/substitution must refuse,
                    # even with byte-identical content and matching tail.
                    saved_live = data_root / ".post-seed-correct-inode"
                    forged_live = data_root / ".post-seed-forged-inode"
                    bytes_live = user_native.read_bytes()
                    user_native.replace(saved_live)
                    forged_live.write_bytes(bytes_live)
                    forged_live.chmod(0o660)
                    if os.geteuid() == 0:
                        os.chown(forged_live, 0, writer_gid)
                    forged_live.replace(user_native)
                    with self.assertRaises(V2OriginalConfigRefused):
                        physical_state()
                    user_native.replace(forged_live)
                    saved_live.replace(user_native)
                    self.assertEqual(
                        physical_state()["profiles"][1]["phase"],
                        "replaced-with-unprocessed-tails")
                    # Only the disposable fixture restores original
                    # native inode names; product may NOT use this to
                    # bypass original pending-tail reconciliation.
                    youtube_pending.replace(native)
                    user_pending.replace(user_native)
                    native.write_bytes(b"video.example.com\n")
                    user_native.write_bytes(
                        b"mail.example.org\nlate.example.org\n")
                    self.assertEqual(queue.segments(), [])
                    with self.assertRaisesRegex(
                            CursorChainRefused,
                            "learning_first_slot_post_inode_seed_requires_forward_cursor"):
                        chain.prepare_learning_first_slot(
                            proof, self.work, attest=lambda: proof,
                            inspect=drained)
                    # DISPOSABLE TEST FIXTURE ONLY: erase synthetic
                    # post-rename observation records after restoring both
                    # old inodes to run the earlier independent source
                    # regression assertions. Production MUST NEVER erase
                    # these write-once receipts or roll a cursor back.
                    for disposable in observed_root.iterdir():
                        disposable.unlink()
                    observed_root.rmdir()
                for changed_exclude in ("example.com\n", "example.org\n"):
                    with self.assertRaises(V2OriginalConfigRefused):
                        compaction_preview(exclude=changed_exclude)
                with self.assertRaises(V2OriginalConfigRefused):
                    compaction_preview(owner_witness=lambda: None)
                # No preflight is allowed to consume / ACK any input or
                # rewrite the native/owned/managed file even when eligible.
                self.assertEqual(user_native.read_bytes(),
                                 b"mail.example.org\nlate.example.org\n")
                self.assertEqual(native.read_bytes(),
                                 b"video.example.com\n")
                self.assertFalse((slot / "ack.json").exists())
                user_native.write_bytes(b"mail.example.org\n")
                # Checkpoint means the original event cannot be reapplied
                # after an explicit GUI deletion of that permanent Found.
                targets["youtube"].write_bytes(b"")
                with self.assertRaises(V2OriginalConfigRefused):
                    compaction_preview()
                if sys.platform.startswith("freebsd"):
                    with writer.exclusive_targets():
                        repeated = writer._locked_commit(
                            slot, persisted, source_raw,
                            p1["p1"]["effects"], live=working)
                else:
                    repeated = commit_with_original_learning_first_slot(
                        writer, proof, self.work,
                        config_fd=cfg_fd, config_path=config_path,
                        owned_root=owned_dir,
                        manual_hostlists={
                            "youtube": "youtube.com\n", "user": ""},
                        global_exclude="", attest=lambda: proof,
                        inspect=drained,
                        psl=self._tz6v4_psl_for_fixtures())
                self.assertEqual(repeated, saved_checkpoint)
                os.close(cfg_fd)
                self.assertEqual(targets["youtube"].read_bytes(), b"")
                self.assertEqual((slot / "intent.json").read_bytes(), durable)
                self.assertFalse((slot / "ack.json").exists())
                # Permanent Found and effective managed MUST have changed
                # during the original CAS; only the physically live native
                # producer/debug sources remain untouched until cleanup.
                for path in (debug_path, native, user_native):
                    self.assertEqual(path.read_bytes(), originals[str(path)])
                with self.assertRaises(CursorChainRefused):
                    chain.prepare_learning_first_slot(
                        proof, self.work, attest=lambda: None,
                        inspect=drained)
                with self.assertRaises(CursorChainRefused):
                    chain.prepare_learning_first_slot(
                        proof, self.work, attest=lambda: proof,
                        inspect=lambda *args, **kwargs: FDState.UNKNOWN)
                # A later native append is NOT a conflict with the
                # original immutable first slot. It remains unprocessed:
                # reattest the original inode/PREFIX and never consume the
                # new suffix before a separately acknowledged next slot.
                with user_native.open("ab") as out:
                    out.write(b"late.example.org\n")
                replayed_slot = chain.prepare_learning_first_slot(
                    proof, self.work, attest=lambda: proof, inspect=drained)
                self.assertEqual(replayed_slot["intent_sha256"],
                                 saved["intent_sha256"])
                self.assertEqual((slot / "intent.json").read_bytes(), durable)
                self.assertEqual(user_native.read_bytes(),
                                 b"mail.example.org\nlate.example.org\n")
                # Same-size in-place corruption of an ALREADY sealed
                # original native prefix must refuse; the queued suffix
                # must not be used to repair or replace that first intent.
                user_native.write_bytes(
                    b"evil.example.org\nlate.example.org\n")
                with self.assertRaises(CursorChainRefused):
                    chain.prepare_learning_first_slot(
                        proof, self.work, attest=lambda: proof,
                        inspect=drained)
                self.assertEqual((slot / "intent.json").read_bytes(), durable)
                user_native.write_bytes(b"mail.example.org\n")

                self.assertTrue(all(row[3] == proof.owner and
                                    row[4] == writer_gid for row in scans))
                for not_drained in (FDState.BUSY, FDState.UNKNOWN, True):
                    with self.subTest(not_drained=not_drained):
                        with self.assertRaises(OriginalSourceRefused):
                            attest_original_learning_drained_candidate_locked(
                                queue, epoch, proof, self.work,
                                attest=lambda: proof,
                                inspect=lambda *args, **kwargs: not_drained)
                # Native writers DO NOT take P2a flock. If one appends while
                # fstat scans, second snapshots must refuse, not checkpoint.
                def append_during_scan(path, *args, **kwargs):
                    if path == native:
                        with user_native.open("ab") as out:
                            out.write(b"racing.example.org\n")
                    return FDState.DRAINED
                with self.assertRaises(OriginalSourceRefused):
                    attest_original_learning_drained_candidate_locked(
                        queue, epoch, proof, self.work,
                        attest=lambda: proof, inspect=append_during_scan)
                user_native.write_bytes(b"mail.example.org\n")
                self.assertEqual((folder / "epoch.json").read_bytes(), epoch_bytes)
                self.assertEqual(native.read_bytes(), b"video.example.com\n")
                self.assertEqual(user_native.read_bytes(), b"mail.example.org\n")

                # A positive emitted before its matching native append
                # cannot create a Found entry. Neither can wrong-profile
                # debug, an incomplete debug window or a stale owner.
                for bad_debug in (
                    first_debug + second_debug +
                        native_debug(learning[0][0], "absent.example.com",
                                     learning[0][2]),
                    native_debug(learning[1][0], "video.example.com",
                                 learning[0][2]) + second_debug,
                    first_debug + second_debug[:-1],
                ):
                    debug_path.write_bytes(bad_debug)
                    with self.assertRaises(OriginalSourceRefused):
                        preview_original_learning_candidates_locked(
                            queue, epoch, proof, self.work,
                            attest=lambda: proof)
                debug_path.write_bytes(first_debug + second_debug)
                with self.assertRaises(OriginalSourceRefused):
                    preview_original_learning_candidates_locked(
                        queue, epoch, proof, self.work,
                        attest=lambda: None)
                self.assertEqual((folder / "epoch.json").read_bytes(), epoch_bytes)
                self.assertEqual(native.read_bytes(), b"video.example.com\n")
                # Native replaced inode is fatal even if its bytes match:
                # a new process must never inherit the original zero cut.
                replacement = data_root / "new-native-inode"
                replacement.write_bytes(b"video.example.com\n")
                replacement.chmod(0o660)
                if os.geteuid() == 0:
                    os.chown(replacement, 0, writer_gid)
                replacement.replace(native)
                with self.assertRaises(ReceiptRefused):
                    epoch.finish_learning_running(
                        proof, queue, workspace=self.work,
                        attest=lambda: proof)
                self.assertEqual((folder / "epoch.json").read_bytes(), epoch_bytes)

    def test_tz6v4_active_source_refuses_forged_found_owner(self):
        mapped, args = self.build(
            "--filter-tcp=443\n<HOSTLIST:youtube>\n--lua-desync=fake\n")
        source = self.check_nonactivating(mapped, args)
        original = args.read_bytes()
        projected, proposal = origin.plan_learning_tier(
            source, original, owner_id=self.work.name,
            owner_candidate_sha256="d" * 64)
        active = {**proposal, "evidence": owner.LEARNING_ACTIVE,
                  "activation_authorized": True}
        check = lambda value: owner._valid_learning_active(
            json.dumps(value).encode(),
            {"id": self.work.name, "candidate": "d" * 64},
            source, original, projected)
        self.assertEqual(check(active)[0][1], "youtube")
        for kind in ("wrong-source", "wrong-final-hash", "wrong-role",
                     "false-active", "observer-proof", "wrong-hostlist"):
            row = json.loads(json.dumps(active))
            learn = next(p for p in row["profiles"] if p["role"] == "learning")
            if kind == "wrong-source":
                learn["source_profile"] = self.work.name + ":777"
            elif kind == "wrong-final-hash":
                row["final_args_sha256"] = "f" * 64
            elif kind == "wrong-role":
                learn["role"] = "working"
            elif kind == "false-active":
                row["activation_authorized"] = False
            elif kind == "observer-proof":
                row["evidence"] = "ORIGINAL_SHARED_GENERATOR_CAPTURE"
            else:
                learn["hostlist"] = "user"
            with self.subTest(kind=kind), self.assertRaises(
                    owner.GenerationRefused):
                check(row)

    def test_tz6v4_mixed_ipset_and_voice_not_learned(self):
        mapped, args = self.build(
            "--filter-tcp=443\n<HOSTLIST:user>\n<IPSET:telegram>\n"
            "--lua-desync=fake\n", voice_on=True)
        source = self.check_nonactivating(mapped, args)
        original = args.read_bytes()
        projected, proposal = origin.plan_learning_tier(
            source, original, owner_id=self.work.name,
            owner_candidate_sha256="d" * 64)
        self.assertEqual(projected, original)
        self.assertFalse(any(p["role"] == "learning"
                             for p in proposal["profiles"]))
        self.assertTrue(any(p["origin_status"] == "excluded-voice"
                            for p in proposal["profiles"]))
        self.assertTrue(any(p["origin_status"] == "excluded-ipset"
                            for p in proposal["profiles"]))
        self.assertNotIn(b"--hostlist-auto=", projected)

    def test_tz6v4_list_mode_has_no_learning(self):
        mapped, args = self.build(
            "--filter-tcp=443\n<HOSTLIST:user>\n--lua-desync=fake\n",
            mode="list")
        # The original generator does not publish an Auto-detect source
        # map outside auto mode and therefore cannot admit learning profiles.
        self.assertFalse(mapped.exists())
        self.assertNotIn(b"--hostlist-auto=", args.read_bytes())
        self.assertFalse((self.release / owner.MAP_NAME).exists())

    def test_tz6v4_resolved_target_and_native_row_are_bound(self):
        mapped, args = self.build(
            "--filter-tcp=443\n<HOSTLIST:youtube>\n--lua-desync=fake\n")
        source = self.check_nonactivating(mapped, args)
        original = args.read_bytes()
        real = next(p for p in source["profiles"] if p["status"] == "known-hostlist")
        self.assertEqual(
            real["native_hostlist_token"],
            source["native_selector_bindings"]["<HOSTLIST:youtube>"])
        self.assertIn(real["native_hostlist_token"].encode(), original)
        for kind in ("row-sha", "native-token", "cross-target"):
            altered = json.loads(json.dumps(source))
            row = next(p for p in altered["profiles"]
                       if p["status"] == "known-hostlist")
            if kind == "row-sha":
                row["native_row_sha256"] = "0" * 64
            elif kind == "native-token":
                row["native_hostlist_token"] = "--hostlist=/tmp/foreign"
            else:
                row["selector"] = "<HOSTLIST:user>"
                row["hostlist"] = "user"
                row["source_selectors"] = ["<HOSTLIST:user>"]
            with self.subTest(kind=kind), self.assertRaises(origin.AttributionError):
                origin.plan_learning_tier(
                    altered, original, owner_id=self.work.name,
                    owner_candidate_sha256="d" * 64)

    def test_tz6v4_original_fd9_preflight_is_read_only(self):
        mapped, args = self.build(
            "--filter-tcp=443\n<HOSTLIST:youtube>\n--lua-desync=fake\n")
        (self.work / "plan.json").write_text(json.dumps({
            "page": "strategies", "candidate": {"general": {"enabled": "1"}},
            "changed_fields": [], "dependencies": "a" * 64,
        }))
        source_before = mapped.read_bytes()
        argv_before = args.read_bytes()
        digest = "d" * 64
        record = origin.preflight_learning_tier(self.work, digest)
        self.assertEqual(
            record["evidence"],
            "TZ6V4_ORIGINAL_FD9_LEARNING_PREFLIGHT_NONACTIVATING")
        self.assertEqual(record["learning_hostlists"], ["youtube"])
        self.assertEqual(record["learning_native_numbers"], [2])
        self.assertEqual(record["native_candidate_sha256"], digest)
        self.assertNotEqual(record["original_args_sha256"],
                            record["proposed_args_sha256"])
        self.assertEqual(args.read_bytes(), argv_before)
        self.assertEqual(mapped.read_bytes(), source_before)
        self.assertFalse((self.release / owner.MAP_NAME).exists())
        self.assertFalse((self.release / "auto-detect-learning-preview.args").exists())
        with self.assertRaises(origin.AttributionError):
            origin.preflight_learning_tier(self.work, "wrong")

    def test_tz6v4_stale_or_forged_source_map_is_refused(self):
        mapped, args = self.build(
            "--filter-tcp=443\n<HOSTLIST:youtube>\n--lua-desync=fake\n")
        source = self.check_nonactivating(mapped, args)
        original = args.read_bytes()
        for field, value in (
            ("final_args_sha256", "0" * 64),
            ("evidence", "P2F_OFFLINE_PLAN_ONLY"),
            ("activation_authorized", True),
            ("generation", "e" * 32),
        ):
            damaged = dict(source, **{field: value})
            with self.subTest(field=field), self.assertRaises(origin.AttributionError):
                origin.plan_learning_tier(
                    damaged, original, owner_id=self.work.name,
                    owner_candidate_sha256="d" * 64)

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

    def test_original_fd9_preview_promotes_once_to_exact_active_schema2(self):
        mapped, args = self.build(
            "--filter-tcp=443\n<HOSTLIST:youtube>\n--lua-desync=fake\n",
            voice_on=True)
        source = self.check_nonactivating(mapped, args)
        old = args.read_bytes()
        (self.work / "plan.json").write_text(json.dumps({
            "page": "strategies", "candidate": {"general": {"enabled": "1"}},
            "changed_fields": [], "dependencies": "a" * 64,
        }))
        digest = "b" * 64
        preview = origin.stage_original_preview(self.work, digest)
        self.assertEqual(origin.verify_original_preview(self.work, digest),
                         preview)
        record = origin.promote_original_preview(self.work, digest)
        self.assertEqual(record["evidence"], "ORIGINAL_SHARED_GENERATOR_CAPTURE")
        self.assertNotIn("activation_authorized", record)
        self.assertNotEqual(old, args.read_bytes())
        self.assertIn(b"--hostlist-auto=/var/db/zapret2-auto-detect/inbox.txt",
                      args.read_bytes())
        self.assertEqual(record, origin.verify_original_promotion(self.work, digest))
        self.assertEqual(source, json.loads(mapped.read_bytes()))
        self.assertEqual(
            owner._valid_map(
                (self.release / owner.MAP_NAME).read_bytes(),
                {"id": self.work.name, "candidate": digest},
                args.read_bytes())[0],
            record)
        self.assertFalse((self.release / "auto-detect-observer-preview.args").exists())
        self.assertFalse((self.release / "auto-detect-observer-preview.json").exists())
        with self.assertRaises(origin.AttributionError):
            origin.promote_original_preview(self.work, digest)
        with self.assertRaises((origin.AttributionError, owner.GenerationRefused)):
            origin.verify_original_promotion(self.work, "c" * 64)
        active = args.read_bytes()
        args.write_bytes(active + b"--new\n")
        with self.assertRaises((origin.AttributionError, owner.GenerationRefused)):
            origin.verify_original_promotion(self.work, digest)

    def test_original_fd9_readonly_authorize_exact_source_and_installed_copy(self):
        mapped, args = self.build(
            "--filter-tcp=443\n<HOSTLIST:youtube>\n--lua-desync=fake\n",
            voice_on=True)
        self.check_nonactivating(mapped, args)
        (self.work / "plan.json").write_text(json.dumps({
            "page": "strategies", "candidate": {"general": {"enabled": "1"}},
            "changed_fields": [], "dependencies": "a" * 64,
        }))
        digest = "b" * 64
        origin.stage_original_preview(self.work, digest)
        origin.promote_original_preview(self.work, digest)
        create_seal(self.work, owner=os.geteuid())
        active_copy = self.root / "active"
        shutil.copytree(self.release, active_copy)
        with patch("shared_apply_seal.WORK", self.root), \
             patch("voice_live_inspect.COMMON_ACTIVE", active_copy):
            # Both pre-journal candidate and copied native release are
            # verified against the same original sealed source and argv.
            post_drop.native_authorize_original_release(self.release)
            post_drop.native_authorize_original_release(active_copy)
            with self.assertRaises(post_drop.PostDropRefused):
                post_drop.native_authorize_original_release(self.root / "other")
            active_args = active_copy / "dvtws.args"
            active_args.write_bytes(active_args.read_bytes() + b"--new\n")
            with self.assertRaises((post_drop.PostDropRefused,
                                    owner.GenerationRefused,
                                    origin.AttributionError)):
                post_drop.native_authorize_original_release(active_copy)
            shutil.copy2(args, active_args)
            # A changed sealed source is never authorized, even if the
            # installed copy is still byte-for-byte the prior good one.
            (self.release / "traffic-user.conf").write_bytes(b"changed\n")
            with self.assertRaises(SharedBundleError):
                post_drop.native_authorize_original_release(active_copy)

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
        self.assertIn('promote "$_shared_work" "$_shared_auto_digest"', body)
        self.assertLess(body.index('promote "$_shared_work" "$_shared_auto_digest"'),
                        body.index("shared_apply_bundle_service seal"))
        begin = service.index("shared_apply_execute_service()\n")
        end = service.index("shared_apply_wan_save_service()\n", begin)
        applied = service[begin:end]
        self.assertLess(applied.index("shared_apply_native_config preflight"),
                        applied.index('auto_detect_origin_map.py" verify-active'))
        self.assertLess(applied.index('auto_detect_origin_map.py" verify-active'),
                        applied.index('shared_apply_record_service prepared'))
        self.assertLess(applied.index('auto_detect_origin_map.py" verify-active'),
                        applied.index('apply_runtime_probe "$_shared_apply_root/release"'))
        self.assertIn("preflight-rejected=observer-generation", applied)
        # Staging now promotes original P2h after native candidate proof;
        # pre-activation source authorization remains independently closed
        # in the original launcher until real producer/FD/epoch qualification.
        self.assertIn('auto_detect_origin_map.py" verify-active', applied)
        self.assertIn('auto-detect-generation.json" ]; then', applied)
        runtime = (BACKEND / "apply_runtime.sh").read_text()
        self.assertIn('auto_detect_post_drop.py" authorize', runtime)
        # The old order was unsafe: a refused epoch left terminal committed.
        # An active schema-2 candidate must remain nonterminal through
        # Config saved/readback, IPFW and final FD9 epoch attestation.
        self.assertLess(applied.index('shared_apply_native_config save'),
                        applied.index('shared_apply_record_current_service epoch-finalizing'))
        # Schema2 uses its original epoch verifier; schema3 uses the
        # separate independently authenticated full N-inbox verifier.
        # Both must finish before the terminal shared Apply record.
        self.assertIn('_shared_epoch_verb=finish-epoch', applied)
        self.assertIn('_shared_epoch_verb=finish-learning-epoch', applied)
        self.assertIn('select(. == 2 or . == 3)', applied)
        finish_call = applied.index('"$_shared_epoch_verb" "$_shared_apply_id"')
        self.assertLess(applied.index('shared_apply_record_current_service epoch-finalizing'),
                        finish_call)
        self.assertLess(finish_call,
                        applied.index('shared_apply_record_current_service committed'))
        self.assertLess(applied.index('apply_runtime_probe "$_shared_apply_root/release"'),
                        finish_call)

    def test_p2f_native_candidate_preview_and_promotion_precede_original_seal(self):
        service = (BACKEND.parent / "zapret_service.sh").read_text()
        begin = service.index("shared_apply_prepare_service()\n")
        end = service.index("extra_resources_native_previous_owner_service()\n", begin)
        stage = service[begin:end]
        # Original P2f preflight was replaced by an authenticated preview
        # then one promotion during build. Neither belongs in the executor
        # after the candidate was already sealed.
        self.assertLess(stage.index('shared_apply_native_config preflight'),
                        stage.index('preview "$_shared_work"'))
        self.assertLess(stage.index('preview "$_shared_work"'),
                        stage.index('promote "$_shared_work"'))
        self.assertLess(stage.index('promote "$_shared_work"'),
                        stage.index('shared_apply_bundle_service seal "$1"'))

        begin = service.index("shared_apply_execute_service()\n")
        end = service.index("shared_apply_wan_save_service()\n", begin)
        execute = service[begin:end]
        self.assertLess(execute.index('shared_apply_native_config preflight'),
                        execute.index('apply_runtime_probe "$_shared_apply_root/release"'))
        self.assertLess(execute.index('apply_runtime_probe "$_shared_apply_root/release"'),
                        execute.index('shared_apply_record_service prepared'))
        self.assertIn('"$_shared_apply_mode" = 1', execute)



if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    if result.wasSuccessful():
        print(MARKER + "=PASS_ORIGINAL_BUILD_NONACTIVATING", flush=True)
    raise SystemExit(0 if result.wasSuccessful() else 1)
