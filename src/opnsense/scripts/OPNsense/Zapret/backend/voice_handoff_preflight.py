#!/usr/bin/env python3
"""Voice release handoff compiler for one engine and scoped IPFW. No activation.

Validate relationships among the inert staged Voice bundle, actual native
dvtws.args emitted by generator.sh, ordinary ports and IPFW capture plan.
Caller must independently establish Config/lifecycle lock, prior ownership,
installed native engine capability, legacy PoC migration and durable rollback
before permitting any live mutation. This module cannot authorize Apply.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sys

from voice_firewall_transaction import VoiceFirewallError, prepare_desired
from voice_traffic_merge import VoiceMergeError, merge_profiles
from voice_profile_compiler import SERVICES
from voice_capture_plan import CapturePlanError, compile_capture_plan
from voice_firewall_ledger import canonical_manifest, decode_manifest, fingerprint

PORT = re.compile(r"^--port=([0-9]{1,5})$")
LUA = re.compile(r"^--lua-init=@/\S+$")


class VoiceHandoffError(ValueError):
    pass


def _decode(artifacts: dict, name: str) -> dict:
    raw = artifacts.get(name)
    if not isinstance(raw, str) or len(raw) > 2 * 1024 * 1024:
        raise VoiceHandoffError(f"missing or oversized Voice {name}")
    try:
        value = json.loads(raw)
    except ValueError as error:
        raise VoiceHandoffError(f"invalid JSON in Voice {name}") from error
    if not isinstance(value, dict):
        raise VoiceHandoffError(f"invalid Voice {name} object")
    return value


def _hash(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _ordinary_ports(source: str) -> tuple[str, str]:
    """Independent strict port cross-check; CI compares with ports.sh.

    Only parse the *ordinary* source, never merged traffic: native Voice
    profiles have their own separate, destination-scoped IPFW rules.
    """
    found: dict[str, list[str]] = {"tcp": [], "udp": []}
    for line in source.splitlines():
        for token in line.split():
            for protocol in ("tcp", "udp"):
                if not token.startswith("--filter-" + protocol + "="):
                    continue
                spec = token.partition("=")[2]
                if not spec or len(spec) > 8192:
                    raise VoiceHandoffError("ordinary port filter is missing or oversized")
                for part in spec.split(","):
                    values = part.split("-")
                    if len(values) not in (1, 2) or any(
                        not re.fullmatch(r"[0-9]+", n) or len(n) > 10
                        for n in values
                    ):
                        raise VoiceHandoffError("unsupported ordinary port filter")
                    numbers = [int(v) for v in values]
                    if min(numbers) < 1 or max(numbers) > 65535 or \
                       numbers[0] > numbers[-1]:
                        raise VoiceHandoffError("ordinary port filter outside 1–65535")
                    normalized = "-".join(str(n) for n in numbers)
                    if len(numbers) == 2 and numbers[0] == numbers[1]:
                        normalized = str(numbers[0])
                    if normalized not in found[protocol]:
                        found[protocol].append(normalized)
    return ",".join(found["tcp"]), ",".join(found["udp"])


def verify_staged_handoff(artifacts: dict[str, str], native_argv: str,
                          ordinary: str, tcp: str, udp: str) -> dict:
    """Prepare a non-authorizing proof of a complete one-engine candidate."""
    if not isinstance(artifacts, dict) or not isinstance(native_argv, str) or \
       not isinstance(ordinary, str):
        raise VoiceHandoffError("invalid native Voice staging input")
    metadata = _decode(artifacts, "metadata.json")
    capture = _decode(artifacts, "capture-plan.json")
    plan = _decode(artifacts, "profile-plan.json")
    voice = artifacts.get("voice.conf")
    merged = artifacts.get("traffic.conf")
    if not isinstance(voice, str) or not isinstance(merged, str) or \
       len(voice) > 1048576 or len(merged) > 2 * 1048576:
        raise VoiceHandoffError("missing Voice profile or shared traffic")
    if metadata.get("schema") != 1 or metadata.get("mode") != "staged-only" or \
       metadata.get("activation_authorized") is not False:
        raise VoiceHandoffError("Voice bundle lacks an inert staged-only marker")
    if not isinstance(metadata.get("saved_xml_sha256"), str) or \
       not re.fullmatch(r"[a-f0-9]{64}", metadata["saved_xml_sha256"]):
        raise VoiceHandoffError("missing pinned saved XML revision")
    try:
        rebuilt = merge_profiles(voice, ordinary)
    except VoiceMergeError as error:
        raise VoiceHandoffError("Voice/ordinary traffic collision") from error
    if merged != rebuilt or metadata.get("merged_sha256") != _hash(merged) or \
       metadata.get("ordinary_sha256") != _hash(ordinary):
        raise VoiceHandoffError("Voice and Strategies release content disagrees")
    records = capture.get("voice")
    profiles = plan.get("profiles")
    if not isinstance(records, list) or not isinstance(profiles, list) or \
       metadata.get("profile_count") != len(records) or len(profiles) != len(records):
        raise VoiceHandoffError("Voice capture and profile count mismatch")
    enabled = [entry.get("service") for entry in records if isinstance(entry, dict)]
    expected = [entry.get("service") for entry in profiles if isinstance(entry, dict)]
    if len(enabled) != len(records) or len(expected) != len(profiles) or \
       len(set(enabled)) != len(enabled) or \
       any(s not in SERVICES for s in enabled) or enabled != expected or \
       enabled != [name for name in SERVICES if name in enabled]:
        raise VoiceHandoffError("Voice profiles differ from capture plan")
    if plan.get("wan") != capture.get("logical_wan") or \
       metadata.get("logical_wan") != plan.get("wan") or \
       metadata.get("resolved_wan") != capture.get("wan"):
        raise VoiceHandoffError("Voice WAN identity differs across staged artifacts")
    if any(f"--name=voice-{name}" not in merged for name in enabled) or \
       "--name=telegram-voice-poc" in merged:
        raise VoiceHandoffError("unbound Voice identity or legacy PoC collision")
    native_parts = [part.rstrip("\n") for part in voice.split("\n--new\n")] if voice else []
    if len(native_parts) != len(profiles):
        raise VoiceHandoffError("Voice profile boundaries do not match validated plan")
    for part, entry, service in zip(native_parts, profiles, enabled):
        if not part.startswith(f"--name=voice-{service}\n") or \
           _hash(part) != entry.get("profile_sha256"):
            raise VoiceHandoffError("Voice profile content differs from its approved hash")
    try:
        rebuilt_capture = compile_capture_plan(
            plan, capture["rule_base"], capture["rule_max"],
            capture["divert_port"], physical_wan=capture["wan"],
        )
    except (KeyError, TypeError, ValueError, CapturePlanError) as exc:
        raise VoiceHandoffError("Voice IPFW capture plan cannot be reconstructed") from exc
    if rebuilt_capture != capture:
        raise VoiceHandoffError("Voice IPFW capture plan differs from profile manifest")
    if not isinstance(native_argv, str) or len(native_argv) > 4 * 1048576 or \
       "\x00" in native_argv or "\r" in native_argv:
        raise VoiceHandoffError("invalid native engine arguments")
    lines = native_argv.splitlines()
    if not lines or any(not x or x != x.strip() for x in lines):
        raise VoiceHandoffError("malformed native engine argument file")
    ports = [PORT.fullmatch(x) for x in lines if x.startswith("--port=")]
    if len(ports) != 1 or ports[0] is None or \
       int(ports[0].group(1)) != capture.get("divert_port"):
        raise VoiceHandoffError("one-engine divert socket identity disagrees")
    if sum(bool(LUA.fullmatch(x)) for x in lines) < 1:
        raise VoiceHandoffError("missing verified Lua engine initializer")
    if any(line.startswith("--port=") for line in merged.splitlines()):
        raise VoiceHandoffError("Voice injected a second divert socket")
    # The normal generator loads Lua then blob declarations, followed by
    # merged traffic and global exclusions/extra options. Verify the exact
    # contiguous traffic segment once; extra args remain downstream.
    traffic_lines = merged.splitlines()
    matches = [i for i in range(len(lines) - len(traffic_lines) + 1)
               if lines[i:i+len(traffic_lines)] == traffic_lines]
    if len(matches) != 1:
        raise VoiceHandoffError("generated argv does not contain exactly one merged traffic plan")
    if _ordinary_ports(ordinary) != (tcp, udp):
        raise VoiceHandoffError(
            "ordinary Strategies port extraction differs from the proposed IPFW rule scope"
        )
    try:
        desired = prepare_desired(capture, tcp, udp)
    except VoiceFirewallError as error:
        raise VoiceHandoffError("native IPFW plan does not match Voice profiles") from error
    names = [name for name in enabled if "zapret2_voice_" + name in desired["tables"]]
    if names != enabled or len(desired["tables"]) != len(enabled):
        raise VoiceHandoffError("scoped IPFW destination tables differ from Voice profiles")
    fingerprints = metadata.get("ipset_sha256")
    if not isinstance(fingerprints, dict) or set(fingerprints) != set(enabled):
        raise VoiceHandoffError("missing or incorrect managed IPSET fingerprints")
    for entry in profiles:
        name = entry["service"]
        targets = entry.get("targets")
        if not isinstance(targets, list) or not targets or \
           any(not isinstance(target, str) for target in targets):
            raise VoiceHandoffError("malformed Voice managed target set")
        expected_hash = _hash("".join(target + "\n" for target in targets))
        if fingerprints[name] != expected_hash:
            raise VoiceHandoffError("Voice managed target hash differs from profile plan")
    return {
        "schema": 1,
        "state": "preflight-only",
        "activation_authorized": False,
        "saved_xml_sha256": metadata["saved_xml_sha256"],
        "merged_sha256": _hash(merged),
        "native_argv_sha256": _hash(native_argv),
        "enabled_services": enabled,
        "rule_count": len(desired["rules"]),
        "rule_base": desired["rule_base"],
        "rule_max": desired["rule_max"],
        "table_count": len(desired["tables"]),
    }


def build_runtime_handoff(stage: Path, engine_argv: Path, ordinary: Path,
                          tcp_ports: Path, udp_ports: Path, saved_xml: Path) -> tuple[dict, dict]:
    """Bind production engine argv to one exact scoped IPFW manifest.

    All inputs must be already-built private release artifacts. No kernel,
    service, firewall, OPNsense Config or installed release is modified.
    """
    names = ("voice.conf", "traffic.conf", "metadata.json",
             "profile-plan.json", "capture-plan.json")
    sources = [stage / name for name in names] + [
        engine_argv, ordinary, tcp_ports, udp_ports, saved_xml
    ]
    for source in sources:
        # OPNsense config.xml holds ALL plugin and system settings, not just
        # Zapret; it can legitimately exceed the 4 MiB candidate-file cap.
        # Match voice_release_stage.file_sha256's existing 128 MiB XML bound.
        limit = 128 * 1048576 if source == saved_xml else 4 * 1048576
        if source.is_symlink() or not source.is_file() or source.stat().st_size > limit:
            raise VoiceHandoffError("Voice handoff input is missing, unsafe or too large")
    artifacts = {name: (stage / name).read_text(encoding="utf-8") for name in names}
    argv = engine_argv.read_text(encoding="utf-8")
    ordinary_text = ordinary.read_text(encoding="utf-8")
    tcp = tcp_ports.read_text(encoding="utf-8").strip()
    udp = udp_ports.read_text(encoding="utf-8").strip()
    report = verify_staged_handoff(artifacts, argv, ordinary_text, tcp, udp)
    # The XML passed through the original release compiler must still be
    # the same generation at the end of native argument generation.
    # Stream the full system config. Do not materialize unrelated OPNsense
    # subsystem content in the Voice handoff process.
    with saved_xml.open("rb") as xml_stream:
        xml_hash = hashlib.file_digest(xml_stream, "sha256").hexdigest()
    if xml_hash != report["saved_xml_sha256"]:
        raise VoiceHandoffError("saved OPNsense Voice Config changed during runtime build")
    capture = json.loads(artifacts["capture-plan.json"])
    desired = prepare_desired(capture, tcp, udp)
    manifest = canonical_manifest(desired)
    if decode_manifest(manifest) != desired:
        raise VoiceHandoffError("Voice IPFW ownership cannot round-trip safely")
    report["desired_ipfw_sha256"] = fingerprint(manifest)
    # A release artifact is not permission to mutate kernel resources.
    if report["state"] != "preflight-only" or report["activation_authorized"] is not False:
        raise VoiceHandoffError("native handoff unexpectedly claims activation")
    return manifest, report


def _publish_runtime_handoff(stage: Path, manifest: dict, report: dict) -> None:
    """Publish final bound files into the candidate only; never active root."""
    outputs = (
        (stage / "desired-ipfw.json", manifest),
        (stage / "handoff-proof.json", report),
    )
    if stage.is_symlink() or not stage.is_dir():
        raise VoiceHandoffError("unsafe Voice candidate output")
    if any(target.exists() or target.is_symlink() for target, _ in outputs):
        raise VoiceHandoffError("native Voice handoff already exists")
    for target, content in outputs:
        payload = json.dumps(content, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
        with target.open("x", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(target, 0o600)


def main(argv: list[str]) -> int:
    if len(argv) != 7:
        print("usage: voice_handoff_preflight.py CANDIDATE_DIR ENGINE_ARGS "
              "ORDINARY_TRAFFIC TCP_PORTS UDP_PORTS CONFIG.XML", file=sys.stderr)
        return 64
    stage, engine, ordinary, tcp, udp, xml = (Path(v) for v in argv[1:])
    try:
        manifest, report = build_runtime_handoff(stage, engine, ordinary, tcp, udp, xml)
        _publish_runtime_handoff(stage, manifest, report)
    except (OSError, ValueError, UnicodeError, VoiceFirewallError) as error:
        print("ERROR: native Voice runtime handoff not built: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
