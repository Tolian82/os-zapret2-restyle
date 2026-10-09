#!/usr/bin/env python3
"""Pure, fail-closed allocation of plugin-owned Voice IPFW rule/table scopes.

The result is a declarative action plan. This module does NOT execute IPFW,
allocate kernel tables, clear any rule or activate a dvtws2 process.
Native IPFW installation/transaction and rollback are separate work.
"""
from __future__ import annotations

import ipaddress
import json
from pathlib import Path
import re
import sys

SERVICES = ("telegram", "discord", "x", "sip", "custom")
TABLE_PREFIX = "zapret2_voice_"
WAN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,63}$")
HASH_RE = re.compile(r"^[a-f0-9]{64}$")
MAX_TARGETS = 4096
MIN_RULE = 1
MAX_RULE = 65534


class CapturePlanError(ValueError):
    pass


def fail(message: str) -> None:
    raise CapturePlanError(message)


def valid_numbers(first: int, last: int, name: str) -> None:
    if not (type(first) is type(last) is int and 1 <= first <= last <= 65535):
        fail(f"{name}: invalid UDP port interval")


def compile_capture_plan(candidate: dict, rule_base: int, rule_max: int,
                         divert_port: int, physical_wan: str | None = None) -> dict:
    if not isinstance(candidate, dict) or candidate.get("schema") != 1:
        fail("unsupported or missing Voice candidate schema")
    wan = candidate.get("wan")
    if not isinstance(wan, str) or not WAN_RE.fullmatch(wan):
        fail("unsafe or missing Voice WAN logical interface")
    # 'WAN' in OPNsense XML is a logical name. Runtime callers must supply
    # the resolved kernel interface separately. Never treat this as routing.
    capture_wan = wan if physical_wan is None else physical_wan
    if not isinstance(capture_wan, str) or not WAN_RE.fullmatch(capture_wan):
        fail("unsafe or missing resolved Voice WAN device")
    if type(rule_base) is not int or type(rule_max) is not int or not (
        MIN_RULE <= rule_base <= rule_max <= MAX_RULE
    ):
        fail("invalid plugin-owned IPFW number range")
    if type(divert_port) is not int or not 1 <= divert_port <= 65535:
        fail("invalid divert port")

    profiles = candidate.get("profiles")
    if not isinstance(profiles, list) or len(profiles) > len(SERVICES):
        fail("Voice candidate requires a bounded profile list")

    rows: list[dict] = []
    previous = -1
    for profile in profiles:
        if not isinstance(profile, dict) or profile.get("enabled") is not True:
            fail("Voice profile must be a validated enabled service")
        name = profile.get("service")
        if name not in SERVICES:
            fail("Voice profile service must be registered")
        number = SERVICES.index(name)
        if number <= previous:
            fail("Voice services must be unique and in native profile order")
        previous = number
        if profile.get("wan") != wan:
            fail(f"{name}: WAN does not match the shared engine")
        ipset_path = profile.get("ipset_path")
        if not isinstance(ipset_path, str) or ipset_path != (
            f"/usr/local/etc/zapret2/runtime-v2/managed/ipset-{name}.txt"
        ):
            fail(f"{name}: IPSET path is not the managed active runtime file")
        digest = profile.get("profile_sha256")
        if not isinstance(digest, str) or not HASH_RE.fullmatch(digest):
            fail(f"{name}: missing native profile fingerprint")
        targets = profile.get("targets")
        if not isinstance(targets, list) or not 1 <= len(targets) <= MAX_TARGETS:
            fail(f"{name}: empty or oversized destination set")
        normalized: list[str] = []
        networks: list[ipaddress.IPv4Network] = []
        for idx, target in enumerate(targets, 1):
            if not isinstance(target, str):
                fail(f"{name} target {idx}: expected IPv4/CIDR")
            try:
                network = ipaddress.IPv4Network(
                    target if "/" in target else f"{target}/32", strict=True
                )
            except ValueError as exc:
                fail(f"{name} target {idx}: {exc}")
            canonical = str(network) if "/" in target else str(network.network_address)
            if canonical != target:
                fail(f"{name} target {idx}: noncanonical IPSET entry")
            normalized.append(target)
            networks.append(network)
        if len(set(normalized)) != len(normalized):
            fail(f"{name}: duplicate IPSET entry")
        if profile.get("target_count") != len(targets):
            fail(f"{name}: inconsistent target count")
        intervals = profile.get("ports")
        if not isinstance(intervals, list) or not 1 <= len(intervals) <= 128:
            fail(f"{name}: empty or too many UDP port intervals")
        checked_ports = []
        for interval in intervals:
            if not isinstance(interval, list) or len(interval) != 2:
                fail(f"{name}: invalid UDP port structure")
            lo, hi = interval
            valid_numbers(lo, hi, name)
            checked_ports.append((lo, hi))
        for other in rows:
            if any(a <= d and c <= b for a, b in checked_ports for c, d in other["_ports"]):
                if any(left.overlaps(right) for left in networks for right in other["_networks"]):
                    fail(f"{name}: overlapping UDP capture with {other['service']}")
        table = TABLE_PREFIX + name
        port_expression = None if checked_ports == [(1, 65535)] else ",".join(
            str(lo) if lo == hi else f"{lo}-{hi}" for lo, hi in checked_ports
        )
        # IPFW 'to table(name)' remains mandatory even for wildcard UDP.
        # The port selector, if present, follows the destination table.
        argv = ["divert", str(divert_port), "udp", "from", "any",
                "to", f"table({table})"]
        if port_expression is not None:
            argv.append(port_expression)
        argv += ["out", "not", "diverted", "not", "sockarg", "xmit", capture_wan]
        rows.append({
            "service": name,
            "table": table,
            "table_stage": table + "_stage",
            "rule": rule_base + len(rows),
            "ports": [list(p) for p in checked_ports],
            "destination_count": len(targets),
            "destinations": targets,
            "argv": argv,
            "_ports": checked_ports,
            "_networks": networks,
        })
    # Reserve ordinary TCP and UDP numbers even when one protocol is absent.
    # This matches the current plugin (at most two ordinary port rules).
    if rule_base + len(rows) + 1 > rule_max:
        fail("not enough plugin-owned IPFW numbers for Voice and ordinary Strategies")
    return {
        "schema": 1,
        "logical_wan": wan,
        "wan": capture_wan,
        "divert_port": divert_port,
        "rule_base": rule_base,
        "rule_max": rule_max,
        "ordinary_rule_base": rule_base + len(rows),
        "voice": [{k: v for k, v in row.items() if not k.startswith("_")}
                  for row in rows],
    }


def main(argv: list[str]) -> int:
    if len(argv) != 6:
        print("usage: voice_capture_plan.py CANDIDATE.json RULE_BASE RULE_MAX DIVERT_PORT OUT.json",
              file=sys.stderr)
        return 64
    try:
        source = Path(argv[1])
        if source.stat().st_size > 1_048_576:
            fail("Voice candidate JSON is too large")
        data = json.loads(source.read_text(encoding="utf-8"))
        plan = compile_capture_plan(data, int(argv[2]), int(argv[3]), int(argv[4]))
        # Do not create output for any invalid candidate.
        output = Path(argv[5])
        output.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
