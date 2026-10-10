#!/usr/bin/env python3
"""Compile a deliberately narrow Voice/STUN profile candidate.

This is a pure staging/validation component. Until orchestrator and IPFW have
transactional support for its plan, no production code invokes this module.
It never runs shell commands or starts dvtws2.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import sys
import tempfile

SERVICES = ("telegram", "discord", "x", "sip", "custom")
MAX_INPUT_BYTES = 1024 * 1024
MAX_ARGS_BYTES = 16384
MAX_TARGETS = 4096
MAX_PROFILES = len(SERVICES)
# Bounded documented native parameters. This compiles candidates only:
# installed dvtws2/Lua dry-run and FreeBSD wire qualification are required
# before Apply can rely on any advanced fake TTL/checksum/IPfrag action.
HEX_BLOB = re.compile(r"^blob=0x([0-9A-Fa-f]{2,8192})$")
RANGE = re.compile(r"^(?:[ndb][0-9]{1,6}(?:[-<][ndb][0-9]{1,6})?|a|x)$")
PORT = re.compile(r"^[0-9]{1,5}(?:-[0-9]{1,5})?$")


def validate_fake(item: str, field: str) -> None:
    parts = item.split(":")
    if len(parts) < 2 or parts[0] != "--lua-desync=fake":
        fail(field, "only native fake:blob=0xHEX Lua action is allowed")
    blob = None
    features: set[str] = set()
    repeat_count = 1
    pos = None
    for token in parts[1:]:
        key = token.split("=", 1)[0]
        if key in features:
            fail(field, f"duplicate fake option {key}")
        features.add(key)
        if key == "blob":
            match = HEX_BLOB.fullmatch(token)
            if not match:
                fail(field, "fake blob requires native 0xHEX syntax")
            blob = match.group(1)
            if len(blob) % 2:
                fail(field, "fake blob must contain whole bytes")
        elif key == "repeats":
            value = token.partition("=")[2]
            if not re.fullmatch(r"[0-9]{1,2}", value) or not 1 <= int(value) <= 10:
                fail(field, "fake repeats must be between 1 and 10")
            repeat_count = int(value)
        elif key == "ip_ttl":
            value = token.partition("=")[2]
            if not re.fullmatch(r"[0-9]{1,3}", value) or not 1 <= int(value) <= 255:
                fail(field, "fake TTL must be between 1 and 255")
        elif key == "badsum":
            if token != "badsum":
                fail(field, "badsum is a flag, not a value")
        elif key == "ipfrag":
            if token != "ipfrag":
                fail(field, "only the installed default native ipfrag function is permitted")
        elif key == "ipfrag_pos_udp":
            value = token.partition("=")[2]
            if not re.fullmatch(r"[0-9]{1,4}", value):
                fail(field, "fake UDP fragment position must be a number")
            pos = int(value)
            if not 8 <= pos <= 4096 or pos % 8:
                fail(field, "fake UDP fragment position must be a multiple of 8")
        elif key == "ipfrag_disorder":
            if token != "ipfrag_disorder":
                fail(field, "ipfrag_disorder is a flag")
        else:
            fail(field, f"unverified fake option '{key}'")
    if blob is None:
        fail(field, "native fake requires blob=0xHEX")
    if any(key in features for key in ("ipfrag_pos_udp", "ipfrag_disorder")) and "ipfrag" not in features:
        fail(field, "fragment parameters require ipfrag")
    if "ipfrag" in features:
        if "badsum" in features:
            fail(field, "badsum+ipfrag combination is not yet qualified")
        if pos is not None and pos >= 8 + len(blob) // 2:
            fail(field, "fragment offset must split the actual UDP fake datagram")



class VoiceConfigurationError(ValueError):
    """An invalid service/line, not a runtime engine failure."""


def fail(field: str, message: str) -> None:
    raise VoiceConfigurationError(f"{field}: {message}")


def normalize_targets(value: str, service: str) -> tuple[list[str], list[ipaddress.IPv4Network]]:
    if not isinstance(value, str):
        fail(f"{service}.ips", "expected a text list")
    result: list[str] = []
    networks: list[ipaddress.IPv4Network] = []
    seen: set[str] = set()
    for number, raw in enumerate(value.splitlines(), 1):
        text = raw.strip().strip(",;:")
        if not text:
            continue
        try:
            if "/" in text:
                parsed = ipaddress.IPv4Network(text, strict=True)
                canonical = str(parsed)
            else:
                address = ipaddress.IPv4Address(text)
                parsed = ipaddress.IPv4Network(f"{address}/32")
                canonical = str(address)
        except ValueError as exc:
            fail(f"{service}.ips line {number}", f"invalid IPv4/CIDR '{text}': {exc}")
        if canonical not in seen:
            seen.add(canonical)
            result.append(canonical)
            networks.append(parsed)
        if len(result) > MAX_TARGETS:
            fail(f"{service}.ips", f"too many IPv4/CIDR entries (max {MAX_TARGETS})")
    return result, networks


def parse_ports(spec: str, field: str) -> list[tuple[int, int]]:
    if spec == "*":
        return [(1, 65535)]
    values = spec.split(",")
    if not 1 <= len(values) <= 128:
        fail(field, "expected 1 to 128 numeric ports/ranges or *")
    ranges = []
    for token in values:
        if not PORT.fullmatch(token):
            fail(field, f"invalid UDP port or range '{token}'")
        parts = token.split("-")
        first, last = int(parts[0]), int(parts[-1])
        if not (1 <= first <= last <= 65535):
            fail(field, f"invalid UDP port range '{token}'")
        ranges.append((first, last))
    return ranges


def validate_arguments(source: str, service: str) -> tuple[list[str], list[tuple[int, int]]]:
    if not isinstance(source, str) or len(source.encode("utf-8")) > MAX_ARGS_BYTES:
        fail(f"{service}.args", "missing/oversized arguments")
    lines = []
    port_ranges = None
    seen: set[str] = set()
    for line_number, raw in enumerate(source.splitlines(), 1):
        item = raw.strip()
        if not item:
            continue
        field = f"{service}.args line {line_number}"
        if len(item) > 9000 or not item.isascii() or any(ord(ch) < 33 or ord(ch) > 126 for ch in item):
            fail(field, "only printable single-token ASCII native arguments are permitted")
        option = item.split("=", 1)[0]
        if option == "--filter-udp":
            if option in seen or "=" not in item:
                fail(field, "only one --filter-udp= is allowed")
            port_ranges = parse_ports(item.partition("=")[2], field)
        elif option in ("--filter-l7", "--payload"):
            if option in seen:
                fail(field, f"duplicate {option}")
            expected = "stun"
            if item != f"{option}={expected}":
                fail(field, f"only {option}=stun is supported in Voice")
        elif option == "--out-range":
            if "=" not in item or not RANGE.fullmatch(item.partition("=")[2]):
                fail(field, "unsupported native UDP out-range expression")
        elif option == "--lua-desync":
            validate_fake(item, field)
        else:
            fail(field, f"forbidden or unverified option '{option}'")
        seen.add(option)
        lines.append(item)
        if len(lines) > 64:
            fail(field, "too many arguments")
    for needed in ("--filter-udp", "--filter-l7", "--payload"):
        if needed not in seen:
            fail(f"{service}.args", f"required {needed} is missing")
    assert port_ranges is not None
    return lines, port_ranges


def _intersects(a: list[tuple[int, int]], b: list[tuple[int, int]]) -> bool:
    return any(x1 <= y2 and y1 <= x2 for x1, x2 in a for y1, y2 in b)


def compile_candidate(data: dict, managed_root: Path) -> tuple[str, dict]:
    if not isinstance(data, dict):
        fail("voice", "configuration must be an object")
    unknown = set(data) - {"strategy_wan", "voice_wan", "services"}
    if unknown:
        fail("voice", f"unexpected keys: {', '.join(sorted(unknown))}")
    strategy_wan = data.get("strategy_wan")
    voice_wan = data.get("voice_wan") or strategy_wan
    if not isinstance(strategy_wan, str) or not strategy_wan.strip():
        fail("voice.strategy_wan", "Strategies WAN must be set")
    if not isinstance(voice_wan, str) or not voice_wan.strip():
        fail("voice.voice_wan", "Voice WAN must be set")
    if voice_wan != strategy_wan:
        fail("voice.voice_wan", "independent WAN is not yet isolated by the shared divert engine; select the Strategies WAN")
    if not managed_root.is_absolute():
        fail("voice.managed_root", "managed output root must be absolute")
    provided = data.get("services")
    if not isinstance(provided, dict) or set(provided) != set(SERVICES):
        fail("voice.services", "exactly the five named service records are required")

    profiles = []
    plan = []
    for name in SERVICES:
        entry = provided[name]
        if not isinstance(entry, dict) or set(entry) != {"enabled", "args", "ips"}:
            fail(f"voice.{name}", "expected enabled, args and ips")
        if not isinstance(entry["enabled"], bool):
            fail(f"voice.{name}.enabled", "expected a checkbox boolean")
        if not isinstance(entry["args"], str) or not isinstance(entry["ips"], str):
            fail(f"voice.{name}", "args and ips must be text")
        # OFF retains editable content, including incomplete text, without
        # creating capture/profile or accidentally validating a draft.
        if not entry["enabled"]:
            continue
        args, ports = validate_arguments(entry["args"], name)
        targets, networks = normalize_targets(entry["ips"], name)
        if not targets:
            fail(f"voice.{name}.ips", "enabled service requires at least one IPv4/CIDR destination")
        for other in plan:
            if _intersects(ports, other["_ranges"]) and any(
                n.overlaps(m) for n in networks for m in other["_networks"]
            ):
                fail(f"voice.{name}", f"overlapping UDP port and destination scope with {other['service']}")
        managed_path = managed_root / f"ipset-{name}.txt"
        profile = [
            f"--name=voice-{name}",
            "--filter-l3=ipv4",
            f"--ipset={managed_path}",
            *args,
        ]
        profiles.append("\n".join(profile))
        digest = hashlib.sha256("\n".join(profile).encode()).hexdigest()
        plan.append({
            "service": name,
            "enabled": True,
            "wan": voice_wan,
            "ipset_path": str(managed_path),
            "target_count": len(targets),
            "targets": targets,
            "ports": [list(item) for item in ports],
            "profile_sha256": digest,
            "_ranges": ports,
            "_networks": networks,
        })
    # Output records contain no Python objects or hidden internal details.
    public_plan = {
        "schema": 1,
        "wan": voice_wan,
        "profiles": [{key: val for key, val in row.items() if not key.startswith("_")}
                     for row in plan],
    }
    text = "\n--new\n".join(profiles) + ("\n" if profiles else "")
    return text, public_plan


def _atomic_write(path: Path, content: str) -> None:
    # This helper only prepares staging artifacts; active runtime activation
    # remains the existing orchestrator's responsibility.
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     prefix=f".{path.name}.", delete=False) as output:
        pending = Path(output.name)
        try:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        except Exception:
            pending.unlink(missing_ok=True)
            raise
    os.replace(pending, path)


def main(argv: list[str]) -> int:
    if len(argv) != 5:
        print("usage: voice_profile_compiler.py INPUT.json MANAGED_ROOT VOICE.conf PLAN.json", file=sys.stderr)
        return 64
    source, root, profile_path, plan_path = map(Path, argv[1:])
    try:
        if source.stat().st_size > MAX_INPUT_BYTES:
            fail("voice", "input JSON is too large")
        payload = json.loads(source.read_text(encoding="utf-8"))
        traffic, plan = compile_candidate(payload, root)
        # Do not emit any staged artifact unless the entire candidate validates.
        _atomic_write(profile_path, traffic)
        _atomic_write(plan_path, json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
        return 0
    except (VoiceConfigurationError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
