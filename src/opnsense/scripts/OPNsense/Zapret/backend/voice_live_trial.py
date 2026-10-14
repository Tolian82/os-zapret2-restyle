#!/usr/local/bin/python3.13
"""Read-only packet-counter evidence for a real Voice call acceptance trial.

No IPFW zero/add/delete, pcap capture, Config change, service restart or daemon.
A positive divert counter proves only matched packets, never STUN replies,
media delivery or a successful call. Run snapshots around a MANUAL test call.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from shared_apply_operation import SharedApplyOperation, committed_owner
from shared_apply_seal import WORK
from voice_ipfw_adapter import shared_release_manifest
from voice_live_inspect import examine_shared

_RULE = re.compile(r"^\s*([0-9]{4,6})\s+([0-9]+)\s+([0-9]+)\s+(.+)$")
_MAX_OUTPUT = 4 * 1048576
_MAX_SAMPLE = 65536


class VoiceTrialError(ValueError):
    pass


def count_owned(ipfw_output: str, numbers: set[int]) -> dict[int, dict[str, int]]:
    """Parse FreeBSD 'ipfw -a list' exactly for preverified Voice rule numbers."""
    if not numbers or len(numbers) > 5 or any(type(n) is not int or
                                               not 1 <= n <= 65534 for n in numbers):
        raise VoiceTrialError("untrusted Voice IPFW rule number set")
    observed = {}
    for line in ipfw_output.splitlines():
        match = _RULE.fullmatch(line)
        if match is None:
            continue
        number = int(match.group(1))
        if number not in numbers:
            continue
        if number in observed:
            raise VoiceTrialError("duplicate Voice IPFW counter")
        observed[number] = {
            "packets": int(match.group(2)),
            "bytes": int(match.group(3)),
        }
    if set(observed) != numbers:
        raise VoiceTrialError("Voice IPFW rule counters missing")
    return observed


def snapshot() -> dict:
    if sys.platform != "freebsd" or os.geteuid() != 0:
        raise VoiceTrialError("live OPNsense FreeBSD root is required")
    first = SharedApplyOperation().read()
    owner = committed_owner(first) if first is not None else None
    if owner is None or first["phase"] != "committed":
        raise VoiceTrialError("no committed common Voice/Strategies owner")
    status = examine_shared(first)
    if not isinstance(status, dict) or status.get("state") != "ready":
        raise VoiceTrialError("native engine/IPFW ownership not ready")
    release = WORK / owner["id"] / "release"
    manifest = shared_release_manifest(release)
    plan = json.loads((release / "voice-plan.json").read_text(encoding="utf-8"))
    rows = plan["capture"]["voice"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= 5:
        raise VoiceTrialError("no active Voice UDP rule to measure")
    known = {}
    for row in rows:
        name, number = row.get("service"), row.get("rule")
        if not isinstance(name, str) or name not in (
            "telegram", "discord", "x", "sip", "custom"
        ) or type(number) is not int or number not in manifest["rules"] or name in known:
            raise VoiceTrialError("Voice rule numbers disagree with common manifest")
        known[name] = number
    result = subprocess.run(
        ["/sbin/ipfw", "-a", "list"], capture_output=True, text=True,
        timeout=15, check=False,
    )
    if result.returncode != 0 or len(result.stdout) > _MAX_OUTPUT:
        raise VoiceTrialError("read-only FreeBSD IPFW counter query failed")
    counts = count_owned(result.stdout, set(known.values()))
    # A concurrent Apply may change both owner and rules while counters are
    # read. Double-check the SAME sealed identity and live physical witness.
    second = SharedApplyOperation().read()
    if second is None or second != first or not isinstance(
        (final_status := examine_shared(second)), dict
    ) or final_status.get("state") != "ready":
        raise VoiceTrialError("common Voice owner changed during counter snapshot")
    return {
        "schema": 1,
        "state": "ready",
        "owner": owner["id"],
        "time_unix": int(time.time()),
        "rules": {
            name: {"number": number, **counts[number]}
            for name, number in known.items()
        },
        "stun_verified": False,
        "media_verified": False,
        "call_verified": False,
    }


def compare(before: dict, after: dict) -> dict:
    for value in (before, after):
        if not isinstance(value, dict) or value.get("schema") != 1 or (
            value.get("state") != "ready"
        ) or not re.fullmatch(r"[a-f0-9]{32}", str(value.get("owner", ""))) or (
            type(value.get("time_unix")) is not int
        ) or not isinstance(value.get("rules"), dict):
            raise VoiceTrialError("invalid live Voice counter evidence")
    if before["owner"] != after["owner"] or (
        after["time_unix"] < before["time_unix"]
    ):
        raise VoiceTrialError("Voice owner changed or sample time went backwards")
    a, b = before["rules"], after["rules"]
    if set(a) != set(b) or not a or len(a) > 5:
        raise VoiceTrialError("Voice configured rules changed during trial")
    changes = {}
    for name, initial in a.items():
        final = b[name]
        if name not in ("telegram", "discord", "x", "sip", "custom") or (
            not isinstance(initial, dict) or not isinstance(final, dict)
        ) or set(initial) != {"number", "packets", "bytes"} or (
            set(final) != set(initial)
        ):
            raise VoiceTrialError("invalid Voice rule counter data")
        if any(type(x[k]) is not int or x[k] < 0 for x in (initial, final)
               for k in ("number", "packets", "bytes")) or (
            initial["number"] != final["number"]
        ):
            raise VoiceTrialError("inconsistent Voice rule identity")
        packets = final["packets"] - initial["packets"]
        octets = final["bytes"] - initial["bytes"]
        if packets < 0 or octets < 0:
            raise VoiceTrialError("IPFW counters reset: trial is inconclusive")
        changes[name] = {"rule": initial["number"],
                         "packet_delta": packets, "byte_delta": octets}
    return {
        "schema": 1, "state": "measured", "owner": before["owner"],
        "elapsed_seconds": after["time_unix"] - before["time_unix"],
        "services": changes,
        "ipfw_packets_observed": any(v["packet_delta"] > 0 for v in changes.values()),
        "stun_verified": False, "media_verified": False, "call_verified": False,
        "note": "Counters indicate matching outgoing UDP only; inspect actual call independently.",
    }


def _read_sample(path: str) -> dict:
    source = Path(path)
    if source.is_symlink() or not source.is_file() or source.stat().st_size > _MAX_SAMPLE:
        raise VoiceTrialError("untrusted trial snapshot")
    return json.loads(source.read_text(encoding="utf-8"))


def main(args: list[str]) -> int:
    try:
        if len(args) == 1 and args[0] == "snapshot":
            report = snapshot()
        elif len(args) == 3 and args[0] == "compare":
            report = compare(_read_sample(args[1]), _read_sample(args[2]))
        else:
            raise VoiceTrialError("usage: voice_live_trial.py snapshot | compare BEFORE.json AFTER.json")
        print(json.dumps(report, sort_keys=True))
        return 0
    except (VoiceTrialError, OSError, ValueError, TypeError, KeyError,
            RuntimeError, subprocess.SubprocessError) as error:
        print("Voice live trial refused: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
