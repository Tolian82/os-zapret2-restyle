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
            with queue.exclusive():
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
                with self.assertRaises(ReceiptRefused):
                    epoch.seal_learning_pretraffic(
                        queue, workspace=self.work,
                        candidate_sha256=candidate, wire=wire,
                        root_gid=root_gid, engine_uid=engine_uid,
                        attest=lambda: True)
                self.assertEqual((folder / "pretraffic.json").read_bytes(), raw)
                self.assertEqual(native.read_bytes(), b"video.example.com\n")

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
        self.assertLess(applied.index('shared_apply_record_current_service epoch-finalizing'),
                        applied.index('finish-epoch "$_shared_apply_id"'))
        self.assertLess(applied.index('finish-epoch "$_shared_apply_id"'),
                        applied.index('shared_apply_record_current_service committed'))
        self.assertLess(applied.index('apply_runtime_probe "$_shared_apply_root/release"'),
                        applied.index('finish-epoch "$_shared_apply_id"'))

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
