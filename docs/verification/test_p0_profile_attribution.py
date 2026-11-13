#!/usr/bin/env python3
"""P0 only: actual detached generator artifacts -> generation-bound origins.

No plugin installation, engine, Config, service, packet or firewall operations.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))
from global_exclusions import compose, audit
from voice_traffic_merge import merge_profiles


class AttributionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="p0-profile-origins-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.module = None

    def implementation(self):
        if self.module is None:
            path = Path(__file__).with_name("p0_profile_attribution.py")
            self.assertTrue(path.is_file(), "complete generator has no generation-bound attribution implementation")
            spec = importlib.util.spec_from_file_location("p0_profile_attribution", path)
            self.module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.module)
        return self.module

    def generate(self, strategy, mode="auto", *, voice="", extra="",
                 checkout=None, divert=989, telegram_ips="149.154.160.0/20"):
        """Execute existing parser/default/normalizer/targets/blobs/generator.

        Capture origins at their stage boundaries, never recover them by
        searching the final argv for a filename or a similar strategy.
        """
        case = self.root / uuid.uuid4().hex
        case.mkdir()
        self.last_case = case
        voice = voice(case) if callable(voice) else voice
        extra = extra(case) if callable(extra) else extra
        (case / "strategy").write_text(strategy)
        (case / "extra.input").write_text(extra)
        (case / "runtime/ipset").mkdir(parents=True)
        (case / "runtime/files/fake").mkdir(parents=True)
        (case / "runtime/files/fake/http_iana_org.bin").write_bytes(b"P0 fixture only")
        (case / "init.lua").write_text("return true\n")
        env = dict(os.environ, BACKEND_DIR=str(BACKEND), BACKEND=str(BACKEND),
                   PYTHON_RUNTIME=sys.executable, CASE=str(case), MODE=mode,
                   TEST_TELEGRAM_IPS=telegram_ips, TEST_DIVERT=str(divert),
                   TEST_CHECKOUT=str(checkout) if checkout else "",
                   PYTHONDONTWRITEBYTECODE="1")
        script = r'''
set -eu
for component in common parser registry storage targets target_mode profile_normalizer profile_pipeline blobs generator; do
    . "${BACKEND}/${component}.sh"
done
mkdir "${CASE}/work" "${CASE}/effective" "${CASE}/normalized" "${CASE}/resolved"
count=$(profile_pipeline_parse "${CASE}/work" 0 "$(cat "${CASE}/strategy")")
count=$(profile_pipeline_registry "${CASE}/work" "$count" "${CASE}/registry")
count=$(profile_pipeline_target_mode "${CASE}/work" "$count" "${MODE}" "${CASE}/registry")
no=1
while [ "$no" -le "$count" ]; do
    cp "${CASE}/work/profile-${no}.conf" "${CASE}/effective/${no}"
    no=$((no + 1))
done
count=$(profile_pipeline_normalize "${CASE}/work" "$count")
count=$(profile_pipeline_index "${CASE}/work" "$count")
targets_prepare_managed "${CASE}/release/managed" 'youtube.com' "${TEST_TELEGRAM_IPS}" 'example.org' '' '' '' '' '10.0.0.0/8'
printf '%s\n' excluded.example > "${CASE}/release/managed/hostlist-exclude.txt"
storage_catalog_build "${CASE}/catalog"
: > "${CASE}/bindings"
while IFS="$(printf '\t')" read -r kind name option key required; do
    reference=$(storage_resolve_roots "$key" "${CASE}/active/managed" "${CASE}/runtime" "${CASE}/catalog")
    printf '<%s:%s>\t%s=%s\n' "$kind" "$name" "$option" "$reference" >> "${CASE}/bindings"
done < "${CASE}/registry"
targets_resolve_all_mapped "${CASE}/work" "$count" "${CASE}/registry" "${CASE}/catalog" "${CASE}/release/managed" "${CASE}/active/managed" "${CASE}/runtime" "${CASE}/targets"
blobs_resolve_file "${CASE}/targets" "${CASE}/ordinary" "${CASE}/blobs" "${CASE}/loaded" "${CASE}/runtime/files/fake"
blobs_resolve_file_append "${CASE}/extra.input" "${CASE}/extra" "${CASE}/blobs" "${CASE}/loaded" "${CASE}/runtime/files/fake"
no=1
while [ "$no" -le "$count" ]; do
    cp "${CASE}/work/profile-${no}.conf" "${CASE}/normalized/${no}"
    cp "${CASE}/work/profile-${no}.resolved.conf" "${CASE}/resolved/${no}"
    no=$((no + 1))
done
'''
        result = subprocess.run(["sh", "-c", script], env=env, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)

        def sequence(name):
            return [p.read_bytes() for p in sorted((case / name).iterdir(), key=lambda p: int(p.name))]

        traffic = merge_profiles(voice, (case / "ordinary").read_text())
        (case / "traffic").write_text(traffic)
        command = r'''
set -eu
. "${BACKEND}/common.sh"
. "${BACKEND}/generator.sh"
if [ -n "${TEST_CHECKOUT}" ]; then
    set -- "${TEST_CHECKOUT}/lua/zapret-lib.lua" "${TEST_CHECKOUT}/lua/zapret-antidpi.lua"
else
    set -- "${CASE}/init.lua"
fi
printf '%s\n' "--port=${TEST_DIVERT}" > "${CASE}/preamble"
for initializer do
    printf '%s\n' "--lua-init=@${initializer}" >> "${CASE}/preamble"
done
cat "${CASE}/blobs" >> "${CASE}/preamble"
generator_build_args_mapped "${CASE}/assembled" "${TEST_DIVERT}" "${CASE}/traffic" "${CASE}/extra" "${CASE}/blobs" "${CASE}/release/managed/hostlist-exclude.txt" "${CASE}/active/managed/hostlist-exclude.txt" "$@"
'''
        result = subprocess.run(["sh", "-c", command], env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        paths = (case / "release/managed/hostlist-exclude.txt", str(case / "active/managed/hostlist-exclude.txt"),
                 case / "release/managed/ipset-exclude.txt", str(case / "active/managed/ipset-exclude.txt"),
                 case / "active", case / "release", case / "runtime")
        assembled = (case / "assembled").read_bytes()
        final = compose(assembled.decode(), *paths).encode()
        audit(final.decode(), *paths)
        (case / "final").write_bytes(final)
        data = dict(
            generation=uuid.uuid4().hex, mode=mode, strategy=(case / "work/traffic.input").read_bytes(),
            bindings=(case / "bindings").read_bytes(),
            effective=sequence("effective"), normalized=sequence("normalized"),
            resolved=sequence("resolved"), ordinary=(case / "ordinary").read_bytes(),
            voice=voice.encode(), extra=(case / "extra").read_bytes(),
            preamble=(case / "preamble").read_bytes(),
            assembled=assembled, final=final,
            overlays=(f"--hostlist-exclude={paths[1]}", f"--ipset-exclude={paths[3]}"),
        )
        before = {p: p.read_bytes() for p in case.rglob("*") if p.is_file()}
        result = self.implementation().build_map(**data)
        self.assertEqual(before, {p: p.read_bytes() for p in before}, "attribution modified a generator artifact")
        # The map is round-trippable and contains no raw traffic/list entries.
        result = json.loads(json.dumps(result))
        self.assertNotIn("P0 fixture only", json.dumps(result))
        return data, result

    def test_mixed_source_stays_excluded_after_real_expansion(self):
        data, mapping = self.generate("--filter-tcp=443\n<HOSTLIST:youtube>\n<IPSET:telegram>\n--lua-desync=fake\n")
        rows = mapping["profiles"][:-1]
        self.assertEqual([r["native_number"] for r in rows], [1, 2])
        self.assertEqual([r["source_number"] for r in rows], [1, 1])
        self.assertEqual([r["selector"] for r in rows], ["<HOSTLIST:youtube>", "<IPSET:telegram>"])
        self.assertTrue(all(r["source_has_ipset"] and r["status"] == "excluded-ipset" for r in rows))
        self.assertTrue(all(r["hostlist"] is None for r in rows))
        self.assertNotIn(b"<IPSET:telegram>", data["normalized"][0])

    def test_actual_modes_and_separate_source_identity(self):
        for mode, expected in (("all", 1), ("list", 3), ("auto", 3)):
            with self.subTest(mode=mode):
                _, mapping = self.generate("--filter-tcp=443\n--blob=http_iana_org\n--lua-desync=fake\n", mode)
                self.assertEqual(len(mapping["profiles"]), expected + 1)
                self.assertTrue(all(r["hostlist"] is None for r in mapping["profiles"]))
        _, mapping = self.generate("--filter-tcp=80\n<HOSTLIST:user>\n--new=named-tls\n--filter-tcp=443\n<HOSTLIST:user>\n")
        rows = mapping["profiles"][:-1]
        self.assertEqual([r["source_number"] for r in rows], [1, 2])
        self.assertEqual([r["hostlist"] for r in rows], ["user", "user"])
        self.assertNotEqual(rows[0]["id"], rows[1]["id"])

    def test_voice_extra_templates_and_native_number_zero(self):
        voice = "--name=voice-telegram-stun\n--filter-udp=3478\n--filter-l7=stun\n"
        strategy = ("--template=example-template\n--filter-tcp=443\n<HOSTLIST:user>\n"
                    "--new\n--skip\n--filter-tcp=80\n<HOSTLIST:youtube>\n"
                    "--new=imported\n--import=example-template\n<HOSTLIST:user>\n"
                    "--new=known\n--filter-tcp=443\n<HOSTLIST:youtube>\n")
        _, mapping = self.generate(strategy, voice=voice, extra="--new=extra\n--filter-tcp=80\n")
        rows = mapping["profiles"]
        self.assertEqual([r["native_number"] for r in rows], [1, None, None, 2, 3, 4, 0])
        self.assertEqual([r["hostlist"] for r in rows], [None, None, None, None, "youtube", None, None])
        self.assertEqual(rows[3]["status"], "unknown-import")
        self.assertEqual(rows[-1]["role"], "native-default")

    def test_extra_tail_cannot_keep_known_hostlist(self):
        _, mapping = self.generate("--filter-tcp=443\n<HOSTLIST:user>\n", extra="--ipset-ip=192.0.2.0/24\n")
        self.assertEqual(mapping["profiles"][0]["status"], "excluded-ipset")
        self.assertIsNone(mapping["profiles"][0]["hostlist"])
        _, mapping = self.generate("--filter-tcp=443\n<HOSTLIST:user>\n", extra="--filter-l7=tls\n")
        self.assertEqual(mapping["profiles"][0]["status"], "unknown-extra")

    def test_native_lists_and_stun_do_not_infer_a_hostlist(self):
        _, mapping = self.generate("--filter-tcp=443\n<HOSTLIST:user>\n--hostlist-domains=other.example\n")
        self.assertEqual(mapping["profiles"][0]["status"], "unknown-native-list")
        _, mapping = self.generate("--filter-udp=3478\n--filter-l7=stun\n<HOSTLIST:user>\n")
        self.assertEqual(mapping["profiles"][0]["status"], "excluded-stun")
        self.assertIsNone(mapping["profiles"][0]["hostlist"])

    def test_empty_voice_only_and_multiple_hostlists(self):
        for strategy, voice in (("", ""), ("", "--name=voice-telegram-stun\n--filter-udp=3478\n")):
            with self.subTest(voice=bool(voice)):
                _, mapping = self.generate(strategy, voice=voice)
                self.assertEqual([r["native_number"] for r in mapping["profiles"]], [1, 0])
                self.assertTrue(all(r["hostlist"] is None for r in mapping["profiles"]))
        _, mapping = self.generate("--filter-tcp=443\n<HOSTLIST:youtube>\n<HOSTLIST:user>\n")
        self.assertEqual([r["hostlist"] for r in mapping["profiles"]], ["youtube", "user", None])

    def test_same_bytes_new_generation_and_stale_read_refuse_guessing(self):
        data, mapping = self.generate("--filter-tcp=443\n<HOSTLIST:user>\n")
        api = self.implementation()
        self.assertEqual(api.lookup(mapping, data["generation"], data["final"], 1)["hostlist"], "user")
        self.assertIsNone(api.lookup(mapping, "another-generation", data["final"], 1))
        self.assertIsNone(api.lookup(mapping, data["generation"], data["final"] + b"\n", 1))
        self.assertIsNone(api.lookup(mapping, data["generation"], data["final"], 999))
        self.assertIsNone(api.lookup(mapping, data["generation"], data["final"], True))
        changed = dict(data, generation=uuid.uuid4().hex)
        other = api.build_map(**changed)
        self.assertNotEqual(mapping["generation"], other["generation"])
        self.assertNotEqual(mapping["profiles"][0]["id"], other["profiles"][0]["id"])
        for key, value in (("normalized", list(reversed(data["normalized"])) + [b"--filter-tcp=80\n"]),
                           ("strategy", b"--filter-tcp=80\n<HOSTLIST:youtube>\n"),
                           ("resolved", [data["resolved"][0] + b"--filter-tcp=80\n"]),
                           ("ordinary", data["ordinary"] + b"--filter-tcp=80\n"),
                           ("final", data["final"] + b"--filter-tcp=80\n"),
                           ("preamble", data["preamble"] + b"--new\n")):
            with self.subTest(tampered=key), self.assertRaises(api.AttributionError):
                api.build_map(**dict(data, **{key: value}))

    def test_inline_new_is_refused_before_any_number_guess(self):
        data, _ = self.generate("--filter-tcp=443\n<HOSTLIST:user>\n")
        api = self.implementation()
        # Existing source splitter deliberately handles standalone --new;
        # an inline native boundary must not borrow that source's ordinal.
        with self.assertRaises(api.AttributionError):
            api.build_map(**dict(data, resolved=[data["resolved"][0] + b"--new --filter-tcp=80\n"]))

    def test_wrong_registry_destination_cannot_borrow_selector_identity(self):
        data, _ = self.generate("--filter-tcp=443\n<HOSTLIST:user>\n")
        api = self.implementation()
        with self.assertRaises(api.AttributionError):
            api.build_map(**dict(data, bindings=data["bindings"].replace(b"hostlist-user.txt", b"hostlist-youtube.txt")))


if __name__ == "__main__":
    result = unittest.main(exit=False).result
    if result.wasSuccessful():
        print("P0_GENERATION_BOUND_ATTRIBUTION=PASS_DETACHED_SOURCE_ONLY")
    raise SystemExit(0 if result.wasSuccessful() else 1)
