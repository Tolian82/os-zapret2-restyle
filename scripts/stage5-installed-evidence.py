#!/usr/bin/env python3
"""Read-only, owner-assisted Stage 5 installed OPNsense evidence bridge.

Uses the EXISTING production voice_live_inspect.py, which attests the single
committed Strategies+Voice owner, runtime process census and exact IPFW
rule/table manifest. It performs no IPFW mutation, Apply, service operation,
lock manipulation, packet generation, or config save.

Counters are shared across IPv4 and IPv6. Their increase is NOT IPv6
attribution, STUN response, dvtws2 manipulation or a Stage 5 live PASS.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys

INSTALLED_INSPECTOR = (
    "/usr/local/opnsense/scripts/OPNsense/Zapret/backend/voice_live_inspect.py"
)
INSTALLED_PYTHON = "/usr/local/bin/python3.13"
SERVICES = ("telegram", "discord", "x", "sip", "custom")
MAX_SNAPSHOT = 262144
REQUIRED_INSTALLED_VERSION = "0.6.1_6"


class EvidenceError(ValueError):
    pass


def _parse_snapshot(raw: bytes, label: str) -> dict:
    if len(raw) > MAX_SNAPSHOT:
        raise EvidenceError(f"{label}: evidence exceeds safe size")
    try:
        report = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as error:
        raise EvidenceError(f"{label}: evidence is not valid JSON") from error
    if not isinstance(report, dict):
        raise EvidenceError(f"{label}: evidence must be an object")
    if report.get("state") != "ready" or report.get("source") != "native-common":
        raise EvidenceError(f"{label}: installed native owner is not ready and attested")
    digest = report.get("config_digest")
    if not isinstance(digest, str) or len(digest) != 64 or any(
        c not in "0123456789abcdef" for c in digest
    ):
        raise EvidenceError(f"{label}: untrusted owner Config witness")
    if report.get("installed_plugin_version") != REQUIRED_INSTALLED_VERSION:
        raise EvidenceError(f"{label}: Stage 5 candidate 0.6.1_6 is not installed")
    runtime = report.get("runtime")
    if not isinstance(runtime, dict) or runtime.get("state") != "running" or (
        runtime.get("engine_verified") is not True or
        runtime.get("supervisor_verified") is not True or
        runtime.get("source_verified") is not True
    ):
        raise EvidenceError(f"{label}: one-engine runtime was not attested")
    if type(report.get("rule_count")) is not int or report["rule_count"] < 1 or (
        type(report.get("table_count")) is not int or report["table_count"] < 0
    ):
        raise EvidenceError(f"{label}: invalid owned-rule/table counts")
    services = runtime.get("services")
    if not isinstance(services, dict) or set(services) != set(SERVICES):
        raise EvidenceError(f"{label}: unexpected Voice service inventory")
    for name, detail in services.items():
        if not isinstance(detail, dict) or type(detail.get("configured")) is not bool:
            raise EvidenceError(f"{label}: invalid {name} service status")
        if detail["configured"]:
            if detail.get("capture_verified") is not True:
                raise EvidenceError(f"{label}: {name} owned capture is not attested")
            rule = detail.get("rule")
            if type(rule) is not int or not 1 <= rule <= 65534:
                raise EvidenceError(f"{label}: invalid {name} IPFW rule identity")
            for metric in ("rule_packets", "rule_bytes"):
                if metric in detail and (
                    type(detail[metric]) is not int or
                    not 0 <= detail[metric] <= 2**64 - 1
                ):
                    raise EvidenceError(f"{label}: invalid {name} {metric}")
    return report


def _read_snapshot(path: str, label: str) -> dict:
    source = Path(path)
    info = source.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_SNAPSHOT:
        raise EvidenceError(f"{label}: require a small regular evidence file")
    with source.open("rb") as stream:
        raw = stream.read(MAX_SNAPSHOT + 1)
    return _parse_snapshot(raw, label)


def _scope(report: dict) -> tuple:
    services = report["runtime"]["services"]
    return tuple(
        (name, services[name]["configured"],
         tuple(services[name].get(key) for key in
               ("rule", "wan", "udp_ports", "profile_revision", "ipset_entries"))
         if services[name]["configured"] else None)
        for name in SERVICES
    )


def compare(before: dict, after: dict) -> dict:
    """Compare only existing native inspection reports, never infer IPv6."""
    before = _parse_snapshot(json.dumps(before).encode("utf-8"), "before")
    after = _parse_snapshot(json.dumps(after).encode("utf-8"), "after")
    for key in ("installed_plugin_version", "config_digest", "rule_count", "table_count"):
        if before[key] != after[key]:
            raise EvidenceError(f"installed {key} changed between observations")
    if _scope(before) != _scope(after):
        raise EvidenceError("installed Voice rule ownership changed between observations")
    deltas = {}
    missing = []
    for name in SERVICES:
        if not before["runtime"]["services"][name]["configured"]:
            continue
        original = before["runtime"]["services"][name]
        current = after["runtime"]["services"][name]
        if not all(
            metric in original and metric in current
            for metric in ("rule_packets", "rule_bytes")
        ):
            missing.append(name)
            continue
        if any(current[key] < original[key] for key in ("rule_packets", "rule_bytes")):
            raise EvidenceError(f"{name}: counter reset/wrap or runtime replacement")
        deltas[name] = {
            "packets": current["rule_packets"] - original["rule_packets"],
            "bytes": current["rule_bytes"] - original["rule_bytes"],
        }
    activity = any(entry["packets"] > 0 for entry in deltas.values())
    return {
        "status": "READ_ONLY_OBSERVATION",
        "stage5_installed_acceptance": "OPEN",
        "ipv6_packet_proven": False,
        "voice_activity": (
            "COUNTERS_INCREASED_FAMILY_UNKNOWN" if activity
            else "NO_COUNTER_INCREASE_OBSERVED"
        ),
        "counter_deltas": deltas,
        "counter_unavailable": missing,
        "note": (
            "IPv4 and IPv6 share the same IPFW counters. Correlate actual IPv6 "
            "WAN capture, live dvtws2 behavior, Apply/FD9 and controlled rollback "
            "separately; this report can never be a Stage 5 PASS."
        ),
    }


def collect() -> int:
    """Run only the already-installed, read-only native status inspector."""
    if platform.system() != "FreeBSD" or os.geteuid() != 0:
        raise EvidenceError("collect requires installed FreeBSD/OPNsense root")
    if not Path(INSTALLED_PYTHON).is_file() or not Path(INSTALLED_INSPECTOR).is_file():
        raise EvidenceError("installed Python or Voice native inspector unavailable")
    pkg = subprocess.run(
        ["/usr/sbin/pkg", "query", "%v", "os-zapret2-restyle"],
        capture_output=True, check=False, timeout=15,
    )
    if pkg.returncode != 0 or pkg.stdout.decode("ascii", "replace").strip() != REQUIRED_INSTALLED_VERSION:
        raise EvidenceError("required 0.6.1_5 testing package is not installed")
    result = subprocess.run(
        [INSTALLED_PYTHON, INSTALLED_INSPECTOR],
        capture_output=True, check=False, timeout=30,
    )
    if result.returncode != 0:
        raise EvidenceError(
            "native inspector did not attest a running committed owner; "
            "do not use this capture as a PASS"
        )
    try:
        decoded = json.loads(result.stdout.decode("utf-8"))
    except (ValueError, UnicodeError) as error:
        raise EvidenceError("installed native inspector returned invalid JSON") from error
    if not isinstance(decoded, dict):
        raise EvidenceError("installed native inspector returned a non-object")
    decoded["installed_plugin_version"] = REQUIRED_INSTALLED_VERSION
    report = _parse_snapshot(json.dumps(decoded).encode("utf-8"), "installed")
    # The only added field attests the installed package. The runtime/IPFW
    # evidence remains the existing native owner's report, not our own model.
    print(json.dumps(report, sort_keys=True))
    return 0


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1] == "collect":
        return collect()
    if len(argv) == 4 and argv[1] == "compare":
        result = compare(
            _read_snapshot(argv[2], "before"), _read_snapshot(argv[3], "after")
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    print("usage: stage5-installed-evidence.py collect | compare BEFORE.json AFTER.json",
          file=sys.stderr)
    return 64


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except (EvidenceError, OSError, subprocess.TimeoutExpired) as error:
        print(f"STAGE5_INSTALLED=UNVERIFIED: {error}", file=sys.stderr)
        raise SystemExit(1)
