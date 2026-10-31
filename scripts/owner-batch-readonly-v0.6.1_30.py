#!/usr/local/bin/python3.13
"""Three read-only OPNsense owner checks; no Apply, Stop/Start, network or IPFW writes.

Emit only service statuses and aggregate counts, never saved IP/domain content.
"""
import datetime
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

EXPECTED = "0.6.1_30"
ROOT = Path("/usr/local/etc/zapret2/runtime-v2")
SERVICE = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
INSPECT = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/backend/voice_live_inspect.py")
checks = []


def mark(group, name, ok, details=None, optional=False):
    status = "PASS" if ok else ("WARN" if optional else "FAIL")
    row = {"group": group, "check": name, "status": status}
    if details is not None:
        row["details"] = details
    checks.append(row)
    print(f"[{status}] {group} {name}" +
          (f" ({details})" if details is not None else ""), flush=True)


def cmd(args, timeout=14):
    try:
        p = subprocess.run(args, capture_output=True, text=True,
                           timeout=timeout, check=False)
        return p.returncode, p.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return 127, ""


def read(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 2_000_000:
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def package_service():
    group = "1 PACKAGE/SERVICE:"
    rc, out = cmd(["/usr/sbin/pkg", "info", "-x", "os-zapret2-restyle"])
    versions = [v.strip() for v in out.splitlines() if v.strip()]
    mark(group, "correct installed package",
         rc == 0 and versions == ["os-zapret2-restyle-" + EXPECTED],
         versions[0] if versions else "package absent")
    system = os.uname()
    mark(group, "FreeBSD 15", system.sysname == "FreeBSD" and system.release.startswith("15."),
         system.sysname + " " + system.release)
    mark(group, "production service installed", SERVICE.is_file())
    if SERVICE.is_file():
        rc, out = cmd(["/bin/sh", str(SERVICE), "status"], timeout=18)
        mark(group, "service is running",
             rc == 0 and "running" in out.lower(),
             "running" if rc == 0 and "running" in out.lower() else "not confirmed")
    rc, out = cmd(["/bin/pgrep", "-f", "[/]dvtws2"])
    mark(group, "dvtws2 process observed",
         rc == 0 and any(x.isdecimal() for x in out.splitlines()),
         optional=True)


def exclude():
    group = "2 STRATEGIES/EXCLUDE:"
    args = read(ROOT / "dvtws.args")
    mark(group, "installed active dvtws args", args is not None)
    if args is not None:
        profiles = [x for x in re.split(r"(?m)^--new\s*$", args) if x.strip()]
        counts = [len(re.findall(r"(?m)^--ipset-exclude=", p)) for p in profiles]
        mark(group, "one global IP exclusion per active profile",
             len(profiles) > 0 and all(n == 1 for n in counts),
             {"profiles": len(profiles), "exactly_once": sum(n == 1 for n in counts)})
        wrong = sum(bool(re.search(r"(?m)^--hostlist-exclude=", p)) and
                    ("--name=voice-" in p or "--filter-l7=stun" in p)
                    for p in profiles)
        mark(group, "domain exclude absent from Voice/STUN", wrong == 0,
             {"violations": wrong})
    data = read(ROOT / "managed/ipset-exclude.txt")
    mark(group, "managed Exclude IPSet present", data is not None)
    if data is not None:
        counts = {"ipv4": 0, "ipv6": 0, "invalid": 0, "full_family": 0}
        for raw in data.splitlines():
            value = raw.strip()
            if not value or value.startswith("#"):
                continue
            try:
                network = ipaddress.ip_network(value, strict=False)
                counts["ipv" + str(network.version)] += 1
                counts["full_family"] += network.prefixlen == 0
            except ValueError:
                counts["invalid"] += 1
        mark(group, "valid IPv4/IPv6 exclusions, no /0",
             counts["invalid"] == 0 and counts["full_family"] == 0, counts)
    try:
        config = ET.parse("/conf/config.xml").getroot()
        zapret = config.find("./OPNsense/Zapret")
        mark(group, "native saved Zapret Config", zapret is not None)
        mark(group, "Exclude IPSet saved field",
             config.find("./OPNsense/Zapret/hostlist/excludeipset") is not None,
             optional=True)
    except (ET.ParseError, OSError, ValueError):
        mark(group, "native saved Config readable", False)


def firewall_voice_resources():
    group = "3 IPFW/VOICE/RESOURCES:"
    if INSPECT.is_file():
        rc, output = cmd(["/usr/local/bin/python3.13", str(INSPECT)], timeout=20)
        try:
            data = json.loads(output)
        except (ValueError, TypeError):
            data = None
        mark(group, "native Voice inspector returns JSON",
             rc == 0 and isinstance(data, dict))
        if isinstance(data, dict):
            engine = data.get("runtime", {}).get("engine_verified") is True or data.get("engine_verified") is True
            mark(group, "shared engine attested", engine,
                 {"condition": str(data.get("condition", "unknown"))[:80],
                  "rule_count": data.get("rule_count")})
    else:
        mark(group, "native Voice inspector installed", False)
    rc, listing = cmd(["/sbin/ipfw", "list"])
    if rc:
        mark(group, "read-only IPFW list", False)
    else:
        numbers = [int(m.group(1)) for line in listing.splitlines()
                   if (m := re.match(r"^\s*(\d+)\s", line))]
        owned = [n for n in numbers if 19000 <= n <= 19010]
        temporary = [n for n in numbers if 19100 <= n <= 19131]
        mark(group, "IPFW read-only snapshot", True,
             {"common_owned": len(owned), "lab_temporary": len(temporary)})
        mark(group, "no stale laboratory IPFW rules", not temporary)
    inventory = (Path("/var/db/zapret2/extra-resources/installed.json"),
                 Path("/usr/local/etc/zapret2/extra-resources/installed.json"))
    mark(group, "Extra Resources inventory observed", True,
         "present" if any(p.is_file() for p in inventory) else "absent (allowed)")
    mark(group, "Strategy Lab installed",
         Path("/usr/local/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/result.py").is_file(),
         optional=True)


def main():
    if os.geteuid() != 0 or len(sys.argv) != 1:
        print("Usage: run this script as root with no arguments.", file=sys.stderr)
        return 64
    package_service()
    exclude()
    firewall_voice_resources()
    stamp = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "schema": 1, "expected_package": EXPECTED, "timestamp_utc": stamp.isoformat(),
        "checks": checks,
        "limits": "Read-only local checks; no WAN DPI, GUI, Apply or calls tested."
    }
    path = Path("/root") / ("zapret2-batch-" + stamp.strftime("%Y%m%d-%H%M%S") + ".json")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as output:
        json.dump(payload, output, indent=2, ensure_ascii=False)
        output.write("\n")
    totals = {s: sum(c["status"] == s for c in checks)
              for s in ("PASS", "WARN", "FAIL")}
    print("SUMMARY:", json.dumps(totals, ensure_ascii=False))
    print("REPORT:", path)
    return 1 if totals["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
