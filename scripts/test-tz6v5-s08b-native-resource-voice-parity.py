#!/usr/bin/env python3
"""S08b real native storage rows + original domain/IPSET/Voice producer parity.

No service, FD9, Config, engine, IPFW, runtime or privileged file mutation.
Shell catalog compares original source on disposable test-only files.
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import hashlib
from pathlib import Path
from unittest.mock import patch
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))
from config_projection_opnsense import registered_ids
from neutral_config_model import project
from neutral_target_compiler import parse_original_policy, compile_target_profiles
from neutral_resource_compiler import (parse_original_storage, compile_resources,
                                       compare_original_managed_bytes, ResourceCompileError)
import domain_policy
from domain_policy import normalize
from ipset_policy import parse_ipset
from auto_detect_effective_known import compose_known
from voice_profile_compiler import compile_candidate, SERVICES

REGISTRY = BACKEND / "registry.sh"
STORAGE = BACKEND / "storage.sh"
TARGET_MODE = BACKEND / "target_mode.sh"
ROOT_MANAGED = Path("/tmp/s08b-detached-managed-only")
VOICE_ARGS = (
    "--filter-udp=*\n--filter-l7=stun\n--payload=stun\n"
    "--lua-desync=fake:blob=0x00000000000000000000000000000000:repeats=2"
)


def saved(*, mode="auto", voice_on=False, voice_args=""):
    voices = {name: {} for name in SERVICES}
    voices["telegram"] = {"enabled": "1" if voice_on else "0", "args": voice_args}
    return project({
        "general": {"enabled": "0", "waninterface": "opt0",
                    "divertport": "989"},
        "hostlist": {"mode": mode, "youtubedomains": "OLD_XML_NOT_AUTHORITY"},
        "strategy": {},
        "strategylab": {},
        "voice": voices,
    }, registered_ids(REGISTRY.read_bytes()))


def prepared():
    return {
        "hostlist.youtube": b"example.org\n",
        "hostlist.user": b"",
        "ipset.telegram": b"91.108.0.0/16\n",
        "ipset.discord": b"",
        "ipset.x": b"",
        "ipset.sip": b"",
        "ipset.custom": b"",
        "hostlist.exclude": b"",
        "ipset.exclude": b"",
    }


def targeted(model=None, strategy=b"--filter-tcp=443\n<HOSTLIST:youtube>\n--lua-desync=fake\n"):
    model = saved() if model is None else model
    return compile_target_profiles(model, strategy,
                                   parse_original_policy(TARGET_MODE.read_bytes()))


def preview(model=None, texts=None, owned=None, *, strategy=None, runtime_auto=None):
    model = saved() if model is None else model
    texts = prepared() if texts is None else texts
    targets = targeted(model) if strategy is None else targeted(model, strategy)
    return compile_resources(model, targets,
                             parse_original_storage(STORAGE.read_bytes()),
                             texts, owned, runtime_auto=runtime_auto,
                             voice_managed_root=ROOT_MANAGED)


class S08bNativeProducerParity(unittest.TestCase):
    def test_original_shell_storage_catalog_exact_byte_parity(self):
        source = parse_original_storage(STORAGE.read_bytes())
        self.assertEqual(len(source.entries), len(registered_ids(REGISTRY.read_bytes())))
        with tempfile.TemporaryDirectory(prefix="s08b-catalog-") as tmp:
            out = Path(tmp) / "catalog.tsv"
            script = """set -eu
common_error() { printf '%s\\n' "$*" >&2; }
. "$1"
storage_catalog_build "$2"
"""
            native = subprocess.run(
                ["/bin/sh", "-c", script, "s08b", str(STORAGE), str(out)],
                capture_output=True, text=True, timeout=15, check=False)
            self.assertEqual(native.returncode, 0,
                             "original shell storage catalog refused")
            expected = "".join(
                f"{item.storage_key}\t{item.provider}\t{item.locator}\n"
                for item in source.entries)
            self.assertEqual(out.read_text(), expected)

    def test_empty_manual_plus_proven_known_is_effectively_nonempty(self):
        raw = prepared()
        raw["hostlist.youtube"] = b""
        owned = {"youtube": b"example.org\n", "user": b""}
        got = preview(texts=raw, owned=owned)
        youtube = next(x for x in got.resources if x.name == "youtube")
        self.assertEqual((youtube.state, youtube.linked, youtube.entry_count),
                         ("READY", True, 1))
        self.assertEqual(got.manual_known_empty, ("youtube", "user"))
        self.assertEqual(got.effective_known_empty, ("user",))
        self.assertEqual(got.owned_known_input, "SNAPSHOT_SUPPLIED_NO_AUTHORITY")
        canonical_manual = {"youtube": "", "user": ""}
        original = compose_known(canonical_manual, {
            "youtube": "example.org\n", "user": ""})
        self.assertEqual(youtube.content_sha256,
                         hashlib.sha256(original["youtube"].encode()).hexdigest())
        self.assertEqual(got.authorization, "NONE")
        self.assertFalse(got.physical_transition_allowed)
        with self.assertRaises(FrozenInstanceError):
            got.authorization = "ROOT"

    def test_empty_manual_unlinked_allowed_linked_refuses_without_owned(self):
        raw = prepared()
        raw["hostlist.youtube"] = b""
        with self.assertRaisesRegex(ResourceCompileError, "LINKED_RESOURCE_EMPTY"):
            preview(texts=raw)
        got = preview(texts=raw, strategy=b"")
        youtube = next(x for x in got.resources if x.name == "youtube")
        self.assertEqual(youtube.state, "PRESENT_EMPTY_UNLINKED")
        self.assertEqual(got.owned_known_input, "NO_OWNED_SNAPSHOT_SUPPLIED")
        self.assertEqual(got.effective_known_empty, ("youtube", "user"))

    def test_explicit_optional_auto_empty_is_connectable_but_missing_refuses(self):
        auto_profile = b"--filter-tcp=443\n<HOSTLIST:auto>\n--lua-desync=fake\n"
        with self.assertRaisesRegex(ResourceCompileError, "LINKED_RESOURCE_NOT_PRESENT"):
            preview(strategy=auto_profile)
        result = preview(strategy=auto_profile, runtime_auto=b"")
        auto = next(x for x in result.resources if x.name == "auto")
        self.assertEqual((auto.state, auto.linked, auto.entry_count),
                         ("PRESENT_EMPTY_OPTIONAL", True, 0))
        self.assertEqual(result.status, "DETACHED_INPUT_PREVIEW_ONLY")
        self.assertEqual(next(x for x in preview().resources if x.name == "auto").state,
                         "NOT_SUPPLIED")

    def test_exclude_domains_ipset_switches_and_original_parsers(self):
        none = preview()
        self.assertEqual([(e.kind, e.enabled) for e in none.global_exclusions],
                         [("HOSTLIST", False), ("IPSET", False)])
        raw = prepared()
        raw["hostlist.exclude"] = b"ADs.Example.org\n"
        raw["ipset.exclude"] = b"192.0.2.1\n"
        result = preview(texts=raw)
        self.assertEqual([(e.kind, e.enabled, e.entry_count)
                          for e in result.global_exclusions],
                         [("HOSTLIST", True, 1), ("IPSET", True, 1)])
        host = normalize(raw["hostlist.exclude"].decode(), "exclude")["normalized"] + "\n"
        ipset = parse_ipset(raw["ipset.exclude"], "exclude", collapse=True)[0]
        self.assertEqual(result.global_exclusions[0].content_sha256,
                         hashlib.sha256(host.encode()).hexdigest())
        self.assertEqual(result.global_exclusions[1].content_sha256,
                         hashlib.sha256(ipset.encode()).hexdigest())
        for key, invalid in (("hostlist.exclude", b"!ads.example.org"),
                             ("ipset.exclude", b"0.0.0.0/0"),
                             ("ipset.exclude", b"bad IP")):
            with self.subTest(key=key, invalid=invalid):
                broken = dict(raw, **{key: invalid})
                with self.assertRaises(ResourceCompileError):
                    preview(texts=broken)

    def test_off_voice_preserves_invalid_args_draft_and_on_uses_original_candidate(self):
        off = saved(voice_args="INCOMPLETE PRIVATE DRAFT; NOT NATIVE")
        result = preview(model=off)
        self.assertEqual(result.voice_native_args_sha256, None)
        self.assertFalse(result.voice[0].enabled)
        self.assertEqual(result.voice[0].args_sha256,
                         hashlib.sha256(off.voice[0].args.encode()).hexdigest())
        on = saved(voice_on=True, voice_args=VOICE_ARGS)
        got = preview(model=on)
        self.assertTrue(got.voice[0].enabled)
        self.assertIsNotNone(got.voice[0].native_profile_sha256)
        original_source = {
            "strategy_wan": "opt0",
            "services": {name: {
                "enabled": name == "telegram",
                "args": VOICE_ARGS if name == "telegram" else "",
                "ips": prepared()["ipset."+name].decode(),
            } for name in SERVICES},
        }
        traffic, native = compile_candidate(original_source, ROOT_MANAGED)
        self.assertEqual(got.voice_native_args_sha256,
                         hashlib.sha256(traffic.encode()).hexdigest())
        self.assertEqual(got.voice[0].native_profile_sha256,
                         native["profiles"][0]["profile_sha256"])
        with self.assertRaisesRegex(ResourceCompileError, "VOICE_CANDIDATE_INVALID"):
            preview(model=saved(voice_on=True, voice_args="invalid fake"))
        raw = prepared()
        raw["ipset.telegram"] = b""
        with self.assertRaisesRegex(ResourceCompileError, "VOICE_CANDIDATE_INVALID"):
            preview(model=on, texts=raw)

    def test_invalid_even_disabled_voice_ipset_is_original_batch_refusal(self):
        broken = prepared()
        broken["ipset.discord"] = b"::/0\n"
        with self.assertRaisesRegex(ResourceCompileError, "INVALID_DISCORD_IPSET"):
            preview(texts=broken)
        broken = prepared()
        broken["ipset.telegram"] = b"host.example.org"
        with self.assertRaisesRegex(ResourceCompileError, "INVALID_TELEGRAM_IPSET"):
            preview(model=saved(voice_on=False), texts=broken)

    def test_untrusted_snapshots_and_storage_changes_refuse(self):
        native = STORAGE.read_bytes()
        for tamper in (
            b"no catalog",
            native.replace(b"hostlist.youtube\\tmanaged", b"hostlist.youtube\\tunknown", 1),
            native.replace(b"hostlist.youtube\\tmanaged", b"hostlist.youtube\\truntime", 1),
        ):
            with self.subTest(tamper=hash(tamper)):
                try:
                    bad = parse_original_storage(tamper)
                except ResourceCompileError:
                    continue
                with self.assertRaises(ResourceCompileError):
                    compile_resources(saved(), targeted(), bad, prepared(), None,
                                      voice_managed_root=ROOT_MANAGED)
        for abnormal in (
            {"youtube": b"example.org\n"},
            {"youtube": b"!example.org\n", "user": b""},
            {"youtube": b"EXAMPLE.ORG\n", "user": b""},
            {"youtube": b"example.org", "user": b""},
        ):
            with self.assertRaises(ResourceCompileError):
                preview(owned=abnormal)
        for invalid in (
            {key: value for key, value in prepared().items() if key != "ipset.sip"},
            dict(prepared(), **{"ipset.sip": None}),
            dict(prepared(), **{"hostlist.youtube": b"garbage\x00domain"}),
        ):
            with self.assertRaises(ResourceCompileError):
                preview(texts=invalid)
        with self.assertRaisesRegex(ResourceCompileError, "UNQUALIFIED_RESOURCE_PREVIEW"):
            compile_resources(saved(mode="list"), targeted(saved(mode="auto")),
                parse_original_storage(STORAGE.read_bytes()), prepared(), None,
                voice_managed_root=ROOT_MANAGED)

    def test_extended_registered_sources_use_one_storage_catalog(self):
        # Future GUI editor registration is a SEPARATE product task. This
        # adapter-only fixture temporarily extends the existing source rows
        # and original domain field declarations; it does not create extra
        # production GUI/Auto/Voice entities or physical launcher entries.
        extras = ("gaming", "streaming", "social")
        names = ("cloud", "gamingnet")
        registry_src = REGISTRY.read_bytes()
        storage_src = STORAGE.read_bytes()
        reg_anchor = b"        printf 'HOSTLIST\\tauto\\t--hostlist\\thostlist.auto\\t0\\n'"
        storage_anchor = b"        printf 'hostlist.auto\\truntime\\tipset/auto-domains.txt\\n'"
        self.assertEqual(registry_src.count(reg_anchor), 1)
        self.assertEqual(storage_src.count(storage_anchor), 1)
        registry_added = b"".join(
            ("        printf 'HOSTLIST\\t%s\\t--hostlist\\thostlist.%s\\t1\\n'\n"
             % (name, name)).encode("ascii") for name in extras)
        registry_added += b"".join(
            ("        printf 'IPSET\\t%s\\t--ipset\\tipset.%s\\t1\\n'\n"
             % (name, name)).encode("ascii") for name in names)
        storage_added = b"".join(
            ("        printf 'hostlist.%s\\tmanaged\\thostlist-%s.txt\\n'\n"
             % (name, name)).encode("ascii") for name in extras)
        storage_added += b"".join(
            ("        printf 'ipset.%s\\tmanaged\\tipset-%s.txt\\n'\n"
             % (name, name)).encode("ascii") for name in names)
        registry_src = registry_src.replace(reg_anchor, registry_added + reg_anchor)
        storage_src = storage_src.replace(storage_anchor, storage_added + storage_anchor)
        ids = registered_ids(registry_src)
        catalog = parse_original_storage(storage_src)
        model = replace(saved(mode="list"), registered_sources=ids)
        strategy = ("--filter-tcp=443\n<HOSTLIST:youtube>\n--lua-desync=fake\n"
                    + "".join("--new\n--filter-tcp=443\n<HOSTLIST:%s>\n"
                              "--lua-desync=fake\n" % name for name in
                              ("user", *extras))).encode()
        profiles = targeted(model, strategy)
        self.assertEqual(len(profiles.profiles), 5)
        raw = prepared()
        for name in extras:
            raw["hostlist." + name] = (name + ".example.org\n").encode()
        for name in names:
            raw["ipset." + name] = b"198.51.100.25\n"
        fields = {name: (name + "domains", name + " Domains", True)
                  for name in extras}
        with patch.dict(domain_policy.FIELDS, fields):
            result = compile_resources(
                model, profiles, catalog, raw, None,
                voice_managed_root=ROOT_MANAGED)
        self.assertEqual(len(result.resources), len(ids))
        self.assertEqual(len(result.voice), len(SERVICES))
        actual = {entry.locator: raw[entry.storage_key]
                  for entry in catalog.entries if entry.provider == "managed"}
        actual["hostlist-exclude.txt"] = raw["hostlist.exclude"]
        actual["ipset-exclude.txt"] = raw["ipset.exclude"]
        matched = compare_original_managed_bytes(result, catalog, actual)
        self.assertEqual(len(matched), len(ids) - 1 + 2)
        with self.assertRaisesRegex(ResourceCompileError,
                                    "ORIGINAL_MANAGED_BYTES_MISMATCH"):
            compare_original_managed_bytes(
                result, catalog, dict(actual, **{"hostlist-gaming.txt": b"modified.example.org\n"}))
        with self.assertRaisesRegex(ResourceCompileError,
                                    "ORIGINAL_MANAGED_SET_MISMATCH"):
            compare_original_managed_bytes(
                result, catalog,
                {k: v for k, v in actual.items() if k != "ipset-cloud.txt"})

    def test_unregistered_new_hostlist_refuses_without_original_domain_policy(self):
        from neutral_config_model import SourceId
        from neutral_resource_compiler import StorageEntry, OriginalStorage
        ids = (*saved().registered_sources,
               SourceId("HOSTLIST", "gaming", "hostlist.gaming", True))
        model = replace(saved(mode="list"), registered_sources=tuple(ids))
        storage = parse_original_storage(STORAGE.read_bytes())
        catalog = OriginalStorage(storage.source_sha256, storage.entries + (
            StorageEntry("hostlist.gaming", "managed", "hostlist-gaming.txt"),))
        raw = dict(prepared(), **{"hostlist.gaming": b"gaming.example.org\n"})
        profiles = targeted(model, b"--filter-tcp=443\n<HOSTLIST:gaming>\n--lua-desync=fake\n")
        with self.assertRaisesRegex(ResourceCompileError,
                                    "INVALID_GAMING_DOMAINS"):
            compile_resources(model, profiles, catalog, raw, None,
                              voice_managed_root=ROOT_MANAGED)


if __name__ == "__main__":
    unittest.main(verbosity=2)
